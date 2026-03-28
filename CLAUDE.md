# PSXRecomp v2

**Goal**: Generic PS1 static recompiler — any PS1 game → native PC binary.

**MVP target**: Tomba! — get it running to the main menu. That proves the toolchain works and builds
the shared foundation (MIPS→C emitter, BIOS stubs, runner) that makes every subsequent game easier.

This is NOT a PS1 emulator. We are NOT cycle-accurate. We are NOT exhaustively documenting functions.
We are translating MIPS machine code to C, compiling it, and running it on the PC. That's it.

Tomba is the vehicle. The recompiler is the product.

---

## ██████████████████████████████████████████████████
## ██  RULE 0: TCP DEBUG SERVER FIRST. ALWAYS.     ██
## ██████████████████████████████████████████████████

**ALL debugging starts with the TCP debug server.** Query live game state via
`python psxrecomp/tools/dbg.py`. Read RAM, set watchpoints, pause/step, check
registers, query frame history. Do NOT parse stdout logs. Do NOT add printf traces.

**RULE 0.1: If the TCP server can't answer your question, BUILD the command.**
Add a new handler to `debug_server.c`. The server is the debugging interface —
extend it, don't work around it.

Logs (stdout/stderr) are a LAST resort, not a debugging strategy.

**Other tools (secondary):**

1. **PSXE interpreter** (`psxrecomp/tools/interp/`) — full PS1 emulator for ground truth
   comparison and function discovery. Run: `psxe -a -b BIOS.BIN game.cue`

2. **Ghidra** — for decompiling unknown game-specific functions. Not required for BIOS calls
   (PS1 BIOS is publicly documented) or runtime infrastructure work.
   Ghidra address = PS1 address (no offset — raw binary loaded at 0x80010000).

3. **Annotations** — when you confirm what a function does, annotate it in
   `annotations/SCUS_942.36_annotations.csv` so generated code is self-documenting.

---

## ██████████████████████████████████████████████████
## ██  RULE 1: NEVER TOUCH generated/tomba_full.c  ██
## ██████████████████████████████████████████████████

`generated/tomba_full.c` is a BUILD ARTIFACT. It is output from the recompiler.

**NEVER read it whole. NEVER modify it. NEVER patch it.**

If something is wrong in the generated code → fix `recompiler/src/code_generator.cpp` and regenerate.

`tomba_full.c` is ~11MB / 200K+ lines. Reading it whole **destroys the context window**.
- Need to find a function? `Grep for the address`
- Need to read it? `Read with offset + limit`
- Need to change it? **You don't. Fix the recompiler.**

---

## The Loop (this is the entire development methodology)

```
1. BUILD runner            →  runner + generated/tomba_full.c → PSXRecompGame.exe
2. RUN game (timed)        →  start, wait 30s, kill
3. OBSERVE visual output   →  Read C:/temp/game_screenshot.bmp  (auto-saved every 300 frames)
                               Compare against src/main.jpg (the reference)
4. OBSERVE log output      →  cat /c/temp/game_output.txt | tail -50
5. IDENTIFY bug            →  wrong colors → shader; wrong geometry → GPU decode; crash → Ghidra
6. GHIDRA if needed        →  understand what the PS1 code actually does
7. FIX the bug             →  opengl_renderer.cpp / gpu_interpreter.cpp / runtime.c
8. GOTO 1
```

## Debugging Hierarchy

When investigating a bug, use the most effective tool:

**TCP debug server** — first line of defense. Pause the game, read RAM, set watchpoints,
query frame history. Connect: `python psxrecomp/tools/dbg.py`

**PSXE interpreter** — ground truth for behavioral questions. Run the same game in the
full emulator and compare state. Also discovers function entry points automatically.

**Ghidra** — for unknown game-specific functions where decompilation helps understand logic.
Not needed for BIOS calls or well-documented PS1 hardware behavior.

**INTERP-CALL trace** — for overlay debugging. Overlay functions (≥0x80098000) run through
the MIPS interpreter; their JAL calls to compiled code show up in INTERP-CALL logs.

**Targeted printf** — last resort. Log ONE specific value. If you need more than one new
printf per investigation cycle, use the debug server instead.

Session resume after context clear: **say "Run the game."**

---

## Visual Debugging

The game auto-saves screenshots every 300 PS1 frames (~5 seconds at 60Hz).

| File | Contents |
|------|----------|
| `C:/temp/game_shot_01.png` .. `game_shot_10.png` | Numbered screenshots every 300 frames (~5 sec) |
| `C:/temp/game_vram.png` | Full 1024×512 PS1 VRAM at frame 300 — textures, CLUTs, framebuffers |
| `src/main.jpg` | **Reference** — what the main menu should look like |

**How to observe output yourself:**
```bash
# 1. Kill any running instance
powershell.exe -NoProfile -File "C:/temp/kill_game.ps1"
# 2. Start game in background
powershell.exe -NoProfile -File "C:/temp/run_in_console.ps1" -bat "C:/temp/psxrecomp_run_game.bat" &
# 3. Wait for screenshots to accumulate
sleep 30
# 4. Kill game
powershell.exe -NoProfile -File "C:/temp/kill_game.ps1"
# 5. Read screenshots (use Read tool — PNG files, small enough to view)
# Read: C:/temp/game_shot_01.png  (frame 300, ~5 sec)
# Read: C:/temp/game_shot_05.png  (frame 1500, ~25 sec)
# Read: C:/temp/game_vram.png     (full VRAM at frame 300)
```

