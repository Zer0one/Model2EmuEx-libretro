#!/usr/bin/env python3
"""Focused qualification of read-return scratch through existing A68K bodies.

Invoked by a68k_loop_compare.py --memory-reads. Instruction arithmetic is not
requalified: each newly connected target gets one source/EA shape, with two
callback control-flag states and uninterrupted versus single-step dispatch.
"""
import ctypes as C
import hashlib
import json
import re
from a68k_sequence_compare import ChainOracle,ROOT,WORDS,words
from a68k_boundary_compare import CTX,READ,DATA,CALL,RAM
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_EFLAGS


class ReadOracle(ChainOracle):
    def __init__(self,exe):
        super().__init__(exe)
        self.read_value=0x12348081;self.read_edx=0x602;self.read_xor=0;self.read_events=[];self.read_script=[]
        for kind,base in enumerate((DATA,READ)):
            self.put(base,*([0,*[CALL+160+kind*48+i*16 for i in range(3)]]*4096))
    def configure_bus(self):
        super().configure_bus()
        self.put(0x572a88,0x4b3250,0x4b3220,0x4b31f0)
        self.put(0x572aa4,0x4b31c0,0x4b3190,0x4b3160)
        self.read_events=[]
    def hook(self,u,at,size,data):
        if CALL+160<=at<CALL+256:
            kind=(at-CALL-160)//48
            self.read_events.append([u.reg_read(UC_X86_REG_ECX),kind,self.get(CTX+80)[0],self.get(CTX+72)[0]])
            self.ret(self.read_script[len(self.read_events)-1] if len(self.read_events)<=len(self.read_script) else self.read_value);u.reg_write(UC_X86_REG_EDX,self.read_edx)
            u.reg_write(UC_X86_REG_EFLAGS,u.reg_read(UC_X86_REG_EFLAGS)^self.read_xor)
            return
        super().hook(u,at,size,data)


def specs(rmw=False,misc=False,bulk=False,control=False):
    records=[]
    if control:
        for t,bits,cost,mode in re.findall(r'A68K_ADDRESS\((0x[0-9a-f]+), \w+, (\d+), (\d+), (\w+)\)',(ROOT/'port/a68k/address_ops.inc').read_text()):
            records.append((int(t,16),int(bits),int(cost),mode,None,('link',0x1023) if int(t,16)==0x488608 else 0))
        for t,cc in re.findall(r'A68K_CONTROL\((0x[0-9a-f]+), DBCC, (\d+)\)',(ROOT/'port/a68k/control_ops.inc').read_text()):
            cc=int(cc);outcomes={}
            for flags in range(16):
                c,z,n,v=[bool(flags&(1<<bit)) for bit in range(4)]
                take=(True,False,not(c or z),c or z,not c,c,not z,z,not v,v,not n,n,n==v,n!=v,not z and n==v,z or n!=v)[cc]
                outcomes.setdefault(take,2|int(c)|(int(z)<<6)|(int(n)<<7)|(int(v)<<11))
            for flags in outcomes.values():
                for counter in (0,1):records.append((int(t,16),16,0,'NONE',None,('condition',flags,counter)))
        # Only shared EA-observation helper refactor: retain representative
        # empty MOVEM displacement/index checks, not its whole old matrix.
        for target in (0x4878d8,0x487958,0x4880f0,0x488168):
            mode={0x4878d8:'DISP16',0x487958:'INDEXED',0x4880f0:'PCDISP',0x488168:'PCINDEX'}[target]
            records.append((target,16,0,mode,None,('mask',0)))
        return records
    if bulk:
        for file in ('memory_sequence_ops.inc','movem_ops.inc'):
            for line in (ROOT/'port/a68k'/file).read_text().splitlines():
                match=re.match(r'A68K_(MOVEP|CMPM|MOVEM)\(([^)]+)\)',line)
                if not match:continue
                macro,fields=match[1],match[2].split(', ');target=int(fields[0],16)
                if macro=='MOVEM':
                    for mask in (0,1,0xa581,0xffff):records.append((target,int(fields[1]),int(fields[3]),fields[4],None,('mask',mask)))
                elif macro=='MOVEP':records.append((target,int(fields[1])*8,0,'DISP16',None,0))
                else:records.append((target,int(fields[1]),0,'NONE',None,0))
        return records
    if misc:
        for file,macro in (('bit_ops.inc','BIT'),('shift_memory_ops.inc','SHIFT_MEMORY'),
                           ('bcd_memory_ops.inc','BCD_MEMORY'),('extend_memory_ops.inc','EXTEND_MEMORY')):
            for line in (ROOT/'port/a68k'/file).read_text().splitlines():
                match=re.match(r'A68K_'+macro+r'\(([^)]+)\)',line)
                if not match:continue
                fields=match[1].split(', ');target=int(fields[0],16);immediate=0
                if macro in ('BIT','SHIFT_MEMORY'):
                    bits,cost,source=fields[2:5]
                    if source=='REGISTER':continue
                    immediate=int(fields[-1]=='IMMEDIATE_LOW')
                elif macro=='BCD_MEMORY':bits,cost,source=8,18,'NONE'
                else:bits,cost=fields[2:];source='NONE'
                records.append((target,int(bits),int(cost),source,None,immediate))
        return records
    if rmw:
        for file,macro in (('memory_dest_ops.inc','MEMORY_DEST'),('memory_operand_ops.inc','MEMORY_OPERAND'),
                           ('memory_unary_ops.inc','MEMORY_UNARY'),('memory_scratch_ops.inc','MEMORY_SCRATCH')):
            for line in (ROOT/'port/a68k'/file).read_text().splitlines():
                match=re.match(r'A68K_'+macro+r'\(([^)]+)\)',line)
                if not match:continue
                fields=match[1].split(', ');target=int(fields[0],16)
                bits,cost,source=fields[2:5]
                immediate=(2 if int(bits)==32 else 1) if fields[-1]=='IMMEDIATE_LOW' else 0
                records.append((target,int(bits),int(cost),source,None,immediate))
        return records
    for file,macro in (('memory_move_ops.inc','MEMORY_MOVE'),('memory_binary_ops.inc','MEMORY_BINARY'),
                       ('memory_address_ops.inc','MEMORY_ADDRESS'),('move_memory_ops.inc','MOVE_MEMORY'),
                       ('multiply_ops.inc','MULTIPLY')):
        for line in (ROOT/'port/a68k'/file).read_text().splitlines():
            match=re.match(r'A68K_'+macro+r'\(([^)]+)\)',line)
            if not match:continue
            fields=match[1].split(', ');target=int(fields[0],16)
            if macro=='MEMORY_MOVE':bits,cost,source=fields[1:];destination=None
            elif macro in ('MEMORY_BINARY','MEMORY_ADDRESS'):bits,cost,source=fields[2:];destination=None
            elif macro=='MOVE_MEMORY':bits,cost,source,destination=fields[1:]
            else:
                cost,source=fields[2:];bits=16;destination=None
                if source in ('REGISTER','IMMEDIATE'):continue
            records.append((target,int(bits),int(cost),source,destination,0))
    return records


