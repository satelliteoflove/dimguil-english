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

- **Lines with `"` or "w " off center, and "b  away" (2026-10-13).** The game's line
  measures skipped those two glyphs as Japanese voicing marks, so 81 event lines and the
  Inn's "Learned new spells." sat 2-12 px right of center, and two printers still merged
  them into the glyph before ("Ocelotl tries to b  away" in battle). Fixed in
  `asm/voicing_marks.asm`; found by the T5 screen checks. Details in `writeup-notes.md`.

- **Battle lines ending in a digraph's space (2026-10-13).** "Giant Ant calls for help! A /
  monster appears." sat 2 px left; a break after "A ", "s " etc. now draws the letter alone (`asm/word_wrap.asm`).

- **Monster abilities with no target (FIGHTMSG 214, 2026-10-15).** A monster's attack
  verb is written for the targeted line, "Basilisk glares at Venus with its many eyes."
  (108/109). An ability (a shriek, a dance, a gaze: an attack noun of 683 or more) prints
  214 instead, "{monster} {verb} {noun}." with nobody named, so the same verbs gave
  "Ghost startles a shriek.", "Merry Puppet tries to lull a strange dance.", "Were Bat
  glares at a piercing glare." and "Giant Spider tries to entangle sticky goo.". The
  Japanese reads fine both ways (ゴースト は 金切り声 で 驚かせた), because the particle
  sits in the verb. Which template prints is fixed per attack by its noun (code in
  `engine-notes.md`, "Battle text and monster files"), so the fix is data: the abilities
  got targetless verbs of their own in FIGHTMSG 61, 65-71 and 74, which the game never
  printed (65-71 are 未使用), and their verb bytes point there (82 attacks in 69 monster
  and party files, `binary/*.verbs.json`, written by `scripts/re/attackverbs.py
  --write`). Verbs 46 and 76 were only ever used by abilities, so they were reworded in
  place. Against the party most abilities hit one row, a few one member and five the
  whole party (the table is in `engine-notes.md`), and the line can't say which, so the
  object is "them", as the Japanese leaves it unsaid. Chris chose "them" over "everyone"
  (2026-10-15): it's right for a row, and it also reads right when summoned undead or
  other creatures fight on the party's side. The lines are now "Ghost startles them with
  a shriek.", "Merry Puppet tries to lull them with a strange dance.", "Wight glares at
  them with piercing eyes.", "Giant Spider tries to entangle them in sticky goo.",
  "Smelia tries to melt them with eerie smoke.", "Succubus flashes a sultry look.",
  "Mictlan stares with hollow eyes." (its Badi hits one member; slot 61), "Greater Golem
  fires BIG GUN.", "Nex tepehua throws ASH OF CONFUSION.", "Old Drummer beats DEVIL'S
  DRUM.", "Noisy Tempter plays VIOLIN OF MADNESS." and "Lilia plays LUTE."; Venus Man
  Trap's pollen uses the existing "sprays" (55), like Fire Rock's red-hot stones. The
  abilities' glare nouns (I_NAME_E 705, 707, 709, 713, 鋭い目付き) became "piercing
  eyes", so the line doesn't say glare twice. The melee one, 665 (鋭い目つき, the same
  word, used only with "glares at" by Fear, Medusa and Kel), followed on Chris's ask:
  "Fear glares at Uranus with piercing eyes." instead of "...with a piercing glare.". The
  three instrument attacks had pointed at the party's whole-sentence instrument lines
  (60, 63, 64); the codes inside them print nothing there, so they read "Noisy Tempter
  plays . VIOLIN OF MADNESS." and "Lilia strikes up . LUTE.".

- **Inn and Temple lines off center (2026-10-13).** "Not enough gold." sat 9 px left (x fixed for the
  Japanese, `asm/inn_gold_message.asm`); the Temple's chant 10 px (`asm/temple_layout.asm`).

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

- **Attack verb 9 is "bashes" (FIGHTMSG 9, を 打ち降ろした; Chris, 2026-10-12).** The
  battle line is "{attacker} {verb} {target} with {weapon}.", and the Japanese verb takes
  the weapon as its object, so "brings down on" read oddly ("Cy brings down on Giant
  Mosquito with ANOINTED MACE."). Now "Cy bashes Giant Mosquito with ANOINTED MACE."
  "ANOINTED" is spelled right (anoint, one n before the o); it's the disc's own English
  item name. Found by the harness.
- **"There's no trap" has no full stop (FIGHTMSG 221, 罠は かかっていない; Chris,
  2026-10-12).** It's the first name in the trap list (221-233), and a fumbled chest
  inspection prints "Oops! {trap}!!" (242), so the full stop gave "Oops! There's no
  trap.!!". The Japanese has none, and neither do the other trap names. Found by the
  harness (rips/harness/t2/issues/oops_no_trap.png).
- **"Hits 1 times!" stays (FIGHTMSG 118, {ff11}0回 Hit!; Chris, 2026-10-12).** One string
  serves every count, so a single hit reads "Hits 1 times!". The Japanese gets around it
  because 回 works for any number. "Hit ×{n}!" was considered and dropped: the plural-less
  "HITS 1 TIMES" is a Wizardry tradition (from memory of the early games, not checked
  against a disc). Found by the harness's text capture (harness-plan.md, T1).
- **"EVENT Item" is now "Event Item" (SISETU 604; Chris, 2026-10-12, decisions.md item
  16).** The disc's own English on the item details screen (Boltac's and camp Identify on
  an identified item), shown for category 6-7 items other than instruments, potions and
  scrolls: event items, specials, monster cards. Every other label there is Title Case
  ("<Alignment>", "Male / Female"), so "Magic Item" (603) stays and only the capitals
  went. Built and decoded from the disc image (8e03a3f); not seen on screen, since the
  test party carries no such item. 601/602 are the Japanese-mode labels and never show
  in English (`config[3]`). Shot of the screen: rips/re/work/P3-label/itemdetails/bi_02.png.
