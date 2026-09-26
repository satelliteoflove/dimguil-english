# Roadmap

## Goal

A complete English translation of Wizardry Dimguil (PS1, SLPS-02691, Rev 1) that anyone can
play from start to finish. It's released on GitHub, with a packaged release for
romhacking.net: a patch file to apply to your own Rev 1 disc image, a readme and credits.

Releases go out as the work progresses. We don't hold everything back for 1.0.

## Release stages

**Alpha.** The game is believed to be playable to the end, but some text is still
Japanese, rough, or badly formatted.

**Beta (0.8.x).** Every piece of text the player can reach is in English. Quality passes
are still in progress. v0.8.0 is the first beta, and further 0.8.x releases follow as
review passes land.

**Release candidate (0.9).** After the full playthrough, with whatever it turns up fixed.

**1.0.** Every piece of text the player can reach is in English and has had at least one
quality check, and the game has been played through to the ending and confirmed
completable.

Each release gets a version tag and a changelog entry. Pushing a `v*` tag builds the
patch and publishes the release (`.github/workflows/release.yml`); the notes come from
that version's section of `CHANGELOG.md`. The patch is an xdelta for the Track 1 `.bin`
of the redump set, since the build leaves both audio tracks untouched.

## Still to do around releases

- **Project identity.** A name and repo of its own instead of a GitHub fork. Keep the full
  git history (Remisse's commits and authorship stay in it) and GPL-3.0.
- **Credits.** Remisse (patcher, VWF hacks), [name removed] (base translation: the event
  script and much of the menu, status and combat text) and [name removed] (editing). Contact
  all three to ask how they'd like to be credited.
- **Known issues.** A list players can read before starting, and GitHub issues for
  reports.
- **romhacking.net.** Submit the release package once the project has its own name.

## Work streams

### Text coverage (done for v0.8.0)

`scripts/jpinventory.py` sorts every string in the dumped text files into translated,
needing translation, and deliberately Japanese (with the reason for each exclusion). As
of 2026-09-26 every reachable string is translated: 4,245 of 4,245. The rest are
Japanese-mode lists the game doesn't use because it has built-in English beside them,
placeholder slots, debug text, and two item files nothing loads. The staff roll and the
other screen graphics were already in English. Checked in play: the level-up stat
messages and the catalog's item names. Inferred but not seen in play: the ITEM.DAT
alignment and sex labels, and that ITEM_SE and ITEM_CA are never loaded.

Typos in the game's own English monster names are for the quality passes:
"Silhoutte", "Drumer", "Maelific", and "Dragonare" (the card game says "Dragonaire").

### Quality passes (to reach 1.0)

1. NPC dialogue cultural review (NPC_MES1-5). In progress; tracked in
   `docs/npc-review.md`.
2. Inherited text review. The original team's translation (about 9,600 words) is still
   almost exactly as they wrote it. EVENTMES hasn't changed at all, and upstream put it
   at about 15% edited. Review it to the same standard as the NPC pass, EVENTMES first,
   then their parts of SISETU, STATUS and FIGHTMSG. Also check it against terms we've
   settled on since (character names, the game's own spell list) and conventions like
   ellipses (their text uses the `` ` `` placeholder, ours three periods).
3. Our own first-pass text that hasn't had a second look: item and monster
   descriptions (ITEM, M_CATALG), MESSAGE, combat verbs.

Total translation is about 44,700 words as of 2026-09-26.

### Playthrough (to reach 1.0)

A full playthrough to the ending on a release build, in DuckStation. The emulator
tooling can check that each string fits its window, but it can't show that the game is
finishable. Findings go into GitHub issues, or `docs/playtest.html` before the repo is
public.

Saves live on the memory card, and as far as we know the patch doesn't touch the save
format, so a save should carry over from one release to the next. Verify this once
before telling players they can upgrade mid-game.

### Build from a clean clone

A fresh clone builds the same image as the development machine (checked 2026-09-26,
after making file relocation independent of filesystem order). The release workflow pins
the armips and mkpsxiso commits; `docs/building.md` has the steps.

## After 1.0

Once 1.0 is out and any early bug reports are dealt with, the repo mostly goes quiet.
- Turn off Dependabot (delete `.github/dependabot.yml`). Its weekly pull requests only
  make sense while releases are still coming.
- Archive the repo, so it stays readable and downloadable and it's clear the patch is
  finished rather than abandoned.
- The disc token can be left to expire. The private disc repo only matters if another
  release is ever needed, and that would need a new token too.

## Open questions

- Project name.
- Should the version show in-game (title screen) so bug reports say which build they're
  on?
