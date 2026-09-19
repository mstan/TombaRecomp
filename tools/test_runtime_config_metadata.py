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
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("runtime config metadata guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
