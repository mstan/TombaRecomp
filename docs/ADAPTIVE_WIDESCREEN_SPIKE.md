# Tomba adaptive-widescreen spike

The bundled **Tomba Adaptive Widescreen** mod now selects the framework's
native-wide compositor and its `Fit to screen (uncapped)` view. It starts a
16:9 window, then tracks live window resizing with no upper aspect limit
(native 4:3 minimum). This grows the native-wide render target; the native-wide
path leaves GTE projection unsquashed. It is not a newly implemented scene
renderer. Menus and FMV retain the framework's 4:3 policy.

## Culling policy

The regenerated main EXE applies the live `psx_ws_x_margin()` to Tomba's
camera-relative classifier family at `0x80022C34..0x800230FC` and enables the
generic per-primitive screen-X and backdrop-window emitters. The config adds a
32-pixel general guard plus another 32 pixels for the fixed-bias/range family. At 4:3
every emitted expression is the original instruction result.

That is a **resident/draw/retirement** cull change. It makes already-managed
actors and geometry eligible through the expanded view plus a small guard, but
it is not evidence that every area overlay's allocation/spawn producer has
been widened. The existing 64-pixel stock margin already covers much of the
16:9 reveal; the new lead is deliberately conservative rather than claiming a
new spawn system.

### Terrain chunk selection and HUD (September 19 follow-up)

The owner's ultrawide tower/hillside repro exposed an upstream selection limit:
the terrain mesh list at `0x800B00F8` still received the stock nine-column camera
window. Increasing ordinary screen-X culling did not restore the missing hill.
The existing `auto_backdrop` hooks found the overlay producer at
`0x80116E24/0x80116E2C`, but their runtime preload margin was zero. The mod now
opts into an adaptive margin:

`ceil(window_columns * (viewport_reveal_pixels + guard_pixels) / native_width)`.

The guest's level-bound clamps remain in place. This is mesh submission, not
stretching terrain. At the reported 1032-pixel-wide native view the margin is
11 columns per side; live A/B restored the missing hillside. The shared detector
also now rejects dependent quotient consumers/layer biases: `0x80116638/44`
previously mistook a +28 layer-table offset for a second window. Its complete
clamp/bias block is recognized before matching the actual eight-column window
at `0x80116650/58`. This restores the foreground ground near the tower's sign.
Adaptive START is floored at zero and END cannot wrap signed 16-bit arithmetic;
the guest still clamps END to the real table extent. Overlay codegen version 11
invalidates cached code with the old match. Other ambiguous dependent-bound
patterns remain stock until their data flow is handled explicitly.

Persistent HUD packets are identified at `0x8005E08C` using the calling builder
and its saved parent return address, rooted at `0x8004E468`. Vitality, equipped
item and lives anchor left; the AP bar and digits anchor right. Their entire
groups translate by the live reveal, not the guard margin. Shared dialogue and
world-sprite callers are excluded; no blanket screen-position heuristic is used.

Regression tests: `tests/test_adaptive_widescreen.c` covers HUD identity,
non-HUD callers, outward-rounded viewport margins, safe detector shapes and the
observed false positive. `tools/probe_adaptive_widescreen.py` resizes a running
debug build, verifies live margins, captures wide surfaces and selection rings,
and restores the window afterward (unless `--keep-size` is specified).

Final local validation passed: rebuilt recompiler and OpenGL runtime; unit
tests; gameplay resizes 4:3 -> 16:9 -> 21:9 -> 32:9 -> 64:9 -> 4:3. Captures are
under `build-adaptive-spike/validation-final-gameplay/`. The tower handoff at
2048x476 is `build-adaptive-spike/handoff/wide-2048x476.png`: ground under the
sign restored, HUD at the actual edges. The live eight-column producer bounds
changed from 69..77 to 59..87, matching the 388-pixel reveal-plus-guard margin.
This is spot validation, not complete level/spawn coverage.

Save-state compatibility: the existing runtime rejects states from a different
codegen signature. User slots 0/1 and diagnostic slots 9/10 were not overwritten.
For this local test only, diagnostic slot 9 was copied into previously unused
slot 11 with the new codegen signature (guest state/ABI/serialization unchanged).
Normal compatibility checks were not weakened. A hot load during validation
once hit the starvation watchdog; a fresh launch restoring slot 11 succeeded.

