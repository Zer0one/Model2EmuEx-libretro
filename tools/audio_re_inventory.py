#!/usr/bin/env python3
"""Classify original A68K dispatch and probe SCSP decode/codegen boundaries.

ISA labels are supplied by the existing Musashi disassembler, not inferred
semantics of original handlers. SCSP probes execute original decoder/generator
code with synthetic inputs and isolated allocator fixtures; no audio replacement.
"""
import argparse
import collections
import hashlib
import json
import random
import struct
import subprocess
import sys
from pathlib import Path
from original_inventory import OriginalPE
from a68k_inventory import decode_dispatch

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [('TRA',0,8,127),('TWT',0,7,1),('TWA',0,0,127),
          ('XSEL',1,15,1),('YSEL',1,13,3),('IRA',1,6,63),('IWT',1,5,1),('IWA',1,0,31),
          ('TABLE',2,15,1),('MWT',2,14,1),('MRD',2,13,1),('EWT',2,12,1),
          ('EWA',2,8,15),('ADRL',2,7,1),('FRCL',2,6,1),('SHIFT',2,4,3),
          ('YRL',2,3,1),('NEGB',2,2,1),('ZERO',2,1,1),('BSEL',2,0,1),
          ('NOFL',3,15,1),('COEF',3,9,63),('MASA',3,2,31),('ADREB',3,1,1),('NXADR',3,0,1)]


def classify(pe, disassembler):
    _, _, _, targets = decode_dispatch(pe)
    lines = subprocess.check_output([str(disassembler.resolve()), '--opcode-map'], text=True).splitlines()
    if len(lines) != 65536:
        raise ValueError('Expected all 65536 disassembler entries')
    by_target = collections.defaultdict(lambda: collections.Counter())
    examples = collections.defaultdict(dict)
    families = collections.Counter()
    for opcode, line in enumerate(lines):
        number, length, asm = line.split('\t', 2)
        assert int(number,16) == opcode and int(length) >= 2
        family = asm.split()[0].split('.')[0].upper()
        # Preserve actual trap encoding classes that a disassembler may label
        # DC.W; these are categories, not assertions of implemented semantics.
        if opcode >> 12 == 10: family = 'LINE_A'
        if opcode >> 12 == 15: family = 'LINE_F'
        if family == 'DC': family = 'DISASSEMBLER_DC'
        if opcode == 0x4afc: family = 'ILLEGAL'
        at = targets[opcode]
        by_target[at][family] += 1
        examples[at].setdefault(family, f'{opcode:04x}')
        families[family] += 1
    rows = [dict(address=f'{a:08x}', opcode_count=sum(c.values()),
                 isa_labels=dict(sorted(c.items())), examples=examples[a],
                 original_prefix_hex=pe.read(a,16).hex()) for a,c in sorted(by_target.items())]
    return dict(opcode_entries=65536, distinct_targets=len(rows),
        isa_label_count=len(families), isa_labels=dict(sorted(families.items())),
        single_label_targets=sum(len(r['isa_labels'])==1 for r in rows),
        mixed_label_targets=sum(len(r['isa_labels'])>1 for r in rows),
        architectural_illegal_opcode_target=f'{targets[0x4afc]:08x}',
        target_rows=rows,
        disassembler_sha256=hashlib.sha256(disassembler.read_bytes()).hexdigest(),
        disassembler_source_sha256=hashlib.sha256((ROOT/'port/m68k/m68kdasm.c').read_bytes()).hexdigest(),
        limits=['ISA labels classify encodings only; original handler semantics and cycles are not executed.',
                'A target shared with ILLEGAL is a review candidate, not proof that all its encodings trap.',
                'Zero extension words are fixtures; only first-word mnemonic categories are indexed.',
                'DC pseudo-ops are disassembler output, not proof of architectural illegality.'])


