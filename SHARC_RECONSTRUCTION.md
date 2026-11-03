# Native SHARC Reconstruction

Updated: 2026-11-03. Implementation status is tracked by M27 in
[Roadmap](ROADMAP.md). The opt-in research build now executes Fighting Vipers
through scripted combat and real RetroArch attract. This is not whole-catalog
or production qualification. Sections below retain chronological recovery
evidence and its original scope; the latest groups appear at the end.

## Scope And Authority

The user authorized continuing the reconstruction of ElSemi's original
implementation. M2-HLE may be consulted to understand the hardware and compare
behavior; its SHARC interpreter is not the implementation to import. SM2 remains
the frontend reference. The pristine standalone checkout is unchanged.

The first bounded activity is source mapping and one binary-verified helper,
before attempting a complete DSP or board integration. The account-wide usage
baseline is 40%, with an initial ceiling of 50%. No publication is authorized.

## Material Inspected

- Existing `src/all_functions.c`, `src/functions.tsv`, `src/prototypes.h` and
  `src/strings.tsv`, inherited from the pinned upstream baseline.
- Existing `tools/RegionExport.java` and `tools/ptrtables.py` for recovering
  indirect code and dispatch tables from the executable.
- Existing `port/tgp/test/difftest.py` and TGP documentation: native portable
  helpers are compared against original PE32 code under Unicorn.
- Current M2-HLE `src/board/sharc_cpu.h`: a separate MAME-derived implementation,
  not an ElSemi recovery source. No code was imported or executed.

