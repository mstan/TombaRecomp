# TombaRecomp v0.1.5-alpha

The "smoother, faster, doesn't freeze" release.

## Highlights

**The random freeze is fixed.** Some players (and our own long play
sessions) hit a freeze where the game window would suddenly stop dead —
picture frozen, no input, had to kill it from Task Manager. It could strike
at any time, even while idle, and faster loading made it strike more often.
We finally caught it in the act: a one-in-a-million timing accident in the
code that paces the game to TV speed could put the program to sleep for —
literally — about 24 days. That code has been rebuilt so the accident is
impossible, and an automated test now guards it. (High-level technical: a
race between two clock reads could underflow an unsigned sleep duration;
frame pacing now reads the clock once per decision and caps every sleep at
one frame.)

**Loading screens are now fast — on by default.** TombaRecomp now runs the
console at full host speed during loading screens (the screen that used to
sit there for seconds now flashes past, typically 3-5x faster). This was
ready earlier but shipped disabled because it made the freeze above more
likely; with the freeze fixed it's on for everyone. If you ever want
authentic load times back, set `turbo_loads = false` in `game.toml` — no
rebuild needed, options are plain text now.

**The game gets faster the more the community plays — and this release
ships everyone's progress so far.** Tomba streams chunks of its code off
the disc as you reach new areas. Chunks we've seen get converted into fast
native code; chunks nobody has visited yet run in a slower compatibility
mode. This release bundles a `cache` folder with native code for all areas
contributed so far, so those areas are fast from your very first visit.
And while you play, newly visited areas are recorded into
`overlay_captures.json` next to the executable — share that file on a
GitHub issue and the next release makes *your* areas fast for everyone,
permanently. It's a snowball: every player session can make the game
faster for all players. (See "Help make your game faster" in README.md.)

**Smoother on stubborn graphics drivers.** If the graphics driver starts
stalling the picture (seen on some NVIDIA setups: the game crawls at less
than one frame per second for minutes), TombaRecomp now detects it and
switches itself to its own internal frame timing. The game keeps running
at full speed instead of slideshow-ing.

**Clearer first-run setup.** The two files you supply — your PlayStation
BIOS (SCPH1001.BIN) and your Tomba! disc image — are now asked for with
step-by-step dialogs that say exactly which file is wanted, what it's
called, and what it is NOT, so there's no guessing which picker you're
looking at.

## Also in this release

- Production builds run without a console window and with the development
  instrumentation compiled out — measurably less overhead per frame.
- If something does go wrong, the runtime still writes a diagnostic
  `psx_freeze_dump_*.json` next to the executable; attaching that file to
  a bug report tells us almost everything we need.
- Player options (`turbo_loads`, `disc_speed`, BIOS-logo skip) live in
  `game.toml` and can be changed with a text editor — no rebuild.

## Known limitations

- Some audio/SPU behavior remains partial.
- Areas no one has contributed yet still run in compatibility mode until
  someone visits them (see above — that someone could be you).
- This package does not include the PS1 BIOS, Tomba disc image, generated
  game source, save data, or copyrighted Sony/Whoopee Camp assets. You
  supply your own legally obtained BIOS and disc image.
