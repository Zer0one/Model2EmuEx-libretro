# Original Emulator Reconstruction Inventory

Date: 2026-11-04. Original: ElSemi Model 2 Emulator 1.1a,
SHA-256 `2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc`.
Source baseline: public core v0.3.0 plus the documentation-only publication
receipt at `724eab3`. This is an evidence inventory, not another roadmap.
Activity M30 in [Roadmap](ROADMAP.md) owns follow-up work.

Current disposition — 2026-11-15: the eight ElSemi audio adoption groups are
closed. By user decision, the remaining Dynamite Cop protection-table and
TGPx4 shared-memory ownership/reachability questions are optional, deferred
research. Reopen only on new evidence reaching those paths. They do not block
delivery of the completed scope. Existing bounds checks, diagnostics and
qualification limits remain in effect. Dated findings below retain their
original evidence scope; they do not establish an active work queue.

## Scope And Interpretation

The completed M27/M28 inventories cover known SHARC/TGPx4 recovery targets;
they do not establish complete reconstruction of the entire Windows executable.
The current core deliberately inherits portable replacements and platform
adaptations. A difference is not automatically a bug or authorization to replace
an implementation. Preserve approved SM2 frontend behavior and Model2EmuEx
machine behavior until a concrete change is discussed.

The audit uses the pinned PE, inherited Ghidra exports, tracked portable
source, existing differential-test loader and LLVM. No ROM, Windows VM or
installed core is changed. The initial inventory only corrected a misleading
geometry-command `0x0d` comment. The subsequent targeted qualification below
also corrects inherited i960 NaN handling, after physical-x86 original-code
confirmation; it does not change the rendering or audio backends.

## Whole-Source Evidence Index

`tools/original_inventory.py` indexes every row of `src/functions.tsv`, matches
the inherited export headers, records portable address references and extracts
aligned code-pointer runs from the PE's actual `.rdata` and `.data` sections.
It handles named exception-handler headers as well as `FUN_*` names.

| Observation | Count | Meaning |
| --- | ---: | --- |
| Original Function-Export Rows | 2,048 | 2,041 non-thunks and seven thunks; all start in executable memory. |
| Rows With Portable Address References | 119 | Lookup leads in production source, including comments/constants; not verified recovery. |
| Rows Without Such References | 1,929 | Unclassified by this lexical index; not 1,929 missing functions. |
| Additional Addresses In Targeted Decompiles | 319 | Entries absent from the initial function list; not automatically distinct routines. |
| Aligned Code-Pointer Runs Of At Least 16 Entries | 13 | Physical runs, not necessarily semantic tables. |
| Pointer Targets Absent From Initial Function List | 408 | May include internal labels, shared tails or false positives. |

The index covers **100% of the inherited 2,048-row list**, not 100% of the
executable's indirect dispatch or semantics. It includes input hashes and
per-address evidence. Direct-call candidates only recognize `FUN_address(...)`;
named/imported/indirect calls remain outside that graph. Runtime/GUI/library
ownership must not be inferred from broad address ranges: the historical
README's ranges mix subsystems and omit indirectly reached entries.

No meaningful overall RE completion percentage can yet be assigned. In
particular, the A68K table below contributes 1,667 distinct code destinations
that are entirely absent from the original function list.

## Reviewed Subsystem Map

This table records source ownership and identified research boundaries. It is
not a claim that every instruction in a subsystem was compared this turn.

