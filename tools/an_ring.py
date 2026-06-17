#!/usr/bin/env python3
import socket, json
s = socket.create_connection(("127.0.0.1", 4470), timeout=20); s.settimeout(20)
s.sendall(b'{"cmd":"ws_backdrop_ring"}\n')
buf = b""
while b"\n" not in buf:
    c = s.recv(65536)
    if not c: break
    buf += c
s.close()
d = json.loads(buf.decode(errors="replace").splitlines()[0])
e = d.get("ents", [])
print("ring seq", d.get("seq"), "n", d.get("n"))
if e:
    print("oldest entry frame", e[0]["f"])
    print("newest entry frame", e[-1]["f"])
    for x in e[-4:]:
        print(" f", x["f"], "pc", x["pc"], "base", x["base"], "cam", x["cam"], "ext", x["ext"], "o", x["o"], "fin", x["fin"])
