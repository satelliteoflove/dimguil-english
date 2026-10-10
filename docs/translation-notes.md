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
  7 lines. The Japanese always fits. 24 English descriptions from the earlier work were
  cut off, all under tall pictures. (1:24 looked like a 25th at 8 lines, but it holds two
  separate strings, the Battle Axe's and the Nunchaka's, and each fits.) Chris caught it on the Emerald Robes. The picture for each item was
  identified one by one (the Bartok's Trading Post item table, checked against the
  pictures in ITEM.DAT), not guessed from the item type. `scripts/itemfit.py` holds
  every description to its own limit. Rule in `engine-notes.md`, "Item catalog".
  Rather than cut 24 descriptions to 4 lines, the text under tall pictures now starts
  9 px higher and the tall pictures were cut to 143 rows, so 5 lines fit. Only the item
  in each picture is moved or shrunk, laid back onto the panel's own parchment so the
  texture stays aligned (scaling whole pictures misaligned it, which Chris caught). One
  description was still over: the Sapphire Robes. Chris checked all 55
  pictures in the game (`docs/q7-picture-check.md`): no visible flaws, and every other
  description fits. The Sapphire Robes was then cut to 5 lines (Chris's wording, which
  also fixes "cold" to ice for 氷). Every description now fits.

- **The training maze sign (SISETU 492, 2026-10-07).** The sign's box holds as many
  glyphs as the game gives it, and the game gave it 172, one more than the Japanese.
  Chris caught it in play (the text stopped at "but as a b"). The box now gets 177 and
  the text was reworded to fit, in Chris's words, with "Summoned monsters" keeping the
  summoning system from 特殊な魔物召喚システム: "Underneath the Fortress City is this
  maze, made to train young adventurers. Summoned monsters keep coming, so earn all the
  experience you can. There's no gold or items dropped, but anyone wiped out is sent to
  the temple free of charge." It dropped "as a bonus" (特典付き). Chris confirmed it in play, along with the
  return prompt ("Press △ to return to the Fortress City.", SISETU 442).

- **Event lines off center (2026-10-07).** The event box centers each line, spaces
  included. 26 event strings still carried the Japanese padding on one side, so their
  lines printed off center; the Guardians' speeches (280-285) were 7 spaces right. The
  padding is gone. Found by printing all 317 event strings through the real box
  (`scripts/evsweep.py`): every page printed in full.

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
  cold. The Ogre's stamina (体力) and the Beast's looks (姿) had been dropped. The Black
  Belt marks "advanced skill" (上級者), not "mastery": in Japan a black belt is a
  competent student, and the Japanese doesn't repeat the Western idea that it means a
  master. Excalibur's two hands are a shrug at a drawback (仕方のないことだろう), not "only
  fair."
- **The Nunchaka (item 25) had a two-line stub.** The earlier English was "A strange
  Eastern flail of two linked rods", dropping two of the three Japanese sentences. Now
  the full text, with Chris's "flail" for メイス: the game files it under maces, but that
  menu also holds whips and clubs, and flail is what it is. The "precision machine"
  classes (精密機械のように戦闘に長けた職業) are Ninja and Monk, the only two that can equip it.
- **Elizabeth (catalog 9:16) is Elizabeth Báthory,** the "Blood Countess" said to have
  kept her youth with young women's blood. 普通の人間 stays "an ordinary woman": she's a
  woman, and "human... her" would read oddly. Checked and kept.
- **The Were Jaguar (catalog 8:7) stays a jaguar.** 豹 is strictly leopard or panther,
  but the Japanese name is ワージャガー, and dictionaries gloss ジャガー as アメリカ豹, so
  豹 is just the kanji to hand. Jaguars also suit the game's Maya borrowings (Camazotz,
  Gucumatz, Mictlan, Ixtah). Checked and kept.
