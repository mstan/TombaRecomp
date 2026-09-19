Tomba Custom Renderer

This default-disabled mod enables Tomba's native-wide adaptive rendering path.
Fit to Window is the default and follows live resizing from 4:3 without an
upper aspect limit. The dropdown also offers 16:9, 21:9 and 32:9, all using
the same custom native-wide renderer. The old 16:9 squash path is retired.
With this mod disabled, Tomba uses its stock 4:3 renderer. The custom
projection, culling, sprite, HUD, and backdrop hooks remain inert at native
4:3 and are activated through the stable tomba.widescreen plugin id.
Terrain chunk selection follows the live viewport plus a guard band. Persistent
HUD groups anchor to the actual left/right edges as the window is resized.

This is a spike: content coverage and overlay-specific enemy spawning at
expanded boundaries still need gameplay validation, especially at extreme widths.

Credit

mstan — widescreen implementation and mod integration
