# Bugs in the original game, and content no code reaches

Every bug and every unreachable string the phase-2 analysts found (`docs/re/*.md`), two
from the fallen-party audit (`docs/re/fallen-parties.md`), four from the harness runs
(1.11, 1.12, 1.15, 1.16), one from the rescue test (1.13), one from the lock test (1.14)
and two from a later read of the greeting code (1.17, 1.18, and 2.9). Each was re-read in the code from the
original disc (`rips/clean`, decompiled at 585c983) and confirmed or refuted. Addresses
are RAM; MCARD, JOUKA and MAZE load at 0x800a1000.

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
| 1. Clear bugs | 19, all fixed (2.8, the pit soft lock, moved here; fixed in 5ff86d2 and kept) |
| 2. Cut or unclear, ask | 7: 6 decided (2.2-2.5 reopened, 2.1 and 2.6 left unused), 2.9 open |
| 3. Balance, ask | 3, all decided (kept as the original; decisions.md 8-10) |
| Not bugs, or harmless | 9 (2.7 and 3.4 moved here after the follow-ups) |

Entries keep their numbers after a follow-up moves them to another group.

Bugs our own patch caused aren't listed here; they're written up where the patch's code
is described in `docs/engine-notes.md` and in `docs/writeup-notes.md`. So far: the
voicing-mark hang ("Text printer") and the freeze on the town logo after the ending
("The VWF block and libds's play list": Remisse's width table and centering wrappers sat
in libds DsPlay's play list, which the credits' CD audio call wrote over).

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

### 1.11 A pillar guardian's fight can be lost, locking the game

From the harness runs (T3/T4, 2026-10-12): four soft locks at the Grounds pillars, all
on "The pillar begins to shake ... attacks." The summon (MAZE 0x800afb34) opens that
event box, locks walking input (0x800796ab = 1) and starts the dust step (0x800cc9fc,
walk sub-state 3). When the dust has settled, the step requests the fight
(0x80079bf1 = 2, at 0x800cca4c). The box closes by itself once its text has typed out,
and `maze_frame` clears 0x80079bf1 on every box close (0x800a3234, in a delay slot).
Nothing ties the two together. If the dust settles first, the request is wiped, nothing
clears the input lock, and only a reset gets out. [code, emu]

Original code, but the Japanese disc never hits it: its line finishes typing 78-94
frames before the dust settles. Our English line is about three times as long and
finishes 84 frames later, which leaves -6 to +10 frames, and about 3% of pillar events
locked up (200 seeds of the BIOS `rand()` the dust uses, at the bird: 6 hangs on our
disc, none on the Japanese one; message speed makes no difference). Over the four
pillars that comes to about one play-through in nine.
`docs/engine-notes.md`, "Pillar guardians: the box and the dust race", has the trace.

Fix: the dust step counts an open box (0x80079838) as dust still alive, so the request
is only set once the box has closed. Two `nop`s at 0x800cca20 (`lbu a0, -0x67c8(s0)`)
and 0x800cca28 (`or v0, v0, a0`), no extra space. `asm/bugfix_pillar_race.asm`, c13dea2.

Checked (c13dea2; the chapter 1 runs and the suite in 824943d): emulator, on the built
disc. MAZE.BIN loads from the disc on entering the maze,
after the START menu and after a battle, and RAM then reads 92049838 and 00441025 at the
two addresses. The bird, 200 seeds from a fresh boot on the built disc: no hangs. The
snake, the same 200 seeds from matched states on the old and new discs: 11 hangs before,
none after. The 189 seeds that worked before start their fight on the same frame; the 11
that hung now start it 4 frames after the box closes, the earliest the others do. The
arrival-frame repro that hung every time (`t3/freeze/snake6_arrive.state`) starts its
fight 2 frames after the box closes. Eight chapter 1 bot runs from a cold boot on the
built disc reached the tablet door with all 32 pillar fights starting on the first try
(on the old disc the same seeds lost one, the snake in run v3), and the harness suite
passes 187 of 187. (The RNG seed is set with a RAM write as a stand-in for different
play histories.) Scripts: `rips/harness/t3/freeze/`.

### 1.12 A disc read can stall for about 20 seconds ("You've met someone!" and no meeting)

From the harness runs (T4 round 6, 2026-10-12): twice, a party stepped next to a roamer
at the tiger approach, "You've met someone!" came up, and nothing more happened. The
screen held, the music played on, no input was taken. The main loop was waiting in
`load_file_alt` (0x80012f5c) for the meeting's data file (M_DT005, table 1 index 49) and
the CD library kept reporting all 33 sectors still to come. The harness gave up after
about 350 frames and called it a lock; it isn't one. Left alone, the read times out
after about 1,200 frames (20 seconds), the game's load pump (0x800130a4, up to 3 tries,
retry count at 0x800798c9) issues it again, and play goes on: from
`rips/harness/t3/metlock/v1_r6b/f3066.state` with no input the fight starts at frame
1,263, against frame 63 with the fix (checked 2026-10-13). [code, emu]

The cause is in the CD library linked into the game (libds, byte-identical on the
Japanese disc). DsRead (0x80038300) has DsPacket (0x80036888) put Pause, Setmode, Setloc
and ReadN in the library's command queue, writing each slot's id first and its parameter
pointer last. The library sends queued commands from interrupts: its VSync callback asks
for the drive status, and the drive's answer starts the packet's next slot. If the VSync
lands in the 48 instructions between the Setmode slot's id and its parameter pointer,
and the answer arrives before the interrupt returns, Setmode goes out with a null
parameter. CD_cw refuses it ("no param", 0x80035118), the packet goes no further, and
the read waits until the library gives it up as failed; then the game retries it. Any
file load can hit it.
`docs/engine-notes.md`, "CD reads: the DsPacket race", has the trace.

Original code. Our patch doesn't touch the library or the files it was reading (same
LBAs and sizes), but our text code changes how long frames take, so it moves which reads
land in the window. The rate on the Japanese disc wasn't measured: the harness can't
finish battles there. Beetle answers commands faster than the hardware does (12,315-15,315
cycles against 19,000-201,000 in psx-spx), which makes the second condition likelier in
the emulator; no Beetle option changes that, and RetroArch's defaults behave like the
harness. In about 60 hours of harness play it locked twice, both at the same spot; four
timed chapter 1 runs made 10,337 reads with none in the window, and at the t4v1 meeting
1 of 100 timing shifts locks.

**Fixed** (`asm/bugfix_dspacket_race.asm`, 0ef275c). Why it's fixed rather than listed as a known
issue: it's rare, but a 20-second freeze with the music playing looks like a crash, and
a player may well reset and lose everything since the last save. Beetle in RetroArch
(what most players will use) hits it more often than hardware, and the fix only reorders
stores the library already makes. Chris weighed documenting it instead, given the fix
touches every disc read, and decided on 2026-10-13 to fix it once the checks below showed
no change in timing or reads (decisions.md 24). When he decided, the stall was believed permanent; that
was corrected the same day (the 20-second retry above), and the fix stands on the
grounds given here.

