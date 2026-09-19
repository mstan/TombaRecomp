"""Same-save Windows viewport A/B: host CPU, guest vblanks and display flips.

Requires an idle debug build. Never saves; restores the diagnostic slot before
each sample. Optional mirror ablation is temporary and always cleared. Frame
perf's emu_cpu_ms is wall time (includes pacing), NOT process CPU time; GPU
queries span command-submission gaps, so are not GPU utilization percentages.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

from probe_adaptive_widescreen import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--port", type=int, default=4499)
    parser.add_argument("--load-slot", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--sizes", nargs="+", default=["800x600", "1280x720",
                        "1680x720", "1920x540", "2048x510"])
    parser.add_argument("--ablate", action="store_true")
    args = parser.parse_args()
    if args.seconds < 5 or args.seconds > 25:
        parser.error("Use 5-25 seconds (bounded by presentation ring capacity)")
    args.output.mkdir(parents=True, exist_ok=True)
    kernel = C.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.GetProcessTimes.argtypes = [W.HANDLE] + [C.POINTER(W.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [W.HANDLE]
    proc = kernel.OpenProcess(0x1000, False, args.pid)
    if not proc:
        raise C.WinError(C.get_last_error())

    def cpu_seconds():
        stamps = [W.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(proc, *(C.byref(t) for t in stamps)):
            raise C.WinError(C.get_last_error())
        return sum((t.dwHighDateTime << 32) | t.dwLowDateTime
                   for t in stamps[2:]) / 10_000_000

    def capture():
        return dict(gpu=request(args.port, "gpu_state"),
                    dirty=request(args.port, "dirty_ram_stats"),
                    hot=request(args.port, "phase_hot", set="static", top=64),
                    process_cpu=cpu_seconds(), wall=time.perf_counter())

    cases = [(s, 0) for s in args.sizes]
    if args.ablate:
        cases += [(args.sizes[-1], 1), (args.sizes[-1], 0)]
    rows = []
    try:
        for index, (size, ablate) in enumerate(cases):
            case = args.output / f"{index}-{size}-mirror{1-ablate}"
            request(args.port, "gl_ws_ablate", mode=0)
            subprocess.run([sys.executable,
                str(Path(__file__).with_name("probe_adaptive_widescreen.py")),
                "--pid", str(args.pid), "--port", str(args.port), "--output", str(case),
                "--sizes", size, "--load-slot", str(args.load_slot), "--keep-size"],
                check=True, stdout=subprocess.DEVNULL)
            request(args.port, "gl_ws_ablate", mode=ablate)
            time.sleep(1)
            before = capture()
            time.sleep(args.seconds)
            after = capture()
            frame_lo = before["gpu"]["ws"]["cur_frame"]
            frame_hi = after["gpu"]["ws"]["cur_frame"]
            presents = request(args.port, "present_ring", n=2048)
            swaps = request(args.port, "gl_present_ring", n=2048)
            perf = request(args.port, "frame_perf")
            phase = request(args.port, "phase_profile", window=int(args.seconds))
            events = [r for r in swaps["events"] if frame_lo < r[1] <= frame_hi]
            flips = []
            prior = None
            for r in events:
                if r[2] not in ("wide", "vram"):
                    continue
                origin = tuple(r[4][:2])
                if prior is not None and origin != prior:
                    flips.append(r[3])
                prior = origin
            intervals = [b-a for a, b in zip(flips, flips[1:])]
            elapsed = after["wall"] - before["wall"]
            old_hot = {r["addr"]: r["samples"] for r in before["hot"]["top"]}
            hot = sorted([dict(addr=r["addr"], samples=r["samples"]-old_hot.get(r["addr"], 0))
                          for r in after["hot"]["top"]], key=lambda r:r["samples"], reverse=True)
            row = dict(size=size, mirror_enabled=not ablate, elapsed_s=elapsed,
                guest_vblank_hz=(frame_hi-frame_lo)/elapsed,
                display_flips_hz=len(flips)/elapsed,
                flip_interval_ms_median=statistics.median(intervals) if intervals else None,
                cpu_core_equivalents=(after["process_cpu"]-before["process_cpu"])/elapsed,
                interpreted_insns_s=(after["dirty"]["insns_run"]-before["dirty"]["insns_run"])/elapsed,
                gp0_draws_s=(after["gpu"]["gp0_draw"]-before["gpu"]["gp0_draw"])/elapsed,
                hot_static_wall_samples=hot[:12], frame_perf=perf, phase=phase)
            rows.append(row)
            (case / "measurement.json").write_text(json.dumps(dict(summary=row,
                before=before, after=after, presents=presents, swaps=swaps), indent=2))
            (args.output / "summary.json").write_text(json.dumps(rows, indent=2))
            print(json.dumps({k:v for k,v in row.items()
                              if k not in ("frame_perf", "phase", "hot_static_wall_samples")}), flush=True)
    finally:
        request(args.port, "gl_ws_ablate", mode=0)
        kernel.CloseHandle(proc)


if __name__ == "__main__":
    main()
