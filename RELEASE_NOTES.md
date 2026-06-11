# TombaRecomp v0.1.7-alpha

The "sharper picture" release.

## New

**The game looks sharper.** It now renders at 2x the original resolution
with anti-aliasing, so edges and characters are cleaner and less blocky.
This is on by default. If you want to change it, open `game.toml` and look
for the `[video]` section: set `supersampling = 1` for the original PSX
look, or `3`/`4` for even sharper edges if your PC can keep up (higher
settings cost more, so drop back down if the game slows).

**Optional texture smoothing.** A new `texture_filtering = "bilinear"`
setting in `[video]` softens textures and 2D backgrounds. It's off by
default so the original look is kept; turn it on if you prefer a smoother
picture.

## Fixed

**A freeze during play.** Following on from the crash fix in the last
release, this catches a related case where the game could still lock up
after certain object interactions. It should no longer happen.

## Notes

The graphics settings live in `game.toml` under `[video]` — edit the file
and restart to apply. As before, this package does not include the PS1
BIOS or the Tomba disc; you supply your own.
