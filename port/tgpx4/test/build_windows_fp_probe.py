#!/usr/bin/env python3
"""Build the ROM-free Windows x86 trampoline and audited global relocations.

Uses installed LLVM/Clang only. Does not execute the PE or contact a remote host.
The three relocated globals avoid CLR allocations; FP opcodes remain unchanged.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

PIN = '2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc'
MAPPING = {0x10481F4: 0x310081F4, 0x104824C: 0x3100824C, 0x10F1FEC: 0x31011FEC}
RANGES = ((0x4B3FB0, 0x4B4030), (0x4B4E60, 0x4B4F30), (0x4B53B0, 0x4B5590),
          (0x4B5630, 0x4B58C0), (0x4B64A0, 0x4B66A0), (0x5008F0, 0x50099B))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('output_prefix', type=Path)
    args = parser.parse_args()
    assert hashlib.sha256(args.exe.read_bytes()).hexdigest() == PIN, 'Unrecognized original executable'
    root = Path(__file__).resolve().parent
    obj = args.output_prefix.with_suffix('.obj')
    subprocess.run(['clang', '-target', 'i386-pc-windows-msvc', '-c',
                    str(root / 'windows_original_fp.S'), '-o', str(obj)], check=True)
    raw = obj.read_bytes()
    machine, sections = struct.unpack_from('<HH', raw)
    assert machine == 0x14C
    table = 20 + struct.unpack_from('<H', raw, 16)[0]
    text = None
    for i in range(sections):
        off = table + 40 * i
        if raw[off:off + 8].rstrip(b'\0') == b'.text':
            size, start = struct.unpack_from('<II', raw, off + 16)
            assert struct.unpack_from('<H', raw, off + 32)[0] == 0, 'Trampoline requires relocation'
            text = raw[start:start + size]
    assert text and len(text) <= 0x200
    relocations = []
    for start, end in RANGES:
        disasm = subprocess.check_output(['xcrun', 'llvm-objdump', '-d', f'--start-address={start}',
                                          f'--stop-address={end}', str(args.exe)], text=True)
        for line in disasm.splitlines():
            match = re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)', line)
            if not match:
                continue
            address = int(match[1], 16)
            code = bytes.fromhex(match[2])
            for old, new in MAPPING.items():
                pos = code.find(struct.pack('<I', old))
                if pos < 0:
                    continue
                assert code[:pos] in (b'\xa1', b'\x8b\x0d', b'\x8b\x15', b'\x83\x3d'), line
                relocations.append((address + pos, old, new))
    assert len(relocations) == 37 and len({r[0] for r in relocations}) == 37, relocations
    manifest = b''.join(struct.pack('<III', *r) for r in relocations)
    args.output_prefix.with_suffix('.bin').write_bytes(text)
    args.output_prefix.with_suffix('.reloc').write_bytes(manifest)
    report = dict(original_sha256=PIN, trampoline_sha256=hashlib.sha256(text).hexdigest(),
                  relocations_sha256=hashlib.sha256(manifest).hexdigest(),
                  relocation_count=len(relocations), relocated_globals={f'{k:08x}': f'{v:08x}' for k, v in MAPPING.items()},
                  scope='Only absolute global operands; original FP code and constants unchanged')
    args.output_prefix.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
