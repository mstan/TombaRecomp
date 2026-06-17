#!/usr/bin/env python3
"""Dump the current drawn frame's GP0 prims in DRAW ORDER (seq), correctly
decoding per primitive type (flat vs gouraud, tri/quad/rect). Shows seq, op,
src OT addr, color, vertex X range, clut, tpage. Goal: locate the flower-field
backdrop run and test whether it is a contiguous OT src-addr range.
"""
import socket, sys, json
HOST, PORT = "127.0.0.1", 4470

def send(cmd, timeout=30.0):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.settimeout(timeout)
    if not cmd.endswith("\n"): cmd += "\n"
    s.sendall(cmd.encode()); buf = b""
    while b"\n" not in buf:
        ch = s.recv(65536)
        if not ch: break
        buf += ch
    s.close()
    return buf.decode(errors="replace").splitlines()[0] if buf else ""

def s11(v):
    v &= 0x7FF
    return v - 0x800 if v & 0x400 else v

def decode(op, w):
    """Return (color, [xs], clut, tpage). Handles flat/gouraud tri/quad/rect."""
    color = w[0] & 0xFFFFFF
    xs, clut, tpage = [], None, None
    g = (op & 0x10) != 0          # gouraud (shaded)
    quad = (op & 0x08) != 0
    tex = (op & 0x04) != 0
    rect = (op & 0x60) == 0x60
    if rect:                       # 0x60-0x7f: cmd+color, xy, (uv+clut), (wh)
        if len(w) > 1: xs.append(w[1] & 0xFFFF and s11(w[1]))
        if tex and len(w) > 2: clut = (w[2] >> 16) & 0xFFFF
        return color, [s11(w[1])] if len(w)>1 else [], clut, None
    nv = 4 if quad else 3
    i = 1
    for vtx in range(nv):
        if g and vtx > 0:
            i += 1                 # color word before each vertex (except first uses w0)
        if i < len(w):
            xs.append(s11(w[i])); i += 1
        if tex:
            if i < len(w):
                wd = w[i]
                if vtx == 0: clut = (wd >> 16) & 0xFFFF
                elif vtx == 1: tpage = (wd >> 16) & 0xFFFF
                i += 1
    return color, xs, clut, tpage

def main():
    frame = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if frame is None:
        st = json.loads(send('{"cmd":"gpu_ring_stats"}')); frame = st["newest_frame"]
    d = json.loads(send(json.dumps({"cmd":"gpu_frame_dump","frame":frame,"count":20000})))
    ents = d.get("entries", [])
    print(f"frame={frame} prims={len(ents)}")
    print(f"{'#':>3} {'seq':>6} {'op':>4} {'src':>8} {'color':>7} {'clut':>5} {'tpage':>5}  xrange")
    for i,e in enumerate(ents):
        op = int(e["op"],16); w = [int(x,16) for x in e["w"]]
        color, xs, clut, tpage = decode(op, w)
        src = int(e["src"],16) & 0xFFFFFF
        xr = f"[{min(xs)},{max(xs)}]" if xs else "-"
        cl = f"{clut:04x}" if clut is not None else "  -  "
        tp = f"{tpage:04x}" if tpage is not None else "  -  "
        print(f"{i:>3} {e['seq']:>6} 0x{op:02X} {src:08x} {color:06x} {cl:>5} {tp:>5}  {xr}")

if __name__ == "__main__":
    main()