def extension(mode):
    if mode=='IMMEDIATE':return [0x8981]
    if mode in ('DISP16','INDEXED','ABS16','PCDISP','PCINDEX'):return [0x1023]
    if mode=='ABS32':return [0x0012,0x3456]
    return []


def compare(exe,lib,rmw=False,misc=False,bulk=False,control=False):
    o=ReadOracle(exe);p=C.CDLL(str(lib));fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    records=specs(rmw,misc,bulk,control);targets={t for t,*_ in records};digest=hashlib.sha256();cases=0
    if control:targets-={0x4878d8,0x487958,0x4880f0,0x488168}
    for target,bits,cost,source,destination,immediate in records:
        op=next(op for op,t in enumerate(o.table) if t==target)
        prefix=[2 if immediate[0]=='condition' else immediate[1]] if isinstance(immediate,tuple) else [0x89ab,0xcdef][:immediate]
        code=[(op,*prefix,*extension(source),*extension(destination)),0x4e71,0x50d1,0x72ff,0x4e71]
        program=words(code);ops=(C.c_uint16*len(program))(*program)
        for variant in (0,1):
            context=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
            context[20]=0x1000;context[17]=0x27;context[21]=0;context[18]=0x243;context[19]=1
            if isinstance(immediate,tuple) and immediate[0]=='condition':
                context[18]=immediate[1]|(0x400 if variant else 0);context[op&7]=0x12340000|immediate[2]
            o.read_xor=0x400 if variant else 0
            o.read_edx=0x602 if variant else 0xa43
            p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
            native,writes=o.stream(context,1000,0x89abcdef,0x202,code,False,0x87654321,0x400)
            for chunk in (1,128):
                data=(C.c_uint32*38)(*context,1000,0x89abcdef,0x202,0x87654321,0x400)
                out=(C.c_uint32*(2+WORDS+2*128))()
                assert fn(data,ops,len(program),len(code),chunk,out)
                actual=list(out[2:2+WORDS]);want=native[-1].copy();key=(hex(target),variant,chunk,immediate) if bulk or control else (hex(target),variant,chunk)
                assert out[0]==len(native)-1,(key,'steps',out[0],len(native)-1)
                assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                assert actual_writes==writes,(key,'writes',actual_writes,writes)
                reads=(C.c_uint32*(128*4))();count=p.a68k_probe_get_reads(reads)
                assert count<=128
                events=[list(reads[i*4:i*4+4]) for i in range(count)]
                assert events==o.read_events,(key,'reads',events,o.read_events)
                digest.update(json.dumps([key,actual,events,actual_writes]).encode());cases+=1
    wrappers=compare_wrappers(o,p) if not (rmw or misc or bulk or control) else 'Retained read-bridge receipts; no wrapper change in this group.'
    group='address_dbcc_connections' if control else 'bulk_memory_connections' if bulk else 'bit_shift_paired_connections' if misc else 'read_modify_write_connections' if rmw else 'read_return_connections'
    return dict(group=group,native_streams=len(records)*2,portable_comparisons=cases,
                new_scratch_targets=len(targets),new_scratch_encodings=sum(t in targets for t in o.table),
                read_wrappers=wrappers,
                mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'Only new read-return/control-flag connections; prior arithmetic and source correspondence retained.',
                    'Synthetic native/portable callbacks, including published context, EAX, EDX and host DF; actual board callbacks remain separate.',
                    'Direct wrapper results and malformed bindings are checked separately; not a complete CPU or frontend claim.'])


