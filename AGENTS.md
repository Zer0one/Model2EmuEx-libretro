# Model2EmuEx Libretro Workspace

## Scope And Repositories

- This is an independent repository on `main`, preserving Model2EmuEx history.
- `upstream` is `https://github.com/octavioCuatrochio/Model2EmuEx.git`; its source branch is `daytona_decomp`, not `main`.
- The pristine standalone checkout is `../Model2EmuEx`. Keep its files and user data untouched.
- Integrated baseline: `25d82be56f339c754cc566f771ca9ffb90b69289`.
- User authorization — 2026-11-02: first public GitHub repository, commit, push, release and repository-page update are authorized for this delivery. Target: `Zer0one/Model2EmuEx-libretro`, independent `main`, preserving native history. Subsequent publication needs its own authorization.
- Preserve unrelated changes. Never add ROMs, generated ROM-derived game code, saves or local audit outputs to Git.
- Read ROMs directly from their existing storage path wherever possible, including executions and tests. Creating ROM copies requires explicit user authorization before copying, even when a test would otherwise require a private copy. The user also authorizes removing existing local copies where possible, after verifying the archive originals are available and equivalent and preserving working paths. Never remove unique dumps, differing experimental ROMs or archive originals; ask when equivalence or ownership is uncertain. Coordinate cleanup through the Framework chat, which is already inventorying project duplicates; do not start a parallel cleanup from this directive. User directives — 2026-10-25.

## Active Implementation Priority

M27 reconstruction decision — 2026-11-03: preserve the existing upstream renderer and its normal compiler flags. A diagnostic ARM64 build with FP contraction disabled matched x86-64 geometry hashes, while SHARC/main-RAM fingerprints already matched; this is not proof of equivalence to the original Windows renderer. Track that comparison separately. The reconstruction used a distinct `SHARC=1` build. The subsequent request to close M2B and publish it authorizes `SHARC=1` in distribution CI after qualification. Ordinary local and standalone builds still require the explicit flag. Keep the configured local RetroArch installation separate.

M27 Save State decision — 2026-11-03: the user's subsequent instruction is to follow this port's existing Model 2A Save State conventions. This supersedes the immediately preceding selection to retain the original Windows session dependency. Reuse the recovered native SHARC CPU callbacks, adding the program/cache and execution context required for a complete snapshot and fresh-session load; preserve emulation behavior. The research SHARC archive uses 16 MiB and an explicit ABI feature bit, while Model 2/2A retain 12 MiB. No Windows state-file compatibility is implied.

Complete the applicable native Model2EmuEx selectors first, as originally requested; common SM2 feature work supplements them afterwards. Keep the complete native inventory and actual implementation status in NATIVE_OPTIONS.md. Inspect native source choices and defaults before exposing a control; do not let a shared-feature matrix hide or replace this starting point.

## Architecture And References

Follow SM2-Emu's independent-port model. Keep machine code frontend-neutral and the upstream layout intact. The adapter lives in `src/libretro`; the root Makefile builds it separately from `port/Makefile`. Prefer existing machine APIs over duplicated emulation. Preserve standalone/headless builds and compare against pristine upstream at the same revision.

Read the current shared references before adapting equivalent functionality:

- `../libretro-core-framework/FRAMEWORK.md` and `REFERENCE_SOURCES.md`.
- `../sm2-emu-libretro/Docs/UPSTREAM_PORTING_MANIFESTO.md`.
- SM2-Emu's current Core Options, input profiles and design documents.
- TGPulse and Supermodel's current implementation for the relevant subsystem when menu differences arise.

Use the complete SM2-Emu port as the implementation reference, including all control profiles, NVRAM engine/catalogue/templates, samples, tests, tools and documented compatible features. Start from existing implementations rather than rebuilding their analysis or acquisitions. Missing Model 2B/2C execution limits runtime verification, not preparation of applicable frontend code, profiles, options, metadata, NVRAM and ROM-free tests. Track imported, integrated, unit-tested and runtime-verified status separately. See SM2_APPLICABILITY.md and SM2_REFERENCE_INVENTORY.json.

The existing NVRAM workbook is a shared SEGA Model 2 reference, not an emulator-specific deliverable. Do not recreate or duplicate it for this port. Use current SM2-Emu source code as the primary authority for implemented fields, values, defaults, templates and behavior; the workbook may lag behind the source. M23 covers source-based integration/coverage review and existing-evidence indexing, not workbook production. Report concrete discrepancies and their impact; discuss target-specific semantic choices before changing behavior.

