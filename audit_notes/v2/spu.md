# Audit: v2/runner/src/spu.cpp (+ spu.h)
- LOC: 604 (.cpp) + 45 (.h) = 649 total
- Source: v2 (`F:/Projects/psxrecomp-projects/psxrecomp/runner/src/spu.cpp`)
- Purpose: Standalone PS1 SPU emulator: 24 voices, SPU-ADPCM decoder, ADSR envelope, mixer, WinMM-based audio output on a separate thread. Handles MMIO at `0x1F801C00-0x1F801DFF` and DMA4.
- Read date: 2026-05-09
- Read mode: end-to-end, every line

## Critical finding: v2 has the same silent-voice-recycle bug we just fixed in v4 this session

`spu_read_half` (L569-580) returns the register mirror for ALL voice registers, including voice register 6 (byte offset `0x0C`) which on real PS1 returns the live envelope level (CURVOL / ADSR_LEVEL). v2's mirror is never written from the envelope state — the BIOS music engine reading CURVOL to find a "free" voice always gets 0, so it over-recycles voices 0-3.

This is **exactly the bug** we identified and fixed in v4's `runtime/src/spu.c` this session (commit `f75159c`, "SPU ADSR + free-voice CURVOL fix: chime fans across all 24 voices"). v2 ships with this bug uncorrected.

**Implication:** if the user's prior Tomba experience on v2 sounded thin or had channel-cutouts during the chime / music passages, this is the cause. v4 is now ahead of v2 on this exact behavior.

## Stub / HLE patterns found

- **L214-216 (Sustain phase)**: `case 2: /* Sustain — simplified: just hold at level */ v->env_vol = sustain_level; break;` — admission of incompleteness. Real PS1 sustain uses ADSR_HI bits 22-31 (Sr — sustain rate), bit 30 (sustain_dec direction), bit 31 (sustain_exp mode). v2 ignores all three; sustain just clamps at the level. Affects games that use sustain-decay or sustain-rise (less common but real).
- **L319-320**: voice volume register bit 15 (sweep mode) ignored. Same simplification as v4. Not a v2-specific bug — both backends share this gap. Beetle implements sweep; if Tomba's chime fade uses sweep, both v4 and v2 misrender the fade tail.
- **L360-362**: `fprintf(stderr, "[SPU] waveOutOpen failed\n");` then `fflush(stderr);` — printf debugging in production. CLAUDE.md §3.
- **L432-433**: `printf("[SPU] Initialised — 24 voices, 44100 Hz stereo\n"); fflush(stdout);` — same.
- **L468**: `/* [SPU KON] first 30 — re-enable printf when investigating voice keying */` — debug-print scaffolding left in source.
- **L603**: `/* [SPU DMA] printf("[SPU DMA] %u bytes: RAM 0x%06X → SPU RAM 0x%05X\n", ...) */` — same.
- **No CURVOL exposure** at L569-580: see the critical finding above.
- **L575**: `if (phys == 0x1F801DAEu) return 0;` — SPUSTAT returns 0. v4 returns `0x0400` (the "transfer FIFO ready" / "SPU ready" bit). v2's 0-return is technically incomplete; games polling SPUSTAT for ready state will see "not ready" forever. Hasn't bitten v2's Tomba apparently, but fragile.
- **No ENDX latch** — the global "voice n reached loop_end without repeat" register at `0x1F801D9C/9E` is not exposed. The flags are tracked per-voice (`flags & 0x01`) but never aggregated into ENDX. Music engines polling ENDX never see voice-finished signal. v4 has the ENDX latch (added this session in spu.c).

## Genuinely useful patterns / ideas

