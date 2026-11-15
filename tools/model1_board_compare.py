#!/usr/bin/env python3
"""Exercise the original Model 1-style sound board independently of any game."""
import argparse
import ctypes as C
import subprocess
import tempfile
import hashlib
import json
import struct
from itertools import groupby
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                               UC_X86_REG_EDX, UC_X86_REG_EIP, UC_X86_REG_ESP,
                               UC_X86_REG_FPCW)
from a68k_boundary_compare import CTX, DATA, READ, WRITE, Oracle, SP, STOP

BOARD, PROGRAM, STORAGE, AUDIO_RAM = 0x74000000, 0x75000000, 0x76000000, 0x77000000
DEVICE, OUTPUT = BOARD+0x204000, BOARD+0x205000
READ_PTR, WRITE_PTR, FIFO, IRQ = 0x5aa761, 0x5a96be, 0x5aa6e0, CTX+0x54


def initialize(exe, samples=None, program=None, fps=58):
    o = Oracle(exe)
    o.u.reg_write(UC_X86_REG_FPCW,0x007f)
    o.u.mem_map(BOARD,0x300000)
    o.u.mem_map(PROGRAM, max(0x40000,len(program or b"")))
    o.u.mem_map(AUDIO_RAM,0x10000)
    o.u.mem_map(STORAGE,0x800000)
    if samples is not None:
        o.u.mem_write(STORAGE,bytes(samples))
    o.put(BOARD+4,DEVICE)
    o.put(BOARD+0x14,OUTPUT,DEVICE+0x400)
    o.put(BOARD+0x20389c,AUDIO_RAM)
    o.put(DEVICE+0x28,PROGRAM,0x40000,STORAGE,0x800000)
    o.put(0x5aa730,BOARD)
    o.put(OUTPUT+0xac4a8,44100)
    o.u.mem_write(OUTPUT+0x20,struct.pack('<f',fps))
    # Guest code at reset keeps interrupts masked and executes a BRA to itself.
    if program is not None:
        o.u.mem_write(PROGRAM,bytes(program))
    else:
        o.u.mem_write(PROGRAM,struct.pack('<5H',0x00f0,0xff00,0,8,0x60fe))
    o.u.hook_del(o.code_hook)
    o.put(0x10f1fec,1)
    thread = 0x72018000
    o.put(thread+0x14,1)
    o.u.mem_map(0x78000000,0x20000)
    allocations = iter([(0x3198,0x78000000),(0xc2b0,0x78004000)])
    def allocate(u,pc,size,data):
        requested = o.get(u.reg_read(UC_X86_REG_ESP)+4)[0]
        expected, address = next(allocations)
        assert requested == expected
        o.ret(address)
    def host_stream(u,pc,size,data):
        # The original has already computed and stored this stream's block
        # length. Skip the host device calls and execute its real epilogue.
        u.reg_write(UC_X86_REG_EIP,0x4eee3b)
    hooks = [o.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc) for pc,fn in
             [(0x48d12f,allocate),(0x4980b1,lambda *_:o.ret(thread)),(0x4eed53,host_stream)]]
    o.u.ctl_flush_tb()
    o.run(0x4ccbe0,{UC_X86_REG_ECX:BOARD},stops=(),count=16000000)
    for hook in hooks: o.u.hook_del(hook)
    assert o.get(BOARD+0x28)[0] == int(44100/fps)
    return o


def maps(o):
    maps = {}
    for name,base in [('fetch',READ),('data',DATA),('write',WRITE)]:
        pages = list(struct.iter_unpack('<4I',o.u.mem_read(base,4096*16)))
        groups = []
        begin = 0
        for descriptor,group in groupby(pages):
            count = sum(1 for _ in group)
            groups.append([f'{begin<<12:06x}',f'{((begin+count)<<12)-1:06x}',*[f'{n:08x}' for n in descriptor]])
            begin += count
        maps[name] = groups
    assert o.get(READ,4)==[PROGRAM,0,0,0] and o.get(READ+0x800,4)==[PROGRAM-0x60000,0,0,0]
    assert o.get(DATA+0x200,4)==[0,0x4c7d40,0x4c7d30,0x4c7d20]
    assert o.get(DATA+0xf000,4)==o.get(WRITE+0xf000,4)==[AUDIO_RAM-0xf00000,0,0,0]
    return maps


