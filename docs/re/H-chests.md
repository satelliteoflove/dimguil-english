# Chests and loose loot after fights

Read 2026-10-15 from the clean disc's BATTLE code, checked against the harness and
human-play logs and the Japanese sites. The code details are in engine-notes.md,
"Treasure after a fight: chest, loose loot or gold". Scripts: `scripts/trebox.py` (the
reward table and each monster's reward bytes) and `scripts/chesttally.py` (the harness
counts).

## Short answer

Dimguil doesn't roll for a chest. What a won fight gives depends on how it started:

- **Fight square** (the fixed encounter squares; each fires once per floor visit at
  80-100%): always a chest.
- **Moving red magic circle, ordinary monsters:** gold, never an item, no chest.
- **Magic circle that turns out to be a party** (Kobolds, Orcs, Ogres, Arch Fighters and
  so on), **or a fight with an NPC party:** gold and often items, dropped loose.
- **Story fights, guardians, the Training Maze:** nothing.

How much comes from the first group's monster (or the party leader): one of 30 reward
records. The floor only matters through which monsters live there.

So the chest rate per fight is the share of fights that come from fight squares. Most
fights come from the magic circles (up to 16 per floor, placed again on every arrival,
wandering the floor), so chests feel rare. In the harness, where the square was known,
209 of 838 non-story fights (25%) had a chest; Chris's own session had 0 of 9, the
human-play bot 2 of 12. The harness numbers follow the bot's routes, so they say little
about normal play.

