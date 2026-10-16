# Text check: bot runs, chapters 1-13

Checked 2026-10-16 against the text the game printed in every bot run with a text capture:
157 run captures (`rips/harness/chapters`, `ch12`-`ch16`, `t3` and its rounds, `t2`,
`rips/agents/chapters/guard15`, `runx` and a11's live capture) and 810 one-trial files from
the inn trials (`rips/harness/t2/trials/inn/captured/`), 13.6 million lines in all. The brief
said 168 files; these 967 are every capture file there is.

All of them were pooled and deduped by (file, idx), or by text when the capture has no
file. That gave 1,802 strings. The 725 already covered by the chapter 14-15 check (the 611
tracked strings and 114 unmatched texts seen in n1v0y, n1v1ac, n1v3w and n1v6v) were
dropped, which left:
- 544 tracked strings: I_NAME_E 126, NPC_MES1 89, EVENTMES 80, SISETU 59, NPC_MES2 52,
  NPC_MES4 45, STATUS 37, FIGHTMSG 29, NPC_MES3 21, NPC_MES5 6.
- 533 captures with no file match: 353 numbers and HP readouts, 87 item names and 93
  character names, monster names and status labels. These were checked by their text.

Many runs are on older builds, so each string was judged by its current text in
`translations/*.json`, read against the Japanese in `rips/stage/out/dumps`, with its status
from `textstatus.py`. The battle templates the 14-15 check already covered were also looked
at again for what gets inserted into them: all 24,109 distinct battle lines in the captures,
and the 147 verb and noun pairs the monster and party records use (`attackverbs.py`).
`evfit.py`, `npcfit.py`, `fightfit.py` and `itemfit.py` report no width or page problems in
any captured string. evfit flags only events 36 and 258, which no run captured, and both
differ from the Japanese on purpose.

**1 bug, 6 awkward, 8 nits.**

Checked and left alone:
- **"ー" in place of ";"** in SISETU 201 and STATUS 447. That's the capture artifact
  explained in the 14-15 report (glyph 0xcc).
- **Kana inside the ancient-letter boxes** in events 80, 107, 136-138, 170, 198 and 268.
  The capture decodes the `{ancient_x}` glyphs as the kana that share their codes.
- **"]Good[" and "]Evil["** in SISETU 197-199. The Japanese uses the same bracket codes
  (`]善[`), as do the event script's ancient-letter lines.
- **Series item names.** Bartok's Trading Post's item data has DEMONS TOOTH in Wizardry VI
  (12 entries), THIEVES BOW in Wizardry V, and CURSED BREAST and SUFFOCATE HELM in
  Gaiden IV. SHEPHERD CROOK is common across the series.
- **Breath lines with a break after the name** (FIGHTMSG 79-96, "Bird / spits venom
  everywhere."). The English added breaks the Japanese doesn't have. They predate the
  word wrap and look a little ragged with short names, but nothing is wrong with them.
- **Settled already:** "Hits 1 times!", "Really throw it away?", Balbo's "you lot" in his
  maze lines (2:86, 2:88). Fixed tonight and not raised again: the ability verbs ("Mother
  startles a shriek."), "looses at", run-together names ("OrcHealer", "Strange \nFigure"),
  HobGoblin and FAERIE'S CLOTHE in old captures, and Cutie Thief's verb.
- **Melee lines.** The verb and noun pairs read fine ("Gremlin Mother slaps Venus with an
  open hand.", "Arch Ninja thrusts at Venus with a knife-hand.").
- **EVENTMES and NPC_MES1** (reviewed with Chris): no mechanical problems in the 80 and 89
  captured strings.

## Bugs

### 1. FIGHTMSG 137: "drained of 1 levels"

- JP: `{ff18}は {ff11}2レベル吸い取られた`
- EN: `{ff18} is drained of {ff11}2 levels.`
- Printed: "Earth is drained of 1 levels.", "Mercury is drained of 1 levels.", "Uranus is
  drained of 1 levels." This was 4 runs (f1v3g, n1v0r, n1v1v, n1v6o). Each time it came
  from Ruby Hand's fists, which drain one level, so the singular is the case players will
  see most.
- **Problem.** The number doesn't agree with the noun. The Japanese avoids this because
  レベル has no plural. This isn't the "Hits 1 times!" case: no series tradition stands
  behind it.
- **Fix.** `{ff18}'s level drops by {ff11}2.`, which reads right for any number
  ("Earth's level drops by 1."). In fightfit's simulation that's at most 2 lines over all
  name and number lengths. `{ff18} loses {ff11}2 level(s).` also fits, but it's clunkier.

## Awkward

### 2. FIGHTMSG 163: monster healing still has no unit

- JP: `{ff13}は {ff11}1回復した`
- EN: `{ff13} recovers {ff11}1.`
- Printed: "Beast recovers 14.", "Orc Adept recovers 11.", "OrcHealer recovers 12." This
  was 6 runs.
- **Problem.** 143, the party version, became "recovers 10 HP." tonight. 163 is the
  monster version of the same line and was left out.
- **Fix.** `{ff13} recovers {ff11}1 HP.` That's at most 2 lines with a 17-letter name and
  5 digits.

### 3. SISETU 191: Dracon "the only race that breathes"

- JP: ドラゴンと人間のハーフ。唯一ブレスを吐くことができる。肌が硬い鱗の為,特殊攻撃に強い。
- EN: "Half dragon, half human, and the / only race that breathes. Scaly / skin makes them
  resist specials."
- Shown at character creation (5 runs).
- **Problem.** "The only race that breathes" reads as breathing air. ブレスを吐く means a
  breath attack.
- **Fix.** "Half dragon, half human, and the / only race with a breath attack. / Scaly
  skin resists specials." Widths are 166/156/135 px. The widest race and class line is
  190 px (SISETU 209).

### 4. SISETU 208: Bard description starts with a fragment

- JP: 楽器を奏でて,呪文と同様の効果を発揮する。魔法使い呪文を習得程度は低いが盗賊技能有り。
- EN: "Instruments that work like spells. / They learn Mage spells, slowly, / and have
  thieving skills."
- Shown at character creation (5 runs).
- **Problem.** "Instruments that work like spells." has no verb, so it reads like a
  label. The other class descriptions all say what the class does.
- **Fix.** "Their instruments work like spells. / They learn Mage spells, slowly, / and
  have thieving skills." Widths are 177/158/124 px.

### 5. NPC_MES4 84: Cresson's decipher score (ai-reviewed)

- JP: どうやらあなたたちとの適合率は{ff11}0%でしょうか。
- EN: `Um, you seem to match us at about {ff11}0%.`
- Printed: "Um, you seem to match us at about 0%." This was 3 runs.
- **Problem.** "You seem to match us" sounds like the people match, not the results. The
  "about" is there for でしょうか, but it reads oddly next to an exact figure, and
  especially next to 0%.
- **Fix.** `Um, it looks like your results\n match ours {ff11}0%.` (npcfit: OK)

### 6. NPC_MES4 39 (and Bergamot's copy, 33): "bound to get on" (open scene 6)

- JP: 26個の古代文字がこのように揃っていれば,研究も進むというものだ。
- EN: "With all 26 ancient glyphs laid out like / this, our research is bound to get on."
- 3 runs.
- **Problem.** "Get on" for "make progress" is British.
- **Fix.** "...our research is bound to move forward." (npcfit: OK)

### 7. NPC_MES4 107: Cresson's "ever so lively" (open scene 9)

- JP: 年若い冒険者のパーティが来ましてねぇ,とてもにぎやかだったのですよ。
- EN: "A party of young adventurers came by. / They were ever so lively."
- 1 run.
- **Problem.** "Ever so" is British.
- **Fix.** "They were very lively." (npcfit: OK)

## Nits

### 8. FIGHTMSG 78: "breathes a sweet breath"

- JP: `{ff13}は 甘い息を吹き掛けた`
- Printed: "Sleeper breathes a sweet breath.", "Tamazul breathes a sweet breath." This was
  21 runs.
- **Problem.** "Breathes" and "breath" repeat each other. 97 has the same shape ("breathes
  a holy breath"), though no run showed it.
- **Fix.** `{ff13} blows a sweet breath.` (吹き掛けた), and 97 `{ff13} blows a holy
  breath.` Both are at most 2 lines.

### 9. SISETU 201: Mage "few items"

- JP: HPは低く装備できる物は少なく前衛には向かない。
- EN: "Low HP and / few items; not for the front."
- Shown at character creation (157 runs).
- **Problem.** 装備できる物 means what they can equip. "Few items" sounds like they don't
  carry much.
- **Fix.** "...Low HP and / little gear; not for the front." Widths are 152/153/147 px.

### 10. NPC_MES2 88 (and 89): "three discs" (ai-reviewed)

- JP: 三つの円盤を操作すれば良いはずだが,
- EN: "Turning the three discs ought to do it,"
- 4 runs.
- **Problem.** The door's own text (events 158 and 159, 三層に分かれた円盤) says "a dial
  of three rings". Guy's line (NPC_MES1) and the SISETU 339 hint say "three rings" too. Balbo's two copies are
  the only ones that say discs.
- **Fix.** "Turning the three rings ought to do it," (npcfit: OK)

### 11. NPC_MES4 62: Bergamot's ".." and "you lot" (open scene 4)

- JP: ・・おまえさんたちゃ物覚えが悪いのぉ・・・。
- EN: `..Memories like sieves, you lot...`
- 1 run.
- **Problem.** The line opens with two dots, while the rest of the game uses three or
  more. "You lot" is British. It was kept as Balbo's voice, but it has spread beyond him:
  Alba (2:51), Zaril (3:22, 23, 35, 238; 5:8, 9, 22, 80) and Bergamot (4:62, 4:145) say it
  too. The voice sheet's Bergamot is an American old codger ("I tell ye", "whippersnappers").
- **Fix.** `...You folks sure got memories like sieves...` (npcfit: OK). It might be worth
  a look at the others when their scenes come up.

### 12. NPC_MES4 105: Cleo's "full of beans" (open scene 9)

- JP: みんな若くて元気いっぱいでしたよ。
- EN: "All young and full of beans."
- 1 run.
- **Problem.** "Full of beans" is mainly British. To many American readers it means
  talking nonsense.
- **Fix.** "All young and full of energy." (npcfit: OK)

### 13. NPC_MES2 220: Reiran "try hard" (ai-reviewed)

- JP: あたしもがんばろっと。
- EN: "Okay! Guess I'll try hard too."
- 1 run.
- **Problem.** "Try hard" reads stiff for her. がんばる here means doing her best.
- **Fix.** "Okay! Guess I'd better do my best too." (npcfit: OK)

### 14. Developer item names that no other Wizardry uses

These have the same kind of slip as tonight's PRIEST'S MACE and GLOVE OF THE DEAD. Bartok's
Trading Post's item data finds each of them only in Dimguil:
- AXE OF GIANT'S (I_NAME_E 54/993, 巨人の斧, 10 runs) has a broken possessive. "GIANT'S
  AXE" would match GIANT'S CLUB (巨人の棍棒) and is the same length.
- DEVILS STICK (56/995, 悪魔の小杖, 7 runs) is missing its apostrophe, while DEMON'S STAFF
  has one. Its neighbor DEMONS TOOTH is Wizardry VI's own spelling, so the developer may
  have copied that pattern on purpose.
- HURT GLOVES (151/1090, 傷ついた小手 "damaged gauntlets", 4 runs). "DAMAGED GLOVES" would
  say what it is.

### 15. "Ancient glyphs" vs "ancient letters" (open scene 6)

- The scholars say "ancient glyphs" (NPC_MES3 1 line, NPC_MES4 6 lines; captured: 4:37,
  39 and 84, 3 runs). The events, the item text and SISETU say "ancient letters" (56
  lines). SISETU 411 is "Decipher Ancient Script". All of them are 古代文字.
- **Fix.** "Letters" in the NPC lines, when NPC_MES4's scenes are reviewed. Scholars could
  plausibly say glyphs, so this may be fine as it is.
