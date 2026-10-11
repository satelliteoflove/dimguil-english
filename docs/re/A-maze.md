# The maze: movement, events, encounters (analyst A)

How Dimguil runs the dungeon, read from MAZE.BIN and the executable routines it uses.
Part of the rules-first code analysis (see `docs/code-map.md`); phase 4 merges this into
`engine-notes.md`. Names are in `scripts/re/symbols/maze.csv`; the decompiled functions
are in `rips/re/decomp/MAZE/` and `rips/re/decomp/MAIN/`. Work files are in
`rips/re/work/A/`.

Every claim is marked:
- **[code]**: confirmed by reading the decompiled C (and the disassembly where noted);
- **[emu]**: confirmed in the emulator (how is said);
- **[inf]**: inferred: the code is read, but what a value *means* is a guess from how
  it's used.

The Ghidra projects were built from our patched files (`rips/q7iso/dimguil`). None of
the routines below is a patch site (MAZE's patches are all in the text printer at
0x800a1fa4-0x800a1fd7), and every data table quoted here was read from the clean disc
(`rips/clean/dimguil`) and compared with the patched one: identical. Emulator runs use
our English build, whose game logic is the same.

Coordinates: x is east (E), and the code's y counts from the north edge, so the fan
sites' N is 23 - y. Area numbers are the game's map indexes (`cur_area`, 0x80079668),
the same as the site's `data/maps/dim/fNN.json`: 0 Grounds, 1-4 Shrine 1F-4F, 5-8
Underground B4-B1, 9-16 Training Maze B1-B8, 18 Area X, 19-22 Area A B4-B1, 23-27
Area B B5-B1, 28-31 Area C, 32-34 Area D, 36-39 Area E, 40-42 Dragon's Cave, 43 Area Z.

## Contents

