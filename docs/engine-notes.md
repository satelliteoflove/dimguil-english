# Engine notes

What we know about how Wizardry: Dimguil (SLPS-02691 Rev 1) works, beyond Remisse's
notes in `findings.md`. This file is the front door. It summarizes the game's rules and
keeps the notes the translation itself depends on (text printing, file loading, glyph
pools). The detail is in the chapters in `docs/re/`, listed in `docs/re/README.md`,
and the layout of the code and the tools are in `code-map.md`.

Addresses are RAM unless a module or file is named. Overlays share the window at
0x800a1000, so an overlay address only means something with its module named. Every
finding in the chapters is marked confirmed (by code read, RAM read or an emulator
test, named each time) or inferred; the summaries below link to them rather than
repeating the marks, and say "inferred" where a summary rests on an inference.

The rules were read from the original disc's code (`rips/clean/dimguil`) with Ghidra,
on 2026-10-10 and 11; the earlier notes below came from translating the game.

## How the game is put together

- **Modules.** The executable (MAIN) stays resident. Seven overlays take turns at
  0x800a1000: MAZE (the maze and its camp; also loaded at boot), BATTLE, MCARD (every
  NPC talk, the maze's START menu, and the memory card), JOUKA (the castle town and
  the Training Grounds), HAZURE (the Edge of Town), and the card game's CMAIN and
  CMENU. `load_file` (0x80012d18) loads them from file table 0 (indexes 172-178); the
  card game's two are loaded by name. Sizes, coverage and patch sites: `code-map.md`.
- **Main loop.** `main` (0x800114d8) loops forever. A request in `game_mode`
  (0x8007967e) makes it load an overlay (1 and 4 MAZE, 2 BATTLE, 3 JOUKA, 5 HAZURE,
  6 the card game, 7 and 9 MCARD, 8 the catalog or Compendium) and set `game_state`
  (0x80079a13), which picks the routine it calls each frame. With MAZE loaded that's
  `maze_frame` (0x800a31d8); with BATTLE, `battle_main` (0x800a2cd8); a talk is state
  0x35, which calls the handler picked by `talk_party` (0x80079797).
- **Underlays.** A smaller overlay leaves the previous one's tail in RAM, and two rely
  on it: BATTLE calls seven of MAZE's routines at 0x800ee5f4-0x800ef0cc (so a patch to
  MAZE above 0x800db028 changes battles too), and HAZURE calls JOUKA's 0x800d9130.
