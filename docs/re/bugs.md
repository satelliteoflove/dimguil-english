# Bugs in the original game, and content no code reaches

Every bug and every unreachable string the phase-2 analysts found (`docs/re/*.md`), and
two from the fallen-party audit (`docs/re/fallen-parties.md`). Each was re-read in the
code from the original disc (`rips/clean`, decompiled at 585c983) and confirmed or
refuted. Addresses are RAM; MCARD, JOUKA and MAZE load at 0x800a1000.

Chris's rule (2026-10-11): fix the clear bugs, and reopen content a bug cut off. Bring
anything that looks deliberately cut, and any fix that changes how hard the game is, to
him first. So each entry is in one of three groups:

1. **Clear bug.** Fixed with a small patch in `asm/`, one commit each.
2. **Looks cut, or the intent isn't clear.** A question for Chris, with what reopening
   it would take.
3. **The fix would change difficulty or balance.** A question for Chris, with the effect
   on play either way.

| Group | Count |
|---|---|
| 1. Clear bugs | 11 (10 fixed; 2.8, the pit soft lock, confirmed and waiting on one choice) |
| 2. Cut or unclear, ask | 6 |
| 3. Balance, ask | 3 |
| Not bugs, or harmless | 9 (2.7 and 3.4 moved here after the follow-ups) |

Entries keep their numbers after a follow-up moves them to another group.

## Group 1: clear bugs

### 1.1 Guy's statue warning shows a stranger the wrong line (NPC_MES1 89 for 87)

Handler 7 (`talk_scene_guy_statue_a`, MCARD 0x800c064c) plays Guy's warning about the
statue on the altar: 1:88 to a party that has met Guy, else the stranger's version. The
stranger's string is set at 0x800c0814, `addiu a1, zero, 0x59`: 1:89, "The room up
ahead's got some crazy trap in it!", the trap warning from handler 10. 1:87 is the
"Man with a greatsword" copy of the full statue speech, and nothing else uses it.
Handler 8, the other statue scene, pairs 1:86 with 1:295 the same way. [code]

Fix: 0x57 for 0x59. `asm/bugfix_guy_statue_line.asm`, 29233ff. Checked: disassembly only; no state reaches
the scene with a party that hasn't met Guy.

### 1.2 Rosea's Madi heal plays the "take care" line (NPC_MES2 135 for 134)

