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

Use `model2emuex_dev_libretro.dylib` and its matching `.info` for development. By explicit user request, a development copy and matching info are installed in the configured local RetroArch directories. Its core-specific Model2EmuEx.cfg selects gl; global Vulkan is unchanged. The scoped override and installed binary were frontend-tested in an isolated run. See LIBRETRO.md and the ignored local installation manifest. Do not infer authorization for releases or unrelated core/config changes. Keep configuration, NVRAM, states, screenshots and options isolated. Runners must own their processes and clean up only those processes. Distinguish ABI tests, frontend rendering, scripted input, physical controller behavior and audible output. No runtime claim follows from compilation alone.

## Save States

M12 uses frontend-neutral native serializers and Model2EmuEx format 1 in a fixed 12 MiB Libretro buffer. Preserve pointer rebinding, header/full-buffer integrity checks, payload preflight, rollback, GPU/audio/rumble recovery and current-option/NVRAM authority. Local loopback states for every set use a validated LNK1 extension in the reserved header and ABI feature bit 0x80000000; older zero-reserved headers are currently readable and the base payload layout is unchanged. Maintaining pre-release backward compatibility is not required by the user. External linked sessions remain non-serializable. Manx TT adds guarded AUD1 audio identity/header fields and feature bit 0x40000000, with appended I8251/AMS/SCSP-return/M1/mixer state and legacy reset/read support; see MANX_TT_CABINET_AUDIO.md. See SAVE_STATES.md. Do not claim SM2 state-file or cross-platform compatibility.

## Roadmap And Functional Groups

ROADMAP.md is the sole implementation roadmap. Follow the shared project presentation: legend, icon-only Status column, Activity and Remaining Work columns, rows grouped Completed/Partial/Not Started/Deferred. Keep project documents in English. Preserve stable activity IDs and distinguish imported code, integration, source tests, frontend execution and physical-device qualification. Option/applicability inventories are not competing roadmaps. The user requests a stop and summary after each functional group; ask during work only for concrete semantic differences, and never commit or push without explicit authorization.
