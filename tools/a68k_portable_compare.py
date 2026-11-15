#!/usr/bin/env python3
"""Compare recovered C A68K primitives against unchanged ElSemi x86 bodies.

Reuses the independently checked Python models as a third implementation.
Builds the isolated module, never the production sound backend. No ROMs.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from a68k_boundary_compare import compare
from a68k_flow_compare import compare_flow, compare_faults
from a68k_register_compare import compare_registers
from a68k_map_compare import compare_maps
from a68k_control_compare import compare_control
from a68k_binary_compare import compare_binary
from a68k_operand_compare import compare_operands
from a68k_memory_compare import compare_memory
from a68k_memory_dest_compare import compare_memory_dest
from a68k_move_memory_compare import compare_move_memory
from a68k_rotate_compare import compare_rotates
from a68k_jump_compare import compare_jumps
from a68k_divide_compare import compare_divides
from a68k_software_trap_compare import compare_software_traps
from a68k_return_compare import compare_returns
from a68k_restore_compare import compare_restore
from a68k_movep_compare import compare_movep
from a68k_cmpm_compare import compare_cmpm
from a68k_movem_compare import compare_movem
from a68k_stop_compare import compare_stop
from a68k_status_compare import compare_status
from a68k_bcd_memory_compare import compare_bcd_memory
from a68k_later_cpu_compare import compare_later_cpu
from a68k_reset_instruction_compare import compare_reset_instruction
from a68k_chk_compare import compare_chk, compare_chk_memory
from a68k_unary_scratch_compare import compare_unary_scratch
from a68k_extend_memory_compare import compare_extend_memory
from a68k_divide_memory_compare import compare_divide_memory
from a68k_scc_memory_compare import compare_scc_memory
from a68k_bcd_compare import compare_bcd


class Portable:
    def __init__(self,library):
        self.library=C.CDLL(str(library))
        self.library.a68k_probe_cpu.argtypes=[C.c_uint,C.POINTER(C.c_uint32),C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)]
        self.library.a68k_probe_cpu.restype=C.c_int
        self.library.a68k_probe_memory.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)]
        self.library.a68k_probe_memory.restype=C.c_int

    @staticmethod
    def events(words,count):
        events=[]
        for i in range(count):
            kind,address,value=words[i*3:i*3+3]
            if kind==11:events.append(['reset'])
            elif kind>=5:events.append(['bus',kind,address,value])
            elif kind in (1,2):events.append(['write16' if kind==1 else 'write32',address,value])
            else:events.append([{0:'read32',3:'bind',4:'ack'}[kind],address])
        return events

    def cpu(self,operation,context,pc=0,flags=0,cycles=0,arg=0,target=0,ack=-1,direct=False,costs=None,host_flags=0x202,entry=0,extension=0,extension2=0,bus_value=0,bus_address=0,bus_direct=False,bus_width=4,write_direct=False,extension3=0,extension4=0,write_address=None,write_value=0,separate_write=False,script=None,reset_target_pc=None,reset_target_flags=0,bus_edx=None,script_edx=None,native_eax=None):
        values=context+[pc,flags,cycles,arg,target,ack,int(direct),host_flags,entry,extension,extension2,bus_value,bus_address,int(bus_direct),bus_width,int(write_direct),extension3,extension4,bus_address if write_address is None else write_address,write_value,int(separate_write)]
        if operation==9:values[44:47]=[reset_target_pc or 0,reset_target_flags,int(reset_target_pc is not None)]
        if operation==13:
            assert native_eax is not None
            values.append(native_eax)
        if operation in (10,11):
            assert bus_edx is not None
            values.append(bus_edx)
        if operation in (8,12):
            assert script is not None and len(script)<=32
            values += [len(script)]+[v for event in script for v in event]
            if operation==12:
                assert script_edx is not None and len(script_edx)==len(script)
                values += script_edx
        data=(C.c_uint32*len(values))(*(v&0xffffffff for v in values))
        cost=(C.c_uint8*256)(*(costs or [0]*256));out=(C.c_uint32*(1269 if operation in (8,12) else 213 if operation==9 else 212))()
        assert self.library.a68k_probe_cpu(operation,data,cost,out)
        result=dict(context=list(out[:33]),pc=out[33],flags=out[34],cycles=out[35],
                    boundary=out[36],fetch=out[37],events=self.events(out[39:],out[38]),
                    illegal_opcode=out[135],illegal_pc=out[136],fault=list(out[137:144]))
        if operation==9:result.update(prefetched_opcode=out[212],reset_context=list(out[144:177]))
        if operation in (8,12):result['script_context']=[list(out[213+i*33:246+i*33]) for i in range(out[212])]
        if operation in (5,6,7,10,11,13):result['bus_context']=list(out[144:177])
        if operation in (6,7,11,13):
            result.update(write_context=list(out[177:210]),written_value=out[210],memory_value=out[211])
        return result

    def memory(self,write,width,direct,address,value,ram,space=0):
        data=(C.c_uint8*len(ram)).from_buffer_copy(ram);out=(C.c_uint32*98)()
        assert self.library.a68k_probe_memory(2 if write else space,width,direct,address,value,data,out)
        return dict(value=out[0],ram=bytes(data),events=self.events(out[2:],out[1]))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--optimization',choices=('O0','O2'),default='O2')
    ap.add_argument('--ubsan',action='store_true')
    args=ap.parse_args();root=Path(__file__).resolve().parent.parent
    sources=[root/'port/a68k/a68k.c',root/'port/a68k/test/shim.c']
    with tempfile.TemporaryDirectory(prefix='model2-a68k-') as directory:
        library=Path(directory)/'a68k.dylib'
        command=['clang','-'+args.optimization,'-g','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-dynamiclib',*map(str,sources),'-o',str(library)]
        if args.ubsan:
            resource=subprocess.check_output(['clang','--print-resource-dir'],text=True).strip()
            command+=['-fsanitize=undefined','-fno-sanitize-recover=all','-shared-libsan','-Wl,-rpath,'+resource+'/lib/darwin']
        subprocess.run(command,check=True)
        portable=Portable(library)
        result=compare(args.exe,portable)
        result['opcode_flow']=compare_flow(args.exe,portable)
        result['odd_vector_policy']=compare_faults(args.exe,portable)
        result['register_ops']=compare_registers(args.exe,portable)
        result['map_installers']=compare_maps(args.exe,portable)
        result['control_ops']=compare_control(args.exe,portable)
        result['binary_ops']=compare_binary(args.exe,portable)
        result['operand_ops']=compare_operands(args.exe,portable)
        result['memory_source_ops']=compare_memory(args.exe,portable)
        result['memory_dest_ops']=compare_memory_dest(args.exe,portable)
        result['memory_operand_ops']=compare_memory_dest(args.exe,portable,immediate=True)
        result['memory_unary_ops']=compare_memory_dest(args.exe,portable,unary=True)
        result['address_ops']=compare_memory_dest(args.exe,portable,address_group=True)
        result['bit_ops']=compare_memory_dest(args.exe,portable,bit=True)
        result['move_dest_ops']=compare_memory_dest(args.exe,portable,transfer=True)
        result['move_memory_ops']=compare_move_memory(args.exe,portable)
        result['multiply_ops']=compare_memory(args.exe,portable,multiply=True)
        result['rotate_ops']=compare_rotates(args.exe,portable)
        result['shift_memory_ops']=compare_memory_dest(args.exe,portable,shift=True)
        result['shift_register_ops']=compare_rotates(args.exe,portable,shift=True)
        result['jump_ops']=compare_jumps(args.exe,portable)
        result['divide_ops']=compare_divides(args.exe,portable)
        result['software_trap_ops']=compare_software_traps(args.exe,portable)
        result['usp_ops']=compare_software_traps(args.exe,portable,usp=True)
        result['return_ops']=compare_returns(args.exe,portable)
        result['restore_ops']=compare_restore(args.exe,portable)
        result['movep_ops']=compare_movep(args.exe,portable)
        result['cmpm_ops']=compare_cmpm(args.exe,portable)
        result['movem_ops']=compare_movem(args.exe,portable)
        result['stop_ops']=compare_stop(args.exe,portable)
        result['later_cpu_ops']=compare_later_cpu(args.exe,portable)
        result['reset_instruction_ops']=compare_reset_instruction(args.exe,portable)
        result['chk_ops']=compare_chk(args.exe,portable)
        result['chk_memory_ops']=compare_chk_memory(args.exe,portable)
        result['unary_scratch_ops']=compare_unary_scratch(args.exe,portable)
        result['extend_memory_ops']=compare_extend_memory(args.exe,portable)
        result['divide_memory_ops']=compare_divide_memory(args.exe,portable)
        result['scc_memory_ops']=compare_scc_memory(args.exe,portable)
        result['status_move_ops']=compare_status(args.exe,portable)
        result['status_logic_ops']=compare_status(args.exe,portable,immediate=True)
        result['bcd_register_ops']=compare_bcd(args.exe,portable)
        result['bcd_memory_ops']=compare_bcd_memory(args.exe,portable)
        result['nbcd_ops']=compare_bcd(args.exe,portable,nbcd=True)
        instruction_groups=('register_ops','control_ops','binary_ops','operand_ops','memory_source_ops','memory_dest_ops','memory_operand_ops','memory_unary_ops','address_ops','bit_ops','move_dest_ops','move_memory_ops','multiply_ops','rotate_ops','shift_memory_ops','shift_register_ops','jump_ops','divide_ops','software_trap_ops','usp_ops','return_ops','restore_ops','movep_ops','cmpm_ops','movem_ops','stop_ops','later_cpu_ops','reset_instruction_ops','chk_ops','chk_memory_ops','unary_scratch_ops','extend_memory_ops','divide_memory_ops','scc_memory_ops','status_move_ops','status_logic_ops','bcd_register_ops','bcd_memory_ops','nbcd_ops')
        entries=result['opcode_flow']['cases']+sum(result[k]['covered_entries'] for k in instruction_groups)
        targets=4+sum(len(result[k]['targets']) for k in instruction_groups)
        all_targets=['00478438','0048b518','0048b540','0048b568']+[t for k in instruction_groups for t in result[k]['targets']]
        assert len(set(all_targets))==targets,'Instruction groups overlap; dispatch coverage would be double-counted.'
        result['dispatch_coverage']=dict(entries=entries,total_entries=65536,entry_percent=100*entries/65536,
            targets=targets,total_targets=1667,target_percent=100*targets/1667,
            note='Dispatch coverage, not weighted total CPU completion.')
        result['host_binding_guards']=portable.library.a68k_probe_host_contract()
    result.update(implementation='Portable C plus independent Python model against original x86',
                  optimization=args.optimization,ubsan=args.ubsan,
                  source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sources+[root/'port/a68k/a68k.h',root/'port/a68k/register_ops.inc',root/'port/a68k/control_ops.inc',root/'port/a68k/binary_ops.inc',root/'port/a68k/operand_ops.inc',root/'port/a68k/memory_move_ops.inc',root/'port/a68k/memory_binary_ops.inc',root/'port/a68k/memory_dest_ops.inc',root/'port/a68k/memory_operand_ops.inc',root/'port/a68k/memory_address_ops.inc',root/'port/a68k/memory_unary_ops.inc',root/'port/a68k/address_ops.inc',root/'port/a68k/bit_ops.inc',root/'port/a68k/move_dest_ops.inc',root/'port/a68k/move_memory_ops.inc',root/'port/a68k/multiply_ops.inc',root/'port/a68k/rotate_ops.inc',root/'port/a68k/shift_memory_ops.inc',root/'port/a68k/shift_register_ops.inc',root/'port/a68k/jump_ops.inc',root/'port/a68k/divide_ops.inc',root/'port/a68k/software_trap_ops.inc',root/'port/a68k/usp_ops.inc',root/'port/a68k/return_ops.inc',root/'port/a68k/memory_sequence_ops.inc',root/'port/a68k/movem_ops.inc',root/'port/a68k/status_ops.inc',root/'port/a68k/chk_ops.inc',root/'port/a68k/memory_scratch_ops.inc',root/'port/a68k/extend_memory_ops.inc',root/'port/a68k/divide_memory_ops.inc',root/'port/a68k/scc_memory_ops.inc',root/'port/a68k/bcd_register_ops.inc',root/'port/a68k/bcd_memory_ops.inc',root/'port/a68k/nbcd_ops.inc',Path(__file__),root/'tools/a68k_boundary_compare.py',root/'tools/a68k_flow_compare.py',root/'tools/a68k_register_compare.py',root/'tools/a68k_map_compare.py',root/'tools/a68k_control_compare.py',root/'tools/a68k_binary_compare.py',root/'tools/a68k_operand_compare.py',root/'tools/a68k_memory_compare.py',root/'tools/a68k_memory_dest_compare.py',root/'tools/a68k_move_memory_compare.py',root/'tools/a68k_rotate_compare.py',root/'tools/a68k_jump_compare.py',root/'tools/a68k_divide_compare.py',root/'tools/a68k_software_trap_compare.py',root/'tools/a68k_return_compare.py',root/'tools/a68k_restore_compare.py',root/'tools/a68k_movep_compare.py',root/'tools/a68k_cmpm_compare.py',root/'tools/a68k_movem_compare.py',root/'tools/a68k_stop_compare.py',root/'tools/a68k_status_compare.py',root/'tools/a68k_later_cpu_compare.py',root/'tools/a68k_reset_instruction_compare.py',root/'tools/a68k_chk_compare.py',root/'tools/a68k_unary_scratch_compare.py',root/'tools/a68k_extend_memory_compare.py',root/'tools/a68k_divide_memory_compare.py',root/'tools/a68k_scc_memory_compare.py',root/'tools/a68k_bcd_compare.py',root/'tools/a68k_bcd_memory_compare.py']})
    result['limits'][0]='Recovered C primitives only; no complete dispatcher, sound-board integration or executable CPU replacement.'
    result['limits'][3]='MOVEQ checks defined guest NZVC/X and parity; undefined x86 AF and host control bits are not guest claims.'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
