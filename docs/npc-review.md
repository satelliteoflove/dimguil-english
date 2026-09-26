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

The reviewers' reports quote the Japanese at length, so they stay out of the repo
(same policy as the redacted `source` fields). They live in `rips/review/` on the
build machine: `NPC_MESn.md` (the reports), `pending.json` (proposed English still to
review, in `npcfit.py --overlay` format), `approved.json` (what has been applied) and
`merged.json` (all proposals after syncing shared lines).

## Done

Guy's party (NPC_MES1) is finished: all 13 flagged scenes, plus the first-door scene.
See the `NPC dialogue:` commits from 2026-09-25/26. Along the way, Lilia's "scout me"
and age lines and her shady-man line were also applied to NPC_MES3, and Guy's party
turned out to be a Dragon Quest III party (see "Guy's party and Dragon Quest III" in
`npc-translation.md`).

Balbo's party (NPC_MES2): scene 1 (Balbo accidentally turns Good) is done.

## Next up

**NPC_MES2, scene 2: Alba's past (233, 180).** Proposed to Chris, not yet approved:
Rosea's あの人の苦しみを救ってあげたい as "I want to take that pain away from him..."
(the quiet hint she cares for him), and Alba's worry about Fontana's young party as
"With nobody but youngsters in it... will they be all right, I wonder......". Reiran's
"sword master" line (230) stays ambiguous, as in the Japanese.

## Remaining scenes

Priority as the reviewers ranked it. Numbers are string indices.

NPC_MES2 (Balbo, Rosea, Artemisia, Reiran, Alba, Gaura)
- [ ] 2. Alba's past (233, 180), HIGH, proposed (above)
- [ ] 3. Balbo's progress reports (81-89, 142, 261-265), HIGH: the Japanese is stiff
      and haughty here, unlike Balbo anywhere else. Needs a decision (open question 1).
- [ ] 4. Goodbyes when a party member is dead or lost (34-46), MEDIUM: sincerity, and
      Artemisia's flustered "see each other again" gag (also NPC_MES3 24-26).
- [ ] 5. Services: body collection offer, Balbo's sarcastic せいぜい (123, 142-145), MEDIUM
- [ ] 6. Rosea's Kadorto warning (130), MEDIUM: currently a question the player can't answer
- [ ] 7. First meeting, the wolfish man (13, 22), LOW-MEDIUM
- [ ] 8. Talk odds and ends (70, 173, 199), LOW
- [ ] 9. The switch puzzle (72-81), LOW

NPC_MES3 (Fontana, Cephala, Artemisia, Lilia, Zaril, Reiran)
- [ ] 1. Zaril walks out (75-89), HIGH: manzai quarrel that turns on Lilia siding with Zaril
- [ ] 2. Fontana's god-word hint (278), HIGH: 占い師 is the Diviner, as in Guy's line
- [ ] 3. The Sun statue (67-71), HIGH-MEDIUM: "Lithograph of the Sun", the item's name
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

- Balbo's progress reports: coarse Balbo voice, or keep the stiff register the
  Japanese has there? (NPC_MES2 scene 3)
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
  for the Camazotz. All four are はばたくかげ ("flapping shadow") in Japanese. Proposed:
  "Flying Insect(s)" and "Winged Shadow(s)" (17-character slots; "Fluttering Insects"
  doesn't fit), and fixing the plurals "Dragon Flys" and "Faerie Flys". Awaiting
  Chris's decision.
