#!/usr/bin/env python3
"""Record the live SM2 reference and the destination catalogue for applicability review."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
ref = args.reference.resolve()
root = Path(__file__).resolve().parent.parent

def git(*args):
    return subprocess.check_output(['git', '-C', str(ref), *args], text=True).strip()

def group(path):
    name = path.name
    if 'checks' in path.parts:
        return 'Reference Checks'
    if 'include' in path.parts:
        return 'Libretro ABI Headers'
    if name.startswith(('nvram_', 'initial_nvram', 'save_ram')):
        return 'NVRAM And Persistence'
    if name.startswith(('input.', 'crosshair.', 'gun_flash')):
        return 'Controls And Gun Presentation'
    if name.startswith(('automatic_network.', 'netpacket.')):
        return 'Network Transport And Native Role Policy'
    if name.startswith(('power_sled', 'manxtt')):
        return 'Cabinet-Specific Extensions'
    if name.startswith(('vulkan', 'opengl', 'gpu.', 'vk_', 'timing_overlay')):
        return 'Video And Diagnostics'
    if name.startswith('rumble.'):
        return 'Native And Synthetic Feedback'
    if name == 'audio_output.h':
        return 'Audio Output Processing'
    if name in ('CMakeLists.txt', 'exports.map', 'exports.macos'):
        return 'Build And Packaging'
    if name in ('core.cpp', 'core_options.h'):
        return 'Core Lifecycle And Options'
    return 'Requires Classification'

files = []
for p in sorted((ref/'src/libretro').rglob('*')):
    if not p.is_file():
        continue
    data = p.read_bytes()
    files.append(dict(path=str(p.relative_to(ref)), group=group(p),
                      sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
xml_games = {g.get('name'): g for g in ET.parse(ref/'data/games.xml').getroot().iter('game')}
text = (root/'port/m2/gamedb.inc').read_text()
pattern = r'^    \{ "([^"]+)", "([^"]+)", "([^"]+)", "([^"]+)", "([^"]+)"'
games = []
for name,title,parent,shared,board in re.findall(pattern,text,re.M):
    g = xml_games.get(name)
    games.append(dict(name=name,title=title,parent=parent,board=board,
                      destination_machine_available=board in ('Model 2','Model 2A'),
                      frontend_preparation_in_scope=True,
                      reference_name_match=g is not None,
                      reference_parent=g.get('parent') if g is not None else None,
                      identity_status='Name Match Only; ROM Revision Must Match' if g is not None else 'Explicit Identity Mapping Required'))
result = dict(reference_head=git('rev-parse','HEAD'),
              reference_dirty_paths=git('diff','--name-only').splitlines(),
              reference_policy='Live working-copy contents; hashes, not HEAD alone, identify the inspected source',
              reference_libretro_files=files,
              reference_game_count=len(xml_games),
              reference_full_catalogue=[dict(name=name, parent=g.get('parent'), board=g.get('board'),
                  present_in_destination_catalogue=any(d['name']==name for d in games),
                  preparation_policy='Prepare applicable frontend features independently of machine runtime availability; retain prototype scope rules')
                  for name,g in sorted(xml_games.items())], destination_games=games,
              summary=dict(reference_libretro_file_count=len(files),destination_set_count=len(games),
                           machine_available_sets=sum(g['destination_machine_available'] for g in games),
                           exact_name_matches=sum(g['reference_name_match'] for g in games)))
assert not any(f['group']=='Requires Classification' for f in files), 'Unclassified reference module'
args.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result['summary'], indent=2))
