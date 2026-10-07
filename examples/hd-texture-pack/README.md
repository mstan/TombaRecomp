# Tomba texture example

This optional pack replaces a few textures in **Tomba! USA, SCUS-94236** with
obvious cyan/magenta checkerboards. The title logo is the easiest place to see
it; a few foliage/background textures can match during Village gameplay. It
is a demonstration and editing starting point, not a complete HD artwork pack.
All five PNGs contain only generated colors. No game artwork, dumps, saves, or
mod-selection settings are included. The example uses the repository's
[PolyForm Noncommercial license](mods/texture-packs/SCUS-94236/LICENSE),
included inside the pack so it travels with your copied files.

Copy this directory's **`mods`** folder into the directory containing
`TombaRecomp.exe` or `Tomba__Recompiled.exe`. Merge directories rather than
replacing your existing `mods` folder. If you already use a texture pack, keep
this example separate and choose its `mods/texture-packs/SCUS-94236` folder
with **Change folder** instead of overwriting your files.

For Linux AppImage, copy `mods` into the writable data directory:
`${XDG_DATA_HOME:-$HOME/.local/share}/TombaRecomp`, or the directory selected
by `TOMBA_RECOMP_DATA_DIR`.

Open **Mods**, enable **HD Texture Packs**, leave **Load replacements** on and
**Dump textures** off, select **OpenGL** in Settings, then click **Play**.
The mod remains disabled until you enable it yourself. Read
[the Tomba pack-directory README](mods/texture-packs/SCUS-94236/README.md) for
capture, editing, compatibility, and removal instructions.

Source-checkout users can verify or package this example with Python 3:

```sh
python tools/generate_hd_texture_example.py --check
python tools/generate_hd_texture_example.py --check --archive build/Tomba-HD-texture-example.zip
```

Run without `--check` to regenerate the five PNGs from literal dimensions and
two colors. The script reads no game files and the ZIP includes only this
README, the pack-directory README and license, and those five replacements.
