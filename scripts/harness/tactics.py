"""Spell choice in battle: what each castable spell is worth against what stands now,
from the monsters' records in RAM, weighed by the chance it lands (2026-10-14).

Sources (each checked in the code or the site data, not taken from other Wizardry games):
  spells        ~/Documents/bartoks-trading-post/data/chara/spells/dim.json (ids are
                school * 21 + (level - 1) * 3 + slot; rips/agents/chapters/spells_table.txt)
  dice          docs/re/D-battle.md "Damage spells" and "Alchemist clouds"
  resistance    D-battle.md "Magic resistance": a hostile spell is shrugged off when
                rand(100) < the target's resistance to the caster's school (record +0xa3
                + school) + the group's magic screen (battle_groups +7) + 1
  elements      +0xcc resist bits halve the dice, +0xce weakness bits double them:
                0x80 fire, 0x100 cold, 0x4000 Tiltowait's
  saves         BATTLE spell_katino 0x800ac9fc (save 50, 15 if weak 0x200, immune if
                resistant 0x200), spell_montino 0x800adbc4 (50, 16 if weak 0x800),
                spell_lorks 0x800afbec (35, 70 if resistant 0x10, 17 if weak), spell_badi
                0x800ae040 (25, at least 5 + 4 a level above the caster; 125 for flags
                0x1480000), spell_bakadi 0x800ae7f8 (38; flagged immune), Mogato (summoned
                0x100000 only, 30), spell_matokani 0x800af4fc (level 8 or below, not undead)
  dispel        act_dispel 0x800a9eec: undead (+0xa8 0x80000) only, per monster
                5 * level + 50 - 10 * monster level (Bishop -26, Lord -18)
  records       monster_records 0x8008a918 + group * 0xd0 (groups 1-6 in a fixed battle);
                combatants 0x8008e230 + group * 0x7e + member * 0xe (+6 HP, +0xc status)

Values are in hit points, dealt or kept from the party, for this one cast. Threat is a
monster's expected damage a round: its mean attack (swings x dice) at half its hits
landing, or for a caster 8 a level, whichever is more; a breather adds half its HP over
three members.
"""
import struct

MREC = 0x8008a918
COMBAT = 0x8008e230
GROUPS = 0x8008c480
FIXED = 0x80079bde
UNDEAD, SUMMONED, DEATH_IMMUNE = 0x80000, 0x100000, 0x1480000
FIRE, COLD, PURE = 0x80, 0x100, 0x4000

# id: (mean per target, 'one' | 'group' | 'all', element)
DAMAGE = {
    1: (5, 'one', 0), 3: (5, 'group', FIRE), 7: (14, 'group', FIRE), 9: (36, 'one', 0),
    10: (21, 'group', FIRE), 13: (36, 'group', COLD), 16: (55, 'group', COLD),
    17: (60, 'one', 0), 20: (80, 'all', PURE), 22: (5, 'one', 0), 60: (96, 'one', 0),
    80: (36, 'group', 0),
    # clouds: three rounds of their dice (D-battle.md "Alchemist clouds")
    45: (7.5, 'group', FIRE), 48: (15, 'group', COLD), 51: (22.5, 'group', PURE),
    54: (36, 'group', FIRE), 57: (67.5, 'group', PURE), 62: (96, 'group', PURE),
    # psionic damage (the confusion on top isn't counted)
    63: (3, 'one', 0), 66: (3, 'group', 0), 72: (12, 'group', 0), 77: (50, 'one', 0),
    81: (30, 'all', 0), 82: (40, 'all', 0),
}
# death: id -> ('one' | 'group' | 'all', base save)
DEATH = {34: ('one', 25), 40: ('group', 38), 38: ('one', 30), 59: ('all', 0), 15: ('one', 0)}
SLEEP, SILENCE, PARALYZE = 0, 25, 69
KATIQUREA = 49
DISABLE = {SLEEP: 'group', KATIQUREA: 'all', SILENCE: 'group', PARALYZE: 'group'}
CORTU, BAMATU, MAPORFIC, PORFIC, DILTO, MORLIS, BADUMAS = 8, 29, 32, 23, 5, 6, 74
HEALS = {21, 30, 33, 36, 41, 58, 64, 79}
DIALKO, MADI = 28, 36
CHEAP_LEVEL = 3          # in a fight that doesn't matter, spells above this level wait
# (c) kill first (main, 2026-10-14, from the n1v0 chapter 9 wipe: Dalosto killed one
# member, then four Lorks paralyzed the rest): a group that can paralyze or stone a whole
# row (Lorks 69 hits one row, status_spell_targets 0x800b1524; Galtomas 81 all) counts
# PARA_FIRST times over for group and all-enemy damage, so Lahalito, Tiltowait and the like
# go there first. A paralyzed member stays down until a cure (party_upkeep 0x800a73f4).
PARA_SPELLS = (69, 81)
PARA_FIRST = 3.0
# (agent 13, main's call) the same for a group that casts group or all-enemy damage
# (Madalto, Lahalito, Tiltowait: DAMAGE kind 'group' or 'all'), GDMG_FIRST times over; a
# lone caster (one monster standing) counts that much for single-target spells too, since
# one kill removes the caster (n1v1m, n1v3k chapter 9: an Orc Adept party's Madalto killed
# Venus twice on the walk home and wiped n1v3 once). battle.choose_group puts fighters'
# blows on such a lone caster first.
GDMG_FIRST = 2.0
CORTU_STACK = 4          # Cortu casts a boss fight (support_value), each worth 3/4 of the last
HELPLESS_MELEE = True    # (revision 10) Katino and Lorks count the front-liners' extra damage (helpless_bonus)
DEBUFF_MIN = 0.3         # (fix 3) sleep, silence, paralysis only where a monster's chance of being caught is this


