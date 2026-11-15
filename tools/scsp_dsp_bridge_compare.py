#!/usr/bin/env python3
"""Recover native mixer tables and compare DSP boundary integer operations.

Runs unchanged PE fragments with synthetic samples; no ROM or whole-chip claim.
Table initialization uses Unicorn x87, not physical-x86 validation.
"""
import argparse
import ctypes as C
import hashlib
import json
import struct
import sys
from pathlib import Path
from scsp_dsp_compare import OriginalDSP, SP, STOP, instruction
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,
    UC_X86_REG_EDX,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP,
    UC_X86_REG_FPCW,UC_X86_REG_FPSW,UC_X86_REG_FPTAG)


def native_boundaries(original):
    u=original.uc
    # Read beyond the original 1 MiB allocation into a deliberately mapped
    # synthetic guard. This never reads actual host or user memory.
    ram=0x74000000;u.mem_map(ram,0x120000)
    state=bytearray(0x800);struct.pack_into('<III',state,0,ram,127,8192)
    state[0xcc:0xe4]=instruction()+instruction(MRD=1,TABLE=1)+instruction(IWT=1,IWA=7)
    struct.pack_into('<I',state,0x7b8,3);struct.pack_into('<H',state,0x8c,65535)
    address=(127*4096+65535)*2;u.mem_write(ram+address,struct.pack('<H',0x1234))
    result,code_hash=original.run(state)
    got=struct.unpack_from('<i',result,0x6cc+28)[0];assert got==0x123400
    boundary=dict(allocation_bytes=0x100000,byte_address=address,original_mems7=got,
                  generated_sha256=code_hash,game_reachability=False)
    # Native word/byte register writes. Stop at Start before running codegen;
    # other addresses return normally to the mapped sentinel.
    events=[];started=[]
    def stop_at_start(mu,address,size,data):
        started.append(address);mu.emu_stop()
    hook=u.hook_add(UC_HOOK_CODE,stop_at_start,begin=0x4aa7f0,end=0x4aa7f0)
    u.mem_write(0x5728bc,struct.pack('<I',0x72000000))
    for width,entry in ((16,0x4afa20),(8,0x4afb00)):
        for address in (0xbf0,0xbfc,0xbfe,0xbff):
            started.clear();u.mem_write(SP,struct.pack('<I',STOP))
            for reg,value in ((UC_X86_REG_ESP,SP),(UC_X86_REG_ECX,address),(UC_X86_REG_EDX,0x1234)):
                u.reg_write(reg,value)
            u.emu_start(entry,STOP,count=1000)
            assert bool(started)==(address==0xbfe)
            assert u.reg_read(UC_X86_REG_EIP)==(0x4aa7f0 if started else STOP)
            events.append(dict(width=width,address=hex(address),compile=bool(started)))
    u.hook_del(hook)
    return dict(ram=boundary,register_writes=events)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('library',type=Path)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    original=OriginalDSP(args.exe);u=original.uc
    boundaries=native_boundaries(original)
    for reg,val in ((UC_X86_REG_ESP,SP),(UC_X86_REG_EBX,0),(UC_X86_REG_EBP,0),
                    (UC_X86_REG_FPCW,0x27f),(UC_X86_REG_FPSW,0),(UC_X86_REG_FPTAG,0xffff)):
        u.reg_write(reg,val)
    u.emu_start(0x4af3ce,0x4af5aa,count=1000000)
    assert u.reg_read(UC_X86_REG_EIP)==0x4af5aa
    tables={name:list(struct.unpack('<'+'i'*n,u.mem_read(addr,n*4))) for name,addr,n in
        [('TL',0x10c3a40,256),('SDL',0x10c1168,8),('LPAN',0x10be4d8,32),('RPAN',0x10e3f40,32)]}
    lib=C.CDLL(str(args.library.resolve()))
    lib.scsp_dsp_original_input.argtypes=[C.c_int32,C.c_uint,C.c_uint]
    lib.scsp_dsp_original_input.restype=C.c_uint32
    lib.scsp_dsp_original_output.argtypes=[C.c_int16,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p]
    failures=[];digest=hashlib.sha256();counts={'input':0,'output':0}
    samples=(-32768,-32767,-4096,-1,0,1,4096,32767)
    for tl in range(256):
        for level in range(8):
            for sample in samples:
                u.mem_write(0x7200006a,struct.pack('<i',tables['TL'][tl]))
                u.mem_write(0x72000000,struct.pack('<H',(3<<3)|level))
                u.mem_write(0x109c474+12,bytes(4))
                u.reg_write(UC_X86_REG_EDI,0x72000002);u.reg_write(UC_X86_REG_EAX,sample&0xffffffff)
                # EDI+0x6a is where the fragment expects the cached TL gain.
                u.mem_write(0x7200006c,struct.pack('<i',tables['TL'][tl]))
                u.emu_start(0x4aeb76,0x4aeba5,count=1000)
                assert u.reg_read(UC_X86_REG_EIP)==0x4aeba5
                native=struct.unpack('<I',u.mem_read(0x109c474+12,4))[0]
                recovered=lib.scsp_dsp_original_input(sample,tl,level)
                digest.update(struct.pack('<II',native,recovered));counts['input']+=1
                if native!=recovered:failures.append(dict(kind='input',tl=tl,level=level,sample=sample,native=native,recovered=recovered))
    for pan in range(32):
        for level in range(8):
            for sample in samples:
                u.mem_write(0x72000000,struct.pack('<H',pan|(level<<5)))
                u.mem_write(0x72000010,struct.pack('<h',sample))
                for reg,val in ((UC_X86_REG_EDX,0x72001a2c),(UC_X86_REG_ECX,0x72001a3c),(UC_X86_REG_EBP,0),(UC_X86_REG_EBX,0)):
                    u.reg_write(reg,val)
                u.emu_start(0x4aecf0,0x4aed36,count=1000)
                assert u.reg_read(UC_X86_REG_EIP)==0x4aed36
                native=(u.reg_read(UC_X86_REG_EBP),u.reg_read(UC_X86_REG_EBX))
                left,right=C.c_int32(),C.c_int32()
                lib.scsp_dsp_original_output(sample,pan,level,C.byref(left),C.byref(right))
                recovered=(left.value&0xffffffff,right.value&0xffffffff)
                digest.update(struct.pack('<4I',*native,*recovered));counts['output']+=1
                if native!=recovered:failures.append(dict(kind='output',pan=pan,level=level,sample=sample,native=native,recovered=recovered))
    report=dict(cases=sum(counts.values()),groups=counts,native_boundaries=boundaries,mismatches=len(failures),failures=failures,tables=tables,
                result_sha256=digest.hexdigest(),original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
                limits=['Synthetic signed16 input samples; unchanged original integer fragments.',
                        'Original gain-table initialization uses Unicorn x87; no physical-x86/full-PCM equivalence claim.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:report[k] for k in ('cases','groups','mismatches','result_sha256')})
    return bool(failures)

if __name__=='__main__':sys.exit(main())