def probe_scsp(exe):
    sys.path.insert(0, str(ROOT/'port/sharc/test'))
    from difftest_bits import load_original, SP, STOP
    from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_EDI, UC_X86_REG_ESP, UC_X86_REG_EIP
    uc = load_original(exe)
    ctx, code = 0x72000000, 0x73000000
    uc.mem_map(ctx, 0x10000); uc.mem_map(code, 0x10000)
    def call(entry, **registers):
        uc.mem_write(SP, struct.pack('<I', STOP))
        uc.reg_write(UC_X86_REG_ESP, SP)
        for name, value in registers.items():
            uc.reg_write({'eax':UC_X86_REG_EAX,'edx':UC_X86_REG_EDX,'edi':UC_X86_REG_EDI}[name], value)
        uc.emu_start(entry, STOP, count=1000000)
        assert uc.reg_read(UC_X86_REG_EIP) == STOP
    rng = random.Random(0x5c5b)
    words = [0, (1<<64)-1] + [1<<b for b in range(64)] + [((1<<64)-1)^(1<<b) for b in range(64)]
    words += [rng.getrandbits(64) for _ in range(512)]
    digest = hashlib.sha256()
    for bits in words:
        data = struct.pack('<Q',bits)
        uc.mem_write(ctx,data); uc.mem_write(ctx+0x100,bytes(100))
        call(0x4a9e90,eax=ctx+0x100,edx=ctx)
        got = bytes(uc.mem_read(ctx+0x100,100))
        w = struct.unpack('<4H',data)
        expected = struct.pack('<25I', *[(w[i]>>shift)&mask for _,i,shift,mask in FIELDS])
        assert got == expected, f'Decoder mismatch: {bits:016x}'
        digest.update(data+got)
    # Only imported host allocation is replaced; original generator code is
    # untouched. Stdcall stubs return a bounded synthetic 64 KiB allocation.
    alloc, free = STOP+0x100, STOP+0x120
    uc.mem_write(alloc,b'\xb8'+struct.pack('<I',code)+b'\xc2\x10\x00')
    uc.mem_write(free,b'\xb8\x01\x00\x00\x00\xc2\x0c\x00')
    uc.mem_write(0x5081d8,struct.pack('<I',alloc)); uc.mem_write(0x5081e0,struct.pack('<I',free))
    writes, calls = [], []
    uc.hook_add(UC_HOOK_MEM_WRITE,lambda mu,access,a,n,v,user:writes.append((a,n)),begin=code,end=code+0xffff)
    def host_call(mu, address, size, user):
        sp=mu.reg_read(UC_X86_REG_ESP)
        args=struct.unpack('<4I' if address==alloc else '<3I',bytes(mu.mem_read(sp+4,16 if address==alloc else 12)))
        calls.append((address,args))
    uc.hook_add(UC_HOOK_CODE,host_call,begin=alloc,end=alloc)
    uc.hook_add(UC_HOOK_CODE,host_call,begin=free,end=free)
    programs=[('empty',[],False),('zero-step',[0],False),('all-fields',[0xffffffffffffffff]*2,False),
              ('full-128',[0xffffffffffffffff]*128,False),('recompile',[0],True)]
    programs += [(f'bit-{b:02}',[1<<b,0],False) for b in range(64)]
    generated=[]
    for name, program, old in programs:
        uc.mem_write(ctx,bytes(0x1000)); uc.mem_write(code,bytes(0x10000)); writes.clear(); calls.clear()
        uc.mem_write(ctx+0xcc,b''.join(struct.pack('<Q',w) for w in program))
        uc.mem_write(ctx+0x7b8,struct.pack('<I',len(program)))
        uc.mem_write(ctx+0x7e8,struct.pack('<I',code if old else 0))
        call(0x4aa040,edi=ctx)
        assert calls == ([(free,(code,0,0x8000))] if old else [])+[(alloc,(0,0x10000,0x1000,0x40))]
        assert struct.unpack('<I',uc.mem_read(ctx+0x7e8,4))[0] == code
        end=max(a+n for a,n in writes)
        blob=bytes(uc.mem_read(code,end-code))
        assert blob.startswith(bytes.fromhex('51525356')) and blob.endswith(bytes.fromhex('5e5b5a59c3'))
        generated.append(dict(name=name,steps=len(program),bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),host_calls=len(calls)))
    starts=[]
    for last in [-1,0,1,63,126,127]:
        uc.mem_write(ctx,bytes(0x1000)); uc.mem_write(code,bytes(0x10000))
        if last >= 0: uc.mem_write(ctx+0xcc+last*8,struct.pack('<Q',1))
        call(0x4aa7f0,eax=ctx)
        got=struct.unpack('<I',uc.mem_read(ctx+0x7b8,4))[0]
        assert got == last+1 and uc.mem_read(ctx+0x7b4,1)==b'\0'
        starts.append(dict(last_nonzero_step=last,native_last_step=got))
    return dict(decoder_entry='004a9e90',decoder_cases=len(words),fields=[x[0] for x in FIELDS],
        decoder_result_sha256=digest.hexdigest(),generator_entry='004aa040',
        generator_cases=len(generated),generated=generated,start_entry='004aa7f0',start_cases=starts,
        host_services={'VirtualAlloc':'005081d8','VirtualFree':'005081e0'},
        limits=['Generated bodies are captured and hashed, not executed or compared to portable DSP audio.',
                'Allocator fixtures establish a reproducible boundary, not Windows allocation behavior.',
                'Decoder fixtures cover bit bases/complements plus random combinations, not the full 64-bit domain.'])