def school(sid):
    return sid // 21


def level(sid):
    return sid % 21 // 3 + 1


def rec(g, k):
    return g.e.read(MREC + k * 0xd0, 0xd0)


def standing(g, k):
    """[(member, hp, status)] for group k's monsters still up."""
    out = []
    for j in range(9):
        d = g.e.read(COMBAT + k * 0x7e + j * 0xe, 0xe)
        hp, st = struct.unpack_from('<h', d, 6)[0], struct.unpack_from('<H', d, 0xc)[0]
        if hp > 0 and st < 0x80:
            out.append((j, hp, st))
    return out


def groups(g):
    n = 6 if g.u8(FIXED) else 4
    return [k for k in range(1, n + 1) if g.u8(GROUPS + k * 8 + 5)]


AI_WEIGHTS = 0x800d89e0     # monster_ai_weights: 13 columns a row, row = record +0x88 (1-based)
LEVEL_WEIGHTS = 0x800da5c4  # 7 level weights per spell entry (monster_pick_spell 0x800d0c6c)
SPELL_FLAGS = 0x800d5874    # spell_flags_table: 0x100 damage, 0x400 status (BATTLE spell_flags)
F_DAMAGE, F_STATUS = 0x100, 0x400
BACK_REACH = 0x80           # attack +7: the attack reaches the back row
ROW = 3                     # a monster's group spell or breath hits one row of the party
# AI columns (monster_ai 0x800cffb0): 0 fight, 1 fight the weakest, 2 defend, 3-4 damage
# spell (entry 0, flag 0x100), 5 status spell (entry 1, flag 0x400), 10-11 breath
SPELLS_ON = True             # (b) caster threat from the record's spells, not 8 x level (on: main, 2026-10-14)
GROUP_REACH = False          # groups 3-4 of a random fight threaten only with back-row reach


def spell_flag(g, sid):
    return struct.unpack('<H', g.e.read(SPELL_FLAGS + sid * 2, 2))[0]


def monster_spells(g, r, entry, flag):
    """[(chance, spell id)] of what a monster casts for one AI spell column: a school at
    random among those with an entry, a level by the entry's weight row, a spell of that
    school and level with the column's flag at random (monster_pick_spell 0x800d0c6c,
    FUN_800d18c8). Chances are per cast of that column."""
    schools = [sc for sc in range(4) if r[0x8f + sc * 5 + entry] != 0xff]
    out = []
    for sc in schools:
        w = g.e.read(LEVEL_WEIGHTS + r[0x8f + sc * 5 + entry] * 7, 7)
        for lv in range(7):
            if not w[lv]:
                continue
            ids = [sc * 21 + lv * 3 + j for j in range(3) if spell_flag(g, sc * 21 + lv * 3 + j) & flag]
            for sid in ids:
                out.append((w[lv] / 100 / len(schools) / len(ids), sid))
    return out


