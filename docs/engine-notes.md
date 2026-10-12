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
  writing to RAM.
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

### Wipes and bodies (A-maze.md §4-6, D-battle.md, fallen-parties.md)

- **A wipe** deletes anyone Lost, halves every member's gold, and rolls one member's
  items for destruction six times over (2 in 3 per roll for rare items, the Tablet of
  the Sun among them; 1 in 4 for the rest). That's a bug: the loop should go over each
  member (bugs.md 3.1, left as is pending Chris's decision). Outside the Training Maze
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
- **Sales** are sets of three items at one price (5 to 20,000 G), chosen by
  `progress_bits`; some of the items are cursed.
- **The rescue.** Guy's, Balbo's and Fontana's parties offer it; Cresson's and Zaril's
  never do. A party counts if every member is paralyzed or worse. On yes, one such party
  goes back to town, still dead, and the NPC party takes a fee from each member: Guy all
  the gold; Balbo every item (all ten slots, equipped and cursed ones too); Fontana half
  the gold and the items in slots 1, 3, 5, 7 and 9. The gate (`progress_bits` & 0x1e)
  is open from the first trip into the Grounds.
- **Bugs and cut content.** C found a dozen. The clear bugs are fixed (bugs.md group
  1). Of the cut-looking ones, Zaril's healing (9135ef5) and Guy's and Fontana's
  re-introductions (7498b1c) are reopened, the identify service stays unused, and the
  rest wait on Chris (decisions.md).
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

### Records (G-records.md)

- The character record's fields (status bits, age, stats, the pack's flag bits:
  sub hand, main hand, equipped, identified, cursed), the item table (restrictions,
  curse, break chance, price, stock, AC, to-hit, damage, swings, slaying, battle spell),
  monster records, race and class tables, the seven EXP tables, HP dice, spell points
  and learning, level-up stat rolls and death of old age.

### Bugs, descriptions and open decisions

- `docs/re/bugs.md`: every bug found, in three groups. Group 1 (ten clear bugs) is fixed
  in `asm/bugfix_*.asm`.
- `docs/re/description-check.md`: item, spell, Compendium and help text checked against
  the records and the code (18 spell ranges in the original are wrong).
- `docs/re/decisions.md`: what's waiting on Chris.

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
  Still open, no room left in the two areas: a break before a name leaves the space
  before the name at the end of the line, half a space left of center ("Xicalli whips
  Venus with / vines.", 4 of 187 wrapped messages in a run).

### Text buffer

- Dialogue, event and castle strings are expanded whole (every page) by 0x8001dfc0 into
  a buffer at 0x8008b400 before printing. Nothing bounds it, and 16 bytes of live data
  sit at 0x8008b640, so a string that expands past byte 576 has that stretch overwritten:
  measured with filler strings, 557 bytes print whole, and at 625 bytes page 9 shows a
  run of zeros and loses the rest of the line. This is the "random cutoff" in long
  narrator lines in Remisse's notes. Our longest are SISETU 326 (445 bytes), EVENTMES 234
  (424) and NPC_MES4 151 (378). `textbuf.py` holds every string to 544 bytes, leaving
  room for inserted names, and the build stops if one is over.

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
- The town status screen (Training Grounds and tavern inspect, JOUKA 0x800cbec0) sizes
  the layers 346, 70, 190, 114. With START's help on, layer 1 holds the five bold command
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
