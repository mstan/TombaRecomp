# Archipelago and local debugging

Release builds include the TCP debug server. It is **off by default**.
In the launcher, open **Mods**, enable **TCP Debug Server** in **Advanced**,
and launch the game. The launcher remembers the choice. Disable the feature
before your next launch to turn the server off.

The server listens on **127.0.0.1:4370** by default and lets local tools read
and write game memory. The existing `[runtime] debug_port` setting in
`game.toml`, or `--debug-port <port>`, changes the port. Choosing a port alone
does not enable the server. For scripts, `PSX_DEBUG_SERVER=1` explicitly
enables the listener and `PSX_DEBUG_SERVER=0` forces it off.

Archipelago clients can use the existing newline-delimited JSON protocol:

```json
{"id":1,"cmd":"write_bulk","addr":"0x80010000","hex":"48656c6c6f00"}
```

`addr` is a quoted hexadecimal PS1 address, and `hex` contains 1–1024 bytes
encoded as hexadecimal pairs. The 128-byte chunks used by the Tomba
Archipelago bridge are supported. One request writes the full run and returns
one `{"id":1,"ok":true}` response. Invalid hex, oversized payloads and writes
outside a contiguous main-RAM span return an error before changing memory.
The existing `read_ram` and single-byte `write_ram` commands remain available.

No custom debug build or replacement `debug_server.c` is required. Enabling
the server does not enable development-only per-block tracing. This supplies
the connection and bulk-write support requested in
[issue #47](https://github.com/mstan/TombaRecomp/issues/47); installation and
gameplay setup still follow the instructions for your Archipelago client.
