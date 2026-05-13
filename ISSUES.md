# TombaRecomp — Open Issues

Game-specific issues. Framework-side issues live in
`F:/Projects/psxrecomp-v4/ISSUES.md`.

---

## Issue #4 — FMV plays at ~6.7 fps (target ≥15) — IRQ-rate limited

**Status:** **FIXED 2026-05-13** by psxrecomp-v4 `b486c13`. FMV now
plays at 15.0 fps exactly (Tomba's designed rate). 2.24× speedup.
**Branch:** `tomba-in-game`

### Fix summary

Root cause was NOT in MDEC, NOT in CDROM, NOT in DMA, NOT in IRQ
handler chain. It was in `runtime/src/interrupts.c`: VBlank firing
was gated on `dispatch_count >= 50000` (block-dispatch count), but
each dispatch is only ~5-6 cycles. Effective ~289k cycles per
VBlank, vs real-PSX 564480. Game-internal time ran at ~51% of
real, so every cycle-paced flow (including Tomba's FMV state
machine driven by MDEC-out DMA-done IRQ) decoupled at that rate.

Fix: switch VBlank trigger to `cycles_since_vblank >= 564480` where
`cycles_since_vblank` is incremented by `interrupts_advance_cycles`
called from `psx_advance_cycles`. Subtract one period on fire
(don't reset) so cycle overshoot from long blocks carries forward.

Verified by `tools/_mdec_pace.py`:
- Before: 0.111 decodes/VBlank (6.7 fps).
- After:  0.250 decodes/VBlank (15.0 fps exactly).

### Symptom

Tomba FMVs (Sony splash, Whoopee Camp logo, intro) play with correct
colors and audio at correct rate, but video updates at ~6.7 fps
(measured directly — see "Diagnostic chain" below). Target for PSX
FMV is 15-30 fps depending on game; even the most conservative
target is more than 2× faster than what we deliver.

### Diagnostic chain

1. `mdec_state` shows full 280-macroblock decodes happening for each
   FMV frame. MDEC itself is correct.
2. `mdec_trace` cmd_begin events with command type DECODE happen
   every **9-10 VBlanks** (= ~6.7 fps at 60Hz). Confirmed via
   `tools/_mdec_pace.py`.
3. `fn_entry_dump` over a 5-VBlank window shows two functions
   dominate ~50% each (`0x80066FEC` + `0x8001EFE8`): 15,000 calls
   each in 5 VBlanks = ~360k calls/sec total. This is a **tight
   polling loop** in Tomba's FMV player.
4. Reading the recompiled C: `func_8001F1C0` block_8001F2FC is a
   classic `do { ret = func_8001EFE8(queue_ptr); } while (ret == 0);`
   busy-wait. Each iteration consumes ~30 PSX cycles (= ~5.4ms of
   per-VBlank cycle budget = ~32% of a VBlank).
5. `func_80066FEC` is the inner state-machine check on a queue
   element. Queue base = `0x800D7188`, 32-byte stride, counter at
   `0x800A188C`, base ptr at `0x800A326C`. Element offset 0 is a
   halfword state field. Function returns the "consumed" path only
   when state == 1 (rare) or state == 2 (the trigger).
6. `wtrace` on the queue range (tools/_wtrace_state.py) shows
   state-transition histogram over 3 sec: `{3: 160, 0: 175, 2: 20,
   4: 20}`. **State=2 writes happen 20 times in 3 sec = exactly
   6.7 Hz, matching the FMV rate.** Each state=2 write unblocks one
   FMV frame.
7. The state=2 writer's RA is `0x80068824`. Reading
   `generated/SCUS_942.36_full.c` shows this is `func_8006877C`
   block_80068824 — return point from a `jalr cpu->gpr[2]`. The
   function is the **BIOS interrupt dispatcher**: reads a 7-bit
   pending-IRQ mask from `0x800974DC` and iterates handlers at
   `0x800974E0` (4-byte stride per bit, classic IRQ chain layout).
8. So state=2 is written by **one of the registered IRQ handlers**.
   At 6.7 Hz, candidates are MDEC-out DMA-done (one per FMV frame)
   or CDROM sector-batch-done. Not VBlank (60 Hz). Not raw CDROM
   (75/150 Hz).

### Suspected additional contributor: cycle pacing is at ~60% of real

Measured over 5 sec wall-clock:
- VBlanks fired: 356 (= 71 Hz, ~18% over real PSX 60 Hz)
- PSX cycles emitted: 103 M (= 20.6 M/sec, **61% of real PSX 33.87 M/sec**)
- Cycles per VBlank: 289 k (vs real 565 k = 51% of real)

So game-internal time runs at ~60% of real-PSX rate. Cycle-paced
events (DMA completion, MDEC decode, etc.) all proportionally slow.
Could combine with IRQ-rate issue to amplify the slowness — needs
disentangling.

### Forward path

1. Identify exactly WHICH IRQ handler in the chain at `0x800974E0`
   writes state=2 — narrow to MDEC-DMA-done vs CDROM-done etc. by
   reading the chain entries' function pointers and matching against
   known PSX IRQ handlers.
2. Find why the source IRQ fires at 6.7 Hz when it should fire
   faster. Most-likely candidates: (a) DMA channel 1 (MDEC out)
   completion timing in `runtime/src/dma.c`, (b) cycle-pacing
   amplifying delay because guest cycles tick at 60% real.
3. Fix in `runtime/src/dma.c` and/or `runtime/src/psx_cycles.c`,
   verify with `tools/_mdec_pace.py` (target: 0.250+ decodes/VBlank
   = 15+ fps).

### Tools added this session for this issue

- `tools/_mdec_pace.py` — FMV decode-rate measurement
- `tools/_fn_dump.py` — hot-function tally over fn_entry_dump
- `tools/_wtrace_state.py` — state-field halfword-write filter
- `tools/_wtrace_byte.py` / `_wtrace_value.py` — value-filtered wtrace
- `tools/_dbg.py` — generic debug-server CLI (handles string vs int
  field encoding correctly)

These are gitignored (`tools/_*.py`) — keep them under that umbrella
unless a tool becomes critical enough to promote (drop the leading
underscore).

---

## Issue #5 — OPTIONS → black screen

**Status:** first divergence located 2026-05-13 on `options-and-newgame`.
Initial memcard-WRITE theory below is **WRONG** (left as a cautionary
record; see "Reset: state-comparison with beetle" at the bottom).

### First-divergence finding (2026-05-13, late session)

Per `F:\Projects\recomp-template\NES\PRINCIPLES.md` #3 (first-divergence
debugging): extended `psx-beetle.exe` to accept `--disc <cue>` so it
can boot Tomba alongside our runtime. Navigated both to OPTIONS.
Beetle: renders the OPTIONS UI (MESSAGE FAST, SOUND STEREO, ADJUST
SCREEN, CONFIG MENU). Our runtime: black screen.

Diffed RAM 0x80090000..0x801F0000 (1.44 MB of game state) between
the two via `tools/_first_divergence.py`. **First diverging byte:**

| address      | runtime | beetle |
|--------------|---------|--------|
| `0x80090C9C` | `0x00`  | `0x03` |

All bytes before differ in 0; total differing bytes downstream: 122k.

### Trace of the writer in static code: NOT FOUND

The address is read at offset `+0xC9C` (= 3228) from a 0x80090000
base by many static functions (grep `read_byte(... + 3228)` finds 13
sites in `generated/SCUS_942.36_full.c`). **No corresponding writes
in static generated C** — grep for `write_byte/half/word(... + 3228)`
returns zero. Wtrace on the runtime over a 3-second window with
range narrowed to `0x80090C9C..0x80090CA0` also captured zero writes.

Implication: the writer is either
- **In overlay code** (RAM-installed, run by `dirty_ram_interp`), OR
- A pointer-chain store where the effective address resolves to
  `0x80090C9C` but the static C uses a base register that we can't
  easily grep for.

Either way the OPTIONS state never gets its bit-3 set in `*0x80090C9C`,
and the OPTIONS draw code (reading +0xC9C) sees 0 and takes the
"don't draw" branch. Black screen.

### Reset: state-comparison with beetle (process-of-record)

The work above followed the right method (state comparison, first
divergence, no theorizing). Earlier in the session I went off on
multiple wrong theories (MDEC IDCT, stuck animation, memcard WRITE).
Those notes are removed/struck below to keep the record clean. The
finding above stands and is the correct starting point.

### Forward path next session

1. Relaunch both runtimes cleanly, navigate both to title screen,
   arm wtrace on `0x80090C9C..0x80090CA0` in our runtime BEFORE
   pressing the OPTIONS-entry input.
2. Press OPTIONS-entry. Even though our path ends black, the writer
   for `0x80090C9C` may still be invoked once at state-transition
   time before failing. Capture its PC + RA.
3. If no write captured on our side, the divergence is upstream of
   the writer — a CONDITION that's true on beetle but false here.
   Trace that condition by reading `mem_words` at the test address
   from each reader's compare.
4. Beetle as cross-reference is useful but FRAGILE — minimize debug
   queries against it (it appears to crash or wedge under heavy
   tooling). Use it for one-shot snapshots, not sustained probing.

### (Original — INCORRECT — memcard-WRITE theory below, kept for record)

---

## Issue #6 — Runtime hard-freezes ("Not Responding") under heavy debug queries

**Status:** root-cause hypothesized 2026-05-13. Independent of any
game bug — affects both `psx-runtime.exe` AND `psx-beetle.exe`.

### Symptom

Both binaries' SDL windows enter Windows-level "Not Responding" state
after extended sessions, with partial framebuffer corruption visible
(top half = last rendered scene, bottom half = garbage from
uninitialised memory). Reproducible by issuing repeated heavy debug
queries.

### Root-cause hypothesis

Debug server runs on the **main thread** — called from
`sdl_vblank_present` in `runtime/src/main.cpp` via
`debug_server_poll()`. Heavy queries (e.g. `wtrace_dump count=200000`
allocates ~100 MB JSON buffer + sends over TCP; `fn_entry_dump
count=16384` similar; `gpu_frame_dump count=8192` smaller but still
non-trivial) block the main thread for seconds. During that block:
- SDL event pump doesn't run → Windows marks the window non-responsive
- Audio buffer underruns or queues up
- VRAM presentation stalls — only the top half of the framebuffer
  may have been updated when the stall hit

Beetle has the same architecture (`beetle_main.cpp` calls
`beetle_debug_server_poll` per frame).

### Forward path (when next addressed)

Three options, in increasing order of correctness:
1. **Cap query sizes on the SERVER side.** wtrace_dump count default
   200000 is too high; cap at ~1024 and require explicit
   pagination. Easy patch.
2. **Stream large dumps across frames.** Server splits a big dump
   into per-frame chunks, returns "continue" tokens. Medium effort.
3. **Move debug server to its own thread.** Correct fix; SDL thread
   never blocks on debug work. Requires read-side synchronisation
   on ring buffers (currently single-writer/single-reader assumed).
   Larger refactor.

### Workaround (today)

Avoid bulk queries: prefer `count<=2000` for wtrace_dump /
fn_entry_dump, query small RAM windows (≤16 KB) one at a time
instead of `read_ram len=0x200000`.


### Diagnosis chain

1. In OPTIONS-black, `gpu_frame_dump frame=N` shows only **11 GP0
   commands per frame** — all environment-setting (texpage,
   drawarea, drawoffset, etc.) + one fill-rect + four NOPs.
   **Zero draw primitives.** Tomba's OPTIONS state is clearing the
   back buffer and drawing nothing.
2. `fn_entry_dump` (8000 entries over 31 VBlanks) shows the hot
   function is `0x8006B4EC` (2575 calls = ~83/frame). Reading it
   in `generated/SCUS_942.36_full.c:244638`: it reads PSX Timer 1
   value (MMIO `0x1F801120`) and Timer 2 (`0x1F801128`). This is a
   timeout/timer poll.
3. The caller `func_800695C4` (`generated/SCUS_942.36_full.c:238133`)
   wraps it in a poll loop reading `halfword[mem[0x80097574]+4]`.
   `mem[0x80097574] = 0x1F801040` — that's the **SIO0 register
   base**, and offset +4 is `JOY_STAT`. The mask `& 0x0001` is the
   TX-ready bit. So the OPTIONS state is doing SIO transfers and
   waiting on TX_RDY with a timer timeout.
4. `sio_state` confirms heavy SIO traffic (~334 TX writes/sec) but
   no progress: `mc_max_state: 17`. State 17 in our memcard state
   machine is **MC_WRITE_ACK1** (`runtime/src/sio.c:785`). Tomba is
   **WRITING to memcard** — almost certainly saving OPTIONS
   settings on entry to the OPTIONS screen.
5. State machine advanced 0 → 1 → … → 17 then stuck. Never reached
   MC_WRITE_ACK2 (state 18). Meanwhile sio_ctrl = 0x0000 (SIO de-
   selected by the game). Game gave up on the WRITE after reaching
   ACK1.

### Why it stalls

Our `MC_WRITE_CHK` → `MC_WRITE_ACK1` transition writes `rx = 0x00,
SIO_STAT_ACK |= 1` (runtime/src/sio.c:769-771). Then on the next TX
byte we'd transition to `MC_WRITE_ACK2` returning `rx = 0x5C`.

But Tomba doesn't send that next TX byte. It either:
- Reads our rx byte (0x00), interprets it as wrong, aborts;
- Or hits its timeout (Timer 1/2 check in func_8006B4EC) and aborts;
- Or its post-WRITE-CHK protocol expects a specific ack sequence we
  don't deliver in the right cycle window.

Same family as memo `phase4_card_chain_real_structure` (chain-reads
stalled at byte 11/16 area for similar SIO byte-interleaving
mismatches).

### Forward path

1. Read Tomba's WRITE handler (caller of `func_800695C4` that
   eventually triggers the memcard WRITE sequence) — find the
   post-CHK byte sequence it expects.
