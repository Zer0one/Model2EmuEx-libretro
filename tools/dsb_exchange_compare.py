#!/usr/bin/env python3
"""Compare portable digital-board packet, track and post-decode exchanges with ElSemi."""
import argparse
import ctypes as C
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path

from a68k_boundary_compare import Oracle, SP
from dsb_board_compare import MUSIC, OUT, PROGRAM, commands, mix, native_board
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_FPCW

ROOT = Path(__file__).resolve().parents[1]
U8, U32, I16, I32 = C.c_uint8, C.c_uint32, C.c_int16, C.c_int32


class State(C.Structure):
    _fields_ = [('packet', U8*3), ('used', U8), ('segment', U8)] + [
        (name, U32) for name in ('descriptor','position','end','loop','active','route','phase','step')
    ] + [('previous', I32 * 2)]


def bind(path):
    dll = C.CDLL(str(path))
    ptr, rom = C.POINTER(State), C.POINTER(U8)
    dll.m2_dsb_command.argtypes = [ptr, C.c_uint, rom, C.c_size_t, U8]
    dll.m2_dsb_next_segment.argtypes = [ptr, C.c_uint, rom, C.c_size_t]
    dll.m2_dsb_mix_decoded.argtypes = [ptr, C.c_uint, *([C.POINTER(I16)]*3), C.c_size_t]
    dll.m2_dsb_mix_decoded.restype = C.c_size_t
    return dll


def compare_state(o, s):
    assert list(s.packet) == list(o.u.mem_read(0x1078788, 3))
    for prop, addr in [('used',0x10ed99d),('segment',0x1078798)]:
        assert getattr(s, prop) == o.u.mem_read(addr, 1)[0]
    desc = o.get(0x10787ac)[0]
    assert s.descriptor == (desc - PROGRAM if desc else 0)
    for prop, addr in [('position',0x1078758),('end',0x1078780),('loop',0x10787a4),
                       ('active',0x1078790),('route',0x10787b0),('phase',0x10787a0),('step',0x10787a8)]:
        assert getattr(s, prop) == o.get(addr)[0], (prop, getattr(s, prop), o.get(addr))
    assert [x & 0xffffffff for x in s.previous] == [o.get(0x107879c)[0],o.get(0x1078794)[0]]


def fixture(exe, kind):
    o = Oracle(exe)
    s = State()
    raw = bytearray(0x20000)
    def word(at, x):
        struct.pack_into('<H', raw, at, x)
    if kind == 1:
        word(0x1000, 0x2101)
        word(0x1002, 0x2301)
        word(0x1004, 3)
        word(0x9100, 0x2200)
        word(0x9102, 0x2210)
        raw[0x9203:0x9208] = bytes([1,0xff,2,0xf1,0xf0])
        raw[0x9213:0x9216] = bytes([2,2,0xf0])
        raw[0x92fa:0x9300] = bytes.fromhex('001123011234')
        raw[0x930c:0x9312] = bytes.fromhex('0289ab0389cd')
    else:
        word(0x8002, 0x9001)
        word(0x800a, 3)
        for i in (1, 2):
            word(0x9000 + 4*i-2, 0x9100 + 32*i)
            at = 0x9100 + 32*i
            raw[at:at+18] = bytes.fromhex('00800100231202003423000000000100dcfe')
            raw[at+1] = 0x80 if i==1 else 0
    o.u.mem_map(PROGRAM, len(raw))
    o.u.mem_write(PROGRAM, bytes(raw))
    o.u.mem_map(OUT, 0x10000)
    o.put(0x107878c, PROGRAM)
    o.u.mem_write(0x107878b, bytes([kind]))
    return o, s, (U8*len(raw)).from_buffer(raw)


