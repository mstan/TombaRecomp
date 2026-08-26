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
