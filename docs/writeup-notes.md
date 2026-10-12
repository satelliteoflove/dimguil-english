# Notes for a writeup: what was hard, and how it was solved

Raw material for a later writeup of the project. These are notes, not prose: what
went wrong or got in the way, how it showed up, what the cause turned out to be, what
fixed it, and the numbers. The writeup itself is Chris's to write. Add new entries as
they come up; the commits named here have the detail.

## The game's text limits

Each of these was a limit sized for Japanese that English ran into. Almost none of
them gave an error: text just stopped, vanished or came out wrong.

**Event text silently dropped (2026-10-04, d7b4e6d, 250cf32).**
- What happened: a test build went out with every event message still in Japanese.
- Cause: the event review had pushed EVENTMES.BIN 326 bytes past what the encoder
  allowed. The encoder printed "[ERROR] ... Ignoring translations." and carried on, and
  the build script only grepped for errors without stopping. The file's own checker
  had been comparing against the wrong number (the section length, 25,721) so it
  always said "over" and nobody believed it.
- Fix: the file sits in 14 sectors with 1,049 bytes of slack after it, and the game
  loads all 14 (checked by hijacking a loader in the emulator), so the encoder may use
  the slack. The build now stops on any encoder error. Lesson recorded as a rule: never
  publish a build until its whole log has been read and the result checked in the game.

