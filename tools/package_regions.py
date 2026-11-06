"""Package clean Windows USA/Europe/Japan players from audited release builds.

One separate download per region, all from this entry point.

Uses the framework's catalog, toolchain, cache and ZIP staging implementations.
Never copies a used player folder, original disc, resident cache or player state.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'psxrecomp/tools'), str(ROOT / 'eu')]
import aot_overlay_pipeline as pipeline
import release_stage
from create_release_zip import create_release_zip
from mod_channel_filter import filter_catalog
from stage_release import copy, privacy
from toolchain import executable


def package(region, build, aot, out, version):
    build, aot = build.resolve(), aot.resolve()
    if not (aot / 'audit.json').is_file():
        attempts = sorted(aot.glob('disc-aot-*/audit.json'))
        if len(attempts) != 1:
            raise ValueError('Select the exact audited AOT attempt directory with --us-aot/--eu-aot')
        aot = attempts[0].parent
    cache = (build / 'CMakeCache.txt').read_text()
    for flag in ('PSX_DEBUG_TOOLS:BOOL=ON', 'TOMBA_GEOMETRY_VALIDATE:BOOL=ON',
                 'TOMBI_GEOMETRY_VALIDATE:BOOL=ON', 'TOMBI_EU2_GEOMETRY_VALIDATE:BOOL=ON'):
        if flag in cache:
            raise ValueError(f'Cannot publish private validation build: {flag}')
    jp = region == 'jp'
    eu = region in ('eu', 'eu2')
    eu2 = region == 'eu2'
    title, serial = (('Tombi! (Europe, En/Es/Pt/Sv/Da)', 'SCES-01331') if eu2 else
                     ('Tombi! (Europe, En/Fr/De/It/Nl)', 'SCES-01330') if eu else
                     ('Ore! Tomba (Japan)', 'SLPS-01144') if jp else
                     ('Tomba! (USA)', 'SCUS-94236'))
    if eu2:
        sys.path.insert(0,str(ROOT/'eu2'))
        from revisions import source, PROFILES, write_standalone_catalog
        revision=(build/'disc-revision.txt').read_text().strip()
        if revision not in PROFILES:raise ValueError('Unqualified EU2 build revision')
    if eu2 and revision=='rev1':title+=' (Rev 1)'
    folder = ('TombiRecomp-Europe-SCES01331-windows-x64' if eu2 else
              'TombiRecomp-Europe-SCES01330-Rev1-windows-x64' if eu else
              'TombaRecomp-Japan-SLPS01144-windows-x64' if jp else 'TombaRecomp-USA-windows-x64')
    if eu2 and revision=='rev1':folder=folder.replace('SCES01331-','SCES01331-Rev1-')
    player = out / folder
    player.mkdir(parents=True, exist_ok=False)
    exe = ('TombiRecompEU2.exe' if eu2 else 'TombiRecompEU.exe' if eu else
           'TombaRecompJP.exe' if jp else 'TombaRecomp.exe')
    copy(build / (exe if eu or jp else 'Tomba__Recompiled.exe'), player / exe)
    config = source('release/game.toml',revision) if eu2 else ROOT / (
                     'eu/release/game.toml' if eu else 'jp/release/game.toml' if jp else
                     'packaging/release/game.toml')
    copy(config, player / 'game.toml')
    if eu2:write_standalone_catalog(player,revision)
    elif eu:
        # The serial also exists on older gameplay-code revisions. Keep the
        # standalone EU1 package on the same full-disc gate as the common UI.
        (player/'regional-launch.toml').write_text(
            '[[profile]]\nid = "SCES-01330"\nsize = 492370032\n'
            'sha256 = "25aa80a9f7000fc68a4621e17c60fd1505df540dd6ed383baac305c37087bce2"\n'
            'backend = "TombiRecompEU.exe"\n',encoding='utf-8',newline='\n')
    if eu or jp:
        copy(ROOT / ('eu2/seeds/boot.txt' if eu2 else 'jp/seeds/boot.txt' if jp else 'eu/seeds/boot.txt'),
             player / 'seeds/boot.txt')
    else:
        copy(ROOT / 'game_options.toml', player / 'game_options.toml')
    for folder_name in ('assets', 'bios'):
        shutil.copytree(build / folder_name, player / folder_name)
    release_stage.stage_mods(str(build), str(player),
                            runtime_target='tombi-eu2' if eu2 else 'tombi-eu-seamless' if eu else
                            'tomba-jp' if jp else 'psx-runtime')
    filter_catalog(player / 'mods/bundled')
    forbidden = {'psx.enhancement.cd-speed', 'psx.enhancement.fast-loading',
                 'tomba.enhancement.fast-loading', 'tomba.enhancement.frame-interpolation'}
    # Picture, sound and rewind controls exist only as these framework mods
    # (recomp-ui docs/SETTINGS_STANDARD.md); a package without them loses them.
    required = {'psx.enhancement.crt-filter', 'psx.enhancement.image-filtering',
                'psx.enhancement.internal-resolution', 'psx.enhancement.enhanced-audio',
                'psx.feature.rewind'}
    missing = sorted(i for i in required if not (player / 'mods/bundled' / i).is_dir())
    if missing:
        raise ValueError(f'Package lacks framework mods: {", ".join(missing)}')
    manifests = sorted((player / 'mods/bundled').glob('*/*/manifest.toml'))
    names = {}
    for manifest in manifests:
        package_data = tomllib.loads(manifest.read_text())
        if package_data['id'] in forbidden:
            raise ValueError(f'Excluded release package: {manifest}')
        features = package_data.get('feature', [])
        names[package_data['id']] = [f['name'] for f in features]
        for entry in [package_data, *features]:
            if re.match(r'^(EU |Tomba |Tombi )', entry['name']):
                raise ValueError(f'Regional prefix in mod name: {entry["name"]}')
    receipt = json.loads((aot / 'audit.json').read_text())
    if receipt['game_id'] != serial or not receipt['all_pairs_valid'] or not receipt['all_guards_match_known_input_bytes']:
        raise ValueError('Native cache audit failed or belongs to another region')
    tag = pipeline.compiler.cache_tag(str(ROOT / 'psxrecomp/runtime/include'),
        str(ROOT / 'build-eu-tools/psxrecomp-game.exe'), str(config), receipt.get('flavor', 0))
    if receipt['cache_tag'] != tag:
        raise ValueError('Native cache configuration differs from the packaged config')
    native_cache = aot / 'cache'
    if not native_cache.is_dir():
        # EU2/JP attempts have separate source workspaces; the runtime destination
        # holds the staged, audited modules. Recheck bytes before redistribution.
        native_cache = build / 'cache'
        namespace = native_cache/serial/'gcc'/pipeline.compiler.cache_arch_abi()/tag
        for pair in receipt['pairs']:
            for name,digest in ((pair['dll'],pair['dll_sha256']),
                               (pair['dll'].removesuffix('.dll')+'.ranges',pair['manifest_sha256'])):
                if hashlib.sha256((namespace/name).read_bytes()).hexdigest()!=digest:
                    raise ValueError('Staged native module differs from its audit: '+name)
    pipeline.stage(native_cache, player, receipt)
    strip = executable('llvm-strip.exe')
    staged_hashes = {}
    for dll in sorted((player / 'cache').rglob('*.dll')):
        subprocess.run([strip, '--strip-debug', str(dll)], check=True)
        staged_hashes[dll.name] = hashlib.sha256(dll.read_bytes()).hexdigest()
    receipt['staged_dll_sha256_after_debug_strip'] = staged_hashes
    (player / 'AOT_CACHE_AUDIT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    release_stage.stage_toolchain(str(player), str(ROOT / 'build-eu-tools'),
        str(ROOT / 'psxrecomp/tools'), str(ROOT / 'psxrecomp/runtime/include'),
        str(ROOT / 'build-release-dual/downloads'), platform_tag='win',
        mingw_bin=str(Path(executable('clang.exe')).parent))
    tk = player / 'overlay_toolchain'
    # LLVM-MinGW emitters use libc++ rather than GCC's C++ runtime.
    for dependency in ('libc++.dll', 'libunwind.dll'):
        copy(Path(executable('clang.exe')).parent / dependency, tk / dependency)
    copy(ROOT / 'build-eu-tools/psxrecomp-bios.exe', tk / 'psxrecomp-bios.exe')
    for name in ('psxrecomp-game.exe', 'psxrecomp-bios.exe'):
        subprocess.run([strip, '--strip-debug', str(tk / name)], check=True)
    # Remove example-only local paths from distributed helper comments.
    helper = tk / 'compile_overlays.py'
    helper.write_text(helper.read_text().replace('C:/Users/...', '<Windows user path>'))
    header = tk / 'include/audio_trace.h'
    header.write_text(header.read_text().replace('F:/Projects/_audio_round2/ROUND2_PLAN.md',
                                                'the shared audio measurement design'))
    shutil.copytree(ROOT / 'psxrecomp/runtime/licenses', player / 'licenses')
    for source, target in ((ROOT / 'LICENSE', player / 'LICENSE'),
                           (ROOT / 'PERMISSIONS.md', player / 'PERMISSIONS.md'),
                           (ROOT / 'psxrecomp/LICENSE', player / 'licenses/PSXRecomp-LICENSE'),
                           (ROOT / 'recomp-ui/LICENSE', player / 'licenses/recomp-ui-LICENSE'),
                           (ROOT / 'recomp-ui/src/third_party/imgui/LICENSE.txt', player / 'licenses/ImGui-LICENSE.txt'),
                           (ROOT / 'recomp-ui/assets/common/fonts/NOTICE.md', player / 'licenses/Fonts-NOTICE.md'),
                           (ROOT / 'recomp-ui/assets/common/img/NOTICE.md', player / 'licenses/Images-NOTICE.md')):
        copy(source, target)
    for source in (ROOT / 'eu/release/licenses').glob('*'):
        copy(source, player / 'licenses' / source.name)
    tools_root = Path(executable('clang.exe')).parent.parent
    copy(tools_root / 'LICENSE.TXT', player / 'licenses/LLVM-LICENSE.txt')
    copy(tools_root / 'deps/share/licenses/SDL3/LICENSE.txt', player / 'licenses/SDL3-LICENSE.txt')
    for source in (tools_root / 'x86_64-w64-mingw32/share/mingw32').glob('COPYING*'):
        copy(source, player / 'licenses' / source.name)
    zlib = (tools_root / 'deps/include/zlib.h').read_text()
    (player / 'licenses/zlib-NOTICE.txt').write_text(zlib[:zlib.index('*/') + 2] + '\n')
    guide = ROOT / ('eu/release/docs/HD_TEXTURE_PACKS.md' if eu else 'docs/HD_TEXTURE_PACKS.md')
    copy(guide, player / 'docs/HD_TEXTURE_PACKS.md')
    copy(ROOT / 'psxrecomp/docs/DUCKSTATION_TEXTURE_FORMAT.md', player / 'docs/DUCKSTATION_TEXTURE_FORMAT.md')
    readme = 'README.txt' if eu2 else 'README.md'
    copy(ROOT / ('eu2/release/README_EN.txt' if eu2 else 'eu/release/docs/README.md' if eu else
                 'jp/release/README.md' if jp else 'README.md'),
         player / readme)
    disc = (f'Tombi! (Europe) (En,Es,Pt,Sv,Da){PROFILES[revision]["suffix"]}, SCES-01331.\n'
            f'BIN SHA-1: {PROFILES[revision]["sha1"]}.\n'
            'SCES-01330 uses the separate Europe SCES-01330 build.' if eu2 else
            'Tombi! (Europe) (En,Fr,De,It,Nl) (Rev 1), SCES-01330.\n'
            'BIN SHA-1: 2505d958b4439d04844cadd3f968fc7432a48e00.\n'
            'SCES-01331 and other SCES-01330 revisions are unsupported.' if eu else
            'Ore! Tomba (Japan), SLPS-01144.\n'
            'BIN SHA-1: c86baf702303e7e0963b99aff307b1c40e40478a.\n'
            'Other regions use their own builds.' if jp else
            'Tomba! (USA), SCUS-94236. European and Japanese discs use their own builds.')
    (player / 'START_HERE.txt').write_text(
        f'{title} - v{version} - Windows x64\n\n'
        f'Run {exe}, select your own disc, then press Launch.\n'
        'OpenBIOS is bundled; no system Python/compiler or retail BIOS is required.\n\n'
        f'Supported disc: {disc}\n\n'
        'Seamless Loading is enabled by default. Widescreen is optional: enable it\n'
        'in Mods and choose Fit to Window or a fixed ratio. Keep the entire folder.\n'
        'Memory Cards are in saves/. Each region build keeps its own saves.\n'
        'No disc, extracted game assets, personal settings or saves are included.\n'
        f'Read {readme} for setup and features. Version changes and validation limits:\n'
        'https://github.com/mstan/TombaRecomp/releases\n')
    report = privacy(player)
    for file in player.rglob('*'):
        if file.is_file():
            data = file.read_bytes()
            for private in (str(ROOT), str(build), 'G:/Temp/Codex', 'G:\\Temp\\Codex',
                            'F:/Temp/Codex', 'F:\\Temp\\Codex'):
                if private.encode().lower() in data.lower() or private.encode('utf-16le').lower() in data.lower():
                    raise ValueError(f'Private path in {file.relative_to(player)}')
    if eu2:report['disc_revision']=revision
    report.update(region=region, game_id=serial, version=version, mod_names=names,
                  native_pairs=receipt['published_pairs'], cache_tag=tag, debug_tools=False)
    (out / f'{region}-package-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    release_region = ('Europe-SCES01331' if eu2 else 'Europe-SCES01330-Rev1' if eu else
                      'Japan-SLPS01144' if jp else 'USA')
    if eu2 and revision=='rev1':release_region+='-Rev1'
    archive = out / f'{"TombiRecomp" if eu else "TombaRecomp"}-v{version}-{release_region}-windows-x64.zip'
    create_release_zip(player, archive)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip():
            raise ValueError('ZIP integrity check failed')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n')
    print(json.dumps(dict(report, archive=str(archive), sha256=digest)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', nargs='+', choices=('us', 'eu', 'eu2', 'jp', 'all'), default=['all'],
                        help='one or more of us/eu/eu2/jp; all (default) packages every region')
    parser.add_argument('--us-build', type=Path, default=ROOT / 'build-regions/us/native')
    parser.add_argument('--us-aot', type=Path, default=ROOT / 'build-regions/us/aot')
    parser.add_argument('--eu-build', type=Path, default=ROOT / 'build-eu-release-final/native')
    parser.add_argument('--eu-aot', type=Path, default=ROOT / 'build-eu-seamless/hook-aot')
    parser.add_argument('--eu2-build', type=Path, default=ROOT / 'build-eu2-release/native')
    parser.add_argument('--eu2-aot', type=Path, default=ROOT / 'build-eu2-seamless/aot')
    parser.add_argument('--jp-build', type=Path, default=ROOT / 'build-jp/rc2/player/native')
    parser.add_argument('--jp-aot', type=Path, default=ROOT / 'build-jp/rc2/aot')
    parser.add_argument('--output', type=Path, default=ROOT / 'build-release-dual/packages')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT) or out.drive.upper() == 'C:':
        parser.error('output must stay in the non-C: project workspace')
    out.mkdir(parents=True, exist_ok=True)
    version = (ROOT / 'VERSION').read_text().strip()
    if (ROOT / 'eu/VERSION').read_text().strip() != version:
        parser.error('both regional versions must match')
    regions = tuple(r for r in ('us', 'eu', 'eu2', 'jp') if 'all' in args.region or r in args.region)
    for region in regions:
        package(region, getattr(args, region + '_build'), getattr(args, region + '_aot'), out, version)


if __name__ == '__main__':
    main()
