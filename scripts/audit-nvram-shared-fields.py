#!/usr/bin/env python3
"""Inventory shared NVRAM patches and name-related campaign settings.

Read-only triage: bit overlap or similar labels are candidates, never proof of
an emulator bug. Uses the existing diagnostic YAML and both current catalogs.
No samples, ROMs, reference files or emulator behavior are modified.
"""
import argparse, collections, hashlib, itertools, json, re, subprocess
from pathlib import Path


def catalog(path):
    text = path.read_text()
    patches = {}
    for name, body in re.findall(r'static constexpr Patch (\w+)\[\] = \{(.*?)\};', text, re.S):
        rows = []
        for row in re.findall(r'\{([^{}]+)\}', body):
            values = [v.strip() for v in row.split(',')]
            assert len(values) in (2, 3), (path, name, row)
            rows.append(dict(offset=int(values[0], 0), mask=int(values[1], 0),
                             memory='eeprom' if len(values) == 3 and 'Eeprom' in values[2] else 'backup'))
        patches[name] = rows
    block = text.split('static constexpr Option kOptions[] = {', 1)[1].split('\n};', 1)[0]
    rows = []
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("//"): continue
        strings = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        patch = re.search(r', (k\w*Patches\d*), std::size', line)
        assert len(strings) == 5 and patch, line
        game, key, label = strings[:3]
        fields = [dict(p) for p in patches[patch[1]]]
        if game == 'doa':
            for p in fields: p['memory'] = 'eeprom'
        rows.append(dict(game=game, key=key, label=label, patches=fields))
    return rows


def overlaps(rows):
    groups = collections.defaultdict(list)
    for row in rows: groups[row['game']].append(row)
    result = []
    for game, options in sorted(groups.items()):
        for a, b in itertools.combinations(options, 2):
            for x, y in itertools.product(a['patches'], b['patches']):
                if (x['memory'], x['offset']) != (y['memory'], y['offset']): continue
                mask = x['mask'] & y['mask']
                if mask:
                    result.append(dict(game=game, keys=[a['key'], b['key']], labels=[a['label'], b['label']],
                                       memory=x['memory'], offset=hex(x['offset']), shared_mask=hex(mask),
                                       status='candidate: shared bits; native semantics require classification'))
    return result


def related(a, b):
    aa = re.findall(r'[A-Z0-9]+', a.upper()); bb = re.findall(r'[A-Z0-9]+', b.upper())
    prefix = []
    for x, y in zip(aa, bb):
        if x != y: break
        prefix.append(x)
    if not prefix or len(prefix) == min(len(aa), len(bb)): return None
    if len(prefix) == 1 and prefix[0] in {'NO', 'NUMBER', 'MAX', 'MIN', 'INITIAL', 'SET', 'THE'}: return None
    return ' '.join(prefix)


def nvram_offsets(value, path='', default_storage='backup'):
    """Preserve bank and bit identity; equal offsets alone are not sharing."""
    result = []
    if not isinstance(value, dict): return result
    storage = value.get('storage', default_storage)
    storage = 'eeprom' if 'eeprom' in str(storage).lower() else 'backup'
    def add(key, offset, mask):
        if not isinstance(offset, int) or not isinstance(mask, int): return
        bank = 'eeprom' if 'eeprom' in key else 'backup' if 'backup_ram' in key else storage
        result.append(dict(property=path+key, memory=bank, offset=hex(offset), mask=mask))
    primary_mask = value.get('mask', (1 << value['bit']) if isinstance(value.get('bit'), int) else 0xff)
    for key, child in value.items():
        if key == 'offset' or key.endswith('_offset'):
            mask = 0xff if key.startswith('derived_') else primary_mask
            add(key, child, mask)
        elif key == 'offsets' or key.endswith('_offsets') or key == 'compound_fields':
            if isinstance(child, list):
                masks = value.get(key.replace('offsets', 'masks'), [])
                for i, offset in enumerate(child):
                    add(key, offset, masks[i] if isinstance(masks, list) and i < len(masks) else 0xff)
        elif key.endswith('_ranges') and isinstance(child, list):
            for interval in child:
                if isinstance(interval, str) and re.fullmatch(r'0x[0-9a-fA-F]+-0x[0-9a-fA-F]+', interval):
                    first, last = (int(x, 0) for x in interval.split('-'))
                    for offset in range(first, last+1): add(key, offset, 0xff)
        elif isinstance(child, dict):
            result.extend(nvram_offsets(child, path+key+'.', storage))
    return result


