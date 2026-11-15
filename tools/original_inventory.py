#!/usr/bin/env python3
"""Index original-code evidence, without equating address mentions to recovery.

Uses the inherited Ghidra exports and the pinned original PE. Reports belong
outside Git; ROADMAP.md is the sole implementation roadmap. No ROM input.
"""
import argparse
import collections
import csv
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

from model2c_inventory import EXPECTED


class OriginalPE:
    def __init__(self, path):
        self.data = path.read_bytes()
        if hashlib.sha256(self.data).hexdigest() != EXPECTED:
            raise ValueError('Expected the recorded original ElSemi 1.1a executable')
        pe = struct.unpack_from('<I', self.data, 0x3c)[0]
        if self.data[pe:pe+4] != b'PE\0\0':
            raise ValueError('Invalid PE signature')
        optional = pe + 24
        base = struct.unpack_from('<I', self.data, optional + 28)[0]
        count = struct.unpack_from('<H', self.data, pe + 6)[0]
        size = struct.unpack_from('<H', self.data, pe + 20)[0]
        self.sections = []
        for i in range(count):
            at = optional + size + 40*i
            name, virtual, rva, raw, offset = struct.unpack_from('<8sIIII', self.data, at)
            flags = struct.unpack_from('<I', self.data, at + 36)[0]
            self.sections.append(dict(name=name.rstrip(b'\0').decode(), address=base+rva,
                                      virtual_size=virtual, raw_size=raw, offset=offset,
                                      executable=bool(flags & 0x20000000)))

    def read(self, address, size):
        for section in self.sections:
            offset = address - section['address']
            if 0 <= offset and offset + size <= section['raw_size']:
                start = section['offset'] + offset
                return self.data[start:start+size]
        raise ValueError(f'Not file-backed: {address:08x}+{size:x}')

    def is_code(self, address):
        return any(s['executable'] and s['address'] <= address < s['address']+s['virtual_size']
                   for s in self.sections)


def inventory(root, exe):
    pe = OriginalPE(exe)
    rows = list(csv.DictReader((root/'src/functions.tsv').open(), delimiter='\t'))
    entries = {}
    for row in rows:
        address = int(row['address'], 16)
        if address in entries:
            raise ValueError(f'Duplicate original entry {address:08x}')
        entries[address] = dict(address=f'{address:08x}', name=row['name'],
            export_size=int(row['size']), thunk=row['thunk'] == 'true',
            executable_section=pe.is_code(address), exports=[], portable_address_references=[])
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    headers = re.compile(r'^// ===== (.+?) @ ([0-9a-f]{8})(?: \(\d+ bytes\))? =====$', re.M)
    exported = collections.defaultdict(list)
    calls = collections.defaultdict(set)
    provenance = {}
    for name in tracked:
        path = root/name
        if not name or not path.is_file():
            continue
        is_export = name == 'src/all_functions.c' or (name.endswith('_decomp.c') and not name.startswith('port/'))
        is_port = (name.startswith(('port/i960/', 'port/tgp/', 'port/sharc/', 'port/tgpx4/', 'port/m2/', 'port/snd/'))
                   and '/test/' not in name and path.suffix in ('.c', '.h', '.cpp'))
        if not (is_export or is_port):
            continue
        data = path.read_bytes()
        text = data.decode()
        provenance[name] = hashlib.sha256(data).hexdigest()
        if is_export:
            matches = list(headers.finditer(text))
            if len(matches) != sum(line.startswith('// =====') for line in text.splitlines()):
                raise ValueError(f'Unrecognized export header in {name}')
            for i, match in enumerate(matches):
                address = int(match[2], 16)
                exported[address].append(name)
                end = matches[i+1].start() if i+1 < len(matches) else len(text)
                body = text[match.end():end]
                calls[address].update(int(a, 16) for a in re.findall(r'\bFUN_([0-9a-f]{8})\s*\(', body)
                                      if int(a, 16) != address)
        else:
            for line, value in enumerate(text.splitlines(), 1):
                # A comment/case/constant is only a lookup lead, never proof.
                found = set(int(a, 16) for a in re.findall(
                    r'(?i)\b(?:0x)?(00[4-5][0-9a-f]{5}|[4-5][0-9a-f]{5})\b', value))
                for address in found & entries.keys():
                    entries[address]['portable_address_references'].append(f'{name}:{line}')
    for address, row in entries.items():
        row['exports'] = sorted(set(exported[address]))
        row['direct_call_candidates'] = [f'{a:08x}' for a in sorted(calls[address])]
        row['evidence_class'] = ('portable_address_reference_only' if row['portable_address_references']
                                 else 'export_only_unclassified')
    pointer_runs = []
    # Reuses ptrtables.py's aligned-run criterion, but reads actual PE sections.
    # Values pointing into .text can still be data or internal labels.
    for section in pe.sections:
        if section['name'] not in ('.rdata', '.data'):
            continue
        run = []
        def flush():
            if len(run) >= 16:
                pointer_runs.append(dict(address=f'{run[0][0]:08x}', entries=len(run),
                    targets=[f'{v:08x}' for _, v in run],
                    absent_from_function_export=sorted({f'{v:08x}' for _, v in run if v not in entries})))
        for offset in range(0, section['raw_size'] - 3, 4):
            at = section['address'] + offset
            value = struct.unpack('<I', pe.read(at, 4))[0]
            if pe.is_code(value):
                run.append((at, value))
            else:
                flush(); run = []
        flush()
    return dict(schema_version=1, original_sha256=EXPECTED,
        function_export_sha256=hashlib.sha256((root/'src/functions.tsv').read_bytes()).hexdigest(),
        input_hashes=provenance, sections=pe.sections,
        summary=dict(function_export_entries=len(entries),
            non_thunk_entries=sum(not r['thunk'] for r in entries.values()),
            thunks=sum(r['thunk'] for r in entries.values()),
            entries_with_portable_address_references=sum(bool(r['portable_address_references']) for r in entries.values()),
            export_only_unclassified=sum(not r['portable_address_references'] for r in entries.values()),
            extra_decompile_entry_addresses=len(set(exported)-entries.keys()),
            pointer_runs=len(pointer_runs),
            pointer_targets_absent_from_function_export=len({t for r in pointer_runs for t in r['absent_from_function_export']})),
        functions=list(entries.values()),
        additional_decompile_entries=[dict(address=f'{a:08x}', exports=sorted(set(exported[a])))
                                      for a in sorted(set(exported)-entries.keys())],
        code_pointer_runs=pointer_runs,
        limits=['No whole-emulator completion percentage: this is an evidence index.',
                'Address references and exported bodies do not prove implementation or equivalence.',
                'Absent export entries may be internal labels, generated code or data, not missing functions.',
                'Direct-call candidates include FUN-address calls only; named, imported and indirect calls are not a closed graph.',
                'Host/API/library and replacement classifications require semantic review.',
                'No runtime, ROM or gameplay evidence is produced.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inventory(args.root, args.exe)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
