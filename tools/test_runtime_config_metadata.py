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


def main() -> int:
    errors = []
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
    if package["feature"][0]["default_enabled"]:
        errors.append("custom renderer must be default-off")
    aspect = next(o for o in package["option"] if o["id"] == "aspect")
    if aspect["default"] != "Fit":
        errors.append("custom renderer must default to Fit to Window")
    if [c["value"] for c in aspect["choice"]] != ["Fit", "16:9", "21:9", "32:9"]:
        errors.append("custom renderer dropdown choices changed")
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("runtime config metadata guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
