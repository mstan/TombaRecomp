# Tomba! (USA) release notes

## 0.24.1-alpha — shared optimization release

Fresh settings enable Internal Resolution at 4x. The Mods selector offers 1x through 32x; saved choices are preserved, and GPU texture and memory limits still apply. Disabling the mod selects native resolution.

This build includes the combined qualified engine optimizations and uses the shared release pipeline with selective runtime PGO. CD Speed and Fast Loading packages are excluded. Existing memory cards remain supported.

Automated gameplay validation for this release batch is limited to Ape Escape and Tomba 2. The other titles use build and package checks followed by owner visual approval; no per-title performance gain is claimed.

USA: select audited SDK/scratchpad waits and the native flat textured-triangle terrain batch. The four geometry formats matched the original generated callers on 800 captured batches; opening-level movement and current-build save/load pass. Two usable production comparisons of the combined package observed about 33% less process CPU per frame under background load; this is not a whole-game guarantee. Refresh the USA native cache for ABI 35. Other regions retain their previously published builds; this release's optimization coverage is USA only.

