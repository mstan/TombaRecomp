# TombaRecomp

Tomba! (USA, SCUS-94236) running on
[PSXRecomp](https://github.com/mstan/psxrecomp) v4.

[![PSXRecomp demo](https://img.youtube.com/vi/CID9oVhgCyY/maxresdefault.jpg)](https://www.youtube.com/watch?v=CID9oVhgCyY)

## What This Is

This repository contains the game-specific configuration, seeds, tools, and
build glue for running Tomba on the PSXRecomp framework.

It does not contain the Tomba disc image, the PS1 BIOS, generated game code, or
any decompiled Tomba C. Those are generated locally from your own legally
obtained assets.

Important files:

- `game.toml`: Tomba runtime/recompiler configuration.
- `seeds/`: Ghidra-derived function starts and game-specific seed data.
- `tools/regen.ps1`: regenerates the Tomba recompiled C output.
- `psxrecomp-v4.pin`: framework commit this project is known against.
- `ISSUES.md`: game-specific issue log.

## Status

Current milestone as of 2026-05-17:

| Area | State |
|---|---|
| PS1 BIOS boot | Works |
| Disc-detected / license screen | Works, with a known missing PS-logo glyph |
| Whoopee Camp FMV | Works |
| Intro FMV | Works and is skippable |
| Title menu | Works |
| OPTIONS | Works |
| NEW GAME | Works |
| Save prompt / memory-card save | Works |
| LOAD GAME / memory-card load | Works |
| Gameplay | Reaches the first in-game area |

Known follow-up work:

- `NEW GAME / LOAD / OPTIONS` title text is still fuzzy.
- In-game rendering still needs visual correctness work.
- Some audio/SPU behavior is partial.
- The title menu intentionally returns to the attract/demo flow after idling.
- The historical Windows "Not Responding" hang is mitigated but should remain
  under observation during longer in-game sessions.

## Setup

Requirements:

- Windows 10/11 x64.
- Tomba! (USA, SCUS-94236) disc image (`.cue` + `.bin`). Not included.
- Sony SCPH1001 BIOS ROM (`SCPH1001.BIN`). Not included.
- MSYS2 with the `mingw-w64-x86_64` toolchain, CMake 3.20+, and SDL2.

Example local layout:

```sh
F:/Projects/psxrecomp-v4
F:/Projects/TombaRecomp
F:/Projects/TombaRecomp/tomba/tomba.cue
F:/Projects/TombaRecomp/tomba/tomba.bin
F:/Projects/TombaRecomp/bios/SCPH1001.BIN
```

Build and run:

```sh
cd F:/Projects/TombaRecomp
cmake -S . -B build -G "Unix Makefiles"
cmake --build build -j16
./build/psx-runtime.exe --game game.toml
```

If generated game output is missing or stale, regenerate first:

```sh
pwsh tools/regen.ps1
cmake --build build -j16
```

## Controls

| PSX button | Keyboard |
|---|---|
| D-Pad Up / Down / Left / Right | Arrow keys |
| Cross | X |
| Square | Z |
| Circle | S |
| Triangle | A |
| L1 / R1 | Q / W |
| L2 / R2 | E / R |
| Start | Enter |
| Select | Right Shift |
| Turbo | Tab (hold) |

## Memory Cards

Runtime memory-card files are local artifacts and must not be committed. The
current runtime uses raw PS1 memory-card images compatible with DuckStation,
PCSX-Redux, Mednafen, ePSXe, and similar emulators.

## Development Rules

- Use the real recompiled BIOS and real hardware simulation in PSXRecomp v4.
- No HLE BIOS shims, no stubs, no fake events, no hand-edited generated files.
- Framework changes go in `mstan/psxrecomp`, not here.
- Game binaries, generated code, memory cards, Ghidra databases, and build
  outputs stay local.
- See `CLAUDE.md` for project-specific rules.

## License

PolyForm Noncommercial 1.0.0. See `LICENSE`.

Tomba! is copyright Whoopee Camp / Sony Computer Entertainment. This
repository contains none of Tomba's copyrighted content.
