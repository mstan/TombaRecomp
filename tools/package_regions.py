"""Package the USA, EU1, EU2 (either revision) and Japanese regional players.

The engine owns staging, guarded cache publication, ZIPs, manifests and audits.
The title keeps its original-disc profiles and regional payload assertions.
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    'us': ('build-regions/us/native', 'build-regions/us/aot'),
    'eu': ('build-eu-release-final/native', 'build-eu-seamless/hook-aot'),
    'eu2': ('build-eu2-release/native', 'build-eu2-seamless/aot'),
    'jp': ('build-jp/rc2/player/native', 'build-jp/rc2/aot'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', nargs='+', choices=(*DEFAULTS, 'all'), default=['all'])
    for region, (build, aot) in DEFAULTS.items():
        parser.add_argument('--'+region+'-build', type=Path, default=ROOT/build)
        parser.add_argument('--'+region+'-aot', type=Path, default=ROOT/aot)
    parser.add_argument('--output', type=Path, default=ROOT/'build-release-dual/packages')
    parser.add_argument('--work-dir', type=Path, default=ROOT/'build-regional-package')
    parser.add_argument('--recompiler', type=Path, default=ROOT/'build-eu-tools/psxrecomp-game.exe')
    parser.add_argument('--toolchain-bin', help='native compiler bin directory (shared builder default otherwise)')
    parser.add_argument('--channel', required=True, choices=('public', 'playtest'))
    args = parser.parse_args()
    if not args.toolchain_bin:
        sys.path.insert(0, str(ROOT/'psxrecomp/tools'))
        from toolchain_pack import resolve_toolchain_bin
        native = resolve_toolchain_bin(ROOT)
        if native: args.toolchain_bin = str(native)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.drive.upper() == 'C:':
        parser.error('output must stay in the non-C: project workspace')
    for region in DEFAULTS:
        if 'all' not in args.region and region not in args.region:
            continue
        build = getattr(args, region+'_build').resolve()
        attempt = getattr(args, region+'_aot').resolve()
        if not (attempt/'audit.json').is_file():
            attempts = sorted(attempt.glob('disc-aot-*/audit.json'))
            if len(attempts) != 1:
                parser.error('Select the exact audited AOT attempt with --'+region+'-aot')
            attempt = attempts[0].parent
        selected = region
        if region == 'eu2':
            revision = (build/'disc-revision.txt').read_text().strip()
            if revision not in ('original', 'rev1'):
                parser.error('Unqualified EU2 build revision')
            if revision == 'rev1': selected = 'eu2-rev1'
        command = [sys.executable, str(ROOT/'psxrecomp/tools/package_title_release.py'),
            'package-existing', '--root', str(ROOT), '--config', 'packaging/regions/'+selected+'.toml',
            '--channel', args.channel, '--platform', 'windows', '--build-dir', str(build),
            '--aot-attempt', str(attempt), '--recompiler', str(args.recompiler.resolve()),
            '--out-dir', str(output), '--work-dir', str(args.work_dir/selected)]
        if not (attempt/'cache').is_dir():
            command += ['--aot-cache', str(build/'cache')]
        if args.toolchain_bin: command += ['--toolchain-bin', args.toolchain_bin]
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__': main()
