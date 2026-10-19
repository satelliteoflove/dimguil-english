# Roadmap

## Goal

A complete English translation of Wizardry Dimguil (PS1, SLPS-02691, Rev 1) that anyone can
play from start to finish. It's released on GitHub, with a packaged release for
romhacking.net: a patch file to apply to your own Rev 1 disc image, a readme and credits.

Releases go out as the work progresses. We don't hold everything back for 1.0.

## Release stages

**Alpha.** The game is believed to be playable to the end, but some text is still
Japanese, rough, or badly formatted.

**Beta (0.8.x).** Every piece of text the player can reach is in English. The work is
fixing glaring and game-breaking bugs and cleaning up rough translations. v0.8.0's
condition, that the text removed at the original team's request be translated again,
was met on 2026-10-03. As of 2026-10-10 v0.8.0 isn't tagged yet and the repo is still
private. Left to do: the release readme, the changelog entry and the release title
(Chris writes these), then make the repo public and push the tag. It also waits for the
harness bot to play through to the ending (Chris, 2026-10-17), the gate for going public
set on 2026-10-12. There's no
announcement, and the README says not to play it until 0.9.0. Further 0.8.x releases
follow as fixes land.

**Release candidate (0.9.x).** v0.9.0 needs three things: the quality pass is complete
(every piece of text the player can reach has been reviewed at least once, see "Quality
passes"); Chris's playthrough has reached the ending and what it turned up is fixed; and
the disc layout is settled (see "Disc layout"). v0.9.0 is announced on r/wizardry and
RetroGameTalk, for people to play and report the smaller bugs. 0.9.x releases are bug
fixes and minor translation adjustments only. Testing on a real PlayStation happens
during 0.9.x.

**1.0.** Done and polished: after 1.0, only minor bugs or typos should turn up.

Each release gets a version tag and a changelog entry. Pushing a `v*` tag builds the
patch and publishes the release (`.github/workflows/release.yml`); the notes come from
that version's section of `CHANGELOG.md`. The patch is an xdelta for the Track 1 `.bin`
of the redump set, since the build leaves both audio tracks untouched.

## Still to do around releases

- **Project identity.** Done 2026-10-03: the project is dimguil-english, in a repo of its
  own (satelliteoflove/dimguil-english, private until 2026-10-19, when Chris opened it to show friends
  ahead of any announcement) instead of a GitHub fork.
  Its history was filtered so the original team's translation never appears in it:
  the five files that held their strings start at the commit that removed them, and
  their names are gone from old READMEs. Remisse's commits and authorship stay. It
  keeps GPL-3.0 and points to the original repo in the README.
- **The original team's requests (2026-09-26),** made by Remisse in reply to Chris's email,
  speaking for the whole team (the original translator and editor too); Remisse was the
  only one Chris corresponded with. Their translation is removed and must not
  come back, and they aren't to be credited. Remisse's code stays under the GPL, with the
  notice in `docs/notice.txt` on the repo (README) and on every release page: no LLMs
  were used in Remisse's original code, Remisse had no role in this project, and the
  original team doesn't endorse it. `scripts/mkrelease.py` adds it to the release notes
  and the readme in the zip. It also goes on the romhacking.net page.
- **Known issues.** Tracked as GitHub issues with the "known issue" label, which the
  README links to; there's no separate file to keep in sync (decided 2026-10-07). The
  release notes name the worst few, for players who download from romhacking.net.
- **Game changes up front.** Every fix to the original game's code, and every piece of
  restored or reopened content, is listed plainly in the README, the release notes and the
  romhacking.net page, where a player sees it before patching (Chris, 2026-10-11: players
  may feel either way about content that's suddenly patched in, so they need to know up
  front). It also covers deliberate non-fixes players might ask about, such as the wipe's
  one-character item loss. The source list is `docs/re/bugs.md` and the "Game bug fixes"
  section of `docs/translation-notes.md`. The wording is Chris's.
- **Backstage docs before the forums.** The repo went public before any announcement, with
  the planning notes still in `docs/`: `announcement-outline.md` and
  `release-notes-outline.md` (where and how to announce, venue rules, what to say), and
  working notes such as `playthrough-review-plan.md`. Fine for now (Chris, 2026-10-19);
  move them out of the repo, or rewrite them as public docs, before the release goes
  on the forums. The README is an interim one, to be rewritten for the announced release.
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

The patch is English only: the four language switches are locked on "Eng", since the
Japanese names would draw as a jumble. The README, the changelog and the release readme
say so (2026-10-13).

The game's own English names were reviewed on 2026-10-09 and 2026-10-10, checking
earlier Wizardry games first (`docs/translation-notes.md`). Fixed: typos (Dragonaire,
Old Drummer, DISPLACER ROBE, Web Spinner, Allosaurus), Small Shadow(s) ("Small
Silhouettes" is too long for its name slot), -y plurals (Dragon Flies, Vorpal Bunnies
and others), the Mesoamerican names as their sources spell them (Xochitonal, Ocelotl,
Itzcuintli, Cuauhtli, Utiu, Zopilote, Ixpuztec, Nextepehua, Tepeyollotl), Smelia in
the Compendium as in battle, and three items renamed: BREASTPLATE OF BOONS, IRON
GLOVES (Wizardry III's name for 鉄の小手) and TABLET OF THE SUN. Kept as the series or
the developer had them: Halycon (Wizardry V), Maelific (Wizardry I), NUNCHAKA (Wizardry
VI and VII), BENT STAFF (Wizardry I), Flap Figure (Gaiden IV), Astro Zombie and Chany
Mask. Bartok's Trading Post shows the patch's names with the disc's beside them.
On 2026-10-13 four unidentified names were changed to match what the player sees:
Vampire Bat, Wing Lizard and Were Bat are Flying Figure(s) instead of Bird(s), and
Marchosias is Greater Demon instead of Very Big Bird (`docs/unidentified-flyers.md`,
decisions.md 26).

### The game's code and the original's bugs

On 2026-10-10 and 11 the game's rules were read out of its code with Ghidra, so questions
about what happens when no longer rest on guesses: the maze and its encounters, the camp,
every NPC talk and when each line plays, battle, the town, the Edge of Town and the
save, and the records. The findings are in `docs/re/` (index `docs/re/README.md`),
summarized in `docs/engine-notes.md`; the tools are in `scripts/re/` (`docs/code-map.md`).

Decided 2026-10-11: the patch fixes the original game's clear bugs, and reopens content
a bug cut off. Fifteen are fixed (`asm/bugfix_*.asm`, `docs/re/bugs.md` group 1): NPC
lines that played in the wrong place or never (Guy's statue warning, Rosea's and
Cephala's heals, Alstron's Madi, the pit scene, Fritillaria's "walkin' corpse",
Cresson's speech after the Decipher table, the rerolled chat topics), the Temple
scrambling the party table after a failed raise from ashes, the BROKEN ITEM purge
clearing the wrong slot, and the pit scene locking up for a party in which nobody has
met Guy (2.8). The harness runs found two of them: a race at the Grounds pillars
(bugs.md 1.11) that the longer English text set off, locking the game in about 3% of
pillar events, and a rare race in the game's CD library that can freeze any disc read for
about 20 seconds before the game retries it (1.12). Decided since (`docs/re/decisions.md`, nothing there is waiting on Chris
now): Zaril's healing, Guy's and Fontana's re-introductions, Cresson's greeting and
Fontana's chat about Zaril's new party are reopened; the NPC identify service and
Balbo's party's "heard that already" stay unused; the balance bugs are kept (see
"hardcore mode" below), except one: the Ninja's and Monk's class hit effects, which the
code meant to give and never did, now apply (bugs.md 3.5, fixed 2026-10-17 and to be
disclosed in the release notes as a balance change); and the original's wrong numbers in spell and item descriptions
are corrected (`docs/re/description-check.md`). The NPC rescue fees were tested in
natural play on 2026-10-13 (`docs/re/rescue-test.md`): all three match the code, and the
test found that a rescued party stayed on offer and could be charged again (bugs.md 1.13),
now fixed: the Yes frees the party's record.

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
   and the 37 hits were reviewed one at a time (`docs/sweep-review.md`, 2026-10-03 to
   2026-10-04). That isn't the full second look these files still need; the items
   flagged for another look are under "To revisit" in `docs/translation-notes.md`.
   The descriptions were also checked against what the game does
   (`docs/re/description-check.md`, 2026-10-11), which found three of our lines
   mistranslating 力 and many wrong numbers in the original, all since corrected.

Total translation is about 44,700 words as of 2026-09-26.

### Playthrough (to reach 0.9)

A full playthrough to the ending on a current build, Chris's recorded one in RetroArch
with the Beetle PSX HW core. The emulator
tooling can check that each string fits its window, but it can't show that the game is
finishable. Findings go into GitHub issues, or `docs/playtest.html` before the repo is
public. `docs/event-review.md` lists event lines to watch for, whose wording
depends on where they turn up ("To check in play or in the code").

Saves live on the memory card, and as far as we know the patch doesn't touch the save
format, so a save should carry over from one release to the next. Verify this once
before telling players they can upgrade mid-game; the format is now mapped
(`docs/re/F-edge-save.md`, `scripts/re/savefile.py`). Carry emulator save states across
a patch update only as far as the memory card: a state keeps the battle text it booted
with (`docs/engine-notes.md`, "Loading files").

### Disc layout (to reach 0.9)

The goal is that the patch loads no slower than the original disc. Right now every file
keeps its original LBA, except that a file that outgrows its sectors is appended after the
last data file (`scripts/relocate.py`). As of 2026-10-10 that's five files: I_NAME_E
and NPC_MES1-4 move from around LBA 28,500-29,500 to around 163,300, so each load of
one of them is a seek across most of the data track and back. NPC_MES loads on every
NPC encounter (known issue on GitHub).

Decided 2026-10-07: keep the original file order, and let a file that grew push the files
after it along, instead of moving it to the end. relocate.py already rewrites the
executable's four MSF tables for moved files, so shifting every later file is the same
mechanism. Before relying on it:
- Confirm nothing outside the four tables holds an LBA: overlays, movie or XA streams,
  or files that point into other files.
- Compare load times against the original disc in DuckStation with accurate CD timing,
  for 0.9.0. Real hardware (a burned disc or an ODE) during 0.9.x.

The PS1 drive reads at constant linear velocity, so data comes off at the same rate
anywhere on the disc. What placement changes is seek distance.

Loading faster than the original, by reorganizing the data track around the real load
order or by changing the loading code, isn't a goal for this patch. It could be a
separate patch later.

### The play harness (the release gate)

Chris, 2026-10-12: the bot play-through's runs are what let the repo and the patch go
public. They have to show that the patched game behaves and can be finished without
major breakage; his own playthrough still happens, but the release doesn't wait on it.
`docs/harness-plan.md` has the plan, the checks and the results. As of 2026-10-13:
- The suite runs after every change to the harness or the game, about 330 cases
  including four cold boots through chapter 1; a game change is published only after a
  full pass on that exact disc (by md5).
- Parties play from power-on through chapter 3 into chapter 4 of 19; the chapter 4
  Guardians are the current wall. The bot now picks its target group.
- It has found two freezes in the original code (bugs.md 1.11, 1.12, both fixed), the
  voicing-mark centering bug, and many smaller screen problems.
- Still to do: chapters 8-19 to the ending (chapters 1-7 played through by 2026-10-13);
  rebuilding the suite from a fresh clone, since its states live in the gitignored
  `rips/` (in progress). The NPC rescue fees were tested on 2026-10-13
  (`docs/re/rescue-test.md`).
- Lock picking and chests were tested in play on 2026-10-13 (`docs/re/lock-test.md`):
  the three reachable locked doors, the doors with no lock menu, and every chest action.
  It found a bug in the pick (it reads a character chosen by the cursor's blink, not the
  picker) and four screen problems (the ornate door's line is cut off, Ghost Swarm's
  "strength", the picking dots, "can't act" off center), all waiting on Chris.

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

## Maybe later: corner-bracket cursor

Chris, 2026-10-13: the menu cursor stays the original's orange box, but he liked the
corner-bracket mockup and may add it later as a choice on the settings screen. Nothing is
built. The spec, what it touches and what a setting would take are in
`docs/re/cursor-frame.md` ("Corner brackets: the full spec"; decisions.md 25).

## Maybe later: a "hardcore mode"

Chris, 2026-10-11: original bugs that make the game easier are kept in the main patch, to
match the Japanese release, but each one is a candidate for an optional "hardcore mode"
patch later. Nothing is decided about whether it happens. The list so far:
- **The wipe's item loss** (`docs/re/bugs.md` 3.1). Every member gets their one roll per
  item, as the loop was written, instead of the first position getting six and the rest
  none.
- **Weapon effects and level** (`bugs.md` 3.2). The level adjustment the game computes
  and throws away is applied: about 1 point per 4 levels, +30 at most, -20 at least.
- **Level drain's save** (`bugs.md` 3.3). The comparison is turned round so a better save
  resists drain, as it does against breath and traps. That takes drain from about 9% to
  about 91% of draining hits on a level-5 character.
- **NPC Kadorto** (`docs/re/C-talk.md` §5). Five NPCs warn that their Kadorto may fail,
  but it never does. A hardcore version would give it a real chance of failing, with odds
  to be chosen (camp Kadorto's VIT roll is the obvious model).

## Open questions

- Should the version show in-game (title screen) so bug reports say which build they're
  on?
