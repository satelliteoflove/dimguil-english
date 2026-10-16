# Text check: bot runs n1v0y, n1v1ac, n1v3w, n1v6v (chapters 14-15)

Checked 2026-10-15 against the text the game printed in four bot runs
(`rips/harness/chapters/{n1v0y,n1v1ac,n1v3w,n1v6v}/captured.jsonl`, 164,053 lines). None of
the four runs covers chapter 13: n1v6v plays chapters 14 and 15, the other three only
chapter 15. Every string the runs showed was checked, whichever chapter it came from.

After deduping by (file, idx) there were 611 strings in tracked files: STATUS 211,
SISETU 148, I_NAME_E 129, FIGHTMSG 83, EVENTMES 22, NPC_MES1 8, NPC_MES3 5, NPC_MES5 3,
NPC_MES2 2. Another 76 captures had no file match. They're item names, numbers and
status-screen labels, and were checked by their text. Each was read against the Japanese
in `rips/stage/out/dumps`, with its status from `textstatus.py`. `evfit.py` and `npcfit.py`
report no width or page problems in any captured event or NPC string.

**3 bugs, 5 awkward, 4 nits.**

Checked and left alone:
- **Semicolons in spell descriptions.** The capture shows ";" as "ー" ("startles a groupー
  their AC +4"). Both share glyph 0xcc, and the decoder prints the kana. The VWF table
  gives 0xcc a width of 2 px, so it draws as a semicolon. This is a capture artifact.
- **"Hits 1 times!"** (FIGHTMSG 118). This was a settled decision on 2026-10-12.
- **"There's no trap"** without a full stop (FIGHTMSG 221). This was deliberate,
  because of "Oops! {trap}!!".
- **"you lot"** is Balbo's kept voice, and DEMON'S STATUE is the item's name.
- **"DISPLASER/ROBE" and "PADDED/LEARHER" in the harness logs.** These come from the
  bot's own item reader. The screen shows DISPLACER ROBE and PADDED LEATHER.

## Bugs

### 1. FIGHTMSG 214: targetless attacks read as broken English

- JP: `{ff13}は {ff14}{ff15}` (e.g. ゴースト は 金切り声 で 驚かせた)
- EN: `{ff13} {ff15} {ff14}.`
- Printed in these runs: "Mother startles a shriek.", "Mushroom Master startles a
  shriek.", "Merry Puppet tries to lull a strange dance.", "Strange Figure tries to lull a
  strange dance."
- Older harness runs show the same thing: "Ghost startles a shriek." (92 times),
  "Were Bat glares at a piercing glare.", "Giant Spider tries to entangle sticky goo.",
  "Faerie Fly tries to lull strange mutterings."

**Cause.** The {ff15} verbs are written for the targeted templates 108/109 ("{ff13} {ff15}
{ff18} with {ff14}."). Without a target, verbs 45 "glares at", 46 "tries to lull",
47 "startles" and 76 "tries to entangle" end up taking the attack noun as their object.
Verbs 72 "unleashes the power of" and 75 "raises" read fine in 214. Verbs 45-47 are also
used with a target ("2-Head Toad startles Venus with a loud shout.",
"Basilisk glares at Venus with its many eyes."), so changing the verb strings or the
214 template alone breaks the other case.

**Suggested fix.** FIGHTMSG 65-71 are unused (未使用). Put targetless forms there:
- "tries to lull everyone with"
- "startles everyone with"
- "glares at everyone with"
- "tries to entangle everyone in"

Then point the targetless attack entries in the monster records (DATA02, BATTLE.BIN) at
those slots. That gives "Ghost startles everyone with a shriek." and "Giant Spider tries
to entangle everyone in sticky goo." First confirm that the verb index is stored per
attack in the record. If it isn't, 214 needs a small code change that uses a separate
verb for those four.

**Fixed (2026-10-15, wt/verbfix).** The verb index is per attack and the template is fixed
by the attack's noun, so it was a data fix. Every ability's verb was checked, not only these
four; see `translation-notes.md`, "Monster abilities with no target".

### 2. FIGHTMSG 106: blank line in the dispel message

- JP: `{ff18}は {ff11}0体の\n{ff13}の 呪いを解いた`
- EN: `{ff18} dispels {ff13}.\n({ff11}0 destroyed)`
- Printed (n1v1ac, frame 21154): "Earth dispels Noisy Tempter." / (empty line) /
  "(4 destroyed)". The expanded bytes end the first line `c2 ff21 ff21`.

**Cause.** "Earth dispels Noisy Tempter." fills the 24-code battle line exactly, so the
automatic break goes in after the full stop. The explicit `\n` then follows it and leaves
an empty line. `fightfit.py` doesn't catch this, because the message still fits in
3 lines. A simulation over all name lengths finds one other string that can do it:
FIGHTMSG 188 "{ff13} nullifies\nthe spell." with a 16-letter monster name.

**Suggested fix.** In `asm/word_wrap.asm`, skip the automatic break when the next code is
{ff21} or {ff40}, and add a blank-line check to `fightfit.py`. A text-only fix for 106:
`{ff18} dispels {ff13}. ({ff11}0 destroyed)`, which lets the word wrap place the count.

**Fixed** (2026-10-15, a1529b7, the proper fix): `asm/word_wrap.asm` doesn't break a full
line when {ff21} comes next, and `fightfit.py` reports blank lines. Shots:
`docs/shots/wrap-blank/`.

### 3. Monster names run together in battle messages (parked item, cause found)

- Printed in these runs: "ArchNinja kicks Venus with its feet.", "ArchPriest casts
  Bakadi.", "OrcKnight dies.", "RageBeast", "BladeMaster", "OgreSorcerer", "OgreBrother",
  "KoboldRogue", "KoboldScout", "KoboldPriest", "KoboldKing", "GoblinOracle".
- The group list shows the same monsters correctly, as "Arch / Ninja", "Orc / Knight"
  and so on.

**Cause.** The monster records store these names with a bare line break, for example
`Arch{ff21}Ninja`. The group list draws the break, and the battle messages drop it. The
records that already have a space before the break (`Man in {ff21}Robe`,
`Strange {ff21}Figure`) come out right in messages ("Man in Robe is confused."). So this
is in the game's data and display, not in the capture.

This is the item in translation-notes.md "Monster names run together in battle text?",
which Chris parked on 2026-10-14. It's listed here because it shows up in every fight
with these monsters.

Watch out for two things:
- Some records hold `Man in{ff21}Robe` and `Man in{ff21}Armor` with no space, so those
  would print "Man inRobe".
- `Nex{ff21}tepehua` and `Tepe{ff21}yollotl` should stay joined.

**Suggested fix.** Add a space before the break in each two-word record, the way the
`Man in {ff21}Robe` records do. Then check the group list for a double space, which the
parked note saw with "Strange  Figure".

## Awkward

### 4. FIGHTMSG 18 (verb used in 98/99): "looses at"

- JP: `を 放った`
- Printed: "Mercury looses at Arch Mage with BLOW GUN.", "Mercury looses at OgreSorcerer
  with BLOW GUN."
- **Problem.** "Looses at" is archaic and reads like a typo for "loses".
- **Fix.** "fires at" ("Mercury fires at Arch Mage with BLOW GUN.").

### 5. FIGHTMSG 143: no unit on healing

- JP: `{ff18}は {ff11}1回復した`
- EN: `{ff18} recovers {ff11}1.`
- Printed: "Mercury recovers 10."
- **Problem.** "Recovers 10" doesn't say what is recovered.
- **Fix.** `{ff18} recovers {ff11}1 HP.` This is at most 27 codes, so it wraps to 2 lines
  in the worst case.

### 6. SISETU 84: "Gather gold on this character?"

- JP: このキャラクタにお金を集めますか?
- Shown when a character is short of gold (n1v6v, next to "Not enough gold.").
- **Problem.** "Gather gold on" isn't idiomatic, and it doesn't match the Pool Gold command
  (SISETU 395, STATUS 93).
- **Fix.** "Pool all gold on this character?"

### 7. SISETU 314: "Your pack is full. Swap it for something."

- JP: アイテムがいっぱいです。どれかと交換してください
- **Problem.** "Swap it for something" is vague about what the player has to do.
- **Fix.** "Your pack is full. Choose an item to swap."

### 8. NPC_MES3 16 (open scene): the little elf's goodbye

- JP: 小さなエルフ「失礼します。
- EN: Little elf "Excuse me."
- **Problem.** This is the parting line. 失礼します here means "we'll be going", but in
  English "Excuse me." reads as an apology or an interruption.
- **Fix.** "...Goodbye." This keeps her shy, clipped manner (her hello is "......Hello.").

## Nits

### 9. I_NAME_E 314: DEMON STATUE vs DEMON'S STATUE

- After "Obtained a strange stone statue." (EVENTMES 187), the pickup line reads
  "DEMON STATUE obtained." (SISETU 305 + I_NAME_E 314).
- The pack and the chapter title say DEMON'S STATUE (I_NAME_E 1253).
- **Fix.** Make 314 "DEMON'S STATUE". At 14 letters it fits: that list holds names up to 20.

### 10. SISETU 36: "Really throw it away?"

- JP: 本当に捨てますか?
- **Problem.** The same action is "Drop" in the menu (STATUS 101) and in the prompts around
  it (SISETU 90 "Drop which item?", SISETU 303 "Who will drop it?").
- **Fix.** "Really drop it?"

### 11. SISETU 404 / 147: Temple menu and prompt don't match

- **Problem.** The menu item is "Heal Character" (キャラクタを助ける), and the prompt
  that follows is "Help whom?" (誰を助けますか?).
- **Fix.** Use one verb for both: "Heal whom?", or "Help Character".

### 12. Developer item and monster names not on the 2026-10-09 kept/fixed list

These were seen on the equipment and pack screens and in the group list:
- GLOVE OF DEAD (I_NAME_E 178/1117, 死者の小手)
- FAERIE'S CLOTHE (132/1071, 妖精の服)
- PRIESTS MACE (92/1031, 僧侶のメイス)
- HobGoblin (monster group name)

They read as slips, not series spellings. Possible names are "GLOVES OF THE DEAD",
"FAERIE CLOTHES", "PRIEST'S MACE" and "Hobgoblin". Check the earlier games first, as
for the other developer names.
