# NPC dialogue (NPC_MES1-5.OBJ): translation notes

The dungeon NPC parties talk through DATA06/NPC_MES1-5.OBJ. One file is loaded at a
time, when a party is met, to 0x801a0400; `scripts/relocate.py` allows each up to 32
sectors (64 KB, which is also the most the 16-bit string offsets can address).

Translations live in `translations/NPC_MESn.OBJ.json` (JP `source` redacted as usual).
Check them with `scripts/npcfit.py [n]` after `scripts/build.sh` has produced the dumps.

## Layout

- The box is 288 px wide and shows 3 lines. A page break is `\n\r`.
- First line of a string is the speaker, then the speech opens with `"` and has no
  closing quote, matching the rest of the patch. Speech lines after the first on a page
  start with one space, as the Japanese does.
- English runs longer than the Japanese, so add pages where needed. Keep every page at
  3 lines or fewer (the first page's 3 includes the speaker line).
- Menus (`A:武器\nB:防具\nC:その他\nD:やめる`) keep their 4 lines and letters:
  `A:Weapons\nB:Armor\nC:Other\nD:Quit`.
- Quotes inside a line are single quotes ('Item'). The printer treats `"` as the
  Japanese voicing mark and merges it into the glyph before it, so a mid-line `"` can
  come out as a kana; only the `"` that opens a line is safe. npcfit checks this.
- Plain ASCII only. `...` for ・・・ (a long run of ・ can be a longer run of dots);
  no curly quotes or dashes the font doesn't have (`npcfit` reports those).

## Control codes

Keep every control code from the source, the same number of times.

- `{ff12}` a character's name (the player's, or a missing member's). Drop さん/殿/くん
  after it, or turn 殿 into something in the speaker's voice ("Sir {ff12}") when it's
  part of the character.
- `{ff11}0` a number the game fills in (price, percentage).
- `{ff30}2 ... {ff30}0` colours a spell name. Use the game's own English spell names:
  マディ Madi, ディアルコ Dialko, ラツモフィス Latumofis, ディアル Dial,
  ディアルマ Dialma, カドルト Kadorto, ディオス Dios, マディアル Madial.
  Write `{ff30}2Madi{ff30}0` and drop the `]` `[` around it. Spells named in plain
  text (ロクトフェイト Loktofeit and so on) use the same list, `rips/tl/spells.json`.
- `{ff40}` ends a string early; keep it where it is.

## Names and terms

Names follow the reference site's glossary (bartoks-trading-post), which transliterates
the NPC party names the same way everywhere.

The same names go into the party records the game shows in battle (DATA02/NPT00-15.BIN,
written by `scripts/nptnames.py`).

| Japanese | English | Notes |
|---|---|---|
| ガイ / ガイラルディア | Guy / Gaillardia | self-proclaimed hero, party leader |
| アルストロン | Alstron | priest, polite, dry, flirts; "Al" for アルちゃん. His battle record (NPT files) says アルストン, the site's "Alston"; the patch uses Alstron there too, as the dialogue does 59 times |
| リナリア | Linaria | fighter, frank, big-sisterly |
| ライチ | Lychee | mage, childish, calls herself "Lychee" |
| フリチラリア | Fritillaria | thief, cheeky kid voice (おいら) |
| リリア / リリアセウス | Lilia / Liliaceus | bard, flirty |
| アルテミシア | Artemisia | cheerful, digs up lost spells |
| セファラ / サファラ | Cephala | bishop, polite and earnest (サファラ appears once; same person) |
| ザリル | Zaril | leader, gruff but decent |
| バルボ | Balbo | dwarf, Evil-aligned Lord, rough-spoken |
| アルバ | Alba | ranger, formal, melancholy |
| ロゼア | Rosea | gentle, healer |
| フォンタナ | Fontana | polite |
| レイラン | Reiran | ninja, sassy |
| ガウラ | Gaura | shy, halting speech (stammers) |
| クレオ | Cleo | scholar |
| クレソン | Cresson | scholar |
| ベルガモット | Bergamot | cranky old man (じゃ/のぅ) |
| 巫女(さん) | the Priestess | |
| 神殿 | the Shrine | 地下神殿 Shrine Vaults |
| 迷宮 | the maze | |
| ガイネス / ガイネス城塞都市 | Ganess / the Fortress City of Ganess | |
| ギルガメッシュの酒場 / 酒場 | Gilgamesh's Tavern / the tavern | |
| カント寺院 / 寺院 | Temple of Cant / the Temple | |
| ボルタック商店 | Boltac's Trading Post | |
| 冒険者の宿 | Adventurer's Inn | |
| 古代文字 | ancient glyphs | |
| 石板 | stone tablet | |
| 属性 / 性格 / 戒律 | alignment | 善 Good, 中立 Neutral, 悪 Evil |
| 勇者 | hero | Guy's self-description |
| 邪教徒 | heretics | |
| 灰 / ロスト | ashes / lost | |

Classes and races use the game's English: Fighter, Mage, Priest, Thief, Alchemist,
Bard, Ranger, Psionic, Bishop, Samurai, Lord, Ninja, Monk, Valkyrie; Human, Elf, Dwarf,
Gnome, Hobbit, Faerie, Lizardman, Dracon, Felpurr, Rawulf, Mook.

Descriptions used before a name is known (大きな剣をかついだ男 and so on) become short
speaker tags: "Man with a greatsword", "Tall man", "Hooded woman", "Green-haired elf".

## Voice

This was written for a Japanese audience in the late 90s, and every NPC is built on a
stock character type of that era, marked by a first-person pronoun, sentence endings
and a verbal tic or two. The English has to carry the type, not just the meaning: a
reader should know who is talking with the speaker line covered. Give each character an
English voice that does the same job as their Japanese one, and keep it the same in
every file. Jokes stay jokes: the Japanese pokes fun at players who name characters
"あ", "アイテム" or "かねもち"; carry those over as names a player might really type
("A", "Item", "Richguy").

What marks each one in the Japanese, and what that becomes in English:

- **Guy (Gaillardia)**. 俺, 〜さっ, よろしくっ!, 勇者. The self-appointed hero from
  "far across the sea", a hot-blooded shounen lead and a lovable blowhard. Loud,
  upbeat, grandstanding, exclamation marks, calls himself a hero at every chance; laughs
  off his own disasters ("Ha, ha... ow."). Friendly "you guys".
- **Alstron**. 私, ですな / ですねぇ, drawled politeness. The genteel, slightly
  lecherous priest who plays straight man to Guy and needles him with perfect manners
  ("Oh my, oh my", "Quite so", "if you'll pardon my saying"). Fawns over pretty women.
  Once Evil, and says so without embarrassment.
- **Linaria**. あたし, わよ / なんだ, アハハッ! Tomboyish big-sister fighter: blunt,
  breezy, laughs at people's blunders, proud of her cooking. Casual, direct, short.
- **Lychee**. Calls herself ライチ, ねぇねぇねぇ, 聞いて聞いて〜, すごいっしょ〜.
  The airheaded child-mage. Refers to herself in the third person ("Lychee summoned a
  Greater Demon!"), run-on excitement ("and then, and then"), "Listen, listen!",
  "Isn't that amazing? Isn't it?", stretched vowels ("Byeee!").
- **Fritillaria**. おいら, 〜だよ, 〜な! Scrappy kid thief, hero-worships Zaril.
  Street-urchin English: "ain't", "gonna", "me and Zaril", brags then deflates. (One
  confession line is deliberately stiff and formal; that's the joke.)
- **Lilia (Liliaceus)**. あたし, なぁに?, ふぅん, 〜ねぇ, 〜わよ. The flirt: a
  teasing, worldly older-sister bard who toys with people. "Hmm? Want to know about me?",
  "darling", sighs and purrs, mock-bored "Oh, really?"
- **Artemisia**. あたし, 〜のよ / 〜ね, bubbly. Energetic research girl who digs up lost
  spells and gets them wrong; cheerful, quick to exasperation ("Honestly, these two!").
- **Zaril**. オレ, 〜ぜ, 知らんと言ったら知らん. Gruff Dracon Lord, tough guy with a
  soft centre, stubborn. Clipped and plain: "I said I don't know. So I don't."
  (A few reaction lines are stiffly polite and sarcastic in the source; keep those.)
- **Balbo**. 俺様, 〜ねぇ, 知らねぇぞ, 〜っつう. Rough-mouthed Evil dwarf Lord, a
  swaggering tough. Coarse English: dropped g's, "ain't", "ya", "don't come cryin' to me".
- **Gaura**. オレ, stammers, no grammar: オレ,ガウラ. The timid gentle giant. Broken,
  halting English, dropped articles and verbs, stutters: "M-me... Gaura. H-hello."
- **Reiran**. あたし, ヤンなっちゃう, バイト, ハマっちゃって, なーんか偉そう. A ninja
  who talks like a late-90s high-school girl. Teen slang: "like", "totally", "so
  over it", "whatever", "ugh", "I'm kinda hooked on...".
- **Fontana**. 僕, polite ですよ. Earnest young samurai, polite and a bit
  unsure of himself; real name Kikunoshin, renamed by Zaril. Proper, eager, a little
  stiff, "sir"/"ma'am" optional.
- **Cephala**. わたし, polite ですね, clumsy (えいっ! あいたーっ). Sweet, earnest
  bishop girl, a little ditzy, sometimes a sly giggle. Polite and soft, trailing "...".
- **Rosea**. わたし, かしら, gentle feminine. The kind healer. Soft, warm, refined,
  worries about others.
- **Alba**. 私 / 俺, terse, ・・・. Ranger with a dark past. Few words, weary, pauses
  ("...Alba."), formal when kind.
- **Cleo**. 私, 〜ですよ, chatty. Elf scholar, a talkative professor who loves his
  subject, pleasant and faintly condescending; the late reveal should land.
- **Cresson**. 私, polite, timid (や,やめて下さい). Nervous scholar, apologetic.
- **Bergamot**. わし, 〜じゃ, 〜のぉ / のぅ, わしゃ. The crotchety old man. Old-codger
  English: "Eh?", "whippersnappers", "I tell ye", grumbling, "back in my day".
- **Man in armor**. 俺, 〜ねぇ, チッ. A rough, short-tempered adventurer.
- **Agan, the mysterious figures**. Grand, archaic, portentous.

## Guy's party and Dragon Quest III

Guy's party reads as a Dragon Quest III party stranded in a Wizardry game. No source
we found says so; the case rests on the facts below. They are kept apart from the
interpretation so either can be checked or overturned on its own.

### What the game says (NPC_MES1 string numbers)

- Guy calls himself a 勇者, "hero", in ten strings (1, 86-88, 115, 124, 128, 202,
  248, 295; 86-88 and 295 are one speech under two speaker tags). Three treat it as
  his class or rank:
  128 クラスは勇者だ ("my class is Hero"), 202 俺はロードでなくて勇者だぜ! ("I'm not a
  Lord, I'm a hero!"), and 1 俺は勇者だからそんな差別はしないつもりだ (he's above the
  alignment rules because he's a hero). His battle record shows him as a Lord (class
  letter L in the enemy panel, DATA02/NPT00.BIN). Wizardry has no Hero class.
- 115: 俺は遥か遠い海の向こうから来た勇者さっ, "I'm the hero from far across the sea."
- 248: 俺は勇者だから、やっぱ炎系や雷系の魔法が得意だなっ, "Being a hero, naturally
  I'm good with fire and lightning spells."
- The first four members are introduced as 僧侶 Priest Alstron (116), 戦士 Fighter
  Linaria (117) and 魔法使い Mage Lychee (118), with Guy the hero. Later additions are
  盗賊 Thief Fritillaria (120) and バード Bard Liliaceus (122). Linaria's portrait wears
  bikini-style armor.
- 238: Alstron tried to become a Bishop, was told his 信仰心 (the Piety stat) was too
  low, and asks この国では例の書物を神殿に持って行けばよいという訳ではないのですかな?,
  "in this country, isn't it enough to take that book to the temple?"

### What the other games do

- Dragon Quest III (Enix, 1988): the protagonist is the 勇者 (Hero). The Sage (賢者),
  which casts both mage and priest spells, is reached by taking the 悟りの書 to the
  ダーマ神殿 and changing class there (or by changing from Goof-off (遊び人) at level 20).
  The 悟りの書 was the "Book of Satori" in Dragon Warrior III (NES) and the Game Boy
  Color version, and "Words of Wisdom" in the 2024 HD-2D remake; the temple was the
  "Temple of Dharma", later "Alltrades Abbey". The female Soldier (戦士) wears Akira
  Toriyama's well-known bikini armor. Sources: https://strategywiki.org/wiki/Dragon_Warrior_III/Player_classes ,
  https://game8.co/games/Dragon-Quest-3/archives/463736 ,
  https://dic.pixiv.net/a/%E5%A5%B3%E6%88%A6%E5%A3%AB(DQ3)
- Wizardry never uses a book for this. The Bishop class change comes from an item's
  special power: ほうおうのローブ in Gaiden III, ほうおうのおまもり (Amulet of Pope) in
  Gaiden IV, and 法皇のローブ (ROBE OF POPE) in Dimguil itself (ITEM.DAT section 1,
  string 231). Source: the item tables in the 得物屋 archive (emonoya.net), which
  bartoks-trading-post mirrors in data/items/g3, g4 and dim.
- Dimguil can bring in characters from Gaiden III and IV (the Tome of Rebirth lists
  "Scripture of the Dark" and "Throb of the Demon's Heart"), so a Wizardry player of
  the time knew those rules.

### Our reading (interpretation, not established)

- Alstron's "that book" and "that temple" are Dragon Quest III's, and 例の ("you know
  the one") assumes the player knows them. This is the firmest part: the mechanic
  matches exactly, and no Wizardry game has it.
- Guy is a Dragon Quest hero who doesn't fit Wizardry's classes: he insists he's a
  Hero, not a Lord, and claims the DQ hero's lightning magic, which a Wizardry Lord
  can't cast. "From far across the sea" would then mean from another game.
- The core party matches DQ3's classic lineup of Hero, Soldier, Priest and Mage, with
  Linaria's armor in the DQ3 Soldier style. Weaker: the Thief matches the class the
  1996 Super Famicom DQ3 added, and the flirty Bard may stand in for the Goof-off,
  whose female form is the bunny girl. Either could be coincidence.

### What that means for the translation

- Keep "hero" as Guy's word for himself everywhere; it's the running gag. Where he
  names it as a class (128, 202), capitalise it: "Hero".
- 238 names the book as the English Dragon Warrior III did ("Book of Satori"), so the
  one explicit reference can be recognised in English.
- Don't add Dragon Quest references the Japanese doesn't make.
