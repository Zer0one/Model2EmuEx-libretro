# Native Emulator Selectors

Priority: complete the applicable native Model2EmuEx selectors before adding the common SM2 feature set. SM2 remains the reference for shared frontend conventions; it does not replace these native controls.

Source of truth: `port/sdl/options.h`, `m2opt_defaults()` in `options.c`, and Configuration controls in `launcher.cpp`. Status below describes the current destination implementation, not a promise that pending switches are already functional.

| Native Control | Source Choices / Default | Destination Status |
| --- | --- | --- |
| Render Resolution | Auto (default), 1x–4x | Internal Resolution implements 1x–4x, default 1x. User approved final scaling/fill in RetroArch; source Auto depends on SDL window dimensions and is delegated to the frontend. |
| Texture Filter | Nearest (default), Bilinear, Trilinear | Implemented as 3D Texture Filtering. |
| Shadows And Fences | Blend (50% See-Through, default), Checker (As The Hardware) | Implemented. The initial core's implicit Checker value was corrected to the actual native Blend default. |
| Saturation | 0.50–2.00; default 1.00 | Implemented in 0.05 steps; applies without a machine reset. |
| Gamma (Red) | 0.50–2.00; default 1.00 | Implemented in 0.05 steps using native tile/colour-table generation. |
| Gamma (Green) | Same | Implemented independently. |
| Gamma (Blue) | Same | Implemented independently. |
| Keyboard Shifter | H-Pattern (default), Sequential | Excluded by user decision: no separate keyboard input support. Use common Libretro control profiles and frontend remapping. |
| Hold Gears | Disabled (default), Enabled | Excluded with separate keyboard input support. |
| Widescreen | Default (default), Off (4:3), 16:9, 16:10, Fill The Window | Implemented through separate SM2-style Aspect Ratio and Widescreen Mode controls by user decision. Aspect Ratio adds native 16:10; expansion uses native per-game geometry/layer rules. Fill is managed by RetroArch. |
| Picture Shape | Keep (Bands, default), Stretch, Crop | Final image scaling/cropping belongs to RetroArch. Cooperative split-screen is excluded for now. |
| Pipeline | Enabled (default) / Disabled | Implemented using native capture/replay and a joined worker. One-frame video latency when enabled. |
| Frame Skip | Enabled (default) / Disabled | Implemented using frontend audio-buffer underrun notifications, with at most two consecutive drawing skips. Machine/input/audio continue. No skips without frontend notifications. |
| Linked Play | Disabled (default) / Enabled | Excluded for now by user decision. |
| Linked Play Layout | Side By Side (default), One Above The Other | Excluded with cooperative mode. |
| Scaling Filter | Smooth (default), Sharp | The source scales its completed frame to its own window. Final scaling belongs to RetroArch; avoid exposing a nonfunctional duplicate when the core renders directly at the selected internal size. |
| Frame Cap | Enabled (default) / Disabled | Frontend pacing / fast-forward responsibility. The core does not run a second host throttling loop. |
| VSync | Disabled (source default) / Enabled | Frontend presentation responsibility; no standalone swap interval in the core. |
| Fullscreen / Window Size | Windowed / Automatic source defaults | Frontend window ownership. |
| ROM Folder / Save Folder | Source paths | Use content/system and frontend save directories. Do not read standalone INI paths as core-owned global configuration. |

The last five rows remain native settings in the source inventory; assigning their behavior to the frontend is an explicit adaptation, not silently dropping them. Applicable native execution/presentation controls are integrated; common SM2 functionality follows.

## Implementation And Checks

The core registers eleven rendering options in both V2 and legacy APIs: resolution, texture filter, Aspect Ratio, Widescreen Mode, pipeline, frame skip, mesh treatment, saturation and three gamma channels. Separate keyboard selectors and direct keyboard polling were removed by user instruction. The subsequent Input and Audio categories now contain delivered SM2-style common options; see COMMON_FEATURES.md.

Aspect Ratio values are Auto (default), 4:3, 16:9 and 16:10. Widescreen Mode values are Disabled (default) and Expand 3D View Only, using the same tokens as SM2. Disabled keeps native rendering width and reports the chosen display aspect to the frontend. Enabled expands to 662 columns at 16:9 or 596 at 16:10; Auto selects 16:9, and explicit 4:3 suppresses expansion. Native per-game geometry and layer rules remain authoritative; unsupported game rules are not replaced with a new widescreen algorithm. All changes apply on Resume without reset.

