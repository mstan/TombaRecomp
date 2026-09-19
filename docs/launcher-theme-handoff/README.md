# Tomba recomp-ui Launcher Theme Handoff

Date: 2026-08-13

This packet is for a full custom theme for the Tomba recomp-ui launcher. The current raw assets have been copied into `current-assets/` so a design artist can inspect the actual source files and return a mockup that can be implemented.

## Current Asset Packet

Images copied to `current-assets/img/`:

| Asset | Current size | Current use |
| --- | ---: | --- |
| `boxart.tga` | 512x512, 24-bit | Tomba's only title-specific launcher asset today. |
| `brand_psx.tga` | 70x70, 32-bit | PSX header mark loaded by the current PSX profile. |
| `pad_analog.tga` | 344x200, 32-bit | Controller card art for the normal PSX analog pad view. |
| `pad_digital.tga` | 346x198, 32-bit | Controller card art when a game is locked to digital pad mode. |
| `memcard.tga` | 148x164, 32-bit | Memory-card panel icon. |
| `verdict_ok/warn/bad/none.tga` | 100x100, 32-bit | Disc verification status icons. |
| `brand_mark.tga`, `disc.tga`, `check_on/off.tga`, `caret.tga` | see CSV | Available raw assets, but not all are staged/loaded by Tomba today. |

Fonts copied to `current-assets/fonts/`:

| Asset | Current use |
| --- | --- |
| `LatoLatin-Regular.ttf` | Main ImGui launcher font at 18 px. |
| `LatoLatin-Bold.ttf` | Staged, but not currently selected by the ImGui launcher renderer. |
| `NotoSansSymbols2-Regular.ttf` | Symbol fallback. |
| `OpenMoji-black-glyf.ttf` | Emoji fallback when wide glyph support is enabled. |
| `NOTICE.md` | Font license notes. |

Use `asset-dimensions.csv` for the full machine-readable dimensions table.

## Screen Dimensions

Primary mockup size: `1100x880` logical pixels. This is the production initial launcher window opened by `recomp_launcher_run_window()`.

Also provide responsive checks at:

| Mockup | Purpose |
| --- | --- |
| `1100x880` | Required desktop/default implementation target. |
| `800x880` | Required narrow layout, because the dashboard collapses below 820 logical px wide. |
| `1280x720` | Optional live-resize widescreen sanity check. |
| `1600x900` | Optional large-window/background crop sanity check. |

Current logical layout tokens:

| Token | Value |
| --- | ---: |
| Outer window padding | 24 px |
| Primary gap | 16 px |
| Small gap | 8 px |
| Extra-large gap | 24 px |
| Body font | 18 px |
| Header title scale | 1.55x body, about 28 px rendered |
| Card radius | 14 px |
| Control radius | 6 px |
| Footer band | 92 px tall |
| Desktop dashboard breakpoint | 820 px wide |
| Desktop GAME column | 400 px wide |
| Memory-card/controller preferred card | 300 px wide |

At the default 1100x880 size, the outer safe content area is approximately `1052x832` after the 24 px padding on each side. The desktop dashboard uses a 400 px left GAME column, a 16 px gap, and the remaining width for controller/memory-card content.

## Visible States to Mock

Return at least these frames:

| Frame | Required content |
| --- | --- |
| Dashboard ready | `Tomba!`, PlayStation subtitle or custom subtitle treatment, box art, disc verified, controller assigned/unassigned, two memory card slots, PLAY CTA, skip-launcher checkbox. |
| Dashboard no disc | Same dashboard with no disc selected, disabled PLAY state, no-disc verdict. |
| Settings | Display, Audio, Input, System, and Hotkeys cards visible enough to prove the theme handles dense controls. |
| Controller config | Binding grid and capture state styling. |
| First-run setup modal | Modal over themed background, with BIOS/disc selection controls. |
| Confirmation modal | Skip launcher or restore defaults confirmation, including destructive/secondary action styling. |

