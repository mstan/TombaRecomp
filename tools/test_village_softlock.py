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

    python tools/test_village_softlock.py --exe build-tcctest/psx-runtime.exe

Exit 0 = PASS. Exit 1 = FAIL (wedge, lag, or no boot). Don't run under heavy CPU
load (a concurrent shard compile starves the boot and can look like a wedge).
"""
import argparse, json, os, socket, subprocess, sys, time

PORT = 4470
WEDGE_ADDR = "0x00000CF0"


def call(cmd, **kw):
    obj = {"cmd": cmd, "id": 1}
    obj.update(kw)
    s = socket.socket()
    s.settimeout(6)
    s.connect(("127.0.0.1", PORT))
    s.sendall((json.dumps(obj) + "\n").encode())
    buf = b""
    while b"\n" not in buf:
        d = s.recv(65536)
        if not d:
            break
        buf += d
    s.close()
    return json.loads(buf.decode())


def wait_tcp(timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
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
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default="build-tcctest/psx-runtime.exe")
    ap.add_argument("--game", default="game.toml")
    ap.add_argument("--boot-wait", type=int, default=180,
                    help="max seconds to allow boot to reach a gameplay scene")
    args = ap.parse_args()

    env = dict(os.environ)
    env.setdefault("PSX_OVERLAY_BACKEND", "gcc")
    proc = subprocess.Popen([os.path.abspath(args.exe), "--game", args.game],
                            cwd=os.getcwd(), env=env)
    try:
        if not wait_tcp(40):
            print("FAIL: TCP debug server never came up "
                  "(build without PSX_DEBUG_TOOLS, or a boot crash).")
            return 1

        # Phase 1: reach a live gameplay scene. "Gameplay" = the overlay native ring
        # shows VARIETY (not just the 0xCF0 SIO stub) and plenty of dispatch. A
        # sustained 100% 0xCF0 with native still climbing AND interp flat = WEDGE.
        deadline = time.time() + args.boot_wait
        reached = False
        while time.time() < deadline:
            time.sleep(5)
            cf0, uniq, nat, interp, cg = snap()
            if uniq >= 4 and (nat > 200_000 or interp > 200_000):
                reached = True
                break
        if not reached:
            cf0a, _, na, ia, _ = snap(); time.sleep(3); cf0b, _, nb, ib, cg = snap()
            if cf0b > 0.9 and nb > na and (ib - ia) < 500:
                print(f"FAIL [WEDGE]: main loop spinning on {WEDGE_ADDR}, executing "
                      f"nothing else (cf0={cf0b:.2f}, native {na}->{nb}, interp flat "
                      f"{ia}->{ib}). The blue-screen wedge is back.")
            else:
                print(f"FAIL: never reached a gameplay scene within {args.boot_wait}s "
                      f"(cf0={cf0b:.2f}, native={nb}, interp={ib}).")
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
            return 1
        print(f"PASS: Village reached gameplay, no wedge, {native_frac*100:.0f}% native.")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
