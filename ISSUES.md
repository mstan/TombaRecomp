# TombaRecomp — Open Issues

Game-specific issues. Framework-side issues live in
`F:/Projects/psxrecomp-v4/ISSUES.md`.

---

## Issue #2 — Mid-function call_by_address targets not registered (2 sites)

**Status:** open, audit-surfaced
**Date opened:** 2026-05-12
**Manifestation of:** psxrecomp-v4 ISSUES.md Issue #5 (mid-func split
dispatch miss — platform bug class)

### Symptom

Phase B2 audit surfaced 2 mid-function continuations called via
`call_by_address(cpu, 0xX); return;` from inside `func_800905DC` that
are NOT registered in `SCUS_942.36_dispatch.c`:

| Target       | Status                                                |
|--------------|-------------------------------------------------------|
| `0x800905E4` | mid-function continuation, missing from dispatch      |
| `0x80090600` | mid-function continuation, missing from dispatch      |

At runtime, calls to these addresses fall through dispatch-table
binary-search → `dirty_ram_dispatch` (text isn't dirty) →
`psx_unknown_dispatch` (log/abort).

### Impact

Whatever control flow `func_800905DC` produces via these mid-func
splits never executes correctly. We don't yet know what feature this
function is responsible for. Fix at platform level (psxrecomp-v4
Issue #5) will close this automatically on next regen.

### Tomba GTE coverage findings (also surfaced by B2)

The `gte_audit` reports **8 missing `gte_execute` + 21 missing
LWC2/SWC2 emits** in Tomba's text segment. Cluster at
`0x8007C800..0x8007CD00` (likely a single 3D-math function) + 3
isolated sites at `0x80077458`, `0x8007E674`, `0x800805F4`. Either
discovery gap or emit gap. Could affect 3D rendering / gameplay
visuals. See psxrecomp-v4 ISSUES.md Issue #4 for analogous BIOS
findings — same investigation pattern applies.

---

## Issue #1 — FMVs render at 1/4 size, anchored to upper-left

**Status:** fixed in `psxrecomp-v4` `feature/fmv-followup`
**Date opened:** 2026-05-11
**Date fixed:** 2026-05-11
**Affects:** Whoopee Camp intro FMV, Tomba intro FMV (and presumably
every subsequent MDEC/STR clip)

### Symptom

The Whoopee Camp logo FMV and the Tomba intro FMV both play with
visually correct decoded content, but each occupies only the
upper-left quadrant of the window. The bottom-right three quadrants
stay blank (clear color). MDEC decode itself looks right — the
imagery is recognizable and frame-paced — so the bug is in the GPU
display path, not the decoder.

### Likely areas

- GPU display-area / screen-area registers (`GP1(0x05)` start address,
  `GP1(0x06)` horizontal display range, `GP1(0x07)` vertical display
  range, `GP1(0x08)` display mode) being applied with the wrong scale
  or wrong target. A 1/4-size, top-left-anchored render is the
  classic symptom of a 640×480 (or 640×448) framebuffer being shown
  with a display mode that's set for 320×240, or vice versa, with
  no horizontal/vertical stretch applied at present.
- `GPUSTAT` width/height bits not honored by the SDL blit path.
- Tomba uses the standard 24bpp MDEC display mode for FMVs; check
  whether the runtime's GPU handles the bit-15 / 24bpp display
  toggle.

### Concrete next step

1. At an FMV frame, query GPU regs from both the recomp runtime and
   Beetle (same FMV frame number). Diff GP1(0x05/0x06/0x07/0x08) and
   GPUSTAT.
2. Inspect the SDL present path in `runtime/src/main.cpp` / the GPU
   software renderer — confirm it actually reads the display-area
   regs rather than hardcoding 320×240 from VRAM (0,0).

### Resolution

The SDL presenter was updating a fixed 640×512 texture using the
active display width as the source pitch, then rendering the entire
texture. FMV display modes such as 320×224 therefore occupied only the
upper-left portion of the window. `runtime/src/main.cpp` now updates
and renders the active source rectangle (`di.width` × `di.height`)
scaled to the 640×480 window.

---

## Issue #2 — Tomba intro FMV has no audio (Whoopee Camp FMV audio works)

**Status:** fixed in `psxrecomp-v4` `feature/fmv-followup`
**Date opened:** 2026-05-11
**Date fixed:** 2026-05-11

### Symptom

The Whoopee Camp logo FMV plays with correct audio. The Tomba intro
FMV that follows it plays silently. The video portion of both FMVs
renders the same way (see Issue #1).

This rules out a wholesale "SPU output is dead" problem — the audio
path works for the first clip. Something specific to the transition
between FMVs, or to Tomba's clip in particular, is muting the second
clip.

### Likely areas

- **XA-ADPCM CD audio path.** PSX FMV audio is usually XA-ADPCM
  interleaved sectors fed via CD->SPU, not the SPU RAM playback path.
  If Whoopee Camp uses one mode and Tomba uses the other, that maps
  to one of these working and the other not. CD-XA / SPU bridge
  isn't fully modeled per Codex's handoff.
- **SPU CD volume / CD reverb registers** being cleared between
  clips and never reprogrammed.
- **SPU voice/key-on state** if Tomba's clip uses SPU voices for
  the audio rather than CD-XA.

### Concrete next step

1. Determine which audio path Tomba's FMV uses (XA via CD or SPU
   voices) — sniff CD sector mode bits + SPU register writes around
   the FMV-2 start frame.
2. If XA: confirm `cdrom.c` whole-sector mode is emitting the XA
   audio sectors and the SPU CD-input path actually consumes them.
3. If SPU voices: check key-on / volume / ADSR around the FMV-2
   start.

### Resolution

The second FMV uses standard CD-XA sectors (`file=1`, `channel=1`,
`coding=0x01`: 4-bit stereo, 37.8 kHz). `runtime/src/cdrom.c` now
handles CD `SetFilter`, `Mute`, and `Demute`, demuxes matching XA
audio sectors, decodes them to PCM, and feeds the SPU CD input bus.
`runtime/src/spu.c` now mixes that input when SPU control bit 0 and
the CD volume registers enable it. Live validation showed decoded
CD frames entering SPU and nonzero output peaks during the Tomba FMV.

---

## Issue #3 — Previous FMV's last frame bleeds into the gap before the next FMV

**Status:** fixed by Issue #1's presenter fix
**Date opened:** 2026-05-11
**Date fixed:** 2026-05-11

### Symptom

Between the Whoopee Camp FMV and the Tomba FMV, the Whoopee Camp
logo's last frame is briefly visible (slightly distorted) in the
lower-left quadrant of the window before the Tomba FMV starts in
the upper-left. The screenshot taken at the transition captures
this: upper-left = start of Tomba FMV, lower-left = stale Whoopee
Camp frame, right side = blank.

Likely related to Issue #1 (quadrant rendering) — the same display
area that's only filling one quadrant isn't clearing the other
quadrants between FMVs.

### Likely areas

- Missing `GP0(0x02)` Fill VRAM between clips, or `GPUSTAT`-driven
  framebuffer swap not actually swapping (so the previous frame
  persists where new content isn't drawn).
- Display rect change between clips reducing the visible area but
  leaving the older area uncleared.

### Concrete next step

Likely falls out of Issue #1's fix; revisit once that lands. If it
persists, add a wtrace on GPU command FIFO for the inter-clip frame
window.

### Resolution

The stale-frame bleed was a side effect of rendering the full backing
texture instead of the active display rectangle. After the presenter
fix, the title/menu capture after skipping the FMV renders cleanly
without the old lower-quadrant stale frame.

---

## Issue #4 — Cannot skip FMVs with controller input

**Status:** fixed in `psxrecomp-v4` `feature/fmv-followup`
**Date opened:** 2026-05-11
**Date fixed:** 2026-05-11

### Symptom

Pressing Start / Cross / Circle / Square during the FMVs does not
skip them. Game continues looping or playing FMVs indefinitely (see
also: "FMV/attract path loops for long durations" note from Codex's
handoff). CD streaming, MDEC trace, and frame counter all keep
advancing — game is not frozen, the input just doesn't reach the
FMV's skip handler.

### Likely areas

- **Pad input not actually reaching the game.** Pad polling works
  during BIOS shell, but the game-side input read path (Tomba's
  pad code, likely in the recompiled EXE) may use a code path that
  isn't being hit yet. Possible: install-at-runtime pad handler in
  game RAM that the dirty-RAM interpreter is or isn't catching.
- **FMV skip logic gated on game state** that's not advancing
  (e.g. an "FMV done" flag set by an MDEC callback that isn't
  firing because of Issue #1/#2).
- The "infinite attract loop" the FMVs are running in might not
  actually be the main-menu attract — it could be the boot-time
  intro before the title screen, which on real hardware proceeds
  to title-screen-with-press-start regardless of input.

### Concrete next step

1. Verify pad input is reaching the game RAM. Set the override pad
   to "Start held", check that some game-side variable changes in
   response (use `wtrace` on a suspect input-state global).
2. Find Tomba's FMV skip routine in the recompiled EXE. Tomba uses
   a standard FMV player; the skip check usually polls `PadRead`
   each frame and bails out of the MDEC loop on a press. Verify
   that routine is being entered.
3. Determine whether this is "attract loop is expected behavior, no
   skip exists at this stage" or "skip exists but input isn't
   reaching it". A Beetle run of the same disc through the same
   frame range answers this.

### Resolution

Input override was reaching `sio_set_pad_state`, but the SIO device
trace showed only the first pad-select byte completing. The subsequent
pad access/config bytes were written by the BIOS but were killed by
the cycle-paced shifter before the digital-pad state machine saw them.
`runtime/src/sio.c` now completes pad transfers through the
access-paced path while leaving memory-card traffic on the stricter
cycle-paced path, and the digital pad model accepts the config/status
commands Tomba sends (`0x43`, `0x45`) in addition to the normal poll
command (`0x42`). Holding input during the intro FMV now stops CD
streaming and advances to the Tomba title screen.
