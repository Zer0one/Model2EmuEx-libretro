#!/usr/bin/env python3
"""Seventeen original memory/branch wrappers vs C, using synthetic bus callbacks.

The bus is an identical deterministic fixture on each side, NOT a reconstructed
board. Compare callback order/arguments, all words, PC and decoded-record offset.
"""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW, UC_X86_REG_FPSW, UC_X86_REG_FPTAG)
from difftest_bits import load_original, EXE_SHA256, STOP, SP
from difftest_integer import ENTRIES, EDGES
from difftest_condition import ARENA, SIZE, STATUS, RECORD, STOP_FLAG, P32, put, pointer, FLAG_MASK

from difftest_compute import Context,WORD,DIAG
from difftest_fp import FP,ENTRIES as FP_SIMPLE,ARITHMETIC,SCALING
SUPPORTED=C.CFUNCTYPE(C.c_bool,C.c_void_p,C.c_uint32)
RUN=C.CFUNCTYPE(C.c_bool,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,P32,P32)
class Operation(C.Structure):_fields_=[('opaque',C.c_void_p),('supported',SUPPORTED),('run',RUN)]
READ, WRITE = STOP + 0x100, STOP + 0x200
HANDLERS = (0x4bd810, 0x4bd890, 0x4bd910, 0x4bd990, 0x4bddb0, 0x4bde20, 0x4bdea0, 0x4bdf20,
            0x4bdad0,0x4bdb10,0x4bdb60,0x4bdbb0,0x4bdc00,0x4bdc60,0x4bdcb0,0x4bdd00,0x4bdd50)
READ_FN = C.CFUNCTYPE(C.c_uint32, C.c_void_p, C.c_uint32)
WRITE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32, C.c_uint32)


class Record(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in ('condition','operation','immediate','flags')] + [
        (n, P32 * 2) for n in ('address','step','data','mirror')] + [
        (n, P32) for n in ('lhs','rhs','destination')]


