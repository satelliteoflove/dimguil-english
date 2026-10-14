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


def info(g, k):
    r = rec(g, k)
    lv = struct.unpack_from('<H', r, 0x74)[0]
    melee = []
    for o in (0xac, 0xb6, 0xc0):
        sw, n, s, b = r[o + 3], r[o + 4], r[o + 5], r[o + 6]
        if sw and n:
            melee.append(sw * (n * (s + 1) / 2 + b))
    caster = any(x != 0xff for x in r[0x8f:0xa3])
    hp = struct.unpack_from('<h', r, 0x72)[0]
    threat = max(sum(melee) / len(melee) * 0.5 if melee else 0, 8 * lv if caster else 0)
    if r[0xc9]:
        threat += hp / 2 * 3 / 2
    return dict(id=struct.unpack_from('<H', r, 0x6c)[0], level=lv, mr=list(r[0xa3:0xa7]),
                flags=struct.unpack_from('<I', r, 0xa8)[0],
                resist=struct.unpack_from('<H', r, 0xcc)[0],
                weak=struct.unpack_from('<H', r, 0xce)[0], caster=caster, threat=threat,
                screen=g.u8(GROUPS + k * 8 + 7), mons=standing(g, k))


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


def value(g, sid, k, M, clevel, cast_counts):
    """What casting sid at group k is worth now (hit points), or 0."""
    v = 0.0
    if sid in DAMAGE:
        mean, kind, el = DAMAGE[sid]
        for t in targets(g, k, kind, M):
            m = M[t]
            p = lands(m, sid)
            f = 0.5 if m['resist'] & el and el else 2.0 if m['weak'] & el and el else 1.0
            d = mean * f
            mons = m['mons'] if kind != 'one' else m['mons'][:1]
            for _, hp, st in mons:
                kill = 1.0 if d >= hp else 0.5 if d >= hp * 0.7 else 0.0
                v += p * (min(d, hp) + kill * m['threat'])
        return v
    if sid in DEATH:
        kind, base = DEATH[sid]
        for t in targets(g, k, 'group' if kind == 'group' else kind, M):
            m = M[t]
            mons = m['mons'] if kind != 'one' else m['mons'][:1]
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
            for _, hp, st in mons:
                v += p * (hp + m['threat'] * 2)
        return v
    if sid in DISABLE:
        for t in targets(g, k, DISABLE[sid], M):
            m = M[t]
            if sid in (SLEEP, KATIQUREA):
                if m['resist'] & 0x200:
                    continue
                base = 15 if m['weak'] & 0x200 else 50
                mons = [x for x in m['mons'] if x[2] < 8]
                worth = m['threat'] * 1.5
            elif sid == PARALYZE:
                base = 70 if m['resist'] & 0x10 else 17 if m['weak'] & 0x10 else 35
                mons = [x for x in m['mons'] if x[2] < 0x20]
                worth = m['threat'] * 2
            else:                               # Montino: only casters, twice a group
                if not m['caster'] or cast_counts.get((SILENCE, t), 0) >= 2:
                    continue
                base = 16 if m['weak'] & 0x800 else 50
                mons = m['mons']
                worth = 8 * m['level'] * 2
            p = lands(m, sid) * (1 - save_adj(base, m['level'], clevel))
            v += sum(p * worth for _ in mons)
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
    if sid == CORTU and n < 2:
        return 0.25 * spells * 3
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


def matters(g, M, party_hp, party_level=None):
    """A fight worth spending points on: a fixed fight, or monsters that could take half
    the party's hit points in two rounds. (A third made most of Area A's roamers count,
    and a training trip cast 53 spells in 12 fights; 2026-10-14.)"""
    if g.u8(FIXED):
        return True
    # a monster above the party's median level (the Jail Ogre, 17, against a party of 14
    # counted as trash and got Mahalito five times; 2026-10-14)
    if party_level is not None and any(M[k]['level'] > party_level for k in M):
        return True
    threat = sum(M[k]['threat'] * len(M[k]['mons']) for k in M)
    return threat * 2 >= party_hp / 2


def matters_detail(g, M, party_hp, party_level=None):
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
                        caster=c, breath=round(br, 1), threat=round(M[k]['threat'], 1)))
    threat = sum(x['threat'] * x['n'] for x in out)
    why = ('fixed' if g.u8(FIXED) else
           'above median level' if party_level is not None and any(M[k]['level'] > party_level for k in M) else
           'threat' if threat * 2 >= party_hp / 2 else None)
    return dict(groups=out, threat=round(threat, 1), party_hp=party_hp, half_hp=party_hp / 2,
                two_rounds=round(threat * 2, 1), median_level=party_level, why=why)
