# TombaRecomp

TombaRecomp is the Tomba! project for PSXRecomp v4. It is intentionally split
from the framework repo so game-specific generated code, seeds, audit notes,
and scripts do not become framework state.

## Current Status

- Tomba's PS-X EXE has been imported into Ghidra at base `0x80010000`.
- Header facts are confirmed: entry `0x8006B58C`, text size `0x88000`,
  stack base `0x801FFFF0`, no header BSS/data sections.
- BIOS thunk inventory lives in `seeds/tomba_bios_thunks.txt`.
- Prior v2 code is audit-only. Nothing is imported without a committed audit
  note and a v4-side reimplementation decision.

## Local Assets

Put local game assets under `tomba/`. This directory is ignored by Git.

Expected local names:

- `tomba/SCUS_942.36`
- `tomba/SCUS_942.36_no_header`
- `tomba/tomba.cue`
- `tomba/tomba.bin`

## Rules

- Use the real recompiled BIOS and real hardware simulation.
- Do not add HLE BIOS shims, stubs, fake events, or generated-file edits.
- Keep memory-card saves in `saves/`, also ignored by Git.
- Keep framework changes in `F:/Projects/psxrecomp-v4`.