- **"Retrain?" stays (SISETU 167, 再訓練をしますか?; Chris, 2026-10-12, decisions.md item
  15).** It's asked after Yes to "Use this character?" when the creation roll was 9 or
  under. Yes trains three years: level 4, three years older (F-edge-save.md §9, [emu]).
  "Train for three years first?" was considered and dropped. Retraining is a convention of
  the Japanese line: Emonoya's pages describe the same offer in Gaiden IV (bonus 10 or
  under) and Dimguil (9 or under), and a 2001 Emonoya BBS post says it started with Gaiden
  IV (外伝4から再訓練できる). Emonoya's pages for I-V, FC III / SFC V and Gaiden I-III don't
  mention it [tertiary; not code-checked]. Dimguil's players know it, the Japanese doesn't
  explain it either, and a mistaken Yes only gives a level-4 character three years older.
  The site explains the three years.
- **"Sane" is now "Confused" (STATUS 208, 627, 197; Chris, 2026-10-11, decisions.md item
  14).** The disc's own English labelled status bit 0x02, こんらん (confused), "Sane", so a
  confused character showed "Sane" on the status screen and in Look for Companions, and
  "Sane" in the party panel. Most likely a clipped "Insane", the series' old word. But
  Dimguil renamed the status: Gaiden IV's Psionic spells drive the target 発狂 (insane),
  while every mention of it in Dimguil is 混乱, and Emonoya's spell page notes the
  effect message was changed to 「混乱した」. Our battle text already says "is confused."
  - 208 `{ff24}Confused`: the full label (status screen, Look for Companions, every
    other 0xce + n site). Right-aligned to the same edge as the original's "Paralyze",
    which is as long.
  - 627 `／Conf`: the party panel's four-letter label beside current HP (the panel has
    its own set, STATUS 626-635: Afra, Pois, Slee, Para, Ston...). Found because the
    panel still said "Sane" after 208 changed.
  - 197 `{ff23}desufnoC`: the reversed copy in a right-aligned set (195-205, "KO",
    "peelS"...) that no code reads: every status-label site uses 0xce + n (English) or
    0x261 + n (Japanese), and a read watch on 188-205 saw only 188 ("Luck" on the status
    screen) across the status screen, camp and the maze. Changed so no "Sane" is left.
  Checked in the emulator on the built disc with a RAM-write setup (a member's status
  set to 0x02; Mars put in a second party record on the square for Look for Companions):
  shots in `rips/re/work/P3-label/` (before.png, after.png, width_cmp.png). The Tavern
  and Training Grounds lists don't show status; the battle screens weren't checked.

- **Reiran's cut-off line (NPC_MES2 200, 2026-10-10).** In the original, an {ff40}
  (end of string) after her first sentence hid the rest: "He goes 'Begone!' and stuff,
  all high and mighty." The English drops it so both pages show; the string's own
  terminator had been switched off in the translation file because the Japanese ended
  there, so it's back on. It's the only cut-off line in the game's text. npcfit.py now
  flags a string with neither.

