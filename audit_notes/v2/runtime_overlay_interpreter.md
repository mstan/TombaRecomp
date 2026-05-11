# Audit: v2 runner runtime overlay interpreter

Source:
- `F:/Projects/psxrecomp-projects/psxrecomp/runner/src/runtime.c`

Read scope:
- Focused read of the MIPS overlay interpreter (`mips_exec_one`, `mips_interpret`).
- Focused read of `call_by_address` overlay dispatch handling.
- Focused read of nearby `runtime.log` overlay notes.

Findings:
- v2 treats addresses at and above `0x80098000` as runtime-loaded overlay code and executes them with a MIPS interpreter.
- The interpreter runs whole overlay control-flow chains locally: local branches, jumps, calls, and returns stay in the interpreter until control returns to compiled code or an invalid target.
- The opcode surface is broader than v4's current dirty-RAM interpreter: multiply/divide, unaligned loads/stores, COP2/GTE transfer/commands, LWC2/SWC2, syscall/break handling.
- Several later v2 overlay fixes are HLE guards or direct state injection. Those are not acceptable for v4 and were not carried over.

Useful salvage:
- The architectural distinction is useful: dynamic overlay code is not a tiny BIOS install stub, so interpreting exactly one basic block per dispatch causes extreme dispatch churn.
- The opcode inventory is useful as a checklist, but v4 should use its own runtime CPU/GTE helpers and ring-buffer diagnostics.

Decision:
- Do not import v2 code.
- Rework v4's dirty-RAM interpreter so local dirty-code control flow can stay in the interpreter for a bounded run, and expand the missing plain MIPS/GTE opcode surface using v4's existing helpers.