Rosea's healing blocks in Balbo's handler (static script data in MCARD) run 20 Dial (2:132), 21 Dialma (2:133), 22 Madi, 23 cancel (2:135 "I see... Do take
care."). Block 22 at 0x800a4dec is `face(6,4,109) say(135) cure(5)`: block 23's face
and line, with the Madi cure added. 2:134 ("Oh my, how awful!" / Madi / "There, all
better.") is her Madi line, and no block uses it. [code, dump]

Fix: block 22's expression 4 → 0 (as 20 and 21) and string 135 → 134.
`asm/bugfix_rosea_madi_line.asm`, 54596b4. Checked: script dump and patched bytes.

### 1.3 Cephala's healing table is one block off

Fontana's handler (MCARD 0x800cf8c0) picks Cephala's blocks by number, and the numbers
assume a block for 3:134 ("I don't think I can treat that person.") that the script
array doesn't have: blocks 9 offer (3:132), 10 healthy (3:133), then 3:135 is block 11.
Every number from 11 up lands one block late. [code, dump]
- Her 20% "out of magic" plays Dial (3:141) and heals.
- At stage 1, stone or dead plays "Paralysis" and casts Dialko; paralysis plays the
  poison line and Latumofis (not cured); poison gets Madi.
- At stages 2-3, poison or paralysis plays "can't treat" (3:138).
- Stage 2 dead gets Kadorto; stage 3 dead plays "no magic".
- HP heals land one block late (Dialma for Dial, and so on).

The cancel (block 20, 3:144) was numbered against the real array and is right.

Fix: lower the ten block numbers at 0x800d1934 (0x11), 0x800d1994 (0xb), 0x800d19ac
(0xc), 0x800d19c8 (0xd), 0x800d1a28 (0xe), 0x800d1a88 (0xf), 0x800d1ae8 (0x10),
0x800d1b4c (0x12), 0x800d1bb0 (0x13) and 0x800d1c10 (0x14) by one, except stage 1's
stone/dead (0xb), which goes to 0xe: 3:138, the same line as the missing 3:134 (the
Japanese of the two is identical). `asm/bugfix_cephala_heal_table.asm`, 34cd45c. Checked: block by block against the
script dump.

### 1.4 Alstron's Madi can never be cast (NPC_MES1 157)

In Guy's handler, Alstron's cure for poison, paralysis and stone at stages 2 and 3 is
`(npc_stage & 0xc) == 0xc` (0x800b74c0-0x800b74c8): both stage bits at once. The maze
clears the old stage bit when it sets the next, so it's never true. A member who's
poisoned or paralyzed with full HP gets "That one seems quite all right, I'd say."
Cephala's matching check is `npc_stage & 0x300` (stage 2 or 3). [code]

Fix: `bne v0, v1` → `beqz v0` at 0x800b74c8 (any of the two bits).
`asm/bugfix_alstron_madi.asm`, 1976612. Checked: emulator, RAM-write setup (stage 2,
everyone poisoned): block 14 in 8 of 8 runs before, block 19 (Madi) in 8 of 8 after.

### 1.5 The pit scene skips its middle (NPC_MES3 95-96, 99-100)

`talk_scene_pit` (handler 21, MCARD 0x800d5f8c) builds five blocks every frame: 0 the
fall and Fontana's (or the young samurai's) first lines, 1 the rescuer's voice from above
and "Looks like help has arrived. If you'll excuse us, we'll go on ahead.", 2-4 the
rescuer (Guy, Balbo, or the man in armor). State 5 plays block 0; state 10 goes straight
to 0xf, which picks the rescuer. Block 1 is built, with its two strings filled in from
`talk_str_b + 2` and `+ 3`, and never run. [code, dump]

Fix: state 10 runs block 1 first (talk_block 1, back to state 5), then goes on to 0xf.
The three spare instructions at 0x800d63f0 jump to a few lines placed over an
unreferenced debug routine (MCARD 0x800c57c8, an encounter-id picker drawn with
FntPrint; no caller, pointer or computed address reaches it). `asm/bugfix_pit_scene.asm`,
5b565b9. Checked: disassembly only; no state reaches the pit.

### 1.6 Fritillaria names the wrong "walkin' corpse" (NPC_MES5 17)

`greet_fritillaria_line` (MCARD 0x800dba44) picks 5:16 if a member has 10,000+ kills and
5:17 ("Hey! It's {ff12}, the walkin' corpse!") if one has died 10+ times. [code]
- The loops that find whose name to show test kills (`lw 0xc0`, `sltiu 0x2710`) instead
  of deaths (`lbu 0xc4`, `sltiu 10`), at 0x800dbb98/0x800dbba0 and 0x800dbcc4/0x800dbccc.
  With nobody at 10,000 kills they run off the end of the party (index 6) and copy
  whoever byte 0x8007e818 points at (roster character 0 in every dump we have).
- When both conditions hold, a coin flip is meant to choose: heads sets 5:17 and copies
  the name, then falls through into the kills-only branch at 0x800dbc38, which sets 5:16
  again. So 5:17 never shows when both are true.

Fix: test deaths in both loops, send the tails path straight to the end (0x800dbb34),
and send the heads path into the deaths-only branch (0x800dbc38: `addiu v0, zero, 2`
makes the next `bne s1, v0` take it). `asm/bugfix_fritillaria_corpse.asm`, fc6158f. Checked: disassembly only.

### 1.7 A full Decipher table skips Cresson's speech after the control room (NPC_MES4 24-29)

`marks[0]` bit 1 (+0xca) means two things. Cresson's decipher check sets it on every
member when the table matches 100% (`talk_cresson`, 0x800d77e0: `ori v1, v1, 2`), and
`talk_scene_cresson_mourning` (handler 22, 0x800d91a4) reads it as "already heard
Cresson's speech about Cleo and Bergamot" and sets it after the speech. Nothing else
reads the bit (every access to +0xca in every module was checked). So a party that
finishes the Decipher table first never hears 4:24-29. [code]

Fix: the decipher check no longer sets the bit (`ori v1, v1, 0`). Its flag had no
reader of its own, so nothing else changes. `asm/bugfix_decipher_flag.asm`, 3e36a06. Checked: disassembly only.

### 1.8 Special chat topics with low block numbers are always rerolled

Guy's, Balbo's and Fontana's Talk first sets `talk_block` to a random topic, then
overwrites it with a special topic if the location, stage or a story flag calls for
one, then keeps a special 90% of the time. A special is recognized by its number being
above the random range (`slti talk_block, 0xc`, or `8` for Fontana). Specials numbered
inside that range are always thrown away. [code]
- Guy (0x800b6b28): blocks 9-11, the topics for areas 1-4 and 0x17-0x1b (1:195-210).
- Balbo (0x800c9a28): blocks 6-8, "about other parties", by stage (2:174-187).
- Fontana (0x800d1394): blocks 6 and 7 of the stage-1 specials (3:181-196).

Fix: the first roll stores -1 (no special) instead of a random topic, and the test
becomes "below 0". The random topic was never used: anything not special is rerolled.
For each handler, the `jal rand_upto` and its delay slot (which stores `talk_state`)
are swapped for the store and `addiu v0, zero, -1` (Guy 0x800b670c, Balbo 0x800c951c,
Fontana 0x800d12b0), and the `slti` immediate becomes 0. `asm/bugfix_chat_specials.asm`, a9ed605. Checked: emulator, Guy only, RAM-write setup
(area 1): block 9 never came up before; 20 of 22 runs after.

### 1.9 A failed raise at the Temple scrambles the party table

From the fallen-party audit. When a raise from ashes fails, `temple_heal`'s Lost path
(JOUKA 0x800cb024-0x800cb04c) deletes the record and calls `roster_compact`
(0x800dcb70), which moves every higher record down one slot, but doesn't call
`party_index_fixup` (0x800dcdec) afterwards. Every other deletion does (the inn and
town entry at 0x800dcf98 and 0x800dd370, the battle, camp Kadorto, the Edge of Town,
Training Grounds). Parties above the lost character then list the wrong people, and
the bodies of a fallen party can end up in no party at all, where nothing finds them.
[code, disassembly, emu; the stranded bodies are inferred]

Fix: the `jal roster_compact` at 0x800cb030 calls a short routine that runs
`roster_compact` and then `party_index_fixup` with the Temple's character
(0x80079888), placed over JOUKA's unreferenced debug menu (0x800a6c40, which toggles
`debug_flags`; nothing calls it). `asm/bugfix_temple_lost.asm`, e4c0da7.

