# Native Model 2C Reconstruction Analysis

Updated: 2026-11-04. M28 tracks the static inventory and isolated recovery
groups in [Roadmap](ROADMAP.md). Model 2C is connected in the explicit
`TGPX4=1` build. Ordinary local defaults remain unchanged; the distribution CI
recipe now enables it explicitly, pending CI execution and publication. The
bounded reconstruction and integration group is complete. Broader game/device
qualification and distribution enablement remain M14/M16, respectively.

## Findings

The original ElSemi 1.1a executable contains a distinct Model 2C driver and
MB86235/TGPx4 execution path. Reuse that implementation as the recovery source;
neither SHARC nor the existing MB86234 interpreter implements this instruction
set. The i960, shared machine, audio, frontend and renderer remain existing
components, subject to destination integration checks.

The first reviewed static inventory contains **286 candidate entry addresses**:

| Area | Candidate Addresses | Existing Decompiled Bodies | Missing Exported Bodies |
|---|---:|---:|---:|
| CPU Helpers, Decode, Execution And Lifecycle | 261 | 22 | 239 |
| Board Driver And Two Bound Memory Callbacks | 25 | 0 | 25 |
| Total | 286 | 22 | 264 |

This table records the initial inventory, before recovery. All 286 addresses
have since been covered by the groups below, with 18 additional helpers.
The original exported-body count does not measure implemented recovery, and
286 is not an effort estimate or proof of every possible execution path.
New indirect dependencies or split function entries can expand that inventory.

## Original Anchors

| Address | Observed Role |
|---|---|
| `00574c00` | Driver table, anchored by `Model 2C Driver v2.0 by ElSemi` at `0051bc38`; 29 code slots, 23 specific and six shared |
| `004c5c80` | Board initialization; calls program setup, binds memory/FIFO pointers and applies native per-game geometry configuration |
| `004c58d0`–`004c5c10` | Host control, upload and FIFO access handlers, with separate access widths |
| `004c5a70`, `004c5a90` | Bound external memory handlers, additional to the 23 specific table entries |
| `004b7940` | Program allocation/decode/reset and native state registration |
| `004b77a0` | Top-level instruction decode; selects seven instruction-class wrappers |
| `004b6730`, `004b6ac0`, `004b6b90`, `004b6ef0`, `004b7100`, `004b7440`, `004b75d0`, `004b76b0` | Subdecoders composing operation, operand and transfer callbacks |
| `004b6010` | Execution loop, FIFO stopping, queued effects, repeat/branch handling |
| `004b3470`, `004b3480`, `004b34a0`, `004b34c0`, `004b3520` | State address, FIFO binding, external memory binding, x87 setup and reset helpers |
| `004b34d0`, `004b34f0` | Original CPU save/restore callbacks |

The `00572ac0` pointer run has 480 entries and 150 unique targets. The
`00573248` run has 32 entries and 32 distinct additional targets: **182 unique
dispatch targets** across 512 slots. These are physical contiguous runs, not
claims that each run is a single semantic table. Their roles are established
by the subdecoders' references. Source address-taking, original code stores,
direct calls and reviewed lifecycle entries supply the remaining candidates.

Boundary review excludes two misleading neighbors:

- `00572a88` begins with 14 A68K interface pointers before the Model 2C tables;
  these are not missing MB86235 instructions. Corresponding code before
  `004b3470` uses the 68000 state/memory interface.
- `004b7ad0` already accesses Direct3D texture state. It is outside the CPU
  inventory. Inline switch-table bytes must also not be mistaken for executable
  instructions: a linear decode at `004b6aa9` produces a spurious code-valued
  IMUL immediate. It is excluded from candidate extraction.

The six shared driver targets are `004bbdd0`, `004ba7b0`, `004b9f70`,
`004b93a0`, `004b8410`, and `004b83e0`. Their reuse must be checked at integration,
but they are not counted as newly missing CPU routines.

## Integration And Preservation Concerns

- **Decoded execution:** each eight-byte uploaded instruction expands into a
  `0x94`-byte record with multiple callbacks. The scheduler runs queued effects
  and consults FIFO readiness. Replacing this with a generic instruction loop
  would require a semantic decision; the intended recovery preserves it.
- **Native edge behavior:** the 16-bit host write at `004c5990` masks ECX with
  `0xfff` and then compares it with `0x804000`, making that upload branch
  unreachable. Preserve this as observed until an explicit bug-fix decision.
  The top-level decoder has no class-3 branch; its behavior requires bounded
  original-execution tests before implementing an assumed fallback.
- **Floating point:** `004b34c0` loads x87 control word `003f` (architectural
  reserved-bit normalization yields `007f`). Arithmetic results and inherited
  flags require the same original-code/oracle discipline used for SHARC.
  This finding does not authorize changing the shared renderer.
- **Save States:** setup registers a `0x140`-byte CPU block. Restore copies it,
  then writes `destination+0x144 = PC_at_0x114 * 0x94 + base_at_0x140`.
  The cache base is outside the copied block, so this callback depends on the
  current decoded program. The research binding now follows the approved M2A
  complete-snapshot policy, preserving that callback and adding the decoded
  upload/cache and execution context. Over Rev passes same/fresh-process exact
  continuation. See SAVE_STATES.md for the current 16 MiB TGX3 payload and limits.
- **Catalog:** existing Model 2C frontend/catalog preparation does not mean the
  CPU executes. Type 3 executes only with `TGPX4=1`; all 13 native records now
  have MAME-aligned metadata. Bounded frontend evidence and remaining per-game
  qualification are detailed below.