If the redesign changes layout, the mockup should still include all of those functional surfaces. Do not remove controls in the art unless the implementation plan explicitly replaces the workflow.

## Replacement Asset Requests

Preferred deliverables from the artist:

| Asset | Requested source | Runtime target |
| --- | --- | --- |
| Full background | Layered source at least 2200x1760; keep critical detail inside the center 1100x880 safe area | Flattened PNG/TGA at 2200x1760, cover-cropped by the launcher |
| Tomba wordmark | Vector or layered source, transparent | PNG/TGA around 720x180; exact rendered size can be theme-driven |
| Header mark | Vector or layered source, transparent | 160x160 or 512x512 transparent; currently renders near 32 px high |
| Box art / hero art | Layered square source at least 1024x1024 | 1024x1024 PNG/TGA |
| Controller art | Transparent layered source | About 688x400 for analog and 692x396 for digital if keeping current slot |
| Memory card art | Transparent layered source | 512x568 preferred |
| Status icons | Vector or layered source | 200x200 transparent for ok/warn/bad/none |
| UI icons | Vector preferred | 64x64 or 128x128 transparent icons for Settings, Mods, Back, Play, Browse, New, Configure, Restore, etc. |
| App/window icon | Vector or 1024 source | `.ico` containing 16, 32, 48, 64, 128, and 256 px sizes, plus PNG source |
| Font files | TTF/OTF with license | Body, heading, and optional display/wordmark font files |

Flat runtime images can be PNG or TGA from a design standpoint. Today the repo ships TGA assets, but the loader already uses image decoding in the launcher backend; final format can be chosen during implementation.

## Current Theme Baseline

The current PSX theme is color-token based, not image based:

| Token | Current color |
| --- | --- |
| Background | `#0A0C14` |
| Background center | `#10141F` |
| Panel | `#121826` |
| Panel hovered | `#1C2740` |
| Control | `#161D2E` |
| Control hovered | `#212D45` |
| Border | `#283248` |
| Accent | `#2E7DFF` |
| Accent pressed | `#1A5AD6` |
| Text | `#E8ECF5` |
| Muted text | `#7E8AA3` |
| Good | `#46E39B` |
| Warn | `#F5B23C` |
| Focus ring | `#38E1E6` |

The current launcher draws a procedural background from colors only. It does not support a per-game bitmap background yet.

## Implementation Notes for recomp-ui

Expected recomp-ui changes:

1. Add per-game theme selection. `launcher_profile_apply("psx")` currently sets `gi.theme = "psx"`, and Tomba does not override it. Add a `tomba` theme path through game config, CMake, or a `RecompLauncherCGameInfo` field.
2. Add per-game asset staging beyond `BOXART`. Current `recomp_target_launcher_ui()` supports `BOXART`, `PAD`, and `BRAND`, but the `BRAND` override copies to `brand_mark.tga`; the PSX profile loads `brand_psx.tga`, so this does not actually override the PSX header mark today.
3. Add a theme asset manifest, for example `launcher_assets/theme/tomba/theme.toml`, so image names, font names, colors, and layout constants do not require hardcoded C changes.
4. Add bitmap background support with cover/contain modes, opacity, tint, and optional scrim so text remains readable.
5. Add font-family support. Today the ImGui backend loads `LatoLatin-Regular.ttf` as the body font; `font_title` and `font_small` are theme tokens, but the renderer mostly uses the body font and a header scale.
6. Add icon-capable controls for top navigation and frequent actions. Current navigation is text buttons (`Settings`, `Mods`, `Back`), while the requested redesign explicitly includes icons.
7. Add screenshot regression coverage for the Tomba theme at `1100x880` and `800x880`, because the dashboard has distinct wide/narrow layouts.

## Naming Cleanup

Release configs use `Tomba!`, but the development `game.toml` currently has `name = "TombaRecomp"` and `window_title = "TombaRecomp Recompiled"`. The theme mockup should target the release-facing name, `Tomba!` / `Tomba! Recompiled`.