def uart(o):
    reads = 0
    for burst in [0,1,31,32,33,63,64,65,128]:
        for width,fn in [(1,0x4c6a40),(2,0x4c82d0),(4,0x4cb1c0)]:
            for start in (0,1,2,0xfffe,0xffff):
                rd=wr=29
                fifo=bytearray(32)
                o.u.mem_write(READ_PTR,bytes([rd]))
                o.u.mem_write(WRITE_PTR,bytes([wr]))
                o.u.mem_write(FIFO,bytes(fifo))
                o.put(IRQ,5)
                for i in range(burst):
                    value=(i*31+burst*3)&255
                    o.run(0x4c8660,{UC_X86_REG_ECX:value})
                    fifo[wr]=value
                    wr=(wr+1)&31
                assert bytes(o.u.mem_read(FIFO,32))==fifo
                assert o.get(IRQ)[0]==5
                o.run(fn,{UC_X86_REG_ECX:0xc20000+start})
                result=0
                for i in range(width):
                    value=0
                    if (start+i)&65535==1 and rd!=wr:
                        value=fifo[rd]
                        rd=(rd+1)&31
                    result=(result<<8)|value
                popped=any((start+i)&65535==1 for i in range(width))
                assert o.u.reg_read(UC_X86_REG_EAX)&((1<<(width*8))-1)==result
                assert o.u.mem_read(READ_PTR,1)[0]==rd
                assert o.get(IRQ)[0]==(0 if popped and rd==wr else 5)
                reads+=1
    return dict(width_offset_burst_cases=reads,capacity=32,equal_cursors_read_empty=True)


def schedule(o):
    trace=[]
    sites = {0x462b1c:'A68K',0x4a9e00:'FM timers'}
    def observe(u,pc,size,data):
        trace.append((sites[pc],o.get(0x10ed9b0)[0]))
    hooks=[o.u.hook_add(UC_HOOK_CODE,observe,begin=x,end=x) for x in sites]
    o.u.ctl_flush_tb()
    for idle in (False,True):
        o.put(0x10482a4,0x80 if idle else 0)
        for pending in (False,True):
            trace.clear()
            o.u.mem_write(READ_PTR,bytes([6]))
            o.u.mem_write(WRITE_PTR,bytes([7 if pending else 6]))
            o.put(0x10e3fc0,0,0,0,0)
            o.put(IRQ,0)
            o.run(0x4cc710,{UC_X86_REG_EAX:BOARD},count=20000)
            assert [name for name,budget in trace]==(['FM timers'] if idle else ['A68K','FM timers'])*10
            assert all(budget==79 for name,budget in trace if name=='A68K')
            assert o.get(0x10e3fc0,4)==[670,0,670,0]
            assert o.get(IRQ)[0]==(2 if pending else 0)
    for h in hooks: o.u.hook_del(h)
    return dict(cycles_per_dispatch=79,ticks_per_scanline=10,timer_increment=67,
                irq_after_last_tick=2, template_stop_suppresses_cpu_only=True)


def multipcm_ports(o):
    """Both chips, full width stores and state actually touched by the key-on."""
    tests = 0
    for chip, (put8,put16,put32) in enumerate([(0x4cbab0,0x4cc5a0,0x4cc650),
                                                (0x4cba80,0x4cc530,0x4cc630)]):
        base = 0xc40000+chip*0x20000
        device = 0x1087020+chip*0x3450
        slot = device+0x2800
        def write8(offset,value):
            o.run(put8,{UC_X86_REG_ECX:base+offset,UC_X86_REG_EDX:value})
        def reg(register,value):
            write8(5,register)
            write8(1,value)
        for width,fn in [(1,put8),(2,put16),(4,put32)]:
            for offset in range(0xfffc,0x10005):
                packed=0x3527c4fe & ((1<<(8*width))-1)
                o.put(device+0x3448,6)
                o.run(fn,{UC_X86_REG_ECX:base+offset,UC_X86_REG_EDX:packed})
                expected=6
                if offset<=0x10001<offset+width:
                    expected=packed.to_bytes(width,'big')[0x10001-offset]&7
                assert o.get(device+0x3448)[0]==expected
                tests+=1
        for select in range(32):
            write8(3,select)
            expected = 0xffffffff if (select&7)==7 else select-select//8
            assert o.get(device+0x3440)[0]==expected
        write8(3,0)
        for sample in (0,37,255):
            # The slot latches only the low byte of the sample selector. Reg 2 bit 0
            # does not extend it to 9 bits as in the inherited chip.
            smp=device+20*sample
            o.put(smp,0x183abc)
            for bit in (0,1):
                reg(2,bit)
                reg(1,sample)
                for bank in range(8):
                    write8(0x10001,bank)
                    reg(4,0x80)
                    assert o.get(slot+0x0c,2)==[smp,bank*0x100000+0x83abc]
                    write8(0x10001,bank^1)
                    assert o.get(slot+0x10)[0]==bank*0x100000+0x83abc
                    tests+=1
        # Inactive slot selectors (-1) address the decoded descriptor area
        # immediately preceding the voices in the original chip allocation.
        before=bytes(o.u.mem_read(slot-0x70,0x70))
        write8(3,7)
        reg(0,0xd0)
        after=bytes(o.u.mem_read(slot-0x70,0x70))
        assert after[1]==0xd0 and after[0x1c]==13
        assert [i for i in range(0x70) if after[i]!=before[i]]==[1,0x1c]
    return dict(bank_and_keyon_cases=tests,slot_decode_cases=64,latched_bank_bits=3,
                highest_selectable_sample=255,invalid_slot_alias='slot[-1], descriptor storage')