Colour changes rebuild native derived tile/palette tables and invalidate the GL colour/luma uploads without resetting the machine. Gamma settings survive machine reset, renderer recreation and subsequent content loads through the normal frontend option reads. No colour transform is added to machine RAM or sound synthesis. The imported machine and renderer sources remain unchanged.

Validation (2026-10-20): native-default VF2 RAM/PCM remain exact to pristine upstream at 900 frames. Independent 1800-frame runs show changed rendered images for saturation and each gamma channel while RAM/PCM match across variants. Blend/Checker selection is checked against the actual meshblend uniform submitted to GL; the chosen VF2 scene did not show a pixel difference and is not claimed as visual proof of native mesh polygons. Live option changes, invalid-colour fallback, reset, GL recreation and reload pass the harness. The historical separate keyboard settings were subsequently removed by user decision; frontend keyboard remapping remains available.

Validation update: `audit/sm2-video-style-vf2` passes actual OpenGL rendering, all aspect/expansion combinations, invalid-value fallback, bounded frame skips, reset/context recreation and reload. The harness rejects direct keyboard polling. At 900 frames, with identical SM2-seeded initial NVRAM supplied to both runners, VF2 RAM and PCM match pristine upstream exactly. This is harness evidence, not a claim of physical-controller or audible-output testing.

## Unified Upstream And Original Option Review — 2026-11-14

This inventory covers user-facing settings and operational menu commands. Upstream means the pristine Model2EmuEx checkout at `25d82be56f339c754cc566f771ca9ffb90b69289`. Original means ElSemi Model 2 Emulator 1.1a. Common entries occur in the upstream section once; the second section adds original controls or original-specific semantics absent from the upstream configuration interface. Original controls also shared with upstream include Bilinear/Trilinear, MeshTransparency, GammaR/G/B, WideScreenWindow, HoldGears, ROM directories and frame/window management.

**Integrated** includes an explicit RetroArch-owned equivalent, identified in the status. Partial equivalence is stated individually. **Excluded** records an existing user decision, frontend ownership, or a documented empty menu. **To Evaluate** records an unimplemented original control requiring review. **Selected For Integration** records the user-approved scope awaiting implementation. **Selected For Behavior Review** records an investigation preceding a frontend decision.

The original menu has been read directly from PE resource type 4, menu 101. The shipped INI, README, Lua documentation and game scripts have been read directly from the existing local archive. The original menu resource supplies menu labels; it does not prove the behavior of undocumented INI keys.

### Upstream Controls

| Option And Description | Provenance | Status And RetroArch Mapping |
| --- | --- | --- |
| Render Resolution — internal 3D resolution, Auto or 1x–4x | Upstream | Integrated — Internal Resolution 1x–4x. Window-dependent Auto is excluded from the core under the approved RetroArch scaling policy. |
| Texture Filter — Nearest, Bilinear, Trilinear | Upstream | Integrated — 3D Texture Filtering. |
| Shadows And Fences — blended or checkerboard transparency | Upstream | Integrated — native Blend/Checker choices. |
| Saturation — colour intensity | Upstream | Integrated — independent live selector. |
| Gamma R / G / B — per-channel brightness curves | Upstream | Integrated — three independent live selectors. |
| Widescreen — Default, Off, 16:9, 16:10, Fill | Upstream | Integrated — Aspect Ratio and Widescreen Mode. Window Fill is delegated to RetroArch by user decision. |
| Pipeline — overlap emulation and rendering | Upstream | Integrated — selector with performance and one-frame latency help. |
| Frame Skip — skip drawing when running late | Upstream | Integrated — frontend underrun-driven adaptation, at most two consecutive drawing skips. |
| Keyboard Shifter — H-pattern or sequential keyboard gears | Upstream | Excluded — separate keyboard controls were rejected by the user. Controller profiles and RetroArch remapping provide input. |
| Hold Gears — return keyboard H-pattern to neutral on release | Upstream | Excluded — part of the rejected separate keyboard controls. This does not qualify physical shifter behavior. |
| Linked Play — two local Daytona players in one emulator | Upstream | Excluded — local cooperative mode was explicitly excluded by the user. External Linked Cabinets is a separate feature. |
| Linked Play Layout — side by side or stacked | Upstream | Excluded — depends on the excluded local cooperative mode. |
| Picture Shape — Keep, Stretch, Crop | Upstream | Excluded from core options — final presentation/cropping belongs to RetroArch by user decision. |
| Scaling Filter — Smooth or Sharp final enlargement | Upstream | Excluded from core options — RetroArch owns final scaling/filtering. |
| Frame Cap — native pacing or uncapped execution | Upstream | Integrated through RetroArch — pacing and fast-forward are frontend-owned. |
| VSync — presentation synchronization | Upstream | Integrated through RetroArch — frontend video setting. |
| Fullscreen — standalone window mode | Upstream | Integrated through RetroArch — frontend window setting. |
| Window Size — automatic, presets or custom dimensions | Upstream | Integrated through RetroArch — frontend window setting. |
| ROM Folder — content search path | Upstream | Integrated through Libretro content loading and system directory. The standalone global INI is excluded. |
| Save Folder — native backup/EEPROM destination | Upstream | Integrated through RetroArch Save RAM paths; native raw byte layout retained. |
| Restore Defaults / Colour Reset — launcher reset actions | Upstream | Integrated through RetroArch option management. No duplicate launcher action. |
| Game Selection / Play / Pause / Continue / Exit — launcher actions | Upstream | Integrated through RetroArch content and execution controls. |
| Reset / Fast Forward — F3 and Tab runtime actions | Upstream | Integrated through RetroArch Restart and fast-forward. |
| Dump 3D Scene — F7 export to a model in dumps/ | Upstream | Excluded By User — not selected in the original-options review. |