def info(g, k):
    """Group k's monster: its record's numbers and what it threatens. threat is the
    expected damage to the party a round per monster: its AI row's chance of each action
    (fight, damage spell, breath; a spell or breath column it has nothing for falls back
    to fighting) times that action's mean damage, melee at half its swings landing. blow
    is the most one action can do to one member, by row (front, back): every swing of its
    best attack (back only with reach), its strongest damage spell, its breath. death:
    it has a death spell among its status spells."""
    r = rec(g, k)
    lv = struct.unpack_from('<H', r, 0x74)[0]
    hp = struct.unpack_from('<h', r, 0x72)[0]
    melee, blow_f, blow_b, reach = [], 0.0, 0.0, []
    for o in (0xac, 0xb6, 0xc0):
        sw, n, s, b = r[o + 3], r[o + 4], r[o + 5], r[o + 6]
        if sw and n:
            d = sw * (n * (s + 1) / 2 + b)
            melee.append(d)
            blow_f = max(blow_f, d)
            if r[o + 7] & BACK_REACH:
                blow_b = max(blow_b, d)
                reach.append(d)
    if GROUP_REACH and k > 2 and not g.u8(FIXED):
        # groups 3-4 of a random fight reach nobody without the reach bit (monster_ai:
        # it defends instead)
        melee, blow_f = reach, blow_b
    caster = any(x != 0xff for x in r[0x8f:0xa3])
    melee_round = sum(melee) / len(melee) * 0.5 if melee else 0
    breath_one = hp / 2 * 0.75 if r[0xc9] else 0
    death = False
    if SPELLS_ON:
        ai = struct.unpack_from('<H', r, 0x88)[0]
        p = [x / 100 for x in g.e.read(AI_WEIGHTS + (ai - 1) * 13, 13)] if ai else [1.0] + [0] * 12
        dmg = monster_spells(g, r, 0, F_DAMAGE) if caster else []
        sts = monster_spells(g, r, 1, F_STATUS) if caster else []
        p_fight, p_dmg, p_breath = p[0] + p[1], p[3] + p[4], p[10] + p[11]
        if not dmg:
            p_fight, p_dmg = p_fight + p_dmg, 0
        if not sts:
            p_fight += p[5]
        if not breath_one:
            p_fight, p_breath = p_fight + p_breath, 0
        tot = sum(pr for pr, _ in dmg) or 1
        spell_round = 0.0
        for pr, sid in dmg:
            if sid in DAMAGE:
                mean, kind, _ = DAMAGE[sid]
                spell_round += pr / tot * mean * (1 if kind == 'one' else ROW if kind == 'group' else 6)
                blow_f, blow_b = max(blow_f, mean), max(blow_b, mean)
        death = any(sid in DEATH for _, sid in sts)
        threat = p_fight * melee_round + p_dmg * spell_round + p_breath * breath_one * ROW
        threat_spell = p_dmg * spell_round
        # monster_ai 0x800cffb0: columns 3-4 damage (spell entry 0), 5 status (1), 6 buff
        # (2), 7 heal (3), 8 cure (4); a column it has no spells for falls back to fighting
        has = [any(r[0x8f + sc * 5 + e] != 0xff for sc in range(4)) for e in range(5)]
        cast_share = sum(p[c] for c, e in ((3, 0), (4, 0), (5, 1), (6, 2), (7, 3), (8, 4)) if has[e])
        # column 1 fights the reachable member with the least HP: that part lands on one
        # member, the weakest (front row: any attack; back row: reach attacks only)
        reach_round = sum(reach) / len(reach) * 0.5 if reach else 0
        focus = (p[1] * melee_round, p[1] * reach_round)
        dsrc = disable_sources(g, k, r, p_fight, p[5] if sts else 0.0, sts)
    else:
        dsrc = []
        threat_spell = 8 * lv if caster else 0
        threat = max(melee_round, 8 * lv if caster else 0)
        if r[0xc9]:
            threat += hp / 2 * 3 / 2
    if breath_one:
        blow_f, blow_b = max(blow_f, breath_one), max(blow_b, breath_one)
    if not SPELLS_ON:
        cast_share = 1.0 if caster else 0.0
        focus = (0.0, 0.0)
    return dict(id=struct.unpack_from('<H', r, 0x6c)[0], level=lv, mr=list(r[0xa3:0xa7]), cast_share=cast_share, focus=focus,
                flags=struct.unpack_from('<I', r, 0xa8)[0],
                resist=struct.unpack_from('<H', r, 0xcc)[0],
                weak=struct.unpack_from('<H', r, 0xce)[0], caster=caster, threat=threat, threat_spell=threat_spell,
                blow=(blow_f, blow_b), death=death, dsrc=dsrc, dis_hp=0.0, dis_hp_spell=0.0,
                para=para_caster(dsrc, dmg + sts if SPELLS_ON else []),
                gdmg=any(sid in DAMAGE and DAMAGE[sid][1] != 'one' for _, sid in (dmg if SPELLS_ON else [])),
                silenced=silenced(g, k),
                screen=g.u8(GROUPS + k * 8 + 7), mons=standing(g, k))


# Disabling (agent 9, 2026-10-14, from the n1v1 chapter 8 near-wipe: 18 Nightmares and 6
# Merry Puppets cast or danced Katino 92 times and the party slept through 19 rounds, rated
# 5 hit points a Nightmare). A member asleep, paralyzed, stoned or silenced loses actions,
# which the damage threat doesn't see. The party's side of the code:
#   status_spell_targets 0x800b1524: a monster's group spell hits one row (the caster's
#     row byte, combatant +0xb; chosen at random when both rows stand), Katiqurea both;
#     save = the spell's base, 85 if the member's resist bits (+0xae) have the spell's bit,
#     + the member's effect resistance (+0xb0 + table 0x800d8524[kind]) for kinds 0-2,
#     + 4 a level the member is above the caster (save_adjust 0x800c990c), clamped 5-100
#   status_spell 0x800b173c: first the member's magic resistance (+0x87 + school) + the
#     party's magic screen (battle_groups +7) + 1 nullifies
#   monster_attack_roll 0x800aaed0: an attack whose noun is 0x100 or more is an ability: it
#     casts spell +6 as an item would, so silence doesn't stop it (the Nightmare's and the
#     Merry Puppet's "strange dance" is Katino: attack 2 = [19, 1, 46, ...]); monster_melee
#     0x800aaa04 uses attack 1 on rand(100) > 68 when it's usable, else attack 0, plus
#     attack 2 when it has swings
#   apply_status_effects 0x800aa190: an attack's effect bits (+7) land at chance (+8) x
#     (99 - the member's resistance to that effect)
#   party_upkeep 0x800a73f4: sleep and knock-out wear off at min(4 x level, 35)% a round,
#     paralysis and stone not at all; silence lasts rand(L) + L/8 rounds, L = max(3, caster
#     level - target level), counted down at each round's start (silence_rounds)
DIS_SPELL = {0: ('sleep', 0, 50, 0x200, 'row'), 49: ('sleep', 0, 50, 0x200, 'all'),
             25: ('silence', 1, 50, 0x800, 'row'), 69: ('para', 4, 35, 0x10, 'row')}