# Original, immutable synthesis tables. The twelve extra words below each rate
# table are reachable through a negative octave/key scaling combination.
TABLES = {
    'left_pan': (0x108fdc0,2048), 'right_pan': (0x10962d8,2048),
    'frequency': (0x1092dd8,1024), 'envelope_gain': (0x1091dc8,1024),
    'attack_rate': (0x108fcc0-12*4,76), 'decay_rate': (0x10961d8-12*4,76),
    'pitch_wave': (0x1095dd8,256), 'amp_wave': (0x108f8c0,256),
    'pitch_gain': (0x108d8c0,2048), 'amp_gain': (0x1093dd8,2048),
}


def table_evidence(o, destination):
    digest=hashlib.sha256()
    rows=['/* ElSemi 1.1a, initializer 004b01b0 including 004afd20, CW=007f.',
          ' * Generated by tools/model1_board_compare.py --emit-tables from emulator',
          ' * constants. Native table values do not depend on external ROM data. */']
    for name,(base,count) in TABLES.items():
        raw=bytes(o.u.mem_read(base,4*count))
        digest.update(raw)
        if destination:
            values=struct.unpack('<'+'i'*count,raw)
            rows.append(f'static const int32_t {name}[{count}] = {{')
            for at in range(0,count,12):
                rows.append('    '+', '.join(map(str,values[at:at+12]))+',')
            rows.append('};')
    if destination:
        destination.write_text('\n'.join(rows)+'\n')
    return dict(words=sum(n for _,n in TABLES.values()),sha256=digest.hexdigest())


