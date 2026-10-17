# How the agents work

The rules every agent working on this repo follows, set on 2026-10-13 after a day of
running five or six agents at once. Each one answers a problem that day turned up. Agent
briefs point here instead of repeating them.

## Working copies and builds

- **One worktree per job.** `scripts/worktree.sh NAME` makes `../worktrees/NAME` on a new
  branch `wt/NAME`, with its own `rips/` for builds and links to the shared data
  (`rips/clean`, `rips/harness`, `rips/states`, `build/`). Edit, build and test there,
  never in the main copy. The coordinator merges the branch when the work is accepted.
  (Before this, agents shared one copy: builds overwrote each other, and a disc labelled
  bf1eac6 was really another agent's uncommitted build.)
- **A disc is named by its bin md5,** never by a commit label alone. Every report gives
  the md5 of what was tested.
- **Build:** `ARMIPS=~/tools/armips MKPSXISO=~/tools/mkpsxiso ./scripts/build.sh >
  rips/build.log`, then read the whole log (0 ERROR) and run `scripts/fightfit.py`.

## The suite

- **Only the coordinator runs suite rounds,** with `scripts/suite_round.sh BUILD_DIR
  LABEL "NOTE"` started in the background, from the copy whose harness code is meant.
  It installs the disc in `rips/harness/disc/`, archives the previous one, and runs
  `regress.py`. Nobody babysits a round: the coordinator is notified when it ends.
- **Only the suite runner writes `rips/harness/regress/`.** An agent with new cases
  writes them to `rips/harness/regress/pending/NAME.jsonl`; they're added between rounds.
  (A sandbox once appended cases to the live list mid-round.)
- **Quick rounds** (`--quick`: every boot, pick, cdrace, friendly and screen case, 2
  trials per macro, every 8th stuck case; about a quarter of the time) are for fast
  feedback while working. They're recorded as `partial` and never count.
- **Publishing:** `scripts/publish_test.sh BUILD_DIR` copies a build to Chris's playtest
  image only if a full, valid round passed every case on that md5. Any change to game
  code gets that round first.
- **Save states keep old code.** A state keeps MAIN's code from the build it was made on,
  and the MAZE or MCARD code it last loaded until the next fight or town trip reloads
  it. To test a fix, make fresh states on the new disc (or start from power-on), and
  check the fixed words are in RAM. Keep a fix's matching changes in one file, so an old
  state can't run half old and half new code (the voicing-mark hang).

## Claims and evidence

- **A "lock" or "freeze" needs proof:** thousands of frames with no progress, where the
  CPU is (PC over time), and the state saved. The harness giving up after a few hundred
  frames isn't proof (the CD race was written up as permanent; it recovers after 20
  seconds).
- **Code claims cite addresses,** and are checked in the code, not inferred, before
  they're used for a decision.
- Final evidence for a fix comes from a built disc, with no code written into RAM.
  RAM-written code is fine for investigating.

## Keeping usage down

Nearly all the cost is context re-read on every step (2.6 billion tokens re-read on
2026-10-12 and 13, against 1.3 million written), so:

- **No forked agents.** A fork starts with the coordinator's whole conversation. Start
  fresh agents with a short brief that points to this file and to the status file.
- **Retire a long-running agent** when its context gets large: it brings its status file
  up to date, and a fresh agent continues from it.
- **Don't poll.** Start long jobs in the background and wait for the notification; never
  check a running job every few minutes.
- **Fewer, bigger steps.** Put a sequence of commands in one script rather than one tool
  call each.
- **Model by task.** Routine work (running hunts and replays, repeating a test, moving
  files, checking fits) runs on Sonnet or Haiku; root-causing, fix design and review run
  on the strongest model.
- **Short reports.** The full report goes in the agent's status file, under "## Report N"
  (agents can't write report files; the harness blocks them); the
  message to the coordinator is a few lines: result, md5, files changed, the report's
  path, and anything that needs a decision.

## Long runs: launch, hand back, pick up fresh

An agent never waits inside its own session for a long job: a chapter run, a chain, a
bench of dozens of fights, anything over a few minutes. Waiting costs it context every
time it wakes to check, and it gets cut off partway. On 2026-10-16 chapter 17's agent
launched three runs, waited, ran out of room before any finished, and sent the same
half-finished report three times. The fix is to split such work into short jobs:

1. **Launch agent:** writes or changes the code, commits it, launches the runs detached
   (nohup or setsid, PIDs and log paths in the status file), and hands back at once with
   what it launched and how a run's result is read.
2. **Watcher:** the coordinator starts one background wait on those PIDs (an until-loop
   on `kill -0`, run_in_background) and gets a notification when they end. No agent is
   alive in the meantime.
3. **Analysis agent:** a fresh agent with a short brief reads the results from the status
   file and the run outputs, makes the next fix, and launches the next runs, which
   starts the cycle again.

Every agent then starts clean and ends cleanly, and nothing it did is lost when it stops.
A detached run survives its agent being stopped. Short waits (a single fight bench of a
few minutes, a build) can stay inside one agent.

## Status files

Each agent keeps `rips/agents/NAME/STATUS.md`, updated at each milestone: the task, the
worktree and branch, what's done (commits, md5s), what's running (PIDs, log paths), and
the next step. After a crash or a hand-over, work resumes from it, not from the
transcript.

## Decisions

Anything that needs Chris goes on `docs/waiting-on-chris.md`, one item per entry with
what's being decided, the options and a recommendation. Nothing on that list blocks
other work unless it says so.

## Standing rules (unchanged)

Kill processes by PID, never `pkill -f` (or `pgrep -f` patterns that match your own
shells). No `/tmp`; work files go in `rips/re/work/` or the agent's folder. Never touch
RetroArch or `../playthrough`. Stage files by name. Public writing (README, release
notes) is Chris's to write or approve. No AI attribution in repos Chris doesn't own.