DIS_HIT = {0x01: ('sleep', 0), 0x20: ('sleep', 5), 0x10: ('para', 4), 0x04: ('para', 2)}
EFFECT_RES = 0x800d8524     # status kind -> index into a member's +0xb0 effect resistances
LOST_CAP = 0.9              # the lost share of the party's actions counted at most
LOST_ACTIONS = True         # (fix 1) count actions taken away as threat


def first_weight(m, kind):
    """How many times over a damage spell's worth counts at group m (PARA_FIRST,
    GDMG_FIRST): group and all-enemy spells at a group that can paralyze a row or cast
    group damage, any spell when that group is down to one monster."""
    if not (m.get('para') or m.get('gdmg')):
        return 1.0
    if kind == 'one' and len(m['mons']) > 1:
        return 1.0
    return PARA_FIRST if m.get('para') else GDMG_FIRST


def para_caster(dsrc, dmg):
    """Whether a group can paralyze or stone a row or the whole party (PARA_SPELLS), by spell
    or by an ability that casts one."""
    return (any(src[0] == 'spell' and src[1] in PARA_SPELLS for _, src, _ in dsrc)
            or any(sid in PARA_SPELLS for _, sid in dmg))


def silence_rounds(clevel, mlevel):
    """Expected rounds a landed Montino keeps a monster from casting. status_spell 0x800b173c
    kind 1: counter = rand(L) + L / 8, L = caster level - target level clamped 3-255;
    counters_tick 0x800a77e0 takes 1 off at the start of every round, and cast_spell
    0x800abcc0 refuses while it's not 0. So the rest of this round when the counter is 1 or
    more (half a round on average: the monster may already have acted), then counter - 1
    whole rounds. At equal levels (L = 3): 2/3 x 0.5 + 1/3 = about 0.67 of a round."""
    L = min(255, max(3, clevel - mlevel))
    n = 0.0
    for r in range(L):
        c = r + L // 8
        n += (0.5 if c >= 1 else 0.0) + max(0, c - 1)
    return n / L


def disable_sources(g, k, r, p_fight, p_status, sts):
    """What group k's monster does a round that can take a member's actions away:
    [(chance a round, ('spell', sid, silenceable) | ('hit', kind, effect index), reach)]."""
    out = []
    for pr, sid in sts:
        if sid in DIS_SPELL and p_status:
            out.append((p_status * pr, ('spell', sid, True), False))
    atk = [r[o:o + 10] for o in (0xac, 0xb6, 0xc0)]
    nouns = [struct.unpack_from('<H', a, 0)[0] for a in atk]
    ability = [0x100 <= n < 1621 for n in nouns]
    reach_any = bool((atk[0][7] | atk[1][7]) & BACK_REACH)
    if k > 2 and not g.u8(FIXED) and not reach_any:
        return out              # groups 3-4 of a random fight can't reach: their fight turns defend
    use1 = ability[1] or (nouns[1] < 0xff or nouns[1] >= 0x8000) and atk[1][3] > 0
    uses = [(0, 0.69 if use1 else 1.0), (1, 0.31 if use1 else 0.0), (2, 1.0 if atk[2][3] else 0.0)]
    for i, u in uses:
        if not u:
            continue
        a = atk[i]
        if ability[i]:
            if a[6] in DIS_SPELL:
                out.append((p_fight * u, ('spell', a[6], False), False))
            continue
        sw, chance = a[3], a[8] / 100
        if not sw or not chance:
            continue
        for bit, (kind, idx) in DIS_HIT.items():
            if a[7] & bit:
                out.append((p_fight * u * (1 - 0.5 ** sw) * chance, ('hit', kind, idx), bool(a[7] & BACK_REACH)))
    return out


def silenced(g, k):
    """Group k's monsters with a silence counter (combatant +2), by member."""
    return {j for j in range(9) if g.u8(COMBAT + k * 0x7e + j * 0xe + 2)}


