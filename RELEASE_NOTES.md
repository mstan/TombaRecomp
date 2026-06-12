# TombaRecomp v0.1.8-alpha

The "launcher + hardware rendering" release.

## New

**A startup launcher.** TombaRecomp now opens to a settings screen before
the game boots. From there you pick your PlayStation BIOS and Tomba disc,
choose the renderer, supersampling, anti-aliasing and screen-colour look,
set up your controller, and check your memory cards — all in one place,
with your choices remembered for next time. (Your previously saved BIOS and
disc are picked up automatically, so you won't have to re-select them.)

**Hardware OpenGL rendering.** A new GPU-accelerated renderer is now the
default. It moves the heavy drawing work off the CPU and onto your graphics
card, so detail-heavy areas — like the mushroom forest — stay at full speed
even with 2x supersampling turned on. You'll need a GPU with OpenGL 3.3 or
newer (effectively any machine from the last decade); if the GPU renderer
can't start for any reason, TombaRecomp automatically falls back to the
software renderer, so it always runs.

You can switch back to the software renderer in the launcher, or in
`game.toml` under `[video]` with `renderer = "software"`.

## Notes

Graphics and gameplay settings still live in `game.toml` under `[video]`
and `[runtime]` — edit and restart to apply, or use the launcher. As
before, this package does not include the PS1 BIOS or the Tomba disc; you
supply your own (the launcher asks for each one and remembers them).
