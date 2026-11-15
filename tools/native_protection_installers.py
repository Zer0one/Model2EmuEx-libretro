#!/usr/bin/env python3
"""Execute all four ElSemi protection installers on synthetic native contexts."""
import argparse,json,struct,sys
from pathlib import Path
from original_inventory import OriginalPE
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'port/sharc/test'))
from difftest_bits import load_original,SP,STOP
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 pe=OriginalPE(args.exe);uc=load_original(args.exe)
 board,cache=0x72000000,0x73000000
 uc.mem_map(board,0x204000);uc.mem_map(cache,0x100000)
 assert struct.unpack('<I',pe.read(0x5735bc,4))[0]==0x4c24d0
 stops=[]
 def stop_stub(u,at,size,opaque):
  stops.append(u.reg_read(UC_X86_REG_EAX));sp=u.reg_read(UC_X86_REG_ESP)
  ra=struct.unpack('<I',u.mem_read(sp,4))[0]
  u.reg_write(UC_X86_REG_ESP,sp+4);u.reg_write(UC_X86_REG_EIP,ra)
 uc.hook_add(UC_HOOK_CODE,stop_stub,begin=0x4c2670,end=0x4c2670)
 rows=[]
 for entry,patches in ((0x4c7e90,[0x4a58,0x6078]),(0x4c7f30,[0x5658]),(0x4c7fa0,[]),(0x4c8000,[0x5418])):
  uc.mem_write(board,bytes([0xa5])*0x204000);uc.mem_write(cache,bytes([0xa5])*0x100000)
  uc.mem_write(0x10ed940,struct.pack('<I',cache));uc.mem_write(SP,struct.pack('<I',STOP));stops.clear()
  uc.reg_write(UC_X86_REG_ESP,SP);uc.reg_write(UC_X86_REG_ECX,board)
  uc.emu_start(entry,STOP,count=2000);assert uc.reg_read(UC_X86_REG_EIP)==STOP
  reads=[];writes=[]
  for page in range(0x1d8,0x1e0):
   rd=struct.unpack('<4I',uc.mem_read(board+0x40+page*16,16))
   wr=struct.unpack('<4I',uc.mem_read(board+0x40+0x100000+page*16,16))
   assert rd==(0,0x4c73b0,0x4c7340,0x4c7330),(hex(entry),hex(page),rd)
   assert wr==(0,0x4c75e0,0x4c73d0,0x4c73c0),(hex(entry),hex(page),wr)
   reads.append(list(rd));writes.append(list(wr))
  expected=bytearray([0xa5])*0x100000
  for offset in patches:struct.pack_into('<I',expected,offset,0x5735bc)
  assert bytes(uc.mem_read(cache,len(expected)))==expected
  assert stops==([0x27e0] if entry==0x4c7e90 else [])
  rows.append(dict(entry=f'{entry:08x}',read_pages=reads,write_pages=writes,
   nop_guest_addresses=[(offset-0x18)//0x30*4 for offset in patches],stop_after=list(stops),
   board_flag_2f=uc.mem_read(board+0x2f,1)[0]))
 args.output.write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS: 4 original installers, 64 complete width-handler page records, exact cache patches/stop addresses')
if __name__=='__main__':main()
