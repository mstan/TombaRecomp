#!/usr/bin/env python3
"""Guard Tomba runtime metadata that powers game-owned mods."""

from pathlib import Path
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FMV = {
    "auto_skip_fmv": False,
    "offer_skip_fmv": False,
    "fmv_skip_total_table": 0x80077728,
    "fmv_skip_movie_id": 0x1F8001CD,
    "fmv_skip_end_total": 3,
}


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def check_fmv_metadata(path: Path) -> list[str]:
    data = load_toml(path)
    video = data.get("video", {})
    errors = []
    for key, expected in EXPECTED_FMV.items():
        actual = video.get(key)
        if actual != expected:
            errors.append(
                f"{path.relative_to(ROOT)} [video].{key} = {actual!r}, "
                f"expected {expected!r}"
            )
    return errors


# Each shipped config must generate the same overlay code as the config its
# audited native cache was built from: tools/package_regions.py refuses a
# cache whose tag (psxrecomp overlay_codegen_config_hash) differs, and the
# runtime would otherwise run the release with different mod entry hooks.
CODEGEN_PAIRS = (
    ("game.toml", "packaging/release/game.toml"),
    ("eu/seamless/game.toml", "eu/release/game.toml"),
    ("eu2/pc.toml", "eu2/release/game.toml"),
    ("eu2/rev1/pc.toml", "eu2/rev1/release/game.toml"),
    ("jp/pc.toml", "jp/release/game.toml"),
)


def codegen_settings(data: dict) -> dict:
    """The TOML inputs of overlay_codegen_config_hash (config_loader.cpp)."""
    settings = {
        "mod_function_entry_funcs":
            data.get("recompiler", {}).get("mod_function_entry_funcs", []),
        "widescreen": data.get("widescreen", {}),
        "netplay_local_viewport":
            {k: v for k, v in data.get("netplay", {}).items() if "viewport" in k},
    }
    for key, value in data.items():
        if key.startswith(("mod_immediate", "mod_instruction")):
            settings[key] = value
    return settings


def check_codegen_parity() -> list[str]:
    errors = []
    for dev, release in CODEGEN_PAIRS:
        if not (ROOT / dev).exists() or not (ROOT / release).exists():
            errors.append(f"codegen pair missing: {dev} / {release}")
            continue
        a = codegen_settings(load_toml(ROOT / dev))
        b = codegen_settings(load_toml(ROOT / release))
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                errors.append(f"{release} differs from {dev} in codegen setting {key}")
    return errors


def main() -> int:
    errors = check_codegen_parity()
    for rel in ("game.toml", "packaging/release/game.toml"):
        errors.extend(check_fmv_metadata(ROOT / rel))
        data = load_toml(ROOT / rel)
        ws = data.get("widescreen", {})
        if data.get("video", {}).get("aspect_ratio") != "4:3":
            errors.append(f"{rel}: stock presentation must default to 4:3")
        if ws.get("offer") is not False or ws.get("native_wide") is not True:
            errors.append(f"{rel}: custom renderer must be mod-owned/native-wide")
        if ws.get("hud_sprt_squash") or ws.get("backdrop"):
            errors.append(f"{rel}: retired Tomba squash patches remain enabled")
    package = load_toml(ROOT / "mods/preloaded/packages/"
                        "tomba.enhancement.widescreen/1.0.0/manifest.toml")
    eu = load_toml(ROOT / "eu/mods/preloaded/packages/"
                   "tomba.enhancement.widescreen/1.0.0/manifest.toml")
    for regional in (package, eu):
        if regional['name'] != 'Widescreen' or regional['feature'][0]['name'] != 'Widescreen':
            errors.append('US and EU must display Widescreen')
        if regional['id'] != 'tomba.enhancement.widescreen' or regional['feature'][0]['id'] != 'widescreen':
            errors.append('renaming Widescreen must preserve existing package/feature identities')
        if regional['option'][0]['default'] != 'Fit':
            errors.append('regional Widescreen must default to Fit')
    if eu['target'][0]['game_id'] != 'SCES-01330':
        errors.append('EU Widescreen must target the verified EU release')
    for rel in ('eu/pc.toml','eu/seamless/game.toml','eu/release/game.toml'):
        cfg=load_toml(ROOT/rel)
        if not cfg['widescreen'].get('adaptive_view') or not cfg['widescreen'].get('native_wide'):
            errors.append(rel+': missing adaptive native-wide rendering')
        if cfg['widescreen']['sprite_tag_funcs'] != ['0x8005E634']:
            errors.append(rel+': incorrect EU sprite builder')
        if '0x100' not in cfg['widescreen']['cull'].get('screen_h_imms',[]):
            errors.append(rel+': PAL geometry requires its 256-line screen signature')
    if package["feature"][0]["default_enabled"] is not True:
        errors.append("USA Widescreen must default on for fresh profiles")
    aspect = next(o for o in package["option"] if o["id"] == "aspect")
    if aspect["default"] != "Fit":
        errors.append("custom renderer must default to Fit to Window")
    if [c["value"] for c in aspect["choice"]] != ["Fit", "16:9", "21:9", "32:9"]:
        errors.append("custom renderer dropdown choices changed")
    fmv = load_toml(ROOT / "mods/preloaded/packages/"
                    "tomba.enhancement.skip-fmv/1.0.0/manifest.toml")
    if fmv["feature"][0]["default_enabled"]:
        errors.append("FMV skipping must be default-off")
    preserve = next(o for o in fmv["option"] if o["id"] == "preserve-any-percent")
    if (preserve["feature"] != "skip-fmv" or preserve["type"] != "boolean"
            or preserve["default"] != "false"):
        errors.append("Any% exceptions must be an opt-in boolean on Skip FMVs")
    if fmv["plugin"] != [{"feature": "skip-fmv", "id": "tomba.skip-fmv"}]:
        errors.append("FMV skip plugin must retain its existing feature and id")
    blending = load_toml(ROOT / "mods/preloaded/packages/"
                         "tomba.enhancement.frame-interpolation/1.0.0/manifest.toml")
    feature = blending["feature"][0]
    if (blending.get("channel") != "developer" or
            feature.get("default_enabled") is not False or
            feature.get("hidden") is not True):
        errors.append("retired frame blending must remain developer-only, hidden and off")
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("runtime config metadata guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