The user authorized autonomous acquisition of `EMULATOR.EXE`. The 1.1a archive
was obtained from [Batocera's distribution repository](https://github.com/batocera-linux/model2emu/tree/57b5cff598e63ca688a9a58f3b341104e43c4b01),
pinned at `57b5cff598e63ca688a9a58f3b341104e43c4b01`; the original author's site
was unavailable. The included ElSemi README identifies version 1.1a.

- Archive SHA-256: `5ffebe72d2885bde3fbfab816947475a9a2ce2795284b9d1e90344209bd4c65f`.
- `EMULATOR.EXE` SHA-256: `2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc`.
- Local image: `port/build-sharc/original/EMULATOR.EXE` (1,924,608 bytes).
- Receipt: `port/build-sharc/original/provenance.json`; this entire directory
  is ignored by Git. Only the executable and its README were extracted.

Static checks confirm PE32/i386, image base `0x00400000`, section layouts
matching the upstream tools, and SHARC strings at `0x0051bd30`/`0x0051bd50`.
The two executables in the archive differ by six bytes, consistent with the
upstream observation. These checks establish consistency with the recovery
material, not an unavailable author-signed hash.

The existing Apple `llvm-objdump` disassembled the complete 41-byte helper at
`0x004bcd10`: input EAX/DL, result EAX, ESI preserved, plain return. The two
variable shifts confirm x86 count masking must be preserved in the first port.
The user subsequently authorized installing Unicorn. Version 2.1.4 is installed
only in `port/build-sharc/venv`, with its test dependency pinned in
`port/sharc/test/requirements.txt`. The Windows application was not launched;
the original helper was executed under Unicorn as described below. No game
ROMs were read or copied.

## Source Findings

The original README's coarse SHARC range is misleading at both ends and is
not a complete inventory. `0x004bbdd0` still initializes the Direct3D renderer
and reads Renderer settings. SHARC reset is present at `0x004c0230`, beyond
the old `0x004c0000` endpoint. Arithmetic handlers also live near `0x00460f40`,
inside the README's broad range labelled A68K.

| Original Address | Evidence In The Existing Export |
| --- | --- |
| `0x00460f20` | Assembly confirms ECX supplies the arithmetic status destination and `FLDCW` loads x87 control word `0x003f`. Floating-point setup is not ported yet. |
| `0x00462140`, `0x004622a0` | Scaling/conversion helpers selected by the SHARC compute decoder; x87 status affects emulated flags. |
| `0x004bc420`–`0x004bc5b0` | Bit-field helpers, with status bit `0x1000` at state offset `0x240`. Similar decompiles do not establish identical original instructions. |
| `0x004bcb80` | Resolves encoded registers to state/decoded-record locations. |
| `0x004bcd10` | Sign-extension helper selected for the first differential experiment. Decompiled inputs are EAX and DL. |
| `0x004bcf70` | Countdown and delayed callback processing. |
| `0x004bdfa0` | Executes two successive decoded records and processes delayed callbacks. |
| `0x004be000` | Execution loop, indirect handlers, loop-stack bookkeeping and stop flag. |
| `0x004be800` | Compute-field decoder selecting both exported functions and address-taken `LAB` targets. |
| `0x004bf610` | Program predecoder: six input bytes per instruction, `0x6c` bytes per decoded record, guest base `0x20000`. |
| `0x004c0230` | Clears `0x2a4` state bytes at `0x010edc30`, initializes stack sentinels, decodes the program and selects initial PC `0x20004`. |
| `0x004c6510` | Model 2B initialization: invokes reset, sets board callbacks `0x004c6020`/`0x004c6100`, and applies game-specific settings. |

These are interpretations of decompiler output. In particular, `in_ECX`,
`in_EDX`, `unaff_*`, inferred pointer types and x87 expressions are not safe C
interfaces. Inspect the original instructions before choosing portable types
or translating calling conventions.

## Missing Indirect Code

Run the ROM-free source inventory:

```sh
python3 tools/sharc_inventory.py > /tmp/model2emuex-sharc-inventory.json
```

The inspected export has SHA-256
`c944723c80b0edb4d6e1c9207ba4290942486a6ec16f96d39e0da5259e4234ae`.
The inventory contains 22 source-identified functions and 116 distinct
address-taken `LAB` candidates referenced by them:

| Candidate Region | Count | Interpretation |
| --- | --- | --- |
| `0x00460f40`–`0x00462a60` | 45 | Arithmetic targets selected by the compute decoder. |
| `0x004b93d0`–`0x004b9480` | 3 | Renderer callbacks changed by game-specific initialization. |
| `0x004bc130`–`0x004be7c0` | 66 | Main SHARC handler targets. |
| `0x004c6020`–`0x004c6100` | 2 | Board callbacks. |

None of these 116 targets has a function entry or label body in the current
`all_functions.c` export. They are recovery candidates, not 116 proven distinct
functions. The count also excludes undiscovered targets in pointer tables such
as `0x00573490` and `0x00573510`; inspect those in the original image.

Reuse `RegionExport.java` with reviewed explicit entry addresses in an isolated
Ghidra project. Its aligned-padding heuristic alone is not proof of function
boundaries. Generated exports, executable images and Ghidra databases stay
outside tracked source.

## First Differential Experiment

Use `0x004bcd10` before bringing in state, FIFO or floating-point dependencies:

1. Identify and hash the original 1.1a PE32 image, inspect the helper instructions
   and confirm its input/output registers and return convention.
2. Reuse the TGP test's PE mapping and bounded Unicorn execution method; call
   the original helper with synthetic inputs, without loading a game.
3. Translate that helper to unsigned, defined C operations. Verify sign-bit
   boundaries, all encoded widths, zero/all-one inputs and fixed-seed random
   cases against the original output.
4. Report mismatches and unsupported cases without skipping them silently.
   Record the executable hash, case counts and native build details.

### Verified Result

`port/sharc/sharc_bits.c` now reconstructs this helper using defined unsigned
C99 operations. No M2-HLE or SM2 implementation was imported. The original x86
code and the native arm64 helper agree on **34,496 inputs**, independently for
both `-O0` and `-O2` builds: **zero mismatches and zero skipped cases**.

Coverage includes all 256 DL encodings, each isolated input bit and single-bit
hole, sign/mask boundaries, alternating bits and 64 fixed-seed random values
per encoding. EDX's upper bits are randomized. The harness also verifies the
original's return, balanced stack, preserved registers, scratch-register results
and sole expected stack write. Host x86 condition flags are not part of the C
helper's result contract. Execution is bounded to 64 guest instructions per
call and a failure aborts the run with the exact input.

The original masks shift counts with `0x1f`. Encoded widths divisible by 32
produce `0xffffffff` for values with bit 31 set and zero otherwise, rather than
returning the input unchanged. Both disassembly and differential execution
confirm this behavior; the recovered helper preserves it. Higher encoded widths
repeat the same count-masking behavior. No hardware-correctness claim follows
from matching this original implementation.

Host: macOS 26.5.1 arm64; Apple clang 21.0.0 (`clang-2100.1.1.101`), Python
3.14.6, Unicorn 2.1.4. Both builds passed `-Wall -Wextra -Werror -pedantic`.
The initial sandboxed attempt stopped with SIGILL in Unicorn's host cache
initialization at `mem_map`, before guest execution. The authorized run outside
the sandbox passed. This is a host-tool constraint, not a SHARC mismatch.

Receipt: `port/build-sharc/bits-differential.json`, including original image,
native source and both library hashes. Reproduction after dependency setup:

```sh
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_bits.c -o port/build-sharc/libsharc_bits_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_bits.c -o port/build-sharc/libsharc_bits_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_bits.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_bits_O0.dylib \
  port/build-sharc/libsharc_bits_O2.dylib \
  --output port/build-sharc/bits-differential.json
```

This completes the first bounded helper activity. The user then authorized
grouping related recovery blocks; the next combined group is recorded below.

## Bit Fields And Register Selection

Seven further original entry points are now reconstructed and compared against
the original image. The portable code remains frontend-neutral and test-only
until the decoder and board integration are ready.

| Original Entry | Portable Operation | Differential Inputs |
| --- | --- | --- |
| `0x004bc420` | Field Deposit | 24,576 |
| `0x004bc470` | Field Extract | 24,576 |
| `0x004bc4c0` | Direct-Operand Field Merge | 25,152 |
| `0x004bc510` | Field Deposit | 24,576 |
| `0x004bc560` | Indirect-Operand Field Merge | 25,728 |
| `0x004bc5b0` | Field Deposit | 24,576 |
| `0x004bcb80` | Register Location And Decode Flags | 1,024 |

The six field routines pass **149,184 cases**, including **1,728 operand/status
alias cases**, for both O0 and O2. The register selector passes **1,024 cases**
for both builds. The original immediate-extension experiment was rerun against
the updated bit-helper library and retains its 34,496 passes. Combined coverage
is **184,704 input cases across eight original entry points**, each compared
with both builds, with zero mismatches and zero skipped cases.

### Recovered Semantics

- The three deposit functions have identical 70-byte machine code, so they
  share one portable implementation. All three original entries were executed.
- `0x004bc470` returns the extracted field in EAX. The raw decompile's `void`
  declaration is incorrect; the assembly and differential results establish
  the return value.
- The control encodes six-bit position and width fields; the x86 shifts mask
  their counts again to five bits. All 4,096 low-control combinations were
  tested, with randomized high control bits.
- Only status bit `0x1000` changes. For deposit/merge, it reflects the masked
  source before shifting, including cases where the shift discards every bit.
  For extract, it reflects the resulting extracted field.
- Merge is OR with the base; the destination field is not cleared first.
  Source values are read before status mutation, but the base is read after
  mutation. The portable merge retains a live base pointer to preserve that
  behavior when the base is the status word. Tests cover source/status,
  base/status, both/status and shared source/base locations as applicable.
- `sharc_registers.c` checks all 256 register codes under four initial flag
  patterns. Group 4 sets decode flag `0x80` while preserving other bits;
  group 6 falls through to the special group-7 mapping for indices 9–15.
  Unmapped codes retain the original decoded-record scratch location.
- Register locations use logical 32-bit word views of the recovered state and
  decoded record. They do not freeze a future serialized host-pointer layout.
  The whole synthetic data arena is compared after each native/original call,
  including guard bytes and unrelated state. Original writes are restricted
  to known stack slots and the appropriate status/decode-flag location.

Receipts: `port/build-sharc/fields-differential.json` and
`port/build-sharc/registers-differential.json`. They record the original image,
portable source and compared library hashes. Reuse the bit-library builds
above for `difftest_fields.py`; build and run the selector as follows:

```sh
port/build-sharc/venv/bin/python port/sharc/test/difftest_fields.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_bits_O0.dylib \
  port/build-sharc/libsharc_bits_O2.dylib \
  --output port/build-sharc/fields-differential.json
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_registers.c -o port/build-sharc/libsharc_registers_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_registers.c -o port/build-sharc/libsharc_registers_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_registers.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_registers_O0.dylib \
  port/build-sharc/libsharc_registers_O2.dylib \
  --output port/build-sharc/registers-differential.json
```

No semantic departure from the original was introduced in this group; the
decompiler signature correction is backed by executable evidence.

## Integer ALU, Shifts And Original Flag Dependencies

The next combined group reconstructs **28 additional original entry points**:
19 arithmetic/logic helpers in `sharc_integer.c` and nine shift/bit helpers in
`sharc_shift.c`. These use the compute selectors observed in the original
`0x004be800` decoder, not a replacement DSP implementation. Unsupported
selectors return failure without changing outputs. The partial helper APIs
are not yet wired into a production decoder.

| Original Entries | Recovered Operations | Differential Inputs |
| --- | --- | --- |
| `0x00460f40`, `0x00460fc0`, `0x00461040`, `0x004610c0` | Add/Subtract And Carry Variants | 31,360 |
| `0x00461140`, `0x004611a0` | Half Sum And Compare | 15,680 |
| `0x004611e0`, `0x00461260`, `0x004612e0`, `0x00461360` | Increment/Decrement And Carry Variants | 31,360 |
| `0x004613e0`, `0x00461460`, `0x004614e0` | Negate, Absolute Value And Pass | 23,520 |
| `0x00461520`, `0x00461560`, `0x004615a0`, `0x004615e0` | AND, OR, XOR And NOT | 31,360 |
| `0x00461620`, `0x00461660` | Signed Minimum/Maximum | 15,680 |
| `0x004627a0`, `0x00462900`, `0x00462960` | Logical/Arithmetic Shift And Rotate | 22,440 |
| `0x00462800`, `0x00462880` | Indirect Shift And OR Merge | 15,660 |
| `0x00462a20`, `0x004629c0`, `0x00462a60`, `0x004bc3f0` | Set/Clear/Toggle/Test Bit | 29,920 |

**148,960 ALU inputs and 68,020 shift/bit inputs pass against original x86
execution**, independently for native O0 and O2 builds, with zero mismatches
and zero skipped inputs. The latter include 700 operand/status alias cases.
Recovery evidence after this group was **401,684 inputs across 36 original entries**,
each compared with both native optimization levels. This is helper coverage,
not instruction-stream or game execution coverage.

### Preservation Notes For Future Review

The user explicitly requested preserving and honoring ElSemi's emulator as it
is, while documenting quirks for possible later review. The following are
intentional reconstructions of its machine code, not claims about physical
SHARC behavior. Do not silently replace them with conventional arithmetic.

- Plain INC (`0x004612e0`) and DEC (`0x00461360`) preserve the **incoming x86
  CF** and transfer it into ASTAT bit `0x8`. This is distinct from incoming
  guest ASTAT carry. Their portable API therefore accepts an explicit snapshot
  of the original helper-entry EFLAGS.
- NOT (`0x004615e0`) leaves x86 flags unchanged. ElSemi copies the **incoming
  x86 ZF/SF** into ASTAT bits `0x1`/`0x4`, even when they do not describe the
  complemented value. The portable helper retains these explicit inputs.
- The helper contract alone does not solve caller flag provenance. The
  condition/dispatch group below establishes it for specific call paths; each
  remaining dispatcher must reconstruct its instruction effects up to the call. A fixed EFLAGS value, current host-machine flags or guest ASTAT used
  as a substitute would change ElSemi behavior and is not approved.
- Carry variants are ordinary ADD/SUB or INC/DEC after wrapping an adjusted
  operand, rather than x86 ADC/SBB. Overflow/carry reflect the **final** host
  operation. The TEST before the unary carry variants clears host CF.
- Subtraction stores x86 borrow directly in ASTAT carry. Compare returns the
  first operand, uses the wrapped subtraction sign/zero and clears carry and
  overflow. Half-sum performs two logical right shifts before addition.
- Absolute value preserves an already-set ASTAT `0x10` on nonnegative inputs
  and sets it for negative inputs. `0x80000000` wraps as in the original;
  there is no implicit saturation. Portable calculations use unsigned C to
  avoid signed-overflow and implementation-defined signed shifts.
- Shift direction uses the signed low byte, with counts masked to five bits.
  For effective zero counts, x86 keeps ZF from TEST/NEG of that byte; rotations
  keep that ZF at **all** counts. Thus ASTAT `0x80` is not always `result == 0`.
  These flags are reconstructed deterministically from the original preceding
  operations, without querying host flags. OR merges read their base after
  updating status, including aliases of the status word.
- Set/clear/toggle use a signed index check. Negative indices reach the masked
  shift, but positive indices above 31 return the **index** and retain the
  early-exit status updates. The separate bit-test helper lacks this range
  check and returns its input value while changing only ASTAT `0x1000`.

Small original-execution witnesses, all with input value 0 and ASTAT 0:

| Operation | Entry EFLAGS | Result | Final ASTAT |
| --- | --- | --- | --- |
| INC | `0x02` | `0x00000001` | `0x00000000` |
| INC | `0x03` | `0x00000001` | `0x00000008` |
| DEC | `0x02` | `0xffffffff` | `0x00000004` |
| DEC | `0x03` | `0xffffffff` | `0x0000000c` |
| NOT | `0x02` | `0xffffffff` | `0x00000000` |
| NOT | `0x42` | `0xffffffff` | `0x00000001` |
| NOT | `0x82` | `0xffffffff` | `0x00000004` |

These witnesses are retained in `integer-differential.json` and in API comments.
The tests vary all CF/ZF/SF combinations, both guest carry states, signed and
unsigned boundaries, all low ALU flag combinations, each ASTAT bit and full-word
random data. Shift tests cover all 256 count bytes, larger positive/negative
indices and shared source/count/base/status locations. Both suites compare the
entire data arena and verify preserved registers, balanced return/stack, allowed
writes and unrelated ASTAT-bit preservation. They reject unsupported native
selectors atomically rather than treating unimplemented work as success.

Reproduce each suite after building its isolated library:

```sh
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_integer.c -o port/build-sharc/libsharc_integer_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_integer.c -o port/build-sharc/libsharc_integer_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_integer.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_integer_O0.dylib \
  port/build-sharc/libsharc_integer_O2.dylib \
  --output port/build-sharc/integer-differential.json
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_shift.c -o port/build-sharc/libsharc_shift_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_shift.c -o port/build-sharc/libsharc_shift_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_shift.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_shift_O0.dylib \
  port/build-sharc/libsharc_shift_O2.dylib \
  --output port/build-sharc/shift-differential.json
```

## Condition Tables And Integer Dispatch

`port/sharc/sharc_condition.c` recovers both 32-entry tables read from the
pinned executable at `0x00573490` (instruction) and `0x00573510` (loop), covering
34 distinct original functions. The tables differ only at slots 15 and 31:

| Slot | Instruction Table | Loop Table |
| --- | --- | --- |
| 15 | Loop counter differs from 1 | Loop counter equals 1 |
| 31 | True | False |

Slots 0–13 test the original ASTAT masks/combinations; slots 16–29 invert
them. Slot 14 is false and slot 30 is true. Positive mask conditions retain
the original bit-mask return value, not a normalized boolean. Conditions 9,
10, 25 and 26 set the shared stop flag to 1 when their underlying ASTAT flag
is set, including the inverted conditions; otherwise they preserve its prior
value. This stop side effect does not by itself suppress a true compute path.

Two recovered wrappers bind condition and integer compute helpers:

- `0x004bcb50`: condition, operand snapshots, compute, destination store.
- `0x004bcb10`: condition, move-source and operand snapshots, compute,
  destination store, then saved move-source store. Aliased destinations retain
  this order, including moves to ASTAT and overwriting the compute destination.

The API uses host pointer bindings rather than serializing original 32-bit
pointers. Only the 19 recovered integer selectors are accepted. Invalid
selectors/condition indices fail before side effects; this is a partial-port
boundary, not a replacement for the original bad-opcode handling. A false
condition returns without reading operands or move pointers.

### Helper-Entry Flag Provenance

| Original Call Paths | Last Flag Producer Before Compute | Observed Helper Inputs |
| --- | --- | --- |
| `0x004bcb10`, `0x004bcb50` | `TEST EAX,EAX` at `0x004bcb1a` / `0x004bcb5a`, true condition | CF/ZF/SF/OF clear; PF follows low-byte parity of the raw condition result |
| `0x004bd810`, `0x004bd890`, `0x004bd910`, `0x004bd990` | Condition TEST, compute on the false branch | ZF/PF set; CF/SF/OF clear |
| `0x004bddb0`, `0x004bde20`, `0x004bdea0`, `0x004bdf20` | No flag-writing instruction between handler entry and compute | Inherit handler-entry flags; outer-loop provenance still requires reconstruction |

MOV, PUSH and CALL between these producers and the helper preserve flags.
The portable conditional wrappers derive their snapshot from the raw condition
return. They do not read host compiler flags. TEST's undefined AF is excluded
from the comparison and is not an input consumed by these integer helpers.
Consequently INC/DEC see clear carry in the first two groups, but NOT sees a
set ZF in the second group. The third group cannot use either constant: it
retains the caller's flags. This preserves ElSemi's implementation rather than
substituting fresh flags from the arithmetic result.

At the condition-group boundary, only the first table row was fully ported.
The other eight handlers were audited
by executing their original prefixes and stopping at helper entry. The next
group below completes those eight integer wrappers and recovers outer-loop
flag producers. The execution group below then recovers scheduler and delay-slot
bookkeeping, with decoder/board integration still separate.

### Completion Metric

Current recovery coverage is **133 of 185 inventoried addresses: 71.9%**
(previous groups: 72/172, 41.9%; 80/172, 46.5%). The denominator is the
union (deduplicated by address) of the 22 source functions, 116 address-taken
candidates, 34 condition-table targets, and newly identified execution entry
`0x004bd000`. The newly reviewed direct mode/bank/stack helpers add 13 addresses, making
185 known targets. All 133 verified entries belong to that expanded union.
`port/sharc/recovery_targets.json` records additional-address provenance;
`tools/sharc_progress.py` deduplicates completed receipts and excludes fragments. Prefix/fragment probes
and bounded loop traces do not count as completed handlers.

Report this metric after every group, with its denominator. It measures known
routine/target recovery, not weighted engineering effort or total Model 2B
readiness. Candidates still require boundary review; new tables or targets may
expand the inventory. Full integration, timing and game acceptance remain
separate and are not measurable as a reliable overall percentage yet.

### Differential Evidence

`port/sharc/test/difftest_condition.py` reads the original tables from the
hash-checked executable and compares **38,400 condition cases** and **109,442
complete integer-dispatch cases** with both O0 and O2 libraries. It exercises
all table slots, low flag combinations, isolated ASTAT bits/complements,
full-width random status, loop/stop boundaries, all 19 integer operations,
operand/status aliases and overlapping result/move stores. False-condition
cases use null/unmapped operands to verify that no dereference occurs.
Complete data arenas, stop state, preserved registers, stack and write bounds
are checked. Original helper-entry flags are captured at the actual call target.

An additional **256 prefix-only probes** vary all CF/PF/ZF/SF/OF combinations
on the eight partially examined handlers. They are recorded separately and
are not included in implemented-entry counts. Zero mismatches or skips occurred.
The existing 148,960-case integer suite was rerun after adding the selector
predicate and still passes; repeated cases are not added to cumulative totals.

Cumulative differential evidence is **549,526 inputs across 72 original entry
points**, each compared with O0/O2, excluding prefix-only probes. The ignored
receipt is `port/build-sharc/condition-dispatch-differential.json`, with source,
test, binary and library hashes plus the exact table contents.

```sh
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_condition.c port/sharc/sharc_integer.c \
  -o port/build-sharc/libsharc_condition_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_condition.c port/sharc/sharc_integer.c \
  -o port/build-sharc/libsharc_condition_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_condition.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_condition_O0.dylib \
  port/build-sharc/libsharc_condition_O2.dylib \
  --output port/build-sharc/condition-dispatch-differential.json
```

## Memory/Branch Dispatch And Outer-Loop Flags

`sharc_memory.c` completes the integer subset of eight previously inspected
handlers. Stable host record bindings and bus callbacks retain the original
read/write order. Address modifiers are reloaded after callbacks and destination
stores, rather than cached at handler entry. Outgoing values are snapshotted
before compute, while incoming values and address updates occur afterwards.

| Original Entry | True Conditional Path | Compute/Memory Path |
| --- | --- | --- |
| `0x004bd810` | Immediate jump | False condition: compute, write, post-modify |
| `0x004bd890` | Jump to sum of two register words | False condition: compute, write, post-modify |
| `0x004bd910` | Immediate jump | False condition: compute, read, store, post-modify |
| `0x004bd990` | Read a jump target at the sum of two register words | False condition: compute, read, store, post-modify |
| `0x004bddb0` | Unconditional | Compute, write/post-modify, write/post-modify |
| `0x004bde20` | Unconditional | Compute, write/post-modify, read/store/post-modify/mirror |
| `0x004bdea0` | Unconditional | Compute, read/store/post-modify/mirror, write/post-modify |
| `0x004bdf20` | Unconditional | Compute, two read/store/post-modify transfers with native mirror behavior |

Branches write `target - 1` to PC and `target * 0x6c - 0x6c` as the decoded
record displacement, both wrapping at 32 bits. The outer loop owns the later
advance. The portable API retains a byte displacement rather than forming an
invalid C pointer for zero/wrapping targets. Bus callbacks may mutate bound
register words; this subset requires stable record fields/bindings throughout
the call. Actual board callbacks, floating-point compute and decoder binding
remain outside this integration boundary.

### Preserved Second-Read Mirror Quirk

At `0x004bdf8f`, bit 1 requests a mirror update after the second transfer.
However `0x004bdf95` reloads record field `+0x24`, the **first** data pointer,
and copies its current value to that pointer minus `0x80`. The implementation
preserves this exact behavior, including when callbacks or aliases changed the
first word. It does not substitute the second pointer (`+0x28`). The other
read/write combinations retain their own original mirror choices.

### Outer-Loop Flag Producers

`sharc_flow.c` reconstructs the defined flag bits from the original 32-bit
inputs. It does not yet implement either complete execution loop.

| Site | Original Producer | Consequence For Unconditional Compute |
| --- | --- | --- |
| Bounded loop first entry, `0x004bd058` | `OR EDI,-1` after the initial budget check | EFLAGS `0x86` (SF/PF set); NOT sets ASTAT sign even for input `0xffffffff` whose complement is zero |
| Continuous loop first entry, `0x004be076` | `CMP budget,0` | Flags reflect the budget; normal 100,000 yields `0x06` |
| Subsequent entries, `0x004bd13a` / `0x004be165` | `SUB budget,1` | Defined subtraction flags, including overflow at `0x80000000` |
| Delay slots, `0x004bdfa5` / `0x004bdfce` | `ADD record,0x6c` | Flags reflect the original virtual record address, not native host pointer arithmetic |

The arithmetic flag helpers retain CF/PF/ZF/SF/OF plus fixed bit 1; undefined or
irrelevant AF is not synthesized. Delay-slot virtual address mapping must be
settled when the decoded-program store is integrated, rather than silently
substituting truncated host pointers. Pending-event processing, loop-stack
unwinding and delay-slot lifecycle were the next recovery group (below).

### Verification And Reproduction

`difftest_memory.py` compares **97,280 complete wrapper cases** against the
original at O0/O2. It covers all 32 conditions for the conditional wrappers,
all 19 recovered integer operations, full host-flag combinations on unconditional
paths, eight alias layouts, four mirror-bit combinations, callback mutations,
branch wraparound, full arenas, stop state, record displacement, callback traces,
stack and preserved registers. Unsupported partial-port selectors reject before
side effects. The synthetic bus is deliberately not claimed as board emulation.

`difftest_flow.py` separately verifies **6,402 flag-fragment cases** at six
original sites and **eight bounded loop traces**. The latter execute original
NOT through `0x004bdf20`, record ASTAT, then return from the handler before
memory callbacks and advance to the next outer-loop entry. For example, with
budget 2 and operand 0, the bounded loop produces ASTAT 4 then 0; the continuous
loop with its normal budget produces 0 then 0. This is original execution
evidence for flag provenance, not complete loop/board qualification.

All checks pass with zero mismatches/skips. Cumulative **full-entry** coverage
is **646,806 inputs across 80 addresses**; fragment/trace probes and repeated
runs are excluded. Receipts `memory-differential.json` and
`flow-differential.json` are ignored under `port/build-sharc/` and contain source,
test, original executable and library hashes.

```sh
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_memory.c port/sharc/sharc_condition.c port/sharc/sharc_integer.c \
  port/sharc/sharc_flow.c \
  -o port/build-sharc/libsharc_memory_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_memory.c port/sharc/sharc_condition.c port/sharc/sharc_integer.c \
  port/sharc/sharc_flow.c \
  -o port/build-sharc/libsharc_memory_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_memory.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_memory_O0.dylib port/build-sharc/libsharc_memory_O2.dylib \
  --output port/build-sharc/memory-differential.json
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_flow.c -o port/build-sharc/libsharc_flow_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_flow.c -o port/build-sharc/libsharc_flow_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_flow.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_flow_O0.dylib port/build-sharc/libsharc_flow_O2.dylib \
  --output port/build-sharc/flow-differential.json
```

## Execution Scheduler, Pending Events And Delay Slots

`sharc_execute.c` reconstructs four control-flow entries around the recovered
condition and flag helpers. The execution state retains the original 169-word
machine layout and explicit 32-bit virtual record/binding tokens; it is not a
Save State or finalized decoder interface. No original virtual address is
silently replaced by a truncated native host pointer.

| Original Entry | Recovered Behavior | Differential Cases |
| --- | --- | --- |
| `0x004bcf70` | Pending events, live callback count and event-delay decrement | 80 |
| `0x004bdfa0` | Two delay slots, event processing and wrapping budget/record updates | 160 |
| `0x004bd000` | Bounded scheduler, counted/conditional loop bookkeeping and state handoff | 972 |
| `0x004be000` | Continuous scheduler with 100,000-instruction batches | 973 |

The bounded and continuous schedulers share instruction/loop bookkeeping but
retain their different entry checks and flag producers. Setup refreshes active
program/bus bindings, binds ASTAT to the state word and records the original
16-bit x87 control value `0x003f`, preserving the storage word's upper half.
Floating-point emulation will consume that metadata later: this integer-only
scheduler does not modify the host floating-point environment or claim x87
arithmetic reconstruction. The setup helper itself is not added as a fifth
completed address.

### Preserved Ordering And Edge Behavior

- Event dispatch reloads the pending count after each callback. A callback can
  shorten or extend that same iteration. The count is cleared on completion;
  otherwise the delay is decremented, including `0 -> 0xffffffff` when both
  delay and pending count were initially zero. No saturating counter is added.
- Bounded execution with a nonzero budget dispatches even if stop was already
  set. Continuous execution returns immediately for that initial stop state.
  A zero bounded budget still performs setup and saves the current record.
- After a handler, pending events and loop bookkeeping run before PC/record
  advance. If stop is set, the advance is retained but that iteration does not
  decrement budget. Counter and offset arithmetic wraps at 32 bits.
- Counted-loop stack entries and the active counter are decremented separately.
  Loop completion pops/restores the counter, descriptor and PC-stack state;
  loop repetition reloads the configured program base. It does not assume the
  active base still equals the configured base after callbacks.
- Both delay slots run without stop or exhausted-budget checks between them.
  Each slot processes pending events and charges one budget unit, including
  underflow. The second slot starts from the current record after the first
  slot's events. Final restoration subtracts `0xd8` from the latest record;
  it does not blindly restore the entry pointer. Nested use from a dispatcher
  retains these rules. Delay mode is cleared to zero on return.
- Defined callback-entry flags are explicit. Initial bounded execution retains
  OR flags, continuous execution retains budget-CMP flags, subsequent iterations
  retain budget-SUB flags, events retain TEST/CMP flags and slots retain virtual
  record-ADD flags. No dependency on the native compiler's condition flags is
  introduced, and no new watchdog changes original termination behavior.

### Complete Routine Comparisons

`difftest_execute.py` runs each original routine to its return, rather than
stopping at a prefix. Identical synthetic instruction/event handlers on the
original and native side mutate the exposed state and record callback tokens,
entry flags, budgets, PC, stop, delay mode and event state. The test compares
that complete trace, all 169 state words and runtime fields, balanced stack,
return address, preserved registers and allowed original writes.

**2,185 cases pass with O0 and O2**, zero mismatches/skips. Coverage includes all
32 conditional-loop selectors with raw and handler-modified ASTAT, all three
counted-loop types, restore indices including the original wrapped -1 offset,
zero/wrapping budgets, pre-existing stop, event-count growth/shrinkage, callback
changes to record/PC/configured base/bindings, and nested delay slots. A complete
continuous case executes **100,001 original dispatches**, crossing the actual
100,000-instruction batch boundary and stopping on the first instruction of the
second batch. No patched budget or skipped original instructions substitutes
for that rollover case.

This qualifies scheduler logic around controlled handler boundaries. It does
not qualify real DSP instruction decode, floating point, program upload, bus
callbacks, board timing or Model 2B games. The existing production core and
Model 2B/2C gates remain unchanged.

Cumulative full-entry evidence is **648,991 inputs across 84 addresses**.
Fragment probes, previous bounded traces and repeated suite runs remain excluded.
The ignored receipt is `port/build-sharc/execute-differential.json`, with exact
source, test, original executable and O0/O2 library hashes.

```sh
clang -std=c99 -Wall -Wextra -Werror -pedantic -O0 -dynamiclib \
  port/sharc/sharc_execute.c port/sharc/sharc_flow.c \
  port/sharc/sharc_condition.c port/sharc/sharc_integer.c \
  -o port/build-sharc/libsharc_execute_O0.dylib
clang -std=c99 -Wall -Wextra -Werror -pedantic -O2 -dynamiclib \
  port/sharc/sharc_execute.c port/sharc/sharc_flow.c \
  port/sharc/sharc_condition.c port/sharc/sharc_integer.c \
  -o port/build-sharc/libsharc_execute_O2.dylib
port/build-sharc/venv/bin/python port/sharc/test/difftest_execute.py \
  port/build-sharc/original/EMULATOR.EXE \
  port/build-sharc/libsharc_execute_O0.dylib port/build-sharc/libsharc_execute_O2.dylib \
  --output port/build-sharc/execute-differential.json
```

## Consecutive Transfer, Control And Mode Groups

The user authorized consecutive groups up to the account-wide 50% usage ceiling,
with no commit/push and a review report at the stop point. Current evidence:

| Group | Additional Entries | New Full-Entry Cases | Result |
| --- | --- | --- | --- |
| Conditional Single-Transfer Compute | 9 | 175,104 | Passed O0/O2 |
| Branch, Call, Return And Loop Setup | 15 | 30,720 | Passed O0/O2 |
| Simple Transfers And Register Tests | 10 | 2,560 | Passed O0/O2 |
| Mode, Banks And Stack Helpers | 15 | 15,360 | Passed O0/O2 |

`sharc_memory.c` now covers 17 wrappers. The additional entries are
`0x004bdad0`, `0x004bdb10`, `0x004bdb60`, `0x004bdbb0`, `0x004bdc00`,
`0x004bdc60`, `0x004bdcb0`, `0x004bdd00`, `0x004bdd50`. They retain condition
TEST flags, outgoing-value capture before compute, address calculation after
compute, and immediate/register pre-address versus post-update ordering.
The memory suite now has 272,384 cases; the earlier 97,280 are not counted twice.

`sharc_control.c` covers `0x004bcad0`, `0x004bd700`, `0x004bd750`, `0x004bd7b0`,
`0x004bda10`, `0x004bda60`, and the nine targets from `0x004be2a0` through
`0x004be7c0`. It preserves alternate compute on false conditions, combined
compute/branch on true conditions, call-bit precedence over loop-exit, return
stack ordering and the distinction between calls pushed before versus after
delay slots. A resolver reloads the current virtual record after slots, matching
the original global-pointer reload. Tests redirect that record and mutate PC/
stack data during slots; final branch fields are read from the resulting record.
Each target passes 2,048 cases with all conditions and low branch-flag combinations,
operand aliases and recovered integer compute selectors.

`sharc_transfer.c` covers register equality/masked tests, XOR/assignment, address
addition and immediate/indirect bus transfers at `0x004bca50`, `0x004bca80`,
`0x004bcab0`, `0x004bcac0`, `0x004bd540`, `0x004bd650`, `0x004bd680`,
`0x004bd6a0`, `0x004bd6c0`, `0x004bd6e0`. The existing memory fixture is reused
with `--transfers`; no second synthetic bus implementation was introduced.

`sharc_mode.c` reconstructs the mode clear/set entries `0x004bd550`/`0x004bd5d0`,
four bank callbacks (`0x004bce10`, `0x004bce60`, `0x004bceb0`, `0x004bcf00`),
and nine direct stack/event/ASTAT/read helpers listed in `recovery_targets.json`.
A change in mode bit 7 queues the high-bank swap first; bit 10 queues the low-bank
swap next. Unchanged bits enqueue nothing. Each affected 8-word bank is swapped
with its preserved counterpart, for both set and clear transitions. The 15,360
cases include 512 compound sequences that run original event scheduling and
actual original bank callbacks, compared with the portable equivalents. Queue
capacity and valid stack storage remain original caller invariants; no new
clamping or fallback is substituted. The original ABI requires DF clear.

All new suites compare complete arenas/state, meaningful results, callback
traces, stop/budget/record effects, stack, preserved registers and write bounds.
Zero mismatches/skips occurred. Cumulative evidence is **872,735 cases across
133 entries**, excluding fragment probes and reruns. Inventory size increased
by 13 newly reviewed direct entries: **133/185 = 71.9%**. These counts describe
address recovery, not weighted effort or board/game readiness.

Receipts: `memory-differential.json`, `control-differential.json`,
`transfer-differential.json`, `mode-differential.json` under ignored
`port/build-sharc/`. All original images and local evidence stay outside Git.
The relevant `difftest_*.py` scripts accept the pinned image, O0/O2 libraries and
`--output`; transfer mode reuses `difftest_memory.py --transfers`. Control and
mode libraries link their module with `sharc_execute.c`, `sharc_condition.c`,
`sharc_integer.c`, `sharc_flow.c`; transfer links `sharc_transfer.c` with the
memory/condition/integer/flow modules. Use the same strict C99 warning flags as
in the preceding recipes. `python3 tools/sharc_progress.py` regenerates totals.

## Auxiliary Integer And Initial Floating-Point Groups

`sharc_aux.c` adds six original entries: literal zero/pass-through stubs,
low-32-bit multiplication (`0x004bc600`), signed-magnitude clipping
(`0x004bc240`) and simultaneous sum/difference (`0x004bc3a0`). The original
multiply changes only ASTAT bit 6. Accumulator register transfers remain
transfers; no wider multiply/accumulate semantics are invented. Clipping keeps
the original wrapping `ABS(INT_MIN)` and signed comparison. Sum/difference
snapshots inputs, writes sum before difference and then updates ASTAT, including
output/status aliases. **65,804 cases** pass original x86 comparisons at O0/O2.
Receipts: `aux-differential.json` (39,200), `pair-differential.json` (26,604).

`sharc_fp.c` adds four balanced x87 helpers: min/max selection (`0x004bc130`,
`0x004bc170`), exponent extraction (`0x004bc1b0`) and truncation (`0x004bc210`).
They model architectural x87 control/status separately from SHARC ASTAT, using
integer bit operations without dependence on the host floating-point mode.
Equal/unordered min/max selects RHS, preserving the selected zero sign and
quieting signaling NaNs. Exponent extraction does not normalize denormals.
Truncation converts to signed 64-bit and returns its low 32 bits, rather than
treating every value outside INT32 range as invalid. Exceptions are sticky,
C1 is cleared and the caller's rounding control is restored.

**Oracle limitation discovered:** Unicorn 2.1.4 does not reproduce x87 signaling-
NaN quieting, exception accumulation or C1 clearing in these sequences. Its
control-register API also retains reserved bit 6 as supplied, unlike FLDCW/
FNSTCW. These are test-engine differences, not behavior copied into the port.
`test/x87_simple_oracle.c` independently transcribes the relevant instruction
sequences and runs as x86_64 under the already-installed Rosetta. No dependency
was installed. The 46,224-case FP suite checks O0/O2 against that sequence and
executes every original helper to return in Unicorn. Original comparison
differences are narrowly asserted and counted: 480 SNaN results, 8,129 exception
flag cases and 9,272 C1 cases (overlapping counts). All other results, SHARC state,
condition codes, control state, preserved registers and write bounds agree.
This dual-emulation evidence is **not physical-x86 qualification**. No unmasked
exception handling or non-empty x87-stack execution is claimed.

Receipt: `fp-differential.json`, including both oracle and O0/O2 hashes. Build
the FP module with the strict C99 flags above; build the sequence oracle using
`clang -arch x86_64 -O2 port/sharc/test/x87_simple_oracle.c`. The FP test takes
the pinned executable, sequence-oracle executable, O0/O2 libraries and `--output`.
Auxiliary mode reuses `difftest_integer.py --aux`; the pair test is separate.

The next five FP helpers add negation, absolute value, register pass, integer
rounding and floating clipping. The unary flag helpers read sticky x87 IE/OE
**before** FNCLEX: even a plain pass can import an earlier exception into ASTAT.
Their FTST flags precede the final store; unordered sets both AN and AZ.
Clipping retains its ordered/unordered branch selection and selected zero sign.
The expanded nine-entry suite has **104,004 cases**. Bounded oracle discrepancies
now total 1,440 SNaN results, 9,163 exception cases, 20,768 C1 cases and 581 ASTAT
invalid-flag cases caused by missing SNaN handling (overlapping categories).

## Compute And Program Decoders

`sharc_decode.c` recovers the complete `0x004be800` compute decoder. It retains
compound-operation precedence, accumulator-bank moves, immediate forms, nested
record pointers and the native diagnostic target for unknown selectors. The
**77,824-case** suite covers every 11-bit compute selector, all immediate forms,
register combinations and full-width extension inputs, selecting 76 handlers.
Handler/address fields are explicit virtual tokens, never truncated host pointers.

`sharc_program.c` adapts the existing Ghidra body of `0x004bf610`, resolving its
missing calling-convention arguments against the original instructions. It
reuses the recovered register and immediate helpers and compute decoder.
The original frees the previous allocation before replacing it, truncates byte
length to complete six-byte instructions, preserves untouched allocation words,
clears only the low 16 flag bits, and finishes with a one-past record binding.
The fixed-state DAG addresses remain distinct from the selected register-state
base. One transfer form passes the full byte register code while neighboring
forms mask it to a nibble; special/scratch-register behavior is retained.
Unknown instruction classes leave the original record handler untouched.

**207 complete original program calls**, covering **262,180 decoded synthetic
instructions**, pass O0/O2 comparisons. Coverage includes all 65,536 upper opcode
words, a complete 65,536-instruction input, fresh/replacement/empty allocations,
trailing bytes, loop-distance encodings, write bounds and preserved registers.
CRT allocation/free are controlled boundary callbacks, not reconstructed CRT
implementations. Successful allocation and sufficient storage remain the valid
original caller contract. The 512-case condition binder checks `0x004bc660` and
its five-bit masking. The register-selector regression still passes 1,024 cases.

Receipts: `decode-differential.json`, `program-differential.json`. Build the
program suite from `sharc_program.c`, `sharc_decode.c`, `sharc_registers.c` and
`sharc_bits.c`; its test accepts the pinned image, O0/O2 libraries and `--output`.
The two decoder suites add 78,543 cases; decoded instruction totals are not
miscounted as independent program calls. Inventory adds the condition binder
and the discovered `0x004bca40` NOP handler, which is not yet counted recovered.

## Floating Comparison, Conversion And Arithmetic

Three further simple entries cover floating comparison, float-to-INT32 and
INT32-to-float. The simple FP suite now covers **12 entries / 138,672 cases**.
Conversion flags are intentionally sampled before the final FISTP/FSTPS;
exceptions raised by that store remain available to the next helper. The
INT32 conversion honors RC; the separate `0x004bc210` truncation still converts
to INT64 and returns its low word. These are distinct original contracts.

`sharc_fp_arithmetic.c` adds sum, difference, absolute sum/difference, average,
multiply, reciprocal and reciprocal square root. It uses integer significand
operations, sticky discarded bits and explicit rounding; no host float casts
or imported SHARC implementation are used. The caller contract is the original
scheduler's **24-bit x87 precision**, with all four RC modes verified. The
extended exponent is retained until the final binary32 store: a temporary
overflow of binary32 does not prematurely become infinity, and a tiny nonzero
temporary does not become zero before FTST. ASTAT remains based on the original
pre-store order. Reciprocal square root retains both FSQRT and FDIV rounding.
Other x87 PC settings are rejected without mutation, not silently approximated.

The arithmetic suite passes **93,600 cases / eight entries** at O0/O2, including
targeted half-ULP and normal/subnormal boundaries. It uses the same original/
x87-sequence evidence model. In addition to missing exception/C1 handling,
Unicorn's missing FLD quieting changes NaN operand selection in 72 cases; both
results are constrained to the input NaNs with only quiet-bit/FABS changes.
The portable result must still agree exactly with the independent x87 sequence.
The receipt records all bounded differences. Physical x86 validation remains
open. Build this module independently and run `difftest_fp.py --arithmetic`;
the shared sequence-oracle executable covers both FP suites.

Current coverage is **1,249,354 cases, 162/187 entries (86.6%)**. The integer
ALU regression still passes 148,960 cases after its harness extension; reruns
are not added to totals. Remaining FP combinations/scaling, initialization/state
helpers, board integration and actual Model 2B games remain unqualified.

No SHARC code is linked into the core yet. Model 2B/2C loading gates, options,
Save States and installed RetroArch binaries are unchanged. Model 2C
reconstruction is a separate later activity, not a result of this first SHARC
investigation.

## Scaling And Native State Callbacks

Four FSCALE entries (`0x00461d60`, `0x00462000`, `0x00462140`,
`0x004622a0`) pass **65,680 cases** at O0/O2, including signed INT32
exponents, all RC modes and extended-exponent boundaries. Floating and integer
loads, optional FRNDINT, pre-store ASTAT sampling and final exponent-stack pop
retain their original order. The final pop clears C1 after the result store.
`sharc_fp_scale.c` retains x87 extended subnormals until the final conversion.
The original-under-Unicorn comparison exposes two further bounded oracle
limitations: missing FSCALE overflow flags and 270 zero-versus-tiny comparisons
at the extended subnormal boundary. The test permits only the corresponding
ASTAT/condition bits in that domain; portable results and state must agree
exactly with the independent x87 sequence. Physical x86 qualification remains
open. Receipt: `fp-scale-differential.json`; use `difftest_fp.py --scaling`.

`0x00462480` is a bitwise sign copy, with no FP or ASTAT effects. It adds
7,840 cases to the auxiliary suite (now six entries / 47,040 cases). It does
not quiet signaling NaNs.

`sharc_lifecycle.c` recovers native save/restore callbacks, fixed-state getter,
ASTAT/x87 setup, NOP and bad-compute diagnostic. **6,144 cases** compare full
original bodies with explicit memcpy/logging CRT boundaries. Restore copies the
requested bytes first, then rebinds the record token at `0x2a8` from the copied
PC and the base at `0x2ac`; the usual `0x2a4` payload leaves that base intact.
Wrapping PC arithmetic and short/extended copies are covered. The getter clears
the allocation token without freeing it. Setup retains the high memory/EAX
words, while the architectural x87 control reports reserved bit 6. Diagnostic
output retains the native format and returns the snapshotted LHS. These native
callbacks are not the Libretro Save State API. No frontend persistence contract
was changed. Receipt: `lifecycle-differential.json`.

The three newly inventoried callbacks bring the denominator to 190. Current
coverage is **1,329,018 cases, 173/190 entries (91.1%)**. Remaining work includes
FP compound operations, full initialization, renderer/bus dependencies and
board integration. No SHARC recovery code is linked into production.

## Compound Floating-Point Operations

All ten identified compound FP entries are recovered. Seven two-result
operations pass **307,160 cases**: simultaneous sum/difference and product
combined with sum, difference, average, absolute value, minimum or maximum.
The product/sum/difference entry adds **52,656 cases**. Two product/conversion
entries add **129,520 cases**, including extended-exponent boundaries. Each
suite checks complete original bodies, independent x87 instruction sequences
under Rosetta, O0/O2 native results, write order and output/ASTAT aliases.
Unicorn NaN/exception/C1 omissions remain narrowly bounded and recorded.

Unlike scalar helpers, most compound entries keep the extended temporaries
alive across FSTS and retain accumulated x87 exceptions. The numeric helper
now records discarded significand bits and denormal loads for that purpose;
the scalar regression still passes. Conversion compounds `0x004bd320` and
`0x004bd3b0` instead spill the product to binary32 before invoking the conversion
helper. The subsequent comparison interprets the returned bits as an unsigned
integer, even for the floating result of `0x004bd3b0`. That original quirk is
documented in code and deliberately retained, including the high-bit FADD
rounding. No replacement with idealized SHARC arithmetic was made.

Use `difftest_fp_compound.py` with the compound sequence oracle; `--triple`
uses `x87_triple_oracle.c`, while `--scaled` selects the conversion compounds.
The arithmetic library now links `sharc_fp_scale.c` as well. Receipts are
`fp-compound-differential.json`, `fp-triple-differential.json` and
`fp-scaled-compound-differential.json`. Current total: **1,818,354 cases,
183/190 known entries (96.3%)**. Production integration remains open.

## Native Bus And Initialization Closure

The two board bus entries and three renderer skip callbacks pass **138,679
cases**. Coverage includes every upper 16-bit address selector, 16/32-bit RAM
views, shared memory, ROM-range edges, every FIFO index and full/empty/wrapping
counters. FIFO access selects the fixed SHARC state and retains the exact
ASTAT/stop behavior; writes to a full FIFO are not silently saturated. The three
renderer callbacks only advance the original stream token by four bytes.
All memory is synthetic. Receipt: `board-differential.json`.

Full reset `0x004c0230` passes **256 cases**, including **43 native exception
paths**. It executes the real recovered program decoder, handles optional
serializer registration and preserves create-before-limit-check ordering. The
native list-node/exception/CRT boundaries are explicit callbacks, not hidden
success stubs. Fatal handling is non-returning; the test fixture catches it
with setjmp/longjmp entirely in C. Source capture, selected-state changes during
registration, temporary PC, final PC and saved-record rebinding are checked.
Receipt: `reset-differential.json`.

Board initialization `0x004c6510` passes **576 cases** with original C-locale
CRT comparisons (mixed case, exact names, prefixes and near misses). The reset
call is an explicit separately qualified boundary. Native per-title constants,
renderer substitutions and mode flags are preserved. The ignored comparison
with `zerogun` still leads to an unconditional enabled flag, as in the original.
Receipt: `board-init-differential.json`.

The initial known routine inventory is now **190/190 (100%)**, with
**1,957,865 helper cases**. This is not complete Model 2B support: the recovered
pieces still need an integrated execution path, machine binding and real-game
qualification. Additional dependencies can expand the inventory.

## Decode-To-Compute Integration

`sharc_compute.c` binds all **76 compute targets** to original 32-bit record
tokens through an explicit word resolver. It uses the recovered integer, shift,
field, auxiliary and FP helpers. Both native compute/compute-plus-move wrappers
now accept every recovered target. TEST-derived entry flags, pre-compute move
snapshot, output ordering and post-helper record reloading are preserved.

`difftest_compute.py` passes **24,576 integration cases** across all 2,048
selectors, three extension forms and both wrappers, with always-true and varied
conditions. It calls the original helper bodies and checks full arena/stop/record
state; 7,992 diagnostic callbacks redirect the active record. Finite synthetic
operands isolate wiring; detailed FP NaN/exception qualification remains in the
dual-oracle unit suites. Known exception/C1 differences are recorded separately.
This is additional integration evidence, not 76 newly recovered routines and
not a complete scheduler/board integration. Receipt: `compute-integration.json`.

## Execution, Memory And Control Composition

The memory and control wrappers now accept explicit compute-operation hooks.
The established integer-only entry points remain wrappers selecting the original
backend. The complete backend reaches the recovered scalar/compound operations
without copying their implementations. Native flag producers and delayed
record re-resolution remain in their existing layers. Integration passes
**59,520 memory cases** and **21,360 control cases**; the existing integer-only
regressions pass another 272,384 and 30,720 cases without changing their counts.
Receipts: `memory-integration.json`, `control-integration.json`.

`difftest_run_compute.py` composes the bounded scheduler and real decoded
compute handlers. **768 programs / 9,604 instructions** pass for straight-line
and counted-loop paths, varied conditions/budgets and preexisting stop. No
instruction-body stub replaces computation on the original side. Detailed FP
exceptions are qualified by the helper dual-oracle suites; finite operands here
isolate composition. Receipt: `run-compute-integration.json`.

`difftest_memory_board.py` composes all 17 memory wrappers with the real board
read/write bodies: **3,672 cases** cover RAM views, ROM/unknown regions, FIFOs,
ASTAT destination aliases and counter edges. Full RAM is compared after every
address batch. Portable callbacks propagate native stop state around bus calls;
the selected SHARC state is the fixed board state throughout this suite.
No synthetic callback supplies read values in place of the original bus.
Receipt: `memory-board-integration.json`.

## Raw Record Bindings And Consumption Stop

`sharc_bind.c` translates the original 27-word records into the existing memory,
transfer and control representations. Operation entry addresses are retained for
the complete compute backend; condition addresses map through the original
table. The resolver performs only address lookup: unused native fields may hold
allocator data and resolve to NULL without speculative guest loads. Consumed
bindings must be valid, as required by the original handlers. Memory bindings
remain stable during each wrapper; control records are rebound at every resolver
call, including after delay slots. This layer does not replace the scheduler.

The 59,520 memory and 21,360 control integration cases pass again with
`--backend --bindings`; they are not counted twice. All ten transfer handlers
pass **2,560 additional integration cases** with `--transfers --bindings`.
Receipt: `transfer-integration.json`. All recovery C translation units build
together with strict C99 warnings as errors at O0 and O2.

Total integration evidence is **112,456 cases**, separate from the **1,957,865
helper cases / 190 known addresses**. The remaining composition includes a full
instruction dispatcher, queued events, board lifecycle and production machine
binding. No production linkage, ROM execution or Model 2B compatibility claim
follows. Physical x86 qualification also remains open.

Work stopped on 2026-11-03 when account usage reported the authorized **50%**
ceiling. Reset reported: 2026-11-08 13:59 CET. No further implementation group,
commit, push, production build or local core deployment was performed at this
stop point. Further work awaits authorization and a renewed consumption limit.

## Complete Instruction Dispatch And Mixed Execution

Work resumed with an additional five percentage points authorized by the user
(55% account-wide ceiling). `sharc_runtime.c` composes all **47 instruction
forms**, four queued bank callbacks, the complete compute backend and the
existing bounded/continuous schedulers. Unsupported entries report failure;
scheduler failure callbacks must not return. No unknown instruction becomes NOP.

The delayed control resolver retains the original handler's layout and already
evaluated condition when a nested slot redirects the active record. Native code
does not dispatch or validate the replacement record's entry/condition words.
This detail is documented in code and exercised with redirected NOP records
whose unused condition word is deliberately invalid.

`difftest_runtime.py` passes **12,032 cases** with real original instruction,
compute, board-bus, delay-slot and bank-event bodies. `--scheduled` adds **512
mixed programs / 8,252 instructions** through bounded/continuous execution:
counted loops, delayed calls/returns, queued swaps and FIFO-empty stopping.
Architectural x87 reserved control bit 6 uses the previously qualified
normalization; no new arithmetic discrepancy was suppressed. Receipts:
`runtime-integration.json`, `scheduled-runtime-integration.json`.
Integration now totals **125,000 cases**; helper inventory remains 190/190.

## Native Host Driver And Composed Device

Inspection of the original Model 2B driver table at `0x00574c78` adds **17
addresses** outside the first CPU-helper inventory. Sixteen host/control/no-op
and renderer-forwarding entries pass **24,320 cases**. Upload completion
`0x004c6470` passes **256 cases** through the real decoder. Recovery coverage is
now **207/207 known entries**, with **1,982,441 helper cases**. The shared renderer
body is an explicit callback boundary, already ported in `port/m2/m2geo.c`;
forwarding evidence is not new renderer qualification.

The recovered host driver preserves its original quirks: 32-bit upload stores
only the low 16 bits and advances two bytes; 16-bit upload performs its own store
then falls through, potentially storing the word twice. Command writes retain
priority over upload in the 32-bit entry. The 16-bit control-write upload branch
is unreachable because the original masks the address to 12 bits before comparing
against `0x804000`. FIFO counts wrap and read results are captured before resume.
Access results are normalized to the i960 bus width; unused upper x86 return
bits are not a device register. Receipts: `host-differential.json`,
`upload-differential.json`.

`sharc_device.c` composes native power-on/reset, program decode, runtime, host
ports and the board bus while leaving buffers, allocation and renderer ownership
with the enclosing machine. Program RAM, data-upload storage and copro RAM remain
distinct original bindings. Reset's ASTAT is fed back into board initialization
before its empty/full flags are applied. `difftest_device.py` compares **44
scenarios / 1,892 operations** from power-on through synthetic 48-bit uploads,
host commands and FIFO execution/resume against the original EXE. Only CRT
allocation/memset and the shared renderer are boundary fixtures. Receipt:
`device-integration.json`. Total integration evidence: **126,892 cases**.

The i960 machine and production catalog are not connected by these device tests.

## Opt-In i960 Machine Binding

`port/m2/m2sharc.c` binds the composed device to the existing board. The original
driver entries own command/control accesses and program/data uploads; the i960
page map remains in `m2board.c`. Original program, copro RAM, shared buffer RAM
and data-upload buffers remain distinct. Native FIFO state is mirrored into the
board's existing status registers after each access. SHARC writes mark shared
buffer RAM dirty for the existing renderer hand-over. No replacement CPU from
another emulator is used.

Build in a separate directory; do not reuse ordinary objects with this switch:

```sh
make -C port SHARC=1 BUILD=build-sharc-machine -j4
make -C port SHARC=1 BUILD=build-sharc-machine check-sharc-machine
```

The switch admits Model 2B only in this research build. Model 2C remains rejected;
the root Libretro build and installed core are unchanged. The synthetic machine
check traverses the real i960 handlers, including double 16-bit upload stores,
decoded execution, FIFO responses/status, packed shared writes, dirty tracking,
data upload, reset and teardown. SHARC Save States currently fail before any
archive mutation; complete payload ownership, pointer rebinding and validation
are required before enabling that contract. Existing default core compilation
passes. These machine checks are not counted as new original-address cases.

Fighting Vipers was read directly from the existing archive with no ROM copies.
Runs used new ignored directories under `port/build-sharc-machine`:

- `fvipers-120`: bounded upload/CPU execution, no invalid i960 instructions.
- `fvipers-900`: tile capture shows SEGA / Insert Coin(s); 3D has not begun yet.
- `fvipers-2400`: geometry and SCSP enabled, 1,083 polygons at the final frame,
  1,824,827 stereo PCM frames at 44.1 kHz, 3,413,208 nonzero scalar samples.
  PC `0x20133` and FIFO-empty stop are observed in the SHARC diagnostic.
- `fvipers-pipe-2400`: all accumulated geometry hashes, final tile capture and
  the entire PCM stream match the direct run byte for byte.
- `fvipers-gl-display-2400`: existing SDL/OpenGL renderer captures textured 3D
  attract with a character, environment and HUD; exits normally at frame 2,400.
  Configuration and NVRAM are isolated; SDL uses dummy audio. The first
  sandbox-only attempt (`fvipers-gl-2400`) failed before initialization because
  no display was accessible; the display-authorized run is the rendering proof.

PCM SHA-256 for the matching headless paths:
`70be33eceea1f75ffa51bfc1ea8a206ea70558f5b47f6bdcdfea46ba55936a5e`.
The runner now reports SHARC state separately: the old TGP PC is unused for 2B.
This evidence does not establish sustained gameplay, physical controls, audible
speaker output, matching original rendering, Model 2C or Libretro support.
Recovered per-title renderer settings and the existing geometrizer's CRTC-based
placement still require comparison; no speculative renderer correction was made.

### Machine Safety And Scripted Input

The synthetic machine check passes again with AddressSanitizer and UBSan.
Fighting Vipers completes 2,400 CPU/geometry frames with both checks enabled and
no diagnostics (`fvipers-sanitized-cpu-2400`). With audio enabled, the first
strict run stops at an existing Musashi signed shift (`m68k/m68kops.c:8125`).
A separate run keeps AddressSanitizer fatal and lets UBSan report all sites:
seven signed-shift diagnostics occur in the unchanged Musashi/SCSP files,
no AddressSanitizer error occurs, and all geometry hashes match the ordinary
build. This is not a clean whole-audio UBSan result. No suppression or audio
source change hides these findings; see `fvipers-sanitized-audio-2400/result.json`.

`fvipers-gl-input-2400` adds scripted Coin, Start, selection, movement and attack
inputs through the existing standalone debug runner. Its final GL capture shows
Stage 1, Grace against Bahn, with the fight timer and health bars. This establishes
a short scripted gameplay path, not physical-controller qualification or sustained
play. Configuration/NVRAM remain private; audio is dummy in the GL run.

`vf2-regression` compares the same 900-frame Model 2A path in a default build and
the SHARC-enabled build. Entire logs, per-frame main-RAM hashes, accumulated
geometry hashes and PCM are identical. PCM SHA-256:
`74ddf899cede94332a9fec2c1c36320dd4a65e2987d4b01cb2a909a214b6b851`.

### Cross-Architecture Rendering Boundary

An x86-64 build of this recovered C code runs through Rosetta 2; it is not the
Windows emulator. At 2,400 Fighting Vipers frames its final tile capture and PCM
match ARM64 exactly, while accumulated geometry hashes differ. Read-only
`M2_SHARCHASH` diagnostics then compare 1,200 frames: execution state, FP status,
event queue, FIFOs and the native program/copro/shared/data buffers match on every
frame, as does main RAM. The fingerprint excludes unused predecode allocator
words, host pointers and ROM contents; it does not claim every process byte is
identical. Evidence: `fvipers-x86_64-2400`, `fvipers-architecture-hashes`.

The ARM64 compiler emits FMA instructions in the existing `m2geo.c`. Relinking
the same ARM64 binary with **only that object** compiled with
`-ffp-contract=off` makes all four accumulated geometry hashes match x86-64 for
the 1,200-frame diagnostic, with unchanged SHARC/main-RAM hashes. Evidence:
`fvipers-no-contract-1200`. This localizes the observed discrepancy to renderer
arithmetic, not the recovered CPU. It does not identify which renderer matches
the original Windows implementation.

User decision, 2026-11-03: retain the current upstream renderer/compiler behavior;
track original-renderer comparison separately. No ordinary build flags or
geometrizer implementation were changed by this diagnostic.

### Shared Upload Controller

`sharc_upload.c` adds original entry `0x004c79c0`, used by the i960 mapping.
**32,768 cases** pass at O0/O2 against the original binary. Tests include exact
whole-word XOR transitions, same values, unrelated-bit changes, random addresses,
counter values and callbacks that mutate all latches. Completion reads the old
control latch; the incoming value is committed after it returns. Both native
driver completion slots are retained; Model 2B's data callback is the recovered
RET-only `0x004c5ea0`. Synthetic machine upload/execution still passes with this
controller integrated. Receipt: `upload-control-differential.json`.
Current helper coverage: **208/208 entries, 2,015,209 cases**. Integration remains
**126,892 cases**, without counting reused tests twice.

## Opt-In Libretro Binding

The root Makefile accepts the same research switch in a separate output tree:

```sh
make SHARC=1 BUILD=port/build-sharc-libretro -j4
```

This reuses the existing adapter, MAME catalog overlay, SM2-facing controls,
NVRAM, sound, graphics and lifecycle. It does not install or publish the result.
`retro_serialize_size()` returns zero for loaded SHARC content; save/load calls
return false before touching the machine or caller buffer. The ordinary 12 MiB
contract remains available for Model 2/2A, including in this research build.
The lower-level machine archive also rejects SHARC before mutation.

`fvipers-libretro-2400` uses the existing ABI/GL harness, not RetroArch: 2,400
frames at 60 Hz deliver 1,764,000 PCM frames; the captured scene is Stage 1 Grace
against Bahn with scripted Libretro controller input. Option updates, aspect /
widescreen separation, Pipeline, bounded frame skipping, resolution/context
recreation, native reset, Save RAM import and unload/reload pass. The harness
also verifies zero Save State capacity and rejected save/load calls with an
unchanged caller buffer. It does not add keyboard polling to the adapter.

`vf2-libretro-states` verifies that the research gate does not disable existing
Model 2A Save States: cold save/load, four exact 12-frame RAM/device/PCM/image
continuations, corruption/truncation/identity rejection, reverse-order loads,
context recreation and current NVRAM authority pass using the existing test.
`make SHARC=1 BUILD=port/build-sharc-libretro check-eeprom` also passes.

`fvipers-retroarch-1800` uses the existing isolated RetroArch runner with the
research binary directly. The real frontend exits normally after 1,800 frames
and captures textured 3D attract. Audio was muted; this is no listening claim.
The runner owns its process, config, options, Save RAM, states and screenshot
directories. It does not replace the installed core or normal frontend settings.
Default Libretro compilation still passes. SHARC persistence, sustained gameplay,
other titles/platforms and production enablement remain open in M27.

## Original Save State Path Review — 2026-11-03

The Windows 1.1a emulator already supports Save States. Its bundled README
records their introduction and later texture-restoration fixes. The pristine
Model2EmuEx SDL reconstruction does not expose the complete original save/load
path. Do not confuse that missing reconstruction/integration with an absence
of original functionality.

The current source export and pinned PE32 disassembly establish this path:

- `004f7540` writes the registered blocks to `STATES/<game><slot>.sta`.
- `004f7400` reads registered blocks, invoking each custom restore callback.
- `004c0230` registers the `SHARC` block: 0x2a4 bytes, save callback
  `004bc0d0`, restore callback `004bc0f0`. Both callbacks have already passed
  the existing original-binary lifecycle differential suite.
- `004bc0d0` copies the supplied CPU block. `004bc0f0` copies it back and sets
  the saved decoded-record pointer to `PC * 108 + destination[0x2ac]`.
  The destination's pre-existing program base is retained for the normal
  0x2a4-byte restore; this callback does not reconstruct the decoded program.
- The two native input paths call the machine's vtable slot `+0x30` after
  `004f7400`. RTTI identifies Model2's vtable at `0051bbcc`; that slot is
  `004caf00`. It marks graphics dirty and tails into `004b7c60` for texture
  resource invalidation, not a SHARC program decode.
- In the board constructor `004cd450`, the SHARC program/data upload buffers
  at machine offsets `0x203878`/`0x20387c` are allocated without the named
  archive registrations used by the adjacent shared/coproc RAM allocations.
  The recovered SHARC registration does not contain scheduler globals or the
  decoded allocation either.

Therefore the original SHARC restore depends on the already-loaded session's
program/cache. A self-contained Libretro snapshot that also works before the
game has uploaded that program must preserve additional context. This is a
snapshot-contract extension, not a reason to replace the recovered CPU or
decoder with SM2. The original callbacks remain the starting point. The choice
between retaining the original session dependency and extending the snapshot
has been raised before implementation, as required by the workspace policy.

That review itself was source/disassembly evidence, not a new runtime round-trip
result. The following integration records the subsequent user decision and work.

## Complete SHARC Snapshots Using The Model 2A Contract

The user first selected the original session dependency, then explicitly
directed the work to follow the existing Model 2A port conventions. That latest
instruction governs this implementation: preserve the recovered emulator and
wrap its CPU callbacks with a complete frontend snapshot.

`m2sharc_state_archive` reuses `004bc0d0`/`004bc0f0`, including native PC rebinding.
It additionally preserves the execution globals, queued bank events, board
configuration and FP state. Common board serialization already owns RAM,
upload controls and FIFOs. The decoded allocation is saved with the upload
bytes that produced it; guest program-RAM writes do not update that snapshot.
The native decoder validates its immutable record fields against that upload.
Unused allocator bits and mutable scratch remain as recorded, without changing
decoder allocation or normal execution behavior. Host addresses and callbacks
are rebound in the current process, including shared-memory dirty tracking.

The research payload has a `SHR1` subheader, ABI feature bit `0x20000000`, and
16 MiB frontend capacity to accommodate decoded records. Model 2/2A retain
12 MiB and their existing payload. The existing header/full-buffer integrity,
preflight, rollback, graphics/audio recovery and current-option authority apply.
Cache storage grows before replacement and never shrinks on load, so rollback
can reuse storage even if a later subsystem rejects the payload.

Evidence so far:

- The ROM-free mapped-machine test covers warm cache versus changed program
  RAM, replacement by reset, complete restore, exact continuation, rejected
  structural corruption and every truncation boundary of the SHARC subarchive.
- `fvipers-sharc-states`: cold save/load and four exact 12-frame machine,
  PCM and image continuations after 2,400 scripted frames; reverse loads,
  GL recreation, malformed data rejection and rollback pass. PCM CRC is
  `bb8ea02a` for 8,820 stereo frames.
- `fvipers-sharc-fresh`: a new process loads before its first game frame.
  Saved and continued states plus the continued image match the first process
  exactly. Continued-state SHA-256:
  `485d926dd40ef4de94c0b47242de87329100c1406dcb618677c46a6378b7296a`.
- `vf2-sharc-regression`: existing Model 2A suite passes, including current
  NVRAM authority; 12 MiB, PCM CRC `105dc853` for 8,820 stereo frames.

The first actual RetroArch attempt created its state successfully, but the
runner could not read the diagnostic frame trace before process exit because
the frontend console logger buffered it. Only the opt-in state trace now flushes
stdout/stderr after logging. That initial attempt is not a completed frontend
round-trip.

`fvipers-retroarch-state-trace` then passes using the corrected diagnostic path:
RetroArch writes a 16,777,240-byte state (16 MiB core payload plus its wrapper),
advances, reloads and reproduces machine frame 2,281 exactly. Both the full
screenshots and the OSD-free game regions match. The game advances again after
Resume; exit code is zero, without forced termination. Core SHA-256:
`968bb3739807374d04a9bc1ce8ceb9b0cad5da7005031a324fa9e4d15b57521a`.
The final binary also passes the ABI suite again from a fresh process
(`fvipers-sharc-final`), matching the earlier saved/continued states and image.
This verifies frontend restoration during attract, not physical controls or
audible fidelity.

The ROM-free archive checks pass under ASan/UBSan. A maximum 0x40000-byte
program upload produces an 11,779,228-byte machine archive in the synthetic
fixture, before separate audio/geometry/frontend payloads. The decoder and CPU
lifecycle O0/O2 comparisons were refreshed against the pinned original EXE:
719 and 6,144 cases respectively, with zero mismatches. Normal rendering flags
and the installed core remain unchanged.

Known recovery coverage remains 208/208 (100%). Archive integration and tests
do not add recovered original routine addresses or imply overall Model 2B
completion. No installed/default/release core was enabled for Model 2B.

## Linux x86-64 Build And ROM-Free Qualification

The existing `linux-x86-64-on-apple-silicon` builder runs an amd64 container
through the already-running Colima/Rosetta environment. A 418-file source-only
snapshot excludes ignored builds, the original EXE, ROMs, states and user data.
The generic image lacked zlib headers; no packages were installed. The existing
SM2 image `codex-sm2-gcc15:bookworm` supplies GCC 15.2.0 and zlib instead:
image ID `sha256:ee9978e885ebe1a533fa8b86ee842209fae390f56ec1fc118efff67c7b8f76b8`.

`make platform=unix SHARC=1` uses the project's Linux build flags. The resulting
ELF x86-64 shared core passes the existing ROM-free ABI check. The mapped-machine
SHARC test, including Save State replacement/rebinding and maximum upload,
also passes. The new test target was corrected to accept an absolute `BUILD`
directory (removing the erroneous `./` prefix); no emulator behavior changed.
The same native state checks pass in macOS x86-64 under Rosetta.

The exported research core is retained under the ignored
`port/build-sharc-machine/linux-artifact/`, SHA-256:
`feb1083484e99bcee85a2e60601c3fe7f80f5b057a87f15f78423d4362d48af3`.
`readelf`/`ldd` resolve libz, libm, libc and the amd64 loader, with no missing
dependencies. Source hashes, build/validation logs and artifact metadata are
adjacent to it. No Linux frontend, GPU, audio or gameplay execution is claimed;
Windows and Linux ARM64 research builds remain unqualified. The shared Colima
profile was already running and was left running. No installation/publication.

## Over Rev Model 2B Attract And Complete Save States

Both `overrevb.zip` and its parent `overrev.zip` were read directly from the
existing archive. The bounded real RetroArch run reaches 3D attract after
1,800 frames and exits normally in 33.85 seconds. The retained screenshot
shows cars, track and scenery. No Model 2C execution or catalog change follows
from resolving the parent archive's shared files.

The existing state runner accepts `--core` to select an already-built research
core, and `--sharc` to expect its 16 MiB state capacity. Its default Model 2A
path is unchanged; individual harness processes have a 180-second bound.
Over Rev passes cold save/load, four exact 12-frame continuations after frame
1,200, invalid-state rejection, GL context recreation and fresh-process
restoration. PCM continuation CRC is `f1d61346` for 8,820 stereo frames.
The state SHA-256 is
`e91837be4fa0c0b5eddbcbec87912da80e051c631a1064f92f5f75353edb7858`.
Receipts are `port/build-sharc-machine/overrevb-states/result.json` and
`overrevb-retroarch-1800/result.json`. These are attract/state checks, not
sustained gameplay, audible fidelity, physical controls or native linked races.

## Separate Original Geometry Arithmetic Comparison

The user retained current upstream rendering and requested a separate original
comparison. `test/geometry_probe.c` includes the actual `m2geo.c` static helpers
for diagnostic builds, or compiles an independent x87 arithmetic-sequence
oracle. `test/compare_geometry.py` reuses the existing pinned-EXE Unicorn loader
to execute point transform `004b9cb0` and vector transform `004b9df0`, including
both selected matrix locations. No ROM or production-code change is involved.

The deterministic finite sample has 1,024 points and 1,024 vectors, repeated
with x87 control words `007f`, `027f` and `037f` (24/53/64-bit precision,
round-to-nearest). Original machine-code execution and the independent x87
oracle under Rosetta match in all **6,144 cases**. Counts below are complete
three-coordinate outputs differing from that oracle:

| x87 Precision | Transform | Normal ARM64 | ARM64 Without Contraction | Current x86-64 |
|---|---|---:|---:|---:|
| 24 Bit | Vector | 548/1,024 | 0/1,024 | 0/1,024 |
| 24 Bit | Point | 416/1,024 | 0/1,024 | 0/1,024 |
| 53 Bit | Vector | 548/1,024 | 756/1,024 | 756/1,024 |
| 53 Bit | Point | 694/1,024 | 760/1,024 | 760/1,024 |
| 64 Bit | Vector | 548/1,024 | 756/1,024 | 756/1,024 |
| 64 Bit | Point | 694/1,024 | 760/1,024 | 760/1,024 |

This makes the earlier cross-architecture hash difference more specific:
disabling contraction agrees with the original transforms **when** the original
uses 24-bit x87 precision for these finite inputs. It does not establish the
active precision in the Windows rendering thread, nor full renderer fidelity.
The recovered SHARC execution entry calls `00460f20`, selecting 24-bit precision,
but thread/call-path propagation to geometry has not been dynamically traced.
The CRT also contains precision setup and temporary conversion-mode changes.
The diagnostic therefore does not justify changing production renderer flags.
NaNs, denormals, overflow, other rounding modes, clipping, projection, texture
sampling, D3D rasterization and physical x86 execution are outside this sample.

Reproduction from the repository root (existing tools only):

```sh
clang -O2 -Wl,-dead_strip port/sharc/test/geometry_probe.c -lm -o port/build-sharc-machine/geometry-arm64
clang -O2 -ffp-contract=off -Wl,-dead_strip port/sharc/test/geometry_probe.c -lm -o port/build-sharc-machine/geometry-arm64-no-contract
clang -arch x86_64 -O2 -Wl,-dead_strip port/sharc/test/geometry_probe.c -lm -o port/build-sharc-machine/geometry-x86_64
clang -arch x86_64 -O2 -DGEOMETRY_X87_ORACLE port/sharc/test/geometry_probe.c -o port/build-sharc-machine/geometry-x87
port/build-sharc/venv/bin/python port/sharc/test/compare_geometry.py port/build-sharc/original/EMULATOR.EXE --oracle port/build-sharc-machine/geometry-x87 --portable port/build-sharc-machine/geometry-arm64 port/build-sharc-machine/geometry-arm64-no-contract port/build-sharc-machine/geometry-x86_64 --output port/build-sharc-machine/geometry-original-comparison.json
```

The receipt retains source/binary hashes and first mismatch inputs/outputs.
These are diagnostic comparisons of existing renderer code, not additional
recovered SHARC routines. Coverage remains **208/208 (100%)**. The normal renderer,
installed core, pristine checkout and all user saves remain unchanged.

### Windows x86-64 Libretro in VMware Fusion

On Windows 11 ARM with VMware SVGA 3D (driver 9.17.8.9), MSYS2 MinGW64
built the opt-in x86-64 DLL with `SHARC=1` and the ABI smoke test passed.
RetroArch 1.22.2 initialized OpenGL, loaded Fighting Vipers directly from the
archive on the interactive session's `K:` mapping, and rendered 3D attract
mode at the 1,800-frame capture. The test disabled audio. The first attempt
exposed the adapter's slash-only basename handling, which rejected a native
Windows path before ROM loading. The successful run used the corrected
adapter and isolated save, state and core-option directories.

Evidence: `port/build-sharc-machine/model2b-catalog/fusion/core` (local).

The unmodified ElSemi 1.1a x86 executable also renders Fighting Vipers
attract mode in the same VM, reading the same archive. The isolated
original bundle uses the shipped scripts and the official x86 legacy
DirectX components: D3DX9_42, D3DCompiler_42 and XAudio2 2.6. The test
registered the legacy COM class temporarily in the 32-bit per-user view.
Without D3DCompiler_42 the original faulted after shader compilation
(RVA 0xED090); with the compiler present and before the matching XAudio2
registration it faulted during audio initialization (RVA 0xEEEDE).
The client captures at 21 and 28 seconds show rendered output. The core
and original captures use different attract frames and establish runtime
readiness for a controlled comparison. Matched-frame or numerical renderer
equivalence and audible output remain unqualified.

Evidence: `port/build-sharc-machine/model2b-catalog/fusion/original` (local).

#### Fighting Vipers Attract Scene Comparison

On the same VM, three bounded captures produced 417 original D3D9 images,
349 core OpenGL images at the default Export setting, and 353 core images
with the original test session's Japan NVRAM. Both renderers used nearest
texture filtering. All runs read the same archive on `K:`. The original
test save stored the 64 KiB SRAM and 128-byte EEPROM as ZIP entries. The
Japan core run used those same bytes in the adapter's raw Save RAM format,
within its isolated save directory. The country field at `0x3350 & 3`
was 0 (Japan) in the original and seeded core saves, and 2 (Export) in the
unseeded core save. The attract fight HUD displays Honey in Japan and
Candy in Export. The Japan core run displays Honey.

Candidate pairs were selected by minimum RGB mean absolute error after
area resampling to 48×36, then checked visually at a shared presentation
size. The Japan pair at the fight timer **28.46** shows the same arena,
character poses and HUD names. The Tokio intro, shadow silhouette and
title screen also have visually corresponding captures. Small edge and
sampling differences remain visible. The original client is 992×768,
the core client is 1536×1152, and these are asynchronous JPEG desktop
captures. They establish scene correspondence and expose regional HUD
behavior. Numerical geometry, the original runtime x87 control word,
and frame-exact framebuffer equivalence remain open.

Evidence: `port/build-sharc-machine/model2b-catalog/fusion/matched` (local),
including source captures, side-by-side images and match metadata.

#### Runtime x87 Precision And Binary64 Candidate

The pinned ElSemi 1.1a executable was copied and instrumented with
`port/sharc/test/trace_geometry_x87.py`. The two entry trampolines execute
`FNSTCW`, record the latest control word and count the precision/rounding
combinations while preserving EAX, EFLAGS and the original prologues. The
Windows 11 ARM Fusion run launched Fighting Vipers from the archive on `K:`.
Both routines reported **0x027F (53-bit precision, round-to-nearest)**.
The sole precision/rounding bucket contained **6,022,388 point calls**
and **2,599,636 vector calls** at the final read. The instrumented run
establishes the mode at those entry points on this host. Its desktop
captures were blank and are not evidence of rendering fidelity.

At the measured mode, the current ARM64 helpers differ from the independent
x87 oracle on 1,242/2,048 finite cases. ARM64 without FMA and current
x86-64 each differ on 1,516/2,048. The diagnostic binary64 candidate
preserves the recovered arithmetic order, disables contraction and rounds
to binary32 on output. It matches the independent oracle in **2,048/2,048**
cases on both ARM64 and x86-64. Unicorn raised SIGILL at memory mapping
during this rerun, so this comparison uses the independently executed
x87 oracle on Rosetta. The earlier original-binary Unicorn cross-check
remains a separate receipt.

Reproduce the candidate with `-O2 -ffp-contract=off
-DGEOMETRY_BINARY64_CANDIDATE` on `geometry_probe.c` and run
`compare_geometry.py --oracle-only-cw 0x27f` with the candidate binaries.
The manifest, runner, runtime samples and numerical receipt are in
`port/build-sharc-machine/model2b-catalog/fusion/runtime-x87` (local).

The candidate is diagnostic. Before selecting it for the production
renderer, compare captured live operands and output coordinates, then
check clipping, shading and rendering regressions on the boards affected
by the shared helpers. No production renderer or build flags were changed.

#### Live Fighting Vipers Geometry Operands

A second instrumented copy of the pinned ElSemi executable records the
original input vector, selected matrix, x87 control word and returned
coordinates at the two transform entry points. The VM run sampled every
65,536 calls and retained 32 completed records per routine. All 64 inputs
are finite and distinct within their routine, with control word 0x027F.
The test reads Fighting Vipers directly from the archive on `K:`.

| Comparison Against Original Returned Bits | Point Differences | Vector Differences |
|---|---:|---:|
| Current ARM64 | 16/32 | 20/32 |
| ARM64 Without Contraction | 17/32 | 25/32 |
| Current x86-64 | 17/32 | 25/32 |
| Independent x87 Oracle | 0/32 | 0/32 |
| Binary64 Candidate, ARM64 and x86-64 | 0/32 | 0/32 |

This corroborates the candidate on live operands before clipping and
rasterization. The sample is from one game and one host. The renderer
integration and regression gates remain open. The instrumented run's
desktop captures were blank, so this run contributes coordinate evidence
only. Local evidence: `port/build-sharc-machine/model2b-catalog/fusion/live-vertices`.

#### Model 2B Transform Integration

The research build now selects binary64 intermediates for Model 2B point
and vector transforms in the existing geometrizer. Each product of two
finite binary32 operands is exact in binary64. The original addition
sequence is preserved, with one binary32 conversion per output coordinate.
The normal compiler flags remain in effect. The board discriminator already
travels with the frame pipeline shadow, so direct and pipeline rendering
select the same arithmetic. The change adds no serialized state.

- The integrated path matches all 64 live ElSemi transforms and all 2,048
  finite oracle inputs on ARM64 and x86-64 with normal compiler flags.
- Model 2 and 2A arithmetic selections in the research build match the prior
  ARM64 transform probe bit for bit on 2,048 inputs per selection. Virtua
  Fighter 2 also matches the prior headless run over 1,200 frames. The
  Daytona USA and Virtua Cop headless runs stop on missing shared Model 2 ROM
  payloads in the archive path tested.
- Fighting Vipers matches its prior main RAM hashes over 1,200 frames.
  Direct and pipeline runs match their RAM and sampled geometry/tile hashes.
  Corrected geometry/tile hashes differ from the prior build during attract.
  At frame 1,800, both versions emit 648 polygons and 2,447 finite clipped
  vertices within the 496×384 viewport. RetroArch on macOS renders 3D attract
  at that frame and exits normally.
- This group does not repeat the frame-exact Windows renderer comparison or
  full Model 2B gameplay and Save State qualification.

Local evidence: `port/build-sharc-machine/geometry53-run.7uAvyc`.

#### Indy 500 And Rail Chase 2 Spot Checks

The corrected research renderer was checked on two additional Model 2B
games. The headless test build used the Libretro MAME catalog with ROMs
read directly from the existing archive. Each game ran through 3,600
attract frames in both direct and pipeline modes. All 3,600 main RAM
hashes and 12 sampled geometry/tile hashes matched between the two paths
for each title.

Clipped polygon dumps at frames 1,800, 2,040 and 2,400 were compared
against the same headless build linked with the pre-change geometrizer.
All six corrected dumps preserve polygon/vertex counts and viewport
extents to the dump's printed precision. All emitted coordinates are
finite with positive depth. Indy 500 reaches x=498 in both builds;
Rail Chase 2 reaches x=496. Both reach y=384.

Both titles also rendered 3D attract in isolated macOS RetroArch runs
and exited normally at 2,400 frames. Indy 500 shows the track and car
from the race demo. These runs cover attract and clipping regressions
for two titles, without claiming paid gameplay, physical controls,
Save State coverage or frame-exact equivalence to the Windows renderer.

Local evidence: `port/build-sharc-machine/geometry53-sample.Ql6dqJ`.

#### Windows Lossless Grace Scene Comparison

The before/after x86-64 research DLLs passed the ABI checks and ran Fighting
Vipers in RetroArch on Windows 11 ARM under Fusion. Both used the same
Japan test NVRAM and nearest filtering. RetroArch captured the same
1,536×1,152 PNG byte for byte at its frame limit of 1,800 for both builds.
The game ROM remained on `K:`. The first desktop captures were invalid
because the application windows were obscured or inactive. The repeated
RetroArch run disabled pause-on-focus-loss in its isolated config.

An instrumented ElSemi 1.1a test copy sampled 25 consecutive visits to
its built-in D3D9 back-buffer screenshot path. It produced lossless
496×384 BMPs. The previous denser capture campaign faulted in the VMware
D3D driver after 42 captures. The bounded 25-capture run completed.
The best pose match for the Grace scene was BMP 016. Its 48×36 area-resampled
RGB mean absolute error against the corrected core PNG is 1.55/255;
the next closest candidate is 7.42/255. The pose, spotlight and HUD align
visually. The D3D9 native back buffer and the OpenGL frontend viewport
have different sampling and dimensions. This establishes close lossless
scene correspondence, with a byte-exact before/after core result on this
one frame. It does not establish a common emulated-frame counter or
pixel-exact ElSemi equivalence.

Local evidence: `port/build-sharc-machine/model2b-catalog/fusion/geometry53-lossless`.

#### Model 2 Regression And Extended Model 2B Save State

Daytona USA and Virtua Cop ran for 1,800 headless frames each using the
Libretro MAME catalog and the existing ROM archive. The baseline differs
only in the geometrizer object. Both titles produce identical logs,
including 1,800 main RAM hashes and six geometry/tile hashes per title,
before and after the Model 2B arithmetic change. Both runs contain
rendered polygons. Daytona also reaches rendered 3D attract at frame
2,400 in isolated macOS RetroArch and exits normally. The Libretro MAME
catalog resolves the relevant payloads without the standalone catalog's
shared video-table requirements.

Fighting Vipers ran 6,000 frames at 60 Hz with scripted inputs in the
Libretro ABI/OpenGL harness. The final capture shows the active Grace
versus Bahn match. The 16 MiB Save State passes four exact 12-frame
RAM/device/PCM/image continuations in the same process, context recreation,
malformed-state rejection without mutation and exact serialized continuation
in a fresh process. This is a scripted single-title qualification on
macOS; the Save State run used the harness, and the Daytona attract run
used real RetroArch.

Local evidence: `port/build-sharc-machine/final-regression.gdWHBW`.

#### Additional Save State And Cross-Platform Qualification

Dead or Alive Revision C and Virtual-On Twin Export pass 2,400-frame
macOS ABI/OpenGL tests, including exact same-process and fresh-process
Save State continuation. Both also pass the isolated RetroArch slot
round-trip. The 16,777,240-byte frontend state restores the game region
exactly, both games advance and resume, and both RetroArch processes
exit normally without a forced kill.

The current research tree also builds on Linux x86-64 with the existing
Debian/Colima amd64 image. The ELF ABI check and mapped SHARC machine
test pass, including upload, FIFO execution, shared RAM, reset, state
replacement/rebinding and teardown. This was a ROM-free container check
and does not qualify a native Linux RetroArch GPU or controller.

A separate Windows-only diagnostic read the corrected core's OpenGL
framebuffer before frontend scaling. The 25 native 496×384 OpenGL
frames were compared against the 25 lossless ElSemi D3D9 frames in the
Grace capture window. The closest pair by area-resampled RGB distance
was ElSemi BMP 009 and OpenGL sample 1793. At native size, 34,031 of
190,464 RGB pixels differ, with a channel MAE of 2.85/255. The comparison
removes frontend resizing. It establishes image differences in the
sampled pose, with no shared machine-state marker to distinguish
remaining timing and renderer differences. No production code was
instrumented. The prior bit-exact comparison of 64 transformed operands
remains the precision evidence.

Local evidence: `port/build-sharc-machine/m27-qualification.FVQaeS`.

#### Fighting Vipers Raw Display List And Draw Geometry

Temporary Windows diagnostics captured native 496×384 frames, the
512 KiB display-list RAM with its active start offset, and the geometry
submitted to each graphics API. The ElSemi probe traces the four Model 2
DrawPrimitiveUP sites and records the last geometry slot immediately
before the built-in D3D9 back-buffer readback. Its single-capture run
completed after the denser mapped capture faulted in VMware's D3D driver.
The core probe records clipped polygons and indexed OpenGL triangles
alongside the FBO readback. The binaries and scratch sources are diagnostic
copies; no production renderer change is involved.

The free-running pose matches had differing display-list payloads.
A replay fed the exact ElSemi-captured display-list RAM and start offset
into the core geometrizer for one draw using a shadow board. The probe
verified the input byte for byte. The 1,716 original and 1,194 core
triangles are submitted at different clipping and tessellation boundaries.
For the 3,381 original submitted vertex occurrences projected inside
the viewport, 3,381 have a core mesh neighbor within one pixel on replay,
compared with 199 on the free-running candidate. This is a spatial
nearest-neighbor check, with repeated vertices counted, and does not prove
matching topology, texture attributes or sort order.

The replay did not synchronize other graphics state, including tiles,
texture and palette RAM, or the full machine state. Its RGB error against
the reference BMP was 13.52/255, versus 2.84/255 for the visually selected
free-running frame. The command replay therefore isolates a useful
geometry input while leaving pixel equivalence unresolved. Directly
comparing raw polygon counts or treating pose selection as a common
frame index would overstate the result.

Local evidence: `port/build-sharc-machine/model2b-catalog/fusion/geometry-buffers/mapped`,
including the ElSemi display list and triangle batches, original BMP, core
polygons, indexed mesh, PPM and comparison receipt.

#### Replay With ElSemi Video RAM

A bounded repeat of the ElSemi capture produced the same BMP and display
list. The probe also copied the original tile, character, palette,
color-translation, luminance and two texture banks immediately before
the back-buffer read. A Windows diagnostic core replayed the exact list
and all seven RAM banks through a shadow board at OpenGL draw 1792.
It rebuilt the tile cache and invalidated GPU uploads for the replay.
No production source or installed core was changed.

The audit confirmed the renderer inputs matched all seven ElSemi RAM
banks. Relative to the live core, the replay changed 42,115 character
bytes, 12,282 palette bytes and 3,018/2,005 bytes in texture banks 0/1.
Tile, color translation and luminance bytes already agreed. Despite
those input changes, the OpenGL mesh and native PPM are byte-identical
to the previous display-list-only replay. The RGB error against the
ElSemi BMP remains 13.52/255. The test rules out these seven captured
RAM banks as an explanation for that change in this sample. Persistent
geometrizer state, render-target timing and API draw state are outside
this replay. Matching at the point of presentation remains necessary
before attributing the pixel discrepancy to rasterization.

Local evidence: `port/build-sharc-machine/model2b-catalog/fusion/geometry-buffers/video-replay`.

### Batocera x86-64 Frontend Smoke Test

On 2026-11-03, the Linux x86-64 `SHARC=1` core
(`3ac0e83a334a48fde5643a025687b996e205cf0669a3a5ae8398795a246e60`)
ran Indy 500 in RetroArch with the GL driver. The isolated run used the
existing Batocera ROM archive, captured the rendered 3D attract sequence,
and exited with status 0 after the 2,400-frame limit. The private Save RAM
was 65,664 bytes. The ROM, Addon override, and shared test save and state
sentinels matched their pre-run hashes. This was an attract-mode smoke test.

### Remaining MAME Set Definitions And Power Sled Boot

The Libretro catalogue now contains 61 sets, including all 35 pinned MAME
Model 2B definitions. The compiled catalogue check verifies program identity,
consumed ROM tuples, archive lookup, and standalone isolation.

- Fighting Vipers Revisions A and B use the matching program and data EPRs.
  Both reached 3D attract in isolated macOS RetroArch runs at 1,800 frames.
  The Revision D i960 wait-loop hook is specific to its original program.
- Dynamite Baseball reached 3D attract at 2,400 frames. The definition retains
  the Baseball cabinet input profile and uses the earlier board's actual ROM
  population.
- Virtual-On Relay initialized the coprocessor, geometry and textures and
  displayed `THIS IS RELAY SITE` at 1,800 frames in local loopback.
- Power Sled Slave, Relay and reconstructed Main use pinned MAME ROM
  identities and the Power Sled program patches in the imported SM2
  catalogue. All three crash in SHARC dispatch during startup. A bounded
  retry with explicit invalid-record reporting identifies Main's failing
  SHARC PC as `003e0402`, outside the current decoded program window. A
  second trace identifies a delayed branch at `0002000b` with that decoded
  target and two NOP delay slots. The upload bytes and their interpretation
  need comparison against the working SM2 boot path before changing decode.
  That failure was resolved by the scoped upload correction below.

### Power Sled Upload And Local Cabinet Qualification

A bounded LLDB capture matched all 64 initial Model2EmuEx i960 FIFO writes
against SM2's first 64 DMA input words for the reconstructed Main. The writes
are 16-bit. ElSemi's recovered handler stores each word twice through its
fall-through, while SM2 delivers each word once. The duplicate stream yields
the invalid delayed branch above. The Libretro Power Sled sets now use the
existing single-word upload handler only during FIFO program uploads. This
title family is absent from ElSemi's 1.1a catalogue. Other titles and the
original recovered handler retain their existing behavior.

The Power Sled communication window is mapped at both host mirrors, with
the appropriate CN/FG lanes and the title's 0x180 receive offset. The
original Model2EmuEx communication paths for its catalogue remain in use.
SM2's guarded Standalone, Relay attract, Relay Commands and AI Finish Speed
patch algorithms borrow the destination i960 program span. All guards passed
against the pinned archives. Main and Relay reached 3D attract with a live
one-node link, and Slave displayed its native network wait screen. All three
isolated macOS RetroArch runs exited normally at 1,500 frames. SM2 Headless
reached the same Slave network wait screen at 1,500 frames. A separate
3,500-frame Libretro ABI/GL run drove Main through boarding, departure,
countdown and into the race with scripted Select, Start and Entry inputs.

The Slave test exercises boot and its local wait state. The subsequent
three-instance RetroArch test formed one SM2 Netpacket roster from all three
ROMs. The original Model2EmuEx link driver assigned Main ID 1, Relay ID 3
and Slave ID 2. All three rendered 3D and exited normally. A second run
reproduced the linked 3D boot. The available log does not separately
establish in-session Restart recovery or synchronized race gameplay.

A Linux x86-64 package-style SHARC build passes the ABI and dependency
checks in the Debian container and renders Power Sled Main in Batocera
RetroArch for 2,400 frames. The installed Addon, configuration and ROM
hashes are preserved. The macOS Intel binary passes the ROM-free ABI
check under Rosetta. The SM2 auxiliary Relay audio arrangement remains
outside this reconstruction.
