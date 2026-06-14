# TombaRecomp v0.1.9-alpha

The "skip the movies" release.

## New

**Skip FMVs.** A new optional setting fast-forwards Tomba's full-motion
videos (like the opening movie) so you can get straight to playing. When
it's on, a streaming video is skipped the instant it starts — the game
jumps cleanly to whatever comes next, exactly as if you'd pressed the skip
button yourself, with nothing shown and nothing left out.

Turn it on in the launcher under **Settings → Video → "Skip FMVs"** (it's
**off** by default), or in `game.toml` under `[video]` with
`auto_skip_fmv = true`. Your choice is remembered between sessions.

## Notes

Graphics and gameplay settings still live in `game.toml` under `[video]`
and `[runtime]` — edit and restart to apply, or use the launcher. As
before, this package does not include the PS1 BIOS or the Tomba disc; you
supply your own (the launcher asks for each one and remembers them).
