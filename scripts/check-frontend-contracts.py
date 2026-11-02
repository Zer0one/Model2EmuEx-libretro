#!/usr/bin/env python3
"""Targeted M25 ABI faults/retry checks; read ROMs in place, isolate all output."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom-directory', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='New isolated directory')
parser.add_argument('--pipeline', choices=('enabled', 'disabled'), default='disabled')
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
roms = args.rom_directory.resolve(strict=True)
core = root / 'port/build-libretro-macos/model2emuex_dev_libretro.dylib'
spec = importlib.util.spec_from_file_location('network_contracts', root/'scripts/test-network-conventions.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
PROC = C.CFUNCTYPE(C.c_void_p, C.c_char_p)
FRAME = C.CFUNCTYPE(C.c_size_t)
RESET = C.CFUNCTYPE(None)
class HW(C.Structure):
    _fields_ = [('kind', C.c_int), ('reset', RESET), ('framebuffer', FRAME), ('proc', PROC)]

def frontend(label, values=None, legacy=False):
    f = mod.Frontend(core, out/'system', out/label)
    f.original = f.environment
    f.writes, f.notifications, f.shutdowns = [], [], []
    f.missing, f.framebuffer = PROC(lambda name: None), FRAME(lambda: 0)
    def observe(command, data):
        if command == 14:
            f.hw = C.cast(data, C.POINTER(HW)).contents
            f.hw.proc, f.hw.framebuffer = f.missing, f.framebuffer
        if command == 70:
            v = C.cast(data, C.POINTER(mod.abi.Variable)).contents
            f.writes.append((v.key.decode(), v.value.decode()))
        if command == 7:
            f.shutdowns.append(True)
            return True
        if command == 59 and legacy:
            C.cast(data, C.POINTER(C.c_uint))[0] = 0
            return True
        if command == 60:
            m = C.cast(data, C.POINTER(mod.abi.MessageExt)).contents
            f.notifications.append((m.msg.decode(), m.level, m.priority))
        return f.original(command, data)
    f.observer = mod.abi.ENV(observe)
    f.lib.retro_deinit()
    f.lib.retro_set_environment(f.observer)
    f.lib.retro_init()
    f.values[b'model2emuex_pipeline'] = args.pipeline.encode()
    if values:
        f.values.update({k.encode(): v.encode() for k, v in values.items()})
    return f

def load(f, name):
    f.game = mod.abi.Game(str(roms/(name+'.zip')).encode(), None, 0, None)
    return bool(f.lib.retro_load_game(C.byref(f.game)))

results = {}
for legacy in (False, True):
    f = frontend('unknown-'+str(legacy), legacy=legacy)
    assert not load(f, 'unknown')
    assert any('Unknown ROM set' in m for m in f.messages)
    if not legacy:
        assert any(level == 3 and priority == 2 for _, level, priority in f.notifications)
    assert not f.shutdowns
    results['load_error_legacy' if legacy else 'load_error_extended'] = f.messages.copy()
    f.close()

for fault in ('gpu', 'invalid-audio', 'stalled-audio'):
    f = frontend(fault)
    assert load(f, 'vf2')
    delivered = []
    def batch(samples, n):
        delivered.append(n)
        return n+1 if fault == 'invalid-audio' else 0 if fault == 'stalled-audio' else n
    f.batch_observer = mod.abi.BATCH(batch)
    f.lib.retro_set_audio_sample_batch(f.batch_observer)
    if fault == 'gpu':
        f.hw.reset()
    f.run(65 if fault == 'stalled-audio' else 1)
    before = len(delivered)
    f.run(2)
    assert len(f.shutdowns) == 1 and len(delivered) == before
    assert any(level == 3 and priority == 2 for _, level, priority in f.notifications)
    if fault == 'gpu':
        assert not delivered
    results[fault] = {'shutdowns': len(f.shutdowns), 'audio_callbacks': before,
                      'notifications': f.notifications.copy()}
    f.close()

keys = ['model2emuex_linked_cabinets_manxtt', 'model2emuex_automatic_network_manxtt']
f = frontend('network', {k: 'invalid' for k in keys})
assert load(f, 'manxtt')
assert all(f.values[k.encode()] == b'-1' for k in keys)
assert len([w for w in f.writes if w[0] in keys]) == 2
f.set({k: 'invalid-again' for k in keys})
before = len(f.writes)
assert all(f.values[k.encode()] == b'invalid-again' for k in keys)  # Readers only queue.
f.run()
assert all(f.values[k.encode()] == b'-1' for k in keys)
assert len(f.writes) == before+2
warnings = len(f.messages)
f.run(3)
assert len(f.messages) == warnings and not f.shutdowns
results['network'] = {'writes': f.writes.copy(), 'warnings': f.messages.copy(), 'reentrant_display': True}
f.close()

values = {'model2emuex_initial_nvram_setup': 'disabled', 'model2emuex_nvram_settings': 'enabled',
          'model2emuex_nvram_vf2_difficulty': 'hard'}
f = frontend('late-nvram', values)
assert load(f, 'vf2')
f.run(600)
assert len(f.memory()) == 65664 and f.memory()[13122] & 3 == 2
assert f.resets() == 1, f.messages
f.run(4)
assert f.resets() == 1
f.set({'model2emuex_nvram_vf2_difficulty': 'normal'})
f.run()
assert f.memory()[13122] & 3 == 1 and f.resets() == 2
results['late_nvram'] = {'difficulty_after_retry': 'hard', 'resets_after_retry': 1,
                         'resets_after_live_normal': f.resets(), 'save_ram_size': len(f.memory())}
f.close()

f = frontend('cancel-pending', values)
assert load(f, 'vf2')
f.run()
f.set({'model2emuex_nvram_settings': 'disabled'})
f.run(600)
assert f.memory()[13122] & 3 == 1 and not f.resets()
results['cancel_pending'] = {'native_difficulty': 'normal', 'resets': f.resets()}
f.close()
f = frontend('persisted-user-image', {
    'model2emuex_nvram_settings': 'enabled', 'model2emuex_nvram_vf2_difficulty': 'hard'})
assert load(f, 'vf2')
f.run()
user = bytearray(f.memory())
assert user[13122] & 3 == 2
user[0xff00] = 0x6d  # Beyond the shared 16 KiB view; native raw bytes must survive.
user = bytes(user)
(out/'saved-user.srm').write_bytes(user)
f.close()

for initial in ('enabled', 'disabled'):
    f = frontend('save-precedence-'+initial, {
        'model2emuex_initial_nvram_setup': initial, 'model2emuex_nvram_settings': 'disabled'})
    assert load(f, 'vf2')
    C.memmove(f.lib.retro_get_memory_data(0), (out/'saved-user.srm').read_bytes(), len(user))
    f.run()
    assert f.memory() == user, initial
    assert not f.resets()
    (out/('reloaded-'+initial+'.srm')).write_bytes(f.memory())
    f.close()
results['raw_save_precedence'] = {'initial_setup_enabled_and_disabled': True,
    'fresh_core_reload_exact': True, 'bytes': len(user), 'sha256': hashlib.sha256(user).hexdigest()}

f = frontend('save-precedence-override', {
    'model2emuex_initial_nvram_setup': 'enabled', 'model2emuex_nvram_settings': 'enabled',
    'model2emuex_nvram_vf2_difficulty': 'normal'})
assert load(f, 'vf2')
C.memmove(f.lib.retro_get_memory_data(0), user, len(user))
f.run()
overridden = f.memory()
assert overridden[13122] & 3 == 1 and overridden[0x4000:] == user[0x4000:]
f.run(3)
assert not f.resets()  # Initial application is silent; unchanged Resume does not reset.
f.set({'model2emuex_nvram_vf2_difficulty': 'hard'})
f.run()
assert f.memory()[13122] & 3 == 2 and f.resets() == 1
results['raw_save_operator_authority'] = {'normal_then_live_hard': True,
    'tail_and_eeprom_preserved': True, 'one_live_reset': True}
f.close()
results['core_sha256'] = hashlib.sha256(core.read_bytes()).hexdigest()
results['pipeline'] = args.pipeline
(out/'result.json').write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results, indent=2))