| Subsystem | Original Evidence | Current Core And Remaining Question |
| --- | --- | --- |
| i960 CPU | `i960/i960_decomp.c`, original opcode tables and `port/i960/test` | Recovered portable interpreter with inherited differential tools. Missing hardware opcodes also absent in ElSemi are not port-recovery tasks. No new missing block established here. |
| Model 2/2A TGP | `port/tgp` and original interpreter anchor `004a81c0` | Recovered native interpreter/table unit and board wiring. Historical README statements that B/C are absent are obsolete. |
| Model 2B SHARC | M27 address inventory and differential receipts | Known 208 targets recovered; completed M27 evidence remains valid. |
| Model 2C TGPx4 | M28 inventories, CPU/driver/per-game differential receipts | 286 initial targets plus 18 helpers recovered. The native-memory boundary audit below refines its explicit limits. |
| Audio 68000 | A68K initializer `00462ae0`, compressed dispatch at `00529024` | All 65,536 opcodes map to 1,667 classified dispatch targets. The reconstructed CPU runs both ElSemi boards. The direct-store caller stack, interrupt path and register callbacks have differential coverage. The standalone profile uses Musashi. |
| SCSP Synthesis And DSP | Original SCSP block and DSP generator `004aa040` | The ElSemi board has separate synthesis, exchange, timing and DSP evidence below. The standalone profile retains the upstream SCSP/DSP. The two-chip mixer has vector coverage; an activating title remains unidentified. |
| MultiPCM / YM2612 | Original MultiPCM entries `004b01b0..004b0cd0` and YM initialization `004b0b30` | The ElSemi profile uses the two reconstructed MultiPCM instances and the reconstructed YM2612. The alternate profile uses the standalone MultiPCM and ymfm. The native chip and board comparisons are recorded below. |
| Audio Board Wiring | Native setup `004ccbe0`, UART callbacks, `port/snd/QUIRKS.md` | The reconstructed board runs its own A68K and native callbacks. MIDI, timers, IRQs, PCM and the optional DSB are compared at machine boundaries. The Manx TT auxiliary cabinet uses its separate SM2 connection and clock. |
| Geometry And Tile Front End | Original parser `004baa60`, table `00573340`, targeted renderer exports | Recovered/adapted native paths. Existing geometry comparisons stay closed. Sorting, clipping and attributes need separate evidence before asserting full equivalence; command `0x0d` is not missing. |
| Rasterization And Textures | D3D9 code/pixel shader versus `port/m2/m2gl.c` | OpenGL atlas, filtering and tile precision differ by design. Audit actual original behavior before proposing corrections; do not reopen a cross-backend pixel-identity gate. Absence of microtextures in this port alone does not prove the original implemented them. |
| Board, Per-Game Hooks And I/O | Setup `004cd450`, driver tables, game records | Recovered machine bindings and approved current per-game hooks. Review indirect dependencies individually; frontend input profiles remain SM2-based. Historical standalone input omissions are not automatically current Libretro omissions. |
| Communication | Native receive/thread `004cf3d0` / `004cf740`, `m2link.c` | Native communication semantics with approved frontend Netpacket transport. Recreating Winsock or Windows threads is not required RE for this core. |
| Windows UI / Host Libraries | Win32, DirectInput/XInput, D3D9, CRT/STL, Lua, zlib/minizip | Platform/frontend services or library replacements, not automatically missing emulation. Classify their callers before excluding individual functions. Recreating the original GUI is outside current scope. |

Sources: `port/i960/QUIRKS.md`, `port/tgp/QUIRKS.md`, `port/m2/QUIRKS.md`,
`port/snd/QUIRKS.md`, `SHARC_RECONSTRUCTION.md`, `MODEL2C_ANALYSIS.md` and the
current adapter. The Audio Subsystem option binds one complete primary board at content load. Its default is the reconstructed ElSemi board.

## SCSP Chip And Bus Call Inventory

The ROM-free tool `tools/scsp_board_inventory.py` resolves direct calls, reviewed tail transfers and indirect tables in the pinned PE. It follows both conditional successors except at seven explicit board-type tests, where each walk follows its selected hardware. Unexpected indirect transfers fail the walk.
Each entry records reachable instruction count, transfer sites and targets
in the local receipt `port/build-a68k-board/standard-build/scsp-board-inventory.json`.

| Roots | Reachable Internal Entries | Portable Counterparts And Boundaries |
| --- | ---: | --- |
| Mixer dispatch `004af7f0` | 38 | Two mixer bodies, 32 ordinary voice handlers, the interleaved voice, envelope update, DSP step and dispatch itself. Compare with `port/snd/scsp.c` and `scsp_dsp_original.c`. DSP-generated execution is a separate program-dependent edge. |
| Chip initialization `004af2c0` | 2 | Chip and LFO initialization in `scsp.c`. Math, CRT allocation, clearing and random-number routines are recorded at the call boundary. |
| Six byte/word/long CPU read and write handlers | 19 | CPU handlers, global and slot updates, pitch, envelopes, LFO setup, DSP Start, generator and instruction decoding. See `scsp.c`, `scsp_dsp_original.c` and `port/a68k/scsp_bus.c`. |
| SCSP scheduler and both acknowledge entries | 5 | Board scheduling, timer service, IRQ selection and the live/template acknowledge callbacks. The A68K execution entry is linked to its existing dispatch inventory. |
| Board setup and installed callbacks | 14 | `004ccbe0` selects the SCSP map at `004cd0f9`. Six CPU-to-chip handlers, six empty program/bank write handlers and the live and template IRQ bindings are verified against the setup operands. Stream setup `004eecf0` supplies the buffer length. |
| i960 command and status | 7 | Installed byte/word/long ports and the command helper. The nonzero board-type branch feeds the input ring. The optional DSB receives a command through `004b2bc0`. A status read can decrement the host counter independently of the MIDI output queue. |
| Outer mix, scanline, reset and post-load | 45 | The machine's mix callback at `004cc4a0` directly selects the two mixer bodies. The frame loop calls `004cc710` at `004cc892`. Reset restores A68K vectors. Post-load calls the renderer invalidation path. |
| PCM buffer submission | 2 | Vtable slot +0x2c calls `004c8190`. It passes left then right PCM to `004eeba0`, each with twice the stereo-frame count in bytes. The helper waits for queue capacity if needed, copies bytes, advances the ring index and submits the buffer to the host voice. |
| Data producers outside the call walk | 6 | Mixer-mode setters, left/right PCM buffer and block-length setter, board binding and MIDI input/output helpers. Static presence of a setter alone does not establish an active caller. |