def compare_wrappers(o,p):
    fn=p.a68k_probe_read_live
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)]
    digest=hashlib.sha256();cases=0;guards=0
    original=bytes((i*37+11)&255 for i in range(8192))
    for kind,base,entries in ((0,DATA,(0x4b3250,0x4b3220,0x4b31f0)),(1,READ,(0x4b31c0,0x4b3190,0x4b3160))):
        for index,width in enumerate((1,2,4)):
            for direct in (False,True):
                for low in (1,0xfff):
                    address=0x123000+low;host=0x602 if direct else 0x202
                    o.put(base+(address>>12)*16,RAM-0x123000 if direct else 0,*[CALL+160+kind*48+i*16 for i in range(3)])
                    o.u.mem_write(RAM,original);o.read_xor=0x400;o.read_edx=0xa43
                    o.run(entries[index],{UC_X86_REG_ECX:address|0xab000000,UC_X86_REG_EFLAGS:host})
                    memory=(C.c_uint8*8192).from_buffer_copy(original);out=(C.c_uint32*8)()
                    data=(C.c_uint32*8)(width,1-kind,address|0xab000000,int(direct),o.read_value,o.read_edx,o.read_xor,host)
                    assert fn(data,memory,out)
                    assert out[0] and out[1]==out[4]==o.u.reg_read(UC_X86_REG_EAX),(kind,width,direct,low,list(out),hex(o.u.reg_read(UC_X86_REG_EAX)))
                    assert out[5]==o.u.reg_read(UC_X86_REG_EDX)
                    assert out[2]&~0x8d5==o.u.reg_read(UC_X86_REG_EFLAGS)&~0x8d5
                    assert out[3]==1 and out[6]==int(not direct) and not out[7] and bytes(memory)==original
                    digest.update(bytes(out));cases+=1
            for mode in (2,3,4,5):
                memory=(C.c_uint8*8192).from_buffer_copy(original);out=(C.c_uint32*8)()
                data=(C.c_uint32*8)(width,1-kind,0x123fff,mode,0x12345678,0xa43,0x400,0x202)
                assert fn(data,memory,out)
                assert list(out[:6])==[0,0xa5c3e791,0x202,1,0x11111111,0x22222222]
                assert out[6]==int(mode==5) and not out[7] and bytes(memory)==original
                guards+=1
    mapping=p.a68k_probe_read_mapping();assert mapping==3
    return dict(cases=cases,guards=guards+mapping,mismatches=0,result_sha256=digest.hexdigest())


class FlowOracle(ReadOracle):
    def configure_bus(self):
        super().configure_bus()
        self.put(READ+16,RAM-0x1000)
        self.put(0x572aa0,0x4b30a0)


def compare_flow(exe,lib,odd=False):
    o=FlowOracle(exe);p=C.CDLL(str(lib));p.a68k_probe_enable_binding()
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_set_irq.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8)]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    if odd:p.a68k_probe_set_irq(0,0,(C.c_uint8*256)(*o.cost))
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    records=[]
    for target,kind,cc in re.findall(r'A68K_CONTROL\((0x[0-9a-f]+), (BR_WORD|BR_BYTE), (\d+)\)',(ROOT/'port/a68k/control_ops.inc').read_text()):
        target=int(target,16);cc=int(cc)
        op=next(op for op,t in enumerate(o.table) if t==target and (kind=='BR_WORD' or op&255==2))
        outcomes={}
        for f in range(16):
            c,z,n,v=[bool(f&(1<<bit)) for bit in range(4)]
            take=(True,True,not(c or z),c or z,not c,c,not z,z,not v,v,not n,n,n==v,n!=v,not z and n==v,z or n!=v)[cc]
            outcomes.setdefault(take,2|int(c)|(int(z)<<6)|(int(n)<<7)|(int(v)<<11))
        for flags in outcomes.values():records.append((target,op,[2 if kind=='BR_WORD' else 0x4e71],flags,'BR'))
    for target,sub,cost,mode in re.findall(r'A68K_JUMP\((0x[0-9a-f]+), (\d+), (\d+), (\w+)\)',(ROOT/'port/a68k/jump_ops.inc').read_text()):
        target=int(target,16);op=o.table.index(target)
        ext={'INDIRECT':[],'DISP16':[0],'INDEXED':[0x0800],'ABS16':[0x1004],'ABS32':[0,0x1006],'PCDISP':[2],'PCINDEX':[0x0802]}[mode]
        records.append((target,op,ext,0x243,mode))
    digest=hashlib.sha256();cases=0;targets={r[0] for r in records}
    for target,op,ext,flags,mode in records:
        if odd:
            ext=ext.copy()
            if mode=='BR':
                if op&255:op+=1
                else:ext[0]+=1
            elif ext:ext[-1]+=1
        code=[(op,*ext),0x50d1,0x72ff,0x4e71,0x4e71];program=words(code)
        ops=(C.c_uint16*len(program))(*program)
        for variant in (0,1):
            c=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
            c[20]=0x1000;c[17]=0x27;c[21]=0;c[18]=flags|(0x400 if variant else 0);c[19]=1;c[0]=0
            c[8]=0x1002+2*len(ext)+(1 if odd and mode=='INDIRECT' else 0);c[32]=0xab001234
            if odd:
                c[29]=0x100;o.read_value=0x1002+2*len(ext);o.read_xor=0x400 if variant else 0
                p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
            if variant and mode in ('INDIRECT','DISP16','INDEXED'):c[8]|=0xab000000
            native,writes=o.stream(c,1000,0x89abcdef,0x202,code,False,0x87654321,0x400)
            for chunk in (1,128):
                data=(C.c_uint32*38)(*c,1000,0x89abcdef,0x202,0x87654321,0x400)
                out=(C.c_uint32*(2+WORDS+256))();assert fn(data,ops,len(program),len(code),chunk,out)
                actual=list(out[2:2+WORDS]);want=native[-1];key=(hex(target),flags,variant,chunk)
                assert out[0]==len(native)-1,(key,'steps')
                assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                assert actual_writes==writes,(key,actual_writes,writes)
                actual_reads=[]
                if odd:
                    reads=(C.c_uint32*512)();n=p.a68k_probe_get_reads(reads)
                    actual_reads=[list(reads[4*i:4*i+4]) for i in range(n)]
                    assert actual_reads==o.read_events,(key,'reads',actual_reads,o.read_events)
                digest.update(json.dumps([key,actual,actual_writes,actual_reads] if odd else [key,actual,actual_writes]).encode());cases+=1
    guards=p.a68k_probe_jump_guards();assert guards==2
    return dict(group='odd_branch_jump_connections' if odd else 'branch_jump_connections',native_streams=len(records)*2,portable_comparisons=cases,
                new_scratch_targets=0 if odd else len(targets),new_scratch_encodings=0 if odd else sum(t in targets for t in o.table),qualified_target_paths=len(targets),
                guards=guards,mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'Odd destinations enter original vector 3 with native target-minus-two saved PC.' if odd else 'Conditional/unconditional branches, BSR/JMP/JSR to even destinations; raw-PC aliases and stack return values preserved.',
                    'Native fetch binder 004b30a0 executes in the oracle; portable fixture supplies its explicit EAX/control observation.',
                    'Vector fetch returns an even target in this group; the approved odd-vector fatal prefix remains separate. No complete CPU/board/frontend claim.'])


