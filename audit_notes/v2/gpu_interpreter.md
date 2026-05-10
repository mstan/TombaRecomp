# Audit: v2/runner/src/gpu_interpreter.cpp
- LOC: 1160
- Source: v2 (`F:/Projects/psxrecomp-projects/psxrecomp/runner/src/gpu_interpreter.cpp`)
- Purpose: GP0 command FIFO + per-command parser/executor; GP1 command handler. Translates GPU MMIO writes into renderer calls (renderer is a separate abstraction passed by pointer).
- Read date: 2026-05-09
- Read mode: end-to-end, every line

## Stub / HLE patterns found

- **L85**: `fprintf(stderr, "Warning: GP0 FIFO overflow, command dropped\n");` — printf debugging in production source. Violates CLAUDE.md §3.
- **L285**: `fprintf(stderr, "Warning: Unknown GP0 command 0x%02X\n", opcode);` — same.
- **L403**: `fprintf(stderr, "Warning: Unknown GP0 misc command 0x%02X\n", opcode);` — same.
- **L756**: `fprintf(stderr, "Warning: CPUToVRAM dimensions %dx%d overflow, skipping\n", ...);` — same.
- **L804**: `fprintf(stderr, "Warning: VRAMToCPU dimensions %dx%d overflow, skipping\n", ...);` — same.
- **L847**: `fprintf(stderr, "Warning: Unknown GP0 environment command 0x%02X\n", opcode);` — same.
- **L951**: `fprintf(stderr, "Warning: Unknown GP1 command 0x%02X\n", opcode);` — same.

Seven separate stderr-print sites. None are fatal-abort sites where CLAUDE.md §3 allows exception. All would need conversion to a debug-server ring entry before any reuse.

## Bit-encoding errors in GP0(E1h) handler

This is the more important finding. **`HandleDrawMode` (L854-870) misreads three GP0(E1h) bits**, propagating wrong state into draw_mode:

