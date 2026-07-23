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
