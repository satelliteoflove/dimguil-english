# G: characters, items and records

Phase 2 analyst G, 2026-10-11. The record layouts are in `scripts/re/types.h` and the
names in `scripts/re/symbols/records.csv`. Addresses are RAM, or the module named.
Every claim is marked **confirmed** (and how: code read, RAM read of a dump, label
strings) or **inferred**. `scripts/re/fielduse.py roster` (or `item_table`, `parties`)
lists which functions touch which field; it's the quickest way into any of this.

## Index

Records: roster, parties, items, monsters. Tables: races, classes, EXP, HP, spell
points. Rules found on the way: equipping and curses, item use and breakage, level-up,
class change, the status screen. The rules belong to other analysts' areas (E for the
town, B for the camp, D for battle); this file gives the records and tables they run on.

## Roster record (0xd0 bytes, 20 at 0x8007d708)

Roster order is the Training Hall's. The record holds everything about a character; there
is no separate in-maze copy. The party you walk with is a list of roster indexes (below).

| Off | Size | Field | What | How we know |
|---|---|---|---|---|
| +0x00 | 10 | name | game encoding, ff40-terminated, 8 glyphs at most | confirmed: every copy loop moves 10 bytes; the clear routine writes ff40 and 8 zeros |
| +0x0a | 1 | race_align | bits 0-5 race, bits 6-7 alignment (0 Good, 1 Neutral, 2 Evil) | confirmed: status screen labels (STATUS.OBJ 554-564, 576-578), class and EXP tables |
| +0x0b | 1 | class_sex | bits 0-6 class, bit 7 female | confirmed: status labels 515-532; Valkyrie needs bit 7 |
| +0x0c | 1 | portrait | 0 = the class's portrait, else a special one | inferred: 0x800e6598 draws class, or portrait+0x14 |
| +0x0d | 1 | | no reader found | |
| +0x0e | 2 | status | 1 afraid, 2 confused, 4 poisoned, 8 asleep, 0x10 K.O., 0x20 paralyzed, 0x40 stoned, 0x80 dead, 0x100 ashes, 0x200 lost | confirmed: status_draw shows the highest set bit with labels 610-619 |
| +0x10 | 1 | age_years | | confirmed: status screen; class change adds 3 |
| +0x11 | 1 | age_weeks | 0-51 | confirmed: 52 weeks carry into a year (camp resurrection, 0x800d0514) |
| +0x12 | 1 | age_days | 0-6 | confirmed: the inn adds a day, and 7 carry into a week (0x800c5e34) |
| +0x13 | 6 | stats | Str, IQ, Pie, Vit, Agi, Luc | confirmed: status screen order and labels 592-597 |
| +0x19 | 3 | | no reader found (padding) | |
| +0x1c | 4 | gold | | confirmed |
| +0x20 | 2x10 | items | pack, see "Pack slots" | confirmed |
| +0x34 | 10 | item_state | per slot: uses left on potions and scrolls; 0xfb-0xfe special marks | confirmed: shop sells them with 5, use decrements, status shows the count |
| +0x3e | 2 | | no reader found | |
| +0x40 | 4 | exp | | confirmed: matches the EXP table in a RAM dump (Dracon Fighter, level 5, 4,396) |
| +0x44 | 2 | level | | confirmed |
| +0x46 | 2 | hp | signed | confirmed |
| +0x48 | 2 | max_level | highest level reached | inferred: raised with level, not lowered by drains |
| +0x4a | 2 | max_hp | signed | confirmed |
| +0x4c | 4x4 | spells_known | per school (Mage, Priest, Alchemist, Psionic), a nibble per spell level 1-7, low nibble first; bits 1, 2, 4 are that level's three spells | confirmed: levelup learning 0x800b9090 and spell_points_recalc 0x800b9540 |
| +0x5c | 4x7 | spell_points | per school and spell level, 0-9 | confirmed: casting subtracts 1; recalc caps at 9 |
| +0x78 | 1 | poison | HP lost per poisoned step | confirmed: maze_step_hp 0x800c5570; cleared with the poison bit |
| +0x79 | 1 | | battle counter: 0x7f from hit effects, less 10 a round, cleared on death | inferred |
| +0x7a | 1 | area | 0xff in town, else the area it was left in | confirmed: RAM read and code read |
| +0x7b-0x7d | 3 | x, y, facing | where it was left | confirmed: code read |
| +0x7e-0xbf | | (derived) | values worked out from class and gear, read by battle | see below |
| +0xc0 | 4 | kills | monsters killed | confirmed: status screen label さっしょうすう (584) |
| +0xc4 | 1 | deaths | | confirmed: status screen (しぼうかいすう), +1 at each death |
| +0xc5 | 1 | char_flags | bit 0 a mark on the status screen; bits 1-4 set by the King and maze events | inferred |
| +0xc6 | 3 | met_bits | one bit per NPC meeting | confirmed (talk opcode 0, engine-notes) |
| +0xc9 | 1 | talk_flags | more per-character flags set in talks | inferred |
| +0xca | 2 | marks | +0xca bit 7 and +0xcb bits 0-3 pick the emblems beside the name; +0xca bits 0-1 set in talks | confirmed: status_marks_draw 0x800d9f00 |
| +0xcc | 4 | | | |

