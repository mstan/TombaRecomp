# Low Input Latency

Optional, default-off input resampling for SCES-01330 Rev 1 English MAIN.
The original digital pad reader and its outer 50 Hz update still execute in
full. A checked return-site hook substitutes a newer resolved digital sample;
the original game alone derives button edges, applies input locks and updates
rumble. There is no render pass, interpolation, extra simulation or frame queue.

Requires the companion psxrecomp digital-pad snapshot API. Rebuild the runtime
and native overlays with the updated `mod_instruction_sites`; do not rename
existing native DLLs into the new configuration namespace.

Initial coverage is offline single-player digital P1. Other EU1 languages,
analog/Hybrid controllers, controller transforms/sources, multitap, netplay,
replay, rewind and state-load input guards retain original input. Previously
captured taps are not replayed across a discontinuity. Host observations cannot
recover taps that the operating system never delivered.

The engine regression is `digital_pad_snapshot_test`. The optional title
fixture `eu/tests/test_low_input_latency.c` accepts extracted MAIN0..4 paths
and checks the original-byte contracts, all 65536 return values, preserved
registers and unsupported-language/device fallback. Retail inputs are local
only and must not be distributed. Internal timings are not controller-to-TV
measurements.