Checked: emulator, RAM-write setup (Uranus in ashes with VIT 0, a made-up fallen party
of roster 4 and 5). Before, the current party itself scrambled: Venus dropped out and
Mars, who was never in it, took her place; the made-up party still listed 4 and 5. After,
Venus, Jupiter and Earth, and the made-up party listed 3 and 4. The first draft loaded
the index in the jal's delay slot, which the routine's first instruction reads too early
(load delay); the test caught it.

### 1.10 The town's BROKEN ITEM purge clears the wrong slot's state

From the fallen-party audit. `broken_items_purge` (JOUKA 0x800db4c4, run for every
character on entering town) empties each slot holding item 0, then zeroes
`item_state[9]` (`sb zero, 0x3d(a2)` at 0x800db51c) instead of the emptied slot's own.
A potion or scroll in the tenth slot loses its uses left. The camp's copy (MAZE
0x800e6260) clears the right byte. [code]

Fix: the loop is laid out again in place to clear `0x34 + slot`, as the camp's copy
does. Dropping a redundant sign extension of the loop counter makes room.
`asm/bugfix_broken_item_state.asm`, c717515. Checked: emulator, boot to town with a
RAM-write setup (item 0 in slot 6, a 9-use item in slot 9): before, the purge zeroed
+0x3d and the item was left with 0 uses; after (fix bytes over JOUKA, then again on the built
disc), it cleared +0x3a and the item kept 9.

## Group 2: looks cut, or the intent isn't clear

### 2.1 The identify service

