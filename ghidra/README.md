# Tomba! Ghidra project

The local `Tomba1.gpr`/`Tomba1.rep` database is intentionally ignored. The
portable human-authored work is stored in
`annotations/SCUS_942.36.annotations.json`.

## Source image

- File: `tomba/SCUS_942.36`
- MD5: `0b895b1ed84d5b1efcb574168e0be8ff`
- SHA-256: `c45cd788df40a540d8641dc9682007c80e6ab8a4bcdd0e4a4e2c14c5108aa10b`
- PS-X EXE load address: `0x80010000`
- PS-X EXE entry point: `0x8006b58c`
- Header size: `0x800`
- Loaded payload size: `0x88000`

## Recreate the database

Run Ghidra's `support/analyzeHeadless.bat` from the repository root:

```powershell
analyzeHeadless.bat ghidra Tomba1 `
  -import tomba/SCUS_942.36 `
  -loader BinaryLoader `
  -loader-baseAddr 0x80010000 `
  -loader-fileOffset 0x800 `
  -loader-length 0x88000 `
  -loader-blockName RAM `
  -processor MIPS:LE:32:default `
  -analysisTimeoutPerFile 600 `
  -max-cpu 8
```

Then apply `annotations/SCUS_942.36.annotations.json` with the headless
`GhidraAnnotationImporter`. Re-export with `GhidraAnnotationExporter` after
making annotation changes. Never commit the `.gpr` or `.rep` files.
