# TombaRecomp

**Tomba! (USA, SCUS-94236) running on the [PSXRecomp](https://github.com/mstan/psxrecomp) v2 static recompiler.**

[![PSXRecomp demo](https://img.youtube.com/vi/CID9oVhgCyY/maxresdefault.jpg)](https://www.youtube.com/watch?v=CID9oVhgCyY)

*(Demo footage is from the v1 prototype, hosted in the framework repo. v2's progress is described under "Status" below.)*

---

## What this is

This repository contains the game-specific glue for running Tomba! on PSXRecomp v2:

- `game.toml` — Tomba's executable metadata (entry point, load address, stack, seeds).
- `seeds/ghidra_funcs.txt` — function-start addresses from Ghidra, fed to the recompiler.
- `seeds/tomba_bios_thunks.txt` — BIOS A0/B0/C0 call sites inside Tomba.
- `audit_notes/` — annotated reading of the v1 prototype's game-specific runtime code (FMV player, overlay manager, GPU interpreter, etc.), kept as reference while the v4 framework reimplements each subsystem properly.
- `tools/regen.ps1` — regenerates the recompiled C from your local Tomba binary.
- `psxrecomp-v4.pin` — pinned commit of the framework this game is known to build against.

It does **not** contain Tomba game code, the Tomba disc image, or any decompiled Tomba C. Those are produced locally from your own legally-obtained disc.

---

## Status

| Stage | State |
|---|---|
| PS1 logos (Sony Computer Entertainment) | Works |
| Disc-detected screen ("Licensed by SCEA") | Works |
| Whoopee Camp "Presents" FMV | Plays slowly (MDEC video decode is incomplete) |
| Tomba intro FMV | Plays slowly, skippable |
| Main menu | Reachable |
| Gameplay | **Not reached** |

CD-ROM emulation in the underlying PSXRecomp framework is partial — disc reads work well enough for boot, FMV streaming, and main-menu navigation, but multi-sector / interleaved-XA streaming during gameplay has not been validated.

This is **heavy WIP**. There is no release binary yet; you have to build from source.

---

## Setup

### Requirements

- **Windows 10/11 x64**.
- **Tomba! (USA, SCUS-94236)** disc image — `.cue` + `.bin`. You must provide your own legally-obtained dump. Not included.
- **Sony SCPH1001 BIOS ROM** (`SCPH1001.BIN`). You must provide your own. Not included.
- MSYS2 with the `mingw-w64-x86_64` toolchain, CMake ≥ 3.20, SDL2.
- Optional: Ghidra (for analyzing the EXE and producing additional seeds).

### Build

```sh
# Clone both repositories side-by-side.
cd F:/Projects
git clone https://github.com/mstan/psxrecomp.git psxrecomp-v4
git clone https://github.com/mstan/TombaRecomp.git
cd TombaRecomp

# Link the framework into this tree. On Windows this is a directory junction;
# adjust for your shell.
cmd //c "mklink /J psxrecomp-v4 ..\psxrecomp-v4"

# Drop in your assets (DO NOT commit these).
mkdir -p tomba bios saves
# Copy your Tomba disc image: tomba/tomba.cue + tomba/tomba.bin
# Copy your SCUS_942.36 EXE if you want regen.ps1 to find it: tomba/SCUS_942.36
# Copy your BIOS dump: bios/SCPH1001.BIN (or symlink to psxrecomp-v4/bios/)

# Build the recompiler (one-time).
cd psxrecomp-v4
cmake -S recompiler -B recompiler/build -G "Unix Makefiles"
cmake --build recompiler/build
cd ..

# Regenerate Tomba's recompiled C. This reads tomba/SCUS_942.36 and writes
# generated/SCUS_942.36_full.c + _dispatch.c. Re-run whenever seeds change.
pwsh tools/regen.ps1

# Build the runtime with Tomba's recompiled code linked in.
cmake -S . -B build -G "Unix Makefiles"
cmake --build build --target psx-runtime

# Run. --game game.toml is required to boot Tomba; without it the binary
# falls back to a discless BIOS boot.
./build/psx-runtime.exe --game game.toml
```

The runtime is built from the framework's shared runtime sources plus the freshly-generated `SCUS_942.36_*.c`. The result is a native binary that boots SCPH1001 BIOS → loads Tomba from your disc image → runs the game's MIPS-translated-to-C natively.

---

## How to use

### Keyboard map

| PSX button | Keyboard |
|---|---|
| D-Pad Up / Down / Left / Right | Arrow keys |
| Cross (✕) | X |
| Square (□) | Z |
| Circle (○) | S |
| Triangle (△) | A |
| L1 / R1 | Q / W |
| L2 / R2 | E / R |
| Start | Enter |
| Select | Right Shift |
| Turbo (fast-forward, no render) | Tab (hold) |

### Memory cards

Saves live in `saves/card1.mcd` and `saves/card2.mcd` — standard 128 KB raw PS1 memory card images. They are interchangeable with files from PCSX-Redux, Duckstation, ePSXe, mednafen, and other PS1 emulators.

### Caveats

- **FMVs play slowly.** MDEC video decode is software-only and not optimised.
- **Audio is partial.** XA-ADPCM streaming works; SPU does not yet model reverb, sweep, or noise.
- **No gameplay yet.** The game boots to the main menu but does not progress past it cleanly.

---

## Rules (development)

- Use the real recompiled BIOS and the real hardware simulation in PSXRecomp v2.
- No HLE BIOS shims, no stubs, no fake events, no hand-edited generated files.
- Framework changes go in [`mstan/psxrecomp`](https://github.com/mstan/psxrecomp), not here.
- See `CLAUDE.md` for the full architecture rules.

---

## License

PolyForm Noncommercial 1.0.0 — see [`LICENSE`](LICENSE). Non-commercial use (personal, educational, research, hobbyist) is welcome. Commercial use requires a separate license — contact via [1379.tech](https://1379.tech).

Tomba! is © Whoopee Camp / Sony Computer Entertainment. This repository contains none of Tomba's copyrighted content; everything game-specific is generated locally from your own legally-obtained disc.