Rosea (2:137-141), Cephala (3:145-150) and Cleo (4:78-83) each have a full "identify an
item?" exchange: the offer, a pick, success, failure and a cursed outcome. Every party
file has the log line "We asked them to identify items." (1:300, 2:268, 3:280, 4:164,
5:115). No handler has a state for it, and no code stores any of those string numbers.
MCARD also holds an unreferenced yes/no box (0x800b4100), which may be what's left of
it. [code]

Reopening it means writing a new service: a state in three handlers, the 50% roll beside
healing and sales, a member and item picker, an identify roll, and the curse outcome.
That's new game logic, with odds we'd have to choose.

Question for Chris: the text is all there, but the code was never written, or was
removed. Should NPC parties offer identification? If yes, the odds would be ours (the
Bishop's (level - item level + 1) × 20%, held to 5-75%, is one model). If not, the
lines stay in the files, unused.

### 2.2 Zaril's healing

5:35-42 are a whole healing table for Zaril (the offer, "nothing wrong", "can't", Dialko,
Latumofis, Dialma, out of spells). His handler (MCARD 0x800d9b34) has no heal offer at
all, and "We asked them for healing." (5:114) is unused too. [code]

Reopening it means adding the heal offer and result states to his handler, modeled on
the others'.

Question for Chris: Zaril is the party leader who can't do anything right, and the
lines read like his healing was meant to be grudging. Should his party heal? It would
make his party a little more useful, and his lines would be heard.

### 2.3 Guy and Fontana never re-introduce themselves

Balbo's, Cresson's and Zaril's handlers play a short re-introduction when only some of
your party have met them. Guy's and Fontana's replay the full introductions instead, so
their "didn't we do this already?" lines (1:134-139, 3:117-123) and a second Guy
line-up (1:128-133) never play. [code]

Reopening needs a new branch in each handler's Talk state, modeled on Balbo's.

Question for Chris: a missing branch, probably, since the lines are written for exactly
that case. Should Guy and Fontana get it?

### 2.4 Cresson calls every party "boys" (NPC_MES4 18-20)

`greet_cresson_line` (MCARD 0x800d8c98) chooses among 4:18 "Well, boys", 4:19 "Well,
girls" and 4:20 "Well, my good fellows" with three flags, `s0`, `s1` and `t6`, that are
set to zero at the top and never set again. The loop that should set them (it sets
the name, max HP and level flags) has no code for them. So it's always 4:18. [code,
disassembly]

Reopening means writing the scan. The natural reading is: no woman in the party →
"boys"; women only → "girls"; mixed → "my good fellows" (`t6` would need a guess).
The sex bit is +0x0b bit 7.

Question for Chris: fix it with that rule, or make 4:18's English neutral instead ("Well,
everyone, any progress?")? The second is a text change only.

### 2.5 Fontana's chat block 8 (NPC_MES3 197-200)

Fontana's stage-1 specials are picked from a list of seven (6, 7, 9, 10, 15, 16, 19 at
0x800d130c-0x800d1384). Block 8, Fontana and Cephala on Zaril's new party, isn't in
it, and nothing else picks it. [code]

Adding it would mean replacing one of the seven, or widening the roll.

Question for Chris: a slip, or cut? It's about Zaril leaving to lead his own party, so
it belongs once that's happened.

### 2.6 Balbo's "heard that already" (NPC_MES2 243-247, 253)

Blocks 27 and 28 have each member say they've heard that one before. Nothing picks them.
They'd answer the player telling news ("We told them everything we knew.", 2:249), and
there's no "tell" topic in the code. [code]

Question for Chris: looks like a cut topic. Leave unused?

### 2.7 Greeting blocks nothing picks: harmless duplicates

Traced 2026-10-11. **Harmless; nothing is lost.** Every one of these blocks plays the same
lines as a block that is picked.

- **Guy 38/39 and 41/42.** `greet_guy` (MCARD 0x800b9ed0) returns them from the branches
  for "met all four of Guy's party, stage 2" (`greet_flags & 0x4101 == 0x4100`, line 1056
  of the C) and the same at stage 3 (`& 0x8101 == 0x8100`), in the sub-case where the
  party has already had that stage's first greeting (`met_bits[1]` 0x40, or 0x10 at
  stage 3). But an earlier branch of the same if/else chain, `& 0x4181 == 0x4180` (and
  `& 0x8141 == 0x8140`), matches exactly that case first and returns 33/34 (35/36 at
  stage 3). So only the first-greeting sub-case of the later branch (block 37, or 40) is
  ever reached. [code]
  - Block 38 is Guy's 1:18 alone, and block 39 is 1:18 with a member's reply (1:20-22, or
    Fritillaria's 1:14); 33 and 34 are the same lines. Block 41 is 1:19 alone, and 42 is
    1:19 with a reply; 35 and 36 are the same lines. The only difference is which global
    carries the reply's string and face (`talk_str_b`/0x800796e4 against
    `talk_str_a`/0x800796ed). [dump]
