#!/usr/bin/env python3
"""ROM-free ABI metadata, legacy options and rejected-content smoke check."""
import ctypes as c
from pathlib import Path
import sys
core = c.CDLL(str(Path(sys.argv[1]).resolve()))
class SystemInfo(c.Structure):
    _fields_ = [('name', c.c_char_p), ('version', c.c_char_p), ('extensions', c.c_char_p),
                ('need_fullpath', c.c_bool), ('block_extract', c.c_bool)]
class Variable(c.Structure):
    _fields_ = [('key', c.c_char_p), ('value', c.c_char_p)]
class GameInfo(c.Structure):
    _fields_ = [('path', c.c_char_p), ('data', c.c_void_p), ('size', c.c_size_t), ('meta', c.c_char_p)]
registered = []
@c.CFUNCTYPE(c.c_bool, c.c_uint, c.c_void_p)
def environment(command, data):
    if command == 52:  # GET_CORE_OPTIONS_VERSION: exercise legacy fallback
        c.cast(data, c.POINTER(c.c_uint))[0] = 0
        return True
    if command == 16:  # SET_VARIABLES
        values = c.cast(data, c.POINTER(Variable))
        i = 0
        while values[i].key:
            registered.append((values[i].key.decode(), values[i].value.decode()))
            i += 1
        return True
    return False
core.retro_set_environment.argtypes = [type(environment)]
core.retro_set_environment(environment)
core.retro_init()
expected = {
    'model2emuex_internal_resolution': 'Internal Resolution; 1|2|3|4',
    'model2emuex_texture_filter': '3D Texture Filtering; nearest|bilinear|trilinear',
    'model2emuex_aspect_ratio': 'Aspect Ratio; auto|4_3|16_9|16_10',
    'model2emuex_widescreen_mode': 'Widescreen Mode; stretch|expand_3d',
    'model2emuex_pipeline': 'Pipeline; enabled|disabled',
    'model2emuex_frame_skip': 'Frame Skip; enabled|disabled',
    'model2emuex_mesh': 'Shadows And Fences; blend|checker',
}
expected.update({
    'model2emuex_linked_cabinets_unsupported':'Linked Cabinets; unsupported',
    'model2emuex_automatic_network_unsupported':'Auto Network Role Settings; unsupported',
    'model2emuex_controller_profile_type': 'Controller Profile Type; test_service|normal',
    'model2emuex_gamepad_rumble': 'Gamepad Rumble; enabled|disabled',
    'model2emuex_gun_input': 'Gun Input Mode; hybrid|lightgun|mouse_analog|mouse|analog',
    'model2emuex_gun_stick_control': 'Gun Analog Stick Control; relative|absolute',
    'model2emuex_offscreen_reload_shortcut': 'Off-Screen Reload Shortcut; enabled|disabled',
    'model2emuex_mouse_edge_offscreen_reload': 'Mouse Edge Off-Screen Reload; disabled|enabled',
    'model2emuex_four_speed_shifter': '4-Speed Shifter; h_gate|standard',
    'model2emuex_gear_shift_neutral_time': 'Gear Shift Neutral Time; 100|'+'|'.join(str(i) for i in range(0,501,10) if i!=100),
    'model2emuex_automatic_start_gear': 'Automatic Start Gear (Restart Required); enabled|disabled',
    'model2emuex_steering_response': 'Driving Steering Response; linear|progressive|fbneo',
    'model2emuex_steering_output_range': 'Driving Steering Output Range; 100|50|60|63|70|80|90|110|120|130|140|150',
    'model2emuex_accelerator_output_range': 'Driving Accelerator Output Range; 100|50|60|70|75.3|80|90|110|120|130|140|150',
    'model2emuex_brake_output_range': 'Driving Brake Output Range; 100|50|60|70|75.3|80|90|110|120|130|140|150',
    'model2emuex_desert_elevation_control': 'Desert Tank: Elevation Control; relative|absolute',
    'model2emuex_desert_elevation_speed': 'Desert Tank: Elevation Speed (Relative Only); 100|'+'|'.join(str(i) for i in range(10,201,10) if i!=100),
    'model2emuex_desert_elevation_axis': 'Desert Tank: Elevation Axis Mode; normal|inverted',
})
expected['model2emuex_timing_overlay'] = 'Timing / FPS Overlay; disabled|auto|11|12|13|14'
expected['model2emuex_rom_crc_verification'] = 'ROM CRC Verification (Restart Required); enabled|disabled'
expected['model2emuex_manxtt_cabinet_audio'] = 'Manx TT: Cabinet Audio; enabled|disabled'
expected['model2emuex_av_timing'] = 'A/V Timing (Restart Required); 60hz|native'
for key, label in [('scsp_gain', 'SCSP Gain'), ('multipcm1_gain', 'MultiPCM 1 Gain'),
                   ('multipcm2_gain', 'MultiPCM 2 Gain'), ('ym3438_gain', 'FM (YM3438) Gain')]:
    expected['model2emuex_'+key] = label+'; auto|0|10|20|30|40|50|60|70|80|90|100'
