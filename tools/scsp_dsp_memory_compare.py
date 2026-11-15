#!/usr/bin/env python3
"""Bounded original/portable DSP memory and sample-lifecycle comparison.

Differences are research results, not a production compatibility policy.
RAM is word-identical: both now use the original word-swapped representation.
"""
import argparse
import collections
import ctypes as C
import hashlib
import json
import random
import struct
import sys
from pathlib import Path
from scsp_dsp_compare import OriginalDSP, instruction, fixtures as arithmetic_fixtures
from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE

RAM=0x74000000
RAM_SIZE=0x80000
FIELDS=[('TEMP',0x4cc,512),('MEMS',0x6cc,128),('DEC',0x74c,4),
        ('MIXS',0x750,64),('EFREG',0x794,32)]


def wordswap(data):
    out=bytearray(len(data));out[0::2]=data[1::2];out[1::2]=data[0::2]
    return out


def state(program,dec=0):
    s=bytearray(0x800)
    struct.pack_into('<III',s,0,RAM,0,8192)
    s[0xcc:0xcc+len(program)]=program
    struct.pack_into('<I',s,0x7b8,len(program)//8)
    struct.pack_into('<I',s,0x74c,dec)
    return s


def fixtures():
    for group,s,params in arithmetic_fixtures():
        struct.pack_into('<I',s,0,RAM)
        yield group,s,bytearray(RAM_SIZE),1,params
    # MRD executes on odd instruction positions. The following IWT exposes
    # MEMVAL; RAM data use signed16 boundary/packing encodings explicitly.
    for nofl in (0,1):
        for word in (0,1,0x7ff,0x800,0x3fff,0x7fff,0x8000,0x8001,0xf800,0xffff):
            for slot in (0,1):
                p=([instruction()]*slot + [instruction(MRD=1,NOFL=nofl,TABLE=1)] +
                   [instruction(IWT=1,IWA=7)])
                s=state(b''.join(p)); r=bytearray(RAM_SIZE)
                struct.pack_into('<H',r,0,word)
                yield 'read',s,r,1,dict(nofl=nofl,word=word,slot=slot)
    for nofl in (0,1):
        for value in (-8388608,-4096,-1,0,1,4096,8388607):
            for slot in (0,1):
                # The portable loop has no incoming ACC. Produce it in a
                # predecessor, then issue the write at the requested parity.
                p=[instruction(TRA=5)]
                if slot==0:p.append(instruction(TRA=5))
                p.append(instruction(MWT=1,NOFL=nofl,TABLE=1))
                s=state(b''.join(p));struct.pack_into('<i',s,0x4cc+20,value)
                yield 'write',s,bytearray(RAM_SIZE),1,dict(nofl=nofl,value=value,slot=(len(p)-1)&1)
    # Address traces independently verify selection of DEC, RBL, MADRS and
    # RBP, even where the following sample conversion differs.
    for table in (0,1):
        for dec in (0,1,8191,8192,0xffffffff):
            for rbp in (0,3):
                for nxadr in (0,1):
                    p=instruction()+instruction(MRD=1,TABLE=table,NXADR=nxadr)+instruction(IWT=1,IWA=7)
                    s=state(p,dec);struct.pack_into('<I',s,4,rbp)
                    struct.pack_into('<H',s,0x8c,8191)
                    r=bytearray(RAM_SIZE)
                    for i in range(0,RAM_SIZE,2):struct.pack_into('<H',r,i,(i//2)&0x7ff)
                    yield 'address',s,r,1,dict(table=table,dec=dec,rbp=rbp,nxadr=nxadr)
    # Scratch is initialized once, then reused across original sample calls.
    for register in ('ACC','MEMVAL','FRC','Y','ADRS'):
        for samples in (1,2,3):
            if register=='ACC':
                p=instruction(TWT=1,TWA=11,TRA=5)+instruction(TWT=1,TWA=12,TRA=5)
            elif register=='MEMVAL':
                p=instruction(IWT=1,IWA=7)+instruction(MRD=1,TABLE=1)
            elif register=='FRC':
                p=(instruction(TRA=5,YSEL=0)+instruction(TWT=1,TWA=11,FRCL=1))
            elif register=='Y':
                p=(instruction(TRA=5,YSEL=2,YRL=1,IRA=7)+instruction(TWT=1,TWA=11))
            else:
                p=(instruction(ADRL=1,IRA=7)+instruction(MRD=1,TABLE=1,ADREB=1)+instruction(IWT=1,IWA=9))
            s=state(p)
            for i in range(128):struct.pack_into('<i',s,0x4cc+4*i,4096)
            struct.pack_into('<i',s,0x6cc+28,0x123456)
            r=bytearray(RAM_SIZE);struct.pack_into('<H',r,0,0x1234)
            yield 'continuation',s,r,samples,dict(register=register,samples=samples)
    for ira in (32,33,47,48,49):
        for value in (-32768,-1,1,32767):
            p=instruction(XSEL=1,YSEL=1,IRA=ira,ZERO=1)+instruction(TWT=1,TWA=11)
            s=state(p);struct.pack_into('<h',s,0xc,0x4000)
            struct.pack_into('<i' if ira<48 else '<h',s,0x750+(ira-32)*4 if ira<48 else 0x790+(ira-48)*2,value)
            yield 'input-representation',s,bytearray(RAM_SIZE),1,dict(ira=ira,value=value)


    rng=random.Random(0x5c5b02)
    for i in range(256):
        program=b''
        for j in range(16):
            mem=rng.randrange(3)  # Separate read/write; combined handled below.
            program+=instruction(TRA=rng.randrange(128),TWT=rng.randrange(2),TWA=rng.randrange(128),
                XSEL=rng.randrange(2),YSEL=rng.randrange(4),IRA=rng.randrange(32),IWT=rng.randrange(2),IWA=rng.randrange(32),
                MRD=int(mem==1),MWT=int(mem==2),TABLE=rng.randrange(2),NOFL=rng.randrange(2),
                EWT=1,EWA=rng.randrange(16),ADRL=rng.randrange(2),FRCL=rng.randrange(2),SHIFT=rng.randrange(4),
                YRL=rng.randrange(2),NEGB=rng.randrange(2),ZERO=rng.randrange(2),BSEL=rng.randrange(2),
                COEF=rng.randrange(64),MASA=rng.randrange(32),ADREB=rng.randrange(2),NXADR=rng.randrange(2))
        s=state(program,rng.getrandbits(32))
        struct.pack_into('<II',s,4,rng.randrange(4),8192<<rng.randrange(4))
        for j in range(64):struct.pack_into('<h',s,0xc+2*j,rng.randrange(-32768,32768))
        for j in range(32):struct.pack_into('<H',s,0x8c+2*j,rng.randrange(65536))
        for off in range(0x4cc,0x74c,4):struct.pack_into('<i',s,off,rng.randrange(-8388608,8388608))
        for off in (0x7bc,0x7c0,0x7d0,0x7d4,0x7d8,0x7dc,0x7e4):
            struct.pack_into('<i',s,off,rng.randrange(-8388608,8388608))
        r=bytearray(rng.randbytes(RAM_SIZE))
        yield 'memory-chain',s,r,3,dict(index=i)
    for nofl in (0,1):
        for value in (0,256,4096,8388607):
            s=state(instruction(TRA=5)+instruction(MRD=1,MWT=1,NOFL=nofl,TABLE=1)+instruction(IWT=1,IWA=7))
            struct.pack_into('<i',s,0x4cc+20,value)
            r=bytearray(RAM_SIZE);struct.pack_into('<H',r,0,0x2345)
            yield 'combined-read-write',s,r,1,dict(nofl=nofl,value=value)
    for steps in (0,1,127,128):
        for stopped in (0,1):
            s=state(instruction(TWT=1,TWA=11,TRA=5)*steps)
            struct.pack_into('<I',s,0x7b4,stopped)
            for j in range(128):struct.pack_into('<i',s,0x4cc+j*4,4096)
            yield 'program-boundary',s,bytearray(RAM_SIZE),3,dict(steps=steps,stopped=stopped)
    # At 128 instructions the generator's lookahead reads the first TEMP
    # bytes once at compilation. A write to TEMP[1] must not re-decode that
    # successor dynamically during execution or the next sample.
    for seed in (0,0x1000):
        for samples in (1,3):
            s=state(instruction(TWT=1,TWA=1,TRA=5)*128)
            struct.pack_into('<i',s,0x4cc+4,seed)
            for j in range(2,128):struct.pack_into('<i',s,0x4cc+j*4,4096)
            yield 'lookahead-capture',s,bytearray(RAM_SIZE),samples,dict(seed=seed,samples=samples)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('library',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    original=OriginalDSP(args.exe);original.uc.mem_map(RAM,RAM_SIZE)
    accesses=[]
    def memory(u,kind,address,size,value,data):
        accesses.append(dict(kind='write' if kind==UC_MEM_WRITE else 'read',offset=address-RAM,size=size,
                            value=value if kind==UC_MEM_WRITE else int.from_bytes(u.mem_read(address,size),'little')))
    original.uc.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,memory,begin=RAM,end=RAM+RAM_SIZE-1)
    lib=C.CDLL(str(args.library.resolve()))
    lib.scsp_dsp_sequence_probe.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint]
    lib.scsp_dsp_recovered_probe.argtypes=lib.scsp_dsp_sequence_probe.argtypes
    counts=collections.Counter();bad=collections.Counter();rows=[];digest=hashlib.sha256()
    recovered_bad=[];recovered_digest=hashlib.sha256();sample_calls=0
    for group,s,ram,samples,params in fixtures():
        sample_calls+=samples
        original.uc.mem_write(RAM,bytes(ram));codehash=original.prepare(s);accesses.clear()
        for _ in range(samples):native=original.step()
        native_ram=bytes(original.uc.mem_read(RAM,RAM_SIZE))
        inp=(C.c_uint8*len(s)).from_buffer_copy(s);out=(C.c_uint8*len(s))()
        port_ram=(C.c_uint8*RAM_SIZE).from_buffer_copy(ram)
        assert lib.scsp_dsp_sequence_probe(inp,out,port_ram,RAM_SIZE,samples)==1
        portable=bytes(out);portable_ram=bytes(port_ram)
        recovered=(C.c_uint8*len(s))();recovered_ram=(C.c_uint8*RAM_SIZE).from_buffer_copy(ram)
        assert lib.scsp_dsp_recovered_probe(inp,recovered,recovered_ram,RAM_SIZE,samples)==1
        rec=bytes(recovered);rec_ram=bytes(recovered_ram);rec_diff=[]
        for name,offset,length in FIELDS+[('scratch',0x7bc,44),('RAM',0,RAM_SIZE)]:
            a,b=(native_ram,rec_ram) if name=='RAM' else (native[offset:offset+length],rec[offset:offset+length])
            recovered_digest.update(a+b)
            if a!=b:
                at=next(i for i in range(length) if a[i]!=b[i]);start=at&~3
                rec_diff.append(dict(field=name,offset=at,original=a[start:start+4].hex(),recovered=b[start:start+4].hex()))
        if rec_diff:recovered_bad.append(dict(group=group,parameters=params,differences=rec_diff))
        differences=[]
        for name,offset,length in FIELDS+[('RAM',0,RAM_SIZE)]:
            a,b=(native_ram,portable_ram) if name=='RAM' else (native[offset:offset+length],portable[offset:offset+length])
            digest.update(a+b)
            if a!=b:
                at=next(i for i in range(length) if a[i]!=b[i]);start=at&~3
                differences.append(dict(field=name,offset=at,original=a[start:start+4].hex(),portable=b[start:start+4].hex()))
        if group=='address':
            addr=8191+(params['dec'] if not params['table'] else 0)+params['nxadr']
            addr&=65535 if params['table'] else 8191
            addr=(addr+params['rbp']*4096)*2
            assert [x['offset'] for x in accesses]==[addr]
        counts[group]+=1
        if differences:bad[group]+=1
        rows.append(dict(group=group,parameters=params,differences=differences,accesses=accesses.copy(),
                         original_mems7=struct.unpack_from('<i',native,0x6cc+28)[0],
                         portable_mems7=struct.unpack_from('<i',portable,0x6cc+28)[0],generated_sha256=codehash))
    report=dict(cases=sum(counts.values()),sample_calls=sample_calls,groups=dict(counts),mismatches=sum(bad.values()),
                mismatch_groups=dict(bad),result_sha256=digest.hexdigest(),rows=rows,
                recovered_mismatches=len(recovered_bad),recovered_failures=recovered_bad,
                recovered_result_sha256=recovered_digest.hexdigest(),
                original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),
                limits=['Synthetic state; no game program or final PCM.',
                        'Original x86 under Unicorn; portable loop unchanged.',
                        'Input-representation cases deliberately compare raw fields, not normalized mixer units.',
                'Differences from MAME are not automatically errors in ElSemi; reconstruction preserves native behavior.'])
    report['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path('port/snd/test/scsp_dsp_recovered.c'),Path('port/snd/test/scsp_dsp_shim.c'),Path('port/snd/scsp.c')]}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('cases','groups','mismatches','mismatch_groups','recovered_mismatches')},indent=2))

    return bool(recovered_bad)

if __name__=='__main__':sys.exit(main())