## Recommended Recovery Order

1. Recover/export the reviewed candidates with the existing RegionExport tool,
   confirm function boundaries and register ABIs, and close indirect references.
2. Recover lifecycle, native state callbacks and memory/FIFO handlers. Establish
   isolated original-vs-port fixtures using the existing Unicorn workflow.
3. Recover operand access, transfers, integer/flag and floating-point operations
   in related groups; use independent x87 evidence where necessary.
4. Recover the subdecoders, composed records and execution loop; verify their
   ordering and stop behavior with synthetic programs.
5. Connect an isolated research machine build, then complete frontend snapshots
   and bounded game execution. Production enablement remains a separate choice.

The work is a substantial CPU recovery with hundreds of candidate entries, not
a board-type switch. A calendar estimate or comparison to SHARC effort would be
premature until the indirect callback graph and execution-loop complexity
are better understood.

## Verified Recovery Groups

304 entries now have isolated portable implementations: **286/286 initial
candidate addresses (100%)**, plus 18 helpers outside that initial inventory. That is a static-entry metric, not a
measure of CPU or game compatibility. LLVM confirmed the entry boundaries
and instruction paths for these groups. The tests execute the original x86
with Unicorn and compare it to the portable helpers at `-O0` and `-O2`.

| Group | Verified Entries | Original Executions | Portable Comparisons |
|---|---:|---:|---:|
| Lifecycle, Bindings, Reset And Native State Callbacks | 7 | 3,584 | 7,168 |
| Host FIFO And Program Upload | 5 | 3,840 | 7,680 |
| External And Shared Memory, Upload Completion Entry | 6 | 3,072 | 6,144 |
| Program Allocation, Record Construction And Reset (Isolated And Integrated) | 1 | 1,024 | 2,048 |
| Instruction Class Dispatch, Isolated And Integrated | 1 | 4,096 | 8,192 |
| Operand And Transfer Subdecoders | 6 | 12,288 | 24,576 |
| Control, Wide Transfers And Target Addresses | 5 | 89,088 | 178,176 |
| Continuous And Single-Batch Schedulers | 2 | 512 | 1,024 |
| Instruction Execution Wrappers | 7 | 3,584 | 7,168 |
| Register, Immediate And Counter Primitives | 127 | 32,512 | 65,024 |
| Flow, Deferred Queues And Memory Primitives | 38 | 19,456 | 38,912 |
| Integer Arithmetic, Logic And Shifts | 20 | 81,920 | 163,840 |
| Address Generators, Transfers And FIFO Operations | 43 | 44,032 | 88,064 |
| Native Driver Setup And Callback Surface | 14 | 3,840 | 7,680 |
| FP Dispatch And Native Callback ABI | 22 | 45,056 | 90,112 |

Lifecycle comparison checks stack and preserved registers, FIFO and external
callback bindings, the native state copy and decoded-record rebinding, and
reset boundaries. Unicorn exposes the raw x87 control word; the comparison
normalizes reserved bit 6 as in the SHARC oracle. The host test compares
upload RAM, FIFO counters and data, read widths and the state on entry to the
original scheduler. The scheduler itself is an explicit stub at `004b6010`
in this fixture. The 16-bit FIFO program upload writes one halfword.
The separate 16-bit control-port handler at `004c5990` leaves state
untouched because the address mask makes its upload branch unreachable.

External-memory reads at `004c5a90` use the original 16 MiB bias relative
to writes at `004c5a70` in the shared-memory address range. The differential
uses distinct contents at both offsets. It also checks tagged and untagged
host writes, latch values, wraparound and the data-upload window. The
program-completion entry at `004c5c70` forwards the byte count and a null
state-registration argument to `004b7940`. That predecoder entry is stubbed
in the test. The common upload-control routine at `004c79c0` already has a
portable SHARC binding with the same full-word XOR and callback ordering.

Program setup at `004b7940` matches normal serializer registration,
release/allocation ordering, the 8-byte upload to 0x94-byte record loop,
the neighboring-record rewrite and reset. Its test uses explicit native
list allocation, CRT allocation and decoder callback boundaries. The
fatal registration overflow branch is retained and has static evidence.
The native rewrite can inspect the 0x2c-byte allocator prefix on record
zero. The portable allocator contract makes that storage explicit.

Dispatch at `004b77a0` covers all eight classes. Class 3 retains the
allocator-provided wrapper while recomputing FIFO flags. The comparison
checks neighboring-record FIFO updates and live register handoff, including
ESI as the low instruction word for `004b75d0`. All eight subdecoders now run
through dispatch without subdecoder stubs. Control coverage includes all 32
operations, 64 conditions, 16 target modes and both register banks. Wide
transfers cover every source/destination selector pair and both port
directions. Target address helpers run as original code, with separate
checks of their exit registers. `004b6730` derives ECX from EAX, while
`004b6b90` reads the high instruction word from EDX and uses different
immediate widths and a distinct memory-to-port reader from `004b7100`.
The program-setup test now also runs the complete original decoder and all
subdecoders without stubs, comparing the full resulting record array and state.
Only native CRT/list allocation remains a fixture in that integrated path.

Scheduler `004b6010` matches FIFO gates, early stop, dynamic deferred queues,
delayed-instruction ordering, repeat-counter wrap/expiry and the 1000-instruction
batch reload. Its 256 scenarios compare 12,619 callback events, all general
registers observable at those boundaries, arithmetic flags, the x87 control token
and final memory. The seven class wrappers independently match 16,896 callback
events, including changes to the active record/state between operations. Their
indirect operation bodies remain explicit fixtures; portable arithmetic and
full upload-to-execution validation remain open. The execution bus uses native
32-bit address tokens with explicit memory/call callbacks. The x87 token does
not change host rounding; numerical handlers must implement original semantics.