The expanded SCSP walk covers **94 distinct native entries** across nine root groups. Family counts overlap. All **27 indirect transfer sites** encountered have a table, a producing callback slot, or an identified boundary. Two vector-read fallbacks are conditional on an unbound page. The board installs direct RAM at page zero. Three host audio-object calls end at vtable offsets +0x00, +0x20 and +0x40. The block-length calculation on their caller's side remains in scope. Two Windows performance-counter calls profile the outer mix. The stream submission wrapper adds two profiling calls and six host queue operations. The generated DSP entry is covered separately by the microprogram probes.

The PE check binds seven machine vtable slots at `0051bbcc` to the constructor, frame loop, reset, sound-board setup, mix, buffer submission and post-load. The receipt records 21 callback-address operands separately from the call graph. The original registration fixture confirms a 1 MiB allocation and a 64 KiB archive member named `M2SCSP`. The reset, command and post-load probes were rerun with synthetic memory, including 48 host status reads through the two port aliases.

**Mixer data ownership.** The original board setup clears mode byte `010ed99e`. Game hook `004c6710` sets it to one. The recovered `hotdo` descriptor carries that hook address. Both mixer entry points read the same byte. Both routes have now been compared at the ring, DSP send and stereo return boundaries. Separately, twelve absolute operands read dual-chip byte `010ed9da` in the two mixers. The flag resides in the zero-filled tail of the PE data section. The twelve direct operands only compare it. The adjacent MIDI cursor stores at 010ed9d8/9 are byte-wide. A Unicorn write watch around the full chip initializer (`004af2c0`) preserved a sentinel of one and saw zero overlapping stores. Other computed stores or later configuration remain unproven. Keep the dual-chip branch in behavioral qualification. The receipt also lists the absolute references to both output pointers and the block length.

**Game setup coverage.** The native registration table at `010ed4b0` contains 67 records including the base system. Thirty have no setup hook at record offset +0x3c. The other 37 use 21 distinct targets. `tools/scsp_game_hook_probe.py` ran each target to return against bounded machine and i960 cache allocations, with the dual-chip flag initially zero and one and both settings of the configuration byte tested at `004c7e50`. Across 84 calls the watch saw zero overlapping writes. As a positive control, the House of the Dead setup wrote the separate interleaved-mode byte. This covers the setup hooks. Other callbacks, external configuration and guest-driven accesses are outside that measurement.

**Two-chip effect output.** In the original both mixers call DSP 0 then DSP 1 on each frame when the chip-count flag is set. With the flag clear they call only DSP 0. With stopped DSPs holding distinct effect returns, both routes added the enabled returns before signed stereo clipping. Sixteen vectors cover the disabled second return, cancellation and both saturation limits. The portable paired mixer reproduces these sixteen observations. Twelve additional native/portable cases compare active voices on both chips, distinct RAM and ring values, the two DSP buses and the final stereo sums. The secondary interleaved ring cursor does not advance. Both chips fetch voice PCM and modulation taps through the primary binding at 005728bc. The shipping game descriptors select a single chip.

**Voice source control.** The ordinary dispatch uses PCM for all four SSCTL values. In the interleaved routine the early return at `004548ce` mutes values 1–3 before touching the cursor, history or ring. The outer mixer continues advancing its ring cursor. `tools/scsp_mixer_block_compare.py` tested 32 selectors × four source values × two routes against the PE. The port now selects this SSCTL behavior from the native setup hook. Native and portable block comparisons also cover all 256 combinations. They compare output, cursor, activity, LFO phase, ring and DSP input.

**PCM fetch and cursor.** The ordinary handlers interpolate between slot history and the current sample using the low 12 cursor bits. The interleaved routine at `004548c0` reads two live samples. For bytes it reads the current and then the next logical byte, applying the lane swap to each. For words it reads the next word first. Its weight comes from the modulated byte offset (12 bits for bytes, 11 for words). It leaves slot history untouched and performs the two sign-control XORs in a 32-bit register. The ordinary handlers bypass the ring displacement and sign-control XORs. The interleaved loop-link check uses the incoming cursor. Reverse ping-pong at the lower endpoint changes direction on equality only in the ordinary route.

The production voice engine and x86 oracle agreed on 416 in-bounds cases. In 32 more vectors the second logical sample was beyond the selected MiB. The oracle traced the read against synthetic guard memory and the port reported the first escaped address, leaving the cursor and history intact. The 448 cases cover both widths, both routes, all loop and sign-control values, positive and negative ring displacement, fractional cursor and selected endpoint transitions. Ordinary dispatch additionally passed the existing 2,080-frame regression over its 32 targets.

### Second SCSP Activation In The Original Catalog

ElSemi 1.1a's type-4 ROM descriptor records write configuration words at
device offset `0x100 + 4 * index`. The loader uses the low byte of the index.
The machine constructor copies word 0 to machine offset `0x3c`. The audio
installer uses it to choose the Model 1-style or SCSP path. On the SCSP
path, word 1 at device offset `0x104` selects the optional DSB. The two
stereo stream calls request opposite pan positions for the output channels.
The shipped INI's `[Renderer] Sound` value becomes a boolean at host offset
`0x286` (`004f65b3`); the frame loop tests it before clocking the sound board
(`004cc887`). None of these selectors supplies the second-chip flag.

