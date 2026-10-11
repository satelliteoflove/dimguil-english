# E. The town (JOUKA.BIN)

What the castle town's code does: the tavern, the inn, Boltac's, the temple, the King,
the Fortune Teller, and how characters come back from the maze. This is analyst E's
part of the rules-first code analysis (see `docs/code-map.md`). Addresses are RAM, and
the town overlay JOUKA loads at 0x800a1000. Names are in `scripts/re/symbols/town.csv`.
Some were named by analyst G first, in `records.csv`: the level-up routines, `hp_roll`,
`hp_dice`, `spell_point_rules`, `race_base_stats`, `current_members`.

Every claim is marked:
- **[code]**: confirmed by reading the decompiled code
- **[emu]**: confirmed in the emulator (RAM reads, breakpoints, screenshots)
- **[inferred]**: not confirmed

The emulator checks used `temple_pay.state`, `shop_gold.state` and `inn_gold.state` from
`rips/states`. Their gold was seeded by RAM edits when they were made, so they're
test fixtures, not natural play. Nothing in these tests wrote to RAM. These old states
also hold an older build's SISETU text: the screen said "hath been reduced to ash!",
which isn't in today's translation. Read their wording as stale.

## How the town code is laid out

- `town_main` (0x800a2198) is the routine main calls every frame in town. Its state is
  `town_state` (0x80079b18). [code]
  - States 1 to 5 are the arrival and the main menu.
  - Then each facility gets 10 + 5 × its menu position: tavern 10, inn 15, Boltac's 20,
    temple 25, Training Grounds 30, King 35, Edge of Town 40.
  - State 45 is the King's ending scene.
- Each facility has its own entry point and a sub-state:
  - entry points: `tavern_main` 0x800a79d4, `inn_main` 0x800c51e0, `boltac_main`
    0x800ba6e0, `temple_main` 0x800c8b50, `training_main` 0x800ae0c0, `king_audience`
    0x800a4898
  - sub-state: 0x80079669 (B named it `camp_state`; town uses the same byte)
  - each screen also has its own state byte: `temple_heal_state` 0x80079984, `inn_state`
    0x8007998b, `shop_state` 0x800797a4
  - [code]
- Text goes through three helpers.
  - `town_print` (0x800dbd7c): (x, y, file, string, layer)
  - `town_bar_print` (0x800dba48): (y, file, string, layer), centred
  - `town_text_expand` (0x800dbac8): (file, string), for the long story boxes
  - "File" indexes `text_files` (0x8008a010), set at boot by 0x8001d570: 0 STATUS.OBJ
    (0x801ce800), 1 item names, 3 FIGHTMSG, 4 SISETU, 6 NPC text.
  - So "SISETU n" below is `town_*_print(..., 4, n, ...)`, and "STATUS n" is file 0. [code]
- `menu_input` (0x800a471c) reads the cursor for a menu grid. It returns 4 on confirm and
  2 on cancel. [inferred]
