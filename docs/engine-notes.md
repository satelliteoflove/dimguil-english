# Engine notes

What we learned about Wizardry: Dimguil (SLPS-02691 Rev 1) while translating it, beyond
Remisse's notes in `findings.md`. Addresses are RAM unless a file is named. Commit messages carry
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
- EVENTMES.BIN (table 2 index 26) is 27,623 bytes in 14 sectors, so it can grow 1,049
  bytes in place (`extendByBytes` 1049) without moving. The event review pushed it 326
  over on 2026-10-03, and until 2026-10-04 the encoder silently dropped every event
  translation (build.sh only printed the ERROR). build.sh now stops on an encoder
  ERROR. Checked: the game's loader reads the whole grown file, tail included.
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
- The battle box wraps at 24 glyph codes per line. Messages are expanded by 0x8001dfc0
  into 0x8008b400; only the battle call (BATTLE.BIN 0x800d1e20) turns wrapping on. The
  original moves an inserted name that won't fit to the next line, but breaks plain text
  wherever it hits 24, mid-word included, and where that lands depends on the name
  lengths ("Jupiter sweeps Cuautori wi / th LANCE."). `asm/word_wrap.asm` adds a
  lookahead at each space (and each digraph ending in one), so words move whole.
  `fightfit.py` simulates it over every combination of name lengths.

## Text buffer

- Dialogue, event and castle strings are expanded whole (every page) by 0x8001dfc0 into
  a buffer at 0x8008b400 before printing. Nothing bounds it, and 16 bytes of live data
  sit at 0x8008b640, so a string that expands past byte 576 has that stretch overwritten:
  measured with filler strings, 557 bytes print whole, and at 625 bytes page 9 shows a
  run of zeros and loses the rest of the line. This is the "random cutoff" in long
  narrator lines in Remisse's notes. Our longest are SISETU 326 (445 bytes), EVENTMES 234
  (424) and NPC_MES4 151 (378). `textbuf.py` holds every string to 544 bytes, leaving
  room for inserted names, and the build stops if one is over.

## Glyph sprite layers

- Each glyph is drawn as a sprite from a pool ("layer"). A screen sets up four layers
  when it opens (0x800db3d0 in JOUKA calls 0x8001f150 per layer; 720 sprites in all;
  table at 0x8008b390: start, size). 0x8001f840 refuses a glyph once its layer is full,
  so text simply stops: there's no error and no wrap.
- Boltac's Trade screens put the shop name and the one-line caption in layer 1, sized 28.
  "Boltac's Trading Post" takes 14, so captions showed only 14 glyph codes ("Choose an
  item to un", "Which weapon i"); the Japanese name is 7. `asm/shop_caption_layer.asm`
  makes it 58, taking 30 from layer 0 (270 -> 240; its peak over every Trade flow is
  130). Measured peaks after the change: layer 1 at most 43.
- Other screens size layer 1 differently (30, 40, 70, 100, 154). They haven't all been
  checked for full layers.

## Spell bar

- Inspect Character > Cast Spell shows the highlighted spell's description (STATUS.OBJ
  420-503) in a one-line bar. It prints the first 30 glyph codes and drops the rest; the
  cut is by codes (digraphs count once), not pixels. Remisse's "about 40 characters" is
  this limit. Every current description fits (Wish is exactly 30); `spellfit.py` checks.
- Writing a test string into RAM while a description is on screen and then moving the
  cursor can show only the tail of the text. That's an artifact of editing RAM under a
  drawn string; normal cursor movement, fast or slow, draws correctly.

## Item catalog

- The catalog draws the item's picture, then the description below it, and clips the
  text at about y=220 with no scrolling. ITEM.DAT has 252 pictures at 152x108 (text
  starts at y=129, 7 lines of 13 px) and 55 at 152x152 for polearms, long staves,
  robes, cloaks and full armor (text starts 39 px lower, 4 lines). The Japanese under
  tall pictures never runs past 4 lines. `itemfit.py` checks every description against
  the right limit; found by Chris on the Emerald Robes, 2026-10-04.
- The pictures are stored normal-sized first, then tall, each set in item order, with
  picture 0 a "file not found" placeholder. Description k is item k up to 24 and item
  k+1 from 25 on: entry 24 holds two strings, the Battle Axe's, then after its {ff40} terminator the
  Nunchaka's (item 25). The game shows each on its own.
- Only JOUKA.BIN (the castle-town overlay, loaded at 0x800a1000) reads these pictures:
  the shop catalog and its detail screen. The card game has its own copies
  (CB/DAT/ITEM_S.DAT and ITEM_L.DAT, the same 252 + 55 split).
- 0x800de244: the item's picture entry has bit 0x8000 for tall; tall pictures load from
  sector 0x8dc + 12n, normal ones from 9n, through 0x800e3dcc. The a2 passed there
  (0x4c/0x36) is only the upload strip size. The upload takes width and height from
  the TIM header, so a shorter TIM displays cleanly.
- 0x800deb1c (JOUKA.BIN 0x3db1c): the description's y is a fixed base plus tall × 39,
  built as ((s3 << 2) + s3) << 3 − s3. `subu v0,zero,s3; andi v0,v0,N; nop; nop` sets
  the tall offset to N. The parchment ends at y=227; text starts at y=129 + offset, in
  13 px lines.
- Tested 2026-10-04 (emulator, six items): offset 26 with the pictures cut to 139 rows
  shows a full 5th line under tall pictures, no overlap, normal items unchanged.
- Chosen 2026-10-04: offset 30 (`asm/catalog_tall_text.asm`) and pictures cut to 143
  rows (`scripts/itempics.py`, run by build.sh): 16 trimmed, 11 moved up, 28 shrunk
  (1-9%). Each picture is a copy of the panel's parchment with the item on it, so only
  the item is moved or scaled and it goes back onto the bare parchment
  (`graphics/item_panel_bg.png`); scaling the whole picture misaligned the texture.

## Battle

- Monster data sits in DATA02/M_DTnnn.BIN at 0x10280 (in RAM, 0xd0-byte records from
  0x8008a918). Each of up to three attacks has a u16 noun at +0xac/+0xb6/+0xc0 and a verb
  byte two bytes later.
- BATTLE.BIN adds 427 to the noun; if the result is 2000 or more it subtracts 2000 and
  sets a flag. The result indexes I_NAME_E.OBJ, whose strings 427-938 were never
  localised in the English-mode file: 428-557 mirror the item list, 558+ are natural
  attacks (claws, fangs, stinger). The verb indexes FIGHTMSG.OBJ.
- In a battle, the current group's monster record is at 0x801b0680 (in
  rips/states/battle_wriggle.state).
- `battleshow.py` renders any template/verb/noun combination in the real battle box, with
  `--monster NAME` to try other name lengths.
- NPC parties fight as monsters. The encounter loader (0x80021268) loads the enemy file
  as table 1 index id+0x2c; NPC parties use id 379+n, which is DATA02/NPTnn.BIN. Their
  member records sit at the end of the file in the monster layout, with katakana in the
  English name slots too. `nptnames.py` writes the patches in `binary/`, and `nptshow.py`
  forces a fight with any party to check the enemy panel.

## Card battle

See `scripts/cardref.py`'s header for the CMENU.BIN tables (passwords, Lv 1 templates,
EXP scale, Option bonuses, unit records) and `docs/cheats.md` for the card stock in RAM.
