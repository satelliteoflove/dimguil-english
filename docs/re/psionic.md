# Psionic confusion (Sios, Lios, Masios, Lasios)

Read 2026-10-17 for the chapter 19 golem bench (rips/harness/ch19/golembench/STATUS.md,
Report 4). Decompiled C in `rips/re/decomp/BATTLE/` (and JOUKA for spell points). Every
line here is **[code]** unless it says otherwise; the bench numbers are **[emu]**.

## The handlers

| Spell | Id | Level | Handler | Call | Targets |
|---|---|---|---|---|---|
| Sios | 63 | 1 | `spell_sios` 0x800ca5d0 | `psionic_damage(2, 2, 65, 0)` | one monster (also hits a dead one's slot) |
| Lios | 66 | 2 | `spell_lios` 0x800af924 | `psionic_damage(2, 2, 65, 1)` per member | a group (fixed battles: `spell_group_range`), standing members |
| Masios | 72 | 4 | `spell_masios` 0x800aff00 | `psionic_damage(8, 2, 60, 1)` per member | a group, as Lios |
| Lasios | 82 | 7 | `spell_lasios` 0x800b06f8 | `psionic_damage(8, 9, 60, 1)` per member | every monster group 1-6 |

The arguments are dice count, dice sides, confusion chance p, and "skip a dead target".
Against one lone monster (the golems) the four differ only in damage (2d2, 2d2, 8d2, 8d9)
and p.

## The landing roll

`psionic_damage` 0x800b34b0 for each target:

1. **Damage**, through `spell_damage_one` 0x800b0b50 and `spell_damage_core` 0x800b0c6c:
   resisted on rand(100) < r - (r/5) × min(N, 4) + 1, r = the target's resistance to the
   caster's school (spell id / 21 = 3, Psionic: monster record +0xa6, party +0x8a) + the
   target group's magic screen (0x8008c487 + group × 8). N is the monsters' Nofis count
   0x80079932 (`spell_damage_one` caps it at 4 for its call). If resisted ("nullifies the
   spell"), nothing more happens: no confusion roll.
2. If the target still has status below 8 (alive, awake, not paralyzed or stoned):
   p is halved (integer, 65 → 32, 60 → 30) if the target resists confusion (resist bits
   +0xcc bit 8 for a monster, +0xae for a member), else set to 80 if it's weak to it
   (+0xce bit 8). Then `status_spell(8, 100 - p, member)` 0x800b173c.
3. `status_spell` rolls the **same school resistance again**, this time with the full
   Nofis count: resisted on rand(100) < r - (r/5) × N + 1 (no message: `psionic_damage`
   sets 0x80079820 = 1, which mutes it).
4. Then the save: clamped to 5..100, saved on rand(100) < 100 - p. There's no level term
   anywhere: not the caster's, not the target's (the "+4 a level above the caster" in
   D-battle.md is `status_spell_targets` 0x800b1524's, which the psionic spells don't go
   through). 0x8007977c, which skips the rolls, is only set by Matokani.
5. Kind 8: if the target is already confused, nothing; else status |= 2 (a party member's
   counter +0x79 = 127), message "X is confused." (word | 0x2000).

**Settled:** both things the notes said are true and don't conflict. There's no immunity:
resisting confusion (+0xcc bit 8) halves p, it never blocks. The "Psionic resistance at
+0xa6" is the monster record's fourth school resistance, and it's rolled twice (steps 1 and
3). So one cast lands with

  P = (1 - r₁/100) × (1 - r₂/100) × p'/100

with r₁ (Nofis capped at 4) and r₂ (Nofis in full) from step 1 and 3, p' = p/2 for a resister.

### Against the chain's monsters

Records (M_DT150/151/169.BIN, and the Fire Golem's read in RAM at its fight, start_v6b_150):

| Monster | Level | School resistance (Mage, Priest, Alch, Psionic) | Resists confusion | Screen |
|---|---|---|---|---|
| Fire Golem | 60 | 60, 100, 60, 60 | yes (+0xcc 0x42ff) | 0 |
| Shadow Golem | 70 | 70, 50, 70, 50 | yes (0x427f) | 0 |
| Quetzalcoatl | 17 | 80, 95, 60, 60 | yes (0x571f) | 0 |

Chance a cast confuses, by the party's Nofis casts N (the golems cast none):

| N | Fire Golem, Lios/Sios | Masios/Lasios | Shadow Golem, Lios/Sios | Masios/Lasios |
|---|---|---|---|---|
| 0 | 4.9% | 4.6% | 7.7% | 7.2% |
| 1 | 8.3% | 7.8% | 11.1% | 10.4% |
| 2 | 12.7% | 11.9% | 15.2% | 14.3% |
| 3 | 18.0% | 16.9% | 20.0% | 18.7% |
| 4 | 24.2% | 22.7% | 25.3% | 23.8% |
| 5 | 27.6% | 25.8% | 28.2% | 26.4% |

(Quetzalcoatl is the Fire Golem's row.) Without Nofis that's a mean of 20.5 casts to
confuse the Fire Golem (39% within 10 casts, 55% within 16) and 13 for the Shadow Golem (55%
within 10). Lios and Sios beat Masios and Lasios against a lone resister (p 32 against 30);
Lasios only adds damage (8d9) that the same first roll mostly voids.

**Caster level doesn't enter the roll,** so a freshly built Psionic lands as often as a
level-40 one; level only buys spell points (below).

## How long it lasts and what clears it

- **Monsters: for the rest of the fight.** `monster_upkeep` 0x800a6aa0 rolls recovery for
  fear (bit 1), sleep and knock-out (0x18), paralysis (0x20) and stone (0x40), never
  bit 2. Nothing else clears a monster's bit 2: `spell_damage_core` cuts the confusion
  counter only for a party target (target_group 0, at 0x800b0c6c's +0x79 branch), and the
  only status writes that drop bits on a monster are Dialko (& 0xffc7), Latumofis (& 0xfffb),
  Madi and Morfis (status 0) — healing spells the golems don't have (their spell bytes
  +0x8f..+0xa2 are all 0xff). A new fight clears everything (`battle_clear_tables`
  0x800a5c44).
- **Party members** (for comparison): +0x79 starts at 127 and `party_upkeep` 0x800a73f4
  takes 10 a round (13 rounds); a hurting spell or breath cuts it by half plus one
  (0x800b0c6c); death clears it.
- Recasting on a confused monster wastes the point: `status_spell` kind 8 returns at once
  if bit 2 is set (after both rolls).

## What a confused golem does

`monster_ai` 0x800cffb0: for a confused monster, rand(100) ≤ 71 (72%) picks action -12
(0xf4) at a random group. In an ordinary fight (0x80079bde = 0, the golem fights) that's
any group, its own included, so with one group it's always itself. Otherwise (28%) it acts
normally, **breath included**. `battle_special_action` 0x800a8980 runs -12 as
`monster_melee` on a random standing member of that group: all its attacks, to-hit base 21
against its own AC (T = 21 - AC + mod - (level/2 + 1), held to 1..19: 19 for both golems,
5% a swing), + rand(damage) since the target can't act (status 2 or more).

AI rows (table 0x800d89e0, read in RAM): Fire Golem (row 150) 30% fight, 20% fight the
weakest, 50% breath; Shadow Golem (151) 20%, 20%, 60% breath. So confused, the Fire Golem
breathes on about 14% of its actions instead of 50%, the Shadow Golem 17% instead of 60%.
Party blows on a confused golem also get + rand(damage) (`party_melee` 0x800a8c2c).

Side note found on the way: `battle_special_action`'s Fight branch for a monster group
sends the blow at group 7 (summons) instead, with chance 1 in 4, whenever group 7 has a
member standing (0x8008c4bd > 0, rand(4) == 2, `monster_melee(7)`). So summons do draw some
melee; Report 2's "summons can't be hit" holds only for breath and for
`monster_target_random` itself.

## Spell points and spell levels

`spell_points_recalc` 0x800b9540 (JOUKA): each spell level starts at the number of its
spells known (three count as 4); then the class rule (Psionic: school 3, start 0, step 2,
`spell_point_rules` 0x800a133c) gives spell level j (1-7) max(that, L - 2(j - 1)) while
that's positive, capped at 9. Monks use the same school with start 6, step 3.

| Spell level | Confusion spell | First points at | 9 points from |
|---|---|---|---|
| 1 | Sios | L1 | L9 |
| 2 | Lios | L3 | L11 |
| 4 | Masios | L7 | L15 |
| 7 | Lasios | L13 | L21 |

A cast costs one point of its level (`cast_spell` 0x800abcc0), shared with the level's other
spells: Sios with Diomas and Poba, Lios with Diafic and Calko (neither castable in battle,
so Lios's 9 are free), Masios with Quremor and Badumas, Lasios with Galtomas and Ihalon.
From L21 that's 36 confusion casts a camp; at L11, 18 (Sios and Lios), enough for any one
fight. Spells are learned at each level-up on rand(0..29) < (IQ + Vit)/2 for each unknown
spell of a level with points, plus one at random for a level with none
(`levelup_learn_spells` 0x800b9090).

## Being a Psionic (what the bench changes)

What the game reads for the class change in golembench.py's `make_psionic`: class +0x0b
(10), alignment +0x0a bits 6-7 (Psionic: Neutral or Evil, `class_alignment` 0x8005e280),
the class minimums (Str 10, IQ 14, Vit 14, Luc 10), spells known +0x4c and points +0x5c,
HP (Psionic 1 + 1..3 a level, Bishop 2 + 1..4, `hp_dice` 0x800a138c), and gear (item +0x1c
class bit 10: of the Bishop's gear the Psionic keeps only the Staff, Bullwhip and Darkness
Cloak; Leather Gloves, Leather Sallet, Black Boots, Breast Plate and the Shield of Defense
come off). The derived block (+0x7e..+0xbf: saves, AC, resistances, slay bits) is rebuilt at
every fight's start from class, stats and gear (`battle_derive_stats` 0x800a1830, saves by
class in `battle_derive_saves` 0x800a1b84: Psionic save_bonus (1, 1), (2, 3), (4, 2)), so it
follows by itself. The party command list (`party_initiative` 0x800cf8e0) gives a Psionic
Spell but no Dispel.
