# B: the camp (MAZE overlay)

Analyst B, phase 2 of the code analysis, 2026-10-11. Scope: the camp the party opens in
the maze with Cross, and the menus under it: spells cast outside battle, item use,
identify, equip, give, drop, pool gold, reorganize, save, the settings screen and the
Decipher Ancient Script screen. Symbols are in `scripts/re/symbols/camp.csv`; the
decompiled C with those names applied is in `rips/re/decomp/MAZE/`.

How claims are marked:

- **confirmed (code)**: read in the decompile and, where the decompile flattened a switch or
  an if-chain, in the disassembly.
- **confirmed (emulator)**: seen in the headless harness (`scripts/emu.py`) from the test
  save, with button presses only and RAM reads. No test here used a RAM write.
- **inferred**: what the code most likely means, not checked further.

Spell and item names below are the English labels used in the translation. Spell ids are
the camp's own numbering (`camp_spell_id`), not the battle's. The in-game description is
given by its STATUS.OBJ string index, since the descriptions are what the translation shows.

## Opening the camp

`camp_main` 0x800ce564 runs while game_state is 3; main calls it every frame. Cross in the
maze opens it (confirmed, emulator: game_state went to 3 and five icons showed).
`camp_state` 0x80079669 picks the screen:

| camp_state | Screen |
|---|---|
| 1 | entry: writes the party's area, x, y and facing into each member's roster record |
| 3 | the icon row |
| 5 | the menu under the icons |
| 10 | Inspect Character (`camp_inspect` 0x800cf8dc) |
| 15 | Reorganize Party (`camp_reorganize` 0x800d8bcc) |
| 20 | Save Adventure (`camp_save` 0x800d903c) |
| 25 | Settings (`camp_settings` 0x800d9304) |
| 30 | Decipher Ancient Script (`camp_decipher` 0x800d9e60) |
| 35 | leave the camp |

Confirmed (code). The Decipher icon is only offered once `story_flags` bit 0x20000000 is
set (confirmed, code). That bit is set by MCARD 0x800d65c8, talk handler 3; which NPC
that is belongs to analyst C. With it unset the test save shows five icons, not six
(confirmed, emulator). The icon numbers come from a six-byte table at 0x800a1b78
(inferred).

`camp_main` also runs the "who takes it?" picker when an item is found with every pack
full; the item waits in DAT_80079be0 (confirmed, code). Giving it to a full pack goes
through `camp_drop` to make room.

main zeroes `camp_state` when a talk starts (confirmed, code), so a talk never resumes into
a half-open camp.