### Additional Original Controls And Semantics

| Option And Description | Provenance | Status And RetroArch Mapping |
| --- | --- | --- |
| FakeGouraud — guessed per-vertex lighting from flat polygon colours | Original | Integrated — Fake Gouraud Shading carries light and material parameters across linked vertices. Live, Disabled by default. |
| Wireframe — disable polygon filling for debugging | Original | Excluded By User — not selected in the original-options review. |
| FilterTilemaps — bilinear filtering for 2D tilemaps | Original | Integrated — 2D Tilemap Filtering, Disabled default, live changes. Native priority alpha is filtered after colour decoding. Synthetic GL and actual RetroArch continuation pass. |
| AutoMip — Direct3D automatic mipmap generation | Original | Integrated — Automatic Mipmaps generates levels and blends between them using the D3D9 sampling behavior measured on Windows. Live, Disabled by default. |
| FSAA — Direct3D full-scene antialiasing | Original | Integrated — Full-Scene Anti-Aliasing, Disabled default, Enabled (2x). Unsupported contexts notify without changing the saved selection. Exact two-sample desktop GL and actual RetroArch continuation pass. |
| SoftwareVertexProcessing — select the Direct3D vertex-processing path | Original | Excluded By User — not selected in the original-options review. |
| ForceManaged — managed rather than dynamic Direct3D textures | Original | Excluded By User — not selected in the original-options review. |
| ForceSync — original renderer configuration key | Original | Excluded By User — native D3D VSync, already supplied by RetroArch. Zero selects IMMEDIATE; nonzero selects ONE. |
| FullScreenWidth / FullScreenHeight / FullMode / AutoFull — fullscreen resolution and startup mode | Original | Integrated through RetroArch — frontend display mode and window management. |
| Filters / Configure Filter / Filter — original final-image filter menu and stored selection | Original | Excluded By User — not selected in the original-options review. |
| Enable Sound / Sound — global audio output switch | Original | Integrated through RetroArch mute/audio settings. Per-source gains are also available in the core. |
| Frameskip — automatic/manual frame skipping using keypad +/- | Original | Integrated with adaptation — automatic core Frame Skip retained. Original manual skip levels excluded by user selection. |
| DrawCross — gun-game crosshair visibility | Original | Integrated — SM2-style crosshair controls and styles in the core. |
| Configure Controls / XInput — controller bindings and Windows input backend | Original | Integrated through Libretro input profiles and RetroArch remapping. Windows XInput backend selection belongs to the frontend. |
| UseRawInput / RawDevP1 / RawDevP2 — assign two physical mice | Original | Integrated through RetroArch input/device assignment and core player ports. Native Windows RawInput IDs are excluded from core options; physical multi-device qualification remains open. |
| EnableFF — enable driving force effects | Original | Excluded By User — the standard Libretro interfaces used here provide gamepad rumble, without the native steering-wheel force-effect contract required by these controls. |
| FE_CENTERING_Gain / Coefficient / Saturation / Deadband — spring centering parameters | Original | Excluded By User — the standard Libretro interfaces used here provide gamepad rumble, without the native steering-wheel force-effect contract required by these controls. |
| FE_CLUTCH_Gain / Coefficient — wheel friction parameters | Original | Excluded By User — the standard Libretro interfaces used here provide gamepad rumble, without the native steering-wheel force-effect contract required by these controls. |
| FE_LEFT_Gain / Magnitude and FE_RIGHT_Gain / Magnitude — directional constant force | Original | Excluded By User — the standard Libretro interfaces used here provide gamepad rumble, without the native steering-wheel force-effect contract required by these controls. |
| FE_UNCENTERING_Gain / Magnitude / Offset / Phase / Period — periodic wheel force | Original | Excluded By User — the standard Libretro interfaces used here provide gamepad rumble, without the native steering-wheel force-effect contract required by these controls. |
| RxPort / NextIP / NextPort — external cabinet ring endpoints in m2network.ini | Original | Integrated with adaptation — Linked Cabinets uses the approved RetroArch Netpacket transport. Native IP/UDP endpoint controls are excluded under that transport design. |
| Cheats & Options — Lua-defined game selectors | Original | Integrated — Lua Script Options appears for entries declared by the active game script. |
| Infinite Time — shipped Daytona Lua cheat | Original | Integrated through the original Daytona script. Its controller option writes the game timer when enabled. |
| Load Lua / Reload LUA Script — game scripting and reload action | Original | Integrated — embedded Lua 5.1.4, one main script per set, shared modules and same-interpreter reload. |
| Texture Replacement — .pat mappings, PNGs and mode-specific pixel shaders | Original | Integrated — per-game .pat, PNG and GLSL modes 0–15. Disabled by default, content reload required. |
| Dump Texture Cache — export tagged textures as PNG | Original | Excluded By User — not selected in the original-options review. |
| SSF Player — Ctrl+F5 debug sound playback | Original | Excluded By User — not selected in the original-options review. |
| Save / Load State — native machine snapshots | Original | Integrated — Libretro complete snapshots and frontend commands, with the approved fresh-session behavior. Original Windows state-file interoperability is not established. |
| FPS / Additional Statistics — F9, Ctrl+F9, F8 diagnostics | Original | Integrated in part — current Timing / FPS Overlay retained. Additional original diagnostic pages excluded by user selection. |
| Tilemap Rendering Toggle — F7 debug drawing switch | Original | Excluded By User — not selected in the original-options review. |
| Pause / Single Step / Hold To Run — PAUSE, ENTER, SPACE | Original | Integrated through RetroArch pause/frame advance. Exact hold-to-run shortcut behavior belongs to frontend mapping. |
| Load / Unload ROM / Exit / About / Website — original application menu commands | Original | Integrated through RetroArch content lifecycle and core information. Original application-specific dialogs and website navigation are excluded from the core. |
| Options... — original placeholder application menu | Original | Excluded — README explicitly describes this menu as having no options. |