def packets(exe, dll, kind):
    o, s, rom = fixture(exe, kind)
    prefix, cmd = (0xaf,0x6f) if kind == 1 else (0xae,0x10)
    edges = []
    def send(value):
        commands(o, [value])
        assert dll.m2_dsb_command(C.byref(s), kind, rom, len(rom), value)
        compare_state(o, s)
        edges.append(value)
    for byte in (0,5,0xff,prefix,cmd,prefix,cmd,1,prefix,cmd,3,0xa0,0,1,
                 prefix,cmd,0,prefix,0x03,2,prefix,cmd,1):
        send(byte)
    if kind == 3:
        return len(edges), 0
    checks = 0
    for track in (1, 2):
        for byte in (prefix,cmd,track):
            send(byte)
        for _ in range(3):
            s.position = s.end
            o.put(0x1078758, s.position)
            o.put(0x1078760, 1)
            # Run up to the decoder call for a continuing segment. Ended tracks
            # return from the mixer directly, leaving the cursor at the boundary.
            o.run(0x4b2d10, stops=(0x4e9e50,))
            assert dll.m2_dsb_next_segment(C.byref(s),kind,rom,len(rom))
            compare_state(o, s)
            checks += 1
            if not s.active:
                break
            assert o.u.reg_read(UC_X86_REG_EIP) == 0x4e9e50
    return len(edges), checks


def mixer(exe, dll):
    o, s, _ = fixture(exe, 1)
    o.put(0x107877c, OUT)
    o.put(0x1078784, OUT+0x8000)
    left = (I16 * 1152)(*[((x*727+11)&65535)-32768 for x in range(1152)])
    right = (I16 * 1152)(*[((x*991+21)&65535)-32768 for x in range(1152)])
    o.u.mem_write(OUT+0x1000,bytes(left))
    o.u.mem_write(OUT+0x9000,bytes(right))
    o.put(0x1078768, OUT+0x1000,OUT+0x9000)
    digest = hashlib.sha256()
    cases = 0
    for kind in (1,2):
        o.u.mem_write(0x107878b, bytes([kind]))
        for route in (0,1,2,3):
            for phase in (0,1,127,255,256,1151*256):
                for step in (0,185,256,1024):
                    s.active, s.route, s.phase, s.step = 1,route,phase,step
                    s.previous[:] = [32767,-32768]
                    for address, val in ((0x1078790,1),(0x10787b0,route),(0x10787a0,phase),
                                         (0x10787a8,step),(0x107879c,32767),(0x1078794,-32768)):
                        o.put(address,val)
                    pcm=(I16*18)(*([16357,-12345]*9))
                    n=dll.m2_dsb_mix_decoded(C.byref(s),kind,left,right,pcm,9)
                    original = mix(o,struct.pack('<hh',16357,-12345)*n)
                    assert original == bytes(pcm)[:4*n]
                    compare_state(o,s)
                    digest.update(original)
                    cases += 1
    return cases, digest.hexdigest()


class Header(C.Structure):
    _fields_ = [(n,U32) for n in ('layer','rate','channels','joint_bands','bytes','payload_bit')]


def frame_headers(exe, dll):
    o, _, _ = fixture(exe, 2)
    dll.m2_dsb_frame_header.argtypes = [C.POINTER(U8), C.c_size_t, C.POINTER(Header)]
    def check(raw):
        header = Header()
        array = (U8*4).from_buffer_copy(raw)
        ok = dll.m2_dsb_frame_header(array,4,C.byref(header))
        o.u.mem_write(OUT,raw+bytes(40))
        o.put(SP+4,OUT,OUT+0x100)
        o.run(0x4e9e50,stops=(0x4e9fd0,))
        if not ok:
            assert o.stop is None and o.u.reg_read(UC_X86_REG_EAX)==0xffffffff
            return
        assert o.stop == 0x4e9fd0
        esp=o.u.reg_read(UC_X86_REG_ESP)
        fields=[o.get(esp+at)[0] for at in (0x1c,0x38,0x40,0x30)]
        assert list(fields)==[header.layer,header.channels,header.joint_bands,header.bytes]
        assert o.u.reg_read(UC_X86_REG_EBP)==header.rate
        assert o.get(0x10ed8b4)[0]==header.payload_bit
    cases = 0
    for layer in (1,2,3,4):
        for bitrate in range(16):
            for rate in range(4):
                for mode in range(4):
                    for pad in (0,1):
                        # Vary CRC and all four joint-stereo bounds.
                        crc=(rate+bitrate)&1
                        ext=(pad+rate+bitrate)&3
                        check(bytes((0xff,0xf8|((4-layer)<<1)|crc,(bitrate<<4)|(rate<<2)|(pad<<1),
                                     (mode<<6)|(ext<<4))))
                        cases += 1
    for first,second in ((0,0xfd),(0xff,0xf5),(0xfe,0xfd),(0xff,0xe5)):
        check(bytes((first,second,0x88,0)))
        cases += 1
    return cases


