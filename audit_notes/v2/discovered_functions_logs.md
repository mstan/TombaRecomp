# v2 discovered function logs audit

Source files:
- `F:/Projects/psxrecomp-projects/psxrecomp/tools/interp/discovered_functions.log`
- `F:/Projects/psxrecomp-projects/psxrecomp/tools/interp/discovered_functions_live.log`

Status: data-only salvage source. The logs record entry points discovered by
the old v2 dynamic/interpreter tooling, not a trusted static manifest.

Findings:
- I did not find a v2 `game.toml`, `game.cfg`, or other per-game seed config
  carrying these entries.
- Both discovered-function logs contain 612 parseable unique Tomba-range
  addresses.
- The current v4 generated Tomba dispatch table contains 2904 game dispatch
  cases.
- Comparing the v2 log union against current v4 dispatch leaves 273 v2-only
  addresses.
- Several sampled v2-only addresses are real executable code, but not all are
  clean function entries. Examples include mid-function blocks and epilogues,
  so bulk promotion would likely fragment current function boundaries.

Preserved artifact:
- `seeds/v2_discovered_funcs_candidates.txt`

Use policy:
- Do not wire the candidate file into `game.toml`.
- Promote addresses to `seeds/ghidra_funcs.txt` only after a runtime dispatch
  miss, a focused Ghidra audit, or another proof artifact establishes that the
  address is a real required entry point.
- Batch promotions should be bisected if they affect boot behavior.
