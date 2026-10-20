# After the ending: the post-game, and no new game+

Read 2026-10-17 (Chris asked whether the game has a new game+): decompiled C in
`rips/re/decomp/`, raw disassembly of the clean binaries in `rips/clean/dimguil/` (a small
capstone disassembler, `rips/re/work/postgame/pgdis.py`, overlays at 0x800a1000), the repo docs, and Bartok's Trading Post walkthrough chapters
19-21 (`~/Documents/bartoks-trading-post/data/walkthrough/dim/`).

Labels: **[code]** read in the code; **[emu]** seen in the emulator; **[FAQ]** fan
sources or the walkthrough; **[inferred]** a reading not directly proven. Nothing here was
tested in the emulator when it was written, except the ending's end state: on the
Japanese disc the save is followed by the town logo over an empty party, then the bar
after circle (worktrees/vwffix stage D, 2026-10-17). **[emu]**

## Short answer

There is no new game+. Nothing carries into a fresh game, no clear flag changes one, and
there is no second loop. After the ending the game saves and drops you back in town with
the same characters, now titled, and you keep playing. The title (roster +0xc5 bit 0)
turns on a handful of small extras: Otaka, a hidden sound test, a 20th recruit, a
Fortune Teller topic, an MP refill at the King's, a few NPC lines. It also turns off the
golem route, the final boss and the mysterious man's warnings for that party. The real
post-game areas, the Priestess's Door, the Dragon's Cave and the Magic Amulet, are
gated on the RING OF MEDIUM's stat change, not on the ending.

## 1. What sets story_flags bit 31 (Dragon's Cave)

