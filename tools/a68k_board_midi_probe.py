#!/usr/bin/env python3
"""Original SCSP command FIFO versus inherited board, without game ROMs.

The native enqueue fragment stops before unrelated host/thread notification.
The native dequeue executes the complete SCSP word-read callback. Results are
observations for a semantic decision; no production fix is applied by this tool.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
from a68k_boundary_compare import Oracle
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path)
    ap.add_argument('--portable',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();o=Oracle(a.exe);o.put(0x5728bc,0x109aae8)
    o.u.mem_write(0x10ed9d8,b'\0\0');o.u.mem_write(0x1078799,b'\0')
    for value in range(1,41):o.run(0x4c868a,{UC_X86_REG_ECX:value},stops=(0x4c86a8,))
    after_enqueue={'write_index':o.u.mem_read(0x10ed9d8,1)[0],'read_index':o.u.mem_read(0x10ed9d9,1)[0],'counter':o.u.mem_read(0x1078799,1)[0]}
    native=[]
    for _ in range(40):
        o.run(0x4ae800,{UC_X86_REG_ECX:0x100404});native.append(o.u.reg_read(UC_X86_REG_EAX)&65535)
    assert native==list(range(1,41))
    portable=json.loads(subprocess.check_output([str(a.portable.resolve()),'--midi-read-probe'],text=True))
    result={'group':'SCSP command FIFO capacity and CPU dequeue','commands':40,'native':native,'portable':portable,
            'same':native==portable,'original_after_enqueue':after_enqueue,
            'original_sha256':hashlib.sha256(a.exe.read_bytes()).hexdigest(),'portable_sha256':hashlib.sha256(a.portable.read_bytes()).hexdigest(),
            'limits':['Synthetic burst, not game reachability.','Native enqueue stop excludes Windows thread notification.','Model 1 FIFO and Manx TT auxiliary UART are separate.']}
    root=Path(__file__).resolve().parents[1]
    result['sources_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),root/'scripts/check-dsp-integration.c',root/'port/snd/m2snd.c',root/'port/snd/scsp.c')}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
