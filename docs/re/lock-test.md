# Locked doors and chests, tested in play

The play harness never reached a lock: chapter 1 has no ordinary locked door, and the
harness opened chests only where they're known to be safe. This test plays the locked-door
menu and the chest menu through in the emulator, counts the tries against the rules read
from the code, and checks the English on every screen involved.

Run 2026-10-13. Scripts, states, logs and screenshots: `rips/re/work/locks/` (not
tracked). Screenshot names below are relative to `rips/re/work/locks/shots/`.

## Method

- **Build.** The published English WIP, `Wizardry - Dimguil (English WIP).bin`, md5
  `06c9523ad68909f36dfc9746f6fb7c3a` (version.txt: a8df9cc, 2026-10-13T13:16:55; the
  harness's disc 2540ecc is the same file). Copied to `locks/disc/dimguil-en.bin` before
  the first boot; every state used was loaded on that copy.
- **Standard.** Button presses and save states only. RAM was read, never written.
  Breakpoints on the game's own compare instructions logged the numbers each try used
  (chance, roll, skill, difficulty, which roster record was read); they change nothing.
- **Harness.** `scripts/harness` imported, not edited (a regress round held the lock the
  whole time). `chapters.Run` with `auto_cases=False`, its checkpoints in `locks/run*/`,
  so nothing was added to the regression cases.
- **Party.** Harness variant 3, the only one with a created Thief: Venus (Samurai),
  Earth (Priest), Mercury (Thief, premade), Jo (Thief), Kai (Mage), Lu (Priest).
  Shrine tests start from `rips/harness/chapters/f1v3/goal_27_train_09` (all level 9),
  Underground tests from `f1v3f/final_fail` (levels 10-13, chapter 5 in progress). Nobody
  in any harness party knows Calnova (Alchemist level 7), so the spell was only tested as
  "not known".
- **The random numbers.** The maze's `rand_upto` (0x8001cb18) doesn't move with time;
  standing still, turning, opening the camp or Investigating leave it alone, and roamers
  stepping and floor changes move it. Reloading a state and repeating the same presses
  gives the same roll every time, so each door trial first walks k times off the door
  square and back, and after a failure walks until the penalty has worn off, the way a
  player would come back to it (`doortest2.py`). Battle uses `rand_below`, a separate
  LCG; each chest's actions were tried from the same saved chest menu (`chest.py`), so all
  the actions on one chest see the same first roll, and each chest is one independent
  sample. For Rainbow Flash, a fight was refought with different commands until its chest
  had one (`rainbow.py`, below).

## Locked doors

### What the code says

Investigate (START menu) facing a locked side runs `square_examine` (MAZE 0x800bb790).
Event type 2 (a plain locked door, SISETU 516 "The door is locked.") and type 0x1e (the
ornate door, EVENTMES 33) open the lock menu, game_state 8, `FUN_800ae1c8`:
"Who will pick the lock?" (518), a member picker, then **Force the lock** (522),
**Unlock with a spell** (523), **Give up** (524). Nothing else is on the menu; there is
no Desto-type spell in Dimguil, only Calnova. A member whose status has any of 0x3e0
(paralyzed, stoned, dead, ashes, lost) gets "{name} can't act." (525) and the picker
again; asleep, afraid and K.O. members can pick.

- **Force the lock.** "Picking the lock..." (526) with an animation of 20 dots, then one
  roll: success on `rand_upto(99)` < chance, where chance is 70 if
  (level + 5 for a Thief or Ninja, + 2 for a Ranger or Bard) × 5 + Luck, divided by 10,
  is at least the door's difficulty (event record byte 2), else 15; minus the party's
  pick penalty (0x8007e838). Success prints "* Success! *" (520) and sets the door's bit
  in 0x800795fc (saved with the game, global to all parties); failure prints
  "* Failed! *" (521) and adds 10 to the penalty, to at most 50. The penalty drops by 1
  a step (`maze_step_hp`), and is cleared on entering a floor (0x800a4498) and in town.
  **But the level, class and Luck are read from the wrong character** (bug below).
- **Unlock with a spell.** The chosen member must know Calnova (`spells_known[2][3] & 2`,
  Alchemist level 7) or gets "You don't know the spell." (517); with no level 7 Alchemist
  point, "Not enough spell points." (519). Otherwise the point is spent, then it fails on
  `rand_upto(99)` > 94 or on an anti-magic square (`nomagic_steps`), so 95%, with no
  penalty and no class or level term. Calnova can't be cast from the camp.
- **Give up**, or cross at the menu or the picker: back to walking, nothing spent.
- **No cost beyond the penalty.** A failed pick or spell sets no trap, does no damage,
  calls no monsters and makes no noise; the code has none of these.

Doors with a lock (raw bit 25 of the square's flags, direction in bits 26-27; the site's
`locked` list):

| Door | Site square | Event | Lock menu | Difficulty |
|---|---|---|---|---|
| Shrine 1F, the ornate door | E11N8 north | 0x1e, bit 1 | yes | 1 |
| Underground B3 | E22N12 west | 2, bit 2 | yes | 1 |
| Underground B4 | E4N15 east | 2, bit 3 | yes | 13 |
| Area D B2 (two sides) | E12N13 west, E13N12 south | 2, bits 5, 6 | yes | 8 |
| Grounds, the Shrine's front door | E11N4 north | 0x12 | no: EVENTMES 11, then 12-16 by stones and Tablet | |
| Shrine 1F, the front door from inside | E11N5 south | 0xb | no: EVENTMES 75 facing south opens it | |
| Underground B3, the moon door | E19N4 north / E19N5 south | 0x15 | no: the Tablet opens it (EVENTMES 80, else 81) | |
| Area A B4, two doors | E19N10/E19N11, E17N12/E18N12 | 0x32 on two of the four sides | no | |
| Area C B2 | E11N10 north | 0x4d | no | |

`maze_walk` (0x800a96b0) treats a lock bit as shut unless the square's own event is
type 2 or 0x1e and either faces another way or has its bit set. So only the five type 2
and 0x1e doors can ever be unlocked by the party; the rest open through their events.
Pressing circle into a locked side prints "The door is locked." (SISETU 527).

The 3F side doors are a different kind: event 99 ("sealed") on the side, no lock bit,
opened by the two switches (story_flags bit 1); Investigate gives EVENTMES 10 "The door is
shut tight, and there isn't even a keyhole."

**The five lock bits on sides with no door** (harness-plan.md, T2):

| Site square | Side | What's there | Effect (code) |
|---|---|---|---|
| Grounds E11N5 | north | a no-entry square inside the Shrine's footprint | none: the party can't stand there |
| Training Maze B8 E10N11 | south | a wall (event 0x59) | the wall blocks anyway; circle at it would print "The door is locked." |
| Area B B5 E5N12 | south | open (event 0x3d) | none: the walk only checks a lock where there's a wall or a door |
| Area D B3 E11N17 | north | open | none |
| Area D B3 E11N18 | south | a wall (the other face of the same edge: a one-way wall) | as B8: circle at it would print "The door is locked." |

None of these is on the harness's route, so they're from the code only.

### The bug: the pick reads the wrong character

The pick's roll (0x800aea44-0x800aeb44) reads the level, class and Luck from
`roster[*(u8 *)0x80079791]`, not from the chosen member (0x800798d1, which the status
check and the spell use). 0x80079791 is the member picker's blink counter
(`FUN_800ac6bc`, called every frame by the picker): it steps 1, 2, 3, 4, 5, 4, 3, 2, 1,
1, ... every 4 frames. So the skill compared with the difficulty is that of roster entry
1 to 5 (the Training Grounds' second to sixth characters, in or out of the party, alive or
not) depending on how long the picker was open. The chosen Thief's level and Luck never
count, and an empty roster slot there gives skill 0, so 15% even on difficulty 1.

Seen in play (1F door, every try logged): Mercury, the Thief, chosen 22 times and Kai, the
Mage, 7 times; the records read were roster 1 (2 tries), 2 (3), 3 (7), 4 (7) and 5 (10),
and the skill compared was always that record's: Mars, level 5 Bard, Luck 12, gives 4;
Mercury, level 9 Thief, Luck 13, gives 8; Jupiter, level 5 Valkyrie, gives 3. On the B4
door the same: Kai, the Mage, chosen and Mercury's skill used, and the reverse.

In practice: on the two difficulty-1 doors anyone in roster slots 1-5 with a level passes,
so it's 70% whoever picks; on B4 (difficulty 13) a level 13 Thief with Luck 15 would get
skill 10 and 15% anyway, and only a level 18+ Thief or Ninja would reach 70%, which this
bug denies unless one sits in roster slots 1-5. On Area D's doors (difficulty 8), a level
13 Thief would pass but a level 5 premade in slots 1-5 wouldn't. Not fixed; Chris decides
(the fix is to load 0x800798d1 at 0x800aea44 and 0x800aeaac). [code, emu]

### Results

Every try below was logged at the game's compare (0x800aeb44: roll and chance;
0x800aeb0c: skill and difficulty; 0x800aeab8: the roster record read) and checked
against the formula above, using the record actually read: **91 tries, no mismatch**.
`rips/re/work/locks/analyze2.py` does the check; the logs are `s1f_door2.jsonl`,
`b3_door2.jsonl` and `b4_door2.jsonl`.

