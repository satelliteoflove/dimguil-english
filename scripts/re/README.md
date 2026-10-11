# Code analysis tools

Headless Ghidra over the original disc's code. The map of the code and the workflow are
in `docs/code-map.md`; findings go in `docs/engine-notes.md`.

- `ghidra.py`: build, refresh, check, merge, where (see its docstring)
- `symbols/*.csv`: names, kinds, confidence, notes and types, one file per subsystem
- `types.h`: record layouts (Roster, PartyRec, ...), applied to typed globals
- `patchsites.py`: where asm/ patches change the code, by function
- `ghidra_scripts/`: the Java scripts ghidra.py runs (LoadOverlay, CleanOverlay,
  RecordLibrary, ApplySymbols, ExportModule; ReportProgram and DumpFunctions for checks)

Output, untracked, in `rips/re/`:

- `decomp/<MOD>/<addr>_<name>.c`: one decompiled function per file. The header lists its
  callers and any functions that take its address, then the symbol note.
- `decomp/<MOD>/index.json`: per function addr, name, end, size, callers, pointer_from,
  callees, reads, writes (data addresses; `reads` also holds addresses only taken)
- `xref.json`: every function keyed `MOD:addr`, with callers across modules
  (an overlay's calls into MAIN show up as MAIN callers)
- `globals.json`: every data address keyed `MOD:addr` (RAM for data outside the overlay
  window), with readers and writers across modules
- `ghidra/<MOD>/`: the Ghidra projects (open in the GUI with
  `~/tools/ghidra/ghidra_12.1.4_PUBLIC/ghidraRun`, JAVA_HOME as in ghidra.py)
- `logs/`
