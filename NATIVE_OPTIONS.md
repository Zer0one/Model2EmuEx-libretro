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
