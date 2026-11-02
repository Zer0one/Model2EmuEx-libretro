#!/usr/bin/env python3
"""Import explicitly selected existing SM2 frontend helpers with source provenance."""
from pathlib import Path
import argparse, hashlib, json, subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference',type=Path,required=True)
a=p.parse_args(); ref=a.reference.resolve()
root=Path(__file__).resolve().parent.parent
out=root/'src/libretro/sm2'
files=['nvram_settings.h','nvram_settings.cpp','nvram_settings_data.inc',
       'initial_nvram.h','initial_nvram.cpp','initial_nvram_templates.inc',
       'save_ram.h','save_ram.cpp','automatic_network.h','automatic_network.cpp',
       'input.h','input.cpp','rumble.h','rumble.cpp','crosshair.h','crosshair.cpp','timing_overlay.h','timing_overlay.cpp']
manifest=out/'IMPORT.json'
previous=json.loads(manifest.read_text()) if manifest.exists() else {'files':{}}
records={}
extra={
 'include/rom/game.h':'src/rom/game.h', 'include/rom/game_db.h':'src/rom/game_db.h',
 'rom/game.cpp':'src/rom/game.cpp','rom/game_db.cpp':'src/rom/game_db.cpp',
 'include/core/types.h':'src/core/types.h','include/core/log.h':'src/core/log.h','core/log.cpp':'src/core/log.cpp',
 'include/osd/drive_command.h':'src/osd/drive_command.h','osd/drive_command.cpp':'src/osd/drive_command.cpp',
 'pugixml/pugixml.cpp':'3rdparty/pugixml/src/pugixml.cpp',
 'include/pugixml.hpp':'3rdparty/pugixml/src/pugixml.hpp','include/pugiconfig.hpp':'3rdparty/pugixml/src/pugiconfig.hpp',
 'checks/timing_overlay.cpp':'src/libretro/checks/timing_overlay.cpp',
 'checks/input.cpp':'src/libretro/checks/input.cpp',
 'include/stb_image.h':'3rdparty/stb/stb_image.h',
 'data/games.xml':'data/games.xml','LICENSE.sm2':'LICENSE','NOTICE.sm2':'NOTICE'
}
for name in files:
    source=ref/'src/libretro'/name; target=out/name; data=source.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if target.exists() and target.read_bytes()!=data:
        expected=previous['files'].get(name,{}).get('sha256')
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            raise SystemExit(f'Local changes must be reviewed before replacing {target}')
    source_digest=digest
    if name=='timing_overlay.cpp':
        original='ImGui::Text("SM2 timing (%s)", data.native_timing ? "57.524 Hz" : "60 Hz");'
        replacement='ImGui::Text("Model2EmuEx Timing (%.3f Hz)", frames_per_second);'
        assert original.encode() in data
        data=data.replace(original.encode(),replacement.encode())
        digest=hashlib.sha256(data).hexdigest()
    target.write_bytes(data)
    records[name]={'source':str(source.relative_to(ref)),'sha256':digest,'unchanged':name!='timing_overlay.cpp'}
    if name=='timing_overlay.cpp':records[name].update(source_sha256=source_digest,adaptation='Panel title and actual destination cadence only')
for name,original in extra.items():
    source=ref/original; target=out/name; data=source.read_bytes()
    target.parent.mkdir(parents=True,exist_ok=True)
    source_digest=digest
    if name=='timing_overlay.cpp':
        original='ImGui::Text("SM2 timing (%s)", data.native_timing ? "57.524 Hz" : "60 Hz");'
        replacement='ImGui::Text("Model2EmuEx Timing (%.3f Hz)", frames_per_second);'
        assert original.encode() in data
        data=data.replace(original.encode(),replacement.encode())
        digest=hashlib.sha256(data).hexdigest()
    target.write_bytes(data)
    records[name]={'source':original,'sha256':hashlib.sha256(data).hexdigest(),'unchanged':True}
# Only the unchanged Inputs data model is needed by the reused frontend adapter;
# do not import an unrelated machine class or its CPU/render dependencies.
source=ref/'src/hw/model2_machine_base.h'; text=source.read_text()
start=text.index('struct Inputs {'); end=text.index('\n};',start)+3
inputs=text[:text.index('#pragma once')]+'#pragma once\n#include "core/types.h"\n#include "rom/game.h"\n#include <array>\n#include <iterator>\nnamespace sm2::hw {\n'+text[start:end]+'\n}\n'
target=out/'include/hw/model2_machine_base.h';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(inputs)
records['include/hw/model2_machine_base.h']={'source':'src/hw/model2_machine_base.h','sha256':hashlib.sha256(inputs.encode()).hexdigest(),'unchanged_struct':'Inputs'}
xml=(out/'data/games.xml').read_text()
assert ')M2XML"' not in xml
(out/'data/games_xml.inc').write_text('// Embedded unchanged SM2 metadata; see IMPORT.json and NOTICE.sm2.\nstatic constexpr char sm2_games_xml[] = R"M2XML('+xml+')M2XML";\n')
text=(ref/'src/libretro/core_options.h').read_text()
functions=[]
for name in ('retroarch_option_label','retroarch_option_info'):
    start=text.index('inline std::string '+name+'(')
    pos=text.index('{',start); level=1; end=pos+1
    while level:
        if text[end]=='{':level+=1
        elif text[end]=='}':level-=1
        end+=1
    functions.append(text[start:end])
wording='// SPDX-License-Identifier: BSD-3-Clause\n// Functions imported from SM2 core_options.h without algorithm changes.\n#pragma once\n#include "nvram_settings.h"\n#include <algorithm>\n#include <cctype>\n#include <iterator>\n#include <string>\n#include <string_view>\nnamespace sm2::libretro {\n'+'\n\n'.join(functions)+'\n}\n'
(out/'menu_wording.h').write_text(wording)
records['menu_wording.h']={'source':'src/libretro/core_options.h','sha256':hashlib.sha256(wording.encode()).hexdigest(),'unchanged_functions':['retroarch_option_label','retroarch_option_info']}
result={'reference':'https://github.com/Zer0one/sm2-emu-libretro','head':subprocess.check_output(['git','-C',str(ref),'rev-parse','HEAD'],text=True).strip(),'source_state':'Live working-copy contents, including local changes','files':records}
manifest.write_text(json.dumps(result,indent=2)+'\n')
print(f'Imported {len(files)} existing helpers/data files and two unchanged wording functions')
