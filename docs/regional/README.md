# European launcher additions (October 2026)

Contributed by [michaelm-afk](https://github.com/michaelm-afk) in the
24 October 2026 handoff and integrated through the shared framework and
launcher. The German notes in this folder are the contributor's earlier test
records. This page covers only what changed.

## Cover gallery

The launcher shows the bundled box art (`eu/launcher_assets/img/boxart.tga`,
from the libretro PS1 box-art set) until you choose your own covers.
**Browse Covers** opens a folder picker for the verified disc; the launcher reads
PNG, JPG, JPEG and TGA files from that folder without copying or changing them.
Files are ordered front, back, disc, then by name; arrows step through them and a
click enlarges the current one. The choice is saved per disc serial in
`artwork/<serial>/cover-folder.txt` beside the launcher, relative when the folder
is inside the installation. Cover scans and manuals are never part of this
repository or a release package.

## Quick controls

EU1 and EU2 set `[launcher] quick_controls = true`. The dashboard then shows a
**Quick Mods** card next to the memory cards, listing Widescreen and Seamless
Loading (their manifests set `quick = true`), and a **Quick Settings** card
with VSync, Internal resolution, Screen mode and Screen model. Any listed mod can
be added or removed with **Show in Quick Mods** on the Mods page.

## Wait for Language Confirmation (SCES-01331)

The original SCES-01331 release's language selector continues on its own after a
countdown. This mod holds the countdown until you press Cross, like the existing
SCES-01330 mod. It checks the selector's original code before every write and
does nothing after the selector. `eu2/boot_profile.py` verifies the executable at build time; the mod
is omitted for the Rev 1 disc, whose selector binding is not verified.

## Not integrated

- RetroAchievements: held until RetroAchievements approves a recompiled client.
- The Windows-only multi-region entry program (`launcher_entry/`): a
  multi-region chooser belongs in the shared launcher on every platform.
- Ore! Tomba (Japan, SLPS-01144): kept on its own branch until it reaches
  feature parity with the USA and European builds.
- USA default changes (1080p, VSync off, SPU HQ on): the USA build is unchanged.
