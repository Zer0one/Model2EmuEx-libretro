# Implemented Core Options Review

Date: 2026-10-22. Status: Native Options Retained; M24 Cabinet Audio Integrated.

Extracted from the built core through Core Options V2 registration: 410 definitions = 70 general options + 340 operator fields across 56 catalogues. Registration, ROM-free tests, frontend execution and physical hardware verification are separate evidence levels.

Reference: current SM2-Emu src/libretro/core_options.h and nvram_settings files; native Model2EmuEx port/sdl/options.c, options.h and launcher.cpp. The imported NVRAM engine, header and data match the current SM2 files byte-for-byte.

## General Options

| Option | Values (Default In Bold) | SM2 Equivalent | Native Model2EmuEx / Adaptation |
| --- | --- | --- | --- |
| ROM CRC Verification (Restart Required) | **Enabled**; Disabled | Same selector, Enabled default and content-reload lifecycle. | Native loader checks ZIP metadata. The shared Enabled choice also computes CRC32 of actual ZIP/loose payload bytes. Disabled skips CRC matching; size/decompression remain checked. Original standalone API keeps metadata-only CRC policy. |
| Automatic Initial NVRAM Setup (Restart Required) | **Enabled**; Disabled | Same name, values, Enabled default. | Uses only SM2 template seeding and its explicit compatible-parent policy. No native Daytona fallback. Existing frontend save data replaces the startup seed. Full clone/revision identity validation is pending. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets; 6 Cabinets; 7 Cabinets; 8 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Single; Car 1 (Master); Car 2 (Slave); Car 3 (Slave); Car 4 (Slave); Car 5 (Slave); Car 6 (Slave); Car 7 (Slave); Car 8 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets; 6 Cabinets; 7 Cabinets; 8 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Single; Car 1 (Master); Car 2 (Slave); Car 3 (Slave); Car 4 (Slave); Car 5 (Slave); Car 6 (Slave); Car 7 (Slave); Car 8 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets; 6 Cabinets; 7 Cabinets; 8 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Single; Car 1 (Master); Car 2 (Slave); Car 3 (Slave); Car 4 (Slave); Car 5 (Slave); Car 6 (Slave); Car 7 (Slave); Car 8 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets; 6 Cabinets; 7 Cabinets; 8 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Single; Car 1 (Master); Car 2 (Slave); Car 3 (Slave); Car 4 (Slave); Car 5 (Slave); Car 6 (Slave); Car 7 (Slave); Car 8 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets; 6 Cabinets; 7 Cabinets; 8 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Single; Car 1 (Master); Car 2 (Slave); Car 3 (Slave); Car 4 (Slave); Car 5 (Slave); Car 6 (Slave); Car 7 (Slave); Car 8 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Notlink; Car 1 (Master); Car 2 (Slave); Car 3 (Slave); Car 4 (Slave); Relay | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Notlink; Car 1 (Master); Car 2 (Slave); Car 3 (Slave); Car 4 (Slave); Relay | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets; 5 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Stand Alone; Cabinet 1 (Master); Cabinet 2 (Slave); Cabinet 3 (Slave); Cabinet 4 (Slave); Live | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Not Link; Master; Slave; Relay | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Not Link; Master; Slave; Relay | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Not Link; Carno.1 (Master); Carno.2 (Slave); Carno.3 (Slave); Carno.4 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Not Link; Carno.1 (Master); Carno.2 (Slave); Carno.3 (Slave); Carno.4 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; No Link; Cabinet 1 (Master); Cabinet 2 (Slave); Cabinet 3 (Slave); Cabinet 4 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **1 Cabinet / Disabled**; 2 Cabinets; 3 Cabinets; 4 Cabinets | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Disabled**; Stand Alone; Cabinet 1 (Master); Cabinet 2 (Slave); Cabinet 3 (Slave); Cabinet 4 (Slave) | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Linked Cabinets | **Not Supported** | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| Auto Network Role Settings | **Not Supported** | SM2 per-set choices, limits, Disabled default and independent authority; help explicitly states the approved next-running-frame lifecycle. | Native in-process ring adapted to frontend-owned Netpacket; reviewed NVRAM mappings reused. Exactly one pair is visible for the current game. Unsupported sets show Not Supported. See EXTERNAL_LINKED_CABINETS.md for per-game limits, runtime evidence and approved all-set local loopback. |
| NVRAM Settings (Service Menu) | **Disabled**; Enabled | Same name, values, Disabled default. | No equivalent unified operator Core Options menu. Imported patch/checksum engine adapted to the first 16 KiB backup RAM plus 128-byte EEPROM; remaining backup RAM preserved. Effective changes reset once on Resume. Master visibility now follows SM2: hidden without an active operator catalogue. |
| Internal Resolution | **1x (496 x 384)**; 2x (992 x 768); 3x (1488 x 1152); 4x (1984 x 1536) | Internal Resolution: 1x–8x, default 1x. | Render Resolution: Auto (native default), 1x–4x. Core keeps 1x–4x, default 1x. Auto/window scaling delegated to RetroArch by user decision. |
| 3D Texture Filtering | **Nearest**; Bilinear; Trilinear | 3D Texture Filtering: Faithful (default), Anisotropic 2x/4x/8x/16x. | Native Nearest (default), Bilinear, Trilinear retained by user decision; same shared option name, different actual filters. |
| Aspect Ratio | **Auto**; 4:3; 16:9; 16:10 | Aspect Ratio: Auto (default), 4:3, 16:9. | Approved separate control with added 16:10. Native Widescreen combines ratio/expansion. Final window fill remains frontend-owned. |
| Widescreen Mode | **Disabled**; Expand 3D View Only | Widescreen Mode: Disabled (default), Expand 3D View Only. | Approved shared two-control contract; actual expansion and layer treatment use native per-game rules. Auto + expansion selects 16:9; explicit 4:3 suppresses expansion. 16:10 supported. |
| A/V Timing (Restart Required) | **60 Hz (Default)**; 58 Hz (Native Model2EmuEx) | Same selector and 60 Hz default; SM2 native choice is 57.524 Hz. | Native catalogue declares 58 Hz. User approved 60 Hz default. One native machine frame per callback; SM2 endpoint audio interpolation. Content reload required. |
| Timing / FPS Overlay | **Off**; Auto; On (11 px); On (12 px); On (13 px); On (14 px) | Same label, Off/Auto/11–14 px values, Off default and live lifecycle. | Reuses SM2 panel and measurement equations, destination CPU timings and frontend OpenGL submission. Caption uses the actual 60/58 Hz cadence. See TIMING_OVERLAY.md for limits. |
| Pipeline | **Enabled**; Disabled | No equivalent selector. Software Renderer Threading is a different subsystem and is not equivalent. | Native Pipeline (Emulate On A Separate Core), default Enabled. Core reuses capture/replay with a joined worker; can add one frame of video latency. Retained by user decision; help explains the performance/latency tradeoff. |
| Frame Skip | **Enabled**; Disabled | No equivalent selector in current SM2 Core Options. | Native Frame Skip defaults Enabled and responds to late frames. Core instead responds to Libretro audio-underrun status; at most two consecutive drawing skips. No status callback means no skipping. Retained by user decision. |
| Shadows And Fences | **Blend (50% See-Through)**; Checker (As The Hardware) | No equivalent selector in current SM2 Core Options. | Native Shadows And Fences choices/default preserved. Retained by user decision. |
| Saturation | 0.50; 0.55; 0.60; 0.65; 0.70; 0.75; 0.80; 0.85; 0.90; 0.95; **1.00**; 1.05; 1.10; 1.15; 1.20; 1.25; 1.30; 1.35; 1.40; 1.45; 1.50; 1.55; 1.60; 1.65; 1.70; 1.75; 1.80; 1.85; 1.90; 1.95; 2.00 | No equivalent selector in current SM2 Core Options. | Native slider converted to discrete choices 0.50–2.00 in 0.05 steps, default 1.00. Retained by user decision. |
| Gamma (Red) | 0.50; 0.55; 0.60; 0.65; 0.70; 0.75; 0.80; 0.85; 0.90; 0.95; **1.00**; 1.05; 1.10; 1.15; 1.20; 1.25; 1.30; 1.35; 1.40; 1.45; 1.50; 1.55; 1.60; 1.65; 1.70; 1.75; 1.80; 1.85; 1.90; 1.95; 2.00 | No equivalent selector in current SM2 Core Options. | One of three native Gamma (R, G, B) slider channels, split into a selector. 0.50–2.00 in 0.05 steps, default 1.00. Retained by user decision. |
| Gamma (Green) | 0.50; 0.55; 0.60; 0.65; 0.70; 0.75; 0.80; 0.85; 0.90; 0.95; **1.00**; 1.05; 1.10; 1.15; 1.20; 1.25; 1.30; 1.35; 1.40; 1.45; 1.50; 1.55; 1.60; 1.65; 1.70; 1.75; 1.80; 1.85; 1.90; 1.95; 2.00 | No equivalent selector in current SM2 Core Options. | Same adaptation for the green channel. Retained by user decision. |
| Gamma (Blue) | 0.50; 0.55; 0.60; 0.65; 0.70; 0.75; 0.80; 0.85; 0.90; 0.95; **1.00**; 1.05; 1.10; 1.15; 1.20; 1.25; 1.30; 1.35; 1.40; 1.45; 1.50; 1.55; 1.60; 1.65; 1.70; 1.75; 1.80; 1.85; 1.90; 1.95; 2.00 | No equivalent selector in current SM2 Core Options. | Same adaptation for the blue channel. Retained by user decision. |
| Manx TT: Cabinet Audio | **Enabled**; Disabled | Same label, help, Enabled/Disabled values, Enabled default and NVRAM-driven cabinet policy. | Native primary SCSP with optional Model 1 audio board and full SM2 I8251/AMS path. Optional sound-only sibling ROMs; selected-set fallback and notices follow SM2. Inert outside Manx TT. See MANX_TT_CABINET_AUDIO.md. |
| SCSP Gain | **Auto**; Mute; 10%; 20%; 30%; 40%; 50%; 60%; 70%; 80%; 90%; 100% | Same label, Auto/Mute/10–100% values and Auto default. | No native selector. Optional neutral source-gain API; Auto and 100% retain the native mix. Muted synthesis continues. Absent sources are no-ops. Resume without reset. |
| MultiPCM 1 Gain | **Auto**; Mute; 10%; 20%; 30%; 40%; 50%; 60%; 70%; 80%; 90%; 100% | Same label, Auto/Mute/10–100% values and Auto default. | No native selector. Optional neutral source-gain API; Auto and 100% retain the native mix. Muted synthesis continues. Absent sources are no-ops. Resume without reset. |
| MultiPCM 2 Gain | **Auto**; Mute; 10%; 20%; 30%; 40%; 50%; 60%; 70%; 80%; 90%; 100% | Same label, Auto/Mute/10–100% values and Auto default. | No native selector. Optional neutral source-gain API; Auto and 100% retain the native mix. Muted synthesis continues. Absent sources are no-ops. Resume without reset. |
| FM (YM3438) Gain | **Auto**; Mute; 10%; 20%; 30%; 40%; 50%; 60%; 70%; 80%; 90%; 100% | Same label, Auto/Mute/10–100% values and Auto default. | No native selector. Optional neutral source-gain API; Auto and 100% retain the native mix. Muted synthesis continues. Absent sources are no-ops. Resume without reset. |
| Controller Profile Type | Normal; **Normal + Test/Service** | Same selector, values and default; `sm2_controller_profile_type`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Gamepad Rumble | **Enabled**; Disabled | Same selector, values and default; `sm2_gamepad_rumble`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Show Crosshair | **Automatic**; Disabled; Player 1 Only; Player 2 Only; Players 1 & 2 | Same selector, values and default, explicitly approved by the user. | No standalone external crosshair. Reuses unchanged SM2 presentation/PNG module; destination OpenGL overlay and system/model2emuex/crosshairs directory. Resume without reset; PNG changes require content reload. |
| Crosshair Style | Auto; **SM2-Emu**; Supermodel; Custom | Same selector, values and default, explicitly approved by the user. | No standalone external crosshair. Reuses unchanged SM2 presentation/PNG module; destination OpenGL overlay and system/model2emuex/crosshairs directory. Resume without reset; PNG changes require content reload. |
| Crosshair Inactivity Timeout | **Disabled**; 1 Second; 2 Seconds; 3 Seconds; 4 Seconds; 5 Seconds; 6 Seconds; 7 Seconds; 8 Seconds; 10 Seconds; 15 Seconds; 30 Seconds; 60 Seconds | Same selector, values and default, explicitly approved by the user. | No standalone external crosshair. Reuses unchanged SM2 presentation/PNG module; destination OpenGL overlay and system/model2emuex/crosshairs directory. Resume without reset; PNG changes require content reload. |
| Gun Input Mode | **Standard**; Lightgun Only; Mouse + Analog Stick; Mouse Only; Analog Stick Only | Same selector, values and default; `sm2_gun_input`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Gun Analog Stick Control | **Relative**; Absolute | Same selector, values and default; `sm2_gun_stick_control`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Off-Screen Reload Shortcut | **Enabled**; Disabled | Same selector, values and default; `sm2_offscreen_reload_shortcut`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Mouse Edge Off-Screen Reload | **Disabled**; Enabled | Same selector, values and default; `sm2_mouse_edge_offscreen_reload`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| 4-Speed Shifter | **H-Gate Mode**; Standard | Same selector, values and default; `sm2_four_speed_shifter`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Gear Shift Neutral Time | 0 ms; 10 ms; 20 ms; 30 ms; 40 ms; 50 ms; 60 ms; 70 ms; 80 ms; 90 ms; **100 ms**; 110 ms; 120 ms; 130 ms; 140 ms; 150 ms; 160 ms; 170 ms; 180 ms; 190 ms; 200 ms; 210 ms; 220 ms; 230 ms; 240 ms; 250 ms; 260 ms; 270 ms; 280 ms; 290 ms; 300 ms; 310 ms; 320 ms; 330 ms; 340 ms; 350 ms; 360 ms; 370 ms; 380 ms; 390 ms; 400 ms; 410 ms; 420 ms; 430 ms; 440 ms; 450 ms; 460 ms; 470 ms; 480 ms; 490 ms; 500 ms | Same selector, values and default; `sm2_gear_shift_neutral_time`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Automatic Start Gear (Restart Required) | **Enabled**; Disabled | Same selector, values and default; `sm2_automatic_start_gear`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Driving Steering Response | **Linear**; Progressive (Fine Center); FBNeo Logarithmic (Fine Center) | Same selector, values and default; `sm2_steering_response`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Driving Steering Output Range | 50%; 60%; 63% (30-80-D0); 70%; 80%; 90%; **100%**; 110%; 120%; 130%; 140%; 150% | Same selector, values and default; `sm2_steering_output_range`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Driving Accelerator Output Range | 50%; 60%; 70%; 75.3% (00-C0); 80%; 90%; **100%**; 110%; 120%; 130%; 140%; 150% | Same selector, values and default; `sm2_accelerator_output_range`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Driving Brake Output Range | 50%; 60%; 70%; 75.3% (00-C0); 80%; 90%; **100%**; 110%; 120%; 130%; 140%; 150% | Same selector, values and default; `sm2_brake_output_range`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Desert Tank: Elevation Control | **Relative**; Absolute | Same selector, values and default; `sm2_desert_elevation_control`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Desert Tank: Elevation Speed (Relative Only) | 10%; 20%; 30%; 40%; 50%; 60%; 70%; 80%; 90%; **100%**; 110%; 120%; 130%; 140%; 150%; 160%; 170%; 180%; 190%; 200% | Same selector, values and default; `sm2_desert_elevation_speed`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |
| Desert Tank: Elevation Axis Mode | **Normal**; Inverted | Same selector, values and default; `sm2_desert_elevation_axis`. | No equivalent standalone selector. Reuses unchanged SM2 input/rumble engine with destination port, ADC, gear and gun-counter translation. See COMMON_FEATURES.md for lifecycle and verification limits. |

