# Fritillaria: character profile (2026-11-05)

Written before his voice review, the way Linaria's and Lychee's were. The question came
up during Lychee's profile: the game calls him a "small man" (1:120), but the voice
sheet calls him a "scrappy kid thief". This profile is drawn from his 53 tagged strings
(tags フリチラリア and 背の低い男), 31 in NPC_MES1 and 22 in NPC_MES5. It also uses the
lines where others introduce or describe him (1:120, 5:27, 5:28, 5:65), the party
timeline in `docs/npc-map.md`, his portraits, and the sources at the end. His lines are
collected in `rips/review/fritillaria-lines.txt`, which isn't committed.

## Short version

Fritillaria is a small grown man: almost certainly a Hobbit, Wizardry's small race and
its natural thieves. He isn't a child. His sore spot is being treated like one. He
bristles when Zaril introduces him as "this little one" and complains that Balbo calls
him a brat, ガキ.

He has two moods, and the game's story explains them. With you, and later with Zaril,
he's cheeky and cocky: おいら, あんたたち, ヤァ!, スッゲー! ヤルじゃん!. In Guy's party's
group talk, he's cowed. He stammers, speaks stiff polite Japanese (私, です/ます,
了解しました, ごめんなさい) and apologizes. He tells you why: the party "relies on me
completely; when I fail, they hit me" (1:254). Later someone leaves him behind,
paralyzed, Zaril saves him, and he follows Zaril from then on with a sidekick's devotion
(5:84, 5:90).

The current English gets his cheek and his stammer. It also bakes in two things the
Japanese doesn't have:
- **Childhood:** "When I grow up, I wanna be a Ninja" (5:78) for 将来, which means
  "someday".
