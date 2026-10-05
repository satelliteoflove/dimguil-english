# LLM-habit sweep review (pre-announce item Q1)

Before the first public release, all the English was screened for habits that read as
machine-written, and the hits are being reviewed with Chris one at a time. This file
says where that review stands and how it's done, so a new session can pick it up cold.

## Pick up here

**37 of 37 reviewed (2026-10-04).** Every hit is approved and committed. The follow-ups
and the noted-in-passing items below are still open.

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

Chris named the unidentified monsters in hits 10-25 from the in-game catalog on
2026-10-04 (the names in the table are his). Portrait details he gave that may bear on
the text: the Crystal Man is tiny and alien-looking and barely fills the portrait; the
Fire Rock is a cyclops that looks like a blacksmith of Hell; Ixtah is a beautiful
cultist priestess.

Learned in this review:

- **Chris prefers close-to-literal versions** over smoother rewrites. Offer one every
  time.
- **Don't oversell.** Calling the Goblin Prince's "his class is Lord" a joke was a
  reach. Back any claim with precedent in the game's own text: the bestiary uses
  職業は… (his class is…) for the Kobold King, Orc Healer and Ogre Brother too, and
  職業 is the class word on the Training Grounds screens. When there's no evidence,
  say it's a reading.
- **Don't spoon-feed a joke the Japanese leaves implicit.** On the Guilty, Chris chose
  "making adventurers look the same" over spelling out the beheading: the developers
  left it for the reader to work out, and so should we. Spelling it out is fine when
  English players would otherwise miss a series reference the Japanese assumes (Murphy's
  Ghost, "over and over").
- **Check where names come from.** "Cutie Thief" is the developer's own English. It's
  on the untouched Rev 1 disc in the M_CATALG name table and in the MPT02/03 enemy
  records.

After approval, record anything notable (a liberty, a kept joke, a follow-up) in
`docs/translation-notes.md`. Apply with `python3 scripts/descwrap.py "<flat text>" --apply
translations/<FILE>.json SECTION INDEX`. Run `scripts/wtquotes.py check`, then commit
one hit per commit, with "Q1 sweep n/37" in the body.