## NVRAM Differences And Validation Limits

- All 340 field choices, values and default tokens come from the unchanged SM2 catalogue. Labels use the same Title Case conversion. Destination keys replace the sm2_ prefix with model2emuex_.
- Operator default value labels now carry (Default), exactly following SM2. Stored default tokens and choices are unchanged.
- V2 NVRAM Settings master visibility now follows SM2: hidden without an applicable catalogue, visible with one. Operator fields appear only for the active catalogue when the master is Enabled. Legacy menus cannot reproduce dynamic display hiding.
- SM2 hides native role/identity fields managed by Auto Network Role Settings. That network authority layer is not integrated here; there is no corresponding suppression.
- Destination catalogue selection currently uses game/parent names. Complete clone aliases and main-program CRC identity mapping are not integrated yet. Imported entries for future board backends are preparation, not per-game runtime validation.
- ROM-free engine/bridge checks and a VF2 upstream comparison exist. No claim of complete gameplay validation for all 340 fields is made.

## Complete NVRAM Field Inventory

Each row is a registered operator option. Values/default tokens are identical to the corresponding SM2 key. Native Model2EmuEx exposes these through emulated service menus rather than an equivalent host options catalogue. Some catalogues belong to games whose destination backend is not executable yet. The catalogue name below is not a claim that the destination loader accepts that set name.

### daytona (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Link ID | Master; Slave; **Single (Default)** | `model2emuex_nvram_daytona_link_id` | `sm2_nvram_daytona_link_id` |
| Car Number | **1 (Default)**; 2; 3; 4; 5; 6; 7; 8 | `model2emuex_nvram_daytona_car_number` | `sm2_nvram_daytona_car_number` |
| Cabinet | Twin; Upright; **Deluxe (Default)** | `model2emuex_nvram_daytona_cabinet` | `sm2_nvram_daytona_cabinet` |
| Country | JPN; **Export (Default)**; USA | `model2emuex_nvram_daytona_country` | `sm2_nvram_daytona_country` |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_daytona_difficulty` | `sm2_nvram_daytona_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_daytona_advertise_sound` | `sm2_nvram_daytona_advertise_sound` |
| Game Mode | **Normal (Default)**; Grand Prix; Endurance | `model2emuex_nvram_daytona_game_mode` | `sm2_nvram_daytona_game_mode` |
| Rival Arrow | **On (Default)**; Off | `model2emuex_nvram_daytona_rival_arrow` | `sm2_nvram_daytona_rival_arrow` |

### daytonagtx (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Link ID | Master; Slave; **Single (Default)** | `model2emuex_nvram_daytonagtx_link_id` | `sm2_nvram_daytonagtx_link_id` |
| Car Number | **1 (Default)**; 2; 3; 4; 5; 6; 7; 8 | `model2emuex_nvram_daytonagtx_car_number` | `sm2_nvram_daytonagtx_car_number` |
| Cabinet | Twin; Upright; **Deluxe (Default)** | `model2emuex_nvram_daytonagtx_cabinet` | `sm2_nvram_daytonagtx_cabinet` |
| Country | JPN; **Export (Default)**; USA | `model2emuex_nvram_daytonagtx_country` | `sm2_nvram_daytonagtx_country` |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_daytonagtx_difficulty` | `sm2_nvram_daytonagtx_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_daytonagtx_advertise_sound` | `sm2_nvram_daytonagtx_advertise_sound` |
| Game Mode | **Normal (Default)**; Grand Prix; Endurance | `model2emuex_nvram_daytonagtx_game_mode` | `sm2_nvram_daytonagtx_game_mode` |
| Rival Arrow | **On (Default)**; Off | `model2emuex_nvram_daytonagtx_rival_arrow` | `sm2_nvram_daytonagtx_rival_arrow` |

