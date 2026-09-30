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
are still in progress. v0.8.0 will be the first beta, once the text removed at the
original team's request is translated again. Further 0.8.x releases follow as review
passes land.

**Release candidate (0.9).** After the full playthrough, with whatever it turns up fixed.

**1.0.** Every piece of text the player can reach is in English and has had at least one
quality check, the game has been played through to the ending and confirmed
completable, and the disc layout has been reviewed so the patch doesn't slow loading
(see "Disc layout").

Each release gets a version tag and a changelog entry. Pushing a `v*` tag builds the
patch and publishes the release (`.github/workflows/release.yml`); the notes come from
that version's section of `CHANGELOG.md`. The patch is an xdelta for the Track 1 `.bin`
of the redump set, since the build leaves both audio tracks untouched.

## Still to do around releases

- **Project identity.** A name and repo of its own instead of a GitHub fork. Decided
  2026-09-27: create a fresh repo under the new name and push the full git history
  there (Remisse's commits and authorship stay in it), keep GPL-3.0, and point to the
  original repo at the bottom of the README as the origin of the code, as the license
  and courtesy ask. The local folder, the jar name and paths in scripts follow the new
  name.
- **The original team's requests (2026-09-26).** Their translation is removed and must not
  come back, and they aren't to be credited. Remisse's code stays under the GPL, with the
  notice in `docs/notice.txt` on the repo (README) and on every release page: no LLMs
  were used in Remisse's original code, Remisse had no role in this project, and the
  original team doesn't endorse it. `scripts/mkrelease.py` adds it to the release notes
  and the readme in the zip. It also goes on the romhacking.net page.
- **Known issues.** A list players can read before starting, and GitHub issues for
  reports.
- **romhacking.net.** Submit the release package once the project has its own name.

## Work streams

### Text coverage (to reach beta)

`scripts/jpinventory.py` sorts every string in the dumped text files into translated,
needing translation, and deliberately Japanese (with the reason for each exclusion).
Before the original team's text was removed, every reachable string was translated.
Now 1,281 strings are left, about 21% of the Japanese by character count: all of
EVENTMES (316 strings), and parts of SISETU (551), STATUS (195), FIGHTMSG (203) and
M_CATALG (16). Until they're done, these show up garbled in the patched game, because
the English font and digraphs replace the kana glyphs.

The rest of the Japanese doesn't need translating: Japanese-mode lists the game doesn't
use because it has built-in English beside them, placeholder slots, debug text, and two
item files nothing loads. The staff roll and the other screen graphics were already in
English. Checked in play: the level-up stat messages and the catalog's item names.
Inferred but not seen in play: the ITEM.DAT alignment and sex labels, and that ITEM_SE
and ITEM_CA are never loaded.

Typos in the game's own English monster names are for the quality passes:
"Silhoutte", "Drumer", "Maelific", and "Dragonare" (the card game says "Dragonaire").

### Quality passes (to reach 1.0)

1. NPC dialogue cultural review (NPC_MES1-5). In progress; tracked in
   `docs/npc-review.md`.
2. The retranslated text (see "Text coverage"). The event script is under review
   scene by scene; `docs/event-review.md` says where it stands. Translate it fresh from
   the Japanese, to the same standard as the NPC pass, with the terms we've settled on
   (character names, the game's own spell list) and three periods for ellipses.
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

### Disc layout (to reach 1.0)

Review where the build puts files on the disc, and optimize it. Every file keeps its
original LBA, except that a file that outgrows its sectors is appended after the last
data file (`scripts/relocate.py`). As of 2026-09-30 that's five files: SISETU,
I_NAME_E and NPC_MES1-3 move from around LBA 28,300-29,500 to around 163,300, so each
load of one of them is a seek across most of the data track and back. NPC_MES loads on
every NPC encounter.

Things to look at:
- Whether the original layout groups files by when they're loaded, and what a moved
  file sits next to in the loads around it.
- Whether a moved file can go somewhere nearer, such as sectors of a file nothing
  loads (ITEM_SE and ITEM_CA are believed never to be loaded), or not move at all
  because its text is trimmed to fit.
- Load times against the original disc, in DuckStation with accurate CD timing and on
  real hardware if possible.

The PS1 drive reads at constant linear velocity, so data comes off at the same rate
anywhere on the disc. The outer-edge speed advantage of CAV drives doesn't apply here;
what placement changes is seek distance.

### Build from a clean clone

A fresh clone builds the same image as the development machine (checked 2026-09-26,
after making file relocation independent of filesystem order). The release workflow pins
the armips and mkpsxiso commits; `docs/building.md` has the steps.

## After 1.0

Once 1.0 is out and any early bug reports are dealt with, the repo mostly goes quiet.
- Archive the repo, so it stays readable and downloadable and it's clear the patch is
  finished rather than abandoned.
- The disc token can be left to expire. The private disc repo only matters if another
  release is ever needed, and that would need a new token too.

## Open questions

- Project name.
- Should the version show in-game (title screen) so bug reports say which build they're
  on?