- **Fixed calls.** The executable calls overlay routines at fixed addresses, valid only
  while the right overlay is loaded (0x800c76f0, for one, falls in the middle of
  Balbo's talk handler in MCARD).
- **Randomness.** `rand_upto(n)` (0x8001cb18, 0..n inclusive) keeps its state at
  0x80079558 and 0x8007955c; `$gp` is 0x80079538. BATTLE doesn't use it: it rolls
  with two small LCGs in the executable (D-battle.md, "Randomness"). The town calls `rand_upto(2)` every frame, so
  waiting a different number of frames before the same button presses changes the next
  roll: that's how the emulator tests checked both sides of a threshold without
  writing to RAM. Battle rolls don't follow frame timing: `rand_below` keeps its LCG
  state at 0x80079a34 (`battle_rng_state`, x * 0x41c64e6d + 0x3039), and a fight
  started from a save state plays out the same whatever frames are waited first, so
  the harness's old "seed" (a few frames of waiting) gave the same fight every time.
  Writing a seeded value to 0x80079a34 after loading the state gives a real spread of
  fights from one state. The harness benches do this
  (`rips/agents/chapters/ag16/fight_rng.py`). On the 17 Were Centipedes at Area B
  (26,8,14) it showed 30 different fights: 6 wipes under the current rules, 9 when
  running at round 1. It's a write of data, for testing only.
- **Records.** Twenty characters at 0x8007d708 (0xd0 bytes each), twenty party records
  at 0x8008f8c8 (54 bytes), the party you walk with mirrored at 0x8007e810, 382 item
  records at 0x80052bf2 in the executable, and monster records loaded per battle at
  0x8008a918. Every field is in `docs/re/G-records.md` and `scripts/re/types.h`.
- **Story state.** `progress_bits` (0x8007986c) gets bit k the first time the party
  enters area tier k (bit 1 the Grounds, bit 2 the Shrine, and so on), so it grows 2, 6,
  0xe ... 0x7fe; many talks and shops pick their lines and stock by it. `npc_stage`
  (0x80079618) holds each NPC party's story stage, `npc_flags` (0x80079754) which
  meetings and scenes have happened, `story_flags` (0x80079b44) and `oneshot_flags`
  (0x80079b28) the rest. Each character remembers which NPCs it has met (`met_bits`,
  roster +0xc6), and the save keeps it.

## The game's rules

The formulas players care most about are collected in `docs/re/README.md`, "Rules at a
glance". By subsystem:

### The maze (A-maze.md)

- **Steps.** After each step, in order: a wandering token on your square starts a
  fight or a talk; poison (1 in 4 per step, its strength off HP) and regeneration
  (1 in 4) run, and the party's spell timers count down; a party with nobody standing
  is wiped (`wipe_check`, so poison or a pit wipes a party exactly as a battle does);
  then the square's event runs, and the tokens move.
- **Encounters.** There's no per-step encounter roll. Fights come from fight squares
  (each a single percentage chance per visit to the floor), from up to 16 wandering
  tokens per floor that you meet by sharing a square (you can hear them within one
  square), and from fixed fights set by events.
- **NPC parties.** On most floors exactly one token is an NPC party, picked at random
  from the parties the story allows there. A party's random meetings only start after
  its fixed first meeting, and on the Grounds and in the Shrine no party wanders at all
  while any fixed meeting there is pending. The full table of who can be met where:
  A-maze.md §8.
- **Events.** Each floor has a 24 x 24 map of event records (teleports, chutes, lifts,
  fight squares, signs, doors, pillars...); stepping on a square runs `square_arrive`,
  Investigate runs `square_examine`. Hidden doors are found by a search roll on each
  step. A-maze.md §9-10.
- **Heal spots.** Event 0x3f is a wall switch ("There's a switch on the wall. Will you
  press it?", EVENTMES 167) that heals. `square_examine` (0x800bb790) case 0x3f needs
  the party facing the record's p1, then sets prompt 0xe. On Yes, `maze_prompt_result`
  (0x800befcc, prompt 0xe at 0x800bf5e8) gives every member whose status has none of
  0x380 (dead, ashes, lost) full HP, status 0, poison 0 and +0x79 0. Spell points
  aren't touched and the dead stay dead. There's no cost and no flag, so it works every
  time. Three squares: Area B B4 E5 N18 facing west, Area E B3 E12 N4 facing north,
  Dragon B1 E10 N13 facing west. **[code]**, checked in the emulator on B4 (2026-10-15).
  - The same switch text has other effects on other event types: 0x40 poisons the party
    (prompt 0xf, poison +50; one sits on B4 at E5 N5 facing south), 0x42 toggles
    `maze_event_flags` bit p2 (prompt 0x10), and 0x6c refills spell points (prompt 0x1f,
    which calls a MAZE copy of the spell point recalc, 0x800be8e0). Event 0x50 (Area D's
    seeping pillars, EVENTMES 210/211) refills spell points with no prompt. A-maze.md
    "Heal spots" has the squares.
  - Ghidra's case labels in `maze_prompt_result` are wrong in places: it shows prompt 1
    sharing the heal and 0x11 sharing the spell refill. The jump table at 0x800a1918
    sends 1 to the pillar fight (0x800bf018) and 0x11 to a fixed toggle of bit 0x200000.
- **Area B's west rooms.** B4 and B5 (areas 24 and 23) each have a west part, x 4-9 in
  game coordinates (not B4's south-west corner: Chris walked to the heal switch at
  (5, 5) without leaving B4), joined to each other by the stairs at (8, 10) but not to
  the rest of either floor. The only way in is B3's stairs at (5, 13) down to B4
  (4, 13), and B3's west side is reached through B2 and B1. So five of B4 and B5's fight squares (B4
  (5, 9), (5, 15), (8, 12); B5 (7, 8), (7, 15)) are a walk through B3, B2 and B1 from
  the others. Found from the fan site's map data with the harness's planner
  (2026-10-15); Chris's own B4/B5 trip from the same state never went there.

### Wipes and bodies (A-maze.md §4-6, D-battle.md, fallen-parties.md)

- **A wipe** deletes anyone Lost, halves every member's gold, and rolls one member's
  items for destruction six times over (2 in 3 per roll for rare items, the Tablet of
  the Sun among them; 1 in 4 for the rest). That's a bug: the loop should go over each
  member (bugs.md 3.1). Chris decided to keep it (decisions.md item 8); it's on the
  hardcore-mode list in ROADMAP.md. Outside the Training Maze
  the bodies stay on the square where they fell; in it they go straight to town, but
  still lose items and gold.
- **Bodies don't decay.** Nothing takes items, gold or status from a party left in the
  maze, however long it lies there: every routine that writes characters or the party
  table was read, and two emulator runs (40 inn nights; a trip back into the maze to the
  bodies' square) logged no such write. fallen-parties.md has the full table.
- **Getting them back.** Look for Companions (the maze's START menu) picks up bodies
  on your exact square for free, items and gold included; one square off it says
  "There are faint traces, but no one was found." Or an NPC party carries them home for
  a fee (below). Either way they reach town still dead, and the Temple raises them.

### NPC talks (C-talk.md, C-talk-lines.md)

- **Handlers.** Every talk runs in MCARD. `talk_party` picks one of 28 handlers: 0-4
  are the parties met at random (Guy, Balbo, Fontana, Cresson's scholars, Zaril), 6-28
  one-off scenes. Each builds its scripts on its own stack every frame and runs them
  through `talk_script_run` (0x800b8ccc), a small interpreter of 13 opcodes (say,
  bar, show and hide a portrait, cure, gold, close...). `scripts/re/talkscripts.py`
  dumps them, and `C-talk-lines.md` says when each NPC_MES string plays.
- **A Talk press.** Introductions first, while no member has met the leader. After
  that, half the time a service is tried, in order: healing (when someone is hurt or
  has a status), a sale (when someone has an empty pack slot), a rescue (when another
  of your parties lies wiped in the maze), each on its own 50% roll. Otherwise a chat
  topic.
- **Healing** is free, from two healers per party chosen 50/50, and what they can cure
  grows with their party's story stage; most roll a 20% "out of magic" first. An NPC's
  Kadorto never fails: no roll, no fee, no VIT loss, no aging, and it works on ashes.
  Checked in the emulator on 2026-10-14 (rips/agents/chapters/cleo/): Cleo raised a dead
  Dax to full HP, age and stats unchanged. The offer came on the 18th Talk of one meeting
  and the 11th of another; picked a frame earlier, the first one was her 20% "no healing
  magic", which is rolled after the pick. The
  pick's cursor is 0x800796cc (column) and 0x800796cd (row), party slot = row × 3 +
  column. Cresson's party's Underground B3 meeting is at RAM (8, 17) (fixed_meet_table
  0x8005e6ac, id 0x16); its token is spent once met, until the party next arrives on B3,
  and the talk starts some frames after the step onto the square.
- **Sales** are sets of three items at one price (5 to 20,000 G), chosen by
  `progress_bits`; some of the items are cursed.
- **The rescue.** Guy's, Balbo's and Fontana's parties offer it; Cresson's and Zaril's
  never do. A party counts if every member is paralyzed or worse. On yes, one such party
  goes back to town, still dead, and the NPC party takes a fee from each member: Guy all
  the gold; Balbo every item (all ten slots, equipped and cursed ones too); Fontana half
  the gold and the items in the first, third, fifth, seventh and ninth slots (0, 2, 4, 6,
  8 counting from 0). The gate (`progress_bits` & 0x1e) is open from the first trip
  into the Grounds. All three fees were confirmed in natural play
  (`re/rescue-test.md`), which also found that a rescued party stayed on offer and paid
  again: the Yes left its record in the party table, and the scan only checks status.
  Fixed (bugs.md 1.13, `asm/bugfix_rescue_repeat.asm`): the Yes frees the record the way
  Look for Companions does, in a routine shared by the three handlers over two unused
  MCARD routines (0x800ab1cc). The town only clears such records in its full cleanup,
  after a wipe, a load or "Go On with Another Party" (JOUKA 0x800a2348); a plain return
  home just copies the current party back into its slot.
- **Bugs and cut content.** C found a dozen. The clear bugs are fixed (bugs.md group
  1). Of the cut-looking ones, Zaril's healing (9135ef5), Guy's and Fontana's
  re-introductions (7498b1c), Cresson's greeting (7166f5d) and Fontana's chat about
  Zaril's new party (7c99607) are reopened, and the identify service and Balbo's party's
  "heard that already" stay unused (decisions.md).
- Earlier notes, now in C-talk.md: the 2026-10-06 trace had the interpreter at
  0x800b8ccc right but read two opcodes' arguments wrong (opcode 0 takes two and sets
  met bits only during introductions; opcode 6 takes one). The 2026-10-10 body-recovery
  trace, from a RAM dump taken during a talk with Guy (`rips/probe/ram_talk94.bin`),
  stands, except that the offer is the third service roll, not a coin flip of its own.
  Forcing an NPC party through the battle loader (`nptshow.py`'s trick) starts a fight,
  not a talk; the first meeting with Guy at the Shrine door is a fixed meeting like
  the others (A-maze.md §8).

### The camp (B-camp.md)

- **Spells.** 26 spells work in camp. Dumapic and Malor fail in areas 9-17, Loktofeit
  there too, and a 232-step no-magic countdown set by some squares makes every camp
  spell fail; each failure still spends the point. A heal with nothing to heal says
  "What?" and spends it. Camp Kadorto works on rand(0..80) < VIT × 4, takes 0-1 VIT and
  adds 1-52 weeks of age; below 4 VIT the dead turn to ashes and the ashes are Lost.
  Loktofeit empties every pack slot of every member.
- **Items.** Effects are hard-coded by item id. A Bishop identifies with
  (level - item level + 1) × 20%, held to 5-75%; a miss may make the Bishop afraid and
  put a cursed item on them. Equipping an item of the wrong alignment curses it.
- **Heal ranges** in camp: Dios 2-8, Diomas 3-6, Madial 10-50 per member.

### Battle (D-battle.md)

- **Initiative.** Every fighter gets a tick 0-10 each round; lower acts first. The
  party's is rand(10) adjusted by agility; monsters' is 2-9, so a fast character often
  beats every monster.
- **To hit.** A swing hits on rand(20) >= T, where T depends on the target's AC, the
  attacker's to-hit and the target group (party: base 20-23 by group, capped at 19, at
  least 1); 5% to 95% a swing. Damage is the weapon's dice, up to nearly double against
  a target that's confused, poisoned or worse (or from hiding), and doubled by a
  slaying weapon that matches the monster's class.
- **Spells.** Most battle spells are one call to a dice routine (Halito 2d4). Magic
  resistance is a per-school percentage, and every spell has at least a 1% chance of
  being resisted. The Alchemist's damage spells
  are three-round clouds. Battle heals: Dios 2-8, Dial 2-16, Dialma 3-24, Diomas 3-6,
  Madial 17-68 per member.
- **Surprise and fleeing.** 19% the party surprises the monsters, else 15.4% the
  monsters surprise the party. The party flees on 80 (+5 × the level ratio when
  stronger) minus 2 × the area's danger level; fixed battles can't be fled.
- **After.** Experience is split among members below status 0x20; chest gold the same.
  Chests are trapped by the area's danger level, and traps are picked from the chest's
  mask.
- **Choosing the target group** (`group_pick` 0x800cf0dc, from `party_commands`
  0x800cbec8; checked in the emulator 2026-10-13, rips/re/work/grouppick/). One picker
  serves every command aimed at monsters. The menu state `battle_menu_screen`
  (0x800796e0) is 0x11 for Fight, 0x34 for a spell, 0x54 for an item, 0x41 Dispel,
  0x71 Ambush and 0x91 Breath. On circle the pick goes to `pick_result` (0x800da802) and
  then into the member's combatant record, +0xb at 0x8008e23b + member × 0xe, with +0xa
  the action (-1 Fight, -4 Dispel, -9 Breath, or the spell id). Group numbers are
  `battle_groups` indices, kept contiguous from 1. The picker has two forms:
  - Random encounters use a list in the group window at the top. The cursor is
    0x80079b95 (group - 1), set to 0 every time the pick opens. Up and down wrap over
    0..max; left and right do nothing. For Fight, max is min(weapon reach,
    groups standing) - 1 (0x800da7fc), so a short weapon only offers groups 1-2. For
    spells and items it's groups standing (0x800798b8) - 1.
  - Fixed battles (`battle_fixed` 0x80079bde = 1: the chapter guardians and other set
    fights) use the 3x2 grid of name boxes, top row the front. The cursor is column
    0x800da800 (0-2) and row 0x800da801. Grid cell p = column + 3 × row + 1 shows
    layout entry 0x80079c28[p] (0xff is the grey "Empty" box), and group g is entry
    0x80079c50[g]. Each command opens on the top row, on the middle box if it holds a
    group, else the left, else the right. Left and right wrap within the row and skip
    empty boxes. Up and down flip the row, then look for a group starting from the same
    column, going left for up and right for down; if the row has none, the cursor stays
    put. Fight only reaches the bottom row when the weapon reaches more groups than the
    front row holds (`short_reach_groups` 0x8007989d < `cmd_reach` 0x800da7fb), and its
    confirm is limited to the top row otherwise. Spells, items, Dispel, Ambush and
    Breath can always pick either row.
  - A group spell or item in a fixed battle (spell flag 0x40; also Breath from a
    member above level 8, read in the code but not tried) picks a whole row: the frame spans the row, and +0xb gets 1 for the top row or 2
    for the bottom one. `spell_group_range` then sweeps groups 1..front count or the
    back row's groups. So Mahalito at the Guardians' Arch Mage hits the Arch Priest
    too: in a fixed battle a group spell can't single out one group.
  - With one group standing (and a last index of 0) the pick takes group 1 at once.
    Fight never shows 0x11; a spell shows 0x34 for one frame before moving on.
  - The cursor isn't remembered between members or rounds. The one exception is
    cancelling a fixed-battle spell pick back to the spell list: the grid keeps its
    place.
  - A confused member's command list skips the reach check, so its Fight pick uses the
    previous member's reach (left in 0x800da7fb), and can offer fewer groups than
    the weapon would.
  - In random encounters, `groups_reorder` can shuffle the groups at the start of every
    round, so a target has to be found again each round by monster id (`battle_groups`
    +2) and identified flag. Index numbers from an earlier round won't do.
- Battle sound (bugs.md 1.15). Spell sounds, the encounter music and the item and
  chest-trap tunes all play on one libsnd sequence slot, gp+0x2c0, out of the file they
  came in with: a spell's animation file (MAGICnn.BIN, table 1, 0x1bb + animation) and
  the music into 0x801a0400, the tunes into 0x801b4400. MAIN 0x8001c494 stops and closes
  the old sequence and opens the new one, but only after the new file has loaded, so
  until 2026-10-13 a sound still playing read the next file's bytes as its events; a
  tempo of 0 there is a divide by zero (MAIN 0x80029c08, `break 7`), which the kernel
  doesn't handle, and the game froze. `asm/bugfix_spell_sound_reload.asm` stops it
  before each of the three loads (0x800a421c, 0x800a54d8, 0x800a5534), from a routine
  in the dead FUN_800c3188. A second SsSeqStop on a stopped or closed slot is harmless.

### The town (E-town.md)

- **Temple.** The fee (level × 100 paralysis, × 200 stone, × 250 dead, × 500 ashes) is
  paid before the roll. Paralysis and stone always cure. The dead come back with
  1 HP on rand(0..99) < 60 + 2 × VIT, else turn to ashes; ashes come back with full HP
  on < 68 + 2 × VIT, else the character is Lost and deleted. Ashes are easier to raise
  than the dead.
- **Inn.** Rooms cost 0, 10, 50, 200, 500 or 10,000 G a week for +0, 1, 3, 7, 10 HP or
  full; each paid week ages the character a week (the Stables a day), and one level-up
  is tried per stay.
- **Boltac's** pays half the price for anything sold; uncursing destroys the item;
  selling out nothing earns a free Book of Movement, more than once.
- **Tavern recruits** come from pools gated by alignment, wipes and progress, matching
  a June 2000 fan tally.

### The Edge of Town, the Training Grounds and the save (F-edge-save.md)

- **Creation.** Bonus points are 7-10 (about 95%), 17-20 (4.5%) or 27-30 (0.2%). The
  class list follows the stats and the alignment table. Accepting a character that rolled
  under 10 points offers "Retrain?": Yes trains them three years, to level 4 and three
  years older (emulator-checked 2026-10-12; first written as "declining" and "a year").
- **Class change** resets each stat to the higher of the race base and the new class's
  minimum, adds three years and unequips everything not cursed.
- **The save** is one file of two blocks: a header and a 0x2400-byte image whose layout
  is fully mapped (`scripts/re/savefile.py` decodes it). Nothing in saving, loading or
  resuming touches characters left in the maze.
- **Creation costs nothing.** A new character starts with 100 gold (`training_create`
  0x800af5d8 sets `new_char.gold = 100`); a Fighter also brings a Long Sword and Leather
  Armor, worn. Going to the Training Grounds empties the party: everyone waits in the
  tavern (emulator, 2026-10-14, the harness mule).
- **Out of the party, a character keeps everything.** The tavern's Remove Member
  (`tavern_remove_member` JOUKA 0x800aa0a4, state 0x19) writes only the party record
  (0x8007e812 slot = 0xff, then the parties table); it never touches the roster
  (0x8007d708, 0xd0 a record, pack words at +0x20). A spare character can hold items.
- **Give at the Edge of Town** (Prepare > Inspect > Items > Give, `edge_give_item`
  HAZURE 0x800b3c6c) shows both packs side by side and moves items either way; it won't
  open for a character with an empty pack. Its regeneration bookkeeping reads the wrong
  pack slot: after a give it takes the given item's regen from slot `0x80079c60` (the
  Inspect menu's cursor, 1 here) instead of the list row `0x80079c6b`, and a swap reads
  slot `0x80079c65` (the Items menu's cursor, 2). The code was copied from the camp's
  Give, where `0x80079c60` is the list row. Only items with a regen value (Item +0x21)
  are affected; not yet seen in play.
- **Equip at the Edge of Town** (Prepare > Inspect > Items > Equip, `equip_menu` HAZURE
  0x800afa9c) runs the camp's equip prompts on the same fields: slot `0x80079b7a`,
  prompt `0x80079562`, state `0x8007956c` (5, 10, then 15 at each slot's prompt, 20, and
  110 then 0 at the end), candidates at `0x800905e0`. Only the cursor differs: the
  Edge's list row `0x80079c6b` instead of camp's `0x80079c60` (0 for none, k for
  candidate k - 1, in both). The Edge's own state `0x800796e1`
  stays at 45 throughout. Cross backs out one screen a press: the Give lists, "to
  whom?", Items, the member's menu, then "Inspect whom?" (45 -> 35 -> 25), so one visit
  can serve several members (emulator, 2026-10-15, the harness backups).

### Records (G-records.md)

- The character record's fields (status bits, age, stats, the pack's flag bits:
  sub hand, main hand, equipped, identified, cursed), the item table (restrictions,
  curse, break chance, price, stock, AC, to-hit, damage, swings, slaying, battle spell),
  monster records, race and class tables, the seven EXP tables, HP dice, spell points
  and learning, level-up stat rolls and death of old age.

### Bugs, descriptions and open decisions

- `docs/re/bugs.md`: every bug found, in three groups. Group 1 (sixteen clear bugs,
  three of them found by the harness runs, one by the rescue test and one by the lock test) is fixed in `asm/bugfix_*.asm`.
- `docs/re/description-check.md`: item, spell, Compendium and help text checked against
  the records and the code (18 spell ranges in the original are wrong).
- `docs/re/decisions.md`: the open questions and Chris's decision on each (all decided).

## Notes the translation depends on

These came from fitting the English into the game. They're the reason for most of the
patches in `asm/`.

### Loading files

- The executable holds four tables of file locations (MSF + sector count); a loader call
  takes (destination, index, table). `scripts/gametext.py --files` lists them, and
  `scripts/relocate.py` moves files that outgrow their sectors and patches the tables.
- A file may only grow as far as its load buffer allows. Limits checked so far, all in
  `relocate.py`'s `MAX_SECTORS`:

| File | Loads to | Limit | What follows |
|---|---|---|---|
| SISETU.OBJ | 0x801d8c00 | 14 sectors | live data at 0x801e0200 |
| I_NAME_E.OBJ / I_NAME_J.OBJ | 0x801d1000 | 12 sectors | FIGHTMSG.OBJ, resident at 0x801d7000 |
| FIGHTMSG.OBJ | 0x801d7000 | 3 sectors (unchanged) | SISETU.OBJ at 0x801d8c00 |
| NPC_MES1-5.OBJ | 0x801a0400 | 32 sectors | shared staging area (wall textures, portraits) |

- NPC_MES files load when a party is met, after the portrait TIM has gone to VRAM through
  the same buffer. The portrait uploader (0x8001d93c) is called again mid-conversation
  with 0x801a0400, finds no TIM magic there and does nothing, in the original too.
- EVENTMES.BIN (table 2 index 26) is 27,623 bytes in 14 sectors, so it can grow 1,049
  bytes in place (`extendByBytes` 1049) without moving. The event review pushed it 326
  over on 2026-10-03, and until 2026-10-04 the encoder silently dropped every event
  translation (build.sh only printed the ERROR). build.sh now stops on an encoder
  ERROR. Checked: the game's loader reads the whole grown file, tail included.
- String offsets in the text files are 16-bit, so no text file can pass 64 KB.
- Save states hold loaded files. After a build that changes text, or moves a file, old
  states show stale text or read the wrong sectors; regenerate them (`mkstates.py`).
  - A state from before a build that moved files reads the NPC files from the old
    sectors and shows blank boxes. Copying the four file tables (0x80051760-0x80052700)
    from the built SLPS_026.91 into RAM after loading fixes that.
  - FIGHTMSG.OBJ is loaded once at boot and stays resident, so a state made on an older
    build keeps that build's battle text for as long as it runs, and with newer code
    around it prints garbage ("Mars looses at Flap Insect wi / th / 0088ththerer...",
    seen 2026-10-11 in a test state descended from an old one). The same goes for an
    emulator save state carried across a patch update in play: continue from the
    memory card instead.

### CD reads: the DsPacket race ("You've met someone!" lock)

- Every disc read goes through the CD library's DsRead (0x80038300; libds, identical
  bytes on the Japanese disc). `load_file` (0x80012d18) calls it and spins on DsReadSync
  (0x800386b0); `load_file_alt` (0x80012f5c, the encounter path 0x80020e10) queues an
  async read instead: 0x80079bc2 = 1, and the pump 0x800130a4 calls DsSync (0x80036bf8)
  then DsRead and sets 2, then 3 once DsReadSync reports 0. Its pending read is in
  0x80079748 (MSF), 0x800795ec (index), 0x8007986b (table), 0x80079824 (destination).
  The next load first loops on the pump until 3.
- DsRead has DsPacket (0x80036888) put four commands in the library's 8-slot queue (ring
  at 0x80098628, 0x18 bytes a slot, count 0x800986f0). Each slot is written in order: id
  (0x80036b08), command, parameter bytes (memcpy 0x800380cc), parameter pointer
  (0x80036b38), then the count. The second of the four is Setmode, whose parameter is
  the mode byte.
- The commands are sent from interrupts. libds's VSync callback sends Getstat, and when
  the drive answers (INT3, handled in the same exception if it comes before the VSync
  handler returns) the dispatcher sends the packet's next slot (0x80037358 → CD_cw
  0x800350cc). It issues the slot under its cursor (0x800986ec) if the slot's id is
  non-zero (0x800360dc, 0x80036efc); the count only has to be above 0.
- The stall: the VSync lands while DsPacket is between the Setmode slot's id and its
  parameter pointer (instructions 270-318 after DsRead's entry, 48 instructions), and
  the VSync handler runs long enough for the Getstat answer to arrive inside it. The
  dispatcher sends Setmode with a null parameter, CD_cw refuses it ("no param", returns
  -2 at 0x80035118), and the packet goes no further. DsReadSync keeps reporting the
  whole file (33 sectors for M_DT005) and the main loop spins in `load_file_alt`; the
  screen holds, the music plays on (the sound driver runs in the VSync handler), and no
  input is taken. After about 1,200 frames the library times the read out, DsReadSync
  returns -1, and MAIN's load pump (0x800130a4) issues DsRead again (retry count
  0x800798c9; three tries, then a blocking `load_file`). So it's a 20-second freeze, not
  a lock: from `rips/harness/t3/metlock/v1_r6b/f3066.state` with no input the read
  finishes at frame 1,263, and at frame 63 with the fix laid over MAIN. (Corrected
  2026-10-13: this note first said nothing retries. The harness had given up 350 frames
  into the stall.)
- Traced (`rips/harness/t3/metlock/`): the t4v1 lock replays exactly from its goal state
  (`replay.py`, `inrep.py`). The meeting read M_DT005 (table 1 index 49, LBA 2109) starts
  301 instructions before the VSync; one frame later (532 before) it's fine. In the
  stall a single exception runs from instruction 248,395 to 280,083: Getstat sent at
  257,625, Setmode with a null parameter at 279,839, the parameter pointer stored by the
  main thread at 280,170. If the handler returns first (a lead of 277 in the shift
  sweep, a 14,000-instruction exception) the read goes through.
- Not our patch: the library is byte-identical, the files read (M_DT003-006) sit at the
  same LBAs with the same sizes on both discs (our relocations only touch table 2), and
  the read is one the original makes. Our text code does change how many instructions a
  frame takes, so it moves which reads land in the window; the harness can't finish
  Japanese battles, so the rate on the Japanese disc wasn't measured.
- Not the emulator either, though its timing matters. Beetle answers a command after
  12,315-15,315 cycles (`cdc.c`, `PendingCommandCounter`); psx-spx gives 19,000-201,000
  (average 50,401) on hardware, so the answer comes inside a long VSync handler less often
  there. None of Beetle's CD options touch that delay (`cd_fastload` only scales the
  sector rate, `cd_access_method` is host I/O), and RetroArch's Beetle HW defaults
  (interpreter, sync, 2x) run the same timing as the harness.
