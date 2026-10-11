# Engine notes

What we learned about Wizardry: Dimguil (SLPS-02691 Rev 1) while translating it, beyond
Remisse's notes in `findings.md`. Addresses are RAM unless a file is named. Commit messages carry
more of the detail behind each item.

## Loading files

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

## Overlays and the main loop

Mapped on 2026-10-11 while setting up the decompiler; the full map is in `code-map.md`.
Confirmed by code read of `main` (0x800114d8) and by matching 23 RAM dumps against the
overlay files, unless marked inferred.
- Seven overlays share 0x800a1000: MAZE, BATTLE, MCARD, JOUKA, HAZURE, CMAIN, CMENU.
  `load_file` (0x80012d18) loads one: table 0 index 172 JOUKA, 173 BATTLE, 174 HAZURE,
  175 MCARD, 178 MAZE. The card game's CMAIN and CMENU are loaded by name through
  DsSearchFile (0x800241f8), though table 0 lists them too (176, 177).
- `main` loads MAZE at boot and loops. A request in `game_mode` (0x8007967e) makes it
  load the overlay that mode needs (1 and 4 MAZE, 2 BATTLE, 3 JOUKA, 5 HAZURE, 6 the
  card game, 7 and 9 MCARD), record which one in 0x800798b3, and set `game_state`
  (0x80079a13), which picks the overlay routine called each frame.
- Every NPC talk runs in MCARD. In talk state (0x35) `main` calls one of 23 handlers
  picked by 0x80079797: 0 Guy (0x800b5694), 1 Balbo (0x800c7264), 2 Fontana
  (0x800cf8c0), 3 and 4 inferred to be Cresson's and Zaril's parties (0x800d65c8,
  0x800d9b34), 6 to 0x17 the rest (listed in code-map.md).
- A smaller overlay leaves the previous one's tail in RAM, and two depend on it. BATTLE
  calls seven of MAZE's routines at 0x800ee5f4-0x800ef0cc (about 40 call sites), so
  battles need MAZE underneath, and a patch to MAZE above 0x800db028 changes battles too.
  HAZURE calls JOUKA's 0x800d9130 (from 0x800afa9c); the outskirts RAM dump has JOUKA's
  tail under HAZURE. MCARD runs over MAZE's tail in talks but calls nothing past its end.
- The executable calls overlay routines at fixed addresses, valid only while the right
  overlay is loaded. One of them, 0x800c76f0, falls in the middle of Balbo's talk
  handler in MCARD, so it belongs to another overlay.
- `$gp` is 0x80079538. `rand_upto` (0x8001cb18) keeps its state at 0x80079558 and
  0x8007955c.

## Text printer

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

## Text buffer

- Dialogue, event and castle strings are expanded whole (every page) by 0x8001dfc0 into
  a buffer at 0x8008b400 before printing. Nothing bounds it, and 16 bytes of live data
  sit at 0x8008b640, so a string that expands past byte 576 has that stretch overwritten:
  measured with filler strings, 557 bytes print whole, and at 625 bytes page 9 shows a
  run of zeros and loses the rest of the line. This is the "random cutoff" in long
  narrator lines in Remisse's notes. Our longest are SISETU 326 (445 bytes), EVENTMES 234
  (424) and NPC_MES4 151 (378). `textbuf.py` holds every string to 544 bytes, leaving
  room for inserted names, and the build stops if one is over.

## Glyph sprite layers

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

## Spell bar

- Inspect Character > Cast Spell shows the highlighted spell's description (STATUS.OBJ
  420-503) in a one-line bar. It prints the first 30 glyph codes and drops the rest; the
  cut is by codes (digraphs count once), not pixels. Remisse's "about 40 characters" is
  this limit. Every current description fits (Wish is exactly 30); `spellfit.py` checks.
- Writing a test string into RAM while a description is on screen and then moving the
  cursor can show only the tail of the text. That's an artifact of editing RAM under a
  drawn string; normal cursor movement, fast or slow, draws correctly.

## Item catalog

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

## Battle

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

## NPC conversations

Partly traced on 2026-10-06, to find what decides which NPC lines play. Addresses are in
the maze overlay as loaded during a talk.
- A talk runs as a small script. 0x800c154c builds it on the stack, 43 blocks of 40
  halfwords, mostly constants with a few values filled in from globals (0x8007969a,
  0x800796ed, 0x800796e4, 0x800795d6, 0x80079c6c, 0x80079a5a), and copies it to
  0x801ff118. The interpreter at 0x800b8ccc reads the opcode at the script position
  (halfword index at 0x80079a26) and dispatches through a 13-entry table at 0x800a1cc4,
  for opcodes -1 to 11.
