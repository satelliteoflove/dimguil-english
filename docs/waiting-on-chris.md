# Waiting on Chris

Decisions only Chris can make, newest last. Each entry gives the options and a
recommendation. When one is decided it moves to `docs/re/decisions.md` (game and code)
or `docs/translation-notes.md` (text), and comes off this list. Nothing here blocks
other work unless it says **blocks**.

## Game code

1. **The party's Bacortu in fixed battles seals the wrong group.** The group pick in a
   fixed battle stores a row (1 front, 2 back) as the target, and `spell_bacortu`
   (0x800c9e2c) uses it as a group number, so the cast seals group 1 or group 2 whatever
   was aimed at (D-battle.md "Healing and buffs"; harness ch17 report 5). Story fights and
   the type-2 parties are fixed battles, which is where a player would reach for it.
   Options: fix it (seal every group in the chosen row, as Montino and Morlis do through
   `spell_group_range`), or leave it. Recommendation: fix it, since the description
   promises one enemy group and the cast lands on another. Not started.

## Text

2. **Fontana's rescue offer** (NPC_MES3 153). Ours reads as pure kindness ("Soft-hearted
   bunch… We'll take good care of them") while the fee is half the gold and every other
   item. The Japanese お人好し (closer to "easy marks") and 悪いようにはしませんから ("we
   won't do you wrong") carry the irony. Recommendation: rework it to keep the edge, as
   Guy's and Balbo's lines do. `docs/re/rescue-test.md`.
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
