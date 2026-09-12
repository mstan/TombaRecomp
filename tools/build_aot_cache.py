"""Compile and audit a verified Tomba inventory without importing a live cache."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--framework-root', type=Path, required=True)
    parser.add_argument('--recompiler', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--gcc', default='gcc')
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    framework = args.framework_root.resolve()
    output = args.out_dir.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error('--out-dir must be empty; historical caches are not inputs')
    output.mkdir(parents=True, exist_ok=True)
    inventory = json.loads(args.inventory.read_text(encoding='utf-8-sig'))
    assert inventory['game_id'] == 'SCUS-94236'
    assert len(inventory['jobs']) == 25
    for index, job in enumerate(inventory['jobs'], 1):
        print(f"[{index}/25] {job['name']}", flush=True)
        # One recipe per invocation avoids nominating unrelated area entries
        # across incompatible byte variants during initial discovery.
        with (output / (job['name'] + '.log')).open('w') as log:
            subprocess.run([
                sys.executable, str(framework / 'tools/compile_overlays.py'),
                '--captures', job['input'], '--game-toml', str(root / 'game.toml'),
                '--project-root', str(root), '--recompiler', str(args.recompiler),
                '--runtime-include', str(framework / 'runtime/include'),
                '--out-dir', str(output), '--compiler', 'gcc', '--gcc', args.gcc,
                '--flavor', '0', '--jobs', str(args.jobs),
            ], stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run([
        sys.executable, str(root / 'tools/audit_aot_cache.py'),
        '--framework-root', str(framework), '--recompiler', str(args.recompiler),
        '--game-toml', str(root / 'game.toml'), '--inventory', str(args.inventory),
        '--cache-root', str(output), '--output', str(output / 'aot-audit.json'),
    ], check=True)


if __name__ == '__main__':
    main()
