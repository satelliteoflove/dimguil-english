# Roadmap

## Goal

A complete English translation of Wizardry Dimguil (PS1, SLPS-02691, Rev 1) that anyone can
play from start to finish. It's released on GitHub, with a packaged release for
romhacking.net: a patch file to apply to your own Rev 1 disc image, a readme and credits.

Releases go out as the work progresses. We don't hold everything back for 1.0.

## Release stages

**Alpha (0.x).** The game is believed to be playable to the end, but some text is still
Japanese, rough, or badly formatted. Where we are now.

**Beta.** Every piece of text the player can reach is in English. Quality passes are
still in progress.

**1.0.** Every piece of text the player can reach is in English and has had at least one
quality check, and the game has been played through to the ending and confirmed
completable.

Each release gets a version tag, a changelog entry and a known-issues list. The upstream
repo already has a `v0.1-pre` tag (Remisse's), so our numbering has to avoid it.

## Before the first public release

- **Release packaging.** A script that turns a build into the release package: patch
  file, readme, credits, checksums of the expected Rev 1 source image. Redump's Rev 1 is
  three files (a data track and two audio tracks), while our build writes one merged
  `.bin`, so the patch format needs working out first (see open questions).
- **Project identity.** A name and repo of its own instead of a GitHub fork. Keep the full
  git history (Remisse's commits and authorship stay in it) and GPL-3.0.
- **Credits.** Remisse (patcher, VWF hacks), [name removed] (base translation: the event
  script and much of the menu, status and combat text) and [name removed] (editing). Contact
  all three before the first public release to ask how they'd like to be credited.
- **README.** The current one is Remisse's, and it describes their Windows build and
  their project status. Rewrite it for players (how to patch) and for people who want to
  build it (see "Build from a clean clone").
- **Known issues.** A list players can read before starting, and GitHub issues for
  reports.

## Work streams

### Text coverage (to reach beta)

We don't have a full inventory of the Japanese text that's left. What we know:
- Translated files: EVENTMES, STATUS, SISETU, FIGHTMSG, M_CATALG, ITEM, I_NAME_E,
  MESSAGE, NPC_MES1-5.
- Dungeon text outside those files hasn't been inventoried.
- Text drawn into graphics (TIMs) hasn't been checked either.

A script that lists every string still in Japanese across all text-bearing files, with
the deliberately unused ones marked (the Japanese-mode name lists, see
`docs/engine-notes.md`), would tell us how far beta is and track it down to zero.

### Quality passes (to reach 1.0)

1. NPC dialogue cultural review (NPC_MES1-5). In progress; tracked in
   `docs/npc-review.md`.
2. Inherited text review. The original team's translation (about 9,600 words) is still
   almost exactly as they wrote it. EVENTMES hasn't changed at all, and upstream put it
   at about 15% edited. Review it to the same standard as the NPC pass, EVENTMES first,
   then their parts of SISETU, STATUS and FIGHTMSG. Also check it against terms we've
   settled on since (character names, the game's own spell list).
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

The GPL means the source we publish has to be buildable. Today the build expects armips
and mkpsxiso at local paths (`scripts/build.sh`). Document the tool versions and the
steps, and check that a fresh clone builds the same image.

## Open questions

- Patch format: one patch against a merged single-`.bin` image (players merge the redump
  tracks first), or a patch per track, or something else. What do other PS1 translations
  on romhacking.net do?
- Project name and version numbering.
- Should the version show in-game (title screen) so bug reports say which build they're
  on?
- Is the first public release an alpha or an early beta?