def disable(g, M, members, scale=None):
    """The share of the party's actions monsters present take away a round (fix 1), over
    the next two rounds from now, and each monster's part of it in hit points. members:
    [(slot, roster raw, level)] standing. scale: group -> share of its monsters still up
    (likely_loss's after-the-party's-round view). Sets M[k]['dis_hp'] (a monster's
    disabling worth, hit points a round it lives) and 'dis_hp_spell' (the part silence
    would stop). Returns dict(share, L, lost) with L = 1 / (1 - share): how much longer the
    fight runs, so how much more of the monsters' damage the party takes."""
    if not LOST_ACTIONS or not members or not M:
        return dict(share=0.0, L=1.0, lost=[])
    scale = scale or {}
    tbl = g.e.read(EFFECT_RES, 8)
    screen = g.u8(GROUPS + 7)
    front = [m for m in members if m[0] < 3]
    back = [m for m in members if m[0] >= 3]
    T = sum(M[k]['threat'] * len(M[k]['mons']) * scale.get(k, 1.0) for k in M)
    worth = T / len(members)             # a member-round lost: the fight runs that much longer
    for k in M:
        M[k]['dis_hp'] = M[k]['dis_hp_spell'] = 0.0
    lost = []
    for slot, raw, mlv in members:
        has_spells = any(raw[0x5c:0x5c + 28])
        keep = {}                        # kind -> chance of staying clear this round
        for k in M:
            m = M[k]
            act = [j for j, hp, st in m['mons'] if st < 8]
            n_all = len(act) * scale.get(k, 1.0)
            n_spell = len([j for j in act if j not in m['silenced']]) * scale.get(k, 1.0)
            for rate, src, reach in m['dsrc']:
                if src[0] == 'spell':
                    _, sid, silenceable = src
                    kind, ki, base, rbit, rows = DIS_SPELL[sid]
                    mr = raw[0x87 + school(sid)] + screen
                    land = max(0.0, 1 - min(255, mr + 1) / 100)
                    save = 85 if struct.unpack_from('<H', raw, 0xae)[0] & rbit else base
                    if ki < 3:
                        save += raw[0xb0 + tbl[ki]]
                    save += 4 * max(0, mlv - m['level'])
                    p = land * (1 - min(100, max(5, save)) / 100)
                    share = 1.0 if rows == 'all' or not (front and back) else 0.5
                    n = n_spell if silenceable else n_all
                else:
                    _, kind, idx = src
                    p = max(0, 99 - raw[0xb0 + idx]) / 100
                    reachable = members if reach else front
                    share = 1.0 / len(reachable) if any(x[0] == slot for x in reachable) else 0.0
                    n = n_all
                if kind == 'silence':
                    if not has_spells:
                        continue
                    weight = 0.5         # a silenced caster still fights
                else:
                    weight = 1.0
                d = rate * p * share
                if d <= 0 or n <= 0:
                    continue
                keep[kind] = keep.get(kind, 1.0) * (1 - d) ** n
                w = wake(kind, mlv)
                hp_ = d * weight / w * worth             # member-rounds it takes, in hit points
                m['dis_hp'] += hp_
                if src[0] == 'spell' and silenceable:
                    m['dis_hp_spell'] += hp_
        out = 1.0
        for kind, q in keep.items():
            h, w = 1 - q, wake(kind, mlv)
            x1 = h
            x2 = x1 * (1 - w) + (1 - x1) * h
            out *= 1 - (0.5 if kind == 'silence' else 1.0) * (x1 + x2) / 2
        lost.append((slot, round(1 - out, 2)))
    share = min(LOST_CAP, sum(x for _, x in lost) / len(members))
    return dict(share=round(share, 3), L=1 / (1 - share), lost=lost)


def wake(kind, mlv):
    """A member's chance a round of shaking a disabling status off in battle."""
    if kind == 'sleep':
        return max(0.2, min(4 * mlv, 35) / 100)
    if kind == 'silence':
        return 0.33
    return 0.2                  # paralysis, stone: only a cure (Dialko, Madi) ends them


# (revision 10, agent 14) a party hit on a monster that can't act (status 2 or more:
# confused, poisoned, asleep, paralyzed...) does damage + rand(damage) (melee_apply_hits
# 0x800a963c; to-hit doesn't change, party_melee 0x800a8c2c), about half again. So
# Katino and Lorks are also worth the front-liners' extra damage on the group they hit,
# for the rounds it stays down: monster_upkeep 0x800a6aa0 wakes a monster with chance
# min(4 x level, 35)% a round (paralysis 2 x level).
PARTY = 0x8007e812          # the party's roster indices by slot (-1 empty)
OSLO = 0x8007e830           # the party's to-hit bonus while Oslo or Maoslo lasts
REACH_ROW = 0x8007989d      # fixed battles: reach 2 means the front row's groups (weapon_reach 0x800c94a8)
REACH_ALL = 0x800798b8      # ... and reach 4 every group
ROSTER, ROSTER_LEN = 0x8007d708, 0xd0
WAKE_K = {SLEEP: 4, KATIQUREA: 4, PARALYZE: 2}


def weapon_reach(g, code, slot):
    """The last group a weapon reaches from party slot `slot` (weapon_reach 0x800c94a8)."""
    r = code & 7
    if code & 3:
        r = r << 1 if slot < 3 else code & 2
    if g.u8(FIXED) == 1:
        r = g.u8(REACH_ROW) if r == 2 else g.u8(REACH_ALL) if r == 4 else r
    return r