### Evidence And Review Limits

- Upstream definitions and defaults — `../Model2EmuEx/port/sdl/options.h`, `options.c`, `launcher.cpp` and the runtime input handling.
- Core registration and lifecycle — `src/libretro/sm2_bridge.cpp`, `libretro.c`, `network_options.h` and `COMMON_FEATURES.md`. Frontend-owned equivalents are identified explicitly above.
- Original archive — `port/build-sharc/original/m2emulator.zip`, entries `EMULATOR.INI`, `README.TXT`, `scripts/model2lua.txt`, `scripts/daytona.lua`, and Sega Rally scripts.
- Original binary — `port/build-sharc/original/EMULATOR.EXE`, menu resource 101. The application placeholder Options entry is documented as empty in README.
- The INI's `Filter` integer is an opaque saved menu selection in this review. No filter algorithm is inferred from that integer. ForceSync has subsequently been identified from its original instructions; see ForceSync Result.
- Per-game Service Menu settings remain under the existing NVRAM catalogue and its source review; this list covers emulator controls.
- The F7 scene export is included as an exposed runtime action. Internal environment-driven test instrumentation is outside this user-facing inventory.

Original archive SHA-256 — `5ffebe72d2885bde3fbfab816947475a9a2ce2795284b9d1e90344209bd4c65f`.



### Pre-Selection Suitability Estimates — Historical

These percentages are editorial estimates of suitability for exposure as a Core Option. They are independent of implementation completion, reconstruction fidelity, implementation cost and likelihood of successful support. Scores weigh usefulness during normal arcade play, a clear selector contract, frontend ownership, overlap with existing controls, platform relevance and the current SM2/Supermodel menu examples. Ten-point or five-point distinctions are approximate judgments.

