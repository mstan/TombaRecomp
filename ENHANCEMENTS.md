# TombaRecomp — Deferred Enhancement Ideas

Ideas worth doing later. Active bugs live in `ISSUES.md`.

---

## E1 — FMV auto-skip for ALL movies (IMPLEMENTED 2026-06-18)

**Status:** IMPLEMENTED + USER-VALIDATED on master. When `auto_skip_fmv` is on and
an FMV is detected (MDEC decoding + XA streaming), the runtime writes the CURRENT
movie's per-movie frame-total (`[video] fmv_skip_total_table` + `movie_id*2`, with
`movie_id` read from `fmv_skip_movie_id`) down to `fmv_skip_end_total` (3). Tomba's
MDEC player (`FUN_8001efe8`) tears a movie down when the streamed frame number
reaches `total − 3`, so the lowered total ends it on the next frame — a NATURAL end
that reaches EVERY movie (Whoopee Camp logo, opening, in-game cutscene movies),
including ones whose caller never polls the skip button. Only the active movie's
table entry is touched; present-suppress + audio mute hide the 1–2 transition
frames. Runtime-only, no regen; the launcher's "Skip FMVs" toggle drives it. Config
in `game.toml` ([video] `fmv_skip_total_table=0x80077728`,
`fmv_skip_movie_id=0x1F8001CD`, `fmv_skip_end_total=3`); generic fallback (no table
configured) = START injection. The historical RE notes that led here are kept below.

### What's already on master (works, unchanged)
`[video] auto_skip_fmv` → when an FMV is detected (MDEC decoding + XA streaming,
in `main.cpp` `sdl_vblank_present`) the runtime holds START so the game's own
cutscene handler aborts the movie. Works only for movies that poll the pad.

### What's on this branch (scaffolding + a DEAD END)
- `config_loader.{h,cpp}`: new `[video] fmv_exit_flag` (guest RAM addr).
- `main.cpp`: when `fmv_exit_flag` is set, the per-FMV-frame hook writes `1` to
  that guest address instead of injecting START.
- `game.toml`: `fmv_exit_flag = 0x8009b044`.

**This flag-write approach DOES NOT WORK — verified empirically (movie kept
playing; `0x8009b044` read back as `1` while the player ignored it).** Keep the
config/`main.cpp` per-frame hook as scaffolding, but repurpose what it writes
(see levers below). Do NOT trust the original RE that said `0x8009b044` is the
exit trigger.

### The REAL termination mechanism (verified — disasm + live RAM)
The MDEC movie player is `FUN_8001f1c0` @0x8001f1c0 (movie state byte at
scratchpad `0x1f8001cc`; substate at `*(_DAT_1f8001d4 + 0x48)`; context pointer
at scratchpad `0x1f8001d4`). It ends a movie when the per-frame consumer
`FUN_8001efe8` @0x8001efe8 sets the substate to 3 (teardown):

```c
// FUN_8001efe8, once StGetNext returns a ready frame (descriptor = local_14):
if ((int)*(short *)(&DAT_80077728 + DAT_1f8001cd * 2) - 3U <= *(uint *)(local_14 + 8)) {
    *(undefined2 *)(_DAT_1f8001d4 + 0x48) = 3;   // substate = 3  => teardown
}
```

- `DAT_80077728[movie_id]` = **per-movie total-frame table** (u16). Movie id is
  the byte at scratchpad `0x1f8001cd`. VERIFIED LIVE: entries for ids 0,1,2,3,4…
  read `1414, 366, 316, 467, 110, 152, 181, 181, 182, 227, …` — sane frame
  counts. Table base `0x80077728` is static main-EXE data.
- `*(local_14 + 8)` = the **running frame number**, sourced from the streamed
  STR sector data (filled into the ring descriptor by the data-ready ISR
  `FUN_800670d0`).
- So the movie ends when `streamed_frame_number >= total_frames - 3`. There is
  no CD-XA EOF/EOR involvement, and the `0x8009b044` flag is only consulted on
  the teardown PATH *after* this decision — which is why writing it does nothing.

### The two clean levers to implement next (pick one; A is simpler/universal)

- **LEVER A — poke the frame-total table (recommended).** When `auto_skip_fmv`
  is on, write `DAT_80077728[movie_id]` (or the whole ~24-entry table) down to a
  small value so `(total-3) <= frame#` is true at frame 0 → instant teardown.
  CAUTION: the check is `total - 3U` (unsigned), so a total `< 3` underflows to a
  huge number and BREAKS the test — clamp the poked value to `>= 3` (e.g. 4).
  Universal across all 23 movies, no STR-format knowledge needed, runtime-only.
  The existing `main.cpp` per-FMV-frame hook can do the poke each detected frame
  (cheap, idempotent). NOT yet verified end-to-end — was about to test (via the
  `write_ram` debug command) when parked. First check whether the table is
  re-initialised per movie load; if so, poke continuously (the per-frame hook
  already does) or hook the load.
- **LEVER B — data swap (the original "1 black frame" idea).** At the CD
  chokepoint `psxrecomp/runtime/src/cdrom.c` `read_sector_at` (shared by all
  games), rewrite the streamed STR video sectors' frame-number field to `>=`
  the movie total so the player ends after one frame. Needs the exact STR-header
  offset that lands at descriptor `+8` (trace via StGetNext `FUN_80066fec` +
  ISR `FUN_800670d0`) — NOT yet pinned. `main.cpp` already suppresses present +
  mutes audio while skipping, which blacks out the single transition frame.

### On-disc STR format (Tomba, verified from `tomba.bin`, raw 2352-byte sectors)
- 23 movies in `MOVIE/` (LBA 22146–88710), e.g. `LOGO.STR` @57830,
  `OP_INST.STR` @74422 (the "Tomba in grass" opening), `100US.STR` @22146,
  `END_US.STR` @39050.
- Video sectors: Mode 2, submode `0x48` (DATA|REALTIME), coding 0.
- Audio sectors: submode `0x64` (AUDIO|FORM2|REALTIME), coding `0x01`, ~1 per 7
  video sectors. EOF (`0x80`) set only on the final sector — but Tomba's player
  ignores the CD-XA sub-header entirely.

### Key player addresses (SCUS-94236 main EXE, base 0x80010000)
- `FUN_8001f1c0` @0x8001f1c0 — movie player state machine.
- `FUN_8001efe8` @0x8001efe8 — per-frame consumer; sets substate=3 via the
  frame-count check above (the real end trigger).
- `FUN_80066fec` — StGetNext (returns 0 = frame ready w/ descriptor, else nonzero).
- `FUN_800670d0` — CD data-ready ISR (builds ring descriptor from STR header).
- `DAT_80077728` — per-movie total-frame table (u16, indexed by movie id).
- `0x1f8001cc` movie state byte; `0x1f8001cd` movie id; `0x1f8001d4` context ptr.
- `0x8009b044` — player loop flag; DEAD END for external writes (see above).
- `FUN_80020c00` — cutscene-script abort (the Start/Cross path); not the player
  teardown.
