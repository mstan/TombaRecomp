#!/usr/bin/env python3
"""Find which code writes the backdrop sprites' OT packet words.
1. Dump newest frame, locate the first run of 0x65/0x64 sprite prims (the early
   2D backdrop) and collect their OT src addresses.
2. wtrace_all_dump over that addr range (newest) -> histogram of writer (pc,ra),
   and show the X-word (packet+4) writers specifically.
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
# first contiguous backdrop sprite run (0x64-0x67), before any gouraud (0x30-0x3f)
srcs=[]; started=False
for e in ents:
    op=int(e["op"],16)
    if 0x30<=op<=0x3f: break          # 3D world begins -> backdrop run over
    if 0x64<=op<=0x67:
        started=True; srcs.append(int(e["src"],16)&0x1FFFFF)
    elif started and not (op>=0xE0 or op in (0,1,2,3) or 0x64<=op<=0x67):
        break
if not srcs:
    print("no early sprite backdrop run found this frame"); sys.exit(0)
lo, hi = min(srcs), max(srcs)+0x20
print(f"frame={frame} backdrop sprite run: {len(srcs)} prims, OT src [{lo:06x}..{hi:06x}]")
print("sample srcs:", [f"{s:06x}" for s in srcs[:8]])
wt = send(json.dumps({"cmd":"wtrace_all_dump","addr_lo":f"0x{lo:x}","addr_hi":f"0x{hi:x}",
                      "newest":1,"count":2048}))
es = wt.get("entries", [])
print(f"wtrace hits in range: {len(es)} (total ring {wt.get('total')})")
from collections import Counter
byra = Counter(); bypc = Counter()
xword = Counter()  # writers of packet+4 (the xy word) -- detect by addr&0xc==4
for e in es:
    pc=int(e["pc"],16)&0x1FFFFF; ra=int(e["ra"],16)&0x1FFFFF; addr=int(e["addr"],16)&0x1FFFFF
    bypc[pc]+=1; byra[(pc,ra)]+=1
    if (addr & 0xf)==0x4: xword[(pc,ra,e["w"])]+=1
print("\ntop writer pc:")
for pc,n in bypc.most_common(8): print(f"  pc={pc:06x} n={n}")
print("\ntop (pc,ra) pairs:")
for (pc,ra),n in byra.most_common(10): print(f"  pc={pc:06x} ra={ra:06x} n={n}")
print("\nwriters of *+4 (xy word):")
for (pc,ra,w),n in xword.most_common(10): print(f"  pc={pc:06x} ra={ra:06x} w={w} n={n}")