## Uncapped Fit

Fit has no 16:9, 21:9, or 32:9 ceiling. The activation API accepts `(0, 0)`
to select uncapped Fit; existing capped callers keep their behavior. The GL
stencil scratch texture grows when a native-wide target exceeds VRAM width.
Finite backdrop producers and area-specific spawning remain experimental:
exposing those limitations is part of this spike, not a reason to restrict
the requested viewport. Fixed 16:9 is an optional separate mod choice.

## Validation route

1. Enable **Tomba Adaptive Widescreen** and leave **View** on **Fit**.
2. In gameplay, resize through 4:3, 16:9, 21:9, 32:9, and beyond. Verify the view grows/shrinks
   without a restart; title/menu/FMV screens should remain pillarboxed.
3. Walk both directions through a populated horizontal area and pause at each
   expanded edge. Check that terrain and resident enemies remain visible into
   the guard band rather than appearing exactly at the edge.
4. With the debug build, sample `gpu_state` and `wide_shot`: gameplay should
   report a native-wide present with a non-zero margin, while 4:3/menu/FMV
   should not. Record actor-table slot counts on an edge approach before
   asserting expanded *spawn* coverage.

## Rooftop object residency (2026-09-19)

The flower-background rooftop repro was a separate upstream object-bank swap,
not terrain clipping. Area 1 changes its logical sector at player X 2925/2926;
the stock manager at `0x8005A184` retires the old bank even when both sides
remain visible. Increasing terrain and draw margins alone did not fix it.

`src/mods/tomba_widescreen_residency.c` now keeps banks 0 and 1 resident
simultaneously when the live camera viewport plus its guard overlaps that
boundary. The logical sector and its quest transitions remain unchanged.
The hook validates the overlay instructions, reconstructs residency from guest
actor pools, and synchronizes the manager's observed sector to prevent its
unwanted bank swap. Outside the expanded boundary, extra bank actors receive
the normal retirement request.

Spawning uses the original constructor and event predicate through nested CPS
dispatch, not a direct call to a generated C fragment. A complete preflight
checks all three fixed pools and reserves eight primary slots for gameplay
spawns. Shared objects and consumed events are not deliberately duplicated.
The live rooftop test had 165 primary actors resident, leaving 35 free slots.
The runtime rebuilt successfully and the adaptive-widescreen unit tests passed.
The owner verified the running rooftop fix and resumed play; automated
bidirectional crossing/resize validation of this new residency hook was not
completed. User save slots 0/1 were not overwritten.

This rule is deliberately scoped to the verified area-1 boundary, not a claim
of complete game-wide spawn coverage. Other boundaries, object-pool pressure,
and draw-queue capacity still need audits. The owner explicitly permits
host-side replacements or extensions of stock systems as needed; these limits
are not a reason to cap Fit's aspect ratio.

## Detached forest foliage (2026-09-19)

The next hillside repro was a renderer classification bug, not another missing
bank. Two transformed world-sprite packets (`0x000B3610` / `0x000B3638` in the
captured buffer) sorted at OT rank 1, before the first Gouraud polygon. The
legacy backdrop-phase heuristic stretched these early sprites into the far-left
reveal, creating a floating copy of foliage while the canonical center remained
correct. Approaching it changes draw order, explaining its disappearance.
A live stretch-on/off comparison confirmed the cause.

The title now identifies the transformed sprite builder by its SetShadeTex
return address, `0x8004A170`, and calls `psx_mod_tag_world_primitive`. Explicit
world packet roles override the backdrop heuristic regardless of draw order;
actual backdrop treatment remains enabled. The role table also carries the
existing HUD edges, clears recycled packet roles and expires stale entries.
This is producer identity, not a texture, screen-position or OT-rank blacklist.

Validation: runtime rebuild and expanded unit tests passed (caller identity,
packet aliases, header/command distinction, recycling, expiry and frame rewind).
Restored separate diagnostic slot 6, visually verified the floating foliage was
gone, and passed live resizes at 2048x510, 4:3, 16:9, 32:9 and 64:9, returning
to 2048x510. Captures and margin assertions are in
`build-adaptive-spike/tree-validation/`. The game is left running at this spot;
user save slots 0/1 were not overwritten. This is spot validation, not proof of
all other scene producers or area boundaries.

