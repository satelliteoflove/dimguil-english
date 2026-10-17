# NPC dialogue review: status and remaining work

A second pass over the dungeon NPC dialogue (NPC_MES1-5), for what the lines meant to
the original late-90s Japanese audience rather than their words: jokes and comic
routines, set phrases, drama, hints and tone. Started 2026-09-25 after the first-door
scene was reworked with Chris.

## How it works

1. Five reviewers read each file against the Japanese and proposed changes by scene,
   with the reasoning for each. Lines shared between files were given one English.
2. Each scene is then reviewed with Chris in play order of importance: the scene as the
   player reads it, what the Japanese conveyed, and the proposed English. Chris
   approves or adjusts it.
3. Each approved scene is its own commit (`scripts/npcapply.py`), with the reasoning in
   the commit message. Every line is fit-checked with `scripts/npcfit.py`.
4. Run `scripts/wtquotes.py check` after applying a scene. The website walkthrough quotes
   NPC lines (`docs/walkthrough-npcs.json`, ledger in `docs/walkthrough-quotes.md`); any
   quote that changed is listed with its chapter, to carry over to the site.

The reviewers' reports quote the Japanese at length, so they stay out of the repo
(same policy as the redacted `source` fields). They live in `rips/review/` on the
build machine: `NPC_MESn.md` (the reports), `pending.json` (proposed English still to
review, in `npcfit.py --overlay` format), `approved.json` (what has been applied) and
`merged.json` (all proposals after syncing shared lines).

## How a scene is presented (from 2026-10-04)

Chris reads the whole scene first, then judges it. Show it three times, complete, in the
same order of lines: **Literal** (word for word, no help, stiff where the Japanese is
stiff), **Current** (what the patch has now), **Faithful** (true to the original's
intent, readable for English players). Notes come after all three, never inside them.
Research the Japanese and its late-90s context before proposing (dictionaries, role
language, references) and cite sources. A "scene" scattered across the talk menu is
assembled in a sensible reading order, and says so.

The review happens in the browser tool (`scripts/reviewtool/`, see `building.md`): the
three readings plus the Japanese, a Compare view with the differences marked, word
notes, dictionaries, the line drawn in the game's own font, and Apply, which writes the
chosen lines after a fit check. Claude prepares each scene as
`rips/review/scenes/<id>.json` (lines in reading order with their context, the literal
and faithful readings, why each change, word notes with register, confidence and
sources, and scene notes), commits each applied scene from
`rips/review/decisions/<id>.json`, and answers questions asked in the tool by writing
the answer into `rips/review/questions.json`.

Each speaker gets a fixed marker, the same across every scene (the terminal can't color
text). Shape is the home party, color is the person. Unnamed tags use the person's
marker.

| Group | Markers |
|---|---|
| Guy's party | 🔴 Guy, 🟠 Linaria, 🟡 Lychee, 🟢 Fritillaria, 🔵 Alstron, 🟣 Lilia |
| Balbo's party | 🟧 Balbo, 🟦 Alba, 🟪 Rosea, 🟥 Reiran, 🟫 Gaura, 🟨 Artemisia |
| Fontana's party | 💙 Fontana, 💚 Zaril, 💛 Cephala |
| The scholars | 📘 Cleo, 📗 Cresson, 📙 Bergamot |
| Others | 🌑 the shadow (Mysterious figure), 🌘 Mysterious man, 🌟 Agan, 🎮 Otaka, 👑 the King, 🔮 the Priestess, 🗿 the Guardians, 📋 message boards |

Narration and the party's own thoughts get no marker.

## Done

Guy's party (NPC_MES1) is finished: all 13 flagged scenes, plus the first-door scene.
See the `NPC dialogue:` commits from 2026-09-25/26. Along the way, Lilia's "scout me"
and age lines and her shady-man line were also applied to NPC_MES3, and Guy's party
turned out to be a Dragon Quest III party (see "Guy's party and Dragon Quest III" in
`npc-translation.md`).

