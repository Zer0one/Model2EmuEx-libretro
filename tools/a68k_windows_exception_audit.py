#!/usr/bin/env python3
"""Audit the pinned original's Windows filters around A68K, without ROMs.

Execute unchanged filter bodies with synthetic EXCEPTION_RECORD/thread data.
This is not a Windows kernel dispatcher or a full-process crash experiment.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

from a68k_boundary_compare import Oracle, RAM, SP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX


def audit(exe):
    o = Oracle(exe)
    pe = o.pe
    record, pointers, ptd, frame = RAM, RAM + 0x100, RAM + 0x200, RAM + 0x800
    o.put(ptd + 0x5c, 0x50ee90)
    o.put(pointers, record, RAM + 0x1000)
    intercepted = []

    def thread_data(u, address, size, data):
        if address in (0x498038, 0x4980b1):
            intercepted.append(f'{address:08x}')
            o.ret(ptd)

    o.u.hook_add(UC_HOOK_CODE, thread_data)
    table = [struct.unpack('<III', pe.read(0x50ee90 + i * 12, 12)) for i in range(12)]
    assert not {0xc0000094, 0xc0000095} & {row[0] for row in table}
    assert all(row[2] == 0 for row in table)
    scope = list(struct.unpack('<7I', pe.read(0x524bc0, 28)))
    assert scope[4:] == [0xfffffffe, 0x493ff5, 0x494009]
    info = list(struct.unpack('<9I', pe.read(0x525378, 36)))
    assert info == [0x19930522, 1, 0x525370, 0, 0, 0, 0, 0, 1]
    cases = []
    for code in (0xc0000094, 0xc0000095, 0xc0000005):
        o.put(record, code, 0, 0, 0x48198c, 0, *([0] * 15))
        before = bytes(o.u.mem_read(record, 80))
        for name, entry, args, expected in (
            ('CRT __XcptFilter', 0x4a168b, [code, pointers], 0),
            ('Top-Level __CxxUnhandledExceptionFilter', 0x4a163b, [pointers], 0),
            ('Main Loop C++ Frame Handler', 0x5042be,
             [record, frame, RAM + 0x1000, 0], 1),
        ):
            intercepted.clear()
            o.put(SP + 4, *args)
            o.run(entry)
            result = o.u.reg_read(UC_X86_REG_EAX)
            assert result == expected, (name, code, result)
            assert bytes(o.u.mem_read(record, 80)) == before
            cases.append(dict(filter=name, entry=f'{entry:08x}',
                              exception=f'{code:08x}', result=result,
                              meaning='Continue Search', thread_data_stubs=list(intercepted)))
    # Positive controls: demonstrate that XcptFilter actually obeys table
    # actions, rather than interpreting every return as unhandled.
    for action, expected in ((1, 0xffffffff), (5, 1)):
        o.put(0x50ee98, action)  # Synthetic action on the access-violation row.
        o.put(SP + 4, 0xc0000005, pointers)
        o.run(0x4a168b)
        assert o.u.reg_read(UC_X86_REG_EAX) == expected
        cases.append(dict(filter='CRT Positive Control', synthetic_action=action,
                          exception='c0000005', result=expected))
    o.put(0x50ee98, 0)

    # LLVM supplies instruction boundaries; do not infer call sites by finding
    # arbitrary E8 bytes in the executable or depend on incomplete decompilation.
    disasm = subprocess.check_output(['xcrun', 'llvm-objdump', '-d', str(exe)], text=True)
    instructions = []
    for line in disasm.splitlines():
        m = re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(.*)$', line)
        if m:
            instructions.append((int(m[1], 16), bytes.fromhex(m[2]), m[3]))
    calls = [f'{a:08x}' for a, b, t in instructions if re.match(r'calll\s+0x462b1c\b', t)]
    assert calls == ['004af01d', '004b3064', '004cc736']
    setters = [f'{a:08x}' for a, b, t in instructions if b == bytes.fromhex('ff156c815000')]
    assert setters == ['0049545c', '004a1605', '004a1682']
    assert pe.read(0x495458, 4) == bytes.fromhex('6a008bf8')
    assert pe.read(0x4a1603, 2) == bytes.fromhex('6a00')
    assert pe.read(0x4a167d, 5) == bytes.fromhex('683b164a00')
    assert pe.read(0x51bbd0, 4) == struct.pack('<I', 0x4cc7a0)
    ranges = [(0x462b1c, 0x462bcb), (0x4aefb0, 0x4af050),
              (0x4b3050, 0x4b3070), (0x4cc710, 0x4cc7a0),
              (0x4cc7a0, 0x4ccbe0), (0x5004e0, 0x500530)]
    bodies = []
    for start, end in ranges:
        lines = [(a, t) for a, b, t in instructions if start <= a < end]
        fs = [(f'{a:08x}', t) for a, t in lines if '%fs:' in t]
        assert not fs
        bodies.append(dict(start=f'{start:08x}', end_exclusive=f'{end:08x}',
                           sha256=hashlib.sha256(pe.read(start, end-start)).hexdigest(),
                           fs_accesses=fs))
    return dict(original_sha256=hashlib.sha256(pe.data).hexdigest(), cases=cases,
                exception_action_table=[dict(code=f'{c:08x}', signal=s, action=a) for c, s, a in table],
                crt_scope_table=[f'{x:08x}' for x in scope],
                main_loop_cpp_funcinfo=[f'{x:08x}' for x in info],
                a68k_direct_call_sites=calls, set_unhandled_filter_call_sites=setters,
                reviewed_bodies=bodies,
                findings=[
                    'Both integer division status codes continue search in all three tested original filters.',
                    'The main-loop C++ metadata has zero catch blocks and EHs enabled.',
                    'The CRT registers its C++ top-level filter; the other two setter calls clear it in fatal-reporting paths.',
                    'No recovered path translates host division overflow to 68000 flags or resumes the opcode.'
                ],
                limits=[
                    'Unchanged filter machine code under Unicorn; synthetic thread data replaces only CRT TLS lookup.',
                    'No Windows process crash, kernel exception dispatch, external DLL handler or game reachability test.',
                    'SEH disposition ContinueSearch is 1; filter-expression EXCEPTION_CONTINUE_SEARCH is 0. They are different APIs.',
                    'Ordinary Windows unhandled-exception termination is an inference from this audit and documented OS behavior.'
                ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.exe)
    result['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=len(result['cases']), findings=result['findings']), indent=2))
