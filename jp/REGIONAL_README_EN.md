# TombaRecomp regional Windows package

Extract the complete package to a new writable directory and run
`Start-TombaRecomp.cmd` (or `TombiRecompEU.exe`, the shared entry point).
Use the original launcher Browse control to select your legal CUE/BIN disc.
The launcher checks the serial, track size and complete SHA-256, then restarts
into the matching native backend. PLAY uses that backend's normal verification.
The last selected disc is remembered. No game files are included.

| Disc | Original game languages | Backend directory |
| --- | --- | --- |
| SCUS-94236 | English | backends/SCUS-94236 |
| SCES-01330 Rev 1 | English, French, German, Italian, Dutch | package root |
| SCES-01331 | English, Spanish, Portuguese, Swedish, Danish | backends/SCES-01331 |
| SLPS-01144 | Japanese | backends/SLPS-01144 |

Each backend keeps its own settings and `saves/<serial>/card1.mcd` / `card2.mcd`
under its directory. Existing installations and cards are not imported or moved.
To test an existing save, select a COPY using the original memory-card picker.
Cross-region save compatibility is not established. Launcher language remains
English and is independent of the game's original languages.

The US and European feature sets are retained. EU2 still hides unverified FMV
skip and widescreen. Japan provides normal graphics/audio, digital controller,
native boot and guarded overlays with interpreter fallback, and optional PGXP.
HD textures require a matching external pack; bezel artwork requires an image.
These remain off initially. RC2 adds optional Seamless Loading and FMV Skip.
Both are off initially; enable Seamless Loading under Mods for transition testing.
Japanese Geometry Optimization, Hybrid Controller and Widescreen remain hidden.
Fast Forward and normal audio/video settings use the shared framework.

Japan starts with native resolution, windowed OpenGL, VSync off, original digital
pad and original SPU path. PGXP is off; select at least 2x internal scale to see
sub-pixel rendering clearly. Existing settings take precedence over defaults.
Original NTSC-J timing and Japanese text resources are preserved. English words
on the original Japanese title menu are intentional. Confirm Japanese dialogs
with Circle; Cross jumps in gameplay.

See `JAPAN_HANDOFF_EN.md` for verified scope and deferred bindings. Confirm an
ordinary Japanese area transition and return on a new or copied card before
treating this candidate as fully accepted. A whole-game playthrough is not
claimed. OpenBIOS is included under its license; Sony BIOS and original game
resources are not included. No development tools need to be installed to play;
the bundled overlay fallback tools are runtime dependencies.
