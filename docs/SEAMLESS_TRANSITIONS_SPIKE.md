# Tomba seamless transitions feasibility spike

The target is a menu or area transition with no loading screen, load-induced
blackout, held image, or audio hiccup. This assessment recommends preparing all
ordinary assets before play, then implementing a Tomba-specific replacement for
the loading and transition workflow. Pre-decompression is feasible and has now
been tested against the original decoder. Seamless runtime transitions have
**not** been implemented or validated by this spike.

Game-specific code may remain entirely in TombaRecomp, as the owner clarified.
Generalizing the implementation is optional. The immediate next experiment
should cover one menu-to-area route and one round-trip area boundary. The owner
clarified that the audio concern is the stuttering heard with previous turbo
fast-loading. Keep normal audio timing and normal game-directed music changes;
continuous outgoing music across every boundary is not a separate requirement.

Baseline: Tomba `05d82b96d31c2bab59256095cdfec82ccd328310`, framework
`c68bf6e08568327d0c6816d083cf7d00875593f0`, UI
`e45e1f3062731abc188e351cad3608730b01fa12`. Worktree branch:
`spike/tomba-seamless-transitions-20261004`. Central tracking: `beads-eio.4.18`.

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
ready. The exact pig-screen entry/exit functions, every transition caller,
audio teardown policy, and a safe commit boundary remain to be traced live.

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

## Recommended implementation boundary

Start with a default-off Tomba mod owning its format, descriptor interpretation,
transition state machine and address/byte guards. Prepare the
asset archive during setup, and make required bytes resident before the player
can initiate transitions. Do not defer a cold-cache stall to the first door or
the Load Game confirmation.

The proposed lifecycle is: prepare immutable data, construct the destination
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

The current framework already supplies `psx_mod_read_disc_file`, which reads
original files with active sector mods applied without changing guest CD state.
It is limited to emulation-thread callbacks; it is not an asynchronous preload
service. Existing guest-memory allocation, code-write invalidation, and the
mod catalog are also available. The offline probe currently accepts only the
exact unmodified supported disc. A shipping archive key must additionally
include codec version and active asset-mod identity, with invalidation on change.

The current `psx_mod_register_function_entry_plugin` callback returns void. The
generator emits the callback and then continues the original function body.
Changing `cpu->pc` inside that callback is not a proven replacement mechanism.
A true replacement needs an explicit dispatch/return contract or a carefully
guarded game-owned patch using existing invalidation machinery. Generated CPS
continuations, overlay identity, and interpreter/native paths all need coverage.
Determine that concrete seam before choosing whether any framework change is
necessary; do not invent a hook API that does not exist.

Reusable pieces, if justified later, are a content-addressed prepared-asset
store, host preparation jobs, a validated function-replacement contract, and
transition/audio telemetry. Tomba's addresses and resource semantics stay in
the game repo. A generic loader is not a prerequisite for demonstrating this.

## Audio and validation gates

The reported historical stuttering occurred with turbo fast-loading. The goal
here is to remove loading work while audio and gameplay run at normal speed.
Preserve the game's intended music changes, fades, and stops. Do not accelerate
the machine or discard audio buffers to shorten a transition.

There is no observed sound-bank lifetime bug in this prototype: no runtime
replacement has been installed. Check audio during the first normal-speed
transition experiment. Investigate sequence commands or bank replacement only
if that experiment introduces a glitch; a new mixer or continuous-music system
is not a prerequisite for the loading spike.

The next bounded runtime gate should use menu Load Game into one known area and
a Village-to-neighbor-to-Village round trip. Confirm current supported saves
and the baseline first. Instrument the transition trigger, descriptor queue,
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

Historical evidence consulted: central issue `beads-eio.4.7` (August save-load
measurements and rejected snapshot proposal), the pinned framework's
`docs/LOAD_TIME_ZERO.md`, `docs/ENHANCEMENTS.md`, `runtime/include/mod_plugins.h`,
`runtime/src/mod_runtime.cpp`, and `recompiler/src/code_generator.cpp`. The old
roughly eight-second baseline is historical, not a new measurement on this pin.