Item refs don't map to item numbers by a fixed offset (I 1:5 is item 5, the Anointed
Mace; I 1:33 is item 34, the Bent Staff). Match the description against
`rips/tl/item_names.json` (Japanese and English names in item order) and the Bartok's
Trading Post item table (`data/items/dim/ps.json`, from Emonoya), which gives effects. Item
boxes are 144 px wide and 7 lines at most, but only **4 lines under a tall picture**
(robes, cloaks, full armor, polearms, long staves): `descwrap.py --width 144`, then
`scripts/itemfit.py`, which knows which items have tall pictures.

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
| 7 | M 9:17 | Astro Zombie (ロストワン) | "none can say" | Done: close to literal |
| 8 | M 10:8 | Beast | added "truly" | Done: close to literal |
| 9 | M 4:3 | Cyclops (inferred) | "Blessed with… without a trace of rage" | Done: close to literal |
| 10 | M 12:26 | Crystal Man | "untold power" | Done: swapped the phrase only |
| 11 | M 7:4 | Vorpal Bunny | "fangs loom" | Done: close to literal, "neck" for 首筋 |
| 12 | M 9:30 | High Zombie | "eyes burn with hostility" | Done: close to literal |
| 13 | M 12:15 | Mouth | "a being of pure mind" ("pure" added) | Done: close to literal |
| 14 | M 5:8 | Oserotoru | "Still," (contrast is implicit in the Japanese) | Done: close to literal |
| 15 | M 14:3 | Gremlin | "Proper gremlins… surely" | Done: close to literal, keeps the writer's "I" |
| 16 | M 14:5 | Ogre | "see it off" | Done: close to literal, stamina restored |
| 17 | M 8:8 | Were Amoeba | "Nasty business." | Done: Chris's rewording, fitted |
| 18 | M 11:9 | Chamalcan | "most unpleasant" | Done: close to literal |
| 19 | M 14:16 | Orc Lord | "Of the Orcs' ruling class stands…" | Done: close to literal |
| 20 | M 9:24 | Murphy's Ghost | broken "For him, being slain over and over, …" | Done: grammar fixed, "over and over" kept on purpose |
| 21 | M 9:11 | Guilty | "born of a guilty conscience made flesh" | Done: close to literal, joke left implicit |
| 22 | M 17:4 | Ixtah | "guards slip before her beauty" | Done: matches the 15:0 Mage's wording |
| 23 | M 9:5 | Vampire | "A bloodsucker, in short." | Done: "What you'd call a bloodsucker" |
| 24 | M 8:2 | Giant Spider | "the spider-woman of legend perhaps" | Done for now: "an arachne"; **follow up** (see below) |
| 25 | M 10:9 | Fire Rock | proverb carried over ("water on a hot stone") | Done: kept on purpose (it's a pun), quoted as in the Japanese |
| 26 | I 1:33 | Bent Staff | "An odd choice, but there it is." | Done: close to literal |
| 27 | I 1:278 | Ankh of Life | added pun "Vitality is a vital stat" | Done: close to literal |
| 28 | I 1:5 | Anointed Mace | added mirrored antithesis | Done for now; **follow up** (see below) |
| 29 | I 1:82 | Wizard's Yew Bow | "Out of magic mid-quest? This bow has you covered." | Done: Chris's wording |
| 30 | I 1:189 | B-Plate of Goodness (希望の胸当て) | added "of course" | Done for now; **follow up** (see below) |
| 31 | I 1:32 | Demon's Staff | added "the very" | Done for now: Chris's wording; **follow up** |
| 32 | I 1:31 | Sword of Slashing | "seasoned" | Done: Chris kept "seasoned" (the sword holds up in the deepest maze) |
| 33 | I 1:119 | Oodenta | cleaver/cleaving echo | Done: Chris's wording |
| 34 | I 1:179 | Emerald Robes | "rewarded" | Done: 使用者が制限される分 as "Few can wear it, so its powers are all the finer" |
| 35 | I 1:203 | Helm of Obitus | fragment "Not only cursed:" | Done: Chris's "modeled after that of" (というイメージ), full "Not only is it cursed, but" |
| 36 | I 1:126 | Excalibur | "only fair" | Done: 仕方のない as "there's no helping that"; 破壊力 restored |
| 37 | I 1:304 | Black Belt | "venerable" | Done: 上級者 is "advanced skill", not "mastery"; dangling "Even worn by a novice" fixed |

## Noted in passing, after the 37

These aren't LLM habits. They're accuracy and consistency points the deep pass turned
up. Take them after the 37, or fold them in where they share a string.

- **M 8:2, Giant Spider: follow up.** The Japanese says いわゆる女郎蜘蛛 ("what they call a
  jorōgumo"): both a common Japanese spider and a yōkai that appears as a seductive
  woman. The sprite has a woman's upper body on a spider's. "An arachne" went in on
  2026-10-04 as a stopgap. The options considered were "spider-woman" (plain and folksy,
  like the Japanese), "arachne" (the modern fantasy term, from Ovid's weaver) and
  "drider" (D&D's exact body, but drow and Lolth baggage). Chris wants this one
  given deeper thought before release.
- **I 1:5, Anointed Mace: follow up.** Chris approved "…Never touching the metal, they
  bring its tip down on a monster's skull." on 2026-10-04 but wants another look later.
  The Japanese: 自らは触れることなく、棒の先端につけた金属で、魔物の脳天に振り降ろす.
  It is at the 7-line limit, and the "they" refers back to the singular "the fighting
  cleric".
- **I 1:189, B-Plate of Goodness: follow up.** The Japanese name is 希望の胸当て,
  "breastplate of hope", and the description is about hope. The English name doesn't
  match, and Chris dislikes it. The description now says "Said to be filled with hope"
  (希望の込められた), which no longer clashes with the name, but the entry needs a second
  look together with the naming question below.
- **I 1:32, Demon's Staff: follow up.** Chris's wording went in on 2026-10-04: "Weak in
  direct combat, but when used as a magic item it summons demons as allies, making it
  more useful than an ordinary weapon." It leaves out three things the Japanese has:
  focusing the mind (精神を集中し), that these are the demons that plague adventurers
  (冒険者を悩ます悪魔達), and the "probably" (だろう). The Japanese:
  直接攻撃ではその力を発揮できないが、精神を集中し魔法のアイテムとして使用すれば、
  冒険者を悩ます悪魔達が味方となって召喚される。その効果は普通の武器よりも頼りになるだろう。
- **Naming question: the developer's English names.** Item and monster names follow the
  game's built-in English list (`docs/event-voice.md`). Chris's view (2026-10-04): the
  game was never released in English, so these names are almost certainly early,
  unpolished placeholders, not what a team localizing for the West would have shipped.
  Candidates so far: B-PLATE OF GOODNESS (希望の胸当て), BENT STAFF (ねじれた杖; Chris
  leaned toward "Twisted Staff", kept for now), Astro Zombie (ロストワン, below). A
  rename touches the inventory list (I_NAME_E), the catalog, Boltac's list and the
  battle copy of the names, and breaks the match with Emonoya and other guides.
- **M 9:17, Astro Zombie.** English players see "Astro Zombie" over a text about a name
  meaning "alone". The Japanese name is ロストワン, Lost One. This is a naming
  question for Chris.
- **M 10:24.** 邪教徒 is "heretics" here but "cultists" in 14 other entries.
  Done 2026-10-04 (Demon Baby, an inference): "cultists", and "still-clumsy breath" became
  "Its breath still comes out in fits and starts".
- **M 8:7.** 豹 (leopard or panther) became "jaguar". The English name is Were Jaguar,
  so this is probably fine; just confirm.
  Decided 2026-10-04: kept. The Japanese name is ワージャガー; 豹 covers ジャガー (アメリカ豹).
- **M 9:16.** "an ordinary human" became "an ordinary woman". It's fine if that entry is
  the female Vampire.
  Decided 2026-10-04: kept. The entry is Elizabeth (an inference from the catalog order),
  i.e. Elizabeth Báthory.
- **I 1:274.** The last "fiends" (魔族) in the game text. The event review replaced the
  others. Done 2026-10-04: "lesser demons should shatter to pieces"; 魔族 = demons in
  terms.md. Flagged for another look in translation-notes.
- **I 1:150, 1:151.** "steel" where the Japanese is 鉄 (iron). Same fix for both.
  Decided 2026-10-04: kept, because the item is named STEEL GLOVES; goes with the naming
  question in translation-notes.
- **I 1:296, Dragon's Tooth.** "spitefully whispers" dropped the hedge in その怨念からか
  ("perhaps out of its grudge"). Done 2026-10-04: Chris's wording, with "quietly" (そっと)
  and "perhaps out of spite" restored, and "rare treasure" back to "quite valuable".
- **I 1:24.** The Japanese entry holds two descriptions back to back (the battle axe and
  the nunchaku), and the English adds a flail sentence. Check what the game shows.
  Done 2026-10-04: two separate strings in game (Chris saw the Battle Axe's at 6 lines);
  the Nunchaka's two-line stub replaced with the full Japanese (Chris's wording).
