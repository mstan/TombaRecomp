#!/usr/bin/env python3
"""Clean single-word trace: find the writer of ONE backdrop sprite's XY word.
Dump newest frame, take the first 0x65 sprite (its OT packet base = src), then
wtrace EXACTLY [base+4, base+8) (the xy word) and [base, base+4) (cmd word).
Report distinct (pc,ra,new_val,w). Avoids the shared-OT range contamination.
"""
import socket, json, sys
HOST, PORT = "127.0.0.1", 4470
def send(cmd, t=30.0):
    s=socket.create_connection((HOST,PORT),timeout=t); s.settimeout(t)
    if not cmd.endswith("\n"): cmd+="\n"
    s.sendall(cmd.encode()); b=b""
    while b"\n" not in b:
        c=s.recv(65536)
        if not c: break
        b+=c
    s.close(); return json.loads(b.decode(errors="replace").splitlines()[0])

frame = send('{"cmd":"gpu_ring_stats"}')["newest_frame"]
d = send(json.dumps({"cmd":"gpu_frame_dump","frame":frame,"count":20000}))
ents = d.get("entries", [])
base=None
for e in ents:
    op=int(e["op"],16)
    if 0x30<=op<=0x3f: break
    if 0x64<=op<=0x67:
        base=int(e["src"],16)&0x1FFFFF
        w=[int(x,16) for x in e["w"]]
        print(f"frame={frame} first sprite op=0x{op:02X} base={base:06x} words={[f'{x:08x}' for x in w]}")
        break
if base is None:
    print("no sprite found"); sys.exit(0)
for label,(lo,hi) in [("cmd  base+0",(base,base+4)),("XY   base+4",(base+4,base+8)),
                       ("uv   base+8",(base+8,base+12)),("wh   base+c",(base+12,base+16))]:
    wt=send(json.dumps({"cmd":"wtrace_all_dump","addr_lo":f"0x{lo:x}","addr_hi":f"0x{hi:x}",
                        "newest":1,"count":64}))
    es=wt.get("entries",[])
    seen={}
    for e in es:
        k=(int(e["pc"],16)&0x1FFFFF, int(e["ra"],16)&0x1FFFFF, e["w"])
        seen.setdefault(k,[]).append(int(e["new"],16))
    print(f"\n[{label}] hits={len(es)}")
    for (pc,ra,w),vals in sorted(seen.items(), key=lambda kv:-len(kv[1]))[:5]:
        print(f"  pc={pc:06x} ra={ra:06x} w={w} n={len(vals)} vals={[f'{v:08x}' for v in vals[:4]]}")
