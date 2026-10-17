# Ninjas: decapitation, criticals, alignment (2026-10-17)

Read 2026-10-17 because Chris asked whether Ninjas get lots of critical hits and can behead,
as in earlier Wizardry games. Scripts, logs and tables are in `rips/re/work/ninja/`.
Labels: **[code]** decompiled C or disassembly (`mipsdis.py` there),
**[emu]** emulator on the JP Rev 1 disc, **[record]** data on the disc, **[inf]** inferred.
Addresses are BATTLE unless marked. The emulator Ninja runs set the test character up by
writing RAM (roster 0 made class 12, weapon unequipped, HP restored between fights); the
$s3 probe used button presses only.

## Short answers

- **No separate critical hit.** The Ninja's "critical" (SISETU 212, "Critical hits and
  thieving skills") is the decapitation hit effect, bit 0x40. Party melee has no other
  instant-kill or crit path: damage dice, ×2 slaying, + rand(damage) on helpless or ambushed
  targets, then the hit effects. [code] 0x800a963c
- **Bare-handed Ninja: 20% decapitation, flat.** Level doesn't scale it. With weapons the
  20% goes away and only the gear's chances count.
- **The class's own 11% is dead code** (a register bug, below). The Monk's 11% knock-out too.
- **Ninja is Evil-only at creation and class change, but a Thief who uses the THIEVES
  DAGGER becomes a Ninja and keeps his alignment**, so a Neutral Ninja is possible. [code]
- **Good and Evil can't share a party; Neutral mixes with either.** [code]

## 1. What fills the derived block

`battle_derive_stats` 0x800a1830 rebuilds +0x7e..+0xbf in `new_char` (0x8008ff10) from
scratch, then copies it back. Callers: battle start (0x800a293c, via 0x800a5b0c from
battle_main) and **every status-panel redraw** (0x800d32dc ← 0x800d25cc, the panel's AC
readout), so it runs many times a second in battle. [code] [emu: 76-1000 calls a fight]

Order [code]:
1. `battle_derive_saves` 0x800a1b84 (saves).
2. To-hit 0x800a1edc: class term + Str term. Class term: Fighter, Lord, Valkyrie,
   **Ninja: level/2 + 1**; Samurai level/2 + 4; Ranger, **Monk** level/2 + 2; Priest
   level/3 + 1; Thief, Bard level/3; Mage, Alchemist, Psionic, Bishop level/4. Str 16+:
   + (Str - 15); Str 6-15: + 0; Str ≤5: + (Str - 6), floor 0.
3. Dice: both hands 2d2, bonus Str - 13 if Str ≥ 14.
4. Swings 0x800a1ff8 → 0x800a2ba4(div, base, cap 10): swings[0] = min(level/div + base, 10),
   swings[1] = min(that/3, cap). Fighter/Lord/Valkyrie/Ranger level/5 + 1 (cap 10);
   **Samurai, Ninja, Monk level/5 + 2 (cap 10)**: L10 4, L20 6, L30 8; Mage, Bishop,
   Alchemist, Psionic level/12 + 1 (cap 2); Priest, Bard level/12 + 2 (cap 3); Thief
   level/8 + 1 (cap 3). party_melee then adds the combatant's +0x8 (Ponti) and caps at 10.
5. Regen, magic resist, reach (1), protect/slay masks, resists +0xb0..+0xbd and chances
   +0x8d..+0x93 zeroed. Race resists 0x800a20dc (Faerie +25 decap resistance, etc.).
