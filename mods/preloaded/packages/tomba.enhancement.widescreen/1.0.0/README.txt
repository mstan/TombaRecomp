Tomba Adaptive Widescreen

This default-disabled mod enables Tomba's native-wide adaptive rendering path.
Fit follows the live window from 4:3 without an upper aspect limit. Its
projection, culling, sprite, HUD, and backdrop hooks remain inert at native
4:3 and are activated through the stable tomba.widescreen plugin id.
Terrain chunk selection follows the live viewport plus a guard band. Persistent
HUD groups anchor to the actual left/right edges as the window is resized.

This is a spike: content coverage and overlay-specific enemy spawning at
expanded boundaries still need gameplay validation, especially at extreme widths.

Credit

mstan — widescreen implementation and mod integration