### daytona93 (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_daytona93_advertise_sound` | `sm2_nvram_daytona93_advertise_sound` |
| Country | JPN; **Export (Default)**; USA | `model2emuex_nvram_daytona93_country` | `sm2_nvram_daytona93_country` |
| Cabinet | **Deluxe (Default)**; Upright | `model2emuex_nvram_daytona93_cabinet` | `sm2_nvram_daytona93_cabinet` |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_daytona93_difficulty` | `sm2_nvram_daytona93_difficulty` |

### daytonas (9 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Link ID | Master; Slave; **Single (Default)** | `model2emuex_nvram_daytonas_link_id` | `sm2_nvram_daytonas_link_id` |
| Car Number | **1 (Default)**; 2; 3; 4; 5; 6; 7; 8 | `model2emuex_nvram_daytonas_car_number` | `sm2_nvram_daytonas_car_number` |
| Cabinet | Twin; Special; Upright; **Deluxe (Default)** | `model2emuex_nvram_daytonas_cabinet` | `sm2_nvram_daytonas_cabinet` |
| Country | JPN; **Export (Default)**; USA | `model2emuex_nvram_daytonas_country` | `sm2_nvram_daytonas_country` |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_daytonas_difficulty` | `sm2_nvram_daytonas_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_daytonas_advertise_sound` | `sm2_nvram_daytonas_advertise_sound` |
| Game Mode | **Normal (Default)**; Grand Prix; Endurance | `model2emuex_nvram_daytonas_game_mode` | `sm2_nvram_daytonas_game_mode` |
| Rival Arrow | **On (Default)**; Off | `model2emuex_nvram_daytonas_rival_arrow` | `sm2_nvram_daytonas_rival_arrow` |
| Promote Saturn | Off; **Coming Soon (Default)**; Available Now | `model2emuex_nvram_daytonas_promote_saturn` | `sm2_nvram_daytonas_promote_saturn` |

### desert (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Country | Japan; U.S.; **Export (Default)** | `model2emuex_nvram_desert_country` | `sm2_nvram_desert_country` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_desert_advertise_sound` | `sm2_nvram_desert_advertise_sound` |
| Difficulty: Desert | **Easy (Default)**; Normal; Hard; Hardest; Monkey | `model2emuex_nvram_desert_difficulty_desert` | `sm2_nvram_desert_difficulty_desert` |
| Difficulty: Canyon | **Easy (Default)**; Normal; Hard; Hardest; Monkey | `model2emuex_nvram_desert_difficulty_canyon` | `sm2_nvram_desert_difficulty_canyon` |

### doa (7 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| VJCOM Difficulty | **Normal (Default)**; Easy; Hard; Very Hard | `model2emuex_nvram_doa_vjcom_difficulty` | `sm2_nvram_doa_vjcom_difficulty` |
| VJCOM Energy | **Normal (Default)**; Easy; Hard; Very Hard | `model2emuex_nvram_doa_vjcom_energy` | `sm2_nvram_doa_vjcom_energy` |
| VJMAN Energy | **Normal (Default)**; Easy; Hard; Very Hard | `model2emuex_nvram_doa_vjman_energy` | `sm2_nvram_doa_vjman_energy` |
| Demo Sound | **On (Default)**; Off | `model2emuex_nvram_doa_demo_sound` | `sm2_nvram_doa_demo_sound` |
| Nation | Japan; U.S.A.; **Export (Default)** | `model2emuex_nvram_doa_nation` | `sm2_nvram_doa_nation` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_doa_continue` | `sm2_nvram_doa_continue` |
| Burst Mode | **Off (Default)**; On | `model2emuex_nvram_doa_burst_mode` | `sm2_nvram_doa_burst_mode` |

### fvipers (6 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_fvipers_difficulty` | `sm2_nvram_fvipers_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_fvipers_advertise_sound` | `sm2_nvram_fvipers_advertise_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_fvipers_continue` | `sm2_nvram_fvipers_continue` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_fvipers_country` | `sm2_nvram_fvipers_country` |
| Display Type | **Projector (Default)**; C.R.T. | `model2emuex_nvram_fvipers_display_type` | `sm2_nvram_fvipers_display_type` |
| Ranking Mode | **Off (Default)**; On | `model2emuex_nvram_fvipers_ranking_mode` | `sm2_nvram_fvipers_ranking_mode` |

### schamp (12 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Enemy Rank | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_schamp_enemy_rank` | `sm2_nvram_schamp_enemy_rank` |
| Energy (1P) | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_schamp_energy_1p` | `sm2_nvram_schamp_energy_1p` |
| Energy (VS) | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_schamp_energy_vs` | `sm2_nvram_schamp_energy_vs` |
| Barrier | **5 (Default)**; 6; 7; 8; 9; 10; 1; 2; 3; 4 | `model2emuex_nvram_schamp_barrier` | `sm2_nvram_schamp_barrier` |
| Barrier Reset | **Off (Default)**; On | `model2emuex_nvram_schamp_barrier_reset` | `sm2_nvram_schamp_barrier_reset` |
| Automatic | **On (Default)**; Off | `model2emuex_nvram_schamp_automatic` | `sm2_nvram_schamp_automatic` |
| Hyper Mode | **On (Default)**; Off | `model2emuex_nvram_schamp_hyper_mode` | `sm2_nvram_schamp_hyper_mode` |
| Damage | **Normal (Default)**; Real | `model2emuex_nvram_schamp_damage` | `sm2_nvram_schamp_damage` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_schamp_advertise_sound` | `sm2_nvram_schamp_advertise_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_schamp_continue` | `sm2_nvram_schamp_continue` |
| Country | USA; **Export (Default)**; Japan | `model2emuex_nvram_schamp_country` | `sm2_nvram_schamp_country` |
| Display Type | **C.R.T. (Default)**; Projector | `model2emuex_nvram_schamp_display_type` | `sm2_nvram_schamp_display_type` |

### sfight (12 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Enemy Rank | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_sfight_enemy_rank` | `sm2_nvram_sfight_enemy_rank` |
| Energy (1P) | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_sfight_energy_1p` | `sm2_nvram_sfight_energy_1p` |
| Energy (VS) | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_sfight_energy_vs` | `sm2_nvram_sfight_energy_vs` |
| Barrier | **5 (Default)**; 6; 7; 8; 9; 10; 1; 2; 3; 4 | `model2emuex_nvram_sfight_barrier` | `sm2_nvram_sfight_barrier` |
| Barrier Reset | **Off (Default)**; On | `model2emuex_nvram_sfight_barrier_reset` | `sm2_nvram_sfight_barrier_reset` |
| Automatic | On; **Off (Default)** | `model2emuex_nvram_sfight_automatic` | `sm2_nvram_sfight_automatic` |
| Hyper Mode | **On (Default)**; Off | `model2emuex_nvram_sfight_hyper_mode` | `sm2_nvram_sfight_hyper_mode` |
| Damage | **Normal (Default)**; Real | `model2emuex_nvram_sfight_damage` | `sm2_nvram_sfight_damage` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_sfight_advertise_sound` | `sm2_nvram_sfight_advertise_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_sfight_continue` | `sm2_nvram_sfight_continue` |
| Country | USA; **Export (Default)**; Japan | `model2emuex_nvram_sfight_country` | `sm2_nvram_sfight_country` |
| Display Type | **C.R.T. (Default)**; Projector | `model2emuex_nvram_sfight_display_type` | `sm2_nvram_sfight_display_type` |

### vcop (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_vcop_advertise_sound` | `sm2_nvram_vcop_advertise_sound` |
| Country | JPN; **EXP (Default)**; USA | `model2emuex_nvram_vcop_country` | `sm2_nvram_vcop_country` |
| Cabinet | **DX (Default)**; SP U/R; U/R | `model2emuex_nvram_vcop_cabinet` | `sm2_nvram_vcop_cabinet` |
| Difficulty | **Normal (Default)**; Medium Hard; Hard; Very Hard; Hardest; Easiest; Very Easy; Easy; Medium Easy | `model2emuex_nvram_vcop_difficulty` | `sm2_nvram_vcop_difficulty` |