The derived block (+0x7e to +0xbf) is recomputed when gear changes and is read mostly in
battle. D mapped its uses (D-battle.md, "Roster fields used in battle"), and types.h
names them: +0x7f-0x82 four saving throws (rand(20) < value), +0x84 to-hit bonus, **+0x86
AC** (confirmed here too: status screen, ac_calc 0x800dc810), +0x87-0x8a magic resistance
by school, **+0x8b regen** (confirmed here: maze steps; D: battle rounds), +0x8c the status
bits the weapons inflict and +0x8d-0x93 their chances, +0x94/+0x95 extra swings and
+0x96-0x9b damage dice of the two weapons, +0x9c/+0x9d their reach, +0xa0 protection
(monster classes whose hits are halved; copied to +0xa4 at battle start), +0xa8 slaying,
+0xae resist bits, +0xb0-0xb6 resistance to the seven hit effects, +0xba resistance to
level drain. What fills the block from the items (+0x22-0x34 and +0x42-0x47 of the item
record, most likely) hasn't been traced yet.

### Status bits in practice

Lost (0x200) ends a character: the town deletes the record, closes the gap and adds the
name to a list of the last three lost at 0x80096720 (E, code read). Level-up makes an old
character Lost when Vit falls under 4 (below), and level drain to 0 does too (D).

"0x20 or more" (paralyzed, stoned, dead, ashes or lost) is the game's test for a character
who can't act: the inn won't take them, the rescue offer looks for parties whose members
are all past it, and the tavern and temple sort on it (confirmed: code read, many sites).
Under 0x80 still counts as alive for healing (0x800d0514).

### Pack slots (Roster.items)

| Bits | Meaning | How we know |
|---|---|---|
| 0x01ff | item id | confirmed |
| 0x0800 | equipped as the sub-hand weapon | confirmed: equip_menu's second pass |
| 0x1000 | equipped as the main-hand weapon (or the first item of its kind) | confirmed: equip_menu |
| 0x2000 | equipped | confirmed: equip_one 0x800cffcc |
| 0x4000 | identified | confirmed: Boltac's buy sets it, the camp identify sets it |
| 0x8000 | cursed: stays equipped | confirmed: equip_one sets it; unequip loops skip it |
| 0xffff | empty slot | confirmed |

Equipping an item whose alignment bits leave out the wearer's alignment curses it (sets
0x8000); so does an item with bit 7 of Item.specials. Class, race and sex bits stop the
equip outright (item_restricted). Every "unequip all" (the Equip command, class change,
becoming a Bishop) clears 0x3800 on everything except cursed items, so a cursed item
stays on through a class change (confirmed: code read, 0x800b4934 and 0x800ccc94).

## Parties