- **Zaril 2/3.** `greet_zaril` (MCARD 0x800db730) returns 0, 1, 4 or 5, never 2 or 3
  (its last `else` can't be reached either: with `greet_flags` bit 3 set, bits 3 and 1
  are always 8 or 10). Blocks 2 and 3 are identical to 4 and 5: Zaril's 5:2, alone or
  with Gaura's or Fritillaria's reply. [code, dump]

No question for Chris: picking these would change nothing on screen.

### 2.8 The pit scene with no rescuer: a soft lock (now group 1)

When `npc_flags` bit 7 is set (Guy is the rescuer) but nobody in the party has met Guy,
`talk_scene_pit` (MCARD 0x800d5f8c) picks no rescuer block in state 0xf, so `talk_block`
keeps the block that just played. State 0x14 runs it again; it ends with `end`, not
`close`, so `talk_state` stays 0x14 for good. `talk_script_run` does nothing once the
status is -1, and nothing else ends the talk. [code]

**Confirmed in the emulator** (2026-10-11, `rips/re/work/P3-follow/pit_test2.py`). The
setup used RAM writes: from `npc_talkmode.state` (a real talk, window open), the current
build's MCARD.BIN and file tables were laid into RAM, the talk was switched to handler
21, `npc_flags` bit 7 was set and every member's "met Guy" bit (`met_bits[0]` bit 0) was
cleared or set. Circle was pressed every 30 frames for 3,000 frames.
- Nobody met Guy, our build: blocks 0 and 1 play, then block 1 plays again in state
  0x14, then the screen sits on Fontana's portrait and an empty text window with
  `talk_state` 0x14, status -1, for the rest of the run. The game can't be continued.
- Nobody met Guy, original MCARD: the same, except block 0 (the fall) plays twice.
- Control, a member met Guy: Guy's block 2 plays, `close` ends the talk, and the game is
  back in the maze within 90 frames.

When it can happen: bit 7 is set the first time the party enters areas 0x13-0x16 (MAZE
0x800a45b0, while progress tier 5 is new) and cleared by giving Guy the Ruby Slippers or
on first reaching areas 0x20-0x23. The pit is in Area C's trash rooms (C-B2). So a party
in which no member has been introduced to Guy (new recruits, or a party rebuilt after a
loss) that falls into the pit in that window is stuck. [code]

**Fixed in 5ff86d2** (`asm/bugfix_pit_rescuer.asm`). When the Guy loop picks nobody,
state 0xf now falls through to the bit-7-clear choice: block 3 (Balbo) if a member has met
Balbo, else block 4 (the man in armor). Guy has no stranger version, and his block 2
("Besides, I owed you one") assumes an introduction, so the game's own choice for a party
that isn't Guy's acquaintance is used and nothing new is written. The loop's exit jumps to
a few lines in the unused debug routine at 0x800c5800, after the pit-scene fix (1.5).

Tested in the emulator on the built MCARD (`rips/re/work/P3-pit/pit_rescuer_test.py`, the
same RAM-write setup as above):
- nobody met Guy or Balbo: the man in armor (block 4) plays, `close` ends the talk, and the
  game is back in the maze by frame 840;
- Balbo met, Guy not: Balbo's party (block 3), back in the maze by frame 840;
- Guy met (control): Guy's block 2, as before, back by frame 900.

Chris kept the fix (2026-10-11): Guy still rescues every party that knows him, and the fix
only fills the case the developers left empty. In practice that needs a party made
entirely of characters who never met Guy, such as fresh recruits sent to rescue a wiped
party, so a steady single party never meets it.

## Group 3: fixes that would change how the game plays

### 3.1 A wipe destroys only one character's items