def multipcm_differential(exe):
    # All 512 descriptors and both sides of the 4 MiB ROM boundary are synthetic.
    size=0x800000
    samples=(bytearray((i*97+31)&255 for i in range(256))*(size//256))
    for chip in range(2):
        for i in range(512):
            at=chip*0x400000+12*i
            start=(0x100000 if i&1 else 0)+0x8000+32*i
            samples[at:at+12] = (start.to_bytes(3,'big') + bytes.fromhex('0006ffdf') +
                bytes([(i*7)&63,0xf3,0xa4,0xf2,(i+chip)&7]))
    o=initialize(exe,samples)
    with tempfile.TemporaryDirectory() as td:
        image=Path(td)/'mpcm.so'
        source=Path(__file__).resolve().parents[1]/'port/snd/multipcm_original.c'
        shim=Path(td)/'chip_image.c'
        shim.write_text('#include "multipcm_original.c"\n'
                        'const void *probe_image(const m2_original_mpcm *m) { return &m->image; }\n')
        subprocess.run(['cc','-std=c11','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',
                        '-I',str(source.parent),str(shim),'-o',str(image)],check=True)
        lib=C.CDLL(str(image))
        pu8=C.POINTER(C.c_uint8)
        lib.m2_original_mpcm_create.argtypes=[C.c_uint,pu8,C.c_size_t]
        lib.m2_original_mpcm_create.restype=C.c_void_p
        lib.m2_original_mpcm_write.argtypes=[C.c_void_p,C.c_uint,C.c_uint8]
        lib.m2_original_mpcm_bank.argtypes=[C.c_void_p,C.c_uint]
        lib.m2_original_mpcm_mix.argtypes=[C.c_void_p,C.POINTER(C.c_int16),C.c_size_t,C.c_uint]
        lib.m2_original_mpcm_error.argtypes=[C.c_void_p]
        lib.m2_original_mpcm_error.restype=C.c_char_p
        lib.m2_original_mpcm_archive.argtypes=[C.c_void_p,C.c_void_p]
        lib.probe_image.argtypes=[C.c_void_p]
        lib.probe_image.restype=C.c_void_p
        class Archive(C.Structure):
            _fields_=[('data',pu8),('size',C.c_size_t),('pos',C.c_size_t),('mode',C.c_int),('failed',C.c_int)]
        rom=(C.c_uint8*size).from_buffer(samples)
        chips=[lib.m2_original_mpcm_create(i,rom,size) for i in range(2)]
        assert all(chips)
        digest=hashlib.sha256()
        writes=frames=0
        def check(chip):
            expected=bytes(o.u.mem_read(0x1087020+0x3450*chip,0x3450))
            actual=C.string_at(lib.probe_image(chips[chip]),len(expected))
            assert actual==expected, (chip,writes,frames,next(
                    (hex(i),a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b))
        def round_trip(chip):
            expected=C.string_at(lib.probe_image(chips[chip]),0x3450)
            # Only the aliased descriptor tail and live slots/registers are mutable.
            tail=0x2800-0x70
            data=(C.c_uint8*(len(expected)-tail))()
            a=Archive(data,len(data),0,0,0)
            lib.m2_original_mpcm_archive(chips[chip],C.byref(a))
            assert not a.failed and a.pos==len(data) and bytes(data)==expected[tail:]
            fresh=lib.m2_original_mpcm_create(chip,rom,size)
            assert fresh
            before=C.string_at(lib.probe_image(fresh),len(expected))
            selected=len(data)-16
            data[selected] ^= 0x40
            a=Archive(data,len(data),0,1,0)
            lib.m2_original_mpcm_archive(fresh,C.byref(a))
            assert a.failed and C.string_at(lib.probe_image(fresh),len(expected))==before
            data[selected] ^= 0x40
            a=Archive(data,len(data),0,2,0)
            lib.m2_original_mpcm_archive(fresh,C.byref(a))
            assert not a.failed and C.string_at(lib.probe_image(fresh),len(expected))==expected
            free(fresh)
        def write(chip,offset,value):
            nonlocal writes
            fn=(0x4cbab0,0x4cba80)[chip]
            base=0xc40000+0x20000*chip
            o.run(fn,{UC_X86_REG_ECX:base+offset,UC_X86_REG_EDX:value})
            if offset == 0x10001:
                lib.m2_original_mpcm_bank(chips[chip],value)
            else:
                lib.m2_original_mpcm_write(chips[chip],offset//2,value)
            writes+=1
            check(chip)
        def mix_block(n):
            nonlocal frames
            inp=[((i*39+frames*73)&65535)-32768 for i in range(n*2)]
            out=(C.c_int16*(n*2))(*inp)
            for ch,offset in [(0,0x68),(1,0x2b178)]:
                o.u.mem_write(OUTPUT+offset,struct.pack('<'+'h'*n,*inp[ch::2]))
            o.put(0x1092dd0,n)
            for chip in range(2):
                o.run(0x4affb0,{UC_X86_REG_EAX:chip},count=10000000)
                lib.m2_original_mpcm_mix(chips[chip],out,n,100)
                assert lib.m2_original_mpcm_error(chips[chip]) is None
                check(chip)
                for ch,offset in [(0,0x68),(1,0x2b178)]:
                    assert list(out[ch::2])==list(struct.unpack('<'+'h'*n,o.u.mem_read(OUTPUT+offset,2*n))), (chip,frames,ch)
            digest.update(bytes(out))
            frames+=n
        for chip in range(2):
            check(chip)
            for i in range(32):
                write(chip,3,i)
                if (i&7)==7:
                    write(chip,5,0)
                    write(chip,1,0x70)
                    continue
                write(chip,0x10001,i%4)
                for reg,value in [(1,2*i+1),(0,(i*17)&255),(2,0x43),(3,0x3a),
                                  (5,1),(6,(i+1)&63),(7,i&7),(4,128)]:
                    write(chip,5,reg)
                    write(chip,1,value)
        for k,n in enumerate((1,2,16,127,760,31,512)):
            mix_block(n)
            for chip in range(2):
                write(chip,3,k)
                for reg,value in ((5,60+2*k),(3,0x20+k),(6,0x37),(7,0x06),(4,0)):
                    write(chip,5,reg)
                    write(chip,1,value)
        free=C.CDLL(None).free
        free.argtypes=[C.c_void_p]
        for chip in range(2):
            round_trip(chip)
            free(chips[chip])
        return dict(register_writes=writes, compared_stereo_frames=frames, chips=2,
                    native_image_bytes_per_check=0x3450, archived_bytes_per_chip=0xcc0,
                    fresh_chip_restores=2, invalid_selectors_rejected=2, sha256=digest.hexdigest())


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--emit-tables',type=Path)
    args=ap.parse_args()
    o=initialize(args.exe)
    result=dict(original=hashlib.sha256(args.exe.read_bytes()).hexdigest(), tables=table_evidence(o,args.emit_tables), maps=maps(o),uart=uart(o),schedule=schedule(o),multipcm=multipcm_ports(o),differential=multipcm_differential(args.exe))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['uart'],result['schedule'])


if __name__=='__main__':
    main()
