"""Build a local, disc-verified resident-asset pack for the Tomba spike.

The pack contains copyrighted game data and must stay in an ignored directory.
Raw records include the last sector's padding: CdRead writes whole sectors.
"""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import struct

from seamless_asset_probe import DISC_SHA1, decode_gam


def decoder_state(raw, output):
    declared = struct.unpack_from('<H', raw, 4)[0] | raw[7] << 8 | raw[6] << 16
    pos, produced, bit = 10, 0, 0
    flags = int.from_bytes(raw[8:10], 'little')
    while produced < declared:
        if flags & (1 << bit):
            produced += raw[pos + 1]
            pos += 2
        else:
            produced += 1
            pos += 1
        bit += 1
        if bit == 16:
            flags = int.from_bytes(raw[pos:pos + 2], 'little')
            pos += 2
            bit = 0
    assert produced == len(output)
    return declared, flags | (bit << 16)


def build(disc_path, framework_root, destination):
    with disc_path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha1').hexdigest() == DISC_SHA1, 'Unsupported disc'
    spec = importlib.util.spec_from_file_location('disc_reader', framework_root / 'tools/extract_overlays.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    disc = reader.DiscReader(str(disc_path), raw=True)
    payload, entries, blobs = bytearray(), [], {}

    def add(data):
        digest = hashlib.sha256(data).digest()
        if digest not in blobs:
            blobs[digest] = len(payload)
            payload.extend(data)
        return blobs[digest]

    try:
        for name, lba, size in reader.enumerate_files(disc):
            if name.endswith('.STR') or name == 'ZZZ/DUMMY.DAT':
                continue
            raw = disc.read_file_bytes(lba, (size + 2047) & ~2047)
            decoded = decode_gam(raw) if raw[:4] == b'GAM\0' else b''
            declared, state = decoder_state(raw, decoded) if decoded else (0, 0)
            entries.append(struct.pack('<8I', lba, size, add(raw), len(raw),
                                       add(decoded), len(decoded), declared, state))
    finally:
        disc.close()
    body = b''.join(entries) + payload
    # Integrity check, not an authentication mechanism. Disc identity is SHA-1.
    checksum = 2166136261
    for byte in body:
        checksum = ((checksum ^ byte) * 16777619) & 0xFFFFFFFF
    header = struct.pack('<8sII20sI8x', b'TMBPK001', len(entries), len(payload),
                         bytes.fromhex(DISC_SHA1), checksum)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(header + body)
    print(f'{len(entries)} entries; {len(payload):,} resident bytes; {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disc-bin', type=Path, required=True)
    parser.add_argument('--framework-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.disc_bin, args.framework_root, args.output)