| GP0(E1h) bit | nocash spec | v2 reads as | Real meaning | Severity |
|---|---|---|---|---|
| 11 | `texture_disable` | `texpage_y_base_bit1` | Texture disable (when GP1(09h) bit 0 set) | Bug — affects games that use texture-disable feature |
| 12 | `texture_disable` (per L863, but spec says it's textured-rect X-flip) | `texture_disable` | X-flip for textured rectangles | Bug — X-flipped sprites would render wrong |
| 13 | `h_flip` (per L864) | `h_flip` | Y-flip for textured rectangles | Bug — Y-flipped sprites mis-mapped to bit 13 instead of being a separate flag |

There is no "texpage Y bit 1" on real PS1 — texpage Y is a single bit (×256, so 0 or 256). v2's `texpage_y_base_bit1` is a phantom field perpetuated through:
- `gpu_state.h` L18 (the field declaration)
- `gpu_state.cpp` L131 (composes bit 15 of GPUSTAT from this phantom — confirmed bug in `gpu_state.md`)
- `gpu_interpreter.cpp` L862 (writes phantom from GP0(E1h) bit 11)
- `gpu_interpreter.cpp` L1139 (`BuildDrawState` ORs phantom into `texpage_y_base` for the renderer)

**Net effect on Tomba:** if Tomba uses textured rectangles (very likely — it's a 2D-sprite-driven platformer), v2's renderer receives a corrupted texpage_y_base value (1-bit value masquerading as 2-bit) AND a misplaced texture_disable flag AND treats X-flip as if it were texture-disable. This is silent visual corruption.

## Other issues

- **L1126-1128 `ExtractTexpage`**: `y = ((word >> 20) & 1) | (((word >> 27) & 1) << 1);` — combines bits 20 (correct: Y base) and 27 (NOT Y; bit 27 is GP0 polygon "raw texture" flag, unrelated to texpage Y). Either v2 invented this combination (likely wrong) or a quirk in some homebrew test. Either way, the OR with bit 27 is suspicious and should not propagate.
- **L537, 764, 809**: heap-alloc-per-call pattern (`new Vertex[256]`, `new uint16_t[pixel_count]`). Performance smell but not poison.

## Genuinely useful patterns / ideas

- **L144-243 `ProcessGP0FIFO`**: Two-state FIFO drain (normal mode vs streaming CPU→VRAM mode) with proper state-machine resets. The streaming-into-staging-then-uploading model (`cpu_vram_staging_` vector) is cleanly factored. v4's gpu.c handles MMIO writes one-at-a-time without a FIFO; *if* v4 ever needs DMA-batched GP0 transfers, this is a useful reference for how to drain a multi-word transfer cleanly.
- **L290-356 `GetGP0ParameterCount`**: Returns expected param count from command opcode, including the variable-length polyline case (`return -1`) and the CPU→VRAM-handled-specially case. v4's gpu.c likely encodes these inline; this consolidates them in one place. Worth checking whether v4 has equivalent param-count introspection.
- **L66-79 `AbortStreaming`**: Comment notes a real-bug fix where aborting a CPU→VRAM mid-transfer must reset header-accumulation state (`current_command/params_received/params_needed`). v4 may want to verify it has equivalent reset on similar abort paths.
- **L1095-1107 sign-extend X/Y**: `if (x & 0x400) x |= 0xF800;` — correct 11→16 bit sign extension. Worth verifying v4 does the same.
- **L1049-1091 `HandleGP1GetGPUInfo`**: GP1(10h) returns texture_window/draw_area/draw_offset/GPU-version through GPUREAD. This is real PS1 hardware behavior; if v4's gpu.c omits GP1(10h), some games will read 0 from GPUREAD when expecting valid info.

## Dependencies (other files this references)

- `gpu_interpreter.h` (its own header) — defines GPUInterpreter class, Vertex struct, DrawState struct, GPURenderer abstract base.
- `gpu_state.h` — already audited (verdict: NEEDS_HUMAN, do not import).
- `gpu_renderer.h` — abstract `GPURenderer` interface (DrawTriangle, DrawLine, DrawRectangle, UploadToVRAM, etc.).
- Implementations: `opengl_renderer.cpp` (the concrete renderer — pending audit).
- External: `extern "C" uint32_t g_ps1_frame;` — global frame counter, presumed defined elsewhere in v2's runner.
- C++ stdlib: `<cstdio>`, `<cstring>`, `<vector>` (implicit via class member).

## Verdict: NEEDS_HUMAN

Substantial value (FIFO state machine, parameter-count map, GP1(10h) info handler) BUT:
1. Three GP0(E1h) bit-shift bugs that would cause silent visual corruption.
2. Seven `fprintf(stderr)` sites violating CLAUDE.md §3.
3. Heap-alloc-per-call patterns (perf, not poison).
4. C++ class abstraction doesn't fit v4's C codebase.

The bit-shift bugs alone disqualify bulk import — any importer would have to fix them, at which point we're not "salvaging," we're "rewriting v2 to be correct."

## Recommended action

**Do NOT import.** Use as a reference checklist when verifying v4's gpu.c. Specific items to check against v4:

1. **GP0(E1h) bit semantics** — verify v4 reads bits 11=texture_disable, 12=textured-rect-X-flip, 13=textured-rect-Y-flip per nocash. v2 had three bugs here; v4 should be checked.
2. **GP0 FIFO behavior on overflow** — v2 drops commands; v4 needs to either match or do something demonstrably correct.
3. **GP1(10h) GetGPUInfo handler** — verify v4 returns texture_window/draw_area/draw_offset/GPU-version per nocash spec when GP1(10h) is written.
4. **CPU→VRAM streaming abort** — verify v4 resets accumulation state if a transfer aborts mid-stream.
5. **Polyline terminator** — v2 detects `0x55555555` and `0x50005000` (L545); verify v4 detects both.
6. **Sign-extension of GP0 polygon vertex X/Y** — v2 sign-extends 11-bit to 16-bit; verify v4 does the same.

If any of those checks find v4 missing, the fix lands in `runtime/src/gpu.c` against v4's existing API, **not** by importing this v2 file. The v2 code is a reference for *what to check* and *what nocash says*, not source to port.

**No promotion to extras.cpp.** GPU command parsing is hardware sim, framework-side.

**No promotion to game.toml.** No per-game config emerges.

**Future work (outside this audit's scope):** the polyline terminator detection (`0x55555555`/`0x50005000`), if not already in v4, is the kind of one-bit fact that should live in `runtime/src/gpu.c` as a constant with a comment citing the v2 file as the source of the discovery. That would be the proper-solution path if a check finds v4 missing it.
