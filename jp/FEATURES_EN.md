# Regional feature scope

| Feature | USA | EU1 | EU2 | Japan candidate |
| --- | --- | --- | --- | --- |
| Common launcher and checked regional routing | Yes | Yes | Yes | Yes |
| Original game languages | English | Five original languages | Five original languages | Japanese |
| Separate settings and default cards | Yes | Yes | Yes | Yes |
| Native boot / guarded overlay fallback | Yes | Yes | Yes | Yes, 24 precompiled images |
| Normal controller, audio, Fast Forward | Shared implementation | Shared implementation | Shared implementation | Shared implementation; physical-device check remains manual |
| Seamless Loading | Existing | Existing | Existing | Optional RC2; shared loader with checked Japanese profile; default off |
| Geometry Optimization | Existing | Existing | Existing | Hidden; packet ABI unverified |
| PGXP Precision | Existing framework support | Existing | Existing | Verified in ordinary gameplay; off by default |
| Hybrid Controller | Existing | Existing | Existing | Hidden; legacy Japanese PadRead path needs an adapter |
| HD Texture Packs | External matching pack | External matching pack | External matching pack | Shared renderer; Japanese-target installer fixtures passed |
| Bezel Artwork | External image | External image | External image | Shared renderer; external image |
| FMV Skip | Existing, default off | Existing, default off | Hidden | Optional RC2; 22 checked original movie bindings; default off |
| Widescreen renderer | Existing, default off | Existing, default off | Hidden | Hidden |

The unchanged EU backends retain their previous defaults and test results.
Japanese defaults preserve the prototype baseline (native scale, digital pad,
original SPU path, NTSC-J, windowed OpenGL, VSync off). Optional Japanese mods
start off. Existing user settings always take precedence. The launcher retains
the official memory-card Browse implementation.

Owner-confirmed Japanese prototype results include boot, controls, Japanese
text/menus and saving/loading. The expanded build passes original New Game,
walk/jump/land, audio generation and PGXP-on/off checks. A regular area
transition and return, final visible UI/device acceptance and campaign-wide
play remain open. Read JAPAN_HANDOFF_EN.md and JAPAN_TEST_DE.md before acceptance.
