#!/usr/bin/env python3
"""Target only the new portable RLE decoder and live dispatch connections.

Historical Make68K CodeSegmentBegin/Completed supplies the structure; ElSemi
remains the binary authority. This deliberately does not rerun arithmetic
qualification or the full single-handler/sequence matrices.
"""
import argparse
import ctypes as C
import hashlib
import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path
from a68k_sequence_compare import ChainOracle, ROOT, WORDS, words


def compare(exe, lib, move_writes=False):
    p=C.CDLL(str(lib));o=ChainOracle(exe)
    init=p.a68k_init_dispatch
    init.argtypes=[C.POINTER(C.c_uint32),C.c_size_t];init.restype=C.c_int
    table=(C.c_uint32*65536)();assert init(table,65536)
    assert list(table)==o.table
    table_hash=hashlib.sha256(struct.pack('<65536I',*table)).hexdigest()
    fn=p.a68k_probe_loop
    fn.argtypes=[C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint32)]
    fn.restype=C.c_int
    cases=0;native_runs=0;digest=hashlib.sha256()
    # Each stream targets a connection, not an arithmetic opcode inventory.
    programs={
        'live_vs_published': [0x70ff,0x4e71,0x7201,0x4e71],
        'extension_fetch': [(0x203c,0x1234,0x5678),0x4e71,0x50c1,0x4e71],
        'callback_eax_df': [0x50d0,0x4e71,0x5cd0,0x70ff,0x4e71],
        'signed_condition_df': [0x5cc0,0x7201,0x51d0,0x4e71],
    }
    new_targets=set()
    if move_writes:
        programs={}
        specs=re.findall(r'A68K_MOVE_DEST\((0x[0-9a-f]+), MOVE, (\d+), \d+, (\w+), (\w+)\)',
                         (ROOT/'port/a68k/move_dest_ops.inc').read_text())
        for target,bits,mode,source in specs:
            target=int(target,16);new_targets.add(target)
            op=next(op for op,t in enumerate(o.table) if t==target)
            extension=[]
            if source=='IMMEDIATE_LOW':extension=[0x89ab,0xcdef] if int(bits)==32 else [0x89ab]
            if mode in ('DISP16','INDEXED','ABS16'):extension+=[0x1023]
            elif mode=='ABS32':extension+=[0x0012,0x3456]
            # Scc consumes the MOVE callback's EAX; MOVEQ then captures the
            # outgoing host DF. Instruction semantics are already qualified.
            programs[f'move_write_{target:08x}']=[(op,*extension),0x4e71,0x50d1,0x72ff,0x4e71]
    for name,code in programs.items():
        program=words(code);ops=(C.c_uint16*len(program))(*program)
        for budget in ((0,1000) if move_writes else (0xffffffff,0,3,4,5,16,1000)):
            for mode in (0,1):
                context=[(0x12345678+i*0x01020304)&0xffffffff for i in range(33)]
                context[20]=0x1000;context[17]=0x27;context[21]=3 if mode else 0
                context[18]=0x602 if mode else 0x243;context[19]=mode;context[8]=0x123456
                eax=0x89abcdef;host=0x202;callback=0x76543210;toggle=0x400 if mode else 0
                native,writes=o.stream(context,budget,eax,host,code,False,callback,toggle)
                native_runs+=1;expected=native[-1];expected_steps=len(native)-1
                for chunk in ((1,128) if move_writes else (1,2,128)):
                    data=(C.c_uint32*38)(*context,budget,eax,host,callback,toggle)
                    out=(C.c_uint32*(2+WORDS+2*len(code)))()
                    assert fn(data,ops,len(program),len(code),chunk,out)
                    actual=list(out[2:2+WORDS]);want=expected.copy()
                    if not actual[38]:want[36:38]=actual[36:38]
                    key=(name,budget,mode,chunk)
                    assert out[0]==expected_steps,(key,'steps',out[0],expected_steps)
                    assert actual==want,(key,actual,want)
                    actual_writes=[list(out[2+WORDS+2*i:2+WORDS+2*i+2]) for i in range(out[1])]
                    assert actual_writes==writes,(key,actual_writes,writes)
                    digest.update(json.dumps([key,actual,actual_writes]).encode());cases+=1
    guards=p.a68k_probe_loop_guards();assert guards==9,guards
    return dict(group='move_write_scratch' if move_writes else 'live_loop',
                native_streams=native_runs,portable_comparisons=cases,guards=guards,
                mismatches=0,decoded_entries=65536,decoded_table_sha256=table_hash,
                new_scratch_targets=len(new_targets),new_scratch_encodings=sum(t in new_targets for t in o.table),
                result_sha256=digest.hexdigest(),limits=[
                    'Targeted loop/decoder changes only; unchanged arithmetic relies on source correspondence and prior qualification.',
                    'Research chunk boundaries preserve live state; native execution has no injected scratch or per-handler re-entry.',
                    'No full CPU, native board callback, scheduler, state or frontend claim. MOVE mode tests only its new write-scratch connection.'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('exe',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--optimization',choices=('O0','O2'),default='O2');ap.add_argument('--ubsan',action='store_true')
    ap.add_argument('--move-writes',action='store_true',help='Only the newly observed MOVE write-return connection')
    ap.add_argument('--memory-reads',action='store_true',help='Only newly connected memory-source/MOVE-memory/MUL read returns')
    ap.add_argument('--memory-rmw',action='store_true',help='Only newly connected read/modify/write and unary memory paths')
    ap.add_argument('--memory-misc',action='store_true',help='Only bit/shift and paired BCD/extend memory connections')
    ap.add_argument('--memory-bulk',action='store_true',help='Only MOVEP/CMPM/MOVEM connections, including empty register masks')
    ap.add_argument('--control-basic',action='store_true',help='Only address/stack and DBcc scratch connections')
    ap.add_argument('--control-flow',action='store_true',help='Only even-target branch/call/jump and binding connections')
    ap.add_argument("--interrupt-entry",action="store_true",help="Only accepted IRQ bus/binder and next-instruction connections")
    ap.add_argument("--exception-entry",action="store_true",help="Only software exception and USP connections")
    ap.add_argument("--odd-flow",action="store_true",help="Only odd branch/jump destinations through vector 3")
    ap.add_argument("--return-flow",action="store_true",help="Only stack-return/status/IRQ continuation connections")
    ap.add_argument("--status-flow",action="store_true",help="Only SR/CCR bus/IRQ and next-handler connections")
    ap.add_argument("--checked-arithmetic",action="store_true",help="Only CHK/DIV scratch and exception connections")
    ap.add_argument("--final-control",action="store_true",help="Only MOVEC/STOP/RESET and prefetch continuation connections")
    args=ap.parse_args()
    sources=[ROOT/'port/a68k/a68k.c',ROOT/'port/a68k/test/sequence_shim.c']
    with tempfile.TemporaryDirectory(prefix='model2-a68k-loop-') as d:
        lib=Path(d)/'loop.dylib';command=['clang','-'+args.optimization,'-g','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-dynamiclib',*map(str,sources),'-o',str(lib)]
        if args.ubsan:
            resource=subprocess.check_output(['clang','--print-resource-dir'],text=True).strip()
            command+=['-fsanitize=undefined','-fno-sanitize-recover=all','-shared-libsan','-Wl,-rpath,'+resource+'/lib/darwin']
        subprocess.run(command,check=True)
        if args.final_control:
            from a68k_read_chain_compare import compare_final_control
            result=compare_final_control(args.exe,lib)
        elif args.checked_arithmetic:
            from a68k_read_chain_compare import compare_checked
            result=compare_checked(args.exe,lib)
        elif args.status_flow:
            from a68k_read_chain_compare import compare_status
            result=compare_status(args.exe,lib)
        elif args.return_flow:
            from a68k_read_chain_compare import compare_returns
            result=compare_returns(args.exe,lib)
        elif args.exception_entry:
            from a68k_read_chain_compare import compare_traps
            result=compare_traps(args.exe,lib)
        elif args.interrupt_entry:
            from a68k_read_chain_compare import compare_irq
            result=compare_irq(args.exe,lib)
        elif args.control_flow or args.odd_flow:
            from a68k_read_chain_compare import compare_flow
            result=compare_flow(args.exe,lib,args.odd_flow)
        elif args.memory_reads or args.memory_rmw or args.memory_misc or args.memory_bulk or args.control_basic:
            from a68k_read_chain_compare import compare as compare_reads
            result=compare_reads(args.exe,lib,args.memory_rmw,args.memory_misc,args.memory_bulk,args.control_basic)
        else:result=compare(args.exe,lib,args.move_writes)
    result.update(original_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest(),optimization=args.optimization,ubsan=args.ubsan)
    paths=[Path(__file__),ROOT/'tools/a68k_sequence_compare.py',ROOT/'tools/a68k_boundary_compare.py',ROOT/'tools/a68k_inventory.py',ROOT/'tools/original_inventory.py',ROOT/'tools/scsp_dsp_compare.py',ROOT/'port/a68k/a68k.h',*sources,*sorted((ROOT/'port/a68k').glob('*.inc'))]
    if args.memory_reads or args.memory_rmw or args.memory_misc or args.memory_bulk or args.control_basic or args.control_flow or args.interrupt_entry or args.exception_entry or args.odd_flow or args.return_flow or args.status_flow or args.checked_arithmetic or args.final_control:paths.append(ROOT/'tools/a68k_read_chain_compare.py')
    result['sources_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sources_sha256'},indent=2))


if __name__=='__main__':main()