- The town RNG keeps moving: `town_main` calls `rand_upto(2)` every frame (from
  0x800a2264). So every random result in town depends on how many frames pass first.
  [emu: breakpoint on rand_upto's return, 0x8001cba8]
- `rescue_candidates` (0x8008d300, with its count `rescue_candidate_count` 0x80079895) is a
  shared scratch list, not only for the NPC rescue. The town reuses it for:
  - the temple's patient list
  - the tavern's "who can join" list
  - the recruit pool
  - the list of bodies announced when a party comes home
  - [code]
- 0x80079891 (seed.csv calls it `party_member_count`) counts **roster entries**, not
  party members. [code]
  - The temple, tavern and recruit loops run over roster indexes up to it.
  - Recruiting writes the new character at `roster[it]` and adds one.
  - `roster_compact` (0x800dcb70) recounts it after deleting.
  - The real party count is `current_party_count` (0x8007e811).

### Which strings each function prints

`scripts/re/strmap.py` lists, for each function of a module, the SISETU and STATUS
strings it prints with a constant index. In short:

| Strings (SISETU) | Function |
|---|---|
| 6-11, 25, 27 join; 12 remove; 13 inspect; 14, 24 gold | `tavern_add_member` 0x800a846c, `tavern_remove_member` 0x800aa0a4, `tavern_inspect` 0x800aa444, 0x800aa848, 0x800aa95c |
| 15, 35 table | `tavern_table` 0x800aab28 |
| 18, 28, 381, 382; bios 361-380 | `tavern_recruit` 0x800ab08c |
| 38-43, 57, 84, 579, 580 | `inn_stay` 0x800c5e34 |
| 44-56, 67-78, 581, 582 | `levelup_messages` 0x800b9f8c |
| 65, 66 old age | `inn_stay` |
| 79-145 | Boltac's: `boltac_menu` 0x800bae4c, `boltac_buy` 0x800bb914, `boltac_sell` 0x800bf9ec, `boltac_uncurse` 0x800c0ef4, `boltac_identify` 0x800c1de8, `weapon_compare` 0x800c2b84 |
| 146-157, 583-586 | `temple_main`, `temple_heal` 0x800c95f0, `temple_retrieve` 0x800cb274, `temple_drop_off` 0x800cba20 |
| 158-183 | Training Grounds: `training_create` 0x800af5d8, `training_view` 0x800b264c, `training_delete` 0x800b32d4, `training_rename` 0x800b3e24, `training_class_change` 0x800b4934, `training_reorder` 0x800b6eec |
| 322 | `king_ending` 0x800a52cc |
| 323-329, 360, 418 | `king_audience` |
| 330-359, 399 | `fortune_teller` 0x800ac684 |
| 394, 14, 427, 614, 11 | `town_main` |

## Coming home from the maze

When a party arrives back in town, `town_main` does the following. [code]

1. Sets every member's location byte to 0xff, which means "in town".
2. Goes through the party:
   - A member with status below 0x20 and HP above 0 is cleared to status 0. That drops
     the minor conditions in bits 0x1f: afraid, confused, poisoned, asleep, K.O.
   - A member with status below 0x20 but HP of 0 or less is marked dead (0x80).
   - Every member at 0x20 or above (paralyzed, stoned, dead, ashes) leaves the party
     and goes into `rescue_candidates`.
3. Strips the RING OF MEDIUM (item 0x142) from any member who carries it and goes to the
   ending (state 45). That matches the walkthrough: the King sends for the party the
   moment the ring reaches town.
4. Announces each body in turn with SISETU 614, "{name} was carried to the temple."

So 614 is **not** the NPC rescue. It's the bodies a surviving party brings home. [code]

- The same "all of them out of action" check (`party_down_count`, 0x800dbcd0) also runs
  in two places, which then empty the party into the temple the same way:
  - town state 35, the King's menu item, before the audience starts
  - the inn, after a death from old age
  - [code]
- **Bodies an NPC party carries back.** `talk_balbo` and the others only set the
  location to 0xff. The temple's list takes anyone at 0xff with status 0x20-0x1ff who
  isn't in the party, so those bodies show up in the temple, still dead, with no
  message in town. [code: `temple_main` list, against the fee loops in engine-notes]
- **Time decay, for Chris's question.** Nothing in JOUKA changes the items, gold or
  status of a character whose location isn't 0xff. [code]
  - JOUKA writes items only in a few places: Boltac's (buy, sell, uncurse, identify),
    equipping and trading, the ring taken in step 3, and blanking a deleted or lost
    record (`roster_clear_entry` 0x800dccc4).
  - Time does pass in HAZURE: 0x800a4ef8, line ~1058 of its C, adds weeks and can make
    a character Lost on a VIT roll. That's analyst F's.
  - Whether the maze or HAZURE wears anything away is for A and F.

## The temple (Temple of Cant)

### Menu and patient list

`temple_main` (0x800c8b50). [code, emu]

- The menu: 0 Heal Character, 1 Retrieve Character, 2 Drop Off Character, 3 back.
- The patient list is every roster entry that:
  - isn't Lost (no bit 0x200)
  - is in town (location 0xff)
  - has status 0x20 or more
  - isn't in the current party
- A dead member who is still in your party isn't on the list. You drop them off first:
  `temple_drop_off` takes a party member whose status is 0x20 or more. [emu: in
  `temple_dead.state`, Uranus (dead, in the party) went from the party to the temple]
- Retrieve (`temple_retrieve`) takes a patient back into the party. It's refused if the
  party is full (SISETU 149). [inferred from the strings]

### Healing costs

`temple_heal` (0x800c95f0). The fee is set by the worst condition. [code]

| Condition | Status bit | Fee |
|---|---|---|
| Paralyzed | 0x20 | level × 100 |
| Stoned | 0x40 | level × 200 |
| Dead | 0x80 | level × 250 |
| Ashes | 0x100 | level × 500 |

[emu] For Uranus (level 5) the screen showed 1250 G dead and 2500 G as ashes.
Venus's gold dropped by exactly those amounts.

- One party member pays (SISETU 148). If they can't cover it and the party has two or
  more members, the game offers to pool the party's gold to them (SISETU 84).
- The fee is taken after the chant (SISETU 583-586, "pray - whisper - chant - invoke")
  and before the roll, so a failed raise is still paid for. [code, emu]

### Outcomes

Here r = `rand_upto(99)` (0-99) and VIT = roster +0x16. [code]

- **Paralyzed or stoned:** always cured. Status 0, HP unchanged, SISETU 153 "is healed".
- **Dead:**
  - if r < 60 + 2 × VIT: alive with **1 HP** (SISETU 155)
  - otherwise: **ashes** (status 0x100, SISETU 156)
  - [emu, VIT 14 so the line is 88: rolls 78, 49, 46, 31 raised Uranus to 1 HP; a roll
    of 90 turned him to ashes]
- **Ashes:**
  - if r < 68 + 2 × VIT: alive with **full HP** (SISETU 155)
  - otherwise: **Lost**
  - [emu, the line is 96: rolls 9, 45, 28, 41, 7, 35, 74, 71, 56, 81, 8, 6, 33, 64 and
    more all raised Uranus with HP 30/30. No roll reached 96 in 55 tries.]
  - So in Dimguil, ashes are *easier* to raise than a dead body, by 8 points.
- **When Lost** (the Lost branch is code only):
  - status becomes 0x200
  - the name is blanked to ff40, which deletes the character
  - SISETU 157 "is lost forever"
  - the name goes into `lost_names` (0x80096720), the last three characters lost; the
    oldest is pushed out
  - MAZE, BATTLE and the MCARD talk handlers (0x800b21f0, 0x800cd600) read `lost_names`
    too, so some NPC talk may mention lost characters (for C)
- **After any success:** SISETU 154 "went back to the tavern", location 0xff, status 0.
  They can then join a party again.
- VIT is the stat Vitality (`stats[3]`). SISETU 217's description says the same: it
  affects "the odds of coming back from death". [code]

## The inn (Adventurer's Inn)

`inn_stay` (0x800c5e34). Room numbers as in STATUS 9-14. [code; emu for the Stables and
the Merchant Suite]

| Room | Cost | Each week |
|---|---|---|
| The Stables | free | spell points back, no HP, one *day* older |
| A Cot | 10 G/week | +1 HP |
| Economy Rooms | 50 G/week | +3 HP |
| Merchant Suites | 200 G/week | +7 HP |
| The Royal Suite | 500 G/week | +10 HP |
| Special Room | 10000 G/week | HP to full |

- Characters with status 0x20 or more can't stay. [code]
- **Paid rooms** run in weekly ticks. Each tick:
  - charges the room price
  - ages the character a week (`age_weeks` +0x11)
  - adds the HP
  - restores spell points (`spell_points_recalc`)
  - The stay ends when HP is full or the player cancels.
  - Even a character already at full HP pays for one week and ages one.
  - [emu: Uranus, full HP, Merchant Suite: 50000 → 49800 G, weeks 16 → 17]
- **The Stables** add one day (`age_days` +0x12), restore spell points, and charge
  nothing. [emu: days 16 → 17, gold unchanged]
- **Ageing:** 7 days make a week and 52 weeks make a year (`age_years` +0x10). A new
  year shows SISETU 42, "Happy birthday". [code]
  - The checks are `== 7` and `== 52`, not `>=`.
  - The six premade characters start with all three age bytes at 16. So their day
    counter can't roll into a week until it wraps past 255, which takes about 240
    nights in the Stables. [emu read; the effect is inferred]
- **Level-up:** one chance per stay, after resting. [code]
  - If `can_level_up` (0x800c8b10) passes, level and max level go up by one.
  - Then four routines run (G's names): `spell_points_recalc`, `levelup_learn_spells`,
    `spell_points_recalc` again, `levelup_stats_age`.
  - If the character survives, `levelup_max_hp` runs, then `levelup_messages`
    (SISETU 43 and the stat lines).
  - Otherwise SISETU 579/580 shows the EXP still needed. [emu: "To next lvl: 2950 EXP"]
  - The inn copies the record before the level-up into `roster_scratch` (0x80096858)
    and shows it. [code]

### What a level-up does

These were also named by G. The rules as read here: [code]

- **Stats** (`levelup_stats_age`, 0x800b99dc). Each of the six stats (+0x13..+0x18:
  STR, IQ, PIE, VIT, AGI, LUC) gets a 76% chance of being tried (rand 0-99 < 76).
  - **If rand 0-59 < age in years, the stat may fall:**
    - It can't fall below 4.
    - It falls by one if it's below `rand_upto(14 + race base − 1)` (15 for a male's
      STR or a female's VIT) and `rand_upto(level)` > 3.
    - If VIT is already below 4 when this happens, the character **dies of old age**:
      status 0x200 (Lost, not dead) and HP 0. The inn shows SISETU 65/66, the name
      joins `lost_names`, and the record is deleted.
  - **Otherwise it may rise:** by one if it's below race base + 10 (+11 for a male's
    STR or a female's VIT) and below `rand_upto(41)`.
  - Race bases are in `race_base_stats` (0x8005e1e8, G's row), in the order STR IQ PIE
    VIT AGI LUC. They match Wizardry VII's:
    - Human 9 8 8 9 8 8; Elf 7 10 10 7 9 8; Dwarf 11 6 10 12 7 7
    - Gnome 10 7 13 10 6 7; Hobbit 8 7 6 9 10 11; Faerie 5 11 6 6 14 11
    - Lizardman 12 5 5 14 9 7; Dracon 10 7 6 12 8 8; Rawulf 8 6 12 10 8 9
    - Mook 10 10 6 10 7 8; Felpurr 7 10 7 7 12 10
  - SISETU 195/196 describe this sex difference ("the race's STR goes up by 1" for men,
    VIT for women). In the level-up code it's a +1 on the stat's cap.
- **HP** (`levelup_max_hp`, 0x800b9e6c, and `hp_roll`, 0x800ba5b0).
  - The new max HP is one roll per level, all re-rolled; Samurai and Monk get one
    extra. It's always at least the old max + 1, and the gain is added to current HP.
  - A roll is base + `rand_upto(sides − 1)` from `hp_dice` (0x800a138c, per class:
    Fighter 3+0..6, Mage 1+0..2, Priest 2+0..5, Thief 2+0..3, Samurai 3+0..5, Lord
    3+0..6, Valkyrie 3+0..6, Ranger 2+0..5, Bard 2+0..3, Alchemist 1+0..2, Psionic
    1+0..2, Bishop 2+0..3, Ninja 2+0..3, Monk 2+0..3).
  - The VIT modifier:
    - VIT 3: −1
    - VIT 4-5: +0
    - VIT 6-15: +1
    - VIT 16 and up: +1 + (VIT − 15)
    - The roll is at least 1.
- **Spells** (`levelup_learn_spells`, 0x800b9090).
  - For each school and spell level the character has points in, each unknown spell
    of that level is learned if `rand_upto(29)` < the school's stat:
    - Mage: IQ
    - Priest: PIE
    - Alchemist: (IQ + LUC) / 2
    - Psionic: (IQ + VIT) / 2
  - Learning any spell sets the "new spell" message (SISETU 56).
- **Spell points** (`spell_points_recalc`, 0x800b9540). Per caster class, a
  (school, first level, step) triple from `spell_point_rules` (0x800a133c). At level L,
  spell level j gets L − first − step × j points, capped at 9, and never fewer than the
  spells known at that level (1, 2, or 4 when all three are known). The Bishop gets two
  triples (Mage 0/4, Priest 3/4). [code]
  - The table is indexed by a class remap: Mage 0, Priest 1, Bishop 2 and 3, Lord 4,
    Samurai 5, Valkyrie 6, Bard 7, Alchemist 8, Ranger 9, Ninja 10, Monk 11, Psionic 12.
  - Its triples: Mage 0,0,2; Priest 1,0,2; Bishop 0,0,4 and 1,3,4; Lord 1,3,2;
    Samurai 0,3,3; Valkyrie 1,3,2; Bard 0,3,2; Alchemist 2,0,2; Ranger 2,3,2;
    Ninja 2,6,3; Monk 3,6,3; Psionic 3,0,2. School 0 Mage, 1 Priest, 2 Alchemist,
    3 Psionic.

## Boltac's Trading Post

[code; emu for selling]

- **Buy** (`boltac_buy`, 0x800bb914).
  - The price is `item_table[id].price`.
  - The bought item is identified (word | 0x4000).
  - Potions and scrolls (subtype 0x14/0x15) come with 5 uses (item_state 5).
  - The stock byte (`boltac_stock`) drops by one if it's positive; −1/0xff means
    unlimited. SISETU 125 "That's the last one" when it reaches 0.
  - Selling out an item clears flag 0x40000000 of 0x80079b44.
  - Buying an item with a positive +0x21 byte adds it to roster +0x8b. [inferred: a
    carried bonus, G's field]
  - The beginner/intermediate/advanced sets (SISETU 114-117) are per class. They need
    five free slots and cost the sum of their items.
- **Sell** (`boltac_sell`, 0x800bf9ec).
  - Refused for:
    - price 0 (SISETU 96 "can't be sold")
    - an unidentified item, no bit 0x4000 (SISETU 97)
    - a cursed item, bit 0x8000 (SISETU 113)
  - An equipped item (0x2000) asks first (SISETU 98).
  - It pays **price / 2**. Potions and scrolls pay price / 10 × uses left.
  - Stock goes up by one (potions and scrolls go to unlimited).
  - The item is marked seen for the catalog.
  - [emu: Uranus sold his equipped PLATE MAIL, price 1500: gold 50000 → 50750, stock 1 → 2]
- **The free item.** If a sale leaves nothing sold out (all 307 stock bytes non-zero)
  and the flag is clear:
  - Boltac gives a free item 0x133, the BOOK OF MOVEMENT, with SISETU 127 ("Why,
    nothing's sold out any more!").
  - The flag is set again until something sells out.
  - So it can happen more than once.
  - [code]
- **Dispel Curse** (`boltac_uncurse`, 0x800c0ef4).
  - Costs price / 2. Items 0x133-0x143, the event items, use `item_table.sell`
    instead.
  - The cursed item is **destroyed**, as in the old games, not freed.
  - A negative +0x21 bonus is taken off roster +0x8b. [inferred field]
- **Identify** (`boltac_identify`, 0x800c1de8). Costs price / 2 and sets 0x4000.
- **Compare Weapons** is `weapon_compare` (0x800c2b84, G's name), SISETU 129-145.

## The tavern (Gilgamesh's Tavern)

- **Add to party** (`tavern_add_member`). [code]
  - Lists characters with status below 0x20 who are in town and not already in the
    party. The dead and anyone left in the maze can't join.
  - The party keeps each slot's alignment as it joined (0 good, 0x40 neutral, 0x80
    evil, at current party +0x0e, 0x8007e820).
  - Alignment rules (SISETU 9, "Their alignments won't mix"):
    - good is refused if the party has an evil member
    - evil is refused if it has a good member
    - neutral always joins
    - nobody joins a party that already mixes both
- **Recruit Members** (`tavern_recruit`, 0x800ab08c). Twenty built-in characters can
  turn up. [code]
  - Their bios are SISETU 361-380 (recruit n uses 361 + n).
  - Their names are a JOUKA table at 0x800a1178. A recruit whose name is already in the
    roster isn't offered.
  - Whoever joins is marked in `recruits_joined` (0x80079700). Each visit picks one at
    random from the current pool:
    - Always, unless the party mixes good and evil: recruits 2, 7, 10, 12, 14, 16, 17
      (7 people).
    - When **any of your parties is wiped out**, all its members at 0x20 or more:
      recruits 4, 5, 6, 18.
    - After `progress_bits` 0x10:
      - with no evil in the party: 1, 11, 13
      - with evil and no good: 0, 9, 15, 19
    - When a party member has roster +0xc5 bit 1, the same bit that unlocks the
      Fortune Teller's "The End" topic: recruit 8.
    - When 0x80079754 bit 0x800000 is set: recruit 3.
  - This matches a player's count on Emonoya's message board in June 2000, word for
    word: 「最初N7+全滅G2E2+中盤G3E4+クリア後N1=19人」 ("7 at the start, + 2 good and
    2 evil after a wipe, + 3 good and 4 evil midway, + 1 neutral after clearing = 19").
    Another post that month: 全滅させちゃうと３人ばかり増えますよ ("wipe out and a
    few more turn up"). (`rips/research/bodies/bbs_divvy008.html`)
  - The 20th is recruit 3, behind the 0x80079754 flag.
  - When nobody is available, SISETU 381 "No one came".
- **Viewing a dead character's items.** The Training Grounds' view (`training_view`,
  0x800b264c) steps through every roster entry with no status check. So a dead or
  maze-bound character's items can be seen there. [code; not tried in the emulator]
  The tavern's inspect lists only the party.

## The King

`king_audience` (0x800a4898). The King gives one of these lines per visit. They're
tried in this order, and the first that applies is used. [code]

1. A member has roster +0xc5 bit 1: SISETU 325 ("You seem to be training hard, take
   your rest"). The party's spell points are restored.
2. 0x80079b44 bit 0x400 is set, the reward hasn't been given (0x80079b28 bit 0x40000),
   and no member has +0xc5 bit 4: SISETU 326 ("So the Shrine's underground was not of
   this world..."). **Every member gets 10000 G**, once per game.
3. 0x80079b44 bit 8 is set and a member lacks +0xc5 bit 8: SISETU 327 (the quakes have
   stopped, the lake has its magic back). Sets bit 8.
4. A member already has +0xc5 bit 0x10: SISETU 328 ("Have you learned anything?").
5. Otherwise SISETU 329 (the order to go to the Shrine and rescue the Priestess). Sets
   bit 0x10 on everyone.

SISETU 324 ("there's nothing more to do?") fully heals the party and restores spell
points. It's set from another state, not this list. [inferred] SISETU 323 is the
greeting.

## The Fortune Teller

`fortune_teller` (0x800ac684). Free. [code]

Topic n shows title SISETU 345 + n and text 331 + n. The topics open with story flags:

| Topic | Title | Opens with |
|---|---|---|
| 0 | 事の起こり (how it began) | always |
| 1 | 巫女と祭壇 (the Priestess and the altar) | always |
| 2 | 古き友 (an old friend) | `progress_bits` 4 |
| 3 | 仮面 (the mask) | `progress_bits` 8 |
| 4 | 冷凍庫 (the freezer) | 0x80079754 bit 0x20000000 |
| 5 | 奇妙な機械 (a strange machine) | 0x80079b44 bit 8 |
| 6 | 黄金の戦士 (the golden warrior) | `progress_bits` 0x10 |
| 7 | 幽閉されし者 (the imprisoned one) | 0x80079b44 bits 0x300 |
| 8 | 輪の扉 (the ring door) | 0x80079b44 bit 0x1000 |
| 9 | 作られた神 (the made god) | 0x80079b44 bit 0x800 |
| 10 | 神の名 (the god's name) | `progress_bits` 0x100 |
| 11, 12 | 奇妙な装置 (a strange device), 邪神 (the evil god) | 0x80079b44 bit 0x400 |
| 13 | 終わり (the end) | a party member has roster +0xc5 bit 1 |

`progress_bits` is 0x8007986c. Which events set these flags is analyst A's to map.

## Training Grounds

The Training Grounds code is in JOUKA, not HAZURE: create, view, delete, rename,
change class and reorder. The functions are named in town.csv and records.csv. Their
rules (creation, bonus points, class change) were left to analysts F and G and aren't
written up here. [code: the strings each prints]

## Translation impact

What the game's text says about itself, checked against the code:

| Text | Says | Code |
|---|---|---|
| SISETU 58 | Stables: "Restores MP only. No HP." | true |
| SISETU 59-63 | room rates and HP per week | true |
| SISETU 63 | the Special Room "restores all HP for 10000G a week" | true; one week is always enough |
| SISETU 217 | VIT affects max HP on a level up and the odds of coming back from death | true (`hp_roll`, `temple_heal`) |
| SISETU 195/196 | men +1 STR, women +1 VIT | true for the level-up cap |
| SISETU 117 | a set needs five free slots | string shown by the buy code; the slot check wasn't read |
| SISETU 154 | "went back to the tavern" after a raise | true: location 0xff, joinable |
| SISETU 614 | "was carried to the temple" | shown only for bodies your own party brings home, not NPC rescues |
| SISETU 127 | Boltac's gift when nothing is sold out | true, item 0x133 (BOOK OF MOVEMENT), can repeat |
| SISETU 65/66 | "has died of old age" | the character is **Lost** and deleted, not dead |

- **Rosea, NPC_MES2 130** ("Revival at the Temple has better odds..."). The Temple's
  odds for the dead are 60 + 2 × VIT percent. A failure means ashes, which is then
  68 + 2 × VIT. Whether that beats Rosea's own Kadorto depends on her spell's formula.
  Her healing in `talk_balbo` picks script blocks; the result is in the talk script
  opcodes, which are analyst C's. So her claim isn't settled here. If her Kadorto turns
  out to be a flat or lower chance, the line is true as written.
- The bodies an NPC party carries back appear in the Temple with no message. Text that
  says they're "carried to the Temple" (Balbo's 142, the log lines) matches what the
  code does.

## How it was traced

- **Finding the strings.** The town prints through two wrappers around `text_expand`.
  Once those were found, a regex over the decompiled C mapped every constant SISETU and
  STATUS index to its function. That gave a ready-made map of which screen is which
  (`scripts/re/strmap.py`). The facility functions fell out of it, along with the state numbers in
  `town_main`.
- **Reading the rules.** The temple and inn are big state machines with one state per
  screen step, so the rules sit in a few states each:
  - the temple's fee switch and its 'Z' and '_' rolls
  - the inn's ')' and '-' states
- **Checking in the emulator.** A breakpoint on `rand_upto`'s `jr ra` (0x8001cba8)
  logged every roll with its caller.
  - That showed the town rolls `rand_upto(2)` every frame.
  - Each temple raise logged exactly one `rand_upto(99)` from 0x800cacb0 (dead) or
    0x800cadb4 (ashes).
  - Waiting different numbers of frames before the same button presses gave different
    rolls. That made it possible to check both sides of each threshold from one save
    state without touching RAM.
  - Results are in `rips/re/work/E/ashes_rolls.txt`, and the shots are `t*.png`,
    `s1_sheet.png` and `i1_sheet.png` in that folder.
- **The recruit pools.** The pool code had a nice outside check. A June 2000 message
  board post tallied the recruits by alignment and timing, and its numbers match the
  code's pools exactly.

## Open

- **Rosea's claim.** Her Kadorto's odds (analyst C, talk opcodes).
- **Time decay.** HAZURE's 0x800a4ef8 adds weeks and can make a character Lost on a
  VIT roll (rand 0-80 < VIT × 4). It may be the Edge of Town's rescue or rebirth path
  (analyst F).
- **Fields for analyst G.** roster +0x8b (item bonus total), +0xc5 (King and story bits
  1, 4, 8, 0x10), 0x80079b44 and 0x80079754 (story flags).
- **Shared variables.** 0x80079669 and 0x80079a5a are shared by town and camp and have
  camp names (`camp_state`, `camp_char`). Generic names would read better in town code.