| Game | Chest after a won fight | Loose items (no chest) | Source |
|---|---|---|---|
| Dimguil | 100% on fight squares; 0% from magic circles, parties and story fights | yes: party tokens and NPC parties (gold and items); ordinary magic circles pay gold only | code (this file) |
| Wizardry I | room (fixed-fight square) table a chest for 95 of 101 monsters; wandering table gold only for 99 | only Werdna's table | Apple II/DOS p-code and data, via the site's reading |
| Wizardry II | room table a chest for 73 of 78; wandering gold only for 73 | 5 guardian tables (the Knight's armor) | same |
| Wizardry III | room table a chest for 70 of 78; wandering a chest for 33 of 78 | 4 tables, about 14 monsters | same |
| Wizardry IV | no fight treasure tables; enemy adventurers carry packs | n/a | site, author's tables |
| Wizardry V | chests only in treasure rooms (35-69% of a floor's rooms, drawn each visit): room table a chest for 142 of 175; wandering 22 of 175 | a few special tables (Kong, Fay, the Fire King and Queen) | p-code and cartridge reads, via the site |
| Wizardry VI | none from fights; chests are fixed map squares | yes, every item from a fight | SFC code read, via the site |
| Wizardry VII | 2 of about 250 monster tables are chests | yes, almost all | DOS data, via the site (partly read) |
| Gaiden I-III | room table a chest for most monsters (113/128, 115/129, 173/193); wandering mostly gold only | a few special tables | emonoya's tables, not checked in code |
| Gaiden IV | room table a chest for 395 of 452; wandering gold only for all 452 | none | emonoya's tables, not checked in code |
| Llylgamyn Saga bonus dungeon | both tables a chest for 89 of 94 | 3 tables | emonoya's tables, not checked in code |

The earlier games' figures are per monster, not per fight. No measured per-fight chest
rate turned up for any of them; how often you fight in rooms decides it, and any "one
fight in N gives a chest" figure for I-V is folklore. Dimguil's rule is Wizardry I's
(wandering fights pay gold only, fixed-fight squares give chests) with one new case: the
loose drop from party fights.

## Evidence

### The code (BATTLE, Rev 1)

1. `battle_main` 0x800a2cd8 enters the chest phase ('B', `chest_open` state 5) only if
   the party didn't flee, `0x80079b51 & 0xc0` is clear, `encounter_id` is 0xffff or
   0xfffe or `encounter_source` is 4, and the area isn't the Training Maze
   (FUN_800c9600). Story, guardian and other event fights set their own ids and skip it.
2. `chest_present` 0x800cb9e4 refuses the Training Maze and ids 0x91-0xab; otherwise it
   sets `0x80079954 = 0x800da74c - 1`.
3. `fixed_battle_setup` 0x800b4eb8 sets 0x800da74c from monster record +0x83: group 1's in
   an ordinary fight (0x800b57ec), the leader's in a party layout (0x800b58b0). emonoya
   says the same ("通常の敵では先頭グループで現れたモンスターによって決まる"; for parties
   and NPCs, the leader's).
4. `chest_open` state 5 loads TRE_BOX.BIN (table 1 index 0x1b8) to 0x801c5400. If
   `0x80079954 < 30` and `encounter_source == 2`, it loads the chest model
   (FUN_800152fc) and runs the trap pick and chest menu; otherwise it goes straight to
   state 0x50, `chest_loot` with no chest.
5. `chest_loot` 0x800c7fd0 always pays gold, and pays items only when the record's +0 is
   1 and the source is 2 or 4 or `encounter_id` is 0xfffe. Fight squares are source 2
   (`square_arrive`, MAZE 0x800ba48c); every token is source 0 (`roamer_meet`, MAZE
   0x800abbac), id 0xffff for an ordinary magic circle and 0xfffe for a party token; NPC
   parties are source 4.
6. Leave on the chest menu returns without `chest_loot`, so no gold either. A trap that
   goes off still pays. After an Alarm trap's fight, 0x80079784 = 1 makes `chest_open`
   skip the chest and pay the original chest's loot.

| Fight | source / id | Chest | Gold | Items |
|---|---|---|---|---|
| Fight square | 2 / 0xffff | always | yes | per record |
| Magic circle, monsters | 0 / 0xffff | never | yes | never |
| Magic circle, party (MPT01-39) | 0 / 0xfffe | never | yes | per record, loose |
| NPC party fought (NPT00-15) | 4 | never | yes | per record, loose |
| Training Maze, story, guardians, fled | | never | no | no |

### The reward records (DATA03/TRE_BOX.BIN)

30 records of 0x5c bytes (2,760 bytes exactly), in Wizardry I's TREWARD shape: +0 item
flag (1 in all 30), +4 trap bits; three item slots with a u32 each for chance (+8), base
(+0x14), step (+0x20), max steps (+0x2c), range (+0x38) and step chance (+0x44); gold dice
at +0x50, multiplier +0x54, second dice +0x58.

A slot pays on `rand_below(85)` <= chance, so a printed N% really pays (N+1)/85 (20 is
25%, 80 is 95%). The step walk goes on while `rand_below(90)` <= the step chance. The
chance of at least one item is 47% for record 1, 80-90% for records 7-25 and 100% for
record 30. The gold ranges match emonoya's table exactly (record 1: 42-90; record 30:
910-27,950).

Monster +0x83: every monster in the maze encounter tables has 1-30; the 29 with 0 are event
monsters (145-173). Parties MPT01-39 use 1-25, rising with depth (Goblin 1 up to Arch Ninja
25); MPT08, the Diamond Knights, has 0. NPT00-15 use 1-25.

### Measured: harness chapter logs

6,445 won fights in 54 logs. The log doesn't record how a fight started, so each was
classed by joining `where` with the fight squares in the site's maps (event type 0x14) and
treating group ids 340 and up as parties.

| Fight | All | Chests | Deduped | Chests |
|---|---|---|---|---|
| Monsters on a fight square | 217 | 217 | 209 | 209 |
| Monsters off any fight square | 584 | 0 | 557 | 0 |
| Party tokens | 431 | 0 | 72 | 0 |
| Story fights | 425 | 0 | 376 | 0 |
| Square unknown (older log format) | 4,788 | 2,061 | 965 | 449 |

Deduped counts a replay of the same fight in the same run once. By area (deduped, square
known), chests of fights: Grounds 59/129; A-B4 4/14; A-B3 51/101; B-B5 2/55; B-B4 91/299;
B-B3 2/228; B-B2 0/166; B-B1 0/165; Shrine 3F-4F 0/27. Every chest was a fight-square
fight. The chapter logs don't record loot without a chest.

### Measured: human play

chris1/log.jsonl (9 won fights) and bot/watch/log.jsonl (12), from
worktrees/humanplay/rips/humanplay. "Chest" means "A chest! What will you do?" was shown.

| Fight | Won | Chest | Gold | Items |
|---|---|---|---|---|
| Ordinary monsters, Chris | 3 | 0 | 3 | 0 |
| Parties, Chris | 6 | 0 | 6 | 5 |
| Ordinary monsters, bot | 5 | 2 | 5 | 1 (from a chest) |
| Parties, bot | 5 | 0 | 5 | 2 |

Gold from magic-circle fights fits each monster's record, per member: Cool (record 14)
290, Minotaur (17) 300, Fake Cupid (9) 25, Demon Imp (6) 65.

### The Japanese sources

- **emonoya** (the site's drop data is parsed from it):
  https://emonoya.net/item/dim/dimi_t.html says "魔法陣の通常敵からは宝箱・罠・アイテムは
  出ず、GOLDのみが手に入る"; parties and NPCs drop the leader's items and gold; event
  monsters other than NPCs drop nothing; the Training Maze gives neither.
  https://emonoya.net/monster/dim/dimm_14.html: "パーティ敵とは動き回る赤い魔法陣と接触
  することで遭遇する。ただし魔法陣には通常の敵やNPCも混ざっている". Fight-square fights
  are its 玄室. All of it matches the code; its slot percentages are the raw record values.
- **dra.jp** (https://dra.jp/game/wizardy-dimguil/strategy.html): early chests aren't
  worth the risk; NPC parties "その階層で手に入るようなアイテムをドロップする". Nothing on
  the rule.
- **kouryaku.red** (https://wizardry-dimguil.kouryaku.red/entry6.html): the Dragon's Cave
  "レアアイテムも結構落とします". Nothing on chests.
- **The site's data/drops/dim.json** marks all 30 tables `chest: true` under one "fight"
  situation, which is wrong for magic-circle and party fights.

### Earlier games' sources (bartoks-trading-post/docs/research/drop-tables/)

- Wizardry I-III: w123-pascal.md, a read of the shipped p-code and data. REWARD1 is the
  wandering table; REWARD2 is used only when ATTK012 = 2, a square the maze marks as a
  fixed fight. `CHSTGOLD` opens a chest only if the table's BCHEST flag is set. In I,
  tables 0-9 are gold only, 10-19 and 21-23 chests, 20 (Werdna's) loose. Names from
  Ewers' reconstruction, https://github.com/snafaru/Wizardry.Code.
- Wizardry V: w5-pascal.md. Treasure rooms are drawn at 35-69% of a floor's rooms on every
  load; an ordinary room pays the wandering table at double gold.
- Wizardry VI: w6-sfc.md. Chests are fixed map squares; one loot script serves chests,
  fights and stock.
- Wizardry VII: w7-dos.md. The fill routine is still unread; this row is the author's
  tables.
- Gaiden I-IV and the bonus dungeon: emonoya's tables only.

## Loose ends

- D-battle.md "Chests and traps" and lock-test.md say a chest follows every won random
  battle. They need the source-2 condition.
- emonoya reports a first-edition bug: after an Alarm fight and a soft reset, the next
  chest opens by itself. Rev 1 clears 0x80079784 at MAIN 0x8001d570 and 0x800124a8, which
  may be the fix (inferred, not tested).
- The real fight-square versus magic-circle split in human play needs a log of
  `encounter_source` (0x800799dc) at each fight's start.
