#!/usr/bin/env python3
"""TombaRecomp phase-0 smoke preflight.

This verifies the local asset layout before the runtime milestone runner is
used. It deliberately does not mutate cards or launch the game.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    ROOT / "tomba" / "SCUS_942.36",
    ROOT / "tomba" / "tomba.cue",
    ROOT / "psxrecomp",
]


def main() -> int:
    missing = [p for p in EXPECTED if not p.exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}")
        return 1
    print("smoke prerequisites present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
