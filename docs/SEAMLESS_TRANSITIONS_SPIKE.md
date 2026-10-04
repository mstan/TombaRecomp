# Tomba seamless transitions spike

Release promotion: v0.15.0-alpha enables this implementation by default as
**Seamless Loading**, retaining the existing package and feature IDs so explicit
opt-outs survive. The release also includes the current launcher file-picker
fixes. The assessment and captures below describe the original default-off
spike; broader whole-game validation remains tracked by `beads-eio.4.20`.

The target is a menu or area transition with no loading screen, load-induced
blackout, held image, or audio hiccup. The worktree now implements a default-off,
game-owned resident loader and transition adapter. It prepares immutable assets
once from the supplied disc, installs the requested destination from current
game state, and bypasses completed loading phases. It does not use turbo, alter
CD timing, suppress cooperative yields, discard audio, or restore cached game
snapshots. **This remains an experimental spike, not whole-game acceptance.**

Game-specific code may remain entirely in TombaRecomp, as the owner clarified.
Generalizing the implementation is optional. The live experiment covers menu
loads and a walked round trip through Dwarf Village. The owner
clarified that the audio concern is the stuttering heard with previous turbo
fast-loading. Keep normal audio timing and normal game-directed music changes;
continuous outgoing music across every boundary is not a separate requirement.

Baseline: Tomba `05d82b96d31c2bab59256095cdfec82ccd328310`, framework
`c68bf6e08568327d0c6816d083cf7d00875593f0`, UI
`e45e1f3062731abc188e351cad3608730b01fa12`. Worktree branch:
`spike/tomba-seamless-transitions-20261004`. Central tracking: assessment
`beads-eio.4.18`, constrained implementation `beads-eio.4.19`, broader release
validation `beads-eio.4.20`.

## Prebuilt executable and first-run data preparation

Players supply the supported SCUS-94236 disc to a prebuilt executable. Enabling
the experimental Resident Assets mod prepares its data before gameplay begins.
The native C++ preparer uses the mounted-disc file service; it needs no Python,
compiler, generated game C, source checkout, or extraction script on the
player's machine. The legacy code-generation wizard is now an explicit
developer CMake option, `PSX_SETUP_WIZARD=ON`, default OFF. This spike does not
claim to migrate the existing release CI or redesign the launcher setup UI.
The existing Windows and AppImage prebuilt packagers explicitly disable both
the wizard and setup-host mode, including when reusing an older CMake cache.
The separate setup-host GitHub workflow still needs migration before publishing
the new release model.

The local pack contains 1,062 files, excluding 22 STR movies and the disc filler
file. Both sector-padded originals and decoded GAM output remain resident:
74,405,256 payload bytes, about 71 MiB. Every source and decoded blob is checked
against the supported-disc metadata. Only filenames, sizes, locations and hashes
are committed; the pack contains original game assets and stays local.

Windows cache: `%LOCALAPPDATA%/TombaRecomp/seamless/c259ec7ff6ef4163-gam-v1.pack`.
Other platforms use `$XDG_CACHE_HOME`, or `$HOME/.cache`, under the same game
directory. `TOMBA_SEAMLESS_CACHE` changes the cache directory for isolated tests.
The developer-only `TOMBA_SEAMLESS_PACK` selects an explicit existing pack.
Versioned headers, bounds checks and a body checksum reject invalid caches;
normal caches are then rebuilt from the mounted disc. Publication uses a
process-specific temporary file and atomic replacement. A failed preparation
preserves the previous complete cache and leaves the native loader disabled.

The independent Python builder and native preparer produce exactly the same
74,439,288-byte pack, SHA-256
`dacc6f5ef2d21d6c0a052005621d0bbd379131a290aa058f2d0ba3c3eb221db4`.
Corrupting a body byte in the isolated cache caused regeneration from the disc
and restored the exact expected hash. Warm reuse left the cache timestamp
unchanged, with no preparation pass.
This catalog supports stock assets only. Asset-replacement mods and other disc
editions need a separate compatibility/cache-identity design before support.

