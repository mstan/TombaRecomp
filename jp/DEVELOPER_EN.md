# Four-region launcher / Japan native port handoff

Apply the three binary-capable patches to the exact upstream commits recorded
in `SOURCE_BASES.json`, in their respective repositories. Initialize the pinned
nested submodules. Patch filenames retain the earlier `-Europe` suffix but
contain the complete committed US/EU/JP integration deltas. No unpublished
remote branch is required. Update your own submodule commits/gitlinks after
integration. No source or package has been published or sent upstream.

The common launcher is the original UI with the existing generic regional
catalog and backend handoff. The four profiles contain verified serial/size/full
track SHA-256 identities. No new launcher implementation is added for Japan or
USA. The two EU RC2 executable files are reused without changes. The USA host
is rebuilt against the same common framework, preserving its existing plugins.
Each backend keeps independent settings and `saves/<serial>` cards. The official
memory-card picker functions have not been changed by the Japan integration.

## Build requirements and Japan reproduction

Windows x64, Python 3.11+, Clang/clang++, CMake and Ninja are required. Set
`TOMBI_TOOLCHAIN_BIN` to their bin directory if necessary. Recursively fetch the
pinned sources first; supply the pinned libwebp source tree or allow the normal
framework dependency fetch. OpenBIOS is supplied by the framework; select only
OpenBIOS, not a Sony BIOS. Original discs are private read-only inputs.

```powershell
cmake -S psxrecomp/recompiler -B build-eu-tools -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build-eu-tools --target psxrecomp-game psxrecomp-bios -j 3
cmake -DOUT=psxrecomp/runtime/include/overlay_codegen_hash.h -DPSXRECOMP_CODEGEN_HASH_ROOT=psxrecomp -P psxrecomp/runtime/hash_codegen.cmake
python -I -B jp/build.py --enhancements --disc "path/to/Japan.cue" --webp-source "path/to/pinned/libwebp"
python -I -B jp/build_aot.py --config jp/pc.toml --all-areas --flavor 2 --work-dir build-jp/rc2/aot
python -I -B jp/build.py --enhancements --player --disc "path/to/Japan.cue" --webp-source "path/to/pinned/libwebp"
```

The scripts check full original-disc identity and original boot/overlay bytes.
They build separate private QA and production hosts; old prototype output paths
remain untouched. The production build has no debug server. Existing shared
runtime PGXP support is selected with the wrapper's PGXP keyword. Japanese geometry, hybrid and widescreen remain unregistered. The shared
Seamless and FMV implementations use verified Japanese profiles; both default off.

`jp/overlay-contracts.json` explains the 14 byte-checked data tails needed to
prevent native discovery from treating data as code. The remaining original
code/data and safe fallback are preserved. See `JAPAN_HANDOFF_EN.md` for exact
regional blockers and the limits of the evidence. 24 translated overlay files
and successful first-area play do not establish completion of the whole game.

## European and USA backends / combined staging

The previous EU build and test workflow remains `europe/build.py` and is
documented in `EU_DEVELOPER_EN.md`. Reuse a pristine audited EU RC2 stage at
`dist/TombiRecomp-Europe-Windows-x64-RC2`; do not reuse a played installation.
Earlier isolated EU rebuild and all-ten-language results are retained rather
than repeated for unchanged executable bytes.

For USA, use the existing upstream preparation/code-generation workflow with
`game.toml`, then configure the root project in `build-regional/us-player/native`
with Release, `PSX_DEBUG_TOOLS=OFF`, `PSX_PGXP_VARIANT=OFF`,
`PSXRECOMP_BIOS_STEMS=OpenBIOS`, `BUILD_TESTING=OFF`, and the same Clang toolchain.
Build target `psx-runtime`. Use `tools/build_us_aot.py` and `aot/overlays.json`
for original-disc native inputs. This candidate reuses 176 native pairs from
the official USA cache, validated against a newly extracted 25-recipe inventory
with `audit_aot_cache.py` and the current compiler/configuration. The stage
helper expects that private cache copy at `build-regional/us-cache-copy` and
the resulting receipt at `build-regional/us-audit-full/audit.json`. It verifies
artifact hashes again before copying. Legacy caches are not blindly trusted.
A fresh differently partitioned native cache can require adapting the expected
pair count in staging/audits; counts are packaging assertions, not a reason to
alter original bytes or suppress a failing producer.

