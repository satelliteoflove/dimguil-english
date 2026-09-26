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

| Japanese | English | Notes |
|---|---|---|
| ガイ / ガイラルディア | Guy / Gaillardia | self-proclaimed hero, party leader |
| アルストロン | Alstron | priest, polite, dry, flirts; "Al" for アルちゃん |
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

Natural, conversational English with each character's personality coming through, not a
literal gloss. Jokes stay jokes: the Japanese pokes fun at players who name characters
"あ", "アイテム" or "かねもち"; carry those over as names a player might really type
("A", "Item", "Richguy").
