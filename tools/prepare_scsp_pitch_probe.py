#!/usr/bin/env python3
"""Instrument the end of the pinned Windows SCSP pitch initializer and bind XAudio2 locally."""
import argparse
import hashlib
import struct
from pathlib import Path

from original_inventory import OriginalPE


def prepare(source, destination, manifest_only=False, hotdo=False):
    pe = OriginalPE(source)
    data = bytearray(pe.data)
    header = struct.unpack_from('<I', data, 0x3c)[0]
    optional = header + 24
    section_table = optional + struct.unpack_from('<H', data, header + 20)[0]
    last = pe.sections[-1]
    section = section_table + 40 * (len(pe.sections)-1)
    assert last['name'] == '.rsrc' and last['offset'] + last['raw_size'] == len(data)
    start = data.index(b'<assembly ', last['offset'])
    end = data.index(b'</assembly>', start) + len(b'</assembly>')
    rva = last['address'] - 0x400000 + start - last['offset']
    descriptor = data.index(struct.pack('<II', rva, end-start), last['offset'], start)
    manifest = bytes(data[start:end]).replace(b'<trustInfo', (
        b'<assemblyIdentity type="win32" name="Model2EmuEx.PitchProbe" version="1.0.0.0" '
        b'processorArchitecture="x86"/><trustInfo')).replace(b'</assembly>', (
        b'<file name="XAudio2_6.dll"><comClass clsid="{3EDA9B49-2085-498B-9BB2-39A6778493DE}" '
        b'threadingModel="Both"/></file></assembly>'))
    new_size = start - last['offset'] + len(manifest)
    alignment = struct.unpack_from('<I', data, optional+36)[0]
    raw_size = (new_size + alignment - 1) // alignment * alignment
    assert rva + len(manifest) <= struct.unpack_from('<I', data, optional+56)[0]
    data[start:] = manifest + bytes(raw_size-new_size)
    struct.pack_into('<I', data, descriptor+4, len(manifest))
    struct.pack_into('<I', data, section+8, new_size)
    struct.pack_into('<I', data, section+16, raw_size)
    struct.pack_into('<I', data, optional+96+2*8+4, new_size)
    for s in pe.sections:
        if s['executable']:
            a, b = s['offset'], s['offset'] + s['raw_size']
            assert data[a:b] == pe.data[a:b]
    # The final FLDCW at 004af3b4 has restored the caller's control word.
    # Immediately after the loop, publish it in the following unused gain
    # table and park this disposable process until the observer has read it.
    if hotdo:
        # The original key names the pre-Rev-A dump now archived as hotdo.zip.
        # The extra character fits in padding before the display title.
        marker = b'hotd\0\0\0\0House of the Dead\0'
        assert data.count(marker) == 1
        pos = data.index(marker)
        assert any(s['name'] == '.rdata' and s['offset'] <= pos < s['offset'] + s['raw_size']
                   for s in pe.sections)
        data[pos+4] = ord('o')
    if manifest_only:
        with destination.open('xb') as stream:
            stream.write(data)
        return
    at = 0x4af3c4
    code = next(section for section in pe.sections if section['executable'] and
                section['address'] <= at < section['address'] + section['raw_size'])
    pos = code['offset'] + at - code['address']
    assert data[pos:pos+8] == bytes.fromhex('dd db 33 db dd d9 dd d8')
    data[pos:pos+8] = bytes.fromhex('d9 3d 68 11 0c 01 eb fe')
    with destination.open('xb') as stream:
        stream.write(data)
    print(hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('diagnostic', type=Path)
    parser.add_argument('--manifest-only', action='store_true', help='Preserve all original x86 code for live memory observation')
    parser.add_argument('--hotdo', action='store_true', help='Use the MAME archive key in the read-only game record for the Windows observer')
    args = parser.parse_args()
    if args.hotdo and not args.manifest_only:
        parser.error('--hotdo requires --manifest-only')
    prepare(args.original, args.diagnostic, args.manifest_only, args.hotdo)
