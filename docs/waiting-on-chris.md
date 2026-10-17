# Waiting on Chris

Decisions only Chris can make, newest last. Each entry gives the options and a
recommendation. When one is decided it moves to `docs/re/decisions.md` (game and code)
or `docs/translation-notes.md` (text), and comes off this list. Nothing here blocks
other work unless it says **blocks**.

## Game code

Nothing open.

## Text

3. **The ornate door's message is cut off** (EVENTMES 33). It prints in a one-line bar,
   so the second line, "is locked.", never shows. Recommendation: join it into one line
   (about 265 px, it fits). `docs/re/lock-test.md`.
4. **Ghost Swarm's trap message** (FIGHTMSG 254). 体力が激減した is "{name}'s strength
   drains away"; 体力 here is HP. Recommendation: "{name}'s HP plummets." or similar.
5. **"Picking the lock..." runs into the game's dots** (SISETU 526), and **"{name} can't
   act." sits off center** (SISETU 525, x computed for the Japanese). Both are small
   code or text fixes. Recommendation: fix both.
6. **Balbo's maze-encounter register** (NPC_MES2 142). It has "doin'", "'em" and "ya"
   where the leaders' stiff register keeps the g's on. Chris rebroke 142 himself, so this
   may already be settled. Recommendation: confirm it's intended.

## Release

7. **Who asked for the notice?** ROADMAP files `docs/notice.txt` under the original
   team's requests; a comment in `scripts/mkrelease.py` says "Remisse asked for this on
   the repo and on every release page", and the notice's content (no LLMs in Remisse's
   code, Remisse had no role) reads like Remisse's request. Remisse, the original team,
   or each for different parts?
8. **v0.8.0 and the harness gate.** ROADMAP still plans v0.8.0 (repo public, tag
   pushed) as soon as the readme, changelog and title are written. Since 2026-10-12 the
   harness runs are the gate for going public. Does v0.8.0 wait for the harness to reach
   the ending, or go out as the beta it is?

## The site (Bartok's Trading Post session)

9. **Two Compendium notes** (Smoke Demon, Venus Man Trap), whether to add a note on the
   2-Head Snake's level-drain claim, and a review of the Compendium branch
   (http://127.0.0.1:4321/monsters/dimguil/ps/#compendium).
