# Wizardry: Dimguil English translation

An English translation patch for Wizardry: Dimguil, the 2000 PlayStation release
(SLPS-02691). It targets the Rev 1 disc only.

All the text a player can reach is in English now: the town, the castle and its menus,
the dungeon dialogue, combat, item and monster descriptions and the card game. It's a
beta. Much of the text is still being reviewed, and nobody has played it through to the
ending yet. See [ROADMAP.md](ROADMAP.md) for what's left.

The patch is on the
[Releases](https://github.com/satelliteoflove/dimguil-patcher/releases) page. It applies
to the Track 1 `.bin` of a redump-style Rev 1 set, and the readme in the zip has the
steps. If something looks wrong or breaks, please open an issue.

## Credits

This started as Remisse's [dimguil-patcher](https://github.com/remii7/dimguil-patcher),
which dumps and reinserts the game's text and adds variable-width font support.
[name removed] translated the event script and much of the menu, status and combat text,
and [name removed] edited it. Their work is still in here, and the git history keeps
Remisse's commits as they made them.

I picked it up from there and carried on with the rest of the translation and the
engine work it needed.

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