- **NPC speech closes its quotes (Chris, 2026-10-10).** The Japanese opens each speech
  with 「 and never closes it, and the English copied that, so every NPC box showed an
  opening " and no closing one (Chris noticed in play). Quotes now close where the
  sentence ends: 1,064 strings in NPC_MES1-5 and SISETU 127. Replies shown after a
  yes/no prompt, which had no speaker line and no quote, open with " where the Japanese
  has a space in place of 「. Healing boxes close before the spell's name, which isn't
  spoken, and reopen after it when the healer goes on ("Will that do for first aid?"). A box that stops mid-sentence (Artemisia's "okay, then," and "Um,", Zaril's
  "...but") stays open, and the speaker's next box closes it (Chris). `scripts/npcquotes.py` does it, npcapply.py runs it on reviewed scenes, and
  npcfit.py flags speech left open. No line got too wide, but NPC_MES4 grew past its
  six sectors and is relocated now, like NPC_MES1-3.

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
- **Balbo's introduction (2:96, 2026-10-15).** Chris found it awkward in play; no
  reviewer had flagged it, so it was still the first draft. 何だよ,そんなことか? is
  "what, *that's* what you're asking?", not "that's all?" (which read as disappointment
  that it was over); the fragment "Pain in the neck, but fine" became full sentences;
  and "I guess" was dropped, since ま,よろしくな is gruff but friendly, not grudging.
  Now "Huh? That's all you wanted? What a pain. Oh, all right... Name's Balbo. I'm a
  Lord. Well, nice to meetcha." Chris thought the rest of Balbo's party's talk read fine.
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
- **Unidentified flyers named by their picture (Chris, 2026-10-13).** The disc's English
  called a Vampire Bat, Wing Lizard and Were Bat "Bird(s)" while showing the same
  bat-winged figure as Fake Cupid and Halycon, which it calls Flying Figure(s); and
  Marchosias "Very Big Bird", though its Japanese is きょだいなあくま ("giant demon"), like
  every Greater Demon. Those four are now Flying Figure(s) and Greater Demon(s). "Bird"
  stays on the other picture (uk/07, a winged serpent), whose monsters really are birds
  (Zopilote, Xecotcovach, and the Were Vulture). Death Hawk stays Very Big Bird
  (きょだいなとり), though it shows picture 22: that's the game's one silhouette for any
  huge foe, also shown for Quetzalcoatl, Ugo, Hims and the Greater Demons. The
  picture is byte +2 after the six name slots (07, 08, 0x16...), the same numbers as
  Bartok's Trading Post's uk/ images. 16 slots in DATA02 (`namefixes.py`, keyed by the
  record's English name) and BATTLE.BIN's own Vampire Bat record (`asm/name_fixes.asm`).
  Options and the series' names: `unidentified-flyers.md` (option B).
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

- **Five more of the developer's names (Chris, 2026-10-10).**
  - BENT STAFF stays: it's Wizardry I's item (STAFF -2 on the Apple II, BENT STAFF and
    ねじれたつえ in the later ports). This settles "Twisted Staff".
  - Astro Zombie (ロストワン, "Lost One") stays. The Shrine is a crashed starship (see
    `event-map.md`, "The hidden story"), and the entry calls him a man whose name means
    "the only one", hooded in what may be life-support gear (生命維持装置): the ship's last
    crewman, or what's left of him (Inferred). The developer's name says the same.
  - B-PLATE OF GOODNESS (希望の胸当て, "breastplate of hope") is now BREASTPLATE OF BOONS.
    "Goodness" told the player nothing, and the B- contraction made it worse. Boons is
    the Vodafone Wizardry's word for the same item (B-Plate of Boons), the only other
    English name found for it. 20 letters, as long as STRONGEST CHAIN MAIL; the
    two-line forms break BREASTPLATE / OF BOONS. ITEM.DAT's copy is a byte edit and has
    no room for the space before the break (`scripts/namefixes.py`).
  - STEEL GLOVES (鉄の小手) is now IRON GLOVES, the console ports' name for Wizardry III's
    GLOVES of IRON, the same Japanese item. Dimguil's text keeps 鉄 as iron, and the
    developer didn't use "steel" for its steel items either (鋼の兜 is BACINET, 鋼のブーツ
    SOLLERET). Items 1:150 and 1:151, which said steel to match the old name, now say
    iron.
  - LITHOGRAPH OF SUN (太陽の石板, "stone tablet of the sun") is now TABLET OF THE SUN.
    The item is a stone tablet assembled from four pieces; a lithograph is a print.
    The developer most likely took 石版 (sekiban, a lithographic stone) for its
    homophone 石板 (sekiban, a stone tablet). No earlier Wizardry has the item. Same
    length, so every event line keeps its breaks; the NPC lines that said "Lithograph
    of the Sun" (NPC2 82) and "the Sun tablet" (NPC3 68) now say "Tablet of the Sun".
    The keyboard's "small tablets" are 石板 too, which the new name now matches.

