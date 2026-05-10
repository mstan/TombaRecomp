# Audit: v2/runner/src/ps1_exe_parser.cpp (+ include/ps1_exe_parser.h)
- LOC: 194 (.cpp) + 109 (.h) = 303 total
- Source: v2 (`F:/Projects/psxrecomp-projects/psxrecomp/runner/src/ps1_exe_parser.cpp`)
- Purpose: PS-X EXE header parser. Reads 2048-byte header, validates magic / load address / entry PC / file size / BSS, exposes `PS1ExeParser::parse_file()` and `parse_buffer()` returning a `std::optional<PS1Executable>`.
- Read date: 2026-05-09
- Read mode: end-to-end, every line, **plus byte-diff against v4 copy**

## Key finding: file is byte-identical between v2 and v4

```
$ diff F:/Projects/psxrecomp-v4/recompiler/include/ps1_exe_parser.h \
       F:/Projects/psxrecomp-projects/psxrecomp/runner/include/ps1_exe_parser.h
$ diff F:/Projects/psxrecomp-v4/recompiler/src/ps1_exe_parser.cpp \
       F:/Projects/psxrecomp-projects/psxrecomp/runner/src/ps1_exe_parser.cpp
(both diffs return empty)
```

v4 already has this file salvaged at `F:/Projects/psxrecomp-v4/recompiler/{include,src}/ps1_exe_parser.cpp`. No drift between the two copies.

## Stub / HLE patterns found

None. Pure header parser with strict validation. No CPU regs, no kernel state, no fakery. The file is well-disciplined:
- Magic check (L11): rejects non-`"PS-X EXE"` files cleanly.
- KSEG0 load-address check (L20): rejects load addresses outside `0x80000000–0x9FFFFFFF`.
- File-size sanity (L29-40): rejects 0-byte and >2MB.
- RAM overflow check (L43-50): rejects `load + size > 0x80200000`.
- BSS overlap check (L91-103): rejects BSS that overlaps code section.
- Soft-warning for entry PC outside loaded range (L62-68) — flags as "may indicate overlay-based loading" without hard-failing. This is a legitimate non-fatal observation; some PS-X EXEs do reference overlay code outside the initial load.

## Genuinely useful patterns / ideas

This is the entire reason the file passed audit on first salvage — it's clean, focused, and validates strictly. Worth referencing when extending the recompiler to handle game EXEs (psxrecomp-game tool work).

## Dependencies (other files this references)

- `<fstream>`, `<cstring>`, `<vector>`, `<optional>`, `<filesystem>` — standard library.
- `<fmt/core.h>` — fmtlib. v4 already uses fmt; not a new dep.
- No CPU/kernel references. Pure parser. ✓

## Verdict: PASS-as-is — but already in v4, so no action

No code lands in TombaRecomp from this file. v4 already has it, identical byte-for-byte. The eventual `psxrecomp-game` tool can use v4's existing copy via `recompiler/include/ps1_exe_parser.h`.

## Recommended action

**Nothing.** v4 has it; it's already correct. Cite this audit verdict in `psxrecomp-game` work to confirm the parser is ready and audited.

**No promotion to extras.cpp.** Parser is framework-side.

**No promotion to game.toml.** Parser handles all PS-X EXEs uniformly via header data; per-game config would only be needed for non-standard EXE variants (Tomba is standard).

## One soft observation (not action)

The "Warning: Entry point outside loaded range — may indicate overlay-based loading" path (L62-68) is a pragmatic but worth noting: if Tomba's main EXE is a thin loader that hot-swaps overlays, the entry point could be inside the EXE's own code (load_address + small offset) but real game logic might live in an overlay. The parser warns and continues; consumer code (psxrecomp-game) needs to handle the overlay case — see the next two audits (`overlay_detector.cpp`, `overlay_manager.cpp`).
