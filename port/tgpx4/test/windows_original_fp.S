/* cdecl (input, output), 32-bit Windows. Invoke the ORIGINAL EXE body at its
 * original VA, preserving the host's complete FP/SSE state. ROM-free fixture. */
.text
.globl _model2c_original_fp
_model2c_original_fp:
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
    movl %eax, 0x31011fec
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