A staged player smoke run contained the executable, configs, OpenBIOS, launcher
assets, mod catalog and audited native overlays. It contained no loose PS-X EXE,
generated C, recompiler, Python or overlay compiler. With only Windows system
directories on the runtime PATH and a fresh prepared-data directory, it produced
the expected pack, read the executable image from the supplied disc, played the
opening movies, and entered a new game through the title menu. The first NPC
conversation rendered correctly. This used normal movie playback and no save
state restore. The test directory was under this worktree; save/options paths
still resolved to the worktree, so this is not an installer-isolation test.

## Runtime implementation and current evidence

`src/mods/tomba_seamless.c` chains the existing BIOS/dispatch replacement seam.
It preflights the complete resource queue before replacing loader-thread
startup. The adapter writes the real RAM, texture and sound-bank data, updates
the original decoder's counters, and signals completion only afterward.
Executable writes also invalidate interpreted overlay generations. Unsupported
requests use the retail path and count as failed seamless coverage.

The transition adapters execute the original one-shot setup states together.
They retain current inventory/events and do not pre-run neighboring gameplay.
An outgoing scene that has requested an immediate handoff does not enqueue
primitives referencing memory that the destination will replace; the completed
destination renders in that tick. The ordinary visual fades remain. A deferred
fade actor initialization is combined with its first fade step, removing an
otherwise fully black first destination frame. Music start/stop functions are
preserved; `0x8002065C` starts music and is not a visual fade function.
When exit movement finishes after the fade, its following pure readiness check
now runs immediately. Movement still runs once. This removes the repeated image
at the Watch Tower boundary without changing fade speed or scheduler yields.

Reverb setup also performs real synchronous SPU writes instead of waiting for
each small DMA transfer. The retail allocation guard and music/reverb commands
remain. Forty comparisons with the original MIPS routine cover all ten modes,
two source patterns and two poisoned SPU buffers; full SPU RAM and transfer
globals match, including the last rounded DMA wrapping around SPU RAM. On the
measured mode this removed roughly 500,000 guest cycles of transfer waiting.

Immediate installation also exposed a cold-boot ownership bug: the final logo
queued primitives before replacing their storage with title assets. That final
old-logo draw is omitted only at the verified handoff. Submitted GPU work is
drained before any batch RAM write. A full cold boot now reaches the title.

Menu Load Game reads the live memory-card subsystem, including unsaved in-memory
card writes. It supports Tomba's ordinary single-block saves, checks directory
metadata/checksum, and leaves retail save checksum/deserialization intact.
Unsupported card layouts use the original reader. No save writes are replaced.
Two guarded calls bridge the interpreted menu overlay to existing compiled
entry points because internal interpreter calls do not reach the dispatch hook.

On the local OpenGL debug build:

| Gate | Evidence / remaining limit |
| --- | --- |
| Decoder fidelity | All 397 distinct streams matched original MIPS twice, including final-token tails. |
| Native preparation | Full pack equals the independent offline fixture; altered source rejected; valid cache preserved. |
| Native reverb | Forty original-MIPS/native comparisons match every SPU byte and transfer register. |
| Automated project checks | All four CTest checks pass, including six decoder cases and staged mod catalog validation. |
| AOT overlays | Fresh disc pipeline: 25 recipes, 196 native pairs, 8,213 manifest rows; ABI/byte audit passes and runtime native calls confirmed. Interpreter fallbacks still exist. |
| Cold boot / new game | Staged binary with fresh asset cache reaches title and the opening NPC conversation with movies enabled, without restoring a fixture. |
| Menu destinations | Stormy Mountain, Charity Square and Watch Tower entered from real card saves. |
| Walked exits, latest visual run | Watch Tower `1/3` → `1/1` → Dwarf Village `2/0` → `1/1`; no pigs or fully black frames captured. |
| State continuity | AP changed from 130400 to 130900 through actual gameplay and remained 130900 across the village round trip. This is not an exhaustive inventory/event test. |
| Resource installation | Latest uninstrumented route batches about 0.01–1.4 ms; no native batch crossed a guest VBlank. |
| Whole handoff | Final run: menu ~16.2 ms, neighbor ~5.8 ms, village ~17.6 ms, return ~18.7 ms, including guest pacing. Some handoffs still cross a guest VBlank; computation is not literally zero. |
| Audio, capture/tracing disabled | Four-route run at normal ~60 Hz: zero increases in output underruns, pump skips or overflow drops. WAVs retained for inspection. Existing boot/restore drop totals are not counted as transition results. |
| Final walked boundary images | No repeated adjacent images within seven frames of any of the three handoffs. No loading UI or fully black captured frames. The game's ordinary fades remain. |
| Menu response | Static confirmation menu changes directly to the destination, two presentation frames after the loader starts. This is not a claim of zero input-to-display latency. |