- The only write is MAZE `maze_prompt_result` (0x800befcc), prompt 0x19:
  `sw` at **0x800c0108** ORs 0x80000000 into 0x80079b44, then EVENTMES 239 ("It's a
  match. The door opens..."). A raw scan of MAZE for `-0x64bc` stores and the
  `globals.json` writer lists finds no other writer. **[code]**
- Prompt 0x19 comes from `square_examine` case 0x59 (decomp line ~1009, facing west):
  EVENTMES 241 if bit 31 is already set, else EVENTMES 240 and the prompt. That's the
  Priestess's Door, Training Maze B8 (area 0x10). **[code]**
- The test (0x800c0008-0x800c00e0) is on the one member picked (current party slot
  `0x8007e808`): race_align & 0x3f == 1 (Elf, any alignment), class_sex == 0x82 (female
  Priest), age_years == 18, level == 5, STR 5, INT 18, PIE 18, VIT 5, AGI 5, LUC 18.
  No title, ending, Demon's Statue or story flag is checked. **[code]**
- The six stats are exactly what item 0x142, RING OF MEDIUM, does: Item +0x0d effect
  0x2f sets stats to 5/18/18/5/5/18 (`equip_menu` JOUKA 0x800ccc94, decomp ~line 870; G-records.md
  line 161). Item record (SLPS 0x80052bf2 + 0x142*0x4c): class mask 0x4 (Priest),
  race mask 0x2 (Elf), flags04 0x17 (female only), specials 0x80 (cursed). **[code]**
- Bit 31 does two things: it shows the ninth Edge of Town icon (`edge_main` HAZURE
  0x800a1394, F-edge-save.md line 63), and it opens the B8 wall behind the door at
  floor load (MAZE 0x800a8f1c: area 0x10, square_flags[0x12a]). Behind it is the lift
  to Dragon's Cave B1 (walkthrough ch. 20, from the disc maps). **[code]**, **[FAQ]**
- Getting to B8: the Training Maze lift (`square_examine` case 7 and MAZE 0x800b2e8c)
  opens floors by which stones are set in the TABLET (0x800b7248 tests bits 3, 7, 0, 1,
  5, 2 in turn). Nothing there reads the title. **[code]** The walkthrough says the
  lowest stop needs every stone. **[FAQ]**
- So the answer is **neither the ending nor the Demon's Statue**. It needs the ring's
  power used on a level 5, age 18 female Elf Priest. The ring only exists after the
  final boss (MAZE 0x800c1070 case 0x2e gives item 0x142 after EVENTMES 234/298/299),
  so in practice it comes at the end of the story, but the title doesn't matter.
  **[code]** The Demon's Statue is only for the Dragon's Cave B3 pedestal (S56).

How players do it (walkthrough ch. 19): carry the ring into town, soft reset during the
King's speech, Continue, and the ring is still there with no title; equip it on the
Priest in the tavern, uncurse at Boltac's for 50,000 Gp. **[FAQ]** The code fits that:
`town_main` (JOUKA 0x800a2198, state 2, decomp ~line 704) strips the ring in RAM and goes
to state 45. `king_ending` only rebuilds the RAM save image (`town_redraw`, called
right after 0x800a57e8) after the titles and gold, so a reset before that point
Continues from the older image. **[inferred from code]** It probably also works without
the trick, with the Priest in the boss party: levels only rise at the inn, so she can stay
level 5, equip the ring in camp, and go home for the ending. Her stats stay set. **[inferred]**

## 2. What the ending writes

Entry: `town_main` state 2 finds item 0x142 on a returning member, deletes it,
`items_compact`, sets `town_state` 45 (`'-'`), and state 45 calls `king_ending`
(JOUKA 0x800a52cc). **[code]**

`king_ending` writes, in full (index.json writer list checked against the disassembly):

| What | Where | Note |
|---|---|---|
| roster +0xc5 (`char_flags`) \|= 1 for every party member | 0x800a5530 (state 0x0a) and again 0x800a55c4 (state 0x0f) | the title. Nothing else in the game sets bit 0. The MCARD debug dump at 0x800b3500 prints this byte as `C_FLAG`. |
| +1,000,000 Gp to the **first** party member only, capped at 0x7fffffff | 0x800a5600-0x800a5664 | loop breaks after the first member. Matches SISETU 322 (description-check.md line 345). |
| party disbanded: members 0x8007e812-17 = 0xff, count 0x8007e811 = 0, then the empty party copied back over its `parties[]` entry (0x8008f8c8..) | ~0x800a5680-0x800a57d4 | the characters are free in the tavern afterwards |
| 0x8008c4da = 1 | sb at 0x800a57e8 | see "clear flag" below |
| `roster_snapshot`, `party_snapshot`, `town_redraw` | 0x800a57e4.. | the redraw rebuilds the RAM save image and sets `ram_save_valid` |
| credits: WIZAR07.STR movie, TIM loads, scrolling credits until START (0x80079740 & 0x800) | 0x800a5800-0x800a5e70 | |
| `next_place` = 0xf8 | 0x800a5ea8 | main: game_state 0x32 (`save_screen`, MCARD 0x800ab3b0), then game_mode 3, back to town (MAIN 0x800114d8, decomp lines 300, 353, 376) |

It does **not** touch `story_flags`, `progress_bits`, `npc_flags`, `oneshot_flags`,
`npc_stage`, Boltac's stock or any encounter data. Everything else on the writer list is
UI, fade and sound state. **[code]**

### Every reader of the title bit (roster +0xc5 bit 0)

A raw scan of every module for `0xc5(reg)` loads and stores, with the false positives
(other structs, +0xc7 met_bits, combatant tables) dropped, plus `FUN_800cd980(0,0)`:

| Reader | Address | What the title does |
|---|---|---|
| `square_examine` case 0x21 (Shrine 2F altar) | MAZE 0x800bc2e4 | ring **or** title: EVENTMES 38 "You touch the altar, but nothing happens." No monolith prompt (EV 35), so no Fire Golem, so no golem route |
| `square_examine` case 0x5d (Area Z coffin) | MAZE 0x800bde64 | ring or title: EVENTMES 232 "The relief is silent". No EV 229 prompt, so no final boss |
| `square_arrive` case 0x68 | MAZE 0x800bb2b4 | the mysterious man's scene (talk 0x1a; NPC5 103-111) plays only if **nobody** is titled. Placed on f26 Area B, f34 Area D B1, f36 Area E, f43 Area Z (site map data) |
| map-sprite builder MAZE 0x800a5d50 via `FUN_800cd980(0,0)` | 0x800a6cec / 0x800cd9d4 | same scene's floor marker isn't drawn for a titled party |
| MAZE 0x800c46c8 (random-event placer, 17 callers, map entry paths) | 0x800c488c | **Otaka**: if `rand_upto(0x1e61) == 0x309` (1 in 7778) and a titled member is in the party and the area is 0-8 or 0x12-0x27 (the Field, the Shrine, Area X and Areas A-E; never the Training Maze 9-16, area 17, the Dragon's Cave 40-42 or Area Z 43, by the Kandi region table in B-camp.md; checked in the machine code at 0x800c48bc, 2026-10-19), puts event 0x7d (type 0x6f) on a random square. Type 0x6f (`square_arrive`) is EVENTMES 311 then 312 (count at 0x8008c4d9), the programmer's item handout. No map has a static 0x6f record |
| `tavern_table` (JOUKA 0x800aab28, decomp line ~84) | 0x800aad98 | **hidden sound test**: at the card table's menu, SELECT (menu_input 10) with config[5] == 1 (Music on, per engine-notes "Settings"), a titled member, and a member with portrait 0x0b (recruit 10, the musician who "wrote the tunes you hear in this tavern", SISETU 371; portraits are recruit + 1 in DATA06/701-720.DAT) goes to state 0x37, JOUKA 0x800addec: up/down picks track 0-39, circle plays it, cross goes back |
| `tavern_recruit` (0x800ab08c, line ~279) | 0x800ab9f4 | recruit 8 (SISETU 369, the failed ninja) joins the pool. The "N1 after clearing" in the June 2000 board post (E-town.md) |
| `fortune_teller` (0x800ac684, line ~147) | 0x800acc48 | topic 13, "The End" (SISETU 358 title, 344 text) |
| `king_audience` (0x800a4898, line ~65) | 0x800a4b08 | SISETU 325 and every member's spell points recalculated (0x800b9540). Checked first, so a titled party never gets 326 (10,000 Gp each), 327 or 328/329 |
| `talk_guy` (MCARD 0x800b5694, line ~681) | 0x800b6aa4 | with `progress_bits` & 0x200 (Area E reached): lines 1:274-280 about the title |
| `status_marks_draw` JOUKA 0x800d9f00 and its copies (MCARD 0x800b30e0, HAZURE 0x800bb8bc, MAZE 0x800e4a58) | 0x800d9fd0 etc. | an emblem (index 5) beside the name |
| `equip_menu` effect 0x2e (JOUKA 0x800cf2dc, MAZE 0x800dd1dc, HAZURE 0x800b2178) | | the BOOK OF MOVEMENT (item 0x133) shows a 13-character code, SISETU 630 "Words like these came into your mind", packing race, class, sex, alignment, stats, marks and the title bit (`<< 2` into 0x80086874) |

Writers that clear it: `training_create` (0x800b1c48), `book_of_movement`
(HAZURE 0x800ae088, the met_bits loop from index -1), the roster_compact copies.
There are two unused set/clear helpers at MAZE 0x800cd884 / 0x800cd900, with no jal
and no pointer to them. **[code]**

No reader is in BATTLE, CMAIN or CMENU, in encounter selection, Boltac's, the temple,
the inn or `training_class_change`. So the ending adds no monsters, encounter tables,
harder fights, shop stock or class changes. **[code]**

The golem route's other step, the Shadow Golem statue (`square_examine` case 0x29,
Underground B3), checks only the ring (EVENTMES 60), not the title. **[code]**

## 3. Content reachable only after the end

Gated in code on the ending (the title bit):
- Otaka's handout (very rare, see above).
- The tavern sound test (also needs recruit 10 and Music on).
- Recruit 8.
- Fortune Teller "The End".
- The King's MP refill line (SISETU 325).
- Guy's party's title lines (1:274-280).
- The status emblem and the title bit in the Book of Movement code.

Needs the RING OF MEDIUM, not the ending:
- The Priestess's Door (B8), then story bit 31, then the Dragon's Cave (three floors,
  areas 40-42, its own fixed fights, walkthrough ch. 21). Then, with the Demon's Statue,
  the Diamond Knight band and the MAGIC AMULET (EV 249-253, 300).

Not gated on either: the Training Maze. It needs the Tablet and stones. Its listing
under "After the ending" in event-map.md is convention, not code.

Taken away by the ending, for titled parties only: the Fire Golem altar, the final boss
coffin, the mysterious man's scenes. A party with no titled member and no ring can do
the golem route and the coffin again for another ring, another ending and another
1,000,000 Gp. **[code]**, matching the FAQ (event-map.md line 776; walkthrough ch. 19).

## 4. Any true NG+?

No. **[code]**
- **Clear-data flag:** 0x8008c4da is set to 1 by `king_ending`. It's saved and loaded
  as part of the 0x20-byte block at 0x8008c4d0 (save image +0x23d5, `town_redraw`,
  `save_write`, `save_read`), cleared at boot (MAIN 0x8001275c) and by
  `roster_send_home`. A scan of all eight binaries for its immediate (0xc4da) finds
  only the store. Nothing reads it, so it's a game-cleared marker that does nothing.
- **New Game:** `title_screen` (MAIN 0x8001744c) New Game just sets config 5-7 and
  game_mode 3. The resets (MAIN 0x80012a4c, 0x800124a8, 0x8001d570) read no clear data.
  Note that New Game itself doesn't reset the roster. The pad soft reset only rebuilds
  the default six (0x8001d570) on the quit-to-title path (0x80079c1c == 1). But the
  title offers Continue instead of New Game whenever `ram_save_valid` is set, and
  `town_redraw` sets it on every town redraw. So there's no practical way to start a
  fresh story with a cleared roster. **[inferred from code, not tried]**
- **Carryover:** the Book of Movement imports only from Gaiden III / IV (SISETU
  0x274-0x275). It starts the character at level 1 with 500 Gp and clears +0xc5. The
  in-game export code includes the title bit, presumably for a sequel that never came.
  **[inferred]** Whether Dimguil's own importer accepts a Dimguil code (as either game)
  isn't established, because the decoder hasn't been traced. Even if it did, the title
  bit wouldn't come back.
- **Second loop:** none. After the ending it's the save screen, then town, with the
  same world state.

## Follow-ups worth an emulator check

- The tavern sound test (titled member, recruit 10 in the party, Music on, SELECT at
  the card table). It isn't in any doc yet.
- Whether a Book of Movement code exported in Dimguil imports back (choose either game).
