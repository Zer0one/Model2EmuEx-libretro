#!/usr/bin/env python3
"""Index SHARC recovery evidence in the existing Ghidra export, without ROMs.

Address-taken LAB symbols are recovery candidates, not proven function starts.
Feed reviewed candidates to the existing RegionExport.java; do not assume the
README's coarse contiguous subsystem ranges contain every handler.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def inventory(root):
    source = root / "src/all_functions.c"
    data = source.read_bytes()
    text = data.decode("utf-8")
    headers = list(re.finditer(
        r"^// ===== (\w+) @ ([0-9a-f]{8}) =====$", text, re.M))
    bodies = {}
    for index, match in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        bodies[int(match[2], 16)] = (match[1], text[match.end():end])
    # Source-identified helpers, decode/execute/reset and board initialization.
    roots = [address for address in bodies
             if 0x4bc170 <= address <= 0x4c0230
             or address in (0x460f20, 0x462140, 0x4622a0, 0x4c6510)]
    candidates = {}
    functions = []
    for address in roots:
        name, body = bodies[address]
        refs = sorted(set(re.findall(r"&LAB_([0-9a-f]{8})", body)))
        for ref in refs:
            candidates.setdefault(ref, []).append(name)
        functions.append({"address": f"{address:08x}", "name": name,
                          "address_taken_labels": refs})
    labels = []
    for address, owners in sorted(candidates.items()):
        labels.append({
            "address": address, "referenced_by": owners,
            "exported_function_entry": int(address, 16) in bodies,
            "exported_label_body": bool(re.search(
                rf"^LAB_{address}:", text, re.M)),
        })
    return {
        "schema_version": 1,
        "scope": "Source inventory only; no binary or execution validation",
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "functions": functions,
        "address_taken_candidates": labels,
        "limitations": [
            "Pointer-table contents and indirect targets require EMULATOR.EXE",
            "LAB references are not automatically safe function boundaries",
            "Game-specific renderer callbacks are included as dependencies",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(inventory(args.root), indent=2))


if __name__ == "__main__":
    main()
