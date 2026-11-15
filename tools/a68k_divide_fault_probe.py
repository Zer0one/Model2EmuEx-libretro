#!/usr/bin/env python3
"""Bounded original DIVS host-overflow probe; no behavior replacement."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from unicorn import UcError, UC_ERR_EXCEPTION
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDX, UC_X86_REG_EIP
from a68k_boundary_compare import Oracle, CTX, SP, STOP
from a68k_inventory import decode_dispatch


def probe(exe):
    oracle=Oracle(exe)
    table=decode_dispatch(oracle.pe)[3]
    target=table[0x83c0]  # DIVS.W D0,D1
    body=oracle.pe.read(target,min(t for t in table if t>target)-target)
    stops=tuple(target+m.start() for m in re.finditer(re.escape(bytes.fromhex('0fb70c2e')),body))
    rows=[]
    for dividend in (0x80000000,0x80000001,0x7fffffff,0x00008000,0x00007fff):
        context=[0]*33
        context[0]=0xffff;context[1]=dividend;context[17]=0x20
        oracle.setup_exception(context,200)
        oracle.put(SP+4,*([0]*7),STOP)
        fault=None
        try:
            oracle.run(target,{UC_X86_REG_ECX:0x83c0,UC_X86_REG_ESI:0x1000,
                               UC_X86_REG_EDX:0x202},stops=stops)
        except UcError as error:
            assert error.errno==UC_ERR_EXCEPTION
            fault=oracle.u.reg_read(UC_X86_REG_EIP)
            assert dividend==0x80000000 and fault==0x48198c
            assert oracle.pe.read(fault,2)==bytes.fromhex('f7fb')  # IDIV EBX
        assert bool(fault)==(dividend==0x80000000)
        rows.append(dict(dividend=f'{dividend:08x}',divisor='ffff',
            host_fault_at=f'{fault:08x}' if fault else None,
            context=oracle.get(CTX,33),live_flags=f'{oracle.u.reg_read(UC_X86_REG_EDX):08x}',
            events=oracle.events))
    return dict(original_sha256=hashlib.sha256(oracle.pe.data).hexdigest(),entry=f'{target:08x}',
                cases=len(rows),results=rows,
                finding='DIVS INT32_MIN / -1 reaches x86 IDIV overflow before the guest 16-bit quotient check.',
                limits=['Original CPU body under Unicorn; no claim about outer Windows exception handling or game reachability.',
                        'The public Make68K divides() source emits the same unguarded CDQ/IDIV sequence.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=probe(args.exe)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='results'},indent=2))
