"""Resize a running Windows Tomba spike and verify its live culling margins.

Requires an enabled Fit mod and a debug runtime. Uses only the selected process's
window; restores its original placement after the probe. Screenshots and JSON
are diagnostic output, not evidence of complete level/spawn coverage.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import socket
import time


def request(port, cmd, **kwargs):
    with socket.create_connection(("127.0.0.1", port), timeout=30) as sock:
        sock.sendall((json.dumps(dict(id=1, cmd=cmd, **kwargs)) + "\n").encode())
        with sock.makefile("r") as stream:
            result = json.loads(stream.readline())
    if not result.get("ok"):
        raise RuntimeError(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--port", type=int, default=4499)
    parser.add_argument("--title", default="Tomba! - Uncapped Adaptive Spike")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", nargs="+", default=["800x600", "1280x720",
                        "1680x720", "1920x540", "1920x270", "800x600"])
    parser.add_argument("--keep-size", action="store_true",
                        help="Leave the window at the final test size")
    parser.add_argument("--load-slot", type=int,
                        help="Restore this diagnostic slot before each size (never saves)")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--fixed-aspect", choices=["16:9", "21:9", "32:9"],
                       help="Validate a fixed custom-renderer choice instead of Fit")
    modes.add_argument("--disabled", action="store_true",
                       help="Assert stock rendering even when the window is wide")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    user = C.WinDLL("user32", use_last_error=True)
    user.SetProcessDPIAware()
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumWindows.argtypes = [callback_type, W.LPARAM]
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
    user.IsZoomed.argtypes = [W.HWND]
    user.ShowWindow.argtypes = [W.HWND, C.c_int]
    user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int,
                                  C.c_int, C.c_int, W.UINT]
    windows = []

    @callback_type
    def find(hwnd, _):
        pid = W.DWORD()
        user.GetWindowThreadProcessId(hwnd, C.byref(pid))
        title = C.create_unicode_buffer(512)
        user.GetWindowTextW(hwnd, title, len(title))
        if (pid.value == args.pid and user.IsWindowVisible(hwnd)
                and title.value == args.title):
            windows.append(hwnd)
        return True

    user.EnumWindows(find, 0)
    if len(windows) != 1:
        raise RuntimeError(f"Expected one visible game window, got {windows}")
    hwnd = windows[0]
    original = W.RECT()
    user.GetWindowRect(hwnd, C.byref(original))
    maximized = user.IsZoomed(hwnd)
    rows = []
    try:
        user.ShowWindow(hwnd, 9)  # Restore, so subsequent resizes take effect.
        for size in args.sizes:
            width, height = map(int, size.split("x"))
            outer, client = W.RECT(), W.RECT()
            user.GetWindowRect(hwnd, C.byref(outer))
            user.GetClientRect(hwnd, C.byref(client))
            border_w = outer.right - outer.left - client.right
            border_h = outer.bottom - outer.top - client.bottom
            if not user.SetWindowPos(hwnd, None, 40, 40,
                                     width + border_w, height + border_h, 0x0014):
                raise C.WinError(C.get_last_error())
            if args.load_slot is not None:
                generation = request(args.port, "savestate_status")["generation"]
                request(args.port, "savestate", op="load", slot=args.load_slot)
                deadline = time.monotonic() + 5
                while True:
                    status = request(args.port, "savestate_status")
                    if status["generation"] != generation:
                        assert status["last_ok"] and status["last_op"] == "load", status
                        assert status["last_slot"] == args.load_slot, status
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Diagnostic savestate did not finish loading")
                    time.sleep(0.025)
            time.sleep(0.8)
            user.GetClientRect(hwnd, C.byref(client))
            width, height = client.right, client.bottom
            state = request(args.port, "gpu_state")
            ws = state["ws"]
            expected = 0
            aspect_w, aspect_h = (map(int, args.fixed_aspect.split(":"))
                                  if args.fixed_aspect else (width, height))
            if not args.disabled and aspect_w * 3 > aspect_h * 4:
                offset = (state["width"] * (3 * aspect_w - 4 * aspect_h)
                          + 4 * aspect_h) // (8 * aspect_h)
                expected = offset + 32
            assert ws["mode"] == (2 if expected else 0), state
            assert ws["x_margin"] == expected, (width, height, expected, ws)
            if expected:
                assert ws["game_mode"] and ws["nw_extra"] > 0, (
                    "Probe requires a parked gameplay scene, not a menu/FMV", state)
            row = dict(client=[width, height], native_width=state["width"],
                       expected_margin=expected, ws=ws)
            if ws["nw_extra"] > 0:
                terrain = request(args.port, "ws_backdrop_ring")
                (args.output / f"terrain-{width}x{height}.json").write_text(
                    json.dumps(terrain, indent=2))
                shot = request(args.port, "wide_shot", path=str(
                    (args.output / f"wide-{width}x{height}.png").resolve()))
                row["capture"] = shot
            rows.append(row)
            print(json.dumps(row), flush=True)
    finally:
        if not args.keep_size:
            user.SetWindowPos(hwnd, None, original.left, original.top,
                              original.right - original.left,
                              original.bottom - original.top, 0x0014)
            if maximized:
                user.ShowWindow(hwnd, 3)
    (args.output / "resize-results.json").write_text(json.dumps(rows, indent=2))
    print("PASS: live " + ("stock" if args.disabled else args.fixed_aspect or "Fit")
          + "/culling at " + ", ".join(args.sizes))


if __name__ == "__main__":
    main()
