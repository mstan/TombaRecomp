## v0.16.1-alpha

Corrects which opening movie the Any% FMV option preserves.

- **Preserve title and ending FMVs (Any%)** now plays the opening before the
  title screen, the post-final-pig cutscene, and the credits, with audio.
- The movie after New Game is skipped along with the other in-run FMVs.
- The option remains off by default, retaining skip-all for All Events.
  Existing users who enabled it receive the corrected selection automatically.

Windows and Linux packages include prebuilt native code. Memory cards and
settings carry over. Start from a fresh boot or a memory-card save when
changing skip modes: quick-save states can retain shortened movie lengths.

## v0.16.0-alpha

Skip FMVs now has an optional **Preserve New Game and ending FMVs (Any%)**
setting. Enable it on the Mods page to play the opening after New Game,
the post-final-pig cutscene, and the credits normally, with audio.

- The movie before the title screen and all other FMVs still skip.
- The new setting is off by default. Existing Skip FMVs users retain the
  original skip-all behavior, including for All Events runs.
- Both modes are available in the existing mod; no separate mod is needed.

The New Game opening was checked through its transition into gameplay, and
the owner validated the corrected behavior. Tests cover every movie ID,
mode defaults, and transitions between skipped and preserved movies. The
ending and credits IDs are verified; a full endgame playthrough was not part
of this validation.

Windows and Linux packages include prebuilt native code. Supply your own
Tomba! USA disc. Existing memory cards and settings carry over. When switching
skip modes, start from a fresh boot or a memory-card save: quick-save states
made with skip-all may already contain shortened movie lengths.

## v0.15.3-alpha

Fixes Seamless Loading falling back to the dancing-pig loading screen in many
areas, rooms and pig arenas, and fixes the fullscreen keyboard shortcuts.

- The loading planner now accepts all 75 original sound-bank configurations.
  It previously rejected valid banks above index 15, causing normal loading
  screens depending on the destination and the music already loaded.
- Alt+Enter and Ctrl+F now recognize either left or right modifier key.
  Fullscreen toggling was checked on both the primary and a second monitor.
- Seamless Loading remains enabled by default, and existing opt-outs are
  preserved. Existing prepared asset caches can be reused. CD Speed and the
  host turbo loading option remain absent from the bundled mod list.

The production loading planner was checked against all 135 area/section
queues and 52 music/SFX lists (1,778 resource requests): valid queue rejections
fell from 138 to zero, while invalid-input guards remained intact. Fresh-boot
Haunted Mansion and Mushroom Forest loads, the project tests, and fullscreen
shortcut regression tests also passed.

This fixes the loading-screen fallback; cold first-entry timing and audio
hitches remain under investigation. Every door, wing and event route has not
been visually playtested. Stock SCUS-94236 assets are required.

Windows and Linux packages include prebuilt native code. Select your own disc
and launch; no compiler or ISO rebuild is required. Saves and settings carry
over from v0.15.2-alpha.

## v0.15.2-alpha

Fixes the dog bridge cutscene and quick-save restore softlocks.

- The dog crossing cutscene now completes with Custom Renderer enabled. Script
  visibility queries keep the original camera bounds while the wider view
  continues to draw normally.
- Quick-save restores resume gameplay instead of restarting the Whoopee Camp
  logo and stopping on a white screen. This includes restores immediately after
  launch and existing v0.15.0/v0.15.1 states containing a Seamless Loading call.
- New quick-saves defer captures while a host call is preserving guest registers,
  and retain the game-started state needed to resume safely.

Validated with the reported bridge state, walking across the bridge after the
cutscene, startup and running-session restores, and a new save/restore round
trip. Memory cards and settings carry over.

## v0.15.1-alpha

Simplifies the Mods page's Quality of Life list to **Seamless Loading**.

- CD Speed and Fast Loading (host pacing) are no longer bundled with Tomba.
- Tomba Fast Loading is hidden. If you had enabled it, it still appears so you
  can turn it off.
- No game, renderer or loading changes. Saves and settings carry over from
  v0.15.0-alpha.

## v0.15.0-alpha

**Seamless Loading is now a bundled mod, enabled by default.** It prepares the
disc's assets once and keeps them in memory, removing the dancing-pig loading
screen from supported menu loads and area transitions at normal game and audio
speed. The game's normal fades and music changes remain.

- Releases ship the compiled executable and native overlay cache. Players
  select their own Tomba! USA disc and launch; no compiler, Python, or Generate
  step is required. First launch prepares about 71 MiB of decoded data on disk,
  which later launches reuse. The disc remains required for movies and other
  original data.
- Disable **Seamless Loading** on the Mods page to restore retail loading.
  Existing explicit opt-outs are preserved. If you previously enabled the
  **Fast Loading** mod, disable it before using Seamless Loading.
- Validated with new-game startup, live memory-card loads, and walked
  transitions through Watch Tower and Dwarf Village. Captures show no loading
  screens or held transition frames on the tested route, and audio counters
  report no transition underruns or dropped output. Whole-game coverage,
  including every death, warp and event path, remains under test.