`party_wiped`'s item loss (BATTLE 0x800c5be8) runs six passes but loads the member from
`actor_member` each time instead of the loop counter, so one character (whoever acted
last, or nobody if that slot is empty) is rolled six times: 82% per ordinary item and
99.9% per rare one, the Tablet of the Sun included. The rest lose only half their gold.
[code, disassembly; emu with a RAM-write setup (D)]

Who that is, in practice: the party's first position. `battle_main` zeroes
`actor_member` at the start of each round, and `battle_run_actions` steps it through every
combatant, back to 0 at each new group. Once the party is down, `FUN_800a8878` makes every
monster's action a no-op, so the round runs out and leaves `actor_member` at 0. [code] Both
emulator wipes agree: in D's, Uranus in position 0; in `rips/probe/bodies/wipe5`, roster 3,
whom the party record (0x8008f8c8, bytes 2-7 = `03 ff ff 00 01 02`) puts in position 0.
[emu] The exception is a chest trap that wipes the party: `chest_open` sets
`actor_member` to whoever handled the chest before calling `party_wiped`, so that
character is the one rolled. [code] If position 0 is empty (the record above shows that
positions can be), nobody loses items. Whether a player can leave position 0 empty is
not checked. [inf]

Question for Chris: fixing it gives every member one roll per item, as the loop was
written to do: each character would lose about a quarter of their ordinary items and
two-thirds of their rare ones in every wipe. As it stands, one character loses nearly
everything and the others keep all of theirs. Fix it, or keep what players have always
had?

### 3.2 Weapon effects ignore the level difference

`melee_apply_hits` computes a bonus (a quarter of the level difference, up to 30) or a
penalty (up to 20) and passes them to `apply_status_effects`, which never reads its third
and fourth arguments. [code, disassembly (D)]

Question for Chris: fixing it makes a weapon's poison, sleep, stone and death effects land
more often on weaker monsters and less often on stronger ones. Fix it, or keep the flat
odds?

### 3.3 Level drain reads +0x81 the other way round: confirmed backwards

Traced 2026-10-11. +0x7e..+0x82 are five Wizardry-style saving throws (`unk7e` and
`saves[0..3]` in `types.h`), rebuilt at every battle start by `battle_derive_saves`
(BATTLE 0x800a1b84): each is level / 5 + Luck / 6, held to 1-14, plus class bonuses of
1-3 (`save_bonus`, 0x800a2aac, capped at 33). +0x81 is the fourth, and the Thief's +3
goes there. [code]

Every other reader treats it as a save, higher is better:
- breath (`monster_breath`, BATTLE 0x800b39c4): save (+5 with a matching resistance, at
  most 18) passed to `saving_throw`; a pass halves the damage;
- the chest's gas trap (`chest_trap_effect` 0x800c7010): a pass escapes the poison.

`saving_throw` (0x800cbdbc) returns 0, a pass, when rand(20) < save. [code]

Level drain (`apply_status_effects`, BATTLE 0x800aa190, once per member per battle) lands
when `(rand(255) & 31) < +0x81` and `rand(100) >` the drain resistance (+0xba). So the
better a character's save, the more often they're drained, and the comparison is
backwards against every other use of the field. [code] What it means in play, before
drain resistance:

| +0x81 | Drained now (save / 32) | Drained if fixed ((32 - save) / 32) |
|---|---|---|
| 1 (a new character) | 3% | 97% |
| 3 (level 5, Luck 12) | 9% | 91% |
| 7 (level 20, Luck 18) | 22% | 78% |
| 10 (the same, a Thief) | 31% | 69% |

Question for Chris: almost certainly a reversed comparison, but the fix makes level drain
far more common, especially for low-level characters (about 1 in 11 becomes about 9 in
10). Keep the original, which players of the Japanese game have always had, or fix it?
The numbers suggest keeping it.

### 3.4 The town's stat recompute accumulates, but nothing reads the result

`town_stat_recompute` (JOUKA 0x800d0574) copies the record to `new_char`, resets only AC
and regen, then adds each equipped item's bonuses (`town_item_bonuses` 0x800d0754,
`town_item_bonus_one` 0x800d08f4, `town_unarmed_bonus` 0x800d0d24 for Ninja and Monk):
to-hit, the weapons' damage bonus, magic and effect resistances (held to 100), effect
chances, and OR'd masks. A mis-aligned item takes 1 off to-hit each pass. Nothing is
reset first, so every pass adds again. [code] MAZE's camp has a copy that does the same.

