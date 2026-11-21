# Tomba! (USA) release notes

## 0.24.5-alpha - shared packaging on Windows and Linux

The shared release workflow clears a stale profiling hook in a portable way,
including CMake 3.28 on Linux. The Linux package keeps its writable player data
separate from the read-only AppImage. Both release channels retain visible
Input Recording enabled by default and remember a saved Off choice. The
qualified scene, audio, Fit-to-screen and native-save behavior from 0.24.4 is
retained; explicit saved presentation and audio choices remain authoritative.

## 0.24.4-alpha - regional scene retention and saved audio sync

Event-title animations preserve the scene's intended aspect through the final
display frame. Fresh profiles enable Audio Sync Fix with a 70 ms buffer target;
the Mods page retains saved on/off and buffer choices, applied next game start.
Disabling this optional adjustment restores the configured fallback and keeps
game audio enabled. Home Quick Mods cards remain disabled.

This USA Windows update uses accepted public framework pins and the shared
release pipeline. Available regional originals have identity, plugin and
configuration checks; this package and gameplay qualification are USA only.
US movement, adaptive Fit resizing, current-build state restore, cold native
memory-card loading and continued execution pass. The normal full AOT cache
contains 175 audited native pairs with 8,037 guard rows. Memory cards and
explicit saved settings remain intact.

No new physical audio-latency measurement, listening verdict, native-card write,
whole-campaign or exact all-regional quest-scene acceptance is claimed. Linux
metadata is configured for the shared packager; this update does not ship a
newly qualified Linux artifact. CD Speed, Fast Loading and retired frame
blending packages remain excluded.


## 0.24.3-alpha — production TCP server and default adaptive widescreen

Integrates the production TCP Debug Server previously available only in the
PR #49 test prerelease. Enable it in Mods / Advanced before launching, then
connect Archipelago or another local tool to 127.0.0.1:4370. The choice is
remembered and starts disabled. Bulk RAM writes support 1–1024 bytes and reject
invalid requests before writing any memory. Development tracing stays off.

Fresh profiles enable Widescreen with Fit to Window and Internal Resolution
at 4x. Explicit saved aspect, mod and resolution choices remain in effect.
The qualified HLE geometry, native waits and shared native services from
0.24.2 are retained. This prerelease contains only Tomba! (USA), SCUS-94236.

## 0.24.2-alpha — current master, USA HLE and internal HD resolution

Updates psxrecomp to master `a7b37e07` and recomp-ui to master `a956157`.
The USA build selects the enhanced execution profile, native terrain geometry
(including flat triangles), audited native waits, ordered OpenGL batching, and
the shared native CPU, capture, media, OpenBIOS read, presentation and resident
preparation services. The release pipeline builds fresh selective runtime PGO.

Internal Resolution is enabled at 4x for fresh profiles. Select 1x through 32x
in Mods, subject to GPU limits; existing saved choices remain in effect.
This prerelease contains only Tomba! (USA), SCUS-94236. CD Speed and Fast Loading
are excluded. Native memory-card saves remain supported.

## 0.24.1-alpha — shared optimization release

Fresh settings enable Internal Resolution at 4x. The Mods selector offers 1x through 32x; saved choices are preserved, and GPU texture and memory limits still apply. Disabling the mod selects native resolution.

This build includes the combined qualified engine optimizations and uses the shared release pipeline with selective runtime PGO. CD Speed and Fast Loading packages are excluded. Existing memory cards remain supported.

Automated gameplay validation for this release batch is limited to Ape Escape and Tomba 2. The other titles use build and package checks followed by owner visual approval; no per-title performance gain is claimed.

# 0.24.0-alpha: audited native execution

USA: select audited SDK/scratchpad waits and the native flat textured-triangle terrain batch. The four geometry formats matched the original generated callers on 800 captured batches; opening-level movement and current-build save/load pass. Two usable production comparisons of the combined package observed about 33% less process CPU per frame under background load; this is not a whole-game guarantee. Refresh the USA native cache for ABI 35. Other regions retain their previously published builds; this release's optimization coverage is USA only.