- **A rough grammar:** "ain't", double negatives ("I don't know nothin'", "I ain't
  heard of nobody"), "Whaddaya", "meetcha" and "ya". His Japanese is grammatical. It's
  casual and a little rustic, and that comes from おいら.

The misread is real but narrow. The voice holds, his age and grammar need to change,
and so do the few lines that call him a kid.

## Who he is, from the game

- **Small, not young.** His tag before you know his name is 背の低い男, "short man"
  (1:10, 1:12, 1:27; 5:4, 5:7), not 少年 or 男の子. Alstron introduces him as
  こっちの小柄な男性, "this small-built man" (1:120). 男性 is the adult word, though
  Alstron is polite about everyone ("the larger lady", 大きな方, for Linaria).
- **Built like a Hobbit.** His portrait is a round, rosy face under a fur cap. His battle
  sprite is stocky, with big hands and a short broad body, holding a blade in each hand
  in a low crouch (`rips/review/fritillaria/portraits3x.png`, beside Linaria and Guy).
  That's a small adult's build, not a child's. The text never names his race. "Hobbit"
  is an inference from the portrait, the size jokes and the Thief class. Wizardry's
  Hobbits are its best thieves, and a halfling thief is the stock small rogue of D&D
  fantasy.
- **Touchy about his size.** Zaril says この小さいのがフリチラリアだ, "this little one is
  Fritillaria", and he snaps back 「小さいの」はよけいだよ!, "the 'little' was
  uncalled for!" (5:27-29). He doesn't think he'll like Balbo, だってあの人,おいらのこと
  ガキって言うんだもん!, "because he calls me a brat!" (5:64, 5:65). The もん is a pout:
  he's touchy about being called a kid, and he sounds a little like one when he
  complains about it. That's the joke the trope runs on.
- **A junior with ambitions.** 早く一人前になって,自分のパーティを持ちたいです, "I want
  to become full-fledged soon and have a party of my own" (1:240). 一人前 is a
  journeyman's word, "a full member of the trade", not "a grown-up". おいら将来,忍者になり
  たいんだ, "someday I want to be a Ninja" (5:78): that's Wizardry's Thief-to-Ninja
  class change, the classic thief's dream. He calls himself けちな盗賊, "a small-time
  thief" (1:140).
- **The bullied new member in Guy's party.** Guy's party needs a Thief and goes to
  scout one (1:257). Fritillaria joins and is "scouted" (1:121), and he's the one
  Alstron calls 便利な, "handy" (1:120). Then the confession: 宝箱の罠の解除が苦手です。
  このパーティは私を頼り切っています。失敗すると殴られます。ごめんなさい。 "I'm bad at
  disarming chest traps. This party relies on me completely. When I fail, I get hit.
  I'm sorry." (1:254). The voice sheet called this one line's stiffness "the joke".
  It's actually how he talks in all of Guy's party's group turns: な,何も知らないよ
  (1:187), え! はい! わかりました。たぶん。 (1:193), は,はい。了解しました。 (1:228),
  と,とくに。すいません。 (1:234), や,役にたてぬ。ごめんなさい。 (1:246), and
  そ,そのことは何度も聞きましたが。 (1:272). He's nervous and on his best behavior in
  front of the others.
- **Rescued by Zaril.** 麻痺して動けなくなって,一人で置いてけぼりくらってたおいらを,
  ザリルさんが助けてくれたんだ, "I was paralyzed and left behind on my own, and Zaril
  saved me" (5:84). The timeline fits Guy's party: Guy's party is wiped out in the
  ogre's cage, and Lilia replaces Fritillaria afterwards (`docs/npc-map.md`). The game
  never says who left him. In Zaril's party he's his old cheeky self, always says
  ザリルさん, and hopes Zaril "stays just the way he is" (5:90).
- **Cheeky with outsiders.** ヤァ! 殺人集団。あんたら殺しすぎ! "Hey! Murder squad. You
  guys kill too much!" (1:78), the "walking corpse" tease (1:79), フーンだ! (1:27),
  チェッ,あんたたちか (1:290), and スッゲー! ヤルじゃん! when he's impressed (5:93).

## His language: what he uses

| Marker | Where | What it signals |
|---|---|---|
| おいら | 1:10, 12, 14, 121, 132, 140, 290-292; 5:4, 13-15, 30, 55, 58, 64, 65, 72, 75, 78, 84, 90 | casual, boyish, a little rustic male "I" |
| 私 | 1:254 | stiff, on his best behavior |
| あんた, あんたたち, あんたら | 1:14, 78, 290, 291; 5:13, 14, 16, 81 | casual "you guys" |
| 君たち | 1:265 | milder "you", in Guy's party's turn |
| 〜な, 〜なっ, 〜よ, 〜だよ, 〜じゃん, 〜もん | throughout | casual young male |
| わりぃ, スッゲー, ヤルじゃん, チェッ, フン(ー)だ | 5:75, 5:93; 1:290; 1:27, 5:61 | youthful, a bit rough-edged |
| stammers (な,な / は,はい / や,役に) | 1:187, 215, 222, 228, 234, 246, 272 | nervous, in Guy's party |
| です/ます, ごめんなさい, すいません, 了解しました | 1:193, 228, 234, 240, 246, 254, 272 | stiff politeness, in Guy's party |
| 役にたてぬ | 1:246 | an old-fashioned, stiff negative, said nervously |

## What he doesn't use

- No ungrammatical Japanese: nothing that would map to "ain't", "nothin' new to spill"
  or a double negative. なんにも知らない (5:75) is ordinary colloquial "don't know
  anything at all".
- No ガキ or 子供 for himself. Only Balbo calls him ガキ, and he resents it.
- No オレ and no ぜ: he's not the rough tough guy, as Zaril and Balbo are.
- No dialect. おいら gives a rustic, boyish flavor by itself, the way おら or オイラ does
  for a country boy or a small cheerful sidekick in fiction (Kinsui's 役割語). The rest
  of his speech is standard casual Japanese.

## What it means for the English

- **He's a small man, not a boy.** No "When I grow up". No "kid" for himself, and none
  in other people's lines unless the Japanese has it (Balbo's ガキ, "brat", stays).
- **Keep the cheek:** "Hey!", "Tch", "Hmph!", "Whoa, awesome! You guys are good!".
  Casual contractions and "gonna" are fine for おいら's flavor.
- **Drop the bad grammar:** no "ain't" and no double negatives, because nothing in his
  Japanese is ungrammatical. Use "whaddaya", "meetcha", "ya" and dropped g's sparingly,
  if at all. They read as a street kid, which is the misread. I suggest plain casual
  spellings, and that's for Chris to decide.
- **Keep the two moods apart:** cheeky with outsiders and in Zaril's party, stammering
  and stiffly polite in Guy's party's group turns. 1:254 should sound formal and cowed,
  because the formality is what tells you how they treat him.

## Lines to look at in review

His age:
- 5:78 "When I grow up, I wanna be a Ninja." 将来 is "someday" or "in the future":
  "Someday I want to be a Ninja."
- 1:121 "these guys scouted me special!" The Japanese is このパーティにスカウトされたんだ,
  with no "special". `docs/npc-map.md` quotes the "special" too.

Grammar and register:
- 5:72 "I ain't heard of nobody else meetin' him... Maybe he ain't from this world?"
- 5:75 "Sorry, I don't know nothin'."
- 1:12, 5:4 "Ain't you ever heard of me?" for おいらのことは,知らないのかい?: "Don't you
  know who I am?"
- 1:78, 5:16 "If it ain't the murder squad." for ヤァ! 殺人集団.
- 1:10, 14, 290, 291; 5:13, 14 "Whaddaya want with me?"
- 1:121, 132; 5:30, 122 "Hiya!... Nice to meetcha!"
- 1:140 "Nice to meet ya."
- 1:292, 5:15 "You doin' good? Me, I'm doin' great, as ya can see. So whaddaya need
  today?"
- 5:87 "I got nothin' new to spill."
- 5:58 "You got business with me or somethin'?"
- 5:65 "'Cause he keeps callin' me a brat!" adds "keeps".
- 5:29 "Ya didn't have to say 'little'!"

His cowed mode:
- 1:254 is casual in English ("I'm not so good at...", "Everyone here is counting on
  me, but..."). The Japanese is stiff and formal: 私, 苦手です, 頼り切っています,
  殴られます.
- 1:240 is fine, and polite ("I'd like to...").

Other people's lines about him:
- 1:120, Alstron: "This little fellow is our newest member, the ever-handy Thief,
  Fritillaria." 小柄な男性 is "small-built man". "Little fellow" is diminutive in a way
  Alstron's 男性 isn't, so "This small gentleman"?
- 5:27, 5:28, Zaril: "This little one's Fritillaria." That's right, because it sets up
  his complaint (5:29).

Already in his voice, as far as this profile goes: 1:27, 33, 39, 79, 187, 193, 215,
222, 228, 234, 246, 265, 272, 297; 5:7, 12, 17, 55, 61, 64, 68, 81, 84, 90, 93, 96, 120.

## Sources

- His lines: NPC_MES1 and NPC_MES5, the strings listed above. The party timeline is
  in `docs/npc-map.md` (Guy's party, Zaril's party, the ogre's cage).
- Portraits: `rips/review/faces/fritillaria.png` and battle sprites n01_4.gif and
  n14_1.gif from Emonoya's NPC pages (mirrored in the site repo), composed with Linaria's
  and Guy's in `rips/review/fritillaria/portraits3x.png`. Emonoya's roster lists him as
  盗賊系, level 7 with Guy and level 8 with Zaril.
- Kinsui Satoshi on 役割語, Japan Foundation:
  https://www.jpf.go.jp/j/project/japanese/teach/tsushin/research/201302.html . On
  rustic first persons like おら as instant character shorthand, see the role-language
  discussion surveyed at https://dic.nicovideo.jp/t/a/%E4%B8%80%E4%BA%BA%E7%A7%B0 .
  I found no source that treats おいら on its own, so its flavor here ("boyish, a little
  rustic") is my reading.
- JESC survey (`~/corpora/bin/para`): 将来〜なりたい → "in the future I'd like to be",
  "what you'd like to be in the future", never "when I grow up" in these hits.
