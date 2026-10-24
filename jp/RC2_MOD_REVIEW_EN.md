# Japan RC2: shared implementations and verified regional bindings

Reference: byte-checked original SLPS-01144 boot SHA-1
`07d577698ad31ec1a69b9d7b80a7c3f90b650888`, original disc SHA-256
`fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b`.
The local psx_tomba reference is pinned at
`fb3b36715f6966c099be95564c155bd842003b76`; original instructions are decisive.

| Feature | Reuse category | RC2 result |
| --- | --- | --- |
| Seamless Loading | Shared EU loader with a checked regional profile | Implemented, optional/default off pending regular transition acceptance |
| FMV Skip | Shared plugin unchanged, Japanese table/descriptor bindings | Implemented, optional/default off |
| PGXP | Existing framework implementation | Retained; combined ordinary-gameplay counters pass |
| Controller, audio, Fast Forward, cards | Shared runtime | Retained; no regional replacement |
| HD textures / bezel | Shared renderer and installer | Retained RC1 tests; matching external assets required |
| Geometry Optimization | Shared HLE ideas, different packet ABI | Hidden; larger adaptation and differential tests needed |
| Hybrid Controller | Shared policy, different original input driver | Hidden; adapter and original-menu/analog acceptance needed |
| Widescreen | Shared renderer, unverified Japanese camera/HUD contracts | Hidden; no new renderer work begun |

## Seamless profile

`jp/seamless_profile.py` generates a regional derivative of the existing
`eu/seamless/loader.c`, not a second maintained loader. The generator pins its
source hash and checks original calls, instruction words and code hashes.

| Role | Verified Japanese binding |
| --- | --- |
| openTask / sleepTask | 0x80016740 / 0x800167C0 |
| gameTask / sole root sleep continuation | 0x80019608 / 0x80019728 |
| cosmetic loading animation / render | 0x8001B808 / 0x80043A90 |
| original CD task | 0x8001F574 |
| GPU callback continuation / DrawSync | 0x8001FA48 / 0x8005BA48 |
| WVD continuations | 0x8001FB5C / 0x8001FC98 / 0x8001FCB8 |
| request queue / BCD file table | 0x800A0F70 / 0x800725F4 |
| transfer scratch / alternate arena | 0x800A5B28 / 0x800B58F8 |
| error bytes / game data | 0x8009F0F0 / 0x8009E508 |
| VAB header/body tables / bank table | 0x8009EF98 / 0x8009EE98 / 0x80072398 |
| decoder final bit/flags | 0x8009DBD0 / 0x8009DBD4 |
| protected resident MAIN end | 0x8009E000 |

The original BCD table has 1047 slots, two unused. Japan has resident load
descriptors, so the western language-specific SYS/GP-list write exception is
removed. All MAIN protection, destination overlap, VRAM, WVD, code identity and
whole-batch preflight guards remain. Unsupported batches return to the original
CD task before partial installation. The diagnostic forced-CD mode is private
and demonstrates actual initial gameplay with zero installed resident batches.

Only same-frame completed-batch loading yields may be skipped. Script waits,
opening sequences, ordinary gameplay yields, memory-card transfers, original
quests and NTSC timing are not modified. STR movies keep original streaming.
1054 resources are prepared on first activation; 638 GAM decoder results and
their final bit state were compared against original Japanese MIPS.

New Game installs 13 first-area files plus a WSS batch; Japanese dialogs,
controller movement/jump/land and generated audio pass. A normal saved-game
area roundtrip remains manual: the bounded original-menu navigation did not
reliably reach the owner's save. No artificial state was used. OFF is retained
as the fresh-install default until this acceptance is complete.

## FMV profile

`jp/fmv_profile.py` validates all 22 original descriptor pointers at 0x80071D70,
their file-table identities and actual STR sector headers. Unlike the western
byte-index mapping, Japan uses pointers to 20-byte load records. The original
frame-total table at 0x80071D3C matches the common plugin's movie ordering;
movie ID is the original byte 0x1F8001CD. The original end comparison around
0x8001D454 and state-3/CdMix teardown are checked, not replaced with US addresses.
Some STR trailers intentionally extend beyond the original table's totals.

The shared `src/mods/tomba_skip_fmv_plugin.c` is unchanged. Default OFF and the
existing Any-percent semantics are preserved. 22 isolated original-MIPS leaf
fixtures pass for ON/OFF behavior and table isolation; normal New Game also
passes with the active plugin. Later-film quest continuity is manual acceptance.

## Concrete deferred contracts

Geometry: Japanese neighborhoods emit packet lengths 7 at 0x80022B34 and 9 at
0x80022D04. Western HLE entry points 0x80024EEC, 0x800251C0 and 0x800253C8
emit lengths 9, 9 and 12 and have different input/packet contracts. These are
observations, not approved Japanese entry mappings. Establish full Japanese
entry/end boundaries, argument/register effects, packet layout, returns and
unsupported-case equivalence before registering shared HLE implementations.

Hybrid: Japanese vblank calls legacy PadRead at 0x80016994 -> 0x80064B74,
using BIOS B0:0x16 through 0x80064BBC and buffer 0x8009DDB0. The western
PadInitDirect/PadStartCom analog-report parser is not the same contract.
An actual driver adapter and original-title/menu/analog tests are needed.

Widescreen: qualify Japanese projection/camera state, sprite transforms,
culling, HUD exclusions and geometry packet paths against the common renderer.
No complete small hook set is available; blindly transferring EU addresses
would be unsafe. Normal renderer and original Japanese layouts remain active.

## Evidence and maintenance

24 native pairs / 7277 range rows were regenerated for RC2's four entry filters,
then audited against original bytes and current ABI. Full static coverage is
not claimed; interpreter fallback is retained. EU/USA binaries are copied
unchanged from their previously audited pristine stages. No common launcher,
official Browse function, original ROM or real card is changed by this work.
See TEST_REPORT.json for current vs retained evidence and MANUAL_TESTS_DE.md
for the remaining owner acceptance.
