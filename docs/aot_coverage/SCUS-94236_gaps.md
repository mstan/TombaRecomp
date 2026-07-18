# AOT static-coverage recall — SCUS-94236

_How much of the played reference set did the play-free static extractor reproduce, and how much lies in compiled static code?_

- Disposable clean static shard cache: `SCUS-94236/gcc/win-x64/cg5_060368b2`
- Static manifest entries: **1594**

- Base BIOS native dispatch entries: **1314**; relocated kernel body ranges: **37**
- Combined metrics below count both the play-free overlay cache and the separately generated, live-byte-guarded base BIOS.

## vs played vault (most complete needed-set)

- Manifest entries in the full-playthrough vault: **823**
- Discovered by static: **639** (**77.6%** entry-level recall)
- Covered by compiled static code ranges: **820** (**99.6%** code-range recall)
  - Code-range recall answers whether the played entry PC is in byte-guarded native code. Exact-entry recall is stricter manifest granularity; runtime fragment caches can contain one entry per instruction, so it substantially understates broad static shards.
- Byte-identical (entry+code_crc): **566** (**68.8%**) _(cg-version differences lower this vs entry-level)_
- **MISSED exact entries: 184**
- **TRUE CODE-RANGE GAPS: 3** played entry PCs outside all compiled static ranges

### Combined with base recompiled BIOS

- Exact native dispatch entries: **639** (**77.6%**)
- Covered by native code ranges: **823** (**100.0%**)
- **COMBINED CODE-RANGE GAPS: 0**

#### Combined gaps grouped by region

- None.

### Code-range gaps grouped by overlay region

- region `0x80000000`: 3 misses
  ```
  80000CF0 80000DF8 80000E08
  ```

## vs live capture history

- Sources: **24 capture files**
- Dispatch entries exercised: **450**
- Discovered by static: **143** (**31.8%** entry-level recall)
- Covered by compiled static code ranges: **410** (**91.1%** code-range recall)
- Overlay-only true code-range gaps: **40**
- Including base BIOS native code ranges: **450** (**100.0%**)
- Combined true code-range gaps: **0**
- Exact-entry misses (diagnostic; may be interior fragments): **307**
