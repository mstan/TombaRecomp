# Audit: v2/runner/src/overlay_detector.cpp + overlay_manager.cpp (combined)
- Files: `overlay_detector.cpp` (295 LOC) + `overlay_detector.h` (58) + `overlay_manager.cpp` (149) + `overlay_manager.h` (122)
- Total: 624 LOC
- Source: v2 (`F:/Projects/psxrecomp-projects/psxrecomp/runner/`)
- Purpose: detect overlays referenced by a PS-X EXE (static byte-pattern analysis), and at runtime load/unload them, plus a PS1-address → C-function-pointer registry for dispatching into recompiled overlay code.
- Read date: 2026-05-09
- Read mode: end-to-end, every line, both files

## Why this audit matters more than the others

v4 has **no overlay support at all**. Tomba is ~280MB of disc data with 2MB of PS1 RAM — overlays are inevitable. This is the first audit so far that covers ground v4 simply doesn't cover. The conclusion is more nuanced than "v4 is ahead, do not import" — there's actual unique territory here.

## Architectural model (v2's approach)

Two-stage:

1. **Static detection** (`overlay_detector.cpp`): scans the main EXE's code section for ISO 9660 filename strings (e.g. `"OVER0.BIN;1"`), filters to overlay-typical extensions (`.BIN`, `.OVL`, `.DAT`, `.PRG`), excludes obvious non-overlays (`SYSTEM.CNF`, `SCUS_*`, `SLUS_*`). For each candidate, searches a 256-byte window for a `LUI; ADDIU/ORI` instruction pair to reconstruct the PS1 RAM load address.

2. **Runtime management** (`overlay_manager.cpp`): given a `vector<DetectedOverlay>`, reads each from the ISO via `CDROMController::ReadFile`, malloc-buffers the data, marks loaded. Maintains a `function_registry_` mapping PS1 addresses to C function pointers — the assumption is the overlay's recompiled C code is statically linked, and `LookupFunction(ps1_addr)` returns the right callable.

## Stub / HLE patterns found

- **`overlay_manager.cpp:91-93`** (`GetOverlayFunction`): `// TODO: Implement in later checkpoint return nullptr;` — real stub, never finished. The function would presumably search the registry by `(overlay_name, address)`, but it's pure no-op.
- **`overlay_manager.cpp:25`**: `malloc(size)` for overlay data; `free` in unload. The buffer holds raw bytes, not recompiled code. The recompiled C is statically linked, not loaded — so `info.data` is just for header inspection / debugging / possibly mod-injection. Not poison, just architectural note.
- **No CPU-side or kernel-state references in either file.** Pure static analysis + runtime registry. Both qualify as framework-side under the audit philosophy.

## Critical architectural gap (NOT poison; design-level concern)

The runtime model has a **multi-overlay-at-same-address problem**:

- Real PS1 overlays often load DIFFERENT code to the SAME PS1 address (e.g. stage 1 code at `0x80100000`, then stage 2 code at the same address after unload+load). The recompiled C output for stage 1 functions and stage 2 functions both have PS1 addresses in the `0x80100000+` range.
- v2's `function_registry_` is a flat `map<uint32_t, FunctionInfo>` indexed by PS1 address. When stage 1 unloads, `UnloadOverlay` removes its functions (L66-72). When stage 2 loads, it presumably re-registers. But there's **no "currently loaded" arbitration** — if both overlays' init code runs `RegisterFunction` at startup (likely, since C statics initialize), only one wins by insertion order. The unload-then-reload dance is fragile.

The model assumes overlays are mutually exclusive AND that registration happens lazily on `LoadOverlay` rather than at static-init time. The code doesn't enforce that. Importing this directly without solving the multi-overlay arbitration would corrupt dispatch on overlay swap.

## Limits of the static detection heuristic

`overlay_detector` will miss overlays loaded by these patterns:
1. **Sector number, no filename string in EXE** — common for compressed / packed disc formats. The detector relies on finding the literal filename text.
2. **Filename in a data table with computed load address** — the LUI/ADDIU search assumes a register-load near the filename. If the address comes from `lw $t0, table($t1)` it won't match.
3. **Self-modifying loader** — the loader code that issues `CdReadFile` may itself be loaded as a runtime stub (which is fine for v4's dirty-RAM interpreter, but the static detector running on the main EXE bytes wouldn't see it).

For Tomba specifically: we don't know yet which mechanism the game uses. **Ghidra analysis of `tomba/SCUS_942.36` (task #9) needs to come first** — it'll surface the overlay loading code and tell us whether v2's heuristic would have found Tomba's overlays. If yes: v2's detector is a reasonable starting point. If no: we need a different detector strategy.

