# Translation notes

A running list of what the English had to fix and why, and what is waiting for another
look. Add to it as decisions are made. The detailed records stay in the review files
(`event-review.md`, `npc-review.md`, `sweep-review.md`); this file is the one place to
see all of it.

## Fixed, and why

### The game's own limits

- **Item descriptions under tall pictures (2026-10-04).** The item catalog draws the
  picture, then the description below it, and can't scroll. 55 items have a tall
  152x152 picture, which leaves room for 4 lines; the rest have a 152x108 picture and
  7 lines. The Japanese always fits. 25 English descriptions from the earlier work were
  cut off: 24 under tall pictures, plus 1:24, the doubled Battle Axe/Nunchaku entry, at
  8 lines. Chris caught it on the Emerald Robes. The picture for each item was
  identified one by one (the Bartok's Trading Post item table, checked against the
  pictures in ITEM.DAT), not guessed from the item type. `scripts/itemfit.py` holds
  every description to its own limit. Rule in `engine-notes.md`, "Item catalog".
  Rather than cut 24 descriptions to 4 lines, the text under tall pictures now starts
  9 px higher and the tall pictures were cut to 143 rows, so 5 lines fit. Only the item
  in each picture is moved or shrunk, laid back onto the panel's own parchment so the
  texture stays aligned (scaling whole pictures misaligned it, which Chris caught). Two
  descriptions are still over: the Sapphire Robes and 1:24. Chris checked all 55
  pictures in the game (`docs/q7-picture-check.md`): no visible flaws, and every other
  description fits.

### Machine-written habits (the Q1 sweep)

The English was screened for habits that read as machine-written, and 37 hits were
reviewed one at a time against the Japanese. Each fix is its own commit. The usual
problems:

- Added emphasis and asides: "Indeed," "Truly," "surely," "of course," "the very."
- Stock fantasy phrasing: "none can say," "untold power," "fangs loom," "eyes burn
  with hostility," "shrouded in mystery."
- Polished shapes the Japanese doesn't have: mirrored antitheses, a hook question
  ("Out of magic mid-quest?"), an added pun ("Vitality is a vital stat"), faux-epic word
  order ("Of the Orcs' ruling class stands the Orc Lord").
- British idiom: "see it off," "Nasty business," "Proper gremlins," "most unpleasant."
- Grammar: a dangling clause in Murphy's Ghost, sentence fragments.

The preferred fix is a close-to-literal reading, fitted to the box.

### Deliberate choices

- **Kept on purpose.** The Fire Rock's 「焼け石に水」 is a proverb for futility, kept
  word for word as 'water on a hot stone' because the monster literally is one. The
  Guilty's beheading joke ("making adventurers look the same") stays as implicit as the
  Japanese leaves it. The Gremlin keeps the writer's first-person "I'd think Thief would
  suit it." "Double damage vs X" stays as the item catalog's house shorthand.
- **Liberties.** Murphy's Ghost: "over and over" is added to spell out the Wizardry I
  experience-farming joke, which the Japanese only implies. The Vampire: the Japanese
  glosses the loanword バンパイア with the native 吸血鬼, which can't carry over when the
  name is already English, so it's "What you'd call a bloodsucker."
- **Consistency.** Ixtah (Catalog 17:4) uses the same Japanese as the Mage at 15:0, so
  both say adventurers "drop their guard."
- **Accuracy fixes found along the way.** The Vorpal Bunny goes for the neck (首筋), not
  the throat, which also suits its beheading. The Fire Rock's weakness is ice (氷系), not
  cold. The Ogre's stamina (体力) and the Beast's looks (姿) had been dropped.
- **Alstron, not "Alston".** The dialogue spells the priest アルストロン 59 times; only
  his battle record says アルストン, which earlier work rendered "Alston". Guy's party is
  named for plants (Gaillardia, Linaria, Lychee), and Alstron comes from Alstroemeria
  (アルストロメリア), so the dialogue's spelling is the one that carries the meaning.
- **Names stay the developer's English for now.** "BENT STAFF," not "Twisted Staff," and
  so on, pending the naming question below.

## To revisit

- **The developer's English names.** Item and monster names follow the game's built-in
  English list. Chris's view: the game was never released in English, so these are
  almost certainly unpolished placeholders. Candidates: B-PLATE OF GOODNESS (希望の胸当て,
  "breastplate of hope"), BENT STAFF (ねじれた杖; Chris leaned toward "Twisted Staff"),
  Astro Zombie (ロストワン, "Lost One"; its entry is about a name meaning "alone"). A
  rename touches the inventory list, the catalog, Boltac's list and the battle copy of
  the names, and breaks the match with Emonoya and other guides.
- **Other naming.** "Lithograph of the Sun" vs LITHOGRAPH OF SUN, and "labyrinth" vs
  "maze" for 迷宮 (checklist Q6).
- **Unidentified monster names.** "Flap Insect(s)" and "Flap Figure(s)" for はばたくかげ;
  proposed "Flying Insect(s)" and "Winged Shadow(s)", plus the plurals "Dragon Flys" and
  "Faerie Flys" (`npc-review.md`).
- **Catalog 8:2, Giant Spider.** 女郎蜘蛛 (jorōgumo) is "an arachne" as a stopgap;
  "spider-woman" and "drider" were the alternatives (`sweep-review.md`).
- **Item 1:5, Anointed Mace.** Approved but flagged for another look.
- **Item 1:32, Demon's Staff.** Chris's wording leaves out focusing the mind, "the demons
  that plague adventurers" and the "probably".
- **Item 1:189, B-Plate of Goodness.** Goes with the naming question.
- **Item 1:24.** The Japanese holds two descriptions back to back (Battle Axe and
  Nunchaku), and the English adds a flail sentence. It's also 8 lines, over the limit.
  Check what the game shows.
- **The 25 cut-off item descriptions** (Q7, above).
- **Events 234 and 236,** the Priestess's oracle: approved wording that may need another
  look (`event-review.md`).
- **Event 288,** the switch line: probably the Training Maze switch, where "set into the
  wall" is right. Confirm in play.
- **NPC open questions:** Balbo's register, "Kiku" or "Kiki", Lilia's ガイルディア, what
  triggers 同輩, Bergamot's ジジイ and others (`npc-review.md`, "Open questions for
  Chris").
- **Noted in passing in the catalog:** 邪教徒 is "heretics" once (10:24) and "cultists"
  everywhere else; 豹 became "jaguar" for the Were Jaguar (probably fine); "an ordinary
  woman" at 9:16; the last "fiends" (魔族) at item 1:274; "steel" for 鉄 (iron) at items
  1:150 and 1:151.
