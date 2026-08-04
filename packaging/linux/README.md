# Experimental Linux AppImage

The AppImage keeps its squashfs payload read-only and places all writable state
under `${XDG_DATA_HOME:-$HOME/.local/share}/TombaRecomp`:

- `settings.toml`, `input.ini`, and `keybinds.ini`
- `saves/` and game-option persistence
- `mods/`, including user-installed packages
- `cache/` and overlay captures

Bundled assets, OpenBIOS, release documentation, and the preloaded mod catalog
are refreshed into that directory on launch. User-owned files are not replaced.
Set `TOMBA_RECOMP_DATA_DIR=/some/path` to select a different writable root.

The AppImage is an experimental x86-64 Linux build. It does not contain a game
disc or Sony BIOS. OpenBIOS is included. OpenGL is the supported renderer for
this build; Vulkan falls back when the build host does not have the Vulkan SDK.