### vcop2 (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_vcop2_advertise_sound` | `sm2_nvram_vcop2_advertise_sound` |
| Country | JPN; **EXP (Default)**; USA | `model2emuex_nvram_vcop2_country` | `sm2_nvram_vcop2_country` |
| Cabinet | **DX (Default)**; SP U/R; U/R | `model2emuex_nvram_vcop2_cabinet` | `sm2_nvram_vcop2_cabinet` |
| Difficulty | **Normal (Default)**; Medium Hard; Hard; Very Hard; Hardest; Easiest; Very Easy; Easy; Medium Easy | `model2emuex_nvram_vcop2_difficulty` | `sm2_nvram_vcop2_difficulty` |

### vf2 (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_vf2_difficulty` | `sm2_nvram_vf2_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_vf2_advertise_sound` | `sm2_nvram_vf2_advertise_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_vf2_continue` | `sm2_nvram_vf2_continue` |
| Drink | **OK (Default)**; NG | `model2emuex_nvram_vf2_drink` | `sm2_nvram_vf2_drink` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_vf2_country` | `sm2_nvram_vf2_country` |
| Display Type | **Projector (Default)**; C.R.T. | `model2emuex_nvram_vf2_display_type` | `sm2_nvram_vf2_display_type` |
| Ranking Mode | **Off (Default)**; On | `model2emuex_nvram_vf2_ranking_mode` | `sm2_nvram_vf2_ranking_mode` |
| Version | **Normal (Default)**; Version 2 | `model2emuex_nvram_vf2_version` | `sm2_nvram_vf2_version` |

### vf2a (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_vf2a_difficulty` | `sm2_nvram_vf2a_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_vf2a_advertise_sound` | `sm2_nvram_vf2a_advertise_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_vf2a_continue` | `sm2_nvram_vf2a_continue` |
| Drink | **OK (Default)**; NG | `model2emuex_nvram_vf2a_drink` | `sm2_nvram_vf2a_drink` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_vf2a_country` | `sm2_nvram_vf2a_country` |
| Display Type | **Projector (Default)**; C.R.T. | `model2emuex_nvram_vf2a_display_type` | `sm2_nvram_vf2a_display_type` |
| Ranking Mode | **Off (Default)**; On | `model2emuex_nvram_vf2a_ranking_mode` | `sm2_nvram_vf2a_ranking_mode` |
| Version | **Normal (Default)**; Version 2 | `model2emuex_nvram_vf2a_version` | `sm2_nvram_vf2a_version` |

### vf2o (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_vf2o_difficulty` | `sm2_nvram_vf2o_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_vf2o_advertise_sound` | `sm2_nvram_vf2o_advertise_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_vf2o_continue` | `sm2_nvram_vf2o_continue` |
| Drink | **OK (Default)**; NG | `model2emuex_nvram_vf2o_drink` | `sm2_nvram_vf2o_drink` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_vf2o_country` | `sm2_nvram_vf2o_country` |
| Display Type | **Projector (Default)**; C.R.T. | `model2emuex_nvram_vf2o_display_type` | `sm2_nvram_vf2o_display_type` |
| Ranking Mode | **Off (Default)**; On | `model2emuex_nvram_vf2o_ranking_mode` | `sm2_nvram_vf2o_ranking_mode` |
| Version | **Normal (Default)**; Version 2 | `model2emuex_nvram_vf2o_version` | `sm2_nvram_vf2o_version` |

### vstriker (10 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_vstriker_advertise_sound` | `sm2_nvram_vstriker_advertise_sound` |
| Country | JPN; **EXP (Default)**; USA | `model2emuex_nvram_vstriker_country` | `sm2_nvram_vstriker_country` |
| Monitor | **CRT (Default)**; Projecter | `model2emuex_nvram_vstriker_monitor` | `sm2_nvram_vstriker_monitor` |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_vstriker_difficulty` | `sm2_nvram_vstriker_difficulty` |
| V Goal System | **Off (Default)**; On | `model2emuex_nvram_vstriker_v_goal_system` | `sm2_nvram_vstriker_v_goal_system` |
| V Goal Time Set | **0:15 (Default)**; 0:30; 0:45; 1:00; Time Free | `model2emuex_nvram_vstriker_v_goal_time_set` | `sm2_nvram_vstriker_v_goal_time_set` |
| PK System | **Off (Default)**; On | `model2emuex_nvram_vstriker_pk_system` | `sm2_nvram_vstriker_pk_system` |
| PK Member Set | **3 (Default)**; 4; 5; Real PK | `model2emuex_nvram_vstriker_pk_member_set` | `sm2_nvram_vstriker_pk_member_set` |
| Billboard | **On (Default)**; Off | `model2emuex_nvram_vstriker_billboard` | `sm2_nvram_vstriker_billboard` |
| One Match Mode | **Off (Default)**; On | `model2emuex_nvram_vstriker_one_match_mode` | `sm2_nvram_vstriker_one_match_mode` |

### vstrikero (9 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_vstrikero_advertise_sound` | `sm2_nvram_vstrikero_advertise_sound` |
| Country | JPN; **EXP (Default)**; USA | `model2emuex_nvram_vstrikero_country` | `sm2_nvram_vstrikero_country` |
| Monitor | **CRT (Default)**; Projecter | `model2emuex_nvram_vstrikero_monitor` | `sm2_nvram_vstrikero_monitor` |
| Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_vstrikero_difficulty` | `sm2_nvram_vstrikero_difficulty` |
| V Goal System | **Off (Default)**; On | `model2emuex_nvram_vstrikero_v_goal_system` | `sm2_nvram_vstrikero_v_goal_system` |
| V Goal Time Set | **0:15 (Default)**; 0:30; 0:45; 1:00; Time Free | `model2emuex_nvram_vstrikero_v_goal_time_set` | `sm2_nvram_vstrikero_v_goal_time_set` |
| PK System | **Off (Default)**; On | `model2emuex_nvram_vstrikero_pk_system` | `sm2_nvram_vstrikero_pk_system` |
| PK Member Set | **3 (Default)**; 4; 5; Real PK | `model2emuex_nvram_vstrikero_pk_member_set` | `sm2_nvram_vstrikero_pk_member_set` |
| Billboard | **On (Default)**; Off | `model2emuex_nvram_vstrikero_billboard` | `sm2_nvram_vstrikero_billboard` |

### airwlkrs (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Player Selection | **2P Simultaneous (Default)**; 4P Simultaneous | `model2emuex_nvram_airwlkrs_player_selection` | `sm2_nvram_airwlkrs_player_selection` |
| Attract Sound | **Off (Default)**; On | `model2emuex_nvram_airwlkrs_attract_sound` | `sm2_nvram_airwlkrs_attract_sound` |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Easiest; Easy | `model2emuex_nvram_airwlkrs_difficulty` | `sm2_nvram_airwlkrs_difficulty` |
| Character Type | **Normal (Default)**; Deformation | `model2emuex_nvram_airwlkrs_character_type` | `sm2_nvram_airwlkrs_character_type` |

### dynabb (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_dynabb_game_difficulty` | `sm2_nvram_dynabb_game_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_dynabb_advertise_sound` | `sm2_nvram_dynabb_advertise_sound` |
| Cabinet Type | **US (Default)**; City; Megalo | `model2emuex_nvram_dynabb_cabinet_type` | `sm2_nvram_dynabb_cabinet_type` |
| Favorite | **Off (Default)**; Swallows; Carp; Giants; Baystars; Dragons; Tigers; Bluewave; Marines; Lions; Fighters; Hawks; Buffaloes | `model2emuex_nvram_dynabb_favorite` | `sm2_nvram_dynabb_favorite` |

### dynabb97 (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_dynabb97_game_difficulty` | `sm2_nvram_dynabb97_game_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_dynabb97_advertise_sound` | `sm2_nvram_dynabb97_advertise_sound` |
| Cabinet Type | **US (Default)**; City; Megalo | `model2emuex_nvram_dynabb97_cabinet_type` | `sm2_nvram_dynabb97_cabinet_type` |
| Favorite | **Off (Default)**; Swallows; Carp; Giants; Baystars; Dragons; Tigers; Bluewave; Marines; Lions; Fighters; Hawks; Buffaloes | `model2emuex_nvram_dynabb97_favorite` | `sm2_nvram_dynabb97_favorite` |

### dynamcop (3 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_dynamcop_advertise_sound` | `sm2_nvram_dynamcop_advertise_sound` |
| Game Difficulty | **3 (Default)**; 4; 5; 6; 7; 8; 1; 2 | `model2emuex_nvram_dynamcop_game_difficulty` | `sm2_nvram_dynamcop_game_difficulty` |
| Violence Mode | **On (Default)**; Off | `model2emuex_nvram_dynamcop_violence_mode` | `sm2_nvram_dynamcop_violence_mode` |

### dyndeka2 (3 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_dyndeka2_advertise_sound` | `sm2_nvram_dyndeka2_advertise_sound` |
| Game Difficulty | **3 (Default)**; 4; 5; 6; 7; 8; 1; 2 | `model2emuex_nvram_dyndeka2_game_difficulty` | `sm2_nvram_dyndeka2_game_difficulty` |
| Violence Mode | **On (Default)**; Off | `model2emuex_nvram_dyndeka2_violence_mode` | `sm2_nvram_dyndeka2_violence_mode` |

