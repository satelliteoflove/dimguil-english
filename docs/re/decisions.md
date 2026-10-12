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
**Decided (Chris, 2026-10-11): leave it unused, and say so in the release notes.** It
looks as if the developers wanted it, ran out of time, and cut it rather than implement
the identification system.

**2. Zaril's healing** (2.2). He has a full healing table (5:35-42) and no offer.
Recommendation: reopen it. His lines say which spells he casts, and the offer can copy the
other parties' 50% roll, so very little would be invented.
**Decided (Chris, 2026-10-11): reopen it, without taking anything from his item sale.** Zaril is a Dracon Lord, so the Priest spells
in his lines (Dialko, Latumofis, Dialma) fit, and his party has no other healer ("No
Bishop in our party, see.", 5:43).

**3. Guy's and Fontana's re-introductions** (2.3). Their "didn't we do this already?" lines
never play; they replay the full introductions instead.
Recommendation: add the short branch Balbo's party already has. The lines were written for
exactly this case.
**Decided (Chris, 2026-10-11): add them.** Guy's second line-up (1:128-133), which introduces Fritillaria
and Lilia together though his party never has both, stays unused and goes in the release
notes.

**4. Cresson's "boys"** (2.4). The scan that picks "boys", "girls" or "my good fellows" was
never written, so every party is "boys".
Recommendation: write the scan, with no women meaning "boys", only women "girls" and a mixed
party "my good fellows". All three lines exist.
**Decided (Chris, 2026-10-11): write the check.**

**5. Fontana's chat about Zaril's new party** (2.5, 3:197-200). It's missing from his list of
topics.
Recommendation: add it, shown once Zaril has left to lead his own party.
**Decided (Chris, 2026-10-11): add it, after the split only** (Fontana's stage 3, where
Cephala has joined).

**6. Balbo's party's "heard that already"** (2.6). These answer a "tell them news" topic that
doesn't exist in the code.
Recommendation: leave them unused.
**Decided (Chris, 2026-10-11): leave them unused, and say so in the release notes.**

**7. Greeting blocks nothing picks** (2.7). Settled (1ce9d0f): harmless. Guy's and Zaril's
unpicked blocks repeat lines that other blocks already play, so nothing is lost.
**The pit with no rescuer** (2.8) turned out to be a soft lock, confirmed in the emulator:
a party in which nobody has met Guy, falling into the Area C pit in a certain window, is stuck
for good. Fixed as a clear bug by falling through to the game's own choice for when Guy
isn't the rescuer: Balbo's party if someone has met Balbo, otherwise the man in armor. Nothing
new is written. **Decided (Chris, 2026-10-11): keep the fix.** Guy still rescues every party
in which someone has met him, as written; the fix only fills the case the developers left
empty. It only happens to a party made entirely of characters who joined after the Guy
meeting (a fresh rescue party, say), in the mid-game window, at the Area C pit.

## Fixes that change how the game plays

**8. Wipe item loss** (3.1). One character is rolled six times and everyone else keeps their
items. Fixing it gives everyone one roll per item, which makes every wipe much harsher.
Recommendation: keep the original behavior and document it. Players of the Japanese game have
always had it, and a translation patch that makes wipes harsher would surprise anyone
comparing the two.
**Decided (Chris, 2026-10-11): keep the original and document it on the site; may revisit
later.** Also a hardcore-mode candidate (ROADMAP.md). In practice the one character rolled is whoever stands in the party's first
position (`bugs.md` 3.1).

**9. Weapon effects ignore level** (3.2). A level bonus is computed and thrown away.
Recommendation: keep the original, for the same reason.
**Decided (Chris, 2026-10-11): keep the flat odds, and document it.** A candidate for a
possible later "hardcore mode" (ROADMAP.md), along with item 8.

**10. Level drain is backwards** (3.3, settled in 1ce9d0f). +0x81 is a saving throw, which
gets better with level, Luck and the Thief's bonus, but drain lands *more* often the better
it is. Fixing it would take a low-level character from about 9% to about 91% drained.
Recommendation: keep the original, for the same reason as 8.
**Decided (Chris, 2026-10-11): keep the original; on the hardcore-mode list** (ROADMAP.md).
**Resistances building up in town** (3.4) are harmless. The town's recompute does pile up,
but every battle rebuilds those numbers from scratch before using them. No fix needed.

## Descriptions that disagree with the game

**11. The original's own errors** (`description-check.md`). These are 18 spell ranges, such as
Halito "1-8" against 2-8 and Lahalito "6-58" against 6-36, plus a dozen item claims, such as the
Winter Wand casting Ladalto, six unmentioned curses, and weapons called useless that aren't.
Recommendation: correct the English to match what the game does, and list each change in
translation-notes. The player can't see the code, so the text is their only guide. Where it's
known, the code also matches earlier Wizardry (Lahalito is 6d6 in Wizardry I).
**Decided (Chris, 2026-10-11): correct the English to match the code, and list every
correction in the release notes.** The site's item tables (Emonoya's, from the item data)
already match the code; its spell page repeats the game's wrong ranges, so the site
session was sent the code's values. Chris also asked for a sweep of similar places in the
game.

