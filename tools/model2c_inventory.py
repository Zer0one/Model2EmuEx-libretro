#!/usr/bin/env python3
"""Static Model 2C recovery inventory; candidates are not recovered routines.

Uses the inherited Ghidra export, the original PE pointer tables and LLVM
disassembly. No ROM input, executable emulation or production code changes.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

EXPECTED = "2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc"
CORE = (0x4b3470, 0x4b7ad0)
DRIVER = (0x4c5850, 0x4c5e30)


def inventory(root, exe):
    data = exe.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError("Expected the recorded original 1.1a executable")
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 52)[0]
    sections = [struct.unpack_from("<8sIIII", data, pe + 24 + opt + i * 40)
                for i in range(count)]

    def read(va, n):
        for name, virtual_size, rva, size, offset in sections:
            if base + rva <= va and va + n <= base + rva + size:
                pos = offset + va - base - rva
                return data[pos:pos+n]
        raise ValueError(f"Address outside file-backed PE sections: {va:x}")

    source_path = root / "src/all_functions.c"
    source = source_path.read_text()
    heads = list(re.finditer(r"^// ===== (\w+) @ ([0-9a-f]{8}) =====$", source, re.M))
    bodies = {int(h[2], 16): source[h.end():heads[i+1].start() if i+1 < len(heads) else len(source)]
              for i, h in enumerate(heads)}
    candidates = {}

    def add(address, reason):
        candidates.setdefault(address, set()).add(reason)

    def specific(address):
        return any(lo <= address < hi for lo, hi in (CORE, DRIVER))

    # Driver identity is anchored by its original name, not a guessed range.
    driver_words = struct.unpack("<30I", read(0x574c00, 120))
    name = read(driver_words[0], 64).split(b"\0")[0].decode("ascii")
    if name != "Model 2C Driver v2.0 by ElSemi":
        raise ValueError("Unexpected driver table identity")
    driver = []
    for slot, target in enumerate(driver_words[1:], 1):
        kind = "model2c" if specific(target) else "shared"
        driver.append({"offset": hex(slot*4), "target": f"{target:08x}", "kind": kind,
                       "exported_body": target in bodies})
        if kind == "model2c": add(target, f"driver:00574c00+{slot*4:02x}")
    tables = []
    # Contiguous code-pointer runs found by the existing tools/ptrtables.py.
    # These are physical runs, not claims that each run is one semantic table.
    # Exclude the preceding 14 A68K interface pointers in the same physical run.
    for start, length in ((0x572ac0, 480), (0x573248, 32)):
        values = struct.unpack(f"<{length}I", read(start, length*4))
        if not all(CORE[0] <= value < CORE[1] for value in values):
            raise ValueError("Unexpected dispatch pointer outside reviewed core region")
        for index, value in enumerate(values): add(value, f"pointer:{start+index*4:08x}")
        tables.append({"start": f"{start:08x}", "entries": length,
                       "unique_targets": len(set(values)),
                       "targets": [f"{v:08x}" for v in values]})
    for address, body in bodies.items():
        if specific(address):
            add(address, "existing_export")
            for match in re.finditer(r"&(?:LAB|DAT|FUN)_([0-9a-f]{8})", body):
                target = int(match[1], 16)
                if specific(target): add(target, f"source_address_taken:{address:08x}")
    external = {}
    for address in (0x4b3470, 0x4b3480, 0x4b34a0, 0x4b34c0, 0x4b3520):
        add(address, "reviewed_lifecycle_entry")
    for lo, hi in (CORE, DRIVER):
        disasm = subprocess.check_output(
            ["xcrun", "llvm-objdump", "-d", f"--start-address={hex(lo)}",
             f"--stop-address={hex(hi)}", str(exe)], text=True)
        for line in disasm.splitlines():
            at = re.match(r"\s*([0-9a-f]+):", line)
            if not at: continue
            site = int(at[1], 16)
            call = re.search(r"\bcalll?\s+0x([0-9a-f]+)", line)
            if call:
                target = int(call[1], 16)
                if specific(target): add(target, f"binary_call:{site:08x}")
                else: external.setdefault(target, []).append(f"{site:08x}")
            # Code stores, not constants falsely decoded from inline switch
            # tables (e.g. 004b6aa9 looks like IMUL with a code-valued immediate).
            for immediate in re.finditer(r"\bmovl?\s+\$0x([0-9a-f]+)", line):
                target = int(immediate[1], 16)
                if specific(target): add(target, f"binary_code_immediate:{site:08x}")
    entries = [{"address": f"{a:08x}", "group": "core" if CORE[0] <= a < CORE[1] else "driver",
                "exported_body": a in bodies,
                "first_bytes": read(a, 8).hex(), "evidence": sorted(reasons)}
               for a, reasons in sorted(candidates.items())]
    return {"schema_version": 1, "status": "static_analysis_only",
            "exe_sha256": EXPECTED,
            "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "driver_name": name, "driver_table": "00574c00", "driver_slots": driver,
            "pointer_runs": tables, "candidates": entries,
            "external_direct_calls": [{"target": f"{a:08x}", "sites": sites,
                                       "exported_body": a in bodies}
                                      for a, sites in sorted(external.items())],
            "summary": {"candidates": len(entries),
                        "exported_bodies": sum(e["exported_body"] for e in entries),
                        "without_exported_body": sum(not e["exported_body"] for e in entries),
                        "core_candidates": sum(e["group"] == "core" for e in entries),
                        "driver_candidates": sum(e["group"] == "driver" for e in entries),
                        "shared_driver_slots": sum(e["kind"] == "shared" for e in driver)},
            "limits": ["Candidates require boundary/ABI review; not a final routine denominator",
                       "An exported decompiler body is not a verified portable implementation",
                       "Direct external calls and computed/queued dispatch need further closure",
                       "No runtime, instruction coverage, timing or gameplay validation"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("exe", type=Path)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    report = inventory(args.root, args.exe)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
