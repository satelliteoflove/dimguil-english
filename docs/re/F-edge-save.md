# F. Edge of Town, Training Grounds, and saving and loading

Phase 2 analyst F, 2026-10-11. Scope: HAZURE (the Edge of Town), MCARD below 0x800b0000
(memory card, the maze's START menu, Look for Companions), the title screen, and the
Training Grounds' creation and class change rules (which live in JOUKA). Symbols are
in `scripts/re/symbols/edge.csv`. The save decoder is `scripts/re/savefile.py`.

Each claim is marked:
- **[code]**: confirmed by reading the code.
- **[emu]**: confirmed in the emulator, by button presses and RAM reads only.
- **[inferred]**: not confirmed.

The emulator scripts are in `rips/re/work/F/`.

**Read first:** the phase 1 projects were built from `rips/q7iso/dimguil/`. That's a test
build of checklist item Q7, with our asm patches applied, not the original disc. The
original files are in `rips/clean/dimguil/`. The code files differ from the original only
at patch sites; MCARD has 19 bytes changed and HAZURE 31. So the decompiled C is right
everywhere except at those sites, where it shows our patched code. One example is
MCARD 0x800ad640, inside `mcard_print`. See "For the other analysts" at the end.

## Where these screens run

`main` (0x800114d8) picks the routine to run each frame from `game_state` (0x80079a13)
**[code]**:

| game_state | Module | Routine | What it is |
|---|---|---|---|
| 5 | MAIN | `title_screen` 0x8001744c | Title: New Game (or Continue), Load Data |
| 9 | HAZURE | `edge_main` 0x800a1394 | Edge of Town |
| 0x32 | MCARD | `save_screen` 0x800ab3b0 | The Save screen, from anywhere |
| 0x33 | MCARD | `load_screen` 0x800abf10 | Load Data |
| 0x34 | MCARD | `maze_menu` 0x800ae6b4 | START in the maze |
| 0x36 | MCARD | `continue_from_ram` 0x800acd78 | The title's Continue |

Screens hand control back through `next_place` (0x800796d2), which `main` reads
**[code]**:

| Value | Meaning |
|---|---|
| 0 | Town |
| 0xff | Begin Adventure (maze from the entrance) |
| 0xfe | Training Maze |
| 0xf6 | Dragon's Cave |
| 0xfc | Resume in the maze |
| 0xfb | Save from the Edge of Town |
| 0xfa | Save from the maze camp |
| 0xf9 | Save from the maze's START menu |
| 0xf8 | Save from town |
| 0xfd | Back to the Edge of Town |
| 1-2 | Catalog / Compendium |

Main runs the Save screen as game mode 7: it loads MCARD and sets game_state 0x32. Then
it returns to wherever the save was asked from.

## The Edge of Town (HAZURE)

### Entry and the menu

- **Snapshots every frame [code].** `edge_main` calls `roster_snapshot` (MAIN 0x80020bb8)
  and `party_snapshot` (MAIN 0x80021a0c) every frame. So the saved copies of the roster
  (0x80086880) and of the parties (`parties_saved`, 0x8008e620) are always current here.
- **The menu [code + emu].** Eight icons, nine when bit 31 of `story_flags` (0x80079b44)
  is set; the extra one is Dragon's Cave. The labels are STATUS.OBJ 54, 58, 55, 57, 56, 60
  and 59, plus SISETU 436 (Dragon's Cave) and 429 (Book of Movement), from a table at
  HAZURE 0x800a100c. Choosing entry *i* sets `camp_state` (0x80079669) to 10 + 5*i; the
  Dragon's Cave slot shifts the later ones when it's hidden:

| Entry | Label | Handler | What it does |
|---|---|---|---|
| 10 | Begin Adventure | `edge_enter_maze` 0x800a2034 | next_place 0xff |
| 15 | Go to the Training Maze | same | next_place 0xfe |
| 20 | Dragon's Cave (hidden until story_flags bit 31) | same | next_place 0xf6 |
| 25 | Resume Adventure | `edge_resume_adventure` 0x800a21b0 | see below |
| 30 | Prepare for Adventure | `edge_prepare` 0x800a3be0 | Inspect Character, Reorganize Party, Back |
| 35 | Suspend Game | `edge_suspend_game` 0x800a3998 | saves, see below |
| 40 | Book of Movement | `book_of_movement` 0x800ac9f4 | character import |
| 45 | Change Settings | `edge_settings` 0x800abbd4 | settings screen |
| 50 | Back to Town | | next_place 0, returns 1 |

- **Who can set out [code].** Begin Adventure, the Training Maze and Dragon's Cave need a
  current party (`0x8007e811`, its member count). Without one the game prints SISETU 11
  ("You haven't formed a party"). They also need at least one member with status below
  0x20, which means nobody paralyzed or worse. If every member is paralyzed or worse,
  nothing happens.
- **Input [code].** `menu_input` (0x800a1f50) returns 4 for circle (confirm), 2 for cross
  (cancel), 1/3 for triangle/square, 5-10 for the shoulders, select and start, and 11-14
  for the d-pad. It also moves the cursor bytes passed to it. The same convention runs
  through MCARD and JOUKA (`yesno_read` returns 4 or 2).
- **Fade [code].** `edge_enter_maze` fades out through `edge_fade_out` (0x800af668): 32
  frames, sprites and music. It prints "One moment, please." and reloads FIGHTMSG
  (table 1 index 2) and table 3 index 0x1a to 0x80150000. Its argument (0, 9 or 0x2a by
  entry) isn't used. The destination is `next_place`.

### Resume Adventure

**[code + emu]** This is how a party left in the maze carries on:

1. It copies `parties_saved` back into `parties`.
2. It lists every member of every other party whose roster `area` (+0x7a) isn't 0xff,
   meaning not in town. With nobody out, it prints SISETU 0x13e ("No one is in the
   dungeon.").
3. You pick a character, and the game finds that character's party. If no member has a
   status below 0x20, nothing happens, so **a wiped party can't be resumed**. It has to be
   found and carried out.
4. Otherwise the current party's record is freed, the chosen party is copied into the
   current party block (0x8007e810, 0x36 bytes), and the party walks in at the first
   member's saved `area`, `x`, `y` and `facing`.
5. One fix-up: anyone saved at area 0x17, square (4,11), is moved to (5,11) first. That
   square is presumably one you can't start on.
6. next_place becomes 0xfc.

Emulator test (`rips/re/work/F/suspendtest.py`, then `resumetest.py`):
- In `maze_door.state`, press START, then Save and Suspend.
- Cold boot with that card and use Load Data. The tavern then lists only Mars and
  Mercury; the four in the maze aren't there.
- At the Edge of Town, Resume Adventure lists Uranus, Venus, Jupiter and Earth as
  "A OK/Out".
- Choosing them puts the party in the maze at area 0, (11,20), facing 0, the saved square.

### Suspend Game

**[code + emu]** Suspend Game is the Edge of Town's save:
1. It copies all 20 party records into `parties_saved` and sets next_place 0xfb.
2. Main runs the Save screen, then sets next_place 0xfd and comes back here.
3. The screen shows SISETU 615-617 ("Thank you for playing. You can turn the power off
   now. Press O to resume."). Circle returns to the menu.

The game doesn't reset or quit. ("Save Game" in `mktestsave.py` is this entry.)

### Prepare for Adventure

**[code]** The labels are SISETU 393, 408 and 412, from HAZURE 0x800a1024.

- **Inspect Character** (`edge_inspect` 0x800a3f50) is the status screen, with Cast
  Spell, Items and Sort Items. It's a copy of the camp's (analyst B's). The item code
  (equip, use, give, drop, identify) is in `edge_use_item`, `edge_give_item`,
  `edge_drop_item`, `edge_identify_*` and G's `equip_menu` copy at 0x800afa9c.
- **Reorganize Party** (`edge_reorder` 0x800ab728) asks "Move whom? / Move where?".

**Casting outside battle** (`edge_cast_spell` 0x800a4ef8; B has the maze's copy).

Its effect switch is on 0x800798f0. The cases are numbered by the code; which spell is
which is **[inferred]**.

| Case | Effect | Notes |
|---|---|---|
| 0 | Heal 2d4 | |
| 3 | Heal 2d8 | |
| 4 | Heal 3d8 | |
| 1 | Cure paralysis | Clears bit 0x20 |
| 2 | Cure poison | Clears 0x04 and the poison counter at +0x78 |
| 5 | Full heal and cure everything short of death | |
| 6 | Raise | See below |

These are confirmed by the code:
- Each case first checks the target with `status_has` (0x800a8d9c); heals need "alive and
  hurt".
- `dice(n, s, b)` (0x800becf8) is n dice of s sides plus b.

Raising (case 6) **[code]**, for a dead (0x80) or ashed (0x100) target:
- Vitality (+0x16), if above 1, first drops by 0 or 1 at random.
- If vitality is then below 4, the dead become ashes (status |= 0x100, HP 0) and the ashed
  are **Lost** (status = 0x200; message SISETU 0x9d, "{name} is lost forever.").
- Otherwise it succeeds if `rand_upto(80) < vitality * 4`. On success: status 0, HP to
  max, and the character ages 1-52 weeks (+0x11, rolling into years at +0x10). On failure
  the same two outcomes as above apply.

So a character with vitality 20 is raised every time, and one below 4 never is. (E has
the temple's version.)

There's also a boon menu (SISETU 0x11e-0x127, "Grant which effect?"): raise a stat, or
turn Good, Neutral or Evil. The message is SISETU 0x12e ("{name}'s alignment changed").
**[inferred]** It belongs to one of the high-level spells.

### Book of Movement (転生の書)

**[code, strings]** `book_of_movement` (0x800ac9f4) imports a character from another game.
1. It asks "Reborn from which game?" with two choices, SISETU 0x274-0x275:
   "-Scripture of the Dark-" (Gaiden III) and "-Throb of the Demon's Heart-" (Gaiden IV).
2. It takes a name, then a password (SISETU 0x26d-0x273), then the sex.
3. It refuses when the roster is full (20) or the name is taken.

The password decoder isn't traced yet. It's the bulk of the function's 8 KB. The name
"Book of Movement" is the game's own English (docs/terms.md).

### Settings

`edge_settings` (0x800abbd4) draws rows of "(Jpn/Eng)", "(Str/Mon)" and "(ON/OFF)"
(SISETU 0x25e-0x265) over the `config` bytes. engine-notes.md, "Settings", already maps
the bytes, and `asm/english_only.asm` locks the language rows.

## The maze's START menu (MCARD, game_state 0x34)

**[code + emu]** START in the maze opens MAZE 0x800a96b0, which sets game_state 0x34;
MCARD is then resident. `maze_menu` (0x800ae6b4) has five entries, SISETU 0x1ae-0x1b2:

| Entry | Handler | What it does |
|---|---|---|
| Investigate (調査) | MAZE 0x800cc5e0 (A's) | Main reloads MAZE and runs it |
| Look for Companions | `look_for_companions` 0x800aebe0 | See below |
| Save and Suspend | `maze_save_suspend` 0x800afd54 | See below |
| Go On with Another Party | MCARD 0x800b00c4 | In C's range, not read here |
| Back | | Back to the maze |

**Look for Companions [code]** is the player's own way to pick up a wiped party:
- After a short "Looking for companions..." animation (60 frames), it scans every party
  other than the current one for members whose roster `area`, `x` and `y` equal the
  current square.
- Members on an adjacent square (within one in x and y) don't count, but they turn
  "No one is here." into "There are faint traces, but no one was found." (SISETU 0x140).
- The members found are listed with their worst status (the labels below) and can join
  the current party, up to six.
- A member who joins is removed from their old party: its member slot is set to -1, its
  `member_state` to 0xff and its count decremented; an empty party is freed (id -1).
- **It doesn't touch items or gold.** No write in the function reaches the roster's items
  or gold; its callees are the display routines in MCARD 0x800b1xxx-0x800b3xxx, which are
  **[inferred]** to do nothing else.

So walking to the exact square and choosing Look for Companions recovers a party with
everything it carried. That's the control for the NPC rescue fees in engine-notes.md.

**Save and Suspend [code + emu]**:
1. It writes `cur_x`, `cur_y`, `cur_area` and `cur_facing` into every current member's
   roster `x`, `y`, `area` and `facing`.
2. It copies the current party block back into its `parties` slot.
3. It calls `roster_snapshot` and `party_snapshot`.
4. It sets next_place 0xf9, which runs the Save screen.
5. It shows the same "Thank you for playing" box; circle goes back to the menu.

B found the camp's "Save Adventure" (MAZE 0x800d903c, `camp_save`), which does the same.

## Status bits

From the status labels, in `look_for_companions` and the Training Grounds lists
**[code]**:
- Roster `status` (+0x0e) is a bitfield, and screens show the highest set bit.
- The labels are STATUS.OBJ 0xce + n (English) and 0x261 + n (Japanese), chosen by
  `config[3]`.

| Bit | n | Japanese | Disc's English |
|---|---|---|---|
| 0x001 | 1 | おそれ | Afraid |
| 0x002 | 2 | こんらん | **Sane** (see Translation impact) |
| 0x004 | 3 | どく | Poison |
| 0x008 | 4 | ねむり | Sleep |
| 0x010 | 5 | きぜつ | K.O. |
| 0x020 | 6 | まひ | Paralyze |
| 0x040 | 7 | せきか | Stone |
| 0x080 | 8 | しぼう | Dead |
| 0x100 | 9 | はい | Ash |
| 0x200 | 10 | ロスト | Lost |
| 0 | 0 | せいじょう | OK |

"Status 0x20 or more" counts as out of action. That threshold appears in setting out,
Resume Adventure and the NPC rescue scan. It means a character who is paralyzed or
worse: stoned, dead, ashed or lost. A party whose members are all paralyzed counts as
wiped out.

`status_has(char, k)` (HAZURE 0x800a8d9c) tests one condition:

| k | Condition |
|---|---|
| 0 | Alive and hurt |
| 1 | Poison |
| 2 | Paralyzed |
| 3 | Stone |
| 4 | Dead |
| 5 | Ash |
| 6 | Afraid |
| 7 | K.O. |
| 8 | Confused |
| 9 | Asleep |

## Parties left in the maze

What this part of the code shows, for the body questions in engine-notes.md:
- **Where they're kept [code + emu].** A party in the maze is a `parties` record (20 of
  0x36 bytes at 0x8008f8c8) whose members' roster records hold the square they were left
  on (`area` +0x7a, `x`, `y`, `facing`). In town, `area` is 0xff.
- **Saving them [code + emu].** The save holds `parties_saved`, the copy `party_snapshot`
  makes, and the character images (roster +0x00-0x7d, so location included). Both come
  back on load (`roster_restore`, `parties_restore`). Load then frees any party record
  with no members left. Nothing else changes.
- **No decay in the save path [code].** No code in the save path (`save_write`,
  `save_read`, `roster_restore`, `parties_restore`, `continue_from_ram`) or at the Edge of
  Town touches the items, gold or status of characters out of town. If items do vanish
  over time, it happens in the maze or town code (A, E). It isn't in saving, loading or
  resuming.
- **Getting them back:**
  - Look for Companions on the exact square **[code]**: everything kept.
  - An NPC party's offer (engine-notes.md, "Body recovery by NPC parties"): with a fee.
  - Resume Adventure, only if someone is still standing **[code]**.

## Training Grounds (JOUKA): creation and class change

Training Grounds is in town. Its menu is E's `training_main` (JOUKA 0x800ae0c0). The
rules below are F's; the tables are executable data, and G owns the record layouts.

Record fields used here **[code; stats checked on Uranus's status screen, emu]**:

| Offset | Field |
|---|---|
| +0x0a | Race (low 6 bits), alignment (bits 6-7: 0 Good, 1 Neutral, 2 Evil) |
| +0x0b | Class (low 7 bits), sex (bit 7: 1 female) |
| +0x10 | Age in years |
| +0x11 | Weeks (inferred) |
| +0x13 to +0x18 | Strength, I.Q., Piety, Vitality, Agility, Luck |

Uranus (Dracon, Neutral, Male Fighter) has +0x0a 0x47, +0x0b 0x00, age 16 and stats
22/5/5/14/19/7, which match his status screen.

Classes 0-13: Fighter, Mage, Priest, Thief, Samurai, Lord, Valkyrie, Ranger, Bard,
Alchemist, Psionic, Bishop, Ninja, Monk (STATUS.OBJ 0x74 + n).

Races 0-10: Human, Elf, Dwarf, Gnome, Hobbit, Faerie, Lizman, Dracon, Rawolf, Mook,
Felpurr (STATUS.OBJ 0x97 + n).

### Creating a character

`training_create` (JOUKA 0x800af5d8) builds the character in a work record, `new_char`
(0x8008ff10, a full Roster record). At the end it copies it to `roster[roster count]`
(0x80079891, which E notes counts roster entries). The steps **[code]**:

1. **Name**, then **race**. The base stats are race_base 0x8005e1e8, 6 bytes per race:

   | Race | St | IQ | Pi | Vi | Ag | Lu |
   |---|---|---|---|---|---|---|
   | Human | 9 | 8 | 8 | 9 | 8 | 8 |
   | Elf | 7 | 10 | 10 | 7 | 9 | 8 |
   | Dwarf | 11 | 6 | 10 | 12 | 7 | 7 |
   | Gnome | 10 | 7 | 13 | 10 | 6 | 7 |
   | Hobbit | 8 | 7 | 6 | 9 | 10 | 11 |
   | Faerie | 5 | 11 | 6 | 6 | 14 | 11 |
   | Lizman | 12 | 5 | 5 | 14 | 9 | 7 |
   | Dracon | 10 | 7 | 6 | 12 | 8 | 8 |
   | Rawolf | 8 | 6 | 12 | 10 | 8 | 9 |
   | Mook | 10 | 10 | 6 | 10 | 7 | 8 |
   | Felpurr | 7 | 10 | 7 | 7 | 12 | 10 |

2. **Sex.** Male gets +1 Strength. Female sets bit 7 of +0x0b and gets +1 Vitality.
   (SISETU 0xc3/0xc4 describe these as "Strength goes up by 1" and "Vitality goes up
   by 1".)
3. **Alignment**, into bits 6-7 of +0x0a.
4. **Bonus points**, from `bonus_roll` (0x800ba44c). It takes a = rand_upto(3) and
   b = rand_upto(20), both inclusive:

   | Roll | Bonus | Chance |
   |---|---|---|
   | b ≠ 10 | 7 + a, so 7-10 | 20/21, about 95.2% |
   | b = 10, then a second rand_upto(20) ≠ 10 | 17 + a, so 17-20 | 20/441, about 4.5% |
   | b = 10 twice | 27 + a, so 27-30 | 1/441, about 0.23% |

   Within each band the four values are equally likely. Backing out to the alignment and
   confirming again rolls anew.
5. **Class list.** A class is offered when all of these hold:
   - `class_alignment` (0x8005e280, [alignment][class]) isn't -1:
     - Good: Fighter, Mage, Priest, Samurai, Lord, Bard, Alchemist, Bishop, Monk.
     - Neutral: Fighter, Mage, Thief, Samurai, Valkyrie, Ranger, Bard, Alchemist,
       Psionic, Monk.
     - Evil: Fighter, Mage, Priest, Thief, Ranger, Alchemist, Psionic, Bishop, Ninja.
   - It isn't Valkyrie, unless the character is female.
   - The points needed to bring every stat up to the class minimum (`class_min_stats`
     0x8005e22c) are no more than the bonus.

   Choosing a class spends those points automatically, raising each stat to its minimum.
   **[emu]** A Good male Human with 7 points was offered exactly Fighter, Mage, Priest and
   Bard. Alchemist would need 10 points, and Samurai, Lord, Bishop and Monk more.

   The minimums (St IQ Pi Vi Ag Lu):

   | Class | St | IQ | Pi | Vi | Ag | Lu |
   |---|---|---|---|---|---|---|
   | Fighter | 12 | 0 | 0 | 0 | 0 | 0 |
   | Mage | 0 | 12 | 0 | 0 | 0 | 0 |
   | Priest | 0 | 0 | 12 | 0 | 0 | 8 |
   | Thief | 0 | 0 | 0 | 0 | 10 | 12 |
   | Samurai | 12 | 11 | 0 | 9 | 14 | 9 |
   | Lord | 15 | 11 | 14 | 15 | 11 | 14 |
   | Valkyrie | 10 | 0 | 11 | 11 | 11 | 9 |
   | Ranger | 10 | 8 | 8 | 11 | 8 | 9 |
   | Bard | 0 | 10 | 0 | 0 | 8 | 12 |
   | Alchemist | 0 | 13 | 0 | 0 | 0 | 13 |
   | Psionic | 10 | 14 | 0 | 14 | 0 | 10 |
   | Bishop | 0 | 15 | 15 | 0 | 0 | 8 |
   | Ninja | 15 | 14 | 14 | 15 | 15 | 16 |
   | Monk | 13 | 8 | 13 | 0 | 13 | 9 |

6. **Distribute** what's left. Each stat can go at most 10 above its value before the
   bonus (0x80079bd0).
7. **Finishing:**
   - Age: 15 + rand_upto(5), so 15-20.
   - Weeks (+0x11) and +0x12: 0.
   - Gold: 100.
   - +0x86: 10.
   - Level: 1.
   - HP: `class_hp_base[c]` + rand 0..`class_hp_die[c]`-1, with base/die by class:
     - Fighter 7/4, Mage 4/1, Priest 5/4, Thief 5/3, Samurai 6/6, Lord 7/4,
       Valkyrie 7/4
     - Ranger 6/6, Bard 5/3, Alchemist 4/1, Psionic 4/1, Bishop 5/3, Ninja 8/1,
       Monk 6/6

     So a Mage always starts with 4 HP and a Fighter with 7-10.
   - Spell slots:
     - Mage and Bishop: (I.Q.-1)/6, school 0.
     - Priest: (Piety-1)/6, school 1.
     - Alchemist: (Piety+Luck)/12, school 2.
     - Psionic: (I.Q.+Vitality)/12, school 3.

     A result of 1-3 gives that many first-level points (+0x5c + school*7). It also
     gives known-spell bits 1, 3 or 7 (+0x4c + school*4).
   - EXP: the threshold for the level from G's EXP tables (0x800c8a2c).
8. **Starting gear**, by class, with item ids from I_NAME_E:
   - Slot 0 is `class_start_weapon` (flags 0x7000).
   - Slot 1 is `class_start_armor` (flags 0x6000).
   - With 5% chance (rand_upto(99) > 94), slot 2 is `class_start_extra`. Its flags are
     0x6000 for Fighter, Thief, Samurai, Lord, Valkyrie, Ranger, Alchemist, Ninja and
     Monk, and 0x4000 for the rest. Samurai also gets 0x800. Mage, Priest, Psionic and
     Bishop get item_state 9 for it: the potion's or scroll's uses.
   - Faeries ignore class and always get FAERIE STICK and FAERIE'S CLOTHE, with a 5%
     RING OF JEWELS.

   The flags 0x4000 (identified), 0x2000 (equipped), 0x1000 and 0x800 (hands) are G's
   area; the values here are as the code writes them.

   | Class | Weapon | Armor | 5% extra |
   |---|---|---|---|
   | Fighter | LONG SWORD | LEATHER ARMOR | LEATHER SHIELD |
   | Mage | DAGGER | ROBES | SCROLL OF MAHALITO |
   | Priest | ANOINTED MACE | LEATHER ARMOR | POTION OF DIOS |
   | Thief | SHORT SWORD | LEATHER ARMOR | SANDALS |
   | Samurai | KATANA | LEATHER ARMOR | WAKIZASHI |
   | Lord | LONG SWORD | LEATHER ARMOR | LEATHER GLOVES |
   | Valkyrie | LANCE | LEATHER ARMOR | LEATHER SALLET |
   | Ranger | SHORT BOW | LEATHER ARMOR | FEATHERED HAT |
   | Bard | SLING | LEATHER ARMOR | LUTE |
   | Alchemist | DAGGER | ROBES | SHADOW CLOAK |
   | Psionic | STAFF | ROBES | SCROLL OF MAPOBA |
   | Bishop | STAFF | LEATHER ARMOR | POTION OF LATUMOFIS |
   | Ninja | NINJA-TO | SHINOBI'S ROBE | SANDALS |
   | Monk | ROD | ROBES | SANDALS |

9. **"Use this character?"** Answering no with fewer than 10 bonus points offers
   "Retrain?" (SISETU 0xa7). Yes then gives:
   - "A year has passed." (0xa8)
   - "Happy birthday!" (0x2a)
   - A level-up to level 2, with "Gained a level!" (0x2b). It runs the level-up routines
     0x800b9540, 0x800b9090, 0x800b99dc and 0x800b9e6c, which are E's or G's.
   - Age +1.

   So retraining trades a year of age for a level. It isn't a re-roll.

The unreferenced debug menu at JOUKA 0x800a6c40 toggles `debug_flags` (0x80079560). Bit 4
gives a new character EXP 0xffffffff, and bit 8 gold 0x7fffffff **[code]**. Nothing in
the shipped flow sets them as far as found.

### Changing class

`training_class_change` (JOUKA 0x800b4934) **[code]**.

**The offer.** A class is listed when:
- it's allowed for the character's alignment (`class_alignment`),
- it isn't Valkyrie for a male,
- and it isn't the current class.

Classes whose minimums the character doesn't meet are shown but greyed (flag 0x80) and
can't be picked. The message is "Change to which class?".

**What it does:**
- Level 1, EXP 0, **age +3 years**.
- The class byte keeps the sex bit.
- **Every stat is reset to max(race base, new class minimum).** It's not the stats you
  had, and not the race base plus bonus. For example, a Lord's stats drop to at least 15
  St, 11 IQ, 14 Pi, 15 Vi, 11 Ag and 14 Lu; any higher stats come down to that.
- Every item not marked cursed (bit 0x8000) loses bits 0x3800, which unequips it. Hence
  "Class changed. (Check their equipment.)" (SISETU 0xb4).
- Known spells stay. The new class's school gets its first-level points as at creation,
  and points recomputed as 9 are capped at 4 (0x800b9540, then a clamp).
- `debug_flags` bit 0x10 sets EXP to 0xffffffff.

The old record is kept at 0x80096858 while the confirmation is up. Answering no copies it
back.

`training_rename` (0x800b3e24) is Change Name (SISETU 0xae, 0xaf, 0x9f).

## The save

### On the card

**[code + emu]**
- **One save.** The file is `bu00:BISLPS-02691PSWIZDIM` (MCARD 0x800a1008), two blocks
  (0x4000 bytes).
- **Wrong size.** `card_find_save` erases a save of any other size.
- **Space.** `card_free_space` refuses the save when 14 or more of the 15 blocks are in
  use.
- **Layout.** The file starts with a 0x200-byte "SC" header (icon, title
  "ＷＩＺＡＲＤＲＹ　ＤＩＭＧＵＩＬ" in Shift-JIS). The 0x2400-byte image follows at
  0x200, written 0x80 bytes per VSync. The rest is zeros.
- **Prompts.** The Save screen goes: check, "not formatted, format?", "data found,
  overwrite?", "not enough space, swap the card", "Saving...", "failed", "Stop saving?".
  The strings are SISETU 0x277-0x29c.

### The image

`save_write` (0x800aa1f4) builds the image at `save_image` (0x800f0000), and `save_read`
(0x800aa9e0) restores it field by field **[code]**. `scripts/re/savefile.py` decodes it.
**[emu]** It was checked on `rips/testsave.mcd` and on a save made with Save and Suspend:
the checksums match and the characters, parties and positions are right.

| Image offset | Size | From | Contents |
|---|---|---|---|
| 0x0000 | 0x438 | 0x8008e620 `parties_saved` | 20 party records, 0x36 each |
| 0x0438 | 0xb40 | 0x80086880 | 20 character images, 0x90 each (below) |
| 0x0f78 | 4 each | 0x80079628, 0x800795fc, 0x800796b0, 0x80079b48 | four u32 globals (not identified) |
| 0x0f88 | 4 | 0x80079b44 `story_flags` | bit 31 shows Dragon's Cave; E maps the rest |
| 0x0f8c | 4 each | 0x80079754, 0x80079b28, 0x80079618 | three u32 globals |
| 0x0f98 | 4 | 0x8007986c `progress_bits` | |
| 0x0f9c | 0x20 | 0x80079cb0 | 8 u32 (inferred: event flags) |
| 0x0fbc | 0xd80 | 0x8008c580 | 48 × 24 × 3 bytes: one bit per square, 24 rows of 24, for 48 maps (inferred: the auto-map) |
| 0x1d3c | 0x1a | 0x80089b40 | 26 bytes, 0xff on a new game |
| 0x1d56 | 0x133 | 0x8008a0b0 `boltac_stock` | one byte per item id 0-306 |
| 0x1e89 | 0x27 | 0x8008a040 `items_seen` | only 39 of the bitfield's 40 bytes |
| 0x1eb0 | 4 | 0x80079700 | |
| 0x1eb4 | 1 | 0x80079891 | the roster count |
| 0x1eb5 | 12 | 0x80096378 `config` | settings |
| 0x1ec4 | 0x4a4 | 0x8008a260-0x8008a703 | card game: battle config, card parties, unit, master and option cards |
| 0x2368 | 9 | 0x80087a30 | |
| 0x2371 | 0x1e | 0x80096720 | 3 × 10, `ff40` on a new game (inferred: three names) |
| 0x238f | 0x46 | 0x8008a068 `monsters_seen` | 70 bytes |
| 0x23d5 | 0x20 | 0x8008c4d0 | the mode bytes `mode_bytes_store` writes (0x8008c4d0-0x8008c4d8), and the rest |
| 0x23f5 | 1 | 0x80079a28 | |
| 0x23f6 | 1 | 0x80079b97 | |
| 0x23f8 | 4 | | checksum |

**The checksum [code + emu].** `save_write` zeroes the u32 at 0x23f8, then adds bytes
0..0x23fb into it, one at a time. The last four bytes it adds are the checksum's own,
which by then hold the running sum. In Python:

```python
s = sum(img[:0x23f8])
for k in range(4):
    s = (s + ((s >> (8 * k)) & 0xff)) & 0xffffffff
```

`save_read` restores everything first, then recomputes the checksum. On a mismatch it
sets card_status 0x20. The load screen then prints "The data is corrupt and can't be
loaded." and runs `save_data_reset`, so the corrupt data that was copied in is wiped
straight away.

**The character image (0x90 bytes) [code + RAM compare].** `roster_snapshot` writes it from
the 0xd0-byte roster record, and `roster_restore` reads it back:
- Image +0x00 to +0x7d is roster +0x00 to +0x7d: name, race/alignment, class/sex, status,
  age, stats, gold, pack, item states, EXP, level, HP, spells, the poison counter at
  +0x78, and location.
- Image +0x80 (u32) is roster +0xc0.
- Image +0x84 is roster +0xc4.
- Image +0x85 to +0x8e is roster +0xc5 to +0xce. That includes `met_bits`, +0xc6-0xc8,
  so **NPC meetings are saved**.

Roster +0x0d, +0x19 to +0x1b, +0x3e to +0x3f, +0x7e to +0xbf and +0xcf aren't saved. After
a load the game rebuilds or recomputes them. **[emu]** After loading the test save, roster
+0x00 to +0x8f matched the saved images except +0x84 and +0x86, which are rebuilt fields.

**Parties [code].** The save holds `parties_saved`. On load, `parties_restore` copies it
into `parties`, and any record whose six member slots are all -1 is freed. **[emu]**
After a town save, loading puts the game in town at the Tavern ("Who will join the
party?"). Characters left in the maze aren't in the Tavern's list.

### Continue from RAM

**[code]** The save image stays at 0x800f0000 after saving, and `save_write` sets
`ram_save_valid` (0x800796c6). After that, the title's first option runs game_state
0x36 (`continue_from_ram`) instead of New Game. That routine unpacks the RAM image
(`save_image_unpack`), checks its checksum, rebuilds the roster and parties, and goes to
town, all without reading the card. If the image is bad or `ram_save_bad` (0x80079905) is
set, it prints the corrupt-data message and the title runs New Game instead. Load Data
clears `ram_save_valid`.

**[inferred]** This is the "press O to resume" path after Suspend: if the player resets
to the title without turning the power off, Continue picks up from memory.

### A swap in the mode bytes

**[code]** `mode_bytes_store` (MAIN 0x8001bd0c) runs before each save from game_state
0x32. It writes 0x800796aa to 0x8008c4d7 and 0x8007966a to 0x8008c4d6.
`mode_bytes_load` (0x8001bcd4) runs after a load, and reads 0x800796aa from 0x8008c4d6
and 0x8007966a from 0x8008c4d7. So those two bytes come back swapped. That's harmless
only if they're equal or unused after a load. What they hold isn't known yet. The maze
prints 0x800796aa and 0x8007966a with 0x80079644 in a status line (MAZE 0x800a96b0,
SISETU 0x202), so **[inferred]** they're a date or time counter.

### New game

`save_data_reset` (MCARD 0x800ad018) is the only full reset in MCARD, and it runs only
after a failed checksum. It clears:
- the map bits
- `story_flags`, `progress_bits` and 0x80079754 / 0x80079b28 / 0x80079618
- the event flags at 0x80079cb0
- 0x80089b40
- the party table (current party into slot 0, the rest -1)
- `config` (the language switches to 0, which english_only.asm patches, the rest 1)
- the 0x80096720 names, `roster.area` for six records
- 0x8008c4d0
- Boltac's stock, from each item's +0x1a, its starting stock
- the seen bitfields
- the card game (`FUN_80023e98`)

The title's New Game path sets config bytes 5-7 and goes to town (game_mode 3). Its
initial roster, the six premade characters, comes from code not traced here.

## For the other analysts

- **Everyone: the projects are built from a patched build.** `scripts/re/ghidra.py`
  builds from `rips/q7iso/dimguil` (DISC), which is the Q7 test build. The original Rev 1
  files are `rips/clean/dimguil` (what build.sh starts from). The code files differ at
  our patch sites:

  | File | Bytes changed |
  |---|---|
  | SLPS_026.91 | 1250 |
  | JOUKA | 396 |
  | CMAIN | 278 |
  | CMENU | 234 |
  | HAZURE | 31 |
  | MAZE | 19 |
  | MCARD | 19 |
  | BATTLE | 17 |

  Data tables read out of these files can carry our edits. For tables, read
  `rips/clean`. For anything at a patch site, check `patchsites.py`.
- **G:**
  - The record fields above (+0x0a, +0x0b, +0x10 to +0x18), and the character image's
    mapping to the roster.
  - `party_member_count` (0x80079891) is the roster count, as E noted (now renamed
    `roster_count` in seed.csv).
  - The race base stats table is 0x8005e1e8, 6 bytes per race, 11 races.
- **A:**
  - Investigate (maze menu entry 0) runs MAZE 0x800cc5e0.
  - The maze consumes `next_place` 0xff, 0xfe, 0xf6 and 0xfc.
  - If bodies lose items over time, that would be in the maze, since the save and Edge
    of Town code doesn't do it.
- **C:** "Go On with Another Party" is MCARD 0x800b00c4, in your range.
- **E:**
  - JOUKA 0x800a6c40 is an unreferenced debug menu (nine toggles of 0x80079560).
  - The temple's raise odds may share the vitality rule above.

## How it was traced

1. **Strings first.** HAZURE is small (116 functions). The fastest map came from
   resolving each print call to its text. A small script (`rips/re/work/F/strs.py`)
   matches calls like `FUN_800bc780(0xa6,4,0x13f,1)` against the text tables. The file
   number indexes `text_files` (0x8008a010: 0 STATUS, 1 item names, 3 FIGHTMSG,
   4 SISETU, 6 NPC text). That labelled most of the Edge of Town in minutes: "Which party
   will set out?", "Reborn from which game?", the two Gaiden titles, and so on.
2. **The menu.** The labels come from a table at the start of HAZURE's data. That turned
   up the hidden ninth entry, Dragon's Cave, gated on bit 31 of `story_flags`.
3. **The save.** The save routine copies blocks into 0x800f0000 and writes 0x2400 bytes
   after a 0x200 header. The test save decoded straight away, except for the checksum,
   which was 0xe9 off. Reading the loop again showed why: the sum is accumulated in place
   in the image, so its last four additions are bytes of the sum itself. With that, the
   checksum matched, and it matched again on a second, fresh save.
4. **The roster puzzle.** The image holds 20 records of 0x90 bytes, not the roster's
   0xd0. The pair of copy routines shows which roster fields are saved. NPC `met_bits`
   are among them, which settles whether meetings survive a reload.
5. **Emulator test** (button presses only). START in `maze_door.state`, then Save and
   Suspend. Cold boot, load, and walk to the Edge of Town. The cursor there remembered
   Resume Adventure, which cost one failed run that opened the Save screen instead.
   Resume Adventure then listed the four characters "Out" and put them back on the saved
   square.
6. **Training Grounds.** A search for SISETU's creation prompts found the three JOUKA
   functions. The work record at 0x8008ff10 and the stat array made the rules readable.
   Uranus's status screen fixed the stat offsets. The class list shown in
   `charcreate.state` matched the bonus-point rule.

## Translation impact

- **"Sane" (STATUS.OBJ 0xd0).** This is the disc's own English label for status bit 0x02,
  こんらん (confused). It has no translation, so with the language locked on English,
  confused characters show "Sane" on the Tavern, Training Grounds and Look for Companions
  lists. It's probably a slip for "Insane" (Wizardry's usual word) or should be
  "Confused". Worth a look.
- **"Retrain?" (SISETU 0xa7).** This isn't a re-roll. It's offered when declining a new
  character with under 10 bonus points. Yes ages them a year and gains a level ("A year
  has passed. Happy birthday! Gained a level!"). An English player may well read
  "Retrain?" as "start over". Something like "Train for another year?" would say what it
  does.
- **"Suspend Game" (Edge of Town) and "Save and Suspend" (maze)** both save to the card;
  Suspend Game doesn't quit. The labels are fine. The walkthrough could say plainly that
  this is how you save.
- **The Book of Movement's choices (SISETU 0x274-0x275)** are the Gaiden III and IV
  subtitles in English, "-Scripture of the Dark-" and "-Throb of the Demon's Heart-",
  already English on the disc.
- **"There are faint traces, but no one was found." (SISETU 0x140)** is accurate: it means
  bodies are within one square but not on yours. Players hunting for a wiped party may
  want that spelled out in a walkthrough.
- **NPC meetings are saved** (met_bits), so first-meeting lines don't replay after a
  reload. That bears on which NPC greetings a player sees.
