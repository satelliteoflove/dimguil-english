# Decisions from the code analysis

These are the open questions that came out of the code analysis (2026-10-11), each with a
recommendation. The evidence for each is in the doc named beside it. Ten clear bugs are
already fixed (`bugs.md`, group 1), and the items marked "I'll do it" need no decision.

## Content that looks cut

**1. NPC identify service** (`bugs.md` 2.1). Rosea, Cephala and Cleo have complete "identify
an item?" dialogue, and every party file has its log line, but no code offers the service.
Bringing it back means writing a new service with odds we'd choose.
Recommendation: leave it unused for now. The text survives, but the mechanics would be ours,
not the developers'.

**2. Zaril's healing** (2.2). He has a full healing table (5:35-42) and no offer.
Recommendation: reopen it. His lines say which spells he casts, and the offer can copy the
other parties' 50% roll, so very little would be invented.

**3. Guy's and Fontana's re-introductions** (2.3). Their "didn't we do this already?" lines
never play; they replay the full introductions instead.
Recommendation: add the short branch Balbo's party already has. The lines were written for
exactly this case.

**4. Cresson's "boys"** (2.4). The scan that picks "boys", "girls" or "my good fellows" was
never written, so every party is "boys".
Recommendation: write the scan, with no women meaning "boys", only women "girls" and a mixed
party "my good fellows". All three lines exist.

**5. Fontana's chat about Zaril's new party** (2.5, 3:197-200). It's missing from his list of
topics.
Recommendation: add it, shown once Zaril has left to lead his own party.

**6. Balbo's party's "heard that already"** (2.6). These answer a "tell them news" topic that
doesn't exist in the code.
Recommendation: leave them unused.

**7. Greeting blocks nothing picks** (2.7) and **the pit with no rescuer** (2.8). I'll do it:
trace the first and test the second in the emulator, then bring back anything that needs a
decision.

## Fixes that change how the game plays

**8. Wipe item loss** (3.1). One character is rolled six times and everyone else keeps their
items. Fixing it gives everyone one roll per item, which makes every wipe much harsher.
Recommendation: keep the original behavior and document it. Players of the Japanese game have
always had it, and a translation patch that makes wipes harsher would surprise anyone
comparing the two.

**9. Weapon effects ignore level** (3.2). A level bonus is computed and thrown away.
Recommendation: keep the original, for the same reason.

**10. Level drain check** (3.3) and **resistances building up in town** (3.4). I'll do it:
read and test these first.

## Descriptions that disagree with the game

**11. The original's own errors** (`description-check.md`). These are 18 spell ranges, such as
Halito "1-8" against 2-8 and Lahalito "6-58" against 6-36, plus a dozen item claims, such as the
Winter Wand casting Ladalto, six unmentioned curses, and weapons called useless that aren't.
Recommendation: correct the English to match what the game does, and list each change in
translation-notes. The player can't see the code, so the text is their only guide. Where it's
known, the code also matches earlier Wizardry (Lahalito is 6d6 in Wizardry I).

**12. Our three mistranslations.** 力 rendered as the Strength stat on the Skull Dagger, the
Mace of Power and the Golden Axe. None of them raises Strength.
Recommendation: fix them.

**13. NPC Kadorto's warnings** (`C-talk.md` §5). Five characters warn that their Kadorto
might fail, but it never does.
Recommendation: keep them as written. They're in character, and nothing in the game
contradicts them on screen.

## Untranslated or misleading labels

**14. "Sane" for confused** (STATUS 208, the disc's own English). Confused characters show
"Sane".
Recommendation: "Confused", to match the status.

**15. "Retrain?"** (SISETU 167, 再訓練). Yes ages the character a year and gives a level; it
isn't a re-roll.
Recommendation: "Train for another year?", if it fits the box.

**16. "Magic Item" / "EVENT Item"** (SISETU 603/604, the disc's own English, on the camp's
item details screen).
Recommendation: "Magic item" and "Event item", in the case the other labels use.
