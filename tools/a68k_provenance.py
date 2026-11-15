#!/usr/bin/env python3
"""Compare historical A68K generator dispatch grouping with the pinned EXE.

The caller supplies the public reference source; no emulator or ROM is downloaded.
Generated assembly and compiler products are temporary. This proves grouping,
not instruction semantics or identity of the original generator revision.
"""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from a68k_inventory import decode_dispatch
from original_inventory import OriginalPE

REFERENCE_COMMIT = '388cc91c3d1fc8e041dc081ad67ddf84dab03e64'
REFERENCE_PATH = 'src/cpu/a68k/fba_make68k.c'
REFERENCE_SHA256 = 'dc8aa0f26d975f9b62eebfb9a27d1176c83a360bd68af8e233fc55fd8d6fcf07'
ORIGINAL_SHA256 = '2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc'


def labels_from_table(text):
    lines = text.splitlines()
    assert lines[0] == 'DD OP0_1000'
    labels, i = [], 1
    while i < len(lines):
        match = re.fullmatch(r'DD \((\w+) - OP0_1000\) \+ \((\d+) \* 1000000h\)', lines[i])
        if match:
            label, count = match[1], int(match[2])
        else:
            match = re.fullmatch(r'DD (\w+) - OP0_1000', lines[i])
            assert match, lines[i]
            label = match[1]
            i += 1
            assert lines[i].startswith('DW '), lines[i]
            count = int(lines[i][3:])
        assert count > 0 and len(labels) + count <= 65536
        labels.extend([label] * count)
        i += 1
    assert len(labels) == 65536
    return labels


def compare(exe, source):
    pe = OriginalPE(exe)
    assert hashlib.sha256(pe.data).hexdigest() == ORIGINAL_SHA256
    assert hashlib.sha256(source.read_bytes()).hexdigest() == REFERENCE_SHA256
    with tempfile.TemporaryDirectory(prefix='a68k-provenance-') as temporary:
        directory = Path(temporary)
        compiler = subprocess.run(['clang', '-O2', str(source.resolve()), '-o', str(directory/'generator')],
                                  capture_output=True, text=True, check=True)
        generator = subprocess.run([str(directory/'generator'), str(directory/'code.asm'),
                                    str(directory/'table.asm'), '00'],
                                   capture_output=True, text=True, check=True)
        table = (directory/'table.asm').read_text()
    labels = labels_from_table(table)
    native = decode_dispatch(pe)[3]
    forward, reverse = collections.defaultdict(set), collections.defaultdict(set)
    for label, target in zip(labels, native):
        forward[label].add(target)
        reverse[target].add(label)
    assert all(len(targets) == 1 for targets in forward.values())
    assert all(len(names) == 1 for names in reverse.values())
    assert len(forward) == len(reverse) == 1667
    mapping = {label: f'{next(iter(targets)):08x}' for label, targets in sorted(forward.items())}
    return dict(original_sha256=ORIGINAL_SHA256,
                reference_url=f'https://github.com/finalburnneo/FBNeo/blob/{REFERENCE_COMMIT}/{REFERENCE_PATH}',
                reference_sha256=REFERENCE_SHA256, reference_version='Make68K 0.30',
                reference_authors=['Mike Coates', 'Darren Olafson'],
                generator_stdout=generator.stdout.strip(), compiler_diagnostics=compiler.stderr.strip(),
                compared_entries=65536, reference_labels=len(forward), original_targets=len(reverse),
                split_reference_labels=0, split_original_targets=0,
                table_sha256=hashlib.sha256(table.encode()).hexdigest(),
                mapping_sha256=hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest(),
                label_to_original=mapping,
                limits=['Exact dispatch partition correspondence; not instruction-byte or semantic equivalence.',
                        'FBNeo reference settings/history do not identify the precise ElSemi source revision.',
                        'No generated code imported or linked; original executable remains behavior authority.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.exe, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('label_to_original', 'compiler_diagnostics')}, indent=2))
