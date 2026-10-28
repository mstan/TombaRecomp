# Low Input Latency

Optional, default-off fresher resolved digital P1 input. The original pad reader,
button-edge logic, dialogue locks, actions and rumble remain in control; no extra
simulation or rendering is introduced. US/Japan retain 60 Hz and Europe 50 Hz.

Verified original-byte profiles cover USA, all five EU1 languages, both EU2
revisions and their five languages, and Japan. European routines differ only in
verified data relocations. Japan retains its original packed P1/P2 BIOS producer;
the checked cached-P1 store is observed in both original loop callers. Its
legacy ReadPad button bytes are converted to the canonical host layout before
priming and back to the original layout before the guest store. P2 stays original.

Requires the companion psxrecomp digital-pad snapshot API. Rebuild the runtime
and overlays with the added mod_instruction_sites. Never rename old native DLLs
into a new configuration namespace. Whole-function contracts and device checks
fall back to original input when a profile or controller mode is unsupported.

Short controller-only LOAD checks pass for USA and English EU2 original revision:
walking, direction changes, jump/landing, and observed input edges. English EU1
also has an owner-confirmed responsiveness improvement. The other European
languages and EU2 Rev 1 have original-byte contract coverage, not new gameplay
acceptance. Japan's original menu lists the save, but loading into controllable
gameplay remains unconfirmed after the bounded follow-up, including the byte-
layout correction. These checks are not campaign certification.

Coverage is offline single-player digital P1. Analog/Hybrid, registered controller
transforms or sources, configured multiple pads, multitap, netplay, replay and
input guards retain original input. Unknown guest-only multiplayer patches are
not validated by this API.
Short observed taps are latched; discontinuities re-prime without replaying old
edges. No host API can recover input that the operating system never delivered.

The engine regression is digital_pad_snapshot_test. The optional title fixture
eu/tests/test_low_input_latency.c accepts owner-extracted regional executables
and checks original-byte contracts, preserved registers and fallback paths.
Retail bytes are never distributed. Internal timings are not controller-to-TV
measurements. Frame interpolation is independent and is not part of this change.

The validated US/EU production paths are unchanged; Japan only received the
necessary legacy-button byte-layout correction. Re-polling SDL inside the guest hook
or changing presentation timing needs separate correctness work; neither is an
additional proven safe latency reduction in this change.
