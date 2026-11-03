# External Linked Cabinets

Date: 2026-10-21. M13 implementation and bounded macOS acceptance complete; all-set local loopback follows SM2. No commit or push.

## References And Boundary

SM2-Emu is the primary implementation reference, including current `src/libretro/netpacket.*`, `core_options.h`, `automatic_network.*`, `core.cpp`, its Netpacket checks and isolated RetroArch runner. Framework F05/F12/F14 and NETWORK_REVIEW_GUIDE.md define shared authority and lifecycle requirements. Current TGPulse and Supermodel options were inspected read-only for the shared two-option contract. Supermodel does not replace SM2 as the destination reference.

Reference checkout HEAD: `6780297f516c04a793fc51d1a6242c5070da72b5`, with live working-copy changes. Inspected SHA256:

- SM2 `netpacket.cpp`: `4e94deca5cb21ccfe0c64b8269995950c844d0a5b640f57b64ab138e38f7a954`.
- SM2 `core_options.h`: `f1acc57b4b851f15724f3f00913465cb126430057f8c73c31d69970a3dceb702`.
- Framework `FRAMEWORK.md`: `0a529972c481a1d997de6b641493bbd26b43b8abf179c0fbdc12d93ce32a6365`.

The existing standalone `m2net` ring and cooperative layouts remain separate and excluded from the Libretro interface. The new frontend-neutral `port/m2/m2link.*` handles one machine's native search, ID/count assignment, 0xe00-byte block exchange and heartbeat. The adapter supplies ready/send/receive/clear hooks. No sockets or Libretro callbacks enter machine code; callbacks execute on the frontend thread after the pipeline worker completes.

SM2's bounded queues, callback ownership, identity handshake, predecessor/successor routing and active-lobby reconfiguration are reused. Destination changes are the independent `M2XN` wire identity/version 1, transport-only class interface, removal of stale readiness when a peer changes totals, and clearing pending old machine frames on reset/disconnect. This wire is not compatible with SM2, another emulator or the original standalone UDP protocol. Native protocol messages also request a new handshake when one slave restarts; the frontend session remains owned by RetroArch.

## Controls And Coverage

The System menu shows exactly one adjacent pair for the current set. API 2 registers all per-set pairs and hides the others. The existing legacy path registers the current pair only; APIs 0 and 1 use that path. Unsupported sets show Not Supported on both controls. No Network Board, addresses, ports, keyboard controls or cooperative layouts are exposed.

| Control | Choices And Default | Authority / Lifecycle |
| --- | --- | --- |
| Linked Cabinets | `-1` = 1 Cabinet / Disabled (default), then supported totals | External topology only; does not convert the native role. `0`/`1` are parser-only aliases, absent from selectable lists. |
| Auto Network Role Settings | `-1` = Disabled (default), native offline role, positive native identities and applicable `r` special role | Uses the existing SM2 mappings independently of the NVRAM Settings switch. `l`/`s` parse as `r` only where that role exists; aliases are not registered. |

M21's necessary authority integration is included with M13 because F14 requires the pair to work together. Automation hides only managed manual fields, publishes the applied values, preserves unrelated fields/checksums and hands manual management the last applied values. Callback re-entry is supported without holding transport/machine locks. A frontend that rejects SET_VARIABLE retains an internal handover value until an observed manual edit; the core never writes option files itself.

| Destination Sets | Maximum Total | Role Mapping Source | Qualification |
| --- | --- | --- | --- |
| daytona, daytonas, daytonagtx, daytonase, daytonam | 8 | Corresponding SM2 Daytona catalogue; approved parent mapping for SE/M | Daytona two-instance RetroArch link and race startup; other totals are source/protocol coverage. |
| srallyc, srallycb | 5 | srallyc: four Car roles plus Relay | srallyc two-instance RetroArch link and staggered Restart recovery; five-cabinet operation is unqualified. |
| motoraid | 5 | motoraid: Master/Slave IDs plus Live | Core ABI authority and fitted-board persistence; theoretical total retained from SM2. No linked gameplay claim. |
| manxtt, manxttc | 3 | manxtt: Master/Slave/Relay | Core ABI authority and fitted-board persistence on manxtt. No linked gameplay claim. |
| overrev, overrevb | 4 | overrev | Frontend/catalogue preparation; destination Model 2B/2C execution unavailable. |
| skisuprg, waverunr | 4 | Corresponding SM2 catalogue | Frontend/catalogue preparation; destination Model 2C execution unavailable. |