- **Four more slips, and spaces in two-word monster names (Chris, 2026-10-16).**
  Found in the chapter 13-15 text check (`textcheck-c13-15.md`, items 3 and 12) and
  checked against the earlier games: none is a series spelling.
  - GLOVE OF DEAD (死者の小手) is now GLOVE OF THE DEAD, FAERIE'S CLOTHE (妖精の服) is
    FAERIE'S CLOTHES, PRIESTS MACE (僧侶のメイス) is PRIEST'S MACE, and HobGoblin is
    Hobgoblin. The two-line forms break GLOVE OF / THE DEAD and FAERIE'S / CLOTHES.
    Copies changed: I_NAME_E 92, 132, 178 and their two-line forms 1031, 1071, 1117,
    plus 519 (the mace as an attack noun); the card game's MESSAGE.DAT 832, 872, 918;
    M_CATALG 2:376; MPT14's records; ITEM.DAT's catalog list. ITEM_CA.DAT keeps the old
    names; the game doesn't load it. No battle copy (BATTLE.BIN) has any of them.
  - The catalog list and the card game's list have no spare bytes. The card game's
    copies of FAERIE'S / CLOTHES and GLOVE OF / THE DEAD drop the space before the
    break (2 bytes over otherwise). The catalog list drops it in those two, and in
    EMERALD, SAPPHIRE and SCARLET ROBES to make room for THE; the catalog draws the
    break as a new line, so the space never showed. The catalog reads these names one
    after another, so they have to stay packed in order (`engine-notes.md`, "Item
    catalog"). Repacking also fixed "0FEATHERED CAP" in the Hats list, a stray byte the
    IRON GLOVES fix had left behind.
  - Two-word names in the party fights (MPT01-39, NPT15) were stored with a bare line
    break, `Arch{ff21}Ninja`, which the enemy grid draws on two lines and every battle
    message drops: "ArchNinja kicks Venus." Each such slot (name, unidentified, plural,
    unidentified plural) now has a space before the break, as `Man in {ff21}Robe`
    already did, so messages read "Arch Ninja kicks Venus." and the grid is unchanged.
    That includes the unidentified Man in Robe/Armor plurals and Small Shadow.
    Nex{ff21}tepehua and Tepe{ff21}yollotl stay as they are: each is one word split for
    the grid.
  - **Goblin Assassin still prints "GoblinAssassin"** in messages ("GoblinAssassin casts
    Fisqurea."). `Goblin{ff21}Assassin` is 16 bytes, the most a slot holds, so there's
    no room for the space. Fixing it would take a code change: the name copy at MAIN
    0x8001ebf4 could turn a dropped break into a space for every name.
  - Names that reach 10 letters with the space (Arch Ninja, Rage Beast, Orc Knight, Orc
    Healer) now take FIGHTMSG 151, "Orc Knight / takes 14 damage.", which reads fine.
  - Cutie Thief's second SHORT SWORD attack used verb 213, the item menu's "Use it on
    whom?", in a melee line: an original data bug. It now uses 3, "stabs" ("Cutie Thief
    stabs Jupiter with SHORT SWORD."), through `scripts/re/attackverbs.py`'s MELEE table.
  Shots: `docs/shots/name-fixes/` (fights forced and items placed through RAM to set
  them up; no text was written).

### Game bug fixes (2026-10-11)

Chris decided the patch fixes the original game's clear bugs and reopens text a bug cut
off. Anything that looks deliberately cut, or changes the balance, goes to him first.
The full triage is `docs/re/bugs.md`; each fix is its own `asm/bugfix_*.asm`.

- **Guy's statue warning to a stranger** now plays 1:87, the stranger's copy of the
  speech, instead of the trap warning 1:89 (29233ff).
- **Rosea's Madi** plays her Madi line, 2:134, instead of the cancel line "Do take care"
  (54596b4).
- **Cephala's healing** was one block off from 11 up: wrong lines and wrong spells. The
  missing "can't treat" block goes to 3:138, which has the same Japanese (34cd45c).
- **Alstron's Madi** (1:157) could never be cast; the stage test needed two bits at once
  (1976612).
- **The pit scene** now plays its middle block, the rescuer's voice and "Looks like help
  has arrived" (3:95-96, 99-100) (5b565b9).
- **Fritillaria's "walkin' corpse"** (5:17) tested kills instead of deaths, named the
  wrong member, and never showed when both of her lines applied (fc6158f).
- **Cresson's speech after the control room** (4:24-29) was skipped by any party that
  had finished the Decipher table, because both used the same flag (3e36a06).
- **Chat topics** with low block numbers were always rerolled: Guy's area topics
  (1:195-210), Balbo's "about other parties" (2:174-187) and two of Fontana's (3:181-196)
  (a9ed605).
- **A failed raise from ashes at the Temple** scrambled the party table: in the emulator
  a party member dropped out and a stranger took her place (e4c0da7).
- **The BROKEN ITEM purge on entering town** wiped the uses left on whatever sat in the
  tenth pack slot (c717515).
- **The pit scene with no rescuer** locked the game: a party in which nobody had met Guy,
  falling into the Area C pit while Guy was the rescuer, sat on an empty talk window for
  good. It now gets the game's own rescuer for that case, Balbo's party if someone has
  met Balbo, otherwise the man in armor (5ff86d2).
- **A pillar guardian's fight could be lost,** locking the game on "The pillar begins to
  shake ... attacks." The box closing and the dust settling race, and the box closing
  wipes the fight request. The Japanese line always finished first; ours is about three
  times as long and lost about 3% of the time. The dust now waits for the box. Found by
  the harness runs (asm/bugfix_pillar_race.asm, bugs.md 1.11).
- **A disc read could stall forever,** most visibly as "You've met someone!" with the
  meeting never starting, music playing on and no button working. It's a race in the
  game's own CD library (Sony's libds, the same on the Japanese disc): if the frame
  interrupt lands while a read's commands are being queued, one goes out half-written,
  the drive refuses it and nothing retries. Rare (two locks in about 60 hours of bot
  play), likelier in an emulator than on hardware, and any disc read can hit it. Fixed
  because a lock loses everything since the last save and the fix only reorders stores
  the library already makes: each queued command is marked ready last. Found by the
  harness runs (asm/bugfix_dspacket_race.asm, bugs.md 1.12).
- **A rescued party stayed on offer** (2026-10-13). After a Yes, Guy's and Fontana's
  parties offered to rescue the same party again, in the same meeting and at later
  ones, and took the fee each time; for Fontana's that's half the gold and about half the
  items again, for bodies already at the Temple. The Yes left the party's record in the
  table, and the town only clears such records after a wipe, a load or "Go On with
  Another Party". Found by the rescue test (`docs/re/rescue-test.md`). Chris: fix it. The
  Yes now frees the record as Look for Companions does; no text changes
  (asm/bugfix_rescue_repeat.asm, bugs.md 1.13, decisions.md 27).
- **Picking a lock used the wrong character's skill** (2026-10-13). The roll took level,
  class and Luck from whichever of roster entries 1-5 the member picker's blink was on,
  not the character chosen, so a Thief's skill could be ignored on the harder doors.
  Found by the lock test (`docs/re/lock-test.md`). Chris: fix it. Both reads now take
  the chosen member; no text changes (asm/bugfix_lockpick_member.asm, bugs.md 1.14,
  decisions.md 28).

Reopened content (each one goes in the release notes too):

- **Zaril's healing** (NPC_MES5 35-42, and the log line 114) never played: his handler
  had no heal offer. Chris, 2026-10-11: reopen it; Zaril is a Lord and his lines name
  Priest spells. The offer and its outcomes are copied from Guy's and Balbo's healing,
  with the same odds, and only his own lines are used (9135ef5). His sale is rolled
  first and keeps its original odds; the heal offer comes only when the sale doesn't, so
  25% of Talk presses with someone hurt, or 12.5% when a sale was possible (98b0c5e,
  after Chris asked that the sale not be buried).
- **Guy's and Fontana's re-introductions** (NPC_MES1 134-139, NPC_MES3 117-123) never
  played: when only some of the party had met the leader, Guy replayed his full
  introductions and Fontana skipped introducing the newcomers. Chris, 2026-10-11: add
  them. Modeled on Balbo's branch; Fontana's has a block per stage, Guy's one block, since
  his lines cover only his founding four (7498b1c). Guy's second line-up (1:128-133) is
  still unplaced; the evidence doesn't say where it goes (bugs.md 2.3).
- **Cresson's "girls" and "my good fellows"** (NPC_MES4 19, 20) never played: his greeting
  picked among the three with flags nothing set, so every party was "boys". Chris,
  2026-10-11: write the check. No women: "boys"; only women: "girls"; a mixed party: "my
  good fellows" (7166f5d).
- **Fontana's chat about Zaril's new party** (NPC_MES3 197, 199-200) was a whole chat
  block nothing picked. Chris, 2026-10-11: add it, after the split only. It's a ninth
  topic in his stage-3 roll, so each of the other eight goes from 1/8 to 1/9 there;
  stages 1 and 2 are unchanged (7c99607). 3:198, Artemisia's line about Zaril, isn't in
  the block and stays unused.

Decided and left as the original had it (each one goes in the release notes, per
ROADMAP.md "Game changes up front"):

- **The wipe's item loss** (bugs.md 3.1) stays: one character, in practice whoever stands
  in the party's first position, has every item rolled six times, and the others keep
  theirs. Chris, 2026-10-11: keep it, document it on the site, maybe revisit later.
- **Weapon effects ignore level** (bugs.md 3.2) stays: a weapon's poison, sleep, stone and
  other effects land at their flat chance, whatever the levels. Chris, 2026-10-11: keep
  it; a candidate, with the wipe's item loss, for a possible later "hardcore mode"
  (ROADMAP.md).
- **Level drain's save** (bugs.md 3.3) stays backwards: the better a character's save,
  the more often they're drained. Fixing it would make drain nearly certain. Chris,
  2026-10-11: keep it; on the hardcore-mode list.
- **The NPC Kadorto warnings** (2:130, 1:158, 3:139, 4:67, 4:74) stay as written: Rosea,
  Alstron, Cephala, Cleo and Bergamot warn that their Kadorto may fail, but an NPC's
  Kadorto always works, free, with no VIT loss or aging, on ashes too (C-talk.md §5,
  [code]). The Japanese warns the same way, and they're characters speaking, not the game
  stating a rule. Chris, 2026-10-11: keep them and document the difference; a
  hardcore-mode candidate. The site's spell page already notes it.
- **The NPC identify service** (bugs.md 2.1) stays unused. Rosea, Cephala and Cleo have
  the full exchange and every party log has its line, but no code offers it. Chris,
  2026-10-11: it looks as if the developers meant to have it, ran out of time and cut it
  rather than implement it. The release notes say the lines exist and the service was
  never in the game.
- **Balbo's party's "heard that already"** (bugs.md 2.6; 2:243-247, 253, and the log
  line 2:249 "We told them everything we knew.") stays unused. Every talk topic is the
  player asking; there's no way to tell an NPC party news, and nothing records what
  they've heard, so reopening it would mean designing that feature. Chris, 2026-10-11:
  leave it, and say so in the release notes.
- **Guy's second line-up** (bugs.md 2.3, 1:128-133, "Looks like we've got some new faces
  here...") stays unused. It covers the same case as the re-introduction now in place
  (1:134-139) and introduces Fritillaria and Lilia together, which no stage of Guy's party
  has, so it reads like a draft roster the developers replaced. Chris, 2026-10-11: leave
  it, and say so in the release notes.

Done 2026-10-11 (see "Reopened content"): Zaril's healing, Guy's and Fontana's
re-introductions, Cresson's boys/girls/fellows check, and Fontana's block 8 after the
split. The labels (`docs/re/decisions.md` items 14-16) are decided too: "Sane" is now
"Confused" (14, 2026-10-11), "Retrain?" stays (15, 2026-10-12), and only "EVENT Item"
changed, to "Event Item" (16, 2026-10-12); see "Deliberate choices". Nothing in
decisions.md is open.

### Description corrections (the original's errors, 2026-10-11)

Chris decided (decisions.md item 11) that descriptions should say what the game does, since
the text is the player's only guide, and that every change goes in the release notes. The
Japanese has these errors too; our English had copied them faithfully. Values are from the
code and the records (`docs/re/description-check.md`). Before and after captures:
`docs/shots/description-corrections/`.

Spell descriptions (STATUS.OBJ, the one-line spell bar; 0f0a69b, Bacortu d798054):
- 421 Halito: "Flame: 1-8 damage to one enemy" → "Flame: 2-8 damage to one enemy" (2d4).
- 423 Melito: "Sparks: 1-8 damage to an enemy group" → "Sparks: 2-8 damage to an enemy
  group" (2d4).
- 426 Morlis: "Fear: enemy group AC +4, and held fast" → "Fear: startles a group; their
  AC +4" (only the AC changes; nothing holds them).
- 428 Cortu: "Barrier: a wall that stops enemy spells" → "Barrier: enemy spells fail
  more; stacks" (a magic screen of 3/4 the old one + 2 × level, up to 90%).
- 429 Tzalik: "Heaven: 24-58 damage to one enemy" → "Heaven: 24-48 damage to one enemy"
  (24d2).
- 430 Lahalito: "Inferno: 6-58 damage to a group" → "Inferno: 6-36 damage to a group"
  (6d6, as in Wizardry I).
- 434 Bacortu: "Ward: walls enemies off from casting" → "Ward: enemy spells may be
  sealed; stacks" (sealing is a roll that grows with each cast; found in the sweep).
- 435 Zilwan: "Dispel: 1000 damage to one undead" → "Dispel: 255-2550 damage to one
  undead" (255d10).
- 436 Ladalto: "Ice Storm: 44-98 damage to a group" → "Ice Storm: 10-100 damage to a
  group" (10d10).
- 437 Lazalik: "Smite: 64-80 damage to one enemy" → "Smite: 40-80 damage to one enemy"
  (40d2).
- 441 Dios: "Bless: heals one ally 1-8 HP" → "Bless: heals one ally 2-8 HP" (2d4).
- 442 Badios: "Pain: 1-8 damage to one enemy" → "Pain: 2-8 damage to one enemy" (2d4).
- 459 Kadorto: "Revive: raises the dead or ash, full HP" → "Revive: may raise dead or
  ash; full HP" (in camp it rolls on Vitality and can fail).
- 461 Madial: "Great Prayer: party heals 30-60 HP" → "Great Prayer: party 17-68; camp
  10-50" (17d4 in battle, 10d5 in camp).
- 480 Alikus: "Blast: 80-130 damage to one enemy" → "Blast: 48-144 damage to one enemy"
  (48d3).
- 483 Sios: "Mind Blast: 1-10 mental damage to one" → "Mind Blast: 2-4 mental damage to
  one" (2d2).
- 484 Diomas: "Secret Art: heals one ally 2-6 HP" → "Secret Art: heals one ally 3-6 HP"
  (3d2).
- 486 Lios: "Spirit Blast: 2-10 mental damage, group" → "Spirit Blast: 2-4 mental
  damage, group" (2d2, the same as Sios).
- 492 Masios: "Psi Blast: 2-16 mental damage, group" → "Psi Blast: 8-16 mental damage,
  group" (8d2).
- 497 Dalosto: "Frost: 36-64 damage to one enemy" → "Frost: 14-70 damage to one enemy"
  (14d5).
- 501 Galtomas: "Alch Wave: 12-48 to all, plus ailments" → "Alch Wave: 4-48 to all, plus
  ailments" (4d12).
- 502 Lasios: "Psi Wave: 9-72 mental damage to all" → "Psi Wave: 8-72 mental damage to
  all" (8d9).

Item descriptions (ITEM.DAT §1, Boltac's catalog; da781e2):
- 46 Winter Wand: "holding the cold spell Madalto" → "Ladalto" (its battle spell).
- 69 Rod of Raising: "Nearly useless as a weapon, but thanks to its spell..." → "It's no
  bad weapon either, and thanks to its spell..." (3d8, to-hit +3).
- 107 Wand of Mystery: "The wand itself has no attack power." → "As a weapon it hits
  lightly, but often." (1d7+2, two extra swings).
- 275 Gem of Exorcism: "you can't be hit by undead attacks" → "undead attacks do half
  damage" (its protection halves their hits).
- 301 PK Crystal: "a barrier ... strong enough to nullify sword and magic attacks" → "a
  barrier around the body that can turn magic aside" (20% magic resistance per school;
  nothing against weapons).
- 225 Mythril Plate: "neutralizes all kinds of breath" → "blunts many kinds of breath"
  (resists fire, cold, poison and paralysis, which halves matching breath).
- 228 Dragon Kite: "block all magic and breath attacks" → "ward off magic and breath
  attacks" (10% magic resistance, 15% fire, cold and poison).
- 59 Worst Sword: "It's cursed, cuts your attacks, and lowers both accuracy and defense"
  → "It's cursed, and lowers both accuracy and defense" (no swing penalty).
- 35 Axe of Woe: "you must get very close to cut with it, so you lose attacks" → "you
  must get very close to cut with it." (no swing penalty).
- 230 Holy Crown: "Clergy and any fighter type can wear it." → "Clergy can wear it, as
  can Fighters, Lords and Valkyries." (its classes are Fighter, Priest, Lord, Valkyrie
  and Bishop; Samurai, Ninja and Ranger can't. Decided 2026-10-12, decisions.md item 17.)

Help text (SISETU; decided 2026-10-12, decisions.md item 18):
- 219 Luck: "like disarming traps and dodging enemy attacks" → "like weathering breath
  attacks and escaping traps" (disarming uses class, level, Agility and the area; monster
  to-hit has no Luck term; Luck feeds the saving throws, which halve breath and dodge six
  of the twelve chest traps).