Local evidence is ignored under `build-seamless`: `*-v25` display captures,
`audio-aot-v18/receipt.json` and WAVs, `probe-stage-v22` profiling logs,
`aot-stage/AOT_CACHE_AUDIT.json`, and the `player-smoke-v22` first-run package.
The staged-player repeat in `audio-player-v22` and final `audio-accept-v25` run
both passed all six audio counter checks at normal speed. The final four capture
intervals contain 757 consecutive images in total, with no internal gaps; these
intervals include each transition. Their trailing export/observation time is
not part of the captured interval. A compact, asset-free record is committed as
`docs/seamless_runtime_receipt.json`; the original audio and images stay local.
Frame readback has overhead; audio measurements run separately with
`PSX_FNTRACE_ALL=0` and `PSX_DISPLAY_RING=0`. `TOMBA_SEAMLESS_TRACE=1` enables
detailed resource/initializer logging for diagnosis, not acceptance timing.
Known menu savestate fixtures are test inputs only. Cross-process gameplay
savestates proved unreliable on this framework pin, so route evidence uses an
actual card load followed by uninterrupted walking, not restored area snapshots.

The detailed profile places most remaining guest cycles in the first ordinary
gameplay update/draw, not resource installation. The village update also uses
roughly 460,000--500,000 cycles on subsequent ordinary frames. The repeated
Watch Tower image came from the exit actor's completed movement entering its
final readiness check a tick later. The guarded same-tick completion above
removed it in the final captures. These results do not justify preparing an
inactive neighboring gameplay state for the constrained routes.

The constrained menu/area spike is validated on the routes above. Release
validation still needs frame-level movie handoffs,
death/continue, warps, event variants, further areas, and other
renderers. No speculative neighboring-scene cache is implemented: measurements
must establish which work needs preparation before that complexity is justified.

## What the asset experiment proved

The probe reads the owner's original SCUS-94236 disc, verifies its SHA-1, extracts
ordinary ISO files using the framework reader, and decodes every whole-file
`GAM` stream into host-owned data. It can write content-addressed prepared blobs
into an ignored build directory. No original assets or executable code are
included in the commit.

| Measurement | Result |
| --- | ---: |
| Disc files enumerated | 1,085 |
| GAM files decoded | 637 |
| Distinct compressed GAM streams | 397 |
| Distinct streams checked against original MIPS | 397 |
| Original executions per distinct stream | 2 |
| Decoder or oracle failures in final run | 0 |
| Prepared GAM bytes across all file entries | 44,417,325 |
| Prepared non-STR bytes across all file entries | 119,446,108 |
| Prepared non-STR bytes after content deduplication | 85,277,879, about 81.3 MiB |
| STR movie streams excluded | 22 |

The 81.3 MiB estimate includes raw overlays, sound files, system assets, and
27,648,000 bytes in the ZZZ directory; it is conservative about which files are
needed. It excludes decoded video, GPU allocations, live audio state, metadata,
and other runtime overhead. Storing compressed originals as well would cost
additional memory. The complete file manifest is local at
`../build-seamless/asset-report.json`; a compact receipt is committed beside
this document as `seamless_asset_receipt.json`.

The oracle executes the original executable's `0x8003EF50` routine, including
its original `0x8005B77C` copy helper, in Unicorn 2.1.4. Each distinct stream is
checked with destination bytes initially filled with both `0xA5` and `0x5A`.
Every output byte and surrounding output canaries must match. Six synthetic
tests cover literals, overlapping references, flag rollover, dependence on prior
RAM, truncation/size bounds, and final-token tails.

An important format detail: 302 GAM files finish a back-reference beyond the
declared logical output size, by up to 252 bytes. The original routine tests
the size after completing the token. The probe preserves that full write extent
and matches the original. Truncating a prepared blob to the header size would
lose writes performed by the retail decoder.

