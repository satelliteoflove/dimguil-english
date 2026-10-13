# A harness that plays Dimguil: plan and pilot

Written 2026-10-12. This is a plan, nothing is built yet. The goal is a program that plays
the patched game from a cold boot to the ending by itself: making characters, walking the
maze, fighting, answering prompts and solving the puzzles. The LLM writes the program and
handles the cases it can't, rather than pressing buttons. Several copies can run at once
with different parties.

**The release gate (Chris, 2026-10-12).** These runs are what let the repo and patch go
public: they have to show, to Chris's satisfaction, that the patched game behaves properly
and can be finished without major issues or breakage. They won't catch everything, and
Chris still plays it through himself, but they mean the release doesn't wait on that.

What it's for, in order:
1. **Translation QA.** Every text box the game shows in real play, captured and checked
   for overflow and anything left untranslated, including branches one play-through
   never reaches (Cresson's three greetings, class and alignment text, NPC branches).
2. **Testing the code fixes.** The reopened content and bug fixes, exercised in ordinary
   play rather than from staged states.
3. **Checking the site's walkthrough.** A run that follows a chapter and reaches its end
   flag confirms that chapter step by step.

## What we already have

- **A headless emulator** (`scripts/emu.py`): our own libretro frontend for Beetle PSX,
  the same core as the play-through. It runs without a window or sound, steps frames,
  presses buttons, reads RAM, saves and loads states, and takes screenshots. It also has
  breakpoints, watchpoints and code coverage.
- **A first runtime** (`rips/re/work/P3-rescue/rt.py`, 291 lines, from the rescue test).
  It reads position, party, roster and flags from RAM and builds the current floor's wall
  map from RAM. It also has route-finding (`bfs`), `walk_to`, a basic `battle` loop, and
  message-box handling.
- **The RAM map** (`docs/re/*.md`, `scripts/re/symbols/`): game state and overlay, party
  and roster records, status, position and facing, battle phase, talk state, story and
  NPC flags, the event map and event records of every square, config bytes (message speed
  at 0x80096378 + 8).
- **The rules**, from the code analysis: combat, spells, traps, NPC services and level-ups.
  Combat odds can be computed, not guessed.
- **Map data** (Bartok's Trading Post, `data/maps/dim/`, 44 floors read off the disc):
  walls, doors, darkness, no-entry squares and locks.
- **The site's walkthrough** (`data/walkthrough/dim/`, 21 chapters, from the four pillars
  through the ending, the Training Maze and the Dragon's Cave). Each step names exact
  squares and links its sources and maps. A few record types aren't decoded yet (the 3F
  switches, the jewel lift); the walkthrough places those by position.

The standard is the rescue test's: button presses and save states from ordinary play, no
RAM writes. RAM is only read.

## Measured speed (2026-10-12)

`rips/re/work/harness-bench/bench.py`, on this machine (Ryzen 7 3700X, 8 cores and 16
threads, 31 GB RAM), from the rescue test's states:

| Setup | Frames/s | × real time |
|---|---|---|
| 1 instance, interpreter, walking on the Grounds | 350 | 5.8 |
| 1 instance, interpreter, in a battle | 251 | 4.2 |
| 1 instance, dynarec, walking | 441 | 7.3 |
| 1 instance, dynarec, in a battle | 343 | 5.7 |
| 4 at once, interpreter, battle | 973 total (243 each) | 16 total |
| 8 at once | 1907 total (238 each) | 32 total |
| 12 at once | 2303 total (191 each) | 38 total |
| 16 at once | 2334 total (145 each) | 39 total |

Each instance uses 50-80 MB of RAM. Loading or saving a state takes 0.02 s, and a state is
16 MB.

What that means:
- **Scaling is linear up to the 8 physical cores.** The second thread on each core adds
  only about 20%.
- **8 instances is the natural setting.** It gets about 80% of the machine's throughput
  and leaves the extra threads free for you. 12 is about the most worth running.
- **Each instance runs about 4-7 times faster than real time.** That's slower than I'd
  hoped, and it's the number that decides how long a run takes. Ways to raise it:
  - **The game's fastest message speed**, only if it loses nothing. Text is captured from
    RAM when the game starts printing it (the expander at 0x8001dfc0 and the other
    printers), not read off the screen. The test: play the same stretch, battles
    included, at the slowest and the fastest speed, and compare the captured messages one
    by one. Fastest is used only if the lists match. (Chris, 2026-10-12: nothing may be
    missed because text goes by too fast.)
  - **No idle time.** Every wait is "run until RAM shows the game wants input", then
    press at once. No fixed waits. (Chris, 2026-10-12.)
  - **The dynarec** (dynamic recompiler: it translates the PS1's code into native code
    once instead of interpreting each instruction), about +30%. Our core's debug hooks
    (breakpoints, watchpoints, coverage) are patched into the interpreter
    (`mednafen/psx/cpu.c`), so they probably don't fire under the dynarec. If text
    capture needs them, the dynarec stays off, or capture moves to polling RAM.
  - **Not drawing when no text is on screen.** Pixels are needed to catch layout bugs:
    a misplaced triangle (as at the Training Maze exit), overlaps, clipping, leftover
    Japanese graphics. Those come from the drawing code and can't be predicted from the
    data without copying that code, bugs and all. So drawing stays on whenever a text box
    or menu is up, and each new box is captured as a screenshot. It's off only for walking
    and battle animations. Whether Beetle can skip its software renderer at all is
    untested: its `retro_run` sets `espec->skip = false` every frame, and mednafen's GPU
    may rasterize into VRAM regardless. `emu.py` also copies every frame into Python,
    which can be made lazy.

How long a full run takes isn't known yet. If the bot needs as many frames as 60 hours of
human play, one instance at 6× takes 10 hours, and 8 runs finish overnight together.
Menus will go faster than a human's and grinding may go slower. The pilot measures this
per chapter.

## T1 results (2026-10-12)

Full notes and scripts in `rips/harness/t1/README.md`; code in `scripts/harness/`. All on
the rescue test's disc copy (build c5dee12).

- **Text capture works.** A breakpoint on `text_expand` (0x8001dfc0) plus a write watch
  on the text buffer catches every message with its file, string number and full text,
  names and numbers filled in (e.g. FIGHTMSG 98 "Uranus attacks Ocelotl with LONG
  SWORD."). Menus redraw through the same routine every frame; the capture keeps one copy
  of each. Cost: 19% of speed (260 → 211 frames/s), almost all of it the core's
  breakpoint check.
- **Message speed doesn't apply to the main game.** config[8] is read only by the card
  games' text routines and can only be set from a card battle's SELECT screen. Battle
  narration never advances by itself; every message waits for a press. Pressing as fast
  as possible loses nothing: tapping every 4 frames gave the same 91 messages (file,
  number, text, order) as the slow fixed-wait run.
- **No idle input** (`scripts/harness/inputs.py`): commands are pressed until RAM shows
  them taken (battle phase, the member being commanded at 0x80079786, menu depth at
  0x80079b15), retrying every 4 frames. The same battle finished at frame 2982 instead of
  4429 (−33%), identical messages, no stalls. Every 2 frames or 1-frame taps double-enter
  or drop commands. In the maze a step took 16 frames and a turn 16-21, against 34 and 28
  (one sample).
- **The dynarec is out while capturing.** The breakpoints never fire under it (0 hits
  against 2555). It's about 30% faster, consistent with itself, but its RAM differs from
  the interpreter's on the same inputs.
- **Skipping drawing isn't worth it.** Profiled: walking is about 58% CPU emulation, 12%
  drawing, 10% sound; a battle 43%, 25%, 7%. The core never skips drawing, so it would
  need a core change for at most 12-25%. Copying frames into Python was about 1% and is
  now done only when a screenshot is wanted.
- **So a capturing instance runs at about 3.5× real time,** but does about a third less
  work per battle than the rescue test's waits. A faster breakpoint check in the core's
  debug hooks could win back most of the 19%.
- **For T2:** one emulator per process (the debug hooks are global to the loaded core);
  rt.py's `settle()` and `msgbox()` read pixels, and "calm" in the maze needs a RAM
  indicator; two of three rescue states couldn't walk at the start, probably an open
  message.
- **Found on the way:** FIGHTMSG 118, "Hits {ff11}0 times!", prints "Hits 1 times!".

## T2 results (2026-10-12)

Full notes in `rips/harness/t2/README.md`; code in `scripts/harness/` (`game`, `ui`,
`town`, `maze`, `battle`, `camp`, `flow`, `trials`). Fresh copy of build f068468, all
states from a cold boot by button presses.

- **The chain works** (`flow.chain`): power-on, New Game, three characters created, a
  party of six formed, into the maze, walking until at least one fight or talk, back to
  the entrance and out to town. 100/100, twice, no wipes; about 50 s a trial, 8 minutes
  for 100 with 10 processes.
- **Every macro 100/100:** create character (300/300), form party, Edge of Town into the
  maze, walking with fights and talks, back to town, a fight, talk (Leave), camp spell,
  inn, temple, Boltac's buy and sell, doors. The fight, talk and door trials start from
  few states, so they vary little; the chain carries the variety.
- **Fixed on the way:** fade-ins that ignore input (81 frames after camp, 34 after a
  battle); roaming parties read as walls; water and trees open in RAM's wall map (routing
  uses the site's no-entry squares); doors open with circle; the facility-ready check;
  dead characters in the tavern list; early presses at the inn and Boltac's; the "Gather
  gold?" prompts.
- **Found:** "Oops! There's no trap.!!" (FIGHTMSG 242 + 221); battle lines wrapped before
  "with" start with a space (98, 99, 108, 109); "Cy brings down on Giant Mosquito with
  ANOINTED MACE." reads oddly. (T2 also reported the site's data marking the Shrine's
  outer door locked; that was a coordinate slip. The site marks only the inner door, E11N3
  north is the open outer one. Its lock list is the raw bit 25 of each square's flags, and
  5 of the 19 lock bits sit on sides with no door, e.g. E11N5 north inside the Shrine; the
  harness shouldn't treat a lock bit alone as a door.)
- **Blocks T3:** lock picking never reached (the Grounds' only locked door is the sealed
  Shrine door); event-box text (EVENTMES, MESSAGE.DAT) isn't captured, only shot; some
  first-sighting shots catch the previous box; only the Grounds is handled (no stairs,
  chutes or other floors); wipe-to-temple tested once by hand; basic battle policy, chests
  left, no equipping or leveling, talks always Leave.

## How the work splits

**The harness, with no LLM in the loop:**
- **Input macros** built on RAM: wait for the state the game needs, press, and check that
  it changed. No fixed waits.
- **Navigation:** route-finding over the site's map data plus the event records.
  - It handles doors, locks, one-way walls, spinners, teleporters and darkness.
  - It knows which squares start fights or events.
- **Combat:** a rule-based policy using the code's own formulas.
  - Group spells on groups, single attacks on the weakest target, healing below a set
    level.
  - Escape or go home when spell points or HP run low.
- **Town and characters:** inn, temple, shop, identify and level-ups, plus character
  creation, including taking or declining training.
- **Grinding:** a loop that runs until the party reaches a target level.
- **The route:** each walkthrough chapter as a list of goals. Each goal is "be at a
  square, do something, and see a flag or item change". It's checked by RAM, not by the
  screen.
- **Recovery:** a save state at every goal, so a wipe or a stuck run reloads and tries
  again.
- **Text capture:** every text box with its string ID and a screenshot, checked as in
  "What the checks look for" below. Flagged shots go to the LLM before anyone else.

**The LLM:**
- **Building the harness.** This is most of the cost, mainly getting the menu macros and
  timing reliable.
- **Turning the walkthrough into goal lists.** Mostly mechanical: the chapters already
  give squares, and the code analysis gives most of the flags.
- **Handling stuck runs.** The harness stops and writes a report (state, screenshot,
  recent log), and a session reads it and fixes the harness or the goal. If the harness
  is good, a full run should need tens of these, not thousands. A cheaper model can sort
  the reports; Opus does the fixes.

## What the checks look for

The misplaced triangle at the Training Maze exit is one example of a class, not the
target. The checks cover:

**On screen (from the screenshots):**
- Text cut short. A glyph pool that runs out just stops drawing, with no error (the
  event box's 72-sprite limit, Boltac's captions, the status help line). So: are all the
  glyphs in the string actually on screen?
- Text past a box's border, off the screen, or over another box, label or the picture.
- Lines off center where the box centers them, and wrong page breaks.
- Wrong glyphs: garbage tiles, leftover Japanese, voicing-mark damage, the 〓 fallback.
- The page triangle and the menu cursors in the wrong place or on top of text.
- Names, item names and numbers that don't fit their fields, in menus as well as
  messages.
- Corrupted text: a run of blanks or garbage partway through, as from the text buffer
  overflow at 0x8008b640.

The strongest check is matching the text itself. We have the font and its width table,
so the expected line can be rendered exactly as the game should draw it and matched
against the screenshot. That catches cut-off, garbled, shifted and overlapping text in one
test, with no OCR guesswork. Where a screen can't be matched that way, simpler checks
apply (pixels outside the box, cursor position), and anything odd goes to the LLM to look
at.

**In play (from RAM):**
- Hangs and soft locks: no progress for a set number of frames.
- Crashes, and the game going to a state the route doesn't expect.
- Events that don't fire, and flags or items that don't change when they should.
- The reopened content and bug fixes behaving as written (Zaril's healing, the
  re-introductions, Cresson's greeting, the pit rescuer, and the rest).

**Done means:** several runs with different parties reach the ending, with no hang or
crash left unexplained, and every captured screen either passes or has been looked at.

## The ratchet (Chris, 2026-10-12)

"We need to be certain we aren't just stumbling through these tests; we're building a
solid self-improving system." So every fix has to stick:

1. A run gets stuck; the harness saves the state, a screenshot and what it was doing.
2. That moment becomes a permanent regression case (`rips/harness/regress/cases.jsonl`).
3. The fix goes into the shared code.
4. The whole suite runs: the T2 trials (every macro and the chain) plus every saved case,
   at most 10 processes, about 8 minutes.
5. Only a change that passes the whole suite is committed.
6. Each round logs cases passed and failed, stuck counts by cause, frames and wall time
   (`rips/harness/regress/rounds.jsonl`), so the trend shows whether it's improving.

The 8-party run (T4) waits until this is in place and T3 passes through it from a cold
boot.

`scripts/harness/regress.py` runs it; each round's harness code is a sha1 over
`scripts/harness/*.py`, and the commit must match the hash of a passing round. The cases
and their states (16 MB each) live in `rips/`, which is gitignored, so the suite isn't
reproducible from the repo yet.

## T3 and T4 results (2026-10-12)

Full notes in `rips/harness/t3/README.md`; code committed in 7026414 (`chapter1.py`,
`run_ch1.py`, `regress.py` and fixes across the macros). Same disc copy as T2.

**The suite.** Ten rounds. One change broke 50 of 124 cases (a talk-menu rewrite) and was
caught before it went in.

| Round | Passed | Note |
|---|---|---|
| 1 | 105/121 | baseline after the first T3 fixes |
| 2 | 74/124 | talk rewrite broke the T2 talk, door and chain trials |
| 4 | 124/124 | first full pass |
| 8 | 175/175 | roamers no longer learned as walls |
| 10 | 185/185 | committed (code 28d9dd7fed46) |
| 12 | 187/187 | the disc with the pillar fix (c13dea2) |
| 13 | 187/187 | the disc with the CD-library fix (0ef275c) |

**T3.** From a cold boot, one run finished chapter 1 with no stuck points: party, 13
training trips to level 7, the four pillars, the sealed door. 290,108 frames, 23 minutes
(with 8 other emulators running). The run before it took all four pillars on the first try
and stuck at the door; that moment became a case and round 5 fixed it.

**T4.** Eight parties at once, each with different classes, names and seeds:

| Party | Result | Retries | Frames | Wall |
|---|---|---|---|---|
| v0 | done | 0 | 234,134 | 20 min |
| v1 | done | 0 | 263,833 | 22 min |
| v2 | done | 0 | 298,960 | 24 min |
| v3 | done | 1 (pillar hang) | 235,773 | 21 min |
| v4 | done on rerun | 0 on rerun (door ×6 first, fixed in round 9) | 253,894 | 20 min |
| v5 | done | 1 (roamer in the way) | 343,849 | 28 min |
| v6 | done | 1 (roamer in the way) | 356,580 | 29 min |
| v7 | done | 1 (START at a meeting) | 357,212 | 29 min |

So chapter 1 takes 230,000 to 360,000 frames, and 8 runs finish in about half an hour.
Earlier T4 attempts also fixed name entry, rerolling at the class screen, alignments that
can't be made (no Good Thief), the camp reopening on a late press, and roamers standing
in the way.

**Text seen:** 386 distinct strings (STATUS 140, SISETU 124, NPC_MES1 66, FIGHTMSG 41,
EVENTMES 15), 227 shots.

**Game issues found:**
- **Pillar soft lock, fixed (bugs.md 1.11, c13dea2).** The event box closing and the dust
  settling race, and the box close wipes the guardian's fight request with walking input
  locked. Original code; our longer line set it off, about 3% per pillar event. The START
  press that first looked like the trigger only shifted the random seed the dust uses.
  After the fix: 0 of 400 seeded pillar events hang, and 8 cold-boot chapter 1 runs
  started all 32 pillar fights first try. (What Chris saw, the picture stopping at a
  pillar, may have been this or something else; a state from his play would tell.)
- **"You've met someone!" with no meeting, fixed (bugs.md 1.12, 0ef275c).** A different
  cause: a race in the game's CD library (Sony's libds) that can stall any disc read for
  good. Original code, rare (two locks in about 60 hours of bot play), likelier in Beetle
  than on hardware.

**What blocks chapters 2-5:** goal lists beyond the door; battles on the Japanese disc
don't end cleanly in the harness, which limits comparisons; lock picking still untested
(chapter 1 has no ordinary locked door).

## The pilot: what it takes to find out

The pilot answers three questions: how reliable the harness is, how fast it runs, and how
much LLM time it needs. It stops at the end of walkthrough chapter 1 (the four pillars),
which covers creating characters, the town, walking, fights and an event chain. The rescue
test got about that far by hand, so its states and notes are a head start.

**Needed before it starts:**
1. Move `emu.py` and `rt.py` into a `scripts/harness/` package. rt.py is tied to the
   rescue test's folder, and it builds only the current floor's walls, from RAM.
2. A runs layout in `rips/harness/runs/<id>/`, not /tmp: log, goal checkpoints, text
   captures and reports. States rotate, keeping the last few plus one per goal, so 8 runs
   stay well under 20 GB.
3. A frame budget and stuck detection for every macro: no progress in N frames means
   stop and report.
4. Chapter 1 as a goal list, from `01-four-pillars.json`, each goal with its flag.
5. A simple combat policy, enough for the Grounds.

**The tests, in order:**

| # | Test | Measures | Good enough |
|---|---|---|---|
| T1 | Speed: message speed fastest, the dynarec, video off | frames/s per instance; the same results with the dynarec | at least 10× per instance, or we know the ceiling |
| T2 | Each macro 100 times from varied states: create a character, form a party, walk to a square, open a door, a battle, cast in camp, inn, temple | success rate; frames per action | at least 99% per macro |
| T3 | Chapter 1 from a cold boot, one instance, no help | wall time; frames; reports; LLM time per report | finishes with 5 or fewer reports |
| T4 | T3 with 8 instances at once, different parties and classes | total throughput; how the runs differ; reports per run | all 8 finish; no new kinds of failure |
| T5 | Text capture and screen checks across T3 and T4, including the rendered-text match | strings seen; issues found; false alarms | every captured box checked; few enough false alarms to review by hand |

**What the pilot tells us:**
- **Frames per chapter**, so the length of a full run can be estimated.
- **Reports per chapter**, so the LLM time can be estimated.
- **Which macros break most**, which shows where the harness needs work.

If T3 and T4 pass, the next step is chapters 2-5 with the same method. If T2 can't get
the macros reliable, we'll know early and cheaply.

**Rules that still apply:**
- No RetroArch, and nothing in `../playthrough`.
- No work in /tmp.
- Kill processes by PID.
- Screenshots from bot runs are real button presses with no RAM edits. Whether they
  count as natural for public use is Chris's call; until he decides, they're for QA only.

## Open questions

- Does Beetle skip rendering when the frontend says video is off? That would be the
  biggest speed gain if it does.
- Is the dynarec deterministic, and does it match the interpreter for this game?
- How does a run get variety? From the same state the emulator does the same thing every
  time, so parties, names and input timing will need to differ.
- How many frames does grinding take? The pilot's chapter is too early to say; chapter 3
  or 4 will tell.
