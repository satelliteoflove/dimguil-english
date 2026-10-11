# Battle (analyst D)

How Dimguil runs a fight, read from BATTLE.BIN and the executable routines it calls.
Part of the rules-first code analysis (see `docs/code-map.md`); phase 4 merges this into
`engine-notes.md`. Names are in `scripts/re/symbols/battle.csv`; the decompiled functions
are in `rips/re/decomp/BATTLE/`.

Every claim is marked:
- **[code]** confirmed by reading the decompiled C (and the disassembly where noted);
- **[emu]** confirmed in the emulator (how is said);
- **[inf]** inferred: the code is read, but what a value *means* is a guess from how
  it's used.

Percentages are exact consequences of the code's integer arithmetic unless marked.

## Contents

1. [Randomness](#randomness)
2. [Records](#records)
3. [The battle loop](#the-battle-loop)
4. [Encounter setup: groups, surprise, friendly monsters](#encounter-setup)
5. [Each round: upkeep before commands](#each-round-upkeep)
6. [Initiative and commands](#initiative-and-commands)
7. [Monster AI](#monster-ai)
8. [Melee: the party attacks](#melee-the-party-attacks)
9. [Melee: monsters attack](#melee-monsters-attack)
10. [Status effects](#status-effects)
11. [Spells](#spells)
12. [Breath](#breath)
13. [Other actions: hide, ambush, dispel, call for help, flee](#other-actions)
14. [Items in battle, and what breaks them](#items-in-battle)
15. [After the battle: experience, drained and lost characters](#after-the-battle)
16. [When the party is wiped out](#when-the-party-is-wiped-out)
17. [Chests and traps](#chests-and-traps)
18. [Bugs and oddities in the original](#bugs-and-oddities)
19. [Translation impact](#translation-impact)
20. [How it was traced](#how-it-was-traced)

## Randomness

- Battle rolls use `rand_below(n)` (MAIN 0x800215c0), a linear congruential generator
  (`x = x * 0x41c64e6d + 0x3039`, state at 0x80079a34) returning 0..n-1. For small n it
  takes the top bits. `rand_below_mod(n)` (MAIN 0x80021648) is the same generator with a
  plain modulo, used mostly by the spell animations. **[code]** The maze's
  `rand_upto` (0x8001cb18) is a different generator and isn't used in battle. **[code]**
- `roll_dice(n, sides, bonus)` (BATTLE 0x800c9704) is n dice of 1..sides plus bonus,
  capped at 32767. Weapon damage, HP and group sizes all use it. **[code]**
- A "rand(100) < x" check in this document succeeds x% of the time; "rand(100) > x"
  succeeds (99 - x)%.

## Records

### Combatants

`combatants` (RAM 0x8008e230) holds one 14-byte record per fighter: group g at
+g*0x7e (nine records per group), member m at +m*0xe. Group 0 is the party (members
0-2 front row, 3-5 back row), groups 1-4 the monster groups (up to 6 in fixed
battles), group 7 the party's summoned creatures. **[code]**

| Offset | Size | Field |
|---|---|---|
| +0x0 | u16 | level (for monsters, the group's level) **[code]** |
| +0x2 | u8 | silence counter, rounds left (decremented each round) **[code]** |
| +0x3 | u8 | a second counter decremented each round; nonzero hides the Spell command 74% of the time **[code]**, meaning **[inf]** |
| +0x4 | s8 | AC modifier, -99..99; positive is harder to hit (Sogref, Porfic, Dilto...) **[code]** |
| +0x6 | s16 | current HP **[code]** |
| +0x8 | u8 | extra swings (added to the weapon's swings; also speeds initiative) **[code]**, source **[inf]** |
| +0x9 | u8 | initiative tick, 0-10 (0xff = doesn't act) **[code]** |
| +0xa | s8 | action: 0-83 a spell, negative a command (below) **[code]** |
| +0xb | u8 | target group (low 6 bits); for party spells the row **[code]** |
| +0xc | u16 | status bits (below) **[code]** |

Action codes: -1 fight, -2 defend (0xfe), -4 dispel, -7 ambush from hiding, -8 hide,
-9 breath, -10 call for help (monsters), -11 fight (second form), -12 confused attack,
-20 flee (monsters), 0x2b (43) is set while a breath resolves. **[code]**

### Status bits (combatant +0xc, roster +0x0e)

| Bit | Meaning | Can act? |
|---|---|---|
| 0x001 | afraid **[inf]**: acts only 7 rounds in 8 | yes |
| 0x002 | confused: random targets | yes |
| 0x004 | poisoned | yes |
| 0x008 | asleep | no |
| 0x010 | knocked out (気絶) | no |
| 0x020 | paralyzed | no |
| 0x040 | stoned | no |
| 0x080 | dead | no |
| 0x100 | ashes **[inf]** | no |
| 0x200 | lost (level drained to 0) | no |

Status below 8 can act; 0x20 and above counts as a body for the NPC rescue offer and
gets no experience. **[code]**

### Battle groups

`battle_groups` (RAM 0x8008c480), 8 bytes per group: +0 identified (1 = name known),
+2 monster id, +4 count, +5 standing, +6 spell-sealing level (Bacortu), +7 magic screen
(Cortu, Fofic). Group 0's +4/+5 are the party's "can act" and "alive" counts. **[code]**

### Monster record fields used in battle

Group g's monster record is at `monster_records` + g*0xd0 (0x8008a918; group 1 at
0x8008a9e8). Fields seen in the battle code (G owns the layout):

| Offset | Use |
|---|---|
| +0x6f, +0x70, +0x71 | group size dice: count, sides, bonus **[code]** |
| +0x72 | max HP (heals and regeneration stop here) **[code]** |
| +0x74, +0x76, +0x78 | level, HP die sides, HP bonus: HP = level d sides + bonus **[code]** |
| +0x7a | AC **[code]** |
| +0x7c | u32 experience per monster **[code]** |
| +0x80 | levels drained per hit **[code]** |
| +0x81 | HP regenerated per round **[code]** |
| +0x88 | AI type (row of the action table, 1-based) **[code]** |
| +0x8a | flee chance % **[code]** |
| +0x8b | call-for-help chance (out of 90) **[code]** |
| +0x8c | companion monster id (-1 none), +0x8e companion chance % **[code]** |
| +0xa3..+0xa6 | magic resistance % by school (Mage, Priest, Alchemist, Psionic) **[code]** |
| +0xa5 | breath resistance (capped 60) **[code]**; overlaps the Alchemist byte, so **[inf]** |
| +0xa8 | u32 type flags: 0x80000 undead (dispel, Zilwan, Matokani), 0x100000 summoned (Mogato), 0x400000/0x1000000 death-immune, 0x1000000 decapitation-immune; low bits are the monster class matched by slaying weapons and protection **[code]**, names **[inf]** |
| +0xac, +0xb6, +0xc0 | three attacks of 10 bytes: +0 noun (I_NAME index - 427; >= 2000 picks the other particle), +2 verb, +3 swings, +4/+5/+6 damage dice, +7 effect bits (0x80 = reaches the back row), +8 effect chance % **[code]** |
| +0xc9 | breath type: low bits the side effect, 0xe0 the element **[code]** |
| +0xca | breath message: FIGHTMSG index + 50 **[code]** |
| +0xcc | u16 resist bits (status and element) **[code]** |
| +0xce | u16 weakness bits (double dice, lower saves) **[code]** |

### Roster fields used in battle

Offsets into the 0xd0-byte roster record (G owns the layout; these are the uses seen):

| Offset | Use |
|---|---|
| +0x0a | race in the low 6 bits; +0x0b class in the low 4-5 bits **[code]** |
| +0x13..+0x18 | stats: +0x17 is agility (initiative) **[code]**; +0x14 and +0x15 are added for identifying monsters, +0x16 caps breath damage **[code]**; names **[inf]** |
| +0x44 / +0x48 | level / level at the start of the battle (used when a drain cuts max HP) **[code]** |
| +0x5c.. | spell points, 7 levels × 4 schools (one byte each) **[code]** |
| +0x78 | poison strength (HP lost per round) **[code]** |
| +0x79 | confusion counter (127 when confused; -10 a round) **[code]** |
| +0x7f..+0x82 | four saving throws, rolled as rand(20) < value **[code]**, names **[inf]** |
| +0x84 | u16 to-hit bonus **[code]** |
| +0x86 | AC **[code]** |
| +0x87..+0x8a | magic resistance % by school **[code]** |
| +0x8b | HP regenerated per round (negative drains) **[code]** |
| +0x8c | weapon hit effects (status bits), +0x8d..+0x93 their chances % **[code]** |
| +0x94, +0x95 | extra swings, first and second weapon **[code]** |
| +0x96..+0x98, +0x99..+0x9b | damage dice of the two weapons **[code]** |
| +0x9c, +0x9d | reach of the two weapons **[code]** |
| +0xa0 | u32 protection: monster classes whose hits are halved **[code]** |
| +0xa8 | u32 slaying: monster classes that take double damage **[code]** |
| +0xae | u16 resist bits (element, status) **[code]** |
| +0xb0..+0xb6 | resistances to the seven hit effects % **[code]**; +0xba resistance to level drain **[code]** |
| +0xc0 | u32 monsters killed **[code]** |
| +0xc4 | deaths **[code]** |

Item slots: bit 0x1000 marks the main weapon, 0x800 the second weapon. **[code]**

## The battle loop

`battle_main` (0x800a2cd8) runs once a frame from `main` while BATTLE is loaded,
stepping `battle_phase` (0x800796fa). Seen in the emulator, a fight round goes 0, 1, 2,
3, 4, 6, 8, 0xa, 0xe, 0x12, 0x16, 0x18, 0x1c, 0x28, 0x2c, 0x2e, 0x30, 0x32 ... **[emu]**
(phase list from `rips/re/work/D/round.py` on `battle_wriggle.state`).

| Phase | What runs |
|---|---|
| 0 | set up: copy the party, roll the groups (`battle_setup_groups`), surprise, friendly check |
| 1-6 | intro messages ("An encounter!", surprise lines), the monsters drawn |
| 8 | the monster panel |
| 0xe | round upkeep: `monster_upkeep` 0x800a6aa0, `party_upkeep` 0x800a73f4, `counters_tick` 0x800a77e0, `party_row_swap` 0x800a7abc, then `groups_reorder` 0x800a7e74 (random encounters) |
| 0x18 | identify rolls (`identify_roll` 0x800a7938) |
| 0x1c | the party's commands (0x800cbec8), with `party_initiative` 0x800cf8e0 per member and the flee roll |
| 0x20 (' ') | each monster group picks its actions (`monster_ai` 0x800cffb0); group 7 too |
| 0x22 | `battle_run_actions`: everyone acts in initiative order |
| 0x24-0x2a | `battle_message_build` turns each action's results into FIGHTMSG lines |
| end of round | party buffs count down (below), back to 0xe |
| 0x3e | the end: `battle_rewards` 0x800c4fc8, or the wipe |

**[code]**

## Encounter setup

`battle_setup_groups` (0x800a60fc), for a random encounter: **[code]**

- The area class (table 0x8005a824 by the party's floor) picks the most groups allowed
  (table 0x800d8358): 1 on the first floors, up to 4 deeper. **[code]**
- Group 1 is the encounter's monster; each further group is the previous monster's
  companion (+0x8c), added only while rand(100) < its companion chance (+0x8e). **[code]**
- Each group's size is its size dice; each member's HP is level d sides + bonus,
  rolled separately. **[code]**
- Groups start unidentified unless the encounter is fixed, or Latumapic is active
  (party flag 0x8007e82c, set to 2000 by the spell). **[code]**
- **Surprise:** rand(100) of 81-99 (19%) means the party surprised the monsters (FIGHTMSG
  203). Otherwise rand(100) of 81-99 again means the monsters surprised the party (204),
  unless the party value 0x8007e82e is nonzero (set to 1000 by a camp effect, MAZE
  0x800e82d0) **[code]**. That's 19% and 15.4%. **[code]** Which spell sets 0x8007e82e
  is B's to name.
- **Friendly monsters:** only on floors where table 0x800d832c allows it (not the first
  floor, not the training maze), only for random encounters, and only if the first
  group's record has flag 0x1000 at +0xcc. The chance is 10% if its +0xa8 has bit 1 or 2,
  15% for bit 4, 5% for bit 8 or 0x1000, 25% otherwise; it's rolled once, for the first
  party member whose party-copy byte 0x8007e81e+i lacks 0x40. **[code]** (bit 0x40 of
  that byte is probably Evil alignment **[inf]**; then an all-Evil party never meets
  friendly monsters.) A friendly encounter shows FIGHTMSG 263.

## Each round: upkeep

Before the party gives commands: **[code]**

**Monsters** (`monster_upkeep` 0x800a6aa0), each standing monster:
- recovers, each with chance min(k × level, 35)%: fear k = 3, sleep and knock-out k = 4,
  paralysis k = 2, stone k = 1;
- poison costs HP/8 (at least 1);
- regenerates +0x81 HP, up to max HP;
- at 0 HP it dies and its experience goes in the pool;
- dead monsters drop out of the group, and empty groups close up (group 3 becomes 2).

**The party** (`party_upkeep` 0x800a73f4), each living member:
- poison: loses its poison strength (+0x78) a round if HP is 50 or less, HP/16 above that;
- +0x8b HP regenerated (equipment);
- at 0 HP: dead, poison and confusion cleared, death count +1;
- sleep and knock-out wear off with chance min(4 × level, 35)%, but not on the first
  round of the battle;
- fear with chance min(3 × level, 35)%;
- confusion: the counter drops 10 a round; at 0 the character comes to its senses.
  A spell or breath that hurts a confused character cuts the counter by half plus one.

**Counters** (`counters_tick` 0x800a77e0): silence and the +3 counter drop by 1; a group's
magic screen above 10 drops 5-10 (the party's then gains the Fofic bonus, 10 a round while
Fofic lasts, up to 200); spell sealing of 3 or more drops 1-3, else 1.

**Rows** (`party_row_swap` 0x800a7abc): if nobody in the front row can fight (status
0x20 or worse) and somebody in the back row can, the rows swap.

**Identify** (`identify_roll` 0x800a7938), once a round while a group is unidentified:
each member able to act picks a random group and names it with chance
(level + stat +0x14 + stat +0x15 - 4) out of 99.

**Group order** (`groups_reorder` 0x800a7e74, random encounters): groups are scored by
HP (each monster's HP capped at 200), 14 per monster and 2 per point of AC below 30, minus
a weight for the spells they know; a higher-scoring group moves ahead of a weaker one in
front of it (FIGHTMSG 285, "advances"). **[code]** (the spell weighting's tables, 0x800d8384
and 0x800d7df8, aren't decoded **[inf]**)

## Initiative and commands

**Initiative.** Each round every fighter gets a tick 0-10, and `battle_run_actions`
(0x800a8548) runs ticks 0 to 10 in order, party first within a tick, then groups 1-7, then
members in order. Lower is sooner. **[code]**

- **Party** (`party_initiative` 0x800cf8e0): rand(10) (0-9), then by agility (+0x17):
  14 or more takes off (agility - 13), down to 0; under 8 adds (4 - agility/2); 8-13 no
  change. A character with extra swings (+0x8 nonzero) and a tick above 2 takes 2 off.
  Capped at 10. Surprised, or status 8 and up: no action. **[code]**
- **Monsters** (`monster_ai`): (rand(255) & 7) + 2, so 2-9; a spell adds 0-2 (cap 10).
  **[code]** So a fast character often beats every monster, and monsters never act at
  ticks 0-1.
- Afraid (status 0x1): before acting, a 1-in-8 roll loses the turn. **[code]**

**The party's command list** (built in `party_initiative`): Fight if the better weapon
reaches a group from the character's row (or Ambush while hidden); Hide for classes 3, 7,
8, 0xc and 0xd (not while hidden); Defend always; Spell if the character has a spell
point left, the +3 counter is clear (or a 26% roll passes), the party isn't surprised and
0x8007967d is clear; Dispel for class 2, class 5 from level 9 and class 0xb from level 4.
**[code]** Class numbers are the roster's +0x0b; which class each is belongs to G (3 is
probably Thief and 7 Ninja, 2 Priest, 5 Bishop, 0xb Lord **[inf]**, from the hide and
dispel lists and the dispel penalties below).

## Monster AI

`monster_ai` (0x800cffb0) picks each monster's action: **[code]**

1. Confused: 72% attacks a random group (action -12).
2. Otherwise it rolls rand(100) against its AI row (table 0x800d89e0, 13 columns,
   the row is +0x88): the columns are fight a random reachable member, fight the
   reachable member with the least HP, defend, damage spell (single), damage spell
   (group), status spell, buff, heal, cure, call for help, breath, breath at the weaker
   row, flee. **[code]** Row 1 is 80% fight, 10% fight the weakest, 10% defend; row 13
   mixes 20% fight with 25% damage spells, 10% calls for help and 15% fleeing; and so on
   (dumped in `rips/re/work/D/`).
3. A spell is picked from the monster's spells that match the column (0x800d0c6c).
   If none fits, it fights, or defends if it can't reach anyone. **[code]**
4. When the monsters surprised the party they never cast in that first round. **[code]**
5. When the party surprised the monsters, `battle_main` doesn't call `monster_ai` at all
   that round, so the monsters do nothing. **[code]** (`battle_wriggle.state` opens with
   "Preemptive attack!" and no monster acts in round 1 **[emu]**) Between groups the loop
   makes one extra rand(100) call whose result is thrown away. **[code]**

Reach: a monster whose attacks lack the 0x80 reach bit can only hit the front row, and
in random encounters only groups 1 and 2 can do that; groups 3-4 need reach (or spells,
or breath). **[code]** A hidden party member that's picked is skipped 70% of the time.
**[code]**

## Melee: the party attacks

`party_melee` (0x800a8c2c, with its tail 0x800a9268), for each weapon hand: **[code]**

- **Target.** The chosen group, first standing member (front-to-back). A confused
  fighter picks at random: 50% of the time another target, which can be a party member.
- **Reach.** `weapon_reach` (0x800c94a8): reach code r (+0x9c/+0x9d) & 7; if r & 3, double
  it, and from the back row only r & 2 counts. The weapon reaches groups up to the
  result: short weapons groups 1-2 from the front, nothing from the back; long weapons
  1-4 from the front, 1-2 from the back; bows (r = 4) everywhere. **[code]** (names of the
  reach classes **[inf]**)
- **To hit.** T = base - target AC + target's AC modifier - attacker's to-hit (+0x84),
  base 20, 21, 22, 23 for monster groups 1-4 (22 for a party member, 27 if hiding); -4 if
  the attacker is hiding (ambush); capped at 19. Then the party's Oslo bonus b (0x8007e830,
  2 while Oslo or Maoslo lasts): T - b, and if that's 15 or more, 3 more off; 13-14 becomes
  12. At least 1. **[code]**
- **Swings.** Extra swings (+0x8) + the weapon's (+0x94/+0x95), capped at 10, plus the
  equipped weapon's item_state byte (0-5), at least 1. **[code]** (what sets +0x8 and the
  item_state byte for weapons **[inf]**)
- **Each swing** hits if rand(20) >= T: so 5% to 95%, (20 - T) × 5%. A hit does the
  weapon's dice. **[code]**
- **Bonuses.** If the target can't act (status 2 or more: confused, poisoned, asleep...)
  or the attacker is hiding: damage + rand(damage), up to almost double. If the weapon's
  slaying bits (+0xa8) match the monster's class bits: ×2. **[code]**
- **Weapon effects.** If the weapon has hit effects (+0x8c), they're rolled after damage
  (below). The code works out a level-difference bonus for them, but the function never
  reads it (see bugs). **[code]**
- **Verb.** The weapon's subtype s picks FIGHTMSG verb 2s+1 or 2s+2 at random; bare hands
  are verb 19 with "fist" (I_NAME 680) or verb 20 with "sharp claws" (681), the same coin
  deciding both. **[code]**
- **Messages.** No hits: 119 "The attack misses." Hits but no damage: 201. Otherwise 118
  "Hits N times!", then 150/151 damage, 159 death. **[code]**
- A monster at 0 HP dies (status 0x80); its experience goes in the pool and the attacker's
  kill count goes up. **[code]**

## Melee: monsters attack

`monster_melee` (0x800aaa04), `monster_attack_roll` (0x800aaed0), `monster_hit_apply`
(0x800ab3b0): **[code]**

- **Which attack.** A back-row target needs an attack with the reach bit. With a choice,
  attack 1 is used 69% of the time and attack 2 31% (if it exists). Attack 3, if it has
  dice, always follows, 2 points harder to hit (T + 2 while T < 18).
- **To hit.** T = 22 (29 if the target is hiding) + Maporfic (0x8007e82a, 2) - target's AC
  + target's AC modifier - (monster level/2 + 1); +4 if the target chose Defend; 1..19.
  Against monsters (a confused monster's friendly fire), base 21.
- **Swings.** Extra swings + the attack's +3, capped at 11. Each hits on rand(20) >= T and
  does the attack's dice.
- **Bonuses.** + rand(damage) if the target can't act; halved if the target's protection
  bits (+0xa0) match the monster's class (but never below one point a hit).
- **Effects.** If the attack has effect bits, they're rolled with the attack's chance
  (+8) against the party member's resistances. Monsters that drain levels do it here too.
- **Messages.** All missed: 120 "Dodged the attack." Otherwise 118, then 129 damage, 139
  death.
- An attack noun of 683 or more (rods and wands) isn't a melee hit: the attack's +6 byte
  is a spell, and the monster casts it as an innate ability (no spell points, no silence).

## Status effects

`apply_status_effects` (0x800aa190) rolls the hit effects of a weapon or monster attack.
Each effect needs **rand(100) > resistance and rand(100) < chance**, so the odds are
chance% × (99 - resistance)%. For monsters, resistance is 100 (immune) for each effect
bit in their +0xcc, else 0; decapitation also checks the +0xa8 flag 0x1000000. For the
party it's the member's +0xb0..+0xb6. **[code]**

| Bit | Index | Effect | Notes |
|---|---|---|---|
| 0x40 | 6 | decapitation: dead, HP 0 | rolled first; if it lands, nothing else is rolled |
| 0x04 | 2 | stone | |
| 0x10 | 4 | paralysis | only if nothing above landed |
| 0x20 | 5 | knock-out: HP cut to 1-4 | only if nothing above landed |
| 0x01 | 0 | sleep | only if nothing above landed |
| 0x02 | 1 | poison | not if already poisoned; a party member's poison strength becomes the attacker's level (capped 127) |
| 0x08 | 3 | confusion | not if already confused; counter 127 (13 rounds) |
| drain | | levels | monster attacker, party target, once per member per battle |

**[code]**

**Level drain**: the monster's +0x80 levels are taken if (rand(255) & 31) < the member's
+0x81 and rand(100) > its drain resistance (+0xba). Max HP becomes (max HP / starting
level) × new level, if lower. At level 0 the character is lost (status 0x200). **[code]**

Messages: the bit index i picks FIGHTMSG 130+i for a party member (130 asleep, 131
poisoned, 132 stone, 133 confused, 134 paralyzed, 135 knocked out, 136 decapitated, 137
drained, 138 lost) and 152+i for a monster. **[code]**

## Spells

Spell numbers are the STATUS.OBJ list from 222: 0-20 Mage (Katino ... Tiltowait), 21-41
Priest (Dios ... Madial), 42-62 Alchemist (Oslo ... Madalqua), 63-83 Psionic (Sios ...
Ihalon). A spell's school is n / 21 and its level (n mod 21) / 3 + 1, three spells a
level. **[code]**

`spell_flags_table` (0x800d5874) has a u16 per spell: 1 usable in battle, 2 in camp, 4
on a chest, 0x10 one party member, 0x20 one enemy, 0x40 one group (neither = all), 0x100
damage, 0x200 buff, 0x400 status, 0x800 heal, 0x1000 cure, 0x8000 hostile. **[code]**
(the bits' meanings **[inf]**, from the spells carrying them) `spell_handlers` (0x800d838c)
points at each spell's battle code; Dumapic, Calfo, Kandi, Kadorto, Calnova, Diafic, Calko,
Caldu and Ihalon have none (not castable in battle). **[code]**

### Casting

`cast_spell` (0x800abcc0): **[code]**

- No spell point at that level (+0x5c + school × 7 + level - 1): "couldn't cast" (125).
- Silenced (+0x2): "couldn't cast" (125/126).
- Spells sealed: if the caster's side has sealing level s (Bacortu), the spell is lost
  ("But spells are sealed.", 127) unless rand(8191) / (caster level + s + 1) >= s. The
  party's 0x8007e83a counter seals the party's spells outright. Items and innate
  abilities skip this.
- Malor and Loktofeit do nothing in the training maze (area classes 0x1e-0x25) and in
  fixed battles of type 3 or 5.
- The spell point is spent, then `spell_dispatch` (0x800c98cc) runs the handler.

### Magic resistance

Every hostile spell first rolls against the target's resistance to the caster's school
(party +0x87.., monsters +0xa3..), plus the target side's magic screen (Cortu). Nofis
cuts it by a fifth per cast on the other side (counters 0x80079932 for the monsters'
resistance, 0x80079949 for the party's, up to 21; single-target damage spells count at
most 4). The roll is rand(100) < resistance - (resistance/5 × Nofis) + 1, so **even a
target with no resistance shrugs off 1% of spells.** **[code]** Messages: 186 (party), 187
(when it's an item or ability), 188 (monster nullifies), 168 (group 7).

### Damage spells

`spell_damage_one` (0x800b0b50) and `spell_damage_group` (0x800b0930) roll n dice of
1..sides; a group spell rolls for each member separately. Against a party, a group spell
hits a row. Each target's element bits halve the dice count (+0xcc for monsters, +0xae
for the party) or double it (+0xce). Damage gets the side's bonus (0x800798b0 or
0x800798b6) added. **[code]**

| Spell | Dice | Targets | Element bit |
|---|---|---|---|
| Halito | 2d4 | one | none |
| Melito | 2d4 | group | 0x80 |
| Mahalito | 4d6 | group | 0x80 |
| Lahalito | 6d6 | group | 0x80 |
| Madalto | 8d8 | group | 0x100 |
| Ladalto | 10d10 | group | 0x100 |
| Tzalik | 24d2 | one | none |
| Lazalik | 40d2 | one | none |
| Tiltowait | 10d15 | every group | 0x4000 |
| Badios | 2d4 | one | none |
| Zilwan | 255d10 | one, undead only | none; on the living it's "unaffected" |
| Alikus | 48d3 | one | none |
| Barenes | 8d8 | group | none, then 0x4000 |
| Dalosto | (varies)d5 | one | none |

**[code]**

**Alchemist clouds.** Liqurea, Dalqurea, Kaniqua, Maliqua, Bamoqua and Madalqua don't do
damage when cast. `alchemist_cloud` (0x800b2f94) puts a cloud on the target group, which
`cloud_damage` (0x800b3ef0) burns at the end of each round (phase 0x24) as a group damage
spell, for 3 rounds. A group holds two clouds; a third pushes out the oldest. Groups 8
and 9 are the party's two rows, so monsters' clouds work the same way. **[code]**

| Spell | Each round | Element | Message (party / monster) |
|---|---|---|---|
| Liqurea | 1d4 | 0x80 | 174 / 180 "engulfed in flames" |
| Dalqurea | 2d4 | 0x100 | 175 / 181 "in cold" |
| Kaniqua | 3d4 | 0x4000 | 176 / 182 "in unseen flames" |
| Maliqua | 4d5 | 0x80 | 177 / 183 "in searing flames" |
| Bamoqua | 5d8 | 0x4000 | 178 / 184 "in an unseen inferno" |
| Madalqua | 4d15 | 0x4000 | 179 / 185 "in freezing cold" |

**[code]** Madalqua's message says cold, but its element is 0x4000 (Tiltowait's), so
resisting cold doesn't help against it.

**Psionic damage** (`psionic_damage` 0x800b34b0): dice damage, then, if the target can
still act, confusion with chance p (a status save of 100 - p), halved if the target
resists bit 8 and 80% if it's weak to it. Sios 2d2 and 65%, Lios 2d2 and 65% (skips dead
targets), Masios 8d2 and 60%, Lasios 8d9 and 60%. **[code]**

### Status spells and saving throws

`status_spell_targets` (0x800b1524) and `status_spell` (0x800b173c): after magic
resistance, a saving throw: the save value is clamped to 5-100 and saves on rand(100) <
save. The save starts from the spell's base, +300 (always saves) for a monster immune to
it, 85 for a party member resisting the element (+0xae), plus the member's resistance for
sleep and the next two kinds, and plus 4 per level the target has over the caster.
**[code]**

| Spell | Kind | Base save | Notes |
|---|---|---|---|
| Katino | sleep | 50 (15 if weak to sleep, immune if resistant) | targets status below 8 |
| Montino | silence | 50 (16 if weak) | silence lasts rand(L) + L/8 rounds, L = caster level - target level, at least 3 |
| Lorks | paralysis | 35 (70 if resistant, 17 if weak) | |
| Badi | death, one | 25 (125 for flagged types) | at least 5 + 4 per level the target is above |
| Bakadi | death, group | 38 vs monsters, 65 vs the party | flagged types immune |
| Mogato | banish | 100 (always saves) unless the target is summoned (0x100000): 30 | "vanishes" (171) |
| Matokani | death (dust) | none | party: every monster of level 8 or below that isn't undead dies, with no magic resistance and no save; others are immune. Cast by a monster: party members above level 8 are immune, the rest save at 4 per level above the caster (at least 5%) |

**[code]** So the site's description of the Gold Gauntlets' Matokani ("kills every enemy
of level 8 or below that isn't undead") is exactly right.

### Healing and buffs

- Heals (`spell_heal` 0x800b2b78) roll n dice of 1..sides, up to max HP: Dios 2d4 (2-8),
  Dial 2d8 (2-16), Dialma 3d8 (3-24), Diomas 3d2 (3-6), Madial 17d4 (17-68) on each party
  member; Madi and Kadios to full. Messages 143 (recovers N) and 144 (fully healed);
  163/164 for monsters. **[code]** Analyst B found the camp versions give Dios 2-8, Diomas
  3-6 and Madial 10-50, so Dios and Diomas agree in both modes, the item descriptions
  (1-8, 2-6) are wrong in both, and Madial differs between camp and battle (the
  description says 30-60).
- AC changes (`spell_ac_change` 0x800b083c): Sogref +2 the caster, Porfic +4 the caster,
  Ponti +1, Bamatu +3 the caster's side, Dilto -2 a group, Morlis -4 a group. **[code]**
- Cortu: the caster's side's magic screen becomes 3/4 of what it was + 2 × caster level,
  up to 90. Bacortu: the target side's sealing level + caster level, up to 255.
  Breath halves the party's screen. **[code]**
- Badumas: each of the target group's attacks loses a damage die, up to 4 times. **[code]**
- Oslo / Maoslo: for a monster, +2 / +4 damage bonus on each of its attacks; for the
  party, the attack bonus 0x8007e830 = 2 for 60 more rounds / 2500 rounds. **[code]**
- Fofic: the party's magic screen gains 10 a round for 1250 rounds. Banoka: 3 rounds of
  0x80079bc0 (party) or 0x80079b6b (monsters), which turn monsters' melee on their own
  side 34% / 30% of the time **[code]**, meaning **[inf]**.
- Durations count down at the end of every battle round: Oslo, Fofic, Maporfic, and the
  party counters 0x8007e83a-0x8007e83d. **[code]** (the maze counts them down too: A/B)

### Summons and Mahaman

Socordi, Bamordi, Gardi and Zakaldi call `summon_creatures` (0x800b215c) with 0-3. Only
one summoned group can be out at a time (otherwise "The spell has no effect.", 189). The
caster's level picks a tier, 0 up to level 9 and (level - 10)/3 + 1 above (8 from level
31). A rand(100) picks one of seven columns of that tier's row (46%, 16%, 10%, 10%, 7%, 7%,
4%), and the table at 0x800a1270 turns it into one of the spell's nine creatures (records
at 0x800d5f58, 0xd0 bytes each, in BATTLE). Size and HP are rolled from the record's dice,
and the group appears as group 7 (284). Monsters can banish them with Mogato. **[code]**

| Spell | Creatures, weakest tier first (level, group size) |
|---|---|
| Socordi | Demon Imp (5, 1d4), Gargoyle (8, 1d4), Lesser Demon (12, 1d4+1), Succubus (15, 2d3), Beast (12, 1), Greater Demon (18, 1d3), Hell Master (12, 1d4), Demon Lord (60, 1), Hims (66, 1) |
| Bamordi | Zombie (6, 1d5), Skeleton (7, 1d5+2), Gucumatz (9, 1), Banshee (8, 2d3), Murphy's Ghost (11, 1), Elizabeth (14, 1), Wight (12, 1), Vampire Lord (17, 1), Maelific (55, 1) |
| Gardi | Vampire Bat (5, 1d3+2), Basilisk (8, 1d3), Giant Spider (8, 1d4), Magical Rabbit (8, 2d2), Were Jaguar (11, 1d4), Centaur (9, 2d3), Flack (16, 1d3), Dullahan (36, 1d3), Dragonare (48, 2d2) |
| Zakaldi | Arch Fighter (6, 1d3), Arch Mage (10, 1d3), Arch Priest (8, 1d3), Sylph (8, 1d3), Ixquic (11, 1d3), Beauty (12, 1), Kel (13, 1), Arch Ninja (10, 1d3), Diamond Knight (100, 1) |

The tier rows are [0..6], [1,0,2..6], [2,3,1,0,4,5,6], [3,2,4,5,1,0,6], [4,3,5,6,2,1,0],
[5,4,6,7,3,2,1], [6,5,7,8,4,3,2], [7,6,8,5,4,3,2], [8,7,6,5,4,3,2]. So a caster of level 9
or lower gets the first creature 46% of the time and never the last two, and a caster of
level 31 or above gets the ninth 46% of the time. **[code]** (names decoded from the
records' English name field at +0x24)

Mahaman (0x800ace4c) and its wish menu (0x800ad0a8, FIGHTMSG 267-283) aren't decoded yet.

## Breath

**Monsters** (`monster_breath` 0x800b39c4): breathes on one row (front, or back if
targeted). For each standing member: **[code]**
- damage = q + 2 × rand(q), q = the monster's current HP / 4 (at least 1), so about half
  its HP; above 300 it's 300 - rand(120);
- if the member's resist bits match the breath element: half damage, and +5 to the
  breath save;
- the save is +0x81 (+5), at most 18: rand(20) < save halves the damage again;
- then the breath goes through the damage core with breath resistance (save × 5%, up
  to 75%) instead of magic resistance;
- if the member is still standing, a second save (+4 if resistant) or the side effect:
  sleep 35%, poison 40%, stone 30%, confusion 30%, paralysis 30%, death 20%, by the
  breath's low bits.
- The party's magic screen is halved first.

**The party** (`party_breath` 0x800b36dc, a race ability **[inf]**: FIGHTMSG 207/208 "breathes
acid"): damage = the breather's current HP >> times breathed this battle (so half, then a
quarter...). The first breath of a battle from a character above level 8 hits every group
((damage/4 + 3) d4 each member); otherwise one monster takes it whole. Monsters weak to it
(+0xce 0x2000) take double. Capped by `breath_damage_cap` (0x800b2e50) once it passes 50.
**[code]**

## Other actions

- **Hide** (-8): only if not already hidden, rand(100) <= level/2 + 15 must pass first;
  then rand(level + 9) of 7 or more hides (194), else "tries to hide, but fails" (193).
  **[code]**
- **Ambush** (-7, from hiding): to-hit 4 better and the target takes + rand(damage). But
  each swing first rolls rand(16383) mod (2 × target level + attacker level): above
  1.25 × attacker level and the attacker is spotted ("But they're spotted.", 124) and the
  attack fails. While hidden, monsters skip that member 70% of the time. **[code]**
- **Dispel** (-4): only on undead (+0xa8 0x80000). Each standing monster in the group
  rolls rand(100) < 5 × caster level + 50 - 10 × monster level, -26 for class 5, -18 for
  class 0xb, clamped 10-255. Dispelled monsters give **no experience** and no kill credit.
  (106 / 107) **[code]**
- **Monster calls for help** (-10): if the group has under 9 and +0xcc has 0x800: rand(90)
  < +0x8b adds one fresh monster (114), else "no help comes" (117). **[code]**
- **Monster flees** (-20): +0xcc 0x400 and rand(100) < +0x8a: it leaves (115), else 116.
  **[code]** A fled monster gives no experience.
- **The party flees** (`party_flee_roll` 0x800d1380): M = 1 + the levels of every monster
  that can act, P = 1 + the levels of every party member that can act. The chance is 80
  if P < M, else 80 + 5 × (P / M) (integer), minus 2 × the area's danger level (table
  0x800da6c8, 0-16), and it succeeds on rand(100) + 1 < chance. Fixed battles can't be fled
  ("The enemy cuts off your escape!", 206). **[code]** So on the first floors a party
  stronger than the monsters always gets away, and even a weak one gets away 79% of the
  time; deep down the penalty reaches 32 points.

## Items in battle

`item_use_after` (0x800ac7c4), after an item's spell: **[code]**
- Potions and scrolls (subtypes 0x14, 0x15) use up one of their count (item_state); the
  last one disappears and the slots after it close up.
- Anything else breaks with chance = the item's +0x0e byte (%), and becomes the item at
  its +0x10 (usually 0, BROKEN ITEM): the Gold Helm, Gold Armor, Gold Gauntlets and Gold
  Boots are all 50%, so **the site's "even chance of destroying it" is right**. Others:
  Staff of Montino 5%, Winged Boots 5%, Horn of Prometheus 1%, Ring of Healing 10% (becomes
  a Ring of Madi), Wizard's Wand 10% (becomes a Great Wizard Wand), Demon's Staff 75%
  (becomes a Rod). The full list is in `rips/re/work/D/` (112 items have a break chance).
  **[code]**

The break chance and result are item fields +0x0e (u8) and +0x10 (u16) in G's Item record.

## After the battle

`battle_rewards` (0x800c4fc8): **[code]**
- Survivors are members with status below 0x20 (not paralyzed, stoned or worse).
- A drained character has its experience set to the minimum for its new level
  (0x800c5348 by level, race and class) and gets "loses a level" (197). A character
  drained to level 0 is lost (196): its name goes in a list of the last three lost
  characters (0x80096720) and the record is deleted (0x800c55f8, 0x800c5874).
- The experience pool (the +0x7c of every monster killed or poisoned to death, not
  dispelled or fled) is divided by the number of survivors and added to each survivor
  ("Each survivor gains N experience!", 198). Nobody gets any if the party fled.
- Gold (262) and items found (261) come only from the chest, when it's opened (below).
  **[code]**

## When the party is wiped out

`party_wiped` (0x800c59a0), when no member is left below status 0x20: **[code]**

1. Lost characters are deleted as above.
2. **Where the bodies go.** Outside the training maze, the party record is saved with
   every member's location set to the square they fell on (area, x, y, facing): the
   bodies stay in the maze for a rescue (return 2). In the training maze (area classes
   0x1e-0x25) the party is broken up and the members go back to town (area 0xff), so the
   training maze needs no body recovery (return 1). That matches Emonoya's tip. Both paths
   then run steps 3-5, so **a wipe in the training maze still destroys items and halves
   gold**. **[code]** (the training-maze branch jumps to the same tail at 0x800c5b30)
3. **Items are destroyed** (`wipe_item_loss` 0x800c5be8): each item in a slot is rolled
   with rand(12): items 72-130, 199-240 and 277-324 are destroyed on 0-7 (2 in 3), every
   other item on 0-2 (1 in 4). The high-risk ranges are the rare weapons (Blade Cusinart
   to Great Wizard Wand), the rare armor (Suffocate Helm to Breast of Expert) and the
   ankhs, rings, cards and quest items up to the Tablet of the Sun (323) and the Ring of
   Medium (322). **[code]** That's the fans' "a wipe may lose items", and the player who
   lost the Tablet of the Sun.
4. **But only one character's items are rolled.** The loop should go over the six
   members, but it reads the member at `actor_member` (the last fighter to act) every
   time, so that one character's items are rolled six times and the others keep
   everything (see bugs). **[code]**, confirmed in the disassembly at 0x800c5c28, and
   **[emu]** (below: in a test wipe only the first character lost items).
5. **Gold is halved** for every member. **[code]** **[emu]**
6. The current party's member list is cleared to empty (-1). **[emu]**

There is nothing in the battle code that takes items from bodies over time: once the
battle is over, the battle code never touches the bodies again. (Whether the maze does
is A's question.)

## Chests and traps

After a won random battle (not in the training maze, not fixed battles 0x91-0xab), the
chest record is the encounter's entry in a table loaded from disc (table 1 index 0x1b8 to
0x801c5400, 0x5c bytes each). **[code]**

- Its +4 is a mask of possible traps (bits 1-12). If bit 0 is set the chest may be
  untrapped: it's trapped with chance (t - 1)/18, t being the area's danger level from
  table 0x800d7cec (0-16). Otherwise it's always trapped. The trap is picked evenly among
  the mask's bits. **[code]**
- Inspect, Calfo, Calnova, Disarm, Open and Leave are the chest menu (FIGHTMSG 215-220).
- **What's inside** (`chest_loot` 0x800c7fd0, on opening): gold = (dice at +0x50/+0x51/
  +0x52) × the u32 at +0x54 × (dice at +0x58/+0x59/+0x5a), divided evenly among the members
  with status below 0x20 ("Each survivor gains N gold!", 262). Items: if the record's +0
  byte is 1 and the battle is of type 2 or 4 (or 0x800797f4 is -2), each of three item
  slots k gives an item when rand(85) <= the u32 at +8 + 4k (0x800c8388, 261). **[code]**
  (the battle types' meaning **[inf]**)

| Trap | Effect |
|---|---|
| 1 Stone Shot | the opener takes t d8 |
| 2 Poison Needle | the opener is poisoned (strength + t) |
| 3 Magic Drain | each standing member failing save +0x82: every spell level it has points in is set to a random small number |
| 4 Gas Bomb | each standing member failing save +0x81 is poisoned (+t) |
| 5 Exploding Box | each member failing save +0x82 takes t d10 |
| 6 Ghost Swarm | every standing member's HP becomes 1-10 (254) |
| 7 Demon's Eye | each member below stone failing save +0x7f turns to stone |
| 8 Rainbow Flash | each member failing save +0x80 gets one of: paralysis, stone, t d8, death, poison |
| 9 Goddess's Kiss | the opener gains a point in a random stat (up to its race's maximum + 10), "is blessed" (256) |
| 10 Spell Blaster | each standing member with any Mage spell points, failing save +0x82, dies (257) |
| 11 Alarm | a new battle starts (258) |
| 12 Teleporter | "You've been sent somewhere!" (259); the maze handles the jump |

**[code]** (saves: rand(20) < the save value avoids it)

## Emulator checks

All on `battle_wriggle.state` (Uranus, Venus, Jupiter, Earth against two Wriggle Objects,
level 2) with the patched build, breakpoints and watchpoints only unless said. The scripts
are in `scripts/re/battle_checks/` (run from the repo root); raw output went to
`rips/re/work/D/checks/`.

- **Party initiative** (`melee_init.py`): four rolls logged at 0x800cf990 with the
  character's agility. Rolls 3, 1, 4, 7 with agility 19, 15, 8, 10 gave ticks 0, 0, 4, 7,
  as the formula says (3-6 and 1-2 floor at 0; 8-13 unchanged). **[emu]**
- **Party to-hit**: Uranus (to-hit +0x84 = 14) and Venus (11) against AC 7 in group 1
  had thresholds 1 and 2 at the rand(20) compare (0x800a9224): 20 - 7 - 14 = -1, floored
  at 1, and 20 - 7 - 11 = 2. Every swing with roll >= T added a damage roll. **[emu]**
- **Monster initiative** (`defend.py`, all four Defending for 14 rounds): 26 monster
  ticks, every one (rand(255) & 7) + 2, seen from 2 to 9. **[emu]**
- **Monster to-hit**: every swing had threshold 19 (Defend's +4 pushes 24 - AC past the
  cap for every member's AC of -2..2). Of 22 swings, the one roll of 19 hit and took a
  point off Uranus; no other roll hit. Attack 2 was chosen 7 times of 26. **[emu]**
- **The wipe** (`wipe.py`). **Setup used a RAM write**: at the second command phase all
  four party combatants were set dead (+0xc = 0x80, HP 0); everything after was the
  game's own code. `party_wiped` ran, `wipe_item_loss` read `actor_member` (0) six times
  and called rand(12) 12 times: Uranus's six items were rolled on the first pass (four
  destroyed), then the two left over on each later pass (one more destroyed). Venus,
  Jupiter and Earth weren't rolled and kept all their items. All four members' gold went
  from 18 to 9, and their locations stayed on the square (area 0, x 11, y 21). **[emu]**
  (output `wipe0.txt`)

## Bugs and oddities

- **The wipe destroys only one character's items** (0x800c5be8). The outer loop counter
  isn't used; the member index comes from `actor_member` each pass. Depending on who acted
  last, one member (or nobody, if that slot is empty) is rolled six times: 82% for each
  ordinary item and 99.9% for each rare one. The others lose nothing but half their gold.
  **[code]** (disassembly 0x800c5c28: `lb v0, actor_member`)
- **Weapon effects ignore level difference.** `melee_apply_hits` computes a bonus of a
  quarter of the level difference (capped 30) or a penalty (capped 20) and passes them to
  `apply_status_effects`, which never reads its third and fourth arguments. **[code]**
  (disassembly: $a2 is overwritten at 0x800aa1d0 and $a3 is never read)
- **Every spell has a 1% failure floor** through magic resistance (+1 in the formula).
  Probably intended. **[code]**
- **Level drain reads +0x81 the opposite way to the saves.** Traps and breath save on
  rand(20) < +0x81, but drain lands on (rand(255) & 31) < +0x81. Either the field isn't a
  save, or the drain check is backwards. **[inf]**
- `party_melee_tail` (0x800a9268) is the second half of `party_melee`, split by the
  decompiler; its "callers" in MAIN are the executable's calls meant for other overlays.

## Translation impact

- **Bare-handed attacks** pair "fist" with verb 19 and "sharp claws" with verb 20 (the
  same coin), so "{name} swings at X with fist" / "claws X with sharp claws" never cross.
  **[code]** Weapons use verbs 2s+1 and 2s+2 at random for subtype s: 1/2 swords, 3/4
  katanas, 5/6 wands and daggers, 7/8 axes and hammers, 9/10 maces and whips, 11/12 staves,
  13/14 spears, 15/16 bows, 17/18 thrown weapons. **[code]** (subtype order from STATUS.OBJ
  24-32 **[inf]**) Any verb must read with any weapon of its type.
- 119 "The attack misses." is the party missing; 120 "Dodged the attack." is a monster
  missing a party member. **[code]** Both fit.
- 151 (with a line break) is used instead of 150 when the monster's name is 10 or more
  characters (0x800b4cf0). **[code]**
- 187 "It has no effect on {name}" (not 186 "The spell has no effect") is used when the
  attack is an item or innate ability, so it's right that it doesn't say "spell". **[code]**
- 128 "{name} is unaffected" is the saving throw; 186-188 are magic resistance. **[code]**
- 124 "But they're spotted." is the ambush failing. **[code]**
- 141/161 "crumbles to dust" is Matokani only; 171 "vanishes" is Mogato; other deaths
  are 139/159. **[code]**
- 196 "is lost" means the character is deleted (level drained to 0). **[code]**
- 198 "Each survivor gains N experience!": survivors means status below 0x20, so a
  paralyzed or stoned member gets nothing. **[code]** The line is accurate.
- 199 "Carried to the temple." and 200 "Press a button to return to the castle." weren't
  found in BATTLE's code yet. **[inf]**
- The site's claims checked: the Gold armor's 50% break chance, and Matokani's level-8
  limit, are both true. **[code]**
- 174-185 (the "engulfed in" lines) play once a round for each group under an Alchemist
  cloud, for three rounds after the cast, not when the spell is cast. 179/185 "freezing
  cold" is Madalqua, whose element isn't cold. **[code]**
- 189 "The spell has no effect." is also what a summon prints when a summoned group is
  already out. **[code]**
- 262 "Each survivor gains N gold!" only plays when a chest is opened; gold is split the
  same way as experience, among members below status 0x20. **[code]**
- 284 "{name} appears, N of them." is the summon (and the call for help uses 114). **[code]**

## How it was traced

The decompiled BATTLE had no named functions, and the one thing that made it readable
was the random number generator. BATTLE never calls the maze's `rand_upto`; a frequency
count of what BATTLE calls in the executable turned up two tiny LCG functions with 75
callers between them. Every function that rolls dice sits on one of those lists, so
the rules are in about 70 of BATTLE's 404 functions, and the rest is drawing.

An emulator run on `battle_wriggle.state` with breakpoints on both generators logged
each roll's caller and range (`rips/re/work/D/round.py`): rand(20) from 0x800a9218 is the
to-hit roll, rand(3)/(4)/(8) from 0x800c9780 are damage dice, rand(10) from 0x800cf990 is
initiative. From there the to-hit function led to the combatant records, whose 14-byte
layout came from the way every function indexes them (group × 0x7e + member × 0xe).

The spell table fell out of `cast_spell`: it divides the spell number by 21 and by 3,
which gave the four schools of seven levels, and the 84 names in STATUS.OBJ lined up with
a table of 84 code pointers. Most handlers are one call (Halito is `spell_damage_one(2,4)`),
so the dice table above is read straight off them. Ghidra hadn't made functions at 27 of
the handler addresses (they have no stack frame), so naming them in the CSV created them.

The emulator checks came last. With breakpoints on the compare instructions rather than
on functions (0x800a9224 for the party's swing, 0x800ab2ec for a monster's, 0x800d00a4
for the monster tick), each log entry carried both the roll and the threshold in
registers, so the formulas could be checked roll by roll against RAM snapshots of AC,
agility and to-hit. Getting a long enough fight out of two Wriggle Objects meant having
the party Defend every round, which needed the command menu's flow worked out from
screenshots (pick a character, open its menu, Defend, then "Confirm actions?").

The wipe's item loss was found looking for what happens to bodies. The disassembly
confirmed the loop bug the C showed: the member index is loaded from `actor_member`
inside the loop, and the loop counter is never used. The emulator test (with a RAM-write
setup, since a level-5 party doesn't die to Wriggle Objects) showed it plainly: six reads
of `actor_member`, twelve rand(12) calls, all on Uranus's items, and nobody else's items
touched.

Work files: `rips/re/work/D/` (scripts `round.py`, `look.py`, `mdis.py`; FIGHTMSG and
STATUS.OBJ dumps).
