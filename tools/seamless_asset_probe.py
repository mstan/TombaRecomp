#!/usr/bin/env python3
"""Offline Tomba SCUS-94236 asset feasibility probe; never mutates guest state.

Use --framework-root to reuse psxrecomp's ISO reader. Optional --oracle executes
the original disc's decoder in Unicorn (pip install unicorn==2.1.4) and compares
bytes under two destination fill patterns. Extracted assets belong in an ignored
build directory. This is NOT a runtime cache format or seamless-loading mod.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import time

DISC_SHA1 = "c259ec7ff6ef4163913991f4e4db2eff71702818"
CODEC = "tomba-gam-8003ef50-v1"
MAX_OUTPUT = 2 * 1024 * 1024


def decode_gam(data: bytes) -> bytes:
    """Decode a self-contained GAM stream, rejecting references to old RAM.

    8003EF50: flags are 16 bits, least significant bit first; 0 is a literal,
    1 is (distance:u8, length:u8). 8005B77C copies forward, allowing overlap.
    The peculiar output-size expression follows the original instructions.
    RAM/scratchpad side effects and elapsed guest time are deliberately absent.
    """
    if len(data) < 10 or data[:4] != b"GAM\0":
        raise ValueError("missing GAM header")
    size = struct.unpack_from("<H", data, 4)[0] | data[7] << 8 | data[6] << 16
    if not 0 < size <= MAX_OUTPUT:
        raise ValueError("output size outside supported bound")
    out = bytearray()
    pos = 8
    while len(out) < size:
        if pos + 2 > len(data):
            raise ValueError("truncated flag word")
        flags = int.from_bytes(data[pos:pos + 2], "little")
        pos += 2
        for bit in range(16):
            if len(out) >= size:
                break
            count = 2 if flags & (1 << bit) else 1
            if pos + count > len(data):
                raise ValueError("truncated token")
            if count == 1:
                out.append(data[pos])
            else:
                distance, length = data[pos:pos + 2]
                if not 0 < distance <= len(out) or not length:
                    raise ValueError("back-reference depends on prior RAM or is empty")
                # The game checks the size only after a whole token. Preserve
                # its final token's tail (up to 254 bytes past logical size).
                for _ in range(length):
                    out.append(out[-distance])
            pos += count
    return bytes(out)


class DecoderOracle:
    """Execute original MIPS bytes, not a second translation of the codec."""

    def __init__(self, exe: bytes):
        from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN
        from unicorn import mips_const
        self.reg = mips_const
        self.uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
        # Unicorn's MIPS CPU maps KSEG0 accesses to physical RAM.
        self.uc.mem_map(0, 16 * 1024 * 1024)
        self.uc.mem_map(0x1F800000, 4096)
        if exe[:8] != b"PS-X EXE":
            raise ValueError("invalid PS-X EXE")
        address, size = struct.unpack_from("<II", exe, 0x18)
        if address != 0x80010000 or len(exe) < 0x800 + size:
            raise ValueError("unexpected executable layout")
        self.uc.mem_write(address & 0x1FFFFFFF, exe[0x800:0x800 + size])

    def verify(self, encoded: bytes, decoded: bytes):
        reg = self.reg
        for fill in (0xA5, 0x5A):
            self.uc.mem_write(0x400000, encoded + bytes(16))
            self.uc.mem_write(0x7FFFF0, bytes([fill]) * (len(decoded) + 32))
            self.uc.reg_write(reg.UC_MIPS_REG_A0, 0x80400000)
            self.uc.reg_write(reg.UC_MIPS_REG_A1, 0x80800000)
            self.uc.reg_write(reg.UC_MIPS_REG_SP, 0x801FF000)
            self.uc.reg_write(reg.UC_MIPS_REG_RA, 0x80000000)
            self.uc.emu_start(0x8003EF50, 0x80000000,
                              timeout=5_000_000, count=50_000_000)
            if self.uc.reg_read(reg.UC_MIPS_REG_PC) != 0x80000000:
                raise ValueError("original decoder did not return within budget")
            actual = bytes(self.uc.mem_read(0x800000, len(decoded)))
            if actual != decoded:
                raise ValueError("original MIPS decoder output mismatch")
            if bytes(self.uc.mem_read(0x7FFFF0, 16)) != bytes([fill]) * 16 or \
               bytes(self.uc.mem_read(0x800000 + len(decoded), 16)) != bytes([fill]) * 16:
                raise ValueError("original decoder overwrote output canary")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def inspect(disc_path: Path, framework_root: Path, oracle_enabled=False,
            extract_dir: Path | None = None):
    started = time.perf_counter()
    with disc_path.open("rb") as stream:
        fingerprint = hashlib.file_digest(stream, "sha1").hexdigest()
    if fingerprint != DISC_SHA1:
        raise ValueError(f"unsupported disc SHA-1 {fingerprint}; expected {DISC_SHA1}")
    spec = importlib.util.spec_from_file_location(
        "psx_disc_reader", framework_root / "tools" / "extract_overlays.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    disc = reader.DiscReader(str(disc_path), raw=True)
    try:
        files = list(reader.enumerate_files(disc))
        exe_entry = next(entry for entry in files if entry[0] == "SCUS_942.36")
        exe = disc.read_file_bytes(*exe_entry[1:])
        oracle = DecoderOracle(exe) if oracle_enabled else None
        verified = set()
        unique_source = {}
        unique_prepared = {}
        unique_gam = {}
        groups = defaultdict(lambda: Counter())
        records = []
        errors = []
        if extract_dir:
            extract_dir.mkdir(parents=True, exist_ok=True)
        for name, lba, size in files:
            # STR video/audio streams need a separate streaming/music policy.
            if name.endswith(".STR"):
                records.append({"path": name, "lba": lba, "source_bytes": size,
                                "kind": "stream_excluded"})
                continue
            raw = disc.read_file_bytes(lba, size)
            source_hash = sha256(raw)
            unique_source[source_hash] = len(raw)
            # Whole sectors, exactly what a sector-granular read delivers.
            padded = disc.read_file_bytes(lba, (size + 2047) & ~2047)
            entry = {"path": name, "lba": lba, "source_bytes": size,
                     "source_sha256": source_hash,
                     "source_padded_sha256": sha256(padded), "kind": "raw"}
            prepared = raw
            if raw.startswith(b"GAM\0"):
                entry["kind"] = CODEC
                try:
                    prepared = decode_gam(raw)
                    declared = struct.unpack_from("<H", raw, 4)[0] | raw[7] << 8 | raw[6] << 16
                    entry.update(declared_bytes=declared,
                                 final_token_tail_bytes=len(prepared) - declared)
                    if oracle and source_hash not in verified:
                        oracle.verify(raw, prepared)
                        verified.add(source_hash)
                        if len(verified) % 50 == 0:
                            print(f"Verified {len(verified)} distinct GAM streams", flush=True)
                    unique_gam[source_hash] = len(prepared)
                except Exception as exc:
                    entry["error"] = str(exc)
                    errors.append({"path": name, "error": str(exc)})
                    records.append(entry)
                    continue
            prepared_hash = sha256(prepared)
            entry.update(prepared_bytes=len(prepared), prepared_sha256=prepared_hash)
            unique_prepared[prepared_hash] = len(prepared)
            group = groups[name.split("/")[0]]
            group["files"] += 1
            group["source_bytes"] += size
            group["prepared_bytes"] += len(prepared)
            if extract_dir:
                output = extract_dir / (prepared_hash + ".bin")
                if output.exists():
                    if sha256(output.read_bytes()) != prepared_hash:
                        raise ValueError(f"existing prepared blob has wrong hash: {output}")
                else:
                    output.write_bytes(prepared)
            records.append(entry)
        gam = [r for r in records if r["kind"] == CODEC]
        report = {
            "schema": "tomba-seamless-asset-probe-v1",
            "disc_sha1": fingerprint,
            "exe_sha256": sha256(exe),
            "scope": "Whole-file GAM decode and raw non-STR assets; no runtime installation",
            "summary": {
                "disc_files": len(files),
                "disc_file_bytes": sum(size for _, _, size in files),
                "excluded_str_files": sum(r["kind"] == "stream_excluded" for r in records),
                "gam_files": len(gam),
                "gam_unique_source_files": len(unique_gam),
                "gam_source_bytes": sum(r["source_bytes"] for r in gam),
                "gam_prepared_bytes": sum(r.get("prepared_bytes", 0) for r in gam),
                "gam_unique_source_prepared_bytes": sum(unique_gam.values()),
                "gam_files_with_final_token_tail": sum(bool(r.get("final_token_tail_bytes"))
                                                       for r in gam),
                "gam_max_final_token_tail_bytes": max(
                    (r.get("final_token_tail_bytes", 0) for r in gam), default=0),
                "non_str_source_bytes": sum(r["source_bytes"] for r in records
                                            if r["kind"] != "stream_excluded"),
                "non_str_prepared_bytes": sum(r.get("prepared_bytes", 0) for r in records),
                "non_str_unique_source_bytes": sum(unique_source.values()),
                "non_str_unique_prepared_bytes": sum(unique_prepared.values()),
                "original_mips_verified_unique_streams": len(verified),
                "oracle_destination_patterns": 2 if oracle else 0,
                "errors": len(errors),
            },
            "groups": dict(sorted(groups.items())),
            "files": records,
            "errors": errors,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        return report
    finally:
        disc.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disc-bin", type=Path, required=True)
    parser.add_argument("--framework-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--extract-dir", type=Path)
    parser.add_argument("--oracle", action="store_true")
    args = parser.parse_args()
    report = inspect(args.disc_bin, args.framework_root, args.oracle, args.extract_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {args.report}; elapsed {report['elapsed_seconds']} s")
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
