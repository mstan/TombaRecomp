#!/usr/bin/env python3
"""Run one prim<->pixel correlation experiment: set ws_dbg_stretch mode (+clut/lo/hi),
let a few frames render, capture wide_shot, copy it to a mode-named PNG, and print
the match report. Usage:
  python tools/an_dbg.py 0                 # off (baseline void)
  python tools/an_dbg.py 6                 # all textured
  python tools/an_dbg.py 4                 # tagged
  python tools/an_dbg.py 5                 # untagged textured
  python tools/an_dbg.py 2 780f            # clut==0x780f
  python tools/an_dbg.py 1 - 0b5600 0b5a40 # OT range [lo,hi]
"""
import socket, json, sys, shutil, time
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

mode = int(sys.argv[1])
req = {"cmd":"ws_dbg_stretch","mode":mode}
if len(sys.argv) > 2 and sys.argv[2] != "-": req["clut"] = sys.argv[2]
if len(sys.argv) > 3: req["lo"] = sys.argv[3]
if len(sys.argv) > 4: req["hi"] = sys.argv[4]
r = send(json.dumps(req))
print("set:", json.dumps(r))
time.sleep(0.5)                      # let several frames render with the new gate
r2 = send('{"cmd":"ws_dbg_stretch","mode":%d}' % mode)   # re-read counts
print("counts:", json.dumps(r2))
shot = send('{"cmd":"wide_shot"}')
tag = sys.argv[2] if (mode==2 and len(sys.argv)>2) else ""
out = f"psx_dbg_m{mode}{('_'+tag) if tag else ''}.png"
shutil.copyfile("psx_wide.png", out)
print("shot:", out, shot.get("width"), "x", shot.get("height"))
