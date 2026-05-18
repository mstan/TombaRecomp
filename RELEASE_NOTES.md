# TombaRecomp v0.1.2-alpha

Status: the first gameplay area is believed playable.

Changes since v0.1.1-alpha:

- Added Xbox-style controller support through SDL/XInput.
- Added configurable controller mapping via `input.ini`.
- Release build now clearly prompts for both required user-owned assets:
  `SCPH1001.BIN` BIOS and a Tomba! disc image.
- Fixed the missing PlayStation BIOS logo symbol.
- Fixed fuzzy title-menu text for `NEW GAME`, `LOAD GAME`, and `OPTIONS`.
- Fixed dialog and pause-menu textured quad seam artifacts.
- Improved in-game shaded textured primitives, including the first-area branch
  end cap.

Known limitations:

- Some audio/SPU behavior remains partial.
- The historical Windows "Not Responding" hang is mitigated, but longer
  in-game soak testing is still useful.
- This package does not include the PS1 BIOS, Tomba disc image, generated game
  source, save data, or copyrighted Sony/Whoopee Camp assets.
