"""Private, bounded Japan pad probe. Input cards are copied and hash-checked.

Only the guest's normal controller, screenshots and read-only diagnostics are
available. Commands are numbered JSON files in the private output directory.
No desktop automation, RAM writes, state loading or original-card writes.
"""
import argparse, hashlib, json, os, shutil, socket, struct, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'eu'))
from campaign_test import Probe, ALLOWED, step
ALLOWED.update(('quit', 'mod_counters', 'resident_status', 'video_info', 'spu_status'))

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cards', type=Path, required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--seconds', type=int, default=900)
    p.add_argument('--port', type=int, default=4521)
    p.add_argument('--load', action='store_true')
    a = p.parse_args()
    assert Path(a.name).name == a.name
    out = ROOT / 'build-jp' / a.name
    out.mkdir(exist_ok=False)
    cards = out / 'cards'; cards.mkdir()
    source = a.cards.resolve()
    originals = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in source.glob('*.mcd')}
    assert originals and all((source / n).stat().st_size == 131072 for n in originals)
    for name in originals: shutil.copy2(source / name, cards / name)
    (out / 'original-hashes.json').write_text(json.dumps(originals, indent=2))
    build = ROOT / 'build-jp/rc2/qa/native'
    state = build / 'mods/state.toml'
    previous = state.read_bytes() if state.exists() else None
    probe = Probe(out, a.port)
    try:
        with socket.create_connection(('127.0.0.1', a.port), timeout=.2):
            raise RuntimeError('Private test port occupied')
    except OSError: pass
    state.write_text('format_version = 2\n[[feature]]\npackage_id = "tomba.jp.enhancement.seamless"\nid = "resident-assets"\nenabled = true\n')
    env = dict(os.environ, PSX_OVERLAY_AUTOCOMPILE_OFF='1', PSX_INTERNAL_RESOLUTION='native',
               SDL_AUDIO_DRIVER='dummy', SDL_AUDIODRIVER='dummy', TOMBI_SEAMLESS_TRACE='1',
               PSX_RESIDENT_CACHE=str(ROOT / 'build-jp/rc2/resident-cache'))
    def sample(label):
        assert Path(label).name == label
        b = probe.ram(0x800A7B78, 48)
        data = dict(frame=probe.rpc('frame')['frame'], player_state=list(b[4:8]),
            position=[v/65536 for v in struct.unpack_from('<iii', b, 16)],
            selected=list(struct.unpack('<HH', probe.ram(0x8009E508,4))),
            current=list(struct.unpack('<HH', probe.ram(0x8009EE50,4))),
            task=list(struct.unpack('<4H', probe.ram(0x801FD848,8))),
            counters=probe.rpc('mod_counters'))
        probe.rpc('screenshot_file', path=str(out / (label+'.png')))
        (out / (label+'.json')).write_text(json.dumps(data, indent=2))
        return data
    child = None
    try:
        with (out/'runtime.log').open('w') as log:
            child = subprocess.Popen([str(build/'TombaRecompJP.exe'), '--headless-opengl', '--no-launcher',
                '--game', str(ROOT/'jp/pc.toml'), '--disc', str(ROOT/'disc/jp/disc.cue'),
                '--memcard-dir', str(cards), '--debug-port', str(a.port)], cwd=build, env=env,
                stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+120
            while True:
                assert child.poll() is None
                try:
                    if probe.rpc('frame')['frame'] >= 1500: break
                except (OSError, RuntimeError): pass
                if time.monotonic()>deadline: raise TimeoutError('Boot')
                time.sleep(.1)
            sample('boot'); print('READY '+str(out), flush=True)
            if a.load:
                title_deadline=time.monotonic()+100
                while struct.unpack('<4H', probe.ram(0x801FD848,8))[:2] != (4,3):
                    if time.monotonic()>title_deadline: raise TimeoutError('Original title')
                    probe.drive([step(['start'],4),step([],60)])
                probe.drive([step(['down'],16),step([],35),step(['start'],16),step([],180)])
                sample('load-menu')
            deadline = time.monotonic()+a.seconds
            number = 1
            while time.monotonic()<deadline and child.poll() is None:
                command = out / ('command-%03d.json' % number)
                if not command.exists(): time.sleep(.1); continue
                req = json.loads(command.read_text())
                if req.get('quit'): break
                if req.get('load_title'):
                    title_deadline = time.monotonic()+100
                    while struct.unpack('<4H', probe.ram(0x801FD848,8))[:2] != (4,3):
                        if time.monotonic()>title_deadline: raise TimeoutError('Original title')
                        time.sleep(.1)
                    probe.drive([step(['down'],16),step([],35),step(['start'],16),step([],180)])
                if 'drive' in req: probe.drive(req['drive'])
                result = sample(req.get('sample', 'step-%03d' % number))
                print(json.dumps(result), flush=True); number += 1
    finally:
        if child is not None and child.poll() is None:
            try: probe.rpc('quit'); child.wait(timeout=10)
            except Exception: child.terminate(); child.wait(timeout=10)
        if previous is None: state.unlink(missing_ok=True)
        else: state.write_bytes(previous)
        (out/'events.json').write_text(json.dumps(probe.events, indent=2))
        unchanged = all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in originals.items())
        (out/'originals-unchanged.json').write_text(json.dumps(dict(unchanged=unchanged)))
        assert unchanged, 'Original cards changed'

if __name__ == '__main__': main()