Balbo's party (NPC_MES2): scene 1 (Balbo accidentally turns Good) is done. Scene 2
(Alba's past) was reviewed in the browser tool and applied on 2026-10-05: nine lines
changed, with Chris's edit of Balbo's 231 ("companions", not "comrades"). Chris's note
on it: the characters' relationships to each other shape their lines as much as their
own voices do. Scene 3 (Balbo's progress reports) was applied the same day: 15 strings,
the 'Man in armor' copies included. The stiff register turned out to be shared with
Fontana's maze encounters, so the English keeps Balbo's words but makes him
businesslike (see "The leaders' maze-encounter voice" in `translation-notes.md`; settled
2026-10-17: the shift is a production seam shared by all three leaders, and each keeps
their own voice, a little more formal in business).
Chris's edits: 87 keeps "seems off" and is split over three pages, and 142 is rebroken.
Scene 4 (goodbyes when one of yours is dead) was applied the same night: Alba's 37 is
now a plea, Gaura's 43 a hope, and Artemisia's 44 is "I hope we can see each other
again!" so her fluster in 45 has something to react to. The copies in NPC_MES3 (25)
and NPC_MES5 (11) changed with them; 46 keeps "let's meet again sometime".

## Next up

**NPC_MES2, scene 5: services, the body collection offer and Balbo's sarcastic せいぜい
(123, 143-145).** Prepare it as a scene for the review tool.

## Remaining scenes

Priority as the reviewers ranked it. Numbers are string indices.

NPC_MES2 (Balbo, Rosea, Artemisia, Reiran, Alba, Gaura)
- [x] 2. Alba's past (233, 180 and the thread around them), HIGH, done 2026-10-05
- [x] 3. Balbo's progress reports (81-89, 142, 261-265), HIGH, done 2026-10-05
- [x] 4. Goodbyes when a party member is dead or lost (34-46), MEDIUM, done 2026-10-05
- [x] 5. Services: body collection offer, Balbo's sarcastic せいぜい (123, 143-145; 142 was done in scene 3), MEDIUM, done 2026-10-10
- [ ] 6. Rosea's Kadorto warning (130), MEDIUM: currently a question the player can't answer
- [ ] 7. First meeting, the wolfish man (13, 22), LOW-MEDIUM
- [ ] 8. Talk odds and ends (70, 173, 199), LOW
- [ ] 9. The switch puzzle (72-81), LOW

NPC_MES3 (Fontana, Cephala, Artemisia, Lilia, Zaril, Reiran)
- [ ] 1. Zaril walks out (75-89), HIGH: manzai quarrel that turns on Lilia siding with Zaril
- [ ] 2. Fontana's god-word hint (278), HIGH: 占い師 is the Diviner, as in Guy's line
- [ ] 3. The Sun statue (67-71), HIGH-MEDIUM: "Tablet of the Sun", the item's name
- [ ] 4. First meeting and goodbyes (0-18, 74), MEDIUM: "Little samurai" tag
- [ ] 6. Kikunoshin, the name that won't stick (193-194, 220-221, 229-230, 247-248, 255), MEDIUM
- [ ] 7. Reiran's reunion (9, 11), MEDIUM
- [ ] 8. Introductions, Cephala's "little girl" card (109-123, 236), LOW-MEDIUM
- [ ] 9. Zaril wants to be Evil (231, 249-250), LOW (231 shared with NPC_MES5 86)
- [ ] 10. Fontana's quieter lines (197, 237), LOW
- [ ] 11. The pit trap (90-108), LOW
- [ ] 12. Party-composition quips (33-66), LOW
- [ ] 13. Cephala's healing (132), LOW
- Scene 5 (Lilia wants out, 257-258) is done.

NPC_MES4 (Cleo, Cresson, Bergamot)
- [ ] 1. The reveal in the control room (44-54), HIGH: the story's climax
- [ ] 2. Cresson's epilogue (24-29), HIGH
- [ ] 3. The tea cakes (134-139), HIGH: comic timing
- [ ] 4. Bergamot's "old coot" running gag (72, 124, 148; 62), MEDIUM
- [ ] 5. Cresson's hints (111-113, 116, 119-120, 125, 140, 143), MEDIUM: pay off at the reveal
- [ ] 6. The research scenes and the tablet (22/23, 30-43), MEDIUM
- [ ] 7. Reactions to the player's party (9-21), MEDIUM
- [ ] 8. Introductions and repeat greetings (0-8, 56-63, 152-155), LOW
- [ ] 9. Gossip about the other parties (95-110), LOW
- [ ] 10. Healing and identify (64-83), LOW
- [ ] 11. Cresson's history lecture (150-151), LOW

NPC_MES5 (Zaril, Fritillaria, Gaura)
- [ ] 2. Introductions (26-34, 117, 122/123), HIGH: Zaril's faux-modesty about leading
- [ ] 5. The fight challenge (51-53), HIGH: one-sided argument, punchline timing
- [ ] 7. Zaril wants to turn Evil; Fritillaria's loyalty (63, 84, 86, 89, 90), HIGH:
      Fritillaria's rescue by Zaril, left ambiguous who abandoned him
- [ ] 3. Reputation greetings (13-25, 2/113), MEDIUM (17 shared with NPC_MES1 79)
- [ ] 4. Healing (114, 35-42), MEDIUM
- [ ] 6. Talk: news, reactions, other parties (98-102, 54-76), MEDIUM
- [ ] 8. Farewells (8-12), MEDIUM (11 shared with NPC_MES2 43)
- [ ] 9. The shadow's warning (103-106), MEDIUM
- [ ] 1. First sighting (0-7), LOW (0 shared with NPC_MES3 3)
- [ ] 10. Agan (112), LOW

## Open questions for Chris

- Fontana's nickname キクちゃん: "Kiku" or "Kiki"? And now that Alstron is "Al-chan",
  is "Kiku-chan" the consistent choice? (NPC_MES3 193, 194, 224, 226)
- Lilia calls Guy ガイルディア once (NPC_MES3 186): typo, or her not bothering to
  remember his name?
- Zaril's やあ、同輩 ("comrade", NPC_MES3 38 and NPC_MES5 25) and Cresson's ご同輩
  (NPC_MES4 20): what triggers them? If it's class or age, the English can say so.
- NPC_MES3 82: "Whose side are you on?" or "Don't encourage him!"
- Marguda and Arabik (NPC_MES4 12): a name easter egg; source unknown.
- Bergamot's ジジイ: "old coot" or "old geezer"?
- Fritillaria's ザリルさん: plain "Zaril", or "Mister Zaril" in his lines only?

## Other open items

- Unidentified monster names (DATA02/M_DT*.BIN, the disc's own English): "Flap
  Insect(s)" for the Giant Mosquito, Dragon Fly and Faerie Fly, and "Flap Figure(s)"
  for the Camazotz. All four are はばたくかげ ("flapping shadow") in Japanese. Settled
  2026-10-09: both names stay (Gaiden IV uses Flap Figure), and the plurals are fixed;
  see translation-notes.
- The body-recovery fees (docs/re/C-talk.md §5): Guy's
  party takes all the rescued characters' gold, Balbo's takes all their items, and
  Fontana's takes half the gold and every other item. Their offer lines sound
  generous, so check the irony when their scenes come up. Balbo's (NPC_MES2 142-145)
  was done 2026-10-10 ("Finders keepers").
  - Fontana, NPC_MES3 153: あなたたちもお人好しですね is "you're a trusting bunch"
    more than "soft-hearted"; お人好し leans toward "easy mark". And
    悪いようにはしませんから ("we won't do you wrong") is the classic reassurance of
    someone about to. The current "soft-hearted" and "We'll take good care of them"
    lose both. 151's ここだけの話 ("just between us") may be part of the same act.
  - Guy, NPC_MES1 163-165: 我々の好意として ("as our goodwill") in the offer, then
    いただけるところから,いただきますから ("we'll take what we can, from where we
    can") on yes. The current "We'll just help ourselves to our fee" is close; check
    that "as a favor to you" in 163 lands as the setup.
