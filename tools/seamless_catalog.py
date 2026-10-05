"""Emit non-payload asset identities for the native first-run preparer."""
import argparse
import json
from pathlib import Path
from seamless_asset_probe import DISC_SHA1


def emit(report_path, output):
    report = json.loads(report_path.read_text())
    assert report['disc_sha1'] == DISC_SHA1 and not report['errors']
    lines = ['/* Generated asset names, sizes and hashes; no game data. Source hashes cover',
             ' * whole sectors (sector-padded file). */',
             'static const CatalogEntry catalog[] = {']
    for r in report['files']:
        if r['kind'] == 'stream_excluded' or r['path'] == 'ZZZ/DUMMY.DAT':
            continue
        decoded = r['kind'] != 'raw'
        lines.append('    {%s, %d, %d, %s, %d, %s},' % (
            json.dumps(r['path']), r['lba'], r['source_bytes'],
            json.dumps(r['source_padded_sha256']), r['prepared_bytes'] if decoded else 0,
            json.dumps(r['prepared_sha256'] if decoded else '')))
    lines.append('};\n')
    output.write_text('\n'.join(lines), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('report', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    emit(args.report, args.output)