- **The Demon Baby's breath (catalog 10:24).** まだどこかおぼつかないブレス had been "still-clumsy
  breath". おぼつかない is the word for a toddler's wobbly first steps, and ブレス is the
  games' loanword for a breath weapon, not 息 or 呼吸. Japanese parenting sites and forums
  describe a newborn's real breathing as irregular, fast then slow, with pauses, and never
  use おぼつかない for it. So the line is about a newborn's breath attack that hasn't
  steadied yet: "Its breath still comes out in fits and starts." Same entry: 邪教徒 is
  "cultists", as in the other 14 entries, not "heretics".
- **Alstron, not "Alston".** The dialogue spells the priest アルストロン 59 times; only
  his battle record says アルストン, which earlier work rendered "Alston". Guy's party is
  named for plants (Gaillardia, Linaria, Lychee), and Alstron comes from Alstroemeria
  (アルストロメリア), so the dialogue's spelling is the one that carries the meaning.
- **Names stay the developer's English for now.** "BENT STAFF," not "Twisted Staff," and
  so on, pending the naming question below.

- **Relationships, not just voices (NPC scene 2, Alba's past, 2026-10-05).** Each
  character's stock type and speech habits aren't enough on their own; how characters
  stand toward each other changes the lines too. Rosea calls Alba あの人 (also how a woman
  speaks of a man she's close to) right after saying he rescued her, so "I wish I could
  ease his suffering" became "I want to take that pain away from him." Alba's worry
  for Fontana's young party comes from a man who lost his own, so it's fear for their
  safety ("Will they be all right, I wonder"), not doubt about their skill.
- **"Companions," not "comrades" (2:231).** Chris: "comrade" carries a connotation for
  American players that doesn't fit. Balbo's 仲間 is now "companions"; the other uses
  are listed under To revisit.
- **The leaders' maze-encounter voice (NPC scene 3, Balbo's progress reports,
  2026-10-05).** When Balbo's party meets you in the maze, the Japanese drops his own
  voice (俺様, ねぇ, チッ) for a stiff, superior one: 君たち, 〜たまえ, 〜かね, 我々. The
  first draft called it a writer's slip. Chris questioned that, and a check found
  Fontana, polite everywhere else, shifts the same way in his maze encounters (3:72,
  75, 88, 278), so it looks like one writer's stock voice for party leaders. That's
  deliberate, though not about Balbo in particular. It isn't the careful-speech shift
  Japanese has, which goes toward politeness (です/ます); this goes toward a boss
  talking down. The English meets it halfway: Balbo keeps his words ("ain't", "ya",
  "you lot", "them"), but the grammar is complete, the g's stay on, and the orders are
  clipped ("Sorry, but this is a strategy meeting. Don't interrupt."). 2:264-265 also
  lost a sneer the old English had added ("beyond the likes of you"); the Japanese is a
  warning.
- **Artemisia's "see each other again" (2:44 and 3:25).** また会いましょうね is an
  ordinary friendly parting, and her next line is "Oh gosh, what am I even saying?"
  The Japanese joke is that she hears her own warmth as too forward. "Let's meet
  again sometime" gave an English reader nothing to blush at, so it's now "I hope we
  can see each other again!", innocent on its face but open to the dating sense. Her
  goodbye for a dead party member (2:46, 3:24) keeps "let's meet again sometime",
  since no fluster follows it.
- **Alstron's book stays unnamed (1:238).** The Japanese says 例の書物, "that book,
  you know the one", and leaves the Dragon Quest III player to recognize the Book of
  Satori. Naming it in English spelled out a joke the original only winks at, so it's
  "that book to the temple. You know the one." See "Guy's party and Dragon Quest III"
  in `npc-translation.md`.

- **"Music," not "Sound" (STATUS 67, MESSAGE 254).** The settings screen's サウンドの有無
  is literally "sound on/off", which sat next to "Sound Output" and "Sound Effects"
  with no way to tell them apart. Measured in the emulator: switching it off silences
  the music and leaves the menu sounds playing. エフェクトの有無 stays "Effects".
- **English only: the "Jpn" name switches are locked (2026-10-08).** The settings
  screen offers Japanese or English names for items, monsters and spells, and for the
  status words. The English font took the kana's place, so "Jpn" drew the Japanese
  lists as a jumble of kanji and Latin letters (`castle-sweep-review.html`, section 8).
  Keeping both working would have needed the original font loaded alongside the English
  one and every text routine taught to switch between them. Chris decided the patched
  game is English-only: the switches can't be moved off "Eng" on any of the three
  settings screens (Edge of Town, the maze's camp, a card battle), and loading a save
  that says Japanese gives English. "Jpn" stays on screen, dimmed.
- **The card game's level-up arrow (2026-10-09).** A card's level-up screen compares
  each stat as "1 → 2", but it showed "1 A 2". The arrow is a Shift-JIS string in
  CMAIN.BIN, which the card game converts to the Japanese font's arrow cell, and in
  the English font that cell is the letter pair "A " (as in "A Cot"). The original
  arrow is now drawn into an empty cell (0xb9, a 31 px blank nothing used), and the
  string is "_", which the converter sends there. MESSAGE 274, a "→" between two
  numbers that the crawl never showed on screen, encodes there too. Found by the card
  game crawl.
- **Card battle mode labels: AUT and MAN (2026-10-09).** In a card battle, square
  shows a mode label over each card. "AUTO" and "MANU" are as wide as the gap between
  cards, so the four ran together ("MANUMANUMANUMANU"). Chris chose "AUT" and "MAN";
  the AUTO/MANUAL menu keeps its full words (`cb_strings.asm`).
- **Card game spell names (2026-10-09).** The card game's spell table carries the
  developer's own English, and three differ from the main game's built-in spell list
  (STATUS 222-305), which `terms.md` follows: Kadolto, Nagura and Rios are now
  Kadorto, Nagula and Lios, as the unit names were matched before (`cb_strings.asm`,
  both copies). They show in battle as "Nagula was cast".
- **Halycon stays Halycon (Chris, 2026-10-09).** It looks like a misspelling of Halcyon,
  but it's the series' own name. Sir-Tech's Wizardry V: Heart of the Maelstrom has a
  monster called "Halycons" (number 119 in the SNES bestiary, among the Manes and
  Greater Fiends), and the Japanese Wizardry V gave it as ハリコン, the katakana Dimguil
  uses. Wizardry Gaiden: Five Trials reuses the Wizardry V picture as ハリコン / Halycon
  (Halycons): a white demon whose upper body rises out of a whirlwind. Dimguil's entry
  (M_CATALG 806; built-in names 453 and 672) keeps the wind theme. The Greek halcyon,
  a bird that calms the winds, doesn't fit this sickle-wielding wind spirit anyway.
  Sources: the GameFAQs bestiary PAR codes for Wizardry V (SNES, faqs/29262), the
  Five Trials atwiki monster list (w.atwiki.jp/wiz-fo/pages/27.html, picture 202), and
  Bartok's Trading Post's monster data, which has Halycon(s) in the Apple II Wizardry V
  (`data/monsters/5/ap.json`) and the Game Boy Color Wizardry (`data/monsters/2/gbc.json`,
  あくま "Demonic Figure" unidentified).
  Before calling any developer name a misspelling, check whether an earlier Wizardry
  uses it.
- **Misspelled names fixed (Chris, 2026-10-09).** Four of the developer's English
  names were plain typos with nothing behind them in the series (see "Series spellings
  checked"):
  - Dragonare is now Dragonaire, Wizardry V's spelling (GameFAQs SNES bestiary, number
    115; Five Trials picture 176). The untouched card game also says Dragonare; its
    "Dragonaire" is ours (`cb_strings.asm`, MESSAGE.DAT).
  - DISPLASER ROBE (身かわしの衣) is now DISPLACER ROBE, as in Wizardry VII's
    Displacer Cloak.
  - Old Drumer (オールドドラマー) is now Old Drummer.
  - "Small Silhoutte(s)", an unidentified name, is now "Small Shadow(s)". The right
    spelling doesn't fit: each name slot holds 16 glyphs, "Small Silhouettes" is 17,
    and these fonts have no letter pairs to save room. The Gremlin and Cutie Thief
    records also put a two-byte line break in the name, so even "Small Silhouette" is
    17 there. Small Shadow is the literal ちいさなかげ, the Japanese behind most of
    them, and it keeps "Small". "Tiny Silhouette(s)" fit too and was tried first; Chris
    dropped it because none of these monsters is tiny. The developer used the one name
    for four Japanese ones, and they stay merged: ちいさなかげ (Mad Monkey, Vorpal
    Bunny, Magical Rabbit), はいずるぶったい "crawling thing" (2-Head Toad, Fang),
    ひとがたのほのお "human-shaped flame" (Fire Rock) and ちいさなけもの "small beast"
    (the Gremlins, Cutie Thief). Making room was considered and dropped (Chris): the
    Japanese slots are dead since the English lock, so the game could be pointed at
    them, but that means changing the name-fetch code and every record. Measured over
    all 682 distinct English names in the monster and party records, this is the only
    one that ever needed more than 16 glyphs; 13 of the developer's names fill all 16
    (Skeleton Warrior, Giant Mosquitoes...) and none looks cut short, nor differs from
    the Compendium's separately stored list.

  Each name has several copies: the Compendium's name lists (M_CATALG), the item lists
  (I_NAME_E twice, ITEM.DAT, the card game's MESSAGE.DAT), the monster records in
  DATA02 (`scripts/namefixes.py`) and BATTLE.BIN's own two records
  (`asm/name_fixes.asm`). ITEM_CA.DAT keeps DISPLASER; the game doesn't load it.
- **Mesoamerican names in the Mythical list (Chris, 2026-10-09).** Bartok's Trading
  Post's monster data for every Wizardry it covers (I-VII, Gaiden I-IV, BUSIN and
  others) has no precedent for them; only Dimguil has them, so they follow the Nahuatl:
  - Shocitnal (ショチトナル, "a crocodile monster said to dwell in hell") is now
    Xochitonal, the Aztec iguana or crocodile that guards the waters on the way to
    Mictlan, the land of the dead. The katakana reads Xochitonal.
  - Three of the four temple guardians are Aztec day signs: Oserotoru is now Ocelotl
    (jaguar; the game's tiger), Inkuintori is now Itzcuintli (dog) and Kuautori, which
    the battle records spell Cuautori, is now Cuauhtli (eagle; the game's bird).
    Oserotoru and Kuautori were the katakana romanized; Inkuintori was a garbled
    Itzcuintli. The fourth, Coatl (serpent), and Quetzalcoatl were already right.
  - Chany Mask (チャニーマスク, the red mask that works a naked warrior's body; drops
    the Jade Mask) stays: no source for "Chany" turned up outside Dimguil and Emonoya,
    which uses the same spelling.
  - Death Hawk matches Gaiden III and IV. Stone Head is the developer's English for
    9ヘッド ("9 Head") and is fine.
  Sources: the Online Nahuatl Dictionary (nahuatl.wired-humanities.org, Xochitonal) and
  the day-sign list on Wikipedia's Tōnalpōhualli page.
- **Flap Insect and Flap Figure stay; the -y plurals are fixed (Chris, 2026-10-09).**
  Both are unidentified names for はばたくかげ ("flapping shadow"): Flap Insect(s) for
  the Giant Mosquito, Dragon Fly and Faerie Fly, Flap Figure(s) for the Camazotz. Flap
  Figure is the series' own: Wizardry Gaiden IV (SFC) uses "Flap Figure(s)" for
  はばたくかげ on its bats, bees, crows and faeries (Bartok's Trading Post,
  `data/monsters/g4/sfc.json`), and Flap Insect is Dimguil's insect version of it. So the
  earlier proposal, Flying Insect(s) and Winged Shadow(s), is dropped. The plurals were
  plain errors: Dragon Flys, Faerie Flys, Vorpal Bunnys, Beautys and Stone Sentrys are
  now Dragon Flies, Faerie Flies, Vorpal Bunnies, Beauties and Stone Sentries. Dragon
  Flies (Wizardry I, II, IV and VI) and Vorpal Bunnies (Wizardry I and others) are the
  series' plurals. 17 slots in DATA02 (`scripts/namefixes.py`).
- **The rest of the bestiary (Chris, 2026-10-09).** Of 249 distinct Dimguil monster
  names (records, unidentified names and the Compendium list), 96 appear in another
  Wizardry in Bartok's Trading Post's data. Of the rest, the Maya names match the Popol
  Vuh as Recinos spells them: Ahalmez, Ahalpuh, Chamiabac, Chamiaholom, Cuchumaquic,
  Camazotz, Gucumatz, Holom-Tucur, Iqui-Balam, Ixquic, Ixtah (the maiden sent to
  seduce the gods), Tamazul, Tucumbalam, Vucub-Caquix, Xecotcovach; Chamalcan is the
  Kaqchikel bat god. Fixed, as the sources spell them:
  - Web Spiner (ウェブスピナー) is now Web Spinner, a typo.
  - Sopirote (ソピローテ, the skull-faced bird of ill omen) is now Zopilote, Mexican Spanish
    for the black vulture.
  - Uthiu (ウティウ, the two-headed coyote) is now Utiu, the Popol Vuh's coyote (Utiú, Utiw).
  - Ispusteke (イスプステケ, Hell's ripper) is now Ixpuztec ("Broken Face"), a being of
    Mictlan; the katakana follows the Spanish Ixpuzteque.
  - Neshuteper (ネシュテペア, the old man who scatters ash) is now Nextepehua, "Scatterer of
    Ashes", another being of Mictlan.
  - Tepeyoryotl (テペヨリョトル, a high Monk) is now Tepeyollotl, "heart of the mountain",
    the Aztec jaguar god.
  - Allo Saurus (アロサウルス) is now Allosaurus.
  - スメリア, the Alchemist consumed by its potions, was "Smelia" in battle and
    "Stink Man" in the Compendium (both in the original game). The Compendium now
    says Smelia too.
  The party pictures break two of them across lines; the breaks fall where the
  Nahuatl words meet: Nex/tepehua ("ash"/"scatterer"), Tepe/yollotl ("mountain"/
  "heart"). Compendium list and 28 record slots (`scripts/namefixes.py`).
  Left alone: the developer's own inventions (Hims, Kel, Lala, Ugo, Gigatops...),
  Xicalli, Mictlan, Chai-zanic (no source found), Goblin Canon (a Priest; canon as in
  clergy), and Demon Liche / Dragon Liche (an old spelling of lich).

## To revisit

- **Fontana's maze encounters (3:72, 75, 88, 278).** Same register shift as Balbo's
  reports. Handle them the same way when NPC_MES3 is reviewed: his own words, a little
  more in charge.

- **The developer's English names.** Item and monster names follow the game's built-in
  English list. Chris's view: the game was never released in English, so these are
  almost certainly unpolished placeholders. Candidates: B-PLATE OF GOODNESS (希望の胸当て,
  "breastplate of hope"), BENT STAFF (ねじれた杖; Chris leaned toward "Twisted Staff"),
  Astro Zombie (ロストワン, "Lost One"; its entry is about a name meaning "alone"). STEEL
  GLOVES (鉄の小手, "iron gauntlets"): the item text otherwise keeps 鉄 as iron and 鋼 as
  steel, but 1:150 and 1:151 say "steel" to match the name; a rename to Iron Gloves
  would switch both. A
  rename touches the inventory list, the catalog, Boltac's list and the battle copy of
  the names, and breaks the match with Emonoya and other guides. Some are plain
  misspellings that should be fixed whatever is decided about the rest: Chris spotted
  "Displaser Robes" for Displacer Robes in the catalog. Chris can't stand leaving them
  in, though he isn't sure how the community will take fixing them; to be dealt with
  later.
- **Series spellings checked (2026-10-09).** Before calling a developer name a typo,
  check the earlier games (see "Halycon stays Halycon"). Of the names in the
  known-issues list:
  - NUNCHAKA (ヌンチャク) is Sir-Tech's spelling: the Nunchaka is a Ninja weapon in
    Wizardry VI (145 gold, 1-5) and Wizardry VII (800 gold, 3-9), per the tk421.net
    item lists. Not a typo.
  - Maelific (マイルフィック), listed as a typo in the roadmap, is Wizardry I's demon.
    Not a typo.
  - Dragonare (ドラゴネア), Displaser Robe, Old Drumer and Small Silhoutte are typos,
    now fixed (see "Misspelled names fixed" above), as are the Mesoamerican names in
    the Mythical list.
- **Other naming.** "Lithograph of the Sun" vs LITHOGRAPH OF SUN, and "labyrinth" vs
  "maze" for 迷宮 (checklist Q6).
- **Catalog 8:2, Giant Spider.** 女郎蜘蛛 (jorōgumo) is "an arachne" as a stopgap;
  "spider-woman" and "drider" were the alternatives (`sweep-review.md`).
- **Item 1:5, Anointed Mace.** Approved but flagged for another look.
- **Item 1:32, Demon's Staff.** Chris's wording leaves out focusing the mind, "the demons
  that plague adventurers" and the "probably".
- **Item 1:189, B-Plate of Goodness.** Goes with the naming question.
- **Item 1:274, Amulet of Matokani.** Approved close to the Japanese ("lesser demons
  should shatter to pieces"), flagged for another look. 魔除け is a demon-warding charm,
  so a demon ward that kills demons; the English "amulet" can't carry that. Matokani
  looks like MAKANITO with its syllables rotated (an inference).
- **Events 234 and 236,** the Priestess's oracle: approved wording that may need another
  look (`event-review.md`).
- **Event 288,** the switch line: probably the Training Maze switch, where "set into the
  wall" is right. Confirm in play.
- **Other uses of "comrade"** (see 2:231 above): the talk-menu line "We asked them to
  rescue our comrades." (仲間, in all five NPC files: 1:301, 2:269, 3:281, 4:165, 5:116),
  Zaril's "Hey there, comrade." (同輩, "fellow" or "peer"; 3:38, 5:25, tied to the open
  question of what triggers it), SISETU 367 (a townsman's "my old comrades are all
  dead", 昔の仲間) and item 1:290, the Book of Life ("revive a comrade").
- **NPC open questions:** Balbo's register, "Kiku" or "Kiki", Lilia's ガイルディア, what
  triggers 同輩, Bergamot's ジジイ and others (`npc-review.md`, "Open questions for
  Chris").
- **Stat changes, SISETU 67-78** (2026-10-07): the second set of stat messages (力を 得た
  … 運の強さを 失った) was still Japanese after the original team's text came out. They
  now repeat 44-55 ("Strength rose." … "Luck fell."). 44-55 show at the training
  grounds. Seen at the inn in the emulator: a level-up there prints them in English and
  they match the stat changes ("I.Q. rose." with Int 5 to 6, "Piety fell." with Pie 5
  to 4). Chris confirmed them in play too.
- **One-word last lines in event text** (seen in the 2026-10-07 sweep): "attacks."
  (48-51), "room." (67), "now?" (68), "happens." (135), "wall." (149), "monster." (150,
  194), "the hollow." (258 and others). They read fine; rebalancing the breaks would
  look better.
- **Event 6,** the moving-floor board: "Work out how the moving floors behave," ends a
  page and "and don't forget the mask!" starts the next. The Japanese is two sentences
  (移動床の法則を見つけ出せ! / 仮面をお忘れなく!).
- **The readme and the release announcement should say the patch is English-only**
  (2026-10-08). The four language switches are locked on "Eng" (see "English only"
  above), so a player who expects the Japanese names to still be there needs telling.
- **Long item names crammed in the catalog list** (found 2026-10-08). Names over about
  10 letters wrap to a second line 6 px lower and touch the next name; 170 names wrap.
  These are the developer's uppercase names, so the original likely does the same.
  Left as they are (Chris, 2026-10-09): fixing it is a bigger job than it's worth, and
  the names still read.