| Board Type | Digital Board | Original Records | Primary Audio Route |
| --- | --- | ---: | --- |
| 0 | None | 12, including the base system | Model 1-style for game records |
| 1 | None | 18 | SCSP |
| 2 | None | 24 | SCSP |
| 3 | None | 7 | SCSP |
| 3 | DSB type 1 | 3 (Sega Touring Car family) | SCSP plus DSB |
| 3 | DSB type 2 | 3 (Top Skater family) | SCSP plus DSB |

The initialized catalog snapshot contains zero in the chip-count byte.
`tools/scsp_board_activation_probe.py` reads every descriptor list from that
snapshot and runs the original board installer (`004ccbe0`) to return for
each SCSP configuration, once from zero and once with a diagnostic sentinel
of one. Across all ten calls the flag retained its entry value. The installer
bound voice RAM and private DSP RAM to chip 0, left both chip 1 bindings at
zero without writing either, and cleared the separate mixer-mode byte. The
two DSB configurations ran their native initialization. The fixture supplies
CRT allocation, thread-local storage and Windows stream construction.

Together with the original per-game hook check, this closes the catalog and
board-setup question for all 55 SCSP records. Keep one active SCSP for those
records and retain the qualified two-chip mixer for regression. An observed
later write by a particular title or external component would be new evidence.

### Other Sound Boards

| Walk | Distinct Native Entries | Indirect Sites Classified | Ownership |
| --- | ---: | ---: | --- |
| Model 1-style | 92 | 39/39 | The zero board-type branch installs the A68K map and hardware callbacks. Its scheduler services FM timers and the UART interrupt. The outer mixer calls the FM path and the two MultiPCM instances. The FM initialization installs timer and IRQ callbacks, and four operator slots dispatch through envelope-state pointers. The reconstructed board uses `a68k/model1_board.c`, `model1_bus.c` and the three `snd/*original.c` Model 1 components. The alternate profile retains the standalone chips. |
| DSB | 27 | 1/1 | The machine's optional-device field gates initialization, command delivery and the post-SCSP mix. Follow `004b2bc0` through the type-dependent command decoders, and `004b2d10` through the PCM mix and MPEG decoder. The decoder's four-way branch table is included. The ElSemi subsystem binds both the SCSP and the optional DSB. |

The three walks contain **194 unique native entry addresses**. The Model 1-style and SCSP walks share 19, including the machine reset and post-load entries. Run `tools/scsp_board_inventory.py` against the pinned executable with `--board scsp`, `--board model1` or `--board dsb`. Each receipt records roots, call sites, reachable entries, switch targets and external boundaries. Unknown indirect transfers abort the walk. Counts describe these roots and the reviewed branches. Whole-project behavioral coverage remains open. Original catalog and board setup are covered by the second-SCSP activation audit above. Stereo PCM submission is traced to the host voice.

## A68K Dispatch Recovery

Historical provenance now strongly identifies Mike Coates / Darren Olafson A68K.
The public Make68K 0.30 generator has an exact 65,536-entry / 1,667-target dispatch
partition correspondence with the original. Exact source revision and semantic
identity are not established; see AUDIO_RE_ANALYSIS.md and
`tools/a68k_provenance.py`. The original remains the behavior authority.


The original initializer expands runs of code offsets relative to `00462cd8`.
`tools/a68k_inventory.py` independently decodes that format, then executes the
unchanged initializer in Unicorn and compares every resulting pointer.

| Measurement | Result |
| --- | --- |
| Compressed Runs | 8,313 |
| Opcode Entries Compared | 65,536 / 65,536, exact |
| Distinct Executable Targets | 1,667 |
| Targets Already Named In `src/functions.tsv` | 0 |
| Packed Input | `00529024..00531215` |
| Expanded Table Start | `00531216` |
| Expanded Table SHA-256 | `8398b07505414aa655a011dc6cf96f0ef879a4a3ab432e48a1bf41cf541c3d20` |

This is one execution of the original initialization routine, with 65,536
pointer comparisons; it is **not 65,536 executed 68000 instructions**. Invalid
opcode handlers, shared tails and per-register variants are included. Before
estimating implementation effort, classify those targets into instruction
families and establish native context/interrupt/timing interfaces. Musashi is
unchanged. Reconstructing A68K would be new implementation work, not completion
of the already delivered M2C CPU.

## Model 2C Native-Memory Findings

### Dynamite Cop Protection Selector

Original handler `004c73d0`, arithmetic at `004c75a3`, reads a selector written
through a 16-bit game-facing port. For that reachable selector domain its copy
source is `00574d28 + floor(selector / 6) * 8`, and it copies 128 bytes.

- Selectors **0..5** use exactly the recovered 128-byte table.
- Selectors **6..65535** read at least partly beyond that table. Across the
  domain there are 10,923 source windows, spanning `00574d28..0058a2f7`, all
  file-backed in this PE's `.data` section. They are not additional ROM data.
- Ten representative original executions verify the boundary/source arithmetic
  and response bytes, including 5/6 and 65534/65535. All 65,536 selector values
  are separately enumerated arithmetically; they are not all executed.