| Door (state) | Difficulty | Trials | Tries | Chance | Opened | Expected | First try opened |
|---|---|---|---|---|---|---|---|
| Shrine 1F ornate door, from E11N8 facing north (`s1f_door_n`) | 1 | 20 | 29 | 70 every try | 20 | 20.3 | 15 of 20 |
| Underground B3, E22N12 facing west (`b3_door_w`) | 1 | 20 | 29 | 70 every try | 20 | 20.3 | 14 of 20 |
| Underground B4, E4N15 facing east (`b4_door_e`) | 13 | 13 | 33 | 15 every try | 5 | 5.0 | 2 of 12 |

(B4: one trial ended where a walk left the party a square off, and several where a fight
during the walking killed the member about to pick; those tries aren't counted.)

- **The penalty.** Retrying at once, the chance fell 70, 60, 50, 40, 30, 20, 20, 20 over
  eight failures (0x8007e838: 10, 20, 30, 40, 50, then held at 50). Walking it off went
  10, 8, 6, 4, 2, 0 over ten steps. Because the maze's rolls don't move while the party
  stands still, the same state retried at once gives the same eight rolls (78, 91, 55,
  79, 97, 85, 29, 46 on 1F) and never opens: a player who retries on the spot is worse
  off than one who walks a few steps first. (`s1f_door_chain.jsonl`, the first run.)
- **No other cost.** In 24 failed tries checked for it, no HP or status changed, no
  fight started and nothing else printed (`hp_same` in the chain log).
- **Unlock with a spell**, by Mercury (no Calnova): "You don't know the spell." (517),
  then "Who will pick the lock?" again; nothing spent.
- **Give up**, and cross at the picker: back to walking, nothing printed.
- **"{name} can't act."** (525) came up in play on B4, when a fight during the walking had
  killed Kai and the next try chose him (`b4_stuck_k0_t3.png`).
- **After it opens.** The door's bit is set (1F: 0x800795fc = 0x2, B3: 0x4). Investigate
  then gives "There is a door adorned with beautiful ornaments." (EVENTMES 34) from either
  side, and the party walks through (`s1f_open_lookN_*`, `s1f_open_lookS_*`).
- **The ornate door's other side.** Only the south face (E11N8 north) carries the lock
  bit, so in the code a party in the hall beyond could walk out without unlocking. In
  play the hall and the 2F rooms above it are reached only through this door, so it
  doesn't come up.
- **Doors with no lock menu**, Investigated and walked into:
  - Shrine 3F side door, E8N8 facing east, before the switches: circle into it gives
    "The door is locked." (527); Investigate gives EVENTMES 10 ("The door is shut tight,
    and there isn't even a keyhole."), no menu (`shrine3f_sealedE_s_*`).
  - The Shrine's front door on the Grounds with three of the four stones: 527 walking
    into it; Investigate gives EVENTMES 11 then 12 ("...something seems to be missing"),
    no menu (`grounds_front_s_*`).
  - The moon door, B3 E19N4, with the Tablet: EVENTMES 80, and the party walks on
    (`moon_*`).

## Chests

### What the code says

After a won random battle (not in the Training Maze, not fixed battles 0x91-0xab) the
chest menu is Inspect, Calfo, Calnova, Disarm, Open, Leave (FIGHTMSG 215-220; `chest_open`
BATTLE 0x800c5ed0). The trap is picked before the menu (`chest_trap_pick` 0x800c6768):
D-battle.md has the odds. The member cursor starts on the first standing Thief, then
Bard, Ranger, Ninja (0x800d89c0); members paralyzed or worse can't be chosen.

- **Inspect** (`FUN_800c697c`): chance = Agility × 6 (Thief), × 5 (Ninja), × 4 (Ranger,
  Bard), × 1 (anyone else), 1 to 95. On `rand_below(100)` < chance it names the real trap
  ("There's no trap", 221, or the name, 222-233). Otherwise, on `rand_below(20)` ≤
  Agility it names one of the 13 at random (so right 1 time in 13), else **the trap goes
  off** on the inspector. A member's answer is remembered for the rest of that chest.
- **Calfo** (Priest level 2): 95% the real trap, otherwise a random name; never sets it
  off. Not known: "You don't know Calfo." (234); no points (235); spells sealed (236);
  afraid (237); nobody in the party with it and a point: "No one can cast Calfo." (243).
- **Calnova** (Alchemist level 7): 85% disarms; otherwise 90% nothing (239) and 10% the
  trap goes off. "No one can cast Calnova." (244).
- **Disarm**: pick a member, then the trap (the 12 names, "Choose the trap.", 251). A
  wrong name sets the trap off at once, with no roll. The right name: chance = 80
  (Thief, Ninja), 60 (Ranger, Bard) or 0 (anyone else), + level - the area's danger;
  under `rand_below(100)` it's disarmed ("{name} disarms the trap!", 241). Otherwise the
  trap goes off when `rand_below(20)` + (5 for anyone but those four classes) > Agility,
  else "Couldn't disarm the trap." (239) and the menu again. On an untrapped chest every
  Disarm succeeds with "There was no trap." (240).
- **Open**: on a trapped chest the trap always goes off; untrapped, "There was no trap."
  and the loot.
- **Who a trap hits** (`chest_trap_effect` 0x800c7010; the saves are rand(20) < the
  save): Stone Shot, Poison Needle and Goddess's Kiss hit the member who acted; Gas Bomb,
  Exploding Box, Magic Drain, Demon's Eye, Rainbow Flash and Spell Blaster hit every
  member who fails a save; Ghost Swarm hits everyone standing; Alarm starts a new fight;
  Teleporter moves the party.

Danger by area (`area_danger` 0x800d7cec through `map_type_of_area` 0x8005a824): Grounds
0, Shrine 1F-3F 1, 4F 2, Underground B4 3, B3 4, B2 5, B1 6. Chests on the Grounds are
never trapped, which is why the harness opens them blind.

### Results

Chests from ordinary fights on Underground B4 and B3 (`chest.py`, runs B to E): at each
chest menu the state was saved and every action tried from it in turn, reloading between
them, so each chest gives one sample of each action. A retried fight replays the same
fight and chest, so repeats were dropped (`dedupe.py`: same area, trap and first roll),
leaving **24 chests**: 13 on B4 (6 untrapped, 3 Poison Needle, 3 Exploding Box, 1 Gas
Bomb) and 11 on B3 (6 Poison Needle, 2 Stone Shot, 1 each Gas Bomb, Exploding Box and
Ghost Swarm). Every try was checked against the rules above, using the chance and rolls
logged at the game's compares (0x800c6b88 Inspect, 0x800c6bbc its Agility roll,
0x800c6f68 Disarm, 0x800c6fac its Agility roll): **226 tries, no mismatch**
(`chestcheck.py`; the logs are `run*_chests.jsonl`).

| Action | Who | Chance (code) | Tries | Right or disarmed | Expected |
|---|---|---|---|---|---|
| Inspect | Jo, Thief, Agility 20 | 95 | 22 | 21 | 20.9 |
| Inspect | Mercury, Thief, Agility 18 | 95 | 20 | 18 | 19.0 |
| Inspect | Venus, Samurai, Agility 15 | 15 | 21 | 2 | 3.1 |
| Inspect | Earth, Priest, Agility 13 | 13 | 3 | 1 | 0.4 |
| Calfo | Earth or Lu, Priest | 95 | 23 | 21 | 21.8 |
| Disarm, right trap | Thief, level 13, B3 (danger 4) | 89 | 17 | 17 | 15.1 |
| Disarm, right trap | Thief, level 13, B4 (danger 3) | 90 | 14 | 10 | 12.6 |
| Disarm, right trap | Venus, Samurai, level 10, B3 | 6 | 9 | 2 | 0.5 |
| Disarm, right trap | Venus, Samurai, level 10, B4 | 7 | 7 | 0 | 0.5 |
| Disarm, right trap | Earth, Priest, level 13, B3 | 9 | 2 | 0 | 0.2 |

(The Samurai's 2 of 9 is lucky, about a 1 in 10 chance, but both rolls were under the
logged chance of 6.)

- **Misses.** Of 24 missed Inspects, 19 printed a random name (all 19 wrong) and 5 set
  the trap off: on untrapped chests 3 times ("Oops! There's no trap!!", below), and twice
  an Exploding Box on one B4 chest, once by Venus and once by Mercury, who missed at 95
  and then rolled 19 against Agility 18 (`runE_c04`). Calfo missed twice, naming the
  wrong trap and setting nothing off. Of 20 missed Disarms with the right name, 13 printed
  "Couldn't disarm the trap." and went back to the menu, and 7 set the trap off, each
  time when the Agility roll (+5 for the non-thieves) came out above Agility.
- **The wrong name** set the trap off all 17 times, with no roll logged.
- **Open** on a trapped chest set it off all 18 times; on an untrapped one it printed
  "There was no trap." and the gold (6 of 6). Disarm on an untrapped chest printed "There
  was no trap." all 23 times.
- **Calnova**: "Who will cast Calnova?" (248) flashes, then "No one can cast Calnova."
  (244), 24 of 24; nobody has it.
- **Traps that went off, and who they hit** (`firesum.py`). A wrong name and Open set
  the trap off from the same saved menu with the same rolls, so they hit the same members
  for the same damage; a failed Disarm or Inspect draws its own rolls first and can hit
  others. The counts below are chests.
  - Poison Needle, 9 chests: only the member who acted, poisoned.
  - Stone Shot, 2: only the member who acted, 18 and 21 damage (danger d8, 4d8 on B3).
  - Gas Bomb, 2: those who failed the save, poisoned (once only Venus, once all but Earth).
  - Exploding Box, 4: those who failed the save, 10 to 25 damage each (danger d10, 3d10 on
    B4, 4d10 on B3); one or two members saved each time (`runB_c04_*`, `runE_c04_*`).
  - Ghost Swarm, 1: every member, each left with 2 to 10 HP, Earth from 117 to 9
    (`runB_c02_*`, `sheet_traps.png`). The two already poisoned stayed poisoned.
  - Rainbow Flash, 1 (found on purpose, below): every member who failed the save got
    one of its five effects. Venus turned to stone, Earth was poisoned, Mercury and Lu
    were paralyzed, Jo died (HP 47 to 0); Kai saved. The Disarm with the wrong name and
    the Open both gave this (`rb_c00_9_open_result.png`, `rb_open_01` to `_05`,
    `sheet_rainbow.png`, `sheet_rainbow_open.png`).
  - Not seen going off: Magic Drain (it came up as a chest's trap three times while
    looking for Rainbow Flash, but those chests were left), Demon's Eye, Goddess's Kiss,
    Spell Blaster, Alarm, Teleporter.
- **Rainbow Flash, found on purpose.** None of the 24 chests had one, so `rainbow.py`
  waited for a fight whose chest record allows it (record 7, the fight's 0x800da74c = 8;
  its traps are Stone Shot, Poison Needle, Magic Drain, Gas Bomb, Exploding Box and
  Rainbow Flash), saved the state at the fight's start (`rb_battle00`, B3), and fought it
  again with the front three parrying in different rounds. The trap is drawn from the
  battle generator when the chest appears, so the commands change it, all within ordinary
  play. Of 71 refights, one gave Rainbow Flash (variant 443; the others gave the five
  other traps), and chest.py's plan ran on it (`rb_chests.jsonl`, `rb_chest00.state`):
  both Thieves named it on Inspect, Calfo named it, Venus's fumble named Goddess's Kiss,
  both Thieves disarmed it (89), Venus failed (6) without setting it off, and the wrong
  name and Open set it off. 10 tries, no mismatch with the rules.
- **Inspect's fumble on an untrapped chest**: "Oops! There's no trap!!" 3 times (Venus
  twice, Earth once), nothing else happens (`runD_c01_2_inspect_result.png`, problem 5).
