#!/usr/bin/env python3
"""Summarize the drawn frame as maximal runs of same-category prims, in draw
order. Category = setup(0xE*/0x00/0x01/0x02), sprite(0x60-0x7f), flatpoly
(0x20-0x2f), gouraud(0x30-0x3f), line(0x40-0x5f). Shows seq span, count, src
range, x range, distinct cluts -> reveals scene layering + separability.
"""
import socket, sys, json
HOST, PORT = "127.0.0.1", 4470
def send(cmd, t=30.0):
    s=socket.create_connection((HOST,PORT),timeout=t); s.settimeout(t)
    if not cmd.endswith("\n"): cmd+="\n"
    s.sendall(cmd.encode()); b=b""
    while b"\n" not in b:
        c=s.recv(65536)
        if not c: break
        b+=c
    s.close(); return b.decode(errors="replace").splitlines()[0] if b else ""
def s11(v):
    v&=0x7FF; return v-0x800 if v&0x400 else v
def cat(op):
    if op>=0xE0 or op in (0x00,0x01,0x02,0x03): return "setup"
    if 0x20<=op<=0x2f: return "flatpoly"
    if 0x30<=op<=0x3f: return "gouraud"
    if 0x40<=op<=0x5f: return "line"
    if 0x60<=op<=0x7f: return "sprite"
    return f"op{op:02x}"
def xs_of(op,w):
    g=(op&0x10)!=0; quad=(op&0x08)!=0; tex=(op&0x04)!=0
    if 0x60<=op<=0x7f: return [s11(w[1])] if len(w)>1 else []
    if not(0x20<=op<=0x3f): return []
    nv=4 if quad else 3; i=1; xs=[]
    for v in range(nv):
        if g and v>0: i+=1
        if i<len(w): xs.append(s11(w[i])); i+=1
        if tex and i<len(w): i+=1
    return xs
def clut_of(op,w):
    tex=(op&0x04)!=0
    if 0x60<=op<=0x7f and tex and len(w)>2: return (w[2]>>16)&0xFFFF
    if 0x20<=op<=0x3f and tex and len(w)>2: return (w[2]>>16)&0xFFFF
    return None
def main():
    frame=int(sys.argv[1]) if len(sys.argv)>1 else None
    if frame is None:
        frame=json.loads(send('{"cmd":"gpu_ring_stats"}'))["newest_frame"]
    d=json.loads(send(json.dumps({"cmd":"gpu_frame_dump","frame":frame,"count":20000})))
    ents=d.get("entries",[])
    print(f"frame={frame} prims={len(ents)}")
    runs=[]; cur=None
    for e in ents:
        op=int(e["op"],16); w=[int(x,16) for x in e["w"]]; c=cat(op)
        src=int(e["src"],16)&0xFFFFFF; xs=xs_of(op,w); cl=clut_of(op,w)
        if cur and cur["cat"]==c:
            cur["n"]+=1; cur["srcmin"]=min(cur["srcmin"],src); cur["srcmax"]=max(cur["srcmax"],src)
            if xs: cur["xmin"]=min(cur["xmin"],min(xs)); cur["xmax"]=max(cur["xmax"],max(xs))
            if cl is not None: cur["cluts"].add(cl); cur["ops"].add(op)
        else:
            if cur: runs.append(cur)
            cur={"cat":c,"n":1,"seq0":e["seq"],"srcmin":src,"srcmax":src,
                 "xmin":min(xs) if xs else 9999,"xmax":max(xs) if xs else -9999,
                 "cluts":set([cl]) if cl is not None else set(),"ops":set([op])}
    if cur: runs.append(cur)
    for r in runs:
        xr=f"[{r['xmin']},{r['xmax']}]" if r["xmax"]>-9999 else "-"
        cl=",".join(f"{c:04x}" for c in sorted(r["cluts"])[:6]) or "-"
        ops=",".join(f"{o:02x}" for o in sorted(r["ops"]))
        print(f"  seq0={r['seq0']:>8} {r['cat']:>8} n={r['n']:>3} "
              f"src=[{r['srcmin']:06x}..{r['srcmax']:06x}] x={xr:>14} ops={ops:>11} clut={cl}")
if __name__=="__main__": main()
