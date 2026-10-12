# Description check: what the text claims against what the game does

Phase 3 of the code analysis. Every item description, every spell description, the
Compendium's mechanical claims and the race/class/stat help text were read against the
records on the original disc and the decompiled code (rips/re/decomp, from commit 585c983).
No translation was changed. Where the Japanese itself is wrong the error is the original's,
and whether to correct it is Chris's call; our own mistranslations are listed separately as
fixes to approve.

Marks: **[record]** the record field was read; **[code]** the routine was read;
**[inf]** inferred (a field's meaning or a monster-to-description match not proven).
Nothing here was checked in the emulator yet.

Tool: `scripts/re/desccheck.py` (`items`, `flags`, `monsters`). Scratch output is in
rips/re/work/P3-desc/ (items.txt, spells.txt, monsters.txt, catalg_claims.txt).

## Summary

| Kind | Checked | Original's errors | Our mistranslations |
|---|---|---|---|
| Spell descriptions (STATUS 420-503) | every damage/heal spell, AC and screen spells | 18 wrong ranges, 3 overstated effects | none (we copy the Japanese numbers) |
| Item descriptions (ITEM.DAT §1, 307 entries) | every claim the record can test | 9 wrong or overstated claims, 6 unmentioned curses, 7 notable unmentioned restrictions | 3 ("力" read as Strength) |
| Compendium (M_CATALG §4-17) | the 99 entries with a mechanical claim | 1 wrong (2-Head Snake drain), 2 unsupported | none found |
| Help text (SISETU 184-219) | race, alignment, class and stat lines | none found | none found |

Our English follows the Japanese numbers faithfully, so every wrong spell range is the
original's.

**Corrected 2026-10-11** (Chris, decisions.md item 11: the English now says what the game
does). Spells in 0f0a69b, items in da781e2, the Compendium in a25c54c, Bacortu (found in
the sweep below) in d798054, and our three mistranslations, with Chris's wording, in
8ace280. Each change is listed with old and new wording in translation-notes.md,
"Description corrections". Checked on the real screens of the built disc: before and
after captures in `docs/shots/description-corrections/` and
`docs/shots/strength-mistranslation/`. The three mistranslations are all the same slip: 力 ("power") rendered as the
Strength stat on weapons that don't raise it.

## Spells

Battle damage and healing go through `spell_damage_one` (0x800b0b50),
`spell_damage_group` (0x800b0930), `psionic_damage` (which calls `spell_damage_one`) and
`spell_heal`. Each rolls n dice of 1..sides: `n + Σ rand_below(sides)`, so the range is
n to n×sides. Camp values come from B-camp.md's spell table. **[code]**

### Wrong ranges (all the original's)

All 18 corrected in 0f0a69b. Madial's bar now gives both values ("party 17-68; camp
10-50"), the most the 30-code bar holds.

| STATUS | Spell | Japanese claim | Our English | Code | Mark |
|---|---|---|---|---|---|
| 421 | Halito | 敵1体に1~8ダメージ | 1-8 damage to one enemy | 2d4: **2-8** | [code] |
| 423 | Melito | 敵1グループに1~8 | 1-8 damage to an enemy group | 2d4: **2-8** (fire) | [code] |
| 442 | Badios | 敵1体に1~8 | 1-8 damage to one enemy | 2d4: **2-8** | [code] |
| 441 | Dios | HPを1~8回復 | heals one ally 1-8 HP | 2d4: **2-8**, camp and battle | [code] |
| 484 | Diomas | HPを2~6回復 | heals one ally 2-6 HP | 3d2: **3-6**, camp and battle | [code] |
| 461 | Madial | 味方全員のHPを30~60回復 | party heals 30-60 HP | battle 17d4: **17-68**; camp 10d5: **10-50** | [code] |
| 430 | Lahalito | 敵1グループに6~58 | 6-58 damage to a group | 6d6: **6-36** | [code] |
| 429 | Tzalik | 敵1体に24~58 | 24-58 damage to one enemy | 24d2: **24-48** | [code] |
| 436 | Ladalto | 敵1グループに44~98 | 44-98 damage to a group | 10d10: **10-100** | [code] |
| 437 | Lazalik | 敵1体に64~80 | 64-80 damage to one enemy | 40d2: **40-80** | [code] |
| 435 | Zilwan | 不死系の敵1体に1000 | 1000 damage to one undead | 255d10: **255-2550**, undead only | [code] |
| 480 | Alikus | 敵1体に80~130 | 80-130 damage to one enemy | 48d3: **48-144** | [code] |
| 497 | Dalosto | 敵1体に36~64 | 36-64 damage to one enemy | 14d5: **14-70**; 7d5 (7-35) against cold resisters, 28d5 (28-140) against the cold-weak | [code] |
| 501 | Galtomas | 全ての敵に12~48+状態異常 | 12-48 to all, plus ailments | 4d12: **4-48**, plus the ailment roll | [code] |
| 483 | Sios | 敵1体に1~10精神的な | 1-10 mental damage to one | 2d2: **2-4** | [code] |
| 486 | Lios | 敵1グループに2~10精神的な | 2-10 mental damage, group | 2d2: **2-4** | [code] |
| 492 | Masios | 敵1グループに2~16精神的な | 2-16 mental damage, group | 8d2: **8-16** | [code] |
| 502 | Lasios | 全ての敵に9~72精神的な | 9-72 mental damage to all | 8d9: **8-72** | [code] |

Sios and Lios rolling the same 2d2 looks like a slip in the original code as much as in the
text; Lios is the group version and probably meant more. **[inf]**

### Matching ranges

Mahalito 4d6 (4-24), Madalto 8d8 (8-64), Tiltowait 10d15 (10-150), Dial 2d8 (2-16),
Dialma 3d8 (3-24), Madios 6d3 (6-18), Barenes 8d8 (8-64) all agree with their
descriptions. The cloud spells match per round; they last 3 rounds, which their
descriptions don't say. **[code]**

### Effects stated wrongly or loosely

Morlis, Cortu and Kadorto corrected in 0f0a69b. Morlis also sets the group's result
message to FIGHTMSG 170 "is startled" (`spell_morlis` stores 0xaa in the results table
0x8008d560), which the new wording uses; nothing else reads it. **[code]**

| STATUS | Spell | Claim | Code | Mark |
|---|---|---|---|---|
| 426 | Morlis | 敵1グループのACを4上昇し動きを封じる / "enemy group AC +4, and held fast" | `spell_ac_change` only: the group's AC modifier −4 (easier to hit). Nothing stops them acting. | [code] for the AC; [inf] that no hold exists elsewhere |
| 428 | Cortu | 敵の魔法を無効化する / "a wall that stops enemy spells" | a magic screen: 3/4 of the old screen + 2 × caster level, up to 90%. It cuts the odds, it doesn't stop them | [code] |
| 459 | Kadorto | 死,灰の状態を蘇生させHPを完全回復 / "raises the dead or ash, full HP" | camp Kadorto rolls for success and can fail (B-camp.md, "Kadorto"); the description doesn't say so. The Rod of Raising never fails | [code] |
| 424 | Sogref | 味方一人のACを2低下 / "one ally's AC drops by 2" | correct: it targets one ally. **D-battle.md's line "Sogref +2 the caster" is wrong and needs correcting there.** | [code] |

Banoka, Calfo, Calnova, Mahaman and Quremor were checked in the sweep (below).

## Items

Record layout: 382 records of 0x4c bytes at 0x80052bf2 in rips/clean/dimguil/SLPS_026.91.
JOUKA `FUN_800d0754` and `FUN_800d08f4` copy the record (to 0x80096740) and apply it to
the combat block, and `equip_menu` (0x800ccc94) runs the hidden power. The fields used here:

| Offset | Field |
|---|---|
| +4 | bits 0-2 Good/Neutral/Evil may equip without curse; 3/4 male/female; 5 two-handed; 6 main hand; 7 off hand |
| +5 | bit 7 cursed; bits 0-6 weapon hit effects |
| +6..+0xc | hit-effect chances, % |
| +0xd | hidden power (equip effect code) |
| +0xe / +0x10 | break chance / item it breaks into |
| +0x12 | price |
| +0x1b | battle spell (low 7 bits index STATUS 222+) |
| +0x1c / +0x1e | class mask / race mask |
| +0x21 | regeneration |
| +0x22 | protect mask: hits from these monster classes are halved |
| +0x26, +0x28.. | resist bits, resist % |
| +0x35..+0x3a | AC, to-hit, damage dice (n, sides, bonus), extra swings |
| +0x3e | slay mask |
| +0x42..+0x45 | magic resistance by school |
| +0x46 | reach (1 short, 2 long, 4 bow) |

Hit-effect and resist bits: 0 sleep, 1 poison, 2 stone, 3 confusion, 4 paralysis,
5 knock-out, 6 decapitation, 7 fire, 8 cold, 10 level drain (resist % pairing **[inf]**
from the records). Monster class bits for slay/protect: 0-13 the 14 classes, then 14
Giants, 15 Mythical, 16 Dragons, 17 Animals, 18 Beastfolk, 19 Undead, 20 Demons,
21 Insects, 22 Magical, 23 Mysterious (matched to the Compendium's categories, M_CATALG
§0 2-15, and to which monster records carry each bit **[record]**).

Hidden-power codes read from `equip_menu`: 0x10 the whole party to status 0 and full HP,
dead and ashes included; 0x17 Pie+1 then ashes; 0x20 Str+1 Agi+1 Luc+1; 0x22 Str−1 Agi+1;
0x23 Str+1 Luc−1; 0x24 Pie−1 age−1; 0x25 become Ninja; 0x26 become Lord; 0x27 Vit+1
age−1; 0x28 Vit−1 age+1; 0x29 Agi+1 Luc+1; 0x2a become Monk; 0x2c/0x2d the cold and fire
chain mails combining. **[code]**

String ids below are ITEM.DAT translation section 1: entry *k* is item *k* up to 24,
entry 24 also holds item 25 (after `{ff40}`), and item *i* ≥ 26 is entry *i*−1.

### Wrong or overstated claims (the original's)

All nine corrected in da781e2. Mythril Plate and Dragon Kite: breath is resisted through
the resist bits, not a breath field. `monster_breath` halves the damage and adds 5 to the
breath save when the member's resist bits match the breath's element or effect, so their
fire, cold, poison and paralysis bits do help; the claim "neutralizes all kinds" is still
too strong. **[code]**

| §1 # | Item | Japanese claim | Our English | Record | Mark |
|---|---|---|---|---|---|
| 46 | Winter Wand (47) | 「マダルト」の呪文が封じ込めてある | "holding the cold spell Madalto" | battle spell is **Ladalto** | [record] |
| 69 | Rod of Raising (70) | 武器としての威力はほとんど無い | "Nearly useless as a weapon" | 3d8 (3-24), to-hit +3, two-handed | [record] |
| 107 | Wand of Mystery (108) | ワンド自身には攻撃力のない | "The wand itself has no attack power" | 1d7+2 (3-9), to-hit +1, +2 swings | [record] |
| 275 | Gem of Exorcism (276) | 不死系からの攻撃を受けなくなり | "you can't be hit by undead attacks" | protect mask Undead: their hits are **halved** (D-battle "Bonuses") | [record] [code] |
| 301 | PK Crystal (302) | 剣や魔法の攻撃を無効化してしまう程 | "strong enough to nullify sword and magic attacks" | magic resist 20% each school, sleep/confusion 20%, regen +3; nothing against weapons | [record] |
| 225 | Mythril Plate (226) | 様々なブレスを中和する | "neutralizes all kinds of breath" | fire, cold, poison, paralysis 10% each; no breath field | [record] |
| 228 | Dragon Kite (229) | 魔法やブレスの攻撃を尽く封じる | "block all magic and breath attacks" | magic resist 10% each, fire/cold/poison 15% | [record] |
| 59 | Worst Sword (60) | 攻撃回数も減少し | "cuts your attacks" | no swing penalty (extra swings 0). Cursed, to-hit −3, AC +3 are right | [record] |
| 35 | Axe of Woe (36) | 攻撃回数も減ってしまう | "so you lose attacks" | no swing penalty | [record] |

"Our English" in the Mythril Plate row turns 様々な ("various") into "all kinds of", which
is close enough; the overstatement (中和 "neutralizes") is the original's.

### Cursed, and the description doesn't say so (the original's)

Not changed: adding a warning may give away what the developers hid on purpose. For Chris.

Queen's Whip (67, §1 #66, also female only), Soul Bow (87, #86), Ring of Skulls (263,
#262), Cloak of Capricorn (268, #267; reads like a good item: "various special
protections"), Trollkin Ring (290, #289), Sword of Swishes (15, #15; described as junk, but
not as cursed). All have bit 7 of +5 set. **[record]**