Compendium (M_CATALG; a25c54c):
- 7.16 2-Head Snake: "Worse still, it can drain levels." dropped (no drain; its bite
  poisons).

Left as they are: six unmentioned curses, and the unmentioned restrictions and hidden
powers. Chris decided (2026-10-12, decisions.md item 17) that the descriptions stay silent
about them, as the developers wrote them; the item details screen already shows who can
use an item. "Has died of old age" (SISETU 65/66) stays too, though the character is
Lost and deleted: it reads as final and matches the Japanese (decisions.md item 19).
The Training Maze sign (492) stays as well; it never says a wipe there is free, its box
is full, and the site documents the cost (decisions.md item 20). The Venus Man Trap
Compendium entry stays too (in-world lore; the site gives the real resistances;
decisions.md item 21). The Smoke Demon's was corrected on 2026-10-14: swords do full
damage, and it resists Alchemist spells 80%. Madalqua's "freezing cold" battle lines stay
too, though its element is Tiltowait's; the site notes it (decisions.md item 22).

### Our mistranslation corrections (2026-10-11)

Our own error, not the original's: 力 ("power") on three weapons was rendered as the
Strength stat, which none of them raises while equipped. Chris approved the wording
(decisions.md item 12); 8ace280. Shots: `docs/shots/strength-mistranslation/` (after
only).
- 61 Skull Dagger: "Raises strength and accuracy, and even adds attacks" → "It hits
  harder and truer, and even adds attacks".
