# Widescreen integration

The optional **Widescreen** mod uses the native wide renderer in both USA and
Europe builds. Fresh USA release profiles enable it with **Fit to Window**;
explicit saved mod and aspect choices are preserved. Other regional releases
retain their published settings.
Fit follows live window changes from 4:3 through 34:9; wider windows keep side
bars. Fixed 16:9, 21:9 and 32:9 use the same rendering path. Disabling the mod
restores the native 4:3 view. Movies and full-screen 2D scenes retain their
native presentation policy.

## World and camera

The game configuration identifies the geometry classifiers, render funnels
and backdrop producers that need wider bounds. Widening uses the current
view's margin and conservative guards. At 4:3 the expressions retain their
original instruction results.

The starting grassland anchors the expanded view to its native left boundary,
revealing more world to the right. A renderer origin shifts foreground and
parallax layers together. It does not move the guest camera, alter its velocity
or rewrite packet coordinates. Scene guards disable that origin elsewhere.

Visible width and residency guards are separate: allowing an object to draw
outside 4:3 does not prove that its allocation, spawning, scripts or retirement
are correct throughout the campaign. The village residency and script adapters
retain explicit scene/ownership guards. Story visibility queries preserve the
original predicate independently of wider draw admission.

## HUD and finite scenes

Producer roles distinguish world sprites from HUD. Life and AP stay at the
physical viewport edges, including when the starting-area origin shifts.
Generic packet position alone is not a reliable HUD classifier.

A finite full-screen backdrop may require native 4:3 presentation instead of
revealing space the original scene never contains. The overhead village uses
that policy; it is separate from widening ordinary world geometry.

## Regional bindings

USA hooks are maintained under `src/mods/`. Europe uses
`eu/widescreen_profile.py` and `eu/widescreen-contract.json` to check original
instruction windows and generate address adapters for the shared policies.
Language MAIN fingerprints gate guest callbacks; unknown images are rejected.
The SCES-01331 integration adds `eu2/widescreen_profile.py` and its reviewed
instruction/data contract. It normalizes verified HUD return sites and selects
camera, pool and area bindings from the live language identity, including the
distinct Spanish code layout. Original-MAIN fixtures pass for the original revision and Rev 1.
Rev 1 has separate checked contracts under `eu2/rev1/`; a fresh exact-disc
player/AOT rebuild, EN/ES Fit, English fixed/off, geometry/loading and
combined-launcher probes passed.
See the [EU2 status and QA guide](../eu2/README.md).

All selected EU native overlays must be rebuilt with the PAL screen signatures.
Original disc identity, native-byte guards and scene checks remain enforced.

Package, feature and plugin IDs remain stable when display labels change.
The setting is mod-owned: bundled configs keep `[widescreen].offer = false`
and `native_wide = true`, with stock 4:3 as the video default.

## Validation

Run `python -I -B tools/test_runtime_config_metadata.py` for both regional
config/manifest contracts. The native regression fixtures in `tests/` cover
adaptive policy, HUD roles, residency and scene exclusions. EU profile identity
checks live under `eu/tests/`.

The private runtime sampler is documented in [US/EU builds](EU_INTEGRATION.md).
It checks actual native dispatch, ordinary movement, window/aspect changes,
real margin content and rendered HUD tags. Keep captures and temporary cards
outside player installations, and mute automated game launches.

Scoped results are retained in `audit_notes/tombi-widescreen-20261021.json`.
English/German and US Fit samples, EU fixed 21:9 and disabled cases passed;
2,400 EU geometry batches matched the original routines. These checks do not
establish full campaign content, spawning, collision or exit coverage.
