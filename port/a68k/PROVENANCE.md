# A68K Reconstruction References

The original Windows CPU derives strongly from Mike Coates and Darren Olafson's
A68K. The public Make68K 0.30 generator retained in FBNeo has an exact one-to-one
dispatch partition match: 65,536 encodings and 1,667 distinct labels/targets.
See `tools/a68k_provenance.py` and `AUDIO_RE_ANALYSIS.md` for the pinned source,
reproducible comparison and limits. Exact source revision remains unidentified.

Use its function names, structure and explanatory comments as recovery aids.
Every behavior implemented here must still agree with the pinned ElSemi 1.1a
executable. Do not assume the library's current options or subsequent fixes were
present in that build. Preserve credits when using source-derived material.

| Recovered Area | Historical Generator Guide | Original-Specific Detail To Preserve |
| --- | --- | --- |
| Dispatch inventory | `JumpTable`, `CodeSegmentBegin` | Relative-address RLE table and exact opcode aliases. |
| Address calculation and bus access | `EffectiveAddressRead`, `EffectiveAddressWrite`, `Memory_Read`, `Memory_Write` | Original wrapper return high bits, map geometry and context-publication timing. |
| Unary arithmetic | `not` | NEGX uses width-limited ADC followed by NEG; CLR omits the hardware read. |
| Conditions and branches | `opcode5`, `branchinstructions` | Saved x86 flag-word effects, cycle boundaries, retained raw-PC high byte. |
| Software traps and USP transfers | `trap`, `trapv`, `moveusp` | TRAP/TRAPV exception-PC and zero-budget differences; privilege faults precede the fixed four-cycle charge. |
| Register test/set | `tas`, `tst` | TAS captures flags before modifying bit 7; native TST An aliases remain valid. |
| Decimal arithmetic | `abcd_sbcd`, `nbcd` | ABCD/SBCD preserve high flag bytes and copy C into N; NBCD imports PUSHFD after DAS and has separately qualified Windows flag evidence; memory forms publish full X only after the write callback. |
| Returns And Status Restoration | `ReturnandRestore`, `ReturnFromException`, `rts` | RTR/RTE publish the first stack read as PC before reading the return address; RTE re-enters IRQ with live state, and X receives the full lookup high byte. |
| Spaced And Paired Memory Access | `movep`, `cmpm` | MOVEP passes rotated full-width write arguments; CMPM increments source before reading destination, including shared An and A7 byte steps. |
| Register-List Transfers | `movem_reg_ea`, `movem_ea_reg` | MOVEM publishes its mask in saved flags, defers predecrement writeback and retains native postincrement/zero-budget behavior. |
| Status And Gated Entries | `movesr`, `ReturnandDeallocate`, `MoveControlRegister` | Preserve context+0x7c gating, MOVEC selector aliases and native PC conventions, including RTD reading at the opcode address. |
| RESET Output | `reset` emitter | Fetch successor before the optional callback and dispatch it even after a negative cycle budget. |
| Memory Arithmetic | `not`, `addx_subx`, `divides` | Preserve read-return scratch publication, second-read sticky Z, post-write NEG X and zero-divisor EDX. |
| Conditional Memory Stores | `opcode5` | Keep inherited or EA-produced EAX high bytes, SHI/SLS AH replacement, SF full zero and signed-condition IF publication. |
| Bounds Checks | `chk` | Preserve signed-word comparisons, asymmetric N masks and the memory wrapper return EDX consumed as live flags. |
| Multiplication | `mul` | Word MUL/IMUL followed by full-product TEST; fixed native cycles. |

The generator explains several unusual sequences already found in the binary.
An unusual sequence is not automatically an ElSemi modification: its origin
must be established by comparing the reference and native body. Conversely,
library origin does not authorize replacing that body with a corrected version.

This directory remains an isolated reconstruction module until complete CPU,
sound-board, scheduling, Save State and frontend qualification are finished.

## Confirmed Reference Differences

- IRQ entry: the public generator's `procint` emits `irq &= 0x7f` on the
  low byte, with a comment about explicit acknowledgement. The original
  `00462b1c` path instead clears the pending level with `irq &= 0xffffff78`.
  Keep the already-qualified original behavior; do not copy the library change.
- The public generator enables `QUICKZERO`; original recovered CLR bodies use
  explicit zero loads. Host flags can make that distinction observable.
- Native page wrappers use 4 KiB pages and partial AX/AL loads. Their behavior
  must come from the original wrappers, not assumptions about a library host API.
- NEGX's ADC-then-NEG and CLR's omitted read are already explained by the public
  generator. They are preserved quirks, not proven ElSemi-authored modifications.