Register primitives preserve native 16-bit writes, 14-bit address masks,
32-bit wrapping, circular-counter boundaries and RET-only controls. Tests compare
all general registers, defined arithmetic flags and complete surrounding memory.
AF after x86 logical operations is architecturally undefined and is excluded
from equivalence claims. The large number of short accessor entries must not
be interpreted as an equally large fraction of implementation complexity.

Flow checks cover taken/untaken conditions, return-stack push/pop, delayed
branches, both internal memory banks, external-call handoff and deferred-write
queue arguments. `004b4af0` clears the loop flag when the decremented 16-bit
counter is **one**, not zero. This native behavior is retained and documented.

## Connected Synthetic Programs

The program/decode/execute composition passes 128 complete synthetic programs
at O0/O2: 19,904 original instructions and 39,808 portable instruction-boundary
comparisons. All seven defined instruction classes are covered; class 3 retains
its separately tested allocator-dependent decode behavior and is not executed.
The original runs its real decoder, scheduler, wrappers, operand readers,
integer arithmetic, transfers and deferred queues. Only CRT malloc/free are
replaced. FIFO readiness ends execution through the native decoded flags.

The first 64 programs exercise register/immediate/integer combinations. Another
64 add both internal memory banks, all sixteen address-generator selectors,
deferred modifier writes, ring-buffer increments and live input/output FIFO
transfers. Complete CPU memory, decoded records, queues and FIFOs match, with
CPU snapshots compared at every instruction boundary. These are ROM-free
component integration tests, not a complete i960 machine or game run.
Receipts: `model2c-pipeline.json` and `model2c-pipeline-memory.json`.

## Scalar Floating-Point Recovery

All 22 FP entries are dispatched. Their callback ABI contributes 90,112
comparisons to the **695,808** entry/ABI comparisons above. The dispatch preserves
operand order, record/state rebinding, scratch registers and stack-derived FLAGS
through an explicit x86 stack token. Host stack addresses and the host FP
environment never substitute for that context.

The decisive numerical check runs the **unchanged original 32-bit PE bodies
natively on an AMD Ryzen 5 3400G**, under Batocera's Linux i386 compatibility
mode. The suite executes 206,908 general FP vectors plus 69,692 focused logarithm
vectors: **276,600 original executions and 553,200 O0/O2 portable comparisons**.
Results, guest flags, control word and x87 status agree exactly, with no tolerated
mismatch predicates. An independent native x86-64 transcription of the same x87
sequences agrees as well. This qualifies the tested numerical scope, not all
possible inputs or game execution. Masked exceptions, PC=24 and an initially
empty x87 stack match the original scheduler contract.

The native probes cover constants, integer conversions, arithmetic, comparison,
clamping, absolute value, reciprocal, reciprocal square root and logarithm in all
four rounding modes. Receipts: `model2c-fp-original-amd.json` and
`model2c-log-original-amd.json`, with hardware/checksum receipts under
`m2c-fp-batocera-results` and `m2c-fp-original-results-2`.

The original MSVC CRT flag at `010f1fec` selects two conversion paths for
`004b5460`: SSE2 int32 or legacy x87 int64-low. Both are explicit inputs and
verified, including their different overflow results. The tests run the actual
original CRT conversion; they do not replace it with a conversion fixture.

Unicorn's known exception accumulation, SNaN quieting/selection and C1 omissions
are checked with narrow predicates. Multiply additionally flushes to positive
zero when the **pre-store** x87 status reports a denormal operand. The independent
oracle exposes the unflushed product as well, bounding the resulting Unicorn
numeric/status differences. Other mismatches fail. The portable result, guest
status and x87 state must match the x87 sequence exactly at both optimization
levels. The earlier 21-entry Unicorn receipt records 1,230 numeric, 1,012 guest-status and 78,138
x87-state differences attributable to those oracle limitations (overlapping).

Generic PC=24 x87 arithmetic was extracted unchanged from the qualified SHARC
implementation into `port/x87/x87_binary32.h`; no guest SHARC behavior is reused
as a substitute for TGPx4. Its existing 93,600-case arithmetic differential passes
after extraction. These changes do not alter the renderer or compiler FP flags.

### Logarithm And Translator Limitations

A separate Q96 integer implementation reproduces the original FLDLN2/FYL2X/FMUL
sequence, including its binary32 scale constant `40549a78` and intermediate
extended rounding. It passes 69,692 focused scalar vectors against the independent
Rosetta x87 sequence at O0/O2 (139,384 comparisons), including neighborhoods of
one, powers of two, special values and all four rounding modes. The subsequent
physical-AMD original-code run above confirms these vectors and closes the
numerical blocker. The logarithm is now dispatched. Its Unicorn ABI fixture uses
positive powers of two; special values and broader numerical/state coverage are
owned by the native suite, since Unicorn FYL2X fails even the zero-input case.

The Windows 11 ARM VM ran 206,908 numerical calls into the pinned original x86
bodies, including the actual CRT conversion. The probe maps only required PE
code/constants, without starting the emulator. An audited 37-operand relocation
manifest moves three global variables away from CLR allocations; FP instructions,
branches and constants are unchanged. No ROM is involved.

