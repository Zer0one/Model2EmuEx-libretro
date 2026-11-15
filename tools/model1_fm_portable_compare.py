#!/usr/bin/env python3
"""Model 1 YM2612 synthesis and timer comparison against the initialized original."""
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
import subprocess
import tempfile
from pathlib import Path

from model1_board_compare import initialize, OUTPUT, SP
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_EFLAGS

ROOT = Path(__file__).resolve().parents[1]

def write(o, port, value):
    o.run(0x4b2580, {UC_X86_REG_EAX:port, UC_X86_REG_EBX:value})

def emit(o, path):
    chip = o.get(0x10ed9d4)[0]
    level = o.get(0x107c7d4)[0]
    def words(address, count):
        return struct.unpack('<'+'i'*count, o.u.mem_read(address,count*4))
    arrays = {
        'fm_detune': words(chip+0x40,256), 'fm_attack': words(chip+0x440,94),
        'fm_decay': words(chip+0x5b8,94), 'fm_frequency': words(chip+0x758,2048),
        'fm_lfo_steps': words(chip+0x2760,8), 'fm_attack_curve': words(0x107c7f0,4096),
        'fm_levels': words(level,0xd00),
        'fm_sine_offsets': [(p-level)//4 for p in words(0x1084818,513)],
        'fm_sustain_levels': words(0x5115e0,16), 'fm_ams': words(0x511830,4)
    }
    for i in range(8):
        write(o,0,0xb4)
        write(o,1,i)
        arrays.setdefault('fm_pms',[]).append(o.get(chip+0x2780+0x19c)[0])
    # The timer callback converts using x87 single-precision intermediate
    # arithmetic followed by truncation. Capture the reachable period values.
    for i in range(1024):
        for addr,value in ((0x27,0),(0x24,i>>2),(0x25,i&3),(0x27,1)):
            write(o,0,addr); write(o,1,value)
        assert o.get(0x10e3fc4)[0]==144*(1024-i)
    for i in range(256):
        for addr,value in ((0x27,0),(0x26,i),(0x27,2)):
            write(o,0,addr); write(o,1,value)
        assert o.get(0x10e3fcc)[0]==2304*(256-i)
    rows=['/* Original 1.1a initializer at 004b2780. Regenerate with',
          ' * tools/model1_fm_portable_compare.py --emit-tables, no ROM required. */']
    for name,values in arrays.items():
        rows.append(f'static const int32_t {name}[{len(values)}] = {{')
        for at in range(0,len(values),12):
            rows.append('    '+', '.join(map(str,values[at:at+12]))+',')
        rows.append('};')
    path.write_text('\n'.join(rows)+'\n')

def compare(exe):
    with tempfile.TemporaryDirectory() as td:
        lib=Path(td)/'fm.so'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2','-fPIC','-shared',
                        str(ROOT/'port/snd/fm_original.c'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib))
        dll.m2_original_fm_create.restype=C.c_void_p
        dll.m2_original_fm_write.argtypes=[C.c_void_p,C.c_uint,C.c_uint8]
        dll.m2_original_fm_render.argtypes=[C.c_void_p,C.POINTER(C.c_int16),C.c_size_t]
        dll.m2_original_fm_free.argtypes=[C.c_void_p]
        flush_type=C.CFUNCTYPE(None,C.c_void_p)
        dll.m2_original_fm_tick.argtypes=[C.c_void_p,flush_type,C.c_void_p]
        dll.m2_original_fm_status.argtypes=[C.c_void_p]
        dll.m2_original_fm_write_flush.argtypes=[C.c_void_p,C.c_uint]
        class Completion(C.Structure):
            _fields_=[('eax',C.c_uint32),('flags',C.c_uint32)]
        dll.m2_original_fm_store.argtypes=[C.c_void_p,C.c_uint,C.c_uint8,C.c_uint32]
        dll.m2_original_fm_store.restype=Completion
        flushes=0
        @flush_type
        def flush(_):
            nonlocal flushes
            flushes+=1
        f=dll.m2_original_fm_create()
        o=initialize(exe)
        o.put(0x10e3fe8,0)
        buffer=OUTPUT+0x59000
        left,right=buffer+0x1000,buffer+0x4000
        o.put(buffer,left,right)
        digest=hashlib.sha256()
        frames=events=0
        def reg(bank,idx,v):
            nonlocal events
            for port,data in ((2*bank,idx),(2*bank+1,v)):
                write(o,port,data)
                actual=dll.m2_original_fm_store(f,port,data,0x202)
                expected=(o.u.reg_read(UC_X86_REG_EAX),o.u.reg_read(UC_X86_REG_EFLAGS))
                assert (actual.eax,actual.flags)==expected,(events,hex(idx),port,data,expected,(actual.eax,actual.flags))
            events+=1
        def render(n,name):
            nonlocal frames
            o.put(SP+4,n)
            o.run(0x4b1b50,{UC_X86_REG_EAX:buffer},count=80000000)
            samples=(C.c_int16*(2*n))()
            dll.m2_original_fm_render(f,samples,n)
            for ch,ptr in ((0,left),(1,right)):
                expected=struct.unpack('<'+'h'*n,o.u.mem_read(ptr,2*n))
                got=samples[ch::2]
                assert list(expected)==got,(name,events,frames,ch,next(
                    (i,x,y) for i,(x,y) in enumerate(zip(expected,got)) if x!=y))
            digest.update(bytes(samples))
            frames+=n
        render(32,'reset')
        for pan in range(4):
            reg(1,0xb6,pan<<6)
            reg(0,0x2b,128)
            for v in (0,128,199,255):
                reg(0,0x2a,v)
                render(8,'dac')
        reg(0,0x2b,0)
        for c in range(6):
            bank,idx=divmod(c,3)
            for slot in range(4):
                for addr,v in [(0x30,0x37),(0x40,8+c+slot),(0x50,31),(0x60,143),
                               (0x70,5),(0x80,0x34),(0x90,slot*3)]:
                    reg(bank,addr+slot*4+idx,v)
            reg(bank,0xb4+idx,0xc0)
            reg(bank,0xa4+idx,0x22+c)
            reg(bank,0xa0+idx,8+c*13)
            for alg in range(8):
                reg(bank,0xb0+idx,alg|0x18)
                reg(0,0x28,0xf0|(4*bank+idx))
                render(128,'alg-%d-%d'%(c,alg))
                reg(0,0x28,4*bank+idx)
                render(48,'release')
        for k in range(8):
            reg(0,0x22,8+k)
            for c in range(6):
                bank,idx=divmod(c,3)
                reg(bank,0xb4+idx,((k+c)%4<<6)|(c%4<<4)|k)
                reg(0,0x28,0xf0|4*bank|idx)
            render(760,'lfo')
        for mode in (0x40,0x80,0xc0,0):
            reg(0,0x27,mode)
            for s in range(3):
                reg(0,0xac+s,0x20+s)
                reg(0,0xa8+s,0x19+31*s)
            render(256,'special')
        chip=o.get(0x10ed9d4)[0]
        ticks=0
        for mode in (15,143,48,133,10,0,15):
            reg(0,0x27,0)
            reg(0,0x24,0xff)
            reg(0,0x25,3)
            reg(0,0x26,255)
            reg(0,0x27,mode)
            for i in range(80):
                o.run(0x4a9e00,{})
                dll.m2_original_fm_tick(f,flush,None)
                assert dll.m2_original_fm_status(f)==o.u.mem_read(chip+0x2b,1)[0]
                ticks+=1
            render(127,'timer-CSM')
        # Vary the register being written while other channels, envelopes,
        # interrupts and timers are live. Include register aliases on bank 1.
        rng=random.Random(0x4b2580)
        for step in range(4096):
            bank=rng.randrange(2)
            reg(bank,rng.randrange(256),rng.randrange(256))
            if not step%4:
                render(rng.randrange(1,24),'live-registers')
            if not step%2:
                o.run(0x4a9e00,{})
                observed=dll.m2_original_fm_tick(f,flush,None)
                expected=o.u.reg_read(UC_X86_REG_EAX)
                assert observed==expected,(step,"timer_eax",hex(observed),hex(expected))
                ticks+=1
        dll.m2_original_fm_free(f)
        return dict(register_writes=events, timer_ticks=ticks, timer_a_flushes=flushes, stereo_frames=frames,sha256=digest.hexdigest())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('exe',type=Path)
    p.add_argument('--emit-tables',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.emit_tables:
        emit(initialize(a.exe),a.emit_tables)
    if a.output:
        result=compare(a.exe)
        a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(result)

if __name__=='__main__':
    main()
