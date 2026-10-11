# Parties left wiped out in the maze: everything that touches them

Chris's question (2026-10-11): which routines touch a fallen party left in the dungeon,
and does anything take its items later, for example on going back into the maze after
40 nights at the inn? This is a phase-3 check over the decompiled C rebuilt from the
original disc (commit 585c983), with every analyst's names applied. New names are in
`scripts/re/symbols/fallen.csv`. Scratch files are in `rips/re/work/P3-fallen/`.

**[code]** = confirmed by reading the C (and the disassembly where marked).
**[emu]** = confirmed in the emulator, button presses only. **[inf]** = inferred.

## The answer

Nothing takes items, gold or status from a fallen party after the wipe, however long it
lies there. That includes time at the inn, going back into the maze, changing floors,
and walking onto the square where the bodies lie. **[code]** for the whole list below,
**[emu]** for the 40 nights at the inn (A), the walk from the Edge of Town into the maze
and onto the bodies' square (this check), and the camp opened on arrival.

The things that do change a fallen party, after the wipe itself, are:

1. **Pick-ups.** Look for Companions takes them for free. An NPC rescue charges Guy's,
   Balbo's or Fontana's fee (C).
2. **BROKEN ITEMs vanish.** Every time any party enters town or opens the camp, the
   game empties every slot holding item 0, BROKEN ITEM, from every character in the
   roster, the dead in the maze included. A broken item is worthless, but it is an item
   taken from bodies left in the maze. **[code]**
3. **Item compaction.** At the same moments, every character's items are moved up over
   empty slots. Nothing is dropped. **[code, emu]**
4. **Derived stats.** On entering town, the stat recompute rewrites every character's
   derived bytes (AC, resistances, regen; A saw them drift). Items, gold, status and
   location are untouched. **[code, emu (A)]**
5. **One square of the Grounds.** Resume Adventure moves anyone saved at area 0x17,
   (4,11) to (5,11), dead or alive. **[code]** (F)
6. **A bug at the Temple** (below) can scramble the party table, after which the bodies
   may belong to no party at all, and nothing can find them.

## The Temple bug

When a raise from ashes fails at the Temple, the character is Lost: the record is
deleted and the roster is compacted, so every record above it moves down one slot.
Every other place that deletes a character then renumbers the party table:
- the battle (`remove_lost` → `party_index_fixup` 0x800c5874)
- camp Kadorto (`remove_lost_members` → `party_drop_member`)
- the Edge of Town's Kadorto (HAZURE 0x800bf054 → 0x800be80c)
- town entry and the inn (JOUKA 0x800dd370 and 0x800dcf18 → 0x800dcdec)
- Training Grounds deletion (inline in `training_delete`)
- reordering (inline in `training_reorder`)

`temple_heal` doesn't. The Lost path at 0x800cb024-0x800cb04c sets the name to ff40,
calls `roster_compact` (jal 0x800dcb70 at 0x800cb030), prints string 0x9d and jumps
away. No renumbering follows. **[code, disassembly]**

So every party whose members sit above the lost character in the roster ends up pointing
one record too high. That includes a fallen party in the maze. What follows is
**[inf]**, read from the town's party cleanup in `town_main` (0x800a2198), which runs on
entering town:
- The fallen party now lists other characters. If one of them is in town (area 0xff),
  the cleanup breaks the party up (id -1, count 0).
- On the next entry to town, whoever is still listed in that broken-up party is sent to
  town (area 0xff). If that's a member of another fallen party, they come home for free,
  still dead.
- The real bodies keep their place in the maze, but no party lists them any more. Look
  for Companions, the NPC rescue scans and Resume Adventure all work from the party
  table, so none of them can find those characters. The tavern only takes characters in
  town. They're stranded. Kandi, which reads the roster directly, still points to them.

Not yet seen in the emulator. A test needs ashes, a failed raise (a roll of 68 + 2×VIT
or more), and a fallen party higher in the roster than the character being raised. A
one-line fix would add the renumbering call after the compaction. That's for the bug
list.

