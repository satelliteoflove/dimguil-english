# Linaria: character profile (2026-11-04)

Written before her voice review, to check whether her English rests on a misreading the
way Lilia's did. Everything here comes from her 33 tagged strings in NPC_MES1 (she
appears in no other file), the lines around them in the talk script, and the sources at
the end. Her lines, Japanese and current English, are collected in
`rips/review/linaria-lines.txt` (not committed, like the other review files).

## Short version

Linaria is the big woman warrior of a Dragon Quest III party: the female Soldier in
bikini armor. Her personality is three plain stock traits laid on top of that. She's
cool and unbothered (さばさば), she's food-minded with a "you wouldn't think it" knack
for cooking, and she's the older sister who teases the kids. She speaks ordinary adult
women's Japanese: あたし, わ, わよ, わね, かしら, あら. None of it is rough or boyish.

The current English mostly gets her attitude right. It gets her register wrong: "ya",
"'em", "folks", "Dunno", "Lemme", "How ya doing?" make her a folksy tomboy, and the
Japanese has nothing like that. Her tag 大柄な女 is also "big-framed woman", not "Tall
woman". So yes, there is a systemic misread, but it is smaller than Lilia's. Her
attitude holds, and only the tone of the words needs to change.

## The trope, from the game

- **The DQ3 female Soldier.** Guy's party is a Dragon Quest III party stranded in a
  Wizardry game (`docs/npc-translation.md`, "Guy's party and Dragon Quest III"). Hero,
  Soldier, Priest and Mage is DQ3's classic lineup, and Linaria is 戦士, the Soldier
  slot. Her portrait wears bikini armor, which is Akira Toriyama's famous design for the
  DQ3 female Soldier.
- **Big.** Before you know her name, her tag is 大柄な女 (1:3, 1:7, 1:24): 大柄 means a
  large frame or build, not height. The game tags Alstron 背の高い男, "tall man", so it
  knows the difference. Alstron introduces her as こっちの大きな方, "this big one here"
  (1:116). Her size is the first thing the game tells you about her.
- **"Fighter, born and bred."** 根っからの戦士よ (1:129).
- **The gap.** あたし,こう見えても料理は得意なんだ, "I may not look it, but I'm a good
  cook" (1:237). こう見えても ("though I look like this") points straight back at her
  size and armor. The domestic skill hidden in the big warrior is a standard gag.
- **Food.** Her personal lines are about food: getting starving hungry in the dungeon
  (1:249) and "do you think monsters taste good?" (1:258). Lilia later asks whether it's
  true some people eat the monsters they kill (3:252), a callback that makes her
  appetite a running joke between the files.

## Personality, from what she says

- **Cool and unbothered.** This is her strongest trait. あ,そう。それで? "Oh yeah? So?"
  (1:190); ハイハイ "Yeah, yeah" (1:203); 私はあまり興味無いけどね "not that I care
  much" (1:212); まあ,どうでもいいけどね "well, not that it matters" (1:249); 別に話す
  ようなことはないわ "nothing much to talk about" (1:184); へぇ,そうなんだ (1:225). Her
  sentences are short and she doesn't gush. The one stretched word is 気持ちわるーい
  about the creepy stranger (1:219).
- **She deflates Guy.** When Guy protests "I'm not a Lord, I'm a Hero!" (1:202), her
  whole reply is ハイハイ・・・ (1:203). She's the party's straight man, or tsukkomi,
  to his boasts. She also sends questions to Alstron rather than answer them herself
  (1:178).
- **Teasing older sister.** She greets returning parties as ぼうやたち and
  おじょうちゃんたち (1:51, 1:52), "boys" or "little ones" said from above. She laughs
  at your blunders, アハハッ! ドジねー, then warns you to be careful (1:262). She calls
  Fontana 若様, "the young master", the word a retainer uses for a lord's son, said
  half in fun (1:208). She's the grown woman of the party: Lychee is a cutesy teenager
  (`docs/character-lychee.md`), Lilia is seventeen, and the parties she teases include
  Fontana's 13-year-olds.
- **Frank, not crude.** She calls the grave robbers what they are and is shocked that
  one is a Lord "same as our leader", in a Shrine of all places (1:201). That's moral
  bluntness. She has no slang, no insults, and no rough grammar.
- **Mannered with strangers.** When Alstron introduces her formally, she answers in
  polite form: 戦士のリナリアです。どうぞよろしく。 (1:117). Two of her party greetings
  are in full です/ます with an honorific, 中立の方の御苦労 (1:49, 1:50; 1:50 may never
  play, docs/npc-review.md). With a crowd she knows, she drops to casual (1:129). That
  switch belongs to a grown woman with manners, not to a tomboy.
- **Eager now and then.** 見せてよ見せて "show me, show me" when Guy shows off what the
  King gave him (1:275).

## Her language: what she uses