**The "random cutoff" in long narrator lines (2026-10-04, 98aec10).**
- Seen: Remisse (the earlier patch's author) noted long lines cutting off at random.
- First theory, disproved: file growth.
- Cause: the game expands a whole string, every page of it, into a buffer at
  0x8008b400 before printing, and live data starts 576 bytes later. Anything past byte
  576 gets overwritten. Measured with filler strings: 557 bytes print whole; at 625,
  page 9 shows zeros where bytes 576-592 were.
- Fix: no code change needed; every string is held to 544 bytes (32 spare for inserted
  names) by `textbuf.py` in the build. The longest today is 445.

**Text drawn one sprite per letter (2026-10-04 and 05, f5d4e8f, 6dc52dd).**
- How the game draws text: every glyph is a sprite taken from a pool, and each screen
  splits 720 sprites into four pools when it opens. When a pool runs out, the text
  simply stops. No error, no wrap.
- Boltac's Trade screens: captions showed only their first 14 glyphs ("Choose an item
  to un", "Which weapon i"). The shop name and caption share a pool of 28, and "Boltac's
  Trading Post" takes 14 where the Japanese name took 7. Found by Claude while checking
  Remisse's cut-offs; Chris hadn't noticed it in play. Fix: that pool 28 -> 58, taken
  from one with room to spare (its measured peak was 130 of 270).
- The event box in the maze: Chris found ".........Sure enough, the" at the Shrine door,
  the very start of the game (the line ends "the door won't open."). The window routine
  sizes its pool as rows x columns, 3 x 24 = 72, one sprite per Japanese character. An
  English line of the same width takes up to about 35 glyphs. A scan found 48 event
  strings cut somewhere. Measured in the real box with test strings: spaces count, a
  line that scrolls off gives its sprites back, a new page frees them all. Fix: one
  instruction doubles the pool to 144; the game already reserves 400 for it, so nothing
  else loses room. The checkers now count glyphs, not just pixels.
- The NPC talk box drew a 181-glyph test page whole; the busiest real page uses 93.

**Japanese voicing marks in English text (2026-10-07, 9a955ba).** Chris saw "satisfyin  click."
at the training maze switch. Glyph 0xb6 is `"` in our font but the voicing mark ゛ to the
game, and 0xb7 is the digraph "w " but ゜. The printers look one glyph ahead and, on a
mark, draw the current glyph's voiced form instead. The NPC box only does it after
kana-like codes, so the earlier fix was a rule (no `"` inside a line) and a checker. The
event box does it after anything, and the event review had been rendered in the NPC box,
so it never showed: 91 event strings had a merge, including every "how " and "now ".
Turning the merge off in the event printer and in the six overlay copies of the helper
fixed them all, plus one NPC line the rule had missed ("blew" is "le" + "w "). Lesson:
render in the real box, not a stand-in.

**The training maze sign (2026-10-07, ec26800).** Found in the recorded play-through:
the sign's text stopped at "but as a b". The maze code sizes that box's glyph layer to
172, one more than the Japanese text's 171 glyphs; the English needed 207. Tracing the
layer calls back from the allocator found the constant. The layer can grow to 192
before it would run into the next one, so the fix was half code, half wording: Chris
reworded it to 177 glyphs and the layer gets exactly 177, leaving the rest free.
`signfit.py` reads the size back out of the built MAZE.BIN, so the check can't drift
from the patch.

**The spell bar (2026-10-04, 6cc6966).** The one-line spell description bar prints the
first 30 glyph codes and drops the rest, counted by code, not by pixel. All 84 fit;
`spellfit.py` keeps it that way.

**The item catalog (2026-10-04, 7e46b2f, 6d26caf, 92513dc).**
- Descriptions are 144 px wide, 7 lines under most pictures but only 5 under the 55
  tall ones (after moving the text up; 4 before).
- One catalog entry turned out to hold two items' descriptions separated by a
  terminator (the Battle Axe and the Nunchaka), so from item 25 on, description k
  belongs to item k+1. The fit checker had been counting both as one and reporting a
  problem that wasn't there.
- Letter spacing (2026-09-25, 249f928). The catalog, the Monster Compendium and the
  card game draw text with a different renderer, which spaces each glyph by a width
  field sized for kana, so single letters were spaced like letter pairs ("W ea p on
  s"). Its advance now comes from the main text engine's width table
  (asm/catalog_vwf.asm).

**A quote mark that turns into Japanese (2026-09-25, 9713e23).** Glyph 0xb6 is `"` in
the English font, but it's also the Japanese voicing mark, and the printer merges it
into the glyph before it. After certain letter pairs whose code doubles as a kana
(`y ` is フ), a mid-line `"` prints as ブ. Only quotes that open a line are safe; quotes
inside a line use `'`, and `npcfit.py` catches the rest.

## Working without reading Japanese

- Chris doesn't read Japanese. Each line was shown literally, sentence by sentence,
  with its cultural context, and then a natural rendering. Scenes were reviewed with
  Chris one at a time, and every approved scene was its own commit.
- A plain dictionary wasn't enough. JMdict, the standard free one, gives あの人 only
  as "he, she, that person". It misses the sense that carries Rosea's line: a woman
  speaking of her husband or lover (Daijisen; English Wiktionary has it). The answer
  was to put researched, cited word notes first, with a confidence level, and the
  dictionaries second.
- Role language (役割語, Kinsui Satoshi's term): おぬし, じゃ, かしら and the like tell a
  Japanese reader at once what kind of character is talking. Each character got a
  voice sheet before translation, and the review tool explains these markers word by
  word.
- The terminal was a blocker for review (2026-10-04, 651c96a). Reading a scene line by
  line in chat made it hard to get a feel for the whole. That led to a browser tool:
  the whole scene in Japanese, Literal, Current and Faithful, a compare view with the
  changes marked and the reason for each, word notes and dictionaries on hover and
  click, and every line drawn in the game's own font on the real text box, with the
  fit checks live as you edit.
- The game's font in the browser: drawn by the game itself. Every glyph was printed in
  the real dialogue box in the emulator, and each page was shot twice, with and
  without the text. The pixels that differ are the glyphs, so the see-through box
  background drops out.

## Line breaks

- Our NPC lines are broken the way the Japanese is: a sentence or clause per line, and
  never ending a line on "a", "the" or "to". A greedy fill-the-line rewrap didn't match
  that (Chris noticed in the tool). The rewrap now breaks at sentence ends first, then
  commas, then evenly. Run over all 1,052 NPC strings, it reproduces 840 of the
  hand-broken ones (e575437).
- The game centers event text and left-aligns NPC talk under the speaker's name, as in
  the Japanese.

## Testing in the emulator

- A headless libretro frontend (`scripts/emu.py`) on a patched Beetle PSX core, with
  breakpoints, memory watches and code coverage, drove almost every measurement here.
- To test text in a box you can't easily reach, the file is rewritten in RAM as the
  game loads it, so the box prints test text. Pitfalls that cost time:
  - the disc load is still running when the file's header appears, so the test text
    has to be written again for a while after
  - the expander won't read past the file's original length, so test text goes over an
    existing string
  - event pages need their wait code or nothing prints
- Save states keep the old text and file tables, so states are remade after any build
  that moves files, and a code fix can be tested in an old state by writing the
  patched instruction into RAM.
- The event box sweep (2026-10-07). Event text had been screen-checked in the NPC box,
  which is a different box. `evsweep.py` overwrites the Shrine door's text in RAM with
  each event string in turn, presses search, and saves the box every time it settles
  (each {ff26}), then presses circle. 317 strings, 492 pages, about five minutes on 10
  cores. No page was cut off and none filled the glyph layer. It found 26 strings
  printing off center: the box centers each line with its spaces, and the English kept
  the Japanese padding on one side only.

- Cut-off help lines on the status screen (2026-10-07, found in the first play-through
  session). The bar under a character's stats stopped after 20 glyph codes. It shares a
  70-sprite glyph layer with the five bold command labels below it, which take 50
  because the bold font has no letter pairs. Each screen splits a 720-sprite pool four
  ways in its own code, so the fix moves 20 sprites from the layer holding the item list
  (peak about 230 of 346) to the bar's, 40 for the help line, about what the bar's
  300 px can show (asm/status_text_pool.asm). The Sort help line had
  been left unpacked, apparently copied from the label before it, and is now packed (36
  glyph codes to 22). scripts/cutsweep.py finds such cut-offs in the harness.
  Shots: docs/shots/status-help-line/.

- The town sweep (2026-10-08). After three kinds of help-line trouble (untranslated,
  cut by glyph count, spilling past the bar), every town screen got checked by machine.
  `castlecrawl.py` presses every button on every screen reachable from a save state,
  breadth first, and reads what's on screen back out of the glyph sprite pool (the game
  only redraws glyphs that change, so the draw calls alone show half-lines). Each
  sprite's texture cell gives its glyph code and its font. `castlereport.py` matches the
  lines to the script. About 3,000 screens from 12 start states (party with gold, dead
  and stoned characters at the temple, a character about to level up at the Inn,
  character creation past the name), about half an hour on 16 cores. The card game and
  the Monster Compendium draw their text some other way and aren't covered.
  Found: the Inn's room help lines all cut short ("Restores all HP for 10000G a"),
  because the room list's padding spaces are sprites too and filled the layer; most
  town screens leave 80 of the 720 sprites unallocated. The first fix handed the main
  text layer all 80 on every town screen; Chris pointed out a line the screen can't
  show more than ~39 characters of has no use for 70+ more sprites. The second gave
  every screen 18 more; Chris asked why screens that don't need any should get them.
  Measuring per screen settled it: only the Inn's room list goes over (159 of 154; the
  Fortune Teller's 157 had been measured before the town text was packed, and is 104
  now). The Inn keeps the town map's layers, so the one change is the town map asking
  for 172 instead of 154 (133 for the list, 39 for the bar), and the setup routine is
  the original again (asm/town_text_pool.asm). Shots: docs/shots/inn-help-line/. Change Name opened the
  keyboard on hiragana (its own open path still zeroed the character set); shots:
  docs/shots/change-name-keyboard/. 55 strings drawn in the regular
  font were never packed: shop help lines, the recruits' and fortune teller's speeches,
  the King's, the Inn's level-up lines, the temple's chant; packed now. The longest town
  string went from 445 bytes to 305. Also learned the hard way: the bold label font has
  other glyphs where the letter pairs are, so "Sort Items" packed drew as "S∂/I3ms".
- The settings screen's names were placed for Japanese: a table of (x, y, string) per
  line, with x right-aligning 12 px characters at x = 160, so the English was ragged on
  both edges and "Spell Names" ran into its "(". Every name now starts at x = 80
  (asm/config_layout.asm; the table is in HAZURE.BIN and again in MAZE.BIN). Which
  "Sound" switch did what was settled by ear, so to speak: the emulator harness now
  collects the sound, and the RMS level with each switch off showed サウンドの有無 is
  the music. Shots: docs/shots/settings-name-layout/ (the after also shows "Music").
- English only. The settings let a player switch item, monster and spell names (and the
  status words) to Japanese, which the English font, having taken the kana's place,
  drew as a jumble. Keeping Japanese working would have meant a second font in VRAM and
  every text routine taught to switch, so the patched game is English-only instead
  (asm/english_only.asm). Finding every way the switches could change took a write
  watch on the four bytes: three settings screens (the card battle's goes through a
  generic spinner, so "Jpn" got a minimum of 1 rather than a skipped branch), two save
  load paths, a reset in the memory card overlay, and the card game's own packed copy,
  which it unpacks each time its settings screen opens. Tested by saving with the
  switches on Japanese: the published build loads that card in Japanese, the new one
  in English. Shots: docs/shots/jpn-lock/ (the garbled "Jpn" catalog, then "Jpn" dimmed
  and unmovable on all three settings screens).
- The card game crawl. The card menus and battles draw their text with their own
  copies of the glyph-list renderer (CMENU.BIN 0x800a6a5c, sprite at 0x800c1650;
  CMAIN.BIN 0x800a6074, sprite at 0x800cd180), so castlecrawl now arms those sites
  whenever the overlay is loaded. Roots: the test save, a party formed at the tables,
  a four-card party, and a Rank E battle. Menus are crawled; battles play on AUTO while
  a watcher logs each new line (menus don't move a battle along). Found: the level-up
  arrow drew as "A". The font's arrow cell had become the letter pair "A ", and both
  the code table and the card game's Shift-JIS converter still sent "→" there. The
  original arrow went into a blank cell. Fixing the code table alone changed nothing
  on screen: this arrow is a Shift-JIS string in CMAIN.BIN, so it now reads "_",
  which the converter maps to that cell. The first pick, 0xb8, broke the build: the shop's "∞" (ITEM.DAT 39, left
  untranslated) draws there as a blank, so it went into 0xb9, which no text uses and
  no code loads as a glyph. Shots: docs/shots/card-levelup-arrow/. Also found: the
  battle's per-card mode labels ran together ("MANUMANUMANUMANU"); the label shared the
  menu's "AUTO" string, so "AUT" went into the 8-byte "MANU" slot beside "MAN" and the
  AUTO case points there. Shots: docs/shots/card-mode-labels/. Also learned: the
  password keys are boxed symbols from the card game's own texture, untouched by the
  patch, so they're the original's.

## Facts that needed checking

- The developer credit (2026-10-04, 9bf5cb1). Some English sources name Soliton or
  Thunder Stone. The game's own staff roll, rendered from its image files, ends
  "PRODUCE ©2000ASCII ©2000ACCESS"; Japanese Wikipedia agrees (Access developed, ASCII
  published).
- Only Rev 1 (Redump #60391, the bug-fixed reprint) is supported. It has the same
  serial and barcode as the original pressing, so the box can't tell them apart.
- The "misspelled" names (2026-10-09). Before fixing a developer name, check the earlier
  games. Halycon is Wizardry V's monster, and NUNCHAKA (Wizardry VI and VII) and Maelific
  (Wizardry I) are Sir-Tech's own spellings, so they stay. Dragonare, Old Drumer and
  DISPLASER ROBE had nothing behind them and were fixed, and so was "Small
  Silhoutte(s)", as "Small Shadow(s)". The Mythical list's Mesoamerican names have no
  Wizardry precedent at all, so they follow the Nahuatl: Shocitnal, Oserotoru,
  Inkuintori and Kuautori became Xochitonal, Ocelotl, Itzcuintli and Cuauhtli
  (`docs/shots/mythical-names`). The rest of the bestiary got the same check: seven more
  (Web Spinner, Allosaurus, Utiu, Zopilote, Ixpuztec, Nextepehua, Tepeyollotl;
  `docs/shots/bestiary-names`). A name has up to eight copies:
  the Compendium lists, three item lists, the card game, the DATA02 monster records
  (18-byte slots, 16 glyphs) and a stray record inside BATTLE.BIN, which has to be
  patched in asm because the asm step copies BATTLE.BIN over the binary patches. The
  slot size is why "Small Silhouettes" couldn't simply be spelled right. Shots:
  `docs/shots/name-dragonaire`, `name-old-drummer`, `name-displacer-robe` (befores from
  the 2026-10-08 crawls).

## Reading the game's code

Chris, 2026-10-10: "I'm tired of making guesses about what happens when and how in the
game." Until then the code had been read only where the translation needed it (the text
printer, the glyph pools). This is the story of reading the game's rules out of it.
Findings are in `docs/re/` (index: `docs/re/README.md`); the summary is in
`engine-notes.md`.

### The question that started it

- What Balbo's body recovery costs (2026-10-10). Chris asked whether "That lot had
  some mighty fine gear on 'em" meant Balbo keeps the gear, and whether the bodies are
  even the player's. The answer came from the code, not the web. The NPC_MES files
  hold only strings, so the first step was finding Balbo's offer in a RAM dump taken
  during a talk. That meant searching for the halfword pair "2, 142" (print string
  142). It turned up a static script in the talk overlay: offer, yes/no question
  (143), yes line (144), no line (145). Next was finding the code that copies that
  script to the stack. That gave Balbo's handler, one of several big state machines in the
  overlay. Then I searched it for stores to the roster's location byte
  (+0x7a). Three loops send a wiped party's members back to town, one in each of Guy's,
  Balbo's and Fontana's handlers, and each takes a different fee: Guy takes all the
  gold, Balbo every item, Fontana half the gold and every other item slot. The offer
  only appears when another of the player's parties is wiped out in the maze, and then
  on a coin flip. Nothing was tested in the emulator; it rests on reading the code.
  Details and addresses: docs/re/C-talk.md §5 (it began as engine-notes, "Body recovery
  by NPC parties", since folded into the chapter). Work files:
  rips/probe/bodies/. Two things from that trace held up when the whole code was read the next day: the
  three fees, and that the bodies are the player's own. One didn't: the offer isn't a
  coin flip of its own but the third of the talk's service rolls (C-talk.md §4).

### Setting up

- Setting up a decompiler for the whole game (2026-10-11). Chris asked for the game's
  rules to be read out of its code, not guessed, so the first step was Ghidra 12.1.4 run
  headless with lab313ru's PSX loader, which knows the PS-X EXE format and labels
  about 1,150 functions of Sony's PsyQ 4.3 library by signature. Ghidra needs a JDK and
  the system had only a JRE, so a portable Temurin JDK went in ~/tools. The game's seven
  overlays all load at 0x800a1000, so each became its own program with the executable
  mapped beside it. The first try cut Balbo's talk handler short: the executable calls
  0x800c76f0 in some other overlay, Ghidra started a function there in MCARD, and that
  split the handler in two, hiding the fee loop. The fix was to analyze the executable
  with the window empty, then map the overlay and seed only addresses that look like
  function starts. Two overlays turned out to call into the overlay underneath them:
  BATTLE into MAZE's leftover tail, HAZURE into JOUKA's. Mapping those tails raised
  BATTLE's coverage from 82% to 87% and cut the functions thrown out as junk there from
  20 to 3. In the end: 2,170 game functions, about 195,000 lines of C, eight modules
  rebuilt in about 8 minutes and refreshed in under a minute. With the roster and party
  records typed, Balbo's fee reads `roster[i].items[k] = 0xffff`. Map and workflow:
  code-map.md. Tools: scripts/re/.
  A late catch: the first build read `rips/q7iso`, a copy of our patched build, not the
  original disc. The difference was only our patch sites (checked byte for byte: none
  touched the item table), and the projects were rebuilt from `rips/clean` (585c983).

### Seven analysts at once (2026-10-11)

The code was split by subsystem among seven agents working in parallel, each with its own
symbol file, so nobody overwrote anyone. Each wrote a chapter and ended it with how it was
traced. The short versions:

- **Maze (A).** Looking for Wizardry's usual random roll per step found none. Following the
  step's calls led to `roamer_meet` and 16 token positions, and from their writers to the
  routines that place them and decide which NPC parties may appear. The fixed meeting
  squares, converted to the fan sites' E/N coordinates, landed exactly on the known
  meeting places: the check that the reading was right. For the time-decay question, two
  long emulator runs watched four dead characters' records (40 inn nights, then a walk in
  the maze); the only writes were record copies and compaction.
- **Camp (B).** Ghidra flattened the spell code's two jump tables into one function that
  seemed to cast every heal at once, so the tables were read straight from the file and
  each case followed in the disassembly; Kadorto only made sense that way. Six claims were
  then checked by button presses alone from the test save (Halito free in camp, Dumapic
  failing in the Training Maze and still costing a point, "What?" for a heal with nothing
  to heal, a potion used up on a healthy ally).
- **NPC talks (C).** The talk scripts don't exist as data: each handler builds them on its
  own stack every frame. So `scripts/re/talkscripts.py` runs the handlers' own code, a
  small MIPS interpreter over a RAM dump taken during a talk with Guy, tagging every value
  read from a global so run-time slots show up. That gave the table of when each of 1,150
  NPC lines plays, and a dozen bugs and stretches of text nothing reaches.
- **Battle (D).** BATTLE had no names, and the way in was the dice: it doesn't use the
  maze's random routine but two tiny generators in the executable with 75 callers between
  them, so the rules are in about 70 of its 404 functions. Breakpoints on those generators
  logged each roll's caller and range; breakpoints on the compare instructions caught roll
  and threshold together, so the to-hit and initiative formulas were checked roll by roll
  (26 of 26 monster ticks matched). The wipe's item loss turned up while looking for what
  happens to bodies.
- **Town (E).** A regex over the C mapped every constant text index to the function that
  prints it, which named the town's screens in one pass. The Temple was then checked in
  the emulator without writing to RAM: the town rolls the dice every frame, so waiting a
  different number of frames before the same presses gave different rolls, and both
  sides of each threshold could be seen from one state. The tavern's recruit pools
  matched a fan's tally from a June 2000 message board exactly.
- **Edge of Town and saves (F).** Resolving each print call to its text labelled most of
  the Edge of Town in minutes, and turned up a hidden ninth menu entry (Dragon's Cave). The
  save's checksum was 0xe9 off until a second reading showed the sum is kept inside the
  image, so it adds its own bytes at the end. A save made in the emulator and reloaded
  from a cold boot confirmed the layout.
- **Records (G).** A count of every field the decompiled code touches put the busiest gaps
  first. The status screen prints most fields with their label strings, which named them;
  Boltac's weapon compare named the item fields; the class change code named the race and
  class tables. A premade Dracon Fighter's experience matched the level-5 entry of the
  first EXP table exactly.

Two of them hit their turn limit before writing anything down and had to be resumed with
"save what you have first"; after that every agent committed after each step.

### Checking (2026-10-11)

- **Fallen parties.** Chris asked for every routine that touches a party left wiped in
  the maze. Every writer of the character records and the party table was read, then the
  scenario replayed: 40 nights at the inn, back into the maze, onto the bodies' square,
  with every write logged. Nothing takes from the bodies. Two new bugs came out of it,
  among them the Temple's failed raise from ashes, which scrambles the party table
  (fallen-parties.md).
- **Descriptions.** Every item, spell and Compendium description was checked against the
  records and code: 18 spell ranges in the original are wrong (Lahalito says 6-58 and
  rolls 6d6), and three of our own lines mistranslated 力 as the Strength stat
  (description-check.md).
- **A garbled battle line** ("Mars looses at Flap Insect wi / th / 0088ththerer...") in
  the maze analyst's test run looked like a patch bug. It wasn't: the battle text loads
  once at boot and stays in RAM, and the test state descended from one made on an older
  build. The same line drawn on the current build was fine. It's a warning for anyone
  carrying an emulator save state across a patch update.
- **Merging (phase 4).** The chapters were reconciled with each other and with the code:
  a dozen corrections, among them the rescue offer being open from the start of the game
  rather than from the Shrine, and Sogref targeting an ally rather than its caster.

## Fixing the original game's bugs

- 2026-10-11. Chris: fix the clear bugs, reopen content a bug cut off, ask about anything
  that looks deliberately cut or changes the balance. The phase-2 code analysis had
  listed bugs and unreached strings; each was re-read against the original disc
  (rips/clean) and triaged in `docs/re/bugs.md`: 10 clear bugs, 8 cut or unclear, 4 that
  change the balance, 7 harmless.
- Most of the fixes are a single changed immediate or branch. Two needed new code and had
  no room, so they sit over debug routines nothing calls: an encounter-id picker drawn
  with FntPrint in MCARD (0x800c57c8) and a debug-flag menu in JOUKA (0x800a6c40). "Nothing
  calls" was checked as no jal, j, pointer or computed address reaching them in any
  module.
- How the fixes were tested: load a state, write the case into RAM, lay only the fix's
  bytes over the overlay, drive it with button presses, and compare runs. Waiting a
  different number of frames before the same presses gives different rolls, which is how
  the chat and Temple tests got their spread. Scripts in `rips/re/work/P3-bugs/`.
  - Alstron's Madi (1976612): 8 of 8 runs "quite all right" before, 8 of 8 Madi after.
  - Chat specials (a9ed605): Guy's block 9 never came up before, 20 of 22 runs after.
  - Temple (e4c0da7): the before run showed more than the audit predicted. The current
    party scrambled on the spot: Venus dropped out and Mars, never a member, joined.
    The fix's first draft had its own bug, a MIPS load delay: the index was loaded in a
    jal's delay slot, and the routine's first instruction copied the register before the
    load landed. The table loop got the right index and the party loop a stale one. The
    test caught it.
  - BROKEN ITEM purge (c717515): watchpoints on the pack showed the purge zeroing slot
    9's uses, then the pack compaction carrying the zeroed count along with the item.
    Testing the after case took two tries: the CD loads the overlay sector by sector, so
    the fix bytes had to go in after the sectors holding them had arrived.
  - The other six are checked against the disassembly only; no state reaches their
    scenes.
  - The pit soft lock (5ff86d2) came out of a follow-up test of a "harmless-looking"
    entry. A party in which nobody had met Guy, falling into the Area C pit while Guy was
    the rescuer, got no rescuer block; the scene replayed the last block, which ends
    without closing the talk, and sat on an empty window for good, on the original MCARD
    too. The fix reuses the game's own rescuer for parties that don't know Guy (Balbo's
    party, or the man in armor) in eight instructions over the same debug routine as the
    pit-scene fix. Tested on the built overlay: all three cases (nobody met, Balbo met,
    Guy met) close the talk and return to the maze within 900 frames.
- Zaril's healing (9135ef5), the first reopened content rather than a fix. His handler is
  the same skeleton as the others' but stops short: Talk goes straight from the
  introductions check to his sale roll, and there are no heal states at all, though
  NPC_MES5 has the whole exchange and the log line. Chris approved reopening it.
  - The lines map onto Guy's and Balbo's stage-3 table one for one (same order, one HP
    spell), so the patch copies their logic and invents nothing: 25% offer when someone
    is hurt, 20% out of spells, Dialko/Latumofis/Dialma by status. The one judgment call:
    Zaril's sale never had the others' outer 50% service roll, so the heal check goes in
    ahead of it rather than halving his sale odds.
  - Space was the hard part: about 900 bytes of code and scripts. It fits in three MCARD
    routines nothing calls (a yes/no box, two card-status checks) plus the rest of the
    debug routine the pit fixes use, each checked for references across every module.
    Two other "uncalled" candidates turned out to be the tails of real functions that
    Ghidra had split off, and were left alone. The first build overflowed by 8 bytes;
    reordering so the offer state falls through into the picker setup fixed it.
  - A test-harness slip worth noting: the first run's text-advance press landed in the
    frame the member picker opened and picked the default member. The harness now waits
    for the picker before pressing.
  - Tested on the built overlay, seven cases (each cure, dead, healthy, cancel, out of
    spells), all returning to the maze. Shots in `rips/re/work/P3-zaril/`.
  - Follow-up (98b0c5e): putting the heal check ahead of the sale, as the other parties
    order them, cut Zaril's sale from 50% to 37.5% of Talk presses whenever anyone was
    hurt. Chris: "zaril's code needs to be fixed, so that his item sale option isn't
    buried if the party has hurt characters." The hook moved to the one store all four
    no-sale paths share, the chat state, so the sale runs exactly as the original and
    healing only fills presses that would have been chat. A sampled run (80 trials hurt,
    40 not) showed the sale at the same rate both ways. The first sample showed no sales
    at all: the sale's "compatible" bit is rebuilt by the greeting selector from the
    members' met bits, so setting it directly did nothing.
- No natural before/after shots: every test uses RAM writes. Internal captures of the
  Temple pair are `rips/re/work/P3-bugs/temple/lost_before.png` and `lost_after.png`.