class IRQOracle(FlowOracle):
    def __init__(self,exe):
        super().__init__(exe);self.ack_xor=0
    def hook(self,u,at,size,data):
        if at==CALL+64:
            self.ret(self.ack)
            u.reg_write(UC_X86_REG_EFLAGS,u.reg_read(UC_X86_REG_EFLAGS)^self.ack_xor)
            return
        super().hook(u,at,size,data)


def compare_irq(exe,lib):
    o=IRQOracle(exe);p=C.CDLL(str(lib));p.a68k_probe_enable_binding()
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_set_irq.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8)]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    costs=(C.c_uint8*256)(*o.cost);digest=hashlib.sha256();cases=native_runs=0
    code=[0x50d1,0x72ff,0x4e71];program=words(code);ops=(C.c_uint16*len(program))(*program)
    for level,sr in ((1,0),(1,0x20),(7,7),(7,0x27)):
        for vector in (-1,0x42,0x142):
            for variation in range(4):
                for budget in (1000,0xffffffff):
                    c=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
                    c[20]=0x1000;c[17]=sr;c[21]=0xa5c3e7f8|level;c[18]=0x643;c[19]=1
                    c[15]=0x123450;c[16]=0x234500;c[28]=0x456700;c[29]=0x100
                    o.ack=vector;o.ack_xor=0x400 if variation&1 else 0
                    o.read_value=0x1000;o.read_edx=0x89abcdef;o.read_xor=0x400 if variation&2 else 0
                    native,writes=o.stream(c,budget,0x89abcdef,0x202,code,False,0x87654321,0x400)
                    native_runs+=1;p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
                    p.a68k_probe_set_irq(vector&0xffffffff,o.ack_xor,costs)
                    for chunk in (1,128):
                        data=(C.c_uint32*38)(*c,budget,0x89abcdef,0x202,0x87654321,0x400)
                        out=(C.c_uint32*(2+WORDS+256))();assert fn(data,ops,len(program),len(code),chunk,out)
                        actual=list(out[2:2+WORDS]);want=native[-1].copy();key=(level,sr,vector,variation,budget,chunk)
                        if not actual[38]:want[36:38]=actual[36:38]
                        assert out[0]==len(native)-1,(key,'steps',out[0],len(native)-1)
                        assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                        actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                        assert actual_writes==writes,(key,'writes',actual_writes,writes)
                        reads=(C.c_uint32*512)();n=p.a68k_probe_get_reads(reads)
                        actual_reads=[list(reads[4*i:4*i+4]) for i in range(n)]
                        assert actual_reads==o.read_events,(key,'reads',actual_reads,o.read_events)
                        digest.update(json.dumps([key,actual,actual_writes,actual_reads]).encode());cases+=1
    guards=p.a68k_probe_sequence_guards();assert guards==7,guards
    return dict(group='accepted_irq_connections',native_streams=native_runs,portable_comparisons=cases,
                guards=guards,mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'Accepted IRQ enters the original exception body before budget testing; user/supervisor stacks, vector masking and callback DF covered.',
                    'Original EAX IRQ-level restoration feeds the next Scc; vector uses DATA-long and explicit native fetch-binder provenance.',
                    'Synthetic callback observations only. No real board/scheduler or complete CPU qualification.'])