- The chest's records: the trap is drawn from the fight's chest record (0x80079954, from
  the monsters' data at 0x800da74c), 30 records at 0x801c5400 with a trap mask each. The
  fights met here used records 4 to 8. Rainbow Flash is in record 7 and in most records
  from 9 on, Spell Blaster first in record 8, Goddess's Kiss and Teleporter from 15 and
  18 (`chesttab.py`, `chestidx.py`).

Screenshots: `sheet_c00.png` and `sheet_c01.png` (every screen of the first two chests:
menu, pickers, trap list, results), `sheet_traps.png` (Ghost Swarm, Exploding Box,
"No one can cast Calnova."), and per try `shots/runB_cNN_K_ACTION_{pick,list,result}.png`.

## The English on these screens

Every string below was seen on screen in this build unless marked. Shots in
`rips/re/work/locks/shots/` and the sheets `locks/sheet_*.png`.

Doors (SISETU unless marked):

| String | Japanese | English | Seen | Verdict |
|---|---|---|---|---|
| 527 | 扉はロックされている。 | The door is locked. | walking into any locked side | fine, centered |
| 430, 441 | 調査 / 調査中 | Investigate / Searching... | every Investigate | see problem 3 |
| 516 | 扉に鍵がかかっています。 | The door is locked. | B3, B4 | fine, centered |
| EVENTMES 33 | 美しい装飾品で飾られた扉には,鍵がかけられている。 | The door adorned with beautiful ornaments\nis locked. | 1F | **cut off**, problem 1 |
| EVENTMES 34 | (3 spaces) 美しい装飾品で飾られた扉があります。 | There is a door adorned with beautiful ornaments. | 1F, after it opens | fits, just |
| 518 | 誰が鍵を外しますか? | Who will pick the lock? | all three | fine |
| 522-524 | 力ずくで鍵を外す / 呪文で鍵を外す / 鍵開けを諦める | Force the lock / Unlock with a spell / Give up | all three | fine; cursor on the right line |
| 526 | 鍵開け挑戦中 | Picking the lock... | all three | overlaps the dot animation, problem 3 |
| 520, 521 | * 成功! * / * 失敗! * | * Success! * / * Failed! * | all three | fine, centered |
| 517 | 呪文を覚えていません。 | You don't know the spell. | 1F | fine |
| 525 | {name}は,行動できません。 | {name} can't act. | B4 | off center, problem 4 |
| 519 | 呪文ポイントが足りません。 | Not enough spell points. | no (nobody has Calnova) | reads fine |
| EVENTMES 10, 11, 12, 80 | | (sealed doors) | 3F, Grounds, B3 | fine; 10-12 and 80 were reviewed with the events |

Chests (FIGHTMSG):

| String | Japanese | English | Seen | Verdict |
|---|---|---|---|---|
| 245 | 宝箱だ! どうしますか? | A chest! What will you do? | every chest | fine |
| 215-220 | 調べる / カルフォ / カルノバ / 罠を外す / 開ける / 立ち去る | Inspect / Calfo / Calnova / Disarm / Open / Leave | every chest | fine |
| 246-250 | 誰が 宝箱を調べますか? etc. | Who will inspect the chest? / cast Calfo? / cast Calnova? / disarm the trap? / open the chest? | yes (248 only briefly, before 244) | fine |
| 251 | 罠を選んで下さい | Choose the trap. | yes | fine |
| 221 | 罠は かかっていない | There's no trap | yes | fine (no stop by decision, translation-notes) |
| 222-233 | 石つぶて ... テレポーター | Stone Shot, Poison Needle, Magic Drain, Gas Bomb, Exploding Box, Ghost Swarm, Demon's Eye, Rainbow Flash, Goddess's Kiss, Spell Blaster, Alarm, Teleporter | all twelve in the Disarm list; six as inspect results | all fit the list box |
| 239, 240, 241 | 罠を 外せなかった / 罠は かかっていなかった / {name}は 罠を外すことに成功した! | Couldn't disarm the trap. / There was no trap. / {name} disarms the trap! | yes | fine |
| 242 | おっと! {trap}!! | Oops! {trap}!! | Stone Shot, Poison Needle, Gas Bomb, Exploding Box, Ghost Swarm, Rainbow Flash, and "There's no trap" | see problem 5 |
| 244 | カルノバを唱えられるキャラクターがいません | No one can cast Calnova. | yes | fine |
| 252 | {name}は 毒におかされた | {name} is poisoned. | yes | fine |
| 254 | {name}は 体力が激減した | {name}'s strength drains away. | Ghost Swarm | **problem 2** |
| 129 | {name}は {n}のダメージを受けた | {name} takes {n} damage. | Stone Shot, Exploding Box | fine |
| 261, 262 | | {name} obtains {item}! / Each survivor gains {n} gold! | yes | fine |
| 234-238, 243 | | You don't know Calfo. / Not enough spell points. / Spells are sealed. / Too frightened to cast. / You don't know Calnova. / No one can cast Calfo. | no (the priests always had Calfo and points) | read fine |
| 229 | 虹のきらめき | Rainbow Flash | in the list, as an Inspect and Calfo result, and going off | fine, fits |
| 132, 134, 257 | {name}は 石化した / 麻痺した / 死亡した | {name} turns to stone. / is paralyzed. / dies. | Rainbow Flash | fine, centered |
| 253, 256, 258, 259 | | {name} loses spell points. / is blessed. / New enemies have been summoned!! / You've been sent somewhere! | no (Magic Drain, Goddess's Kiss, Alarm, Teleporter never went off) | read fine |