- The core still exposes only the identified constants and fails explicitly
  on an unrecovered access. Existing accepted gameplay has not reached it.

The remaining question is actual game reachability and whether additional
observed windows contain immutable data or mutable native globals. Treating
all following bytes as one constant protection table would not establish that.
No enlarged table, clamp or fallback was introduced.

### Shared-Memory Read Bias And Allocation

The binary confirms allocation of **0x80000 bytes**: `004cd8a5` loads that size
into EAX before allocator `004fc340`; `004cd8b2` stores the result at board
offset `203874`; `004cdc35` binds it to global `005aa700`.

- Writer `004c5a70` accepts guest addresses `400000..7fffff`, but only
  `400000..41ffff` fit the allocation. Higher accepted writes also escape it.
- Reader `004c5a90` omits the writer's 16 MiB subtraction. Every read in
  `400000..7fffff` addresses byte offsets `1000000..1fffffc` beyond the buffer.
- Eight original executions verify below-window behavior, valid write edges
  and escaped read/write addresses against a deliberately bounded synthetic
  allocation. The resulting Unicorn faults do not prove that the real Windows
  process always faults: another allocation might occupy those addresses.

This is an original host-memory dependency, not evidence of missing 32 MiB of
emulated RAM. Resolving a real game failure would require observing the original
process's allocation and address ownership. The approved explicit failure
remains; no mirroring, zero filling or subtraction correction was added.

### Guest Reachability In The Reconstructed Model 2C Machine

The external-memory callbacks are installed by the common TGPx4 driver.
Ski Super G's game-specific input routine handles its motion cabinet. The
Dynamite Cop protection handler requires both a TGPx4 board and the matching
game hook. The USA Model 2C set for that test is `dynamcopc`.

| Set And Input | Selector Writes | Fixed Commands | Response Words Read | TGPx4 External ROM Reads | TGPx4 Shared-Window Reads / Writes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dynamite Cop, no input | 6, all zero | 6 | 54 | 0 | 0 / 0 |
| Dynamite Cop, scripted input | 4, all zero | 4 | 36 | 0 | 0 / 0 |
| Ski Super G, no input | — | — | — | 6,312,177 | 0 / 0 |
| Ski Super G, scripted input | — | — | — | 1,070,719 | 0 / 0 |

Each row covers 7,200 frames from cold boot in the headless machine. The
fixed response commands were `0x1326` and `0x7700`. No selector-dependent
copy ran. The shared-window counts concern the TGPx4 external callbacks
only; the i960 uses separate paths to buffer RAM. All four runs reached the
last frame with zero invalid i960 opcodes. No stage or ending was verified.

To repeat, build `port/Makefile`'s `m2run` with `TGPX4=1` in a fresh
build directory and `ZLIB_CFLAGS="-DM2_ROMSET_MAME -I../src/libretro/data"`.
Compile `tgpx4_execute.c`, `tgpx4_protection.c` and `tgpx4_host.c` with
Clang's `-fprofile-instr-generate -fcoverage-mapping` and link with
`-fprofile-instr-generate`. Run `m2run <set> 7200 <archive-directory>`
with a distinct `LLVM_PROFILE_FILE` per row. Use no inputs for the first run
of each set and this `M2_KEYS` value for the second:

```text
600:06:5,640:02:5,700:02:5,850:2c:15,1200:cd:40,1300:2d:15,2000:02:6,2100:2c:20,3600:06:5,3640:02:5
```

Merge each completed profile separately with `llvm-profdata`. Use
`llvm-cov export` for exact branch counts. For selector **values**, repeat
the two Dynamite Cop runs with a diagnostic print of `value` in the selector
store branch of `m2_tgpx4_protection_write`. The two repeats reproduced the
same final frame counters as their coverage runs.

### Ski Super G External Read Sites

The same 36 decoded TGPx4 record indices issued all external ROM reads in
both 7,200-frame runs. The indices range from `0801` to `0968`. The counter
uses the current decoded record relative to its program base, including the
record selected during delayed execution. Indices are relative to the upload.

| Input | Reads | Lowest ROM Word | Highest ROM Word | Shared-Window Reads / Writes |
| --- | ---: | ---: | ---: | ---: |
| No input | 6,312,177 | `05bcb3` | `176821` | 0 / 0 |
| Scripted | 1,070,719 | `07215a` | `176821` | 0 / 0 |

These are word indices in the 8 MiB coprocessor data region. Both ranges fit
its 2,097,152 words. No stage, other upload or alternate guest input path
is implied by these counts.

For a headless diagnostic build, compile `tgpx4_execute.c` with the symbol
rename in `port/tgpx4/test/observe_board_reads.c`, compile that observer as
a separate object, and link it into the MAME-catalog `m2run` described above.
Use the same cold boots and input schedule. The observer delegates every call
and reports per-index read counts, minimum and maximum ROM words and total
shared-window traffic at normal exit. The production build does not link it.

### Dynamite Cop USA Command Callers

The four MAME `maincpu` chips for `dynamcopc` form a 2 MiB i960 program.
`tools/dynamcopc_protection_calls.py <archive>` checks their sizes, CRCs,
interleaving and assembled SHA-256, then checks direct references across
the image without writing the program to disk.