The fix: DsPacket writes each slot's id after the rest of the slot, so the dispatcher
can't take a half-written one. 14 words over both copies of
the fill loop (0x80036a10, 0x80036a58-0x80036a6c, 0x80036b08, 0x80036b50-0x80036b64),
same instruction count, no extra space: the old id store becomes a `nop`, and the
queue-count update uses `s0` (free by then) as its base instead of `at`.
The built SLPS_026.91 holds exactly the words tested below.

Why the id is the right thing to hold back: the dispatcher issues the slot under its
cursor (0x800986ec) whenever that slot's id is non-zero (0x800360dc, 0x80036efc; the
second also wants the count above 0, which an earlier slot of the same packet already
gives). Every way a slot is freed writes its id back to 0: the packet pop at 0x80035d10
clears each slot it releases (id at 0x80035d70) and stops at the first slot with another
id, and the queue resets clear all eight (0x80035fe0, init 0x80035e00, and the 0x80035ce0
loops at 0x80036450 and 0x8003658c). Packet ids come from 0x80060c48 and skip 0. So a
slot DsPacket gets from the allocator (0x80035e5c, the one after the live ones) reads
id 0 until the patched code stores its id, after everything the dispatcher reads from it.
The patch drops the `lui at` before the count store; nothing in the loop, the allocator,
memcpy or the code after the loop reads `at` (every other use is a `lui at` immediately
followed by its store), and `s0` is rewritten at the top of each pass (0x80036a2c,
0x80036b24) and not read after the loop before the epilogue restores it.

Checked: emulator, as RAM words over MAIN after loading the state. The t4v1 lock, replayed
frame for frame, reaches the same VSync point (301 instructions after DsRead's entry),
reads the file in the usual 59 frames and starts the meeting; all 100 input shifts read
normally (892 reads). Two chapter 1 bot runs with the words in place make the same 2,578
and 2,580 reads as without them and finish in the same frames (one frame later in the
second). The harness suite passes 187 of 187 on a test copy of the disc with the fix laid
into SLPS_026.91 (and over MAIN in RAM after each state load, since states keep the code
they were saved with), and again on the built disc (round 13). Scripts:
`rips/harness/t3/metlock/`.

### 1.13 A rescued party stays on offer, and pays the fee again

From the rescue test (`rescue-test.md`, 2026-10-13). Guy's, Balbo's and Fontana's
handlers (`talk_guy` 0x800b5694, `talk_balbo` 0x800c7264, `talk_fontana` 0x800cf8c0)
offer a rescue for any party in the table, other than the current one, whose members all
have status above 0x1f. The scan doesn't look at where the members are. On Yes each
member gets area 0xff and pays the fee, but the party's record stays in the table, so
the bodies, now at the Temple, are still a candidate. In the emulator Guy's party
offered the same party again in the same meeting (five Talks later) and at a later one,
and Fontana's in the same meeting, where a second Yes halved the gold again (62 → 31)
and took three more items. Balbo's scan is the same code. The record only went when the
town's full cleanup ran (JOUKA `town_main`, the gate at 0x800a2348), which happens after
a wipe, a load or "Go On with Another Party", not on a plain walk home; or the offers
stopped once a member was raised. [code, emu]

Fix: each Yes ends by freeing the picked party's record the way Look for Companions does
for a party it empties: id -1, count 0, members -1, member_state 0xff. The party is
`rescue_candidates[rescue_candidate_count]` (0x8008d300, 0x80079895), where the handlers
leave their `rand_upto` pick. No MCARD routine frees a party record (Look for Companions
and the town do it inline; BATTLE's `party_record_clear` 0x800cb900 clears only the current
party and isn't loaded during a talk), so the three hooks share one 24-instruction routine
with a short stub each. Hooks, at each Yes branch's exit after the member loop: Guy
0x800b7f44, Balbo 0x800cad6c, Fontana 0x800d24e4 (two words; the stub replays them).
Space: two unreferenced routines in MCARD at 0x800ab1cc-0x800ab27b, each just calling
0x800255b0 four times; no jal, j, branch or pointer from any module reaches them. Two
caves Ghidra listed as uncalled (0x800b216c, 0x800b37b0) turned out to be branch-targeted
tails of live functions and were left alone. Everything is in MCARD.BIN, which loads
whole for each talk, so a state saved on an older build can't run new code against an
old module (the voicing-mark hang in `docs/engine-notes.md`).
`asm/bugfix_rescue_repeat.asm`.

Checked: natural play on the built disc (`rips/re/work/P3-rescue2/fixbuild/`, md5
ca912fe814e0055527fdb67be3cb82a8, with the lock-pick fix), button presses only, from
states saved before each meeting; RAM held the fix's three jumps at every meeting where
it was read.
Guy: Yes took 357, 125 and 125 G and freed the record, then 60 more Talks in the same
meeting and 60 at a later one brought no offer. A second party then lost a real fight;
Guy's party offered it, the Yes took its gold (101 G) and freed its record (slot 1),
leaving the current party's, which had reused the first freed slot, alone. Balbo: Yes
took every item, kept the gold, freed the record; 60 more Talks, no offer. No and Look
for Companions behave as before. Fontana: Yes halved the gold (125 → 62) and emptied the
first, third and fifth slots, then compacted the packs, as before the fix, and freed the
record; 60 more Talks in the same meeting and 60 at each of three later ones brought no
offer, where the old code's repeat took 62 → 31. Details in `rescue-test.md`, "The fix,
tested".

### 1.14 Picking a lock uses the wrong character's skill

From the lock test (`lock-test.md`, 2026-10-13). Investigate on a locked door asks "Who
will pick the lock?". MAZE's routine turns the party position picked (0x800ae324) into a
roster number, stores it at 0x800798d1 (0x800ae39c) and checks that character's status
from it (0x800ae3b4-0x800ae3e0). The roll then works out the skill, ((level, + 5 for a
Thief or Ninja, + 2 for a Ranger or Bard) × 5 + Luck) / 10, against the door's
difficulty, but both of its reads (level and class at 0x800aea44, Luck at 0x800aeaac)
take the roster number from 0x80079791 instead: the member picker's blink counter
(FUN_800ac6bc), which steps 1, 2, 3, 4, 5, 4, 3, 2, 1 every 4 frames. So the skill was
that of roster entry 1 to 5, whichever the blink was on, in the party or not; an empty
entry gave skill 0, so 15% even on the easiest door. In 91 logged tries the chosen Thief
was never the record read; the records read ranged over roster 1-5 whoever was chosen,
and every outcome matched that record's skill. On the difficulty-1 doors nearly anyone
gets 70%, which hides it; on Area D's doors (difficulty 8) it decides whether a Thief's
skill counts. [code, emu]

Fix: both reads take 0x800798d1. One instruction each, and the base each needs
(0x80080000) is already in the register, set by the instruction before:
0x800aea44 `lbu v1, 1(s1)` → `lbu v1, -0x672f(a0)`, 0x800aeaac `lbu v1, -0x686f(v0)` →
`lbu v1, -0x672f(v0)`. MAZE.BIN only. `asm/bugfix_lockpick_member.asm`.

Checked: natural play on the built disc (`rips/re/work/locks/disc_fix/`, md5
ca912fe814e0055527fdb67be3cb82a8, with the rescue fix), door states made fresh on that
disc so MAZE's code was the new one (a state keeps the MAZE code it was saved with until
the next fight reloads it), and the fixed words logged at every try. 103 tries on the
Shrine 1F door (difficulty 1) and the B4 door (difficulty 13), alternating the Thief and
others: the record read was the chosen member's on all 103, roster 6-8 included, which
the blink could never reach, and each member's own skill was compared (B4: Thieves 10,
others 6-7). 1F opened 20 of 29 (20.3 expected at 70%), B4 14 of 74 (11.1 at 15%).
Details in `lock-test.md`, "After the fix".