6. **Class hit effect, 0x800a197c:** `if (s3 == 12) +0x8c = 0x40, +0x93 = 11; else if
   (s3 == 13) +0x8c = 0x20, +0x92 = 11`. **$s3 is never loaded in this function**; it's the
   caller's register (saved in the prologue at 0x800a1874, used at 0x800a197c). [code]
   - Battle start: s3 = 2 (battle_main's caller; likely the game mode, 2 = battle [inf]).
   - Panel redraw: s3 = a screen Y coordinate (0x3c + 0x1a·k or 0xb8 + 8·k in 0x800d25cc),
     seen as 0xc0 and 0xda. Neither can be 12 or 13. [code]
   - [emu] `ninja_test.py`, four seeds, 2,700+ calls with a Ninja in the party: s3 was only
     2, 0xc0 and 0xda; the Ninja's +0x93 read 20 (the bare-hand 20 alone, no 11).
   So the Ninja's intended 11% decapitation and the Monk's 11% knock-out never apply.
   Original-game bug; a fix is balance-changing (ask first; candidate for bugs.md).
7. AC (also JOUKA `town_stat_recompute` 0x800d0574): base 10 (Faerie 5); **Ninja and Monk:
   minus level/3 if anything at all is equipped, minus level/2 if nothing is**; clamp ±99.
   Then gear. [code]
8. Gear 0x800a22b0 → 0x800a2450 per equipped item (any category, not only weapons). The
   item is copied to 0x80096740 (= item record - 2). From the item record [code]:
   - +0x05 specials & 0x7f → OR'd into **+0x8c hit effects**; +0x06..+0x0c → added to
     **+0x8d..+0x93 chances** (cap 100). So G's "specials = special powers" are the hit
     effect bits, and the "7 bytes of 0/5/10/15" are their chances.
   - +0x22 protect, +0x26 resist bits, +0x28..+0x35 resists, +0x35 AC, +0x36 to-hit
     (**+0x84**), +0x37..+0x39 dice, +0x3a swings (main: max(class, weapon); sub:
     max(class sub, (weapon+1)/2)), +0x3e slay, +0x42..+0x45 magic resist, +0x46 reach.
   - 0x800a2c48 alignment/sex check: an item whose G/N/E bits leave out the wearer (or
     with none set), or the wrong sex, gives **nothing** but -1 to-hit, +1 AC, reach, and
     gets the cursed bit (copied back to the roster). [code]
9. **Bare hands**, 0x800a2880, when no equipped item is in either hand (0x1000/0x800) and
   class & 0xf is 12 or 13: reach 4 from level 9 (every group, either row), damage bonus +
   min(level/4 + 4, 10) on both hands, **Ninja: +0x8c |= 0x40, +0x93 += 20; Monk: +0x8c |=
   0x20, +0x92 += 20.** [code] [emu: L5 Ninja Str 22 read +0x93 20, swings 3/1, dice 2d2+14,
   to-hit 10 — all as computed]

## 2. How a hit effect lands

`melee_apply_hits` 0x800a963c, once per **hand** (not per swing), only if that hand did
damage > 0 and the target wasn't already dead, rolls `apply_status_effects` 0x800aa190 with
the character's whole +0x8c and +0x8d..+0x93 (so every hand gets the summed chances).
Decapitation is rolled first: rand(100) > resist and rand(100) < chance → status 0x80,
HP 0, FIGHTMSG 158 "{monster} is decapitated!" (136 for a party member); experience and
the kill count as a normal kill. [code]

- The level-difference bonus (+1 per 4 levels, cap 30) is computed and passed in $a2/$a3,
  and never read. **Level doesn't scale the chance.** [code] (already in D-battle bugs)
- **Monster resistance bytes are never initialised.** For a monster target, the stack
  bytes sp+0x18..0x1e are set to 100 only for the monster's +0xcc bits (and +0x1e for
  +0xa8 0x1000000); the rest keep whatever was on the stack (0x800aa2cc-0x800aa358). [code]
  In play the decap byte read 0 every time the monster lacked the immunity (16 reads) and
  100 every time it had it (9 reads, monsters 1 and 5, +0xcc 0x249 and 0x78). [emu]
  So the effective resistance is 0 in practice, but by luck: a fix would zero them.
  `stack_watch.py`: the stale bytes were last written by register saves in an earlier
  `melee_apply_hits` frame (0x800a9640/0x800a9684). [emu]
- Chance against a non-immune monster = chance% × 99%. Seen: 4 of 17 decap rolls passed
  at 20% (rand 6, 17, 16, 5). [emu]

## 3. Real odds per round

`odds.py` / `odds.txt` (Str 18, group 1, no Ponti). Per swing hit: rand(20) ≥ T, T = 20 -
AC - to-hit, held to 19, min 1. Oslo/Maoslo (party, 0x8007e830 = 2): T - 2, and if that's
15+, 3 more off — so T 19 becomes 14 (5% → 30%). [code]

| Ninja | swings | to-hit | bare hands vs AC 0 / -10 / -50 | with Oslo vs -50 |
|---|---|---|---|---|
| L10 | 4 | 9 | 18% / 4% / 4% | 15% |
| L20 | 6 | 14 | 20% / 15% / 5% | 18% |
| L30 | 8 | 19 | 20% / 20% / 7% | 19% |