- How often: two locks in about 60 hours of harness play (41 chapter 1 runs; of 121
  stuck states, only those two are in this condition), both at the tiger approach. Timed
  over four chapter 1 runs: 10,337 reads, 21 starting within 2,000 instructions of a
  VSync, none in the window. At the t4v1 meeting, 1 of 100 input shifts locks.
- Fix (applied, `asm/bugfix_dspacket_race.asm`; docs/re/bugs.md 1.12 says why): DsPacket
  writes each slot's id last, so the dispatcher can't take a slot that isn't finished.
  14 words in both copies of the fill loop, same instruction count. Tested in RAM: the
  t4v1 repro (same VSync point, lead 301) and all 100 shifts read normally; two chapter 1
  runs make the same reads in the same frames (one frame off in one); the suite passes
  187 of 187 on a patched test copy of the disc. Freed slots always read id 0 (the packet
  pop clears them, 0x80035d10; so do the queue resets), and the dispatcher issues a slot
  only when its id is non-zero (0x800360dc, 0x80036efc), so a slot whose id is written
  last can't go out half-written.

### Text printer

- One printer (reader at 0x8001e0c0) draws dialogue, battle and event text. Codes below
  0xd8 are English glyphs and digraphs, priced by the VWF table at 0x80060e97.
- Glyphs 0xb6 and 0xb7 are `"` and the digraph `w ` in the English font, but the
  Japanese voicing marks (゛ ゜) to the printers, which drew the glyph before them in its
  voiced form and swallowed the mark. The maze's event box (0x8001ff04) did it after any
  glyph ("how hard" printed "ズhard"); the other printers ask a helper that each overlay
  carries (MAZE, MCARD, JOUKA, CMENU, HAZURE, BATTLE), which did it after kana-like codes
  (`y "` printed as ブ). `asm/voicing_marks.asm` turns all of it off, so a `"` inside a
  line is safe now; `npcfit.py` still flags it, which does no harm.