def melee_on(g, k, M):
    """The party's expected melee damage a round on group k (party_melee 0x800a8c2c), from
    the members who can act and would aim at it: k is the lowest-numbered group their
    weapon reaches (battle.choose_group, kill-first aside). Hits land on rand(20) >= T,
    T = 19 + k - AC + AC modifier - to-hit, held to 19, Oslo's bonus off, at least 1."""
    d = rec(g, k)
    ac = struct.unpack_from('<b', d, 0x7a)[0]
    mods = [struct.unpack('<b', g.e.read(COMBAT + k * 0x7e + j * 0xe + 4, 1))[0] for j, _, _ in M[k]['mons']]
    acmod = mods[0] if mods else 0
    b = g.u8(OSLO)
    tot = 0.0
    for slot in range(6):
        ri = struct.unpack('<b', g.e.read(PARTY + slot, 1))[0]
        if ri < 0:
            continue
        c = g.e.read(COMBAT + slot * 0xe, 0xe)
        if struct.unpack_from('<H', c, 0xc)[0] >= 8:
            continue
        r = g.e.read(ROSTER + ri * ROSTER_LEN, ROSTER_LEN)
        items = struct.unpack_from('<10H', r, 0x20)
        main = any(x != 0xffff and x & 0x1000 for x in items)
        second = any(x != 0xffff and not x & 0x1000 and x & 0x800 for x in items)
        hit = struct.unpack_from('<h', r, 0x84)[0]
        for hand, used in ((0, main or not second), (1, second)):
            if not used:
                continue
            reach = weapon_reach(g, r[0x9c + hand], slot)
            if not (k <= reach and k == min(x for x in M if x <= reach)):
                continue
            T = min(19, 19 + k - ac + acmod - hit) - b
            if b and T >= 15:
                T -= 3
            elif b and 13 <= T <= 14:
                T = 12
            T = max(1, T)
            sw = max(1, min(10, c[8] + r[0x94 + hand]))
            n, sides = max(1, r[0x96 + hand * 3]), max(1, r[0x97 + hand * 3])
            bonus = struct.unpack_from('<b', r, 0x98 + hand * 3)[0]
            tot += sw * max(0, 20 - T) / 20 * (n * (sides + 1) / 2 + bonus)
    return tot


def helpless_bonus(g, sid, t, m, frac, M):
    """What disabling a share `frac` of group t's monsters adds to the front-liners'
    melee (revision 10): half their damage a round on it, for the rounds it stays down
    (half the casting round, then (1-q)/q), at most half its hit points left."""
    if frac <= 0:
        return 0.0
    q = min(WAKE_K[sid] * m['level'], 35) / 100
    rounds = 0.5 + (1 - q) / q
    hp = sum(max(0, _left(t, j, h)) for j, h, _ in m['mons'])
    return 0.5 * frac * min(melee_on(g, t, M) * rounds, hp)


def danger_of(m):
    """What one of group m's monsters costs the party a round it stands: its damage threat
    and the actions it takes away (disable(): dis_hp, 0 until it has run)."""
    return m['threat'] + m.get('dis_hp', 0.0)


def lands(m, sid):
    """Chance a hostile spell from sid's school gets past group m's resistance."""
    return max(0.0, 1 - min(255, m['mr'][school(sid)] + m['screen'] + 1) / 100)


def save_adj(base, mlevel, clevel):
    return min(100, max(5, base + 4 * max(0, mlevel - clevel))) / 100


def targets(g, k, kind, M):
    """The groups a spell aimed at k reaches: in a fixed battle a group spell takes the
    row (groups 1-3 or 4-6; spell_group_range), 'all' every group."""
    if kind == 'all':
        return list(M)
    if kind == 'group' and g.u8(FIXED):
        row = range(1, 4) if k <= 3 else range(4, 7)
        return [x for x in M if x in row]
    return [k]


# this round's casts already chosen (battle.default_policy): group -> {monster: expected
# damage} and group -> chance it's already disabled, so a second caster doesn't spend a
# point on what the first one's spell will likely finish (reset each round)
PLAN = dict(round=None, dmg={}, dis={})


def plan_reset(rnd):
    if PLAN['round'] != rnd:
        PLAN.update(round=rnd, dmg={}, dis={})


def _left(t, j, hp):
    return hp - PLAN['dmg'].get(t, {}).get(j, 0)


