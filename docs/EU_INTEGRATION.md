# USA and Europe builds

The root target builds **Tomba! (USA)**. The separate `eu/` target builds
**Tombi! (Europe)** using the shared framework, launcher and game-owned policies.
See [Releases](https://github.com/mstan/TombaRecomp/releases) for version changes
and downloads. Original discs, generated C, native caches and player data stay
local and ignored by Git.

## Supported discs

| Build | Required disc | Raw data-track SHA-1 |
| --- | --- | --- |
| USA | Tomba! (USA), SCUS-94236 | `c259ec7ff6ef4163913991f4e4db2eff71702818` |
| Europe SCES-01330 | Tombi! (Europe) (En,Fr,De,It,Nl) (Rev 1), SCES-01330 | `2505d958b4439d04844cadd3f968fc7432a48e00` |
| Europe SCES-01331 | Tombi! (Europe) (En,Es,Pt,Sv,Da) (Rev 1), SCES-01331 | `ec50074b6fd98f611bae11e3de68d6e76ffdd6d4` |

Both released European tracks are 492,370,032 bytes and use separate native
players. SCES-01331 Rev 1 passed sampled English/Spanish runtime qualification;
see the [EU2 build and QA guide](../eu2/README.md). The original SCES-01331 RC2
revision (492,306,528 bytes, SHA-1 `684dbf0ad03f872511046d40d3cc85b17d839dbf`)
retains a separate static profile and is not the released EU2 input.
EU1/EU2 denote language groups of the first game. A matching serial alone cannot
qualify a disc for guest-address hooks. Keep each region's Memory Cards separate.

## Build

Use Python 3.11+, initialized pinned submodules, CMake, Ninja, Git Bash and a
Windows Clang toolchain. `TOMBI_TOOLCHAIN_BIN` or `--toolchain-bin` selects its
bin directory. Keep temporary files, compiler caches and build outputs on the
project's bulk-output drive.

```powershell
python -I -B tools/build_regions.py --region both --plan
python -I -B tools/build_regions.py --region both --check
python -I -B tools/build_regions.py --region both --us-disc 'G:/owned/Tomba.cue' --eu-disc 'G:/owned/Tombi.cue' --jobs 3
```

`--region eu2` selects the new SCES-01331 target and accepts `--eu2-disc`.
`--region all` selects USA, EU1 and EU2; `both` retains its USA/EU1 meaning.
The combined European launcher is built separately by `europe/build.py` and
routes between its two serial-specific backends. See the EU2 guide above.

`--plan` writes nothing. `--check` verifies the selected disc hashes and tool
prerequisites without copying or building. A build stages verified copies in
ignored `disc/`, refuses conflicting inputs, redirects temporary/cache paths
and stops on the first failure. Raw BIN/IMG and single-track MODE2/2352 CUE
inputs are accepted under the same exact data-track checks.

The entry point builds shared emitters and OpenBIOS, then the selected native
executables and original-disc AOT caches. EU baseline codegen precedes overlay
compilation. USA output is under `build-regions/us/`; EU uses
`build-eu-prototype`, `build-eu-seamless` and `build-eu-release-final`.

EU AOT defaults to the audited `opening` inventory. `--eu-aot-scope full` is
experimental: later-area recipes currently fail the generated-instruction
safety audit. Failed modules are never staged. Native compilation and byte
provenance do not establish complete gameplay execution coverage.

## Package

```powershell
python -I -B tools/package_regions.py --region all
```

`--us-build`/`--us-aot` and the EU counterparts select other build workspaces.
For repeated US AOT builds, select the exact `disc-aot-*` attempt containing
`audit.json`. The packager checks the cache tag against the packaged config,
rejects private debug/differential builds, filters developer mods, stages the
pinned fallback toolchain, scans for private data, and creates regional Windows
ZIPs with SHA-256 sidecars. It does not publish or launch.

Both catalogs omit CD Speed, host-paced Fast Loading and retired frame
blending. Widescreen remains optional and initially selects Fit to Window;
Seamless Loading remains enabled by default. See [Widescreen](WIDESCREEN.md)
for renderer and guest-hook contracts.

## Sampled QA

Build a separate private debug/differential executable for automation:

```powershell
python -I -B eu/build_release.py --debug-tools --geometry-validation --build-dir build-eu-qa/native
python -I -B eu/tests/test_sampled_gameplay.py --view Fit --name widescreen-fit
python -I -B eu/tests/test_sampled_gameplay.py --view 21:9 --languages en --name widescreen-fixed
python -I -B eu/tests/test_sampled_gameplay.py --view off --languages en --name widescreen-stock
```

The sampler uses fresh private cards and muted host audio, changes language,
checks MAIN identity, applies ordinary walk/jump inputs, and requires native
module loads and dispatches with runtime compilation disabled. Resize checks
cover native 4:3, widescreen choices, the 34:9 cap, HUD anchors and real margin
content. Original geometry comparisons use isolated reference state.

Retained evidence:

- `audit_notes/tombi-eu-integration-20261021.json`: loader/native execution and
  English/German samples.
- `audit_notes/tombi-widescreen-20261021.json`: USA/EU adaptive presentation,
  fixed/disabled cases and 2,400 EU differential geometry batches.
- `audit_notes/tombi-dual-release-20261021.json`: clean ZIPs, privacy/import
  audits, stripped native-module checks and relocated exact-package boot.

The shipped EU cache contains 66 audited native pairs from 54 opening/support
recipes, with 15,440 original-byte guards; later code retains fallback. USA
contains 176 pairs from 25 configured recipes, with 8,191 guards. These counts
are provenance/coverage evidence, not a full native-execution guarantee.

Owner EU playtesting reported the integrated build plays well. Campaign-wide
Widescreen content, full EU AOT expansion, an integrated-build native Memory
Card save/full-exit/restart/load roundtrip and other host packaging remain
follow-ups. Do not turn this into an exhaustive five-language runtime matrix.
Private debug/reference binaries are not redistribution packages.


SCES-01331 builds also accept the En/Es/Pt/Sv/Da **Rev 1** track (SHA-1
`ec50074b6fd98f611bae11e3de68d6e76ffdd6d4`). `--eu2-disc` selects the exact
revision automatically; `--eu2-revision rev1 --plan` previews its commands.
Each build and native cache binds one revision. See the [EU2 guide](../eu2/README.md)
for both original inputs, contracts and the bounded EN/ES runtime sample.

Cover gallery, dashboard quick controls and SCES-01331 language confirmation:
see [European launcher additions](regional/README.md).
