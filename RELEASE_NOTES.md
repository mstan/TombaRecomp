# Tomba! Recompiled — v0.8.0-alpha

This release moves Tomba to the latest `psxrecomp` runtime and promotes the
overhauled OpenGL path as the default renderer.

## OpenGL and presentation

- OpenGL presentation no longer performs synchronous per-frame GPU readbacks.
- Painter-ordered primitive batching substantially reduces submission overhead
  while preserving PlayStation draw order and transparency behavior.
- The RmlUi launcher exposes the current renderer and high-refresh presentation
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
