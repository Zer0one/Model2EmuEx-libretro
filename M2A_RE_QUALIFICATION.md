# Inherited Model 2/2A Qualification

Updated: 2026-11-04. Scoped follow-up under M30, after the Model 2B/2C recovery.
This reproduces inherited evidence and fills specific integration/oracle gaps;
it is not a new all-game campaign or a pixel-equivalence gate.

## Results

| Check | Compared | Result And Limits |
| --- | ---: | --- |
| Inherited i960 Suite, Six Seeds | 47,113 / 48,000 generated | All 153 opcodes plus interrupt entry represented. Before correction: 133 sqrt/division mismatches on ARM64. After correction: zero. 887 cases excluded, unchanged between runs. |
| Inherited TGP Interpreter, Eight Seeds | 18,161 / 20,000 generated | Zero mismatches with the inherited Unicorn FLD compatibility build; 1,839 exclusions. This is not the production build. |
| Inherited TGP Driver, Three Seeds | 23,104 calls / 900 sequences | Production flags, zero failing sequences and no reported unmodelled accesses. |
| Targeted Original i960 FP Bodies On Physical AMD | 16,317 vectors | Unchanged original PE code, raw result bytes. Before correction: 1,448 mismatches, all NaN bit patterns. After correction: zero in ARM64 Clang `-O0` and `-O2`, and Linux x86-64 GCC `-O2` running on the same physical AMD host. |
| Model 2 And Model 2A Machine Integration | Two board types | Upload, 43 FIFO transfers per type, command-address encoding, shared/data RAM, pending-output snapshot and complete fresh-machine restoration pass. |
| Combined SHARC/TGPX4 Build | Four machine/geometry gates | TGP, SHARC, TGPx4 and geometry fixtures pass on macOS ARM64. Core build and Libretro ABI/rejected-content check pass. |

The upstream i960 receipt says 47,159 compared cases; the current reproduction
uses the same six seeds and 8,000 generated cases each but compares 47,113 with
the current host/runtime. Do not substitute the historical count or classify
excluded cases as passes. Each run records its exclusions separately.

## Confirmed Port Correction

The inherited i960 arithmetic used C/host NaN selection. ARM64 produced positive
indefinite NaNs for invalid operations where the original x87 produces negative
indefinite. With two NaN inputs, payload/sign selection also differed. The
random suite exposed sqrt/division; explicit edge vectors exposed the remaining
add/subtract/multiply cases.

Original entries `004c2cf0..004c2f60` and `004c3d40/80` first load their operands
with FLD. Thus signalling NaNs are quiet before the arithmetic selects the
larger significand, with positive sign breaking ties. Invalid arithmetic with
no NaN operand produces negative indefinite. `x87_fp_result` preserves these
bits without changing ordinary finite/infinite results or compiler FP flags.
This is a correction to the portable reconstruction, not a correction to
ElSemi's behavior. The shared i960 is also used by Model 2B/2C.

The test covers ten single/double arithmetic/sqrt handlers, all eight mixed
source/destination flags for the single forms, signed zeros, normal/subnormal
boundaries, infinities, signalling/quiet NaNs with both signs and different
payloads, plus deterministic random operands. Comparison is byte-exact: no
NaN normalization or numerical tolerance. It does not prove all i960 FP
instructions, alternate x87 precision modes or all input combinations.

## Oracle And Coverage Boundaries

- The general i960 suite retains upstream transcendental tolerances, NaN
  equality for FP registers, restricted logarithm inputs and its independent
  `fmod` oracle. Original faults, unreproducible x87-stack/native-memory cases
  and cases without an exact oracle remain explicitly excluded.
- TGP's `TGP_TEST_UNICORN_FLD` deliberately preserves signalling NaNs because
  Unicorn 2.1.4 does not quiet them on FLD. It is absent from production. The
  production build compared against Unicorn on seed 1 gives four differences
  among 2,277 compared cases: each is exactly the documented SNaN quiet bit in
  register D. No production behavior was changed to make that oracle pass.
- The interpreter excludes accesses outside its modelled native context,
  faults and overwritten pointer slots. The successful driver sequences do
  not remove those interpreter exclusions.
- The new machine fixture uses the actual board, map, TGP and serializers,
  with synthetic memory and the existing differential suite's FIFO program.
  It proves wiring/continuation, not a title's graphics, audio or gameplay.