### 1.15 A spell cast while the last spell's sound still plays can freeze the game

From the harness runs (chapter 8 training, q8v6, 2026-10-13): twice, on "Kai casts
Tiltowait.", the battle stopped for good. The screen held and no input was taken. The
battle was waiting on the spell animation's read (phase 0x30, 0x80079bc2 = 2), but the
VSync counter (0x80060788) had stopped, so DsReadSync's 1,200-frame timeout never came.
The CPU was in the BIOS A(40h) loop (SystemErrorUnresolvedException). The kernel's saved
context (TCB at 0xa000e29c) has EPC 0x80029c14 and Cause 0x24, a BREAK: the `break 7`
that follows `div 60,000,000 / tempo` in libsnd's tempo event (MAIN 0x80029c08), with a
tempo of 0, on sequence slot 2 (0x80093078), the spell sound. [emu]

The cause is in BATTLE. A spell's animation file (DATA03/MAGICnn.BIN, table 1, index
0x1bb + animation) carries the spell's sound sequence and its VAB header, and battle
loads it into 0x801a0400 with `load_file_alt` (0x800a421c). The previous spell's
sequence is still open on slot gp+0x2c0 and plays out of that same buffer. The game
stops and closes it only after the new file is in (the read is polled in phase 0x30,
0x800a42c0; when it's done, 0x800a42fc calls FUN_800ca890 -> MAIN 0x8001c494: SsSeqStop,
SsSeqClose, SsVabClose, then SsSeqOpen on the new one). If the old sound is still
playing when the new file comes in, the sequencer reads the new file's bytes as its
events. A long sound followed quickly by the next cast is enough. The two other loads
into that slot's buffers work the same way: the encounter music (FUN_800a53fc, index
0x1f6+, into 0x801a0400 at 0x800a54d8) and the item tunes and chest-trap sounds (index
0x20e+, into 0x801b4400 with the blocking `load_file` at 0x800a5534, up to 0x4000 bytes,
which reaches the longer spell sequences at 0x801b68e0-0x801b7cc0). [code, emu]

Original code: BATTLE differs from the Japanese disc in 32 words, all in the text
routines, and the three load sites, FUN_800ca890 and MAIN's sound wrappers are
byte-identical. DATA03 is the same on both discs. What it takes is pressing on fast.
From the first caught pair (h29, "Lu casts Bakadi." state), circle every 2 or 4 frames
or held froze it; one press 10 to 90 frames after each box settled, or a press every 30
or 60 frames, played on. Bakadi's sound runs 271 frames, Tiltowait's 276, Badi's 52-54.
A player holding circle or tapping it through the messages, or using fast-forward, can
reach it. Someone reading each message won't.