- `divides()` emits CDQ/IDIV before the guest quotient-range check. The original
  exhibits the same host overflow for INT32_MIN / -1, so this is another
  source-explained boundary rather than a proven ElSemi-specific modification.
  See the native Windows-process probe and approved Stop Content / Original
  policy in AUDIO_RE_ANALYSIS.md.

## Additional Native Control Details

- `ReturnandDeallocate` and original `0048b5b4` omit the ordinary two-byte PC
  increment before the displacement read. With the normal dispatch binding,
  the opcode word itself supplies that displacement. The reconstruction keeps
  this behavior; a standard 68010 correction would be a separate change.
- The public `reset` emitter calls EAX directly. ElSemi `00486e9b` instead
  calls through `[EAX]`; its context token addresses a callback slot. The
  portable host binding preserves the call timing without dereferencing native
  process pointers.
- Original MOVEC decodes only extension selector bits 11 and 0. Other selector
  bits alias the four native SFC/DFC/USP/VBR slots. Both directions were checked
  over every 16-bit extension; no extra illegal-selector rejection is inserted.
- RESET's supervisor path fetches its successor before calling optional output,
  then jumps directly to the saved opcode regardless of remaining cycles. The
  portable `A68K_PREFETCHED` boundary and `prefetched_opcode` retain this for the
  observed execution loop. A null native callback token means no call; a nonzero
  token requires an explicitly bound host callback, never pointer conversion.
- Memory ADDX/SUBX reads host EDX scratch after memory wrappers rather than
  the saved guest flag word. These forms are now qualified with explicit
  second-read EDX observations. Real board provenance is still separate;
  memory BCD must not be copied there merely because the arithmetic is related.

## Read-Wrapper Scratch Provenance

The original READ/DATA wrappers at `004b3160..004b3273` return more than EAX
from the perspective of their callers. Direct reads leave the descriptor's
Windows base address in EDX. Word/byte callback paths enter their callback with
EDX zero; long callback paths enter with the callback address in EDX. The
callback can then change it. An ordinary C callback's return value alone cannot
represent those effects.

Memory CHK consumes that EDX as live flags, including its non-trapping tail.
The reconstructed observation API carries EAX and EDX separately; direct-map
bases are explicit integer tokens, never converted from a portable host pointer.
Missing provenance is a binding error before a callback runs. No guest value or
zero-register fallback is supplied. Ordinary value-only reads stay independent.

The tests vary original direct allocations and callback-return EDX. They do not
establish the real sound board's allocation bases or callback register results;
recovering those origins is still required before CPU/board integration. This
is an original-behavior dependency, not a proposed correction to the emulator.

## Conditional Store Entry Scratch

Memory Scc uses an explicit `entry_eax` observation where the native handler
retains EAX from its caller. Displacement and index modes derive EAX while
calculating the address; SF clears it. Only SHI/SLS replace AH from the low flag
byte using SAHF. Signed conditions retain the original IF-bit publication.
A missing required entry observation returns a binding error, not an invented
zero high word. All integer tokens remain separate from host pointers.

Per-handler comparisons provide entry EAX explicitly. The observed executor
now propagates qualified predecessor/callback results. Real sound-board
integration must still recover each callback's provenance. Internal connection
coverage does not establish a complete sound CPU. Do not wire these routines
into sound using constant entry EAX or an assumed C callback return convention.

## Continuous Execution And Historical Source Cross-Checks

`a68k_begin_observed` / `a68k_step_observed` extend the single-handler work with
explicit next-handler EAX and host control flags. All original target tokens
are connected, including accepted IRQ with explicitly observed callbacks.
Unknown tokens and unqualified host control/trap bits stop before execution. This is still a research execution
boundary, not a sound-board CPU. An instruction-budget exit invalidates the
next-entry observation: native `POPAD` restores the caller's registers.

The following details are checked against both the historical source and the
original executable, not inferred from architectural 68000 behavior:

| Source Guide | Original Detail Preserved Across Instructions |
| --- | --- |
| `moveq`, `movecodes`, `EffectiveAddressRead` | Source-derived EAX, full high bytes on narrow operands, source capture before register aliases change. |
| `opcode5` | Quick forms retain EAX; register Scc leaves its 4/6 cycle charge in EAX. Signed conditions restore DF from EDX through POPFD and publish IF. |
| `addx_subx` | Register ADC/SBB operates through EBX and Dn memory, leaving predecessor EAX untouched. |
| `asl_asr` | LAHF overwrites AH after Dn was stored. Zero-count, long ASL big-shift and immediate-one special paths differ. |
| `mul` | AX contains the product's low word with the source's high word retained; the full product is assembled separately in EDX/Dn. |
| `abcd_sbcd`, `nbcd` | Decimal register operations retain destination high bytes; NBCD starts from full EAX zero. |
| `Memory_Write` | Register-save flags determine whether callback EAX survives. Scc writes leave the callback result live; no generic void-return assumption. |

