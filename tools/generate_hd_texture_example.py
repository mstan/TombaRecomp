#!/usr/bin/env python3
"""Generate, check, or archive Tomba's synthetic opt-in texture example.

Only literal dimensions, filenames, and two solid colors are inputs. No game
assets, texture dumps, image libraries, or running game are read.
"""

import argparse
from pathlib import Path
import struct
import zipfile
import zlib


EXAMPLE_ROOT = Path(__file__).resolve().parents[1] / "examples" / "hd-texture-pack"
PACK_PATH = Path("mods/texture-packs/SCUS-94236")
FIXTURES = (
    ("texupload-P8-F5F3557223CD3F4A-EAFB5B4F0E007E25-128x256-0-0-256x112-P0-255.png", 512, 224),
    ("texupload-P8-F5F3557223CD3F4A-EAFB5B4F0E007E25-128x256-8-112-72x88-P0-255.png", 144, 176),
    ("texpage-P4-A11813EA8B413CE2-E9C11EE79B72F5C0-64x256-128-32-64x64-P0-15.png", 128, 128),
    ("texpage-P4-853C062916E586A0-4F7160064933C5CC-64x256-192-0-64x64-P0-15.png", 128, 128),
    ("texupload-P4-203250107113A6E2-B66FDA9C474CA728-512x256-1792-72-72x64-P0-15.png", 144, 128),
)


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def checkerboard(width: int, height: int) -> bytes:
    colors = (b"\xff\x00\xff\xff", b"\x00\xff\xff\xff")
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # PNG filter: none.
        for x in range(width):
            rows.extend(colors[((x // 12) + (y // 12)) & 1])
    # Fixed uncompressed DEFLATE blocks keep bytes stable across zlib versions.
    blocks = bytearray(b"\x78\x01")
    for offset in range(0, len(rows), 65535):
        payload = rows[offset:offset + 65535]
        blocks.append(1 if offset + len(payload) == len(rows) else 0)
        blocks.extend(struct.pack("<HH", len(payload), len(payload) ^ 0xFFFF))
        blocks.extend(payload)
    blocks.extend(struct.pack(">I", zlib.adler32(rows)))
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", blocks)
        + png_chunk(b"IEND", b"")
    )


def create_archive(example_root: Path, destination: Path) -> None:
    files = [Path("README.md"), PACK_PATH / "README.md", PACK_PATH / "LICENSE"]
    files.extend(PACK_PATH / "replacements" / name for name, _, _ in FIXTURES)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w") as archive:
        for relative in sorted(files):
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (example_root / relative).read_bytes(), compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify checked-in PNGs without changing them")
    parser.add_argument("--archive", type=Path, help="Write a drop-in ZIP containing README files, the license, and five PNGs")
    args = parser.parse_args()
    replacements = EXAMPLE_ROOT / PACK_PATH / "replacements"
    if not args.check:
        replacements.mkdir(parents=True, exist_ok=True)
    for name, width, height in FIXTURES:
        expected = checkerboard(width, height)
        path = replacements / name
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                parser.exit(1, f"FAIL: synthetic example differs: {path}\n")
        else:
            path.write_bytes(expected)
    actual = {path.name for path in replacements.iterdir() if path.is_file()}
    expected_names = {name for name, _, _ in FIXTURES}
    if actual != expected_names:
        parser.exit(1, "FAIL: example replacements contain unexpected or missing files\n")
    if args.archive:
        create_archive(EXAMPLE_ROOT, args.archive)
        print(f"Wrote {args.archive}")
    print("PASS: five deterministic synthetic RGBA checkerboards; no source artwork read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
