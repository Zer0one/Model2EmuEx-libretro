# Original Audio Reconstruction Boundaries

Updated: 2026-11-04. This records the audio-classification and DSP reconstruction groups of M30, following
the inherited Model 2/2A qualification. It identifies recoverable native work
and reusable test boundaries. The standard Libretro build defaults to the reconstructed A68K/SCSP/DSP path, **Model2Emu (ElSemi)**. **Model2EmuEx** selects the standalone SCSP board. The dated sections below record the stages that preceded whole-board selection. Current ownership and remaining work are in [the inventory](RE_INVENTORY.md) and [the roadmap](ROADMAP.md).

Current disposition — 2026-11-15: all eight ElSemi audio adoption groups are
closed. M30 is Deferred for optional follow-up research under the user decision
recorded in ROADMAP.md. The dated checkpoints below preserve historical
findings, including intermediate pending work superseded by later integration;
use ROADMAP.md for current activity status.

## A68K Dispatch Classification

The previously verified compressed dispatch expands to 65,536 opcode entries
and 1,667 original code destinations. `tools/audio_re_inventory.py` associates
every entry with a first-word label from the existing Musashi 68000 disassembler.
The labels use synthetic zero extension words, not game code.

| Measurement | Result |
| --- | ---: |
| Dispatch Entries Indexed | 65,536 / 65,536 (100%) |
| Distinct Original Targets | 1,667 |
| Targets With One Label | 1,635 |
| Targets With Multiple Labels | 32 |
| Label Categories, Including DC/Line-A/Line-F/ILLEGAL | 120 |
| Encodings Sharing The `4afc` ILLEGAL Target | 8,812 |
| Line-A / Line-F Encodings | 4,096 each |
| Disassembler DC Labels Outside The ILLEGAL Target | 2,733 |

These are **encoding labels**, not recovered handler semantics or 120 proven
instruction implementations. The DC category must not be interpreted as a
hardware-invalid verdict: it includes disassembler ambiguities such as branch
encodings ending in `ff`. Target sharing can be an intentional alias or a
common implementation with further checks. Every target retains its label
counts, representative opcodes and original byte prefix in the JSON receipt.

### One Confirmed Native Alias

Original handler `00478438` implements MOVEQ by sign-extending CL, selecting
Dn from `(opcode >> 9) & 7`, and charging four cycles. It never tests bit 8.
Consequently the original routes both `70xx` and `71xx` (and corresponding
destination-register encodings) to this body. The current Musashi MOVEQ table
uses mask `f100`, value `7000`, requiring bit 8 to be zero.

Eighty original-body executions cover eight destination registers and five
immediates, with bit 8 clear/set: **40 exact alias pairs**. Register result,
PC advancement, selected condition bits and four-cycle charge coincide. The
probe stops before the next opcode fetch; this is not a complete CPU run.
No sound-ROM reachability or audible consequence is established. No alias or
CPU behavior was added to Musashi. Other mixed-label targets require their own
analysis before being called differences or bugs.

### Native CPU Interfaces Identified

| Original Entry / Data | Responsibility | Reconstruction Boundary |
| --- | --- | --- |
| `00462ae0`, table `00531216` | Dispatch initialization | Already independently expanded and compared. |
| `00462b1c` | Interrupt check and dispatch entry | Depends on native global context and register ABI; not a normal C instruction callback. |
| `00462be0` | Exception entry, supervisor stack, vectors | Must preserve original stack/memory callbacks, priority and cycle effects. |
| `0048b518`, `0048b540`, `0048b568` | Line-A, Line-F and generic illegal routes | The generic route calls `004b3360` before deciding whether to enter vector 4. It is not just a universal no-op. |
| `004b30a0`, `004b3280`, `004b32c0` | PC fetch binding and memory-map setup | Native page tables, byte order and handler ABI need an explicit fixture. |
| `004b33a0` | Initial SP/PC and status setup | Reads vectors from direct memory or a callback; not an opcode handler. |
| `004ccbe0` | Board-specific 68000 memory maps | Shared board integration, including UART/chip access; separate from CPU arithmetic. |
| `004aea40`, `004aefb0` | SCSP interrupt selection and sound CPU scheduling | Must be compared independently from opcode results or final PCM. |

Observed context anchors include D0–D7 at `00528ce4`, PC at `00528d34`, pending
IRQ at `00528d38`, fetch-base binding at `010ed9ac` and remaining cycles at
`010ed9b0`. The current sound path invokes Musashi through `port/snd/m2snd.c`.
Replacing it would require CPU state, memory, interrupt, cycle and Save State
integration; the destination-count inventory does not quantify that work.

### A68K Reset, Memory, Exceptions, Interrupts And MOVEQ

`tools/a68k_boundary_compare.py` executes the unchanged original bodies against
independent Python transition models. The pinned PE loader and synthetic host
callbacks are reused; no sound ROM or Windows process is required.

| Boundary | Cases | Observations Compared |
| --- | ---: | --- |
| Reset `004b33a0` | 30 | Direct/callback vectors, SP/PC/SR/fetch binding and untouched context fields. |
| Memory Wrappers `004b30c0..004b3250` | 252 | Read/data/write, byte/word/long, direct/callback, 24-bit aliases, odd and page-boundary addresses. |
| Exception `00462be0` | 6,144 | Vectors 0–47, 32 CCR combinations, supervisor/user stacks, VBR callback, status/PC frame order and cycle-table charge. |
| Interrupt Entry `00462b1c` | 1,536 | Levels/masks, negative/custom acknowledge results, user/supervisor modes, negative/zero/positive cycle budgets. |
| MOVEQ `00478438` | 8,192 | All 4,096 native `7xxx` encodings, both X values, destination result, PC, four-cycle cost and guest NZVC. |
| **Total** | **16,154** | **Zero mismatches.** |

Preserve these original details when implementing the portable CPU:

- Reset sets A7, PC/fetch binding and SR-high `0x27`; it does not blanket-clear
  the remaining register context or separately initialize saved SSP.
- Direct memory is word-swapped. Long operations use the starting page's
  mapping for both words; callback addresses are masked to 24 bits.
- Exception entry reconstructs the guest SR from native x86 NZVC storage and
  the separate X field. The high status byte gains S; this body does not clear
  its trace bit. It stacks SR before PC, retains the raw vector target and masks
  the live fetch PC to 24 bits. These are observed behaviors, not CPU corrections.
- IRQ level 7 bypasses the mask; the entry checks IRQ before rejecting a
  negative cycle budget. Negative acknowledge values use the autovector.
- MOVEQ preserves X and accepts the native bit-8 aliases already identified.
  Its `TEST` produces the NZVC bits consumed by the guest; incidental host
  EFLAGS bits are not claimed as a complete guest status model.

The exception fixture uses even vector targets. Odd-target recursive address
errors, map-installation helpers, Line-A/Line-F/generic illegal dispatch,
complete scheduling and sound-board callbacks remain unqualified. This initial
group established research models; the next section records their portable C
implementation. Neither group establishes a complete A68K CPU or Musashi
equivalence. No percentage of total A68K reconstruction follows from case count.

Receipt and focused disassembly: `port/build-a68k-boundaries/result.json`,
`interrupt-exception.txt`, `memory-reset.txt`. Reproduce with:

```sh
port/build-sharc/venv/bin/python tools/a68k_boundary_compare.py \
  port/build-sharc/original/EMULATOR.EXE \
  --output port/build-a68k-boundaries/result.json
```

### Portable A68K Primitives — 2026-11-04

`port/a68k/a68k.{c,h}` now implements the reviewed native context prefix,
word-swapped direct/callback memory wrappers, reset/fetch binding, exception
frame construction, interrupt entry and MOVEQ. It separates published context
values from live PC/flags and unsigned cycle accounting. Native callback tokens
remain opaque integers; callbacks and host memory bindings are separate.

The byte/word read wrappers preserve a further original detail: `MOV AL/AX`
leaves high EAX bits from the native page-descriptor address. The portable
helper returns that complete value using an integer token derived from original
read/data table addresses, never a dereferenced Windows pointer. The original
fixture now checks all 32 returned bits, not only the requested width. Whether
individual guest instruction handlers rely on those high bits remains separate
instruction-recovery work; they are not silently zero-extended.

`tools/a68k_portable_compare.py` compiles an isolated module and compares it with
the unchanged original bodies and the earlier independent models. O0, O2 and
O2 with UBSan each pass **16,418 cases**, zero mismatches and no sanitizer report:

| Boundary | Cases |
| --- | ---: |
| Reset | 30 |
| Memory Wrappers, Complete Read EAX And Writes | 252 |
| Exception Frame, Even Vector Targets | 6,144 |
| Interrupt Entry And Budget Exit | 1,536 |
| MOVEQ Encodings And X Preservation | 8,192 |
| MOVEQ Budget Exit, PC/Cycle Wrap And Host-Control Inputs | 240 |
| Odd-Vector Prefix Before Recursive Dispatch | 24 |

Nine separate host-binding guards also pass (missing/short mappings and invalid
binding inputs). These are safe host API preconditions, not emulated bus values
or evidence for original out-of-range access semantics.

The odd-vector path explicitly returns a boundary at original `00462c89`;
its recursive address-error/dispatch tail is **not** replaced by a normal
return, corrected vector or fabricated value. The approved fatal-stop policy described below now owns this boundary; the
unsafe recursive host tail remains unexecuted. The module intentionally has no complete execution entry point, sound-board
integration, full context archive or selectable frontend CPU backend. It is
not linked into current standalone/Libretro builds. No frontend/game run was
needed or counted as evidence for code those builds do not yet execute.

The original guest NZVC/X and defined TEST parity are checked. Undefined x86
AF and arbitrary host execution-control semantics are not CPU equivalence
claims. Map installers, callback mutation scenarios,
other instructions and scheduling remain subsequent reconstruction work.

Receipts: `port/build-a68k-portable/{O0,O2,ubsan}.json`, including source and PE
hashes. All three share result digest
`4d6504dbc9eb7a189a6f0ae474b97ce6328c063b4c4341570ef5201ef2b07a68`.
The runner removes its temporary compiled library/debug artifacts automatically;
keep the C source, shim, comparison tools and compact receipts.

```sh
port/build-sharc/venv/bin/python tools/a68k_portable_compare.py \
  port/build-sharc/original/EMULATOR.EXE \
  --output port/build-a68k-portable/O2.json
# Also run with --optimization O0 and --ubsan, each with its own output.
```

### Line-A, Line-F And Illegal Dispatch — 2026-11-04

`a68k_dispatch_target` treats original dispatch addresses as integer identifiers,
never host pointers. It now routes MOVEQ (`00478438`), Line-A (`0048b518`),
Line-F (`0048b540`) and generic Illegal (`0048b568`). Unknown targets return
`A68K_UNRECOVERED` without mutating CPU state; they are not silently replaced
by Illegal.

Native details are retained. Line-A/F stack the live PC and use vectors 10/11.
Their zero-cycle boundary exits (`TEST/JLE`), whereas MOVEQ only exits on a
negative budget (`JS`). Illegal records opcode/PC diagnostics, stacks PC minus
two and, on positive-cycle continuation, adds two to the vector destination.
The original hook `004b3360` is `XOR EAX,EAX; RET`; no invented handled callback
or corrected vector return is substituted.

`tools/a68k_flow_compare.py`, invoked by the portable runner, executes every
original dispatch entry directed at these four targets: MOVEQ 4,096, Line-A
4,096, Line-F 4,096 and Illegal 8,812, totaling **21,100**. Each encoding has
one deterministic state, varying flags, stack mode, wraparound PC/vector and
negative/zero/positive remaining budget. The separate primitive suite provides
additional state coverage; this is not every encoding/state cross-product.
O0/O2/UBSan each pass these cases and the earlier 16,418 primitive cases:
**37,518 comparisons per build**, zero mismatches and no UBSan findings.

Coverage is 21,100/65,536 dispatch entries (**32.20%**) but only 4/1,667 distinct
native targets (**0.24%**). Exception routing accounts for 17,004 entries;
therefore neither percentage measures total CPU implementation effort.
The three ordinary paths are complete. The subsequent approved fault policy
below completes the fourth path: **4/4 (100%) of this bounded module group**.

#### Original Odd-Vector Host Stack Defect

Two native-only probes enter through IRQ `00462b1c`, including its original
`PUSHAD`. Vector 25 returns `00007001`; recursive vector 3 returns `00008000`.
At `00462c89`, the original subtracts two from PC and calls exception entry
`00462be0`. It then jumps directly to fetch or the common exit, bypassing
pending CALL frames. With a 46-cycle budget, the probe stops before RET at
`00462b7b`: ESP is eight bytes below the intended return slot and the next
word is saved ECX (`12345678`), not the caller return address. With a 1,000-cycle
budget, it reaches fetch `00462ca3` with ESP 40 bytes below entry and a pending
return address (`00462bc8`). No original instruction is patched and the invalid
RET is not executed.

