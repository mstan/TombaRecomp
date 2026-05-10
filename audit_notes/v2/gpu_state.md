# Audit: v2/runner/src/gpu_state.cpp (+ include/gpu_state.h)
- LOC: 181 (.cpp) + 135 (.h) = 316 total
- Source project: v2 (canonical at `F:/Projects/psxrecomp-projects/psxrecomp/`)
- Purpose: Pure state-management module — `struct GPUState` plus `Reset()` and `UpdateGPUSTAT()` methods. No command processing, no rendering, no MMIO routing. Just the data structure and the GPUSTAT bit-composition.
- Read date: 2026-05-09
- Read mode: end-to-end, every line

## Stub / HLE patterns found

- **L124-125** (`gpu_state.cpp`): `// Bit 13: Interlace field (always 0 for now)` followed by commented-out write. Admission of incompleteness — real PS1 GPU toggles bit 13 each scanline in 480i mode. Games polling this bit see a constant 0.
- **L143-144**: `// Bit 24: Interrupt request (not yet implemented, always 0)` — GPU IRQ-on-GP0(1F) (vsync IRQ) is hardcoded off. Affects games that explicitly request GPU IRQs (rare but exists).
- **L177-178**: `// Bit 31: Drawing odd/even lines (interlace) — Always 0 for now` — interlace tracking absent. Same family of poison as L124-125. Games polling this for v-sync timing (some 480i titles) will see constant 0.

These are textbook "for now" patterns. They don't synthesize game state (the file doesn't touch CPU regs / kernel data), but they admit GPUSTAT is incomplete in two specific bits.

## Genuinely useful patterns / ideas

- **L14-66 of `.h`**: clean struct decomposition — `DrawMode`, `TextureWindow`, `DrawingArea`, `DrawingOffset`, `MaskSettings`, `DisplayControl`, `VRAMTransfer`. Each maps 1:1 to a documented PS1 GPU register block (GP0(E1h), GP0(E2h), GP0(E3h), GP0(E4h), GP0(E5h), GP0(E6h), GP1). v4's `runtime/src/gpu.c` uses flat C state — *might* benefit from this organization if v4's GPU code grows complex enough to warrant grouping. Pure organizational; doesn't bring in poison.
- **L96-179 of `.cpp`**: `UpdateGPUSTAT()` is a thorough bit-by-bit composition of the GPUSTAT register from internal state, with citations to documented bit positions and meanings. Useful as a *reference* when verifying v4's GPUSTAT path is correct. Worth diffing against v4's GPUSTAT logic to see if v4 is missing any bits.
- **L23**: GPUSTAT default `0x14802000` — bits 26 (ready for command) + 28 (ready for DMA) + 14 (top of stable bit pattern). v4's BIOS reset path can verify against this.
- **L61-64**: NTSC default display ranges `0x200..0xC00` H, `0x10..0x100` V. Hardware-faithful initial values; useful sanity check against v4's gpu reset code.

## Dependencies (other files this references)

- `<cstdint>`, `<cstring>` — standard library only.
- The `.h` is consumed by `gpu_interpreter.cpp`, `opengl_renderer.cpp`, and likely the renderer/runtime glue.
- No CPU-side or kernel-state references. Self-contained.

## Verdict: NEEDS_HUMAN

The file is hardware-sim only — no CPU regs, no kernel state, no fake event delivery. The stubs are GPUSTAT-bit-level admissions of incompleteness, not architectural poison. But they're real, and the file is C++ with namespacing that doesn't fit v4's C codebase.

## Recommended action

**Do NOT import the file.** Two reasons: (1) v4 already has working `runtime/src/gpu.c` in C; importing C++ classes with the same purpose creates parallel codepaths. (2) The three "always 0 for now" stubs would silently regress v4 if it currently models any of those bits.

**Do USE this as a reference checklist.** When auditing v4's GPUSTAT composition, diff the bit-by-bit semantics against this file's `UpdateGPUSTAT()`. Specifically verify:
- v4 sets GPUSTAT bits 0-3 (texpage X), 4 (texpage Y bit 0), 5-6 (semi-transparency), 7-8 (texture depth), 9 (dithering), 10 (draw-to-display), 11 (set-mask), 12 (check-mask), 14 (h-flip), 15 (texpage Y bit 1), 16-23 (video mode), 25 (DMA/data request — **conditional on DMA direction**), 26 (FIFO ready), 27 (GPUREAD ready), 28 (DMA block ready), 29-30 (DMA direction).
- v4 does NOT have its own "always 0 for now" stubs at bits 13, 24, 31. If v4 also stubs these, that's a known limitation; if v4 implements them, v4 is ahead — no regression risk from skipping this file.

**No code lands in the new TombaRecomp from this file.** The struct organization can be referenced when (and only if) v4's gpu.c grows complex enough to warrant a refactor — that's a future-v4 question, not a TombaRecomp question.

**No promotion to extras.cpp.** GPU state is hardware sim, framework-side only.

**No promotion to game.toml.** No per-game config emerges from this file.

## Verified GPUSTAT diff against v4 (`runtime/src/gpu.c:214-275`)

Done immediately after writing the recommended-action section, per the philosophy that audit notes claim things only after verification.

| GPUSTAT bit | v2 (`gpu_state.cpp`) | v4 (`gpu.c`) | Verdict |
|---|---|---|---|
| 0-3 texpage X | ✓ | ✓ | match |
| 4 texpage Y bit 0 | ✓ | ✓ | match |
| 5-6 semi-transparency | ✓ | ✓ | match |
| 7-8 texture depth | ✓ | ✓ | match |
| 9 dither | ✓ | ✓ | match |
| 10 draw-to-display | ✓ | ✓ | match |
| 11 set-mask | ✓ | ✓ | match |
| 12 check-mask | ✓ | ✓ | match |
| 13 interlace field | **stub: always 0** | ✓ live `interlace_field` | **v4 ahead** |
| 14 reverse / h-flip | ✓ | ✓ | match |
| 15 texture disable | **WRONG**: assigns `texpage_y_base_bit1` | ✓ correct `texture_disable` | **v4 correct, v2 buggy** |
| 16-23 video mode | composed | composed | match (different field decomposition but equivalent) |
| 24 IRQ flag | **stub: always 0** | ✓ live `irq1_flag` | **v4 ahead** |
| 25 DMA request | conditional on direction | conditional on direction | match |
| 26 ready for cmd | conditional | always 1 | minor: v4 simpler |
| 27 GPUREAD ready | conditional | conditional | match |
| 28 DMA block ready | conditional | always 1 | minor: v4 simpler |
| 29-30 DMA direction | ✓ | ✓ | match |
| 31 drawing odd/even (LCF) | **stub: always 0** | ✓ live `lcf` (also drives BIOS-vsync poll-thresholding at L217-221) | **v4 ahead** |

**Net:** v4 implements all three "always 0 for now" bits that v2 stubs (13, 24, 31). v4 also has the correct meaning for bit 15 (texture_disable per nocash spec) where v2 has a misreading (`texpage_y_base_bit1` — there is no Y bit 1 on real PS1; the Y base is just one bit). v4's bit-26/bit-28 simplification (always 1 vs v2's "FIFO not full") is fine because v4 processes commands instantly, no FIFO buildup.

**Conclusion: nothing to import. v4 is correct or ahead on every divergent bit.** The v2 file's only residual value is documentation of the GPUSTAT bit semantics — and that's better gotten from nocash directly.