These are the destination entries represented by the primary reference's current supported network list. `daytona93` and unreviewed Turbo revisions are not automatically promoted into network support. Other unlisted sets display Not Supported for this adapter. `srallyp` stays excluded from the whole Libretro catalogue. Limits describe native roles/reference topology, not qualification of every combination.

## Lifecycle And Save States

The user approved next-running-frame application on 2026-10-21. This is also the current SM2 `retro_run` behavior. If the menu suspends execution, changes coalesce on Resume. In a non-pausing Netplay menu, separate edits can apply while the menu is still open. No timer, absent-input heuristic or throttle signal is treated as menu closure. Both controls explicitly describe this limit.

Effective topology/operator changes coalesce into one automatic machine reset. Unchanged values and equivalent aliases do not reset. Explicit Restart reads pending configuration too. Reset restores native settings before the first machine frame, clears stale protocol/audio/presentation/rumble state, and retains frontend send/poll callbacks and already connected clients. It does not unload content or synthesize Netpacket stop/start.

The Netpacket roster is separate from native board state: a full frontend roster is not proof of a working native link or gameplay. The native master is selected by the game settings/registers, never by frontend host/client identity. Native search waits for the requested roster; no fabricated peer is inserted. Different content identities, malformed packets and bounded-queue failures cannot establish a ring.

Following SM2, both Save State operations are rejected with a frontend notification while Linked Cabinets is configured above one, including while waiting for peers. The 12 MiB capacity and existing payload layout remain unchanged. Older offline states remain readable; new local-board states for every set use the guarded header extension described below. Disabling the external link permits normal offline states again. A local single-machine state cannot restore a distributed session.

## Destination Corrections Required By Integration

Daytona's original native I/O emulation stores another settings image in low byte lanes at `back[0x8000 + 2*i]` (I/O addresses 0x200 onward). At restart the game can restore this valid old image over a newly edited backup bank. SM2's NVRAM engine updates the real I/O board EEPROM; the destination must synchronize its corresponding shadow after approved template/override changes. `m2_nvram_sync_settings_io` copies only an already-valid mirrored bank into those lanes. It selects no default, role or identity and is not the excluded native Daytona fallback. Odd lanes and unrelated tail bytes are preserved; the ROM-free native I/O check covers that boundary. Failing runs and the before/after data remain in the ignored M13 audit directories.

Repeated native resets also discarded allocated i960 code-cache pointers through i960_init. Reset now releases those allocations before reinitialization; initial CPU storage is zero-initialized. This prevents repeated network configuration changes from leaking decoded regions. Standalone/headless targets still build.

## All-Set Local Loopback

User decision, 2026-10-21: follow SM2 and retain the communication board in local loopback for every catalog entry when Linked Cabinets is disabled. The earlier Rally-only exception has been removed. SM2 `configure_linked_cabinets` unconditionally calls `comm().set_present(true)` and removes the external transport for one cabinet; this adapter now uses the equivalent unconditional `M2_NET_LOOPBACK` path. No per-game fitting list, selector, ROM patch or native role conversion is involved.

The source review covers all 28 MAME-aligned entries. Native register mapping is shared in `m2board.c`; `m2link_frame` only activates the fitted board when the game sets `net_reg0 & 1`. There is no native conflict requiring a different fitting policy. Unsupported external-link controls stay Not Supported: fitting local hardware does not establish multiplayer support. The six Model 2B/2C entries inherit the same adapter policy when native execution becomes available; the current native creation guard still rejects those boards.

| Catalog Scope | Local Fitting Policy | Verification Boundary |
| --- | --- | --- |
| All 22 Model 2/2A entries, including clones and sets without external-link controls | Board fitted, no external transport, game-owned enable bit and role | Shared source path reviewed; existing ROM-free/ABI regressions and targeted frontend/state checks. No 22-game execution or gameplay acceptance claim. |
| Fighting Vipers, Over Rev / Revision B, Ski Super G, Wave Runner, Water Ski (Model 2B/2C) | Same unconditional adapter policy | Prepared in source; native machine execution remains unavailable. |

The source changes are limited to selecting local mode for every game and initializing its one-node protocol. The existing external topology branch, supported-set/role tables, defaults and SM2 menu wording are retained.

