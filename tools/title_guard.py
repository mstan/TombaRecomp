"""Pause psx-runtime when the current display matches a reference BMP.

This is a development guard for menu testing. It does not write guest RAM and
does not alter game control flow; it only uses screenshot_file + pause through
the debug server after the game has naturally reached a known screen.

Optional press arguments are available so long boot/FMV paths can be skipped
with normal controller input while the guard watches for the target screen.
"""

import argparse
import json
import pathlib
import shutil
import socket
import struct
import time


def request(port, cmd, timeout=60, **kwargs):
    payload = {"id": 1, "cmd": cmd}
    payload.update(kwargs)
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        data = bytearray()
        while not data.endswith(b"\n"):
            chunk = sock.recv(1 << 16)
            if not chunk:
                break
            data.extend(chunk)
    return json.loads(data.decode("utf-8", "replace"))


def parse_int(text):
    return int(str(text), 0)


def read_bmp(path):
    data = pathlib.Path(path).read_bytes()
    if data[:2] != b"BM":
        raise ValueError(f"{path} is not a BMP")
    offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    height_raw = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    if width <= 0 or height_raw == 0 or bpp != 24:
        raise ValueError(f"{path} must be a 24-bit BMP")

    top_down = height_raw < 0
    height = abs(height_raw)
    stride = (width * 3 + 3) & ~3
    rows = []
    for y in range(height):
        src_y = y if top_down else height - 1 - y
        start = offset + src_y * stride
        rows.append(data[start:start + width * 3])
    return width, height, rows


def parse_region(text):
    if not text:
        return None
    parts = [int(p) for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("--region must be x,y,w,h")
    x, y, w, h = parts
    if w <= 0 or h <= 0:
        raise ValueError("--region width/height must be positive")
    return x, y, w, h


def mean_squared_error(a, b, step, region=None):
    aw, ah, ar = a
    bw, bh, br = b
    if aw != bw or ah != bh:
        return float("inf")
    if region:
        x0, y0, rw, rh = region
        x1 = min(aw, x0 + rw)
        y1 = min(ah, y0 + rh)
    else:
        x0, y0, x1, y1 = 0, 0, aw, ah
    total = 0
    count = 0
    for y in range(y0, y1, step):
        arow = ar[y]
        brow = br[y]
        for x in range(x0, x1, step):
            i = x * 3
            for k in range(3):
                delta = arow[i + k] - brow[i + k]
                total += delta * delta
                count += 1
    return total / max(count, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4470)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--threshold", type=float, default=1200.0)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--step", type=int, default=8)
    parser.add_argument("--region", default=None,
                        help="Optional x,y,w,h region to compare instead of the whole frame")
    parser.add_argument("--copy-to", default="title_guard_match.bmp")
    parser.add_argument("--press-buttons", default=None,
                        help="Optional pad word to pulse while waiting, e.g. 0xBFFF for Cross")
    parser.add_argument("--press-frames", type=int, default=6)
    parser.add_argument("--press-interval", type=float, default=0.75)
    parser.add_argument("--continue-first", action="store_true",
                        help="Send continue before starting the guard loop")
    args = parser.parse_args()

    workdir = pathlib.Path(args.workdir)
    reference = read_bmp(args.reference)
    region = parse_region(args.region)
    deadline = time.monotonic() + args.timeout
    next_press = time.monotonic()
    press_buttons = parse_int(args.press_buttons) if args.press_buttons else None
    best = float("inf")

    if args.continue_first:
        request(args.port, "continue")

    while time.monotonic() < deadline:
        now = time.monotonic()
        request(args.port, "screenshot_file")
        shot = workdir / "psx_screenshot.bmp"
        if not shot.exists():
            time.sleep(args.interval)
            continue
        mse = mean_squared_error(read_bmp(shot), reference, args.step, region)
        best = min(best, mse)
        if mse <= args.threshold:
            request(args.port, "pause")
            shutil.copyfile(shot, workdir / args.copy_to)
            print(json.dumps({"matched": True, "mse": mse, "best": best}))
            return 0

        if press_buttons is not None and now >= next_press:
            request(args.port, "press",
                    buttons=press_buttons,
                    frames=args.press_frames)
            request(args.port, "clear_input")
            next_press = now + args.press_interval
        time.sleep(args.interval)

    request(args.port, "pause")
    print(json.dumps({"matched": False, "best": best}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