class TrapOracle(FlowOracle):
    def hook(self,u,at,size,data):
        if at==0x48b568 and getattr(self,'skip_illegal_entry',False):
            # RTD's CPU gate tail-jumps to ILLEGAL without fetching another
            # guest opcode. Count one instruction, not two target entries.
            self.skip_illegal_entry=False;return
        super().hook(u,at,size,data)
    def configure_bus(self):
        super().configure_bus();self.limit=4


def compare_traps(exe,lib):
    o=TrapOracle(exe);p=C.CDLL(str(lib));p.a68k_probe_enable_binding()
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_set_irq.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8)]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    costs=(C.c_uint8*256)(*o.cost);p.a68k_probe_set_irq(0,0,costs)
    targets={0x486dd4,0x486e00,0x484a40,0x484a98,0x48b518,0x48b540,0x48b568}
    digest=hashlib.sha256();cases=native_runs=0
    for target in sorted(targets):
        op=o.table.index(target)
        for supervisor in (0,0x20):
            for overflow in (0,0x800):
                for variation in (0,1):
                    for budget in (0,34,1000):
                        c=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
                        c[20]=0x1000;c[17]=supervisor;c[21]=0;c[18]=0x643|overflow;c[19]=1
                        c[15]=0x123450;c[16]=0x234500;c[28]=0x456700;c[29]=0x100
                        code=[op,0x4e71,0x50d1,0x72ff,0x4e71,0x4e71];program=words(code);ops=(C.c_uint16*len(program))(*program)
                        o.read_value=0x1002;o.read_edx=0x89abcdef;o.read_xor=0x400 if variation else 0
                        native,writes=o.stream(c,budget,0x89abcdef,0x202,code,False,0x87654321,0x400)
                        native_runs+=1;p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
                        for chunk in (1,128):
                            data=(C.c_uint32*38)(*c,budget,0x89abcdef,0x202,0x87654321,0x400)
                            out=(C.c_uint32*(2+WORDS+256))();assert fn(data,ops,len(program),4,chunk,out)
                            actual=list(out[2:2+WORDS]);want=native[-1].copy();key=(hex(target),supervisor,overflow,variation,budget,chunk)
                            if not actual[38]:want[36:38]=actual[36:38]
                            assert out[0]==len(native)-1,(key,'steps',out[0],len(native)-1)
                            assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                            actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                            assert actual_writes==writes,(key,'writes',actual_writes,writes)
                            reads=(C.c_uint32*512)();n=p.a68k_probe_get_reads(reads)
                            actual_reads=[list(reads[4*i:4*i+4]) for i in range(n)]
                            assert actual_reads==o.read_events,(key,'reads',actual_reads,o.read_events)
                            digest.update(json.dumps([key,actual,actual_writes,actual_reads]).encode());cases+=1
    guards=p.a68k_probe_sequence_guards();assert guards==7,guards
    return dict(group='software_exception_connections',native_streams=native_runs,portable_comparisons=cases,
                new_scratch_targets=len(targets),new_scratch_encodings=sum(t in targets for t in o.table),
                guards=guards,mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'TRAP/TRAPV, Line A/F, generic ILLEGAL and USP transfers: only exception/privilege/next-entry connections tested.',
                    'Native JS versus JLE budget exits and saved-PC adjustment preserved; existing instruction bodies reused.',
                    'Synthetic callbacks and even exception vectors. No complete CPU or board qualification.'])


