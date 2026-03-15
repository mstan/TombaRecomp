# TombaRecomp

**Tomba! (USA) running natively on PC via [PSXRecomp](https://github.com/mstan/psxrecomp)**

> Tech demo — not intended to be a complete or fully playable experience.

*Read about how it was built: [I Built a PS1 Static Recompiler With No Prior Experience (and Claude Code)](https://1379.tech/i-built-a-ps1-static-recompiler-with-no-prior-experience-and-claude-code/)*

[![TombaRecomp gameplay demo](https://img.youtube.com/vi/CID9oVhgCyY/maxresdefault.jpg)](https://www.youtube.com/watch?v=CID9oVhgCyY)

---

## What it is

TombaRecomp is a game-specific project built on the [PSXRecomp](https://github.com/mstan/psxrecomp) framework. The PS1 MIPS binary for Tomba! (SCUS-94236) is translated to C, compiled as a native x64 binary, and runs directly on PC with OpenGL rendering and audio.

This is **not** an emulator. There is no interpreter loop, no cycle counting, no accuracy trade-offs.

---

## Current status

**Working:**
- Main menu, attract FMV, SPU audio
- New Game -> gameplay (stable 30Hz)
- Tomba movement, jumping, camera
- Pig grab and throw
- Mace weapon attack
- Equipment menu

**Known issues:**
- Wrong sound effects in some situations; music can sound slightly off
- Some entities don't render fully correctly
- Save system is buggy
- Many softlock conditions exist

---

## Requirements

- **OS**: Windows 10+ (64-bit)
- **Compiler**: MinGW-w64 GCC (C++20, C17) via MSYS2
- **Build system**: CMake 3.20+ with Ninja
- **GPU**: OpenGL 3.3+
- **FFmpeg DLLs**: For FMV playback — place `avcodec-*.dll`, `avformat-*.dll`, `avutil-*.dll`, `swresample-*.dll`, `swscale-*.dll` next to the game exe
- **Game disc**: Tomba! (USA) — `SCUS_942.36` — you must provide your own legally obtained copy

---

## Building

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/mstan/TombaRecomp.git
cd TombaRecomp
```

### 2. Build the recompiler

```bash
cmake -S psxrecomp/recompiler -B psxrecomp/build/recompiler -G Ninja
ninja -C psxrecomp/build/recompiler
```

### 3. Generate translated C

```bash
psxrecomp/build/recompiler/PSXRecomp.exe isos/SCUS_942.36
```

This produces `generated/SCUS_942.36_full.c` and `generated/SCUS_942.36_dispatch.c`.

### 4. Build the game

```bash
cmake -B build -G Ninja
ninja -C build
```

### 5. Run

**Double-click** `build/TombaRecomp.exe` — a file dialog will ask for your CUE file on first run. The path is saved for subsequent launches.

Or use the CLI:
```bash
build/TombaRecomp.exe isos/SCUS_942.36_no_header "isos/Tomba! (USA).cue"
```

### Disc image setup

Place your Tomba! disc image in `isos/` (gitignored):

```
isos/
  SCUS_942.36              # PS1 executable (for recompiler)
  SCUS_942.36_no_header    # Headerless binary (strip first 2048 bytes)
  Tomba! (USA).bin         # Raw disc image
  Tomba! (USA).cue         # CUE sheet
```

To create the headerless binary:
```bash
dd if=SCUS_942.36 of=SCUS_942.36_no_header bs=2048 skip=1
```

---

## Controls

Default key bindings (configurable via `keyconfig.ini` next to the executable):

| PS1 Button | Key |
|------------|-----|
| D-Pad | Arrow keys |
| Cross (confirm) | S |
| Square | A |
| Triangle | W |
| Circle | D |
| Start | Enter |
| Select | ' (apostrophe) |
| L1 / L2 | 1 / 2 |
| R1 / R2 | 0 / 9 |

| Hotkey | Action |
|--------|--------|
| F5 | Toggle turbo mode |
| F11 | Dump VRAM |
| F12 | Screenshot |
| Escape | Quit |

---

## License

TombaRecomp is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE) — free for non-commercial use with attribution.

Tomba! is copyrighted by Whoopee Camp / Sony Computer Entertainment. Game assets and disc images are not included in this repository.

---

<sub>If this project was useful or interesting to you: [ko-fi.com/gamemaster1379](https://ko-fi.com/gamemaster1379)</sub>