## Bridge terrain: generalized multi-strip selection (2026-09-19)

The bridge/water repro exposed more selectors in the same terrain generator.
Its finite 88-entry table packs several independent strips. The old detector
recognized `[q, q+17]` but missed `[q+33, q+44]` and `[q+63, q+70]`. Increasing
the ordinary cull margin or selecting the whole *detected* row did not restore
the missing background strip.

The shared detector now handles two independently biased quotient consumers,
using the difference between offsets (11 and 7 here) as the window width.
Backward def/use checks trace copied/biased camera values to scratchpad camera X,
validate the divide constant, and handle a unique local branch predecessor so
values from a skipped branch do not contaminate the proof. Dependent bounds and
ambiguous/unproven values remain rejected. Existing segment and extent clamps
remain authoritative. This change is shared by the interpreter and recompiler;
there is no bridge-address patch or aspect cap.

Validation:

- Rebuilt recompiler, regenerated main code, rebuilt runtime; C unit tests pass.
- C/C++ detector output and per-PC interpreter-window output agree on the RAM
  capture. The earlier tower's segmented eight-column case still matches.
- Restored the same bridge diagnostic before each resize (hazards can kill
  Tomba while parked). Live 4:3, 16:9, 21:9, 32:9, 64:9 and 2048x510 checks pass.
  The left-side background is restored in the captures under
  `build-adaptive-spike/bridge-validation-final/`.
- The terrain-list initializer clears `0x16C` bytes at `0x800B00F8`: a four-byte
  header plus 90 pointers. The area's table has 88 entries; the observed list
  high-water mark during this check was 63. No capacity expansion is needed for
  this repro. Other producers and draw-packet arenas still need coverage audits.

Overlay codegen is now v12/hash `1C9210E9`, and the shared detector itself is in
the codegen hash inputs so future changes invalidate stale overlay caches.
User slots 0/1 and original diagnostic slot 5 are untouched. For this local
test, diagnostic slot 5 was copied to slot 4 and only its codegen integrity key
was updated (guest state, ABI and serialization unchanged). Normal savestate
compatibility checks remain in force: older-key snapshots are still rejected.

This is a general fix for matching terrain selectors, not a universal bypass
of all game culling. Object-bank residency, different selector algorithms and
finite authored geometry remain separate concerns.

## Intermittent 4:3 pillarbox flashes (2026-09-19)

The bridge gameplay scene could repeatedly switch back to the canonical 4:3
buffer despite continuously projecting the expanded world. Before the fix,
the presentation ring recorded 186 native-4:3 frames out of 1,200, with
2,200-7,837 projected vertices on the incorrectly classified frames. Terrain
packets arrive in bursts separated by 6-8 vblanks; the old six-frame overhang
timeout mistook those submission gaps for a 2D scene transition.

The scene classifier now latches confirmed polygon overhang. Ongoing world
projection maintains that confirmation across submission gaps, but cannot
establish it by itself: GTE-heavy effects in already-2D rooms must not promote
those rooms to widescreen. When both signals stop, the latch expires. Fullscreen
2D screens still clear the latch, and the existing FMV gate remains in place.
Reset and savestate restore discard host-derived classification history so a
previous scene cannot leak into a restored one. No aspect cap was introduced.

Validation: runtime rebuilt; unit tests cover burst gaps, prolonged projection,
2D effects, inactivity expiry, frame rewind and counter wrap. The same saved
repro at 2048x510 recorded 1,200/1,200 wide classifications and 1,200/1,200 wide
OpenGL presents, with no fallback. The fullscreen item screen selected native
4:3 and returning to gameplay re-established the wide target. Same-snapshot
resize checks passed at 4:3, 16:9, 21:9, 32:9, 64:9 and 2048x510. Evidence is
under `build-adaptive-spike/flicker-*.json` and `flicker-resize-validation/`.
FMV and every 2D-room transition were not replayed in this check.

Diagnostic slot 3 preserves the reported gameplay spot; user slots 0/1 were
not written. This runtime-only change does not alter the codegen signature or
savestate format.