- Supports the stock SCUS-94236 disc. Asset replacement mods are not supported
  with Seamless Loading. Custom Renderer and the other enhancements remain
  opt-in. Linux retains the v0.14.1 file-picker fixes.

Windows and Linux packages require fresh original-disc extraction, native
builds and audits for all 25 configured overlay images. No disc image, decoded
asset cache, retail BIOS or save data is distributed. Older quick-save states
may not load; keep your previous installation and saves until verified.

## v0.14.1-alpha

Fixes the Linux file picker. On hosts where the desktop file dialog could not
run, Browse buttons did nothing at all -- no dialog, no error, no fallback.

- The AppImage no longer exports its own `LD_LIBRARY_PATH`. It was inherited by
  every process the game started, including the host `zenity`/`kdialog` opened
  for Browse, which then loaded this bundle's `glib`/`pcre2` against the host's
  GTK. Libraries that were only reachable that way are no longer bundled.
- A backend that cannot start is no longer mistaken for the player pressing
  Cancel, so the built-in browser now takes over instead of nothing happening.
- Every picker can fall back to the built-in browser, not just the ROM and BIOS
  rows: memory cards, mod packages, mod resource files and folders, ROM
  patches, shaders, SRAM import, and the first-run disc picker -- which
  previously dead-ended before you had a game selected.

No gameplay, renderer or save-format changes.

## v0.14.0-alpha

Tomba's opt-in **Custom Renderer** replaces the old fixed-16:9 widescreen
patches. Enable it on the launcher's Mods page; **Fit to Window** is the
default view and follows resizing without an upper aspect-ratio limit.
Fixed **16:9**, **21:9** and **32:9** use the same renderer. With the mod
disabled, the game retains its stock 4:3 renderer.

- Terrain selection and object visibility follow the expanded viewport.
- HUD groups anchor to the visible edges.
- The tested rooftop object-bank boundary retains both visible sides;
  floating foliage, background-terrain gaps and intermittent 4:3 black bars
  in the reported scenes are corrected.
- Validated on OpenGL through 64:9. Extreme-width content and enemy spawning
  remain experimental; this is not a claim of complete all-area coverage.

This release does **not** include speculative performance/HLE optimizations.
Very wide views can lower the game's frame rate because they add emulated
geometry work; see `docs/ADAPTIVE_RENDERER_PERFORMANCE.md` in the source tree.

**Quick-save compatibility:** the updated framework uses a newer snapshot
format. Older quick-save states may not load. Keep your previous installation
and saves; do not rely on an old quick-save as your only record of progress.
Normal save files are not migrated or overwritten by release packaging.

Windows and Linux packaging still requires fresh original-disc AOT extraction,
native builds and audits for all 25 configured overlay images. Supply your own
Tomba! USA disc (SCUS-94236); no disc or retail BIOS is distributed.

---

## v0.13.0-alpha

This release ships native overlay shards extracted ahead of time from all 25 configured original-disc images (17 area variants and eight support images). Both Windows and Linux packages verify shard ranges against original disc bytes and include an audit receipt. Interpreter and dynamic compilation fallbacks remain available; complete static coverage is not claimed.

Extraction and release auditing now use shared psxrecomp methods, also consumed by Tomba 2 US and Italian. Release packaging requires a fresh, complete extraction and successful native build.

# Tomba! Recompiled - v0.12.3-alpha

This patch restores the Tomba Skip FMVs mod's all-movie behavior.

## Fixes

- Skip FMVs once again uses Tomba's per-movie frame-total teardown metadata, so
  it skips movies whose original game callers never poll the skip button.
- The generic PSX Skip FMVs settings row remains hidden; activation still lives
  in the built-in Skip FMVs mod.
- Release packages continue to include the compiled setup shard cache.

---

# Tomba! Recompiled - v0.11.1-alpha

This patch accepts the Steam release's PlayStation disc payload directly.

## Steam disc image

- Steam's `t_data_u.car` can be selected in the launcher without renaming it
  to `tomba.bin`.
- The runtime treats `.car` as the same raw-sector image its contents already
  identify as; normal ISO9660, game-serial, and sector-layout checks still run.
- `.car` is included in the shared launcher, preparation picker, and native
  runtime file dialog.

---

# Tomba! Recompiled — v0.11.0-alpha

This release makes authentic loading and strict controller routing the
baseline, adds direct CHD support, and fixes the Windows ZIP layout.

## Loading

- Fast Loading is now a default-off mod instead of a generic Settings toggle.
- One dropdown makes recommended host-pacing modes mutually exclusive with
  experimental 2x, 4x, and instant emulated-CD timing.
- Host acceleration stops as soon as the sustained load ends, preventing turbo
  input from spilling into the first gameplay frame.
- Tomba no longer opts into generic turbo loads, idle skipping, accelerated CD
  timing, or the experimental warm-disc route by default.

## Discs and packaging

- `.chd` images now mount directly through pinned libchdr support, including
  embedded track metadata and CD audio sectors.