Rate: in the hunts (the harness's chapter 8 training trips from q8v6's states, the bot
tapping circle through the messages), 9 freezes in about 1,280 casts in the first set,
and 5 in about 1,720 in the second (`scripts/re/spellsound/hunt.py`, seeds 103-112).
Every caught freeze followed a Bakadi whose sound was still playing: 11 times Tiltowait
came next, and 3 times Ladalto (Kai's, in the second set). The party was always the same
(Lu and Earth cast Bakadi, Kai Tiltowait or Ladalto), so the rate says more about those
spells than about play in general. Other pairs read different bytes; none was seen to
freeze, but nothing stops them reading junk.

Fix: stop the open sequence (SsSeqStop, MAIN 0x8002b6c0) just before each of the three
loads, through a 7-word routine placed in BATTLE's FUN_800c3188, which is dead: no jal,
j, branch, pointer word or lui/addiu pair in BATTLE or MAIN reaches it (the other
overlays load at the same address and never share RAM with BATTLE), and it never ran in
the coverage runs. The routine skips the stop when no sequence is open (gp+0x2c0 = -1)
and otherwise jumps into SsSeqStop with the caller's return address. 0x8001c494 still
stops and closes the sequence after the load, as before. A second SsSeqStop is harmless,
on a stopped or a closed slot too: it clears the slot's play flags, keys off its voices
and rewinds its read pointer (MAIN 0x8002b540). It only stops, since closing here too
would close the sequence and its VAB twice. Site 1's stop comes a read's length earlier
than the original stop did, so the old spell's sound is cut when the next cast's file
starts loading rather than when it's in; that sound was about to be cut anyway.

36 words, no new space, nothing that's a branch target:
- the routine, 0x800c3188-0x800c31a0 (7 words, over FUN_800c3188's prologue);
- site 1, 0x800a4204-0x800a4218 and 0x800a4220 (7): `lb` does the 8-bit sign extension
  that `lbu` plus `sll`/`sra` 24 did, and the 16-bit one is a no-op for 0x1bb +
  [-128, 127]; a0 is set again after the call;
- site 2, 0x800a54c8-0x800a54e8 and 0x800a5510 (10): the second `lui v1, 0x800e` goes
  (v1 still holds it), and `li s1, 0xa0` moves into the load delay that lui filled;
- site 3, 0x800a5524-0x800a5548, 0x800a5578 and 0x800a557c (12): a1 takes v1 (both were
  0x801b4400) instead of its own lui/ori, and the second `lui v0, 0x800e` goes (v0 still
  holds it); the last word becomes a `nop` before the branch target at 0x800a5580.
Branch targets 0x800a4200, 0x800a4224-0x800a4234, 0x800a54c0, 0x800a5520, 0x800a5580 and
0x800a5588 are untouched, and the instructions in the delay slots keep their meaning.
BATTLE.BIN only. `asm/bugfix_spell_sound_reload.asm`.

Checked first as RAM words over BATTLE (`rips/harness/chapters/dev/ramfix/`): the nine
caught pairs of the first set froze without them and didn't with them, and sites 2 and
3, forced with a sound playing, gave 0x8001c494 the same arguments at the same frames.

Then on the built disc (md5 ba2a42a6353f4bd630bd6b1e9c341a85, against the published
ca912fe814e0055527fdb67be3cb82a8), with no RAM written. BATTLE.BIN differs from the
published one in exactly the 36 words. The hunts kept a state from before each fight's
BATTLE.BIN load, and the buttons from it to the fight, so the fight loads BATTLE fresh
from whichever disc is in; every replay read the 36 words back from RAM, the new ones
on the new disc and the old on the published one. Five freezes from the second set's
hunts were replayed on both discs with the harness's command policy and circle every
5, 6, 7, 8 or 10 frames, shifted 0-7 frames after each round's commands (all 40 timings for
three of them, 16 for the other two: every 5, 6, 8 or 10 frames, shifted 0-3; 152 runs
on each disc). On the published disc 130 of
152 froze, all with EPC 0x80029c14 and the CPU in the kernel's loop
(0x800000a0-0x800005dc) with the VSync counter still for 3,300 frames; one was run
20,000 frames further, presses included, with no change. On the new disc none froze: in
each of the 130 the same inputs gave the same spell loads and casts up to the freeze, the
stop routine ran at every load, and the battle played to its end. The same five hunts,
rerun on the new disc with their seeds, went past the frames where the published disc
froze and on for 1,189 casts without a freeze. Tools in `scripts/re/spellsound/`.

### 1.16 The party's Bacortu in a fixed battle seals group 1 or 2, not the row aimed at

From the harness runs (chapter 17 report 5, 2026-10-17): the Bishop's Bacortu, aimed at a
back-row Ogre Sorcerer in a type-2 party fight, raised the sealing level of group 2, an
Ogre in the front row, and the two Ogre Sorcerers kept casting. [run]

Bacortu is a one-group spell (`spell_flags_table` 0x800d5874, spell 14 = 0x8441: bit
0x40), like Montino, Morlis and Madalto. In a fixed battle (0x80079bde = 1: story fights
and the type-2 roaming parties) the group pick for those spells picks a row, not a group:
`FUN_800cf0dc` calls the grid picker 0x800cf258 in row mode (party_commands state 0x34 for
spells, 0x54 for items, with flag 0x40), which returns 1 for the front row and 2 for the
back, and party_commands stores that as the member's target (combatant +0xb). `cast_spell`
(0x800abcc0) loads it into `target_group` (0x800796ac). The other group spells' handlers
then call `spell_group_range` (0x800c999c), which turns the row into its first group (in
`target_group`) and returns its last, and loop over the row (`spell_madalto` 0x800c9e7c,
`spell_montino` 0x800adbc4, `spell_morlis` 0x800acb94). `spell_bacortu` (0x800c9e2c) has
no such step: it adds the caster's level (0x80079b4e) to `battle_groups[target_group]`'s
sealing level (0x8008c486 + group × 8, up to 255). So the row number was used as a group
number, and the cast sealed group 1 or group 2 whatever was aimed at. The message is the
same either way, so a player couldn't tell. [code]

Original code: all of the above was read from the Rev 1 disc's BATTLE.BIN (`rips/clean`),
and no patch before this one touched the picker, `cast_spell` or the handlers. Chris decided on 2026-10-17 to fix it as Montino and Morlis work: in a
fixed battle Bacortu seals every group in the chosen row (decisions.md 30).

Fix: spell 14's entry in `spell_handlers` (0x800d838c + 14 × 4, was 0x800c9e2c) points at
a new 46-word routine at 0x800c31a4, in the dead FUN_800c3188 after the spell-sound fix's
`spell_sound_stop` (1.15; the rest of that routine is still unreached: no jal, j or
pointer word into it in BATTLE or MAIN). In a fixed battle, when the party (group 0) or its
summons (group 7) cast it at a monster row, it calls `spell_group_range` and then the
original `spell_bacortu` once for each group in the row, stepping `target_group` as
`spell_madalto` does. Each group gets the caster's full level, and there's still no
resistance check. Anything else calls the original `spell_bacortu` once, as before: every
ordinary battle, a monster's cast at the party (target 0) or the summons (7), and a cast
Banoka turned back on its caster's own group. The caster test is the one check Madalto's
handler doesn't have: a monster's bounced spell targets its own group (`cast_spell` sets
`target_group` = `actor_group`), a real group number and not a row. `spell_bacortu` itself
is unchanged. 47 words, BATTLE.BIN only. `asm/bugfix_bacortu_rows.asm`.

Checked on the built disc (md5 bc88211da46e184d081a84fea0a29315, against the suite's
8f785cdedcc9a62637738ba1f483bd73), with no RAM written. Fresh fight-start states were made
on the new disc (`scripts/re/bacortu/mkfights.py`: chapter 17's goal run from c17v2b's
goal_02_area_e, seed 2, saving each fight's start; each fight loads BATTLE.BIN from the
disc in, and BATTLE's code in RAM matched the new build word for word, the new table entry
and routine included). Eve (Bishop, level 17) casts Bacortu on round 1 and everyone else
parries (`scripts/re/bacortu/verify.py`); sealing levels are read at the next command
phase, after a round's decay of 1-3:
- Type-2 party (front row Man in Armor 382, Ogre 437, Ogre Daimyo 467; back row two Ogre
  Sorcerers 452). Aimed at the back row: groups 4 and 5 sealed (16 and 15), the front row
  untouched, and "Ogre Sorcerer casts Cortu." was followed by "But spells are sealed." the
  same round. Aimed at the front row: groups 1, 2 and 3 sealed, the back row untouched.
  Seeds 1 and 3-8 aimed at the back row: in the six where Eve lived to cast (seed 1 had
  her killed first), groups 4 and 5 were sealed every time (14-16).
- The same fight on the suite's disc, from ch17's t2s2_01 (old code in RAM), aimed at the
  back row: group 2 (the Ogre) sealed, as in the report.
- Ordinary battles (0x80079bde = 0): four groups (Wooden Puppets, Blaze, Venom, Strange
  Figures), aimed at group 2 and then group 4; three groups (two of Vampires, then one),
  aimed at group 3 and then group 1. Each time only the group aimed at was sealed. In the
  four-group fight the Strange Figures advanced at the round's end and the groups were
  renumbered, and the seal moved with its monster (Blaze, sealed as group 2, was group 3
  after).

### 1.17 Reiran's young-Ninja greeting never shows, and its name copy is on one path only (NPC_MES2 64, NPC_MES3 66)

Found reading the greeting code (2026-10-19). Reiran's greeting picker, one copy for
Balbo's party (0x800cda60, called from `greet_balbo` when `talk_speaker` is 3) and one for
Fontana's (0x800d3664, from `greet_fontana` when it's 2), sets four party flags: all
young boys, all young girls, all aged 40-59, and a Ninja aged 10-19 (`s1`). The Ninja
flag picks 2:64 / 3:66, "Is that a Thieves Dagger? {ff12}, a Ninja at your age? How
marvelous.", with expression 3, and should copy that member's name into 0x80089ac0 for
{ff12}. [code, disassembly]

Two bugs, the first hiding the second:
- **The class test masks the wrong bits.** The flag test (0x800cdb14 / 0x800d3718) and the
  name copy's test (0x800cde74 / 0x800d3a78) read `class_sex` (+0x0b) with `andi 0x80`,
  the female bit, and compare with 0xc, the Ninja class. 0 or 0x80 never equals 0xc, so
  the line never showed. The class is bits 0-6 (`training_create`, Guy's party's Thief
  loop use `& 0x7f`). Characters start at age 15-20, so a Ninja aged 15-19 qualifies. [code]
