# Event script review

The event script (translations/EVENTMES.BIN.json) is being reviewed with Chris scene by
scene, in play order, using the scenes in `docs/event-map.md`. This file says where the
review stands and how it's done, so a new session can pick it up cold.

## Pick up here

**Next: scene S29, the frost tank (EV 153, 127).** See `docs/event-map.md`.

## How a scene is reviewed

Chris reviews in chat, one scene at a time, and approves or rewrites each line. For
each scene show: its place in the story and anything it sets up or pays off (from the
map), the Japanese read literally, our current English, and a suggestion that fits the
box. Don't quote long Japanese in the repo; chat is fine. After approval, apply it,
run `scripts/evfit.py` (the only expected flags are string 36's extra page and
258's restored {ff30}2), and move on.
Before calling a line a joke or loosening it, search the Japanese for its key nouns
elsewhere; that's how the sticky paste (17, 44, 45) turned out to be a puzzle clue.

The rules are in `docs/event-voice.md`, and these are the ones Chris set during review:

- Present tense, second person, all the way through ("You touch the monolith, but
  nothing happens."). Past only for what happened earlier.
- Full sentences, no clipped fragments unless the speaker really talks that way.
- American English in idiom, not only spelling. A stuffy speaker may be British on
  purpose.
- Prompts are full questions: "Will you touch it?"
- Stay close to the Japanese; Chris often prefers the literal reading.
- 占い師 is the Fortune Teller everywhere.
- Don't consult or reuse the original team's removed translation.
- Only act on a suspected bug in the Japanese if it's corroborated (see the map's
  Translation traps).

## Done

Approved and applied (string numbers): S1 message boards 1-9; S2 the pillars 24-31,
48-51, 289-292; S3 the sun door 10-16; S4 the switch door 17, 42-45, 301, 302 (and
NPC_MES2 79-80 to match); S5 the star ceiling 18-21; S6 Murphy's Ghost 32, 52; S7 the
altar room 0, 35-38; S8 the jade mask 39-41, 293; S9 Shrine odds and ends 33, 34, 46,
47, 53, 54, 72, 73, 75, 227; S10 the moon door 80, 81; S11 the library 76, 106; S12 the
freezer 55, 64, 65, 79; S13 the lake machine 66-70, 77, 78, 280; S14 the blue stone
256-258 (258's green/blue slip fixed: blue, and its {ff30}2 put back); S15 the waterway
87, 88, 129; S16 "The sky fell" 105 (sky and earth, to match the Fortune Teller's SISETU
339); S17 the 2-Head Snake and the winding machine 71, 82-86; S18 the Shadow Golem's
statue 59-63 (no changes); S19 the central computer 58, 134-145; S20 STAFF and the white
stone 268-270; S21 the golden corpses 113-117, 281, 294-297 (281 keeps "remake our own"
for 同士; Chris found "comrades" wrong); S22 the green stone 262-267 (S14's wording); S23
the light altars and the crest doors 89-93, 95-98, 118-126, 133, 195 (94 is S49's
riddle); S24 the Jail Ogre's cage and the yellow stone 99-102, 196, 259-261; S25
LABORATORY 107, 219, 220; S26 the lab door and the black stone 156, 277-279; S27 the
warp switches 197, 306, 307 (keep the noun "switch" so the remark ties to the switch you
pressed; 248 waits for S55); S28 Zaril's party and the Chimera Warrior 150-152, 194 (152
"It's that thing!": やつ is the monster, not "him"). Also done early, out of scene order:
the murals 22 (SHIP) and 23 (DEATH), and 59 and 61 given the same wording as 35 and 36.

Every string also had the present-tense sweep and full-question prompts applied, so
unreviewed strings are consistent but not yet approved.

## Waiting for their scene

- 130: "Don't forget full gear" ties back to board 1, which Chris rewrote as "Did you
  equip your gear?" (the Japanese asks whether you've forgotten any). Raise whether
  board 1 should keep the "forget" link.
- 174-176: "rubbish" (British) in the rubbish-room strings; use "trash" or "junk".
- Naming across files: the NPC files say "Lithograph of the Sun" and "the Sun tablet"
  where the event script says LITHOGRAPH OF SUN; 迷宮 is "labyrinth" in some event
  strings and "maze" elsewhere. Settle these.
- 282-285 (Guardians): 280's intro became "We are the Guardians who rule this land."
  with no comma; 281 matches, and the other four share that intro and should too. Chris decided
  not to carry the contempt of 貴様ら; plain "you" throughout.

## After the event script

Commit it as reviewed, update ROADMAP.md and the README progress, then v0.8.0 when Chris
tags. The new repo and its name are pending (ROADMAP "Project identity").
