# Adaptive renderer performance investigation — 2026-09-19

## Current direction — 2026-10-08

The owner confirmed that the separate enhanced renderer owns widescreen.
Reconstructing a wider image from the stock renderer is deprecated. The
stock-centre/edge replay experiment suggested below has been shelved.
Optimize the complete enhanced-renderer geometry inputs instead.

HLE follows [the owner's policy](F:/Projects/recomp-template/HLE.md): select
HLE or LLE at build time, preserve caller outputs and useful gameplay pacing,
and permit different internal work and timing. Exact cycle charges are not
an acceptance requirement for HLE.

`TOMBA_GEOMETRY_IMPL=HLE` selects native batches for `80024EEC`, `800251C0`
and `800253C8`; `LLE` selects the maintained generated original routines.
`src/hle/tomba_geometry_hle.c` retains exact shared GTE operations, full
widescreen culling, animated UV handling, packet layout and OT links. It removes
per-instruction dispatch/load/stall bookkeeping and charges 16 + 24 cycles
per input polygon for each atomic batch. VSync, devices, input and audio keep
their ordinary pacing. There is no runtime HLE selector.

The test-only `TOMBA_GEOMETRY_VALIDATE=ON` build executes the original against
isolated RAM/scratchpad/CPU inputs, restores them, and compares HLE outputs.
At the supplied Stormy save, 200 batches per routine matched all packet/OT RAM,
scratchpad, GTE arrays, return PC/value and callee-saved registers. Unobserved
stack scratch and internal cycle/load timing are outside the contract.

Latest-release reference versus the first HLE sample, native 240-line output,
Fit, same stationary rainy save, interpolation and rewind off:

| View | Original display flips/s | HLE display flips/s |
| --- | ---: | ---: |
| 16:9 | 59.92 | 59.72 |
| 32:9 | 56.94 | 59.39 |
| 64:9 | 45.64 | 59.76 |

The 16:9 process-CPU sample fell from about 1.00 to 0.67 core equivalents.
Wider HLE views do more useful work per second because they now complete
nearly 60 frames. These are bounded local samples on a faster PC, not results
on the reporter's GTX 1060 / approximate Ryzen 5. Raw local evidence lives in
`evidence/stormy-hle-first/` and the reference performance directories.

HLE snapshots carry implementation tag `TGH1`, separate from the LLE key.
Old mid-instruction LLE snapshots are rejected; memory-card saves remain the
game's original format. Product builds disable differential validation.

The PGXP product build also loaded the supplied Stormy Mountain memory-card
save at the shipped 2x resolution with antialiasing, PGXP, interpolation at
165 Hz, widescreen and rewind enabled. Walking/jumping, saving, loading,
opening and accepting rewind, then saving again succeeded. The HD texture
feature was enabled with an empty pack; replacement texture cost was not
tested. Stationary 5-second game-framebuffer samples measured 53.40, 56.91
and 60.44 flips/s at 16:9, 32:9 and 64:9 respectively. Guest VBlank tracked
those rates, so the remaining drops in these samples were host throughput or
pacing rather than missed guest display deadlines. These are not an A/B
against an equally configured LLE build and do not establish older-GPU speed.
The interpolation presentation surface has a fixed (0,0) origin; the profiler
now also counts actual GP1(05) framebuffer changes so interpolated swaps are
not mistaken for game frames.

Build selection (after the ordinary title setup/code generation):

```powershell
cmake -S . -B build-hle -DTOMBA_GEOMETRY_IMPL=HLE -DPSX_PGXP_VARIANT=ON
cmake --build build-hle --target psx-runtime psx-runtime-pgxp
cmake -S . -B build-lle -DTOMBA_GEOMETRY_IMPL=LLE -DPSX_PGXP_VARIANT=ON
cmake --build build-lle --target psx-runtime psx-runtime-pgxp
```

Both runtime variants build. `LLE` remains the default while the HLE candidate
gets broader gameplay coverage. Each executable prints its effective geometry
selection; the CMake cache records it. For the isolated reference comparison,
add `-DTOMBA_GEOMETRY_VALIDATE=ON` to the HLE configuration; leave it off for
play/performance measurements. The framework must include the optional
`PSX_SAVESTATE_IMPL_TAG` compatibility-key support (commit `edb78e83`).
The freshly rebuilt LLE executable also resumed the rainy diagnostic save and
saved/loaded its own snapshot successfully; no native geometry HLE counters
were present.

The September notes below are historical measurements and recommendations.
Their stock-centre reveal recommendation and strict HLE timing gate are
superseded by the owner instructions above.

## Finding

The reported bridge slowdown is primarily **additional emulated game work**,
not a host GPU fill-rate limit. The machine still advances approximately
59.94 guest vblanks per second, but wider terrain submission makes Tomba miss
more of those display deadlines. Eliminating only the wide GPU mirror does
not recover the lost game frame rate.

## Repro and measurements

The exact original diagnostic slot 3 was tested with the accepted pre-merge
OpenGL debug executable in `build-adaptive-spike`. That executable contains
framework checkpoint `fa435a4a` (ABI 21/codegen 12), not the subsequently merged
master build. Fit, interpolation off, 1x internal resolution, same snapshot
restored before every case, one-second settling, ten-second samples. No
compilation or second game instance ran during measurement. The player's
current position was saved separately in diagnostic slot 2 and restored after
the measurements; normal slots 0/1 were not written.

| Client / view | Guest vblanks/s | Display flips/s | GP0 draws/flip | Process CPU, cores |
| --- | ---: | ---: | ---: | ---: |
| 800×600 / 4:3 | 60.33 | 60.23 | 338 | 0.501 |
| 1280×720 / 16:9 | 59.77 | 52.42 | 438 | 0.461 |
| 1680×720 / 21:9 | 59.83 | 43.36 | 544 | 0.445 |
| 1920×540 / 32:9 | 59.76 | 35.70 | 734 | 0.489 |
| 2048×510 / Fit | 60.12 | 34.25 | 770 | 0.463 |
| 2048×510 / mirror draws disabled | 59.78 | 34.07 | 770 | 0.467 |
| 2048×510 / mirror restored | 59.87 | 34.07 | 770 | 0.490 |

Display flips count changes in the presented PSX framebuffer origin, not
launcher FPS or host swaps of an unchanged front buffer. Endpoint sampling
introduces small rate noise. This stationary-scene measurement is not a
whole-game benchmark or a count of unique animation frames.

At the wider viewport there are about 2.28 times as many submitted GP0 draw
commands per display flip. Host CPU consumption stays below one full core.
Mirror ablation leaves guest work intact and removes the synthetic wide GPU
pass; the unchanged flip rate is the strongest evidence against that pass
being the dominant bottleneck. Its measured CPU batch-flush cost falls from
about 0.24 to 0.14 ms per guest vblank without improving the flip rate.

Raw observations: `build-adaptive-spike/perf-baseline/summary.json` and each
case's `measurement.json`. Reproduce with:

```powershell
python tools/profile_adaptive_widescreen.py --pid <game-pid> --load-slot 3 `
  --output build-adaptive-spike/perf-baseline --ablate
```

Use the snapshot-compatible executable. The script never saves, clears mirror
ablation in `finally`, and requires idle controls. It leaves the final test
viewport/scene in place; restore the player's separate diagnostic afterward.

### Measurement caveats

`frame_perf.emu_cpu_ms_avg` is **wall time between presents minus present-call
wall time**, not consumed CPU time. It includes pacing. Process CPU above is
measured independently with Windows `GetProcessTimes`. Likewise, scene-wide
GL elapsed queries can span idle gaps between command submissions; their
near-frame-length numbers are not GPU utilization. `phase_hot`/`phase_profile`
sample the current guest phase, including host waits inside that phase; they
identify routines to investigate, not exclusive native CPU percentages.

## Concrete opportunities

1. **Move extra terrain to a host-side reveal pass.** Keep the canonical 4:3
   guest submission path and build the additional visible terrain outside its
   emulated instruction budget. Retain/copy immutable mesh inputs, project in
   a separate host context, and submit to the wide surface without changing
   canonical VRAM/texture feedback. This directly addresses the observed
   scaling. Preserve the expanded actor residency/culling behavior separately;
   do not gain speed by making visible enemies disappear again. Camera, level,
   animation, CLUT and texture-upload changes must invalidate retained inputs.

2. **Contract-checked HLE for geometry/packet loops.** In the ultrawide sample,
   the main static wall-sample candidates are `0x800253C8`, `0x80024EEC` and
   `0x800251C0`. Inspection of the generated MIPS translation confirms repeated
   GTE vertex loads/projection, projected-coordinate stores, polygon tests and
   ordering-table/packet writes. `0x8005E08C` is the shared SetShadeTex/tagging
   funnel. These are concrete bounded candidates, not a claim of measured
   exclusive host time. A fast native implementation can reduce host overhead;
   **preserving all original cycle charges will not, by itself, remove this
   guest-budget slowdown**. Use it alongside the host-only reveal design.

3. **Load native overlays and remove diagnostic overhead in production.** The
   baseline ran about 1.56 million interpreted overlay instructions/sec at the
   wide viewport, with no native-overlay phase samples. Its old local config
   had overlay caching disabled. Current master enables the overlay pipeline
   and requires audited original-disc AOT packaging; verify actual shard hits,
   not just the config setting. This offers host headroom but is not a license
   to change guest timing. Debug-build profiling overhead and GPU timestamp
   queries should not be confused with shipping performance.

Lower priority for this repro: further mirror batching/state-change reduction.
It remains worthwhile after the guest-side extra terrain work is removed, but
the ablation does not support it as the first fix.

## LLE contract and validation gate

No HLE optimization or guest timing shortcut was enabled by this investigation.
For a strict swap-in, compare the original and native routine at observable
boundaries: GPR/HI/LO and return behavior; GTE registers, FIFOs, flags and
fixed-point saturation; RAM/scratchpad, packet and OT writes; load-delay state;
cycle/deadline accounting; IRQ/yield ordering; DMA-visible writes and mask,
texture and blending semantics. Check exceptional/clipped/degenerate cases,
overlay signatures and save/load boundaries. Do not just set the return value
or globally accelerate the PS1 clock.

The host-only reveal is explicitly an opt-in presentation extension: extra
geometry should not mutate canonical GTE state or consume extra guest cycles.
Its contract needs canonical-buffer/state comparisons plus wide-content,
occlusion, boundary-residency and temporal tests. This is the recommended next
implementation experiment, not an already-proven optimization.

## Integration and validation

All prior source work was checkpointed in title `99b6758` and framework
`fa435a4a`. Current upstream changes were merged, not discarded: title
`7c94d98`, framework master `c68bf6e0`. These are local commits, not pushed.
The old private-capture packaging changes are preserved in the checkpoint;
the merged tree retains master's newer original-disc AOT release pipeline.

The merged executable in `build-adaptive-master` builds successfully. The
custom renderer is a single default-off mod, defaults to Fit to Window, and
offers fixed 16:9/21:9/32:9 via the same native-wide path. Tomba's legacy HUD
squash and backdrop-X/unsquash emit configuration was removed. Shared squash
support used by other titles remains. Live validation on a fresh, isolated
new-build gameplay save passed Fit through 64:9, fixed ratios under resizing,
and disabled-mod 4:3 with zero wide margin in an ultrawide window. All three
native Windows CTest tests pass: adaptive unit tests, runtime metadata, and
staged mod catalog.

Master uses newer DMA/CD-ROM snapshot sections (ABI 23/codegen 13). The old
slot 3 is **not compatible** with that build; it was neither rekeyed nor
overwritten. New-build smoke tests use separate `validation-saves`, not the
player's saves. The old compatible executable remains available for continued
play and exact-repro profiling. A new-build bridge replay is still needed
before claiming the measured rates describe current master.