def campaign(reference):
    files = sorted((reference/'data/diagnostic-menus').glob('*.yaml'))
    ruby = 'require "json";require "yaml";require "date";puts JSON.generate(ARGV.map{|p|[p,YAML.safe_load(File.read(p),permitted_classes:[Date],aliases:true)]})'
    documents = json.loads(subprocess.check_output(['ruby', '-e', ruby, *map(str, files)], text=True))
    rows = []; provenance = []
    def visit(node, game, menu=''):
        if isinstance(node, dict):
            options = node.get('options')
            if isinstance(options, list):
                for option in options:
                    if not isinstance(option, dict) or 'key' not in option or 'label' not in option: continue
                    rows.append(dict(game=game, menu=menu, key=option['key'], label=option['label'],
                                     nvram=option.get('nvram', {}), coding_reference=option.get('coding_reference'), offsets=[]))
            for key, value in node.items():
                if key != 'options': visit(value, game, menu+'/'+key)
        elif isinstance(node, list):
            for value in node: visit(value, game, menu)
    for path, document in documents:
        provenance.append(dict(path=path, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()))
        game = document.get('game', {}).get('set', Path(path).stem)
        visit(document.get('menus', {}), game)
    docs = {d.get('game', {}).get('set', Path(p).stem): d for p, d in documents}
    index = {(r['game'], r['key']): r for r in rows}
    def resolved(row, seen):
        if row['nvram']: return row['nvram']
        reference = row['coding_reference'] or docs[row['game']].get('nvram_layout', {}).get('coding_reference')
        if not reference: return {}
        target = (Path(reference).stem, row['key'])
        if target in seen or target not in index: return {}
        return resolved(index[target], seen | {target})
    for row in rows:
        storage = docs[row['game']].get('nvram_layout', {}).get('storage', 'backup')
        row['offsets'] = nvram_offsets(resolved(row, {(row['game'], row['key'])}), default_storage=storage)
    return rows, provenance


def campaign_candidates(rows):
    groups = collections.defaultdict(list)
    for row in rows: groups[row['game']].append(row)
    result = []
    for game, options in sorted(groups.items()):
        for a, b in itertools.combinations(options, 2):
            prefix = related(a['label'], b['label'])
            shared = []
            for x, y in itertools.product(a['offsets'], b['offsets']):
                if (x['memory'], x['offset']) == (y['memory'], y['offset']) and x['mask'] & y['mask']:
                    item = dict(memory=x['memory'], offset=x['offset'], mask=hex(x['mask'] & y['mask']))
                    if item not in shared: shared.append(item)
            common = sorted({x['memory']+':'+x['offset'] for x in shared})
            if not prefix and not common: continue
            result.append(dict(game=game, keys=[a['key'], b['key']], labels=[a['label'], b['label']],
                               common_prefix=prefix, declared_common_offsets=common, shared_fields=shared,
                               status='name-filter group: apply approved Energy rule where sharing exists' if prefix else 'review shared-bit semantics'))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, default=Path('../sm2-emu-libretro'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists(), 'Use a new output directory'
    root = Path(__file__).resolve().parent.parent
    sources = {'SM2': a.reference/'src/libretro/nvram_settings_data.inc',
               'Model2EmuEx': root/'src/libretro/sm2/nvram_settings_data.inc'}
    result = {'scope': 'Static complete-catalog and declared campaign-metadata triage; not raw-sample or native-code acceptance', 'catalogs': {}}
    for name, source in sources.items():
        rows = catalog(source)
        result['catalogs'][name] = dict(options=len(rows), games=len({r['game'] for r in rows}),
                                        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                        shared_bits=overlaps(rows))
    rows, files = campaign(a.reference)
    result['campaign'] = dict(yaml_files=len(files), option_rows=len(rows), games=len({r['game'] for r in rows}),
                              provenance=files, candidates=campaign_candidates(rows))
    a.output.mkdir(parents=True)
    (a.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    lines = ['# NVRAM Shared-Field Triage', '', result['scope'], '', '| Game | Options | Reason |', '| --- | --- | --- |']
    for c in result['campaign']['candidates']:
        reasons=[]
        if c['common_prefix']: reasons.append('Name prefix: '+c['common_prefix'])
        if c['declared_common_offsets']: reasons.append('Declared addresses: '+', '.join(c['declared_common_offsets']))
        lines.append('| '+c['game']+' | '+' / '.join(c['labels'])+' | '+'; '.join(reasons)+' |')
    (a.output/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:dict(options=v['options'],games=v['games'],shared_bit_pairs=len(v['shared_bits'])) for k,v in result['catalogs'].items()}))
    print('Campaign:',result['campaign']['yaml_files'],'YAML files;',result['campaign']['option_rows'],'options;',len(result['campaign']['candidates']),'candidate pairs')
    for name, c in result['catalogs'].items():
        for x in c['shared_bits']: print(name,x['game'], '/'.join(x['keys']),x['memory'],x['offset'],x['shared_mask'])

if __name__ == '__main__': main()
