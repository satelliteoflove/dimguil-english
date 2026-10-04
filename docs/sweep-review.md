# LLM-habit sweep review (pre-announce item Q1)

Before the first public release, all the English was screened for habits that read as
machine-written, and the hits are being reviewed with Chris one at a time. This file
says where that review stands and how it's done, so a new session can pick it up cold.

## Pick up here

**7 of 37 reviewed.** Hits 1-6 are approved and committed. Hit 7 (monster 9:17, Astro
Zombie) was presented on 2026-10-03 and is waiting for Chris's choice. Then continue
with hit 8 in the list below.

## What was swept

- `scripts/llmsweep.py` ran pattern checks over every `translations/*.json`, about
  45,000 words: stock LLM words and phrases, British idiom, dashes, triads,
  not-X-but-Y, semicolons, repeated phrases. It found no dashes and almost no stock
  vocabulary. The triads are nearly all genuine lists, and the repeated phrases are
  the game's own templated event text.
- The item (305) and monster (216) descriptions were then read line by line beside
  the Japanese. These two files had never had a second look. The Japanese bestiary
  and item text are chatty and wry themselves, so most asides that look like LLM
  habits ("Mothers are strong, it seems", "so enough praise", "Just a superstition,
  of course") are faithful and aren't hits.
- The event script was already reviewed line by line (`docs/event-review.md`), and
  the NPC files are covered by the NPC review (`docs/npc-review.md`), so neither was
  part of the deep pass.

The detailed findings are in `rips/review/q1-mcatalg.md` and `rips/review/q1-item.md`:
each hit with the Japanese, a literal reading and a suggested line. They're ignored by
git because they quote the Japanese. If they're missing, regenerate the side-by-side
text with `python3 scripts/llmsweep.py --pairs` and re-read the hits listed below.

## How a hit is reviewed

Chris's rule: **one hit at a time**. The only exception is when two hits take the exact
same fix (e.g. 1:150 and 1:151, steel to iron).

For each hit, show:

- **Which monster or item it is**, and say plainly when that's an inference. Catalog
  entries can't be mapped to names directly. The monster records in
  `rips/clean/dimguil/DATA02` (M_DT, MPT) carry English names and a catalog name
  index, which helps.
- **The Japanese, sentence by sentence**, with a literal reading.
- **The current English**, and what's off.
- **Context that bears on the decision**: the language, the culture, and the Wizardry
  world (especially V and Gaiden I-IV).
- **A close-to-literal English version**, fitted with `scripts/descwrap.py`. The
  catalog box is 108 px wide, and the longest existing entry is 13 lines.

Learned in this review:

- **Chris prefers close-to-literal versions** over smoother rewrites. Offer one every
  time.
- **Don't oversell.** Calling the Goblin Prince's "his class is Lord" a joke was a
  reach. Back any claim with precedent in the game's own text: the bestiary uses
  職業は… (his class is…) for the Kobold King, Orc Healer and Ogre Brother too, and
  職業 is the class word on the Training Grounds screens. When there's no evidence,
  say it's a reading.
- **Check where names come from.** "Cutie Thief" is the developer's own English. It's
  on the untouched Rev 1 disc in the M_CATALG name table and in the MPT02/03 enemy
  records.

After approval, apply with `python3 scripts/descwrap.py "<flat text>" --apply
translations/<FILE>.json SECTION INDEX`. Run `scripts/wtquotes.py check`, then commit
one hit per commit, with "Q1 sweep n/37" in the body.

## The 37 hits

Monster refs are section:index in `translations/M_CATALG.DAT.json`. The sections are
the catalog categories: 4 Giants, 5 Mythical, 6 Dragons, 7 Animals, 8 Beastfolk,
9 Undead, 10 Demons, 11 Insects, 12 Magical, 13 Mysterious, 14 Warriors, 15 Mages,
16 Thieves, 17 Priests. Item refs are section:index in `translations/ITEM.DAT.json`.

| # | Ref | Monster/item | Issue | Status |
|---|-----|--------------|-------|--------|
| 1 | M 7:15 | Heated Dog | "Indeed," for 事実 | Done: "Indeed" dropped |
| 2 | M 14:11 | sadist Fighter (likely Blade Master) | "Indeed,"; the hearsay dropped | Done: "said to… In fact," |
| 3 | M 14:14 | Goblin Prince | "Indeed, he's a Lord" | Done: close to literal, "his class is Lord" |
| 4 | M 16:5 | Cutie Thief | "Truly,"; opening fragment | Done: close to literal |
| 5 | M 16:2 | Goblin ninja (likely Goblin Assassin) | added "truly" and "indeed" | Done: close to literal |
| 6 | M 8:13 | Flack (inferred) | "shrouded in mystery" | Done: "largely a mystery" |
| 7 | M 9:17 | Astro Zombie (ロストワン) | "none can say" | **Proposed**, awaiting Chris |
| 8 | M 10:8 | Beast | added "truly" | |
| 9 | M 4:3 | | "Blessed with… without a trace of rage" | |
| 10 | M 12:26 | | "untold power" | |
| 11 | M 7:4 | | "fangs loom" | |
| 12 | M 9:30 | | "eyes burn with hostility" | |
| 13 | M 12:15 | | "a being of pure mind" ("pure" added) | |
| 14 | M 5:8 | | invented "Still," contrast | |
| 15 | M 14:3 | Gremlin | "Proper gremlins… surely" | |
| 16 | M 14:5 | | "see it off" | |
| 17 | M 8:8 | | "Nasty business." | |
| 18 | M 11:9 | | "most unpleasant" | |
| 19 | M 14:16 | Orc Lord | "Of the Orcs' ruling class stands…" | |
| 20 | M 9:24 | | broken "For him, being slain over and over, …" | |
| 21 | M 9:11 | | "born of a guilty conscience made flesh" | |
| 22 | M 17:4 | | "guards slip before her beauty" | |
| 23 | M 9:5 | Vampire | "A bloodsucker, in short." | |
| 24 | M 8:2 | Giant Spider | "the spider-woman of legend perhaps" | |
| 25 | M 10:9 | | proverb carried over ("water on a hot stone") | |
| 26 | I 1:33 | | "An odd choice, but there it is." | |
| 27 | I 1:278 | | added pun "Vitality is a vital stat" | |
| 28 | I 1:5 | | added mirrored antithesis | |
| 29 | I 1:82 | | "Out of magic mid-quest? This bow has you covered." | |
| 30 | I 1:189 | | added "of course" | |
| 31 | I 1:32 | | added "the very" | |
| 32 | I 1:31 | | "seasoned" | |
| 33 | I 1:119 | | added wry closer | |
| 34 | I 1:179 | | "rewarded" | |
| 35 | I 1:203 | | fragment "Not only cursed:" | |
| 36 | I 1:126 | | "only fair" | |
| 37 | I 1:304 | | "venerable" | |

### Hit 7, as presented

The Japanese opens 「たった一人」を意味する男, "a man whose name means 'just one
person'": the writer glossing the Japanese name ロストワン, Lost One. Two options:

- **Fix only the flourish** (recommended): "…yet the face beneath carries an air of
  loneliness. Whatever his purpose, his level drain steals adventurers' life force."
- **Closer to the Japanese throughout**: "A man known as 'the one alone'. Perhaps his
  hood is a life-support device; the face it covers has something lonely about it.
  Whatever his purpose, he drains adventurers' life force with his level drain."

## Noted in passing, after the 37

These aren't LLM habits. They're accuracy and consistency points the deep pass turned
up. Take them after the 37, or fold them in where they share a string.

- **M 9:17, Astro Zombie.** English players see "Astro Zombie" over a text about a name
  meaning "alone". The Japanese name is ロストワン, Lost One. This is a naming
  question for Chris.
- **M 10:24.** 邪教徒 is "heretics" here but "cultists" in 14 other entries.
- **M 8:7.** 豹 (leopard or panther) became "jaguar". The English name is Were Jaguar,
  so this is probably fine; just confirm.
- **M 9:16.** "an ordinary human" became "an ordinary woman". It's fine if that entry is
  the female Vampire.
- **I 1:274.** The last "fiends" (魔族) in the game text. The event review replaced the
  others.
- **I 1:150, 1:151.** "steel" where the Japanese is 鉄 (iron). Same fix for both.
- **I 1:24.** The Japanese entry holds two descriptions back to back (the battle axe and
  the nunchaku), and the English adds a flail sentence. Check what the game shows.
