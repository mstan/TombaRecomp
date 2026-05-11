# v2 xa_audio.cpp Audit

Source: `F:/Projects/psxrecomp-projects/psxrecomp/runner/src/xa_audio.cpp` and `runner/include/xa_audio.h`

## Verdict

Do not salvage this file as a runtime subsystem.

It is an HLE XA player. It opens the disc BIN directly, runs a background reader thread, filters XA sectors itself, decodes XA-ADPCM to PCM, resamples to 44.1 kHz, and feeds WinMM `waveOut` directly. That bypasses CDROM XA routing, SPU CD input, SPU mixing, IRQ timing, and the recompiled game/BIOS hardware path.

The XA-ADPCM decode routine is useful as an algorithm reference, especially the 18 sound groups per sector, stereo 4-bit layout, and filter coefficients. It should not be copied in as a direct audio playback service.

## Architectural Problems

- Direct file I/O: `xa_audio_init` and the worker thread read raw sectors from the BIN outside the CDROM controller.
- Direct host audio: decoded PCM is sent to WinMM instead of entering the emulated SPU/CD audio path.
- Helper-owned channel selection: the file/channel lock is inferred by the helper, not by emulated CDROM filter hardware.
- Debug side effects: it prints diagnostics and writes `C:/temp/xa_capture.wav`.
- Threaded timing is detached from emulated CDROM/SPU timing.

## Safe Uses

- Use the XA-ADPCM decode math as a future reference for SPU CD/XA input support.
- Use the comments about sector layout and file/channel filtering to guide CDROM filter implementation.
- Do not add `xa_audio_*` APIs to v4 as game-facing behavior.

## Immediate Implication For Tomba

Missing FMV audio is expected once video reaches the STR path, because current v4 SPU notes say XA/CD input is not modeled yet. Video progress should come first through real MDEC/DMA. XA audio can follow by routing decoded CD-XA into the SPU mixer rather than by reusing v2's direct WinMM path.