This proves immutable output preparation for these files. It does not prove
when the game may observe those writes, establish an entire loader replacement
ABI, or reproduce the decoder's scratchpad/register side effects. The oracle
has no game scheduler, interrupts, GPU, or audio. It is deliberately a byte
oracle, not a timing or gameplay oracle.

## What loading actually does

Read-only headless Ghidra inspection of `psx/Tomba1` establishes the following
main-executable paths. Addresses apply to the supported USA executable only.

| Address or data | Observed responsibility |
| --- | --- |
| `0x80021D70` | Interprets 20-byte asset descriptors; selects destinations and pointer slots; enqueues descriptor/destination pairs. |
| `0x80021340` | Cooperative loader thread: CD setup/read/wait, decode or direct transfer, GPU transfer/synchronization, sound-bank setup, queue completion. Also used for world streaming. |
| `0x8003EF50` | GAM back-reference decoder; writes scratchpad/global counters as well as output. |
| `0x8005B77C` | Forward byte-copy helper supporting overlapping back-references. |
| `0x80021CC8` | Selects common and subarea descriptors through the table at `0x80079150`. Its zero third-argument path invokes `0x80021180`. |
| `0x8001CE80` | A caller preparing area/subarea state and invoking `0x80021CC8`, followed by additional initialization and load startup. |
| `0x80021C24` | Selects a resource list, starts loader thread 2, and cooperatively waits for completion. |
| `0x800222B8` | Selects other lists and optionally starts loading; can first load a shared resource list. |
| `0x80021BC4`, `0x800223A0` | Other list-selection wrappers around `0x80021D70`. |
| `0x800791A0` | Executable file table, eight bytes per file ID: CD position and size. |
| `0x1F80029C`, `0x1F8002A0` | Producer and consumer indices of the 128-entry loader ring at `0x8009E748`. |
| `0x1F8001CE` | Queue-completion flag; used by multiple callers. Not sufficient alone to identify a safe scene handoff. |
| Type `0xF0` | Executable overlay destination `0x800E7388`; corroborated by the existing AOT overlay analysis. |

The loader's processing stage distinguishes raw/decode/upload modes and handles
sound-bank setup for type `0x90`. It advances cooperatively through
`0x800171D4(1)`. Finishing file reads is therefore only one part of making an area
ready. The implemented state adapters now cover the traced menu/new-game and
ordinary exit paths; enumeration of every special transition remains incomplete.

There are 20 SYS loader catalog files: LDSYS plus 19 LDAR files. The disc also
has AREA00 through AREA19 directories. Neither count is a proven count of
playable areas or transition routes. Existing original-disc AOT analysis finds
25 distinct executable overlays, including 17 area images; native code coverage
does not itself remove their data loads. See [AOT overlays](AOT_OVERLAYS.md).

## Options and their fit

| Approach | Assessment against the requested experience |
| --- | --- |
| Cache the raw disc in host RAM | Removes physical host I/O, but the guest still waits for CD events and loader phases. Useful infrastructure; insufficient alone. |
| Pre-decode all GAM files and retain ordinary assets | Proven feasible here at a modest host-memory cost. Recommended foundation. Still needs scene installation with normal audio timing. |
| Replace only the decompressor | Can remove decode work. Leaves CD waits, cooperative phase waits, transfers, initialization, and loading presentation. A component, not the full solution. |
| Replace file reads with immediate copies | More direct than emulated-CD acceleration, but completion must match the game's queue/consumer contract. Still leaves later phases. Test only within a defined transition transaction. |
| Prepare neighboring areas during gameplay | Conditional second step only if destination initialization remains expensive with all immutable assets already resident. Prepare reachable neighbors' runtime resources in isolated storage and activate only the chosen destination. |
| Replace Tomba's discrete transition workflow | Recommended route to the requested result. Consume prepared assets, initialize from current gameplay state, and publish a completed destination without entering the loading presentation. Requires reverse engineering and live validation. |
| Broader native scene/resource system | Greatest control over resource ownership and concurrent preparation; substantially larger than a constrained spike. Escalate only if the narrow adapter cannot safely install a scene. |
| Full native audio or retained sound-bank service | No demonstrated need in this spike. Consider only if the normal-speed prototype exposes an audio regression requiring it. |
| Expanded guest RAM / keep several areas resident | Host storage is easy; fixed guest pointers, shared overlay addresses, VRAM and SPU address reuse remain. Expanding RAM alone cannot make two active scenes safe. |
| Whole-machine snapshots or speculative second instance | Restore/merge risks for inventory, events, RNG, input, and audio. Prior snapshot proposal was rejected; do not revive it for this spike. |
| Hide pigs, hold a frame, or extend a fade | Conceals work while leaving a wait or blackout. Fails the stated experience as a standalone solution. |
| Turbo, instant CD divisors, skipped yields, dropped audio | Outside the owner's requested solution; prior work also found correctness failures in several of these paths. |