- A supplementary Linux machine-fixture build in the generic builder stopped
  because its image lacks `zlib.h`; no dependency was installed. The Linux
  FP executable built and ran natively. Full machine-fixture results above are
  macOS results; prior Linux M2B/M2C receipts are separate.
- The CI recipe now includes `check-tgp-machine` with its existing three
  gates. Local checks pass; these unpublished edits have not run in GitHub CI.

## Reproduction

The pinned original is ElSemi 1.1a, SHA-256
`2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc`.
No ROMs or generated game programs are required.

```sh
mkdir -p port/build-m2a-re
clang -O2 -g -std=c11 -fPIC -dynamiclib port/i960/i960.c \
  port/i960/test/shim.c -lm -o port/build-m2a-re/i960-O2.dylib
clang -O2 -g -std=c11 -fPIC -dynamiclib -DTGP_TEST_UNICORN_FLD \
  port/tgp/tgp.c port/tgp/test/shim.c -lm -o port/build-m2a-re/tgp-oracle-O2.dylib
clang -O2 -g -std=c11 -fPIC -dynamiclib port/tgp/tgp.c \
  port/tgp/test/shim.c -lm -o port/build-m2a-re/tgp-production-O2.dylib
port/build-sharc/venv/bin/python tools/qualify_m2a.py \
  port/build-sharc/original/EMULATOR.EXE --libraries port/build-m2a-re \
  --output port/build-m2a-re/new-results
python3 port/i960/test/fp_native.py --exe port/build-sharc/original/EMULATOR.EXE \
  --input port/build-m2a-re/input.bin
make -C port BUILD=build-m2a-re/machine check-tgp-machine
make -C port SHARC=1 TGPX4=1 BUILD=build-sharc-machine -j4 \
  check-tgp-machine check-sharc-machine check-tgpx4-machine check-tgpx4-geometry
```

The existing Linux builder compiled the original-body probe with:

```sh
gcc -DI960_FP_ORACLE -m32 -O2 -Wall -Wextra -Werror -ffreestanding \
  -fno-pie -fno-stack-protector -nostdlib -static \
  -Wl,-Ttext-segment=0x20000000 \
  port/tgpx4/test/linux_original_fp.c port/tgpx4/test/linux_original_fp.S \
  -o original-i960-fp
gcc -O2 -std=c11 -D_DEFAULT_SOURCE port/i960/i960.c \
  port/i960/test/shim.c port/i960/test/fp_runner.c -lm -o portable-i960-fp
```

The original loader maps its unchanged code at the original addresses with
`MAP_FIXED_NOREPLACE`; only the decoded-record/operand buffers are fixtures.
The enclosing runner verifies the EXE hash. Run on physical x86:
`original-i960-fp EMULATOR.EXE < input.bin > original.bin`, then
`portable-i960-fp < input.bin > portable.bin`. Compare with `fp_native.py`,
adding `--native original.bin --portable-output portable.bin --report result.json`
to the generation arguments. On macOS use `--library LIBRARY` instead of
`--portable-output`. No Windows application, imports or translated x86 execution
are involved in the physical AMD receipt.

Native host: AMD Ryzen 5 3400G, Batocera Linux x86-64. Compiler: GCC 12.2.0.
The existing `batocera-remote-core-test` workflow handled checksum verification,
bounded execution, fetching and scoped cleanup. The default M2C version of
the shared oracle rebuilds byte-identically to its previous accepted binary
(`99e28c450f280d8efcd94ee3519fc26608cd56ec577131b60f1673b9c3723a9f`).

## Retained Evidence And Scope

`port/build-m2a-re/` retains baseline/corrected suite logs and JSON receipts,
native result records, build/ABI logs, provenance and small executable run
recipes. Input vectors are reproducible from the tool; task-owned staged EXE
copies, binaries, object files and source snapshots are removed after fetching
the results. Existing original executable, historical evidence, standalone
checkout and installed RetroArch core remain untouched. No commit, push or
release is included.

This scoped qualification group is complete; M30's broader audio/indirect-call
classification remains open. It would be misleading to assign the whole
emulator a completion percentage from these sampled CPU tests. Astra with
High effort remains appropriate for subsequent binary-semantic work.