### Notable restrictions the description leaves out (the original's)

Not changed, for the same reason. Also unmentioned: the Worst Sword's hidden power (Vit−1,
a year older), the Dragon Kite's (Str+1), and the PK Crystal's IQ+1 and +3 regeneration.
**[record]**

| Item | Record | Mark |
|---|---|---|
| Holy Crown (231, #230) | Human only; classes Fighter, Priest, Lord, Valkyrie, Bishop. The text said "clergy and any fighter type"; corrected 2026-10-12 to name the classes | [record] |
| Perfection Dougi (233, #232) | Monk, Dwarf only | [record] |
| Armor of Master (237, #236) | Samurai; Human and Mook only | [record] |
| Bloodsucker (124, #123) | Thief and Bard; Hobbit only | [record] |
| Ninja Garb (239, #238), Shuriken (121, #120) | Evil only (Ninja) | [record] |
| Dragon Slayer (96, #95) | every race but Dracon | [record] |
| Scratch Hand (306, #305) | every class but Psionic | [record] |
| Rod of Raising (70, #69) | every race but Faerie | [record] |

### Confirmed (a sample of what matches)

- The Lute (242, #241, "Only a Bard can play it") and Harp of Silence (269, #268): BATTLE
  `FUN_800a29b4` lists an item for use in battle only if its category isn't 6
  (instrument) or the user's class is 8 (Bard). **[code]**
- Long Bow is the only bow a Fighter can use; Robinsword the only main-hand sword a Thief
  can use; the Sling the only stone weapon. **[record]**
- Champion's Ring adds 10% to each hit-effect chance (5% to decapitation). **[record]**
- Ankh of Wonder (0x10) restores the whole party, ashes included; Fire Whip gives Pie+1
  and then turns the user to ash. **[code]**
- Hidden powers: Excalibur becomes Lord (not mentioned in its text), Devil Slayer Monk,
  Thieves Dagger Ninja, Robe of Pope Bishop, Silver Hammer Str+1 Luc−1, Robinsword Str−1
  Agi+1, Sankouken Vit+1 age−1. **[code]**
- Most slay, protect, resist, alignment and break claims match their records; the Blow
  Gun, Nunchaka and the other hit-effect weapons have the effects they claim. **[record]**

### Not verified

Wizard's Cone "raises magic power", Faerie Cap's speed, Amulet of Evil keeping alignment,
Ring of Solitude blocking other rings, Winged Boots' fall damage. None of these has a field
in the item record; they would need the code that reads the item id. **[inf]**

## Our mistranslations (clear fixes to approve)

All three render 力 ("power", attack power) as the Strength stat on weapons whose records
don't touch Strength while equipped. 力そのもの in the Mace of Power's last sentence is
the stat (its hidden power is Str+1), so that one stays.

| §1 # | Item | Japanese | Our English | Record | Suggested |
|---|---|---|---|---|---|
| 61 | Skull Dagger (62) | 力が上昇し,命中精度も向上 | "Raises strength and accuracy" | to-hit +2, 2d5, +2 swings; no stat change | "Raises power and accuracy" |
| 89 | Mace of Power (90) | 装備するだけで力が上昇し,命中精度も上がる | "raises Strength and accuracy just by equipping it" | to-hit +5, 2d7, +2 swings; Str+1 only through the hidden power | "raises its power and accuracy just by equipping it" (the second sentence, "raises Strength for good", is right) |
| 118 | Golden Axe (119) | 力も増幅され,敵に攻撃が当たる確率も増加 | "Strength and accuracy rise too" | to-hit +8, 5d4+5, +2 swings; hidden power Vit+1 age+1, no Str | "Its power and accuracy rise too" |

Wording is a suggestion only; Chris decides.

**Fixed in 8ace280** with Chris's wording: the Skull Dagger "It hits harder and truer",
the Mace of Power "adds power and accuracy ... raises Strength itself", the Golden Axe
"It also hits harder and truer".

## Compendium (M_CATALG)

The descriptions are sections 4-17 of M_CATALG.DAT, one per category in the order of §0
2-15 (Giants ... Priests). The game's mapping from entry to monster id wasn't traced, so
each description was matched to its monster by content (names, looks, the category) and
the match is **[inf]**; the record fields are **[record]**, read with
`desccheck.py monsters`, which loads every group record at the end of each
DATA02/M_DTnnn.BIN and MPTnn.BIN, not only the last one.

Breath byte (+0xc9): 0x20 fire (Fire Giant, Fire Golem, Garm, Heated Dog, Gold Dragon),
0x40 cold (Frost Giant, Ice Rock, Flack), 0x80 an unnamed element (Shadow Golem, Mictlan,
Sidelle, Maelific, Ahalmez); low bits 0x01 sleep, 0x02 poison, 0x04 stone, 0x08
confusion, 0x10 paralysis. **[record]**, element names **[inf]**

### Wrong or unsupported (the original's)

| Entry | Monster | Japanese claim | Our English | Record | Mark |
|---|---|---|---|---|---|
| 7.16 | 2-Head Snake (154) | ドレイン能力も持っているのだ | "Worse still, it can drain levels." | drain 0 (+0x80); its only effect is poison 50%. **Corrected in a25c54c** (the sentence is dropped) | [record]; match [emu]: the entry shows under the 2-Head Snake in the Compendium |
| 10.0 | Smoke Demon (13) | 剣で攻撃してもなかなかダメージを与えられない | "swords barely harm it" | no physical-damage reduction in the record (AC 4); nothing in D's melee code for it | [inf] |
| 12.3 | Venus Man Trap (36) | 炎系の呪文で燃やしてしまうのが一番 | "it burns well with fire spells" | no fire weakness (+0xce empty); the smaller plants (Pink Mushroom, Xicalli) do have it | [record], match [inf] |

### Confirmed

Poison Giant poison breath; Frost Giant cold breath; Fire Golem fire breath and magic
resist 60/100/60/60; Halycon decapitation 10%; Basilisk stone 35%; Stone Head and
Dragonare stone breath (Dragonare has no spells, as said); Medusa stone 75% and poison
breath; the flying "ancient demon" (Death Hawk) has Priest and Alchemist spells;
Quetzalcoatl casts and has stone breath; Wyvern, Twin Dragon, Gold Dragon fire breath;
Green Dragon poison breath; Greater Raptor decapitation 30% and poison 75%; Garm and Heated
Dog fire breath; Wing Lizard poison breath; Giant Slug regenerates; Alligator, Mad Monkey,
Lesser Demon and Blob call for help; Magical Rabbit's staff (sleep, paralysis, knock-out,
poison, confusion); Giant Spider has no poison; Giant Scorpion poison; Cool casts Mage
spells and is weak to fire; Were Jaguar paralysis 30%; Yuan-Ti reaches the back row;
Flack's many effects; Smelia casts Alchemist spells; Zombie poison and paralysis; Shade,
Vampire Lord, Phantasm, Mictlan and Dragon Liche drain; Dragon Liche poison breath and
spells; Boots Zombie paralysis; Beast's companion is Beauty (60%); Fire Rock weak to cold;
Ugo knock-out 50%, regenerates, resists spells; Greater Demon resists 80% of every school;
Arch Demon casts Mage and Priest spells, petrifies and decapitates; Marchosias petrifies;
Demon Baby sleep breath; Tamazul and Fog Beast sleep breath and regeneration; Greater Blob
petrifies; Ice Rock cold breath; Gas Cloud sleep breath and spells; Evil Eye paralysis and
confusion; Ogre Brother (Monk) Psionic spells; Kobold King (Lord) Priest spells; Gremlin
Mother and Old Drumer Mage spells; Goblin Oracle Psionic; 3-Head Gremlin (Bishop) Mage and
Priest; Kel casts from all four schools ("learned every spell"). **[record]**, matches
**[inf]** where the description doesn't name the monster.

Not mapped with confidence: 8.10 (hard-skinned humanoid), 9.13, 9.17, 9.20, 10.15 (its
"instant death" fits no demon with poison and paralysis but no decapitation; Chamiaholom
is the likeliest, and has none).

## Help text (SISETU)

| SISETU | Claim | Check | Mark |
|---|---|---|---|
| 184-194 | race strengths (Elf IQ/Pie, Gnome the highest Piety, Faerie the highest IQ, Hobbit luck, Lizardman no IQ/Pie, Rawulf Pie/Vit, Mook Str/Vit/IQ, Felpurr IQ/Agi) | all match `race_base_stats` (G-records.md) | [record] |
| 185-194 | race resistances (Elf sleep, Dwarf poison, Hobbit and Dracon specials, Rawulf/Mook/Felpurr cold) | where the race resistances are set wasn't found | not verified |
| 191 | Dracon the only race that breathes | `party_breath` exists; the race test wasn't read | [inf] |
| 195/196 | a man's Strength +1, a woman's Vitality +1 | F-edge-save.md, character creation | [code] |
| 205 | Lord can Dispel from level 9 | D-battle.md: class 5 from level 9 | [code] |
| 206 | Valkyrie women only | F-edge-save.md and G-records.md (bit 7) | [code] |
| 211 | Bishop can Dispel | D-battle.md: class 0xb from level 4 (the text gives no level) | [code] |
| 217 | Vitality sways the odds of coming back from death | E-town.md, the temple: 60 + 2 × VIT and 68 + 2 × VIT | [code] |

The inn and temple text was already checked in E-town.md.

## Sweep (2026-10-11)

Chris asked for a check of other places that state a number or a rule. What was read,
against the chapters and the decomp:

**Spells not checked before**
- Banoka (STATUS 473, "may bounce enemy spells back"): right. In `cast_spell`, while the
  party's Banoka counter (0x80079bc0, 3 rounds) runs, a monster's hostile spell turns on
  its own group 34% of the time; a monster's Banoka (0x80079b6b) turns a party member's
  hostile spell on the caster 30% of the time. One bounce uses the counter up. **[code]**
  D-battle.md read these counters as melee; corrected there.
- Calfo (444, "nearly always spots chest traps"): right. It names the trap 95% of the
  time, otherwise one of the 13 at random (`FUN_800c697c`). **[code]**
- Calnova (481, "can fail"): right for chests. It disarms 85% of the time; otherwise 90%
  nothing happens and 10% the trap goes off, 1.5% in all (`FUN_800c6d50`). **[code]** Doors
  weren't read.
- Mahaman (439, "special effects, but lose a level"): right. Under level 13 it fails; at 13
  or more it offers three of seven wishes (a second set in five special encounters) and
  the caster loses a level (`spell_mahaman`). **[code]**
- Quremor (493, "party's attack spells grow stronger"): right. Each cast adds 4 to the
  caster's side's spell damage bonus, up to 12 (`spell_quremor`). **[code]**
- **Bacortu (434), corrected in d798054.** "Walls enemies off from casting" was too
  strong. Each cast adds the caster's level to the target group's sealing level (up to
  255, `spell_bacortu`), and a sealed group's spell is lost only when rand(8191) / (its
  caster's level + sealing + 1) is below the sealing level (`cast_spell`). One cast by a
  level-15 caster stops a level-10 monster's spell about 5% of the time; it takes several
  casts to seal a group reliably. New wording: "Ward: enemy spells may be sealed; stacks".
  **[code]**
- The rest of the buffs, cures and AC spells match: Sogref 2 one ally, Porfic 4 the
  caster, Bamatu 3 and Maporfic 2 (1250 steps) the party, Ponti AC 1 (plus 1, up to 10, on the action record's first byte, read as attacks **[inf]**),
  Poba ±1, Mapoba ±2, Dilto −2, Morlis −4; Nagula is the caster's current HP halved, then
  quartered on the next cast, and so on; Madi cures all but death and ash, Morfis all but
  death and stone, Kadios and Madi to full HP, Labadi leaves 1-8 HP, Loktofeit empties
  every pack. **[code]**
- Cloud elements: Fire Mist and Flame Mist are fire (0x80), Ice Mist cold (0x100), Glow,
  Ray and Low Mist 0x4000. No cloud description names a wrong element; Madalqua's ("Low
  Mist: 4-60 damage to a group") names none. Its battle lines, FIGHTMSG 179/185 "in
  freezing cold", do say cold though its element isn't; that's narration and stays, for
  Chris. **[code]**

**Items**
- Breath and resist bits: see "Wrong or overstated claims".

**Town and system text** (E-town.md had checked the inn, temple and Boltac's text; all
true)
- SISETU 322, the ending: "Accept this title and 1,000,000 Gp." `king_ending` adds
  1,000,000 to the first party member's gold (capped at 0x7fffffff). The text doesn't
  say "each", so it fits. **[code]**
- SISETU 326: 10000 Gp each, right (E-town.md).
- SISETU 492, the Training Maze sign: "no gold or items dropped" is right (no chests
  there), and "sent to the temple free of charge" is right (the members go back to town,
  where the Temple lists them). But a wipe there still halves everyone's gold and rolls
  the front member's items six times (D-battle.md). The sign doesn't say otherwise; left
  as it is, for Chris. **[code]**
- SISETU 65/66, "has died of old age": the character is Lost and deleted, not dead
  (E-town.md). Left, for Chris.
- SISETU 218, Agility: the order of attacks, spotting traps (Inspect's chance is a class
  factor × Agility, up to 95%) and disarming (a failed disarm sets the trap off unless
  rand(20) + a class penalty ≤ Agility): right. **[code]**
- **SISETU 219, Luck: "like disarming traps and dodging enemy attacks".** Not what the
  code does: chest disarming uses class, level, the area's danger and Agility, and a
  monster's to-hit has no Luck term. Luck goes into the saving throws (level / 5 + Luck /
  6), which soften traps and breath. Help text, but the original's own claim and loosely
  worded ("sways many things"); not changed, for Chris. **[code]**
- SISETU 214-217 and the class lines 200-213 match (the spell schools agree with
  `spell_point_rules`). **[code]**

**Compendium, the two unsupported claims**
- Smoke Demon (10.0, "swords barely harm it"): no field or code found that cuts weapon
  damage. **[inf]** Left, for Chris.
- Venus Man Trap (12.3, "burns well with fire spells"): no fire weakness, and it resists
  Mage spells 40%, so Mahalito and Lahalito do worse than usual; the Alchemist's fire
  clouds aren't resisted (Alchemist 0%). **[record]** Left, for Chris.

**Event text.** EVENTMES lines stating mechanics are few. 210/211 (the pillars' water
"seems to restore your magic") weren't traced; the wording hedges. 310 ("Obtained N
Gp") prints the amount given. **[inf]**

## Notes for other docs

- D-battle.md, "AC changes": Sogref targets one ally (STATUS 424 is right), not the caster.
- G-records.md, "Monster record": M_DT and MPT files hold one record per group at the end
  of the file (first group last), not only the last 0xd0 bytes; 17 monsters exist only as
  earlier groups (Medusa, Dullahan, the demon lords, Quetzalcoatl and others).
- D-battle.md lists 0x400000 as death-immune; it's also the Magical category bit (22), so
  every Magical monster is death-immune. **[record]**
