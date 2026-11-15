#!/usr/bin/env python3
"""Original SCSP FIFO/global read/timer/IRQ bodies versus actual port paths.

Source-guided boundary cases, not a CPU-wide instruction test. No ROMs; original
x86 executes in Unicorn with the same synthetic state as the compiled C module.
"""
import argparse,ctypes as C,hashlib,itertools,json,random,struct,subprocess,tempfile
from pathlib import Path
from a68k_boundary_compare import Oracle
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX
ROOT=Path(__file__).resolve().parents[1]
CHIP=0x109aae8

def fixtures():
    def base():
        x=[0]*64;x[6:9]=[2,4,6];x[9]=0xabcd;x[13]=2
        x[24:56]=[(i*0x19234567)&0xffffffff for i in range(32)]
        return x
    for rd,wr,count in ((0,0,0),(0,40,40),(127,0,1),(127,127,0),(7,8,255),(64,96,32)):
        x=base();x[:4]=[rd,wr,count,6];x[12]=0xd3
        yield 'enqueue',0,x
        for offset,width in itertools.product((4,5,0x104,0x105),(1,2)):
            y=x.copy();y[11]=offset;y[13]=width;yield 'midi-read',1,y
    for slot,low,offset,width in itertools.product((0,7,15,31),(0,0x7f),(8,9,0x108,0x109),(1,2)):
        x=base();x[10]=(slot<<11)|low;x[11]=offset;x[13]=width;yield 'monitor-read',1,x
    for fifo,pend,en,old in itertools.product((False,True),(0,8,0x20,0x40,0x80,0x100,0x1c0,0xffff),(0,0x40,0x80,0x100,0x1c0,0xffff),(0,3,7)):
        x=base();x[1]=int(fifo);x[3]=old;x[4]=pend;x[5]=en
        yield 'irq-check',2,x;yield 'irq-ack',3,x
    for scale,counter,expired in itertools.product(range(8),(0,0xfeff,0xff00,0xffff,0x10000),(0,1)):
        x=base();x[4]=0x20;x[5]=0x1c0;x[14:17]=[counter]*3;x[17:20]=[expired]*3;x[20:23]=[(scale<<8)|(counter>>8&255)]*3
        yield 'timer-tick',4,x
    for timer,low,frac,scale in itertools.product(range(3),(0,0xfe,0xff),(0,0x5a,0xff),(0,7)):
        x=base();x[11]=0x18+timer*2;x[14+timer]=0x123400|frac;x[17+timer]=1;x[20+timer]=(scale<<8)|low
        yield 'timer-write',5,x
    for flags,pend,mask in itertools.product(range(8),(0,0x20,0x1c0),(0,0x40,0xffff)):
        x=base();x[11]=0x22;x[4]=pend;x[5]=0x1c0;x[56]=mask;x[3]=4
        x[17:20]=[(flags>>i)&1 for i in range(3)];yield 'irq-reset',6,x
    for offset,width,value in itertools.product((4,8,0x18,0x1a,0x1c,0x1e,0x20,0x22,0x24,0x26,0x28),(1,2),(0,0x40,0xff)):
        for byte in (range(2) if width==1 else (0,)):
            x=base();x[1]=40;x[2]=40;x[3]=6;x[4]=0x1c0;x[5]=0x1c0
            x[11]=offset+byte;x[12]=value;x[13]=width
            x[14:17]=[0xfe5a]*3;x[17:20]=[1]*3;x[20:23]=[0x7fe]*3
            yield 'cpu-global-write',7,x