The Windows ARM x86 translator differs from the Rosetta sequence in exception
accumulation, invalid-result sign and some reciprocal/square-root rounding cases.
Those discrepancies are retained in `model2c-fp-windows-diagnostic.json`; the
report is diagnostic, **not an equivalence pass**. No core behavior was changed
to follow them. The initial 8,996 logarithm cases agree in result and guest flags,
with 3,098 x87-status differences. The expanded 69,692-case logarithm run
also agrees in result and guest flags, with 41,828 x87-status differences
(`model2c-log-windows-diagnostic.json`). The physical AMD result above resolves
this blocker without changing portable arithmetic to follow translator defects.

## Reproduction And Evidence

Only the already-authorized original EXE and existing source/tools were read.
The pristine checkout, normal renderer, installed core and user data were not
changed. No ROM was opened/copied, dependency installed, game started, commit
created or remote publication performed.

```sh
python3 tools/model2c_inventory.py port/build-sharc/original/EMULATOR.EXE --output port/build-sharc-machine/model2c-inventory.json
```

The tool verifies the pinned executable SHA-256
`2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc`,
maps its PE sections, checks driver identity and records every candidate's
source/table/binary evidence and initial bytes. It also lists external CRT/math
calls separately. The ignored JSON receipt records source/tool hashes; the
adjacent `model2c-driver-disassembly.txt` retains the inspected driver body.

For the isolated differentials, use the existing SHARC Unicorn environment:

```sh
d=port/build-sharc-machine
for o in 0 2; do
  clang -std=c11 -Wall -Wextra -Werror -O"$o" -dynamiclib \
    port/tgpx4/tgpx4_lifecycle.c port/tgpx4/tgpx4_host.c \
    port/tgpx4/tgpx4_program.c port/tgpx4/tgpx4_decode.c \
    port/tgpx4/tgpx4_execute.c port/tgpx4/tgpx4_driver.c port/tgpx4/tgpx4_fp.c \
    -o "$d/model2c-lifecycle-o$o.dylib"
done
for group in lifecycle host memory program decode operands control execute wrappers registers flow integer transfers driver; do
  port/build-sharc/venv/bin/python "port/tgpx4/test/difftest_$group.py" \
    port/build-sharc/original/EMULATOR.EXE \
    "$d/model2c-lifecycle-o0.dylib" "$d/model2c-lifecycle-o2.dylib" \
    --output "$d/model2c-$group.json"
done
```

The single-batch scheduler uses the same fixture with `--batch`, writing
`model2c-batch.json`. For the scalar FP group:

```sh
clang -arch x86_64 -O2 -Wall -Wextra -Werror port/tgpx4/test/x87_oracle.c -o "$d/model2c-x87-oracle"
port/build-sharc/venv/bin/python port/tgpx4/test/difftest_fp.py \
  port/build-sharc/original/EMULATOR.EXE "$d/model2c-x87-oracle" \
  "$d/model2c-lifecycle-o0.dylib" "$d/model2c-lifecycle-o2.dylib" \
  --exclude-log --output "$d/model2c-fp.json"
```

The dispatch fixture is `difftest_fp_dispatch.py` with the same EXE/libraries.
It tests finite inputs and excludes Unicorn's known C1/exception omissions;
the scalar suite above owns numerical qualification. `--log-only --portable-only`
on the scalar fixture runs the logarithm sequence comparison without claiming original
code execution. The Windows diagnostic uses `--windows-output FILE
--windows-diagnostic`; omitting the diagnostic flag requires exact agreement.

`port/tgpx4/test/build_windows_fp_probe.py EXE OUTPUT_PREFIX` reproducibly builds
the LLVM trampoline and audited relocation manifest. Compile
`windows_original_fp.cs` with the installed x86 .NET Framework compiler using
`/platform:x86 /baseaddress:0x20000000`; run the resulting probe with arguments
`ORIGINAL_EXE TRAMPOLINE.bin INPUT.bin OUTPUT.bin`. The scalar fixture's
`--export-input` produces the binary vectors. Run only in an isolated directory;
Windows ARM results must be labeled as translated execution.

The connected-program fixture is `difftest_pipeline.py EXE LIBRARY_O0 LIBRARY_O2
--output RECEIPT`; add `--memory` for the memory/deferred-queue/live-FIFO group.

### Native Shared-Read Boundary Before Machine Integration

The unusual `004c5a90` shared-read offset is confirmed in the original opcode
stream (`MOV EAX,[EAX+ECX*4]` at `004c5aa8`). Original board setup allocates
only `0x80000` bytes for M2BUFRAM (`004cd8a5`/`004cd8aa`) and binds that pointer
at `005aa700` (`004cdc2f`/`004cdc35`). Thus the `00400000..007fffff` word-address
read window would access beyond that allocation. The isolated memory fixture
uses a deliberately sufficient backing region to verify address arithmetic;
it does not prove that a game uses this window or that a real board may map it
onto unrelated storage. Preserve the recovered calculation. Machine integration
must detect any such access and establish original usage before choosing a
mapping or correction; no mirror, zero fallback or enlarged guest RAM is implied.

### Native AMD Probe Reproduction

`test/linux_original_fp.c` and `.S` build an isolated freestanding i386 ELF:

```sh
gcc -m32 -O2 -Wall -Wextra -Werror -ffreestanding -fno-pie \
  -fno-stack-protector -nostdlib -static -Wl,-Ttext-segment=0x20000000 \
  linux_original_fp.c linux_original_fp.S -o original-fp
```

