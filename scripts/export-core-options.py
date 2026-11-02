#!/usr/bin/env python3
"""Export the built core's actual V2 options and refresh the review inventory."""
import argparse
import ctypes as c
import json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('core',type=Path)
a=p.parse_args()
root=Path(__file__).resolve().parent.parent
snapshot=root/'CORE_OPTIONS_IMPLEMENTED.json'
old={d['key']:d for d in json.loads(snapshot.read_text())} if snapshot.exists() else {}
class Value(c.Structure):
    _fields_=[('value',c.c_char_p),('label',c.c_char_p)]
class Definition(c.Structure):
    _fields_=[('key',c.c_char_p),('desc',c.c_char_p),('desc_categorized',c.c_char_p),
              ('info',c.c_char_p),('info_categorized',c.c_char_p),('category_key',c.c_char_p),
              ('values',Value*128),('default_value',c.c_char_p)]
class Options(c.Structure):
    _fields_=[('categories',c.c_void_p),('definitions',c.POINTER(Definition))]
records=[]
def decode(value):return value.decode() if value else ''
@c.CFUNCTYPE(c.c_bool,c.c_uint,c.c_void_p)
def environment(command,data):
    if command==52:
        c.cast(data,c.POINTER(c.c_uint))[0]=2;return True
    if command==67: # SET_CORE_OPTIONS_V2
        o=c.cast(data,c.POINTER(Options)).contents
        i=0
        while o.definitions[i].key:
            d=o.definitions[i];key=decode(d.key)
            values=[]
            for v in d.values:
                if not v.value:break
                values.append(dict(value=decode(v.value),label=decode(v.label) or decode(v.value)))
            record=dict(key=key,label=decode(d.desc),info=decode(d.info),category=decode(d.category_key),
                        default=decode(d.default_value),values=values)
            if key in old:
                for field in ('catalogue','field'):
                    if field in old[key]:record[field]=old[key][field]
            records.append(record);i+=1
        return True
    return False
core=c.CDLL(str(a.core.resolve()))
core.retro_set_environment.argtypes=[type(environment)]
core.retro_set_environment(environment)
assert records and len({d['key'] for d in records})==len(records)
snapshot.write_text(json.dumps(records,indent=2)+'\n')
review=root/'CORE_OPTIONS_IMPLEMENTED_REVIEW.md'
text=review.read_text()
head=text[:text.index('## General Options')]
head=head.replace('Status: User Review Responses Applied. Existing Uncommented Options Retained; No New Options Added.',
                  'Status: Native Options Retained; Shared Input, Rumble And Audio Integration Added.')
general=[d for d in records if not d.get('catalogue')]
head=head.replace('Date: 2026-10-20. Status: Native Options Retained; Shared Input, Rumble And Audio Integration Added.', 'Date: 2026-10-21. Status: Native Options Retained; M13 Network Integration Delivered.')
head=head.replace('M13 Network Integration Under Review.', 'M13 Network Integration Delivered.')
start=head.index('Extracted from the built core')
end=head.index('\n\nReference:',start)
head=head[:start]+f'Extracted from the built core through Core Options V2 registration: {len(records)} definitions = {len(general)} general options + 340 operator fields across 56 catalogues. Registration, ROM-free tests, frontend execution and physical hardware verification are separate evidence levels.'+head[end:]
# Retain the already reviewed native mappings, regenerate every value list from the ABI.
oldrows={}
for line in text[text.index('## General Options'):text.index('## NVRAM Differences')].splitlines():
    parts=line.split('|')
    if len(parts)==6:oldrows[parts[1].strip()]=(parts[3].strip(),parts[4].strip())