- 89 Mace of Power: "A mace that raises Strength and accuracy just by equipping it. Its
  hidden power raises Strength for good." → "A mace that adds power and accuracy just by
  equipping it. Its hidden power raises Strength itself. It truly lives up to its name."
- 118 Golden Axe: "Strength and accuracy rise too." → "It also hits harder and truer."

### Text check of bot runs (2026-10-15)

Findings from `docs/textcheck-c13-15.md`, reviewed with Chris one at a time.
- FIGHTMSG 18 (を 放った, a ranged weapon type's second verb): "looses at" → "fires at".
  "Looses" is the archer's word but reads as a typo for "loses"; "shoots" and "takes aim
  at" already belong to the next weapon type, so "fires at" keeps them apart.
- SISETU 84 (このキャラクタにお金を集めますか?, the shop's offer when a buyer is short):
  "Gather gold on this character?" → "Pool all gold on this character?", matching the Pool
  Gold command (SISETU 395, STATUS 93). 159 px, under the 167 px of SISETU 83 in the same
  box.
- SISETU 112 and 314 (アイテムがいっぱいです。どれかと交換してください, a full pack when an
  item comes in): "Your pack is full. Swap it for something." → "Your pack is full. Choose
  an item to swap." The old line read as "go find something"; the game wants one of the
  pack's items picked to trade out. 210 px against 206.
- NPC_MES3 16, the little elf's parting line (失礼します): "Excuse me." → "Goodbye.".
  失礼します is the polite way out of a room; "Excuse me." read as an apology or an
  interruption. Chris chose "Goodbye." without the leading dots her hello has.
- FIGHTMSG 143 ({ff18}は {ff11}1回復した): "Mercury recovers 10." → "Mercury recovers 10
  HP.", which says what came back. Only party members print it (monsters get 163); the
  worst case, an 8-letter name and Labadi's 5-digit drain, is 23 of 24 codes, one line
  (shots: worktrees/verbfix/docs/shots/heal-line/compare.png).
- I_NAME_E 1253, the statue in the pack: the developer's "DEMON'S STATUE" → "DEMON
  STATUE", matching their pickup name (314). The Japanese is 悪魔の石像, a stone statue
  of a demon; nothing in the game makes it a demon's, so Chris chose the plain form.
- Kept: SISETU 36 "Really throw it away?" (本当に捨てますか?), though the command is "Drop".
  Chris: it makes clearer that the item won't come back.
- SISETU 147, the Temple's prompt after "Heal Character" (404; both 助ける): "Help whom?"
  → "Heal whom?", one verb for both. Chris: "Help Character" doesn't sound like a temple,
  and raising the dead isn't quite healing either, so "Heal" is the best of the plain
  words for now; a better one for both would be welcome.
- FIGHTMSG 137 ({ff18}は {ff11}2レベル吸い取られた): "Earth is drained of 1 levels." →
  "Earth is drained of 1 level(s).". Ruby Hand drains one level, so the singular is the
  usual case. Chris kept "drained" because level drain is the game's term ("Restore
  drained levels", "resists level drain"); fightfit passes.
- FIGHTMSG 163, the monster heal ({ff13}は {ff11}1回復した): "Kobold Priest recovers 12."
  → "Kobold Priest" / "recovers 12 HP.", to match 143. With a plain space, mid-length
  names left "HP." alone on the second line ("Kobold Priest recovers 12 / HP."), and the
  font has no non-breaking space, so the line now always breaks after the name, the way
  the game shows long-name casts ("Kobold Priest / casts Bamatu."). Chris's choice.
- SISETU 191, the Dracon at creation (唯一ブレスを吐くことができる): "the only race that
  breathes" read as breathing air → "the only race with a breath attack. / Scaly skin
  resists specials." (166/156/135 px; the widest race and class line is 190).
- SISETU 201, the Mage at creation (魔術師の部類に入る。HPは低く装備できる物は少なく):
  "and a spellcasting class ... few items" → "Experts at attack magic. Casters / with low
  HP and limited gear; / not for the front." 魔術師 is the game's word for the whole
  magic-user family (the Compendium's 魔術師系 type, "Mages"; the Alchemist and Psionic
  are 魔術師の部類 too), so it reads "Casters" as theirs do; 装備できる物 is what they can
  equip, so "limited gear" (Chris).
- SISETU 210, the Psionic (装備できる物は少ない, as the Mage): "few items" → "limited
  gear", to match. "Casters" moved up a line so no line passes 190 px (176/190/150).
- The three-part dial door (EVENTMES 158-163, Guy 1:288, Balbo 2:88-89): one word,
  "disc", as the Japanese has throughout (三層に分かれた円盤, 小さい/中間の/外側の円盤,
  三つの円盤). "The door has a disc split into three layers." / "Will you turn the
  disc?" / "the small disc" / "the middle disc" / "The disc quietly turns back."; Guy's
  "a disc here split into three layers"; Balbo's "three discs" stays. On screen it's a
  carved centre disc with two bands around it (docs/shots/ring-dial/). Chris: "disc"
  throughout, it's more faithful. The last prompt is "the outer disc" (外側の円盤), no
  longer "the large ring". The Fortune Teller stays faithful with rings (SISETU 339
  3つの輪 ... 大きな輪, topic 353 輪の扉 "Ring Door"): the original itself mixes the two,
  and the Japanese fan FAQ (emonoya.net) slips between 円盤 and 輪 the same way.
- NPC_MES4 62, Bergamot (・・おまえさんたちゃ物覚えが悪いのぉ・・・): "..Memories like sieves,
  you lot..." → "...You folks sure got memories like sieves...": three dots like the rest
  of the game, and an American old codger's "you folks" for the British "you lot" (his
  voice sheet). Alba's, Zaril's and Bergamot's other "you lot" lines wait for their
  scenes.
- NPC_MES4 105, Cleo on Fontana's party (みんな若くて元気いっぱいでしたよ): "All young and
  full of beans." → "They were all young and full of energy.", a full sentence without
  the British idiom (to many Americans "full of beans" means talking nonsense).
- SISETU 208, the Bard at creation (楽器を奏でて,呪文と同様の効果を発揮する ... 盗賊技能有り):
  "Instruments that work like spells." had no verb → "Their music works like spells." (the
  playing does it, not the instrument alone, and the Japanese names no songs). "and have
  thieving skills" → "and have some thieving skill", the Ranger's (207) wording, since
  their skills fall short of a Thief's (Chris).
- NPC_MES4 84, Cresson's decipher score (どうやらあなたたちとの適合率は{ff11}0%でしょうか):
  "Um, you seem to match us at about 0%." read as the people matching, with "about" odd
  beside an exact figure → "Hmm... it looks like your results / match 0% of ours."
  (Chris's wording).
- NPC_MES4 33 and 39, the 26 glyphs laid out (研究も進むというものだ): "our research is
  bound to get on" was British → "bound to progress", a scholar's word (Chris).
- NPC_MES4 107, Cresson on the young party (とてもにぎやかだったのですよ): "They were ever
  so lively." was British → "They were such a lively bunch.", which keeps her fond, chatty
  tone.
- FIGHTMSG 78 and 97 (甘い息を吹き掛けた): "breathes a sweet breath" repeated itself →
  "Sleeper blows a sweet breath.", and the holy one to match. Chris found "exhales" didn't
  read well.

## To revisit

- **Fontana's maze encounters (3:72, 75, 88, 278).** Same register shift as Balbo's
  reports. Handle them the same way when NPC_MES3 is reviewed: his own words, a little
  more in charge.

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
- **Other naming.** "Labyrinth" vs "maze" for 迷宮 (checklist Q6).
- **Catalog 8:2, Giant Spider.** 女郎蜘蛛 (jorōgumo) is "an arachne" as a stopgap;
  "spider-woman" and "drider" were the alternatives (`sweep-review.md`).
- **Item 1:5, Anointed Mace.** Approved but flagged for another look.
- **Item 1:32, Demon's Staff.** Chris's wording leaves out focusing the mind, "the demons
  that plague adventurers" and the "probably".
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
- **Monster names run together in battle text** (found 2026-10-14). Fixed 2026-10-16
  except Goblin Assassin (see "Four more slips, and spaces in two-word monster names").