| Direct Call Site | Command | Length Argument | Selector Argument |
| --- | --- | ---: | ---: |
| `00067224` | `1326` | 20 | 0 |
| `000672d8` | `7700` | 20 | 0 |

Both call the same guest routine at `000b67b0`. It writes half the low
16 bits of the selector argument (zero for both callers), then submits the
command. Each call reads one initial response word and eight further words
for length 20. The expected nine reads per call account for all 54 and 36
response reads in the two independent machine traces.

The scan found one directly addressed word store each to the selector and
command ports, both inside this routine. The aligned relative branch/call
scan found only the two callers entering the routine from outside. It also
checked aligned pointer literals and absolute and ElSemi-style i960
IP-relative address forms. Register-computed addresses and executable code
outside this main program are outside the scan. The two identified callers
cannot expose additional response data at any stage.

### Geometry Command 0x0d

Original dispatch table `00573340[13]` points to `004b95a0`. Its entire body is
`add dword ptr [01003018], 8; ret`: it skips two words. Three original executions
verify pointer advancement, including wraparound. The existing port performs
the same skip for normal in-range lists. Removed only the misleading
“unsupported” comment; malformed-list handling is not claimed identical.

## Reproduction And Retained Evidence

```sh
mkdir -p port/build-re-inventory
python3 tools/original_inventory.py port/build-sharc/original/EMULATOR.EXE \
  --output port/build-re-inventory/original-inventory.json
port/build-sharc/venv/bin/python tools/check_original_boundaries.py \
  port/build-sharc/original/EMULATOR.EXE \
  --output port/build-re-inventory/original-boundaries.json
port/build-sharc/venv/bin/python tools/a68k_inventory.py \
  port/build-sharc/original/EMULATOR.EXE --verify-original \
  --output port/build-re-inventory/a68k-inventory.json
```

The existing Unicorn environment is reused. Its JIT required the authorized
outside-sandbox execution; the first sandbox attempt ended before producing
a result. All accepted runs completed. Retain the tools, JSON results and
small relevant disassemblies; there are no raw RAM dumps, ROM copies or test
saves. Source indexing is deterministic; reject a nonmatching executable hash.
The initial comment-only edit needed no rebuild/runtime regression. Subsequent
i960 changes have their own build and execution evidence below.

## Inherited Model 2/2A Follow-Up

[Inherited Model 2/2A Qualification](M2A_RE_QUALIFICATION.md) reproduces the
upstream CPU/driver suites and records all excluded cases and oracle limits.
It confirms and corrects a portable i960 NaN-selection mismatch using unchanged
PE routines on physical AMD; 16,317 targeted raw-result vectors now match on
ARM64 and native x86-64. Additional Model 2/2A map/FIFO/shared-memory and
fresh-machine state fixtures pass, including with M2B/M2C enabled. This scoped
group is complete, without claiming whole-interpreter native equivalence or
reopening all-game/rendering campaigns.

## Audio Classification Follow-Up

[Original Audio Reconstruction Boundaries](AUDIO_RE_ANALYSIS.md) indexes all
65,536 A68K encodings across 1,667 targets: 1,635 single-label and 32 mixed-label
targets, with 120 label categories including pseudo-ops/traps. These labels are
not recovered handler semantics. Forty native MOVEQ alias pairs (80 executions)
confirm that the original ignores bit 8 where Musashi's MOVEQ table requires it
clear; actual sound-program reachability is not established.

The SCSP decoder matches the reviewed 25-field map in 642 original executions.
Six start cases recover the program-length boundary, and 69 synthetic programs
exercise the original generator with only allocator imports replaced. This
makes original generated-code capture reproducible on macOS without a Windows
application. The subsequent execution group compares original generated x86
with the unchanged portable DSP: all 1,020 arithmetic/shift/writeback cases
match at O0 and O2. This uses Unicorn and synthetic state, not native Windows
execution or game audio. No audio backend was changed.

The subsequent test-only C reconstruction now matches 1,439 native-code cases
at O0/O2/UBSan, including bounded RAM, scratch continuity and compile-time
lookahead. The unchanged MAME-derived loop differs in 359 cases; those are not
automatically original-code defects. The user requests eventual recovered-DSP
use, preserving ElSemi first; any original-code correction is a separate,
explicitly discussed activity. Next: integration boundaries (mixer units, RAM,
program cache, Save States), then PCM/frontend verification. A68K ABI and wider
audio interfaces remain separate. Astra with High effort remains appropriate.

## Recovered DSP Integration Preparation

The reusable native DSP module retains all 1,439 differential results. It owns
ElSemi's private 1 MiB delay memory, preserves the compiled program separately
from writable MPRO and passes module-level cold Save State continuation and
invalid-state preflight under ASan/UBSan. Native mixer input/output fragments
match in 18,432 synthetic cases. Eight native register-write probes identify
the BFE start event. See AUDIO_RE_ANALYSIS.md for provenance and limits.