It runs very often: on the town screen with a party it ran about twice a frame, and 66
times on the walk from the town menu to the inn.

**Confirmed in the emulator, on the original disc too** (2026-10-11,
`rips/re/work/P3-follow/jp_tohit.py`, the same button presses as `mkstates.py`, no RAM
writes). The four premade characters' to-hit (+0x84) went 4, 5, 1, 2 → 2116, 2145, 329,
458 after forming the party → 3316, 3645, 629, 1058 after 600 frames idle in town. The
JP Rev 1 disc and our build gave the same numbers. Venus's damage bonus byte (+0x98)
wraps round past 255.

**But nothing outside battle reads those fields.** `fielduse.py` finds every reader of
to-hit, damage dice, resistances, effect chances and masks in BATTLE. And
`battle_derive_stats` (BATTLE 0x800a1830) rebuilds the whole block from scratch at the
start of every battle: dice reset to 2d2 plus a Strength bonus, resistances and masks
zeroed, the saving throws worked out again, then the gear added once. Watched in the
emulator (`fight_test.py` and a watchpoint, button presses only): walking from the
inflated state into a fight, to-hit went 3976, 4470, 794, 1388 → 14, 11, 4, 4, written
at 0x800a1b50 in that rebuild. The swing thresholds and damage rolls logged in that
fight used the rebuilt values (damage bonus 9, 4, 0, 0). [emu]

So the drift is real in the original but never reaches play. Not a bug worth fixing;
moved to "harmless". No question for Chris.

## Not bugs, or harmless

- **2.7, the greeting blocks nothing picks**: duplicates of blocks that are picked, with
  the same lines. See 2.7 above.
- **3.4, the town stat recompute**: it accumulates, but battle rebuilds every field it
  touches before reading them. See 3.4 above.
- **Every spell has a 1% failure floor** through magic resistance (+1 in the formula). Very
  likely intended. (D)
- **`party_store_pos`** (MAIN 0x8001bbc8) writes the area only for roster index 0, but the
  camp and the save rewrite every member's position right after. No effect found. (A)
- **The mode bytes come back swapped after a load** (0x800796aa and 0x8007966a,
  `mode_bytes_store`/`mode_bytes_load`). What they hold isn't known; harmless if equal or
  unused. (F)
- **`save_data_reset`** sets roster[0..5].area rather than the party's members, but only
  after a save that fails its checksum. (audit)
- **Class change** works out a new Alchemist's first spells from (Pie+Luc)/12, while level-up
  learning rolls against (IQ+Luc)/2. An inconsistency, not clearly a bug. (G)
- **The "rescue our companions" and "asked them for healing" log lines** for parties that
  offer rescue themselves (1:301, 2:269 ...) never run, since the NPC makes the offer. By
  design.
- **Strings no script reaches**, in `C-talk-lines.md`: 2:79-80 and 3:108 read like maze
  text (the switches, the rope) and may be printed by MAZE from the loaded file. The other
  untraced ones (1:45, 1:292, 2:5, 2:50, 2:52-53, 3:10-11, 3:50, 3:198, 4:8, 4:17, 4:44,
  4:144-146, 5:3-4, 5:20-25, 5:113) may come from computed stores the dumper doesn't
  follow, so they aren't proof of dead text.

## How the fixes are checked

Each fix is a separate `asm/bugfix_*.asm`, assembled after `vwf.asm` like the other
patches. The checks for each one are in its commit message: the decompiled code re-read
against the patched bytes (`scripts/re/ghidra.py` reads `rips/clean`; the patched
files are in `rips/dirty`), and an emulator run where a state can reach the code. The
emulator runs lay only the fix bytes over the overlay in RAM, and set up the case with
RAM writes, so none of them make natural before/after shots. The test scripts are in
`rips/re/work/P3-bugs/` (`t_alstron.py`, `t_chat.py`, `t_temple.py`, `t_broken.py`).
Every fix byte was checked in the built overlays after the build (c717515).