M23's completed source/registration review, template routes and existing-evidence index are in NVRAM_SOURCE_REVIEW.md. Its initial-template error-reporting omission was corrected immediately: preserve distinct disabled/unsupported, loaded and fatal template/layout results, with rejected content and frontend notification on errors as in SM2. Wider destination persistence qualification remains M11.

Before introducing any unapproved divergence from a known reference solution, involve the user: identify the reference behavior, explain why a different solution is proposed and its consequences, and wait for the user's decision. This includes omitted checks, simplified error handling, fallbacks and lifecycle changes, not only visible menu differences. Do not silently simplify an established solution. Previously approved choices remain authorized and do not require repeated confirmation.

SM2-Emu is the primary menu reference: category order, equivalent names/help, values, defaults, control conventions and lifecycle. Adapt actual Model2EmuEx capabilities. The user approved native emulator selectors in addition to common options such as Gamepad Rumble and NVRAM Settings; do not treat native-only selectors as a replacement for those shared contracts. Discuss genuine semantic differences with the user before implementing those choices; proceed autonomously on clear equivalents. Keep categories without implemented options absent. Show registered options for all games by default. Do not advertise missing capabilities or treat prototype-specific work as included without an explicit request.

ROM set metadata must follow MAME when it differs. The Libretro-only overlay uses canonical MAME names/parents/file identities; the standalone database stays upstream. `srallyp` is excluded from Libretro by explicit user decision. See MAME_ROMSET_ALIGNMENT.md and scripts/align-mame-romsets.py for pinned source provenance and checks. Do not rename or rewrite production ROM archives or saves as part of metadata alignment.

User decision — 2026-10-22: retain native standalone Save RAM compatibility. The current raw 64 KiB backup RAM plus 128-byte EEPROM buffer matches standalone Model2EmuEx DAT content; preserve its byte order and 65,664-byte size. Raw SRAM exposure is established in other cores, including Snes9x and Genesis Plus GX. Do not add the SM2 Libretro header, a new container checksum, migration or a format selector. Game-native layout/checksum validation and pending operator overrides are separate concerns. RetroArch owns save filenames/locations; no automatic native-file import is implied. Pre-release development persistence formats have no general backward-compatibility requirement, but the native standalone format is explicitly retained. Do not delete or rewrite existing user files as part of preparation.

Automatic initial NVRAM setup must use only the SM2 exact-template/explicit-compatible-parent policy. The native Daytona setup fallback is excluded by user decision as overlapping. Preserve frontend Save RAM precedence; leave the standalone helper unchanged.

Shared menu conventions must match SM2 whenever there is no concrete native emulator difference. Default-value labels and NVRAM visibility are required equivalents, not optional adaptations. The user retained the existing uncommented selectors; Pipeline requires help explaining its performance/latency tradeoff.

User-approved frontend choices: follow SM2-Emu / SEGA Model Core conventions wherever semantics match. Present genuine overlaps with the native emulator case by case before choosing a different contract. Aspect Ratio and Widescreen Mode are separate SM2-style controls, with the native 16:10 ratio added. Final scaling/fill belongs to RetroArch. By explicit user decision on 2026-10-21, every catalog entry retains its communication board in local loopback when Linked Cabinets is disabled, matching current SM2. The native program owns the enable bit; fitting alone does not add external-link support or change a native role. Native role selection remains independent. Native cooperative mode and its layouts are excluded for now. Do not expose separate keyboard controls or poll keyboard devices: frontend remapping owns keyboard use, and profiles use Libretro controller inputs.

A/V Timing follows SM2: 60 Hz default, destination-native 58 Hz optional, content reload required. Crosshair styles/defaults follow SM2; PNGs use system/model2emuex/crosshairs. Framework edition 0.1.42 is the fallback shared reference, including F09 single-view Up/Down aliases and F11 rumble output gating. See COMMON_FEATURES.md for integrated contracts and evidence.

Preserve native SCSP output: the user explicitly excluded SM2's additional 8 kHz output low-pass filter and its selector. Do not treat this as a pending integration. Previously approved source gains and A/V Timing remain in scope.

Hide Shot Flash and its selector are explicitly excluded by user decision. Do not treat this as pending or deferred integration.

The user treats this as a rolling project. Do not add Development or equivalent lifecycle qualifiers to the user-facing core name; display it as Sega - Model 2 (Model2EmuEx). Keep implementation/validation limits explicit in technical documentation.

Write project documents and UI labels in English, with Title Case for reader-facing labels. Keep technical identifiers unchanged. Record applicability, defaults, lifecycle and validation limits. Do not install dependencies without authorization.

## Verification And Deployment

