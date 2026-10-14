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
    else:
        threat = max(melee_round, 8 * lv if caster else 0)
        if r[0xc9]:
            threat += hp / 2 * 3 / 2
    if breath_one:
        blow_f, blow_b = max(blow_f, breath_one), max(blow_b, breath_one)
    return dict(id=struct.unpack_from('<H', r, 0x6c)[0], level=lv, mr=list(r[0xa3:0xa7]),
                flags=struct.unpack_from('<I', r, 0xa8)[0],
                resist=struct.unpack_from('<H', r, 0xcc)[0],
                weak=struct.unpack_from('<H', r, 0xce)[0], caster=caster, threat=threat,
                blow=(blow_f, blow_b), death=death,
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
            mons = [x for x in m['mons'] if _left(t, x[0], x[1]) > 0]
            mons = mons if kind != 'one' else mons[:1]
            for j, hp0, st in mons:
                hp = _left(t, j, hp0)
                kill = 1.0 if d >= hp else 0.5 if d >= hp * 0.7 else 0.0
                v += p * (min(d, hp) + kill * m['threat'])
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
                v += p * (_left(t, j, hp) + m['threat'] * 2)
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
            p_new = p * (1 - PLAN['dis'].get(t, 0))
            v += sum(p_new * worth for _ in mons)
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


def matters(g, M, party_hp, party_level=None, party=None):
    """Why a fight is worth spending points on, or None: 'story' (a story or boss fight),
    'above median level' (a monster above the party's median level), 'threat' (monsters
    that could take half the party's hit points in two rounds: a heavy fight, which gets
    levels 6-7 like a boss), or (d) 'kill hits' (a monster that could kill a member in one
    or two hits)."""
    if is_story(g):
        return 'story'
    # a monster above the party's median level (the Jail Ogre, 17, against a party of 14
    # counted as trash and got Mahalito five times; 2026-10-14)
    if party_level is not None and any(M[k]['level'] > party_level for k in M):
        return 'above median level'
    threat = sum(M[k]['threat'] * len(M[k]['mons']) for k in M)
    if threat * 2 >= party_hp / 2:
        return 'threat'
    if KILL_HITS and party and at_risk(g, M, party):
        return 'kill hits'
    return None


HEAVY = ('story', 'threat')     # matters() reasons that free levels 6-7 and support spells


def matters_detail(g, M, party_hp, party_level=None, party=None):
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
                        blow=[round(x, 1) for x in M[k]['blow']], death=M[k]['death']))
    threat = sum(x['threat'] * x['n'] for x in out)
    why = ('story' if is_story(g) else
           'above median level' if party_level is not None and any(M[k]['level'] > party_level for k in M) else
           'threat' if threat * 2 >= party_hp / 2 else
           'kill hits' if KILL_HITS and party and at_risk(g, M, party) else None)
    return dict(groups=out, threat=round(threat, 1), party_hp=party_hp, half_hp=party_hp / 2,
                two_rounds=round(threat * 2, 1), median_level=party_level, why=why,
                fixed=g.u8(FIXED), at_risk=[(s_, h, round(b, 1)) for s_, h, b in at_risk(g, M, party or [])])