def compare_returns(exe,lib):
    o=TrapOracle(exe);p=C.CDLL(str(lib));p.a68k_probe_enable_binding()
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_set_irq.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8)]
    p.a68k_probe_set_read_script.argtypes=[C.POINTER(C.c_uint32),C.c_uint]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    costs=(C.c_uint8*256)(*o.cost);p.a68k_probe_set_irq(0xffffffff,0,costs)
    # Connection shapes only: no exhaustive SR/arithmetic matrix.
    records=[]
    for odd in (0,1):
        records.extend([(0x4e75,0x27,0,1,0,odd),(0x4e77,0x27,0,1,0xaabb001b,odd),
                        (0x4e74,0x27,0,1,0,odd)])
        for sr in (0x001f,0x2015,0x271b):
            for irq in (0,1):records.append((0x4e73,0x27,irq,1,sr,odd))
    records.extend([(0x4e73,7,0,1,0,0),(0x4e74,0x27,0,0,0,0)])
    digest=hashlib.sha256();cases=native_runs=0;targets=set()
    for op,initial_sr,irq,later,sr,odd in records:
        target=o.table[op];targets.add(target)
        for variation in (0,1):
            for budget in (0,34,1000):
                c=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
                c[20]=0x1000;c[17]=initial_sr;c[21]=irq;c[18]=0x643;c[19]=0x123401
                c[15]=0x123450;c[16]=0x234500;c[28]=0x456700;c[29]=0x100;c[31]=later
                code=[op,0x4e71,0x50d1,0x72ff,0x4e71,0x4e71];program=words(code);ops=(C.c_uint16*len(program))(*program)
                o.read_value=0x1002;o.read_edx=0x89abcdef;o.read_xor=0x400 if variation else 0
                if (op==0x4e73 and not(initial_sr&0x20)) or (op==0x4e74 and not later):o.read_script=[]
                else:o.read_script=([sr] if op in (0x4e73,0x4e77) else [])+[0x1002+odd]
                o.skip_illegal_entry=op==0x4e74 and not later
                native,writes=o.stream(c,budget,0x89abcdef,0x202,code,False,0x87654321,0x400)
                native_runs+=1;p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
                p.a68k_probe_set_read_script((C.c_uint32*len(o.read_script))(*o.read_script),len(o.read_script))
                for chunk in (1,128):
                    data=(C.c_uint32*38)(*c,budget,0x89abcdef,0x202,0x87654321,0x400)
                    out=(C.c_uint32*(2+WORDS+256))();assert fn(data,ops,len(program),4,chunk,out)
                    actual=list(out[2:2+WORDS]);want=native[-1].copy();key=(hex(op),initial_sr,irq,later,sr,odd,variation,budget,chunk)
                    if not actual[38]:want[36:38]=actual[36:38]
                    assert out[0]==len(native)-1,(key,'steps',out[0],len(native)-1)
                    assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                    actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                    assert actual_writes==writes,(key,'writes',actual_writes,writes)
                    reads=(C.c_uint32*512)();n=p.a68k_probe_get_reads(reads)
                    actual_reads=[list(reads[4*i:4*i+4]) for i in range(n)]
                    assert actual_reads==o.read_events,(key,'reads',actual_reads,o.read_events)
                    digest.update(json.dumps([key,actual,actual_writes,actual_reads]).encode());cases+=1
    guards=p.a68k_probe_sequence_guards();assert guards==7,guards
    return dict(group='return_connections',native_streams=native_runs,portable_comparisons=cases,
                new_scratch_targets=len(targets),new_scratch_encodings=sum(t in targets for t in o.table),
                guards=guards,mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'RTS/RTR/RTE/RTD stack reads, status restoration, RTE privilege/IRQ masking and acceptance, odd return vector 3 and RTD CPU gating.',
                    'Original RTD reads its displacement at the opcode; this behavior is retained. No general opcode/SR matrix rerun.',
                    'Synthetic callback provenance; no complete CPU or sound-board integration.'])


def compare_status(exe,lib):
    o=TrapOracle(exe);p=C.CDLL(str(lib));p.a68k_probe_enable_binding()
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_set_irq.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8)]
    p.a68k_probe_set_read_script.argtypes=[C.POINTER(C.c_uint32),C.c_uint]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    p.a68k_probe_set_irq(0xffffffff,0,(C.c_uint8*256)(*o.cost))
    specs=[];text=(ROOT/'port/a68k/status_ops.inc').read_text()
    for target,operation,cost,mode in re.findall(r'A68K_STATUS_MOVE\((0x[0-9a-f]+), (\w+), (\d+), (\w+)\)',text):
        specs.append((int(target,16),operation,mode,operation=='TO_SR'))
    for target,operation,full in re.findall(r'A68K_STATUS_LOGIC\((0x[0-9a-f]+), (\w+), (\d+)\)',text):
        specs.append((int(target,16),operation,'LOGIC',int(full)))
    digest=hashlib.sha256();cases=native_runs=0;targets={r[0] for r in specs}
    for target,operation,mode,full in specs:
        op=o.table.index(target);scenarios=[(0x27,0,1)]
        if full:scenarios.extend([(7,0,1),(0x27,1,1)])
        if operation=='FROM_CCR':scenarios.append((0x27,0,0))
        ext=extension(mode)
        value=0x2005
        if mode=='IMMEDIATE':ext=[value]
        if mode=='LOGIC':ext=[{'OR':0x0015,'AND':0x20ff,'EOR':0x0715}[operation]]
        code=[(op,*ext),0x4e71,0x50d1,0x72ff,0x4e71,0x4e71];program=words(code);ops=(C.c_uint16*len(program))(*program)
        for sr,irq,later in scenarios:
            for variation in (0,1):
                c=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
                c[20]=0x1000;c[17]=sr;c[21]=irq;c[18]=0x643;c[19]=0x123401
                c[15]=0x123450;c[16]=0x234500;c[28]=0x456700;c[29]=0x100;c[31]=later;c[0]=value
                o.read_value=0x1002+2*len(ext);o.read_edx=0x89abcdef;o.read_xor=0x400 if variation else 0
                o.read_script=[value] if operation in ('TO_CCR','TO_SR') and mode not in ('REGISTER','IMMEDIATE') and (not full or sr&0x20) else []
                o.skip_illegal_entry=operation=='FROM_CCR' and not later
                native,writes=o.stream(c,1000,0x89abcdef,0x202,code,False,0x87654321,0x400)
                native_runs+=1;p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
                p.a68k_probe_set_read_script((C.c_uint32*len(o.read_script))(*o.read_script),len(o.read_script))
                for chunk in (1,128):
                    data=(C.c_uint32*38)(*c,1000,0x89abcdef,0x202,0x87654321,0x400)
                    out=(C.c_uint32*(2+WORDS+256))();assert fn(data,ops,len(program),4,chunk,out)
                    actual=list(out[2:2+WORDS]);want=native[-1].copy();key=(hex(target),sr,irq,later,variation,chunk)
                    if not actual[38]:want[36:38]=actual[36:38]
                    assert out[0]==len(native)-1,(key,'steps',out[0],len(native)-1)
                    assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                    actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                    assert actual_writes==writes,(key,'writes',actual_writes,writes)
                    reads=(C.c_uint32*512)();n=p.a68k_probe_get_reads(reads)
                    actual_reads=[list(reads[4*i:4*i+4]) for i in range(n)]
                    assert actual_reads==o.read_events,(key,'reads',actual_reads,o.read_events)
                    digest.update(json.dumps([key,actual,actual_writes,actual_reads]).encode());cases+=1
    guards=p.a68k_probe_sequence_guards();assert guards==7,guards
    return dict(group='status_connections',native_streams=native_runs,portable_comparisons=cases,
                new_scratch_targets=len(targets),new_scratch_encodings=sum(t in targets for t in o.table),
                guards=guards,mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'All SR/CCR target shapes: bus return EAX/control, WriteCCR EAX mask, privilege/CPU gates and IRQ continuation.',
                    'Historical ReadCCR/WriteCCR and instruction bodies reused; no exhaustive SR truth table rerun.',
                    'Synthetic callback provenance; no complete CPU or sound-board qualification.'])


