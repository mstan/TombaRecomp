"""Audit original EU resident assets; emit only local catalog metadata, no patch.

The original BIN/CUE, existing builds and Memory Cards are read-only inputs.
STR streams stay on the original streaming path. Generated catalog is local.
"""
import hashlib
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'psxrecomp/tools'), str(ROOT/'tools')]
from aot_overlay_pipeline import Disc, check_disc
from seamless_asset_probe import decode_gam, DecoderOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--oracle', action='store_true',
                        help='Compare unique streams with the original EU MIPS decoder, two fills')
    parser.add_argument('--variant',choices=['eu1','eu2','jp'],default='eu1')
    parser.add_argument('--output',type=Path,help='Private generated catalog directory')
    parser.add_argument('--oracle-limit',type=int,help='Explicit bounded original-MIPS sample; never claims full corpus')
    args = parser.parse_args()
    started = time.monotonic()
    cue = ROOT/('disc/jp/disc.cue' if args.variant=='jp' else 'disc/eu2/disc.cue' if args.variant=='eu2' else 'disc/Tombi! (Europe) (En,Fr,De,It,Nl) (Rev 1).cue')
    disc = Disc(cue)
    eu2_profile = None
    if args.variant=='eu2':
        sys.path.insert(0,str(ROOT/'eu2'))
        from revisions import PROFILES, active, source
        eu2_profile=PROFILES[active()]
    check_disc(dict(disc_hashes={'sha1': 'c86baf702303e7e0963b99aff307b1c40e40478a' if args.variant=='jp' else eu2_profile['sha1'] if eu2_profile else
                               '2505d958b4439d04844cadd3f968fc7432a48e00'}), disc, cue)
    oracle = None
    if args.oracle:
        sys.path.insert(0, str(ROOT/('build-jp/full/test-deps' if args.variant=='jp' else 'build-eu2-seamless/python-deps' if args.variant=='eu2' else 'build-eu-seamless/python-deps')))
        oracle = DecoderOracle(disc.read('SLPS_011.44' if args.variant=='jp' else 'EXE/MAIN0.EXE' if args.variant=='eu2' else 'EXE/MAIN2.EXE'),
                               entry=0x8003C8C4 if args.variant=='jp' else int(json.loads(source('seamless-contract.json').read_text())['languages'][0]['code']['0x8003bafc']['address'],16) if eu2_profile else 0x8003BAFC)
    out = (args.output or ROOT/('build-jp/final/generated' if args.variant=='jp' else 'build-eu2-seamless/generated' if args.variant=='eu2' else 'build-eu-seamless/generated')).resolve()
    assert out.is_relative_to(ROOT)
    out.mkdir(parents=True, exist_ok=True)
    rows, streams, decoded = [], [], {}
    source_bytes = decoded_bytes = gam_count = oracle_count = 0
    for name, (lba, size) in sorted(disc.files.items()):
        if name.endswith('.STR'):
            streams.append(name)
            continue
        raw = disc.reader.read_file_bytes(lba, (size+2047) & ~2047)
        original = raw[:size]
        digest = hashlib.sha256(raw).hexdigest()
        n, result_hash = 0, ''
        if original.startswith(b'GAM\0'):
            key = hashlib.sha256(original).hexdigest()
            if key not in decoded:
                result = decode_gam(original)
                decoded[key] = (len(result), hashlib.sha256(result).hexdigest())
                if oracle and (args.oracle_limit is None or oracle_count<args.oracle_limit):
                    oracle.verify(original, result)
                    oracle_count+=1
                    if len(decoded) % 50 == 0:
                        print(f'Original EU MIPS verified: {len(decoded)} unique streams', flush=True)
            n, result_hash = decoded[key]
            decoded_bytes += n
            gam_count += 1
        rows.append((name, lba, size, digest, n, result_hash))
        source_bytes += len(raw)
    lines = ['/* Local original EU extent/hash metadata; no embedded game data. */',
             'static const CatalogEntry catalog[] = {']
    for name, lba, size, digest, n, result_hash in rows:
        lines.append(f'    {{"{name}", {lba}, {size}, "{digest}", {n}, "{result_hash}"}},')
    lines.append('};\n')
    (out/'eu_catalog.inc').write_text('\n'.join(lines))
    report = dict(files=len(rows), gam_files=gam_count, unique_gam=len(decoded),
        source_sector_bytes=source_bytes, decoded_bytes=decoded_bytes,
        streams_excluded=streams, elapsed_seconds=time.monotonic()-started,
        scope='Offline sector/decode audit only; no live loader or card changes',
        original_mips_oracle=args.oracle,
        original_mips_verified_streams=oracle_count,variant=args.variant,
        original_mips_full_corpus=bool(args.oracle and oracle_count==len(decoded)))
    (out/'catalog-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