def native(o,op,x,fifo,execute=True):
    o.put(0x5728bc,CHIP);o.u.mem_write(CHIP,b'\0'*0x30)
    o.u.mem_write(CHIP+0x1238,b'\1') # Native master guard in global update.
    for at,value in ((2,x[60]),(4,x[9]),(8,x[10]),(0x20,x[4]),(0x1e,x[5]),(0x22,x[56])):
        o.u.mem_write(CHIP+at,struct.pack('<H',value))
    for i in range(3):o.u.mem_write(CHIP+0x18+i*2,struct.pack('<H',x[20+i]))
    for i in range(32):o.put(CHIP+0x58+i*0x8c,x[24+i])
    o.put(0x10bdf44,*x[14:17]);o.u.mem_write(0x10bdf40,bytes(x[17:20]))
    o.u.mem_write(0x10ed9d8,bytes((x[1],x[0])));o.u.mem_write(0x1078799,bytes((x[2],)))
    o.u.mem_write(0x10c35b0,fifo);o.put(0x572890,*x[6:9]);o.put(0x528d38,x[3]);value=0
    if not execute:pass
    elif op==0:o.run(0x4c868a,{UC_X86_REG_ECX:x[12]},stops=(0x4c86a8,))
    elif op==1:
        o.run(0x4ae870 if x[13]==1 else 0x4ae800,{UC_X86_REG_ECX:0x100400+x[11]})
        value=o.u.reg_read(UC_X86_REG_EAX)&(255 if x[13]==1 else 65535)
    elif op==2:o.run(0x4aea40)
    elif op==3:o.put(0x528d38,0);o.run(0x4aeac0)
    elif op==4:o.run(0x4ab0e0);o.run(0x4aea40)
    elif op==7:o.run(0x4afb00 if x[13]==1 else 0x4afa20,{UC_X86_REG_ECX:0x100400+x[11],UC_X86_REG_EDX:x[12]})
    else:o.run(0x4af050,{UC_X86_REG_EAX:x[11]})
    return native_state(o,value)

def native_state(o,value=0):
    word=lambda at:struct.unpack('<H',o.u.mem_read(CHIP+at,2))[0]
    out=[value,o.u.mem_read(0x10ed9d9,1)[0],o.u.mem_read(0x10ed9d8,1)[0],o.u.mem_read(0x1078799,1)[0],o.get(0x528d38)[0],word(0x20),word(4),word(8)]
    out+=o.get(0x10bdf44,3)+list(o.u.mem_read(0x10bdf40,3))+[word(0x18+2*i) for i in range(3)]
    out+=list(struct.unpack('<32I',o.u.mem_read(0x10c35b0,128)))
    out+=[word(2*i) for i in range(24)]+o.get(0x572890,3);return out

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--optimization',choices=('O0','O2'),default='O2');ap.add_argument('--ubsan',action='store_true');a=ap.parse_args()
    sources=[ROOT/'port/snd/test/scsp_control_shim.c',ROOT/'port/snd/scsp_dsp_original.c']
    groups={};digest=hashlib.sha256();o=Oracle(a.exe);fifo=bytes((i*29+17)&255 for i in range(128))
    with tempfile.TemporaryDirectory(prefix='model2-scsp-control-') as d:
        lib=Path(d)/'control.dylib';cmd=['clang','-'+a.optimization,'-std=c11','-Wall','-Wextra','-Werror','-dynamiclib','-fPIC',*map(str,sources),'-lm','-o',str(lib)]
        if a.ubsan:
            resource=subprocess.check_output(['clang','--print-resource-dir'],text=True).strip()
            cmd+=['-fsanitize=undefined','-fno-sanitize-recover=all','-shared-libsan','-Wl,-rpath,'+resource+'/lib/darwin']
        subprocess.run(cmd,check=True);dll=C.CDLL(str(lib));fn=dll.scsp_control_probe
        fn.argtypes=[C.c_uint,C.POINTER(C.c_uint32),C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)];fn.restype=C.c_int
        for group,op,x in fixtures():
            expected=native(o,op,x,fifo);out=(C.c_uint32*76)()
            assert fn(op,(C.c_uint32*64)(*x),(C.c_uint8*128).from_buffer_copy(fifo),out)
            assert list(out)==expected,(group,x,[(i,v,expected[i]) for i,v in enumerate(out) if v!=expected[i]])
            groups[group]=groups.get(group,0)+1;digest.update(struct.pack('<76I',*out))
    result=dict(cases=sum(groups.values()),groups=groups,mismatches=0,result_sha256=digest.hexdigest(),optimization=a.optimization,ubsan=a.ubsan,
                original_sha256=hashlib.sha256(a.exe.read_bytes()).hexdigest(),
                limits=['Synthetic native control bodies, not whole-game or complete A68K integration.',
                        'Global object aliases outside 0x400-0x42f/0x500-0x52f and native host scratch remain separate.',
                        'Original Windows enqueue notification and whole sound-thread scheduler are not executed.'])
    paths=[*sources,Path(__file__),ROOT/'port/snd/scsp.c',ROOT/'port/snd/scsp.h']
    result['sources_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='sources_sha256'},indent=2))

if __name__=='__main__':main()