When the camp closes, `maze_exit_code` 0x800799a8 tells the maze what to do next: 0xfe
show Dumapic's map, 0xfd Loktofeit back to the castle, 0xfc Malor's teleport screen, 0xff
nothing (confirmed, code, for the writes; what main does with them is analyst A's area).

## Inspect Character

`camp_inspect` 0x800cf8dc: pick a member, then a menu of Cast Spell, Items, Pool Gold and
Back. L and R step to the next or previous member (`menu_cursor` 0x800cf7f8 returns 5 and
7 for them, 4 for confirm, 2 for cancel; inferred from the callers). Cast Spell is only
offered when the character knows any spell and their status is below 0x20 (confirmed,
code). That threshold lets afraid, confused, poisoned, asleep and KO'd characters cast in
camp, but not paralyzed, stoned, dead, ashed or lost ones; I haven't checked a KO'd caster
in the emulator.

Sub-screens keep their own step in `camp_sub_state` 0x80079964 (confirmed, RAM watch).

## Casting spells outside battle

`camp_cast_spell` 0x800d0514, with its step in `camp_spell_state` 0x800799e6:

1. Pick the realm (a row; it starts on the class's own book), then the level (1-7), then one
   of three spells on that level. Each spell's byte in `spell_camp_ok` 0x8005e2fc
   (realm × 0x15 + level × 3 + slot) says whether it's shown lit or greyed in the camp list
   (confirmed, code).
2. The chosen realm, level and slot are mapped to a camp spell id, or 0xff if the spell has
   no camp effect (confirmed, code). An 0xff spell prints SISETU 283 "That spell can't be
   cast." and **costs nothing** (confirmed, emulator: Halito, points unchanged).
3. If `nomagic_steps` 0x8007e83a is above 0, the spell prints SISETU 284 "Failed!" and
   **the point is spent** (confirmed, code). That counter is set to 232 when the party steps
   on a square whose word in 0x8005b9d0 is negative, and counts down one per step; the
   stepping side is analyst A's (0x800c5570).
4. Otherwise the point is spent and the spell runs. Spell points are per realm and level
   (Roster +0x5c + realm × 7 + level), as in the early Wizardry games (confirmed, emulator:
   Dumapic 4 → 3).

Two jump tables drive step 4: `camp_spell_select` 0x800a1b88 (26 entries: what happens when
spell N is chosen, a target picker or the effect at once) and `camp_spell_effect`
0x800a1bf0 (23 entries for ids 3-25: the effect on the chosen target). The decompile
flattens both switches; the cases below were read against the disassembly.

### The 26 camp spells

All confirmed (code) unless marked. "Healable" is `status_has(t, 0)`: not dead or ash, and
HP below max. HP gains are capped at max HP.

| id | Spell | Desc. (STATUS) | Camp effect |
|---|---|---|---|
| 0 | Dumapic | 422 "Map" | closes the camp and shows the map (exit 0xfe). Fails in areas 9-17 or when game_state is 0x12 |
| 1 | Litofeit | 431 "Float" | levitation, 1000 steps (0x8007e82e) |
| 2 | Malor | 438 "Teleport" | closes the camp to the teleport screen (exit 0xfc). Same failure rule as Dumapic |
| 3 | Dios | 441 "heals one ally 1-8 HP" | one ally, **2d4** (2-8) if healable |
| 4 | Kandi | 446 "Locate" | finds a party member's body; see below |
| 5 | Latumapic | 447 "reveals enemies" | identifies monsters, 2000 steps (0x8007e82c) |
| 6 | Dialko | 448 "cures paralysis" | clears paralysis (0x20) |
| 7 | Maporfic | 452 "party AC drops by 2; lasts long" | AC −2 for 1250 steps (0x8007e82a = 2, 0x8007e828 = 1250) |
| 8 | Latumofis | 451 "cures poison" | clears poison (0x04) and the poison counter (+0x78) |
| 9 | Dial | 450 "heals 2-16" | 2d8 if healable |
| 10 | Dialma | 453 "heals 3-24" | 3d8 if healable |
| 11 | Madi | 456 "full HP; cures all but death, ash" | full HP, then clears paralysis, poison, stone, afraid, KO, confused, sleep, each if present |
| 12 | Kadorto | 459 "raises the dead or ash, full HP" | raise from dead or ash with a chance; see below |
| 13 | Madial | 461 "party heals 30-60 HP" | every living member (status < 0x80) **10d5** (10-50) |
| 14 | Oslo | 462 "Might: a few steps" | attack boost level 2 (0x8007e830), 60 more steps (0x8007e832) |
| 15 | Maoslo | 470 "Might: lasts long" | attack boost level 2, 2500 steps |
| 16 | Fofic | 472 "party resists magic" | magic defence 10 (0x8007e834), 1250 steps (0x8007e836), only if none is running |
| 17 | Morfis | 476 "party ailments but death, stone" | clears status bits 0-5 (afraid, confused, poison, sleep, KO, paralysis) and poison for the party; stone stays |
| 18 | Kadios | 478 "fully heals one ally" | full HP if healable |
| 19 | Diomas | 484 "heals one ally 2-6 HP" | **3d2** (3-6) if healable |
| 20 | Diafic | 487 "finds secret doors" | 232 steps (0x8007e839) |
| 21 | (look ahead) | 488 "Scout" (inferred) | spends the point, then reports the square ahead: "Looks like rock.", "Open space stretches out." or "Unknown" (same test as the Scratch Hand, below) |
| 22 | Loktofeit | 496 "back to the castle; items lost" | every pack slot of every member is emptied, then the camp closes to the castle (exit 0xfd). Fails in areas 9-17 |
| 23 | Madios | 499 "heals the party 6-18 HP" | every living member 6d3 (6-18) |
| 24 | (appraise) | 498 "identifies an unknown item" | opens the caster's item list with "Whose item will you identify?" (SISETU 307) |
| 25 | Ihalon | 503 "special wish; stats change" | "Grant which effect?" (SISETU 286); see below |

The names in ids 21 and 24 are left as descriptions because I matched them to the STATUS
descriptions by behavior, not by reading the spell-name table (inferred). The other
id-to-name pairs follow the realm/level/slot order of the spell list (confirmed, code).

Effects that find nothing to do, such as Dios on a full-HP ally, print "What?" (state 40),
and **the point is still spent** (confirmed, emulator: Dios 5 → 4). "Spell cast" is state
45 (confirmed, emulator, Dumapic in area 0).

Dumapic, Malor and Loktofeit call `camp_spell_failed` 0x800e59a0 where they don't work. It
prints "Failed!" and the point is gone (confirmed, emulator: Dumapic in the Training Maze,
area 9, 4 → 3). The test is `cur_area − 9 > 8` as an unsigned byte, so areas 9-17 fail and
everything else works. Dumapic and Malor also fail when game_state is 0x12; Loktofeit
doesn't check it (confirmed, code; what game_state 0x12 is belongs to A or G).

### Kandi

`kandi_locate` 0x800d510c. The table `kandi_regions` 0x800a1c4c holds 12 regions of up to
nine area ids each (confirmed, code):

| Region | Areas | Answer (SISETU 0x10d + region) |
|---|---|---|
| 0 | 0 | Field |
| 1 | 1-4 | Shrine Interior |
| 2 | 5-8 | Underground Shrine |
| 3 | 18 | Area X |
| 4 | 19-22 | Area A |
| 5 | 23-27 | Area B |
| 6 | 28-31 | Area C |
| 7 | 32-34 | Area D |
| 8 | 36-39 | Area E |
| 9 | 9-16 | Training Maze |
| 10 | 40-42 | Area G |
| 11 | 43 | "Not in this area." (SISETU 280) |

If the target is in the caster's own region, Kandi gives the floor (not for the Field or
Area X), then N as 23 − y and E as x; otherwise it names the region (confirmed, code). Area
17 and area 35 aren't in any region (confirmed, code); what Kandi says for them I haven't
traced.

### Kadorto

Read from the disassembly at 0x800d2c18 (confirmed, code). For a target who is ash:

1. If Vitality is above 1, it drops by 0 or 1 (`rand_upto(1)`).
2. If Vitality is now below 4, the target is **Lost** (status 0x200).
3. Otherwise, a roll `rand_upto(80) < Vitality × 4` succeeds: status 0, full HP, and 1-52
   weeks of age added (a full 52 weeks carries into a year). A miss leaves them Lost.

For a dead target (not ash) it's the same, except that a failure turns them to **ash**
(status | 0x100, HP 0) rather than Lost. A Lost character is then deleted by
`remove_lost_members` 0x800e859c: the record's name is blanked, `roster_compact`
0x800e7ad0 closes the gap, and `party_drop_member` 0x800e7d4c renumbers every party
(confirmed, code for the first; the other two inferred).

### Ihalon

Lists the stats that are below the race's base + 10 (SISETU 287-292, "More Strength" and
so on; base stats at 0x8005e1e8, six per race), then the alignment changes the target
doesn't have (SISETU 293-295 "Turn Good", "Turn Neutral", "Turn Evil"). Alignment is
Roster +0x0a bits 6-7: 0 Good, 1 Neutral, 2 Evil (confirmed, code; Good seen on screen).
The steps after the choice (55 and 60) apply it; I haven't traced whether the level loss
the description promises happens there (inferred: not checked).

