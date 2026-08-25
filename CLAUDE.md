# TombaRecomp Rules

## Inheritance

This project inherits, in order:

1. **The shared doctrine repo `recomp-ai-rules`** — system-agnostic recomp/debug
   discipline. Read `PRINCIPLES.md`, new `CHANGELOG.md` entries, and
   `PSX/PRINCIPLES.md` for this platform. It is a sibling checkout —
   `../recomp-ai-rules/` in the standard workspace layout, where `CLAUDE.md` at
   the workspace root carries the precedence chain.
2. **The framework constitution at `psxrecomp/CLAUDE.md`** — the `psxrecomp`
   submodule vendored in this repo.

Root wins: where the framework or this file conflicts with the doctrine repo,
the lower file is the bug.

## Additional project rules

- The v2 tree is the canonical salvage source, but it is **not trusted**. It is
  **not present on this host** — the audit notes in `audit_notes/v2/` record what
  was salvaged from it and where each piece came from, and those recorded source
  paths are history, not paths you can open. Re-point them if the v2 tree is ever
  restored.
- Every v2 file must receive an audit note before any idea from it is used.
- Audit notes are committed before implementation commits.
- Game binaries, Ghidra databases, memory cards, and build outputs are local
  only and must not be committed.
- `extras.cpp` is a smell. It may only contain tiny temporary glue with explicit
  user approval and must be removed once the framework has the proper feature.