See `LIBRETRO.md`, `LIBRETRO_DESIGN.md`, `VALIDATION.md` and `ROADMAP.md`.

- `make -j4`: native macOS core, no SDL runtime dependency.
- `make standalone -j4`: original standalone and headless targets.
- `scripts/check-macos.sh`: isolated Libretro harness versus same-revision pristine upstream.
- `scripts/run-retroarch-macos.py`: bounded real frontend run using a new isolated output directory.

Use `model2emuex_libretro.dylib` and its matching `.info` for all builds unless the user explicitly requests a development suffix. By explicit user request, a development copy and matching info are installed in the configured local RetroArch directories. Its core-specific Model2EmuEx.cfg selects gl; global Vulkan is unchanged. The scoped override and installed binary were frontend-tested in an isolated run. See LIBRETRO.md and the ignored local installation manifest. Do not infer authorization for releases or unrelated core/config changes. Keep configuration, NVRAM, states, screenshots and options isolated. Runners must own their processes and clean up only those processes. Distinguish ABI tests, frontend rendering, scripted input, physical controller behavior and audible output. No runtime claim follows from compilation alone.

## Save States

M12 uses frontend-neutral native serializers and Model2EmuEx format 1 in a fixed 12 MiB Libretro buffer. Preserve pointer rebinding, header/full-buffer integrity checks, payload preflight, rollback, GPU/audio/rumble recovery and current-option/NVRAM authority. Local loopback states for every set use a validated LNK1 extension in the reserved header and ABI feature bit 0x80000000; older zero-reserved headers are currently readable and the base payload layout is unchanged. Maintaining pre-release backward compatibility is not required by the user. External linked sessions remain non-serializable. Manx TT adds guarded AUD1 audio identity/header fields and feature bit 0x40000000, with appended I8251/AMS/SCSP-return/M1/mixer state and legacy reset/read support; see MANX_TT_CABINET_AUDIO.md. See SAVE_STATES.md. Do not claim SM2 state-file or cross-platform compatibility.

## Roadmap And Functional Groups

ROADMAP.md is the sole implementation roadmap. Follow the shared project presentation: legend, icon-only Status column, Activity and Remaining Work columns, rows grouped Completed/Partial/Not Started/Deferred. Keep project documents in English. Preserve stable activity IDs and distinguish imported code, integration, source tests, frontend execution and physical-device qualification. Option/applicability inventories are not competing roadmaps. The user permits grouping related reconstruction blocks at the agent's discretion (2026-11-02); summarize completed groups. Ask during work only for concrete semantic differences, and never commit or push without explicit authorization.

## Approved Sound CPU RAM Map — 2026-11-04

The user approved restoring ElSemi's 1 MiB linear SCSP-board CPU RAM map,
shared by A68K and Musashi. Keep SCSP sample addressing separate; do not
implicitly enlarge its current 0x7ffff mask. Save the complete CPU RAM and
reject incompatible old-map state payloads explicitly; no migration or user
save rewriting is authorized. The subsequent user decision adopts original
ElSemi/A68K word-swapped storage for the shared SCSP-board RAM, adapting
Musashi, SCSP samples/DMA and the MAME DSP accessors. Model 1 RAM is unchanged.
Do not add a big-endian-storage adapter to reconstructed A68K. See ROADMAP.md
and VALIDATION.md for current test status.


## Approved SCSP CPU Reads — 2026-11-04

The user selected original ElSemi CPU-facing SCSP read behavior shared by both
A68K and Musashi. Preserve recovered native quirks rather than treating each
upstream difference as a reason to change this preference. Discuss concrete
consequences such as unsafe memory accesses separately. Keep CPU callbacks
separate from chip-internal DMA/DSP access. The first slot/ring/DSP read group
is qualified; global/MIDI/IRQ behavior and A68K scratch binding remain open.
The user selected Astra with high effort for that coupled next RE block.


## Approved CPU DMA Behavior — 2026-11-04

The user confirmed ElSemi's SCSP CPU DMA behavior: writes to global registers
0x12–0x17 store the register values without updating internal DMA state,
transferring memory, clearing the start bit or asserting DMA IRQ. Apply this
shared CPU contract to Musashi and A68K, independently of DSP backend choice.
Keep chip-internal `w16`/`UpdateReg` DMA separate. Do not reintroduce the MAME
CPU-triggered transfer or a selector without another user decision. Native
write-completion scratch uses sparse-table index 2 for these registers.


## Approved SCSP Voice Sample Addressing — 2026-11-12