### dyndeka2b (3 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_dyndeka2b_advertise_sound` | `sm2_nvram_dyndeka2b_advertise_sound` |
| Game Difficulty | **3 (Default)**; 4; 5; 6; 7; 8; 1; 2 | `model2emuex_nvram_dyndeka2b_game_difficulty` | `sm2_nvram_dyndeka2b_game_difficulty` |
| Violence Mode | **On (Default)**; Off | `model2emuex_nvram_dyndeka2b_violence_mode` | `sm2_nvram_dyndeka2b_violence_mode` |

### hotd (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Medium Hard; Very Hard; Very Easy; Medium Easy | `model2emuex_nvram_hotd_game_difficulty` | `sm2_nvram_hotd_game_difficulty` |
| Blood Color | **Green (Default)**; Blue; Purple; Red | `model2emuex_nvram_hotd_blood_color` | `sm2_nvram_hotd_blood_color` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_hotd_advertise_sound` | `sm2_nvram_hotd_advertise_sound` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_hotd_country` | `sm2_nvram_hotd_country` |

### hotdp (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Medium Hard; Very Hard; Very Easy; Medium Easy | `model2emuex_nvram_hotdp_game_difficulty` | `sm2_nvram_hotdp_game_difficulty` |
| Blood Color | **Red (Default)**; Green | `model2emuex_nvram_hotdp_blood_color` | `sm2_nvram_hotdp_blood_color` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_hotdp_advertise_sound` | `sm2_nvram_hotdp_advertise_sound` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_hotdp_country` | `sm2_nvram_hotdp_country` |

### indy500 (9 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Very Easy; Easy | `model2emuex_nvram_indy500_game_difficulty` | `sm2_nvram_indy500_game_difficulty` |
| Race Mode | **Normal (Default)**; Long | `model2emuex_nvram_indy500_race_mode` | `sm2_nvram_indy500_race_mode` |
| Advertise Sound | **Off (Default)**; On | `model2emuex_nvram_indy500_advertise_sound` | `sm2_nvram_indy500_advertise_sound` |
| Country | USA; **EXP (Default)**; Japan | `model2emuex_nvram_indy500_country` | `sm2_nvram_indy500_country` |
| Cabinet Type | **Twin (Default)**; Deluxe | `model2emuex_nvram_indy500_cabinet_type` | `sm2_nvram_indy500_cabinet_type` |
| Network Type | **Stand Alone (Default)**; Master; Slave | `model2emuex_nvram_indy500_network_type` | `sm2_nvram_indy500_network_type` |
| Cabinet ID | **1 (Default)**; 2; 3; 4; 5; 6; 7; 8 | `model2emuex_nvram_indy500_cabinet_id` | `sm2_nvram_indy500_cabinet_id` |
| Engine Volume | 1; 2; **3 (Default)** | `model2emuex_nvram_indy500_engine_volume` | `sm2_nvram_indy500_engine_volume` |
| Default View | 1; 2; 3; **4 (Default)** | `model2emuex_nvram_indy500_default_view` | `sm2_nvram_indy500_default_view` |

### indy500d (7 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Very Easy; Easy | `model2emuex_nvram_indy500d_game_difficulty` | `sm2_nvram_indy500d_game_difficulty` |
| Race Mode | **Normal (Default)**; Long | `model2emuex_nvram_indy500d_race_mode` | `sm2_nvram_indy500d_race_mode` |
| Advertise Sound | **Off (Default)**; On | `model2emuex_nvram_indy500d_advertise_sound` | `sm2_nvram_indy500d_advertise_sound` |
| Country | USA; **EXP (Default)**; Japan | `model2emuex_nvram_indy500d_country` | `sm2_nvram_indy500d_country` |
| Cabinet Type | Twin; **Deluxe (Default)** | `model2emuex_nvram_indy500d_cabinet_type` | `sm2_nvram_indy500d_cabinet_type` |
| Network Type | **Stand Alone (Default)**; Master; Slave | `model2emuex_nvram_indy500d_network_type` | `sm2_nvram_indy500d_network_type` |
| Cabinet ID | **1 (Default)**; 2; 3; 4; 5; 6; 7; 8 | `model2emuex_nvram_indy500d_cabinet_id` | `sm2_nvram_indy500d_cabinet_id` |

### lastbrnx (6 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **1 Normal (Default)**; 2 Hard; 3 Hardest; 0 Easy | `model2emuex_nvram_lastbrnx_game_difficulty` | `sm2_nvram_lastbrnx_game_difficulty` |
| Advertise Sound | **Off (Default)**; On | `model2emuex_nvram_lastbrnx_advertise_sound` | `sm2_nvram_lastbrnx_advertise_sound` |
| Survival Mode | **On (Default)**; Off | `model2emuex_nvram_lastbrnx_survival_mode` | `sm2_nvram_lastbrnx_survival_mode` |
| Cut Cross Street | **Off (Default)**; On | `model2emuex_nvram_lastbrnx_cut_cross_street` | `sm2_nvram_lastbrnx_cut_cross_street` |
| Display Type | **C.R.T. (Default)**; Projector | `model2emuex_nvram_lastbrnx_display_type` | `sm2_nvram_lastbrnx_display_type` |
| Master Volume | 1; 2; **3 (Default)**; 4; 5; 6; 7 | `model2emuex_nvram_lastbrnx_master_volume` | `sm2_nvram_lastbrnx_master_volume` |

### manxtt (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_manxtt_advertise_sound` | `sm2_nvram_manxtt_advertise_sound` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_manxtt_country` | `sm2_nvram_manxtt_country` |
| Cabinet Type | Deluxe; **Twin (Default)** | `model2emuex_nvram_manxtt_cabinet_type` | `sm2_nvram_manxtt_cabinet_type` |
| Link Type | **Not Link (Default)**; Master; Slave; Relay | `model2emuex_nvram_manxtt_link_type` | `sm2_nvram_manxtt_link_type` |
| Bike Color (No.) | **Red (No.1) (Default)**; Blue (No.2); Yellow (No.3); Green (No.4); Green (No.5); Yellow (No.6); Blue (No.7); Red (No.8) | `model2emuex_nvram_manxtt_bike_color` | `sm2_nvram_manxtt_bike_color` |
| Race Mode | **Race (Default)**; T.T. | `model2emuex_nvram_manxtt_race_mode` | `sm2_nvram_manxtt_race_mode` |
| Laxey Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_manxtt_laxey_game_difficulty` | `sm2_nvram_manxtt_laxey_game_difficulty` |
| TT Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_manxtt_tt_game_difficulty` | `sm2_nvram_manxtt_tt_game_difficulty` |

### manxttdx (6 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_manxttdx_advertise_sound` | `sm2_nvram_manxttdx_advertise_sound` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_manxttdx_country` | `sm2_nvram_manxttdx_country` |
| Bike Color (No.) | **Red (No.1) (Default)**; Blue (No.2); Yellow (No.3); Green (No.4); Green (No.5); Yellow (No.6); Blue (No.7); Red (No.8) | `model2emuex_nvram_manxttdx_bike_color` | `sm2_nvram_manxttdx_bike_color` |
| Race Mode | **Race (Default)**; T.T. | `model2emuex_nvram_manxttdx_race_mode` | `sm2_nvram_manxttdx_race_mode` |
| Laxey Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_manxttdx_laxey_game_difficulty` | `sm2_nvram_manxttdx_laxey_game_difficulty` |
| TT Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_manxttdx_tt_game_difficulty` | `sm2_nvram_manxttdx_tt_game_difficulty` |

### motoraid (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Very Hard; Very Easy; Easy | `model2emuex_nvram_motoraid_game_difficulty` | `sm2_nvram_motoraid_game_difficulty` |
| Race Mode | **Standard (Default)**; Long | `model2emuex_nvram_motoraid_race_mode` | `sm2_nvram_motoraid_race_mode` |
| Enemy Level | **Normal (Default)**; Strong | `model2emuex_nvram_motoraid_enemy_level` | `sm2_nvram_motoraid_enemy_level` |
| Engine Volume | **Standard (Default)**; Half | `model2emuex_nvram_motoraid_engine_volume` | `sm2_nvram_motoraid_engine_volume` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_motoraid_advertise_sound` | `sm2_nvram_motoraid_advertise_sound` |
| Country | Japan; USA; **EXP (Default)** | `model2emuex_nvram_motoraid_country` | `sm2_nvram_motoraid_country` |
| Network Type | **Stand Alone (Default)**; Master; Slave; Live | `model2emuex_nvram_motoraid_network_type` | `sm2_nvram_motoraid_network_type` |
| Cabinet ID | **1 (Default)**; 2; 3; 4 | `model2emuex_nvram_motoraid_cabinet_id` | `sm2_nvram_motoraid_cabinet_id` |

### motoraiddx (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Very Hard; Very Easy; Easy | `model2emuex_nvram_motoraiddx_game_difficulty` | `sm2_nvram_motoraiddx_game_difficulty` |
| Race Mode | **Standard (Default)**; Long | `model2emuex_nvram_motoraiddx_race_mode` | `sm2_nvram_motoraiddx_race_mode` |
| Enemy Level | **Normal (Default)**; Strong | `model2emuex_nvram_motoraiddx_enemy_level` | `sm2_nvram_motoraiddx_enemy_level` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_motoraiddx_advertise_sound` | `sm2_nvram_motoraiddx_advertise_sound` |
| Country | Japan; USA; **EXP (Default)** | `model2emuex_nvram_motoraiddx_country` | `sm2_nvram_motoraiddx_country` |
| Network Type | **Stand Alone (Default)**; Master; Slave; Live | `model2emuex_nvram_motoraiddx_network_type` | `sm2_nvram_motoraiddx_network_type` |
| Cabinet ID | **1 (Default)**; 2; 3; 4 | `model2emuex_nvram_motoraiddx_cabinet_id` | `sm2_nvram_motoraiddx_cabinet_id` |
| Cabinet Type | Deluxe; **Twin (Default)** | `model2emuex_nvram_motoraiddx_cabinet_type` | `sm2_nvram_motoraiddx_cabinet_type` |

