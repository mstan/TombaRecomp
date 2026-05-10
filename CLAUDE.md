# TombaRecomp Rules

This project inherits `F:/Projects/psxrecomp-v4/CLAUDE.md`.

Additional project rules:

- `F:/Projects/psxrecomp-projects/psxrecomp` is the canonical v2 salvage
  source, but it is not trusted.
- Every v2 file must receive an audit note before any idea from it is used.
- Audit notes are committed before implementation commits.
- Game binaries, Ghidra databases, memory cards, and build outputs are local
  only and must not be committed.
- `extras.cpp` is a smell. It may only contain tiny temporary glue with explicit
  user approval and must be removed once the framework has the proper feature.