### Problems found

1. **EVENTMES 33 is cut off.** The ornate door's line prints in the one-line message bar
   (`square_examine` case 0x1e, `FUN_8001d368(0x16, 0xa2, 6, 0x21)`), so everything after
   the `\n` is lost: the player sees "The door adorned with beautiful ornaments" and never
   "is locked." (`s1f_i_*.png`, `sheet_s1f_i.png`). The Japanese is one line. Measured on the shots, this font
   runs about 5 pixels a character and the bar's text area ends near x = 318, so the
   English joined into one line ("The door adorned with beautiful ornaments is locked.",
   52 characters, about 265 pixels from x = 22) would fit; so would something shorter.
   EVENTMES 34 is printed the same way and fits (49 characters, x = 34 to 280).
   event-map.md lists 33/34 as "purpose unknown"; this is where they're used.
2. **FIGHTMSG 254 "{name}'s strength drains away."** 体力が激減した is "HP dropped sharply";
   Ghost Swarm sets every standing member's HP to 1-10 and touches no stat. "Strength"
   reads as the Strength stat, the same 力 slip description-check.md found in three item
   descriptions. Something like "{name}'s HP plummets." would say what happens.
3. **"Picking the lock..." runs into its own dots.** After 526 the game draws a row of
   dots, spaced for the Japanese 鍵開け挑戦中 (6 glyphs, no dots of its own). The English
   line is longer, so the first animated dots land on the end of "lock..." and one shows
   as a stray mark under it (`locks/crop_picking.png`, from `b3_t_picking_12.png`). "Picking
   the lock" without the full stops, or something shorter, would leave the dots to the
   animation. "Searching..." (441, 調査中) has the same doubled dots but is short enough
   that they don't collide.
