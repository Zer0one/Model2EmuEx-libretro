#!/usr/bin/env python3
"""Compare A68K Model 1 accesses through native wrappers, including EAX, EDX and flags."""
import argparse
import ctypes as C
import json
import subprocess
import tempfile
from pathlib import Path
from model1_board_compare import initialize,SP,IRQ
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_EFLAGS

ROOT=Path(__file__).resolve().parents[1]

def compare(exe):
    o=initialize(exe)
    with tempfile.TemporaryDirectory() as td:
        shim=Path(td)/'shim.c'
        shim.write_text("""
#include "model1_bus.c"
#include <stdlib.h>
static a68k_cpu cpu;
static a68k_m1_bus bus={.cpu=&cpu};
static uint8_t samples[0x800000];
void init(void) { bus.sound=m2_original_m1_create(samples,sizeof samples); }
void cmd(unsigned v) { m2_original_m1_command(bus.sound,v); }
void reg(unsigned a,unsigned width,unsigned v) {m2_original_m1_write(bus.sound,a,width,v);}
void read_test(unsigned a,unsigned width,unsigned f,uint32_t *r) {
    cpu.r.irq=5;
    a68k_read_observation h=read_bus(&bus,a,f,width);
    r[0]=h.registers.value; r[1]=h.registers.edx;
    r[2]=h.control_flags; r[3]=cpu.r.irq;
}
void write_test(unsigned a,unsigned width,unsigned v,unsigned flags,unsigned sp,uint32_t *r) {
    cpu.write_wrapper_sp=sp;
    a68k_host_state h=write_bus(&bus,a,v,flags,width);
    r[0]=h.eax; r[1]=h.control_flags; r[2]=h.valid;
}
""")
        dll=Path(td)/'bus.so'
        subprocess.run(['cc','-O2','-std=c11','-shared','-fPIC','-I'+str(ROOT/'port/a68k'),
            str(shim),str(ROOT/'port/a68k/a68k.c'),
            *(str(ROOT/'port/snd'/f) for f in ('model1_original.c','fm_original.c','multipcm_original.c')),
            '-o',str(dll)],check=True)
        lib=C.CDLL(str(dll))
        lib.init()
        result=(C.c_uint32*4)()
        reads=writes=0
        for burst in (0,3,32,33):
            for i in range(burst):
                value=(i*91+0xac)&255
                o.run(0x4c8660,{UC_X86_REG_ECX:value})
                lib.cmd(value)
            for a in (0x20000,0xc10001,0xc20000,0xc20001,0xc200ff,0xc20101,0xc2fffe,
                      0xc2ffff,0xc40000,0xc50004,0xc60003,0xd00000,0xd00001,0xd00002,0xffffff):
                for w,fn in ((1,0x4b3250),(2,0x4b3220),(4,0x4b31f0)):
                    for flags in (0x202,0xed7):
                        o.put(IRQ,5)
                        o.run(fn,{UC_X86_REG_ECX:a,UC_X86_REG_EFLAGS:flags})
                        lib.read_test(a,w,flags,result)
                        native=[o.u.reg_read(r) for r in (UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EFLAGS)]+o.get(IRQ)
                        assert native==list(result),(hex(a),w,burst,list(map(hex,native)),list(map(hex,result)))
                        reads+=1
        for a in (0x000000,0xc10001,0xc20001,0x080002):
            for w,fn in ((1,0x4b3130),(2,0x4b3100),(4,0x4b30c0)):
                for v in (0,0x43217a65):
                    flags=0xed7
                    o.run(fn,{UC_X86_REG_ECX:a,UC_X86_REG_EDX:v,UC_X86_REG_EFLAGS:flags})
                    lib.write_test(a,w,v,flags,SP,result)
                    assert list(result[:3])==[o.u.reg_read(UC_X86_REG_EAX),o.u.reg_read(UC_X86_REG_EFLAGS),1]
                    writes+=1
        pcm_writes=0
        for base in (0xc40000,0xc60000):
            for reg in range(8):
                for off in (5,0,1,2,3,4,5,6,15,16,0x10000,0x10001):
                    for w,fn in ((1,0x4b3130),(2,0x4b3100),(4,0x4b30c0)):
                        for v in (0,0x7f018f3f,0x320080dc):
                            o.run(0x4b3130,{UC_X86_REG_ECX:base+5,UC_X86_REG_EDX:reg})
                            lib.reg(base+5,1,reg)
                            a=base+off; flags=0x202
                            o.run(fn,{UC_X86_REG_ECX:a,UC_X86_REG_EDX:v,UC_X86_REG_EFLAGS:flags})
                            lib.write_test(a,w,v,flags,SP,result)
                            native=[o.u.reg_read(r) for r in (UC_X86_REG_EAX,UC_X86_REG_EFLAGS)]+[1]
                            assert list(result[:3])==native,(hex(a),w,reg,hex(v),list(map(hex,native)),list(map(hex,result[:3])))
                            pcm_writes+=1
        fm_writes=0
        for bank in (0,1):
            for reg in range(256):
                for v in (0,1,7,63,128,255):
                    flags=0xed7
                    for port,value in ((2*bank,reg),(2*bank+1,v)):
                        a=0xd00000+port*2
                        o.run(0x4b3130,{UC_X86_REG_ECX:a,UC_X86_REG_EDX:value,UC_X86_REG_EFLAGS:flags})
                        lib.write_test(a,1,value,flags,SP,result)
                        native=[o.u.reg_read(r) for r in (UC_X86_REG_EAX,UC_X86_REG_EFLAGS)]+[1]
                        assert list(result[:3])==native,(bank,hex(reg),port,v,list(map(hex,native)),list(map(hex,result[:3])))
                        fm_writes+=1
        wide_fm=0
        for width,wrapper in ((2,0x4b3100),(4,0x4b30c0)):
            for offset in range(16):
                for value in (0,0x270106ef,0x403f4307,0x12345678,0xffffffff):
                    address=0xd00000+offset
                    o.run(wrapper,{UC_X86_REG_ECX:address,UC_X86_REG_EDX:value,UC_X86_REG_EFLAGS:0xed7})
                    lib.write_test(address,width,value,0xed7,SP,result)
                    expected=[o.u.reg_read(UC_X86_REG_EAX),o.u.reg_read(UC_X86_REG_EFLAGS)]
                    assert list(result[:2])==expected,(width,offset,hex(value),expected,list(result[:2]))
                    wide_fm+=1
        return dict(wide_fm_writes=wide_fm,complete_read_observations=reads,default_write_observations=writes,pcm_writes=pcm_writes,fm_writes=fm_writes)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('exe',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=compare(a.exe)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result)
if __name__=='__main__':
    main()