- Two more printers merge inline without the helper, and were missed at first: BATTLE's
  (0x800d19a4, the battle box and menus; test at 0x800d1a68) and MAZE's text_draw
  (0x800a201c; 0x800a20e0). FIGHTMSG 33 "tries to blow away" printed "b  away": "lo" +
  "w " drew a blank voiced cell. Every inline test is the same three instructions,
  `addiu v0, code, 0x4a / andi v0, v0, 0xff / sltiu v0, v0, 2` (code - 0xb6 < 2). The
  printers only merge with the 12 px font on (0x8007977a bit 0).
- The line measures skip the marks as well, since a merged mark takes no room. A line
  with `"` or `w ` was measured short and printed right of center by half the glyph's
  advance: 2 px per `"`, 6 px per `w `. The measures, all with the same test: the event
  box's first line (0x8001fb4c, test at 0x8001fc98) and later lines (event_box_print,
  0x800201f0), the battle box and BATTLE's single centered lines (both MAIN 0x80022024,
  test at 0x800220cc), each of these only for the 12 px font; text_at in MAZE
  (0x800a1f7c), MCARD (0x800ad618), JOUKA (0x800dbe2c) and HAZURE (0x800bca4c), always.
  The battle expander's wrap column for an inserted name (text_expand, 0x8001e2d0)
  skipped them too, while the name's length counted them, and MCARD's typewriter
  (0x800b3de0, test at 0x800b3ec8) revealed a mark for free with the glyph before.
