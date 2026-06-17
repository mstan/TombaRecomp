#!/usr/bin/env python3
"""Minimal JSON-line client for the psx-runtime debug server (TCP 4470).

Usage:
  python dbg.py '{"cmd":"frame"}'
  python dbg.py '{"cmd":"wtrace_all_dump","addr_lo":"0x0b3000","addr_hi":"0x0b6000","newest":1,"count":400}'
Reads one response line and prints it (optionally pretty for entries arrays).
"""
import socket, sys, json

HOST, PORT = "127.0.0.1", 4470

def send(cmd, timeout=20.0):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.settimeout(timeout)
    if not cmd.endswith("\n"):
        cmd += "\n"
    s.sendall(cmd.encode())
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    s.close()
    return buf.decode(errors="replace").splitlines()[0] if buf else ""

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else '{"cmd":"frame"}'
    line = send(cmd)
    try:
        obj = json.loads(line)
        print(json.dumps(obj, indent=1)[:8000])
    except Exception:
        print(line[:8000])