**Compare:** Read `C:/temp/game_screenshot.bmp` and `src/main.jpg` side by side.
- Reference: blue sky, green grass, colorful "TOMBA!" logo, "NEW GAME / LOAD" text
- Wrong colors mean shader/CLUT bug
- Wrong geometry means GPU decode bug
- Missing content means VRAM upload or OT decode bug

---

## Build Commands

Build system is **CMake/Ninja** with **MinGW GCC** (from MSYS2 mingw64 shell).
MSVC also works for compiling but the game crashes at runtime — use MinGW.

```bash
# Build must run from proper MSYS2 mingw64 shell:
C:/msys64/msys2_shell.cmd -mingw64 -defterm -no-start -c "COMMAND"

# Configure (first time only)
cmake -S . -B build -G Ninja

# Build runner (most common)
ninja -C build

# Run game
./build/TombaRecomp.exe isos/SCUS_942.36_no_header isos/tomba.cue

# Debug server (while game is running)
python psxrecomp/tools/dbg.py ping
python psxrecomp/tools/dbg.py regs
python psxrecomp/tools/dbg.py pause

# Build + run interpreter (function discovery)
cd psxrecomp/tools/interp && make
./bin/psxe -a -b ../../isos/SCPH1001.BIN ../../isos/tomba.cue
# Output: discovered_functions_live.log
```

Key paths: recompiler at `psxrecomp/build/recompiler/PSXRecomp.exe`, game at `build/TombaRecomp.exe`.

---

## Key Files

| File | Purpose | Touch? |
|------|---------|--------|
| `recompiler/src/code_generator.cpp` | MIPS→C emitter — THE PRODUCT | Yes — this is what we fix |
| `recompiler/src/recompilation.cpp` | Function/branch translator | Yes if needed |
| `runner/src/runtime.c` | Memory map, call_by_address stubs | Yes — add BIOS implementations here |
| `runner/src/main_runner.cpp` | GLFW window, load EXE, run loop | Yes — minimal changes only |
| `generated/tomba_full.c` | **GENERATED. NEVER TOUCH.** | **NEVER** |
| `generated/tomba_dispatch.c` | **GENERATED. NEVER TOUCH.** | **NEVER** |
| `isos/SCUS_942.36_no_header` | Game binary (PS1 EXE, header stripped) | Never |
| `annotations/SCUS_942.36_annotations.csv` | Per-function Ghidra notes → emitted as comments in generated C | Yes — add when a function is confirmed |

---

## Annotation Rule

**When Ghidra confirms what a function does, add it to the annotations CSV.**

File: `annotations/SCUS_942.36_annotations.csv`

Format:
```
0x8001dfd4, entity tick dispatcher — iterates 200 entity slots at 0x800A5970, stride 0xD4
```

The comment appears as `/* [NOTE] ... */` above the function signature in `tomba_full.c`
after the next `PSXRecomp.exe` regeneration. This makes the generated code self-documenting
without ever reading `tomba_full.c` whole.

**When to annotate:** after confirming the function's purpose (via Ghidra, debug server, or PSXE comparison). Not speculatively.
**Annotation scope:** function-level only (one entry per function start address).
**For other games:** create `annotations/<serial>_annotations.csv` — same format, picked up automatically.

---

## Log File Rule

**Every `.c` or `.cpp` file that implements hardware/BIOS behavior gets a sibling `.log` file.**

`runtime.c` → `runtime.log`
`bios_kernel.c` → `bios_kernel.log` (if created)

Log entry format:
```
[function_name]
Ghidra: <what the decompiler showed>
Rationale: <why implemented this way>
```

This is the audit trail. It lives next to the code. It does NOT go in the source file as comments.
It does NOT appear when grepping the source. It is reference only.

---

## Architecture

**This is a static recompiler.** The MIPS binary is translated to C once. The C is compiled to a
native x64 binary. No interpreter loop. No cycle counting. No emulation.

**JAL = direct C function calls.** `func_80012345` calls `func_80067890` directly in C.
`call_by_address()` handles only dynamic jumps (BIOS calls, jump tables).

**runtime.c starts empty.** When the game crashes on an unknown BIOS call, `call_by_address`
logs the address. Look it up in Ghidra. Implement it in `runtime.c`. Log it in `runtime.log`.

**Do not pre-implement anything.** If the game hasn't crashed on it, it doesn't need implementing yet.

---

## What NOT to Do

- Do not pre-emptively implement BIOS functions "just in case"
- Do not read large sections of tomba_full.c for "context"
- Do not guess what a function does — check with debug server, PSXE, or Ghidra
- Do not add override/patch mechanisms to avoid fixing the recompiler
- Do not carry assumptions from any previous project or conversation
- Do not write verbose documentation — a one-line log entry is enough
- Do not run tests as primary development driver — run the game

---

## Progress Milestones

| Milestone | Status |
|-----------|--------|
| Recompiler generates tomba_full.c | ⬜ |
| Runner links and boots | ⬜ |
| Any GPU packets produced | ⬜ |
| Any pixel visible | ⬜ |
| Main menu visible | ⬜ |
| Main menu interactive | ⬜ |