def portable_track(exe, archive, dll):
    # Compare the portable decode and mix with the complete original route.
    kind = {'stcc':1, 'topskatr':2}[archive.stem]
    original = native_board(exe, archive, kind)
    decode = native_board(exe, archive, kind)
    f=Filter()
    dll.m2_dsb_synthesis_init(C.byref(f))
    dll.m2_dsb_layer2.argtypes=[C.POINTER(Filter),C.POINTER(U8),C.c_size_t,C.POINTER(Header),C.POINTER(I16)]
    pcm=(I16*2304)()
    raw = bytes(decode.u.mem_read(PROGRAM, 0x20000))
    rom = (U8*len(raw)).from_buffer_copy(raw)
    state = State()
    prefix, cmd = (0xaf,0x6f) if kind == 1 else (0xae,0x10)
    digest = hashlib.sha256()
    refills = 0
    left, right = (I16*1152)(), (I16*1152)()
    for frame in range(36):
        # Start, cut off, stay stopped, restart. Exercise both silent input
        # and existing (synthetic) SCSP audio during the MPEG track.
        if frame in (0,18,20):
            packet = (prefix,3,0) if frame == 18 else (prefix,cmd,1)
            commands(original,packet)
            for b in packet:
                assert dll.m2_dsb_command(C.byref(state),kind,rom,len(rom),b)
        count = 760
        scsp = [((i*463+frame*221)&65535)-32768 if frame&1 else 0 for i in range(count*2)]
        out = (I16*(count*2))(*scsp)
        expected = mix(original,bytes(out))
        at = 0
        while state.active and at < count:
            if state.phase >= 1152*256:
                if state.position >= state.end:
                    assert dll.m2_dsb_next_segment(C.byref(state),kind,rom,len(rom))
                    if not state.active:
                        break
                decode.put(SP+4,MUSIC+state.position,0x1078768)
                decode.run(0x4e9e50,count=20000000)
                consumed = decode.u.reg_read(UC_X86_REG_EAX)
                assert 0 < consumed < 4096
                rawframe=bytes(decode.u.mem_read(MUSIC+state.position,consumed))
                data=(U8*consumed).from_buffer_copy(rawframe)
                h=Header()
                assert dll.m2_dsb_frame_header(data,consumed,C.byref(h))
                assert h.bytes==consumed
                assert dll.m2_dsb_layer2(C.byref(f),data,consumed,C.byref(h),pcm)==1
                state.position += consumed
                laddr,raddr,n,rate = decode.get(0x1078768,4)
                assert n == 1152
                left = (I16*1152).from_buffer_copy(decode.u.mem_read(laddr,2304))
                right = (I16*1152).from_buffer_copy(decode.u.mem_read(raddr,2304))
                assert bytes(left)+bytes(right)==bytes(pcm), (frame,refills,'decoded PCM',next(
                    ((i, (list(left)+list(right))[i], v) for i,v in enumerate(pcm) if v!=(list(left)+list(right))[i]),None))
                left=(I16*1152).from_buffer_copy(pcm)
                right=(I16*1152).from_buffer_copy(pcm,2304)
                state.step = rate*256//44100
                state.phase = 0
                refills += 1
            dest = C.cast(C.byref(out,4*at),C.POINTER(I16))
            mixed = dll.m2_dsb_mix_decoded(C.byref(state),kind,left,right,dest,count-at)
            assert mixed > 0
            at += mixed
        assert expected == bytes(out), (frame, 'post-decode output')
        compare_state(original,state)
        digest.update(expected)
    return dict(stereo_frames=36*760, original_decoder_refills=refills,
                pcm_sha256=digest.hexdigest(), decoder='portable Layer II versus original x86')


