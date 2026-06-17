#!/usr/bin/env python3
"""Analyse the current drawn frame's GP0 ring for flower-field provenance.

Pulls gpu_ring_stats -> newest_frame, dumps that frame, then buckets prims by
opcode and source-address page, and for textured tris (0x24-0x27) extracts the
(tpage, clut) and screen-X extent. Answers: copied-vs-linked (src page), texture
uniqueness, and coord distribution -- in one shot.
"""
import socket, sys, json
HOST, PORT = "127.0.0.1", 4470

def send(cmd, timeout=30.0):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.settimeout(timeout)
    if not cmd.endswith("\n"): cmd += "\n"
    s.sendall(cmd.encode())
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(65536)
        if not chunk: break
        buf += chunk
    s.close()
    return buf.decode(errors="replace").splitlines()[0] if buf else ""

def sx(v):  # signed 11-bit-ish screen coord from low 16 bits (PSX vertex word: y<<16|x)
    x = v & 0xFFFF
    return x - 0x10000 if x & 0x8000 else x

def sy(v):
    y = (v >> 16) & 0xFFFF
    return y - 0x10000 if y & 0x8000 else y

def main():
    frame = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if frame is None:
        st = json.loads(send('{"cmd":"gpu_ring_stats"}'))
        frame = st["newest_frame"]
    dump = json.loads(send(json.dumps({"cmd":"gpu_frame_dump","frame":frame,"count":20000})))
    ents = dump.get("entries", [])
    print(f"frame={frame} prims={len(ents)}")
    # opcode histogram
    opc = {}
    for e in ents: opc[e["op"]] = opc.get(e["op"],0)+1
    print("opcodes:", dict(sorted(opc.items(), key=lambda kv:-kv[1])))
    # source-page histogram (addr>>12)
    pg = {}
    for e in ents:
        a = int(e["src"],16) & 0x1FFFFF
        pg[a>>12] = pg.get(a>>12,0)+1
    print("src pages (addr>>12):", {hex(k):v for k,v in sorted(pg.items())})
    # textured tris/quads: (tpage,clut) for cmd 0x24-0x2f
    tex = {}
    for e in ents:
        op = int(e["op"],16)
        if 0x20 <= op <= 0x3f:
            w = [int(x,16) for x in e["w"]]
            # tri (0x24-0x27): w0 cmd+color, w1 v0, w2 uv0+clut, w3 v1, w4 uv1+page,...
            # quad (0x2c-0x2f): w0 cmd+color, w1 v0, w2 uv0+clut, w3 v1, w4 uv1+page,...
            if len(w) >= 5:
                clut = (w[2] >> 16) & 0xFFFF
                page = (w[4] >> 16) & 0xFFFF
                key = (e["op"], hex(clut), hex(page))
                tex.setdefault(key, {"n":0,"xmin":9999,"xmax":-9999,"src":set()})
                t = tex[key]; t["n"]+=1
                for wi in (1,3,5):
                    if wi < len(w):
                        x = sx(w[wi]);
                        if x < t["xmin"]: t["xmin"]=x
                        if x > t["xmax"]: t["xmax"]=x
                t["src"].add(int(e["src"],16) & 0x1FFFFF)
    print("\ntextured prims by (op,clut,page):")
    for k,v in sorted(tex.items(), key=lambda kv:-kv[1]["n"]):
        srcs = sorted(v["src"]); srng = f"{hex(srcs[0])}..{hex(srcs[-1])}" if srcs else "-"
        print(f"  {k}: n={v['n']:4d} x=[{v['xmin']},{v['xmax']}] src={srng}")

if __name__ == "__main__":
    main()
