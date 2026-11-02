#!/usr/bin/env python3
"""Generate synthetic, CRC-correct sound chips and run ROM-free Manx checks."""
import argparse,json,subprocess,zlib,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
games=json.loads((root/'src/libretro/data/mame_model2_catalog.json').read_text())['games']
def forge(data,target):
    """Solve the final four bytes over GF(2); these are synthetic filler."""
    data[-4:]=bytes(4);base=zlib.crc32(data);basis={}
    for bit in range(32):
        data[-4+bit//8]^=1<<(bit%8);v=zlib.crc32(data)^base;data[-4+bit//8]^=1<<(bit%8);mask=1<<bit
        while v:
            pivot=v.bit_length()-1
            if pivot not in basis:basis[pivot]=(v,mask);break
            v^=basis[pivot][0];mask^=basis[pivot][1]
    v=target^base;mask=0
    while v:
        pivot=v.bit_length()-1;v^=basis[pivot][0];mask^=basis[pivot][1]
    data[-4:]=mask.to_bytes(4,'little');assert zlib.crc32(data)==target
    return data
for name in ('manxtt','manxttc'):
    game=next(g for g in games if g['name']==name)
    with zipfile.ZipFile(out/(name+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for f in game['mame_files']+game['not_consumed']:
            if f['region'] not in ('audiocpu','samples','M1AUDIO_CPU_REGION','M1AUDIO_MPCM1_REGION'):continue
            data=bytearray(f['size'])
            if f['region'] in ('audiocpu','M1AUDIO_CPU_REGION'):
                def word(offset,value):data[offset:offset+2]=value.to_bytes(2,'little')
                word(0,7 if f['region']=='audiocpu' else 0xf0);word(2,0xff00)
                word(4,0x60 if f['region']=='audiocpu' else 0);word(6,0x100);word(0x100,0x60fe)
            elif f['region']=='M1AUDIO_MPCM1_REGION':
                import math
                data[1]=1;data[5]=0xff;data[8]=0xf0
                for i in range(256):data[0x100+i]=int(30*math.sin(2*math.pi*i/64))&255
            z.writestr(f['name'],forge(data,f['crc']))
build=root/'port/build-libretro-macos'
objects=[build/x for x in ('i960/i960.o','tgp/tgp.o','m2/m2board.o','m2/m2rom.o','snd/m2snd.o','snd/scsp.o','snd/multipcm.o','snd/ym3438.o','snd/m2uart.o','snd/sm2/hw/i8251.o','m68k/m68kcpu.o','m68k/m68kops.o','m68k/softfloat/softfloat.o','ymfm/ymfm_opn.o','ymfm/ymfm_adpcm.o','ymfm/ymfm_ssg.o','sm2/nvram_settings.o','sm2/save_ram.o','sm2/core/log.o')]
binary=out/'check-manxtt-audio'
subprocess.run(['clang++','-std=c++20','-O2','-DM2_CABINET_AUDIO','-Iport','-Isrc/libretro/include','-Isrc/libretro/sm2/include','scripts/check-manxtt-audio.cpp',*map(str,objects),'-lz','-lm','-o',str(binary)],cwd=root,check=True)
subprocess.run([str(binary),str(out)],cwd=root,check=True)
