# GPU Stack Audit Summary — v2

## Decision (2026-05-09): SW-only for parity, GL as future option

User confirmed: keep both renderer options open. For the Tomba parity milestone, v4's existing SW renderer (`runtime/src/gpu.c` + `gpu_sw_renderer.c`) is the ground truth. A GL renderer is a Phase-7+ enhancement project, not a parity-scope dependency.

Architectural rationale (lives in `audit_notes/v2/_gpu_renderer_decision.md`):
- SW is hardware-faithful by construction; GL inevitably diverges (FP, vendor differences, shader-side approximation of PS1 blend modes).
- Beetle PSX oracle uses SW; pixel-for-pixel diff stays meaningful only if v4 is also SW.
- Cost of supporting both: doubled test surface, ambiguous "ground truth" when oracle-comparing.
- Future GL renderer can plug in via the `GPURenderer` abstract-base pattern v2 already prototyped — that abstraction is the salvage value, not the GL impl itself.

## Audit verdicts

| File | LOC | Verdict | Note |
|---|---:|---|---|
| `gpu_state.cpp` (+ `.h`) | 181 + 135 | NEEDS_HUMAN; do not import | v4 ahead of v2 on every divergent GPUSTAT bit. v2 has phantom `texpage_y_base_bit1` field (v4 has correct `texture_disable`). |
| `gpu_interpreter.cpp` | 1160 | NEEDS_HUMAN; do not import | Three GP0(E1h) bit-shift bugs (bits 11/12/13). Seven `fprintf(stderr)` violations. Genuine value as v4-side check items, not import targets. |
| `opengl_renderer.cpp` | 1962 | DEFERRED to Phase-7+ GL-renderer investigation | Architecturally out of scope for parity. To be audited when/if GL renderer is greenlit as a separate workstream. |

## Items surfaced as v4-side check candidates (NOT import work)

If/when these become priority for v4:

1. **GP0(E1h) bit semantics** — verify `runtime/src/gpu.c` reads bits 11=texture_disable, 12=textured-rect-X-flip, 13=textured-rect-Y-flip per nocash. (v2 had three bugs here; v4 should be confirmed.)
2. **GP1(10h) GetGPUInfo handler** — verify v4 returns texture_window/draw_area/draw_offset/GPU-version per nocash spec. v2 implements this in `gpu_interpreter.cpp:1049-1091`; if v4 omits, games reading GP1(10h) get 0.
3. **Polyline terminator detection** — v2 detects both `0x55555555` and `0x50005000`. Verify v4 detects both.
4. **CPU→VRAM streaming abort path** — v2 resets accumulation state on abort. Verify v4 has equivalent.
5. **GP0 polygon X/Y sign-extension** — v2 sign-extends 11→16 bit (`if (x & 0x400) x |= 0xF800`). Verify v4.

These are check-items, not port-items. Each fix lands in v4-side gpu.c, citing this audit as the discovery source.

## Net stack-level recommendation

- **Do not import any file from v2's GPU stack.**
- **Do not pursue GL renderer for parity milestone** — defer as Phase-7+ project.
- **Do open a v4-side GPU correctness pass** at the user's discretion, using the 5 check-items above as the agenda. That work would happen in v4, not in TombaRecomp.

## Scope-of-this-audit caveat

`opengl_renderer.cpp` (1962 LOC) was NOT read end-to-end this session. The decision to defer was made after the first two files revealed v4 is correct or ahead, and that the stack-level value of v2's GPU work is not in salvageable code. Should the GL-renderer-as-future-option decision crystallize, the GL audit becomes its own task with its own audit note.
