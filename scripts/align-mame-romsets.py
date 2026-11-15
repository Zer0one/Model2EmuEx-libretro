#!/usr/bin/env python3
"""Generate the Libretro-only ROM catalogue from pinned official MAME metadata.

No ROM contents are read. Native wiring, region layout, options and hooks remain
in the standalone database; only reviewed ROM metadata differences are adapted.
Usage: align-mame-romsets.py --source /path/model2.cpp [--check]
"""
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'src/libretro/data'
REVISION = 'b106b9345dc32ab3c99514d6caeeabe0d0a78830'
SOURCE_SHA256 = '31fc8da039a0d13b5e83c43b8c0cf5fd5e112f672b3920200736c7be0077e562'
SOURCE_URL = f'https://github.com/mamedev/mame/blob/{REVISION}/src/mame/sega/model2.cpp'
EXCLUDED = {'srallyp': 'User excluded the non-MAME Sega Rally Pro Drivin set.',
            'daytonat': 'User excluded Daytona Turbo speed hack, set 1.',
            'daytonata': 'User excluded Daytona Turbo speed hack, set 2.'}
RENAMED = {'dayton93': 'daytona93'}
MODEL2B_REVISIONS = {'overrevba': 'overrevb', 'rchase2a': 'rchase2',
                     'doa': 'doab', 'von': 'vonu', 'vonr': 'vonj',
                     'fvipersa': 'fvipers', 'fvipersb': 'fvipers',
                     'dynabb': 'dynabb97'}
CATALOG_REVISIONS = {
    'doaab': 'doaa', 'doaae': 'doaa', 'hotd': 'hotdo', 'hotdp': 'hotdo',
    'manxttdx': 'manxtt', 'motoraiddx': 'motoraid', 'srallycc': 'srallycb',
    'srallycdx': 'srallycb', 'srallycdxa': 'srallycb', 'stcco': 'stcc',
    'topskatruo': 'topskatru',
}
# No original per-game record: use the existing native board implementation,
# ROM metadata and the already embedded frontend profile; never borrow a
# revision-specific native hook or protection workaround from another title.
CATALOG_NEW_TITLES = {'airwlkrs': 'Model 2A', 'hpyagu98': 'Model 2A', 'rascot2': 'Model 2C'}
VIDEO_TABLE_CRCS = {0xc078a780, 0x452a492b, 0xa25fef5b}
LOAD = re.compile(r'(ROMX?_LOAD\w*)\(\s*"([^"]+)"\s*,\s*(0x[\da-fA-F]+)\s*,\s*(0x[\da-fA-F]+)\s*,[^\n]*?CRC\(([\da-fA-F]+)\)')


def parse_mame(raw):
    # Expand the two local ROM-list macros, including their final non-backslash line.
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', raw, flags=re.S)
    macros = {}
    for line in source.replace('\\\n', ' ').splitlines():
        match = re.match(r'#define (MODEL2\w+)\s+(.*)', line)
        if match:
            macros[match[1]] = match[2]
    result = {}
    for name, body in re.findall(r'ROM_START\(\s*(\w+)\s*\)(.*?)ROM_END', source, re.S):
        for macro, expansion in macros.items():
            body = re.sub(r'\b' + macro + r'\b', lambda _: expansion, body)
        files = []
        for match in LOAD.finditer(body):
            before = body[:match.start()]
            regions = re.findall(r'ROM_REGION\w*\(\s*[^,]+,\s*([^,]+),', before)
            assert regions, name
            files.append(dict(name=match[2], offset=int(match[3], 16), size=int(match[4], 16),
                              crc=int(match[5], 16), region=regions[-1].strip().strip('"'), load=match[1]))
        result[name] = dict(files=files)
    for match in re.finditer(r'^GAMEL?\(\s*[^,]+,\s*(\w+)\s*,\s*(\w+)\s*,[^\n]*?"[^"]*"\s*,\s*"([^"]+)"', source, re.M):
        name, parent, title = match.groups()
        if name in result:
            result[name].update(parent=None if parent == '0' else parent, title=title)
    return result