2. Compare against `runtime/src/sio.c` MC_WRITE_ACK1 / ACK2 / END
   responses. Look for byte-value mismatch, cycle-timing mismatch,
   or missing intermediate state.
3. Reference Mednafen / Beetle's memcard WRITE implementation in
   `beetle-psx/mednafen/psx/sio.cpp` for the canonical response
   sequence + timing.
4. Fix in `runtime/src/sio.c`, verify by entering OPTIONS and
   checking that mc_max_state advances past 17 and a draw primitive
   eventually appears in `gpu_frame_dump`.

Estimated effort: 1-3 hours of focused SIO protocol comparison.

---

## Issue #3 — Title-screen cluster: attract / NEW GAME / OPTIONS / menu glyphs

**Status:** open, observed 2026-05-13
**Branch:** `tomba-in-game`

### Symptoms (user-confirmed on `psx-runtime` port 4470, Tomba boot)

- **A.** Title menu navigation between NEW GAME ⇄ LOAD works (D-pad
  reaches and returns from the LOAD GAME screen cleanly).
- **B.** **NEW GAME → black screen.** Expected: another FMV
  (game-intro / story setup). Suspected related to FMV pipeline
  (see Issue #1) or a missing CDROM seek for the post-title cinematic.
- **C.** **OPTIONS → black screen + soft stall.** Game appears alive
  (frame counter advances) but never renders the OPTIONS UI.
- **D.** **Title menu glyph text ("NEW GAME / LOAD") renders fuzzy /
  garbled** while surrounding logo + "© 1997 WHOOPEE CAMP" text
  render clean. Same family as `psxrecomp-v4/ISSUES.md` #3
  (BIOS-shell glyph corruption) — likely shared discovery-gap for
  no-prologue GTE/COP2 leaves used by the menu's glyph upload path.
- **E.** **Attract demo returns to play after the title screen sits
  idle.** Disables debugging because every multi-minute investigation
  loses the menu state. Prior sessions had an `extras.c`-shaped
  override to suppress this for development; the override is gone
  (not present in either repo's working tree or git history).

### Investigation progress (2026-05-13, no fix yet)

Two-snapshot RAM diff against full Tomba RAM while idle on title
identified four frame-rate-tick state words in BSS:

| Address      | Writer RA    | Pattern                       |
|--------------|--------------|-------------------------------|
| `0x80090DB4` | `0x80061490` | counter; `func_80061480` sets it to `func_80067C30()+240` every frame → *deadline-in-future* refresh, never fires (not the attract trigger) |
| `0x80090D08` | `0x8005F8A4` | toggles `0x80↔0xC0` per frame → display double-buffer flag |
| `0x800974D4` | `0x8006E47C` | per-frame counter, doesn't reset on pad input |
| `0x8009B4DC` | `0x8006AC20` | per-frame counter, doesn't reset on pad input |

None of these is the attract-idle trigger. Cross and Right pad
presses via debug-server `press buttons=...` did not reset any of
them. **Suspected real attract counter is byte/halfword-sized
(missed by 32-bit word diff) or in a region not yet diffed.**

### Side observation worth verifying

`press buttons=0xBFFF` (Cross) and `buttons=0xFFDF` (Right) issued
from the debug server wedged the runtime to a black screen even
from a stable title — but the same keys typed at the SDL window
navigate menus cleanly. Either the inverted-bit convention is
wrong for this debug server build, or `handle_press` is not
asserting the buttons on enough consecutive frames. Worth fixing
before more input-driven probing — every investigation that needs
to drive menus depends on it.

### Recommended next-session approach (per `feedback_use_ring_buffer`)

Do **not** poll + diff. Free-run on title, let attract fire
naturally, then query the always-on `fn_entry` ring backwards from
the attract-transition frame to find the trigger callsite. From
there read the generated C to find the idle-counter address +
threshold, then wire a config-gated override
(`game.toml [debug] disable_attract = true` → framework hooks the
incrementer to pin to 0).

### Fuzzy-glyph investigation progress (2026-05-13)

Repro screenshot: `audit_notes/title_fuzzy_repro_2026_05_13.png`.
"NEW GAME → LOAD" renders with visible **vertical stripes** (every
other pixel column in wrong palette/color). "PRESS [START] or X
BUTTON" (blinks on/off — animation, not a bug) and the static
"© 1997 WHOOPEE CAMP" line render clean using the same font.

GP0 opcode totals at title (lifetime; ~6 min uptime):

| Opcode | Count | Meaning                                  |
|--------|-------|------------------------------------------|
| 0x00   | 52195 | NOP                                      |
| 0x01   | 8945  | clear cache                              |
| 0x02   | 2471  | fill rect (back-buffer clears)           |
| 0x28   | 296   | mono quad opaque                         |
| 0x2C   | 13613 | **textured quad opaque blended**         |
| 0x30   | 360   | shaded tri opaque                        |
| 0x38   | 180   | shaded quad opaque (Gouraud)             |
| 0x64   | 36944 | **textured rect var-size opaque blended**|
| 0x65   | 4367  | textured rect 16×16                      |
| 0xA0   | 8632  | CPU→VRAM copy (texture/CLUT uploads)     |
| 0xE1-6 | ~2799 | state-setting (texpage, twindow, etc.)   |

`capture_quads` on a stepped frame returned 0 entries — menu text
is **not** drawn via shaded quads (0x38). It's almost certainly
0x64 (textured rects) since that's the dominant primitive.

**Blocker for further investigation:** no per-frame GP0 command
ring buffer in the runtime. Lifetime opcode counts don't tell us
which `0x64` calls draw the menu vs the press-start blink vs the
copyright text. Two paths:

1. **Add a per-frame GP0 capture ring** to `runtime/src/gpu.c` —
   captures last N frames of (opcode, header, payload) plus the
   per-primitive draw position. Then `gpu_frame_dump frame=N`
   returns the stream. Real framework work (~1-2 hours). Persistent
   and reusable across all future GPU bugs.
2. **Build `psx-beetle` for TombaRecomp** so a side-by-side title
   capture shows what NEW GAME / LOAD should look like. Framework
   already supports the target via `runtime/runtime.cmake`; need to
   add a `psx-beetle` invocation in `TombaRecomp/CMakeLists.txt`.
   Faster (~30m) but doesn't help future per-frame GPU debugging.

### Fuzzy-glyph root-cause shape established (2026-05-13, post-3cfcdab)

Path 1 above shipped as commit `3cfcdab` in psxrecomp-v4
`tomba-in-game`. Ring captures every GP0 command with frame stamp;
`gpu_frame_dump frame=N` returns the per-frame stream.

Using the new tool on a paused title frame (frame 3413, decoded by
`tools/_2c_track.py`), the fuzzy menu text is **6 GP0(0x2C)
textured-quad commands at Y=168** with **degenerate top-right
vertices**. Pattern across 12 consecutive captured frames is
**identical** (NOT animation):

| Glyph | v1 (top-left) | v2 (top-right) | v3 (bot-left) | top_dx |
|-------|---------------|----------------|---------------|--------|
| 1     | (250, 168)    | (250, 168)     | (250, 184)    | 0      |
| 2     | (249, 168)    | (250, 168)     | (249, 184)    | 1      |
| 3     | (244, 168)    | (247, 168)     | (244, 184)    | 3      |
| 4     | (240, 168)    | (244, 168)     | (240, 184)    | 4      |
| 5     | (235, 168)    | (240, 168)     | (235, 184)    | 5      |
| 6     | (230, 168)    | (235, 168)     | (230, 184)    | 5      |

The texture U coords inside the same commands (e.g. U1=0x08, U2=0x10
on glyph 1) are correct 8-pixel-wide character strides — texture
math is right. **Only the vertex X-coords are wrong**: every
glyph's `v2.x` equals the PREVIOUS glyph's `v1.x` (right edge of
glyph N = left edge of glyph N-1), and the rightmost glyph has
`v2 == v1` (zero-width top). Result: each quad collapses to a
right-triangle covering the bottom-left half of the character box,
adjacent characters' empty triangles abut → visible as the
"vertical stripes" the user sees.

Left-group quads (X=121-185, same frame, also GP0(0x2C)) render
normal 8×16 rectangles. So the bug only affects the right
sub-section — six characters fitting "LOAD!" / "NEW GAME"
proportions.

**Forward path to fix:**

1. `wtrace_range` over the linked-list-packet RAM region while
   stepping a single title-screen frame to capture the GP0(0x2C)
   write site. (Find by reading the DMA ch.2 OTC linked-list head
   in `dma.c` state.)
2. From the writer PC, identify the function in
   `generated/SCUS_942.36_full.c` that constructs the menu-text
   GP0 packet.
3. Compare its v2.x computation against the v1.x / v4.x ones. The
   bug is either:
   - A recompiler mis-translation (a register that should hold W
     instead holds 0/wrong value at the v2.x store).
   - A Tomba quirk relying on real-PSX edge behavior we don't
     replicate (less likely; would have manifested broadly).
4. Fix in `recompiler/src/code_generator.cpp` (if recompiler bug),
   regen Tomba, rebuild, verify with the same per-frame dump.

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