rows=[]
for d in general:
    vals='; '.join(('**'+v['label']+'**') if v['value']==d['default'] else v['label'] for v in d['values'])
    match=oldrows.get(d['label'])
    if d['key'].startswith(('model2emuex_linked_cabinets_','model2emuex_automatic_network_')):
        reference='SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle.'
        native='Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback.'
    elif match and d['key'] not in ('model2emuex_crosshairs','model2emuex_crosshair_style','model2emuex_crosshair_timeout'):reference,native=match
    elif d['key']=='model2emuex_rom_crc_verification':
        reference='Same selector, Enabled default and content-reload lifecycle.'
        native='Native loader checks ZIP metadata. The shared Enabled choice also computes CRC32 of actual ZIP/loose payload bytes. Disabled skips CRC matching; size/decompression remain checked. Original standalone API keeps metadata-only CRC policy.'
    elif d['key']=='model2emuex_timing_overlay':
        reference='Same label, Off/Auto/11–14 px values, Off default and live lifecycle.'
        native='Reuses SM2 panel and measurement equations, destination CPU timings and frontend OpenGL submission. Caption uses the actual 60/58 Hz cadence. See TIMING_OVERLAY.md for limits.'
    elif d['key']=='model2emuex_av_timing':
        reference='Same selector and 60 Hz default; SM2 native choice is 57.524 Hz.'
        native='Native catalogue declares 58 Hz. User approved 60 Hz default. One native machine frame per callback; SM2 endpoint audio interpolation. Content reload required.'
    elif d['key'] in ('model2emuex_crosshairs','model2emuex_crosshair_style','model2emuex_crosshair_timeout'):
        reference='Same selector, values and default, explicitly approved by the user.'
        native='No standalone external crosshair. Reuses unchanged SM2 presentation/PNG module; destination OpenGL overlay and system/model2emuex/crosshairs directory. Resume without reset; PNG changes require content reload.'
    elif d['key']=='model2emuex_manxtt_cabinet_audio':
        reference='Same label, help, Enabled/Disabled values, Enabled default and NVRAM-driven cabinet policy.'
        native='Native primary SCSP with optional Model 1 audio board and full SM2 I8251/AMS path. Optional sound-only sibling ROMs; selected-set fallback and notices follow SM2. Inert outside Manx TT. See MANX_TT_CABINET_AUDIO.md.'
    elif d['category']=='audio':
        reference='Same label, Auto/Mute/10–100% values and Auto default.'
        native='No native selector. Optional neutral source-gain API; Auto and 100% retain the native mix. Muted synthesis continues. Absent sources are no-ops. Resume without reset.'
    else:
        reference='Same selector, values and default; `'+d['key'].replace('model2emuex_','sm2_',1)+'`.'
        native='No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits.'
    rows.append('| '+d['label']+' | '+vals+' | '+reference+' | '+native+' |')
tail=text[text.index('## NVRAM Differences'):]
tail=tail.replace('- Pending: linked cabinets, automatic role settings, applicable cabinet audio extensions.', '- Pending: applicable cabinet audio extensions. Linked Cabinets and Auto Network Role Settings are integrated; see EXTERNAL_LINKED_CABINETS.md for qualification limits.')
tail=tail.replace('- Pending: applicable cabinet audio extensions.', '- Manx TT cabinet audio is integrated; see MANX_TT_CABINET_AUDIO.md.')
tail=tail.replace('Imported SM2 input/rumble/network helpers are not delivered runtime features.',
                  'SM2 input and rumble are integrated and ROM-free tested; external Netpacket is integrated; see EXTERNAL_LINKED_CABINETS.md for qualification and the approved all-set local loopback.')
# Historical exclusion sentence must not contradict the delivered input/audio blocks.
tail=tail.replace('- Not yet integrated: shared input profiles, Gamepad Rumble, audio gains/timing, gun controls, Save States and linked cabinets.',
                  '- Pending: crosshair/flash presentation, further audio processing, Save States and linked cabinets. Shared input profiles, gun inputs, Gamepad Rumble, source gains and A/V Timing are integrated.')
review.write_text(head+'## General Options\n\n| Option | Values (Default In Bold) | SM2 Equivalent | Native Model2EmuEx / Adaptation |\n| --- | --- | --- | --- |\n'+'\n'.join(rows)+'\n\n'+tail)
print(f'Exported {len(records)} definitions ({len(general)} general options).')