- **L131-157 ADPCM decoder**: clean port of standard SPU-ADPCM. Matches v4's decode logic algorithmically. K0/K1 coefficient tables match nocash spec. Defensive `lsh` clamp (`if (lsh > 12) lsh = 12;`) handles malformed shift bytes safely.
- **L286-288 loop-start fallback**: `(v->loop_start >= 0) ? loop_start : (g_spu_regs[vi*8+7] * 8u)` — uses observed loop-start flag from sample data if seen during decode, else falls back to the per-voice repeat-addr register. Defensive; v4 uses similar pattern.
- **L585-596 DMA4 bounds checking**: clamps `src_ram_addr` to `0x1FFFFF` (KSEG strip), then bounds both source and destination ranges. Worth a diff against v4's `spu_dma_write` to confirm v4 has equivalent bounds logic.
- **WinMM-based audio output (L348-410)**: an alternative to v4's SDL2 audio callback. Direct control over buffer queue rotation, NUM_BUFS=4 × 1024 stereo samples = ~93ms latency. Not a clear win — SDL2 is more portable. Worth knowing as an option if SDL2 audio ever becomes problematic on Windows.

## Dependencies (other files this references)

- Windows API (`<windows.h>`, `<mmsystem.h>`) — Win32-only.
- C++ stdlib: `<atomic>`, `<thread>`.
- Standalone — no `cpu_state*`, no kernel structs, no event/IRQ system. Pure hardware sim. ✓ qualifies as hardware-sim under audit philosophy.

## Verdict: NEEDS_HUMAN; do not import

**v4 is ahead of v2 on every meaningful SPU behavior.** This audit produced two diagnostic findings, not import targets:
1. v2's Tomba audio likely had the channel-cutout bug we fixed today — explains a lot of prior session experience.
2. Volume-sweep (vol bit 15) is an unmodeled gap *shared* by v2 and v4. Implementing it would help Tomba's chime fade tail and any game that uses sweep — but the work lands in v4-side spu.c, not by importing this v2 file.

## Recommended action

**Do NOT import.** Reference for two specific pieces:

1. **DMA4 bounds-checking pattern (L585-596)** — quick diff against v4's `spu_dma_write` to confirm v4 has equivalent KSEG-strip + src/dst clamp. If v4 missing, fix lands in v4's spu.c with this audit cited as the discovery source.

2. **Volume sweep implementation** — neither backend has it. If/when sweep becomes priority (likely after first Tomba run if music sounds thin), the cleanest reference is Beetle's `SPU_Sweep::Clock` at `beetle-psx/mednafen/psx/spu.cpp:239` (per the prior session handoff). v2's spu.cpp doesn't have sweep either; this is a pure v4 + Beetle question, no v2 input needed.

**No promotion to extras.cpp.** Hardware sim, framework-side only.

**No promotion to game.toml.** No per-game config emerges.

## Verified diff against v4 (`runtime/src/spu.c` post-CURVOL fix)

Done immediately to confirm the audit's claims:

| Behavior | v2 spu.cpp | v4 spu.c (current) | Verdict |
|---|---|---|---|
| ADPCM decode | ✓ correct, K0/K1 standard | ✓ correct | match |
| Attack phase | linear, `env_rate(step, shift)` | full `calc_vc_delta` ported from Beetle's `CalcVCDelta` | **v4 ahead** (more faithful) |
| Decay phase | exp approximation `current >> (shift+1)` | full `calc_vc_delta` with exp + linear modes | **v4 ahead** |
| Sustain phase | **stub: just hold at level** | full `calc_vc_delta` with Sr/sustain_dec/sustain_exp | **v4 ahead** |
| Release phase | exp approximation `current >> (shift+1)` | full `calc_vc_delta` with release_exp | **v4 ahead** |
| ENDX latch | absent | present (added this session) | **v4 ahead** |
| CURVOL register read | **bug: returns 0 mirror** | ✓ returns live `voices[v].env_level` | **v4 ahead** (fix this session) |
| Volume sweep (bit 15) | ignored | ignored | **shared gap** |
| SPUSTAT read | returns 0 | returns 0x0400 (ready bit) | v4 more correct |
| DMA4 bounds checking | bounds-strip + clamp | (verify) | **action: diff v4-side** |
| Audio output backend | WinMM thread | SDL2 callback | architectural choice; both work |
| Diagnostic ring buffer | absent | always-on KEYON/KEYOFF/END_LOOP/END_STOP ring (1M entries this session) | **v4 ahead** |

**Net: nothing to import. v4 is ahead on the substantive behaviors. Reference value is one DMA4 check item and one shared gap (sweep) for future v4 work.**
