# Tomba! original-disc AOT overlays

Tomba! USA (`SCUS-94236`) can be pre-sharded without a decompilation. The
original disc supplies 25 distinct position-fixed overlay images: 17 area
images and eight support images. All use load address `0x800E7388`.

This uses the shared psxrecomp [AOT sharding workflow](../psxrecomp/docs/AOT_SHARDING.md).
Tomba does not need a new decompressor or a runtime loader replacement. The
declarative profile checks the supported disc, its loader instructions,
duplicate files, and exact source extents; the framework discovers entries,
compiles native shards, and validates live bytes before dispatch.

## Evidence and limits

- Supported data track SHA-1: `c259ec7ff6ef4163913991f4e4db2eff71702818`.
- Original executable loader `0x80021D70` handles type `0xF0` by selecting
  `0x800E7388` at `0x80021E5C` / `0x80021E60`, then queues that destination.
  The read path at `0x8002155C` consumes the queued destination for raw read
  modes 1/2. This independently corroborates the file-based link-address fit.
- 22 images pass the generic header-table heuristic. Its interpretation of
  the first word as a pointer count is not established for Tomba: the support
  images instead begin with sequential values `0x31` through `0x38`, and
  `GOVER.BIN` begins with `0x35` followed by only six pointers. Treat the
  generic scan as entry discovery, not a complete description of this header.
  Two more images, `DSPSUB2.BIN` and `OPTSUB00.BIN`, pass the stricter raw-code
  address fit. Duplicate copies in
  `AREA*` and `SYSTEM` directories are checked byte for byte.
- `GOVER.BIN` is recovered using `SYS/LDSYS.BIN` descriptor `+0x1C24`: file ID
  215, overlay type `0xF0`, direct read mode 2. The executable's file table at
  `0x800791A0 + 215*8` matches its ISO LBA and size. Its small code body also
  independently votes for the loader's exact address. This avoids lowering
  the generic raw-code threshold just to accept a small title-specific file.
- Area images: `X00`, `X01`, `X02`, `X03`, `X04`, `X05`, `X06`, `X08`, `X09`,
  `X10`, `X11`, `X13`, `X14`, `X16`, `X17`, `X18`, `X19` (all `.BIN`).
- Support images: `DSPSUB`, `DSPSUB2`, `DSPSUB3`, `INFO`, `INFO2`, `INFO3`,
  `OPTSUB00`, `GOVER` (all `.BIN`).
- Cache keys start at page `0x800E7000`. The 904-byte alignment prefix is
  outside the established source bounds and must never supply function guards.
- The historical scatter-load hypothesis and gameplay cache coverage report
  are not correctness evidence for these recipes. No captured RAM, executed-PC
  list, historical native shard, or old coverage percentage is used as input.

The 25-image inventory is not proof of every executable byte or dispatch entry
being covered. Indirect targets, code modified after loading, undiscovered
formats, and partial-load combinations can still fall back. The guard audit
checks source-byte provenance and ABI validity; it does not prove native-code
semantics. Gameplay transitions remain the final acceptance check.

## Reproduce locally

Use the framework revision pinned by this repository, with a freshly built
`psxrecomp-game` and the matching runtime. Commands below use shell-neutral
single-line syntax; replace `RECOMPILER` with its native executable path.

```text
python psxrecomp/tools/aot_overlay_pipeline.py extract --profile aot/overlays.json --game-toml game.toml --recompiler RECOMPILER --work-dir build-aot-inputs
python psxrecomp/tools/aot_overlay_pipeline.py release --profile aot/overlays.json --game-toml game.toml --runtime-config packaging/release/game.toml --recompiler RECOMPILER --work-dir build-aot-inputs --stage build-aot-stage --gcc gcc --workers 3
```

The shared pipeline freshly extracts the disc, validates `aot/overlays.json`,
compiles each recipe independently, audits every native pair and checks every
image has native entries. It then stages all audited pairs and an audit receipt.
Only the profile and receipts belong in Git; recipes contain original game data.
Windows and Linux require separate native builds. Set
`PSX_OVERLAY_AUTOCOMPILE_OFF=1` during spot checks to distinguish prebuilt native
execution from runtime compilation. Interpreter fallback remains active.

`tools/package_release.ps1`, `tools/package_appimage.sh`, and
`scripts/package_setup_release.sh` all require this pipeline. Skipping base
regeneration or an already completed runtime build never skips disc extraction
or AOT auditing. There is no historical-cache substitute or partial-build override.
For CI, `PSXRECOMP_DISC_ARCHIVE_URL` must privately supply a ZIP with
`Tomba! (USA).cue` and its referenced `Tomba! (USA).bin` at its root. CI places
these under `disc/`; the profile verifies the data-track hash. The ZIP is an
input only and is never included in release assets. Local release scripts use
the owner's disc at the path in `game.toml` without that CI secret.

For a useful playtest, load a memory-card save, move/jump/interact, then cross
between the Village of All Beginnings and a neighboring area and return. Check
movement, graphics, audio, transition behavior, and performance. Visit other
available areas as convenient; historical save-state files may be incompatible
with the current runtime, so ordinary memory-card saves are preferable.

## Current validation (2026-09-11)

The v0.13.0-alpha Windows and Linux builds each produced 196 native pairs
with 8,213 manifest entry rows for the packaged configuration. Every pair passed the ABI/export audit, and every guard matched known
original-disc bytes. All 25 images have matching native entries; see the
[Windows receipt](aot_coverage/SCUS-94236_windows_audit.json),
[Linux receipt](aot_coverage/SCUS-94236_linux_audit.json) and
[disc inventory](aot_coverage/SCUS-94236_disc_inventory.json).

Isolated OpenBIOS boots with runtime compilation disabled rendered the Windows
intro and booted the Linux AppImage. The preceding discovery build also executed
the prebuilt options overlay: 27 registered entries and advancing native calls,
with no manifest/candidate overflow. Full gameplay and area
transitions await the owner's spot checks. The v0.13.0-alpha release builds and audits platform-specific shards afresh
for both Windows and Linux; each package contains its resulting audit receipt.
