# Engine notes

What we learned about Wizardry: Dimguil (SLPS-02691 Rev 1) while translating it, beyond
Remisse's `Findings.md`. Addresses are RAM unless a file is named. Commit messages carry
more of the detail behind each item.

## Loading files

- The executable holds four tables of file locations (MSF + sector count); a loader call
  takes (destination, index, table). `scripts/gametext.py --files` lists them, and
  `scripts/relocate.py` moves files that outgrow their sectors and patches the tables.
- A file may only grow as far as its load buffer allows. Limits checked so far, all in
  `relocate.py`'s `MAX_SECTORS`:

| File | Loads to | Limit | What follows |
|---|---|---|---|
| SISETU.OBJ | 0x801d8c00 | 14 sectors | live data at 0x801e0200 |
| I_NAME_E.OBJ / I_NAME_J.OBJ | 0x801d1000 | 12 sectors | FIGHTMSG.OBJ, resident at 0x801d7000 |
| FIGHTMSG.OBJ | 0x801d7000 | 3 sectors (unchanged) | SISETU.OBJ at 0x801d8c00 |
| NPC_MES1-5.OBJ | 0x801a0400 | 32 sectors | shared staging area (wall textures, portraits) |

- NPC_MES files load when a party is met, after the portrait TIM has gone to VRAM through
  the same buffer. The portrait uploader (0x8001d93c) is called again mid-conversation
  with 0x801a0400, finds no TIM magic there and does nothing, in the original too.
- String offsets in the text files are 16-bit, so no text file can pass 64 KB.
- Save states hold loaded files. After a build that changes text, or moves a file, old
  states show stale text or read the wrong sectors; regenerate them (`mkstates.py`).

## Text printer

- One printer (reader at 0x8001e0c0) draws dialogue, battle and event text. Codes below
  0xd8 are English glyphs and digraphs, priced by the VWF table at 0x80060e97.
- Glyph 0xb6 is `"` in the English font but the Japanese voicing mark (゛) to the
  printer, which merges it into a preceding kana. Several digraph codes double as kana
  (`y ` is フ), so a mid-line `"` after them prints as a Japanese glyph. Only a `"` that
  opens a line is safe; inner quotes are single quotes. `npcfit.py` checks this.
- The dungeon NPC box is 288 px by 3 lines, pages split by `\n\r`.
- The battle box wraps at 24 glyph codes per line. An inserted name that won't fit moves
  to the next line, but plain text breaks wherever it hits 24, mid-word included, so
  battle lines break after the name. `fightfit.py` checks this.

## Battle

- Monster data sits in DATA02/M_DTnnn.BIN at 0x10280 (in RAM, 0xd0-byte records from
  0x8008a918). Each of up to three attacks has a u16 noun at +0xac/+0xb6/+0xc0 and a verb
  byte two bytes later.
- BATTLE.BIN adds 427 to the noun; if the result is 2000 or more it subtracts 2000 and
  sets a flag. The result indexes I_NAME_E.OBJ, whose strings 427-938 were never
  localised in the English-mode file: 428-557 mirror the item list, 558+ are natural
  attacks (claws, fangs, stinger). The verb indexes FIGHTMSG.OBJ.
- `battleshow.py` renders any template/verb/noun combination in the real battle box.
- NPC parties fight as monsters. The encounter loader (0x80021268) loads the enemy file
  as table 1 index id+0x2c; NPC parties use id 379+n, which is DATA02/NPTnn.BIN. Their
  member records sit at the end of the file in the monster layout, with katakana in the
  English name slots too. `nptnames.py` writes the patches in `binary/`, and `nptshow.py`
  forces a fight with any party to check the enemy panel.

## Card battle

See `scripts/cardref.py`'s header for the CMENU.BIN tables (passwords, Lv 1 templates,
EXP scale, Option bonuses, unit records) and `docs/cheats.md` for the card stock in RAM.