Both sound CPU backends use ElSemi key-on sample bases. Capture the 20-bit
address for 8-bit PCM and the 0x7fffe-masked address for 16-bit PCM. Voice
loads use the full 1 MiB sound RAM and stop content with an address diagnostic
on escape. This supersedes the earlier voice sample mask constraint. Keep the
chip-internal DMA and MAME DSP windows independent. Collect joint listening
and frontend checks in ROADMAP.md for the end of the integration scope.

The user approved ElSemi PCM interpolation in the shared voice engine.
The ordinary mixer uses one current sample and width-dependent history
refresh. The interleaved routine reads two adjacent samples in native order
and preserves history. Use the selected game hook for this distinction.
Retain the approved bounds check on each actual read.

The user approved all four ElSemi PCM loop modes, including the native
forward restart at loop start plus one. Check RAM bounds at the actual
sample fetch. Preserve the native direction flag and signed PCM history
across a Save State.

Both CPU paths use the ElSemi pitch calculation at key-on and after live
pitch writes, including 32-bit octave wrap and the 24-bit nearest-even
frequency table measured at sound initialization on Windows.

Both sound CPU paths use the ElSemi envelope. Preserve eight fractional
volume bits, active-only live rate updates and the quiet Decay 2 cutoff
before rate subtraction, including zero-rate voices. The user approved
reconstructing the PCM mixer path including SDIR, with separate verification
of the DSP input.

Both sound CPU paths use the live ElSemi IRQ autovector at 004b3090. Clear
the accepted request at interrupt entry. Re-evaluate pending sources on the
normal board events. The separate SCSP callback at 004aeac0 was installed
in the original context template after the live context had been copied.

Both sound CPU paths use the ElSemi pitch LFO saw waveform. The subsequent noise choice is recorded below.

Both sound CPU paths use the ElSemi LFO noise table and its adjacent-word
pitch gain at +128. Use the original CPU DSP write address decoding,
including width-dependent upper MADRS writes and the long MPRO/TEMP
crossing. Preserve each selected DSP backend's established Start policy.

## Observable ElSemi Process Addresses — 2026-11-12

Use repeatable 32-bit virtual addresses for original process allocations
observed by A68K. Keep the numeric value independent of the host pointer.
Preserve the actual x86 caller frame when its stack arithmetic contributes
to returned flags. Qualify the sound-board paths against the original image.

A 68000 store to 0x68c/0x68e can change the DSP RAM address. For the ElSemi
DSP, latch it at DSP Start. The user approved either mapped audio allocation
(the DSP's private RAM or the sound CPU/voice RAM), including a bounded
offset into the allocation. Stop on an unknown address at Start or an actual
access outside the selected MiB. Preserve both the pending and compiled
addresses across Save States. MAME retains its own DSP address calculation.

For PCM voice fetches the user approved both mapped audio RAMs. Apply a new
voice RAM base from 0x684/0x686 on the next fetch, preserving the key-on
offset and PCM history. Check the final word or byte against its allocation.
This applies to both CPU paths and both DSP selections.

## Approved SCSP Stereo Output

Both sound CPU backends use the final ElSemi SCSP mix. Saturate the stereo
sums to signed 16-bit PCM before applying the frontend SCSP Gain. The SCSP
master volume register remains accessible to the guest. The ordinary and
interleaved ElSemi output routines both omit the inherited quarter-scale/MVOL
stage. The original ordinary mixer is the measured Sega Rally reference.

## Approved ElSemi Audio Clock And Decoder Stall

The Model2Emu (ElSemi) profile uses the original fixed stream length at the native machine rate (760 stereo frames at 58 Hz). Convert to the frontend timing after synthesis. Preserve the Manx TT auxiliary board clock and the Model2EmuEx alternate profile cadence. An original DSB grouped joint-stereo decoder stall stops the content with a diagnostic identifying the stream position.

## Approved Original Script And Renderer Contracts — 2026-11-14

Use Lua 5.1.4 and the original same-interpreter reload. Run machine, Frame, rendering and PostDraw sequentially while a script is active. Preserve the stored Pipeline choice. Keep Lua session state alive on Load State. Resolve script fonts from scripts/assets with a notified built-in fallback. Texture manifests and converted GLSL mode shaders belong in textures. Include the two original mode conversions. The measured Windows D3D9 path blends adjacent mip levels. Unsupported 2x FSAA notifies and keeps the user's selection.


## Approved Input View Contract — 2026-11-15

Gun aiming follows the effective expansion of the last presented scene.
The renderer performs expansion, with native scene rules and Lua overrides.
Preserve last-image authority across Pipeline, skipped frames and PostDraw
changes. A new content load derives the first mapping from current scene
rules. Frontend resolution scaling does not scale the native aim columns.