expected.update({
    'model2emuex_crosshairs': 'Show Crosshair; auto|0|1|2|3',
    'model2emuex_crosshair_style': 'Crosshair Style; sm2|auto|supermodel|custom',
    'model2emuex_crosshair_timeout': 'Crosshair Inactivity Timeout; disabled|1|2|3|4|5|6|7|8|10|15|30|60',
})
assert dict(registered)['model2emuex_initial_nvram_setup'].endswith('; enabled|disabled')
assert dict(registered)['model2emuex_nvram_settings'].endswith('; disabled|enabled')
assert len(registered) == 42
assert registered[0][0] == 'model2emuex_rom_crc_verification'
ordered_keys=[key for key,value in registered]
input_order=['controller_profile_type','gamepad_rumble','crosshairs','crosshair_style','crosshair_timeout',
             'gun_input','gun_stick_control','offscreen_reload_shortcut','mouse_edge_offscreen_reload',
             'four_speed_shifter','gear_shift_neutral_time','automatic_start_gear','steering_response',
             'steering_output_range','accelerator_output_range','brake_output_range',
             'desert_elevation_control','desert_elevation_speed','desert_elevation_axis']
indices=[ordered_keys.index('model2emuex_'+key) for key in input_order]
assert indices==sorted(indices)
for key, value in registered:
    if key in ('model2emuex_initial_nvram_setup', 'model2emuex_nvram_settings'):
        continue
    if key in expected:
        assert value == expected[key]
    else:
        assert key in ['model2emuex_saturation', 'model2emuex_gamma_r', 'model2emuex_gamma_g', 'model2emuex_gamma_b']
        tokens = value.split('; ')[1].split('|')
        assert tokens[0] == '1.00' and len(tokens) == 31 and len(set(tokens)) == 31
        assert min(map(float, tokens)) == 0.5 and max(map(float, tokens)) == 2.0

info = SystemInfo()
core.retro_get_system_info(c.byref(info))
assert info.name == b'Model2EmuEx' and info.extensions == b'zip'
assert info.need_fullpath and info.block_extract
assert core.retro_api_version() == 1
core.retro_serialize_size.restype = c.c_size_t
assert core.retro_serialize_size() == 12 * 1024 * 1024
core.retro_serialize.argtypes = [c.c_void_p, c.c_size_t]
core.retro_serialize.restype = c.c_bool
core.retro_unserialize.argtypes = [c.c_void_p, c.c_size_t]
core.retro_unserialize.restype = c.c_bool
assert not core.retro_serialize(None, core.retro_serialize_size())
assert not core.retro_unserialize(None, core.retro_serialize_size())
core.retro_load_game.argtypes = [c.POINTER(GameInfo)]
core.retro_load_game.restype = c.c_bool
assert not core.retro_load_game(None)
for path in (b'/no-such-dir/unknown.zip', b'/no-such-dir/vf2.7z', b'/no-such-dir/vf2.zip'):
    game = GameInfo(path=path)
    assert not core.retro_load_game(c.byref(game))
core.retro_get_memory_size.restype = c.c_size_t
assert core.retro_get_memory_size(0) == 0
core.retro_unload_game()
core.retro_deinit()
print('PASS: ABI metadata, legacy options/default, rejected content, empty memory and cleanup')