The reference generator's `Completed()` also explains why ordinary cycle
exhaustion uses JS while selected zero-cost tails use TEST/JLE. Reference
`QUICKZERO` and callback conventions are not copied over native differences.

### Original Caller EAX Origins

The entry at `00462b1c` does not initialize EAX when no IRQ is pending. A masked
IRQ leaves its level in EAX. Accepted IRQ likewise restores that level after
its exception; the observed API requires explicit callback provenance.

- `004b3050` receives the budget in EAX, stores it and calls at `004b3064`.
- Audio scheduler `004aefb0` calls at `004af01d` with its audio accumulator in
  EAX. The cycle allowance is independently formed in EDX as `0x110 - ESI`.
- Board scheduler `004cc710` first calls at `004cc736` with the board pointer
  still in EAX and a fixed budget of `0x4f`. Subsequent slices inherit EAX from
  the preceding `004a9e00` sound update; that native return remains to be bound.

These are integer observations, never portable process pointers. Sound-board
integration must recover each actual origin; budget-derived or zero EAX is not
a universal substitute.

### Write-Wrapper Return Observations

The original direct wrappers leave the descriptor token in EAX for byte/word
writes and the native map base for long writes. `a68k_write_observed` preserves
these tokens and requires explicit EAX/control-flag observations for callback
writes. Missing provenance fails before a write/callback; an invalid callback
result is rejected after that callback. The ordinary write API remains separate.
This API does not yet describe write-return EDX or implement native board
callbacks. Ordinary arithmetic/IF/DF host flags are qualified; other host
control and trap bits remain explicitly unrecovered, not silently masked.

## Source-Led Validation And Live Execution

User direction, 2026-11-04: reuse established historical-library source
correspondence and existing qualification for unchanged bodies. New dynamic
checks target ElSemi differences, portable adaptations and integration seams;
do not routinely repeat the whole arithmetic matrix. Source provenance is not
the same metric as executable integration. The complete dispatch partition
match establishes structure, not proof that every instruction body is unchanged.

`CodeSegmentBegin` supplies the RLE decoder and dispatch structure.
`dispatch_rle.inc` contains the original emulator-owned compressed table,
reproducible with `tools/a68k_inventory.py --emit-dispatch`; it contains no ROM
data. `a68k_init_dispatch` expands integer target identities, never executable
host addresses. The portable table matches all 65,536 original entries.
`a68k_run_live` continues live PC/flags and explicit scratch without re-entering
the CPU or adding a generic cycle check; native handler tails retain JS/JLE
ownership. Research step-limit pauses are distinct from native budget exits.
Unqualified paths remain explicit refusals; this is not a complete sound CPU.

`movecodes` / `Memory_Write` specifies the `---DS-B` preservation mask.
ElSemi's register/immediate MOVE writes likewise preserve the pre-write TEST
flags on the stack but leave wrapper/callback EAX and host control flags live.
The observed MOVE path adds only that portable connection; the ordinary
single-handler path and instruction semantics remain unchanged. Synthetic
callback checks cover all 46 target forms, byte/word/long widths and extension
fetches, including continuation consuming returned EAX and DF.

Evidence: `port/build-a68k-loop/{O0,O2,ubsan}.json` for the loop group and
`move-{O0,O2,ubsan}.json` for MOVE connections. Each receipt records the exact
source snapshot; earlier receipts are historical evidence, not assertions
that their source hashes match subsequent edits. See VALIDATION.md for counts.


### Read, Bulk, Control And Exception Connections

The new read observer carries native EAX, EDX and control flags independently.
`Memory_Read`/`Memory_Write` preservation masks guide memory producers and
consumers; `movep` restores EAX around writes, and MOVEM's empty mask leaves
EA scratch. Original `MemoryBanking` returns the descriptor offset from
004b30a0; portable binding returns this as explicit data, never a pointer.
Exception callbacks preserve native publication order and use DATA-long for
vector fetch. IRQ restores the saved level into EAX before the next handler.

A concrete historical-source difference is preserved: the inspected source
emits IRQ byte AND 0x7f, with older 0x78 commented out. ElSemi executes 0x78;
that binary instruction remains authoritative. `moveusp`, `trapv` and
`illegal_opcode` guide shared handler structure, with native timing and PC
adjustments retained. No correction of original CPU semantics is introduced.

Synthetic uninterrupted-dispatch checks qualify only new connections at
O0/O2/UBSan. They do not establish real sound-board callback provenance or
complete CPU integration. See VALIDATION.md for receipts and remaining scope.


### Remaining Internal Connections