This is original host control flow, not a portable-C mismatch. It is not known
whether a game reaches it. The user approved an explicit error and content stop on reaching this case.
The module now latches the `A68K_ODD_VECTOR` fatal diagnostic at the same
verified prefix. No corrected native return or invented bus value is used.
Frontend propagation remains part of future A68K integration, not a tested
capability of the current operational core.

Receipts: `port/build-a68k-flow/{O0,O2,ubsan}.json`, retaining source/PE hashes,
coverage, callback traces and both native stack probes. Flow digest:
`d2951b25963ce8aef76028fc75304863993b0fad46a702b05a4071e876a10954`.
Primitive digest remains
`4d6504dbc9eb7a189a6f0ae474b97ce6328c063b4c4341570ef5201ef2b07a68`.
The module remains unlinked; no production core or installed binary changes.

#### Approved Sticky Fault Policy — 2026-11-04

`a68k_cpu.fault` is host diagnostic state, separate from the original 0x84-byte
register prefix. It records the fatal boundary, original branch `00462c89`,
exception vector, exception-entry PC, unmasked odd target, remaining cycles
and live flags. Native effects up to that branch are retained. No recursive
vector-3 frame or synthetic successful return is created.

`a68k_fault_message` supplies an explicit diagnostic. All public CPU execution
entries reject further calls with the same fatal boundary; PC binding also
fails without mutation. Even native reset cannot silently clear it. A newly
zero-initialized CPU is required after content teardown. Stateless bus helpers
are independent bindings, not an execution path or a fault-clear mechanism.
The future sound-board/frontend caller must report this error and stop content.
That integration is not implemented or claimed while A68K remains unlinked.

The test runner adds **90 original-prefix comparisons** through direct exception,
IRQ, Line-A, Line-F and Illegal entry, covering user/supervisor mode, three odd
targets (including `ffffffff`) and three budgets. Context, PC, cycles, callback
effects, Illegal diagnostics and every fault field are checked. It then makes
14 retries per fault through seven public entry routes, checking the entire
fixture remains unchanged: **1,260 post-fault guards**. A fresh CPU resumes
ordinary MOVEQ execution with no fault. These retry/recovery checks validate
the approved policy, not equivalence to the original invalid host return.

O0/O2/UBSan pass **37,608 original-code comparisons per build** (16,418 +
21,100 + 90), with no mismatches or sanitizer findings. Existing native stack
probes and nine host-binding guards also pass. The bounded exception/dispatch
group is **100% complete**; opcode coverage remains 32.20% of table entries and
0.24% of distinct targets. No overall CPU completion estimate follows.

Current receipts: `port/build-a68k-fault/{O0,O2,ubsan}.json`. Primitive digest
remains `4d6504dbc9eb7a189a6f0ae474b97ce6328c063b4c4341570ef5201ef2b07a68`.
Flow digest is now
`a7008360fd69469d5a4b948eba76c46658e64978bb4d6fcf71bab58cc4183b8d`
because each compared result also records its empty diagnostic fields.
Fault-prefix/policy digest:
`ccf9360dd6f84f788acc5fb8a97f09cbc4c8aa3fd2e6b37205e962d46af52e7a`.
Earlier receipts remain historical evidence of the preceding source revisions.

### Register-Only Instructions — 2026-11-04

Recovered 22 additional original targets in `register_ops.inc`: SWAP, EXT.B/W,
EXG D/D, A/A and D/A, NOP, and byte/word/long register forms of CLR, NEG,
NEGX, NOT and TST. The native table owns encoding validity; EXT.W-to-long
also retains the eight `49c0` aliases. Partial-width operations preserve the
untouched high register bits; EXG preserves flags and handles identical operands.

NEGX follows native width-limited ADC then NEG, not a replacement 68000 formula:
carry/overflow from ADC are discarded. X stores the complete NEG host-flags word
before sticky-Z is combined with the prior live Z. CLR assigns `EDX=0x40`
directly. Other logical results retain the explicit host-control input; undefined
x86 AF is not a hardware-equivalence claim. Negative budget exits, zero-budget
fetch, PC wrap, user/supervisor stack publication and dirty register fields match.

`tools/a68k_register_compare.py` compares every one of the 345 encodings with
12 boundary/pattern operands, both X values and three cycle budgets: **24,840
cases** per build. O0/O2/UBSan pass, including the existing **37,608** comparisons
and fault guards. Register digest:
`079649d7a9e5cfa4f7c66f4f875f060c40307075c6fba908e37d92451cfcf383`.
Receipts: `port/build-a68k-register/{O0,O2,ubsan}.json`.

Bounded register group: **22/22 targets (100%)**. Combined dispatch coverage:
**21,445/65,536 entries (32.72%)**, **26/1,667 targets (1.56%)**. Memory forms,
other instruction families, full execution and audio integration remain open;
these percentages are not weighted overall CPU completion.

## SCSP DSP: Decoder, Generator And Invocation

| Original Entry | Role | Evidence In This Group |
| --- | --- | --- |
| `004a9e90` | Decode one 64-bit DSP instruction into 25 fields | 642 original executions match the reviewed field map: zero/all-ones, all single bits/complements and 512 deterministic random inputs. |
| `004aa040` | Generate x86 for the active program | 69 synthetic programs captured and hashed; original generator code unchanged. |
| `004aa7f0` | Find the last nonzero step, enable DSP, invoke generator | Six original cases cover empty, first, second, middle and final program positions; LastStep matches 0/1/2/64/127/128. |
| `004a9fa0` | Clear effect outputs, call generated code, decrement DEC and clear MIXS | Identified from native code/export; generated audio semantics not compared in this group. |

The decoder fields correspond to the field extraction in `port/snd/scsp.c`:
TRA/TWT/TWA, XSEL/YSEL/IRA/IWT/IWA, TABLE/MWT/MRD/EWT/EWA, ADRL/FRCL/SHIFT/YRL,
NEGB/ZERO/BSEL, NOFL/COEF/MASA/ADREB/NXADR. The probe compares the original to
an explicit reviewed field map; it does not execute the portable DSP loop.

The generator's only call sites are two calls to the decoder and imported
`VirtualAlloc` / `VirtualFree`. The isolated fixture replaces only those host
imports, at IAT slots `005081d8` and `005081e0`, with bounded allocator stubs.
No original instruction is rewritten. Generated programs contain absolute
addresses into a fixed synthetic context, allowing repeatable code hashes.

| Synthetic Generator Case | Emitted Bytes |
| --- | ---: |
| Empty / One All-Zero Step | 9 |
| Two All-Fields-Set Steps | 419 |
| 128 All-Fields-Set Steps | 28,958 |

The remaining cases toggle each of the 64 instruction bits with a second zero
step; a recompile case verifies the free/allocate boundary. All fixtures remain
inside the requested 64 KiB allocation and have the original register-save /
restore / return envelope. **The generated bodies were not executed in the classification group**: those
results prove a usable capture boundary, not equivalence to the MAME-derived
portable interpreter, final SCSP PCM or audible output.

### First DSP Execution Comparison

The subsequent matched-state comparison executes both the original generator
`004aa040` and its emitted x86 through sample wrapper `004a9fa0` in Unicorn.
The test-only `port/snd/test/scsp_dsp_shim.c` includes the unchanged production
`scsp.c` and calls its private `dsp_step`; it does not duplicate the interpreter.
Native context fields are mapped explicitly into the portable structure.
Only the previously documented host allocator imports are substituted.

| Group | Cases | Scope |
| --- | ---: | --- |
| Multiply / Shift | 252 | Signed input/coefficient edges, multiplication, all four shift modes, saturation/wrap, TEMP and effect writeback. |
| Arithmetic Selection | 512 | TEMP/MEMS operands, ZERO/NEGB/BSEL combinations and wrapped TEMP addresses. |
| Feedback Chains | 256 | Eight-step dependent programs, coefficient/fraction/Y selection, intermediate registers, MEMS/TEMP and accumulated effects. |
| Total | 1,020 | Zero mismatches at both Clang `-O0` and `-O2`. |

The comparisons cover persistent TEMP, MEMS, DEC, MIXS and EFREG bytes.
935 fixtures change TEMP, MEMS or effects; all 252 multiply/shift cases also
check an independent scalar expectation. Both builds have identical input,
generated-code and result hashes. The aggregate result SHA-256 is
`7294860e485cf878171f70c76e3e64b45dee5d08a2413db8de8094acdeb58476`.

This is a synthetic integer-code oracle under Unicorn, **not a native Windows
CPU run**. Initial scratch is zero, inputs come from valid MEMS/TEMP locations,
and MIXS/EXTS remain zero. Sample RAM reads/writes and representation, scratch
continuity across samples, final PCM, IRQ and scheduling are not qualified.
No production audio correction is indicated by this tested scope.

```sh
mkdir -p port/build-scsp-dsp
clang -O2 -g -std=c11 -fPIC -dynamiclib port/snd/test/scsp_dsp_shim.c \
  -lm -o port/build-scsp-dsp/scsp-dsp-O2.dylib
port/build-sharc/venv/bin/python tools/scsp_dsp_compare.py \
  port/build-sharc/original/EMULATOR.EXE port/build-scsp-dsp/scsp-dsp-O2.dylib \
  --output port/build-scsp-dsp/compare-O2.json
```

Repeat with `-O0` and matching output names. JSON receipts and source/toolchain
provenance remain in ignored `port/build-scsp-dsp/`; generated libraries and
debug bundles are removed after validation. The reusable runner and shim remain
in source control scope; no ROM or game-derived code is involved.

### Preservation Versus Original-Code Corrections

User direction — 2026-11-04: pursue a recovered DSP for eventual use in the
core, consistent with preserving ElSemi's emulator. **Reconstruction must first
reproduce the original behavior, including its quirks.** A difference from the
MAME-derived implementation is not automatically an error in ElSemi, nor is
hardware documentation alone authority to silently change the original.
Any proposed original-code correction is a separate activity: establish the
behavior, demonstrate its consequences, explain the change and obtain the
user's decision before applying it. No corrective mode or fallback is implied.

### Memory And Lifecycle Reconstruction

`port/snd/scsp_dsp_original.c` (initially recovered in the test shim) translates the behavior emitted by native
generator `004aa040` and sample wrapper `004a9fa0`. It uses the reviewed native
context layout and explicit integer operations; it is **not linked into the
core**. It preserves selective scratch stores and the generator's one-step
lookahead, rather than adapting the MAME interpreter to resemble it.

`tools/scsp_dsp_memory_compare.py` compares that translation with generated
original x86. The existing portable loop remains a third, unchanged comparator.
RAM words are identical, with explicit little-endian native / big-endian port
storage. The recovered comparison includes TEMP/MEMS, DEC, MIXS, EFREG, native
scratch and resulting RAM. Address traces independently check the 40 dedicated
DEC/RBL/RBP/MADRS/NXADR cases.

| Group | Cases |
| --- | ---: |
| Prior Arithmetic / Shift / Feedback Regression | 1,020 |
| Memory Reads / Writes | 40 / 28 |
| Address Selection | 40 |
| Continuation Across Samples | 15 |
| Raw MIXS / EXTS Representation | 20 |
| Sixteen-Step Memory Chains, Three Samples Each | 256 |
| Combined Read / Write | 8 |
| Empty / Stopped / 127- And 128-Step Programs | 8 |
| Compile-Time Lookahead Capture | 4 |
| Total | 1,439 |

All 1,439 cases match the recovered C at **O0, O2 and O2 with UBSan on the
recovered implementation**, with no sanitizer diagnostic. These execute
1986 original sample-wrapper calls per build. The portable MAME-derived loop
differs in 359 cases; these are bounded differences, not 359 distinct defects.
Twenty deliberately compare raw input fields without mixer-unit normalization.
All three builds have identical result hashes. Original x86 execution uses
Unicorn, not a physical Windows CPU; this remains synthetic DSP evidence, not
game audio or whole-SCSP qualification.

| Native Behavior Preserved | Difference / Qualification |
| --- | --- |
| MRD with NOFL=0 stores a signed linear 16-bit word shifted by eight. | The MAME comparator uses its floating sample UNPACK conversion. |
| MRD with NOFL=1 emits a load and shift but no MEMVAL store. | The MAME comparator updates MEMVAL. The recovered code deliberately preserves the missing native store. |
| MWT writes SHIFTED's upper 16 sample bits in both NOFL modes. | The MAME comparator invokes PACK for NOFL=0. |
| ACC, MEMVAL, FRC, Y and address scratch persist unless emitted code overwrites them. | Current `dsp_step` initializes local scratch each sample. |
| ACC stores depend on the following instruction's consumers. | Preserve this generator optimization; omitted stores can affect subsequent samples. At 128 steps, lookahead captures bytes at the beginning of TEMP during compilation. |
| MIXS is consumed directly as signed 24-bit data; EXTS uses a DWORD load at a WORD stride. | Current input shifts differ. Native mixer units and the adjacent EXTS/effect halfword must be accounted for explicitly before integration. |
| Simultaneous MWT/MRD leaves the shifted write value in EAX before computing the read address. | The eight bounded cases preserve this sequence; the MAME comparator reads then writes the selected address. Broader host-memory escapes are not qualified. |

