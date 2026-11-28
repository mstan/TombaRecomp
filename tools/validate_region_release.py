"""Tomba-specific regional guards after common release staging."""
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eu'))
from stage_release import privacy


def validate(region, build, stage):
    build, stage = Path(build), Path(stage)
    if (ROOT/'eu/VERSION').read_text().strip() != (ROOT/'VERSION').read_text().strip():
        raise ValueError('Regional product versions must match')
    forbidden = {'psx.enhancement.cd-speed', 'psx.enhancement.fast-loading',
                 'tomba.enhancement.fast-loading', 'tomba.enhancement.frame-interpolation'}
    required = {'psx.enhancement.crt-filter', 'psx.enhancement.image-filtering',
                'psx.enhancement.internal-resolution', 'psx.enhancement.enhanced-audio',
                'psx.feature.rewind'}
    found = set()
    for manifest in (stage/'mods/bundled').glob('*/*/manifest.toml'):
        data = tomllib.loads(manifest.read_text(encoding='utf-8'))
        found.add(data['id'])
        if data['id'] == 'tomba.enhancement.widescreen':
            if not any(f.get('id') == 'widescreen' and f.get('default_enabled') is True
                       for f in data.get('feature', [])):
                raise ValueError('Fresh regional players must enable widescreen')
            if not any(o.get('id') == 'aspect' and o.get('default') == 'Fit'
                       for o in data.get('option', [])):
                raise ValueError('Fresh regional players must use Fit to screen')
        for entry in [data, *data.get('feature', [])]:
            if re.match(r'^(EU |Tomba |Tombi )', entry['name']):
                raise ValueError('Regional prefix in mod name: '+entry['name'])
    if found & forbidden or required - found:
        raise ValueError('Regional mod catalog differs from its required product contract')
    if region.startswith('eu2'):
        sys.path.insert(0, str(ROOT/'eu2'))
        from revisions import write_standalone_catalog
        expected = 'rev1' if region == 'eu2-rev1' else 'original'
        if (build/'disc-revision.txt').read_text().strip() != expected:
            raise ValueError('The built EU2 revision differs from the selected product')
        write_standalone_catalog(stage, expected)
    elif region == 'eu':
        (stage/'regional-launch.toml').write_text(
            '[[profile]]\nid = "SCES-01330"\nsize = 492370032\n'
            'sha256 = "25aa80a9f7000fc68a4621e17c60fd1505df540dd6ed383baac305c37087bce2"\n'
            'backend = "TombiRecompEU.exe"\n', encoding='utf-8')
    privacy(stage)
    print(json.dumps({'region':region, 'regional_payload_guard':'passed'}))


if __name__ == '__main__':
    validate(*sys.argv[1:])
