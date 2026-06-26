#!/usr/bin/env python3
"""Regression test: Tomba must NOT softlock entering Village of All Beginnings.

History (this blue-screen class has recurred): the Ape-Escape forward-port added
"pre-prologue" function-start discovery to the recompiler's function_analysis,
which over-extended a function boundary in Tomba's Village-of-All-Beginnings init
path. The result was a main-loop softlock — New Game (and loading the Village
save) wedged with the dirty-RAM dispatcher spinning on the 0x00000CF0 SIO-poll
stub forever, never rendering the area (a solid "blue screen"). It was backend-
independent (gcc + tcc) and NOT overlay-interp related, so only an end-to-end boot
catches it. psxrecomp b9e3841 rolled the AE discovery back; this guards it.

How it works: on boot Tomba auto-progresses into the Village opening scene (no
input needed). The WEDGE signature is the native overlay ring being ~100%
0x00000CF0 while dispatch_native keeps climbing (alive but stuck). Healthy
gameplay shows a VARIETY of overlay addresses. We boot, wait for gameplay, and
discriminate.

Requirements: a dev build with the TCP debug server (configure with
-DPSX_DEBUG_TOOLS=ON), plus the BIOS (baked via DEFAULT_BIOS_PATH) and the Tomba
disc resolvable from game.toml. Run from the TombaRecomp project root:

    python tools/test_village_softlock.py --exe build-tcctest/psx-runtime.exe

Exit 0 = PASS (reached gameplay, no softlock). Exit 1 = FAIL (wedged / no boot).
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


def sample():
    """Return (cf0_fraction, unique_addr_count, native_calls, interp_fallback).

    Two independent progress signals so the verdict is robust to cache state:
      - native overlay variety (cf0_frac / uniq): valid when overlays run NATIVE
        (cache matches the build). Healthy gameplay = many addrs, cf0_frac low.
      - interp-fallback count: valid when overlays run INTERPRETED (stale/empty
        cache -> the native ring shows ONLY the 0xCF0 kernel stub, so cf0_frac=1.00
        even during healthy but slow gameplay). Healthy = interp climbing briskly.
    The WEDGE is the one state with NEITHER: native ring pinned to 0xCF0 AND the
    interp count flat (the main loop spins on the SIO stub, executing nothing else).
    """
    ring = call("overlay_native_ring").get("ring", {})
    rec = ring.get("recent", [])
    native_total = ring.get("calls_total", 0)
    interp = call("overlay_loader_status").get("dispatch_interp_fallback", 0)
    if not rec:
        return 0.0, 0, native_total, interp
    addrs = [x["addr"] for x in rec]
    return addrs.count(WEDGE_ADDR) / len(addrs), len(set(addrs)), native_total, interp


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default="build-tcctest/psx-runtime.exe",
                    help="path to a PSX_DEBUG_TOOLS=ON psx-runtime.exe")
    ap.add_argument("--game", default="game.toml")
    ap.add_argument("--boot-wait", type=int, default=120,
                    help="seconds to allow boot to reach gameplay. NOTE: during "
                         "normal BIOS boot the SIO stub 0xCF0 is the only overlay "
                         "running, so cf0_frac=1.00 early on is NOT yet a wedge — "
                         "the test waits for varied gameplay. Don't run this under "
                         "heavy CPU load (e.g. a concurrent shard compile), which "
                         "starves the boot and can look like a wedge.")
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

        deadline = time.time() + args.boot_wait
        prev_interp, prev_t, last = None, None, None
        while time.time() < deadline:
            time.sleep(5)
            frac, uniq, native_total, interp = sample()
            now = time.time()
            irate = ((interp - prev_interp) / (now - prev_t)) if prev_interp is not None else 0.0
            prev_interp, prev_t = interp, now
            last = (frac, uniq, native_total, interp, round(irate))
            native_ok = frac < 0.5 and uniq >= 3 and native_total > 50000
            interp_ok = irate > 1500 and interp > 50000
            if native_ok or interp_ok:
                why = "native overlays varied" if native_ok else f"interp overlays brisk ({round(irate)}/s)"
                print(f"PASS: reached live gameplay ({why}; cf0_frac={frac:.2f}, "
                      f"uniq={uniq}, native={native_total}, interp={interp}).")
                return 0

        # Timed out — distinguish the WEDGE (native ring pinned to 0xCF0 AND interp
        # flat: the loop spins on the SIO stub executing nothing else) from a merely
        # slow/failed boot.
        f0, _, n0, i0 = sample()
        time.sleep(3)
        f1, _, n1, i1 = sample()
        if f1 > 0.9 and n1 > n0 and (i1 - i0) < 300:
            print(f"FAIL: SOFTLOCK — main loop spinning on {WEDGE_ADDR}, executing "
                  f"nothing else (cf0_frac={f1:.2f}, native climbing {n0}->{n1}, "
                  f"interp flat {i0}->{i1}). The Village-init function-boundary "
                  f"regression is back.")
            return 1
        print(f"FAIL: did not reach gameplay within {args.boot_wait}s "
              f"(last sample cf0_frac/uniq/native/interp/irate={last}).")
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
