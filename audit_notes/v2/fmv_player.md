# v2 fmv_player.cpp Audit

Source: `F:/Projects/psxrecomp-projects/psxrecomp/runner/src/fmv_player.cpp` and `.h`

## Verdict

Do not salvage this file as a runtime subsystem.

It is an HLE FMV player. It opens the disc BIN directly, parses STR sectors itself, decodes the MDEC video stream in software, uploads RGB555 pixels directly to VRAM via `fmv_vram_upload`, forces the display area via `fmv_force_display_area`, and calls `psx_present_frame` with its own 15 FPS throttle. That bypasses the v4 hardware path: CDROM command/data FIFO, DMA channel 0/1, MDEC MMIO, DMA-to-GPU upload, and normal game-controlled display timing.

The file is still valuable as a reference for the Sony MDEC bitstream codec:

- STR demux constants and chunk assembly: raw sector size 2352, STR header at byte 24, 2016-byte video payload at byte 56.
- MPEG-1 style VLC tables, run/level tables, default intra matrix, and zig-zag order used by the PlayStation MDEC video codec.
- The block decode ordering used by FFmpeg's MDEC decoder: Cr, Cb, Y0, Y1, Y2, Y3.
- A working IDCT and YCbCr-to-RGB555 conversion path for visual comparison.

## Architectural Problems

- Direct file I/O: `fmv_player_init`, `fmv_player_seek`, and `fmv_player_tick` seek and read the BIN independently of the emulated CDROM controller.
- Direct presentation: decoded frames are uploaded and presented from the helper, not as a consequence of game-issued GPU commands.
- Forced display state: `fmv_force_display_area` is explicitly outside the game's normal GPU control path.
- Debug side effects: it writes PPM files and prints diagnostics. v4 forbids stdio/log debugging in runtime hot paths.
- Game-specific lifecycle: active/stop/seek decisions are driven by helper state rather than the recompiled game and BIOS interacting with hardware.

## Safe Uses

- Use the codec tables and arithmetic as a comparison oracle when implementing real MDEC decode in `runtime/src/mdec.c`.
- Use the STR sector parsing only to understand what Tomba likely streams from disc, not as a new direct demux layer.
- Do not add `fmv_player_*` APIs or direct VRAM upload hooks to v4.

## Immediate Implication For Tomba

The white-screen intro is not evidence that v4 should import v2's FMV player. It is evidence that Tomba has reached the point where the real CDROM/MDEC/DMA/GPU path matters. The next fix should instrument and correct v4's MDEC and DMA behavior, not bypass it.