- Disc verification and mod targeting fingerprint reconstructed raw sectors, so
  compressing a supported dump does not change its identity.
- Release ZIP entries now use portable forward-slash paths and extract
  correctly outside Windows Explorer.
- An experimental x86-64 Linux AppImage ships the same launcher and preloaded
  mod catalog. Its read-only payload is separated from persistent settings,
  memory cards, installed mods, keybinds, and caches under XDG data storage.

## Controller routing

- The developer “any input” merge is now explicitly enabled only with
  `PSX_DEV_INPUT=1`. Normal launches keep the selected keyboard/controller
  isolated, avoiding stale or unrelated devices driving Hybrid controls.

---

# Tomba! Recompiled — v0.10.0-alpha

This release moves Tomba's optional enhancements into the launcher's Mods
catalog, overhauls controller selection, and exposes the original warp debug
menu as a default-off mod.

## Mods

- **Enhancements have moved to Mods.** Widescreen, Skip FMVs, frame
  interpolation, and the Special Edition Hybrid Controller now live on the
  launcher's **Mods** page instead of being duplicated in generic settings.
- **Frame interpolation** provides presentation-only 60Hz output while the
  game's simulation, animation, physics, timers, and audio keep their original
  cadence.
- **Enable Warp Debug Menu** exposes the original game's warp menu when
  starting a game. It is disabled by default and credited to T4g1 for the
  discovery and reverse engineering.

## Hybrid controller overhaul

- The normal controller setting is now an explicit **Analog** or **D-Pad**
  choice.
- The default-off **Special Edition Hybrid Controller** mod switches to digital
  mode when the D-pad is engaged and back to analog when the stick is moved,
  reproducing the intended variable-speed analog movement plus precise digital
  movement without one-frame disconnects or phantom inputs.
- Hybrid switching now follows the active physical controller even when the
  launcher uses automatic device routing.

## Runtime and packaging

- OpenBIOS is included and selected by default; a legally obtained retail BIOS
  remains optional.
- Built-in mod packages and their trusted implementations are bundled into the
  self-contained Windows x64 release.
- Current BIOS boot-skip parity, launcher Mods support, and renderer/settings
  fixes are included through the pinned PSXRecomp framework.

## Before playing

Supply your own legally obtained Tomba! (USA, SCUS-94236) disc image. It is not
included. This remains an alpha release; keep `overlay_captures.json` private
because it contains code captured from your own disc.

---

# Tomba! Recompiled — v0.9.0-alpha

This release replaces the old in-tree launcher with the shared Dear ImGui
launcher. Its DPI-independent layout keeps the Start Game button and settings
accessible at Windows display scaling levels such as 125%.
This addresses the launcher scaling failure reported in issue #11.

## Launcher and packaging

- The pre-game launcher now uses Dear ImGui, with the current Tomba box art,
  controller configuration, and memory-card management assets bundled beside
  the executable.
- Launcher fonts and controls scale without clipping the bottom of the window.
- Clean release builds now consume the output produced by the repository's
  pinned recompiler. They prefer its monolithic generated file while retaining
  support for newer split-output recompilers.
- The Windows package remains self-contained and includes the fallback overlay
  toolchain; no external Python or compiler installation is required.

## Runtime updates

- Updated to the current pinned `psxrecomp` runtime, including accelerated load
  handling and BIOS HLE fast boot.
- OpenGL remains the default renderer, with software rendering available as a
  fallback.
- Existing controller, memory-card, FMV-skip, and experimental widescreen
  options carry forward.

## Before playing

Supply your own legally obtained PlayStation SCPH1001 BIOS and Tomba! (USA,
SCUS-94236) disc image. Neither is included in this package. This remains an
alpha release; keep `overlay_captures.json` private because it contains code
captured from your own disc.

---

# Tomba! Recompiled — v0.8.0-alpha

This release moves Tomba to the latest `psxrecomp` runtime and promotes the
overhauled OpenGL path as the default renderer.

## OpenGL and presentation

- OpenGL presentation no longer performs synchronous per-frame GPU readbacks.
- Painter-ordered primitive batching substantially reduces submission overhead
  while preserving PlayStation draw order and transparency behavior.
- The launcher exposes the current renderer and high-refresh presentation
  controls. Gameplay and audio simulation remain at the original guest rate.
- The software renderer remains available as a reference and fallback.

## Runtime and stability

- Updated to framework commit `c94fcd5`, including the full-rate OpenGL work.
- The relocated PlayStation kernel now uses byte-verified static dispatch.
  Runtime-patched kernel bodies fall back to the faithful interpreter instead
  of executing stale native translations.
- BIOS HLE fast boot, authentic-timing turbo loads, memory cards, controller
  support, and experimental widescreen carry forward.

## Before playing

Supply your own legally obtained PlayStation SCPH1001 BIOS and Tomba! (USA,
SCUS-94236) disc image. Neither is included in this package. This remains an
alpha release; keep `overlay_captures.json` private because it contains code
captured from your own disc.
