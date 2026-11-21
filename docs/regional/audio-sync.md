# Audio Sync Fix

Audio Sync Fix is enabled by default for new profiles. It reduces host buffering
and prevents accelerated boot/fast-forward audio from building a delayed queue.
After a real presentation underrun it also avoids queuing accelerated catch-up.
Guest speed and SPU simulation are unchanged. Fast-forward is intentionally mute.

ON uses a 70 ms target by default; OFF restores the game's configured fallback.
The Audio Buffer slider offers 20–180 ms in 5 ms steps. 70 ms is Recommended;
lower values are Experimental (20 ms is known unstable), and higher values give
more reserve. Both views use the same saved mod option. Reset to Defaults resets
only that target to 70 ms. Existing enabled/disabled and target choices remain
authoritative. Changes apply at the next game start, not to a running device.
High Quality SPU / Enhanced Audio is independent. Quick Mods and Mods use the
same normal saved feature state. No account or network service is involved.

Audio Diagnostics optionally emits target, actual fill and host lifecycle
counters once per second to the runtime log. It is off by default. Fill is not
measured end-to-end output latency; Windows, HDMI and receivers add delay that
has not been measured here. Underruns count depletion episodes (including some
intentional draining), overflow counts dropped frames, and device closes do not
include driver-internal resets. There is no callback file I/O.

A long display-mode switch may still cause brief silence while recovering.
These host-buffer changes do not measure or control external TV/receiver delay.
The shared runtime uses no regional game addresses. Platform and regional
listening checks remain necessary; this is not a campaign-wide guarantee.
The owner confirmed 70 ms without audible issues on one system. Lower targets
can stutter or drop out; no universal safe minimum is claimed.