The useful analogy to decomp ports is the separation of prepared asset archives
from gameplay execution. Ship of Harkinian, for example, generates OTR/O2R data
from the user's game before play. That is an architectural precedent, not proof
of Tomba's transition behavior. See the [Shipwright instructions](https://github.com/HarbourMasters/Shipwright/blob/develop/README.md?plain=1).

Older framework notes claimed asset transformation was unavailable to a recomp
without source-level knowledge and called a state cache the only near-zero
option. Those are not constraints on this experiment: recovering a concrete
asset format has now enabled offline preparation. The historical evidence of
texture corruption and scheduler failures still matters.

## Implementation boundary

The default-off Tomba mod owns its format, descriptor interpretation,
transition state machine and address/byte guards. It prepares the
asset archive during activation, making required bytes resident before the
player can initiate transitions. Cold-cache work belongs before gameplay,
never at the first door or the Load Game confirmation.

The lifecycle is: prepare immutable data, construct the destination
from the player's current state, commit resources at an established safe game
boundary, and resume normal gameplay. Preparation must stay outside live guest
RAM until the previous consumers have finished. A global write-set replay or
setting the completion flag early does not establish that boundary.

Keep the entire prepared immutable asset set in host memory as the first
approach. Measure destination initialization separately. If it fits the normal
presentation interval, neighboring-area preparation adds no needed benefit.
If initialization still causes a pause, prepare the current area's reachable
neighbors while gameplay continues, subject to measured memory and frame costs.
Prepared neighbors remain inactive: no enemy simulation, script execution, or
event progression before entry. Revalidate state-dependent setup at handoff so
inventory or event changes cannot leave a stale prepared destination. Warps and
menu-selected destinations need their own preparation triggers if this second
step becomes necessary. This changes resource residency; it does not require
merging the game's area logic into one active world.

The framework supplies `psx_mod_read_disc_file`, which reads
original files with active sector mods applied without changing guest CD state.
It is limited to emulation-thread callbacks; it is not an asynchronous preload
service. Existing guest-memory allocation, code-write invalidation, and the
mod catalog are also available. The offline probe currently accepts only the
exact unmodified supported disc. A shipping archive key must additionally
include codec version and active asset-mod identity, with invalidation on change.

The `psx_mod_register_function_entry_plugin` callback returns void. The
generator emits the callback and then continues the original function body.
Changing `cpu->pc` inside that callback is not a proven replacement mechanism.
A true replacement needs an explicit dispatch/return contract or a carefully
guarded game-owned patch using existing invalidation machinery. Generated CPS
continuations, overlay identity, and interpreter/native paths all need coverage.
The implementation uses the existing dispatch hook instead; no framework
changes or new hook API were required.

Reusable pieces, if justified later, are a content-addressed prepared-asset
store, host preparation jobs, a validated function-replacement contract, and
transition/audio telemetry. Tomba's addresses and resource semantics stay in
the game repo. A generic loader is not a prerequisite for demonstrating this.

## Audio and validation gates

The reported historical stuttering occurred with turbo fast-loading. The goal
here is to remove loading work while audio and gameplay run at normal speed.
Preserve the game's intended music changes, fades, and stops. Do not accelerate
the machine or discard audio buffers to shorten a transition.