`parties` (0x8008f8c8) holds 20 records of 0x36 bytes: +0 id (-1 unused), +1 member count,
+2 six roster indexes (-1 empty), +8 six bytes per member (seen 00 01 02 03 ff ff after a
wipe, zero otherwise), +0xe six bytes per member that are set to 0xff when a member leaves
(confirmed: code read in tavern and edge of town), +0x14 unknown. The party you walk with
is mirrored at 0x8007e810 in the same layout (confirmed: RAM dumps): `current_party_id`,
`cur_party_count` (0x8007e811) and `cur_party_members` (0x8007e812, read 963 times).
0x80079891, named party_member_count in phase 1, counts the roster instead (E:
roster_compact 0x800dcb70 recounts it); renamed `roster_count`.

`roster_snapshot` (MAIN 0x80020bb8; seed.csv's `party_copy_build` at 0x80020bd0 is a point
inside it) is not a party copy: it copies all 20 roster records into 0x90-byte images at
0x80086880: bytes +0x00-0x7d, kills (+0x80), deaths (+0x84), and the ten bytes from +0xc5
(+0x85). MCARD's save and load code (0x800aa1f4, 0x800ac670, 0x800aa9e0) reads and writes
them (confirmed: xref), so it is the save image of the roster; F has the save format.

## Item record (0x4c bytes, 382 at 0x80052bf2)

Resident in the executable's data, ids 0-381 with the id at +0 (confirmed: table scan).
I_NAME_E.OBJ names them in the same order (BROKEN ITEM is 0).

| Off | Field | What | How we know |
|---|---|---|---|
| +0x00 | id | equals the index | confirmed |
| +0x02 | category | 0 weapon, 1 armor, 2 shield, 3 helm, 4 gauntlets, 5 boots, 6 instrument, 7 other | confirmed: equip passes and names |
| +0x03 | subtype | 0 sword, 1 katana, 2 wand and dagger, 3 axe and hammer, 4 mace and whip, 5 staff, 6 spear and pole, 7 bow, 8 thrown; 9 leather, 10 robe, 11 chain, 12 breastplate and scale, 13 plate; 14 shield; 15 helm, 16 hat; 17 gauntlets; 18 boots; 19 instrument; 20 potion, 21 scroll, 22 cloak, 23 ankh, 24 ring, 25 amulet, 26 other and event items, 28 monster card | confirmed: names, and Boltac's list headings (STATUS.OBJ 24-50) in the same order |
| +0x04 | flags04 | bit 0 Good, 1 Neutral, 2 Evil may use it without a curse; 3 male, 4 female may equip; weapons: 5 two-handed, 6 main hand, 7 sub hand | confirmed: Boltac's inspect draws them with the labels G/N/E, <Sex>, Main/Sub/2-hand (SISETU 0x232-0x234, 0x24c-0x24e) |
| +0x05 | specials | bits 0-6 special powers, bit 7 cursed | confirmed: the weapon compare counts the bits (特); equip_one tests bit 7 |
| +0x06 | | 7 bytes of 0/5/10/15 | not yet read in code (inferred: resistances) |
| +0x0d | equip_effect | effect run when the item is used, or when equipped (list below) | confirmed: code read 0x800ccc94 |
| +0x0e | break_chance | percent chance a use turns it into break_into | confirmed: 0x800d8b04, battle 0x800ac7c4 |
| +0x10 | break_into | item id; 0 (BROKEN ITEM) is then thrown away | confirmed |
| +0x12 | price | Boltac's price | confirmed: buy subtracts it |
| +0x16 | sell | what Boltac pays, half the price as a rule | confirmed: sell code |
| +0x1a | stock | Boltac's starting stock: 0 none, 0xff unlimited (93 items), else a count | confirmed: boltac_stock_init copies it; values from the table |
| +0x1b | battle_spell | spell cast when used in battle, low 7 bits; 0xff none | inferred: battle 0x800a29b4 |
| +0x1c | class_mask | bit per class (14) | confirmed: item_restricted, inspect |
| +0x1e | race_mask | bit per race (11) | confirmed: item_restricted, inspect |
| +0x21 | regen | HP per step: positive values count while carried, negative ones while equipped | confirmed: buy, sell, trade and equip code add or remove it from Roster.regen |
| +0x22-0x34 | | bit fields at +0x22-0x27, values 5-50 at +0x28-0x34 | not yet read in code |
| +0x35 | ac | AC change, negative is better (a shield is -2) | confirmed: inspect prints it |
| +0x36 | to_hit | 当 | confirmed: weapon compare |
| +0x37/0x38/0x39 | dice_n, dice_sides, dice_bonus | damage n d sides + bonus; max = n*sides + bonus, min = n + bonus | confirmed: weapon compare (大 小) |
| +0x3a | extra_swings | 回 | confirmed: weapon compare |
| +0x3e | slay_mask | 倍: monster families it's strong against, 32 bits | confirmed: the compare counts its bits; battle tests it against the monster's +0xa8 |
| +0x42-0x47 | | 5-30 values at +0x42-0x45; 1/2/4 at +0x46 | not yet read |
| +0x4a | | small numbers (picture or sound?) | not yet read |