It maps only the three required original code/constant regions and original
global addresses, with `MAP_FIXED_NOREPLACE`. Unlike the Windows CLR probe,
**no original instruction operand is relocated or patched**. Only the two
operand readers are fixtures. The original CRT conversion executes unchanged.
The enclosing `run.sh` verifies the pinned EXE SHA-256 before executing
`original-fp EMULATOR.EXE < INPUT.bin > OUTPUT.bin`. Inputs contain no ROM data.
The i386 binary is static; no Batocera packages or dependencies are installed.

Build the independent sequence probe with
`gcc -O2 -Wall -Wextra -Werror -march=x86-64 x87_oracle.c -o x87-oracle`.
The existing Linux builder compiled both probes; the standard Batocera runner
staged checksummed bundles, imposed a 60-second timeout and fetched results.
The accepted runs are `m2c-fp-20261104` and `m2c-fp-original-20261104-2` below
`/userdata/system/codex-core-tests`. The first original-probe staging attempt
omitted the executable and exited 127; it is not counted as execution evidence.
The installed frontend/core, configuration, saves and ROMs were untouched.

Compare collected output using `difftest_fp.py` with
`--x87-output NATIVE_SEQUENCE_OUTPUT --original-output ORIGINAL_BODY_OUTPUT
--original-backend 'Linux i386 on physical AMD Ryzen 5 3400G'`.
Use `--log-only` with the focused input/output pair. This path requires exact
agreement and does not apply the Unicorn or Windows diagnostic allowances.

### Composed Loader, CPU And Machine — 2026-11-04

`tgpx4_loader.c` composes the recovered subdecoders using three original
operand/ALU/condition tables from the pinned executable. `tgpx4_device.c`
connects that loader, driver initialization, CPU dispatcher and external
memory ABI without Python dispatch at runtime. Initialization reads the native
program-source global `005aa87c`; the EDX token entering setup is the serializer
registration list, not the upload buffer.

Callback-entry ESP is explicit in the virtual register context. CALL, tail JMP,
wrapper saves and x87 stack alignment reproduce the original address-dependent
scratch values. Differential tests found and retained the extra PUSH ESI in
`004b53b0`. All wrapper/integer/control/transfer/FP dispatch and both scheduler
fixtures pass again with callback-entry ESP included. The full board-memory ABI
adds 2,048 original executions and 4,096 O0/O2 comparisons, including scratch
registers and flags, beyond the earlier memory-value tests.

The composed decoder adds 2,048 original cases and 4,096 comparisons. The new
mixed FP pipeline adds 64 programs, 7,168 original instructions and 14,336
instruction comparisons; it covers all six executable classes and all 16 ALU
selectors with exact power-of-two inputs. Numerical edge qualification remains
the separate native AMD suite. Re-running memory and FP programs through the
neutral C device passes 128 whole-program comparisons per group; those runs
compare final machine memory rather than claiming internal instruction traces.
Native initialization also passes 64 cases/128 comparisons across 18 game-name
configurations. These device reruns are not additional independent programs.

`port/m2/m2tgpx4.c` binds the recovered host callbacks to the existing i960 map,
FIFOs, shared memory and program/data uploads. The native biased shared read is
preserved: accesses outside actual allocations stop with a diagnostic, rather
than inventing mirrored/zero RAM. No completed sample has reached that boundary.
The native per-game driver configuration is retained. Top Skater command-table
overrides and M2C projection-center selection are now connected to the shared
renderer, as detailed below. The backend-specific applicability review is
recorded at the end of this document. Existing floating-point paths/compiler
flags remain unchanged.

The ROM-free `check-tgpx4-machine` fixture passes three reset cycles, halfword
and word uploads, FIFO echo/stall, shared-memory dirty tracking, data upload,
complete state replacement after device recreation, decoder-cache independence
from mutable program RAM, corrupt/truncated rejection without mutation, and a
maximum-size upload snapshot (11,919,304 bytes for the current TGX3 board archive).

```sh
make -C port TGPX4=1 BUILD=build-tgpx4-machine -j4 check-tgpx4-machine
make TGPX4=1 SHARC=1 BUILD=port/build-tgpx4-libretro -j4
python3 scripts/check-savestates-macos.py --tgpx4 \
  --core port/build-tgpx4-libretro/model2emuex_libretro.dylib \
  --rom /archive/overrev.zip --frames 1800 --output /new/audit-directory
```

Over Rev completes 1,800 headless frames, uploads 32,768 program bytes and
reaches a FIFO stall at decoded PC 547. Independent 1,800-frame macOS RetroArch
runs of Over Rev and Wave Runner render 3D attract scenes and exit cleanly.
The Over Rev GL/ABI state run passes cold save/load, four exact continuations,
context recreation, invalid-state rejection and an exact 12-frame continuation
in a fresh process. This is not all-game gameplay, audible-fidelity, cross-OS,
Windows-renderer equivalence or production-release acceptance.

Receipts remain ignored under `port/build-sharc-machine/model2c-*.json` and
`port/build-tgpx4-machine/`; reproducible tests are retained in `port/tgpx4/test`.
The initial address inventory is complete. The later integration, per-game
review and platform results below close the bounded M28 reconstruction group.

The real RetroArch state test also passes exact restored game-region pixels,
verified three-frame advancement on both paths, resumed scene advancement and
clean exit. Its first attempt restored exactly but waited on the frontend quit
confirmation; the accepted repeat disables confirmation only in the generated
test configuration. Both SHARC and TGPX4 machine fixtures pass in a combined
build, and the ordinary macOS build plus independent SHARC regression pass.
Ski Super G and Sega Water Ski each complete 1,800 headless frames with 32 KiB
program uploads; this is not evidence of gameplay or cleared startup checks.