The research C returns fixture failure for RAM addresses outside the supplied
buffer. This is **not** an invented production masking/fallback policy. No
original quirks were corrected. The candidate captures decoded instructions
once per probe, as the native generator does; a production integration must
preserve compile/recompile and snapshot behavior explicitly.

Reproduction (repeat with O0):

```sh
clang -O2 -g -std=c11 -fPIC -dynamiclib \
  port/snd/test/scsp_dsp_shim.c port/snd/test/scsp_dsp_recovered.c \
  port/snd/scsp_dsp_original.c \
  -lm -o port/build-scsp-dsp/scsp-dsp-O2.dylib
port/build-sharc/venv/bin/python tools/scsp_dsp_memory_compare.py \
  port/build-sharc/original/EMULATOR.EXE port/build-scsp-dsp/scsp-dsp-O2.dylib \
  --output port/build-scsp-dsp/memory-O2.json
```

For UBSan, compile the reusable recovered module with
`-fsanitize=undefined -fno-sanitize-recover=all`; compile the unchanged shim
without those flags, then link both with the sanitizer. The inherited
interpreter's known signed-shift behavior is not attributed to the recovered C.
Retain one detailed result receipt, compact matching O0/UBSan receipts and
`memory-provenance.json`; discard generated libraries, objects and debug bundles.

### Integration Preparation: Memory, Mixer And Saved Program

The recovered implementation now lives in `port/snd/scsp_dsp_original.c` and
`.h`; the prior probe is a thin caller of that same module. Extraction retained
all 1,439 differential cases with the same result hashes. Source integration
subsequently wired this module into both Makefiles and the SCSP caller; full
frontend qualification is still open.

Native allocation/setup in `src/all_functions.c` assigns the channel RAM to
`0109bd1c` and allocates a distinct **1 MiB** buffer for the DSP at `0109bd24`.
The new module therefore owns private delay RAM. The previous MAME-derived path
shared the 68000's 512 KiB RAM and must not silently dictate this native policy.
The native initial RBL is `0x8000`; subsequent register writes set the selected
ring size. Native 16-bit and byte write probes establish the start event at
`0xbfe`, whereas the previous port triggered at `0xbf0`. Eight targeted write
probes cover `bf0/bfc/bfe/bff` for both widths; source wiring now uses BFE.

The module stores both current MPRO and the compiled program snapshot,
including the captured lookahead. Coefficients, RAM and scratch remain live;
MPRO writes alone do not silently recompile. Archives contain private RAM,
context, captured program and explicit diagnostic state, never executable
pointers or decoded host addresses. Restore rebuilds decoded instructions from
the saved compiled snapshot, not from possibly newer MPRO/TEMP contents.

The ROM-free `port/snd/test/check_dsp_lifecycle.c` passes with ASan and UBSan:
initial defaults, cross-sample MEMVAL, private RAM, changes to MPRO after
compilation, preflight without mutation, exact continuation on a fresh instance,
explicit recompilation, truncated/invalid archive rejection and boundary/reset
reporting. This proves the module archive, not Libretro's complete state
container or actual RetroArch persistence.

`tools/scsp_dsp_bridge_compare.py` executes the original gain-table initializer
and then compares unchanged native integer mixer fragments. **18,432 cases
match**: 16,384 input cases (all TL/level choices over eight signed sample
values) and 2,048 effect-output cases (all pan/level choices). The module retains
the native integer tables in `scsp_dsp_gains.inc`, separate input-gain rounding
steps, and distinct PAN=15/PAN=31 behavior. Table creation runs under Unicorn
x87, not physical x86; the TL entries also agree with the independent expression
using the native float constants. This qualifies the DSP boundary operations,
not the upstream channel synthesizer, final frontend gain or complete PCM.

#### Approved Native Memory Limit Handling

With RBP=127, TABLE=1 and MADRS=65535, the original reads byte address
**1,171,454**, beyond its 1,048,576-byte allocation. A mapped synthetic guard
word `0x1234` reaches MEMVAL as `0x123400`, proving the unchecked access without
accessing host memory. Game reachability is not established. Combined reads
and writes can also derive an address from the shifted write value; no new
wrapping or clamping policy has been invented for those cases.

The user approved an explicit address diagnostic and content stop. The working
SCSP/Libretro/standalone paths now propagate that failure, without fabricating
a value or remapping unrelated memory. The recovered module, native mixer
boundaries and BFE start event are wired into the working build. The macOS core
build and ROM-free sound checks pass; full-core Save State/PCM/frontend
qualification remains open. The installed core has not been replaced.

Reproduction:

```sh
clang -O2 -g -std=c11 -Wall -Wextra -Werror -fPIC -dynamiclib \
  port/snd/scsp_dsp_original.c -o port/build-scsp-dsp/scsp-dsp-bridge.dylib
port/build-sharc/venv/bin/python tools/scsp_dsp_bridge_compare.py \
  port/build-sharc/original/EMULATOR.EXE port/build-scsp-dsp/scsp-dsp-bridge.dylib \
  --output port/build-scsp-dsp/bridge-comparison.json
clang -O2 -g -std=c11 -Wall -Wextra -Werror \
  -fsanitize=address,undefined -fno-sanitize-recover=all \
  port/snd/test/check_dsp_lifecycle.c port/snd/scsp_dsp_original.c \
  -o port/build-scsp-dsp/check-dsp-lifecycle
port/build-scsp-dsp/check-dsp-lifecycle
```

Retain compact module/mixer results, lifecycle log and integration provenance.
The reusable bridge tool also reproduces the native guard and register-write
observations. The preparation probes use no ROMs. Subsequent source integration
changes the working audio path; it does not deploy the candidate core.

### Original Save State Audit

The original routines were disassembled from the pinned `EMULATOR.EXE` 1.1a,
not inferred from a block label. Save `004f7540` and load `004f7400` traverse
the registered list: type 0 copies exactly the recorded pointer/length; type 1
uses a fixed-size buffer and explicit CPU callbacks. The `.sta` file is a ZIP
archive of these named blocks, not a process-memory snapshot.

`004cd450` registers 15 raw board-memory entries. At `004cdaff` it allocates
**1 MiB** for the sound RAM stored at board offset `20389c`, but at `004cdb31`
records only **64 KiB** for the `M2SCSP` archive member. Board audio setup
`004ccbe0` binds that sound RAM to `0109bd1c`, and separately allocates **1 MiB**
for DSP private RAM through the pointer at `0109bd24`. These are distinct buffers.

| Original Data | Save State Behavior In The Traced Path |
| --- | --- |
| Sound RAM (`M2SCSP`) | First 65,536 bytes copied; the other 983,040 allocated bytes are not included in this entry. |
| SCSP DSP context at `0109bd24`, size `0x7ec` | Not registered: MPRO, coefficients, TEMP/MEMS, DEC, scratch and effects remain session state. |
| Separate DSP private RAM, 1 MiB | Not registered or traversed through its pointer. |
| Generated DSP x86 program | Not serialized or recompiled by the load routine. |

The other recovered registrations are `TGP` (`0x1072`), `TGPX4` (`0x140`),
`SHARC` (`0x2a4`) and `I960` (`0x108`). Their save/load callbacks copy their
respective CPU contexts and restore execution bindings; they are not SCSP DSP
archives. The frontend also invokes board vtable slot `+0x30` after loading:
table `0051bbcc` resolves it to `004caf00`, which marks renderer resources dirty
and invokes the graphics-resource cleanup at `004b7c60`. It does not restore
the DSP or invoke its compiler.

`tools/scsp_dsp_state_audit.py` executes the unchanged registration fragments
and raw-entry load traversal under Unicorn, with synthetic allocation/list/INI
and archive-I/O fixtures. It captures all 15 raw descriptors and four CPU
descriptors. Sentinel checks confirm restoration of the first sound-RAM 64 KiB
and preservation of the remaining sound RAM, DSP context and private RAM.
The updated probe also executes the post-load hook with empty renderer
resource lists and resumes a synthetic A68K program from restored RAM.
The live MIDI, timer, IRQ and CPU context survive. The other CPU callback
contents are disassembly evidence. See VALIDATION.md under Board Reset And
Original State Load With Pending Sound.

This answers the bounds question narrowly: **the original Save State mechanism
does not preserve arbitrary process memory beyond the DSP allocation and does
not define a recovery policy for those accesses**. It cannot supply a missing
value for an escaped address. This is a native persistence limitation, separate
from whether a game actually triggers the unchecked DSP access. Preserve the
DSP execution semantics; keep the port's already-approved complete-snapshot
contract rather than reproducing the native omission.

Reproduction, with no ROMs or user saves:

```sh
port/build-sharc/venv/bin/python tools/scsp_dsp_state_audit.py \
  port/build-sharc/original/EMULATOR.EXE \
  --output port/build-scsp-dsp/original-state-audit.json
```

The compact receipt retains the executable hash, descriptors and four passing
sentinel checks. No original executable bytes or game data are added to Git.

### Integrated Core Qualification — 2026-11-04

After source wiring, all 1,439 original-code cases still match the recovered
module. The prior MAME comparator retains exactly the same 359 differences.
Both macOS standalone targets and the SHARC/TGPX4 Libretro core build.

`make SHARC=1 TGPX4=1 BUILD=port/build-dsp-libretro check-sound` now includes
`scripts/check-dsp-integration.c`. Its synthetic 68000-bus fixture verifies
BFE/BFF start semantics, nonzero DSP-only PCM with direct output disabled,
cached MPRO after backing writes, nonmutating state preflight, and exact
PCM/full-sound-state continuation in a new instance. A legal bus-programmed
combined MWT/MRD case derives escaped read address `0x01ffc000` from a negative
SHIFTED value. The fixture proves exact address reporting, silence and frozen
sound state after fault, real `retro_run` notification/shutdown, no repeated
shutdown on later calls, and reset recovery. This remains synthetic reachability,
not a claim that a game hits that address. An initial fixture run omitted
`retro_init`, so the notification sink was not registered; fixing the fixture
lifecycle passes without a production behavior change.

| Content | Frames Before Save | State Capacity | Used Bytes | Fresh-Process Continuation |
| --- | ---: | ---: | ---: | --- |
| VF2 / Model 2A | 1,800, scripted match inputs | 12,582,912 | 8,871,140 | Exact |
| Indy 500 / Model 2B | 900 | 16,777,216 | 9,338,940 | Exact |
| Top Skater / Model 2C | 900 | 16,777,216 | 9,519,948 | Exact |

Each existing GL harness run also passes cold save/load, four exact 12-frame
RAM/device/PCM/image continuations, graphics-context recreation and invalid-state
rejection without mutation. VF2 checks current NVRAM override authority.
No escaped-DSP fault was observed in these bounded game runs.

Real RetroArch 1.22.2 (`fce35fc7`), macOS ARM64/OpenGL, restores VF2 at exact
machine frame 2,267. The game image changes before load and after resume; both
full screenshots and the OSD-free regions match after restoration. State file
size is 12,582,936 bytes (core capacity plus frontend wrapper). Exit is zero
without forced termination. The saved image was visually inspected and shows
the rendered VF2 attract scene, not a static boot screen.

Tested core SHA-256:
`93644c70ce3771ceddfe88c484a9a3d58a961066634135a0917fc6c1a72ae9ee`.
Results live under `port/build-scsp-dsp/`: `integration-result.json`, the three
`states-*/result.json` receipts, `retroarch-vf2/result.json`, sound check log and
compact oracle receipt. Tools, logs and frontend screenshots are retained;
temporary states, RAM/PCM dumps, test executables and build objects are removed
after verification. The tested candidate core remains separate from installation.

This bounded macOS integration group is complete. Exact PCM continuation is
not equivalence of the entire sound board to Windows, a listening test, or
whole-catalog/platform qualification. The original DSP quirks remain intact.

### What Can Be Investigated Next

The escaped-address choice is approved; local integration, state ABI/capacity,
PCM continuation and representative frontend restoration are qualified above.
Invalid input selectors and broader escaped-host-memory reachability remain unqualified;
do not silently mask, clamp or reinterpret those accesses.

A68K recovery is a distinct, much larger activity. The bounded CPU fixture
above now qualifies portable context/bus/exception and MOVEQ primitives.
Next are recursive exception/illegal-dispatch tails and remaining instruction
families. The verified
aliases are reasons to preserve native behavior, not grounds for changing
Musashi. The user's latest policy is reconstructed code as the default, with
the existing replacement selectable as an alternative. A68K becomes the 68000
default once complete and qualified; Musashi remains the operational CPU until
then. The user-facing alternative label is **MAME (Musashi)**, as requested.

## Explicit DSP Backend Selection — 2026-11-04