### overrev (7 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Country | Japan; U.S.A.; **Europe (Default)**; Korea | `model2emuex_nvram_overrev_country` | `sm2_nvram_overrev_country` |
| Hardware Type | Normal (2in1); Sega Indy; Sega Indy DX / GT24h DX; **Sega Stcc (Default)** | `model2emuex_nvram_overrev_hardware_type` | `sm2_nvram_overrev_hardware_type` |
| Link Max | **Not Link (Default)**; 2 Links; 3 Links; 4 Links | `model2emuex_nvram_overrev_link_max` | `sm2_nvram_overrev_link_max` |
| Link Type | **Master Carno.1 (Default)**; Slave Carno.2; Slave Carno.3; Slave Carno.4 | `model2emuex_nvram_overrev_link_type` | `sm2_nvram_overrev_link_type` |
| Game Difficulty | **Normal (Default)**; Hard; Very Hard; Easy | `model2emuex_nvram_overrev_game_difficulty` | `sm2_nvram_overrev_game_difficulty` |
| Demo Sound | **On (Default)**; Off | `model2emuex_nvram_overrev_demo_sound` | `sm2_nvram_overrev_demo_sound` |
| Maximum Lap | **Normal Mode (Default)**; Long Mode; Very Long Mode | `model2emuex_nvram_overrev_maximum_lap` | `sm2_nvram_overrev_maximum_lap` |

### rchase2 (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_rchase2_advertise_sound` | `sm2_nvram_rchase2_advertise_sound` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_rchase2_country` | `sm2_nvram_rchase2_country` |
| Game Difficulty | 1/8; 2/8; 3/8; **4/8 (Default)**; 5/8; 6/8; 7/8; 8/8 | `model2emuex_nvram_rchase2_game_difficulty` | `sm2_nvram_rchase2_game_difficulty` |
| Shifting Difficulty | 10 Sec Every; 20 Sec Every; 30 Sec Every; 40 Sec Every; **50 Sec Every (Default)**; 60 Sec Every; 70 Sec Every; None | `model2emuex_nvram_rchase2_shifting_difficulty` | `sm2_nvram_rchase2_shifting_difficulty` |

### segawski (2 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Very Easy; Easy | `model2emuex_nvram_segawski_game_difficulty` | `sm2_nvram_segawski_game_difficulty` |
| Advertise Sound | **Off (Default)**; On | `model2emuex_nvram_segawski_advertise_sound` | `sm2_nvram_segawski_advertise_sound` |

### skisuprg (5 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_skisuprg_country` | `sm2_nvram_skisuprg_country` |
| Network Type | **No Link (Default)**; Master; Slave | `model2emuex_nvram_skisuprg_network_type` | `sm2_nvram_skisuprg_network_type` |
| Cabinet ID | **1 (Default)**; 2; 3; 4 | `model2emuex_nvram_skisuprg_cabinet_id` | `sm2_nvram_skisuprg_cabinet_id` |
| Live Display | **On (Default)**; Off | `model2emuex_nvram_skisuprg_live_display` | `sm2_nvram_skisuprg_live_display` |
| Victoria Display | **On (Default)**; Off | `model2emuex_nvram_skisuprg_victoria_display` | `sm2_nvram_skisuprg_victoria_display` |

### skytargt (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_skytargt_difficulty` | `sm2_nvram_skytargt_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_skytargt_advertise_sound` | `sm2_nvram_skytargt_advertise_sound` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_skytargt_country` | `sm2_nvram_skytargt_country` |
| Cabinet Type | **Standard (Default)**; Deluxe | `model2emuex_nvram_skytargt_cabinet_type` | `sm2_nvram_skytargt_cabinet_type` |

### srallyc (6 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_srallyc_advertise_sound` | `sm2_nvram_srallyc_advertise_sound` |
| Country | JPN; USA; **Export (Default)** | `model2emuex_nvram_srallyc_country` | `sm2_nvram_srallyc_country` |
| Cabinet Type | **Twin (Default)**; Deluxe | `model2emuex_nvram_srallyc_cabinet_type` | `sm2_nvram_srallyc_cabinet_type` |
| Link Type | **Notlink (Default)**; Car 1; Car 2; Car 3; Car 4; Relay | `model2emuex_nvram_srallyc_link_type` | `sm2_nvram_srallyc_link_type` |
| Game Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_srallyc_game_difficulty` | `sm2_nvram_srallyc_game_difficulty` |
| Game Mode | **Normal (Default)**; Short; Long; Longest | `model2emuex_nvram_srallyc_game_mode` | `sm2_nvram_srallyc_game_mode` |

### srallycdx (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_srallycdx_advertise_sound` | `sm2_nvram_srallycdx_advertise_sound` |
| Country | JPN; USA; **Export (Default)** | `model2emuex_nvram_srallycdx_country` | `sm2_nvram_srallycdx_country` |
| Game Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_srallycdx_game_difficulty` | `sm2_nvram_srallycdx_game_difficulty` |
| Game Mode | **Normal (Default)**; Short; Long; Longest | `model2emuex_nvram_srallycdx_game_mode` | `sm2_nvram_srallycdx_game_mode` |

### srallycdxa (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_srallycdxa_advertise_sound` | `sm2_nvram_srallycdxa_advertise_sound` |
| Country | JPN; USA; **Export (Default)** | `model2emuex_nvram_srallycdxa_country` | `sm2_nvram_srallycdxa_country` |
| Game Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_srallycdxa_game_difficulty` | `sm2_nvram_srallycdxa_game_difficulty` |
| Game Mode | **Normal (Default)**; Short; Long; Longest | `model2emuex_nvram_srallycdxa_game_mode` | `sm2_nvram_srallycdxa_game_mode` |

### sgt24h (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Link Type | **Not Link (Default)**; Car NO1 Master; Car NO2 Slave; Car NO3 Slave; Car NO4 Slave | `model2emuex_nvram_sgt24h_link_type` | `sm2_nvram_sgt24h_link_type` |
| Link Max | **2 (Default)**; 3; 4 | `model2emuex_nvram_sgt24h_link_max` | `sm2_nvram_sgt24h_link_max` |
| Country | Japan; USA; **EUR (Default)** | `model2emuex_nvram_sgt24h_country` | `sm2_nvram_sgt24h_country` |
| Game Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_sgt24h_game_difficulty` | `sm2_nvram_sgt24h_game_difficulty` |
| Race Mode | **Normal (Default)**; Long | `model2emuex_nvram_sgt24h_race_mode` | `sm2_nvram_sgt24h_race_mode` |
| Game BGM | **On (Default)**; Off | `model2emuex_nvram_sgt24h_game_bgm` | `sm2_nvram_sgt24h_game_bgm` |
| Demo Sound | **On (Default)**; Off | `model2emuex_nvram_sgt24h_demo_sound` | `sm2_nvram_sgt24h_demo_sound` |
| I/O Type | A; **B (Default)**; C | `model2emuex_nvram_sgt24h_io_type` | `sm2_nvram_sgt24h_io_type` |

### gunblade (5 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_gunblade_advertise_sound` | `sm2_nvram_gunblade_advertise_sound` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_gunblade_country` | `sm2_nvram_gunblade_country` |
| Game Difficulty | 1/8; 2/8; 3/8; **4/8 (Default)**; 5/8; 6/8; 7/8; 8/8 | `model2emuex_nvram_gunblade_game_difficulty` | `sm2_nvram_gunblade_game_difficulty` |
| Shifting Difficulty | 1/8; 2/8; 3/8; **4/8 (Default)**; 5/8; 6/8; 7/8; 8/8 | `model2emuex_nvram_gunblade_shifting_difficulty` | `sm2_nvram_gunblade_shifting_difficulty` |
| Cabinet Type | **DX (Default)**; SD | `model2emuex_nvram_gunblade_cabinet_type` | `sm2_nvram_gunblade_cabinet_type` |

### bel (3 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Country | U.S.; **Export (Default)**; Japan | `model2emuex_nvram_bel_country` | `sm2_nvram_bel_country` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_bel_advertise_sound` | `sm2_nvram_bel_advertise_sound` |
| Difficulty | **6 (Default)**; 7; 8; 9; 10; 1; 2; 3; 4; 5 | `model2emuex_nvram_bel_difficulty` | `sm2_nvram_bel_difficulty` |

### hpyagu98 (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Easy | `model2emuex_nvram_hpyagu98_game_difficulty` | `sm2_nvram_hpyagu98_game_difficulty` |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_hpyagu98_advertise_sound` | `sm2_nvram_hpyagu98_advertise_sound` |
| Cabinet Type | **US (Default)**; City; Megalo | `model2emuex_nvram_hpyagu98_cabinet_type` | `sm2_nvram_hpyagu98_cabinet_type` |
| Favorite | **Off (Default)**; Giants; Eagles; Unicorns; Lions; Raiders; Bears; Twins; Tigers | `model2emuex_nvram_hpyagu98_favorite` | `sm2_nvram_hpyagu98_favorite` |

