# Waiting on Chris

Decisions only Chris can make, newest last. Each entry gives the options and a
recommendation. When one is decided it moves to `docs/re/decisions.md` (game and code)
or `docs/translation-notes.md` (text), and comes off this list. Nothing here blocks
other work unless it says **blocks**.

## Game code

1. **A monster's Banoka-bounced row spell hits a whole row** (found 2026-10-17 with the
   Bacortu fix, bugs.md 1.16; engine-notes "Bacortu in fixed battles"). When Banoka
   bounces a monster's Madalto, Montino, Morlis or another row spell back at it, the
   target is the monster's own group number. In a fixed battle `spell_group_range` reads
   that number as a row, so group 1 hits the whole front row and any other group the
   whole back row. Rare: it needs the party's Banoka, a fixed battle and a monster row
   spell. Documented for later (Chris, 2026-10-17); options are to fix it (pass the
   group through unchanged when the caster is a monster) or leave it. Not started.

## Text

Nothing open.

## Release

3. **Disclose the balance change in the release notes** (Chris, 2026-10-17). The patch
   now applies the Ninja's 11% beheading and the Monk's 11% knock-out from class, which
   the original game meant to give but never did (bugs.md 3.5, decisions.md 31). It's
   the patch's one change to game balance, so the release notes, and probably the
   README, should say so plainly. Chris writes those; this is a reminder, not a draft.

## The site (Bartok's Trading Post session)

9. **Two Compendium notes** (Smoke Demon, Venus Man Trap), whether to add a note on the
   2-Head Snake's level-drain claim, and a review of the Compendium branch
   (http://127.0.0.1:4321/monsters/dimguil/ps/#compendium).