4. **"{name} can't act." is left of center.** The x is computed for the Japanese:
   (320 - 12 × (name length + 10)) / 2 at 0x800ae480-0x800ae498 (`FUN_800ae1c8` state 2),
   so the shorter English sits well left of the bar's middle ("Kai can't act." is
   centered about 50 pixels left) (`b4_stuck_k0_t3.png`).
   Cosmetic; a fix would be a patch to that x or padding in the string.
5. **"Oops! There's no trap!!"** still appears when a non-Thief's Inspect fumbles on an
   untrapped chest (seen 3 times: Venus twice, Earth once; `runD_c01_2_inspect_result.png`). The game "sets off"
   trap 0, prints its name and does nothing. The Japanese says the same nonsense
   (おっと! 罠は かかっていない!!). It's the original's quirk (`FUN_800c697c` returns -1 without
   checking for a trap); the full stop was already taken out (translation-notes).

## Other findings

- **Spell Blaster, corrected.** D-battle.md says it kills "each standing member with any
  Mage spell points". `FUN_800c7e30` checks, for each member below status 0x80 who fails
  the save at +0x82, the first byte of each of the four realms' `spells_known` (mask
  0x7f): anyone who knows a level 1 or 2 spell of any realm dies. The decompiler shows it
  as `roster[0].spells_known[0][member * 0xd0 + 4k]`, which is the member's own record.
  [code; not seen in play]
- **The chest cursor's default** is the first standing Thief, then Bard, Ranger, Ninja
  (0x800d89c0), so a Ninja (Inspect × 5, Disarm 80) comes after a Bard or Ranger (× 4,
  60). Harmless. [code]
- **The door's spell skips two checks the chest's makes.** Calnova on a chest refuses an
  afraid caster (237) or a party whose spells are sealed (0x8007e83c, 236); on a door
  only the anti-magic square stops it. [code]
- **The maze's rolls don't move with time.** Besides the penalty, this is why a door
  retried on the spot repeats its failures, and why a harness goal retried from the same
  state meets the same fight and the same chest (one chest came up 13 times in a row in
  `runB`; `chest.py` now skips a chest it has seen, keyed on the battle generator's state
  at the menu). The harness's battle-command variation (round 28) is the right lever.
- **For the harness** (not changed here): `nav.plan` routes through the moon door
  (Underground B3 E19N4) as an open side, and `walk_to` then stops with "no path" at
  (19, 19); every route from B4's east side to the B3 door went that way. Investigating
  the moon door with the Tablet first (as chapter 5's `moon_door` goal does) got through.
  In this test it stopped eight tries in a row of one route to the B3 door and several
  of the chest run's visits (`runB.log`).