def value(g, sid, k, M, clevel, cast_counts, commit=False):
    """What casting sid at group k is worth now (hit points), or 0, after this round's
    casts already planned (PLAN). commit: add this cast to the plan."""
    v = 0.0
    if sid in DAMAGE:
        mean, kind, el = DAMAGE[sid]
        for t in targets(g, k, kind, M):
            m = M[t]
            p = lands(m, sid) * (1 - PLAN['dis'].get(t, 0) * 0.5)
            f = 0.5 if m['resist'] & el and el else 2.0 if m['weak'] & el and el else 1.0
            d = mean * f
            w = first_weight(m, kind)
            mons = [x for x in m['mons'] if _left(t, x[0], x[1]) > 0]
            mons = mons if kind != 'one' else mons[:1]
            for j, hp0, st in mons:
                hp = _left(t, j, hp0)
                kill = 1.0 if d >= hp else 0.5 if d >= hp * 0.7 else 0.0
                v += p * (min(d, hp) + kill * danger_of(m)) * w
                if commit:
                    PLAN['dmg'].setdefault(t, {})[j] = PLAN['dmg'].get(t, {}).get(j, 0) + p * d
        return v
    if sid in DEATH:
        kind, base = DEATH[sid]
        for t in targets(g, k, 'group' if kind == 'group' else kind, M):
            m = M[t]
            mons = [x for x in m['mons'] if _left(t, x[0], x[1]) > 0]
            mons = mons if kind != 'one' else mons[:1]
            if sid == 15:                       # Zilwan: the undead only
                if not m['flags'] & UNDEAD:
                    continue
                p = lands(m, sid)
            elif sid == 38:                     # Mogato: the summoned only
                if not m['flags'] & SUMMONED:
                    continue
                p = lands(m, sid) * (1 - save_adj(base, m['level'], clevel))
            elif sid == 59:                     # Matokani: level 8 or below, not undead
                if m['flags'] & UNDEAD or m['level'] > 8:
                    continue
                p = 1.0
            else:
                if m['flags'] & DEATH_IMMUNE:
                    continue
                p = lands(m, sid) * (1 - save_adj(base, m['level'], clevel))
            for j, hp, st in mons:
                v += p * (_left(t, j, hp) + danger_of(m) * 2)
                if commit:
                    PLAN['dmg'].setdefault(t, {})[j] = PLAN['dmg'].get(t, {}).get(j, 0) + p * hp
        return v
    if sid in DISABLE:
        for t in targets(g, k, DISABLE[sid], M):
            m = M[t]
            if sid in (SLEEP, KATIQUREA):
                if m['resist'] & 0x200:
                    continue
                base = 15 if m['weak'] & 0x200 else 50
                mons = [x for x in m['mons'] if x[2] < 8]
                worth = danger_of(m) * 1.5
            elif sid == PARALYZE:
                base = 70 if m['resist'] & 0x10 else 17 if m['weak'] & 0x10 else 35
                mons = [x for x in m['mons'] if x[2] < 0x20]
                worth = danger_of(m) * 2
            else:                               # Montino: only casters, twice a group
                if not m['caster'] or cast_counts.get((SILENCE, t), 0) >= 2:
                    continue
                base = 16 if m['weak'] & 0x800 else 50
                mons = m['mons']
                # silence takes away every spell action, heals and buffs too (a healer
                # drags a fight out): 8 x level x 2 scaled by the share of its AI row's
                # actions it has spells for (cast_share; SPELLS_ON), for the rounds the
                # silence lasts (silence_rounds: under one at equal levels)
                n = silence_rounds(clevel, m['level'])
                worth = 8 * m['level'] * n * (m.get('cast_share', 1.0) if SPELLS_ON else 1.0)
                # (fix 2) or what its spells do, damage and members put to sleep, for those
                # rounds; abilities aren't silenced
                worth = max(worth, (m.get('threat_spell', 0) + m.get('dis_hp_spell', 0)) * n)
                mons = [x for x in mons if x[0] not in m.get('silenced', ())]
            p = lands(m, sid) * (1 - save_adj(base, m['level'], clevel))
            if p < DEBUFF_MIN:
                # (fix 3) not into a group that nullifies or saves against it most of the
                # time (n1v1 chapter 8: Montino twice at Nightmares that nullify Priest
                # spells 65% of the time and save half the rest: 17% a monster)
                continue
            p_new = p * (1 - PLAN['dis'].get(t, 0))
            v += sum(p_new * worth for _ in mons)
            if HELPLESS_MELEE and sid in WAKE_K and m['mons']:
                v += helpless_bonus(g, sid, t, m, p_new * len(mons) / len(m['mons']), M)
            if commit and mons:
                PLAN['dis'][t] = 1 - (1 - PLAN['dis'].get(t, 0)) * (1 - p)
        return v
    return 0.0


def support_value(g, sid, M, cast_counts, party_alive):
    """Party-side spells, for fights that matter: worth a share of what the monsters
    would deal over the next three rounds."""
    melee = sum(M[k]['threat'] * len(M[k]['mons']) for k in M if not M[k]['caster'])
    spells = sum(8 * M[k]['level'] * len(M[k]['mons']) for k in M if M[k]['caster'])
    n = cast_counts.get(sid, 0)
    if sid == BAMATU and n < 2:
        return 0.15 * melee * 3
    if sid == MAPORFIC and n < 1:
        return 0.10 * melee * 3
    if sid == CORTU and n < CORTU_STACK:
        # (agent 14, the community's boss advice: stack Cortu) each cast takes the screen to
        # 3/4 of what it was + 2 x level (spell_cortu, D-battle.md), so each adds 3/4 of
        # the last one's gain: 2L, 3.5L, 4.6L, 5.5L
        return 0.25 * spells * 3 * 0.75 ** n
    return 0.0


def armor_value(g, sid, k, M, cast_counts):
    """Dilto (enemy group AC +2), Morlis (+4): once a group, against a group with a lot
    of hit points left, worth the extra blows landing over three rounds; Badumas takes a
    damage die off each attack."""
    m = M[k]
    if cast_counts.get((sid, k), 0) >= 1:
        return 0.0
    hp = sum(x[1] for x in m['mons'])
    if sid in (DILTO, MORLIS):
        return min(hp, 30) * (0.1 if sid == DILTO else 0.2) * 3 if hp > 80 else 0.0
    if sid == BADUMAS and not m['caster']:
        return 0.2 * m['threat'] * len(m['mons']) * 3
    return 0.0


def dispel_value(g, k, M, cls, clevel):
    m = M.get(k)
    if not m or not m['flags'] & UNDEAD:
        return 0.0
    p = 5 * clevel + 50 - 10 * m['level'] - (26 if cls == 0xb else 18 if cls == 5 else 0)
    p = min(255, max(10, p)) / 100
    return sum(min(1, p) * (hp + m['threat']) for _, hp, _ in m['mons'])