1. [Answers to the priority questions](#answers)
2. [The maze's frame and its states](#the-mazes-frame)
3. [What happens on a step](#a-step)
4. [When the party is wiped out](#wipes)
5. [Parties left in the maze, over time](#parties-left-in-the-maze)
6. [Picking up bodies yourself](#picking-up-bodies)
7. [Encounters](#encounters)
8. [NPC parties in the maze](#npc-parties)
9. [Square events](#square-events)
10. [Searching, hidden doors and the automap](#searching)
11. [Other findings](#other-findings)
12. [How it was traced](#how-it-was-traced)
13. [Translation impact](#translation-impact)

<a id="answers"></a>
## 1. Answers to the priority questions

1. **What a wipe does.** The party record is saved with every member left on the square
   where they fell. Lost members are deleted, every member's gold is halved, and one
   member's items are rolled for destruction six times over, because of a bug. The
   other members keep everything. In the Training Maze the bodies go straight to town
   instead. **[code]**, with D's independent read of the same code; the
   one-member bug is also seen in the emulator. See [section 4](#wipes).
2. **Do bodies left in the maze lose anything over time?** No. Nothing in MAZE, the
   town, the Edge of Town or the talk code takes items, gold or status from a character
   left in the maze, however long they lie there. Their records are only touched by:
   - item compaction, which moves items, never removes them;
   - the town's stat recompute, which only changes derived bytes, see [section 11](#other-findings);
   - being picked up, by your own party or an NPC party's rescue (fees, see C).

   **[code]** for the list. **[emu]**: 40 nights at the inn and 91 steps in the maze,
   with write watchpoints on the dead characters' records, showed no item, gold, status
   or location change. See [section 5](#parties-left-in-the-maze).
3. **Picking up bodies yourself.** Look for Companions (START menu, MCARD 0x800aebe0;
   F's analysis, which I checked) finds the members of every other party standing on
   exactly your square. The bodies only stay put if the party wasn't moved by Malor or
   the like. It lists them with their worst status and lets you add them to your party,
   up to six. Items and gold go with them untouched. Bodies on an adjacent square only
   give "There are faint traces, but no one was found." **[code]**
4. **Encounters and friendly NPC meetings.** Wizardry's usual random roll per step
   isn't here. Fights come from two sources:
   - "fight squares" (event 0x14): each is rolled once per visit to a floor, at its own
     percentage;
   - up to 16 "roamer" tokens, placed on the floor's roamer squares when you arrive.
     They wander one square per step, and you meet one by sharing its square.

   One token per floor (on most floors) is an NPC party. It's chosen at random among
   the parties allowed on that area group by story flags (npc_flags); a party whose
   fixed first meeting hasn't happened is left out. Fixed meetings stand still on their
   own squares. Meeting a party token hands off to talk mode (game_mode 9) through a
   short approach animation. **[code]** See [sections 7](#encounters) and
   [8](#npc-parties).

<a id="the-mazes-frame"></a>
## 2. The maze's frame and its states

- **Not 0x800a2cd8.** That address is BATTLE's loop (B pointed this out; the code map's
  "maze loop 0x800a2cd8" is wrong). With MAZE resident, main runs `maze_frame`
  (0x800a31d8) for game_state 0 and the maze's other states. The camp (state 3) runs
  `camp_main`, which is B's. **[code]**
- **What `maze_frame` does each frame:** **[code]**
  - It sets the automap bit for the party's square, and for the same square on the next
    area up. Squares whose flag word has bit 0 set are skipped, and so are areas 0, 4,
    8, 9, 0x12, 0x16, 0x1b, 0x1f, 0x23, 0x27, 0x2a-0x2d, 0x30, 0x35, 0x39 and 0x3d.
    **[inf]**: the Investigate map of the floor above? This needs checking.
  - It closes an event box whose countdown has run out.
  - It dispatches on game_state:

    | game_state | Routine |
    |---|---|
    | 0 | `maze_walk` (0x800a96b0) |
    | 4 | 0x800b2e8c |
    | 6 | 0x800b4388 |
    | 7 | 0x800a3824 (event scenes: monolith, mask, machine) |
    | 8 | 0x800ae1c8 |
    | 0xa, 0xb | MAIN 0x8001a628 and 0x8001a848 (floor changes) |
    | 0xd | 0x800b989c |
    | 0xe | 0x800b4490 |
    | 0xf | 0x800b47f4 |
    | 0x10 | 0x800c8640 |
    | 0x11 | pick a member, 0x800ac798 |
    | 0x12 | 0x800ce2f8 |

  - It runs `maze_prompt_result` (0x800befcc) when an event's yes/no answer is
    pending.
- **The camp's exit (`maze_exit_code`, 0x800799a8, B's name):** main reads it after
  `camp_main` each frame. **[code]**

  | Value | Meaning | What main does |
  |---|---|---|
  | 0xfc | Malor | MAIN 0x8001a728, the teleport, then music |
  | 0xfd | Loktofeit | game_mode 3, back to town |
  | 0xfe | Dumapic | MAIN 0x8001d4d4, the map |
  | 0xff | plain exit | game_state 0; frees the three glyph layers, redraws the panels, and calls MAZE 0x800cc718 (`wipe_check`) and 0x800a9268 |

  Separately, `DAT_800796d2` = 0xfa sends the camp's Save to MCARD (game_mode 7,
  state 0x32).
- **START in the maze** sets game_state 0x34, and MCARD's `maze_menu` runs it (F).
  Investigate (調査) comes back to MAZE: 0x800cc5e0 starts the search animation,
  0x800ac500 plays it, loads EVENTMES and calls `square_examine` (0x800bb790).
  **[code]**

<a id="a-step"></a>
## 3. What happens on a step

When a step's animation ends, `maze_walk` runs, in this order **[code]**:

1. `roamer_meet` (0x800abbac): a token on your square starts a fight or a talk.
2. `maze_step` (0x800c5570, G's `maze_step_hp`), unless 0x800798e0 is 1 or 2. It does
   three things:
   - The search roll for hidden doors and some special squares (see
     [section 10](#searching)).
   - Poison and regeneration. Poison is status 0x04: 1 in 4 per step, it takes the
     poison strength (roster +0x78) off HP. Regen is roster +0x8b: 1 in 4, it adds that
     much up to max HP. A character brought to 0 HP is set to status 0x80 (dead) with
     roster +0xc4, the death count, + 1.
   - The step countdowns of the party's spell timers, which live in the party record
     (B's names):
     - Maporfic (+0x18)
     - Latumapic (+0x1c)
     - Litofeit (+0x1e)
     - the attack boost (+0x22)
     - Fofic (+0x26)
     - Diafic (+0x29)
     - the no-magic countdown (+0x2a), which is set to 232 on squares whose flag
       word is negative
3. `wipe_check` (0x800cc718): if every member's status has a bit of 0x1e0 set
   (paralyzed, stoned, dead or ash), set `maze_wiped`. main then loads BATTLE and runs
   `party_wiped`. So a party killed by poison, a trap or a floor in the maze is handled
   exactly like one killed in battle. **[code]**
4. `square_arrive` (0x800ba48c), unless a menu step is pending: the event on the new
   square.
5. If `0x80079bf0` is set (it's set by the step code), `roamer_move` moves the tokens and
   `roamer_meet` runs again, so a token can walk into you. **[code]**

Status bits, from the code and the status names in STATUS.OBJ (0x261+ Japanese, 0xce+
English; Look for Companions prints them by the highest bit set) **[code]**:

| Bit | Status |
|---|---|
| 0x01 | afraid |
| 0x02 | confused |
| 0x04 | poison |
| 0x08 | asleep |
| 0x10 | knocked out |
| 0x20 | paralyzed |
| 0x40 | stoned |
| 0x80 | dead |
| 0x100 | ash |
| 0x200 | lost |

Status below 0x20 counts as standing. A party counts as wiped when nobody is standing:
dead, ash, stoned and paralyzed all count, which is why the fan trick of a paralysis wipe
works. (In battle the line for taking an action is lower: asleep and knocked out, 0x08
and 0x10, can't act either; D-battle.md, "Status bits".)

<a id="wipes"></a>
## 4. When the party is wiped out

The handler is BATTLE's `party_wiped` (0x800c59a0). D has the battle side; this is the
whole of it as the maze sees it. **[code]**, read twice (D and A, independently).

1. **Who can act.** In battle, `count_survivors` (0x800c5280) counts members below
   status 0x20. In the maze, `wipe_check` uses status & 0x1e0. Either way, when nobody
   is left, main loads BATTLE if needed and calls `party_wiped`.
2. **Lost members are deleted first** (`remove_lost`, 0x800c542c). Status 0x200 or
   above means the record is blanked, and the name goes into `lost_names`
   (0x80096720), the last three lost.
3. **Where the bodies go.** If the party's area (`party_area`, party record +0x34)
   isn't in the Training Maze, the current party record is copied back into its
   `parties[]` slot. Every member's location is set to the square where they fell
   (roster +0x7a area, +0x7b x, +0x7c y, +0x7d facing), and the function returns 2.
   In the Training Maze (`map_type_of_area` 30-37, which are areas 9-16), the party
   record is emptied and every member goes to town (area 0xff, x = y = 0) still dead,
   returning 1. That's the fan tip that a wipe in the Training Maze saves the body
   recovery.
4. **Item loss** (`wipe_item_loss`, 0x800c5be8). Each filled slot is rolled with
   `rand_below(12)` (MAIN 0x800215c0, an LCG: uniform 0-11). The item is destroyed
   (slot set to 0xffff, its slot byte to 0) on 0-7 for item ids 72-130, 199-240 and
   277-324, and on 0-2 for any other item.
   - The high-risk ids are the rare weapons (BLADE CUSINART' to GREAT WIZARD WAND), the
     rare armor (SUFFOCATE HELM to BREAST OF EXPERT), and the special items from ANKH
     OF POWER to the TABLET OF THE SUN (0x143 = 323), the four stones (0x136-0x139)
     included.
   - **The bug.** The outer loop runs six times, but it always reads the member at
     `actor_member` (0x800798c8), never the loop counter (the load at 0x800c5c28 is
     `lb v0, -0x6738(v0)` = 0x800798c8, then members[that]). So one member's items are
     rolled six times and the other five keep everything. `actor_member` is the
     battle's acting-combatant index, so which member suffers depends on how the last
     battle went. **[code]**, with the disassembly checked.
   - What that means per item, for the one member: a high-risk item survives with
     (4/12)^6 = 0.14%, an ordinary one with (9/12)^6 = 17.8%. For a fully rolled
     member, nearly everything is gone. The Tablet of the Sun is high-risk, which fits
     the 2000 BBS post about losing it in a wipe.
   - **[emu]**: in the earlier body-recovery trace (`rips/probe/bodies/wipe5_log.pkl`),
     four characters were wiped on the Grounds. Only one of them (roster 3) lost items:
     six of eight, all ordinary (survival 2/8; one roll each would leave about 6). The
     other three kept all their items. The run's setup used RAM writes to put the party
     on 1 HP before a natural battle killed it; the wipe itself and everything after
     ran naturally.
5. **Gold is halved** for every member (0 stays 0). **[code]**; **[emu]** in the same
   run, the gold writes are BATTLE 0x800c5b30-0x800c5bd8.

<a id="parties-left-in-the-maze"></a>
## 5. Parties left in the maze, over time

Chris's question was whether bodies left in the maze lose gear the longer they lie
there. **They don't.** Evidence:

- **[code]** The places that read a character's location (`.area`) are:
  - the town's party cleanup (JOUKA 0x800a2198, which drops members who are back in
    town from their old parties);
  - the Edge of Town resume list (HAZURE 0x800a21b0, 0x800a31d8);
  - Kandi (MAZE 0x800d510c);
  - the Dumapic and camp code;
  - Look for Companions (MCARD 0x800aebe0);
  - the NPC rescue scans (MCARD talk handlers).

  None of them changes items, gold or status for a character in the maze. The only
  other writes that reach those records are:
  - item compaction (JOUKA 0x800d52f0 on entering town, MAZE 0x800e1dfc in the maze);
    it closes gaps by moving items to lower slots, never dropping one;
  - the town's stat recompute (JOUKA 0x800d0574, for every roster record), which only
    changes derived bytes (+0x84, +0x98, +0xb0-0xbd), see [section 11](#other-findings);
  - the NPC parties' rescue, which charges its fee then (C's handlers; see
    C-talk.md §5).

  E (town), F (Edge of Town, saves, resume) and D (battle) each report that nothing
  in their code takes from characters left in the maze. Aging at the inn applies only
  to the character staying (E's `inn_stay`), so a body in the maze doesn't grow old.
- **[emu] 40 nights at the inn** (`rips/re/work/A/decayA.py`). Starting from
  `wipe5_end.state`, with four characters dead on the Grounds and Mars and Mercury in
  town, Mars took the Stables 40 times, with write watchpoints on the four dead records.
  - All 416 writes were the stat recompute's whole-record copies (JOUKA 0x800d0724-30,
    from 0x800d0574) on entering and leaving the inn.
  - Items, gold, status and location didn't change. The bytes that did change were
    +0x84, +0x98, +0xb7, +0xb8 and +0xbd.
- **[emu] a walk in the maze** (`rips/re/work/A/decayB.py`, from the state above).
  Mars and Mercury walked the Grounds, fighting what they met, with the same
  watchpoints.
  - The first run (`decayD`) got 150 steps in, but then sat in one long battle until
    its time limit, and its log wasn't saved. The rerun (`decayE`, saving every 10
    steps) follows the same path, since the button presses are seeded. It was stopped
    in the same battle, and its log at step 91 is kept as
    `rips/re/work/A/decayE_step90.pkl`.
  - In those 91 steps, there were 146 writes to the four dead records, all from
    MAZE 0x800e1dfc, the item compaction (pcs 0x800e1e9c-0x800e1ec0). Only one
    write changed anything: roster 3's two remaining items moved down one slot,
    from slots 2-3 to 1-2, with their state bytes.
  - Items, gold, status and location were otherwise unchanged for all four.
  - 0x800e1dfc shifts the rest of the list down over each empty slot it finds. When
    two empty slots are next to each other, it moves past the second one, which is
    why slot 0 stayed empty. It never drops an item. **[code]**
  - The battle the run stalled in printed garbled text: "Mars looses at Flap Insect
    wi / th / 0088ththerer((phph…" (`decayD_0150.png`). That's the English build's
    battle text, and not maze code; the harness was pressing circle every 20 frames
    mid-message, so it may not happen in normal play. It hasn't been looked into.

**What Chris may remember:** in some other Wizardry games, bodies left too long get
eaten or rot (a modern port of Wizardry 1 does this). Dimguil has no such rule. What
loses items here is the wipe itself (one member, six rolls) and the NPC rescue fees.

<a id="picking-up-bodies"></a>
## 6. Picking up bodies yourself

Look for Companions (START menu; MCARD 0x800aebe0, F's `look_for_companions`).
Checked by reading the code. **[code]**

- **Matching.** It goes through every other party (id not -1 and not yours) and
  compares each member's area, x and y with yours:
  - On exactly your square, the member is a candidate.
  - On an adjacent square (±1 in x and y), the member only counts as "nearby".
- **Messages:**
  - No candidates and nobody nearby: SISETU 7, "No one is here."
  - Only nearby ones: SISETU 0x140, "There are faint traces, but no one was found."
  - Otherwise the candidates are listed by name with their worst status (STATUS.OBJ,
    0x261 + n or 0xce + n by the name-language setting).
  - A full party: SISETU 8, "A party can have six members at most."
  - Otherwise SISETU 6, "Who will join the party?", then you choose a slot.
- **Joining.** The chosen character is removed from its old party (the count drops,
  and an emptied party is freed) and put in your current party. The current party is
  saved back to `parties[]`, and 0x800b2874 rebuilds the character's derived stats.
  Nothing touches items or gold, and the body stays dead until the Temple.

So the bodies are found only on the exact square where the party fell. "Faint traces"
means one square off.

<a id="encounters"></a>
## 7. Encounters

There's no per-step encounter roll. **[code]** A fight comes from one of these:

1. **A fight square** (event type 0x14, in `square_arrive`). On stepping on it, if its
   bit p4 in `fight_squares_spent` (0x800797dc) is clear, it rolls `rand_upto(99)`
   (0-99) against p3. The bit is then set whether or not the fight happened, and is
   cleared when you enter a floor (MAZE 0x800a42c8, 0x800a4498). So each fight square
   is a single p3% chance per visit to the floor. On the Grounds the fight starts
   at once (0x800798e0 = 3). **[code]**
2. **A wandering token** (roamer type 0) that you meet ([section 8](#npc-parties)
   has how tokens are placed and move). **[code]**
3. **A type-2 token** (roamer type 2): the same, with a group from `type2_groups`.
   **[code]**
4. **A fixed fight** from an event (the pillars, the Ruby Hands, etc.: the event sets
   `encounter_id` and `DAT_8007e806`). **[code]**

**Which group** (`encounter_pick`, MAIN 0x80020e10) **[code]**. The map type is
`map_type_of_area[party_area]`, and the full tables, per map type with the areas
using each, are in `rips/re/work/A/encounters.txt`.

| encounter_id | encounter_source | Group |
|---|---|---|
| 0xffff | 2 (fight square) | Roll 0-99: below the first percentage (0x80059df0) is tier 0, below the sum of the two is tier 1, else tier 2. Pick uniformly among the tier's groups (counts at 0x80059e44, three per type). The odds are 65/25/10 on most floors and 57/29/14 in the Training Maze. |
| 0xffff | 0 (wandering token) | Uniform among `wander_groups` (count 0x8005a504). |
| 0xfffe | (type-2 token) | Uniform among `type2_groups`, + 0x154. |
| fixed | 4 | Id + 0x17b, an NPC party as enemies (D). |
| fixed | 5 | Id + 0x154. |
| fixed | other | The id as given. |

The group file is then loaded from table 1, index id + 0x2c.

Group ids are monster group records (D's subject). Type-2 groups (340 and up) are
probably the human enemy parties **[inf]**.

<a id="npc-parties"></a>
## 8. NPC parties in the maze

### Tokens

**On entering a floor**, `roamers_place` (MAIN 0x800185dc) sets up the floor's tokens.
**[code]**

1. The floor's map data has 16 roamer slots (`roamer_slots`, 0x8005de20; 3 bytes:
   type, x, y, from map file offset 0x35d0). Slots with a start square are counted, and
   every slot's type is reset to 0, a wandering monster token.
2. `npc_availability` (MAIN 0x80018bd4) works out, for the area group:
   - which of the parties 0-4 may be met at random (`npc_available`);
   - which fixed meetings are still pending (`npc_fixed_list`, with their parties
     in `npc_fixed_pending`).
3. **NPC party tokens.** `npc_tokens_per_area[area]` of them (0x8005e654, two bytes
   per area). It's 1 on every area except the Training Maze, area 17, the Dragon's Cave
   and Area Z, which have 0.
   - Each one picks a random party 0-4 (rerolled until it's in `npc_available` and not
     pending or already placed) and a random free slot.
   - The token becomes type 1, with `roamer_party[slot]` = the party.
   - None are placed if every available party is pending. None are placed on the
     Grounds or in the Shrine (areas below 5) while any fixed meeting there is pending.
4. **Type-2 tokens.** The second byte of `npc_tokens_per_area` gives how many (0-6 per
   area). They're placed on random free slots.
5. **Fixed meetings.** Pending ones go on their own squares from `fixed_meet_table`
   (0x8005e6ac) as type 3, counting down from slot 15.
6. A token on the party's square is removed. A fight square under the party is
   disarmed for this arrival, so you don't fight on the stairs you came in by.

**Moving.** `roamer_move` (MAZE 0x800c49a0) **[code]**:
- Every token except the fixed meetings takes one step each time it runs, in a random
  open direction. It won't walk through walls or doors, off the map, into another
  token, onto stairs, lifts, teleports, chutes, pits and other blocked event types, or
  onto an unspent fight square.
- It doesn't turn back unless it's stuck.
- When a token comes within one square of the party, a sound plays (0xb if it moved
  through a door, 0xf otherwise). That's the footsteps the player hears. **[code]**;
  the sound ids are **[inf]**.

**Meeting.** After each step and each token move, `roamer_meet` checks for a token on
the party's square:
- Type 0 or 2: a fight.
- Type 1 or 3: a talk. `talk_party` is set from `roamer_party`, SISETU 0x1d8 "You've
  met someone!" is printed, and `meet_start(3)` begins the approach animation.

At its end, `meet_animate` (0x800b4e94) queues game_mode 9, which main turns into an
MCARD talk with the handler for `talk_party`. **[code]**

So there's no fixed meeting chance. On a floor where an NPC party is allowed, exactly
one party token is on the floor somewhere, wandering. You meet it if your paths cross,
which you can hear coming.

### Which party, where

Parties 0-4 are the five random-meeting parties. 0 is Guy's, 1 Balbo's, 2 Fontana's
**[code]**. 3 is Cresson's party (the archive scholars) and 4 Zaril's, confirmed by C
from their handlers and text files (C-talk.md §1).

The fixed meetings 6-0x19 are separate talk ids, each on one square. Their owners
below come from which party bit each one clears in `npc_fixed_pending`. "npc_flags N"
is bit N of 0x80079754, which the talk handlers set (C maps which talk sets which bit).

**[code]** for the rules. The meanings of the flags are **[inf]** where not obvious.

| Areas | Random parties allowed | Fixed meetings while their flag is clear |
|---|---|---|
| 0 Grounds | Guy unless flag 7 | 6, Guy at E11 N4 (the Shrine door), unless flag 0x15 |
| 1-4 Shrine | Guy unless flag 7; Balbo; Fontana; party 4 if flag 5 | 7, Guy at Shrine 1F E11 N8 (flag 0x11); 0xc, Balbo at Shrine 3F E11 N6 (flag 0x12); 0x12, Fontana at Shrine 4F E11 N10 (flag 0x14) |
| 5-8 Underground | Guy unless flag 7; Balbo; Fontana; party 3; party 4 if flag 5 | 8, Guy at B3 E22 N12 (flag 0xf); 0xd, Balbo at B2 E3 N14 (flag 0x10); 0x16, party 3 at B3 E8 N6 (always, so party 3 is never met at random here) |
| 18 Area X | Guy unless flag 7; Balbo; Fontana; party 4 if flag 5 | 0xe, Balbo at E15 N12 (flag 0xc); 0x13, Fontana at E15 N16 (flag 0xd); 0x17, party 3 at E11 N12 (flag 0xe) |
| 19-22 Area A | Guy; Balbo; Fontana; party 4 if flag 5 | 9, Guy at A-B4 E19 N13 (if flag 7 *is* set); 0xf, Balbo at A-B4 E17 N12 (flag 0xa); 0x14, Fontana at A-B2 E4 N12 (flag 0xb) |
| 23-27 Area B | Guy unless flag 7; Balbo; Fontana unless story_flags bit 0xc | 0x10, Balbo at B-B5 E7 N11 (story_flags bit 0x1a) |
| 28-31 Area C | Guy (unless flags 7 and 8 both set); Balbo; Fontana | 0xa, Guy at C-B4 E7 N2 (flag 8) |
| 32-35 Area D | Guy; Balbo; Fontana | 0x11, Balbo at D-B1 E10 N12 (flag 4) |
| 36-39 Area E | Guy; Balbo; party 3 only with its fixed meetings | 0x19, party 3 at E-B4 E12 N12 (flag 2); 0x18, party 3 at E-B2 E12 N14 (flag 0x18) |
| 9-17, 40-43 | none | none |

Fixed ids 0xb (Shrine 3F E7 N8) and 0x15 (C-B4 E11 N4) are in the table but not placed
by `npc_availability`. **[inf]**: they're placed by events or are unused.

This matches the fan records:
- Guy is met from the start, at the Shrine door.
- Balbo's party is first met at Shrine 3F E11 N6 (the two-switch door), then at random
  until later fixed scenes.
- Fontana's party is first met at Shrine 4F E11 N10.
- The Balbo meeting at Underground B2 E3 N14 is fixed.

**For the rescue test:**
- Balbo can be met at random on any Shrine floor, the Underground and Area X onward, but
  only after his fixed first meeting (npc_flags 0x12).
- On the Grounds and in the Shrine, no random party appears at all while any of the
  three fixed Shrine meetings is still pending. So the random Balbo meeting needs Guy's
  1F, Balbo's 3F and Fontana's 4F meetings all done.
- Each floor gets one party token, picked at random among the allowed parties, so
  Balbo is one of up to four candidates each time you enter a floor.

<a id="square-events"></a>
## 9. Square events

Each floor has a 24 x 24 byte map of event record indexes (`square_event_map`,
0x8005d4d0) and up to 131 records of 5 bytes (`event_records`, 0x8005db90: type, p1, p2,
p3, p4). They're mirrored from the floor's map file (offset 0x400 maps to 0x8005ac50).
The site's `tools/extract_dim_maps.py` decodes many types from the disc, and its
readings agree with the code for the types I checked: 1, 6, 8, 0x14, 0x17, 0x41 and
0x4c. **[code]**

There are three routines:
- `square_arrive` (0x800ba48c) runs on stepping onto a square. Types handled: 1
  teleport; 6 chute; 8 ladder; 0xc; 0x13; 0x14 fight square; 0x15; 0x17 lift
  (0x800b31ec); 0x19; 0x1a; 0x2b; 0x3b; 0x41 magic circle; 0x44 and 0x45 (forced
  turns, 0x45 also marking the automap); 0x4a; 0x4c teleport to another map; 0x61;
  0x64; 0x65; 0x67-0x69; 0x6f.
- `square_examine` (0x800bb790) runs on Investigate, against the side you face.
  - Signs and murals (0x20, 0x23 and more).
  - Locked and sealed doors (2, 0x1e, 99).
  - The four pillars on the Grounds (0xe-0x11): each needs you at its square and
    facing. If its done bit in `maze_event_flags` (0x4000, 0x8000, 0x20000, 0x10000)
    is clear and the party carries neither its stone (0x136-0x139) nor the Tablet
    (0x143), EVENTMES 0x18/0x1a/0x1e/0x1c plays and the guardian fight starts. If the
    bit is clear but you already have the piece, the other string plays.
  - The jewel ceiling (0xc), the machines (0x22, 0x2a), the ice pillar (0x27), and many
    more. The full case list is in the CSV note.
- `maze_prompt_result` (0x800befcc) runs the outcome of an event's yes/no prompt.
  `maze_prompt_pending` picks the scene (1-0x20) and `maze_prompt_answer` 0 is yes. It
  prints the yes or no string and starts the scene.

  | Prompt | Strings (yes / no) | Scene |
  |---|---|---|
  | 3 | 20 / 21 | the jewel lift |
  | 4 | 36 / 37 | the monolith |
  | 2 | 40 / 41 | the jade mask |
  | 6 | 61 / 62 | the statue |
  | 7 | 67 / 70 | the machine's lever |
  | 5 | 84 / 85 | the winding drum; flips story_flags bit 2 each time |

  **[code]**

`rips/re/work/A/event_calls.txt` lists every EVENTMES string MAZE prints with a
constant, by routine and case. That's 115 strings. The rest go through variables, so
the list isn't complete. For the strings it covers, it's a code-derived check on
`docs/event-map.md`.

<a id="searching"></a>
## 10. Searching, hidden doors and the automap

- **Hidden doors are noticed, not searched for.** On a hidden-door square (event 3),
  every step makes a roll in `maze_step` **[code]**:
  - The searcher level is the best Thief or Ninja level (class 3 or 0xc, roster
    +0x0b & 0x1f, per G) among members who can act, or level - 2 (at least 1) for
    classes 7 and 8 **[inf]** (two more classes; G has the class list).
  - Diafic (B: 232 steps) adds half the party's highest level.
  - The chance is (searcher + Diafic bonus - p2) x 25 percent.
  - On success, if the door isn't found yet (`DAT_80079628` bit p1 clear),
    "You sense something strange!" (SISETU 0x1de) shows, and the next examine finds it
    ("Found a secret door!", SISETU 0x1dd, in `square_examine` case 3, which sets the
    bit).
  - With no Thief, Ninja or class 7-8 member, there's no roll at all.
  - Diafic also makes the special squares (types 0xd, 0x28, 0x2f, 0x33, 0x34, 0x3a,
    0x3c, 0x40, 0x42, 0x43, 0x47, 0x48, 0x57, 0x5c, 0x61, 0x6c) always give the
    "something strange" message.
- **The automap** is `automap_seen` (0x8008c580), one bit per square, 3 bytes per
  row, 0x48 bytes per area. `maze_frame` sets it for every square the party stands on.
  **[code]**

<a id="other-findings"></a>
## 11. Other findings

- **`party_store_pos` (MAIN 0x8001bbc8) has an odd branch.** It's meant to write each
  member's position. But it writes `cur_area` only when the member's roster index is 0
  (and then always into roster[0]), and 0xff for everyone else (disassembly at
  0x8001bbf8: `beqz v1` on the index). It runs on entering the maze and at the start of
  every camp frame, and `camp_main` (and the maze's own save, `camp_save`) write
  `cur_area` for every member right after. So it doesn't seem to leave a wrong value
  behind. **[code]**; the "no lasting effect" is **[inf]**.
- **The town's stat recompute runs for characters in the maze too, and drifts.** JOUKA
  0x800d0574 copies a record to 0x8008ff10 and adds the bonuses of identified, equipped
  items (0x800d0754, 0x800d08f4: AC, resistances at +0xb0-0xbd capped at 100, and
  more), then copies it back.
  - It's called from many town routines, including on entering a building.
  - It doesn't reset first: in the inn test, the dead characters' +0x84, +0xb7 and
    +0xb8 rose by 4-5 and +0xbd fell by 2-12 at each pass.
  - Whether a character's derived stats are rebuilt from scratch somewhere else (for
    example when the party sets out) is G's and E's question. **[emu]**; the
    accumulation is **[inf]** until G confirms the fields.
- **`roster` writes during the inn and the maze trip** are listed in
  `rips/re/work/A/decayA.pkl` and `decayE_step90.pkl`, for anyone tracing the record copies.

<a id="how-it-was-traced"></a>
## 12. How it was traced

The wipe was already half-known from the body-recovery trace on 2026-10-10. That agent
had left RAM dumps and a write log of a wipe (`rips/probe/bodies/wipe5_log.pkl`).
Replaying that log over the dump taken before the wipe (`rips/re/work/A/replay.py`)
showed the item writes coming from BATTLE 0x800c5cb8, inside 0x800c5be8. Its C showed
six passes over one member, and the disassembly confirmed the loop never indexes by its
own counter. D had found the same bug from the battle side.

For Chris's time-decay question, the code was searched for every reader of the
location byte and every writer of items, gold and status. Then two long emulator runs
put write watchpoints on four dead characters: one at the inn, one in the maze. The
only writes were record copies and compaction.

The encounter system was the surprise. Looking for a random roll per step found
`maze_step` (poison and timers) and no roll. Following the step's other calls led to
`roamer_meet` and its 16 token positions, and from their writers to `roamers_place` and
`npc_availability`. Those two hold the whole friendly-meeting logic: one wandering
token per floor, which parties may be met, and the fixed first meetings. The fixed
squares, converted to the fan sites' E/N, land exactly on the known meeting places.
That was the check that the reading was right.

Emulator driving notes, for the next person:
- In the maze, Cross opens and closes the camp (game_state 3). Up steps, and
  left, right and down turn.
- A dead party's records are best watched with `Emu.watch` over roster + 0xd0 x n. The
  harness logs every write with pc and ra, and `replay.py` turns a log into
  field-level changes.

<a id="translation-impact"></a>
## 13. Translation impact

- **Balbo's "Finders keepers" line (NPC_MES2 144) is true to the game.** His rescue
  takes the items. A wipe on its own costs only one member's items (six rolls) and
  everyone's gold halved. Nothing takes the rest of the gear later, so Balbo's fee is
  the real cost of his help, and there's no "they'd have lost it anyway".
- **"There are faint traces, but no one was found."** (SISETU 0x140) appears when the
  bodies are one square away. The English fits.
- **"You sense something strange!"** (SISETU 0x1de) is the hidden-door hint from a
  Thief or Ninja (or Diafic), shown on the step before Investigate can find the door.
  "Found a secret door!" (0x1dd) is what Investigate prints. Both fit.
- **"You've met someone!"** (SISETU 0x1d8) prints for every token meeting, fights
  included (`roamer_meet` prints it for both kinds). Worth a check in play that the
  English reads well before a fight.
- **NPC meeting order.** The table in [section 8](#npc-parties) gives, from the code,
  where each party's fixed scenes are and when random meetings start. The walkthrough
  quotes and docs/npc-map.md can be checked against it. One example: party 3 is never
  met at random in the Underground, only at its fixed meeting at B3 E8 N6.
- **Event strings by trigger:** `rips/re/work/A/event_calls.txt` ties 115 EVENTMES
  strings to their event type or prompt, from the code. The no-answer strings of the
  prompts (21, 37, 41, 62, 70) all play when the player declines. The paired "Heeding
  the warning, you draw your hand back." (37, 62) is the same line in two scenes, which
  the English already keeps.
