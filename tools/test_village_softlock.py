#!/usr/bin/env python3
"""Regression test for the two native-overlay failure classes that have bitten
Tomba's Village of All Beginnings (New Game / load-Village-save):

  1. BLUE-SCREEN WEDGE — a native overlay function entered at a foreign interior
     PC ran from its top, corrupting shared state; the main loop then spun forever
     on the 0x00000CF0 SIO stub and never rendered the area. Fixed by the fail-
     closed native entry guard + the jal-target alias discovery (the swallowed
     function becomes its own routable native entry).

  2. READ!=WRITE LAG — the loader read overlay shards from cg<hashA> while
     autocompile wrote them to cg<hashB> (a stale baked-in codegen hash drifting
     from the headers), so the freshly compiled Village shards were never loaded
     and the area ran ~97% interpreted. Fixed by hardcoding the cache to
     <exe>/cache + an OBJECT_DEPENDS so the runtime's cg tag can't drift.

The test boots Tomba, waits until it reaches a live gameplay scene, then asserts:
  - it REACHED gameplay (not the 0xCF0 wedge), and
  - that scene runs NATIVE-DOMINANT (native dispatch >> interp), i.e. the loader is
    reading the same cg dir autocompile writes.

Requires a dev build with the TCP debug server (-DPSX_DEBUG_TOOLS=ON), the BIOS
(baked), and the Tomba disc resolvable from game.toml. Run from the project root:

    python tools/test_village_softlock.py --exe build-tcctest/psx-runtime.exe \
        --profile <test-output> --disc <original-disc.cue>

Exit 0 = PASS. Exit 1 = FAIL (wedge, lag, or no boot). The finite guest workload
advances independently of wall time; transport errors preserve the owned process.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'psxrecomp/tools'))
from debug_client import query
from debug_transport import isolated_environment, available_local_port

PORT = 4470
WEDGE_ADDR = "0x00000CF0"


def call(cmd, **kw):
    obj = {"cmd": cmd, "id": 1}
    obj.update(kw)
    return query('127.0.0.1', PORT, obj, timeout=6)


def wait_tcp(proc):
    while proc.poll() is None:
        try:
            if call("ping").get("pong"):
                return True
        except OSError:
            time.sleep(1)
    return False


def snap():
    """(cf0_frac, uniq_native_addrs, native_total, interp_total, read_cg_dir)."""
    ring = call("overlay_native_ring").get("ring", {})
    rec = ring.get("recent", [])
    native_total = ring.get("calls_total", 0)
    st = call("overlay_loader_status")
    interp = st.get("dispatch_interp_fallback", 0)
    msg = st.get("last_msg", "")
    read_cg = msg.split("/gcc/")[-1].split("/")[1] if "/gcc/" in msg else "?"
    if not rec:
        return 0.0, 0, native_total, interp, read_cg
    a = [x["addr"] for x in rec]
    return a.count(WEDGE_ADDR) / len(a), len(set(a)), native_total, interp, read_cg


def main():
    global PORT
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default="build-tcctest/psx-runtime.exe")
    ap.add_argument("--game", default="game.toml")
    ap.add_argument('--profile', type=Path, required=True, help='isolated non-C: test profile')
    ap.add_argument('--disc', type=Path, required=True, help='original disc image or CUE')
    ap.add_argument('--boot-frames', type=int, default=10800, help='finite guest-frame workload')
    ap.add_argument('--boot-calls', type=int, default=20000000, help='finite native/interpreter dispatch workload')
    args = ap.parse_args()

    execution = Path(args.exe).resolve().with_suffix('.execution.json')
    if not execution.is_file() or json.loads(execution.read_text())['profile'] != 'ENHANCED':
        ap.error('Use a current host-native ENHANCED build with its execution contract')
    if not args.disc.is_file():
        ap.error('The original disc path must exist')
    PORT = available_local_port()

    env = dict(os.environ)
    profile = args.profile.resolve()
    if profile.drive.upper() == 'C:' or args.boot_frames < 1 or args.boot_calls < 1:
        ap.error('Use a non-C: profile and positive finite guest-work budgets')
    env.update(isolated_environment(profile))
    env.update(SDL_AUDIODRIVER='dummy', SDL_AUDIO_DRIVER='dummy')
    env.setdefault("PSX_OVERLAY_BACKEND", "gcc")
    proc = subprocess.Popen([os.path.abspath(args.exe), '--hidden-window', '--no-launcher',
                            '--game', str(Path(args.game).resolve()), '--disc', str(args.disc.resolve()),
                            '--memcard-dir', str(profile/'saves'), '--debug-port', str(PORT)],
                            cwd=profile, env=env, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (profile/'owned-process.json').write_text(json.dumps({'pid':proc.pid,'port':PORT,'exe':os.path.abspath(args.exe)}))
    completed = False
    try:
        if not wait_tcp(proc):
            print("FAIL: TCP debug server never came up "
                  "(build without PSX_DEBUG_TOOLS, or a boot crash).")
            return 1

        # Phase 1: reach a live gameplay scene. "Gameplay" = the overlay native ring
        # shows VARIETY (not just the 0xCF0 SIO stub) and plenty of dispatch. A
        # sustained 100% 0xCF0 with native still climbing AND interp flat = WEDGE.
        start_frame = call('frame')['frame']
        _, _, start_native, start_interp, _ = snap()
        reached = False
        while proc.poll() is None:
            time.sleep(5)
            cf0, uniq, nat, interp, cg = snap()
            if uniq >= 4 and (nat > 200_000 or interp > 200_000):
                reached = True
                break
            if (call('frame')['frame'] - start_frame >= args.boot_frames or
                    nat + interp - start_native - start_interp >= args.boot_calls):
                break
        if not reached:
            cf0a, _, na, ia, _ = snap(); time.sleep(3); cf0b, _, nb, ib, cg = snap()
            if cf0b > 0.9 and nb > na and (ib - ia) < 500:
                print(f"FAIL [WEDGE]: main loop spinning on {WEDGE_ADDR}, executing "
                      f"nothing else (cf0={cf0b:.2f}, native {na}->{nb}, interp flat "
                      f"{ia}->{ib}). The blue-screen wedge is back.")
            else:
                print(f"FAIL: finite guest workload did not reach the gameplay predicate "
                      f"(cf0={cf0b:.2f}, native={nb}, interp={ib}).")
            completed = True
            return 1

        # Phase 2: in a gameplay scene — measure the native:interp RATE. Native must
        # dominate. Interp-dominant here = the read!=write lag (shards written to a
        # cg dir the loader doesn't read) or the boundary-bounce-to-interp lag.
        _, _, n0, i0, cg = snap()
        time.sleep(5.0)
        _, _, n1, i1, _ = snap()
        nrate, irate = (n1 - n0) / 5.0, (i1 - i0) / 5.0
        total = nrate + irate
        native_frac = nrate / total if total else 0.0
        print(f"reached gameplay: loader reads cg {cg}; "
              f"native {nrate:.0f}/s, interp {irate:.0f}/s ({native_frac*100:.0f}% native)")
        if native_frac < 0.6:
            print(f"FAIL [LAG]: gameplay is {(1-native_frac)*100:.0f}% INTERPRETED "
                  f"(native {nrate:.0f}/s vs interp {irate:.0f}/s). The Village is not "
                  f"running native — read!=write cg-dir drift, or boundary bounce.")
            completed = True
            return 1
        print(f"PASS: Village reached gameplay, no wedge, {native_frac*100:.0f}% native.")
        completed = True
        return 0
    finally:
        if completed and proc.poll() is None:
            result = call('quit')
            if result.get('ok'):
                proc.wait()
        elif proc.poll() is None:
            print(f'Transport/setup needs attention; preserving owned PID {proc.pid} and {profile}', file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