Historical `ReturnandRestore`, `ReturnFromException`, `ReturnandDeallocate`,
`ReadCCR`, `WriteCCR`, `chk`, `divides`, `MoveControlRegister`, `stop` and
`reset` supply the established structure. Added observation plumbing follows
the pinned original's actual EAX/EDX/control and callback preservation.
Unchanged arithmetic is not requalified wholesale. RESET's original prefetch
occurs before its optional output callback; the saved opcode is dispatched
without a budget test even if the callback changes PC/flags/code. Portable
research pauses carry that pending opcode explicitly.

The observed-switch inventory now matches every original target token. That
is an internal dispatch milestone, not a real-board or complete CPU claim.
Native sound-board callback outputs and lifecycle/state integration still
need evidence. VALIDATION.md records scoped tests and source snapshots.


## Actual SCSP DATA Callback Read Observations — 2026-11-04

`scsp_cpu_read_observed` reconstructs EAX, EDX and arithmetic/control flags
for ordinary SCSP reads through DATA wrappers 004b31f0/3220/3250. The fixed
chip token is 0109aae8, installed by the original, not a portable pointer.
Slot byte reads retain its high EAX bytes; ring byte reads retain 004ae800.
Long reads return FFFFFFFF with callback token 004ab220 in EDX. Ring words
leave the chip token in EDX. Global MIDI and monitor reads carry their native
computed EDX; byte/word reads have different final flag-producing operations.

664 focused comparisons and 24 nonmutating unsupported-alias guards pass at
O0/O2/UBSan against original wrappers plus their real callbacks. Incoming
flag seeds vary arithmetic/DF state. Undefined x86 AF on logical/shift paths
follows the pinned oracle; this is not an architectural guarantee for every
x86 processor. Actual A68K page/board binding is still pending.

Raw aliases outside ordinary globals remain rejected by the research observer
before chip mutation, rather than receiving a fabricated observation. The
production Musashi read interface is unchanged by this helper. The original
0x444 alias can dequeue MIDI yet return slot bytes: helper side effects use
`offset & 0x3f`, while returned object bytes use `offset & 0xff`. Sample-base
fields in that object include Windows allocation tokens; do not substitute
portable addresses or choose a production virtual allocation policy silently.


## Global Write Completion And Actual Page Binding

`scsp_bus.c` connects the recovered observers through the real DATA/WRITE
page APIs. It deliberately has no ordinary-value fallback. Global write
completion reproduces the sparse table's EAX selector/CMP flags, fractional
timer result, SCIRE IRQ branch and SCILV final byte OR. Native 004af900 stores
both longword halves before invoking either update. The configured acknowledge
004aeac0 ends with OR EAX,-1 after checking pending sources. The live CPU
retains 004b3090, which executes OR EAX,-1 directly. The dispatcher clears
the accepted request before the call. The research bus now follows the live
path, including its returned flags. See VALIDATION.md for the differential
guest program and Windows observations.

The 960 writes and 576 acknowledgements, plus 1,344 nonmutating guards, pass
against native wrappers/callbacks at O0/O2/UBSan. Existing 664 read observations
and 24 guards also pass through actual bound page dispatch. The callback
binding is research code, not full sound-board/CPU lifecycle integration.
The user subsequently approved original DMA stores without transfer. The
write observer now handles them and returns sparse-table index 2 with the
original CMP flags. The expanded binding suite passes 1,168 writes and 576
acknowledgements plus 1,136 write guards at O0/O2/UBSan. Output MIDI, DSP, slot
and odd-word writes still do not fall back to a guessed observation. See VALIDATION.md for receipts and limits.

## SCSP Board Cold Start, Reset And Scanline Clock

Board setup at 004cd0f9 installs fetch/data for program and sample ROM. Program
stores return through the width-specific empty callbacks 004c69c0/d0/e0. At
004cd2e8 the fresh board copies the first 128 bytes of the configured CPU
template. It installs 004b3090 as the live autovector and 00572ab8 as an opaque
original token. The 33rd word starts at its PE initial value. At 00528ff0 the
48 vector-cost bytes precede the packed dispatch data. A byte-sized vector
index above 47 reads that same adjacent data. The C initializer reuses the
packed table and the oracle compares all 256 positions.

Warm board reset at 004cad80 copies the two vectors into existing RAM and
calls 004b33a0. In particular, this leaves the pending MIDI command and clock
phase live. At 004aefb0 the board runs A68K before each SCSP tick. It carries
the sub-256 clock remainder across scanlines and starts a new local cycle
residue each scanline. The original tests the template IRQ field for board
inhibit; the guest STOP field belongs to the live CPU instead. Synthetic
guest execution, including full register comparisons, is in VALIDATION.md.