`python -I -B jp/stage_regional.py --enhancements --output dist/TombaRecomp-Regional-Japan-RC2` assembles a NEW four-region stage. It strips
debug paths only from new copied binaries, copies only required seed inputs,
and excludes user selections/cards, ROMs and developer logs. Keep all licenses
and the runtime overlay toolchain. These embedded fallback tools are needed
for portable execution; no system compiler/Python installation is needed.

## Verification and isolated rebuild

```powershell
python -I -B jp/acceptance.py --name fresh-default --opengl --build-dir build-jp/rc2/qa/native --config jp/pc.toml --seamless off
python -I -B jp/acceptance.py --name fresh-combined --opengl --build-dir build-jp/rc2/qa/native --config jp/pc.toml --pgxp --seamless on --fmv-skip
python -I -B jp/package_test.py --package "path/to/Windows.zip" --name fresh-package --all-regions
python -I -B jp/rebuild.py --enhancements --handoff "path/to/developer-folder" --name fresh-isolated
```

The acceptance tests use normal controller sequences, status reads and internal
framebuffer capture. There are no game-state writes or desktop actions. Each
uses new private cards. Install Unicorn 2.1.4 into a private test environment to
run `jp/test_codec.py` (638 files, two fill patterns, original Japanese decoder).
The HD installer fixture is shared with `eu/tests/test_hd_install.py`, using
`--game-id SLPS-01144` and the existing C++ test fixture binary.

The isolated reconstruction applies all three patches to official source
archives, rebuilds compiler and Japanese player, regenerates boot C and extracts
original overlay recipes again. Reused native DLLs pass fresh ABI, pair, bounds
and original-byte guard audits. It does not claim that every DLL was recompiled
or that unchanged USA/EU hosts were rebuilt in that run. Reports distinguish
previous evidence, new automated checks and owner-confirmed prototype tests.

Use `europe/audit.py --kind regional` for the player directory and ZIP, and
`--kind developer` for this handoff. Both archives must match their full staged
file manifests and pass independent private-path/card/disc scans. Refer to
`MANUAL_TESTS_DE.md` for the remaining area-transition/return and final-device
acceptance. Saving/loading on the earlier prototype was already owner-confirmed.

## RC2 regional implementation and targeted tests

See RC2_MOD_REVIEW_EN.md. Generate profiles with `jp/seamless_profile.py` and
`jp/fmv_profile.py`; CMake runs both automatically in enhancement builds.
The existing EU loader, C++ resident preparation and FMV plugin remain shared.
The Japanese source generator pins the common loader hash, exact original
instructions, request descriptors, protected memory and callback contracts.
It removes the EU-only language/GP list exception and narrows skipped yields to
same-batch loading states. Script waits, movie streams, card code and clock stay
original. Failed preparation or a rejected request retains the original loader.

Run the `tomba-jp-loader-tests` and `tomba-jp-prepare-tests` CMake targets in the
private QA build. The latter takes a copied JP CUE and private cache directory;
its optional fourth argument emits codec-state CSV for `jp/test_codec_state.py`.
`jp/test_fmv_teardown.py` checks 22 isolated original-MIPS teardown paths using
Unicorn 2.1.4. Offline fixtures are explicitly separate from controller-only
regular gameplay acceptance. `jp/card_probe.py` copies owner input cards,
exposes only pad inputs/read-only diagnostics and verifies original hashes.
Never distribute its private outputs or any memory cards.

Old `jp/game.toml` and default build paths remain usable for reproducing RC1.
RC2 uses `jp/pc.toml`, four native filter entries and a distinct cache ABI tag.
Never mix RC1 and RC2 translation artifacts without current audits.
