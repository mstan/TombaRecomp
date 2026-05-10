# Audit: v2/runner/src/iso_reader.cpp + cdrom_stub.cpp
- Files: `iso_reader.cpp` (455 LOC) + `iso_reader.h` (162) + `cdrom_stub.cpp` (28) + `cdrom_stub.h` (18)
- Source: v2 (`F:/Projects/psxrecomp-projects/psxrecomp/runner/`)
- Read date: 2026-05-09 / 2026-05-10
- Read mode: diff vs v4 (iso_reader); end-to-end (cdrom_stub)

## iso_reader.cpp — already in v4 with minor portability tweak

```
$ diff F:/Projects/psxrecomp-v4/runtime/src/iso_reader.cpp \
       F:/Projects/psxrecomp-projects/psxrecomp/runner/src/iso_reader.cpp
< auto ends_with = [](const std::string& s, const std::string& suffix) { ... };
< if (ends_with(filename, ".cue") || ends_with(filename, ".CUE")) {
---
> if (filename.ends_with(".cue") || filename.ends_with(".CUE")) {
```

The only divergence is that v4 uses a lambda implementation of `ends_with` (compatible with C++17) while v2 uses the C++20 `std::string::ends_with` method. v4's choice is a portability fix — the underlying logic is identical. **PASS**, already in v4.

No further action.

## cdrom_stub.cpp — thin C-API wrapper, not import target

28 LOC. Despite the name "stub", it's not a fake-implementation stub in the audit-philosophy sense. It's a 4-function `extern "C"` wrapper around v2's C++ ISOReader/xa_audio/fmv_player/spu subsystems:

- `psx_cdrom_init(cue_path)` — opens ISO via `ISOReader::Open`, initializes XA audio + FMV player + SPU.
- `psx_cdrom_read_sector(lba, buffer)` — reads sector via `ISOReader::ReadSector`.

### Issues

- **L14, L17**: `fprintf(stderr, ...)` — CLAUDE.md §3 violation (printf debugging in production source).
- **L18-20**: tightly couples `xa_audio_init`, `fmv_player_init`, `spu_init` to CD-ROM open. v4 already initializes SPU separately at runtime startup; coupling these would conflict. Not a poison pattern, just architectural mismatch.
- The file presumes v2's particular subsystem ownership model (each subsystem has one global instance, init-once-on-cdrom-open). v4 has its own init sequence in `runtime/src/main.cpp`.

### Verdict: BLOCK (don't import the file as-is)

The file is structurally tied to v2's runtime architecture. v4 already has its own CD-ROM init path (currently `cdrom_init(NULL)` per `runtime/src/main.cpp:352`). The salvageable idea — "open disc, init dependent subsystems" — needs to be re-derived against v4's architecture, not imported.

## Recommended action

**For iso_reader**: nothing. v4 already has it.

**For cdrom_stub**: when implementing the `--disc PATH` CLI flag in v4 (Section B4 of the plan), wire `cdrom_init(cue_path)` to call `ISOReader::Open(cue_path)` — but DO NOT couple xa_audio/fmv_player/spu init to that path. Keep them independent in v4's init sequence. Re-derive against v4's architecture.

**No promotion to extras.cpp.** CD-ROM init is framework-side.

**No promotion to game.toml.** The `--disc` flag handles per-game disc path; no further config needed.
