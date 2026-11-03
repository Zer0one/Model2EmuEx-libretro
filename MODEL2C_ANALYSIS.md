# Native Model 2C Reconstruction Analysis

Updated: 2026-11-03. This is the requested static feasibility/inventory analysis,
tracked by M28 in [Roadmap](ROADMAP.md), not authorization or evidence of an
implemented Model 2C core. Existing Model 2B SHARC progress is independent.

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

These are evidence-backed candidates, not 286 independently verified routines,
a complete instruction inventory, or an effort estimate. The 22 exported bodies
still need ABI, pointer/global, flag and binary differential verification.
No Model 2C-specific portable implementation or runtime test was added.
There is therefore no implemented-recovery completion percentage to infer from
the fraction of available decompiler text. Additional indirect dependencies or
split function entries may change the denominator.

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
  current decoded program. Future Libretro integration should follow the
  already-approved M2A complete-snapshot policy, preserving the native callback
  and archiving/rebinding the additional program/cache/execution context.
  No payload capacity, format compatibility or working state load is claimed.
- **Catalog:** existing Model 2C frontend/catalog preparation does not mean the
  CPU executes. The current machine gate still rejects type 3; this analysis
  changes neither that gate nor ROM metadata.

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
premature before the first recovered group establishes handler complexity and
oracle reliability. The current analysis has no new semantic choice requiring
user intervention; it does not begin the implementation steps above.

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
Static counts are reproducible; execution and instruction fidelity are untested.
