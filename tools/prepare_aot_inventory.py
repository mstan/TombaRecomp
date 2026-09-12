"""Verify Tomba SCUS-94236 static overlay records against the original disc.

Run the framework's extract_generic.py first. This verifier accepts only the
25 known position-fixed overlay files, with exact original bytes and bounds.
The emitted recipes contain game data and must remain local.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--framework-root', type=Path, required=True)
    parser.add_argument('--disc', type=Path, required=True)
    parser.add_argument('--generic-records', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.framework_root / 'tools/aot_overlay_spike'))
    import extract_generic as extractor
    binary, raw = extractor.parse_cue_datatrack(str(args.disc))
    with open(binary, 'rb') as stream:
        disc_sha1 = hashlib.file_digest(stream, 'sha1').hexdigest()
    assert disc_sha1 == 'c259ec7ff6ef4163913991f4e4db2eff71702818', 'Unsupported disc revision'
    disc = extractor.eo.DiscReader(binary, raw=raw)
    files = list(extractor.eo.enumerate_files(disc))
    boot_entry = next((lba, size) for name, lba, size in files if name == 'SCUS_942.36')
    boot = disc.read_file_bytes(*boot_entry)
    assert boot[:8] == b'PS-X EXE'
    boot_base = struct.unpack_from('<I', boot, 0x18)[0]
    # Original loader: type 0xF0 selects the fixed overlay destination. Keep
    # this independent of the extractor's JAL/prologue address inference.
    def word(pc):
        return struct.unpack_from('<I', boot, 0x800 + pc - boot_base)[0]
    assert word(0x80021E4C) == 0x240200F0
    assert word(0x80021E5C) == 0x3C06800E
    assert word(0x80021E60) == 0x24C67388
    # Uncompressed read modes 1/2 use the queued destination directly.
    assert word(0x800102C8) == 0x8002155C
    assert word(0x800102CC) == 0x8002155C
    assert word(0x80021568) == 0x8C420004
    expected = {f'X{n:02}.BIN' for n in [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14, 16, 17, 18, 19]}
    expected.update(['DSPSUB.BIN', 'DSPSUB2.BIN', 'DSPSUB3.BIN',
                     'INFO.BIN', 'INFO2.BIN', 'INFO3.BIN', 'OPTSUB00.BIN', 'GOVER.BIN'])
    payloads = {}
    for name, lba, size in files:
        leaf = name.rsplit('/', 1)[-1].upper()
        if leaf not in expected:
            continue
        body = disc.read_file_bytes(lba, size)
        item = payloads.setdefault(leaf, dict(body=body, sources=[]))
        assert item['body'] == body, f'Conflicting duplicate: {name}'
        item['sources'].append(dict(path=name, lba=lba, size=size))
    assert set(payloads) == expected
    base, page = 0x800E7388, 0x800E7000
    records = json.loads(args.generic_records.read_text(encoding='utf-8-sig'))
    assert len(records) == len(expected) - 1
    # GOVER is too small for the generic raw-code confidence gate. The title's
    # loader descriptor supplies stronger evidence: LDSYS file ID 215, type F0,
    # uncompressed read mode 2, and the exact ISO file extent.
    file_map = {name: (lba, size) for name, lba, size in files}
    ldsys = disc.read_file_bytes(*file_map['SYS/LDSYS.BIN'])
    gover = payloads['GOVER.BIN']['body']
    descriptor = struct.unpack_from('<5I', ldsys, 0x1C24)
    assert descriptor == (0xF0FF00D7, 0x80000000, len(gover), 0, 2)
    location = boot[0x800 + 0x800791A0 - boot_base + 215 * 8:][:8]
    bcd = lambda value: (value >> 4) * 10 + (value & 15)
    lba = (bcd(location[0]) * 60 + bcd(location[1])) * 75 + bcd(location[2]) - 150
    assert (lba, struct.unpack_from('<I', location, 4)[0]) == file_map['SYSTEM/GOVER.BIN']
    assert extractor.raw_base_votes(gover, 0x80098000).most_common(1)[0] == (base, 4)
    direct = extractor.direct_jal_roots(gover, base)
    seeds = sorted(set(direct) | set(extractor.prologues(gover, base)) |
                   extractor.frameless_leaf_entries(gover, base))
    records.append(extractor.rec(page, bytes(base - page) + gover, seeds,
                                 static_discovery=direct))
    output = args.out_dir.resolve()
    inputs = output / 'runtime-inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    jobs, seen = [], set()
    for record in records:
        assert not record.get('executed_pcs'), 'Runtime captures are not static inputs'
        assert int(record['load_addr'], 0) == page
        data = base64.b64decode(record['bytes_b64'], validate=True)
        matches = [name for name, item in payloads.items()
                   if data == bytes(base - page) + item['body']]
        assert len(matches) == 1, 'Record is not an exact original overlay image'
        name = matches[0]
        assert name not in seen
        seen.add(name)
        item = payloads[name]
        known = [(base, base + len(item['body']))]
        record['guard_bytes'] = 0
        record['producer_name'] = name
        record['producer_ranges'] = [dict(start=hex(lo), end=hex(hi)) for lo, hi in known]
        record['strict_producer_ranges'] = True
        path = inputs / (name + '.json')
        path.write_text(json.dumps([record], indent=2), encoding='utf-8')
        jobs.append(dict(name=name, sources=item['sources'], input=str(path),
                         known_ranges=known, load_addr=hex(page), file_load_addr=hex(base),
                         size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                         source_sha256=hashlib.sha256(item['body']).hexdigest(),
                         pair_stem=f'{page & 0x1fffffff:08X}_{zlib.crc32(data):08X}'))
    assert seen == expected
    inventory = dict(game_id='SCUS-94236', original_disc_sha1=disc_sha1,
                     boot_sha256=hashlib.sha256(boot).hexdigest(),
                     loader_destination_instructions=['0x80021E5C', '0x80021E60'],
                     overlay_images=len(jobs), area_images=17, support_images=8,
                     gover_loader_descriptor=dict(file='SYS/LDSYS.BIN', offset='0x1C24',
                                                  file_id=215, read_mode=2),
                     full_static_coverage_proven=False, jobs=jobs)
    (output / 'runtime-input-inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
    # Metadata-only copy is safe to retain with source; no embedded game bytes.
    print(json.dumps(dict(images=len(jobs), output=str(output))))


if __name__ == '__main__':
    main()