References inspected locally: SM2 `src/libretro/core_options.h` (3D Texture Filtering, Anisotropic Filtering Method, 2D Layer Upscaling Filter, Gamepad Rumble); Supermodel `Src/OSD/libretro/libretro_core_options.h` (Supersampling, numeric Frame Skip, Gamepad Rumble). Similar controls establish menu suitability, without establishing identical rendering algorithms. Absence from these menus does not establish an explicit exclusion decision in those projects. ForceSync remains low-confidence because its behavior has not been traced.

| Pending Option | Provenance | Core Menu Suitability | Rationale |
| --- | --- | --- | --- |
| Dump 3D Scene | Upstream | 10% | Developer export action; unsuitable as a persistent Core Option. |
| FakeGouraud | Original | 60% | Visible native rendering choice, but deliberately modifies lighting. No direct equivalent established in the reviewed menus. |
| Wireframe | Original | 15% | Debug visualization; limited value in the ordinary game menu. |
| FilterTilemaps | Original | 90% | Useful visual selector. SM2 exposes 2D Layer Upscaling Filter, with different algorithms. |
| AutoMip | Original | 75% | Fits renderer quality controls; first establish interaction with the existing Trilinear path. SM2 exposes texture filtering and mipmap-method choices. |
| FSAA | Original | 85% | Fits core rendering quality controls. Supermodel exposes Supersampling; its algorithm differs from original D3D FSAA. |
| SoftwareVertexProcessing | Original | 5% | Historical D3D implementation choice with no direct purpose in the current OpenGL renderer. |
| ForceManaged | Original | 5% | Historical D3D texture-allocation workaround. |
| ForceSync | Original | 20% | Native effect remains unknown; score has low confidence until traced. |
| Filters / Configure Filter | Original | 20% | Final-image presentation is already frontend-owned. Original algorithms remain unidentified. |
| Manual Frameskip | Original | 65% | Supermodel exposes numeric Frame Skip. Additional manual levels would overlap this core’s automatic selector. |
| EnableFF — Wheel Effects | Original | 40% | Arcade-relevant, but reviewed SM2/Supermodel menus use Gamepad Rumble. Native wheel-effect transport remains to be established. |
| FE_CENTERING | Original | 20% | Advanced wheel tuning depends on a usable force-feedback output path. |
| FE_CLUTCH | Original | 20% | Advanced wheel tuning depends on a usable force-feedback output path. |
| FE_LEFT / FE_RIGHT | Original | 20% | Advanced wheel tuning depends on a usable force-feedback output path. |
| FE_UNCENTERING | Original | 20% | Advanced wheel tuning depends on a usable force-feedback output path. |
| Cheats & Options | Original | 25% | Script-specific controls require a defined frontend contract and duplicate some frontend cheat responsibilities. |
| Infinite Time | Original | 10% | Single-game cheat is better suited to the frontend cheat interface. |
| Lua / Reload LUA Script | Original | 15% | Generic scripting and reload commands add a developer workflow beyond ordinary persistent core selectors. |
| Texture Replacement | Original | 70% | User-facing renderer feature with a plausible enable/path contract; no equivalent established in the two reviewed menus. |
| Dump Texture Cache | Original | 10% | Developer asset-export action rather than a persistent gameplay setting. |
| SSF Player | Original | 5% | Separate debug playback workflow outside the loaded arcade game. |
| Additional Original Statistics | Original | 30% | Could complement existing metrics if actionable; assess duplication with Timing / FPS Overlay first. |
| Toggle Tilemap Rendering | Original | 20% | Debug layer switch with limited routine gameplay value. |


### Confirmed Selection And Review — 2026-11-14

The five selected renderer capabilities are integrated. The table above records their defaults and lifecycle. ForceSync was selected to determine its behavior. The investigation identified VSync, and the user explicitly excluded the duplicate core control. The port also supports Lua, same-interpreter reload and script-declared options. All other previously pending options are excluded by the user's selection. Native wheel effects and their FE_* controls are excluded because the standard Libretro contract used here has no native wheel-force-effect output. Existing Gamepad Rumble remains integrated.

#### ForceSync Result

