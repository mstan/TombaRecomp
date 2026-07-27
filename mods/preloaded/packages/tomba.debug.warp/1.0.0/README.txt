Enable Warp Debug Menu

This default-disabled feature enables the original game's warp debug menu by
setting the low byte at scratchpad offset 0x01B4 to 1 after game startup.

The implementation is trusted code compiled into TombaRecomp. This package
contains only metadata selecting the stable tomba.warp-debug plugin id.

Credits

T4g1 — discovery and reverse-engineering
mstan — plugin implementation