STORY_ONLY = False       # (a) only story and boss fights count as fixed, not a floor's fight squares
KILL_HITS = False        # (d) a monster that can kill a member in one or two hits makes it matter
STORY = [None]          # battle.fight sets it at the fight's start (story_fight)
TRAINING = False        # chapters.train: a training trip, home walk included


def story_fight(g):
    """A fixed fight met outside a training trip and off the floor's fight squares (the
    site's event type 0x14): a story or boss fight. Chris, 2026-10-14: the training
    floors' fixed fights aren't bosses. Area B's human parties come on fixed grids both
    on the squares and as roamers between them (smoke1: B4 (13, 16), not a square), so a
    training trip's fixed fights never count."""
    if not g.u8(FIXED):
        return False
    if not STORY_ONLY:
        return True
    if TRAINING:
        return False
    from harness import nav, maze
    try:
        sq = g.pos()
        return tuple(sq) not in nav.floor(g.u8(maze.AREA))['fights']
    except Exception:
        return True


def is_story(g):
    if STORY[0] is None:
        STORY[0] = story_fight(g)
    return STORY[0]


def danger(g, M, party):
    """[(slot, hp, blow)] for each standing member: the most one action of a monster
    present could do to them (front row 0-2, back row 3-5; tactics.info blow)."""
    out = []
    for slot, hp, mx in party:
        b = max((M[k]['blow'][0 if slot < 3 else 1] for k in M), default=0)
        out.append((slot, hp, b))
    return out


def at_risk(g, M, party):
    """Members a monster present could kill in one or two hits (d)."""
    return [(slot, hp, b) for slot, hp, b in danger(g, M, party) if hp > 0 and b * 2 >= hp]


def matters(g, M, party_hp, party_level=None, party=None, lost=None):
    """Why a fight is worth spending points on, or None: 'story' (a story or boss fight),
    'above median level' (a monster above the party's median level), 'threat' (monsters
    that could take half the party's hit points in two rounds: a heavy fight, which gets
    levels 6-7 like a boss), 'disable' (the same once the actions they take away are
    counted: lost (disable()) L stretches the rounds), or (d) 'kill hits' (a monster that
    could kill a member in one or two hits)."""
    if is_story(g):
        return 'story'
    # a monster above the party's median level (the Jail Ogre, 17, against a party of 14
    # counted as trash and got Mahalito five times; 2026-10-14)
    if party_level is not None and any(M[k]['level'] > party_level for k in M):
        return 'above median level'
    threat = sum(M[k]['threat'] * len(M[k]['mons']) for k in M)
    if threat * 2 >= party_hp / 2:
        return 'threat'
    if lost and threat * lost['L'] * 2 >= party_hp / 2:
        return 'disable'
    if KILL_HITS and party and at_risk(g, M, party):
        return 'kill hits'
    return None


HEAVY = ('story', 'threat', 'disable', 'long fight', 'focus')     # matters() reasons that free levels 6-7 and support spells


def matters_detail(g, M, party_hp, party_level=None, party=None, lost=None):
    """What matters() weighed, for the trip logs (it doesn't change the rating): per group
    the monster id, level, count, and its threat split into melee, caster (8 x level) and
    breath parts; the total against half the party's HP; and which rule said yes."""
    out = []
    for k in M:
        r = rec(g, k)
        lv = M[k]['level']
        melee = []
        for o in (0xac, 0xb6, 0xc0):
            sw, n, s_, b = r[o + 3], r[o + 4], r[o + 5], r[o + 6]
            if sw and n:
                melee.append(sw * (n * (s_ + 1) / 2 + b))
        m = sum(melee) / len(melee) * 0.5 if melee else 0
        c = 8 * lv if M[k]['caster'] else 0
        br = struct.unpack_from('<h', r, 0x72)[0] / 2 * 3 / 2 if r[0xc9] else 0
        out.append(dict(id=M[k]['id'], level=lv, n=len(M[k]['mons']), melee=round(m, 1),
                        caster=c, breath=round(br, 1), threat=round(M[k]['threat'], 1),
                        blow=[round(x, 1) for x in M[k]['blow']], death=M[k]['death'],
                        dis_hp=round(M[k].get('dis_hp', 0), 1), para=M[k].get('para', False), gdmg=M[k].get('gdmg', False)))
    threat = sum(x['threat'] * x['n'] for x in out)
    why = ('story' if is_story(g) else
           'above median level' if party_level is not None and any(M[k]['level'] > party_level for k in M) else
           'threat' if threat * 2 >= party_hp / 2 else
           'disable' if lost and threat * lost['L'] * 2 >= party_hp / 2 else
           'kill hits' if KILL_HITS and party and at_risk(g, M, party) else None)
    return dict(groups=out, threat=round(threat, 1), party_hp=party_hp, half_hp=party_hp / 2,
                two_rounds=round(threat * 2, 1), median_level=party_level, why=why,
                fixed=g.u8(FIXED), lost=lost and dict(share=lost['share'], L=round(lost['L'], 2), members=lost['lost']),
                at_risk=[(s_, h, round(b, 1)) for s_, h, b in at_risk(g, M, party or [])])
