Tomba Frame Interpolation

This default-disabled mod presents blended intermediate frames above the game's
60Hz output through the stable tomba.frame-interpolation plugin id.

It is presentation only. Guest VBlank, game logic, timers, and audio keep their
stock cadence, so this changes how smooth the game looks and not how fast it
runs. The separate native-VBlank-rate mechanism does change whole-machine speed
and is deliberately not exposed by this package.

Output rate selects the presentation cadence: 'Display refresh' follows the
measured monitor refresh, and the fixed rates pace presentation at that many
frames per second. Interpolation is an OpenGL presenter feature, so enabling it
selects the OpenGL renderer and uses its presentation scheduler instead of
driver vsync.

This replaces the launcher's former Settings row for frame interpolation, which
the shared PSX launcher profile offered on every title. Tomba already owned
widescreen and Skip FMVs as mods; this brings the third generic display toggle
in line so every optional change to the game lives in one place.

Credit

mstan — mod integration