class Bus(C.Structure):
    _fields_ = [('read',READ_FN),('write',WRITE_FN),('opaque',C.c_void_p)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path)
    ap.add_argument('libraries',type=Path,nargs='+')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--transfers',action='store_true')
    ap.add_argument('--backend',action='store_true')
    ap.add_argument('--bindings',action='store_true')
    args=ap.parse_args()
    if args.backend and args.transfers:ap.error('Select one suite')
    if args.bindings and not (args.backend or args.transfers):ap.error('--bindings requires --backend or --transfers')
    mu=load_original(args.exe)
    mu.mem_map(ARENA,0x1000)
    mu.mem_write(READ,b'\xc3')
    mu.mem_write(WRITE,b'\xc3')
    table=struct.unpack('<32I',mu.mem_read(0x573490,128))
    for a,v in ((0x5aeb40,ARENA),(0x528bc0,ARENA+STATUS),(0x5aeb38,ARENA),
                (0x5aeb3c,READ),(0x5aeb48,WRITE)):
        mu.mem_write(a,struct.pack('<I',v))
    libs=[]
    for path in args.libraries:
        lib=C.CDLL(str(path.resolve()))
        fn=lib.m2_sharc_dispatch_memory
        fn.argtypes=[C.c_uint32,C.POINTER(Record),C.POINTER(Bus),C.c_uint32,C.c_uint32,P32,P32,P32,P32]
        fn.restype=C.c_bool
        if args.transfers:
            transfer=lib.m2_sharc_transfer
            transfer.argtypes=[C.c_uint32,C.POINTER(Record),C.POINTER(Bus),P32]
            transfer.restype=C.c_bool
            def fn(handler,r,b,flags,loop,status,stop,pc,offset,transfer=transfer):
                return transfer(handler,r,b,status)
        if args.backend:
            fn=lib.m2_sharc_dispatch_memory_ex
            fn.argtypes=[C.c_uint32,C.POINTER(Record),C.POINTER(Bus),C.c_uint32,C.c_uint32,P32,P32,P32,P32,C.POINTER(Operation)]
            fn.restype=C.c_bool
            lib.m2_sharc_compute_hooks.argtypes=[C.POINTER(Context)];lib.m2_sharc_compute_hooks.restype=Operation
        if args.bindings:
            lib.m2_sharc_bind_memory.argtypes=[P32,WORD,C.c_void_p,C.POINTER(Record)];lib.m2_sharc_bind_memory.restype=C.c_bool
        libs.append((path,fn,lib))
    rng=random.Random(7)
    template=rng.randbytes(SIZE)
    original_events, flags_seen, writes, condition_seen=[],[],[],[]
    current={}
    preserved={UC_X86_REG_EBX:0xabcdef01,UC_X86_REG_ESI:0x12345678,
               UC_X86_REG_EDI:0x87654321,UC_X86_REG_EBP:0x5a5a5a5a}

    def bus_effect(events,address,value,load,store):
        result=((address ^ 0xa55a5aa5)+len(events)*0x1020304)&0xffffffff
        events.append(('R',address,result) if value is None else ('W',address,value))
        if current['mutate']:
            # Native callbacks may affect registers used by later transfers.
            for offset, delta in ((current['steps'][0],0x80000001),
                                  (current['steps'][1],7),(current['data'][0],0x55555555)):
                store(offset,(load(offset)+delta)&0xffffffff)
        return result

    def original_hook(uc,address,size,user):
        if address in (0x4bdada,0x4bdb1a,0x4bdb6a,0x4bdbba,0x4bdc0a,0x4bdc6a,0x4bdcba,0x4bdd0a,0x4bdd5a):
            condition_seen.append(uc.reg_read(UC_X86_REG_EAX))
        if address==current['compute']:
            flags_seen.append(uc.reg_read(UC_X86_REG_EFLAGS)&FLAG_MASK)
        if address in (READ,WRITE):
            value=None if address==READ else uc.reg_read(UC_X86_REG_EDX)
            result=bus_effect(original_events,uc.reg_read(UC_X86_REG_ECX),value,
                lambda o:struct.unpack('<I',uc.mem_read(ARENA+o,4))[0],
                lambda o,v:uc.mem_write(ARENA+o,struct.pack('<I',v)))
            uc.reg_write(UC_X86_REG_EAX,result)
            # A volatile flag result from the fixture must not leak backwards
            # into compute; transfers in these eight handlers follow compute.
            uc.reg_write(UC_X86_REG_EFLAGS,0x8c7)

    mu.hook_add(UC_HOOK_CODE,original_hook)
    mu.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,a,s,v,u:writes.append((a,s)))
    # address0/1, step0/1, data0/1, lhs/rhs/result. Native mirror locations
    # remain within the arena for every layout, including ASTAT aliases.
    layouts=[(0x400,0x404,0x408,0x40c,0x500,0x504,0x510,0x514,0x518),
             (0x400,0x404,0x408,0x40c,0x500,0x504,STATUS,0x514,0x500),
             (0x400,0x404,0x408,0x40c,0x500,0x504,0x510,STATUS,0x400),
             (0x400,0x400,0x408,0x40c,0x500,0x504,0x510,0x514,0x408),
             (0x400,0x404,0x500,0x504,0x500,0x504,0x510,0x514,STATUS),
             (0x500,0x504,0x408,0x40c,0x500,0x504,0x510,0x514,0x518),
             (0x400,0x404,0x408,0x40c,STATUS,0x504,0x510,0x514,0x518),
             (0x400,0x404,0x408,0x40c,0x500,0x500,0x510,0x514,0x500)]
    counts={}
    flag_values=[2|(i&1)|((i&2)<<1)|((i&4)<<4)|((i&8)<<4)|((i&16)<<7) for i in range(32)]
    handlers=(0x4bca50,0x4bca80,0x4bcab0,0x4bcac0,0x4bd540,0x4bd650,0x4bd680,0x4bd6a0,0x4bd6c0,0x4bd6e0) if args.transfers else HANDLERS
    operations={entry:(entry,name) for op,(entry,name) in ENTRIES.items()} if args.backend else ENTRIES
    if args.backend:operations.update({entry:(entry,f'FP_{entry:x}') for entry in FP_SIMPLE+ARITHMETIC+SCALING})
    for handler in handlers:
        count=0
        conditional=handler<0x4bddb0 and not args.transfers
        for op,(compute,name) in ([(1,ENTRIES[1])] if args.transfers else operations.items()):
            for code in ((0,9,16,30) if args.backend and conditional else range(32) if conditional else (0,)):
                active_layouts=[layouts[i] for i in (0,3,4,6)] if args.backend and name.startswith('FP_') else layouts
                for li,layout in enumerate(active_layouts):
                    for phase in range(4 if conditional else 8 if args.backend else 32):
                        data=bytearray(template)
                        for off in range(0x400,0x520,4):put(data,off,EDGES[rng.randrange(len(EDGES))])
                        status=(0,0xffffffff,rng.getrandbits(32),1<<(code%16))[phase%4]
                        loop=(0,1,2,0xffffffff)[phase%4]
                        stop=(0,1,7)[phase%3]
                        host_flags=flag_values[(phase+li*4)%32]
                        immediate=EDGES[(li+phase)%len(EDGES)]
                        if args.backend and name.startswith('FP_'):
                            for off in range(0x400,0x520,4):put(data,off,0x3f800000+(rng.randrange(8)<<20))
                            if compute in SCALING:put(data,layout[7],(phase-2)&0xffffffff)
                        put(data,STATUS,status);put(data,0x18,loop)
                        put(data,RECORD,handler);put(data,RECORD+4,compute);put(data,RECORD+8,table[code])
                        put(data,RECORD+0x1c,immediate);put(data,RECORD+0x2c,phase%4)
                        for field,off in zip((0xc,0x14,0x10,0x18,0x24,0x28,0x34,0x38,0x3c),layout):
                            put(data,RECORD+field,ARENA+off)
                        current.update(compute=compute,mutate=bool(phase&1),steps=layout[2:4],data=layout[4:6])
                        mu.mem_write(ARENA,bytes(data));mu.mem_write(STOP_FLAG,struct.pack('<I',stop))
                        mu.mem_write(0x5aeb10,struct.pack('<I',ARENA+RECORD))
                        mu.mem_write(SP-64,bytes(64)+struct.pack('<I',STOP))
                        for reg,v in preserved.items():mu.reg_write(reg,v)
                        mu.reg_write(UC_X86_REG_ESP,SP);mu.reg_write(UC_X86_REG_EFLAGS,host_flags)
                        if args.backend:
                            mu.reg_write(UC_X86_REG_FPCW,0x7f);mu.reg_write(UC_X86_REG_FPSW,0);mu.reg_write(UC_X86_REG_FPTAG,0xffff)
                        original_events.clear();flags_seen.clear();writes.clear();condition_seen.clear()
                        mu.emu_start(handler,STOP,count=300)
                        if mu.reg_read(UC_X86_REG_EIP)!=STOP or mu.reg_read(UC_X86_REG_ESP)!=SP+4:
                            raise AssertionError('Original did not return cleanly')
                        if any(mu.reg_read(reg)!=v for reg,v in preserved.items()):raise AssertionError('Preserved register changed')
                        allowed={ARENA+o for o in (STATUS,8,*layout[:6],layout[8],layout[4]-128,layout[5]-128)}|{STOP_FLAG,0x5aeb10}
                        if any(not(SP-64<=a and a+s<=SP) and (s!=4 or a not in allowed and not (args.backend and a in (0x528bc4,0x528bc8,0x528bcc))) for a,s in writes):
                            raise AssertionError(f'Unexpected writes {writes}')
                        if bytes(mu.mem_read(SP,4))!=struct.pack('<I',STOP):raise AssertionError('Return address changed')
                        expected=bytes(mu.mem_read(ARENA,SIZE))
                        expected_stop=struct.unpack('<I',mu.mem_read(STOP_FLAG,4))[0]
                        expected_offset=(struct.unpack('<I',mu.mem_read(0x5aeb10,4))[0]-ARENA)&0xffffffff
                        expected_flags=(4 if (condition_seen[0]&255).bit_count()%2==0 else 0) if condition_seen else (0x44 if conditional else host_flags&FLAG_MASK)
                        if flags_seen and flags_seen!=[expected_flags]:
                            raise AssertionError(f'Unexpected compute flags {flags_seen}')
                        for path,fn,lib in libs:
                            native=(C.c_uint32*(SIZE//4)).from_buffer_copy(data)
                            events=[]
                            def access(addr,value=None):
                                return bus_effect(events,addr,value,lambda o:native[o//4],lambda o,v:native.__setitem__(o//4,v))
                            read=READ_FN(lambda _,a:access(a))
                            write=WRITE_FN(lambda _,a,v:access(a,v))
                            bus=Bus(read,write,None)
                            rec=Record(code,op,immediate,phase%4)
                            for field,offsets in (('address',layout[:2]),('step',layout[2:4]),('data',layout[4:6]),
                                                  ('mirror',(layout[4]-128,layout[5]-128))):
                                setattr(rec,field,(P32*2)(*(pointer(native,o) for o in offsets)))
                            rec.lhs,rec.rhs,rec.destination=(pointer(native,o) for o in layout[6:])
                            nstop,offset=C.c_uint32(stop),C.c_uint32(RECORD)
                            extra=()
                            if args.backend:
                                fp=FP(0x7f,0);record_token=C.c_uint32(ARENA+RECORD)
                                word=WORD(lambda opaque,token:C.addressof(native)+token-ARENA)
                                diagnostic=DIAG(lambda opaque,fmt,pc:None)
                                context=Context(None,word,diagnostic,pointer(native,STATUS),pointer(native,8),pointer(native,0x18),C.pointer(nstop),C.pointer(record_token),C.pointer(fp))
                                operation=lib.m2_sharc_compute_hooks(C.byref(context));extra=(C.byref(operation),)
                            if args.bindings:
                                word=WORD(lambda opaque,t:C.addressof(native)+t-ARENA if ARENA<=t<ARENA+SIZE else None)
                                rec=Record()
                                if not lib.m2_sharc_bind_memory(pointer(native,RECORD),word,None,C.byref(rec)):raise AssertionError('Record binding')
                            ok=fn(handler,C.byref(rec),C.byref(bus),host_flags,loop,pointer(native,STATUS),
                                  C.byref(nstop),pointer(native,8),C.byref(offset),*extra)
                            if args.backend and (fp.status^mu.reg_read(UC_X86_REG_FPSW))&~0x23f:raise AssertionError("FP comparison/stack wiring")
                            if not ok or bytes(native)!=expected or nstop.value!=expected_stop or offset.value!=expected_offset or events!=original_events:
                                diffs=[hex(i*4) for i in range(SIZE//4) if bytes(native)[i*4:i*4+4]!=expected[i*4:i*4+4]]
                                raise AssertionError(f'{path.name} {handler:x}/{name}/cond{code}/layout{li}/phase{phase}: '
                                  f'diffs={diffs}, events={events}/{original_events}, offset={offset.value:x}/{expected_offset:x}')
                        count+=1
        counts[f'0x{handler:08x}']=count
        print(f'{handler:08x}: {count} passed',flush=True)
    # Unsupported dispatch rejects before dereferencing null bindings/callbacks.
    for path,fn,lib in libs:
        extra=()
        if args.backend:
            fp=FP(0x7f,0);context=Context();context.fp=C.pointer(fp)
            operation=lib.m2_sharc_compute_hooks(C.byref(context));extra=(C.byref(operation),)
        for handler,op,code in (((0,1,0),) if args.transfers else ((0,1,0),(HANDLERS[0],0,0),(HANDLERS[0],1,32))):
            rec=Record(code,op,0,0);bus=Bus();words=[C.c_uint32(x) for x in (0xffffffff,7,8,9)]
            if fn(handler,C.byref(rec),C.byref(bus),2,0,*(C.byref(x) for x in words),*extra) or [x.value for x in words]!=[0xffffffff,7,8,9]:
                raise AssertionError('Unsupported dispatch mutated state')
    root=Path(__file__).resolve().parents[1]
    sources=[root/n for n in (('sharc_transfer.c','sharc_transfer.h','sharc_memory.h') if args.transfers else ('sharc_memory.c','sharc_memory.h','sharc_condition.c','sharc_integer.c','sharc_flow.c'))]
    if args.backend or args.bindings:sources += [p for p in root.glob('sharc_*.c') if p not in sources]
    receipt={'status':'passed','scope':('17 wrappers with complete compute backend' if args.backend else '10 transfer primitives' if args.transfers else '17 wrappers')+'; synthetic bus, no board integration',
      'exe_sha256':EXE_SHA256,'unicorn':unicorn.__version__,'seed':7,'entries':counts,
      'cases':sum(counts.values()),'mismatches':0,'skipped':0,'raw_record_binding':args.bindings,
      'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
      'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'libraries':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,fn,lib in libs]}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print('Total:',receipt['cases'])


if __name__=='__main__':main()