`M2_NET_LOOPBACK` explicitly distinguishes local fitting from an external session. The existing native ring seam handles one local node synchronously, including block return and heartbeat. No frontend callbacks, sockets, peer identities or queued network frames are needed for that local operation. Master establishes native ID/count 1/1; a selected Slave remains Slave and waits rather than being silently promoted. Thus role persistence is independent of whether a particular one-cabinet native role can play alone.

Topology changes replace the local protocol with external Netpacket or restore local loopback, coalescing with role changes into one reset and retaining the frontend session/clients. The persistent ANRS/handover ABI checks now advance 180 frames at each relevant offline transition and across Restart/reload, on both Rally revisions.

The format-1 payload still has its original layout and 12 MiB buffer. Local states use a checked `LNK1` marker and state/master bytes in the previously reserved header, with ABI feature bit `0x80000000`. This now applies to every set. Older cores reject that feature bit instead of silently discarding local protocol state. This core accepts earlier zero-reserved headers and initializes a fresh local protocol after their successful load. Header validation, preflight, rollback, option authority and external-state refusal remain in place. The supplied pre-loopback Sega Rally gameplay state successfully loads and has exact subsequent same/fresh-process continuations; the original file was not modified. Loading an older board-absent state applies the current fitted-board policy; subsequent execution need not match the old hardware configuration. This is backward read support within this core, not cross-emulator or cross-platform compatibility.

## Evidence And Limits

### Transport Provenance And Local Corrections

The donor transport is SM2-Emu Libretro `be696244fc425f55e3c0cab9bc43c03d44b621aa`,
`src/libretro/netpacket.{cpp,h}`. Existing `src/libretro/sm2/IMPORT.json` records
donor and adapted hashes separately. The destination uses `M2XN`, wire version
1 and the `Model2EmuEx Native Ring v1` identity, with a transport-only interface
rather than a dependency on SM2's machine. This does not establish wire
compatibility with SM2 or standalone native networking.

Local lifecycle corrections also discard a peer's previous ready roster on a
cabinet-count mismatch, remove queued packets from disconnected peers and
discard queued frame packets at reset. These prevent stale lobby/topology data
from surviving the corresponding transitions. They are intentional differences
from that donor revision, not additional emulation or new controls. Existing
transport regressions and F05/F14 receipts below, including M25's repeat, provide
the bounded evidence; arbitrary real network loss/topology combinations are not
qualified. On an authorized donor update retain/adapt these corrections unless
equivalent upstream behavior or ended need is verified. The 2026-11-02 audit
corrected their stale metadata hashes only; it did not change transport code.
These donor differences do not establish a reproduced bug in SM2; any transfer
back to that project needs its own source/behavior review and authorized scope.

Earlier Rally-specific local-loopback evidence (before the all-set extension):

- `m13-loopback-clone-abi/results.json`: `srallycb` offline role persistence, handover, Restart/reload, local state continuation and external-state rejection pass.
- `m13-loopback-state-master/result.json`: active `srallyc` Master loopback, Pipeline enabled; four exact RAM/device/PCM/image continuations, invalid-header/payload rejection/rollback, GL context recreation and fresh-process continuation pass.
- `m13-loopback-legacy-user-state/result.json`: the user's earlier state loads; continued state and imagery reproduce in the same and a fresh process.
- `m13-loopback-retroarch-state/result.json`: installed final core in RetroArch 1.22.2, local native ID/count 1/1. Save file created, image advances, load restores the exact image at matched machine frame 1447, execution resumes, exit 0 without forced kill. No physical-controller or audible-output inference.
- `m13-loopback-comparison/result.json`: matched previous/current cores reproduce the old Car-to-Notlink rewrite and corrected retained Car 1 after 180 frames; unrelated VF2 900-frame RAM, PCM and NVRAM remain byte-identical.


All outputs are ignored under `port/build-libretro-macos/audit/`:

