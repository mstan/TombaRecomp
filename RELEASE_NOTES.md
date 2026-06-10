# TombaRecomp v0.1.6-alpha

The "pigs are safe to throw" release.

## Highlights

**The new-game crash is fixed.** Right after starting a new game, throwing
one pig into another pig (and certain other early collisions) could kill
the game — sometimes a solid blue screen with the music still playing,
sometimes the window closing outright. Thanks to a player crash report
(issue #1 — the attached diagnostic files were exactly what we needed),
we caught the crash live and traced it to the seam between the two ways
TombaRecomp runs game code: areas already converted to fast native code
and areas still running in compatibility mode. When a native-code function
called into a compatibility-mode function, the return trip could sail past
its caller and re-run part of the frame with a stale stack, quietly
corrupting the game's main loop. The return path now stops exactly where
it should, and the original crash no longer reproduces. (High-level
technical: the interpreter's block-chaining fast path ignored the dispatch
loop's return-address contract, so suspended native frames double-executed
their tails; the contract is now enforced at every chain boundary.)

**Better black-box recorder for crash reports.** When a fatal error does
happen, development builds now preserve the entire diagnostic state for
inspection instead of exiting, and every build writes a fuller crash
report. Player bug reports with the `psx_crash.txt` /
`psx_last_run_report.json` / `psx_freeze_dump_*.json` files next to the
executable remain the single most useful thing you can attach to an issue
— this release exists because someone did exactly that.

## Also in this release

- Display-control activity is now recorded continuously in development
  builds (groundwork for fixing the boot-logo flicker some players have
  noticed).
- Same bundled community overlay cache as v0.1.5; newly visited areas are
  still recorded into `overlay_captures.json` for contribution (see "Help
  make your game faster" in README.md).

## Known limitations

- Leaving the game unattended for a long time (10+ minutes idle on
  menus/attract screens) can still wedge it; under investigation.
- Some audio/SPU behavior remains partial.
- Areas no one has contributed yet still run in compatibility mode until
  someone visits them (see above — that someone could be you).
- This package does not include the PS1 BIOS, Tomba disc image, generated
  game source, save data, or copyrighted Sony/Whoopee Camp assets. You
  supply your own legally obtained BIOS and disc image.
