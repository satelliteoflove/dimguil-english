# Roadmap

## Goal

A complete English translation of Wizardry Dimguil (PS1, SLPS-02691, Rev 1) that anyone can
play from start to finish. It's released on GitHub, with a packaged release for
romhacking.net: a patch file to apply to your own Rev 1 disc image, a readme and credits.

Releases go out as the work progresses. We don't hold everything back for 1.0.

## Release stages

**Alpha.** The game is believed to be playable to the end, but some text is still
Japanese, rough, or badly formatted.

**Beta (0.8.x).** Every piece of text the player can reach is in English. The first
quality pass is still in progress. v0.8.0 will be the first beta; its condition, that
the text removed at the original team's request be translated again, was met on
2026-10-03. Further 0.8.x releases follow as review passes land.

**Release candidate (0.9.x).** v0.9.0 comes once the first quality pass is complete:
every piece of text the player can reach has been reviewed at least once (see "Quality
passes"). Further 0.9.x release candidates follow as testing turns things up.

**1.0.** The release candidates have been tested more completely, and at least one
playthrough to the ending, by anyone, has confirmed the translation has no obvious or
game-breaking flaws. The disc layout has also been reviewed so the patch
doesn't slow loading (see "Disc layout").

Each release gets a version tag and a changelog entry. Pushing a `v*` tag builds the
patch and publishes the release (`.github/workflows/release.yml`); the notes come from
that version's section of `CHANGELOG.md`. The patch is an xdelta for the Track 1 `.bin`
of the redump set, since the build leaves both audio tracks untouched.

## Still to do around releases

- **Project identity.** Done 2026-10-03: the project is dimguil-english, in a repo of its
  own (satelliteoflove/dimguil-english, private until v0.8.0) instead of a GitHub fork.
  Its history was filtered so the original team's translation never appears in it:
  the five files that held their strings start at the commit that removed them, and
  their names are gone from old READMEs. Remisse's commits and authorship stay. It
  keeps GPL-3.0 and points to the original repo in the README.
- **The original team's requests (2026-09-26).** Their translation is removed and must not
  come back, and they aren't to be credited. Remisse's code stays under the GPL, with the
  notice in `docs/notice.txt` on the repo (README) and on every release page: no LLMs
  were used in Remisse's original code, Remisse had no role in this project, and the
  original team doesn't endorse it. `scripts/mkrelease.py` adds it to the release notes
  and the readme in the zip. It also goes on the romhacking.net page.
- **Known issues.** A list players can read before starting, and GitHub issues for
  reports.
- **romhacking.net.** Submit the release package.

## Work streams

### Text coverage (done)

`scripts/jpinventory.py` sorts every string in the dumped text files into translated,
needing translation, and deliberately Japanese (with the reason for each exclusion).
Every string that needs translating is translated: 4,245 of 4,245, 100% of the
Japanese by character count (2026-10-03). The text removed at the original team's
request has been translated again: all of EVENTMES (317 strings), and parts of SISETU
(551), STATUS (195), FIGHTMSG (203) and M_CATALG (16).

The rest of the Japanese doesn't need translating: Japanese-mode lists the game doesn't
use because it has built-in English beside them, placeholder slots, debug text, and two
item files nothing loads. The staff roll and the other screen graphics were already in
English. Checked in play: the level-up stat messages and the catalog's item names.
Inferred but not seen in play: the ITEM.DAT alignment and sex labels, and that ITEM_SE
and ITEM_CA are never loaded.

Typos in the game's own English monster names are for the quality passes:
"Silhoutte", "Drumer", "Maelific", and "Dragonare" (the card game says "Dragonaire").

### Quality passes (to reach 0.9)

1. NPC dialogue cultural review (NPC_MES1-5). In progress; tracked in
   `docs/npc-review.md`.
2. The retranslated text (see "Text coverage"). The event script was reviewed scene by
   scene and finished on 2026-10-03; `docs/event-review.md` lists the few items left
   to check in play or revisit later. The menus and combat messages (SISETU, STATUS,
   FIGHTMSG) were translated afresh in September with the term list in
   `docs/terms.md`.
3. Our own first-pass text that hasn't had a second look: item and monster
   descriptions (ITEM, M_CATALG), MESSAGE, combat verbs. A first step before v0.8.0:
   every item and monster description was read beside the Japanese for LLM habits,
   and the 37 hits are being reviewed one at a time (`docs/sweep-review.md`, started
   2026-10-03). That isn't the full second look these files still need.

Total translation is about 44,700 words as of 2026-09-26.

### Playthrough (to reach 1.0)

A full playthrough to the ending on a release build, in DuckStation. The emulator
tooling can check that each string fits its window, but it can't show that the game is
finishable. Findings go into GitHub issues, or `docs/playtest.html` before the repo is
public. `docs/event-review.md` lists event lines to watch for, whose wording
depends on where they turn up ("To check in play or in the code").

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

Consider a complete reorganization of the data track rather than finding nearer
holes for the moved files, so placement is planned around load order from the start.
relocate.py already rewrites the executable's four MSF tables for moved files, so a
full reorder is the same mechanism applied to every file. Before relying on it:
- Log the real load sequence in play (town, maze, NPC encounters, combat, cards) to
  see which files load together.
- Confirm nothing outside the four tables holds an LBA: overlays, movie or XA streams,
  or files that point into other files.
- Drop files nothing loads (ITEM_SE and ITEM_CA are believed never to be loaded) from
  the hot areas, or from the disc if nothing checks for them.
- Compare load times against the original disc, in DuckStation with accurate CD
  timing and on real hardware if possible.

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

- Should the version show in-game (title screen) so bug reports say which build they're
  on?
