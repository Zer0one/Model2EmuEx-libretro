#!/usr/bin/env python3
"""Compare selected real SCSP CPU read callbacks; record differences, not fixes.

Executes the original A68K DATA wrappers and their installed native SCSP
callbacks, with synthetic slot/ring/coefficient values. The portable side uses
the actual sound-board Musashi bus in check-dsp-integration. No game ROMs.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from a68k_boundary_compare import Oracle, DATA
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_EFLAGS

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path)
    ap.add_argument('--portable',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--require-match',action='store_true')
    args=ap.parse_args();o=Oracle(args.exe)
    # 004af2d4 installs this fixed SCSP object, not a host allocation token.
    assert o.pe.read(0x4af2d4,10)==bytes.fromhex('c705bc285700e8aa0901')
    chip=0x109aae8;o.put(0x5728bc,chip)
    for page in range(0x100,0x110):o.put(DATA+page*16,0,0x4ae870,0x4ae800,0x4ab220)
    o.u.mem_write(chip+0x32,b'\x57\x13')
    # Native StartSlot 004af713 sets this byte; StopSlot 004ab331 clears it.
    # Match the portable fixture's active slot, without claiming chip synthesis.
    assert o.pe.read(0x4af713,4)==bytes.fromhex('c6472001')
    o.u.mem_write(chip+0x50,b'\x01')
    o.u.mem_write(chip+0x11b0,b'\x68\x24')
    # Use the actual native coefficient write handler as well.
    o.run(0x4afa20,{UC_X86_REG_ECX:0x100700,UC_X86_REG_EDX:0x369a})
    portable=json.loads(subprocess.check_output([str(args.portable.resolve()),'--board-read-probe'],text=True))
    rows=[]
    for row in portable:
        entry={1:0x4b3250,2:0x4b3220,4:0x4b31f0}[row['width']]
        o.run(entry,{UC_X86_REG_ECX:row['address'],UC_X86_REG_EAX:0x12345678,UC_X86_REG_EDX:0x87654321})
        eax=o.u.reg_read(UC_X86_REG_EAX);value=eax&((1<<(row['width']*8))-1)
        rows.append(dict(address=f"{row['address']:08x}",width=row['width'],original_value=f'{value:08x}',
                         portable_value=f"{row['value']:08x}",same=value==row['value'],
                         original_eax=f'{eax:08x}',original_edx=f'{o.u.reg_read(UC_X86_REG_EDX):08x}',
                         original_flags=f'{o.u.reg_read(UC_X86_REG_EFLAGS):08x}'))
    result=dict(group='real_scsp_cpu_read_callbacks',cases=len(rows),differences=sum(not r['same'] for r in rows),rows=rows,
                original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),portable_sha256=hashlib.sha256(args.portable.read_bytes()).hexdigest(),
                limits=['Synthetic callback values; no game reachability claim.',
                        'Slot/ring/DSP CPU reads only; global/MIDI reads and scratch wiring remain separate.',
                        'Odd slot reads include native unaligned storage and the trailing active byte.'])
    root=Path(__file__).resolve().parents[1]
    paths=[Path(__file__),root/'scripts/check-dsp-integration.c',root/'port/snd/m2snd.c',root/'port/snd/scsp.c']
    result['sources_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sources_sha256'},indent=2))
    if args.require_match:assert result['differences']==0

if __name__=='__main__':main()
