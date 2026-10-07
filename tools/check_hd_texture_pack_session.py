#!/usr/bin/env python3
"""Verify a running development build's HD pack capture or replacement session.

Build with PSX_DEBUG_TOOLS=ON, launch with --debug-port 4478, and visit the
scene under test. This probe only reads status and existing capture files.
Use --expect-dumps after source retirement has written captures,
--expect-replacements after installing a
fixture, or --expect-inactive after disabling the mod.
"""

import argparse
import json
from pathlib import Path
import socket
import struct
import sys


def request(port: int) -> dict:
    with socket.create_connection(("127.0.0.1", port), timeout=20) as sock:
        sock.sendall(b'{"cmd":"hd_textures","id":1}\n')
        with sock.makefile("rb") as stream:
            line = stream.readline(1024 * 1024)
    status = json.loads(line)
    if not status.get("ok"):
        raise ValueError(f"HD texture status failed: {status}")
    return status


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Incomplete or invalid PNG: {path}")
    width, height = struct.unpack(">II", header[16:24])
    if not (0 < width <= 8192 and 0 < height <= 8192):
        raise ValueError(f"Unsupported PNG dimensions {width}x{height}: {path}")
    return width, height


def inspect(status: dict, expect: str) -> dict:
    if expect == "inactive":
        if status.get("active"):
            raise ValueError("HD pack is still active after the mod was disabled")
        return status
    if not status.get("active"):
        raise ValueError("Enable the HD Texture Packs mod and click Play first")
    root = Path(status["root"])
    pack_root = root.parent if root.name.lower() == "replacements" else root
    if expect == "dumps":
        if not status.get("dump"):
            raise ValueError("Enable Dump textures and click Play before checking capture")
        if status.get("dumped_textures", 0) < 1:
            raise ValueError(
                "No capture PNGs queued yet; source usage can remain pending until "
                "overwrite or retirement. Exit the game to finish capture, then inspect "
                "dumps on disk (pending_dump_sources reports live pending usage)."
            )
        captures = sorted((pack_root / "dumps").rglob("*.png"))
        if not captures:
            raise ValueError("Runtime reports queued captures but no PNGs exist yet; wait for writing or exit the game to finish capture")
        samples = [(path.name, *png_dimensions(path)) for path in captures[:16]]
        status["verified_dump_files"] = len(captures)
        status["dump_samples"] = samples
    elif expect == "replacements":
        if not status.get("replacement_backend_supported"):
            raise ValueError("Select OpenGL to display replacements")
        for counter in ("replacement_count", "matched_draws", "ready_draws", "applied_draws"):
            if status.get(counter, 0) < 1:
                raise ValueError(f"No {counter}; visit the source scene with Load replacements enabled")
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4478)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--expect-dumps", action="store_true")
    mode.add_argument("--expect-replacements", action="store_true")
    mode.add_argument("--expect-inactive", action="store_true")
    parser.add_argument("--report", type=Path, help="Write the status evidence as JSON")
    args = parser.parse_args()
    expect = "dumps" if args.expect_dumps else "replacements" if args.expect_replacements else "inactive"
    try:
        status = inspect(request(args.port), expect)
        result = json.dumps(status, indent=2)
        if args.report:
            args.report.write_text(result + "\n", encoding="utf-8")
        print(result)
        print(f"PASS: HD texture {expect} session")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