Ceiling is 19.8% a round bare-handed (one hand). NINJA-TO main + SHURIKEN sub (30% each
hand, +8 to-hit): ~50% a round against AC 0 to -10, 8-13% against AC -50, 34-39% with Oslo.
Late monsters (Dragon's Cave AC -40 to -98) need Oslo/Maoslo; with it a Ninja takes
800-1,800 HP monsters out in one roll.

### Items with decapitation [record] (all Ninja-usable ones marked *)

`effect_items.txt` has every item with hit effects. Decap ones:

| Item | Decap | Other | Classes | Notes |
|---|---|---|---|---|
| *NINJA-TO (22) | 15 | | Nin | sub-capable, Boltac stock 1 |
| *BO SHURIKEN (31) | 5 | | Nin | reach 4 |
| *SAI (37) | 5 | | Nin | |
| *SHIHOU SHURIKEN (64) | 5 | sleep 5 | Nin | reach 4 |
| *MANJI SHURIKEN (93) | 5 | | Nin | reach 4 |
| *SANKOUKEN (115) | 10 | stone 10 | Nin | reach 4, to-hit +8 |
| *SHURIKEN (121) | 15 | paralyze 15 | Nin | **Evil only**, to-hit +7, reach 4 |
| *ANGEL STICK (116) | 5 | stone 5 | all | sub-capable |
| *TROLLKIN RING (290) | 5 | | all | ring, **cursed**; works bare-handed (+20 → 25) |
| THIEVES DAGGER (68) | 5 | poison 15 | Thi | N/E; using it makes a Ninja |
| KABUTOWARI (42) | 5 | KO 10 | Sam | |
| EXECUTIONER (74) | 10 | | Sam | |
| KUNIMITSU (100) | 5 | | Sam | |
| OODENTA (120) | 15 | | Sam | |
| MURAMASA BLADE! (129) | 25 | | Sam | best in game |
| ARMOR OF MASTER (237) | 5 | | Sam | armor |
| ZATOICHI BO (114) | 15 | para 15, KO 15 | Sam Mon | |
| DEVIL SLAYER (123) | 10 | | Fig Sam Mon | |
| 8-TARO BOW (126) | 20 | | Sam Ran Mon | |
| FAUST HALBERD (82) | 10 | para 10 | Fig Lor Val | |
| SCYTHE OF DEATH (117) | 10 | | Fig Lor Val | cursed |
| EXCALIBUR (127) | 15 | stone 15 | Fig Lor Val | |
| HOLY LANCE (125) | 20 | | Val | Neutral only |

Dual wield [code, JOUKA equip_menu 0x800ccc94]: any weapon in the main hand, and a second
weapon whose flags04 has 0x80 in the sub hand. All Ninja weapons above are sub-capable.

## 4. Who is immune [record]

Immune = monster +0xcc bit 0x40 or +0xa8 bit 0x1000000. Full list in `mon_decap.txt`
(`mon_decap.py`, every record in M_DT/MPT/NPT files). Magical (0x400000) is death-immune
but **not** decap-immune.

- **Control room (NPT15, fixed fight source 4, id 0xf):** Cleo (L32, AC -32) IMMUNE (+cc),
  Arch Bishop IMMUNE (+a8), Arch Ninja IMMUNE (+cc). Bergamot (L24, AC -24), Arch Lord,
  Arch Fighter: **not immune**.
- **Quetzalcoatl** (M_DT169 g2, L30, AC -30, 30d7+750): IMMUNE (+a8).
- **Diamond Knight** (L225, AC -100) and **Diamond Drake** (L255, AC -120), MPT08: IMMUNE both ways.
- **Area E** (maps 36-38) random groups: immune are Ispusteke, Mictlan, Stone Golem, the
  Blobs, Were Amoeba, Evil Eye. Not immune: Greater Demon, Vampire Lord, Elizabeth, Ugo,
  Flack, Raver Lord, Doom, the Giants, Astro Zombie, Hell Master, Lesser Demon, Incubus,
  Chamiabac, Beauty, Beast, Fire Guardian, Stone Head. Area E human parties (MPT07/14/27/33):
  Kel, Blade Master, Tepeyo ryotl, Ogre Daimyo immune; all the goblin, orc and other ogre
  casters are not.
- **Dragon's Cave** (maps 40-42): not immune: Medusa, Chamiaholom, Gigatops, Wyvern, Green
  Dragon, Greater Raptor, Allo Saurus, Gold Dragon, Dragonare, Twin Dragon, Tyrannosaurus,
  Ahalpuh, Ahalmez (and their escorts). Immune: Dullahan, Sidelle, Dragon Liche, Deadly
  Angel, and the demon lords Agares, Bael, Arch Demon, Death Hawk, Marchosias, Maelific,
  Demon Lord, Demon Liche, Hims.

## 5. Other Ninja traits

- **Hide** 0x800a8980 (-8): Thief, Ranger, Bard, Ninja, Monk alike, no class bonus. The
  first roll (rand(100) ≤ level/2 + 15) only runs when `hidden` (0x8007974c) is -1, and
  nothing in the C writes -1 (battle start writes 0, hiding 1) [code; the "no writer" part
  is a search of the decompiled C], so hiding is just rand(level + 9) ≥ 7: L10 63%, L20 76%,
  L30 82%. (D-battle.md describes the first roll as live.)
- **Ambush** (-7): T - 4, damage + rand(damage). Per hand, rand(16383) mod (2 × monster
  level + Ninja level) > 1.25 × Ninja level → spotted, attack lost (FIGHTMSG 124). L20 Ninja
  vs L15 monster ~48% spotted; vs a L100+ demon ~90%. Monsters skip a hidden member 70%. [code]
- **AC** above: 10 - level/3 (geared) or level/2 (naked), Faerie 5 - ...
- **Chests and locks** (lock-test.md, already measured): Inspect Agility × 5 (Thief × 6),
  cap 95 — a Ninja with Agi 19 matches a Thief's cap. Disarm 80 + level - danger, same as a
  Thief; failure sets it off on rand(20) > Agility. Lock pick: same +5 as a Thief.
- **Alchemist spells** (spell_slot_table, start 6 step 3): spell level 1 at L7, 2 at L10,
  3 at L13, 4 at L16, 5 at L19, 6 at L22, 7 at L25; learning roll (IQ+Luc)/2 out of 30.
  Late-game useful: **Oslo (L1)/Maoslo (L3)**, the to-hit fix for high AC above; **Ponti
  (L1)**, +1 swing (combatant +0x8, stacks to 10) and +1 AC modifier on one ally
  (0x800aeaf8); Katiqurea sleep (helpless targets take + rand(damage)); Morfis, Kadios
  heals; Calnova (L7) for locks and chests. The damage mists fall off late.

## 6. Alignment

- `class_alignment` 0x8005e280 [record]: Good-only Lord; Evil-only Ninja; Neutral-only
  Valkyrie; Good or Evil Priest, Bishop; Neutral or Evil Thief, Ranger, Psionic; Good or
  Neutral Samurai, Bard, Monk; any Fighter, Mage, Alchemist. Checked at creation
  (0x800af5d8), class change (0x800b4934), training menu (0x800ae0c0).
- **Party mixing** `tavern_add_member` JOUKA 0x800a846c, lines ~245-275 [code]: from the
  party's stored alignment bytes (party +0x0e, written at join: 0/0x40/0x80): Good refused
  if there's an Evil member, Evil refused if there's a Good one, Neutral refused only if
  both are already there; refusal is SISETU 9 "Their alignments won't mix."
- **THIEVES DAGGER** (68, Thief-only, N/E) item effect 0x25 (JOUKA 0x800ccc94 line ~644):
  class bits to 12, unequip all but cursed; **no alignment change, no level reset, no stat
  check**. A Neutral Thief becomes a Neutral Ninja, who can join a Good party. [code] (ROBE
  OF POPE, effect 0x1e, makes a Bishop the same way.)
- **Alignment does change in play:**
  - Friendly monsters (FIGHTMSG 263, "Fight"/"Leave"), 0x800a6804 [code]: **Fight** → each
    standing Good member 7% turns Evil (FIGHTMSG 265); **Leave** → each standing Evil member
    5% turns Good (266), unless wearing the AMULET OF EVIL (301). Neutral never changes. The
    class isn't touched, so an Evil Ninja who turns Good stays a Ninja [code], but his
    Evil-only gear (SHURIKEN) then fails the battle alignment check, gives nothing, and gets
    cursed (0x800a2c48 / 0x800a2450) [code].
  - The friendly roll (battle_setup_groups 0x800a60fc ~line 115) uses the party's stored
    byte & 0x40: it's rolled for the first member who isn't **Neutral**, so an all-Neutral
    party never meets friendly monsters. (D-battle.md guessed 0x40 = Evil; the tavern code
    shows 0x40 is Neutral.) [code]
  - Ihalon in camp: "Turn Good/Neutral/Evil" (MAZE 0x800d0514 ~line 905; B-camp.md). [code]
  - The party's stored alignment byte isn't rewritten by 0x800a6804, so a member who flips
    stays in a now-mixed party until it's re-formed [inf, not tested].

## Files

- `mipsdis.py` capstone disassembler (MODULE START END); `*.dis` the listings read.
- `s3_probe.py`, `s3_jp/` — s3 at the class test, premade party (button presses only).
- `ninja_test.py`, `ninja_jp_s*/`, `ninja_jp_s*.log` — **test setup writes RAM**: roster 0
  (a Fighter) made class 12 and its weapon unequipped, HP restored between fights; the rest
  is button presses on the JP Rev 1 disc from P3-follow/jp/end.state.
- `stack_watch.py`, `stack_jp/` — the uninitialised resistance bytes.
- `decap_items.py`, `effect_items.txt`; `mon_decap.py`, `mon_decap.txt`; `odds.py`, `odds.txt`.
