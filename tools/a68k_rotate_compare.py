#!/usr/bin/env python3
"""Original ROR/ROL/ROXR/ROXL register bodies, including host count/CF quirks."""
import collections
import hashlib
import json
import random
import re
from pathlib import Path

from a68k_boundary_compare import Oracle, CTX, SP, STOP
from a68k_inventory import decode_dispatch
from unicorn.x86_const import *


def compare_rotates(exe, portable, shift=False):
    o = Oracle(exe)
    table = decode_dispatch(o.pe)[3]
    targets = sorted(set(table))
    if shift:
        source = Path(__file__).resolve().parents[1] / 'port/a68k/shift_register_ops.inc'
        specs = {int(a,16):(int(bits),0,0,int(variable),int(cost),int(special),name) for a,name,bits,variable,cost,special in re.findall(
            r'A68K_SHIFT_REGISTER\((0x[0-9a-f]+), (\w+), (\d+), (\d+), (\d+), (\d+)\)', source.read_text())}
    else:
        source = Path(__file__).resolve().parents[1] / 'port/a68k/rotate_ops.inc'
        specs = {int(a, 16): tuple(map(int, fields))+(0,'') for a, *fields in re.findall(
            r'A68K_ROTATE\((0x[0-9a-f]+), (\d+), (\d+), (\d+), (\d+), (\d+)\)', source.read_text())}
    stops = {}
    for target in specs:
        body = o.pe.read(target, next(t for t in targets if t > target) - target)
        stops[target] = tuple(target + m.start() for m in re.finditer(re.escape(bytes.fromhex('0fb70c2e')), body))
        assert stops[target]
    rng = random.Random(0xa68070)
    digest = hashlib.sha256()
    groups = collections.Counter()
    covered = set()
    values = (0, 1, 0x7fffffff, 0x80000000, 0xffffffff, 0xa5c3e791, 0x8000, 0x80)
    count_values = (0, 1, 7, 8, 15, 16, 17, 31, 32, 33, 63, 64, 65, 0xffffffff)
    for opcode, target in enumerate(table):
        if target not in specs:
            continue
        covered.add(opcode)
        bits, left, extend, variable, base, special, shift_name = specs[target]
        name = (shift_name if shift else ('ROX' if extend else 'RO') + ('L' if left else 'R')) + str(bits)
        for index, count in enumerate(count_values if variable else (0,)):
            for vindex, value in enumerate(values):
                context = [rng.getrandbits(32) for _ in range(33)]
                context[opcode & 7] = value
                if variable:
                    context[(opcode >> 9) & 7] = count
                context[19] = 0xa5c3e700 | (vindex & 1)
                context[17] = 0x20 if vindex & 1 else 0
                actual_count = context[(opcode >> 9) & 7] & 63 if variable else (((opcode >> 9) - 1) & 7) + 1
                total = base + (0 if special else 2 * actual_count)
                # Include underflow in the SUB preceding ROR/ROL count 32:
                # CF then depends on budget even though the value is unchanged.
                budget = (total - 1, total, total + 1, 1, 0xffffffff)[(index + vindex) % 5]
                pc = (0, 0x123456, 0xfffffffe)[vindex % 3]
                flags, host = 0x8c3, (0x202, 0x602)[vindex & 1]
                o.setup_exception(context, budget)
                o.put(SP + 4, *([0] * 7), STOP)
                o.run(target, {UC_X86_REG_ECX: opcode, UC_X86_REG_ESI: pc,
                              UC_X86_REG_EDX: flags, UC_X86_REG_EFLAGS: host}, stops=stops[target])
                p = portable.cpu(4, context, pc, flags, budget, opcode,
                                 costs=o.cost, entry=target, host_flags=host)
                expected = o.get(CTX, 33)
                exited = o.stop is None
                key = (hex(opcode), hex(value), hex(count), budget)
                assert p['context'] == expected, (key, 'context', p['context'], expected)
                assert p['flags'] == (expected[18] if exited else o.u.reg_read(UC_X86_REG_EDX)), (key, 'flags', p['flags'], o.u.reg_read(UC_X86_REG_EDX))
                assert p['pc'] == (pc + 2) & 0xffffffff
                assert p['cycles'] == (budget - total) & 0xffffffff
                assert p['boundary'] == (2 if exited else 1)
                assert p['events'] == [] and p['fault'] == [0] * 7
                groups[name] += 1
                digest.update(json.dumps([opcode, value, count, budget, p], sort_keys=True).encode())
    return dict(cases=sum(groups.values()), groups=dict(groups), mismatches=0,
                result_sha256=digest.hexdigest(), covered_entries=len(covered),
                targets=[f'{t:08x}' for t in sorted(specs)],
                limits=[('ASR/ASL/LSR/LSL register forms; original flag and timing quirks preserved.' if shift else 'Register forms only; native count masking, cycle-derived carry and partial X writes are intentional.'),
                        'Every encoding, boundary counts, count/destination aliases and budget underflow; full CPU integration remains separate.'])