### Per-Game I/O Review: Ski Super G

The 1,800-frame RetroArch sample reaches `DRIVE BOARD TROUBLE / CODE: FF`.
The original `FUN_004c9dc0` in `board/board_decomp.c` includes a motion-board
handshake after its input mapping: it consumes `00574cf0`, maintains phase and
countdown at `010f01b8/010f01bc`, and writes port-D input `005aa876`. Phases emit
CE, FF and eventually the command byte, with a ten-step delay and a consumed
command sentinel of FFFFFFFF. LLVM inspection of the pinned binary confirms
the handshake fragment at `004c9f19`, its branches through `004ca105..004ca15e`
and the return epilogues. The countdown advances only when a command is pending;
it is not a wall-clock or unconditional per-frame timer. A zero command starts
phase one with count 10, immediately decremented to 9. The FF command resets
the phase without independently clearing the countdown. Preserve these details
when integrating, rather than simplifying them to the SM2 stub.
The initial research binding had the output latch but omitted
that per-frame native sequence. This is separate from the recovered TGPX4 CPU.

Current SM2 `src/hw/model2c.cpp` uses a stationary-board acknowledgement stub
(CE for output command zero, FF otherwise). It is a useful reference for the
startup symptom, but does not justify replacing the original multi-step behavior.
The ElSemi handshake is now called after frontend input conversion before each
machine frame, selected by original input function 004c9dc0. SM2 control profiles
are unchanged. Native phase/countdown continuation is archived in TGX2, and
machine reset leaves these native globals intact; the game commands reset the
phase. No bypass or stationary-board stub has been added.

Sega Water Ski's separate 1,800-frame RetroArch sample renders its water-ski
attract scene and exits cleanly. Its native input identifier selects the same
recovered handshake, and its hook is a no-op, as reviewed below. Physical
controls remain outside this bounded check. All four existing Model 2C sets now have bounded attract evidence after the
Ski Super G handshake integration.

The handshake fragment is now recovered separately in `tgpx4_motion.c` and
passes **7,825 unchanged-original fragment executions / 15,650 O0/O2
comparisons**. The fixture covers every command byte, upper-byte/sentinel cases,
six phase values, countdown boundaries and a consecutive command sequence.
Receipt: `port/build-sharc-machine/model2c-motion.json`; reproduction:
`difftest_motion.py EXE MOTION_LIBRARY_O0 MOTION_LIBRARY_O2 --output RECEIPT`.
This does not add a full routine to the 286-address CPU/driver inventory. The
fragment comparison qualifies memory-visible continuation, not surrounding
analog conversion or the full function ABI. The machine fixture now verifies
command consumption, countdown/response continuation after device recreation
and state load, CE/FF/echo progression, and idle frames without countdown changes.
The 1,800-frame Ski Super G RetroArch repeat renders 3D attract. Its GL/ABI test
passes cold load, four exact replays, context recreation and fresh-process
continuation; the actual RetroArch test restores the same frame exactly, resumes
and exits cleanly. See VALIDATION.md for receipts.

### Expanded Native Catalog And Top Skater Geometry

All **13/13 native Model 2C records** are now represented by MAME-compatible
metadata (nine recovered additions). This measures native record coverage,
not every MAME revision or working game. The complete Libretro catalog has
70 sets. See MAME_ROMSET_ALIGNMENT.md for addresses and reproduction.

The three Top Skater records require ROM callback `004f77b0`. Its full-region
16-bit byte swap is recovered and integrated; 263 native executions / 526
portable comparisons pass, including guards and odd tails. The callback uses
the original loader's region base/size, not the stale per-record bounds.

STCC renders 3D attract in a bounded 1,800-frame macOS sample. Top Skater exits
normally after 1,800 frames but renders corrupt geometry. This is a failed visual
qualification, not a working-game claim. LLVM and the existing decompilation
identify the native special path:

- Driver initialization replaces object command `00573384` with `004bc040`,
  which sets `00dcec08 = 1` before entering the common object handler `004bb280`.
- `004ba010` fills the alternate 4x4 matrix at `010f0068` from twelve list words;
  `004b94a0` restores it from the primary matrix at `010f00a8` without consuming
  command arguments. Their prepass counterparts consume 12 and zero words.
- `004b9cb0` selects the alternate matrix using the low bit of a vertex's raw
  X word when `010ed95a` is set. This bit remains part of the coordinate bits.
- In special-object mode, `004bb400` omits the three normal words present in
  ordinary objects and derives normals from transformed vertices. Triangle
  records also omit the unused fourth-vertex words. The previous shared parser consumed the ordinary layout, a concrete native
  format mismatch.

The six control overrides now pass **1,536 original executions / 3,072 O0/O2
comparisons** in `difftest_geometry_control.py`. This checks memory-visible
control, stopping `004bc040` before its common-handler tail target; it does not
claim a complete renderer differential or increase the 286-address CPU inventory.

The special grammar and alternate matrix operations are integrated. Native
special normals use `(P0-P1) cross (P2-P1)` and reject positive dot products;
that winding is explicitly adapted to the shared rasterizer's face bit. Regular
objects and other boards retain their previous path and compiler FP flags.
The alternate matrix is archived only for actual M2C machines.

