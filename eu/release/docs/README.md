# Tombi! (Europe, SCES-01330 Rev 1) - v0.23.0-alpha

This Windows x64 build supports **Tombi! (Europe) (En,Fr,De,It,Nl) (Rev 1)**:
SCES-01330, raw BIN SHA-1 `2505d958b4439d04844cadd3f968fc7432a48e00`.
Use the separate SCES01331-Rev1 download for English/Spanish/Portuguese/Swedish/Danish.

Extract the whole ZIP into a writable folder and run `TombiRecompEU.exe`.
Select your own matching BIN/CUE and press Launch. Keep the BIN beside its CUE.
OpenBIOS is included; no installed Python/compiler or retail BIOS is required.
Windows 10/11 x64 and a working OpenGL driver are required.

The original game menu selects English, French, German, Italian or Dutch.
The launcher's interface language is a separate setting. Confirm the game
language explicitly before the opening sequence.

## Features and controls

- **Widescreen** starts on with Fit to Window, which follows resizing from
  4:3 through 34:9. Fixed 16:9, 21:9 or 32:9 and disabling it remain available
  in Mods. Existing saved choices are preserved.
- **Seamless Loading** and **Geometry Optimization** start on. Native opening
  overlays are included; unsupported requests retain the original behavior.
- **Skip FMVs** is available as an optional mod for this disc group.
- **HD Texture Packs** and **Bezel Artwork** start off and need compatible
  external resources. No replacement artwork or game assets are supplied.
- Controller mapping, display, volume, HQ SPU and Fast Forward use the shared
  launcher. Digital mode accepts D-pad and left-stick directions; Hybrid
  Controller is optional. Builds start in a normal window.

Keep all companion folders beside the executable. Settings are stored in
`settings.toml`, mod choices under `mods/`, and Memory Cards under `saves/`.
Exit the game before copying cards. Keep USA and European cards separate and
preserve a backup of existing progress when replacing a build.

The alpha has scoped opening/gameplay and widescreen validation; complete
campaign content and every controller/audio combination are not certified.
See [releases](https://github.com/mstan/TombaRecomp/releases) for the current
validation scope. The [HD texture guide](docs/HD_TEXTURE_PACKS.md) describes
compatible resource formats.

Thanks to **michaelm-afk** for the European integration, and to PSXRecomp,
recomp-ui, OpenBIOS and the other contributors. Project and dependency notices
are included in `LICENSE` and `licenses/`. No game image, retail BIOS or personal
Memory Cards are included.
