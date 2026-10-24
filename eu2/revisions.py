"""Exact SCES-01331 inputs and revision-specific build contracts.

One build binds one original revision. The serial alone never selects code.
"""
from functools import lru_cache
import hashlib
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    'original': dict(size=492306528, sha1='684dbf0ad03f872511046d40d3cc85b17d839dbf',
        sha256='2eba3dfdd25f5d270d47f5fe408391971aa25ee09c6aac9874bba4e3bf6f32cc',
        md5='5cbbd8800409d992ce4b6d0df4bd7fab', directory='eu2', suffix=''),
    'rev1': dict(size=492370032, sha1='ec50074b6fd98f611bae11e3de68d6e76ffdd6d4',
        sha256='48a55fabd29e185dfc7d2afa94490d6092694cbed75ec8511f363b19076c5c2e',
        md5='2456298c5fc4c7686e739f02ee165363', directory='eu2/rev1', suffix=' (Rev 1)'),
}


def identify(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha1').hexdigest()
    for revision, profile in PROFILES.items():
        if path.stat().st_size == profile['size'] and digest == profile['sha1']:
            return revision
    raise ValueError(f'Unsupported SCES-01331 track: {digest} ({path.stat().st_size} bytes)')


@lru_cache(maxsize=1)
def active():
    return identify(ROOT / 'disc/eu2/disc.bin')


def source(relative, revision=None):
    return ROOT / PROFILES[revision or active()]['directory'] / relative


def write_standalone_catalog(destination, revision=None):
    """A standalone player must reject other revisions of the same serial."""
    profile = PROFILES[revision or active()]
    text = ('[[profile]]\nid = "SCES-01331"\n'
            f'size = {profile["size"]}\nsha256 = "{profile["sha256"]}"\n'
            'backend = "TombiRecompEU2.exe"\n')
    (Path(destination)/'regional-launch.toml').write_text(text,encoding='utf-8',newline='\n')


def stage_mods():
    """Bind declarations to the same checked revision as the compiled hooks."""
    target = ROOT / 'build-eu2-seamless/generated/mods'
    shutil.copytree(ROOT/'eu2/mods', target, dirs_exist_ok=True)
    for manifest in target.glob('packages/*/*/manifest.toml'):
        if 'tombi.enhancement.language-confirmation' in manifest.parts and active()!='original':
            manifest.unlink()
            continue # The original selector binding has not been verified for Rev 1.
        text = manifest.read_text(encoding='utf-8')
        text = text.replace(PROFILES['original']['sha256'], PROFILES[active()]['sha256'])
        manifest.write_text(text, encoding='utf-8', newline='\n')
    return target
