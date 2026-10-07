# Tomba! USA texture pack directory

This folder is the default texture-pack root for **Tomba! USA, SCUS-94236**.
The five included PNGs are synthetic cyan/magenta checkerboards enlarged to
2x their native texture dimensions. They contain no original Tomba artwork.
The filenames identify textures previously encountered on the USA disc; the
pixels are generated entirely from two solid colors. The example uses the
included [PolyForm Noncommercial license](LICENSE).

## Enable the example

1. Place this folder at `mods/texture-packs/SCUS-94236` beside the game
   executable. Merge folders and preserve any other packs or captures you use.
2. In the launcher, open **Mods** and enable **HD Texture Packs**.
3. Use **Open folder** to confirm the selected root is this folder. If you
   previously selected a different pack, use **Change folder** to select this
   `SCUS-94236` directory.
4. Enable **Load replacements** and disable **Dump textures**.
5. Select **OpenGL** in Settings, then click **Play**. The title logo should
   show large checkerboards; only a few gameplay textures have examples.

Linux AppImage uses the writable TombaRecomp data directory rather than the
read-only executable payload. Put `mods` under
`${XDG_DATA_HOME:-$HOME/.local/share}/TombaRecomp`, or your
`TOMBA_RECOMP_DATA_DIR` override. **Open folder** shows the actual selected path.

## Capture and edit your own replacements

`replacements/` holds edited PNG/JPEG/static WebP images. The runtime creates `dumps/` beside it when
the pack is configured. No dumps are distributed with this example.

To capture originals, turn **Load replacements** off and **Dump textures** on,
then click **Play** and visit the scenes you want. The runtime combines used
rectangles per source and palette across the source's lifetime. PNGs can appear
in `dumps/` when that source is overwritten or retired. **Exit the game to
finish pending captures**, wait for writing, then copy chosen PNGs into
`replacements/`, and edit them. Keep every filename unchanged: its hashes,
dimensions, offsets, and palette range tell the runtime which texture to
replace. Keep the aspect ratio and use an integer enlargement such as 2x or
4x. You can also edit the example checkerboards directly.

Turn **Load replacements** on and **Dump textures** off, then start again to
check your work. Options apply on **Play** and pack changes are scanned at
session start. The mod keeps native game textures and saves intact. Keep your
packs outside `mods/bundled`, which builds and updates regenerate. Do not
redistribute captured game artwork without permission from its rights holder.

## Capture settings and friendly filenames

`config.yaml.example` is inactive. Copy it to `config.yaml` at this folder's
root only when you want authoring settings; it does not alter the five examples.
The keys belong directly at the YAML root, without an `Options:` section.
Default capture follows uploads, skips C16 textures, requires at least 16x16
texels, and reduces palette ranges to the indices actually used. Lower the
texture thresholds for small parts or enable C16 explicitly when needed.
Optional page capture can produce more duplicate-looking images.

Tomba's characters use separate texture parts and palettes. Captures are source
textures rather than reconstructed characters, so heads and bodies can remain
separate. Palette animation, upload history, and used rectangles can give
related-looking images different identities. These bounds do not promise every
filename will be identical to DuckStation's for an entire game session.

The commented `Aliases:` example maps one canonical identity to a friendly
filename under `replacements/`. Rename that corresponding example file before
enabling its alias. Keep the hash/dimension identity text intact; an existing
canonical file takes precedence. The five full-range example names remain
valid even when new captures use reduced palette ranges.

## Compatibility and removal

The example targets the USA disc. Other regions or revisions may not match;
unmatched textures retain their originals. PNG, JPEG, and static WebP are supported,
with at most 8192 pixels per side, 64 MiB encoded, and 64 MiB decoded RGBA.
Wrapped texture footprints, `vram-write-` XXH3-128 images, legacy unnamed layouts,
animated WebP, and general YAML features remain unsupported. Copy/split,
coalescing, and composition support are bounded; see the format notes below.
OpenGL displays replacements; software
and Vulkan can dump textures but retain the original display artwork. After
loading a savestate, upload-based replacements need fresh game texture uploads
before matching again; page-based matching remains available.

Disable **HD Texture Packs** to restore all original artwork on the next
launch. To keep your mod configuration but remove this demonstration, remove
only these five example files from `replacements/`; keep your own edits and
`dumps/`. Replacing the checkerboard pixels with your own artwork while
retaining their filenames also works.

Full usage: [Tomba HD texture guide](https://github.com/mstan/TombaRecomp/blob/master/docs/HD_TEXTURE_PACKS.md).
Exact supported format: [framework format notes](https://github.com/mstan/psxrecomp/blob/master/docs/DUCKSTATION_TEXTURE_FORMAT.md).
