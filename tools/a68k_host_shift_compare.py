#!/usr/bin/env python3
"""Cross-check x86 shift instructions under Rosetta and the Unicorn oracle.

This is supplementary host-ISA evidence, not execution of the Windows emulator
under Rosetta, nor a guarantee for ISA-undefined flags on all physical CPUs.
"""
import argparse
import collections
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EFLAGS


def compare():
    root = Path(__file__).resolve().parents[1]
    source = root/'port/a68k/test/host_shift.c'
    with tempfile.TemporaryDirectory(prefix='a68k-host-shift-') as directory:
        binary = Path(directory)/'host-shift'
        subprocess.run(['clang', '-arch', 'x86_64', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(source), '-o', str(binary)], check=True)
        output = subprocess.check_output(['arch', '-x86_64', str(binary)])
    assert len(output) == 3*3*64*12*24
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(0x1000, 0x1000)
    counts, differences = collections.Counter(), collections.Counter()
    examples = []
    for operation, bits, count, value, result, flags in struct.iter_unpack('<6I', output):
        # SHR / SHL / SAR AL,AX,EAX by CL; original operand sizes unchanged.
        code = (b'\x66' if bits == 16 else b'') + bytes([
            0xd2 if bits == 8 else 0xd3, (0xe8, 0xe0, 0xf8)[operation]])
        u.mem_write(0x1000, code)
        u.ctl_remove_cache(0x1000, 0x1010)
        u.reg_write(UC_X86_REG_EAX, value)
        u.reg_write(UC_X86_REG_ECX, count)
        u.reg_write(UC_X86_REG_EFLAGS, 0x202)
        u.emu_start(0x1000, 0x1000+len(code), count=1)
        other_result = u.reg_read(UC_X86_REG_EAX)
        other_flags = u.reg_read(UC_X86_REG_EFLAGS)
        assert result == other_result, (operation, bits, count, hex(value), 'value')
        difference = (flags ^ other_flags) & 0x8d5
        assert not (difference & ~0x800), 'Observed result-relevant flag disagreement'
        assert not difference or (count & 31) != 1, 'Single-bit overflow disagreement'
        if difference:
            differences[f'{difference:03x}'] += 1
            if len(examples) < 12:
                examples.append(dict(operation=operation, bits=bits, count=count,
                    value=f'{value:08x}', rosetta_flags=f'{flags:08x}', unicorn_flags=f'{other_flags:08x}'))
        counts[f'{("SHR","SHL","SAR")[operation]}{bits}'] += 1
    return dict(cases=sum(counts.values()), groups=dict(counts), result_mismatches=0,
                flag_difference_masks=dict(differences), nzpc_af_mismatches=0, single_bit_overflow_mismatches=0, examples=examples,
                rosetta_output_sha256=hashlib.sha256(output).hexdigest(),
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                limits=['Isolated original-form instructions compiled for x86-64 and run under Rosetta, not the Windows binary.',
                        'Flags undefined by the x86 ISA remain implementation-dependent even where both engines agree.'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