- A count and the sprites it stands for must change together. The battle box fades its
  text in line by line: FUN_800d202c stores the measure's glyph count for each line at
  0x8008d340 + 8 x layer, and FUN_800d23f4 fades that many sprites, line by line, and
  calls the box done when the faded count equals the layer's sprites in use (0x80079938).
  If a line draws more sprites than its count, the extra ones never fade in and the box
  never finishes. That hung the first version of the fix (2212979), which patched the
  measure in MAIN: a save state keeps MAIN's code from the build it was made on, while
  BATTLE.BIN reloads from the disc at every fight, so a state made on an older build ran
  new BATTLE (no merge) with old MAIN (skip marks). "Ocelotl tries to blow away / Mercury
  with a body slam." drew 42 sprites against counts of 20 + 21, the period never faded
  in, and the box waited for good (phase 46). The measure in MAIN is left as it was;
  BATTLE passes it font 0 at both calls (0x800d21a0, 0x800d3114), since its only use of
  that argument is "skip marks in the 12 px font". Merge and count now sit in the same
  file in every pair: event box (MAIN), text_at and text_draw (each overlay), battle
  (BATTLE.BIN), and no mix of old and new files can disagree.
- Every mark test in the eight code files (clean disc), and what's done with it:
  - MAIN: 0x8001e2c8 expander wrap column, 0x8001fc90 and 0x800201e8 event box
    measures, 0x8001ffe0 event box merge: patched. 0x800220c4 battle measure: left,
    BATTLE passes font 0. (The expander's test, with its font check, was later removed
    whole by word_wrap.asm, which keeps its digraph table there.)
  - BATTLE: 0x800d1a60 merge: patched. The helper (0x800d3510) returns 0.
  - MAZE: 0x800a1f74 text_at measure, 0x800a20d8 text_draw merge: patched.
  - MCARD: 0x800ad610 measure, 0x800b3ec0 typewriter: patched; 0x800ad7ac asks the
    helper. JOUKA: 0x800dbe24 measure: patched; 0x800dbf8c asks the helper. HAZURE:
    0x800bca44 measure: patched; 0x800bcbac asks the helper. CMENU: 0x800be15c asks the
    helper. CMAIN: none.
  - Name entry (JOUKA 0x800b86f0-0x800b8b98, HAZURE 0x800aeca0-0x800af164) and CMENU's
    name store (0x800a8a4c) handle the ゛ ゜ keys of the kana grids, which really are
    marks; the Latin grid (0x8005e120 + 132) has neither code. Left alone.
  - The name expanders (MAIN 0x8001e5ac, 0x8001e814, 0x8001f0d8; JOUKA 0x800e2468,
    0x800e903c; CMENU 0x800a59c0; CMAIN 0x800a4fd8) turn a stored voiced kana (0xf7 xx)
    into base + mark, and glyph_prepare (0x8001f558) draws a voiced cell only when a
    merge hands it a mark. Only names typed on the kana grids reach them, and those
    don't show as kana anyway: single-byte codes draw English glyphs.
  Found by scanning for the `addiu 0x4a` test and every compare against 0xb6-0xb8. Any
  count the original keeps of sprites to come has to skip marks to be right in
  Japanese, so the scan finds them all. Of the readers of the layer counts, only
  FUN_800d23f4 compares them with a count taken from the text. No English text encodes
  to 0xd8 or above, or to a two-byte code.
