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

2. **The Ninja's and Monk's class hit effects never apply** (bugs.md 3.5, found
   2026-10-17, docs/re/ninja.md). The class bonus (Ninja 11% beheading, Monk 11%
   knock-out) tests a register the function never loads. Options: fix it, which makes both
   classes stronger in every fight, or keep the odds as the game plays and add it to the
   hardcore-mode list. Recommendation: fix it, since the class description promises
   critical hits and the code plainly meant to give them. Not started.

## Text

Nothing open.

## Release

Nothing open.

## The site (Bartok's Trading Post session)

9. **Two Compendium notes** (Smoke Demon, Venus Man Trap), whether to add a note on the
   2-Head Snake's level-drain claim, and a review of the Compendium branch
   (http://127.0.0.1:4321/monsters/dimguil/ps/#compendium).
