#!/usr/bin/env python3
"""Build a disposable ElSemi PE with x87 mode counters at transform entry."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from difftest_bits import EXE_SHA256

TRANSFORMS = (
    ("point", 0x4B9CB0, bytes.fromhex("83ec10803d5ad90e0100")),
    ("vector", 0x4B9DF0, bytes.fromhex("83ec108b01")),
)


def align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def jump(source, target):
    return b"\xe9" + struct.pack("<i", target - source - 5)


def instrument(source, output, manifest):
    image = bytearray(source.read_bytes())
    if hashlib.sha256(image).hexdigest() != EXE_SHA256:
        raise ValueError("Expected the pinned ElSemi 1.1a executable")
    if output.exists() or manifest.exists() or output.resolve() == source.resolve():
        raise ValueError("Use new output paths for the instrumented copy and manifest")

    pe, = struct.unpack_from("<I", image, 0x3C)
    sections, = struct.unpack_from("<H", image, pe + 6)
    optional_size, = struct.unpack_from("<H", image, pe + 20)
    optional = pe + 24
    base, section_align, file_align = struct.unpack_from("<III", image, optional + 28)
    table = optional + optional_size
    header = table + sections * 40
    first_raw = min(struct.unpack_from("<I", image, table + i * 40 + 20)[0]
                    for i in range(sections))
    if header + 40 > first_raw or any(image[header:header + 40]):
        raise ValueError("No room for the trace section header")

    rva, = struct.unpack_from("<I", image, optional + 56)
    raw = align(len(image), file_align)
    size = align(512, file_align)
    image.extend(bytes(raw + size - len(image)))
    struct.pack_into("<H", image, pe + 6, sections + 1)
    struct.pack_into("<I", image, optional + 56, align(rva + size, section_align))
    struct.pack_into("<8sIIIIIIHHI", image, header, b".x87diag", size, rva, size, raw,
                     0, 0, 0, 0, 0xE0000060)

    text_rva, _, text_raw = struct.unpack_from("<III", image, table + 12)
    slots = {}
    for i, (kind, entry, prologue) in enumerate(TRANSFORMS):
        offset = text_raw + entry - base - text_rva
        if image[offset:offset + len(prologue)] != prologue:
            raise ValueError(f"Unexpected {kind} prologue")

        slot = 128 * i
        code_offset = 256 + 64 * i
        code_address = base + rva + code_offset
        last = base + rva + slot
        histogram = last + 4
        # Preserve flags/EAX. FNSTCW reads the mode without changing it.
        # Histogram index uses the precision and rounding fields (bits 8-11).
        code = (bytes.fromhex("9c506a00d93c2458a3") + struct.pack("<I", last)
                + bytes.fromhex("c1e80883e00ff0ff0485") + struct.pack("<I", histogram)
                + bytes.fromhex("589d") + prologue)
        code += jump(code_address + len(code), entry + len(prologue))
        image[raw + code_offset:raw + code_offset + len(code)] = code
        image[offset:offset + len(prologue)] = (
            jump(entry, code_address) + b"\x90" * (len(prologue) - 5))
        slots[kind] = {"entry": entry, "control_word_rva": rva + slot}

    output.write_bytes(image)
    manifest.write_text(json.dumps({
        "original_sha256": EXE_SHA256,
        "instrumented_sha256": hashlib.sha256(image).hexdigest(),
        "slots": slots,
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "output", "manifest"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    instrument(args.source, args.output, args.manifest)
