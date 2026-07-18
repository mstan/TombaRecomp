# AOT static-coverage recall — SCUS-94236

_How much of the played reference set did the play-free static extractor reproduce, and how much lies in compiled static code?_

- Static shard cache: `build-aot/cache/SCUS-94236/gcc/win-x64/cg5_e8484213`
- Static manifest entries: **2094**

- Base BIOS native dispatch entries: **1314**; relocated kernel body ranges: **37**
- Combined metrics below count both the play-free overlay cache and the separately generated, live-byte-guarded base BIOS.

## vs played vault (most complete needed-set)

- Manifest entries in the full-playthrough vault: **823**
- Discovered by static: **741** (**90.0%** entry-level recall)
- Covered by compiled static code ranges: **816** (**99.1%** code-range recall)
  - Code-range recall answers whether the played entry PC is in byte-guarded native code. Exact-entry recall is stricter manifest granularity; runtime fragment caches can contain one entry per instruction, so it substantially understates broad static shards.
- Byte-identical (entry+code_crc): **655** (**79.6%**) _(cg-version differences lower this vs entry-level)_
- **MISSED exact entries: 82**
- **TRUE CODE-RANGE GAPS: 7** played entry PCs outside all compiled static ranges

### Combined with base recompiled BIOS

- Exact native dispatch entries: **741** (**90.0%**)
- Covered by native code ranges: **819** (**99.5%**)
- **COMBINED CODE-RANGE GAPS: 4**

#### Combined gaps grouped by region

- region `0x800E7000`: 1 misses
  ```
  800E73C0
  ```
- region `0x80110000`: 1 misses
  ```
  80110E30
  ```
- region `0x80111000`: 2 misses
  ```
  80111BB4 80111BCC
  ```

### Code-range gaps grouped by overlay region

- region `0x80000000`: 3 misses
  ```
  80000CF0 80000DF8 80000E08
  ```
- region `0x800E7000`: 1 misses
  ```
  800E73C0
  ```
- region `0x80110000`: 1 misses
  ```
  80110E30
  ```
- region `0x80111000`: 2 misses
  ```
  80111BB4 80111BCC
  ```

## vs live capture history

- Sources: **latest capture**
- Dispatch entries exercised: **92**
- Discovered by static: **2** (**2.2%** entry-level recall)
- Covered by compiled static code ranges: **53** (**57.6%** code-range recall)
- Including base BIOS native code ranges: **90** (**97.8%**)
- **MISSED live: 90**
