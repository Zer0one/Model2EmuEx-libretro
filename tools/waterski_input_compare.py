#!/usr/bin/env python3
"""Compare Water Ski's adapted Pitch switches with the original input decoder.

Use the pinned executable and a probe calling the actual Libretro bridge and
native board byte reader. The OS device poll is bypassed. Original keyboard
state decoding and digital binding evaluation execute unchanged, stopping
before application hotkeys. Includes P1 aliases, P2 isolation, held inputs,
release, and simultaneous Select Up / Set.
"""
import argparse
import ctypes
import itertools
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'port/sharc/test'))
from difftest_bits import load_original, SP, STOP
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX


def compare(exe, library):
    native = load_original(exe)
    obj, config, head, table = 0x72000000, 0x72001000, 0x72002000, 0x72003000
    native.mem_map(obj, 0x4000)

    def put(address, *values):
        native.mem_write(address, struct.pack('<'+'I'*len(values), *values))

    put(obj, table)
    put(obj+0x59c, config)
    put(table+0x40, STOP+0x100)
    native.mem_write(STOP+0x100, b'\xc3')
    put(table+0x44, 0x4f0c20)
    # Native Water Ski records: packed port/mask, DirectInput key, kind.
    bindings = [(0x0401, 0x1e, 0), (0x0801, 0x1f, 0),
                (0x0201, 0xc8, 1), (0x0101, 0x2c, 1)]
    put(config+4, head)
    native.mem_write(config+0x10, bytes([255, 0xf3, 0xcf, 0, 0, 0, 0, 0]))
    nodes = [head+0x20+i*0x20 for i in range(len(bindings))]
    put(head, nodes[0], nodes[-1])
    for i, (packed, key, kind) in enumerate(bindings):
        put(nodes[i], nodes[i+1] if i+1<len(nodes) else head,
            nodes[i-1] if i else head, packed, key, kind, 0)

    def original(keys):
        native.mem_write(obj+0xc, bytes(256))
        for key in keys:
            native.mem_write(obj+0xc+key, b'\x80')
        native.mem_write(SP, struct.pack('<I', STOP))
        native.reg_write(UC_X86_REG_ESP, SP)
        native.reg_write(UC_X86_REG_ECX, obj)
        native.emu_start(0x4f2480, 0x4f26a6, count=10000)
        assert native.reg_read(UC_X86_REG_EIP)==0x4f26a6
        byte = native.mem_read(obj+0x575, 1)
        native.mem_write(0x5aa875, bytes(byte))
        native.mem_write(SP, struct.pack('<I', STOP))
        native.reg_write(UC_X86_REG_ESP, SP)
        native.reg_write(UC_X86_REG_ECX, 4)
        native.emu_start(0x4c88a0, STOP, count=1000)
        assert native.reg_read(UC_X86_REG_EIP)==STOP
        return native.reg_read(UC_X86_REG_EAX)&255

    probe = ctypes.CDLL(str(library.resolve())).waterski_case
    probe.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
    probe.restype = None
    states = {}
    for player, mask in itertools.product(range(2), range(64)):
        keys=[]
        if player==0:
            if mask&3: keys.append(0x1e)
            if mask&12: keys.append(0x1f)
            if mask&16: keys.append(0xc8)
            if mask&32: keys.append(0x2c)
        expected=[original(keys), original(keys), original([])]
        actual=(ctypes.c_uint*3)()
        probe(mask, player, actual)
        assert list(actual)==expected, (player, mask, list(actual), expected)
        if player==0 and mask<16: states[str(mask)]=expected
    return dict(status='pass', cases=128, byte_comparisons=384,
                original_decoder='004f2480', stop='004f26a6',
                original_keyboard='004f0c20', original_reader='004c88a0',
                pitch_only_states=states)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe',type=Path)
    parser.add_argument('library',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.exe,args.library)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='pitch_only_states'},indent=2))


if __name__=='__main__':
    main()