class Filter(C.Structure):
    _fields_ = [('cosine', C.c_double*2048), ('history', C.c_float*2048), ('cursor',U32*2)]


def synthesis(exe, dll):
    o=Oracle(exe)
    o.u.reg_write(UC_X86_REG_FPCW,0x007f)
    o.u.mem_map(OUT,0x10000)
    o.run(0x4e9de0,count=100000)
    f=Filter()
    dll.m2_dsb_synthesis_init.argtypes=[C.POINTER(Filter)]
    dll.m2_dsb_synthesize.argtypes=[C.POINTER(Filter),U32,C.POINTER(C.c_double),C.POINTER(I16)]
    dll.m2_dsb_synthesis_init(C.byref(f))
    assert bytes(f.cosine) == bytes(o.u.mem_read(0x5a44a0,2048*8))
    digest=hashlib.sha256()
    for block in range(48):
        for ch in (0,1):
            bands=(C.c_double*32)(*[((j*31+ch*11+block*7)%19-9)/(1+(block%7)*11)
                                    for j in range(32)])
            o.u.mem_write(OUT, bytes(bands))
            o.put(SP+4,OUT,OUT+0x1000)
            o.run(0x4e9a70,{UC_X86_REG_ECX:ch},count=100000)
            got=(I16*32)()
            dll.m2_dsb_synthesize(C.byref(f),ch,bands,got)
            assert bytes(got)==bytes(o.u.mem_read(OUT+0x1000,64)), (block,ch,'PCM')
            cur=o.get(0x574de0+4*ch)[0]
            assert cur==f.cursor[ch]
            idx=1024*ch+cur
            history=struct.unpack('<64d',o.u.mem_read(0x5a04a0+8*idx,64*8))
            assert list(history)==list(f.history[idx:idx+64])
            digest.update(bytes(got))
    return dict(control_word='007f',cosine_entries=2048,blocks=96,pcm_samples=3072,
                history_words_checked=96*64,sha256=digest.hexdigest())