A second integration issue was isolated by the real frontend run: pipeline
renderer snapshots intentionally have no CPU binding, so reading the native flag
through that pointer always disabled the special grammar. The flag is now
copied into each pipeline slot alongside its display list, without sharing a
mutable CPU pointer. A two-slot fixture proves that a later frame cannot change
an earlier frame's flag. `check-tgpx4-geometry` also covers mixed compact
triangles/quads, ordinary records, both matrix banks, argument-free restore,
archived continuation and native face winding; ASan/UBSan checks pass.

The final 1,800-frame RetroArch sample renders the complete Top Skater attract
scene, including the floor and environment, and exits normally. Earlier corrupt
and partial-geometry images are retained as diagnosis, not accepted results.
See VALIDATION.md for state and frontend receipts. This does not establish
cross-backend pixel identity or complete gameplay/audio acceptance.

Additional hook review: Sega Water Ski's `004c7de0` is a native no-op. STCC's
`004c6990` sets an input-state latch; House Of The Dead's `004c6710` selects the
native SCSP processing mode. Dynamite Cop's `004c7fa0` installs distinct handlers
for the `01d8xxxx..01dfxxxx` region, now integrated as described below.
These hooks must not be treated as generic i960 idle-loop patches.

### Dynamite Cop Native Protection And Projection Selection

The six original protection handlers at `004c7330..004c75e0` are recovered in
`tgpx4_protection.c`. **67,120 original executions / 134,240 O0/O2 comparisons**
cover every 16-bit command, selectors, access widths, both response aliases,
unknown commands and retained response tails. Another **1,306 comparisons**
check the retained constants directly against the pinned executable. The test
normalizes physical i960 return widths, not scratch x86 flags or registers.

The real i960 map now installs these handlers on the eight pages selected by
Dynamite Cop's native hook. The original uses fixed responses, not SM2's hardware
decryptor. Byte reads return FF; dword reads deliberately return 0000FFFF;
byte/dword writes do nothing. Unknown word commands reset the cursor while
retaining the buffer. Reset installs the map without clearing these native
globals. The 256-byte response area ends at the separately referenced upload
variable 005aa870. Cursor, selector, toggle and response bytes are included in
the private TGX3 complete snapshot, with preflight validation.

Research boundary: the native command's selector arithmetic can address beyond
the 128-byte constant response table into unrelated executable globals and GUI
resources. The pure helper comparison uses the original mapped bytes and checks
that arithmetic. The machine binding currently maps the identified response
constants only; accesses outside recovered memory still fail explicitly.
It does not wrap/clamp selectors or pretend arbitrary executable data is a larger
protection table. No such access occurred in the accepted Dynamite Cop sample.
Broader gameplay may expose additional native-memory dependencies. The accepted
6,000-frame scripted-play continuation also encounters no such access; this is
bounded runtime evidence, not proof of all selector values in every game path.

Before this integration, 1,800- and 3,600-frame samples remained on the parental
advisory. With the native handlers, the 1,800-frame sample reaches the rendered
3D introduction. Complete state tests pass same/fresh-process continuation,
context recreation and malformed-state rejection. Real RetroArch Save/Load
restores the exact game region and resumes, with a clean exit. House Of The Dead
(`hotdo`) also has a separate accepted 1,800-frame 3D attract sample.

The common object handler has another native M2C contract at
`004bb30c..004bb326`: mode 3 selects the projection center from command bits 6–7,
while the other mode uses 29–30. Dispatch passes the full command in ECX and
shifts a separate EAX copy. This fragment passes **6,252 original executions /
12,504 O0/O2 comparisons**. The M2C binding and each pipeline snapshot now carry
the native mode, and the geometry fixture checks opposing low/high selectors
and isolation from subsequent frames. Existing other-board selection is retained.
This is command interpretation, not a change to shared floating-point flags or
a claim of complete D3D/OpenGL equivalence.

### Remaining Native Configuration Applicability

The review uses the pinned executable's actual reads, not just the names of
configuration globals. The existing upstream renderer remains the approved
destination; this group does not replace it with the Windows D3D backend.

| Native State Or Hook | Native Consumer | Destination Treatment |
|---|---|---|
| `010ed974` | Depth conversion at `00452fc0`; per-game D3D Z calculations | Retained in recovered driver state. No new GL depth policy: the existing upstream renderer sorts geometry and disables `GL_DEPTH_TEST`. |
| `010ed95c` | `004ba44f` controls D3D render state 22, Z enable | Retained in recovered state; no independent machine/CPU effect was found. Shared upstream rendering is preserved. |
| `00dcec58`, `005aeb90` | Native window/center setup at `004bacad` and `004baf6c` adds per-game offsets | Retained in driver state. The destination already derives offsets from CRTC H/V sync (`84 + hsync`, `130 + vsync`). Do not add Windows offsets on top without a separate renderer comparison. This is not a claim that the two presentation formulas are equivalent. |
| `010ed978` | Object handler `004bb30c` chooses command center bits | Integrated as actual display-list semantics, including pipeline snapshots; original fragment differential passes. |
| Top Skater command overrides / `010ed95a` | Special compact objects and alternate matrices | Integrated and qualified above; these affect parsing and geometry, not only D3D presentation. |
| Sega Water Ski `004c7de0` | Immediate return | No operation to add. Its `004c9dc0` input handshake is integrated. |
| STCC `004c6990` | Writes input-state latch `005aa8bc = 1` | Static direct references found only writes (also `004cb775`, `004cb873`, `004cec71`), not an emulation consumer. SM2 frontend gear/input profiles remain in use. No speculative machine effect is added; indirect consumers are not disproved by this search. |
| House Of The Dead `004c6710` | Sets `010ed99e`; dispatch at `004af7f0` / `004cc4e8` selects SCSP `004aead0` | The upstream SCSP already processes samples outside the 32-slot inner loop. No second scheduling mode or audio filter is introduced. This is a structural applicability check, not an audible/bit-exact equivalence test. |
| Dynamite Cop `004c7fa0` | Installs six protection handlers on eight i960 pages | Integrated with the original constants, access widths and state continuation; no SM2 decryptor substitution. |