- Opcode 2 prints NPC string N (the next halfword) through 0x8001dfc0 from the file at
  0x801a0400; -2 and -3 variants insert a character's name. Opcode 6 loads a portrait.
- Opcode 0 sets a bit (0-19) in bytes +0xc6..+0xc8 of each of your party's roster
  records (0x8007d708, 0xd0 bytes each). So "have we met them" is remembered per
  character, not globally: a new character in your party gets the unnamed greetings.
- Not yet found: what picks the block for a talk topic (News and the rest), and so
  which progress state gates those lines. The first meeting with Guy at the first door
  is a scripted event and never reaches the talk menu. Forcing an NPC party through
  the battle loader (nptshow.py's trick) starts a fight, not a talk; the friendly
  encounter goes through another path that hasn't been found.
- Save states from before a build that moved files read the NPC files from the old
  sectors and show blank boxes. Copying the four file tables (0x80051760-0x80052700)
  from the built SLPS_026.91 into RAM after loading fixes that.

### Body recovery by NPC parties

Traced on 2026-10-10 to settle what Balbo's offer (NPC_MES2 142-145) does. All of it is
a static code read of the talk overlay in a RAM dump taken during a talk with Guy
(`rips/probe/ram_talk94.bin`; the same bytes are in ram_t, ram_hit and ram_w), unless
marked otherwise. Nothing here was run in the emulator: meeting Balbo's party with a
wiped party of your own in the maze needs a state nobody has made yet. Work files are
in `rips/probe/bodies/`.

The offer is real, and it's about your own characters. When Guy's, Balbo's or
Fontana's party meets you and another of your parties lies wiped out in the maze, the
leader can offer to carry it back to town. Say yes and every member of one wiped party
goes back to town, still dead, and the NPC party takes a fee from each of them. The fee
depends on the party:

| Party | Handler | Script | Fee from each rescued character |
|---|---|---|---|
| Guy (NPC_MES1 163-166) | 0x800b5694 | 0x800a1c28 | all gold (+0x1c set to 0); items kept |
| Balbo (NPC_MES2 142-145) | 0x800c7264 | 0x800a4e28 | every item (all ten slots emptied); gold kept |
| Fontana (NPC_MES3 151-154) | 0x800cf8c0 | 0x800a68b4 | half the gold (+0x1c shifted right by 1) and the items in slots 1, 3, 5, 7 and 9 |

The fees match what each leader says on "yes". Guy's いただけるところから,いただきますから
is "we'll take what we can from where we can", Balbo's line says that lot had fine
gear, and Fontana's says he won't do you wrong. Cresson's and Zaril's parties have the
"rescue our companions" log line (4:165, 5:116) but no offer string and no recovery
code, so they never offer. That last part is inferred from the absence of both.

Confirmed by code read:
- Each party's talk has its own large handler, a state machine with a static script
  copied to the stack. Balbo's handler copies 0x800a4e28 to sp+0x16b8 (0x800c8748),
  Guy's copies 0x800a1c28 to sp+0x3d48 (0x800b5a10) and Fontana's copies 0x800a68b4 to
  sp+0x1ed8 (0x800d0610). Each handler's yes/no code later runs its own copy. The
  other big-frame functions (0x800bff60, 0x800c154c, 0x800c2564, 0x800d65c8,
  0x800d9b34) are probably the other parties' handlers or shared talk code. They
  aren't mapped yet.
- Static talk scripts are runs of 15-halfword (30-byte) blocks. Block 0 is the main
  script, block 1 runs on "yes" and block 2 on "no". The handler selects one by storing
  0, 1 or 2 in 0x80079bb4 and calling the interpreter on stack copy + 30 × that value.
  Balbo's is `6,4,0,4,109 3,4,0,109 2,142 7,143 -1`, then `3,4,1,109 2,144 -1`, then
  `2,145 -1`.
- Opcode arguments, read from the scripts and handlers: 6 takes 4 (portrait), 3 takes
  3 (inferred: the speaker's face), 2 takes 1 (print string N; -2/-3 variants add a
  name), and 7 takes 1. Opcode 7 (0x800b9220) prints string N in the bottom bar
  through 0x800b3c40(0xa6, 6, N, 1). That's how the yes/no question (143) and the topic
  log lines ("We asked them who they were", 7,302 in Guy's runtime script) show. 9
  takes 1 and follows each healing line (inferred: which cure). Opcode 1 (0x800b8e9c)
  sets 0x800798a4 = 10, and opcode 3's slot (0x800b8ec8) sets 0x800798a4 = 15.
  Opcode handlers by table slot: -1 and 4 → 0x800b9598, 0 → 0x800b8d40, 1 → 0x800b8e9c,
  2 → 0x800b8ed8, 3 → 0x800b8ec8, 5 → 0x800b9190, 6 → 0x800b9004, 7 → 0x800b9220,
  8 → 0x800b9338, 9 → 0x800b93f8, 10 → 0x800b944c, 11 → 0x800b9464.
- When the offer is made (Balbo's handler, 0x800c9354-0x800c9508; Guy's and Fontana's
  have the same scan near 0x800b6544 and 0x800d10e8). The handler walks the 20 party
  records at 0x8008f8c8, 54 bytes each: +0 an id (-1 = unused), +1 the member count,
  +2..+7 roster indexes (-1 = empty). A party is a candidate if it's in use, isn't the
  party you're walking with (the id in 0x8007e810), and every member's roster
  halfword +0x0e is 0x20 or more. Candidates go in the list at 0x8008d300, with the
  count in 0x80079895. If any of bits 1-4 of 0x8007986c are set and the count is above
  0, a coin flip (0x8001cb18(1) == 0) decides whether the leader opens with the offer
  (state 0x41). Otherwise the talk goes on as usual (state 0x28).
- The yes/no (state 0x42): 0x800b0614 reads the pad and the two-option cursor at
  0x80079c5a. It returns 4 or 2, inferred to mean confirm and cancel. A 4 with the
  cursor on the first option is yes. A 4 on the second option, or a 2, is no. On yes the handler picks one candidate at random,
  0x8001cb18(count - 1) into 0x80079895. For each of its members it sets roster +0x7a
  to 0xff (back in town) and takes the fee (Balbo: 0x800cac68-0x800cad64; Guy:
  0x800b7e88-0x800b7f3c; Fontana: 0x800d23c4-0x800d24dc). Nothing in these loops
  touches the status at +0x0e. So the bodies arrive in town as they were, and the
  Temple still has to raise them.
- 0x8001cb18(n) is the random number routine (state in 0x20($gp) and 0x24($gp)). It's
  called all over the talk handlers.
- Fontana's version also walks your current party afterwards (count at 0x80079891),
  calling 0x800b3cb8 and 0x800b1ddc for each member. Inferred: it redraws the panel.

Roster record fields learned along the way (0x8007d708, 0xd0 bytes each; see also
`docs/cheats.md`):
- +0x0e, u16: status. 0 for healthy characters (RAM read in several states). The
  offer treats 0x20 and above as dead; the exact values for dead, ashes and lost
  aren't mapped yet (inferred).
- +0x1c gold (u32) and +0x20 ten item slots (u16, 0xffff = empty). Already known;
  the fees above use them.
- +0x34..+0x3d: one byte per item slot. The fee code sets it to 0xff when it empties
  a slot. Inferred: a per-slot state, such as equipped, cursed or identified.
- +0x7a: where the character is. 0xff means in town (RAM read: everyone in town has
  0xff, and characters in the maze with you have 0x00). +0x7b and +0x7c are x and y,
  +0x7d is the facing. Code read: 0x800afd88-0x800afe5c and two copies
  (0x800b0280, 0x800b2250) write the current area (0x80079668), x (0x80079906),
  y (0x80079916) and facing (0x80079b34) into +0x7a..+0x7d for each member of a party.
  That's where a party is left in the maze. Inferred: area 0 is the first area.
- 0x800aed90-0x800aee3c compares each candidate's +0x7a..+0x7c with the square you're
  standing on. Inferred: that's the player's own body search, finding a wiped party on
  the current square.
- 0x800ad2c0 sets +0x7a = 0xff for six records and clears a 32-byte table at 0x8008c4d0.
  Inferred: a reset or new-party path.

## Card battle

See `scripts/cardref.py`'s header for the CMENU.BIN tables (passwords, Lv 1 templates,
EXP scale, Option bonuses, unit records) and `docs/cheats.md` for the card stock in RAM.

## Settings

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
