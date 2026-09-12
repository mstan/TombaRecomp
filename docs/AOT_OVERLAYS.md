# Tomba! original-disc AOT overlays

Tomba! USA (`SCUS-94236`) can be pre-sharded without a decompilation. The
original disc supplies 25 distinct position-fixed overlay images: 17 area
images and eight support images. All use load address `0x800E7388`.

This uses the shared psxrecomp [AOT sharding workflow](../psxrecomp/docs/AOT_SHARDING.md).
Tomba does not need a new decompressor or a runtime loader replacement. The
title-specific verifier checks the supported disc, its loader instructions,
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
python psxrecomp/tools/aot_overlay_spike/extract_generic.py --game-toml game.toml --recompiler RECOMPILER --no-bios-resident --out build-aot-inputs/generic.json --tmp build-aot-inputs/tmp
python tools/prepare_aot_inventory.py --framework-root psxrecomp --disc "disc/Tomba! (USA).cue" --generic-records build-aot-inputs/generic.json --out-dir build-aot-inputs/verified
python tools/build_aot_cache.py --framework-root psxrecomp --recompiler RECOMPILER --inventory build-aot-inputs/verified/runtime-input-inventory.json --out-dir build-aot-cache --gcc gcc --jobs 2
```

Create `build-aot-inputs` first. The cache output must be empty. Each image is
compiled separately to avoid nominating unrelated area entries during initial
discovery. The final audit checks every native pair and every guard against
original source bytes, excluding the alignment prefix. Recipes and generated
code contain game data and remain local; only metadata receipts belong in Git.

Stage the audited `SCUS-94236` directory under the runtime's adjacent `cache`
directory. Windows and Linux require separate native builds. Set
`PSX_OVERLAY_AUTOCOMPILE_OFF=1` during spot checks to establish that the prebuilt
cache is responsible for native execution. Interpreter fallback remains active.

For a useful playtest, load a memory-card save, move/jump/interact, then cross
between the Village of All Beginnings and a neighboring area and return. Check
movement, graphics, audio, transition behavior, and performance. Visit other
available areas as convenient; historical save-state files may be incompatible
with the current runtime, so ordinary memory-card saves are preferable.

## Current validation (2026-09-11)

The clean Windows build produced 72 native pairs with 4,536 manifest entry
rows. Every pair passed the ABI/export audit, and every guard matched known
original-disc bytes. All 25 images have matching native entries; see the
[per-image receipt](aot_coverage/SCUS-94236_windows_audit.json) and
[disc inventory](aot_coverage/SCUS-94236_disc_inventory.json).

An isolated OpenBIOS boot with runtime compilation disabled rendered the intro
and executed the prebuilt options overlay: 27 registered entries and advancing
native calls, with no manifest/candidate overflow. Full gameplay and area
transitions await the owner's spot checks. Linux shards have not been built in
this discovery task; native artifacts are platform-specific.