## Genuinely useful patterns / ideas

- **`overlay_detector.cpp:12-88` MIPS opcode validity table**: complete enumeration of valid R3000 opcodes (including COP2/GTE LWC2/SWC2 at 0x32/0x3A). Useful as a reference for any "is this a real MIPS instruction or padding" check the recompiler does. v4's recompiler should already have an equivalent (rabbitizer covers it), but the table is concise documentation.
- **`overlay_detector.cpp:90-164` ExtractFilenames**: ISO 9660 filename extraction by byte-pattern. Reasonable approach. Filters: uppercase / digits / underscore / single dot / `;version`. Worth referring to if v4 ever needs to scan a binary for embedded filenames.
- **`overlay_detector.cpp:166-220` FindLoadAddress**: LUI + ADDIU/ORI pair search. The "two-instruction-window" approach is a standard technique for reconstructing 32-bit immediates. Useful pattern, but limited (see "limits" above).
- **`overlay_manager.cpp:65-72` UnloadOverlay's function-registry cleanup**: iterates the map and removes entries where `overlay_name` matches. Standard.
- **Two-stage architecture itself**: detect-then-manage as separable concerns. Worth keeping if v4 builds overlay support.

## Dependencies

- `ps1_exe_parser.h` (already PASS-as-is in v4) — for `PS1Executable`.
- `cdrom_controller.h` — for `ReadFile`. v4 has its own `cdrom.c` which may or may not expose a `ReadFile` API.
- `<map>`, `<vector>`, `<string>` — stdlib.
- C++ class abstraction — doesn't fit v4's C runtime cleanly, but the recompiler is C++ so the headers could live there.

## Verdict: NEEDS_HUMAN; do not import; revisit after Ghidra analysis of Tomba

Two reasons:

1. **Tomba's overlay mechanism is unknown.** Until task #9 (Ghidra import + analysis) reveals whether Tomba uses filename-string-based overlays, sector-number-based overlays, or some hybrid, we can't tell whether v2's detector would catch what Tomba needs. Importing a heuristic that doesn't apply is wasted work.
2. **The runtime manager is incomplete.** `GetOverlayFunction` is a stub. The multi-overlay-at-same-address arbitration is missing. Building on top would require designing the missing pieces — at which point we're rewriting, not salvaging.

## Recommended action

**Defer this audit's conclusion until task #9 (Ghidra Tomba import) is done.** Then:

- If Tomba uses filename-string-based overlay loading: v2's detector heuristic is a useful starting point. Re-implement in v4's recompiler-side as a static-analysis pass during `psxrecomp-game` (task: extend `recompiler/src/main_psx.cpp` to scan code for overlay references; emit a list to a manifest file like `tomba_overlays.json`). Don't import v2's C++ class — re-derive against v4's existing recompiler infrastructure.
- If Tomba uses sector-based or other mechanisms: write a different detector. v2's code becomes irrelevant.
- Either way, the runtime manager (overlay_manager.cpp) does NOT travel as-is. The function-registry model needs the multi-overlay-arbitration question answered before any code lands.

**This means: hold this audit open as "pending Ghidra analysis."** Update the verdict file once we know.

## Promotion candidates

- **`game.toml` `[overlays]` section** (FUTURE): if/when overlay support lands, the manifest-of-detected-overlays should live in `game.toml` (one entry per overlay with name, load address, source sector / file). The detector becomes a tool that *generates* this section; the runtime *reads* it. Don't synthesize at runtime — make it config.
- **Framework feature `runtime/src/overlay_loader.c`** (FUTURE): the runtime side of overlay loading should be generic in psxrecomp-v4, not per-game in `extras.cpp`. Dispatch-with-current-overlay-region awareness lives in the framework, not in TombaRecomp.

## Open questions for next session (or after task #9)

1. Does Tomba's main EXE contain literal `OVERN.BIN` style filename strings? (Ghidra grep)
2. Does the EXE have a `LoadOverlayFromCD` style function that's called from multiple sites with different filename arguments? (Ghidra cross-reference analysis)
3. What's the address range overlays load to? (Tomba's main EXE likely loads at `0x80010000` per PS1 convention; overlays at `0x80100000+`?)
4. How many overlays does Tomba have, roughly? (5-20 = manageable; 50+ = needs more thoughtful tooling)
5. Are stage-data and stage-code separate overlays, or combined?