### Item effects (Item.equip_effect)

Read from equip_menu 0x800ccc94 (the use path in the camp copies it); stat changes go
through 0x800cfc4c(stat, delta). Confirmed by code read: 1-6 a stat +1 (Str..Luc), 7-12
a stat -1, 0xd age -1 (only if over 19), 0xe age +1, 0xf cure the user (status 0, full
HP), 0x10 cure the party, 0x11 max HP +1..4, 0x12 max HP -1..5 and age -1, 0x13 every
spell point to 9, 0x14 every spell point to 0, 0x15 forget every spell, 0x16 poisoned and
max HP down, 0x17 ashes, 0x18 death, 0x19 paralysis (HP 1), 0x1a stone (HP 1), 0x1b Vit +1 and age +1, 0x1c max HP down and Vit +1, 0x1d max HP
up then ashes, 0x1e become a Bishop and 0x25 become a Ninja (both unequip all but cursed
items), 0x1f max HP up and Vit -1, 0x21 full HP if not dead or ashes; 0x20 and 0x22-0x2a
are pairs of stat changes, some with an age change (0x2b max HP up and age +1); 0x2c and
0x2d look for items 0xca and 0xc9 in the pack, 0x2e packs the character's race, class,
sex, alignment and stats into bytes at 0x80086870 (inferred: a password, perhaps for the
card game), 0x2f sets the stats to 5/18/18/5/5/18. Item 0x133 is handled on its own beside these.

## Monster record (0xd0 bytes)

