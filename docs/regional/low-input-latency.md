# Low Input Latency

Optional, default-off fresher resolved digital P1 input. The original pad reader,
button-edge logic, dialogue locks, actions and rumble remain in control; no extra
simulation or rendering is introduced. US/Japan retain 60 Hz and Europe 50 Hz.

Verified original-byte profiles cover USA, all five EU1 languages, both EU2
revisions and their five languages, and Japan. European routines differ only in
verified data relocations. Japan retains its original packed P1/P2 BIOS producer;
the checked cached-P1 store is observed in both original loop callers.

Requires the companion psxrecomp digital-pad snapshot API. Rebuild the runtime
and overlays with the added mod_instruction_sites. Never rename old native DLLs
into a new configuration namespace. Whole-function contracts and device checks
fall back to original input when a profile or controller mode is unsupported.

Runtime acceptance beyond EU1 is still pending; static contracts alone are not
a gameplay acceptance test. This regional extension remains a review draft.

Coverage is offline single-player digital P1. Analog/Hybrid, controller transforms
or sources, multitap, netplay, replay and input guards retain original input.
Short observed taps are latched; discontinuities re-prime without replaying old
edges. No host API can recover input that the operating system never delivered.

The engine regression is digital_pad_snapshot_test. The optional title fixture
eu/tests/test_low_input_latency.c accepts owner-extracted regional executables
and checks original-byte contracts, preserved registers and fallback paths.
Retail bytes are never distributed. Internal timings are not controller-to-TV
measurements. Frame interpolation is independent and is not part of this change.