- **The name copy is on one path only.** The picker branches on `story_flags` bit 28
  (0x10000000), which only the card game's code sets (CMAIN 0x800ab574, CMENU
  0x800b7ee8). With it set, Reiran's default line is 2:60, about the Card Master's
  complete set, so the flag is probably that [inf]. Bit 28 set: a
  party with any of the four traits gets a 50% roll between 2:60 and the trait's line, and
  the young-Ninja branch copies the name (0x800cddf0-0x800cded0). Bit 28 clear, the usual
  case: the trait's line every time, and the young-Ninja branch (0x800cdf6c-0x800cdf80)
  sets the line and expression with no name copy. {ff12} then shows whatever the buffer
  last held: the status panel (0x800ad89c) draws each member's name through it, so the
  last member, or at Fontana's the first member, which the helper for the greeting's
  other line (0x800d3bd8) sometimes copies. [code, emu] So
  bit 28 decides the odds, not whether the line shows.

Fix, Chris's decision 2026-10-19 (the second part after the test found it): `andi 0x7f`
at the four tests, and the bit-28-clear branch jumps into the other branch's code, which
sets the same line and expression and copies the name (0x800cdf74 `j 0x800cddf0`,
0x800cdf78 `move a0, zero`; Fontana's 0x800d3b78 `j 0x800d39f4`, 0x800d3b7c `move a0,
zero`). 8 words, MCARD.BIN only. `asm/bugfix_reiran_ninja_greeting.asm`.

**Tested in the emulator** (`rips/re/work/P3-bugs/reiran/reiran_test.py`). RAM-write setup
as in 2.4: from `npc_talkmode.state`, the built MCARD and file tables laid in, the talk
switched to Balbo's party (handler 1: stage 1, every member has seen Balbo and been
introduced, slot alignments Evil and Neutral to match Evil Balbo) or Fontana's (handler 2:
stage 3, introduced), 0x80089ac0 primed with a marker, and the RNG state varied over 40
trials. A breakpoint on the picker counts Reiran's turns. Party: Uranus (male Fighter,
25), Venus (female Ninja, 17), Jupiter (female, 45), Earth (male Priest, 31). [emu]
- Original words (from `rips/clean`): never 2:64 / 3:66. Balbo 8 of 8 Reiran turns gave
  2:58 / 2:59 (bit 28 clear) or 2:60 (set); Fontana 14 of 14 gave 3:60 / 3:61 or 3:62.
- The class fix alone (the first build): 2:64 / 3:66 on every turn with bit 28 clear, but
  naming Earth (Balbo) and Uranus or Earth (Fontana), never Venus. With bit 28 set it
  named Venus.
- Both fixes, bit 28 clear: Balbo 8 of 8 turns 2:64 naming Venus, Fontana 14 of 14 3:66
  naming Venus. Bit 28 set: Balbo 5 of 8 2:64 (3 were 2:60), Fontana 10 of 14 3:66 (4
  were 3:62), each naming Venus.
- No Ninja in the party: Reiran's usual lines, the same as the original (2:58 / 2:59, 2:60;
  3:60 / 3:61, 3:62).
Contact sheets: `round2/sheet.png` (both fixes), `round1/sheet.png` (the class fix alone,
with the wrong names). Not public shots.

### 1.18 Rosea's greeting: the name check was never written (NPC_MES2 52-53, 56-57)

Found reading the greeting code (2026-10-19, engine-notes "Class tests that mask the wrong
bits"). Rosea's picker (Balbo's party, MCARD 0x800cd600, `greet_balbo` speaker 2) sets
three flags: a3, someone knows Loktofeit (+0x5a bit 1) or carries the Ruby Slippers (item
0x11e); t2, a man aged 16-25; t1, a lost character in the list at 0x80096720. It was
built like Guy's party's picker (0x800be88c), which also checks names against a list of
rude words, but Rosea's name check is missing: where it would be tested (0x800cd9ec) a0
is compared with s0, both always 1. [code, disassembly]
- Without a3: a lost character gives 2:55 (with the name); everyone else gets 2:56, "Oh
  dear, must I really talk with you? Whoever gave you that name? ... {ff12}... There. I
  said it.", with no name copied, so {ff12} was the last party member (the status panel
  draws names through the buffer). 2:57 for a young man and 2:52 / 2:53 (a coin flip)
  never played. [code, emu]
- With a3, t1 and t2: a 1-in-4 pick of 54-57, its 56 also with no name. a3 otherwise:
  2:54. [code]

Fix, Chris's decision 2026-10-19 (the design in outline; the 54 fallback was proposed in
the fix): the check is written, against Guy's list (0x800a1eb0, twelve 10-byte entries,
lengths at 0x800a1f28), so one list serves both; it compares whole names, terminator
included, as unsigned bytes. Without a3: lost → 2:55; a rude name → 2:56 with that
member's name; a man aged 16-25 → 2:57; else 2:52 or 2:53. In the a3/t1/t2 pick, case
2 gives 2:56 with the name when there's a rude name and 2:54 when there isn't: 54 is the
line every other a3 party gets, and 55 and 57 keep their 1-in-4. The random pick's
lost-name case had its own copy of the no-a3 path's 52-word "copy the lost name, 2:55"
code; it jumps there now and the new code (49 words) sits in the 50 freed
(0x800cd7f4-0x800cd8bb). `asm/bugfix_rosea_greeting.asm`. The list itself is now
English (`asm/naughty_names.asm`, translation-notes).

**Tested in the emulator** (`rips/re/work/P3-bugs/rosea/rosea_test.py`, output in
`runs/`): RAM-write setup as in 1.17, Balbo's party at stage 1, introduced, 40 RNG trials
per case, Rosea's turns counted by a breakpoint (7 per 40). Party Uranus, a renamed
member 1, Jupiter, Earth; nobody a man aged 16-25 unless the case says so. [emu]
- Original code, a plain party, a young man, or "Dick": 2:56 on 7 of 7 turns, naming Earth.
- Fix: "Dick" and "RETARD" 2:56 on 7 of 7, naming them; "Dickens", "dick" and ちんこ (the
  old list's first word, as kana bytes) 2:52 / 2:53, both seen (3 and 4); a man aged 20
  2:57 on 7 of 7; a lost character (Mars) 2:55 naming Mars; Loktofeit 2:54.
- a3, t1 and t2 with "Dick": 54 ×1, 55 ×2, 56 (naming Dick) ×2, 57 ×2. The same turns
  without a rude name: 54 ×3, 55 ×2, 57 ×2, never 56.
Contact sheet: `rosea/sheet.png`. Not public shots.

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

**Decided (Chris, 2026-10-11): left unused, and said so in the release notes**
(decisions.md item 1).

### 2.2 Zaril's healing

5:35-42 are a whole healing table for Zaril (the offer, "nothing wrong", "can't", Dialko,
Latumofis, Dialma, out of spells). His handler (MCARD 0x800d9b34) has no heal offer at
all, and "We asked them for healing." (5:114) is unused too. [code]

Reopening it means adding the heal offer and result states to his handler, modeled on
the others'.

Question for Chris: Zaril is the party leader who can't do anything right, and the
lines read like his healing was meant to be grudging. Should his party heal? It would
make his party a little more useful, and his lines would be heard.

**Reopened in 9135ef5** (`asm/bugfix_zaril_heal.asm`), Chris's decision 2026-10-11
(decisions.md item 2). Copied from Guy's and Balbo's healing, nothing added:
- **The offer.** On Talk, once everyone is introduced, Zaril's sale roll runs first,
  untouched. Where it doesn't fire (the four paths that went on to a chat topic), if a
  member has a status or HP at or under max/5: a 50% service roll, then a 50% heal roll,
  25% per check as for the other parties. [code] So the sale keeps exactly its original
  odds, hurt party or not, and healing comes up 25% of the Talk presses when no sale can
  be offered (no empty pack slot, not compatible, or `progress_bits` under 0xe) and 12.5%
  when one can (50% no sale × 25%). The first version (9135ef5) checked the heal before
  the sale, which cut the sale to 37.5% whenever someone was hurt; Chris asked for the
  sale not to be buried, and 98b0c5e moved the hook to the chat-state store
  (0x800daae0). [code]
- **The picker and the result** (states 0x2d, 0x32, 0x37), with one healer and the
  stage-3 table Guy and Balbo share, which is the one his lines fit: nothing wrong (5:36)
  or stone/dead/ashes (5:37, "can't") picks again; then 20% out of spells (5:40);
  paralysis Dialko (5:38, cure 1); poison Latumofis (5:39, cure 3); HP below max Dialma
  (5:41, cure 4); cancel 5:42. Any outcome but "nothing wrong" uses up Talk for the
  meeting, as in the others. The offer block opens with the log line 5:114. [code]
- **Mapping.** 5:35-42 run in the same order as Guy's 1:142-151 and Balbo's 2:114-123
  (offer, healthy, can't, Dialko, Latumofis, out of magic, HP spells, cancel), with the
  one HP spell, Dialma. Expressions: 0 plain, 2 annoyed for "quit wasting my time", 3
  sorry for "can't" and "out of spells", as his other lines use them. [code]
- **Space.** Hooks at the state dispatch (0x800da4b8) and the chat-state store after the
  sale roll (0x800daae0). The code and scripts sit in three routines nothing
  calls: 0x800b4100 (a yes/no box), 0x800ab09c-0x800ab1cb (two card-status checks) and
  0x800c5820-0x800c58db (the rest of the debug routine after the pit fixes, through
  FUN_800c589c). Each was checked for jal, j, word and lui/addiu references in every
  module. [code]

**Tested in the emulator** on the built MCARD (`rips/re/work/P3-zaril/zaril_heal_test.py`).
The setup used RAM writes, as the pit tests did: from `npc_talkmode.state` (a real talk),
the current MCARD and file tables were laid into RAM, the talk switched to handler 4,
every member marked introduced to Zaril, and the members given a status. Everything after
was button presses: Talk until the offer came (chats in between played through), the
picker, Leave. [emu]
- Paralyzed member: Dialko, status 0x20 → 0.
- Poisoned: Latumofis, status 4 → 0 and the poison counter 5 → 0.
- HP 1/30: Dialma, HP 12/30.
- Dead: "can't cure this one", the picker again, cancel: "That so? ...", status unchanged.
- Healthy: "quit wasting my time", the picker again, cancel.
- Cancel at the picker: 5:42, nothing changed.
- One run rolled the 20%: "I've used up all my healing spells", nothing changed.
- Every run: Talk drops from the menu (talk_menu 7 → 6), Leave plays the farewell, and
  the game is back in the maze. The log line shows in the bottom bar from the offer on.
Shots: `rips/re/work/P3-zaril/<case>/` (`*_text.png` are the outcome lines).

**The sale after the reorder** (98b0c5e), sampled (`rips/re/work/P3-zaril/sale_sample.py`,
same RAM-write setup, plus the sale's conditions made true: every member's met_bits[1]
bit 0, which `greet_zaril` turns into the "compatible" bit, `progress_bits` at least 0xe,
one empty pack slot). Each trial pressed Talk once, on a different frame. [emu]
- One member paralyzed, 80 trials: sale 44, heal offer 8, chat 28.
- Nobody hurt, 40 trials: sale 26, chat 14.
The sale comes up at the same rate either way (the trials on consecutive frames make the
sample lumpy; 50% is what the code says), and heal offers appear only on presses where
the sale didn't. The paralysis, Dialma and dead cases were rerun on this build with the
same results as above (`r2_*`).

### 2.3 Guy and Fontana never re-introduce themselves

Balbo's, Cresson's and Zaril's handlers play a short re-introduction when only some of
your party have met them. Guy's and Fontana's replay the full introductions instead, so
their "didn't we do this already?" lines (1:134-139, 3:117-123) and a second Guy
line-up (1:128-133) never play. [code]

Reopening needs a new branch in each handler's Talk state, modeled on Balbo's.

Question for Chris: a missing branch, probably, since the lines are written for exactly
that case. Should Guy and Fontana get it?

**Correction (2026-10-11).** Only Guy replays the full introductions. Fontana's handler
plays them only when *nobody* has met him (`cVar4 == party count`, MCARD 0x800d0e28); with
some met, Talk goes straight to services and chat, so newcomers are never introduced to
his party at all. [code]

**Reopened in 7498b1c** (`asm/bugfix_reintroductions.asm`), Chris's decision 2026-10-11
(decisions.md item 3). Modeled on Balbo's Talk state: count the members who haven't met
the leader; all of them: the introductions, unchanged; some: the re-introduction; none:
services and chat, unchanged. [code]
- **Guy** (hook 0x800b62f8, after the stage's introduction block is chosen): with some
  met, `talk_block` 3, one block for every stage: Guy 134 (Guy at 109), Alstron 135 (178,
  stays up), Linaria 136 (8), Lychee 137-139 (8), under the bar line 1:302 "We asked them
  who they were." His "again" lines name only the founding four; Fritillaria and Lilia,
  who join at stages 2 and 3, have no "again" line, and the game already gives each of
  them a self-introduction in Guy's greetings (1:140, 1:141, greeting blocks 37 and 40)
  for a party in which nobody has met them. [code]
- **Fontana** (hook 0x800d0e80, where the not-all-unmet path began): with some met,
  `talk_block` 3, 4 or 5 by stage, mirroring his introductions 0-2: stage 1 Fontana 117,
  Zaril 118, Artemisia 119, Lilia 120-121, Cephala 122; stage 2 the same without Zaril
  (he has left); stage 3 Fontana 117, Cephala 122, Reiran 123. Same places as the
  introductions, bar line 3:282. [code]
- **State 0x23** in both handlers now runs these static scripts for the new block numbers
  and the stack-built introductions otherwise (hooks 0x800b6f48, 0x800d1574). Opcode 0
  sets the shown characters' met bits for every member during state 0x23, so newcomers
  are marked just as by the introductions (Guy's re-introduction doesn't show Fritillaria
  or Lilia, as said above). [code]
- **The second Guy line-up (1:128-133) stays unplaced.** Guy: "Seems some of you are
  meeting us for the first time (初めてのお方もいるようだし), so let's do quick
  introductions", then Linaria, Alstron ("Al-chan"), Lychee, Fritillaria and Lilia, all in
  one set, though no stage of his party has both of the last two. It reads like a
  re-introduction too, which leaves two sets for one case. Possible homes: the stage-2/3
  re-introduction (it has the two later members), or an alignment variant, as Balbo has
  two introduction sets picked by his alignment (`oneshot_flags` bits 12/13, 2:96 and
  2:102). Nothing in the code or the data picks between them: no handler stores 128-133,
  and no leftover script in MCARD uses them. [code] Chris left it unused (2026-10-11),
to be listed in the release notes with the other unused lines.
- **Expressions** are the introduction's for each character, except where the line's mood
  differs: then the one the character uses for that mood elsewhere (Guy 3, as for "what the
  heck happened to this maze?"; Linaria 3; Lychee 1 and 5 for "Ehehe"; Fontana 3; Lilia 3
  then 1; Cephala 1), and for Artemisia and Reiran the ones Balbo's re-introduction gives
  the same lines (2:113, 2:111). [code; choice]
- **Space**: blocks 19-24 of Cresson's chat array (0x800a7e14-0x800a82c3). The array is
  25 blocks of 200 bytes copied to his stack each frame; his chat picks blocks 0-18 only
  (`rand_upto(8)` + 10 at most), so these zero blocks never run. [code]

**Tested in the emulator** (`rips/re/work/P3-zaril/reintro_test.py`, output in
`rips/re/work/P3-zaril/ri/`). The setup used RAM writes, as the other talk tests did: from
`npc_talkmode.state`, the current MCARD and file tables laid in, the talk switched to the
handler, the leader's stage set in `npc_stage` and each member's "met the leader" bit set
or cleared. Then button presses only. [emu]
- Guy, stage 1: one member met → block 3 (the re-introduction, every page as above);
  nobody met → block 0, the full introductions; everyone met → chat. Stage 3, one met →
  block 3.
- Fontana: one member met, stages 1, 2, 3 → blocks 3, 4, 5, each with the right members;
  nobody met → block 0; everyone met → chat.
- Every case ends with all four members marked as having met the leader, and the next Talk
  goes to chat or a sale.
Contact sheets: `ri/guy_mixed_1_sheet.png`, `ri/fontana_mixed_1_sheet.png`,
`ri/fontana_mixed_3_sheet.png`.

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

**Reopened in 7166f5d** (`asm/bugfix_cresson_greeting.asm`), Chris's decision 2026-10-11
(decisions.md item 4).
- **What the flags select**, from the disassembly (0x800d8f48-0x800d9010), after the
  special cases (DIMGUIL, max HP over 9,999, everyone level 100+): `s0` clear → 4:18
  "boys"; else `s1` clear → 4:19 "girls"; else `t6` clear → 4:20 "my good fellows"; else
  4:21 if the Decipher table has no blank entry, or string 0x98 with expression 0 if it
  has. The DIMGUIL branch's random pick reaches the same three for its fourth case (and
  with `s0` and `s1` both set it leaves the line as it was). [code, disassembly]
- **The rule**: `s0` = a woman in the party, `s1` = a man. No women: "boys"; only women:
  "girls"; mixed: "my good fellows". [code]
- **Female is bit 7 set** in `class_sex` (+0x0b): character creation sets it for a
  female, and a Valkyrie needs it (F-edge-save.md, G-records.md). [code]
- **`t6`** stays unset, as it always was, so the 4:21/0x98 branch after "my good fellows"
  stays unreachable. What it was for can't be recovered: it sits where a third kind of
  member would be tested, but the records have only two sexes. A guess: some other
  party trait the developers meant to single out. [inf]
- **The change**: the member loop's level load (0x800d8dbc) jumps to eight instructions
  that set `s0` or `s1` from the member's sex bit, then do the load. They sit at
  0x800a8280, in the never-run end of Cresson's chat array (bugs.md 2.3). [code]

**Tested in the emulator** (`rips/re/work/P3-zaril/cresson_test.py`, output in `cr/`).
The setup used RAM writes, as the other talk tests did: from `npc_talkmode.state`, the
current MCARD and file tables laid in, the talk switched to the scholars (handler 3),
every member seen before and introduced to Cleo, Bergamot and Cresson, Cresson's stage 1,
the state's pending message box cleared, each member's sex bit set by the case, and the
RNG state varied until Cresson spoke the greeting. Four level-5 members. [emu]
- All male: `talk_str_a` 18, "Well, boys, any progress?"
- All female: 19, "Well, girls, any progress?"
- Two and two: 20, "Well, my good fellows, any progress?"
Contact sheet: `cr/sheet.png`.

### 2.5 Fontana's chat block 8 (NPC_MES3 197-200)

Fontana's stage-1 specials are picked from a list of seven (6, 7, 9, 10, 15, 16, 19 at
0x800d130c-0x800d1384). Block 8, Fontana and Cephala on Zaril's new party, isn't in
it, and nothing else picks it. [code]

Adding it would mean replacing one of the seven, or widening the roll.

Question for Chris: a slip, or cut? It's about Zaril leaving to lead his own party, so
it belongs once that's happened.

**Reopened in 7c99607** (`asm/bugfix_fontana_chat8.asm`), Chris's decision 2026-10-11
(decisions.md item 5): only after the split, at Fontana's stage 3.
- **Block 8**: bar 3:276 "We asked about other parties.", Fontana 3:197 "Zaril, who used
  to be with us, has formed a party of his own...", Cephala 3:199-200. Both are in
  Fontana's stage-3 party. 3:198 (Artemisia, "I ran into Zaril the other day") isn't in
  the block and stays unused; Artemisia isn't with him at stage 3. [code]
- **Stage 3** is what the split scene (handler 20) leaves: `npc_stage` & ~0x1d0 | 0x220, so
  0x200 set and 0x80/0x100 clear. The patch tests it as the topic code does:
  (`npc_stage` & 0x180) == 0 and & 0x200. [code]
- **How it's picked.** Fontana's chat (state 0x28): at areas 0x20-0x23 an area special
  (block 24); at stage 1 one of seven "other parties" specials; a special is kept 90% of
  the time. Otherwise `rand_upto(7)` picks one of eight topics, each played as its
  stage-1/2 or stage-3 block. At stage 3 the patch makes that roll `rand_upto(8)`, 8
  meaning block 8. [code]
- **What it costs the others**: at stage 3, each of the eight topics drops from 1/8 to 1/9
  of the topic rolls (12.5% to 11.1%), the same share for each, and block 8 gets 1/9. The
  area special keeps its 90%. Stages 1 and 2 don't change at all. Of the other ways in,
  a stage-3 special would play 90% of the time, and replacing a topic would take one away,
  so a ninth topic is the lightest touch. [code]
- **Hook**: the topic roll (0x800d13b4); the code sits in Cresson's never-run chat blocks
  (bugs.md 2.3), at 0x800a8200. [code]

**Tested in the emulator** (`rips/re/work/P3-zaril/chat8_sample.py`, output in `c8/`). The
setup used RAM writes, as the other talk tests did: from `npc_talkmode.state`, the
current MCARD and file tables laid in, the talk switched to Fontana's party, every member
introduced to him, nobody hurt, his stage set in `npc_stage`, the state's pending message
box cleared, and the RNG state varied per trial. One Talk press per trial. [emu]
- Stage 3, 90 trials: block 8 nine times; the eight stage-3 topics 7-12 times each.
- Stage 1, 40 trials: only the seven specials (6, 7, 9, 10, 15, 16, 19); no block 8.
- Stage 2, 40 trials: only the stage-1/2 topic blocks; no block 8.
Contact sheet of block 8 playing: `c8/sheet.png`.

### 2.6 Balbo's "heard that already" (NPC_MES2 243-247, 253)

Blocks 27 and 28 have each member say they've heard that one before. Nothing picks them.
They'd answer the player telling news ("We told them everything we knew.", 2:249), and
there's no "tell" topic in the code. [code]

Question for Chris: looks like a cut topic. Leave unused?

**Decided (Chris, 2026-10-11): left unused, and said so in the release notes**
(decisions.md item 6).

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

### 2.9 Guy's, Lilia's and Alba's name checks can't match (NPC_MES1 68, 72, 75; NPC_MES2 50; NPC_MES3 48)

Found 2026-10-19 while localizing the joke names and the naughty-name list. Several
greetings test for a name: Lychee's 1:72 (a rude name in the party, the list at
0x800a1eb0) and 1:68 ('Mule', アイテムもち, 8 bytes at 0x800a1ea8) in Guy's party's picker
0x800be88c; Lilia's 'Richguy' (かねもち, 6 bytes; 1:75 in 0x800bf3b8, list at 0x800a1f34;
3:48 in 0x800d47ec, at 0x800a694c); Alba's 'Appraiser' (かんてい, 6 bytes at 0x800a4f50, in
0x800cd104). None of them can ever match, in the original either: [code, disassembly]
- **Signed compare.** Each loop loads the name with `lbu` and the list (copied to the
  stack) with `lb`: Lychee 0x800becf8 / 0x800becfc and 0x800bebc4 / 0x800bebc8, Lilia
  0x800bf5d4 / 0x800bf5d8 and 0x800d4a0c / 0x800d4a10, Alba 0x800cd3d8 / 0x800cd3dc.
  Every entry includes the 0xff terminator, which loads as -1 against 255, and some kana
  codes are 0x80 or more too.
- **Wrong characters.** 'Mule', 'Richguy' and 'Appraiser' are meant for a character at the
  tavern, in no party (`rescue_candidates`, 0x8008d300, built just before), but each loop
  compares `roster[k]` for k below the candidate count, not `roster[rescue_candidates[k]]`.
  So it tests the first few roster characters, usually party members.
- **Alba** counts 6 bytes and then tests the count against 8 (0x800cd40c), so hers can't
  match even unsigned.
- **Lychee's 1:72 copies no name**, so {ff12} shows whatever the buffer last held.

Emulator (`rips/re/work/P3-bugs/rosea/guy_test.py`, output in `guy/`; Guy's party,
introduced, 40 RNG trials, a breakpoint on each picker): on the original code a member named
ちんこ never got 1:72 (Lychee 12 turns: 65-67), nor did アイテムもち get 1:68. With `lb`
made `lbu` at the two Lychee loads (RAM only): "Dick" and "RETARD" got 1:72 on 12 of 12
turns ("Earth... eek!", the wrong name), "Dickens" and "dick" didn't; with Mule also in
the 8-byte slot, a party member named Mule got 1:68 on 12 of 12, and the tavern character
named Mule (roster 4, the one the line is about) never did. [emu]

The English names don't all fit: 'Mule' fits the 8-byte compare (4 letters, 0xff, 0x40,
and two bytes after them, zero in every stored name seen so far; there's one slot, so
MULE can't also match); 'Richguy' needs 9 bytes against 6; 'Appraiser' is 9 letters, more than a name
can hold (8). Alstron's 'A' (1:60, あ) uses three byte tests and works; it's localized
(`asm/joke_names.asm`).

Questions for Chris: fix Lychee's two loads (two words, `lb` → `lbu`) so her 1:72 and
1:68 work, and copy the matched name for 1:72? Make the tavern checks look at the
tavern characters? What should Lilia's and Alba's names be, given the widths?

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

**Decided (Chris, 2026-10-11): kept as the original, and documented on the site**
(decisions.md item 8). On the hardcore-mode list (ROADMAP.md).

### 3.2 Weapon effects ignore the level difference

`melee_apply_hits` computes a bonus (a quarter of the level difference, up to 30) or a
penalty (up to 20) and passes them to `apply_status_effects`, which never reads its third
and fourth arguments. [code, disassembly (D)]

Question for Chris: fixing it makes a weapon's poison, sleep, stone and death effects land
more often on weaker monsters and less often on stronger ones. Fix it, or keep the flat
odds?

**Decided (Chris, 2026-10-11): kept, and documented** (decisions.md item 9). On the
hardcore-mode list (ROADMAP.md).

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

**Decided (Chris, 2026-10-11): kept as the original** (decisions.md item 10). On the
hardcore-mode list (ROADMAP.md).

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

### 3.5 The Ninja's beheading and the Monk's knock-out from class never apply

`battle_derive_stats` (BATTLE 0x800a197c) gives a Ninja (class 12) hit effect 0x40,
beheading, at 11%, and a Monk (13) knock-out at 11%, on top of their gear. It tests the
class in $s3, which the function never loads: it holds the caller's value, 2 at battle
start or a screen Y coordinate on a panel redraw, never 12 or 13. [code] In 2,700 calls
with a Ninja in the party, $s3 was only 2, 0xc0 or 0xda, and the Ninja's chance read 20
(the bare-hand 20% alone, 0x800a2880). [emu] So the class bonus is dead; bare-handed
Ninjas and Monks still get their 20%, and weapons their own chances (ninja.md).

Question for Chris: fixing it (load the class into $s3) gives every Ninja 11% more
beheading and every Monk 11% more knock-out, armed or not. Fix it, or keep the odds as
the game plays? Found 2026-10-17 (docs/re/ninja.md).

**Decided (Chris, 2026-10-17): fix it, and disclose it clearly at release as a balance
change** (decisions.md 31). `asm/bugfix_class_hit_effect.asm` reads the class from the
character's work copy, as the same function does at 0x800a1a1c. A bare-handed Ninja's
beheading goes from 20% to 31% a hand; armed, the gear's chances plus 11. The same for
a Monk's knock-out.

A related oddity, harmless as far as seen: for a monster target, the resistance bytes for
effects it isn't immune to are never set; they read 0 in all 16 checks. [code] [emu]

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