def compare_checked(exe,lib):
    o=TrapOracle(exe);p=C.CDLL(str(lib));p.a68k_probe_enable_binding()
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_set_irq.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8)]
    p.a68k_probe_set_read_script.argtypes=[C.POINTER(C.c_uint32),C.c_uint]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    p.a68k_probe_set_irq(0xffffffff,0,(C.c_uint8*256)(*o.cost))
    specs=[]
    for target,mode,cost in re.findall(r'A68K_CHK\((0x[0-9a-f]+), (\w+), (\d+)\)',(ROOT/'port/a68k/chk_ops.inc').read_text()):specs.append((int(target,16),'CHK',0,mode))
    for file in ('divide_ops.inc','divide_memory_ops.inc'):
        for target,sign,cost,mode,idiv in re.findall(r'A68K_DIVIDE(?:_MEMORY)?\((0x[0-9a-f]+), (\d+), (\d+), (\w+), (0x[0-9a-f]+|0)\)',(ROOT/'port/a68k'/file).read_text()):specs.append((int(target,16),'DIV',int(sign),mode))
    digest=hashlib.sha256();cases=native_runs=0;targets={r[0] for r in specs}
    for target,kind,sign,mode in specs:
        op=next(op for op,t in enumerate(o.table) if t==target and (op>>9)&7==1)
        pairs=[(3,8),(0xffff,8),(9,8)] if kind=='CHK' else [(19,3),(0x12345678,1),(19,0)]
        if sign:pairs.append((0xfffffff1,3))
        for dividend,source in pairs:
            ext=extension(mode)
            if mode in ('INDEXED','PCINDEX'):ext=[0x7023]
            if mode=='IMMEDIATE':ext=[source]
            code=[(op,*ext),0x4e71,0x50d2,0x74ff,0x4e71,0x4e71];program=words(code);ops=(C.c_uint16*len(program))(*program)
            for variation in (0,1):
                c=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
                c[20]=0x1000;c[17]=0x27;c[21]=0;c[18]=0x643;c[19]=0x123401
                c[15]=0x123450;c[16]=0x234500;c[28]=0x456700;c[29]=0x100;c[0]=source;c[1]=dividend;c[7]=0x4000
                o.read_value=0x1002+2*len(ext);o.read_edx=0x602;o.read_xor=0x400 if variation else 0
                o.read_script=[0xa5c30000|source] if mode not in ('REGISTER','IMMEDIATE') else []
                native,writes=o.stream(c,1000,0x89abcdef,0x202,code,False,0x87654321,0x400)
                native_runs+=1;p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
                p.a68k_probe_set_read_script((C.c_uint32*len(o.read_script))(*o.read_script),len(o.read_script))
                for chunk in (1,128):
                    data=(C.c_uint32*38)(*c,1000,0x89abcdef,0x202,0x87654321,0x400)
                    out=(C.c_uint32*(2+WORDS+256))();assert fn(data,ops,len(program),4,chunk,out)
                    actual=list(out[2:2+WORDS]);want=native[-1].copy();key=(hex(target),dividend,source,variation,chunk)
                    if not actual[38]:want[36:38]=actual[36:38]
                    assert out[0]==len(native)-1,(key,'steps',out[0],len(native)-1)
                    assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                    actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                    assert actual_writes==writes,(key,'writes',actual_writes,writes)
                    reads=(C.c_uint32*512)();n=p.a68k_probe_get_reads(reads)
                    actual_reads=[list(reads[4*i:4*i+4]) for i in range(n)]
                    assert actual_reads==o.read_events,(key,'reads',actual_reads,o.read_events)
                    digest.update(json.dumps([key,actual,actual_writes,actual_reads]).encode());cases+=1
    guards=p.a68k_probe_sequence_guards();assert guards==7,guards
    return dict(group='checked_arithmetic_connections',native_streams=native_runs,portable_comparisons=cases,
                new_scratch_targets=len(targets),new_scratch_encodings=sum(t in targets for t in o.table),
                guards=guards,mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'CHK ordinary/negative/upper-bound and DIV quotient/overflow/zero-divisor return connections; memory callbacks preserve EDX/control.',
                    'Existing arithmetic bodies and approved host-IDIV fault policy retained; no exhaustive arithmetic or Windows exception audit rerun.',
                    'Synthetic callback provenance; no complete CPU or sound-board qualification.'])