### pltkids (3 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Difficult | **Normal (Default)**; Difficult; More Difficult; Easy | `model2emuex_nvram_pltkids_difficulty` | `sm2_nvram_pltkids_difficulty` |
| Demo Sound | **Off (Default)**; On | `model2emuex_nvram_pltkids_demo_sound` | `sm2_nvram_pltkids_demo_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_pltkids_continue` | `sm2_nvram_pltkids_continue` |

### stcc (9 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_stcc_advertise_sound` | `sm2_nvram_stcc_advertise_sound` |
| URL Address | **On (Default)**; Off | `model2emuex_nvram_stcc_url_address` | `sm2_nvram_stcc_url_address` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_stcc_country` | `sm2_nvram_stcc_country` |
| Cabinet Type | **Twin (Default)**; Deluxe | `model2emuex_nvram_stcc_cabinet_type` | `sm2_nvram_stcc_cabinet_type` |
| Link Type | **Stand Alone (Default)**; Car 1; Car 2; Car 3; Car 4; Car 5; Car 6; Car 7; Car 8; Relay | `model2emuex_nvram_stcc_link_type` | `sm2_nvram_stcc_link_type` |
| Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_stcc_difficulty` | `sm2_nvram_stcc_difficulty` |
| Game Mode | **Normal (Default)**; Short; Long; Grand Prix | `model2emuex_nvram_stcc_game_mode` | `sm2_nvram_stcc_game_mode` |
| Default Car | **Random (Default)**; Alfa Romeo; Mercedes; Opel; Toyota | `model2emuex_nvram_stcc_default_car` | `sm2_nvram_stcc_default_car` |
| Default View | **Bird'S (Default)**; Driver'S | `model2emuex_nvram_stcc_default_view` | `sm2_nvram_stcc_default_view` |

### stcca (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_stcca_advertise_sound` | `sm2_nvram_stcca_advertise_sound` |
| URL Address | **On (Default)**; Off | `model2emuex_nvram_stcca_url_address` | `sm2_nvram_stcca_url_address` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_stcca_country` | `sm2_nvram_stcca_country` |
| Cabinet Type | **Twin (Default)**; Deluxe | `model2emuex_nvram_stcca_cabinet_type` | `sm2_nvram_stcca_cabinet_type` |
| Link Type | **Stand Alone (Default)**; Car 1; Car 2; Car 3; Car 4; Car 5; Car 6; Car 7; Car 8; Relay | `model2emuex_nvram_stcca_link_type` | `sm2_nvram_stcca_link_type` |
| Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_stcca_difficulty` | `sm2_nvram_stcca_difficulty` |
| Game Mode | **Normal (Default)**; Short; Long; Grand Prix | `model2emuex_nvram_stcca_game_mode` | `sm2_nvram_stcca_game_mode` |
| Default Car | **Random (Default)**; Alfa Romeo; Mercedes; Opel; Toyota | `model2emuex_nvram_stcca_default_car` | `sm2_nvram_stcca_default_car` |

### stccb (9 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_stccb_advertise_sound` | `sm2_nvram_stccb_advertise_sound` |
| URL Address | **On (Default)**; Off | `model2emuex_nvram_stccb_url_address` | `sm2_nvram_stccb_url_address` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_stccb_country` | `sm2_nvram_stccb_country` |
| Cabinet Type | **Twin (Default)**; Deluxe | `model2emuex_nvram_stccb_cabinet_type` | `sm2_nvram_stccb_cabinet_type` |
| Link Type | **Stand Alone (Default)**; Car 1; Car 2; Car 3; Car 4; Car 5; Car 6; Car 7; Car 8; Relay | `model2emuex_nvram_stccb_link_type` | `sm2_nvram_stccb_link_type` |
| Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_stccb_difficulty` | `sm2_nvram_stccb_difficulty` |
| Game Mode | **Normal (Default)**; Short; Long; Grand Prix | `model2emuex_nvram_stccb_game_mode` | `sm2_nvram_stccb_game_mode` |
| Default Car | **Random (Default)**; Alfa Romeo; Mercedes; Opel; Toyota | `model2emuex_nvram_stccb_default_car` | `sm2_nvram_stccb_default_car` |
| Default View | Bird'S; **Driver'S (Default)** | `model2emuex_nvram_stccb_default_view` | `sm2_nvram_stccb_default_view` |

### stcco (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_stcco_advertise_sound` | `sm2_nvram_stcco_advertise_sound` |
| URL Address | **On (Default)**; Off | `model2emuex_nvram_stcco_url_address` | `sm2_nvram_stcco_url_address` |
| Country | Japan; USA; **Export (Default)** | `model2emuex_nvram_stcco_country` | `sm2_nvram_stcco_country` |
| Cabinet Type | **Twin (Default)**; Deluxe | `model2emuex_nvram_stcco_cabinet_type` | `sm2_nvram_stcco_cabinet_type` |
| Link Type | **Stand Alone (Default)**; Car 1; Car 2; Car 3; Car 4; Car 5; Car 6; Car 7; Car 8; Relay | `model2emuex_nvram_stcco_link_type` | `sm2_nvram_stcco_link_type` |
| Difficulty | **Normal (Default)**; Easy; Hard; Hardest | `model2emuex_nvram_stcco_difficulty` | `sm2_nvram_stcco_difficulty` |
| Game Mode | **Normal (Default)**; Short; Long; Grand Prix | `model2emuex_nvram_stcco_game_mode` | `sm2_nvram_stcco_game_mode` |
| Default Car | **Random (Default)**; Alfa Romeo; Mercedes; Opel; Toyota | `model2emuex_nvram_stcco_default_car` | `sm2_nvram_stcco_default_car` |

### topskatr (2 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Advertise Sound | **On (Default)**; Off | `model2emuex_nvram_topskatr_advertise_sound` | `sm2_nvram_topskatr_advertise_sound` |
| Game Difficulty | **4 / 8 (Default)**; 5 / 8; 6 / 8; 7 / 8; 8 / 8; 1 / 8; 2 / 8; 3 / 8 | `model2emuex_nvram_topskatr_game_difficulty` | `sm2_nvram_topskatr_game_difficulty` |

### von (8 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Network Link Attribute | **No Link (Default)**; Slave; Master | `model2emuex_nvram_von_network_link_attribute` | `sm2_nvram_von_network_link_attribute` |
| Winning By Decision | **On (Default)**; Off | `model2emuex_nvram_von_winning_by_decision` | `sm2_nvram_von_winning_by_decision` |
| Game Difficulty | **Normal (Default)**; Hard; Very Hard; Easy | `model2emuex_nvram_von_game_difficulty` | `sm2_nvram_von_game_difficulty` |
| Advertise Sound | **Loud (Default)**; Off; Soft | `model2emuex_nvram_von_advertise_sound` | `sm2_nvram_von_advertise_sound` |
| Continue | **On (Default)**; Off | `model2emuex_nvram_von_continue` | `sm2_nvram_von_continue` |
| Replay And Posing Mode | **Replay&Posing (Default)**; None; Replay Only; Posing Only | `model2emuex_nvram_von_replay_and_posing_mode` | `sm2_nvram_von_replay_and_posing_mode` |
| Ranking Mode | **On (Default)**; Off | `model2emuex_nvram_von_ranking_mode` | `sm2_nvram_von_ranking_mode` |
| Display Brightness | **0 (Default)**; +1; +2; +3; +4; +5; -5; -4; -3; -2; -1 | `model2emuex_nvram_von_display_brightness` | `sm2_nvram_von_display_brightness` |

### waverunr (6 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Game Difficulty | **Normal (Default)**; Hard; Hardest; Very Easy; Easy | `model2emuex_nvram_waverunr_game_difficulty` | `sm2_nvram_waverunr_game_difficulty` |
| Race Mode | **Normal (Default)**; Long | `model2emuex_nvram_waverunr_race_mode` | `sm2_nvram_waverunr_race_mode` |
| Advertise Sound | **Off (Default)**; On | `model2emuex_nvram_waverunr_advertise_sound` | `sm2_nvram_waverunr_advertise_sound` |
| Country | Japan; USA; **EXP (Default)** | `model2emuex_nvram_waverunr_country` | `sm2_nvram_waverunr_country` |
| Network Type | **Stand Alone (Default)**; Master; Slave | `model2emuex_nvram_waverunr_network_type` | `sm2_nvram_waverunr_network_type` |
| Cabinet ID | **1 (Default)**; 2; 3; 4 | `model2emuex_nvram_waverunr_cabinet_id` | `sm2_nvram_waverunr_cabinet_id` |

### zerogun (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Continue Mode | **Normal Mode (Default)**; Free Play Mode | `model2emuex_nvram_zerogun_continue_mode` | `sm2_nvram_zerogun_continue_mode` |
| Demo Sound | **On (Default)**; Off | `model2emuex_nvram_zerogun_demo_sound` | `sm2_nvram_zerogun_demo_sound` |
| Difficulty | Easy; **Normal (Default)**; Hard; Very Hard | `model2emuex_nvram_zerogun_difficulty` | `sm2_nvram_zerogun_difficulty` |
| Fighters | 1 Fighter; 2 Fighters; **3 Fighters (Default)**; 4 Fighters | `model2emuex_nvram_zerogun_fighters` | `sm2_nvram_zerogun_fighters` |