| Evidence | Result / Limit |
| --- | --- |
| `make check-network` | Native ROM-free local Master/Slave loopback and 2/3/4/5/8/9-node rings, IDs/counts, predecessor blocks, staggered restart/reconnect and no-master waiting; adapted SM2 transport checks, malformed/mismatched/burst/early packets, active lobby total changes and stale-queue rejection pass. No native gameplay claim follows from synthetic rings. |
| `m13-network-sanitize` | The same native/transport checks with AddressSanitizer and UndefinedBehaviorSanitizer pass. |
| `m13-eeprom.log` | 93C46 regressions and validated Daytona I/O lane synchronization pass. |
| `m13-loopback-common.log` | Existing NVRAM, input, timing, ABI and native serializer checks pass; legacy smoke includes the unsupported pair. |
| `m13-loopback-abi-persistent/results.json` | Actual core callbacks, consuming GET_VARIABLE reads, APIs 2/1/0, paused callback retention, re-entrant setter, four working families' NVRAM-OFF authority/handover, one combined reset, explicit Restart, retained clients, fresh SRAM import and linked Save State rejection pass. This is ABI evidence, not menu-close detection. |
| `m13-fitted-*` | Daytona/Sega Rally/Manx TT/Motor Raid preserve applied Master fields for 180 frames with a fitted board. No emulated peers or gameplay qualification. |
| `m13-retroarch-daytona/` | Two isolated RetroArch 1.22.2 instances form the roster and native IDs 1/2; both screenshots show UP TO 2 RACERS WANTED. Clean exits, no forced kill. |
| `m13-retroarch-daytona-play/` | Scripted Coin/Start reaches a common two-player race: host 2nd/2, client 1st/2, corresponding cars/minimaps and same race countdown. No completed-race, steering, physical controller or audible-output claim. |
| `m13-retroarch-srally/` | Two native links become state 3 with IDs 1/2. Staggered frontend RESET commands return both to state 3 without reopening their lobby; clean exits, no forced kill. |
| `m13-loopback-standalone.log` | Native macOS standalone/headless builds pass. |

Real frontend evidence covers two local macOS participants. Higher totals, remote hosts, relay combinations, all clone programs, live option editing in an already-open real frontend lobby, long races and physical devices remain qualification work. No dependency was installed; user ROMs, production saves and global RetroArch configuration were not modified by these isolated tests.

The earlier Rally-only core and matching info were atomically copied to the local RetroArch development locations, with backups/receipt in `audit/m13-loopback-install/`. Its SHA256 was `2dab3849d29965f1cd497385f9fae22e12a6918610903c6048638deab23a7872`; it passed the earlier frontend local Save/Load test. The all-set replacement is recorded separately below.

### All-Set Policy Integration — 2026-10-21

Evidence root: `audit/m13-catalog-loopback/`. Verification is deliberately scoped to the shared adapter change, rather than a new per-game qualification campaign. The exploratory catalog execution campaign was interrupted at the user's direction; its partial logs are not an acceptance ledger and no remaining per-set runs are queued.

- `network.log`: existing native local enable/disable, Master/Slave, block and heartbeat regressions, external rings, SM2 transport and Daytona I/O tests pass.
- `common.log`: existing NVRAM, input, timing, native serialization and ABI checks pass.
- `standalone.log`: standalone/headless builds pass; their fitting policy is untouched.
- `conventions/results.json`: existing F05 APIs 2/1/0 and F14 Daytona/Sega Rally/Manx TT/Motor Raid authority, handover, reset, client retention and external-state refusal checks pass.
- `state-vf2/result.json`: VF2 with Pipeline enabled passes four exact local-state continuations, corruption/preflight/rollback, current NVRAM authority, GL context recreation and exact fresh-process continuation. The checked core uses the new local-board header for VF2 too.
- `retroarch-state-vf2/result.json`: the installed all-set core in RetroArch 1.22.2 saves, advances, restores exactly at matched machine frame 1461, resumes, and exits 0 without forced termination. This is the targeted real frontend check, not whole-catalog gameplay qualification.

The core and matching info were replaced atomically in the authorized local RetroArch directories. Build/installed core SHA256: `7d113892c9f24bc7b3fa1eb11e904b3e4e2a703fdfb36d808ccddb17dec4c684`. Backup and receipt: `install/deployment.json`. Global `retroarch.cfg` remains byte-identical. Restart RetroArch to load this replacement in another session. No commit or push.

### Power Sled Mixed Programs

SHARC-enabled Libretro builds offer two through five linked cabinets for
Power Sled. Choose one reconstructed Main, up to three Slave rider programs
and optionally one Relay, using the same total on each frontend. The three
programs share the SM2 Netpacket family and advertise separate role IDs.
Ride Color remains independent of the program role. Switching between local
and external topology selects the matching guarded program before reset.

A Main–Relay–Slave RetroArch session formed a real three-node ring and
rendered 3D on all nodes. See SHARC_RECONSTRUCTION.md for the test limits.