| Marker | Where | What it signals |
|---|---|---|
| あたし | 1:3, 129, 237 | casual feminine first person |
| 私 | 1:212 (once) | neutral; a quieter aside |
| わ, わよ, わね | 1:42, 184, 196, 201, 231, 262, 269 | standard feminine sentence endings |
| かしら | 1:196 | feminine "I wonder", a touch soft |
| あら | 1:46 | feminine "oh!", mature |
| 〜ちゃう | 1:136 忘れちゃったの? | casual feminine |
| じゃない, なんだ, なぁ, けど(ね) | 1:136, 237, 243, 212 | everyday casual, gender-neutral |
| ゴメンネ (katakana ネ) | 1:243 (once) | a light, friendly "sorry" |
| です/ます | 1:49, 50, 117 | politeness with strangers |

In the DQ3 role-language study (Ma 2019), あたし, ちゃう, あら, かしら and わ are
exactly the markers of 女ことば, the women's-speech type.

## What she doesn't use

- No boyish or rough first person: no オレ, ボク or あたい.
- No men's-speech endings or verbs: no だぜ, ぜ, だろ, ちまう, やがる.
- No あんた or おまえ for you. She says みなさん, あなた方 or nothing at all.
- No dialect and no dropped sounds beyond the ordinary 若様んとこ (1:208).
- No drawl. Lilia stretches her vowels (わよぉ, ごめーん) and Lychee runs on, but
  Linaria's speech is clipped. Her only stretched words are なぁに and 気持ちわるーい.
- No terms of endearment and no flirting.

So the earlier voice sheet's "tomboyish" has no support (docs/npc-review.md already
noted that her endings are "ordinary feminine ones"). She's a 女戦士 who talks like an
ordinary grown woman, which fits the trope: the joke of the DQ3 Soldier was always the
contrast between the armor and the woman inside it.

## What it means for the English

Keep the attitude: short, dry, unbothered, teasing, the occasional laugh. Change the
register, so she sounds like a relaxed, self-assured adult woman rather than a country
tomboy:
- **Drop the folksy spellings:** "ya", "'em", "Dunno", "Lemme", "folks", "'bout".
  Plain contractions ("I don't know", "Show me") carry her casualness.
- **Feminine particles don't map onto English words.** わ and かしら have no English
  equivalent, and adding "dear" or "darling" would repeat the Lilia mistake. Her
  femininity comes through in what she notices and how coolly she says it, not in
  extra words.
- **Her cool lines stay curt:** "Oh yeah? So?", "Yeah, yeah...", "Not that I care
  much." These already work.
- **Her polite lines stay polite** (1:49, 1:50, 1:117), so the switch to casual (1:129)
  still shows.

## Lines to look at in review

Register (folksy or boyish where the Japanese is plain feminine):
- 1:46 あら,元気? "Oh, hey. How ya doing?". あら is a mature "Oh!"; maybe "Oh! How are
  you doing?"
- 1:20, 1:47 なぁに? "Yeah? What's up?". なぁに is a soft "Hm? What is it?"; "Yeah?"
  reads gruff.
- 1:201 "some folks... one of 'em's a Lord".
- 1:208 "Dunno why, but...".
- 1:243 "Sorry 'bout that." ゴメンネ is a light "Sorry!"
- 1:275 "Lemme see, lemme see!" 見せてよ見せて is "Show me, show me!"
- 1:30, 1:36, 1:42 "See ya". じゃあね is fine as "See you" or "Bye"; "ya" three times
  sets the folksy tone.
- 1:136 "That's cold. Eh, whatever." ヒドイわね。ま,いいけど is "How mean. Oh well."

Size (the tag and her introduction):
- 1:3, 1:7, 1:24 tag "Tall woman" for 大柄な女: "Big woman", "Large woman" or "Strapping
  woman". The site never uses the tag, so nothing there would change.
- 1:116 Alstron's "The taller lady here" for こっちの大きな方: "the larger lady here".

Already in her voice, as far as this profile goes: 1:3, 7, 48, 49, 50, 51, 52, 117,
129, 178, 184, 190, 196, 203, 212, 219, 225, 231, 237, 249, 258, 262, 269.

## Sources

- Her lines: NPC_MES1, strings listed above; the talk-script dumps in
  `rips/re/work/C/` for who speaks around her.
- Guy's party and Dragon Quest III: `docs/npc-translation.md`, with its sources
  (StrategyWiki, Game8, pixiv dictionary on 女戦士(DQ3)).
- 麻子軒, 「計量的アプローチによる役割語の分類と抽出の試み―テレビゲーム『ドラゴン
  クエスト3』を例に―」, 計量国語学 32(2), 2019, pp. 103-116:
  https://www.jstage.jst.go.jp/article/mathling/32/2/32_103/_article/-char/ja . It
  lists the markers of 女ことば (あたし, ちゃう, あら, かしら, わ) and of 男ことば
  (オレ, あんた, ぜ, ちまう).
- Kinsui Satoshi on 役割語, Japan Foundation:
  https://www.jpf.go.jp/j/project/japanese/teach/tsushin/research/201302.html . Role
  language can include speech nobody really uses, and that is how fiction marks a type.
- JESC survey (`~/corpora/bin/para`): 坊やたち → "hey, boys"; お嬢ちゃんたち →
  "girls", "morning, ladies"; ハイハイ → "uh huh", "yes, yes", "okay, I get it".
