#!/usr/bin/env python3
"""Original SCSP-board CPU RAM mapping probe; no ROM or Windows allocation.

Execute the native DATA-map installer loop, then native word reads at the two
half-megabyte aliases used by the portable board. Allocation size is separately
pinned by the original MOV EAX,100000 / CALL allocator instruction bytes.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from a68k_boundary_compare import Oracle,DATA
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_EBP,UC_X86_REG_ECX


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();o=Oracle(a.exe)
    ram=0x74000000;board=0x75000000
    o.u.mem_map(ram,0x100000);o.u.mem_map(board,0x204000)
    o.put(board+0x20389c,ram)
    # Native 004cdaff allocation immediate, independently of Ghidra's lost ABI.
    assert o.pe.read(0x4cdaff,5)==bytes.fromhex('b800001000')
    o.run(0x4cd136,{UC_X86_REG_EBP:board,UC_X86_REG_EBX:0},stops=(0x4cd162,))
    pages=[o.get(DATA+16*i,4) for i in range(256)]
    assert all(p==[ram,0,0,0] for p in pages)
    o.u.mem_write(ram,b'\x22\x11');o.u.mem_write(ram+0x80000,b'\x44\x33')
    reads=[]
    for address in (0,0x80000):
        o.run(0x4b3220,{UC_X86_REG_ECX:address,UC_X86_REG_EAX:0})
        reads.append({'guest_address':hex(address),'word':hex(o.u.reg_read(UC_X86_REG_EAX)&65535)})
    assert [r['word'] for r in reads]==['0x1122','0x3344']
    result={'original_sha256':hashlib.sha256(a.exe.read_bytes()).hexdigest(),
            'group':'original_scsp_board_cpu_ram_map','native_allocation_bytes':0x100000,
            'native_linear_data_pages':len(pages),'reads':reads,
            'portable_current_ram_bytes':0x80000,'portable_current_mask':0x7ffff,
            'portable_masked_offsets':[0&0x7ffff,0x80000&0x7ffff],
            'limits':['Synthetic RAM; no game reachability or hardware correctness claim.',
                      'CPU address window only; SCSP sample addressing and state policy are separate.',
                      'Production board unchanged; semantic choice pending.']}
    root=Path(__file__).resolve().parents[1]
    result['sources_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),root/'port/snd/m2snd.c')}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sources_sha256'},indent=2))


if __name__=='__main__':main()
