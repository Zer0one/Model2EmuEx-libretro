#!/usr/bin/env python3
"""Compare recovered cross-object protection copies with original ElSemi x86.

The neighboring objects are seeded according to their native owners: timing,
no external session, no optional DSB, untouched Model 2 bank latch. This checks
that the board bus supplies live timing and known object values, not a frozen
whole-process capture. No game ROMs or Windows UI are needed.
"""
import argparse,ctypes as C,json,random,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'port/sharc/test'))
from difftest_bits import load_original,SP,STOP
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESP,UC_X86_REG_EIP

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('exe',type=Path);p.add_argument('library',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 u=load_original(a.exe);lib=C.CDLL(str(a.library.resolve()));fn=lib.protection_alias_case
 fn.argtypes=[C.c_uint]*3+[C.c_void_p]*3
 rng=random.Random(0x574da8);cases=0
 commands=(0x10,0x935,0x1049,0x113d,0x1326,0x13cd,0x234d,0x3422,0x4d53,0x556d,0x7140,0x7700,0x983c,0x9845,0x98cc,0x993d,0xa1bc,0xad23)
 for selector in range(366):
  for command in commands:
   fps=rng.randrange(1,121);initial=rng.randbytes(256)
   u.mem_write(0x5aa770,initial);u.mem_write(0x10ed908,struct.pack('<II',19,selector))
   u.mem_write(0x574da8,struct.pack('<I',0xc00000))
   u.mem_write(0x574dcc,struct.pack('<f6I',float(fps),0xff,0xff,0x1c0,1,64,64))
   u.mem_write(SP,struct.pack('<I',STOP));u.reg_write(UC_X86_REG_ESP,SP)
   u.reg_write(UC_X86_REG_ECX,0x1d9000c);u.reg_write(UC_X86_REG_EDX,command)
   u.emu_start(0x4c73d0,STOP,count=5000);assert u.reg_read(UC_X86_REG_EIP)==STOP
   output=(C.c_uint8*256)();state=(C.c_uint32*4)()
   fn(selector,command,fps,initial,output,state)
   assert not state[2],(selector,hex(command),hex(state[3]))
   assert bytes(output)==bytes(u.mem_read(0x5aa770,256)),(selector,hex(command),fps)
   assert list(state)[:2]==list(struct.unpack('<II',u.mem_read(0x10ed908,8)))
   cases+=1
 a.output.write_text(json.dumps({'cases':cases,'selectors':[0,365],'commands':len(commands),'fps_domain':[1,120],'source_objects':['response tables','Model 2 ROM-bank latch','93C46 interface','previous machine rate','inactive external-link globals','inactive DSB cursors','two immutable PNG resources']},indent=2)+'\n')
 print('PASS:',cases,'original/board-bus response copies with varied live timing and exact adjacent native objects')
if __name__=='__main__':main()