The runtime uses the existing SPU write path and retail sound-bank registration.
The music-change reverb clear also installs its real bytes synchronously. The
original `0x80076400` routine was executed against modeled completed DMA jobs
and compared with the compiled native transfer body in 40 cases: all ten
reverb modes, zero and patterned source buffers, and two poisoned destinations.
All 512 KiB of sound RAM and the transfer globals/registers matched. Some modes
round their last transfer beyond the end of sound RAM and wrap; the native
path preserves those writes. This oracle proves transfer contents/state, not
audio timing. Allocation checks and the caller's reverb disable/enable remain
retail operations.
The observed transition run has clean audio output counters. Further PCM and
route checks remain necessary; a new mixer or continuous-music system is not
a prerequisite for the loading spike.

The bounded runtime gate uses menu Load Game and a walked village round trip.
Instrument the transition trigger, descriptor queue,
last old-scene frame, first complete destination frame, initialization, audio
commands, and host audio underruns. The existing load transition ring observes
CD/load/turbo edges; it does not prove semantic scene readiness.

Acceptance requires zero loading UI frames, zero load-induced black/held frames,
no missing first-frame textures or actors, preserved current inventory/events,
normal-rate gameplay/audio, and no new audio stuttering. Aim to fit destination
commit into one normal presentation interval (about 16.7 ms at 60 Hz); measure
it instead of assuming that memcpy is free. Test cold launch as well as warm
repeats. A fallback to ordinary loading is safe during development but does not
count as passing the seamless gate.

If that gate succeeds, expand coverage to every discovered load caller: new
game, menu reload, normal exits both ways, warps, death/continue, event variants,
and transitions adjoining movies. Exercise returning after changing inventory
or events, and repeat with supported renderers and asset mods. This spike does
not claim that asset enumeration establishes whole-game transition coverage.

Stop the narrow implementation if it still needs yield suppression, exposes
partly installed assets, or introduces an unresolved audio regression. Report the
specific missing ownership/initialization contract and price a larger native
replacement, rather than shipping concealment as seamless loading.

## Reproduce the offline experiment

Use Python 3.11 or newer. The game worktree's submodules need not be initialized
for this probe if an existing checkout at the recorded framework pin is passed.
The ordinary unit tests have no external dependencies:

```text
python -m unittest discover -s tests -p test_seamless_asset_probe.py
python -m pip install --target build-seamless/deps unicorn==2.1.4
```

Add `build-seamless/deps` to `PYTHONPATH` for the oracle run, then substitute the
owner's local paths in this command:

```text
python tools/seamless_asset_probe.py --disc-bin "PATH/Tomba! (USA).bin" --framework-root "PATH/psxrecomp" --report build-seamless/asset-report.json --extract-dir build-seamless/assets --oracle
```

Omit `--extract-dir` to measure without retaining blobs. Omit `--oracle` only
for an inventory run; it must not be reported as original-decoder validation.
Both generated assets and the local dependency installation are ignored by Git.
The probe never launches Tomba or modifies a save, disc, or Ghidra database.

The following checks are developer-only; players do not run Python or compile
these tools. Build an independent local pack with `tools/seamless_pack.py`,
then set `TOMBA_SEAMLESS_CACHE` to an isolated test directory and leave
`TOMBA_SEAMLESS_PACK` unset. Run `tomba-seamless-prepare-tests` with the pack
path as its sole argument. It checks full-pack equality and failed regeneration
preserving the prior cache. This fixture is not a CTest dependency because it
contains the owner's original disc data.

Build target `tomba-seamless-reverb-fixture` and run the reverb byte oracle:

```text
python tools/seamless_reverb_probe.py --exe disc/SCUS_942.36 --native-library BUILD/libtomba-seamless-reverb-fixture.dll
```

Use the platform's shared-library suffix outside Windows. The oracle requires
the local Unicorn installation on `PYTHONPATH` and the exact supported original
executable. Its DMA boundary model completes the real requested transfers;
it makes no claim about an entire SPU or BIOS emulation.

Historical evidence consulted: central issue `beads-eio.4.7` (August save-load
measurements and rejected snapshot proposal), the pinned framework's
`docs/LOAD_TIME_ZERO.md`, `docs/ENHANCEMENTS.md`, `runtime/include/mod_plugins.h`,
`runtime/src/mod_runtime.cpp`, and `recompiler/src/code_generator.cpp`. The old
roughly eight-second baseline is historical, not a new measurement on this pin.