def layer1_frames(exe,dll):
    o=Oracle(exe)
    o.u.reg_write(UC_X86_REG_FPCW,0x007f)
    o.u.mem_map(OUT,0x10000)
    o.run(0x4e9de0,count=100000)
    filt=Filter()
    dll.m2_dsb_synthesis_init(C.byref(filt))
    dll.m2_dsb_layer1.argtypes=[C.POINTER(Filter),C.POINTER(U8),C.c_size_t,C.POINTER(Header),C.POINTER(I16)]
    got=(I16*2304)()
    cases=0
    for mode in (0,1,2,3):
        for ext in range(4):
            raw=bytearray([255,255,0xe8,(mode<<6)|(ext<<4)])
            channels=1 if mode==3 else 2
            bound=4*(ext+1) if mode==1 else 32
            bits=[]
            def append(value,n):
                bits.extend((value>>i)&1 for i in reversed(range(n)))
            alloc=[(i%15+1) if i%3==0 else 0 for i in range(32)]
            for b,n in enumerate(alloc):
                for ch in range(channels if b<bound else 1):
                    append(n,4)
            for b,n in enumerate(alloc):
                if n:
                    for ch in range(channels):
                        append((b+ch*13)%64,6)
            for k in range(12):
                for b,n in enumerate(alloc):
                    if n and n<15:
                        for ch in range(channels if b<bound else 1):
                            append((k*31+b*21+ch*3) & ((2<<n)-1),n+1)
            while len(bits)%8:
                bits.append(0)
            for i in range(0,len(bits),8):
                raw.append(sum(bit<<(7-j) for j,bit in enumerate(bits[i:i+8])))
            size=4*(12000*448//32000)
            raw.extend(bytes(size-len(raw)))
            o.u.mem_write(OUT,bytes(raw))
            o.put(SP+4,OUT,OUT+0x1000)
            o.run(0x4e9e50,count=10000000)
            assert o.u.reg_read(UC_X86_REG_EAX)==size
            data=(U8*size).from_buffer_copy(raw)
            h=Header()
            assert dll.m2_dsb_frame_header(data,size,C.byref(h))
            assert dll.m2_dsb_layer1(C.byref(filt),data,size,C.byref(h),got)==1
            left,right,n,rate=o.get(OUT+0x1000,4)
            assert n==384 and rate==32000
            assert bytes(got)==bytes(o.u.mem_read(left,2304))+bytes(o.u.mem_read(right,2304)),(mode,ext)
            cases+=1
    return cases


def layer2_frames(exe, dll):
    """Exercise allocation tables independently of the two retail stereo streams."""
    o = Oracle(exe)
    o.u.reg_write(UC_X86_REG_FPCW, 0x007f)
    o.u.mem_map(OUT, 0x10000)
    o.run(0x4e9de0, count=100000)
    o.run(0x4ea040, count=5000000)
    filt = Filter()
    dll.m2_dsb_synthesis_init(C.byref(filt))
    dll.m2_dsb_layer2.argtypes = [C.POINTER(Filter), C.POINTER(U8), C.c_size_t,
                                  C.POINTER(Header), C.POINTER(I16)]
    got = (I16*2304)()
    digest = hashlib.sha256()
    # bitrate index, sample-rate index, stereo/mono allocation table.
    # ROM fills use table 0 or 1; the low-bitrate choices also exercise 2 and 3.
    configs = [(4, 0, 2, 0), (4, 2, 3, 0), (8, 1, 0, 0), (10, 0, 1, 1)]
    cases = 0
    for bitrate, rate, stereo_table, mono_table in configs:
        for mode in range(4):
            channels = 1 if mode == 3 else 2
            table = mono_table if channels == 1 else stereo_table
            for ext in range(4):
                joint = 4*(ext+1) if mode == 1 else 32
                crc = ext & 1
                raw = bytearray([255, 252 | crc, (bitrate<<4) | (rate<<2), (mode<<6) | (ext<<4)])
                if not crc:
                    raw.extend(bytes.fromhex('a2b5'))
                header = Header()
                assert dll.m2_dsb_frame_header((U8*len(raw)).from_buffer(raw), len(raw), C.byref(header))
                bits = []
                def put(v,n):
                    bits.extend((v >> i) & 1 for i in reversed(range(n)))
                limit = [27,30,8,12][table]
                fields = []
                for b in range(limit):
                    width = (4 if b<2 else 3) if table>=2 else (4 if b<11 else 3 if b<23 else 2)
                    # Two separate low bands and one joint band. Untouched bands have no side information.
                    allocation = 0
                    code_width = 0
                    grouped = False
                    if b == 0:
                        allocation, code_width, grouped = 1, 5, True
                    elif b == 1:
                        if table == 0 and ext == 3:
                            allocation, code_width = 11, 0  # ElSemi's unmatched 4195 entry
                        elif table >= 2:
                            allocation, code_width, grouped = 3, 10, True
                        else:
                            allocation, code_width = 2, 3
                    elif b == min(joint,limit-1) and b > 1:
                        if table >= 2:
                            allocation, code_width = 4, 4
                        elif b < 23:
                            allocation, code_width = 3, 3
                        else:
                            allocation, code_width = 3, 16
                    fields.append((allocation,code_width,grouped))
                    for _ in range(channels if b<joint else 1):
                        put(allocation,width)
                for b,(a,_,_) in enumerate(fields):
                    if a:
                        for ch in range(channels):
                            put((b+ch+ext)%4,2)
                for b,(a,_,_) in enumerate(fields):
                    if a:
                        for ch in range(channels):
                            select = (b+ch+ext)%4
                            for k in range([3,2,1,2][select]):
                                put((ch*7+b+k*11+ext)%64,6)
                for group in range(12):
                    for b,(a,width,grouped) in enumerate(fields):
                        if a:
                            for ch in range(channels if b<joint else 1):
                                for sample in range(1 if grouped else 3):
                                    put((group*29 + ch*5 + b*7 + sample) & ((1<<width)-1),width)
                bits.extend([0]*(-len(bits)%8))
                for i in range(0,len(bits),8):
                    raw.append(sum(x<<(7-j) for j,x in enumerate(bits[i:i+8])))
                assert len(raw) <= header.bytes, (cases, len(raw), header.bytes)
                raw.extend(bytes(header.bytes-len(raw)))
                o.u.mem_write(OUT,bytes(raw))
                o.put(SP+4,OUT,OUT+0x1000)
                o.run(0x4e9e50,count=10000000)
                assert o.u.reg_read(UC_X86_REG_EAX) == len(raw), (cases,mode,ext)
                left,right,n,decoded_rate = o.get(OUT+0x1000,4)
                assert n == 1152 and decoded_rate == header.rate
                expected = bytes(o.u.mem_read(left,2304)) + bytes(o.u.mem_read(right,2304))
                data = (U8*len(raw)).from_buffer(raw)
                assert dll.m2_dsb_layer2(C.byref(filt),data,len(raw),C.byref(header),got) == 1
                assert bytes(got) == expected, (cases,mode,ext,table,next(
                    (i,a,v) for i,(a,v) in enumerate(zip(struct.unpack('<2304h',expected),got)) if a!=v))
                digest.update(expected)
                cases += 1
    return dict(frames=cases, stereo_buffer_samples_per_frame=2304, sha256=digest.hexdigest())


def board_boundaries(exe, dll):
    """Keep original stale sample buffers and zero-progress frame handling observable."""
    o, state, rom = fixture(exe,1)
    o.u.reg_write(UC_X86_REG_FPCW,0x007f)
    o.u.mem_map(MUSIC,0x40000)
    o.run(0x4e9de0,count=100000)
    o.run(0x4ea040,count=5000000)
    o.put(0x10787b8,MUSIC)
    o.put(0x107877c,OUT)
    o.put(0x1078784,OUT+0x8000)
    o.put(0x10787b4,44100)
    music=(U8*0x40000)()
    dll.m2_dsb_board_create.argtypes=[U32,C.POINTER(U8),C.c_size_t,C.POINTER(U8),C.c_size_t]
    dll.m2_dsb_board_create.restype=C.c_void_p
    dll.m2_dsb_board_command.argtypes=[C.c_void_p,U8]
    dll.m2_dsb_board_mix.argtypes=[C.c_void_p,C.POINTER(I16),C.c_size_t]
    dll.m2_dsb_board_error.argtypes=[C.c_void_p,C.POINTER(U32)]
    dll.m2_dsb_board_error.restype=C.c_char_p
    board=dll.m2_dsb_board_create(1,rom,len(rom),music,len(music))
    assert board
    pos=0x1123
    cases={}
    for label,raw in [('prime',bytes.fromhex('fffd8800')),('bad sync',b'\0'*4),
                      ('reserved layer',bytes.fromhex('fff90800')),('Layer III',bytes.fromhex('fffb8800')),
                      ('unassigned Layer II allocation',bytes.fromhex('fffd1800')),
                      ('free bitrate',bytes.fromhex('fffd0800'))]:
        # Seed a nonzero synthesized buffer for the subsequent no-decode branches.
        payload=bytearray(2048)
        payload[:4]=raw
        if label=='prime':
            payload[4]=0x10
            payload[32:100]=bytes(range(68))
        music[pos:pos+len(payload)]=payload
        o.u.mem_write(MUSIC+pos,bytes(payload))
        commands(o,[0xaf,0x6f,1])
        for value in (0xaf,0x6f,1): dll.m2_dsb_board_command(board,value)
        initial=[8191-i*5 for i in range(1520)]
        out=(I16*1520)(*initial)
        expected=mix(o,bytes(out))
        dll.m2_dsb_board_mix(board,out,760)
        assert dll.m2_dsb_board_error(board,None) is None
        assert bytes(out)==expected,label
        cases[label]=dict(position=o.get(0x1078758)[0],step=o.get(0x10787a8)[0],
                          sha256=hashlib.sha256(expected).hexdigest())
    # Joint stereo, boundary at band four. Bands 0..3 have two empty
    # four-bit allocations each. Band four has one shared grouped allocation.
    frame = bytes.fromhex('fffd8840 00000000 10') + bytes(512)
    music[pos:pos+len(frame)] = frame
    for value in (0xaf,0x6f,1):
        dll.m2_dsb_board_command(board,value)
    offset = U32()
    out = (I16*1520)(*initial)
    dll.m2_dsb_board_mix(board,out,760)
    message = dll.m2_dsb_board_error(board,C.byref(offset))
    assert message == b'native joint-stereo decoder stalled' and offset.value == pos
    assert list(out) == initial
    cases['native stall'] = dict(position=offset.value, error=message.decode())
    free=C.CDLL(None).free
    free.argtypes=[C.c_void_p]
    free(board)
    return cases


def joint_grouped_sample(exe):
    # A grouped code above the joint-stereo boundary enters 004ea870. Stop
    # after observing the repeating CPU state. No full game is run or hung.
    o=Oracle(exe)
    o.u.mem_map(OUT,0x10000)
    o.run(0x4ea040,count=5000000)
    block, header, stream = OUT, OUT+0x4000, OUT+0x5000
    o.put(block,27)
    o.put(header+0x20,2)
    o.put(header+0x28,4)
    o.put(block+4+4*4,1)  # shared band 4, allocation 1, three grouped levels
    o.put(0x59649c,stream)
    o.u.mem_write(stream,b'\xb0'+bytes(8))
    o.put(SP+4,block,header,0)
    indices=[]
    def iteration(u,addr,size,data):
        indices.append(u.reg_read(UC_X86_REG_ECX))
        if len(indices)==5:
            o.stop=addr
            u.emu_stop()
    o.u.hook_add(UC_HOOK_CODE,iteration,begin=0x4ea870,end=0x4ea870)
    o.u.ctl_flush_tb()
    o.run(0x4ea4d0,count=10000)
    assert indices==[0,1,1,1,1] and o.stop==0x4ea870
    assert o.u.reg_read(UC_X86_REG_ESI)==5
    return dict(subband=4,joint_bound=4,levels=3,loop_indices=indices,
                consumed_bits=5,observed_on_game_data=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--archive',type=Path,action='append',default=[])
    args=ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'dsb.so'
        subprocess.run(['cc','-shared','-fPIC','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',
                        str(ROOT/'port/snd/dsb_original.c'),str(ROOT/'port/snd/dsb_synthesis.c'),str(ROOT/'port/snd/dsb_mpeg.c'),str(ROOT/'port/snd/dsb_board.c'),'-lm','-o',str(path)],check=True)
        dll=bind(path)
        joint=joint_grouped_sample(args.exe)
        filter_result=synthesis(args.exe,dll)
        headers = frame_headers(args.exe,dll)
        boundaries = board_boundaries(args.exe,dll)
        layer1=layer1_frames(args.exe,dll)
        layer2=layer2_frames(args.exe,dll)
        command={kind:packets(args.exe,dll,kind) for kind in (1,2,3)}
        cases,digest=mixer(args.exe,dll)
        tracks = {p.stem:portable_track(args.exe,p,dll) for p in args.archive}
    result=dict(board_boundaries=boundaries,layer1_frames=layer1,layer2=layer2,joint_grouped_sample=joint,synthesis=filter_result,frame_header_cases=headers,packet_bytes_and_segment_transitions=command,decoded_mix_cases=cases,sha256=digest,tracks=tracks)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':
    main()
