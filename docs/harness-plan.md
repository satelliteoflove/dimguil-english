# A harness that plays Dimguil: plan and pilot

Written 2026-10-12. This is a plan, nothing is built yet. The goal is a program that plays
the patched game from a cold boot to the ending by itself: making characters, walking the
maze, fighting, answering prompts and solving the puzzles. The LLM writes the program and
handles the cases it can't, rather than pressing buttons. Several copies can run at once
with different parties.

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
- **Text capture:** every text box with its string ID and a screenshot. Data checks
  catch width, line count, missing glyphs and anything left untranslated. Image checks
  flag text pixels outside the box border and a triangle that overlaps text or sits far
  from the last line. Flagged shots go to the LLM before anyone else.

**The LLM:**
- **Building the harness.** This is most of the cost, mainly getting the menu macros and
  timing reliable.
- **Turning the walkthrough into goal lists.** Mostly mechanical: the chapters already
  give squares, and the code analysis gives most of the flags.
- **Handling stuck runs.** The harness stops and writes a report (state, screenshot,
  recent log), and a session reads it and fixes the harness or the goal. If the harness
  is good, a full run should need tens of these, not thousands. A cheaper model can sort
  the reports; Opus does the fixes.

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
| T5 | Text capture across T3 and T4 | strings seen; any overflow or untranslated glyph found | every captured box checked |

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