The original can read beyond its allocation for synthetic RBP/MADRS values;
game reachability is unknown. The user approved explicit diagnostics/content
stop. Working SCSP/Libretro/standalone integration builds and ROM-free sound
checks pass. VF2/Indy 500/Top Skater state capacity, exact PCM/state/image
continuation and fresh-process restore now pass. Real RetroArch VF2 Save/Load
restores the exact advancing scene and exits cleanly. The synthetic adapter
fault test proves address notification and content stop. This completes the
bounded local integration group, with no installed-core replacement. Original Save State disassembly and synthetic
registration/load audit show that `M2SCSP` covers only 64 KiB of the 1 MiB sound
RAM; separate DSP context/private RAM are not serialized. The CPU callbacks
and graphics post-load hook do not recover those fields. See AUDIO_RE_ANALYSIS.md
and `tools/scsp_dsp_state_audit.py`. This does not establish game reachability
or a native recovery policy for escaped DSP accesses.

## Library Sources As Reconstruction References — 2026-11-04

User direction: use identified library sources to recover meaningful structure,
names and comments, preserving ElSemi's changes and treating the pinned binary
as the final authority. Distinguish source identification from semantic proof.

| Component | Evidence | Reconstruction Use And Limit |
| --- | --- | --- |
| A68K | Coates/Olafson Make68K 0.30; exact original dispatch partition match. | Use generator function names and comments to guide recovered handlers; compare each native body. Exact revision/configuration and later fixes remain distinct. |
| zlib / minizip | Original EXE embeds deflate/inflate 1.2.2 and zip/unzip 0.22 author/version strings. | Use matching historical source to classify compression/archive functions when needed. Strings alone do not prove unmodified code. No reason to replace working platform services. |
| Lua | Original EXE embeds Lua 5.1.4 authorship/version signature. | Use that version's source to identify VM/runtime scaffolding and distinguish ElSemi bindings. No Lua replacement is part of A68K. |
| SCSP | [Public source](https://github.com/mamedev/mame/blob/cd2063a575195fd79d887069f8b70852bba35899/src/devices/sound/scsp.cpp) credits ElSemi, with MAME/M1 conversion and later contributions. | Direct source lineage is useful for slots/envelopes/timers, but public changes must be compared with the original. This is not evidence that the Windows core imported current MAME. |
| MultiPCM | [Public source](https://github.com/mamedev/mame/blob/d65391dcfab3d372887ad865521ffc76a8081956/src/devices/sound/multipcm.cpp) expressly credits ElSemi for Model 2 Emulator and MAME. | Use historical structure and names where native routines corroborate them; current source semantics are not automatically the original. |
| YM2612 and other replacement components | Current port replacements alone establish no provenance for the Windows binary. | Leave authorship/revision unassigned until documentary or native-code evidence identifies them. |

Local receipt `port/build-a68k-provenance/library-identities.json` retains exact
embedded strings, file offsets, original hash and pinned source references.
No emulation behavior, backend choice or installed core changed in this review.

## Digital Sound Board Command And PCM Boundary

The native machine descriptor at offset 0x104 selects the optional digital sound board. The Sega Touring Car family uses type 1 and Top Skater uses type 2. Their program and MPEG regions are 7 and 8. Six registered sets have these board attachments. The board receives i960 command bytes alongside the SCSP. Its update at `004b2d10` mixes decoded music into the stereo buffers after the SCSP.

`tools/dsb_board_compare.py` runs both native command parsers and the original MPEG decode/mix against existing archives. The warm machine reset preserves the pending packet and ongoing track. Both native cases and a portable fresh-instance comparison are recorded under [Digital Music Track Boundaries](VALIDATION.md#digital-music-track-boundaries). Track 1 starts with AF 6F 01 (Sega Touring Car) or AE 10 01 (Top Skater). Both produce 32 kHz, 1,152-sample MPEG frames. The witness retains a digest for 12,160 output stereo frames per board and checks the stop command. Sega Touring Car also sends its play sequence during the captured machine run. Primary SCSP PCM qualification does not include this music. The portable optional board and its lifecycle require independent qualification.

The 1,010-frame Sega Touring Car replay feeds the captured i960 stream to the original digital board. Play starts at scanline 198301 and stops at 201706. At game frame 946, sample 327, the primary stereo pair is (0, 0) and the combined output is (-1, 0). The additional board changes 11,837 stereo frames in that capture. This test holds the primary PCM and block lengths fixed.

The portable packet parser, track tables, segment changes and decoded-sample mixer live in `port/snd/dsb_original.c`. They were first qualified by `tools/dsb_exchange_compare.py` in isolation. The synthetic x86 comparison covers 81 input bytes, eight segment transitions and 192 decoded-PCM cases, including silence, channel selection, boundary positions and integer phase carry. The subsequent runtime binding and saved synthesis history are described below. The SM2 MPEG decoder has distinct header handling and synthesis code. Its presence in another project does not establish equivalence to these routines.

A second comparison supplies the same original x86 MPEG decoder to the portable board controller and the original board. Each reproduces 27,360 stereo frames on both parent titles through play, stop, silence and restart. Each decoder refills 17 times. This isolates the board exchange from the decoder. The portable frame-header logic also matches the x86 header path in 1,540 cases across MPEG-1 layers I–III, rates, modes, CRC and padding, with invalid sync, version and rate included. Reserved layer bits remain outside that header equivalence claim.

The recovered synthesis filter at `004e9a70` and its initializer at `004e9de0` match the pinned image at CW 007f on macOS ARM64: all 2,048 cosine entries, 6,144 history values and 3,072 signed PCM samples across 96 blocks. The original DSB joint-stereo decoder can stall in `004ea870` when a grouped allocation lies above the joint boundary. A bounded synthetic vector reached index 0 then repeatedly index 1. This is a native behavior difference from a standards-based decoder. No game-data occurrence was demonstrated.

### DSB Decoder And Runtime Binding

The ElSemi subsystem loads the existing region 7/8 bindings. Its command port, segment controller, Layer I and II decoders, synthesis filter and post-SCSP mixer are implemented in `port/snd/dsb_*.c`. Layer III and the reserved layer take the original no-decode branch and retain PCM. The reserved layer reads the adjacent table words and uses wrapping signed frame-size arithmetic. Rejected headers keep the previous output binding. A rejected Layer II allocation table keeps the compressed position, the output rate and the decoded history. Unknown addresses and the native shared-band stall return a diagnostic at the frontend boundary.

The pinned executable and the portable decoder agree on 2,052 header cases, 16 Layer I frames and 64 Layer II frames covering all four allocation tables, channel modes, scale selectors and the unmatched 4195 entry. The PCM digest of the Layer II matrix is `e7414f62e00ecab5aa5b59b8ccd808e4643d4580fa450c70d53e029e732b17ca`. On each retail board, 17 consecutive or restarted refills agree independently at the decoded output and across 27,360 mixed stereo frames. For Top Skater the combined digest is `a6e5ddd7ae242f62c868e8660cda24e6e52db0129f5a9dfe2e7e15873065a0ac` over 1,010 machine frames (767,948 stereo samples). For Sega Touring Car, the first 1,010 machine frames from the integrated core have the original combined PCM digest `73f530b3ea677d50826603b94bab8c08d4720e986a5fc5a774955059c5c28b86` at matched cadence. A native reference is supplied by `tools/dsb_board_compare.py`; decoder and controller vectors are in `tools/dsb_exchange_compare.py`.

## Model 1-Style Audio Reconstruction

The original board installs a 32-byte command FIFO, a 64 KiB working RAM, two MultiPCM chips and a YM2612. The 68000 receives IRQ 2 after the tenth 79-cycle dispatch in a scanline when commands remain. The FM timers advance 67 clocks after each dispatch. The FM data port can render ten samples before a register write, including writes to the DAC sample but excluding the DAC enable. At the frame boundary, the original completes FM, adds the first MultiPCM and clips, then adds the second and clips again.

The two MultiPCM instances reproduce 1,186 register writes and 1,449 stereo frames with 28 active voices per chip on synthetic ROMs. Each comparison checks all 13,392 bytes of chip state. Tests include latched bank selection, the eight-bit sample selector and the slot selector alias that overlaps the final decoded descriptors. The synthesis tables use the original initialization at 44.1 kHz.

The original YM2612 shares Tatsuyuki Satoh’s historical FM structure. Detune is applied before the multiplier, as in the historic MAME 0.37b12/b14 source. At the original startup precision, all 256 detune entries and 8,193 envelope entries match the historical source compiled on macOS. The frequency table differs at 153 entries, attack at four, decay at two and total level at 1,548. Replacing only the level table in the source comparison removes the four differing channel values from the eight-algorithm witness. The portable chip uses the original tables. Its 522 register writes, 560 timer advances and 16,601 stereo frames match the pinned executable. A separate exhaustive measurement covers all 1,024 timer A and 256 timer B periods.

For the combined board test, the native sound CPU runs the game program directly from its archive. The portable board receives its MultiPCM register/bank writes, FM address/data writes and timer ticks. Daytona agrees for 133,000 stereo frames, including 64,437 nonzero frames. Virtua Cop agrees for 98,800, including 32,253 nonzero frames. The input commands in these tests are synthetic MIDI sequences. The comparison covers chip interconnection and output timing. Portable sound CPU callbacks and the complete runtime binding have separate qualification.


The independent CPU comparison in `tools/model1_cpu_compare.py` runs both sound CPUs, checks all 33 context words after each scanline and all 64 KiB of RAM after each frame, and compares the final stereo output. Daytona and Virtua Cop matched for 64,050 scanlines combined. Warm reset during playback matched through a further 37,800 scanlines in Daytona. The machine test in `tools/model1_game_audio_compare.py` replays actual i960 command timestamps from the integrated core. Daytona, Virtua Cop and Desert Tank match in all accepted interrupts and 2,281,034 stereo frames at the adapter cadence. The active FM comparison includes 4,618 writes, 2,608 ticks and 28,332 stereo frames. The repeated timer B callback compares the single-precision intermediate before integer conversion. TB=250 demonstrates the distinction even when successive integer periods agree.