- Town text (JOUKA) goes through text_at (0x800dbd7c: x, y, a2, SISETU string, a 5th
  argument on the stack). With the flag at 0x80079772 set, it ignores x and centers the
  line: start = 168 - (W + 12) / 2 for a line W px wide, and clears the flag. The 12 is
  apparently the terminator: the measure skips its 0xff but prices the 0x40 as "th"
  (12 px). It's the same for every line, so centered lines agree with each other, about
  6 px left of 168 (checked: "Not enough gold." 83 px starts at 121, "Which room?" 66 px
  at 129). 0x800dba48 (y, a1, string, a4) sets the flag and
  calls it; that's how the message row (y 0xa6) prints. Many lines are placed at fixed
  x instead, sized for the Japanese, and most of those are columns meant to be left
  aligned. Two weren't: the Inn's "Not enough gold." (SISETU 57), printed at x 0x70
  (お金がたりません, 96 px, 112 to 208) from 0x800c6cd8 and 0x800c7054, so the 83 px
  English line sat 9 px left of the row's center; both now call 0x800dba48
  (`asm/inn_gold_message.asm`). And the Temple's chant, four words drawn one at a time
  at fixed x (`asm/temple_layout.asm`, ours since 4b09b08), which sat 10 px left; its
  positions now center the finished line with a 4 px space between words, and have to be
  redone if a word changes. The Inn's "To the next level, you need N more exp." under
  100 exp is one line at fixed x 28 and 124 (0x800c7c30), left aligned like the
  original; at 100 or more it's two centered lines (2026-10-13).