### Completion And Qualification Boundary

M28's native CPU/driver recovery, board binding, applicable per-game hooks,
13-record catalog/frontend preparation, complete snapshots and representative
platform checks are complete. The final macOS Dynamite Cop test reaches actual
scripted play and the Continue screen after 6,000 frames, then passes four exact
same-process replays and a fresh-process continuation. Over Rev, Ski Super G,
Top Skater and Dynamite Cop have actual RetroArch state-restoration evidence.

The opt-in core also builds and renders on native Batocera x86-64 and in the
Windows 11 ARM VM (x86-64 application translation). All 70 destination input
bindings pass; all 13 M2C NVRAM routes pass 236 value cases. The separate shared
Sonic The Fighters conflict was subsequently corrected in M29 with the approved
native callback semantics; the unrestricted common suite now passes. See VALIDATION.md for hashes, receipts and exact test scopes.

This closes known reconstruction/integration tasks, not every possible game
path, physical control, audible-output comparison, or D3D/OpenGL pixel parity.
Unrecovered-memory accesses remain explicit failures. Wider gameplay/device
qualification stays in M14; publication stays in M16. The subsequent completion
group prepares explicit CI enablement and ROM-free machine/geometry gates. No
installed core or pristine standalone checkout was changed.

### Top Skater Same-Input Pre-Backend Geometry Comparison — 2026-11-04

The user requested the M2B-style renderer-integration check after the CPU/driver
qualification. The existing M2B capture hooks were reused in an isolated copy
of pinned ElSemi 1.1a on the Windows 11 ARM VMware guest. They capture the list
at `0x4baa60` and the four existing DrawPrimitiveUP call sites before D3D9
consumes vertices. A single native screenshot gate identifies the corresponding
completed geometry slot (gate 1795, slot 7). No batches were dropped. ROMs were
read directly from the existing `K:` archive; no ROMs were copied.

The first diagnostic preparation used Windows resource updating for an app-local
XAudio2 manifest and produced an invalid diagnostic PE, before emulation began.
The accepted second preparation keeps the original PE section layout and stores
the manifest in unused diagnostic-section bytes; it does not modify rendering
instructions. XAudio2 is activated through the local manifest without registry
writes. Exact pinned-original-to-probe byte changes and hashes are retained in
`original-probe-patch.json`. This is an instrumented original executable, not an
unmodified-file claim; original rendering algorithms remain unchanged.

A diagnostic copy of the current macOS release adapter replays that exact 512 KiB
list, its start offset, and seven captured video RAM banks into a shadow board at
OpenGL draw 1792. Existing native Model 2C flags and the normal upstream compiler
options are retained. The production adapter, renderer and installed core are
unchanged. The captured replay list matches the original input byte for byte.
The two isolated local runs complete 1,800 frames and exit normally.

| Spatial Correspondence Metric | Free-Running Core | Exact-List Replay |
|---|---:|---:|
| Original Interior Vertex Occurrences | 2,753 | 2,753 |
| Within 1 Pixel, No Position Adjustment | 1,115 | 2,753 |
| Within 1/16 Pixel, No Position Adjustment | 3 | 2,753 |
| Replay RMS Error | — | 0.0000184831 px |
| Replay Maximum Error | — | 0.0001012343 px |

The original submits 2,815 triangles; the replayed core submits 1,571, reflecting
separate clipping/tessellation boundaries. As in the accepted M2B comparison,
this is a screen-space nearest-neighbor check of original vertex occurrences
strictly inside the native 496x384 viewport, using vertex data collected before
the graphics backends. Repeated occurrences count separately. It does not prove
matching topology, UV/color attributes, sort order, border clipping, full
persistent geometrizer state or pixel identity. No pixel-equivalence gate was
reintroduced. The retained images are contextual evidence, not the pass metric.

The targeted M2C geometry-integration check passes without a production code
change. This closes the additional comparison requested by the user; general
M14 qualification and M16 distribution gates retain their previous scope.
Evidence: `port/build-m2c-geometry/comparison.json`, `capture.json`,
`probe-provenance.json`, original batch/list/video inputs, core meshes, isolated
run receipts and diagnostic sources. No commit, push, release or installed-core
replacement occurred.

Completion cleanup removed 32,097,408 bytes of task-owned generated binaries,
duplicate captures and unused geometry slots locally, retaining the selected
input/batch data, comparison meshes, screenshots, logs, source and exact PE patch
recipe. `port/build-m2c-geometry/cleanup.json` records hashes and reproduction
limits. The two task-owned Windows test directories were removed with the
standard runner after evidence retrieval. The canonical release-core SHA-256
remains `7d25037ff2e9e8053fee95a041aad4f0787f01f65f7c4f5f0e669ea3e94cb0b4`.

User-directed retention update, 2026-11-04: retain only results and reusable
verification tools for the Top Skater comparison. Raw captures, replay inputs
and generated test saves have now been removed; numerical results, contextual
images, logs, diagnostic source and the executable patch recipe remain. The
receipt is `port/build-m2c-geometry/results-tools-only-cleanup.json`. Repeating
the comparison requires a new acquisition; the previous retained-input rerun
is historical evidence, not a claim that those inputs remain available.