### zeroguna (4 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Continue Mode | **Normal Mode (Default)**; Free Play Mode | `model2emuex_nvram_zeroguna_continue_mode` | `sm2_nvram_zeroguna_continue_mode` |
| Demo Sound | **On (Default)**; Off | `model2emuex_nvram_zeroguna_demo_sound` | `sm2_nvram_zeroguna_demo_sound` |
| Difficulty | Easy; **Normal (Default)**; Hard; Very Hard | `model2emuex_nvram_zeroguna_difficulty` | `sm2_nvram_zeroguna_difficulty` |
| Fighters | 1 Fighter; 2 Fighters; **3 Fighters (Default)**; 4 Fighters | `model2emuex_nvram_zeroguna_fighters` | `sm2_nvram_zeroguna_fighters` |

### powsled (7 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Ride ID | **Silver (Default)**; Red; Black; Yellow | `model2emuex_nvram_powsled_ride_id` | `sm2_nvram_powsled_ride_id` |
| Checkpoint 0 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; **49 (Default)**; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsled_checkpoint_0` | `sm2_nvram_powsled_checkpoint_0` |
| Checkpoint 1 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; **35 (Default)**; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsled_checkpoint_1` | `sm2_nvram_powsled_checkpoint_1` |
| Checkpoint 2 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; **35 (Default)**; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsled_checkpoint_2` | `sm2_nvram_powsled_checkpoint_2` |
| Checkpoint 3 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; **30 (Default)**; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsled_checkpoint_3` | `sm2_nvram_powsled_checkpoint_3` |
| Checkpoint 4 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; **30 (Default)**; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsled_checkpoint_4` | `sm2_nvram_powsled_checkpoint_4` |
| Motion Angle | 10.0; 10.5; 11.0; 11.5; 12.0; 12.5; 13.0; 13.5; 14.0; 14.5; 15.0; 15.5; 16.0; 16.5; 17.0; 17.5; 18.0; 18.5; 19.0; 19.5; 20.0; 20.5; 21.0; 21.5; 22.0; 22.5; 23.0; 23.5; 24.0; 24.5; 25.0; 25.5; 26.0; 26.5; 27.0; 27.5; 28.0; 28.5; 29.0; 29.5; 30.0; 30.5; 31.0; 31.5; 32.0; 32.5; 33.0; 33.5; 34.0; 34.5; 35.0; 35.5; 36.0; 36.5; 37.0; 37.5; **38.0 (Default)**; 38.5; 39.0; 39.5; 40.0; 40.5; 41.0; 41.5; 42.0; 42.5; 43.0; 43.5; 44.0; 44.5; 45.0 | `model2emuex_nvram_powsled_motion_angle` | `sm2_nvram_powsled_motion_angle` |

### powsledm (7 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Ride ID | **Silver (Default)**; Red; Black; Yellow | `model2emuex_nvram_powsledm_ride_id` | `sm2_nvram_powsledm_ride_id` |
| Checkpoint 0 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; **49 (Default)**; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledm_checkpoint_0` | `sm2_nvram_powsledm_checkpoint_0` |
| Checkpoint 1 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; **35 (Default)**; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledm_checkpoint_1` | `sm2_nvram_powsledm_checkpoint_1` |
| Checkpoint 2 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; **35 (Default)**; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledm_checkpoint_2` | `sm2_nvram_powsledm_checkpoint_2` |
| Checkpoint 3 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; **30 (Default)**; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledm_checkpoint_3` | `sm2_nvram_powsledm_checkpoint_3` |
| Checkpoint 4 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; **30 (Default)**; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledm_checkpoint_4` | `sm2_nvram_powsledm_checkpoint_4` |
| Motion Angle | 10.0; 10.5; 11.0; 11.5; 12.0; 12.5; 13.0; 13.5; 14.0; 14.5; 15.0; 15.5; 16.0; 16.5; 17.0; 17.5; 18.0; 18.5; 19.0; 19.5; 20.0; 20.5; 21.0; 21.5; 22.0; 22.5; 23.0; 23.5; 24.0; 24.5; 25.0; 25.5; 26.0; 26.5; 27.0; 27.5; 28.0; 28.5; 29.0; 29.5; 30.0; 30.5; 31.0; 31.5; 32.0; 32.5; 33.0; 33.5; 34.0; 34.5; 35.0; 35.5; 36.0; 36.5; 37.0; 37.5; **38.0 (Default)**; 38.5; 39.0; 39.5; 40.0; 40.5; 41.0; 41.5; 42.0; 42.5; 43.0; 43.5; 44.0; 44.5; 45.0 | `model2emuex_nvram_powsledm_motion_angle` | `sm2_nvram_powsledm_motion_angle` |

### powsledr (7 Fields)

| Option | Values (Default In Bold) | Model2EmuEx Key | SM2 Key |
| --- | --- | --- | --- |
| Ride ID | **Silver (Default)**; Red; Black; Yellow | `model2emuex_nvram_powsledr_ride_id` | `sm2_nvram_powsledr_ride_id` |
| Checkpoint 0 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; **49 (Default)**; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledr_checkpoint_0` | `sm2_nvram_powsledr_checkpoint_0` |
| Checkpoint 1 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; **35 (Default)**; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledr_checkpoint_1` | `sm2_nvram_powsledr_checkpoint_1` |
| Checkpoint 2 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31; 32; 33; 34; **35 (Default)**; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledr_checkpoint_2` | `sm2_nvram_powsledr_checkpoint_2` |
| Checkpoint 3 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; **30 (Default)**; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledr_checkpoint_3` | `sm2_nvram_powsledr_checkpoint_3` |
| Checkpoint 4 | 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; **30 (Default)**; 31; 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 45; 46; 47; 48; 49; 50; 51; 52; 53; 54; 55; 56; 57; 58; 59; 60; 61; 62; 63; 64; 65; 66; 67; 68; 69; 70; 71; 72; 73; 74; 75; 76; 77; 78; 79; 80; 81; 82; 83; 84; 85; 86; 87; 88; 89; 90; 91; 92; 93; 94; 95; 96; 97; 98; 99 | `model2emuex_nvram_powsledr_checkpoint_4` | `sm2_nvram_powsledr_checkpoint_4` |
| Motion Angle | 10.0; 10.5; 11.0; 11.5; 12.0; 12.5; 13.0; 13.5; 14.0; 14.5; 15.0; 15.5; 16.0; 16.5; 17.0; 17.5; 18.0; 18.5; 19.0; 19.5; 20.0; 20.5; 21.0; 21.5; 22.0; 22.5; 23.0; 23.5; 24.0; 24.5; 25.0; 25.5; 26.0; 26.5; 27.0; 27.5; 28.0; 28.5; 29.0; 29.5; 30.0; 30.5; 31.0; 31.5; 32.0; 32.5; 33.0; 33.5; 34.0; 34.5; 35.0; 35.5; 36.0; 36.5; 37.0; 37.5; **38.0 (Default)**; 38.5; 39.0; 39.5; 40.0; 40.5; 41.0; 41.5; 42.0; 42.5; 43.0; 43.5; 44.0; 44.5; 45.0 | `model2emuex_nvram_powsledr_motion_angle` | `sm2_nvram_powsledr_motion_angle` |

## Explicit Exclusions And Not Yet Integrated

- Excluded by user decision: SM2's added 8 kHz SCSP output low-pass filter and its selector; preserve native SCSP output.
- Removed: Keyboard Shifter, Hold Gears and direct RETRO_DEVICE_KEYBOARD polling, by user instruction. Keyboard mappings belong to RetroArch.
- Excluded for now by user instruction: native cooperative mode and layouts.
- Frontend responsibilities: final scaling/filter, window sizing, fullscreen, VSync, frame cap/fast-forward, final crop/fill and host directories.
- Excluded by user decision: Hide Shot Flash and its selector.
- Manx TT cabinet audio is integrated; see MANX_TT_CABINET_AUDIO.md. Linked Cabinets and Auto Network Role Settings are integrated; see EXTERNAL_LINKED_CABINETS.md for qualification limits. Save States use the standard frontend commands; no selector is added. Shared input profiles, rumble, driving/gun controls, source gains, A/V Timing and crosshairs are integrated; see COMMON_FEATURES.md for evidence levels.

## Subsequent MAME Content Alignment

By explicit user request, the loader catalogue is now aligned to pinned official MAME metadata. `dayton93` becomes canonical `daytona93`, selecting the exact existing NVRAM catalogue; `srallyp` is excluded from Libretro by user decision. This changes no Core Option definition or default. See MAME_ROMSET_ALIGNMENT.md for all 28 included set identities, file corrections, sound-revision change and validation. The menu review remains pending.

## User Review Responses

- Native options without an SM2 counterpart remain as reviewed; the user accepted the rows without comments. Pipeline remains Enabled by default, with a plain-language help text explaining parallel emulation, performance and the extra frame of video latency.
- Missing (Default) labels and unsupported-game NVRAM master visibility were adapter omissions, not native emulator differences. Both now follow SM2.
- Initial setup follows only the SM2 solution, by explicit user decision: Disabled suppresses seeding; Enabled uses an exact template or an explicitly compatible parent. Without either, no template is forced and no native Daytona fallback runs. Existing frontend Save RAM replaces startup seeding before the first frame. NVRAM Settings, when explicitly Enabled, can subsequently apply the selected operator overrides. This does not add a separate selector.
