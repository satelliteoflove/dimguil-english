# Lessons from the NPC review

What Chris's edits, questions and notes in the review tool have taught us, written so it
can be applied to lines he hasn't read yet. Before a file reaches him, its unread lines
are checked against this list and the fixes go into his scenes as proposals, so he
approves a fix instead of finding the problem again. Each new lesson goes here, and the
check runs again on everything still unread.

`python3 scripts/lessons.py` lists the unread lines that a mechanical check catches (the
lessons marked *Check* below). The rest need a reading, and the voice scenes and
read-throughs do that by hand.

Started 2026-10-26 from the first 16 scenes of Balbo's party and the questions on them.

## Words and idiom

**L1. American, not British.** "You lot" became "you guys" (2:5, 2:265) and "you
folks" (4:145); "you lot watch yourselves" became "you guys be careful" (5:8). Pick the
word for the voice: "you guys" for most, "you folks" for an old man, "ya" for Balbo.
Also out: "fancy", "rubbish", "lad". *Check:* `you lot`, `fancy`, `rubbish`, `\blad\b`.

**L2. Words with a connotation the Japanese doesn't have.** "Comrades" reads as
political or military to Americans; Balbo's 2:231 became "companions" (Chris: "has a
certain connotation with American audiences"). *Check:* `comrade`.

**L3. Nothing coy or creepy in how people address each other.** Reiran's お嬢さんたち /
ぼうやたち went from "girlies" / "little boys" to "girls" / "boys" (2:61, 2:62; "ladies"
first, then "girls", the natural word from one teenager to others, ac5addf). A tease
should read as a tease, not as something off. *Check:* `girlies`, `little boys`,
`little girls`, `missy`.

**L4. Trim stiff filler from casual speakers.** "Whenever you want a match, do feel free
to give us a shout" became "give us a shout" (2:155). "Do" + verb politeness belongs to
the genteel characters (Alba, Alstron, Rosea), not to Balbo's crew. *Check:*
`do (feel free|be|come)`, flagged only for speakers who aren't formal.

**L4a. Genteel isn't stuffy.** Even Alstron, the most mannered speaker, went from "as
regards {name}" to "as for {name}" (1:43), and from "that smell of the stables" to
"smelling like the stables" (1:62): polite, in words an American still says. His おや?
became "Oh?", not "Oh my?" (1:56, 1:57; 1:4 kept "Oh my?" as a greeting).
*Check:* `as regards`.

**L5. Match the register to the speaker, both ways.** Polite speakers can go more formal
than a first draft: Artemisia's "How odd... Nobody knows your age?" became "How curious...
Your age is unknown?" (2:70). Rough ones lose formality. Read each line against the
character's entry in the voice sheet (`docs/npc-translation.md`, "Voice").

## Meaning

**L6. Say what the Japanese says with an ending.** Small endings carry the point:
からな ("because") made 2:144 the punchline (Balbo helps because the dead had good
gear). The English dropped it, so the joke didn't land; it became "Besides, that lot
had some mighty fine gear on 'em. Finders keepers, right?" When a line seems
pointless in English, look for a から, のに, けど, じゃない or よ that the English lost.

**L7. Name the thing instead of pointing at it.** "Us Evil types ain't fond of this sort
of thing" made the reader wait for "this"; it became "ain't fond of doin' good deeds"
(2:142). Japanese こういうの points ahead naturally; English "this sort of thing" before
the thing is said reads as vague. *Check:* `this (sort|kind) of thing`.

**L8. Read the intent, not just the words.** Balbo's offer (2:142-145) makes three
excuses for a good deed; the English should let a Western reader see the excuses and
the real motive. Chris: "Often in Japanese the literal translation does not communicate
the intent."

**L9. A joke has to click in English.** Rosea's 2:56 only works if the English says it's
your *name* that's embarrassing. The joke names ('A', 'Item', 'Richguy', 'Appraiser')
need to be names an English player would really type; 'Appraiser' didn't click for Chris
(open in bugs.md 2.9).

## Voice

**L10. Short Japanese is not broken English.** Japanese drops subjects and particles in
ordinary speech, so a clipped line in Japanese is usually a full, plain sentence in
English. Gaura's "Me, know nothing" and "Kid, but he leader" read as a caveman, which
his Japanese isn't (questions 12, 13, 16; `docs/work/gaura-character.html`). Keep
stammers, sounds and short sentences; put back "I" and the verbs. Sentence fragments
only where the character really talks that way. *Check:* "Me, Gaura"-style
openings ("Me? I'm Reiran." and "Me, I'm doin' great" are ordinary English).

**L11. The character's voice beats a stiff source line.** Reiran's "there's no
fountain of youth, you know" sounded like a stern grandmother; she's a late-90s teen
everywhere else, so the voice wins (2:63). The leaders' businesslike maze-encounter
voice is the exception: it's a deliberate seam shared by all three leaders, so they
keep it, each a little more formal in business (settled 2026-10-17).

**L12. Relationships shape lines as much as voices do.** Chris on Alba's past
(npc2-02): how a character talks *about* someone depends on what they are to each
other. Balbo on Alba is gruff respect; Gaura on Balbo is fear (5:66).

**L13. Keep forms that have a real English equivalent.** Balbo's 兄弟 stays "brother"
(2:1): American rough-talk uses it the same way.

## Form

**L14. No line ends on a small word.** 2:142 was rebroken so no line ends on "to".
A line that ends on "to", "a", "an", "the" or "of" reads badly in the box. *Check.*

**L15. Series spellings and capitals.** Faerie, not fairy (the race, as in Wizardry VI
and VII). Class names are capitalized: Samurai, Mage, Bishop.
*Check:* `fairy`, lower-case class names in speech.