**12. Our three mistranslations.** 力 rendered as the Strength stat on the Skull Dagger, the
Mace of Power and the Golden Axe. None of them raises Strength.
Recommendation: fix them.
**Decided (Chris, 2026-10-11): fix all three, with the wording he reviewed as diffs:**
Skull Dagger "It hits harder / and truer, and even adds"; Mace of Power "A mace that adds
power and / accuracy just by equipping / it. Its hidden power raises / Strength itself. It
truly / lives up to its name."; Golden Axe "Vitality and age. It also / hits harder and
truer."


**13. NPC Kadorto's warnings** (`C-talk.md` §5). Five characters warn that their Kadorto
might fail, but it never does.
Recommendation: keep them as written. They're in character, and nothing in the game
contradicts them on screen.
**Decided (Chris, 2026-10-11): keep them as written and document the difference.** A
hardcore-mode candidate (ROADMAP.md).

## Untranslated or misleading labels

**14. "Sane" for confused** (STATUS 208, the disc's own English). Confused characters show
"Sane".
Recommendation: "Confused", to match the status.
**Decided (Chris, 2026-10-11): "Confused".** The series says insane (Wizardry VI and VII;
Gaiden IV's psionic spells cause 発狂), but Dimguil renamed the status 混乱 on purpose
(Emonoya's Dimguil spell page notes the change), and our battle text says "is confused".
"Sane" is most likely a mangled leftover of the older "Insane".

**15. "Retrain?"** (SISETU 167, 再訓練). Corrected 2026-10-12 (d47df20, [emu]): it's asked
after Yes to "Use this character?" when the creation roll was under 10 bonus points (most
rolls). Yes trains three years: +3 levels, +3 years of age (a level-1 Fighter aged 15
came out level 4, aged 18). No registers the character as rolled. It isn't a re-roll.
Recommendation: "Train for three years first?", if it fits the box.
**Decided (Chris, 2026-10-12): keep "Retrain?" as it is.** Retraining is a convention of
the Japanese line (Gaiden IV on, per Emonoya's pages and BBS), so its players know what it
means; see translation-notes, "Deliberate choices".

**16. "Magic Item" / "EVENT Item"** (SISETU 603/604, the disc's own English, on the camp's
item details screen).
Recommendation: "Magic item" and "Event item", in the case the other labels use.

## From the description sweep (2026-10-11)

Left alone by the corrections run (38fa241), for Chris. Details in `description-check.md`.

**17. What the item descriptions don't mention.** Six curses; restrictions; hidden powers
such as the Worst Sword's Vit-1 and a year older, the Dragon Kite's Str+1, the PK
Crystal's IQ+1 and regeneration. Adding them may give away what the developers hid.

**18. SISETU 219, Luck.** Says Luck helps disarm traps and dodge attacks. In the code,
disarming uses Agility, level and the area's danger, and monster to-hit has no Luck term;
Luck feeds the saving throws.

**19. SISETU 65/66, "has died of old age".** The character is actually Lost and deleted.

**20. SISETU 492, the Training Maze sign.** Accurate, but doesn't say a wipe there still
halves gold and costs the front member's items.

**21. Compendium claims with no support in the code.** Smoke Demon "swords barely harm it"
(nothing cuts weapon damage); Venus Man Trap "burns well with fire spells" (no fire
weakness, 40% Mage resistance).

**22. FIGHTMSG 179/185, Madalqua's "in freezing cold".** Its element is Tiltowait's, not
cold. Battle narration, so left alone.

Not yet checked: EVENTMES 210/211 (the pillar water "seems to restore your magic"), and
Calnova on doors.
