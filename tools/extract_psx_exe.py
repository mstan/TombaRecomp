#!/usr/bin/env python3
"""extract_psx_exe.py — pull a PS-X EXE out of a PlayStation disc image.

The recompiler ingests the game's main executable (e.g. SCUS_942.36) as a
file on disk; it is a regular file in the disc's ISO9660 filesystem. This
walks the root directory and extracts it, handling raw MODE2/2352 images
(2352-byte sectors, 2048-byte Form-1 payload at offset 24) as well as plain
MODE1/2048 images.

Usage:
    python3 tools/extract_psx_exe.py tomba/tomba.bin SCUS_942.36 tomba/SCUS_942.36

Cross-platform (pure stdlib) — works the same on macOS, Linux, and Windows.
"""
import struct
import sys

DATA = 2048  # ISO9660 logical sector size


def detect_layout(f):
    """Return (raw_sector_size, payload_offset) for MODE2/2352 or MODE1/2048."""
    f.seek(0)
    head = f.read(2352 * 17)
    # PVD lives at logical sector 16; its first bytes are 0x01 "CD001".
    if head[16 * 2048: 16 * 2048 + 6] == b"\x01CD001":
        return 2048, 0
    if head[16 * 2352 + 24: 16 * 2352 + 24 + 6] == b"\x01CD001":
        return 2352, 24
    raise SystemExit("no ISO9660 PVD found (not a recognized PS1 disc image)")


def read_sector(f, raw, off, lba):
    f.seek(lba * raw + off)
    return f.read(DATA)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    bin_path, want, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    want_u = want.upper().encode()

    with open(bin_path, "rb") as f:
        raw, off = detect_layout(f)
        pvd = read_sector(f, raw, off, 16)
        root = pvd[156:156 + 34]
        root_lba = struct.unpack("<I", root[2:6])[0]
        root_size = struct.unpack("<I", root[10:14])[0]

        data = b"".join(
            read_sector(f, raw, off, root_lba + i)
            for i in range((root_size + DATA - 1) // DATA)
        )

        found = None
        i = 0
        while i < len(data):
            rlen = data[i]
            if rlen == 0:                       # padding to next sector
                i = ((i // DATA) + 1) * DATA
                continue
            name_len = data[i + 32]
            name = data[i + 33:i + 33 + name_len]
            if name.split(b";")[0] == want_u:   # ignore ";1" version suffix
                lba = struct.unpack("<I", data[i + 2:i + 6])[0]
                size = struct.unpack("<I", data[i + 10:i + 14])[0]
                found = (lba, size)
                break
            i += rlen

        if not found:
            sys.exit(f"{want} not found in disc root directory")

        lba, size = found
        out = b"".join(
            read_sector(f, raw, off, lba + k)
            for k in range((size + DATA - 1) // DATA)
        )[:size]

    with open(out_path, "wb") as g:
        g.write(out)
    magic = out[:8]
    print(f"extracted {want} -> {out_path} ({size} bytes, magic={magic!r})")
    if magic != b"PS-X EXE":
        print("WARNING: extracted file is not a PS-X EXE (unexpected magic)")


if __name__ == "__main__":
    main()