- The NPC talk runs with MCARD.BIN at 0x800a1000, not MAZE.BIN.
- The dungeon NPC box is 288 px by 3 lines, pages split by `\n\r`.
- The battle box wraps at 24 glyph codes per line. Messages are expanded by 0x8001dfc0
  into 0x8008b400; only the battle call (BATTLE.BIN 0x800d1e20) turns wrapping on. The
  original moves an inserted name that won't fit to the next line, but breaks plain text
  wherever it hits 24, mid-word included, and where that lands depends on the name
  lengths ("Jupiter sweeps Cuautori wi / th LANCE."). `asm/word_wrap.asm` adds a
  lookahead at each space (and each digraph ending in one), so words move whole.
  `fightfit.py` simulates it over every combination of name lengths.
  When a word filled the line exactly, the plain space after it started the next line
  ("Mercury peppers Xicalli with / BLOW GUN.", 2 px right of center; 19 strings could do
  it, found by the play harness, 2026-10-12). An automatic break now skips a plain space
  that follows it (advancing the source pointer); explicit {ff21} breaks are untouched.
  The break before a name went in after the space before the name, which stayed at the
  end of the line, half a space left of center ("Xicalli whips Venus with / vines.";
  16 FIGHTMSG strings could do it). All three automatic breaks now go through one
  routine, `write_break`, which puts the {ff21} over a plain space just before it (every
  caller has a nonzero column, so that byte is on the current line). The room came from
  sharing it: the three inline copies of the {ff21} sequence became one, returning
  through t7, which the original function never uses (2026-10-13).
  A digraph that ends in a space ("s ", "A ", ", " and nine more: 0x8b-0x92, 0xad, 0xae,
  0xb2, 0xb7) is one glyph code with the space drawn into it, so a break after it still
  left that space at the end of the line ("Giant Ant calls for help! A / monster
  appears.", 2 px left of center). The lookahead breaks after such a digraph, and the
  name path breaks after one when a name follows a word like "plays ". `write_break`
  now also rewrites the byte before the break through a 45-byte table at 0x8001e2b0,
  indexed by code - 0x8b: each digraph ending in a space becomes its letter (0x8d "s "
  -> 0x37 "s", 0xb2 "A " -> 0x0b "A"), every other code in 0x8b-0xb7 maps to itself.
  It's one code for one code, so the expander's column, the battle box's per-line glyph
  count and the sprites drawn don't change; the line's measured width loses the space,
  and the measure (MAIN 0x80022024) and BATTLE's drawing read the same buffer. The fix is
  all in MAIN, so no mix of MAIN and overlay builds can disagree about it. Room: the
  name path's check (0x8001e164-0x8001e194) lost two nops and a second lui, so
  `write_break` moved to 0x8001e198 and grew to 22 instructions; the table took the
  name copy's 12 px font and voicing-mark test (0x8001e2b0-0x8001e2df), which
  voicing_marks.asm had made always say no, leaving "count any one-byte glyph below
  0xf8" in three instructions at 0x8001e2a4. 24 FIGHTMSG strings can break after such a
  digraph (`fightfit.py --digraphs`); no event or NPC text can, since only the battle
  call wraps and no explicit line break in them follows one. FIGHTMSG strings without
  `"compress": true` (0, 103, 113, 214, 255, 264-285, 287) are encoded with no digraphs.

### Text buffer

- Dialogue, event and castle strings are expanded whole (every page) by 0x8001dfc0 into
  a buffer at 0x8008b400 before printing. Nothing bounds it, and 16 bytes of live data
  sit at 0x8008b640, so a string that expands past byte 576 has that stretch overwritten:
  measured with filler strings, 557 bytes print whole, and at 625 bytes page 9 shows a
  run of zeros and loses the rest of the line. This is the "random cutoff" in long
  narrator lines in Remisse's notes. Our longest are SISETU 326 (445 bytes), EVENTMES 234
  (424) and NPC_MES4 151 (378). `textbuf.py` holds every string to 544 bytes, leaving
  room for inserted names, and the build stops if one is over.

### Pillar guardians: the box and the dust race

- Answering Yes to "Will you touch it?" at one of the four Grounds pillars runs the
  summon at MAZE 0x800afb34 (only caller: `maze_prompt_result`, 0x800bef20). It opens
  the event box ("The pillar begins to shake ... attacks.", EVENTMES), locks walking
  input (0x800796ab = 1; `maze_walk` zeroes the pad words while it's set, 0x800a9790),
  sets walk sub-state 0x80079878 = 3 and a countdown 0x80079790 = 99.
- Sub-state 3 runs 0x800cc9fc each logic frame (every other frame): count down, animate
  the dust (0x800afc2c: up to 32 particles, spawned with the BIOS `rand()` while the
  count is 2 or more; returns how many are alive), hold the count at 1 while any are
  alive, then sub-state 0 and **0x80079bf1 = 2** (0x800cca4c), the request to start the
  guardian's fight. `maze_frame` picks that up through 0x800c5ca8 / 0x800c5f78, which
  clears the request and the input lock and starts the battle.
- The box closes itself when its text has finished typing (printer 0x80079992 reaches
  0x64; no press needed, and presses don't speed it up). `maze_frame` sees that at the
  top of the frame (0x8001fb4c(6, N, 1) returns 1) and clears the box flag 0x80079838
  **and 0x80079bf1** (0x800a3234, in the delay slot, so on every box close).
- So the two finish independently. If the box closes first, or on the same logic
  frame (the box check runs before `maze_walk`), the cleared byte doesn't matter and
  the fight starts. If the dust ends first, its fight request is wiped one or more
  logic frames later when the box closes. Nothing else ever clears 0x800796ab: the
  game keeps running, the box text stays drawn, and no button does anything. Only a
  reset gets out.
- **Original code, exposed by the English.** MAZE.BIN and the box code in MAIN
  (0x8001fb4c, 0x800224xx) are byte-identical to the Japanese Rev 1 disc. The dust takes
  the same time on both discs; the Japanese text finishes 78-94 frames ahead of it
  (200 RNG seeds at the bird, never negative). The English text is three times as long
  and finishes 84 frames later, which puts it at -6 to +10 frames: 6 of 200 seeds hang,
  about 3% per pillar event (`rips/harness/t3/freeze/race_dist_seeded.jsonl`). The
  message speed setting doesn't change the event box's speed.
- **Fix (applied, `asm/bugfix_pillar_race.asm`; docs/re/bugs.md 1.11):** the dust step
  also waits for the box. Two `nop`s in MAZE.BIN at 0x800cc9fc (s0 = 0x80080000 there):
  - 0x800cca20 `nop` → `lbu a0, -0x67c8(s0)` (the box flag, 0x80079838)
  - 0x800cca28 `nop` → `or v0, v0, a0` (busy = particles alive or box open)

  The count then holds at 1 until the box has closed, and the request is set after the
  clear. No extra space needed. Checked on the built disc: 0 of 200 seeds hang at the
  bird, and at the snake (matched states, old disc against new) 11 of 200 hung before
  and none after. Seeds that worked before start their fight on the same frame; the
  ones that hung now start it 4 frames after the box closes, the earliest the others do.
- MAZE.BIN is read from the disc on entering the maze, after the START menu and after a
  battle. A save state taken in the maze on an older build runs the older code until one
  of those happens.

### Glyph sprite layers

- Each glyph is drawn as a sprite from a pool ("layer"). A screen sets up four layers
  when it opens (0x800db3d0 in JOUKA calls 0x8001f150 per layer; 720 sprites in all;
  table at 0x8008b390: start, size). 0x8001f840 refuses a glyph once its layer is full,
  so text simply stops: there's no error and no wrap.
- Boltac's Trade screens put the shop name and the one-line caption in layer 1, sized 28.
  "Boltac's Trading Post" takes 14, so captions showed only 14 glyph codes ("Choose an
  item to un", "Which weapon i"); the Japanese name is 7. `asm/shop_caption_layer.asm`
  makes it 58, taking 30 from layer 0 (270 -> 240; its peak over every Trade flow is
  130). Measured peaks after the change: layer 1 at most 43.
- The maze's event box opens through 0x80021af0 (x, y, rows, columns), which sizes
  layer 1 at rows x columns, 3 x 24 = 72: one sprite per Japanese character. English
  ran out (48 event strings were cut, e.g. ".........Sure enough, the" at the Shrine
  door). Measured in the real box: spaces count, a line that scrolls off gives its
  sprites back, a new page frees them all. `asm/event_window_pool.asm` doubles the size
  to 144 (the maze reserves 400 for that layer first); `evfit.py` checks any 3 lines in
  a row on a page against it. Test rig: `rips/states/shrine_door.state`, search
  (triangle) at the Shrine door, EVENTMES loaded at 0x801a0400; the expander won't read
  past the original section, so test text goes over an existing string.
- The event box centers each line, counting its spaces. The Japanese pads lines with
  spaces on both sides (often to a common width, so a quote's continuation lines
  indent); padding kept on one side only pushes an English line off center. A page
  break ({ff20}) without {ff26} before it doesn't wait: the page clears at once.
  `scripts/evsweep.py` prints every event string through this box and saves each page.
- The NPC talk box drew a 181-glyph test page whole; `npcfit.py` holds pages to that.
- The town status screen (tavern and Boltac's Inspect, JOUKA 0x800cbec0; the Training
  Grounds' Inspect is another screen and never runs 0x800cbddc) sizes the layers 346,
  70, 190, 114. With START's help on, layer 1 holds the five bold command
  labels (50 glyphs: that font has no digraphs) and the help line, which got the other
  20: "Spells can only be read here, not ca" (2026-10-07, in the play-through).
  `asm/status_text_pool.asm` moves 20 from layer 0 (item list and spell grid: 164 with
  six items, a full eight with two-line names still drew whole) to layer 1, so the help
  line gets 40. The bar shows x = 18-332 with lines centered on 168, so a help line can
  be about 300 px (roughly 35 glyph codes); past that it spills off both ends.
- Most town screens ask 0x800db3d0 for 186, 154, 186, 114: 640 of the 720, leaving 80
  unused, and layer 1 (facility name, menus, the help bar, the tavern's speech boxes)
  ran out first. The Inn's room list is seven lines padded with spaces to line up the
  prices, and every space is a sprite, so with the room help on the bar layer 1 was full
  at 154 and the help lost its end ("Restores all HP for 10000G a"). Nothing in town
  allocates a layer outside 0x800db3d0 (every 0x8001f150 call logged over a crawl of the
  town came from it), so the spare sprites are free to use. The Inn makes no call of
  its own: it keeps the town map's layers (the call at 0x800a34bc, sizes set from
  0x800a3488), as do the King's Chambers and Edge of Town. `asm/town_text_pool.asm`
  has the town map ask for 172 instead of 154: the room list without its help line is
  133 sprites and the bar shows about 39 glyphs. Nothing else on those screens comes
  near 154 (the King's fullest page with its title and caption is 129, packed), and
  every other screen keeps what it asked for. Two earlier versions rewrote the setup
  routine to hand layer 1 all 80 spares (234), then 18 on every screen with room;
  both gave sprites to screens that never use them.
- `scripts/cutsweep.py STATE KEYS` reports lines cut short while KEYS play; a line
  refused at its first glyph is static text being redrawn into a layer it already
  filled (name entry and character creation do it every frame), which is harmless.
- Glyph sprites record their cell: 12 px cells (from v = 0x50, 21 to a row) are the
  regular font, which has the letter pairs; 8 px cells (21 to a row) are the bold font
  of the menu labels and names, which has other glyphs in the pair cells (the status
  screen's "Sort Items", packed, drew as "S∂/I3ms"); 6 px cells are the small font.
  So a string may be packed only if it's only ever drawn in the 12 px font.
- `scripts/castlecrawl.py` walks the town's menus from a save state (every button on
  every screen, breadth first, a screen being the set of live glyph sprites) and logs
  what each screen shows, read back from the sprite pool, since the game only redraws
  glyphs that change. `scripts/castlereport.py` matches each line to its string and
  flags cut-offs, unpacked text in the 12 px font, pair codes in the other fonts and
  lines near the screen edge.
- Boltac's catalog and the Monster Compendium bypass the pool: their glyph-list renderer
  (`asm/catalog_vwf.asm`) fills one GsSPRITE per glyph and sorts it, every frame. The
  Compendium's struct is at 0x800ecaf0 (sorted at 0x800ea120), the catalog's at
  0x800ec998 (sorted at 0x800e335c); x, y at +4, +6 from the screen centre, width at +8
  (12 or 8), tpage at +0xc (0x0f the font, 0x1f kanji), u, v at +0xe, +0xf. Both draw
  14 px right of the struct's x. The crawler watches writes to the struct and logs it
  at each sort; those lines are layer 4 in its output.
- Layers are allocated first-fit from the 720-sprite pool (0x8001f150: size, layer;
  0x8001f428 frees one, or all with -1; 0x8001d164 frees and reallocates one). The table
  at 0x8008b390 is 6 bytes per layer (start, size, 0); glyphs in use per layer are at
  0x80079938, the running total at 0x80079c38. In the maze, layer 0 is 192 at the start
  of the pool and layer 1 follows it at 192.
- The training maze's sign (SISETU 492, shown when you search at it) resizes layer 0 to
  172 at 0x800bef6c in MAZE.BIN, one more than the Japanese text's 171 glyphs. 192 is the
  most it can get without moving layer 1. `asm/training_sign_pool.asm` sets 177, exactly
  what the English takes; `signfit.py` checks it after every build. Test rig:
  `rips/states/training_sign_front.state`, triangle.

### Spell bar

- Inspect Character > Cast Spell shows the highlighted spell's description (STATUS.OBJ
  420-503) in a one-line bar. It prints the first 30 glyph codes and drops the rest; the
  cut is by codes (digraphs count once), not pixels. Remisse's "about 40 characters" is
  this limit. Every current description fits (Wish is exactly 30); `spellfit.py` checks.
- Writing a test string into RAM while a description is on screen and then moving the
  cursor can show only the tail of the text. That's an artifact of editing RAM under a
  drawn string; normal cursor movement, fast or slow, draws correctly.

### Item catalog

- The catalog draws the item's picture, then the description below it, and clips the
  text at about y=220 with no scrolling. ITEM.DAT has 252 pictures at 152x108 (text
  starts at y=129, 7 lines of 13 px) and 55 at 152x152 for polearms, long staves,
  robes, cloaks and full armor (text starts 39 px lower, 4 lines). The Japanese under
  tall pictures never runs past 4 lines. `itemfit.py` checks every description against
  the right limit; found by Chris on the Emerald Robes, 2026-10-04.
- The pictures are stored normal-sized first, then tall, each set in item order, with
  picture 0 a "file not found" placeholder. Description k is item k up to 24 and item
  k+1 from 25 on: entry 24 holds two strings, the Battle Axe's, then after its {ff40} terminator the
  Nunchaka's (item 25). The game shows each on its own.
- Only JOUKA.BIN (the castle-town overlay, loaded at 0x800a1000) reads these pictures:
  the shop catalog and its detail screen. The card game has its own copies
  (CB/DAT/ITEM_S.DAT and ITEM_L.DAT, the same 252 + 55 split).
- 0x800de244: the item's picture entry has bit 0x8000 for tall; tall pictures load from
  sector 0x8dc + 12n, normal ones from 9n, through 0x800e3dcc. The a2 passed there
  (0x4c/0x36) is only the upload strip size. The upload takes width and height from
  the TIM header, so a shorter TIM displays cleanly.
- 0x800deb1c (JOUKA.BIN 0x3db1c): the description's y is a fixed base plus tall × 39,
  built as ((s3 << 2) + s3) << 3 − s3. `subu v0,zero,s3; andi v0,v0,N; nop; nop` sets
  the tall offset to N. The parchment ends at y=227; text starts at y=129 + offset, in
  13 px lines.
- Tested 2026-10-04 (emulator, six items): offset 26 with the pictures cut to 139 rows
  shows a full 5th line under tall pictures, no overlap, normal items unchanged.
- Chosen 2026-10-04: offset 30 (`asm/catalog_tall_text.asm`) and pictures cut to 143
  rows (`scripts/itempics.py`, run by build.sh): 16 trimmed, 11 moved up, 28 shrunk
  (1-9%). Each picture is a copy of the panel's parchment with the item on it, so only
  the item is moved or scaled and it goes back onto the bare parchment
  (`graphics/item_panel_bg.png`); scaling the whole picture misaligned the texture.

### Battle text and monster files

- Monster data sits in DATA02/M_DTnnn.BIN at 0x10280 (in RAM, 0xd0-byte records from
  0x8008a918). Each of up to three attacks has a u16 noun at +0xac/+0xb6/+0xc0 and a verb
  byte two bytes later.
- BATTLE.BIN adds 427 to the noun; if the result is 2000 or more it subtracts 2000 and
  sets a flag. The result indexes I_NAME_E.OBJ, whose strings 427-938 were never
  localised in the English-mode file: 428-557 mirror the item list, 558+ are natural
  attacks (claws, fangs, stinger). The verb indexes FIGHTMSG.OBJ.
- An attack whose noun is 0x100 or more is an ability, not a blow: `monster_attack_roll`
  (0x800aaed0) casts the spell in its +6 byte the way an item is used, with the verb byte
  as the message ("tries to lull a strange dance", FIGHTMSG 214 through
  `battle_message_build`'s mode 5). Because it goes through the item path, silence
  doesn't stop it. The Nightmare's and the Merry Puppet's attack 2 is [19, 1, 46, ...]:
  the dance is Katino. `monster_melee` (0x800aaa04) picks attack 1 on rand(100) > 68 when
  it's usable, else attack 0, so a fighting Nightmare dances about a third of the time
  on top of its 45% Katino column. (Agent 9, 2026-10-14, from the n1v1 chapter 8 fight:
  92 Katino casts and dances in 19 rounds.)
- In a battle, the current group's monster record is at 0x801b0680 (in
  rips/states/battle_wriggle.state).
- `battleshow.py` renders any template/verb/noun combination in the real battle box, with
  `--monster NAME` to try other name lengths.
- NPC parties fight as monsters. The encounter loader (0x80021268) loads the enemy file
  as table 1 index id+0x2c; NPC parties use id 379+n, which is DATA02/NPTnn.BIN. Their
  member records sit at the end of the file in the monster layout, with katakana in the
  English name slots too. `nptnames.py` writes the patches in `binary/`, and `nptshow.py`
  forces a fight with any party to check the enemy panel.

### Card battle

See `scripts/cardref.py`'s header for the CMENU.BIN tables (passwords, Lv 1 templates,
EXP scale, Option bonuses, unit records) and `docs/cheats.md` for the card stock in RAM.

### Settings

- The Configuration settings are bytes at 0x80096378: Item, Monster and Spell Names and
  Status (0 = Japanese, 1 = English), Sound Output (1 stereo, 2 mono), Music, Effects,
  Sound Effects (1 = on), then message speed at +8. A save holds 12 bytes from here
  (MCARD.BIN copies them in at 0x800aae88 and 0x800acbb4).
- Three settings screens change them: Edge of Town (HAZURE.BIN, toggles at 0x800ac5a8),
  the maze's camp (MAZE.BIN, 0x800d9cb8) and a card battle's SELECT screen (CMAIN.BIN
  0x800aa904, through a spinner at 0x800adafc given min, max and steps on the stack).
  A card battle packs the eight bytes into the bits of 0x8008a260 (+1 is the speed)
  when the screen closes and unpacks them when it opens.
- The language switches are zeroed in system init, New Game (english_defaults.asm) and
  a reset in MCARD.BIN (0x800ad250). `asm/english_only.asm` keeps them on English
  everywhere above.
- Byte 9 is a card game flag (CMAIN writes it at 0x800b33b8 and 0x800b33e8). Bytes 10
  and 11 are unused: no code file reads or writes them except the save copies, which
  pack all 12 bytes into the save image (at +0x1eb5) in MAZE 0x800e5f34, JOUKA
  0x800dab10, HAZURE 0x800bc008 and MCARD 0x800aa518 and 0x800b26cc. MAIN's startup
  (0x80032200) zeroes 0x800795b8-0x800a0baf, so they're 0 at power-on. A 1 written to
  byte 10 survived Suspend Game and Load Data from a cold boot (emulator, 2026-10-13).
- The Edge of Town and camp screens are the same code (HAZURE 0x800abbd4, MAZE
  0x800d9304). The names come from a table of ten (x, y, string) halfwords (HAZURE
  0x800a10a8, MAZE 0x800a1cbc: STATUS.OBJ 61-69 and 75), drawn once on layer 0 when the
  screen opens. The options are drawn row by row in straight-line code on layer 1 at each
  cursor move, the unchosen one dimmed by 7 in 0x80079760. The cursor byte (HAZURE
  0x80079c5c, MAZE 0x80079c5a) runs 0-8, 8 being Done; screen row 6 (Sound Effects) is
  byte 7 and row 7 (Effects) byte 6.
- STATUS.OBJ 70-74 and 76-80 are Configuration labels the final game doesn't draw: Help
  Messages, Message Speed, Autosave, View (視点) and Status Bar display, and option
  strings including (常時表示／セレクトボタンで表示) and (1 2 3 4 5 止まる). No code that
  draws them was found. `docs/re/cursor-frame.md` ("Corner brackets: the full spec") has
  the details and a sketch that adds a row using byte 10.