def parse_native(source):
    arrays = {}
    for name, body in re.findall(r'static const m2_rom_entry roms_(\w+)\[\] = \{(.*?)\n\};', source, re.S):
        entries = []
        for line in body.splitlines():
            fields = [v.strip() for v in line.strip().strip('{}, ').split(',')]
            if len(fields) != 7:
                continue
            entries.append([int(fields[0]), None if fields[1] == 'NULL' else fields[1].strip('"'),
                            *[int(v, 0) for v in fields[2:]]])
        arrays[name] = entries
    games = []
    for match in re.finditer(r'^    \{ "(\w+)", "([^"]*)", (NULL|"[^"]*"), "model2", "([^"]*)", (.*) \},$', source, re.M):
        games.append(dict(name=match[1], title=match[2], board=match[4], tail=match[5]))
    assert len(games) == len(arrays)
    return arrays, games


def generate(raw):
    mame = parse_mame(raw)
    catalog = json.loads((DATA / 'mame_catalog_reference.json').read_text())
    display_titles = json.loads((DATA / 'core_display_titles.json').read_text())
    native_raw = (ROOT / 'port/m2/gamedb.inc').read_text()
    arrays, games = parse_native(native_raw)
    recovered_a_raw = (DATA / 'gamedb_model2a_recovered.inc').read_text()
    recovered_a_arrays, recovered_a_games = parse_native(recovered_a_raw)
    assert not arrays.keys() & recovered_a_arrays.keys()
    assert all(g['board'] == 'Model 2A' for g in recovered_a_games)
    arrays.update(recovered_a_arrays)
    games.extend(recovered_a_games)
    recovered_raw = (DATA / 'gamedb_model2b_recovered.inc').read_text()
    recovered_arrays, recovered_games = parse_native(recovered_raw)
    assert not arrays.keys() & recovered_arrays.keys()
    assert all(g['board'] == 'Model 2B' for g in recovered_games)
    arrays.update(recovered_arrays)
    games.extend(recovered_games)
    recovered_c_raw = (DATA / 'gamedb_model2c_recovered.inc').read_text()
    recovered_c_arrays, recovered_c_games = parse_native(recovered_c_raw)
    assert not arrays.keys() & recovered_c_arrays.keys()
    assert all(g['board'] == 'Model 2C' for g in recovered_c_games)
    arrays.update(recovered_c_arrays)
    games.extend(recovered_c_games)
    for name, base in MODEL2B_REVISIONS.items():
        donor = next(game for game in games if game['name'] == base)
        assert donor['board'] == 'Model 2B'
        tail = donor['tail']
        if name in ('doa', 'von', 'vonr'):
            # The donor's unidentified native hook is not executed by the port.
            # Its original address does not identify a hook in the new revision.
            tail, replaced = re.subn(r'M2_HOOK_UNKNOWN, 0x[0-9a-f]+,', 'M2_HOOK_NONE, 0x0,', tail)
            assert replaced == 1
        changed_regions = {'maincpu'}
        if name in ('fvipersa', 'fvipersb'):
            # The EPR data ROMs also changed in these revisions. The donor's
            # i960 wait-loop address belongs to Revision D only.
            changed_regions.add('main_data')
            tail, replaced = re.subn(r'M2_HOOK_STOP_AFTER, 0x[0-9a-f]+,', 'M2_HOOK_NONE, 0x0,', tail)
            assert replaced == 1
        native_regions = {0: 'maincpu', 1: 'main_data'}
        if name == 'dynabb':
            # Both Baseball releases use the same cabinet wiring. The earlier
            # board leaves IC11/IC12 empty and has only three sample ROMs.
            native_regions.update({3: 'polygons', 4: 'textures',
                                   5: 'audiocpu', 6: 'samples'})
            changed_regions.update(native_regions.values())
            tail = tail.replace('0x4c67a0', '0x0')
        assert 'M2_HOOK_NONE' in tail
        def layout(set_name, changed):
            files = [f for f in mame[set_name]['files']
                     if (f['region'] in changed_regions) == changed]
            slots = {(f['region'], f['offset'], f['size'], f['load']): f for f in files}
            assert len(slots) == len(files)
            return slots
        old_data, new_data = layout(base, False), layout(name, False)
        assert old_data.keys() == new_data.keys()
        assert all(f['crc'] == new_data[key]['crc'] for key, f in old_data.items())
        old_code, new_code = layout(base, True), layout(name, True)
        absent = set()
        if name == 'dynabb':
            absent = {('main_data', offset, 0x400000, 'ROM_LOAD32_WORD')
                      for offset in (0, 2)}
            absent.add(('samples', 0x600000, 0x200000, 'ROM_LOAD16_WORD_SWAP'))
        assert old_code.keys() - absent == new_code.keys()
        absent_roms = {(f['region'], f['offset'], f['size'], f['crc'])
                       for key, f in old_code.items() if key in absent}
        replacements = {(f['region'], f['offset'], f['size'], f['crc']): new_code[key]
                        for key, f in old_code.items() if key not in absent}
        entries, region = [], None
        for entry in arrays[base]:
            e = entry.copy()
            if e[0] == 0:
                region = native_regions.get(e[2] & 0xff)
            elif e[0] == 1 and region in changed_regions:
                slot = (region, e[3], e[4], e[5])
                if slot in absent_roms:
                    absent_roms.remove(slot)
                    continue
                replacement = replacements.pop(slot)
                e[1], e[5] = replacement['name'], replacement['crc']
            entries.append(e)
        assert not replacements and not absent_roms
        arrays[name] = entries
        games.append(dict(donor, name=name, tail=tail.replace(
            f'roms_{base},', f'roms_{name},')))
    sm2_games = ET.parse(ROOT / 'src/libretro/sm2/data/games.xml').getroot()
    def primary_layout(name, donor=None):
        """Translate reviewed ROM metadata into the original loader operations.

        No emulator algorithms or game ROM bytes are imported. Optional hardware
        programs absent from the native donor stay outside its consumed regions.
        Existing native table operations and cabinet options remain unchanged.
        """
        xml = sm2_games.find(f"./game[@name='{name}']")
        assert xml is not None
        regions = {'maincpu': 0, 'main_data': 1, 'copro_data': 2,
                   'polygons': 3, 'textures': 4, 'audiocpu': 5, 'samples': 6}
        result = []
        for tag,index in regions.items():
            region = xml.find(f"./roms/region[@name='{tag}']")
            assert region is not None, (name,tag)
            size = int(region.attrib['size'],0)
            result.append([0,None,index,size,0,0,0])
            fill=int(region.get('fill','0'),0)
            if fill:result.append([2,None,0,size,fill,0,0])
            stride=int(region.get('stride','1'),0); chunk=int(region.get('chunk','1'),0)
            flags=4 if region.get('byte_swap')=='true' else chunk|((stride-chunk)<<8)
            for item in region:
                if item.tag=='file':
                    candidates=[f for f in mame[name]['files'] if f['region']==tag
                                and f['offset']==int(item.get('offset','0'),0)
                                and f['crc']==int(item.attrib['crc'],0)]
                    assert len(candidates)==1,(name,tag,item.attrib)
                    f=candidates[0]
                    assert (chunk,stride)==({'ROM_LOAD32_WORD':(2,4),
                        'ROM_LOAD16_WORD_SWAP':(2,2),'ROM_LOAD':(1,1)}[f['load']])
                    result.append([1,f['name'],0,f['offset'],f['size'],f['crc'],flags])
                elif item.tag=='copy':
                    result.append([3,None,int(item.attrib['from'],0),
                        int(item.attrib['to'],0),int(item.attrib['size'],0),0,0])
                else:raise AssertionError((name,tag,item.tag))
        if donor:
            # Keep native non-primary ROM regions (tables, DSB and auxiliary
            # cabinet sound) and all options/transforms in their original order.
            region=-1
            for e in arrays[donor]:
                if e[0]==0:region=e[2]&255
                if e[0]==-1:continue
                if e[0] in (4,5) or region not in range(7):
                    result.append(e.copy())
        elif CATALOG_NEW_TITLES[name]=='Model 2A':
            # Shared native 2A table pack, independent of per-game wiring.
            region=-1
            for e in arrays['skytargt']:
                if e[0]==0:region=e[2]&255
                if region==10 and e[0]!=-1:result.append(e.copy())
        result.append([4,None,0,1 if xml.get('board')=='model2a' else 3,0,0,0])
        result.append([-1,None,0,0,0,0,0])
        return result
    for name,base in CATALOG_REVISIONS.items():
        donor=next(game for game in games if game['name']==base)
        assert name not in arrays
        # For unchanged slot layouts, preserve every native region/copy and
        # replace each consumed slot by its canonical target identity.
        def slotmap(n):return {(f['region'],f['offset'],f['size'],f['load']):f for f in mame[n]['files']}
        old_slots,new_slots=slotmap(base),slotmap(name)
        if old_slots.keys()==new_slots.keys():
            result=[]
            for e in arrays[base]:
                e=e.copy()
                if e[0]==1:
                    matches=[f for f in mame[base]['files'] if f['size']==e[4] and f['crc']==e[5]]
                    if not matches and base=='doaa' and e[1]=='mpr-19324.19' and e[5]==0xd972201f:
                        matches=[f for f in mame[base]['files'] if f['region']=='polygons' and f['offset']==e[3]]
                    assert matches,(name,e)
                    f=next((f for f in matches if f['name']==e[1]),matches[0])
                    target=new_slots[(f['region'],f['offset'],f['size'],f['load'])]
                    e[1],e[5]=target['name'],target['crc']
                result.append(e)
        else:result=primary_layout(name,base)
        arrays[name]=result
        # These installers are shared board/protection handlers, not borrowed
        # guest instruction addresses. Native fixed instruction patches require
        # a separate revision review before use on a new program.
        tail=donor['tail'].replace(f'roms_{base},',f'roms_{name},')
        if name in ('doaab','doaae'):
            tail=tail.replace('0x4c7e90,','0x4c7fa0,')
        games.append(dict(donor,name=name,tail=tail))
    for name,board in CATALOG_NEW_TITLES.items():
        arrays[name]=primary_layout(name)
        games.append(dict(name=name,board=board,tail=
            f'496, 384, 58.0f, M2_HOOK_NONE, 0x0, roms_{name}, NULL, '
            '{ 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00 }, 0x0'))
    # Power Sled has no ElSemi 1.1a record. Use MAME's ROM identities and
    # the SM2 frontend's existing cabinet profile and program patches.
    power_sled_regions = {
        'maincpu': (0, 0x200000, 'ROM_LOAD32_WORD', 0x0202),
        'main_data': (1, 0x2000000, 'ROM_LOAD32_WORD', 0x0202),
        'copro_data': (2, 0x800000, 'ROM_LOAD32_WORD', 0x0202),
        'polygons': (3, 0x1000000, 'ROM_LOAD32_WORD', 0x0202),
        'textures': (4, 0x800000, 'ROM_LOAD32_WORD', 0x0202),
        'audiocpu': (5, 0x80000, 'ROM_LOAD16_WORD_SWAP', 0x0004),
        'samples': (6, 0x800000, 'ROM_LOAD16_WORD_SWAP', 0x0004),
    }
    sm2_games = ET.parse(ROOT / 'src/libretro/sm2/data/games.xml').getroot()
    power_sled_sets = ('powsled', 'powsledr', 'powsledm')
    for name in power_sled_sets:
        files = mame[name]['files']
        assert {f['region'] for f in files} <= power_sled_regions.keys()
        patches = sm2_games.findall(f"./game[@name='{name}']/roms/region[@name='maincpu']/patch")
        assert patches
        entries = []
        for region, (index, size, load, flags) in power_sled_regions.items():
            entries.append([0, None, index, size, 0, 0, 0])
            for f in files:
                if f['region'] == region:
                    assert f['load'] == load, (name, f)
                    entries.append([1, f['name'], 0, f['offset'], f['size'], f['crc'], flags])
            if index == 0:
                for patch in patches:
                    offset = int(patch.attrib['offset'], 0)
                    assert offset % 4 == 0 and offset + 4 <= size
                    entries.append([6, None, int(patch.attrib['value'], 0), offset, 0, 0, 0])
        entries.extend(([4, None, 0, 2, 0, 0, 0], [4, None, 3, 0x180, 0, 0, 0],
                        [-1, None, 0, 0, 0, 0, 0]))
        arrays[name] = entries
        games.append(dict(name=name, board='Model 2B', tail=
                          f'496, 384, 58.0f, M2_HOOK_NONE, 0x0, roms_{name}, NULL, '
                          '{ 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00 }, 0x0'))
    lines = [
        '/* Generated by scripts/align-mame-romsets.py; do not edit.',
        f' * MAME revision: {REVISION}',
        ' * MAME ROM metadata: BSD-3-Clause; R. Belmont, Olivier Galibert, ElSemi,',
        ' * Angelo Salese, Matthew Daniels. Native wiring comes from gamedb.inc.',
        ' * Libretro-only overlay; standalone retains its original catalogue. */', '']
    report = dict(source=dict(url=SOURCE_URL, revision=REVISION, sha256=SOURCE_SHA256),
                  native_sha256=hashlib.sha256(native_raw.encode()).hexdigest(), excluded=EXCLUDED, games=[])
    report['catalog_reference'] = catalog['reference']
    report['layout_metadata'] = dict(source='src/libretro/sm2/data/games.xml', sha256=hashlib.sha256((ROOT/'src/libretro/sm2/data/games.xml').read_bytes()).hexdigest())
    report['display_title_policy'] = 'Preserve this core display strings; MAME controls identifiers and parents only.'
    report['recovered_model2a_sha256'] = hashlib.sha256(recovered_a_raw.encode()).hexdigest()
    report['recovered_model2b_sha256'] = hashlib.sha256(recovered_raw.encode()).hexdigest()
    report['recovered_model2c_sha256'] = hashlib.sha256(recovered_c_raw.encode()).hexdigest()
    lines.insert(6, '#include "gamedb_model2a_recovered.inc"')
    lines.insert(6, '#include "gamedb_model2b_recovered.inc"')
    lines.insert(7, '#include "gamedb_model2c_recovered.inc"')
    declarations = []
    for game in games:
        old = game['name']
        if old in EXCLUDED:
            continue
        name = RENAMED.get(old, old)
        assert name in mame and 'title' in mame[name], name
        target = mame[name]
        assert name in catalog['sets'] and name not in catalog['excluded'], name
        parent = catalog['sets'][name]['parent']
        title = display_titles[name]
        files = target['files']
        program = sorted((f['size'], f['crc']) for f in files if f['region'] == 'maincpu')
        current_region = -1
        original_program = []
        for e in arrays[old]:
            if e[0] == 0:
                current_region = e[2] & 0xff
            elif e[0] == 1 and current_region == 0:
                original_program.append((e[4], e[5]))
        # GTX's original catalogue has wildcard CRCs; pin the same named images.
        if old != 'daytonagtx':
            assert sorted(original_program) == program, (old, 'different main program')
        else:
            assert all(crc == 0 for _, crc in original_program)
        adapted = []
        changes = []
        used = set()
        current_region = -1
        for original in arrays[old]:
            e = original.copy()
            if e[0] == 0:
                current_region = e[2] & 0xff
            if e[0] == 1:
                candidates = [f for f in files if f['size'] == e[4] and f['crc'] == e[5]]
                if not candidates:
                    if game['board'] == 'Model 2' and current_region == 10 and e[5] in VIDEO_TABLE_CRCS:
                        changes.append(dict(action='remove_unused_video_table', old=e[1], crc=e[5]))
                        continue
                    if old == 'dayton93' and current_region == 5:
                        candidates = [f for f in files if f['region'] == 'M1AUDIO_CPU_REGION'
                                      and f['offset'] == e[3] and f['size'] == e[4]]
                    elif (old in ('doa', 'doab', 'doaa') and current_region == 3 and e[1] == 'mpr-19324.19'
                          and e[5] == 0xd972201f):
                        candidates = [f for f in files if f['region'] == 'polygons'
                                      and (f['name'] == e[1] or old == 'doaa') and f['offset'] == e[3]
                                      and f['size'] == e[4]]
                    elif old == 'daytonagtx' and not e[5]:
                        candidates = [f for f in files if f['name'] == e[1] and f['size'] == e[4]]
                assert candidates, (old, e)
                exact = [f for f in candidates if f['name'] == e[1]]
                chosen = (exact or candidates)[0]
                if (chosen['name'], chosen['crc']) != (e[1], e[5]):
                    changes.append(dict(action=('replace_polygon_identity' if old in ('doa', 'doab', 'doaa') else 'replace_audio_revision') if chosen['crc'] != e[5] and e[5]
                                        else 'pin_crc' if not e[5] else 'rename_file',
                                        old=e[1], new=chosen['name'], old_crc=e[5], new_crc=chosen['crc']))
                e[1], e[5] = chosen['name'], chosen['crc']
                used.add((chosen['name'], chosen['size'], chosen['crc']))
            adapted.append(e)
        lines.append(f'static const m2_rom_entry mame_roms_{name}[] = {{')
        for typ, file, arg, offset, size, crc, flags in adapted:
            quoted = json.dumps(file) if file else 'NULL'
            lines.append(f'    {{ {typ}, {quoted}, 0x{arg:08x}, 0x{offset:08x}, 0x{size:08x}, 0x{crc:08x}, 0x{flags:08x} }},')
        lines.extend(['};', ''])
        tail = game['tail'].replace(f'roms_{old},', f'mame_roms_{name},')
        declarations.append(f'    {{ "{name}", {json.dumps(title)}, {json.dumps(parent) if parent else "NULL"}, "model2", "{game["board"]}", {tail} }},')
        report['games'].append(dict(native_name=old, name=name, title=title, parent=parent,
                                    board=game['board'], recovered_model2b=old in recovered_arrays, mame_revision_of=MODEL2B_REVISIONS.get(old), program_identity='named_files_crc_pinned' if old == 'daytonagtx' else 'size_crc_equal',
                                    **({'recovered_model2c': True} if old in recovered_c_arrays else {}),
                                    **({'recovered_model2a': True} if old in recovered_a_arrays else {}),
                                    **({'catalog_revision_of': CATALOG_REVISIONS[old]} if old in CATALOG_REVISIONS else {}),
                                    **({'native_board_extension': True} if old in CATALOG_NEW_TITLES else {}),
                                    **({'mame_cabinet': True} if old in power_sled_sets else {}),
                                    changes=changes, mame_files=files,
                                    not_consumed=[f for f in files if (f['name'], f['size'], f['crc']) not in used]))
    report['missing_catalog_sets'] = sorted(set(catalog['sets']) - set(catalog['excluded']) - {g['name'] for g in report['games']})
    lines.extend(['static const m2_game mame_games[] = {', *declarations, '};', ''])
    return {'gamedb_mame.inc': '\n'.join(lines), 'mame_model2_catalog.json': json.dumps(report, indent=2)+'\n'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise SystemExit('MAME source hash differs from the pinned reference; review before updating.')
    for filename, content in generate(raw.decode()).items():
        path = DATA / filename
        if args.check:
            assert path.read_text() == content, f'Stale generated file: {path}'
        else:
            path.write_text(content)
    print('PASS: existing entries use canonical IDs/parents and preserved core titles; exclusions enforced; standalone preserved')
    manifest = json.loads((DATA / 'mame_model2_catalog.json').read_text())
    print(f"Catalog entries still missing: {len(manifest['missing_catalog_sets'])}; runtime qualification is recorded separately")

if __name__ == '__main__':
    main()