## Every routine that writes characters or the party table

"Fallen" means a character whose party lies wiped in the maze: not the current party, and
area ≠ 0xff. "Current only" means the routine touches the party you're playing with (the
mirror at 0x8007e810), or one picked character, never a fallen one.

### Can change a fallen character or its party

| Module | Address | Name | When it runs | What it changes for the fallen | |
|---|---|---|---|---|---|
| BATTLE | 0x800c59a0 | `party_wiped` | the wipe | the wipe itself: gold halved, one member's items rolled six times (bug), Lost deleted, square saved | code (A, D), emu (A) |
| JOUKA | 0x800a2198 | `town_main`, entry | entering town | party table cleanup: drops duplicate members; breaks up a party with a member in town; sends members of a broken-up party to town | code |
| JOUKA | 0x800db4c4 | `broken_items_purge` | entering town, every roster record | empties slots holding BROKEN ITEM (and zeroes item_state[9], sic) | code |
| JOUKA | 0x800d5250 | `items_compact` | entering town, every roster record | moves items up over gaps | code |
| JOUKA | 0x800dcb70 | `roster_compact` | entering town, deletions | moves records down over deleted ones (renumbered by the callers, except the Temple) | code |
| JOUKA | 0x800d0574 | stat recompute | town_state 3, every roster record; also per character in shops, inn, training | derived bytes only (+0x84, +0x8b regen, +0x98, +0xb0-0xbd) | code, emu (A: 416 writes in 40 nights) |
| JOUKA | 0x800c95f0 | `temple_heal`, Lost path | a failed raise from ashes | compacts without renumbering: the bug above | code, disassembly |
| MAZE | 0x800ce564 | `camp_main`, state 1 | opening the camp, every roster record | runs `broken_items_purge` (0x800e6260) and `items_compact` (0x800e1dfc) | code, emu |
| HAZURE | 0x800a31d8 | `edge_resume_enter` | Resume Adventure | moves anyone at area 0x17 (4,11) to x 5 | code (F) |
| HAZURE | 0x800a21b0 | `edge_resume_adventure` | Resume Adventure | restores the party table from `parties_saved`, which the Edge of Town took on entry, so it's current; makes the chosen party current if anyone in it can act | code (F) |
| MCARD | 0x800aebe0 | `look_for_companions` | START menu in the maze | moves bodies on your exact square into your party and out of their old one; items and gold untouched | code (F, A) |
| MCARD | 0x800b5694, 0x800c7264, 0x800cf8c0 | `talk_guy`, `talk_balbo`, `talk_fontana` | rescue accepted | area 0xff for every member of one wiped party, plus the fee | code (C) |
| MCARD | 0x800ac670 | `roster_restore` | loading a save | rebuilds every record from the save image (+0x00-0x7d, kills, deaths, +0xc5..); the derived block is rebuilt by the town's recompute | code (F) |
| MCARD | 0x800ad440 | `parties_restore` | loading a save | the party table from the save | code (F) |
| MCARD | 0x800ad018 | `save_data_reset` | a save that fails its checksum | resets the game data; sets roster[0..5].area = 0xff (records 0-5, not the party's members, sic) | code |
| BATTLE, MAZE, HAZURE, JOUKA | 0x800c55f8, 0x800e7ad0, 0x800be590, 0x800dcb70 | `roster_compact` | after a deletion | record moves, then renumbering (`party_index_fixup` / `party_drop_member`) | code |
| JOUKA | 0x800b32d4, 0x800b6eec | `training_delete`, `training_reorder` | Training Grounds | record moves with renumbering | code |

### Current party only (never a fallen character)

| Module | Address | Name | What |
|---|---|---|---|
| MAIN | 0x8001bbc8 | `party_store_pos` | position on entering the maze (A's odd branch; the camp rewrites it) |
| MAZE | 0x800e5a58 | `party_save_position` | position, current party → its parties[] record, save image (copies in MCARD 0x800b21f0, HAZURE 0x800bbc14) |
| MAZE | 0x800d903c | `camp_save` | Save Adventure |
| MCARD | 0x800afd54 | `maze_save_suspend` | Save and Suspend |
| MAIN | 0x80021a0c | `party_snapshot` | parties → parties_saved (a copy, no change) |
| MAIN | 0x80020bb8 | `roster_snapshot` | roster → save images (a copy, no change) |
| BATTLE | 0x800c542c | `remove_lost` | Lost members of the current party |
| BATTLE | 0x800cb900 | `party_record_clear` | empties the current party's record |
| MAZE | 0x800e859c | `remove_lost_members` | after camp Kadorto |
| HAZURE | 0x800bf054 | `remove_lost_members` | after the Edge of Town's Kadorto |
| JOUKA | 0x800dd370, 0x800dcf18 | `remove_lost_members`, `inn_party_upkeep` | town entry, inn |
| JOUKA | 0x800c5e34 | `inn_stay` | aging, HP, level-up for the character staying |
| JOUKA | 0x800a846c, 0x800aa0a4 | `tavern_add_member`, `tavern_remove_member` | only characters in town |
| MAZE | 0x800d0514, 0x800d7150 | `camp_cast_spell`, `camp_use_item` | Malor, Loktofeit, Kadorto and items: the caster's party |
| BATTLE | everything else | | the party in the fight |
| MCARD | the talk handlers, apart from the rescue | | met bits, sales, healing: the current party |
| MAIN | 0x8001d570 | new game | clears everything |

### Read only

`kandi_locate` (MAZE 0x800d510c), Dumapic, the NPC token placement and availability (A),
the rescue scans, the Resume list, the Training Grounds' view (E), `town_redraw`.

## The emulator check

From `rips/re/work/A/decayA_afterinn.state`:
- **Provenance.** It descends from `rips/probe/bodies/wipe5_end.state`. That run put the
  party on 1 HP with RAM writes, then a natural battle wiped it (A §4). Everything from
  the wipe on ran on its own. Its resident FIGHTMSG is from an older build, so its battle
  text is stale. Battle text plays no part here.
- **Starting point.** Roster 0-3 lie dead (status 0x80) on the Grounds at (11,19), just
  inside the Shrine's outer door, as party 0. Mars and Mercury (roster 4-5, party 1) are
  in town after 40 nights at the inn.

Write watchpoints were set on roster 0-3 and the whole party table. Scripts:
`enter.py`, `walk.py`.

1. **Town → Edge of Town → maze** (`enter.pkl`): 0 writes.
2. **Arrival.** The game opens the camp on arrival, and `camp_main` (from 0x800cebd0)
   ran `items_compact` over every record: 146 writes. Only roster 3 changed: its two
   items moved from slots 2-3 to 1-2, with their state bytes. Nothing was lost.
3. **Leaving the camp.** `party_save_position` (0x800e5ba8-0x800e5c20, from 0x800cf588)
   rewrote party 1's record with the same values. No byte of the table changed.
4. **Walking.** The party went (10,22) → (10,21) → (11,21) → (11,20), opened the door
   and stepped onto (11,19), the bodies' square: 0 writes.
5. **End result.** Roster 0-2 unchanged. Roster 3 only compacted. Every location still
   (0, 11, 19), status 0x80. Party table unchanged.

## Translation impact

None directly. For the walkthrough: bodies keep everything but BROKEN ITEMs for as long as
they lie there, and Look for Companions on the exact square is the free way home. A
failed raise from ashes at the Temple can strand another party's bodies (the bug above),
until it's fixed.

## How it was traced

The list started from A's (§5). The writers of the roster and the party table came from
`globals.json` and `fielduse.py`. Then every function with a loop over all 20 roster
records was read. That turned up the two broken-item purges, which run over every
record, not just the party's.

The four `roster_compact` copies led to the question of who renumbers the party table
afterwards. Every caller does, except the Temple, and the disassembly confirmed that
nothing follows its compaction. The emulator run repeated A's setup and added the trip
into the maze, the arrival camp and the bodies' square.