### Buff setters

`buff_litofeit` 0x800e82d0, `buff_latumapic` 0x800e8328 (also marks the groups on screen as
identified), `buff_maporfic` 0x800e83a4, `buff_oslo` 0x800e8450, `buff_maoslo` 0x800e8480,
`buff_fofic` 0x800e84ac. They write the current party block at 0x8007e810 (the PartyRec
copy), offsets +0x18 to +0x2a (confirmed, code). The per-step countdown is in 0x800c5570
(A's area). Oslo adds 60 steps to whatever is left; Maoslo sets 2500.

`dice` 0x800e8238: (N, S, B) rolls N dice of S sides (`rand_below(S) + 1` each) plus B
(confirmed, code).

`status_has` 0x800d5504 tests a condition by number: 0 healable, 1 poison 0x04, 2
paralysis 0x20, 3 stone 0x40, 4 dead 0x80, 5 ash 0x100, 6 afraid 0x01, 7 KO 0x10, 8
confused 0x02, 9 asleep 0x08 (confirmed, code; the bit names come from G's types.h).

## Items

`camp_items_menu` 0x800d579c: Identify, Use, Give, Equip, Drop (confirmed, emulator). The
labels are drawn by `items_menu_labels` 0x800e66a4, which greys Identify unless the
character is a Bishop (inferred from the flag it reads).

### Identify (Bishops)

`camp_identify` 0x800d5f24 (confirmed, code):

- A character whose status is 1 (afraid, alone) gets SISETU 239 and can't identify; status
  0x20 and above can't either.
- Chance = (Bishop's level − item's identify level + 1) × 20%, held to 5-75%. The item's
  identify level is Item +0x20. A roll `rand_upto(100)` below the chance succeeds.
- On a miss, a Bishop whose level is **at least twice** the item's identify level just
  fails. Below that, there's a (95 − chance)/4 percent chance of touching the item: the
  Bishop becomes afraid, and if the item is a cursed kind (Item +0x05 bit 0x80) it's
  equipped and cursed on them at once (0xa000), applying its negative regen.
- Two edge cases leave the state unchanged, so the roll repeats on the next frame: a Bishop
  whose level is exactly twice the item's, and a touch roll that lands exactly on the
  threshold. In effect those keep trying until something else happens (inferred from the
  code; not seen in play).
- **The Edge of Town's identify is different** (`edge_identify_item`, HAZURE 0x800a982c,
  2026-10-15). Same chance formula, but it only succeeds when the Bishop's level is at
  least the item's identify level; below that, every try fails, so the 5% floor never
  applies there. A miss never makes the Bishop afraid; only a cursed kind can still go on.
  **[code]** Found in play: Chris's level 14 Bishop missed 110 times on the Battle Drum
  (item 298, identify level 20). The camp identify above has no such gate, so in camp
  that item is 5% a try, with the touch risk.
- For an item that's already identified, the same screen shows its details. That screen
  prints SISETU 603 "Magic Item" and 604 "EVENT Item", which are untranslated English on
  the original disc.

### Use

`camp_use_item` 0x800d7150. The effects are hard-coded by item id; the item record only
supplies the break chance. All confirmed (code); ids from the item table at 0x80052bf2.

| Item (id) | Effect | Afterward |
|---|---|---|
| QUEEN'S WHIP (67), CAPE OF HIDE (257) | Dios: 2d4 to a healable ally | may break (10%, 20%) |
| ROD OF RAISING (70) | raises from dead with full HP, and from ash with full HP; no failure roll | breaks 100% (into id 6) |
| GOLDEN ROD (76), RING OF MADI (285) | full HP, clears paralysis, poison, stone | may break (40%, 25%) |
| RING OF HEALING (289) | full HP | may break (10%, into RING OF MADI) |
| POTION OF DIOS (241) | 2d4 | one dose used |
| POTION OF LATUMOFIS (243) | cures poison | one dose used |
| POTION OF DIALKO (250) | cures paralysis | one dose used |
| POTION OF MADI (271) | full HP, clears paralysis, poison, stone | one dose used |
| BOOK OF LIFE (291) | raises from dead and from ash, full HP, no failure roll | one charge used |
| STAFF OF CURING (98) | cures poison and paralysis for the whole party | may break (50%) |
| POTION OF FOFIC (251) | Fofic | one dose used |
| WINGED BOOTS (266) | Litofeit | may break (5%) |
| SCRATCH HAND (306) | reports the square ahead | may break (5%) |
| TABLET OF THE SUN (323) | loads a picture (file 0x1d) and shows the parts whose bit is set in the item's state byte | (inferred: the collected pieces) |
| RING OF JEWELS (246), AMULET OF GEM (295) | Dumapic's map | may break (40%, 0%) |
| RUBY SLIPPERS (286) | Loktofeit: every pack emptied, back to the castle | breaks 100% |
| RING OF MOVEMENT (189), CAPE OF HIDE' (299), MAGIC AMULET (315) | Malor's teleport | may break (18%, 40%, 0%) |

Anything else prints SISETU 316 "Nothing happened." Notes:

- Doses and charges are the item's state byte (Roster +0x34 + slot). The item is removed
  when it reaches 0 (confirmed, emulator: POTION OF DIOS 9 → 8).
- The healing items don't check whether there was anything to heal: a potion used on a
  full-HP ally is used up, "Used POTION OF DIOS." (confirmed, emulator). Spells say "What?"
  instead, but still spend the point.
- Breakage is `item_use_break` 0x800d8b04 (G's name): `rand_upto(99)` below Item +0x0e turns
  the item into the one at Item +0x10. Id 0 is BROKEN ITEM, which stays in the pack.
- The map, teleport and Loktofeit items break **before** the area check. So in areas 9-17
  (or game_state 0x12) they can break and then print "Failed!" (confirmed, code).
- The Scratch Hand reads the square ahead (map bytes at 0x8005d4d0, 24 wide; tile kinds at
  0x8005db90, five bytes each). At the map's edge, facing out, it says "Looks like rock."
  A tile kind other than 0x36 or 0x26 is "Open space stretches out." Kind 0x36 with
  sub-kind 4 is rock, and kinds 0x26 and 0x36 otherwise are "Unknown". One case, kind 0x36
  with sub-kind above 4, prints nothing (confirmed, code; what the kinds are is A's).

### Equip

`equip_menu` 0x800daa1c (G's name; a copy of JOUKA's). One prompt per slot, weapon,
off-hand, armor, helm, gloves, boots and accessory, with the prompt SISETU 229 + slot
("Choose a weapon." and on); `equip_slot_prompt` 0x800ddecc lists the candidates
(inferred). Cursed items stay on. At the end, each equipped item that has a special power
is offered: "Unleash its special power?" (confirmed, code).

`equip_curse_check` 0x800de34c equips one item (flag 0x2000). If the item's alignment bits
don't include the wearer's alignment, or its specials byte has bit 0x80, it becomes cursed
and equipped (0xa000) and the function returns 2 (confirmed, code). So putting on an item
of the wrong alignment curses it.

`stat_adjust` 0x800ddb4c changes a stat (0 Strength to 5 Luck) by ±1, only if the result
stays at 3 or more and below the race's base + 13, or + 14 for a man's Strength or a
woman's Vitality (confirmed, code). Female is Roster +0x0b bit 0x80 (confirmed, emulator).
The special powers call it.

### Give and Drop

`camp_give` 0x800de578: equipped items can't be given ("It's equipped..."); a cursed one
shows "Cursed!"; a full pack offers a swap (confirmed, code).

`camp_drop` 0x800e0a5c: equipped items can't be dropped. Ids 310 and up ask "This is an
important item. Drop it?", and a yes drops it (confirmed, code). So event items can be
thrown away from the camp.

### Pool Gold

`camp_pool_gold` 0x800e6144 calls `pool_gold` 0x800e12b0, which moves every member's gold
onto the chosen one, capped at 0x7fffffff (confirmed, code).

## Reorganize Party

`camp_reorganize` 0x800d8bcc swaps two of the six slots, moving each member's index and
their alignment byte (0x8007e81e on) together. It needs two or more members (confirmed,
code).

## Save Adventure

`camp_save` 0x800d903c writes the position into each member's roster record, copies the
current party block (0x8007e810, 0x36 bytes) back into its parties[] record, then hands off
to MCARD's save screen: DAT_800796d2 = 0xfa, and main switches to game_mode 7 (confirmed,
code). The save screen itself is analyst F's.

## Settings

`camp_settings` 0x800d9304 has eight rows on `config[0..7]`: three name settings, status,
sound output, music, sound effects and effects (confirmed, code). Turning music on or off
restarts or stops the maze track (track 0xb) at once.

## Decipher Ancient Script

`camp_decipher` 0x800d9e60 is the player's own key for the ancient script: 26 ancient
letters, each mapped to an A-Z letter the player picks, kept at `decipher_table`
0x80089b40 (0xff for unset). MCARD reads and writes it with the save (confirmed, code). The
screen doesn't check the answers; it's a notepad the game remembers (inferred: I found no
code comparing it to anything).

## Help lines

The camp's one-line help is `help_line` 0x800e6628: SISETU string N at (x, y) on glyph
layer 1, nearly always at x = 0xa6 (confirmed, code). There's no help table. Each step of
each screen calls it with a fixed string number when it's entered, so the help text
belongs to the step, not to the cursor (confirmed, code). The exceptions are computed:
the equip prompt (229 + slot), Kandi's region (269 + region) and the Scratch Hand (311-313).

Below it, `text_at` 0x800a1ecc draws string N of text file T (`text_files[T]`: 0
STATUS.OBJ, 1 item names, 3 FIGHTMSG, 4 SISETU, 6 NPC text) at (x, y). `text_draw`
0x800a201c draws the expanded string glyph by glyph (inferred).

## For G: fields seen

These are already in types.h or G's doc, apart from the party-block buffs. I didn't edit
types.h.

- Roster +0x0a race (bits 0-5) and alignment (bits 6-7); +0x0b class (bits 0-6), female
  (bit 0x80); +0x10 age in years, +0x11 weeks; +0x13-0x18 the six stats; +0x34 item state
  bytes; +0x4c known spells; +0x5c spell points; +0x78 poison counter; +0x8b regen.
- Item +0x05 bit 0x80 curse-on-touch; +0x0e break chance; +0x10 breaks into; +0x20
  identify level; +0x21 regen.
- Current party block (0x8007e810, PartyRec): +0x18 Maporfic steps (u16), +0x1a Maporfic AC
  (u8), +0x1c Latumapic steps (u16), +0x1e Litofeit steps (u16), +0x20 attack boost (u8),
  +0x22 its steps (u16), +0x24 magic defence (u8), +0x26 its steps (u16), +0x29 Diafic steps
  (u8), +0x2a no-magic steps (u8).

## How it was traced

Pressing Cross in the maze and watching game_state led to `camp_main`, and its state byte
to the screens. The spell code was the knot. Ghidra flattened both jump tables and the
if-chains into one long function that seemed to heal with every spell at once, so I read
the jump tables at 0x800a1b88 and 0x800a1bf0 straight from the executable (file offset =
address − 0x80010000 + 0x800, after a first wrong guess at the load address) and followed
each case in the disassembly. Kadorto, at 0x800d2c18, only made sense that way. The item
code was similar: a long chain of compares in which each branch tests a value loaded in the
previous instruction's delay slot.

Then I checked the claims that matter most in the emulator from the test save, by button
presses alone: Halito costs nothing, Dumapic costs a point and fails in the Training Maze,
Dios on a healthy ally says "What?" and still costs a point, and a potion on a healthy ally
is used up. The item ids came from a small reader of the item table (scratch in
`rips/re/work/B/`).

## Translation impact

- Camp Dios heals 2d4 (2-8), but its description (STATUS 441) says 1-8.
- Diomas heals 3d2 (3-6); its description (STATUS 484) says 2-6.
- Madial heals the party 10d5 (10-50) in camp; its description (STATUS 461) says 30-60.
  The battle version may differ (D's area), so check before changing the text.
- Madios's 6-18, Dial's 2-16 and Dialma's 3-24 match.
- Loktofeit's "items lost" is true and total: every pack slot is emptied, equipped items
  too. The Ruby Slippers do the same.
- Ihalon is the camp's stat and alignment wish; Mahaman doesn't run in camp.
- Morfis really leaves stone alone, as its description says.
- The Rod of Raising and the Book of Life raise without any failure roll, unlike Kadorto.
- SISETU 603 "Magic Item" and 604 "EVENT Item" show on the item details screen in camp and
  are untranslated (English on the original disc). They're worth a look for case and style.
- "Failed!" (SISETU 284) shows for the no-magic zone and for Dumapic, Malor and Loktofeit
  in areas 9-17; the point is spent each time. "That spell can't be cast." (283) is only for
  spells with no camp effect, and costs nothing.
- "What?" shows when a healing spell finds nothing to heal; the point is still spent.
- "This is an important item. Drop it?" means what it says: event items (id 310 and up)
  can be dropped.
- Kandi's region names (SISETU 269-279) and "Not in this area." (280) are the only answers
  it gives outside the caster's own region.
- Each camp help line belongs to one step of one screen, so its context is fixed: it can be
  checked in the review against the screen that calls it.