Monster records sit at the end of each DATA02/M_DTnnn.BIN, one per group in the
encounter, with the first group last (339 files; correction from description-check.md
**[record]**). This doc first read only the last 0xd0 bytes of each file, which gave
215 distinct records (ids 0-334) and missed 17 monsters that exist only as earlier
groups: Medusa, Dullahan, the demon lords, Quetzalcoatl and others. Each member of an
NPC party file NPTnn.BIN is a record in the same layout. In battle, group g's record
is `monster_records` (0x8008a918) + g*0xd0, so group 1 is at 0x8008a9e8; groups 1-4 are
byte-for-byte copies of the file's (confirmed: RAM dump against M_DT004). seed.csv's
monster_records row is now typed Monster[5] (group 0 is the party's slot).

The fields are named in types.h `Monster`, almost all from D's battle code reads
(D-battle.md, "Monster record fields used in battle"): names (+0x00, six 0x12-byte slots:
Japanese, Japanese unidentified, English, English unidentified, English plural, English
unidentified plural), id (+0x6c), group size dice (+0x6f), max HP (+0x72), level and HP
dice (+0x74-0x79), AC (+0x7a), EXP (+0x7c, u32), level drain (+0x80), regeneration
(+0x81), AI type (+0x88), flee and call-for-help chances (+0x8a, +0x8b), companion monster
and chance (+0x8c, +0x8e), magic resistance by school (+0xa3-0xa6), type flags (+0xa8:
undead, summoned, immunities, and the low bits slaying and protection match), three
10-byte attacks (+0xac, +0xb6, +0xc0), breath type (+0xc9) and message (+0xca), resist
and weakness bits (+0xcc, +0xce). G checked the placement (a battle RAM dump's group 1
record equals M_DT004's tail byte for byte) and the data profile below; +0x6e (inferred:
the picture) and +0x8f-0xa2 (four schools of five entries, 0xff none, read by monster_pick_spell; inferred:
spell levels) are still open.

A byte-by-byte profile of those 215 records (the last group of each file only) is in "How
it was traced"; D owns the rest.

## Races and classes

Race order (Roster.race_align bits 0-5): Human, Elf, Dwarf, Gnome, Hobbit, Faerie,
Lizardman, Dracon, Rawulf, Mook, Felpurr. Class order (class_sex bits 0-6): Fighter,
Mage, Priest, Thief, Samurai, Lord, Valkyrie, Ranger, Bard, Alchemist, Psionic, Bishop,
Ninja, Monk (confirmed: STATUS.OBJ labels and the class tables' use).

Race base stats, `race_base_stats` 0x8005e1e8 (confirmed: code read; they match the
Wizardry VII values):

| Race | Str | IQ | Pie | Vit | Agi | Luc |
|---|---|---|---|---|---|---|
| Human | 9 | 8 | 8 | 9 | 8 | 8 |
| Elf | 7 | 10 | 10 | 7 | 9 | 8 |
| Dwarf | 11 | 6 | 10 | 12 | 7 | 7 |
| Gnome | 10 | 7 | 13 | 10 | 6 | 7 |
| Hobbit | 8 | 7 | 6 | 9 | 10 | 11 |
| Faerie | 5 | 11 | 6 | 6 | 14 | 11 |
| Lizardman | 12 | 5 | 5 | 14 | 9 | 7 |
| Dracon | 10 | 7 | 6 | 12 | 8 | 8 |
| Rawulf | 8 | 6 | 12 | 10 | 8 | 9 |
| Mook | 10 | 10 | 6 | 10 | 7 | 8 |
| Felpurr | 7 | 10 | 7 | 7 | 12 | 10 |

Class minimums (`class_min_stats` 0x8005e22c) and the alignments a class may take
(`class_alignment` 0x8005e280, [alignment][class] = the class or -1). Class change also
needs bit 7 (female) for a Valkyrie, and a class other than the current one (confirmed:
training_class_change 0x800b4934):

| Class | Str | IQ | Pie | Vit | Agi | Luc | Good | Neutral | Evil |
|---|---|---|---|---|---|---|---|---|---|
| Fighter | 12 | - | - | - | - | - | yes | yes | yes |
| Mage | - | 12 | - | - | - | - | yes | yes | yes |
| Priest | - | - | 12 | - | - | 8 | yes |  | yes |
| Thief | - | - | - | - | 10 | 12 |  | yes | yes |
| Samurai | 12 | 11 | - | 9 | 14 | 9 | yes | yes |  |
| Lord | 15 | 11 | 14 | 15 | 11 | 14 | yes |  |  |
| Valkyrie | 10 | - | 11 | 11 | 11 | 9 |  | yes |  |
| Ranger | 10 | 8 | 8 | 11 | 8 | 9 |  | yes | yes |
| Bard | - | 10 | - | - | 8 | 12 | yes | yes |  |
| Alchemist | - | 13 | - | - | - | 13 | yes | yes | yes |
| Psionic | 10 | 14 | - | 14 | - | 10 |  | yes | yes |
| Bishop | - | 15 | 15 | - | - | 8 | yes |  | yes |
| Ninja | 15 | 14 | 14 | 15 | 15 | 16 |  |  | yes |
| Monk | 13 | 8 | 13 | - | 13 | 9 | yes | yes |  |

## EXP tables

`exp_for_level` (JOUKA 0x800c8a2c): level 1 needs 0; levels 2-13 read
`exp_tables[t][level-2]`; past 13, table[11] + table[12] * (level-13). The table t for a
race and class is `exp_table_index` 0x8005e4bc (confirmed: code read, and the RAM dump's
Dracon Fighter at level 5 has exactly 4,396).

| Race | Fig | Mag | Pri | Thi | Sam | Lor | Val | Ran | Bar | Alc | Psi | Bis | Nin | Mon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Human | 0 | 1 | 1 | 1 | 2 | 5 | 2 | 0 | 1 | 2 | 3 | 3 | 6 | 3 |
| Elf | 2 | 0 | 0 | 1 | 3 | 5 | 2 | 2 | 0 | 1 | 3 | 2 | 6 | 4 |
| Dwarf | 0 | 2 | 0 | 2 | 3 | 5 | 1 | 1 | 2 | 3 | 4 | 2 | 6 | 1 |
| Gnome | 0 | 2 | 0 | 2 | 4 | 5 | 1 | 2 | 2 | 3 | 3 | 2 | 6 | 2 |
| Hobbit | 1 | 2 | 2 | 0 | 4 | 5 | 3 | 1 | 0 | 2 | 4 | 4 | 6 | 4 |
| Faerie | 3 | 0 | 2 | 0 | 4 | 5 | 3 | 2 | 0 | 0 | 4 | 3 | 6 | 4 |
| Lizardman | 0 | 3 | 3 | 1 | 3 | 5 | 3 | 1 | 2 | 3 | 4 | 5 | 6 | 4 |
| Dracon | 0 | 1 | 2 | 1 | 3 | 5 | 2 | 0 | 2 | 2 | 2 | 4 | 6 | 4 |
| Rawulf | 1 | 2 | 0 | 1 | 4 | 5 | 1 | 0 | 2 | 3 | 3 | 3 | 6 | 3 |
| Mook | 0 | 0 | 2 | 2 | 2 | 5 | 3 | 0 | 1 | 1 | 1 | 3 | 6 | 4 |
| Felpurr | 2 | 0 | 1 | 0 | 3 | 5 | 3 | 1 | 0 | 1 | 3 | 3 | 6 | 3 |

| Table | Lv 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | each level past 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 800 | 1,583 | 2,638 | 4,396 | 7,326 | 12,210 | 20,350 | 33,916 | 56,526 | 94,210 | 157,016 | 261,693 | 211,693 |
| 1 | 900 | 1,642 | 2,795 | 4,610 | 7,948 | 13,703 | 23,625 | 40,732 | 70,227 | 121,081 | 208,760 | 359,931 | 260,369 |
| 2 | 1,000 | 1,724 | 2,972 | 5,124 | 8,834 | 15,231 | 26,260 | 45,275 | 78,060 | 134,586 | 232,044 | 400,075 | 289,709 |
| 3 | 1,100 | 1,896 | 3,268 | 5,634 | 9,713 | 16,746 | 28,872 | 49,779 | 85,825 | 147,974 | 255,127 | 439,874 | 318,529 |
| 4 | 1,200 | 2,105 | 3,692 | 6,477 | 11,363 | 19,935 | 34,973 | 61,356 | 107,642 | 188,845 | 331,307 | 581,240 | 438,479 |
| 5 | 1,300 | 2,280 | 4,000 | 7,017 | 12,310 | 21,596 | 37,887 | 66,468 | 116,610 | 204,578 | 358,908 | 629,663 | 475,008 |
| 6 | 1,450 | 2,543 | 4,461 | 7,826 | 13,729 | 24,085 | 42,254 | 74,129 | 130,050 | 228,157 | 400,275 | 702,236 | 529,756 |

## Hit points

`hp_dice` (JOUKA 0x800a138c), die and base per class; one level's HP is base + 1..die,
then -1 at Vit 3, +0 at Vit 4-5, +1 at Vit 6-15, and +1+(Vit-15) above (hp_die_roll
0x800ba5b0; at least 1). Level-up rerolls every level (Samurai and Monk get one extra
roll) and keeps the result only if it beats the old max; otherwise max HP + 1
(levelup_hp_reroll 0x800b9e6c). All confirmed by code read.

| Class | HP per level |
|---|---|
| Fighter, Lord, Valkyrie | 4-10 |
| Samurai | 4-9 |
| Priest, Ranger | 3-8 |
| Thief, Bard, Bishop, Ninja, Monk | 3-6 |
| Mage, Alchemist, Psionic | 2-4 |

## Spells and spell points

Spell s = school*21 + level*3 + k (school 0 Mage, 1 Priest, 2 Alchemist, 3 Psionic; level
0-6; k 0-2, bit 1<<k of the level's nibble). STATUS.OBJ 420+s is its description (420-440
Mage, 441-461 Priest, 462-482 Alchemist, 483-503 Psionic). Inferred from the counts (84
descriptions, 4 schools of 7 levels of 3) and the order of the Mage list.

Spell points (spell_points_recalc 0x800b9540, confirmed by code read): for each spell
level, the number of spells known there (3 known count as 4); then a caster class's rule
from `spell_slot_table` (JOUKA 0x800a133c), three u16s (school, start, step): n = level -
start, and for spell levels 1-7 the points are at least n, n-step, n-2*step ..., capped at 9.

| Class | School | Start | Step |
|---|---|---|---|
| Mage | Mage | 0 | 2 |
| Priest | Priest | 0 | 2 |
| Bishop | Mage, and Priest | 0, and 3 | 4, and 4 |
| Lord, Valkyrie | Priest | 3 | 2 |
| Samurai | Mage | 3 | 3 |
| Bard | Mage | 3 | 2 |
| Alchemist | Alchemist | 0 | 2 |
| Ranger | Alchemist | 3 | 2 |
| Ninja | Alchemist | 6 | 3 |
| Monk | Psionic | 6 | 3 |
| Psionic | Psionic | 0 | 2 |

Fighters and Thieves have no rule. Learning (spells_learn_roll 0x800b9090, confirmed):
at each level-up, for every spell level with points, a level with nothing known learns
one spell at random; each spell still unknown is then learned on rand(0..29) < IQ (Mage),
Pie (Priest), (IQ+Luc)/2 (Alchemist) or (IQ+Vit)/2 (Psionic). A Bishop learns Mage spells
on odd levels and Priest spells on even ones. Class change gives a new Mage, Bishop,
Priest, Alchemist or Psionic its first spells from (IQ-1)/6, (Pie-1)/6, (Pie+Luc)/12 or
(IQ+Vit)/12; the Alchemist's sum there differs from the learning roll (both confirmed as
read; worth an emulator check).

## Level-up stats and aging

levelup_stat_rolls (0x800b99dc), confirmed by code read: each stat is considered 76% of
the time. Then if rand(0..59) < age in years, the stat may drop: when it's under 4 and is
Vit, the character is Lost (status 0x200, HP 0: death of old age); otherwise it drops by 1
if under a random cap and rand(0..level-1) > 3. Else it rises by 1 when under the race base
+ 10 (+ 11 for a male's Str or a female's Vit) and rand(0..41) > the stat. The flags it sets
(0x800798a6) pick the level-up messages.

Age: the inn adds a week for each paid week and a day for a night in the Stables (seven
days make a week; E-town.md, emulator-checked), Kadorto adds 1-52 weeks to the character
it raises (B), class change adds three years, "Retrain?" at creation adds three years (F, emulator-checked), and
some items move it by a year (equip_effect 0xd, 0xe).

## Class change

training_class_change (0x800b4934), confirmed by code read: saves a copy of the record
(for undo), age +3, level 1, EXP 0, keeps the sex bit and sets the new class, unequips
everything but cursed items, sets each stat to the larger of the race base and the class
minimum, gives pure casters their first spells (above), recomputes spell points, and
turns any 9-point spell level into 4.

## How it was traced

- The roster had a typed struct with gaps from phase 1. `fielduse.py` (new) counted every
  field and subscript in the decompiled C, so the busiest gaps came first: name[10] and
  name[0xb] (159 uses) turned out to be race/alignment and class/sex.
- The status screen draw (JOUKA 0x800d8804) prints most fields in order with string
  indexes into STATUS.OBJ, so the label strings named the fields: race, age, sex,
  alignment, class, the six stats, AC, deaths, the status bit ladder, HP, gold, kills
  (the label さっしょうすう), EXP.
- Class change named the race and class tables: it compares stats with 0x8005e22c[class*6]
  and resets them from 0x8005e1e8[race*6]. The tables sit back to back (66 and 84 bytes,
  then 42 for alignments), which pinned the counts at 11 races and 14 classes before the
  labels did.
- The item table came from the equip code's `(&DAT_80052bf4)[id * 0x4c]`. A scan showed
  ids 0-381 at +0, so the base is 0x80052bf2. Typing it needed `#pragma pack(1)`: the u32s
  sit at odd halfword offsets, and Ghidra's parser honours the pragma.
- Boltac's weapon compare (0x800c2b84) and inspect (0x800d4574) print item fields beside
  short labels (当 回 大 小 倍 特, Main/Sub/2-hand, G/N/E), which named the weapon fields
  and the restriction bits; equip_one (0x800cffcc) showed 0x2000 is "equipped" and that a
  wrong alignment curses rather than blocks.
- The Roster.regen field turned up as +0x8b, adjusted by every shop and trade routine by
  the item's +0x21 and read by the step routine, which heals by it one step in four.
- EXP: the status screen colours EXP with can_level_up, which led to exp_for_level and its
  tables; the RAM dump's premade Dracon Fighter at level 5 holds exactly table 0's level-5
  figure.
- Monster records: names searched for in a battle RAM dump sat at 0x8008aa0c, 0x24 into a
  record that matched M_DT004's last 0xd0 bytes exactly.

Field profile of the 215 distinct monster records (offset: distinct values, most common):
+0x6e 26 (12, 13, 10), +0x6f 5 (1, 2, 3), +0x70 7 (3, 4, 1), +0x72 88, +0x74 37, +0x76 12
(2-12), +0x78 69, +0x7a 36 (signed, -3..7), +0x7c 110, +0x83 29, +0x84 21 (100, 50, 40),
+0x85 (1, 2), +0x86 (24, 200), +0x8a 12 (0, 25, 20), +0x8b 15 (0, 20, 10), +0x8e 38,
+0x8f-0xa2 mostly 0xff, +0xa3-0xa6 0-95 in steps of 5, +0xa8-0xab single bits,
+0xac/+0xb6/+0xc0 attack records, +0xcc-0xcf flags. `scripts/re/recdump.py monster --profile` prints the full profile.

`scripts/re/recdump.py` (new) prints these records with the fields named: `roster RAMDUMP`
(checked against the dumps: the premade party reads correctly, e.g. Uranus, Dracon
Neutral Fighter, level 5, AC -2, main-hand weapon 9), `party RAMDUMP`, `item ID` and
`monster FILE`. Item 1, the Faerie Stick, has race_mask 0x20 (Faerie only), which
confirms the race bit order.

## Translation impact

- Item descriptions make claims the item table can check: "heals HP while carried" is a
  positive Item.regen (+0x21), "drains" a negative one (only while equipped); "cursed"
  is specials bit 7, or a wrong alignment; "doubles against demons and dragons" is
  slay_mask bits; "breaks" is break_chance and break_into; the Valkyrie-only gear has a
  class_mask of one bit. A sweep that compares each description's claim with its record
  would catch mistranslations (and the original's own errors).
- Boltac's list headings (STATUS.OBJ 24-50) are the item subtypes in order, and the
  catalog picture category is subtype + 9.
- Spell descriptions: STATUS.OBJ 420+s, in school/level/slot order.
- The inn's room prices in STATUS.OBJ 10-14 (10, 50, 200, 500, 10000 G a week) are the
  gold the code checks (inn_stay 0x800c5e34), so the English figures are right.
- The status labels STATUS.OBJ 582-585 are HP, Gold, Kills, EXP; "Kills" is what +0xc0
  counts.
- 帰還 (STATUS.OBJ 496, "Return: back to the castle; items lost") is a spell that loses the
  pack; it bears on Chris's question about item loss after a wipe (A's area).
- For the Balbo question: the rescue fees clear Roster.items (Balbo) or Roster.gold (Guy);
  the pack bits above mean even a cursed or equipped item goes.
