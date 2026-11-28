# Ore! Tomba (Japan) - TombaRecomp

A native PC port of the original Japanese release, SLPS-01144. You need your own
copy of the disc; no game data is included.

## Start

1. Run `TombaRecompJP.exe`.
2. Select your Ore! Tomba (Japan) disc image (single-track MODE2/2352 BIN/CUE,
   289430064 bytes, BIN SHA-1 `c86baf702303e7e0963b99aff307b1c40e40478a`).
3. Press Launch.

OpenBIOS is bundled; no retail BIOS, Python or compiler is required. Keep the
whole folder together.

## Mods

| Mod | Default |
| --- | --- |
| Seamless Loading | On. The first launch prepares a cache from your disc. |
| Widescreen | On with Fit to Window. Fixed ratios and disabling it remain available. Existing saved choices are preserved. |
| Skip FMVs | Off. |
| PGXP Precision, HD texture packs, bezel artwork, CRT Filter, Image Filtering, Internal Resolution, Enhanced Audio, Rewind | Off (shared framework mods). |

The game reads a digital pad; the left stick and the D-pad both move Tomba.
The original Japanese text and menus are kept. Confirm dialogs with Circle;
Cross jumps.

## Saves

Memory cards are in `saves/`. Japanese saves are separate from the USA and
European releases.

## Not included yet

Geometry Optimization (a speed-only feature of the USA/European builds) is not
ported to the Japanese code yet; the original code runs with identical output.
