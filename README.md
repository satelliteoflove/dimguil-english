# Wizardry: Dimguil English translation

An English translation patch for Wizardry: Dimguil, the 2000 PlayStation release
(SLPS-02691). It targets the Rev 1 disc only.

Every line of text is, technically, translated into English. This work was done
largely by a machine. The immediate result is that the game can be played and
(hopefully) completed at this time, including the card game. All translated text is
currently undergoing a meticulous quality pass to account for the expected results of
machine translation. A full playthrough on this build hasn't been done yet. It is
reasonable to expect that game saves will break as the patch is developed. There be
dragons. See [ROADMAP.md](ROADMAP.md) for what's left.

## Origins

This project is built on Remisse's
[dimguil-patcher](https://github.com/remii7/dimguil-patcher): the text dumper and
inserter, the text compression and the variable-width font. No LLMs were used in
writing Remisse's original code. Remisse had no role in this project's development, and
the original team does not endorse it.

Everything added since, including the whole translation, is my own work, done with the
help of Claude, an AI model.

## Building it yourself

See [docs/building.md](docs/building.md). You'll need your own Rev 1 disc image.

## What's where

- `translations/` holds the English text, one JSON file per game file. `binary/` holds
  patches to non-text data (NPC party names).
- `asm/` has the armips patches: Remisse's VWF hacks in `vwf.asm`, and the rest built
  on top of them.
- `src/` is Remisse's Kotlin dumper and encoder. `sections.json` tells it where the
  text sits in each file, and `tables/` has the character tables.
- `graphics/` has the edited font sheet.
- `scripts/` has the build, a headless emulator harness built on the Beetle PSX
  libretro core (`emu.py`), and the checkers and viewers used while translating.
- `docs/` has notes on the engine, the translation and the review work, plus
  Remisse's original notes in `findings.md`.

The text is compressed by packing common letter pairs into single bytes. If you add or
change a digraph, the font sheet, `tables/compression.tbl` and the VWF width table in
`asm/vwf.asm` all have to agree.

## License

GPL-3.0, the same as the original project. See [LICENSE](LICENSE).