def probe_moveq_alias(exe):
    """One concrete mixed-label target; stop before the next opcode fetch."""
    sys.path.insert(0, str(ROOT/'port/sharc/test'))
    from difftest_bits import load_original, SP
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EIP, UC_X86_REG_ESP
    uc=load_original(exe)
    rows=[]
    for reg in range(8):
        for imm in [0,1,127,128,255]:
            pair=[]
            for extra in [0,0x100]:
                opcode=0x7000 | reg<<9 | extra | imm
                uc.mem_write(0x528ce4,bytes(32)); uc.mem_write(0x10ed9b0,struct.pack('<I',100))
                uc.reg_write(UC_X86_REG_ECX,opcode); uc.reg_write(UC_X86_REG_ESI,0x200)
                uc.reg_write(UC_X86_REG_ESP,SP)
                uc.emu_start(0x478438,0x47845c,count=100)
                assert uc.reg_read(UC_X86_REG_EIP)==0x47845c
                regs=struct.unpack('<8I',uc.mem_read(0x528ce4,32))
                expected=(imm if imm<128 else imm-256)&0xffffffff
                assert regs[reg]==expected and all(not v for i,v in enumerate(regs) if i!=reg)
                cycles=struct.unpack('<I',uc.mem_read(0x10ed9b0,4))[0]
                assert cycles==96 and uc.reg_read(UC_X86_REG_ESI)==0x202
                pair.append((regs,uc.reg_read(UC_X86_REG_EDX)&0xc5,cycles))
            assert pair[0]==pair[1]
            rows.append(dict(register=reg,immediate=imm,result=pair[0][0][reg],flags=pair[0][1]))
    return dict(entry='00478438',stop_before_next_fetch='0047845c',executions=len(rows)*2,
        alias_pairs=len(rows),ignored_opcode_bit=8,results=rows,
        limits=['A partial original handler execution proves this alias only; it is not a whole A68K/Musashi comparison.',
                'No actual sound-program reachability or audible impact has been established.'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path); ap.add_argument('--disassembler',type=Path,required=True)
    ap.add_argument('--verify-original',action='store_true'); ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(); pe=OriginalPE(args.exe)
    report=dict(original_sha256=hashlib.sha256(pe.data).hexdigest(),a68k=classify(pe,args.disassembler))
    if args.verify_original:
        report['scsp']=probe_scsp(args.exe)
        report['a68k_moveq_alias']=probe_moveq_alias(args.exe)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report['a68k'].items() if k not in ('target_rows','isa_labels','limits')},indent=2))
    if 'scsp' in report: print(json.dumps({k:v for k,v in report['scsp'].items() if k not in ('generated','limits')},indent=2))


if __name__=='__main__': main()