class FinalControlOracle(TrapOracle):
    def configure_bus(self):
        super().configure_bus();self.reset_count=0
        self.put(CALL+384,CALL+320)
    def hook(self,u,at,size,data):
        if at==CALL+320:
            self.reset_count+=1
            if self.reset_mutate:
                self.u.mem_write(RAM+2,b'\x71\x4e')
                self.put(CTX+80,self.get(CTX+80)[0]+2);self.put(CTX+72,0xa43)
            self.ret(0x76543210)
            u.reg_write(UC_X86_REG_EFLAGS,u.reg_read(UC_X86_REG_EFLAGS)^self.reset_xor)
            return
        super().hook(u,at,size,data)


def compare_final_control(exe,lib):
    o=FinalControlOracle(exe);p=C.CDLL(str(lib));p.a68k_probe_enable_binding()
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    p.a68k_probe_set_reads.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32]
    p.a68k_probe_set_irq.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8)]
    p.a68k_probe_set_reset.argtypes=[C.c_uint32,C.c_uint32,C.c_uint]
    p.a68k_probe_get_reads.argtypes=[C.POINTER(C.c_uint32)]
    p.a68k_probe_set_irq(0xffffffff,0,(C.c_uint8*256)(*o.cost))
    # op, extension, initial SR, pending IRQ, later CPU, callback, mutate
    records=[]
    for op in (0x4e7a,0x4e7b):
        for ext in (0,1,0x8800,0x8801):records.append((op,[ext],0x27,0,1,0,0))
        records.extend([(op,[0],7,0,1,0,0),(op,[0],0x27,0,0,0,0)])
    for sr,irq,imm in ((0x27,0,0x201f),(0x27,1,0x271f),(0x27,1,0x201f),(7,0,0x201f)):
        records.append((0x4e72,[imm],sr,irq,1,0,0))
    for callback,mutate in ((0,0),(1,0),(1,1)):
        records.append((0x4e70,[],0x27,0,1,callback,mutate))
    records.append((0x4e70,[],7,0,1,1,1))
    digest=hashlib.sha256();cases=native_runs=0;targets=set()
    for op,ext,sr,irq,later,callback,mutate in records:
        targets.add(o.table[op])
        code=[(op,*ext),0x50d1,0x72ff,0x4e71,0x4e71,0x4e71];program=words(code);ops=(C.c_uint16*len(program))(*program)
        for variation in (0,1):
            for budget in ((0,131,132,1000) if op==0x4e70 else (0,1000)):
                c=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
                c[20]=0x1000;c[17]=sr;c[21]=irq;c[18]=0x643;c[19]=0x123401
                c[15]=0x123450;c[16]=0x234500;c[28]=0x456700;c[29]=0x100;c[31]=later
                c[25]=CALL+384 if callback else 0
                o.reset_mutate=mutate;o.reset_xor=0x400 if variation else 0
                o.read_value=0x1002+2*len(ext);o.read_edx=0x602;o.read_xor=0x400 if variation else 0
                o.skip_illegal_entry=op in (0x4e7a,0x4e7b) and not later
                native,writes=o.stream(c,budget,0x89abcdef,0x202,code,False,0x87654321,0x400)
                native_runs+=1;p.a68k_probe_set_reads(o.read_value,o.read_edx,o.read_xor)
                p.a68k_probe_set_reset(0x76543210,o.reset_xor,mutate)
                for chunk in (1,128):
                    data=(C.c_uint32*38)(*c,budget,0x89abcdef,0x202,0x87654321,0x400)
                    out=(C.c_uint32*(2+WORDS+256))();assert fn(data,ops,len(program),4,chunk,out)
                    actual=list(out[2:2+WORDS]);want=native[-1].copy();key=(hex(op),ext,sr,irq,later,callback,mutate,variation,budget,chunk)
                    if not actual[38]:want[36:38]=actual[36:38]
                    assert out[0]==len(native)-1,(key,'steps',out[0],len(native)-1)
                    assert actual==want,(key,[(i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b])
                    actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                    assert actual_writes==writes,(key,'writes',actual_writes,writes)
                    reads=(C.c_uint32*512)();n=p.a68k_probe_get_reads(reads)
                    actual_reads=[list(reads[4*i:4*i+4]) for i in range(n)]
                    assert actual_reads==o.read_events,(key,'reads',actual_reads,o.read_events)
                    assert p.a68k_probe_reset_count()==o.reset_count,(key,'reset callback count')
                    digest.update(json.dumps([key,actual,actual_writes,actual_reads,o.reset_count]).encode());cases+=1
    guards=p.a68k_probe_sequence_guards();assert guards==7,guards
    prefetch_guards=p.a68k_probe_prefetch_guards();assert prefetch_guards==5,prefetch_guards
    return dict(group='final_control_connections',native_streams=native_runs,portable_comparisons=cases,
                new_scratch_targets=len(targets),new_scratch_encodings=sum(t in targets for t in o.table),
                guards=guards+prefetch_guards,mismatches=0,result_sha256=digest.hexdigest(),limits=[
                    'MOVEC transfer/gate/privilege, STOP idle/IRQ and RESET prefetched successor including callback PC/flags/code changes.',
                    'RESET successor executes despite negative budget and survives one-step research pauses without re-fetch.',
                    'Synthetic callback provenance; full opcode connection inventory is not complete board/scheduler/state/frontend integration.'])
