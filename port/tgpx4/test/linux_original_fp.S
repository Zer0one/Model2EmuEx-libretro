/* cdecl (input, output), 32-bit Linux. Invoke the ORIGINAL EXE body at its
 * original VA, preserving the host's complete FP/SSE state. ROM-free fixture, no PE relocations. */
.text
.globl original_fp
original_fp:
    pushl %ebp
    pushl %ebx
    pushl %esi
    pushl %edi
    movl 20(%esp), %esi
    movl 24(%esp), %edi
    fxsave 0x30001000
    fninit
    fldenv 28(%esi)
    ldmxcsr 0x30001300
    movl 4(%esi), %eax
    movl %eax, 0x30001200
    movl 8(%esi), %eax
    movl %eax, 0x30001204
    movl 12(%esi), %eax
    movl %eax, 0x30000310
    movl 24(%esi), %eax
    movl %eax, 0x10f1fec
    calll *(%esi)
    movl %eax, (%edi)
    movl 0x30000310, %eax
    movl %eax, 4(%edi)
    fnstcw 8(%edi)
    fnstsw 12(%edi)
    fxrstor 0x30001000
    popl %edi
    popl %esi
    popl %ebx
    popl %ebp
    retl

.globl _start
_start:
    movl %esp, %eax
    pushl %eax
    call probe_main
    movl %eax, %ebx
    movl $1, %eax
    int $0x80
.globl syscall6
syscall6:
    pushl %ebp
    pushl %ebx
    pushl %esi
    pushl %edi
    movl 20(%esp), %eax
    movl 24(%esp), %ebx
    movl 28(%esp), %ecx
    movl 32(%esp), %edx
    movl 36(%esp), %esi
    movl 40(%esp), %edi
    movl 44(%esp), %ebp
    int $0x80
    popl %edi
    popl %esi
    popl %ebx
    popl %ebp
    retl
.section .note.GNU-stack,"",@progbits