Historical contract, superseded by [Audio Subsystem Selection](ROADMAP.md#audio-subsystem-selection) on 2026-11-14.

The user requested independent 68000 and DSP selectors. The current policy is
reconstructed code as default, with the replacement implementation as an
alternative. The DSP already implements ElSemi default / MAME alternative.
The CPU selector will implement A68K default / MAME (Musashi) alternative when A68K
is executable and qualified. The alternative label is explicitly user-approved; no unavailable
choice is exposed. Until then the operational 68000 remains Musashi.

`model2emuex_scsp_dsp_backend` offers `original` (default) and `mame` under Audio,
labelled `SCSP DSP Backend (Restart Required)`. This is a user-requested port
feature, not an inherited standalone/SM2 option. Selection is latched when
content loads. Live option edits and Reset retain the current backend; close
and reload applies the new value. Non-SCSP boards are unaffected. No fault
causes automatic fallback.

The MAME path in `scsp_dsp_mame.inc` preserves the previous interpreter, shared
sound RAM, BF0 Start, live MPRO updates, initial RBL and mixer gain equations.
The original retains private DSP RAM, cached MPRO, BFE Start, native gains and
explicit escaped-address diagnostics. Both use the existing SCSP slot engine
and Musashi sound CPU. State header schema/backend bits and the SCSP archive
marker reject incompatible states before mutation; see SAVE_STATES.md.

Qualification:

- `tools/scsp_mame_backend_compare.py`: 64 synthetic cases / 16,384 sample
  frames match the pinned pre-recovery SCSP source exactly for observed PCM,
  shared RAM and common DSP fields, including Start, live edits and Reset.
- `check-sound`: both backend-specific start/program behaviors, nonzero
  DSP-only PCM, fresh sound-instance archive continuation and reset retention
  pass; cross-backend preflight rejection leaves current state unchanged.
- VF2, both backends: 1,800 scripted frames; cold state, four exact 12-frame
  RAM/device/PCM/image continuations, context recreation, invalid/schema/backend
  rejection and exact fresh-process continuation pass. Option edits and Reset
  retain the backend; reload switches it. The original's continuation PCM CRC
  remains `354e3923`, matching the prior integration receipt.
- RetroArch 1.22.2 ARM64/OpenGL, MAME: exact restored game region and machine
  frame 2,276; scene advances before/after restore, exit 0 without forced kill.

Receipts: `port/build-scsp-dsp/mame-backend-baseline.json`,
`backend-states-{original,mame}-gl/result.json`,
`backend-retroarch-mame/result.json`. The local candidate's SHA-256 is
`614dedaa458b6849c40b60e718568f5473f7d239fb34b7551a9d84cfed72ccd7`.
No listening test or whole-board Windows audio equivalence is claimed. No
installed-core replacement or publication is part of this group.

## Reproduction And Evidence

```sh
mkdir -p port/build-audio-re
clang -O2 tools/m68kdis.c port/m68k/m68kdasm.c -o port/build-audio-re/m68kdis
port/build-sharc/venv/bin/python tools/audio_re_inventory.py \
  port/build-sharc/original/EMULATOR.EXE \
  --disassembler port/build-audio-re/m68kdis --verify-original \
  --output port/build-audio-re/audio-inventory.json
```

The pinned EXE identity is checked before loading. The existing Unicorn PE
loader and isolated JIT authorization are reused. Retained evidence is the
JSON classification/probe receipt, summary, focused disassembly and provenance
in `port/build-audio-re/`; the tool binary, synthetic input and redundant
65,536-line disassembler dump are regenerable and removed after validation.
An initial alias-probe attempt lacked an initialized stack for PUSHF and
faulted in the fixture; the accepted run initializes the mapped stack and
completes all 80 executions. No failed fixture run is counted as a pass.

The dispatch **index**, bounded DSP reconstruction and local integration groups are complete.
No overall RE completion percentage follows: most original audio instruction
semantics remain unqualified. Astra with High effort remains appropriate for
further original-code analysis. Source integration changes DSP behavior and
the SCSP state payload; no installed core, user ROM/save, commit or publication
was changed.


## A68K Native Map Installers — 2026-11-04

The three native installers (`004b3280`, `004b32c0`, `004b3310`) now have a
bounded host implementation. Fetch mapping clears callbacks; data/write mapping
retains the appropriate width callbacks. All mapped pages use one base relative
to the original start. Native page count is `((end-start)>>12)+1`, deliberately
not the difference of rounded endpoints. Unaligned and full-24-bit ranges match.

O0/O2/UBSan pass 60 whole-table comparisons against untouched native routines,
including sentinel pages. Five malformed host-range checks reject changes before
mutation; these are host guards, not original invalid-pointer emulation. Mapping
is independent configuration and does not clear a CPU fatal diagnostic.
Receipts: `port/build-a68k-maps/{O0,O2,ubsan}.json`; digest:
`c2161d989d70b8f1164ed7f71f50db677e9d7f841d078aca441c7efe4e29e6e3`.
Group **3/3 (100%)**; cumulative comparisons **62,508 per build**. Opcode coverage
unchanged (32.72% entries, 1.56% targets). Board-device wiring remains separate.


## A68K Conditions And Branches — 2026-11-04

Recovered 64 targets: all 16 register Scc and DBcc conditions, plus byte/word
BRA, BSR and Bcc. All 4,352 encodings and all 16 NZVC combinations are exercised;
PC wrap, budgets, counters and extension words vary deterministically. Additional
odd-vector branch cases check the approved halt. **70,144 comparisons** pass
O0/O2/UBSan; **132,652 cumulative per build**, including prior groups. There
are 288 branch cases reaching the explicit fault policy and all retry guards pass.

Original quirks are preserved: signed conditions OR `0x200` into live flags;
DBcc does not mask/rebind or test the branch target's alignment; BSR retains
the prior raw-PC high byte in its stacked return. Taken Bcc/BRA/BSR rebind and
check alignment; a resulting odd exception vector uses the approved fatal stop.
Not-taken word branches skip the extension without reading it. Native cycle
costs, callback order, published versus live PC/flags and counter wrap match.

Receipts: `port/build-a68k-control/{O0,O2,ubsan}.json`; digest:
`fdb5e0aa4797b100cfc707e5d68f1ae8c40f0f90a4925cba5251e9314cdcd337`.
Bounded group **64/64 (100%)**; combined dispatch coverage **25,797/65,536
entries (39.36%)**, **90/1,667 targets (5.40%)**. This is not total CPU completion.
A complete fetch/execute loop, arbitrary callback mutation and board integration
remain unqualified. Tools and compact results retained; no ROMs or core deployment.


## A68K Binary Register Arithmetic — 2026-11-04

Thirty additional original targets implement register OR/AND/EOR, ADD/SUB/CMP,
ADDX/SUBX and ADDA/SUBA/CMPA in applicable widths. The actual dispatch table owns
aliases and Dn/An source selection. Native EOR direction/cycle costs and address
arithmetic cycles are retained. Address word inputs are sign-extended; address
ADD/SUB preserve flags, comparisons preserve X, and ADC/SBB store complete X
before merging sticky Z. Partial-register updates and identical operands match.

All 2,752 encodings with boundary/seeded-random operand pairs and both X inputs
pass **121,088 comparisons** per O0/O2/UBSan build. Existing groups also pass:
**253,740 cumulative original-code comparisons**, host guards separate. These
are not exhaustive operand products or memory forms. Receipts:
`port/build-a68k-binary/{O0,O2,ubsan}.json`; digest:
`fad27ff6ccd39307a84209c65b6218e14454d1d9ec83f9b3f4190f91350a72ff`.
Group **30/30 (100%)**; combined coverage **28,549/65,536 entries (43.56%)**,
**120/1,667 targets (7.20%)**, not overall CPU completion. Operational core unchanged.


## A68K Register Transfers And Immediate Operands — 2026-11-04

Thirty-six additional targets implement register/immediate MOVE/MOVEA,
ORI/ANDI/EORI/ADDI/SUBI/CMPI to Dn and ADDQ/SUBQ to Dn/An. The actual original
aliases are retained, including byte-encoded address quick operations. Native
immediate cycles are not normalized: ANDI.L and CMPI.L charge 14, other covered
long immediate arithmetic/logical operations charge 16; MOVE immediate charges 4.
Extension words use the current fetch binding and native word-swapped long order.
MOVEA sign extension and flag preservation, partial updates and PC wrap match.

O0/O2/UBSan pass **62,088 added cases**, all 1,592 covered encodings, operand
boundaries/patterns and negative/zero/positive remaining budgets. Shared arithmetic
helpers also pass all prior regressions: **315,828 cumulative comparisons** per
build. Receipts: `port/build-a68k-operands/{O0,O2,ubsan}.json`; digest:
`22f683dfb07fab2b782a49873f29b3f05ee761b1599cd712f2e11ce92508b8e3`.
Group **36/36 (100%)**. Combined dispatch coverage: **30,141 entries (45.99%)**,
**156 targets (9.36%)**. No complete CPU/audio integration; memory forms remain open.


## A68K Effective Addresses And MOVE Memory Sources — 2026-11-04

Twenty-nine original targets now cover MOVE byte/word/long from memory to Dn:
indirect, postincrement/predecrement (including byte A7's two-byte step), signed
displacement, brief index, absolute short/long and PC-relative displacement/index.
Brief indexes select all 16 Dn/An registers; native ignored scale/full-format bits
remain ignored. Instruction extensions retain the current fetch binding.

The pinned callback table confirms ordinary operand reads use DATA wrappers
`004b3250/3220/31f0`; PC-relative reads use READ wrappers `004b31c0/3190/3160`.
The tests execute those unchanged original wrappers, not only synthetic handler
replacements. Direct and callback memory paths, masked addresses, boundary
crossing, word order and context observed during callbacks are compared.

O0/O2/UBSan pass **16,896 added cases**, all 1,056 encodings, **332,724 cumulative
comparisons per build**. Receipts: `port/build-a68k-memory/{O0,O2,ubsan}.json`;
digest `553cf90941c20a410398b3209b2ae76447e391c70007b6bfabf6b06d720b3549`.
Group **29/29 (100%)**; combined coverage **31,197 entries (47.60%)**, **185
targets (11.10%)**. This is not total CPU completion. Arbitrary callback mutation,
memory destinations, remaining instructions and full audio integration remain open.


## A68K Arithmetic And Logical Memory Sources — 2026-11-04

Added 145 original targets for OR/AND/ADD/SUB/CMP from memory to Dn.
The already qualified effective-address and DATA/READ paths are reused with
each native target's width and cycle cost. All 5,280 additional encodings pass
84,480 added comparisons at O0/O2/UBSan, including original wrappers and
callback-observed context. The memory-source suite now contains 101,376 cases;
417,204 cumulative original-code comparisons pass per build.

Receipts: `port/build-a68k-memory-binary/{O0,O2,ubsan}.json`; memory-suite digest
`9a25b78e78245eda173ef382fe6762f361f1365bba610abd4b1d2b447582210e`.
Group **145/145 (100%)**; combined coverage **36,477/65,536 entries (55.66%)**,
**330/1,667 targets (19.80%)**. These are dispatch metrics, not overall CPU
completion. Memory destinations, remaining instructions, arbitrary callback
mutation and full sound-board integration remain open. Operational core unchanged.


## A68K Arithmetic And Logical Memory Destinations — 2026-11-04

OR/AND/EOR/ADD/SUB Dn-to-memory adds **115/115 targets (100%)**, all 5,040
encodings and **161,280 new comparisons** at O0/O2/UBSan. All four combinations
of direct/callback reads and writes match, including callback-visible context,
full narrow-write argument, memory bytes, native costs and cycle exit. ADD/SUB
publish X after the write callback; that ordering is explicitly preserved.

Receipts: `port/build-a68k-memory-dest/{O0,O2,ubsan}.json`; group digest
`cf98896cca36a26843fd850b8433ebbb6640ae04277748a99d23cb4c96b5c0cb`.
Cumulative comparisons: **578,484 per build**. Combined dispatch: **41,517/65,536
entries (63.35%)**, **445/1,667 targets (26.69%)**, not weighted CPU completion.
Other memory destinations, instruction families, arbitrary callback mutation
and full execution/audio integration remain open. Operational core unchanged.


## A68K Immediate And Quick Memory Operands — 2026-11-04

ORI/ANDI/EORI/ADDI/SUBI/CMPI and ADDQ/SUBQ memory forms add **184/184 targets
(100%)**, all 2,772 encodings and **88,704 comparisons** passing O0/O2/UBSan.
Native immediate-before-EA ordering, word-swapped longs, quick zero encoding
as eight, read/write callbacks, CMPI's lack of write, flags/X and cycles match.
All earlier groups also pass: **667,188 comparisons per build**.

Receipts: `port/build-a68k-memory-operands/{O0,O2,ubsan}.json`; group digest
`0bc51ea996680eb9fd29bb0c8aaf18a1b3ffdfdff0e682075402165f1c00a8ca`.
Combined dispatch: **44,289/65,536 entries (67.58%)**, **629/1,667 targets
(37.73%)**. Full CPU/audio integration and other instruction families remain open;
these dispatch metrics are not overall completion. Operational core unchanged.


### Pending Native Host-Scratch Dependency

The still-unrecovered memory NEG/NOT bodies publish EDX after the read wrapper
into the public flags slot before the write callback (for example `004837b6`).
For direct reads EDX contains the original direct-map base token; callback
reads may expose a callback-clobbered value instead. The final arithmetic flags
are separately held on the x86 stack. Do not replace this intermediate value
with the guest CCR or fabricate zero. Recover the wrapper/callback scratch
contract before qualifying these handlers and the complete execution loop.
This is a fidelity/integration boundary, not evidence of a guest-visible bug
or authorization to correct the original. CLR/TST/TAS/NEGX have distinct,
explicit publication paths and can be reconstructed separately.


## A68K Address-Register Memory Sources — 2026-11-04

MOVEA/ADDA/SUBA/CMPA memory forms add **72/72 targets (100%)**, all 2,816
encodings and **45,056 new comparisons** passing O0/O2/UBSan. Native flag
publication before reads and reload afterward, callback-visible context, signed
word operands, same-An address updates and costs match. All earlier groups pass:
**712,244 cumulative comparisons per build**.

Receipts: `port/build-a68k-memory-address/{O0,O2,ubsan}.json`; the combined
146,432-case memory-source digest is
`d48d2e03134ea92f88e9d0bd2ab9c9b9d2ac01f6363e2ff96442b6cb87c57fbf`.
Combined dispatch: **47,105/65,536 entries (71.88%)**, **701/1,667 targets
(42.05%)**; not weighted CPU completion. Other instructions, full execution and
sound integration remain open. Operational core unchanged.


## A68K CLR/TST/TAS/NEGX Memory Group — 2026-11-04

**78/78 targets (100%)**, all 420 encodings and **26,880 new comparisons** pass
O0/O2/UBSan. All four direct/callback combinations, both prior Z states, X,
callback-visible context and native costs match. CLR performs no dummy read;
TST performs no write; TAS derives flags before setting bit 7. NEGX retains
ADC-width then NEG-width and publishes X/merged flags before the write, reloading
flags afterward. Shared register NEG/NEGX regressions also pass after factoring
the exact arithmetic helper. NEG/NOT memory scratch dependencies remain separate.

Receipts: `port/build-a68k-memory-unary/{O0,O2,ubsan}.json`; group digest
`0cb8d91db3799f4a7ac83ed6e8755f3f3be613719b76b72a89051f75f929b81a`.
Cumulative comparisons: **739,124 per build**. Combined dispatch: **47,525/65,536
entries (72.52%)**, **779/1,667 targets (46.73%)**; not weighted CPU completion.
Remaining instructions and full execution/audio integration are open.


## A68K Effective Addresses And Stack Frames — 2026-11-04

LEA/PEA/LINK/UNLK: **16/16 targets (100%)**, all 268 encodings and **8,576
new comparisons** pass O0/O2/UBSan. Native costs, unmasked address results,
flags/publication, direct/callback stack access and aliasing match. LINK A7
reads the already-decremented stack pointer; displacement is fetched only after
the write. UNLK A7 retains the original final address-plus-four ordering.

Receipts: `port/build-a68k-address/{O0,O2,ubsan}.json`; group digest
`a16891f53c3596c30328d04e684270ee5e029244e6fae81c28b8b2dd4a836a55`.
Cumulative comparisons: **747,700 per build**. Combined dispatch: **47,793/65,536
entries (72.93%)**, **795/1,667 targets (47.69%)**, not weighted CPU completion.
Remaining instructions and full execution/audio integration are open.


## A68K Bit Operations — 2026-11-04

BTST/BCHG/BCLR/BSET register and memory forms: **84/84 targets (100%)**, all
1,818 encodings and **116,352 new comparisons** pass O0/O2/UBSan. Register and
immediate counts, modulo-32/modulo-8 selection, register aliases, prior flags,
PC-relative reads, direct/callback accesses and publication timing match. Only
Z changes; X and other saved flag bits remain intact. The original immediate
count fetch shares the opcode-fetch byte sequence: the harness now explicitly
uses the final fetch as its boundary, and all previous groups pass unchanged.

Receipts: `port/build-a68k-bit/{O0,O2,ubsan}.json`; group digest
`f23627e7851875d4682ae1b8f9436fd32fe3c0deb1f1c6f36ab517ba9136203d`.
Cumulative comparisons: **864,052 per build**. Combined dispatch: **49,611/65,536
entries (75.70%)**, **879/1,667 targets (52.73%)**, not weighted CPU completion.
The harness also rejects overlapping group target sets before reporting coverage.
Remaining instructions and full execution/audio integration are open.


## A68K MOVE Register/Immediate To Memory — 2026-11-04

**46/46 targets (100%)**, all 2,142 encodings and **68,544 new comparisons** pass
O0/O2/UBSan. Original An aliases, full byte/word callback arguments, source capture
before destination address updates, immediate/EA extension ordering, flags and
native costs match. Direct writes and callback-observed contexts are compared.

Receipts: `port/build-a68k-move-dest/{O0,O2,ubsan}.json`; group digest
`2374935c493a0fb657a701a64d729665fe44294a2e44f6768583637e45341667`.
Cumulative comparisons: **932,596 per build**. Combined dispatch: **51,753/65,536
entries (78.97%)**, **925/1,667 targets (55.49%)**, not weighted CPU completion.
Memory-to-memory MOVE, remaining instructions and full integration remain open.

## A68K MOVE Memory To Memory — 2026-11-04

**225/225 targets (100%)**, all 5,544 encodings and **177,408 new comparisons**
pass O0/O2/UBSan. The tests cover all four direct/callback combinations,
source/destination extension ordering, 22,272 same-register cases and 34,536
same-address cases. Source reads precede destination address calculation; the
latter observes source-side address-register updates. Full callback values,
publication timing, flags, writes and native costs match.

Receipts: `port/build-a68k-move-memory/{O0,O2,ubsan}.json`; group digest
`5c793ad331fbb5a3a293d60ac74b93c205bc37f5b39eaf043024dfaaab9728c6`.
Cumulative comparisons: **1,110,004 per build**. Combined dispatch: **57,297/65,536
entries (87.43%)**, **1,150/1,667 targets (68.99%)**, not weighted CPU completion.
Independent read/write maps and exact-address aliases are tested; complete sound
board mapping, remaining instructions and execution/audio integration stay open.

## Historical A68K Provenance — 2026-11-04

The public [Make68K 0.30 generator](https://github.com/finalburnneo/FBNeo/blob/388cc91c3d1fc8e041dc081ad67ddf84dab03e64/src/cpu/a68k/fba_make68k.c)
credits Mike Coates and Darren Olafson (1998–2001). This is an existing 68000
implementation, not evidence of a CPU written wholly by ElSemi. The reproduced
Nebula changelog records switching to Mike Coates' A68K in version 1.7; that
historical statement concerns Nebula, not the exact Model 2 Emulator 1.1a source
revision. The locally retained Model 2 README does not identify its CPU library.

`tools/a68k_provenance.py` compiles the unmodified, hash-pinned public generator
and compares its generated dispatch partition with the original EXE. All
**65,536 encodings** group into **1,667 labels/targets in exact one-to-one
correspondence**, with no split label or target. The compressed-table decoder,
context conventions and distinctive NEGX sequence also agree on inspection.
This strongly supports A68K derivation. It does not establish exact source
revision, byte/semantic identity, or the extent of ElSemi-specific changes.

Reference SHA-256:
`dc8aa0f26d975f9b62eebfb9a27d1176c83a360bd68af8e233fc55fd8d6fcf07`.
Receipt: `port/build-a68k-provenance/result.json`; mapping digest
`3b72dd541dc0735f5cad098e5c7c380b55fb3e493a403313e4f6f22e02faaf64`.
The tool retains only results/mapping and removes generated assembly/compiler
products. Reproduce with a locally supplied copy of that exact source:

```sh
python3 tools/a68k_provenance.py port/build-sharc/original/EMULATOR.EXE /path/to/fba_make68k.c --output port/build-a68k-provenance/result.json
```

The generator is a reference for subsequent reconstruction, not imported CPU
code. Its current FBNeo settings (for example banking and zeroing strategy) must
not be assumed to match ElSemi. The pinned EXE remains the behavioral authority;
later fixes must not silently replace original behavior. A68K authorship and
any future source-derived contribution must retain accurate attribution.

## A68K MULU/MULS — 2026-11-04

**22/22 targets (100%)**, all 848 encodings and **27,136 new comparisons** pass
O0/O2/UBSan together with previous groups. Register, immediate and memory sources,
signed/unsigned edge operands, aliasing, PC-relative space, publication timing,
full products and native fixed costs match. Historical Make68K `mul()` guides
structure/comments; original EXE remains the behavioral authority.

Receipts: `port/build-a68k-multiply/{O0,O2,ubsan}.json`; group digest
`a3a4cf923b175f7b5f620e95079455876207b29a43f44e3bda637198f23281f3`.
Cumulative comparisons: **1,137,140 per build**. Dispatch: **58,145/65,536 entries
(88.72%)**, **1,172/1,667 targets (70.31%)**, not weighted CPU completion.
A68K remains unlinked; other instructions and full integration are still open.

## A68K Register Rotations And Memory Shifts — 2026-11-04

**80/80 targets (100%)**: 24 register ROR/ROL/ROXR/ROXL targets (1,536 encodings,
92,160 comparisons) and 56 word memory shift/rotate targets (336 encodings,
21,504 comparisons). O0/O2/UBSan and previous groups pass. Preserve the original
count masking, cycle-subtraction carry for ROR/ROL count 32, byte-only X updates
in register ROX, and distinct publication order for memory families. Logical
memory shifts save full X before clearing saved DH, not merely the V bit.

Receipts: `port/build-a68k-rotate-shift/{O0,O2,ubsan}.json`. Digests:
- Register rotations: `2972d2088ebb8ed1d58e3bbad69b37bd4e8e9e64ae0ee002a4f785ebae7043f8`.
- Memory shifts: `c4910e41ed72baaaaa0e9ac0c545ce7c69674b81e7c9e3c2c20705ac759abca6`.

Cumulative comparisons: **1,250,804 per build**. Dispatch: **60,017/65,536 entries
(91.58%)**, **1,252/1,667 targets (75.10%)**, not weighted CPU completion.

Supplementary `tools/a68k_host_shift_compare.py` executes 6,912 isolated x86
SHR/SHL/SAR cases under Rosetta and Unicorn. Results and NZPC/AF agree in every
case; 900 cases differ only in multi-bit overflow. The pending original register
shift paths discard/recompute that overflow rather than consuming it directly.
Single-bit overflow agrees. This is host-instruction evidence, not execution of
the Windows binary under Rosetta or a guarantee for ISA-undefined flags on all
physical CPUs. Receipt: `port/build-a68k-host-shift/result.json`. Historical
source structure guides recovery; original executable remains authoritative.

## DIVS Host Overflow Boundary — 2026-11-04

The historical Make68K `divides()` generator emits a 32-bit CDQ/IDIV before its
16-bit guest quotient-range check. The pinned original does the same: DIVS.W
D0,D1 with D0=0xffff and D1=0x80000000 raises a host divide exception at
`0048198c` (`IDIV EBX`). Four adjacent/range-control cases reach ordinary opcode
boundaries. `tools/a68k_divide_fault_probe.py` reproduces this without ROMs;
receipt `port/build-a68k-divide-fault/result.json` retains the five cases.

The user requested analysis of Windows handling before choosing a portable
fault policy. The follow-up follows the original executable through its callers
and exception filters, rather than treating the Unicorn CPU exception as proof
of full-process behavior.

| Original Location | Verified Behavior |
| --- | --- |
| A68K direct callers `004af01d`, `004b3064`, `004cc736` | Sound scheduler / CPU wrapper; no local SEH registration in the reviewed bodies. LLVM finds the wrapper call omitted by the inherited decompilation. |
| Machine frame `004cc7a0`, vtable slot `0051bbd0` | Reached from the main emulation loop through vtable offset +4. No local SEH registration. |
| Main loop `004f68e0`, handler `005042be` | C++ metadata `00525378` has zero catch blocks and EHs flag 1. The unchanged handler returns `ExceptionContinueSearch` for both integer division status codes. Its unwind metadata concerns cleanup, not arithmetic recovery. |
| CRT startup scope `00524bc0`, filter `00493ff5` | Calls `__XcptFilter` (`004a168b`). The original action table at `0050ee90` contains access/illegal-instruction and floating-point codes, but neither `c0000094` nor `c0000095`. Both return `EXCEPTION_CONTINUE_SEARCH`. |
| Top-level filter `004a163b` | Handles C++ exception code `e06d7363` with recognized metadata; integer faults return `EXCEPTION_CONTINUE_SEARCH`. CRT initializer `004a167d` installs it. |
| Other `SetUnhandledExceptionFilter` calls | `0049545c` and `004a1605` clear the filter during fatal-reporting paths; neither installs an emulator arithmetic recovery handler. |

`tools/a68k_windows_exception_audit.py` executes the three unchanged filter
bodies for both integer statuses and an access-violation control, plus two
positive action-table controls: **11/11 checks pass**. Synthetic per-thread
storage replaces only CRT TLS lookup; filter code and default action table come
from the pinned binary. SEH disposition `ExceptionContinueSearch` is 1, whereas
the filter-expression constant `EXCEPTION_CONTINUE_SEARCH` is 0: the receipt
keeps those APIs distinct. Receipt:
`port/build-a68k-windows-exception/result.json`.

No recovered handler repairs the quotient, converts the fault into guest V, or
advances the faulting instruction. With the ordinary Windows unhandled-exception
path, the expected outcome is process termination, not resumed emulation. This
is an inference from original-code evidence and the documented
[Windows unhandled-exception behavior](https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-unhandledexceptionfilter),
not a crash observed in the complete Windows process. External DLL handlers,
debugger intervention and reachability during a game are not tested here. Both
integer status codes are exercised without assuming which code a particular
Windows architecture reports for x86 quotient overflow.

The subsequent user decision approves a selector: **Stop Content (Default)**
reports the fault and stops only the content; **Original** propagates the host
error. Neither is a correction of the guest quotient or flags. The actual
Windows-process probe below supersedes the earlier inference-only limit.

## A68K Register Arithmetic/Logical Shifts — 2026-11-04

**27/27 targets (100%)**, 1,536 encodings and **92,160 new comparisons** pass
O0/O2/UBSan with previous groups. Native zero-count behavior, partial-register
writes, special ASL #1 timing, narrow count-32 flag behavior, and the long ASL
big-shift tail that leaves X untouched are retained. ASR uses the original LAHF
subset; logical shifts clear saved DH. Source comments link these choices to
Make68K while native code fixes the final behavior.

Receipts: `port/build-a68k-register-shift/{O0,O2,ubsan}.json`; group digest
`44f50de31e7d701de2b7f3f66ec7c922ad2835f1572c4edfc55f08bde2973540`.
Cumulative comparisons: **1,342,964 per build**. Dispatch: **61,553/65,536 entries
(93.92%)**, **1,279/1,667 targets (76.72%)**, not weighted CPU completion.
Other instructions and full CPU/audio integration remain open.


## A68K JMP/JSR — 2026-11-04

**14/14 targets (100%)**, all 56 encodings and **14,336 new comparisons** pass
O0/O2/UBSan. Effective-address extension consumption, JSR A7 alias ordering,
stack return PC with retained raw high byte, destination rebinding, original
cycle boundaries and 4,221 approved odd-vector fatal prefixes agree. The shared
transfer helper also preserves the previous 70,144-case branch-group digest.

Receipts: `port/build-a68k-jump/{O0,O2,ubsan}.json`; group digest
`02026ba28687a5e51892cfa5a011849f9dbd7fd6ab999f8995196490fa0e42a5`.
Cumulative comparisons: **1,357,300 per build**. Dispatch: **61,609/65,536 entries
(94.01%)**, **1,293/1,667 targets (77.56%)**. Synthetic CPU/bus boundaries only;
not full execution or sound-board qualification.


## A68K Effective-Address Immediate Arithmetic — 2026-11-04

**21/21 targets (100%)**, all 168 added encodings and **6,552 new comparisons**
pass O0/O2/UBSan. OR/AND/ADD/SUB/CMP immediate sources to Dn, and
ADDA/SUBA/CMPA immediate sources to An, reuse the recovered operand reader.
Original word sign extension, full-width CMPA flags, unchanged address-arithmetic
flags/X, and 4/6-cycle charges are retained. These are distinct native handlers
from ORI/ANDI/ADDI/SUBI/CMPI; their timing is not normalized to the latter.

The expanded operand group has 57 targets, 1,760 encodings, 68,640 cases and
digest `52b61bc757a2bbc93b443715a5ebb9a93f24e74882ea880a0b28c973fd2c5f20`.
Receipts: `port/build-a68k-immediate-high/{O0,O2,ubsan}.json`.
Cumulative comparisons: **1,363,852 per build**. Dispatch: **61,777/65,536 entries
(94.26%)**, **1,314/1,667 targets (78.82%)**, not weighted CPU completion.
DIVS was outside this group; its subsequent qualification is recorded below.


## DIVS Windows Process And Error Policy — 2026-11-04

The ROM-free debugger probe in `port/a68k/test/windows_exception_probe.cs`
starts a private copy of the pinned original executable in Windows 11 ARM64.
At `004f6900`, after the native main-loop SEH registration, it preserves the
host stack/SEH chain and enters the unchanged DIVS D0,D1 body with synthetic
operands. D0=0xffff, D1=0x7fffffff reaches the guest-overflow tail at `004819e0`;
the debugger then terminates this control process before its synthetic next
fetch. D1=0x80000000 generates **STATUS_INTEGER_OVERFLOW (c0000095)** at
`0048198c`, first chance then second chance. The debugger declines both; the
original process exits with **c0000095**. The two fault snapshots match.

This proves process behavior for these injected operands and the original
installed handlers on this Windows host. It does not prove game reachability,
all Windows architectures, or behavior with third-party handlers. No ROMs were
loaded/copied. The first two staging attempts stopped before the probe with a
missing dependency (c0000135); the passing run reused the existing qualified
x86 d3dx9_42.dll without installing it globally.

Receipt: `port/build-a68k-windows-process/results-c/windows-divs.json`, with
`provenance.json` and `dependency.json`. Reusable tools are the C# probe and
`windows_exception_probe.ps1` / `windows_exception_run.ps1`; the latter takes
an explicit existing DLL path and runs through the established remote runner.

Prepared selector contract: `model2emuex_a68k_divs_error_handling`,
**A68K DIVS Error Handling**, values `stop_content` / `original`, labels
**Stop Content (Default)** / **Original**, read on content load, A68K only.
`port/a68k/divs_error_policy.{c,h}` keeps this host policy separate from guest
state and recovered arithmetic. The default returns the sticky fault for the
caller to report and stop content. Original raises Windows c0000095 or POSIX
SIGFPE; no undefined C division or synthesized guest overflow is introduced.
A returning external handler is not allowed to resume an unrecovered CPU.
Portable signal delivery is a host adaptation, not an identical x86 fault
address or Windows context on other platforms.

`tools/a68k_error_policy_test.py` passes O0/O2/UBSan on macOS with an owned
subprocess for Original; normal/default paths preserve CPU state and unrelated
faults are unaffected. Receipt: `port/build-a68k-divs-policy/result.json`.
A separate MinGW-built Windows child then qualifies the actual RaiseException
implementation: Stop Content exits normally after checking the returned fault
and unchanged CPU state; Original exits with c0000095, matching the native
process probe. `port/a68k/test/windows_policy_run.ps1` reuses the installed
compiler, modifying PATH only inside its owned test process. Receipt:
`port/build-a68k-windows-policy/results-b/{policy,provenance}.json`.
This remains an isolated policy check, not frontend execution. A68K remains unlinked: this selector is prepared, **not registered in the
operational frontend**. Its actual menu binding, notification/content stop and
backend visibility must be qualified with sound-board integration. No installed
core, standalone checkout, commit or push was changed.


## A68K Register/Immediate Division — 2026-11-04

**4/4 targets (100%)**, 144 encodings and **60,480 cases per build** pass
O0/O2/UBSan, with previous groups. Signed/unsigned results and packed remainders,
guest overflow with unchanged destination, original cycle refunds for divisor
zero, exception callbacks and zero-budget JLE behavior are preserved. The 192
host-overflow cases match the original prefix immediately before IDIV; 3,408
odd-vector cases match the previously approved prefix. There are 50,400 sticky
post-fault retry checks. No quotient/CCR correction is introduced.

The dedicated native probe executes the faulting IDIV. The bulk differential
suite stops before that instruction for known host-fault operands: repeatedly
injecting CPU exceptions into one Unicorn instance leaves engine exception
state that is not original CPU behavior. The separate real Windows-process
probe qualifies the native termination independently.

Memory-source forms are not included: their zero-divisor path exposes native
read-wrapper scratch EDX. This must be reconstructed rather than replaced with
saved guest flags or an invented value.

Receipts: `port/build-a68k-divide-full/{O0,O2,ubsan}.json`; division digest
`b1f4fbcba00b7adee4642cad9440b79ad02d310ce8e2951c5bcc248b02f03440`.
Cumulative: **1,424,332 comparisons per build**. Dispatch: **61,921/65,536
entries (94.48%)**, **1,318/1,667 targets (79.06%)**, not weighted CPU completion.
Source hashes were checked before removing redundant stdout logs. A68K remains
unlinked, with no operational core or standalone change from this group.


### A68K TAS, TST An And Software Traps — 2026-11-04

Five native targets and 41 encodings add **14,784 original-code comparisons**:
1,728 TAS/TST An cases and 13,056 TRAP/TRAPV cases. O0/O2/UBSan and all previous
groups pass. TAS retains flags from the original byte before setting bit 7;
TST An follows the native dispatch aliases without changing An. TRAP stores the
next PC and exits at zero budget; TRAPV with V set stores the instruction PC,
then charges four cycles with JS (zero continues). The 3,168 odd-vector trap
prefixes preserve the approved diagnostic boundary.

Expanded register-group digest:
`5f325536f3354e5d4e7b83c51be04bfff9922c79ceb5ce0151b716e2918c8aa0`.
Software-trap digest:
`2e5b468bab8bec108f39b19f113772f79e612a39cd67fc7b91a52cf713903ac6`.
Receipts: `port/build-a68k-software-trap/{O0,O2,ubsan}.json`; current source hashes
and redundant stdout equality verified before cleanup. Cumulative:
**1,439,116 comparisons per build**. Dispatch: **61,962/65,536 entries (94.55%)**,
**1,323/1,667 targets (79.36%)**, not weighted CPU completion. Still unlinked;
no audio/game execution claim or installed-core change.


### A68K USP Transfers And Native BTST Immediate — 2026-11-04

**3/3 targets (100%)**, 24 encodings and **12,800 new comparisons** pass
O0/O2/UBSan with prior groups. MOVE An,USP / MOVE USP,An retain all eight register
aliases, privilege-exception PC, callback publication and the native four-cycle
charge; 1,536 odd-vector prefixes match. The original BTST Dn,#word dispatch
entry tests only the low byte, masks the bit count to 0..7 and updates only Z.
No independent decoder rejects or normalizes this original capability.

USP digest: `5861c01c87109a40da08b4d69707b0cd57029688f7ded7ed5857256e950e5d2b`.
Expanded bit-group digest:
`ea7aecabd92de6b3b96c5ea33c511a7c81acb3a2630000410029b1f2763faf7b`.
Receipts: `port/build-a68k-usp-bit/{O0,O2,ubsan}.json`; current source hashes and
redundant stdout identity checked before cleanup. Cumulative:
**1,451,916 comparisons per build**. Dispatch: **61,986/65,536 entries (94.58%)**,
**1,326/1,667 targets (79.54%)**, not weighted CPU completion. A68K remains
unlinked; no installed-core change or gameplay/audio qualification.


### A68K RTS — 2026-11-04

The native RTS target / single encoding passes **27,648 new comparisons** in
O0/O2/UBSan, with all prior groups. Tests cover stack wrap/unaligned/cross-page
starts, direct and callback reads, all guest CCR combinations, user/supervisor
mode, raw-PC high bits, even/odd return targets and cycle boundaries. The native
order increments A7 before reading and publishes the current instruction PC
without adding two. Return rebinding reuses the already qualified JMP/JSR
helper; 6,912 odd-vector prefixes preserve the approved fatal boundary.

The native oracle uses the actual stack read wrapper and the established
synthetic vector service independently. This does not qualify aliasing between
stack and vector storage or the complete sound-board address map.
Digest: `fc95d43a4137c5c84b45a61ebfdf69728d078a8612f5b5dbedc3bf6ca1520930`.
Receipts: `port/build-a68k-rts/{O0,O2,ubsan}.json`; source hashes and redundant
stdout checked before cleanup. Cumulative: **1,479,564 comparisons per build**.
Dispatch: **61,987/65,536 entries (94.58%)**, **1,327/1,667 targets (79.60%)**,
not weighted CPU completion. RTR/RTE and full integration remain open.


### A68K ABCD/SBCD Register Forms — 2026-11-04

**2/2 targets (100%)**, 128 encodings and **483,328 new comparisons** pass
O0/O2/UBSan with all previous groups. This includes **262,144 exhaustive byte
pair/X cases**, including non-BCD digits, plus all register aliases, sticky-Z
states and cycle tails. Original ADC/DAA or SBB/DAS behavior is retained,
including the explicit saved-flag merge: C is copied into N, high flag bytes
(including V) remain unchanged, Z is sticky and full saved flags are copied to X.
The historical Make68K `abcd_sbcd()` emitter explains the same sequence.

Digest: `e2aa79c053e76b67c364530d2e250e7835d26290b94ed0df6451d37ec989f43a`.
Receipts: `port/build-a68k-bcd-register/{O0,O2,ubsan}.json`; current source hashes
and redundant stdout identity checked before cleanup. Cumulative:
**1,962,892 comparisons per build**. Dispatch: **62,115/65,536 entries (94.78%)**,
**1,329/1,667 targets (79.72%)**, not weighted CPU completion.

`tools/a68k_remaining_inventory.py` reuses the existing ISA-label acquisition and
qualified dispatch receipts to index remaining native targets. Labels identify
work, not semantic authority; disassembler pseudo-ops do not imply native
illegality. The post-ABCD/SBCD inventory has 338 targets / 3,421 entries left.
Complete execution, scheduling, state and frontend integration are additional
work, not included in these instruction coverage counts.


### A68K NBCD And Consumption Stop — 2026-11-04

**1/1 target (100%)**, eight encodings and **24,576 new portable comparisons**
pass O0/O2/UBSan with all prior groups. Unlike ABCD/SBCD, NBCD imports full
PUSHFD after DAS, replaces Z rather than keeping it sticky, and copies those
flags into full X. All 512 byte/X pairs were first acquired from the original
Windows 11 ARM64 process after native SEH registration and compared with the
same native body under Unicorn: **512/512 match**, including OF=0. This is
observed behavior on that host, not a guarantee for undefined OF on every x86
processor. No ROMs were copied or loaded.

Windows acquisition/comparison: `port/build-a68k-nbcd-windows/`.
Reusable tools: `port/a68k/test/windows_exception_probe.cs` (`RunNbcd`),
`windows_nbcd_probe.ps1`, and `tools/a68k_nbcd_probe.py`. The owned remote root
and duplicate local staging were removed after hash verification; results and
tools remain. Portable receipts: `port/build-a68k-nbcd/{O0,O2,ubsan}.json`;
digest `d72c1a8d396bf7ec01b758c8498041b9a2a207230729139738e4c2e3f911fbab`.
The preceding ABCD/SBCD digest is unchanged. Source hashes and redundant stdout
identity were checked before cleanup.

Cumulative: **1,987,468 comparisons per build**, plus separate host/policy guards.
Dispatch: **62,123/65,536 entries (94.79%)**, **1,330/1,667 targets (79.78%)**;
not weighted total CPU completion. The current qualified inventory leaves
337 targets / 3,413 entries. It is indexed in
`port/build-a68k-nbcd/remaining.json`, reusing the existing ISA-label acquisition.
Remaining families include memory conditional stores, SR/CCR moves, MOVEM/MOVEP,
CHK, memory NEG/NOT/division/BCD, extended arithmetic, CMPM, RTR/RTE/RESET/STOP
and native entries needing label review. Complete execution, sound scheduling,
Save States and frontend registration remain separate integration work.

Work stops at the user-authorized **50% total account usage**; reported reset
2026-11-11 06:21 CET. No further implementation group started. A68K and its
prepared DIVS selector policy remain unlinked; operational Musashi and the
installed core are unchanged. No commit or push. Astra / High remains suitable
for the remaining original-code reconstruction.

### A68K Memory NBCD And State-Restoring Returns — 2026-11-04

The renewed cap is 55% total account usage. Memory NBCD recovers **9/9 native
bodies (100%)**, 42 dispatch encodings and **2,688 added cases**. The existing
memory-unary suite now has 29,568 cases and the register NBCD regression retains
24,576 cases. Native memory forms preserve flags/X until after the write and
pass the zero-extended byte result, unlike the retained high bits of several
other native writes. The arithmetic reuses the previous Windows-qualified DAS
result. Receipts: `port/build-a68k-nbcd-memory/{O0,O2,ubsan}.json`.

RTR/RTE recover **2/2 native bodies (100%)** and two encodings with **36,864
comparisons**. A reusable scripted bus fixture verifies every read's published
CPU context through the actual original wrappers. Both increment A7 before
reading and publish the full status-read return as PC before the second read.
The native CCR lookup writes its whole high byte into low X, preserving the
upper three X bytes. RTE restores the low SR-high byte, switches to USP when
requested and rechecks IRQ using live PC/flags after its own cycle charge.
RTR retains supervisor state and does not recheck IRQ. The suite covers all
32 CCR values, privilege and stack switching, masked/accepted level 3 and level
7 IRQs, automatic/explicit vectors, odd return addresses, odd-vector guarded
prefixes and cycle boundaries. Scripted callbacks are not full-board/direct-map
aliasing or arbitrary callback mutation qualification.

The full suite passes O0/O2/UBSan: **2,027,020 comparisons per build** plus
separate host guards. Dispatch coverage is **62,167/65,536 (94.86%)** and
**1,341/1,667 native targets (80.44%)**, not weighted CPU completion.
Receipts: `port/build-a68k-restore/{O0,O2,ubsan}.json`; all recorded source hashes
verified before the next group. Restore digest:
`4883836e73263b9aff038569691efaca259dfc9c696e04a846353609149b6399`.
The research CPU remains unlinked. No operational core, ROM or user-save changes.

### A68K MOVEP And CMPM — 2026-11-04

**10/10 native targets (100%)**, 448 encodings and **30,720 new comparisons**
pass focused O0/O2/UBSan runs: 12,288 MOVEP and 18,432 CMPM cases. MOVEP retains
full rotated write arguments, two-byte address spacing and the captured flag
word. CMPM retains ordered postincrements, A7 byte increments, same-register
aliasing and full native comparison flags without changing X. The scripted
fixture checks every callback's context and full write argument through the
unchanged original bus wrappers, with odd/wrapping addresses and budget edges.
No direct-map or arbitrary callback-mutation claim is added.

Receipts: `port/build-a68k-sequence/{O0,O2,ubsan}.json`; source hashes verified.
MOVEP digest `5d47bbf709e80ccfa2fb94ce583db53d049b613b50a19a1627e60d88b996bda9`;
CMPM digest `bb522109281ac4a7f712e3f4e2b3385404313022932165ce3d035a5b62e48b17`.
Qualified groups now cover **62,615/65,536 entries (95.54%)** and
**1,351/1,667 targets (81.04%)**. The complete suite will be rerun after the
related memory-transfer batch. A68K remains unlinked and the installed core is
unchanged.

### A68K MOVEM And STOP Qualification — 2026-11-04

The complete suite passes O0/O2/UBSan after MOVEP/CMPM, MOVEM, STOP and the shared
status-import refactoring: **2,149,516 comparisons per build** plus host guards.
MOVEM adds **28/28 native targets (100%)**, 140 encodings and 67,200 cases. Tests
cover empty/full/alternating register lists, each individual register, every
encoding/address mode, callback-visible state and cycle boundaries. Retained
quirks include mask publication through saved flags, original-base stores in
predecrement mode, delayed final writeback, the initial four-byte postincrement
even for word transfers and exit at zero cycles in postincrement mode.
STOP adds **1/1 target (100%)**, one encoding and 24,576 cases. Its accepted IRQ
path precedes the ordinary four-cycle charge; otherwise it discards the budget,
marks bit 7 of IRQ and exits at -4. Wakeup in the future scheduler is not yet
qualified.

Full receipts: `port/build-a68k-transfers/{O0,O2,ubsan}.json`; source hashes were
verified before the next implementation group. Dispatch coverage at this stage:
**62,756/65,536 entries (95.76%)**, **1,380/1,667 targets (82.78%)**. These are
coverage measures, not weighted overall CPU completion.

### A68K Status, Decimal Memory And Gated Control Entries — 2026-11-04

The full original-code suite passes O0/O2/UBSan: **2,824,332 comparisons per
build**, plus ten separate host-binding guards. Source hashes and unchanged
digests for the prior BCD, return, MOVEP/CMPM, MOVEM and STOP groups were checked
before continuing. Receipts: `port/build-a68k-status-control/{O0,O2,ubsan}.json`.

| Added Group | Native Targets | Encodings | Comparisons Per Build |
| --- | --- | --- | --- |
| SR/CCR Moves | 38/38 | 206 | 158,208 |
| SR/CCR Logical Immediates | 6/6 | 6 | 147,456 |
| ABCD/SBCD Memory | 8/8 | 128 | 221,184 |
| Gated RTD/MOVEC | 3/3 | 3 | 136,448 |
| RESET Instruction | 1/1 | 1 | 11,520 |

Preserved behavior includes the context+0x7c CCR-export gate; differing IRQ
recheck tails after MOVE-to-SR versus logical-immediate privilege faults;
full byte-write arguments and pre-write X publication in memory BCD; RTD's
opcode-address displacement read; all MOVEC selector aliases; and RESET's
callback slot and prefetched successor even after a negative cycle budget.
The test instruction binding now includes the actual opcode word as well as
extensions, allowing the RTD behavior to be compared directly.

RESET uses a distinct `A68K_PREFETCHED` result with `prefetched_opcode`, requiring
the future execution loop to dispatch that saved opcode without another fetch
or budget test. Tests include absent/present output callbacks and callbacks
that change PC, flags and the already-fetched instruction bytes. Native callback
tokens remain integers: a nonzero token without a host binding is a separate
binding error, not a fabricated guest response.

Dispatch coverage: **63,100/65,536 entries (96.28%)**, **1,436/1,667 targets
(86.14%)**. Each listed group is 100% of its selected native targets; neither
metric is weighted CPU completion. The qualified remaining inventory contains
231 targets / 2,436 encodings: conditional stores, NEG/NOT, memory DIVU/DIVS,
ADDX/SUBX and CHK. Several consume native read-wrapper scratch state. Full CPU
execution, board/scheduler/state integration and frontend qualification remain.
All new runtime comparisons are ROM-free native x86 bodies under Unicorn, not
additional original-Windows gameplay evidence. A68K remains unlinked; the
operational core checksum is unchanged. The user renewed the cap to 60% total
account usage during verification; work continues, with no commit or push.

### A68K CHK And Explicit Read Scratch — 2026-11-04

All 11 CHK targets / 424 encodings are qualified: 55,296 register/immediate
and 270,336 memory comparisons. The full suite passes O0/O2/UBSan with
**3,149,964 comparisons per build**, plus 15 separate host-binding guards.
Source hashes were verified before further edits. Every prior group's result
digest is unchanged, including the scripted-map fixture optimization.
Receipts: `port/build-a68k-chk/{O0,O2,ubsan}.json`.

Memory CHK retains read-wrapper/callback EDX as live flags even on the
non-trapping path. Tests vary direct allocation tokens, callback-return EDX,
all addressing forms, signed bounds, privilege state, zero-cycle boundaries
and odd exception vectors. The known upper-bound mask clears bits above bit 6;
the negative-value path only sets N. Both original behaviors are retained.
The observation binding carries EAX and EDX separately and rejects missing
provenance rather than assuming guest flags or zero. Real sound-board base
allocation and callback register origins remain integration work.

Dispatch coverage: **63,524/65,536 entries (96.93%)**, **1,447/1,667 targets
(86.80%)**. This is not weighted CPU completion. A68K stays unlinked, with no
new frontend, audio or original-Windows gameplay claim. The shared immutable
script maps remove redundant table initialization only; test cases and result
digests are unchanged. Duplicate stdout receipts were removed only after JSON
equality with the retained results. No commit, push or installed-core change.

### A68K Memory Arithmetic Qualification — 2026-11-04

The next related group passes the full O0/O2/UBSan comparison:
**3,338,124 comparisons per build**, plus 15 host-binding guards. All prior
result digests and source hashes were checked before the next edits.
Receipts: `port/build-a68k-memory-arithmetic/{O0,O2,ubsan}.json`.

| Added Group | Native Targets | Encodings | Comparisons Per Build |
| --- | --- | --- | --- |
| NEG/NOT Memory | 46/46 | 252 | 48,384 |
| ADDX/SUBX Memory | 12/12 | 384 | 55,296 |
| DIVU/DIVS Memory | 18/18 | 704 | 84,480 |

NEG/NOT retain the read-return EDX in the context observed by the write callback;
NEG publishes X after that write. ADDX/SUBX preserve both predecrements, A7 byte
steps and same-An aliasing; sticky Z comes from the second read's EDX, while X
receives the pre-merge flags. DIV preserves the read-return EDX at vector 5,
original timing refunds, quotient overflow and the already-approved host-IDIV
fault guard. The memory DIV suite includes 2,112 host-overflow prefix cases,
8,448 odd-vector cases and 147,840 retry-guard checks. It is not a new Windows
crash test or a correction to guest arithmetic.

Dispatch coverage: **64,864/65,536 entries (98.97%)**, **1,523/1,667 targets
(91.36%)**. Only memory Scc remains in the target inventory (144 targets / 672
encodings). Full execution and real board scratch provenance are separate work.
The original executable, reusable tools and compact receipts remain; task-owned
temporary focused libraries and duplicate stdout receipts were removed. No ROM,
save, installed-core, commit or push changes.

### A68K Complete Dispatch Inventory Qualification — 2026-11-04

Memory Scc adds **144/144 targets**, 672 encodings and 86,016 comparisons.
The complete suite passes **3,424,140 comparisons per build at O0, O2 and
UBSan**, plus 16 separate host-binding guards and the existing fault-retry
checks. Every prior result digest is unchanged; all source hashes were verified.
Receipts: `port/build-a68k-scc-memory/{O0,O2,ubsan}.json`. The remaining-target
inventory is empty: **1,667/1,667 targets and 65,536/65,536 entries (100%)**.

This is complete dispatch-inventory coverage, NOT a completed executable CPU.
Scc tests supply original entry EAX explicitly. Some forms retain its high bytes;
displacement/index forms derive them from addressing, SHI/SLS replace AH from
flags, SF clears EAX, and signed conditions publish IF. Missing required entry
scratch is a binding error. Propagating predecessor/callback EAX and recovering
real board read-return EDX/direct-base tokens remain execution/integration work.
Do not substitute a constant or portable host pointer for those original values.

The flow fixture previously assumed at least one known target was unrecovered;
its StopIteration at full coverage was corrected to always test an unknown token
and additionally test a known unrecovered target only while one exists. No
instruction behavior changed to satisfy this test. The compact failure record
is retained alongside successful results. Temporary focused libraries and
verified duplicate include/stdout files were removed; tools and compact receipts
remain. The operational build SHA-256 remains
`614dedaa458b6849c40b60e718568f5473f7d239fb34b7551a9d84cfed72ccd7`.

Work stopped at the authorized **60% total account-usage cap** after collecting
already-running verification. Reported reset: **2026-11-11 06:21 CET**. Next:
complete execution-loop and native scratch propagation, board/scheduling,
Save States, then audio/frontend qualification. A68K remains unlinked and
Musashi operational. No installed-core change, commit or push.

### A68K Continuous Scratch Qualification — 2026-11-04

The user renewed the total account-usage cap to 65%. The new observed entry
and step APIs qualify **339/1,667 native targets (20.34%)**, or **13,417/65,536
encodings (20.47%)**, separately from the already-complete single-handler
inventory. The original sequence oracle enters `00462b1c`, uses the original
dispatch table, and executes continuously without restoring synthetic scratch
between instructions. It compares context, PC, live/published flags, cycles,
next-entry EAX, host control flags and full callback write arguments.

O0/O2/UBSan pass **74,548 streams / 206,533 executed steps** with identical
digest `4d55003eecd967688ad0d6c0965c6e9dc24e48120411ae0b4cd2116b9e5a5163`.
The 144 observed-write wrapper cases also agree at every build; their digest is
`2b98a18d395442aa64df3793571525cbd9bc41e013ba0c1eeb9eb460172ba918`.
Seven sequence guards and ten write-binding guards pass separately. Receipts:
`port/build-a68k-sequence/{O0,O2,ubsan}.json`; tools:
`tools/a68k_sequence_compare.py` and `port/a68k/test/sequence_shim.c`.
The full O2 single-handler regression passes 3,424,140 comparisons with all
prior result digests unchanged and 16 separate host-binding guards. Source
hashes were verified; `regression-O2.json` is retained and its identical stdout
duplicate was removed with a compact cleanup receipt.

Historical Make68K `moveq`, `opcode5`, `movecodes`, `addx_subx`, `asl_asr`,
`mul`, `abcd_sbcd`, `nbcd` and `Memory_Write` explain the recovered structure.
The original binary remains the final authority. Notable sequence effects:
register Scc leaves 4/6 in EAX; signed Scc restores DF through POPFD; ASR/ASL
can overwrite AH after writing Dn; word MUL keeps source high EAX bits; direct
byte/word write wrappers return descriptor tokens whereas long writes return
the native base. No native token is converted to a portable pointer.

The first callback fixture failure was a test-map omission: EXG changed the
address register before Scc, so a map installed only for the original address
was insufficient. The reusable fixture now maps the synthetic write callback
for all pages; no emulator behavior was changed to make the test pass.

Limits: real sound-board callback return provenance is still open. The observed
entry/step APIs reject accepted IRQ callbacks, unqualified targets and other
host control/trap bits before execution. Missing write provenance has no
ordinary-callback fallback. The full dispatcher, scheduler, Save States and
frontend integration are unfinished; A68K remains unlinked. No installed core,
ROM, user save, standalone, commit or push changes.


## A68K Source-Led Loop And MOVE Connections — 2026-11-04

The new portable execution connections follow historical Make68K
`CodeSegmentBegin`, `Completed`, `movecodes` and `Memory_Write`, with the ElSemi
binary authoritative for its actual table and behavior. Validation is targeted
at the changes; the general arithmetic/single-handler matrices were not rerun.

- Live loop: 56 original streams, 168 portable comparisons and nine guards at
  O0/O2/UBSan; no differences. Covers budget entry/exit, live versus published
  state, one/multiple-step continuation, extension fetch and callback EAX/DF.
- Original RLE table: all 65,536 entries match, decoded SHA-256
  `8398b07505414aa655a011dc6cf96f0ef879a4a3ab432e48a1bf41cf541c3d20`.
- MOVE write-return connections: 46 additional targets / 2,142 encodings,
  184 original streams and 368 portable comparisons at O0/O2/UBSan; no
  differences. Result SHA-256
  `f20172ab5aba62452249564208ad5af5a79f67259fd57b762b05ae8d4eed8a88`.
- Loop result SHA-256:
  `5bcf9404e093b67448c71e3c4c91cefaae57a9939ad6bbb5613318c842bc2c0d`.

Reusable tool: `tools/a68k_loop_compare.py`, optional `--move-writes`, using
`port/a68k/test/sequence_shim.c`. Receipts are in `port/build-a68k-loop` and
identify their exact source snapshots. Temporary test libraries are removed by
the runner. No ROM, installed core, production sound backend or standalone
checkout was changed. UBSan emitted only the existing duplicate-rpath linker
warning, with no runtime diagnostic.

Cumulative next-handler connection coverage is 385 targets / 15,559 encodings.
This is not overall CPU progress or historical-source acquisition coverage.
Unchanged source-derived bodies retain prior evidence. Native differences and
new portable connections require focused checks; complete sound-board,
scheduler, accepted-IRQ and Save State/frontend integration remain open.
Work stopped at the authorized 65% account-usage ceiling.


## Live Bus And Control Integration — 2026-11-04, +5 Increment

The source-led continuation now connects read returns, memory RMW/unary,
bit/shift/paired operations, MOVEP/CMPM/MOVEM, address/stack/DBcc, branches,
accepted IRQ and software exceptions/USP. Odd jump destinations route through
the native vector-3 body; the approved odd-vector-result fault policy remains.
See the detailed grouped counts and source-snapshot receipts in
[Validation](VALIDATION.md#a68k-source-led-bus-and-control-connections--2026-11-04).
No general arithmetic matrix was rerun. Historical source guides unchanged
bodies; tests focus on portable callback scratch and instruction connections.

The observation inventory is 1,582/1,667 targets and 64,044/65,536 encodings.
Trap/illegal shared handlers explain much of the encoding increase. These
counts do not measure overall CPU completion or unchanged-source identity.
Remaining connections include CHK, divide, status and return/control handlers;
real native callback provenance, sound-board/scheduler/state and frontend
integration are still required. A68K remains research code, not the active
sound CPU. No installed binary or user data was changed.


### Internal Target Inventory Closed

The following groups add RTS/RTR/RTE/RTD, SR/CCR, CHK/DIV and MOVEC/STOP/RESET,
with focused O0/O2/UBSan native comparisons. All 1,667 target tokens and 65,536
opcode entries now have observed internal dispatch paths. RESET's pending
prefetch survives research pauses and callback PC/flag/code changes; native
negative-budget continuation is retained. See the newest Validation section
for counts, result digests and the exact switch-inventory receipt.

This does not claim every opcode input/path, real callback ownership or a
complete sound CPU. Next integration work is the actual sound-board bus and
callback scratch provenance, followed by scheduler/lifecycle, Save States and
frontend qualification. Musashi remains the active production backend.


### Board Integration Decision: CPU RAM Window

The first real-board review confirms a difference: original ElSemi allocates
and maps 1 MiB linearly for SCSP-board CPU RAM, while inherited `m2snd.c` uses
512 KiB mirrored across that window. The ROM-free original-code probe and
exact allocation/map addresses are recorded in VALIDATION.md. Hardware
correctness, game reachability and SCSP sample-address masks are not inferred.

The user approved the shared original map on 2026-11-04 and subsequently
selected original ElSemi/A68K word-swapped storage. The shared allocation is
1 MiB; the separate SCSP sample mask remains 0x7ffff. Musashi guest accesses,
SCSP sample/DMA helpers and the MAME DSP's shared-RAM helpers are adapted;
reconstructed A68K keeps its original direct-storage representation. Original
DSP private RAM and Model 1 sound RAM are unchanged.

State bits 0x00800000 (linear allocation) and 0x00400000 (native storage)
identify the payload, independently of the base ABI. A compile-time assertion
prevents feature/base-ABI overlap. Old map/storage states are rejected without
migration. Synthetic bus/archive/PCM and two-way DMA checks pass; the MAME
baseline comparison also passes after explicit storage normalization. Current
full-core evidence is in VALIDATION.md. A68K remains unlinked and the installed
core is unchanged.


### Shared SCSP CPU Read Recovery — 2026-11-04

The user approved original CPU-facing reads for both 68000 backends. The first
group restores native zero byte reads in ring/DSP space, zero word reads in
DSP space, all-ones long reads, and exact odd slot-word byte assembly. The last
slot register byte is followed by the original active byte, not the portable
struct's next field. CPU accesses use new scsp_cpu_read8/16 boundaries; internal
DMA/DSP uses the unchanged register interface. Twenty-one synthetic cases match
original wrappers/callbacks and VF2 continuation passes.

Global/MIDI reads, native side effects, IRQ lifecycle and A68K host scratch
provenance are still separate unfinished work. The native enqueue/dequeue probe
finds a 128-byte FIFO versus inherited 32 bytes; a 40-byte synthetic burst makes
the difference observable. This is a reconstruction dependency, not a claim of
a game bug. Results/tools and the selected next model are in VALIDATION.md.


### Native SCSP Control Group — 2026-11-04

The preceding global/MIDI/IRQ dependency is now recovered for ordinary CPU
registers: 128-byte FIFO with its separate wrapping counter, stale empty reads,
live slot monitor, native MIDI-first IRQ selection, acknowledge/recompute
ownership, fractional timers and expired-timer relatching. CPU global writes
store without a side-effecting read and retain the original raw SCIPD write.
The complete port snapshot adds this mutable state, with explicit schema and
ABI identity; it does not reproduce omissions in Windows Save State files.

999 native-code cases pass identically at O0/O2/UBSan. The real board/Musashi
fixture consumes 40 commands through IRQ with SCIEB zero and resumes exactly
from a pending-IRQ snapshot after board recreation. VF2/original-DSP and
Sega Rally/MAME-DSP full-core GL checks pass same/fresh-process state, PCM and
image continuation. This is not audible-output or whole-game qualification.

Remaining: global-object aliases outside ordinary 0x400–0x42f/0x500–0x52f
reads, other byte/word/long write edge cases, chip-internal DMA IRQ semantics,
warm-reset retention and actual A68K callback host scratch. The original raw
object layout must be decoded rather than inferred from portable C layout.
Musashi remains the active CPU; A68K scheduling/lifecycle/state/frontend
integration is unfinished. Astra with high effort remains appropriate.


### SCSP Read Return Provenance

The next research observer now preserves the original EAX high bytes, EDX and
x86 control flags for the qualified SCSP CPU read ranges. 664 native wrapper/
callback comparisons plus 24 nonmutating raw-alias guards pass at O0/O2/UBSan.
It is not connected to the production CPU. Known PE addresses are explicit
32-bit tokens; portable pointers are never used as guest-visible scratch.
See port/a68k/PROVENANCE.md for the origin of each return category and the
remaining raw-object/Windows-allocation boundary.


### A68K SCSP Callback Wiring — 2026-11-04

The research DATA/WRITE page binding now uses the recovered read observers and
the new global-write/acknowledge completions. Real A68K bus APIs preserve the
original return values, control flags and SCSP state across 664 read, 960 write
and 576 acknowledge cases at O0/O2/UBSan. Another 1,368 access guards verify
rejection before mutation. This does not activate A68K in `m2snd.c`.

Remaining callback reconstruction includes slot/DSP/output-MIDI writes and raw
object aliases. The user subsequently confirmed original CPU DMA behavior:
registers store normally but no transfer is executed. The shared CPU gate now
implements this choice; internal DMA remains independent. Synthetic native
comparison, Musashi bus and complete-core state checks pass, without a
game-use or audible-output claim. Scheduler, reset/state
lifecycle and final frontend qualification remain separate.

Subsequent board tracing identified the live IRQ autovector at 004b3090.
Musashi and the research A68K binding now use that behavior. The i960
sound-port handlers do not dequeue native SCSP output in the measured
transactions. The separate Manx TT I8251 extension has its own receive
path. See the Native SCSP Board Exchanges section in VALIDATION.md.