The pinned binary reads Renderer/ForceSync with default zero during renderer initialization at 004ee420. Instructions 004ee765–004ee783 convert zero to 0x80000000 and every nonzero value to 1, then store the result in D3DPRESENT_PARAMETERS.PresentationInterval. Both the normal CreateDevice path and the existing-device Reset path receive this structure.

The original machine instructions were executed in Unicorn for configuration results 0, 1, 2 and 0xffffffff. All four produce the stated mapping. The Direct3D header identifies 0x80000000 as D3DPRESENT_INTERVAL_IMMEDIATE and 1 as D3DPRESENT_INTERVAL_ONE. This is the native VSync switch. The existing approved frontend ownership of VSync applies. A duplicate ForceSync Core Option is unnecessary.

Evidence: src/all_functions.c, FUN_004ee420; original executable 004ee765–004ee783; Direct3D declarations in the local MAME dependency at 3rdparty/bgfx/3rdparty/directx-headers/include/directx/d3d9caps.h and d3d9types.h. The probe executed the original parameter-selection instructions; it did not measure physical display presentation.

#### Original Lua Behavior And Current Port

The original embeds Lua 5.1.4. It loads SCRIPTS/<romset>.lua and provides module search paths for shared Lua files. The shipped Daytona script requires model2 and exports Infinite Time through its Options table. Its Frame callback also chooses widescreen and background stretching from game state. The Sega Rally scripts choose widescreen according to game state.

Optional callbacks documented by the original are Init after loading, Reset on subsequent reset, Frame after emulation and before rendering, PostDraw after rendering and before presentation, and End at termination. Scripts can read and modify i960 memory, inspect and patch ROM regions, read keyboard/joystick input, change widescreen/tile-layer stretching, draw text and PNG overlays, and create named menu choices with runfunc/changefunc callbacks. The .pat texture replacement files and associated pixel shaders are loaded separately on game load.

The original Reload LUA Script menu command 40026 (0x9c5a) sets the pending byte at application +0x399. The execution loop services it through 004fda80. That routine loads and executes the game file using the existing Lua state, guarded by the script critical section. It does not recreate the interpreter and does not explicitly call Init or Reset. Top-level assignments and module caching therefore matter on reload. Missing files disable the script; compilation errors show a Windows message box and disable it. Runtime callbacks use Windows error dialogs. This is source/binary inspection; the full Lua interaction was not executed in this review.

The core embeds Lua 5.1.4. In System, select **Lua Script (Restart Required) → Auto** and reopen content to load the current set's main script. **Reload Lua Script → Reload** executes the same file in the live interpreter and requests a return to Idle. Use `require` for additional modules. A missing main file leaves ordinary Pipeline execution available. Script diagnostics use frontend notifications and the core log.

**Lua Script Options** appears when the active script declares named entries in `Options`. Each selector uses the script's value labels, starting at index zero. A missing values table supplies Off and On. Daytona's original script publishes Infinite Time. Libretro joypad and analog inputs supply the original joystick queries for the two frontend ports. DirectInput keyboard codes return zero.

With an active script the order is machine frame, Frame and option callbacks, rendering, PostDraw, then presentation. The user's Pipeline preference stays stored. A skipped video frame still dispatches PostDraw and discards its drawing commands. Load State retains the live interpreter. Opening content creates a fresh Lua session. ROM patches and script-owned state therefore depend on the script and its session.

### Asset Layout

All paths below are relative to the frontend System directory under `model2emuex/`.

| Path | Use |
| --- | --- |
| `scripts/<romset>.lua` | Main script for the set. Modules use `scripts/<module>.lua` or `scripts/<module>/init.lua`. |
| `scripts/assets/` | PNG overlays and named fonts. Video_CreateFont looks for `<name>.ttf` or `<name> Bold.ttf`. A missing file produces a notification and draws with the built-in font. |
| `textures/<romset>.pat` | Manifest loaded when Texture Replacement is Enabled and content is opened. Each row contains the original texture tag, CRC, mode (hexadecimal) and image path relative to `textures/`. |
| `textures/<romset>/` | Recommended location for the replacement PNGs named by that manifest. |
| `textures/mode_<N>.frag` | GLSL fragment body for coloured modes 1–15. The core supplies Texture, Luma, Xlat, LightMap, BaseColor, TexCoord0, mesh and scale. Mode 0 uses native grayscale lighting. |

The local installation contains the original five Lua files, two HLSL sources, commented Daytona manifest and GLSL translations for modes 1 and 2. Custom HLSL modes require a corresponding GLSL conversion. The original distribution supplies no replacement PNGs or TTFs.
