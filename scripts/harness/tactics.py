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
import math, struct

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
DEATH_THREAT = True      # (agent 14) a monster's death spells count in its threat (info)
DEATH_LANDS = 0.5        # ... landing on about half the casts (save and magic screen)
DEATH_REACH = True       # (bossfight) ... Bakadi on every member of a row
DEATH_EXTRA = 1.0        # (bossfight) killing or screening off a death caster: its deaths count this much again (danger_of, casting_danger)
HELPLESS_MELEE = True    # (revision 10) Katino and Lorks count the front-liners' extra damage (helpless_bonus)
DRAIN = {37: 0.75}       # (support) Labadi: the share of a member's max HP one cast takes (it leaves a few)
DRAIN_THREAT = True      # (support) ... counted in a monster's spell threat (info)
# Confusion (Chris, 2026-10-17, c17v4a: an Orc Esper's Lasios confused Dax, Earth and Mercury,
# and Dax killed everyone). Sios, Lios, Masios and Lasios confuse each member they hurt at
# CONFUSE's chance (psionic_damage 0x800b34b0, D-battle.md "Psionic damage"); a confused
# member can only Fight, half its blows go to a random ally, for about 13 rounds unless Madi
# or Morfis cures it. DAMAGE counts only their dice, so a confusing caster rated as a weak
# one. info's threat_conf: a member confused counts CONF_HP of the party's mean max HP (half
# a member killed, as DEATH_THREAT counts a death), at CONF_LANDS for magic resistance and
# the screen, times the members the spell reaches (DAMAGE kind: 1, ROW, 6) and its AI row's
# chance of casting it. Kept out of threat, so the fight ratings (matters, likely_loss) are
# as they were; counted in danger_of, caster_danger and spell_hp, so caster_order (the
# fighters' and focus casters' order), the kill worth of damage spells, sleep/paralysis/
# silence worth and Cortu all rate the confusing group higher.
CONF_THREAT = True
CONFUSE = {63: 0.65, 66: 0.65, 72: 0.60, 82: 0.60}     # Sios, Lios, Masios, Lasios
CONF_HP = 0.5
CONF_LANDS = 0.75
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
    threat_death = 0.0
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
        threat_drain = 0.0
        if DRAIN_THREAT and any(sid in DRAIN for _, sid in dmg + sts):
            # (support) Labadi takes nearly all of one member's HP (ch16 t1: 297, 287 and 281
            # off Uranus) and isn't in DAMAGE, so the Crystal Men's spells rated nothing and
            # Cortu stayed home: DRAIN's share of the party's mean max HP a cast, in whichever
            # spell column the record has it (damage, entry 0, or status, entry 1). Kept out
            # of threat, so the fight ratings (matters, likely_loss) are as they were; only
            # battle's support plan counts it (casting_danger drain=True)
            hp_m = [g.char(i)['max_hp'] for i in g.party()]
            mean_hp = sum(hp_m) / len(hp_m) if hp_m else 0
            tot_s = sum(pr for pr, _ in sts) or 1
            d_round = (p_dmg * sum(pr / tot * DRAIN[sid] for pr, sid in dmg if sid in DRAIN)
                       + p[5] * sum(pr / tot_s * DRAIN[sid] for pr, sid in sts if sid in DRAIN)) * mean_hp
            threat_drain = d_round
        if death and DEATH_THREAT:
            # (agent 14) a death spell takes a whole member: its status column's chance of
            # one, at DEATH_LANDS, times the party's mean max HP (n1v0 chapter 10: the
            # Guardians' ArchPriests rated 2.9 a round while their Badi killed three; now 22.5)
            tot_s = sum(pr for pr, _ in sts) or 1
            hp_m = [g.char(i)['max_hp'] for i in g.party()]
            # (bossfight) Bakadi takes a row, each member saving on their own at 65
            # (D-battle.md), so it counts ROW members at 35% each (n1v0w chapter 13: the
            # Arch Priests' Bakadi rated as one Badi, and Cortu stopped while they stood)
            d_round = p[5] * sum(pr * (ROW * 0.35 / DEATH_LANDS if DEATH_REACH and sid == 40 else 1)
                                 for pr, sid in sts
                                 if sid in DEATH) / tot_s * DEATH_LANDS * (sum(hp_m) / len(hp_m) if hp_m else 0)
            threat += d_round
            threat_spell += d_round
            threat_death = d_round
        threat_conf = 0.0
        if CONF_THREAT and any(sid in CONFUSE for _, sid in dmg + sts):
            reach_n = {'one': 1, 'group': ROW, 'all': 6}
            tot_s = sum(pr for pr, _ in sts) or 1
            n_conf = (p_dmg * sum(pr / tot * CONFUSE[sid] * reach_n[DAMAGE[sid][1]]
                                  for pr, sid in dmg if sid in CONFUSE)
                      + p[5] * sum(pr / tot_s * CONFUSE[sid] * reach_n[DAMAGE[sid][1]]
                                   for pr, sid in sts if sid in CONFUSE))
            hp_m = [g.char(i)['max_hp'] for i in g.party()]
            threat_conf = n_conf * CONF_LANDS * CONF_HP * (sum(hp_m) / len(hp_m) if hp_m else 0)
        # monster_ai 0x800cffb0: columns 3-4 damage (spell entry 0), 5 status (1), 6 buff
        # (2), 7 heal (3), 8 cure (4); a column it has no spells for falls back to fighting
        has = [any(r[0x8f + sc * 5 + e] != 0xff for sc in range(4)) for e in range(5)]
        cast_share = sum(p[c] for c, e in ((3, 0), (4, 0), (5, 1), (6, 2), (7, 3), (8, 4)) if has[e])
        # column 1 fights the reachable member with the least HP: that part lands on one
        # member, the weakest (front row: any attack; back row: reach attacks only)
        reach_round = sum(reach) / len(reach) * 0.5 if reach else 0
        focus = (p[1] * melee_round, p[1] * reach_round)
        dsrc = disable_sources(g, k, r, p_fight, p[5] if sts else 0.0, sts)
        # (agent 16) each damage spell's casts a round per monster, for battle.para_rush
        dcast = [(p_dmg * pr / tot, sid) for pr, sid in dmg if sid in DAMAGE]
        fight_p = p_fight
        # (casterfocus) its status column's spells and that column's chance a round, for
        # caster_danger's debuffs; and every spell it casts, abilities included
        p_status = p[5] if sts else 0.0
        spells = {sid for _, sid in dmg + sts} | {src[1] for _, src, _ in dsrc if src[0] == 'spell'}
    else:
        threat_drain = threat_conf = 0.0
        dsrc, dcast, fight_p = [], [], 1.0
        sts, p_status, spells = [], 0.0, set()
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
                threat_death=threat_death, threat_drain=threat_drain, threat_conf=threat_conf,
                blow=(blow_f, blow_b), death=death, dsrc=dsrc, dcast=dcast, fight_p=fight_p, dis_hp=0.0, dis_hp_spell=0.0,
                para=para_caster(dsrc, dmg + sts if SPELLS_ON else []),
                gdmg=any(sid in DAMAGE and DAMAGE[sid][1] != 'one' for _, sid in (dmg if SPELLS_ON else [])),
                silenced=silenced(g, k), sts=sts, p_status=p_status, spells=spells,
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


def status_lands(raw, mlv, sid, clevel, tbl, screen):
    """The chance a monster's status spell sid (DIS_SPELL) cast at level clevel takes a
    member (roster raw, level mlv): past magic resistance and the magic screen, then the save
    (status_spell 0x800b173c, see above). tbl: EFFECT_RES read; screen: battle_groups +7."""
    kind, ki, base, rbit, rows = DIS_SPELL[sid]
    mr = raw[0x87 + school(sid)] + screen
    land = max(0.0, 1 - min(255, mr + 1) / 100)
    save = 85 if struct.unpack_from('<H', raw, 0xae)[0] & rbit else base
    if ki < 3:
        save += raw[0xb0 + tbl[ki]]
    save += 4 * max(0, mlv - clevel)
    return land * (1 - min(100, max(5, save)) / 100)


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
        M[k]['dis_hp'] = M[k]['dis_hp_spell'] = M[k]['dis_hp_cast'] = 0.0
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
                    p = status_lands(raw, mlv, sid, m['level'], tbl, screen)
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
                if src[0] == 'spell':
                    m['dis_hp_cast'] += hp_          # (casterfocus) spells and spell abilities
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
    return sum(member_melee(g, slot, k, M) for slot in range(6))


def member_melee(g, slot, k, M=None, dmod=0):
    """One member's part of melee_on: its expected melee damage a round on group k, 0 when
    it can't act or its weapon doesn't reach k. With M, only when k is also the lowest group
    its weapon reaches (melee_on's rule); without, any group it reaches (casterfocus).
    dmod: added to the group's AC modifier (support: what a Morlis or Dilto stack would do)."""
    ri = struct.unpack('<b', g.e.read(PARTY + slot, 1))[0]
    if ri < 0:
        return 0.0
    c = g.e.read(COMBAT + slot * 0xe, 0xe)
    if struct.unpack_from('<H', c, 0xc)[0] >= 8:
        return 0.0
    d = rec(g, k)
    ac = struct.unpack_from('<b', d, 0x7a)[0]
    mons = standing(g, k)
    acmod = struct.unpack('<b', g.e.read(COMBAT + k * 0x7e + mons[0][0] * 0xe + 4, 1))[0] if mons else 0
    b = g.u8(OSLO)
    r = g.e.read(ROSTER + ri * ROSTER_LEN, ROSTER_LEN)
    items = struct.unpack_from('<10H', r, 0x20)
    main = any(x != 0xffff and x & 0x1000 for x in items)
    second = any(x != 0xffff and not x & 0x1000 and x & 0x800 for x in items)
    hit = struct.unpack_from('<h', r, 0x84)[0]
    tot = 0.0
    for hand, used in ((0, main or not second), (1, second)):
        if not used:
            continue
        reach = weapon_reach(g, r[0x9c + hand], slot)
        if k > reach or M is not None and k != min(x for x in M if x <= reach):
            continue
        T = min(19, 19 + k - ac + acmod + dmod - hit) - b
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
    and the actions it takes away (disable(): dis_hp, 0 until it has run); its death
    spells DEATH_EXTRA times again, for the dead member's turns (bossfight)."""
    return (m['threat'] + m.get('dis_hp', 0.0) + DEATH_EXTRA * m.get('threat_death', 0.0)
            + m.get('threat_conf', 0.0))


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
PLAN = dict(round=None, dmg={}, dis={}, screen=None, seal={})


def plan_reset(rnd):
    if PLAN['round'] != rnd:
        PLAN.update(round=rnd, dmg={}, dis={}, screen=None, seal={})
    focus_reset(rnd)


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
                sil = SILENCE_PLAN and SPECIAL[0] and SPELLS_ON
                if not m['caster'] or not sil and cast_counts.get((SILENCE, t), 0) >= 2:
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
                worth = max(worth, (m.get('threat_spell', 0) + m.get('dis_hp_spell', 0)
                                    + m.get('threat_conf', 0)) * n)
                if sil:
                    # (silence) in a special fight: what its spells would cost the party
                    # past the magic screen (spell_hp), recast once it wears off
                    worth = max(8 * m['level'] * n * m.get('cast_share', 1.0), silence_worth(g, m) * n)
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


# Silencing in the support plan (Chris, 2026-10-16: against caster-heavy parties; ch17
# report 5, from Area E's type-2 parties, 455-540 a round, nearly all of it spells). In a
# special fight (battle.default_policy's 'special': a story or boss fight, or a likely
# loss; SPECIAL) silencing a group is worth the part of the party's expected damage that
# comes from its spells, for as long as the silence holds, at the chance it lands:
#   - spell_hp: one monster's spells a round, everything silence or a seal stops: damage
#     and death (info threat_spell), death counted again as casting_danger counts it, the
#     members its sleep and silence spells take out (disable dis_hp_spell; abilities are
#     never silenced), its debuffs (DEBUFF_HP) and Labadi (threat_drain), cut by the
#     party's magic screen with this round's Cortus counted (the share that wouldn't land
#     anyway; Cortu's own value already takes silenced monsters out, and in a special fight
#     the ones this round's casts are likely to silence, put to sleep or paralyze too);
#   - Montino (value()): each monster it catches (school resistance, magic screen, save
#     50) times spell_hp times silence_rounds, recast once it wears off (no two-a-group cap
#     in a special fight);
#   - Bacortu (seal_value, Mage 5): each cast adds the caster's level to the target group's
#     sealing level s (battle_groups +6, up to 255; spell_bacortu 0x800c9e2c, with no
#     resistance check: spell_dispatch calls it straight), and a sealed monster's spell is
#     lost when rand(8191) < s x (its level + s + 1) (cast_spell 0x800abcc0, D-battle.md
#     "Casting"); s of 3 or more drops 1-3 a round. One level-17 cast at a level-13 monster
#     stops 6% of its spells, four about 70%, so a cast is valued as its share of the best
#     stack of up to SEAL_STACK casts over SEAL_ROUNDS rounds, as the AC stack is shared
#     over its points. In a fixed battle the pick stores a row (1 front, 2 back) as the
#     target; the original game sealed group 1 or 2 whatever was aimed at (seen in
#     ch17/ffr/silence/seal_trace.py), and since bugfix_bacortu_rows.asm the cast seals
#     every group in the row, each by the caster's level (seal_groups; pick.py's rows).
# SILENCE_FIRST (test): with most of the danger (SILENCE_FIRST_SHARE) in one or two groups'
# spells, Montino at those groups goes ahead of the member's other turns but a finisher.
# Bench (ch17 report 5, four Area E type-2 starts x seeds 1-20, flag off and on): no change
# in wins, escapes or wipes (on: 19 / 42 / 19 both), Montino 10 -> 13 casts; SILENCE_FIRST
# 19 / 42 / 19 with 114 deaths against 112. Their groups are single monsters, a Cortu
# outweighs a Montino there, and a silencer dies in the free round after the failed run in
# 18 of 38 fights. Off until a fight shows it helps (groups of several casters).
SILENCE_PLAN = False
SPECIAL = [False]           # battle.default_policy: this decision is in a special fight
SILENCE_FIRST = False
SILENCE_FIRST_SHARE = 0.6
BACORTU = 14
SEAL_ROUNDS = 3
SEAL_STACK = 4


def spell_hp(m):
    """Hit points a round one of group m's monsters costs the party by its spells, everything
    silence or a seal would stop (see above), before the magic screen."""
    sts = m.get('sts', [])
    tot = sum(pr for pr, _ in sts) or 1
    deb = m.get('p_status', 0.0) * sum(pr / tot * DEBUFF_HP[sid] for pr, sid in sts if sid in DEBUFF_HP)
    return (m.get('threat_spell', 0.0) + m.get('dis_hp_spell', 0.0) + deb
            + DEATH_EXTRA * m.get('threat_death', 0.0) + m.get('threat_drain', 0.0)
            + m.get('threat_conf', 0.0))


def silence_worth(g, m):
    """spell_hp past the party's magic screen (this round's Cortus counted)."""
    return spell_hp(m) * (1 - min(SCREEN_CAP, screen_now(g)) / 100)


def silence_targets(g, M):
    """(SILENCE_FIRST) The one or two groups whose spells carry SILENCE_FIRST_SHARE or more
    of the danger present (danger_of plus Labadi, monsters that can cast now), or []."""
    tot = sum((danger_of(m) + m.get('threat_drain', 0.0)) * len(m['mons']) for m in M.values())
    sh = []
    for k, m in M.items():
        act = [j for j, _, st in m['mons'] if st < 8 and j not in m.get('silenced', ())]
        if act and m['caster']:
            sh.append((spell_hp(m) * len(act), k))
    sh.sort(reverse=True)
    for n in (1, 2):
        if tot > 0 and sum(x for x, _ in sh[:n]) >= SILENCE_FIRST_SHARE * tot:
            return [k for _, k in sh[:n]]
    return []


def p_sealed(s, mlevel):
    """The chance a monster of level mlevel loses a spell to sealing level s (cast_spell)."""
    return min(1.0, s * (mlevel + s + 1) / 8191) if s > 0 else 0.0


def seal_after(s, r):
    """Sealing level s after r rounds of counters_tick (3 or more: 1-3 off, else 1)."""
    for _ in range(r):
        s = max(0, s - (2 if s >= 3 else 1))
    return s


FRONT_N, BACK_N = 0x800796d3, 0x8007967c     # fixed battle: groups in the front and back rows (s8; pick.py)


def seal_groups(g, k, M):
    """The groups the party's Bacortu aimed at group k seals (see above): k in a random
    battle; in a fixed one every group of k's row (row 2 while both rows stand)."""
    if not g.u8(FIXED):
        return [k]
    front = struct.unpack('<b', g.e.read(FRONT_N, 1))[0]
    back = struct.unpack('<b', g.e.read(BACK_N, 1))[0]
    row = lambda j: 2 if front > 0 and back >= 1 and j > front else 1
    return [j for j in M if row(j) == row(k)] or [k]


def seal_value(g, k, M, clevel, rounds=None):
    """(silence) Bacortu sealing group k (one of seal_groups) now, in hit points
    (see above), after this round's casts planned (PLAN seal)."""
    if k not in M:
        return 0.0
    m = M[k]
    act = [j for j, _, st in m['mons'] if st < 8 and j not in m.get('silenced', ())]
    if not act or not m['caster']:
        return 0.0
    s0 = min(255, g.u8(GROUPS + k * 8 + 6) + PLAN['seal'].get(k, 0.0))
    add = clevel
    R = int(round(rounds if rounds else SEAL_ROUNDS))
    base = [p_sealed(seal_after(s0, r), m['level']) for r in range(R)]
    best = 0.0
    for n in range(1, SEAL_STACK + 1):
        s1 = min(255, s0 + n * add)
        gain = sum(p_sealed(seal_after(s1, r), m['level']) - b for r, b in enumerate(base))
        best = max(best, gain / n)
    return best * silence_worth(g, m) * len(act)


def seal_commit(g, k, M, clevel):
    PLAN['seal'][k] = PLAN['seal'].get(k, 0.0) + clevel


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
    if sid == CORTU and CORTU_SCREEN:
        return 0.0                      # cortu_value (battle.default_policy)
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
RANDOM_NOT_STORY = True  # (casterfocus) a fixed grid met as a random encounter isn't a story fight
ENCOUNTER_ID = 0x800797f4   # u16: 0xffff / 0xfffe for a random encounter (battle.fleeable)
TRAINING = False        # chapters.train: a training trip, home walk included
# (chapter 16) squares (area, x, y) whose event starts a boss fight from the dispatcher
# (fight types like 0xd Mother, 0x13 the Crystal Men): those come with FIXED 0, so they
# were rated as any fight ('above median level', no Bamatu or Maporfic: c16v1a wiped three
# times). Chapters add their altars.
BOSS_AT = set()


def at_boss(g):
    """The party stands on a chapter's boss square (BOSS_AT)."""
    if not BOSS_AT:
        return False
    from harness import maze
    return (g.u8(maze.AREA),) + tuple(g.pos()) in BOSS_AT


def story_fight(g):
    """A fixed fight met outside a training trip and off the floor's fight squares (the
    site's event type 0x14): a story or boss fight. Chris, 2026-10-14: the training
    floors' fixed fights aren't bosses. Area B's human parties come on fixed grids both
    on the squares and as roamers between them (smoke1: B4 (13, 16), not a square), so a
    training trip's fixed fights never count."""
    if BOSS_AT:
        from harness import maze
        if (g.u8(maze.AREA),) + tuple(g.pos()) in BOSS_AT:
            return True
    if not g.u8(FIXED):
        return False
    if RANDOM_NOT_STORY and (struct.unpack('<H', g.e.read(ENCOUNTER_ID, 2))[0] + 2) & 0xffff < 2:
        # (casterfocus) a fixed grid met as a random encounter (encounter_id 0xffff or 0xfffe,
        # the ones a party can run from; battle.fleeable) isn't a story fight: Area B's
        # human parties (0xfffe) were rated 'story', so the walk out and home ran from them
        # at round 1 and a fight with them opened with Tiltowait, Cortu and Badi
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


# Caster focus (Chris, 2026-10-15, after playing a chapter 9 trip by hand: "The main thing
# is to take out the casters first. They really hurt with sleep, paralysis, debuffs and
# group damage. You don't need to lead with the biggest spells. You need to focus your
# damage on the casters."). A caster group is one whose monsters cast sleep, paralysis,
# silence, confusion, death, a debuff or group damage, or whose spells (and abilities that
# cast a spell) cost the party CASTER_MIN hit points a round or more each (is_caster;
# caster_danger rates them). The party's blows and its damage spells go at the caster groups in
# caster_order, the most dangerous first, then the quickest to kill (the fewest hit points
# standing, so a lone caster goes down in one round); battle.choose_group aims the
# fighters, battle.focus_pick the casters: the cheapest damage or death spell likely to
# kill the whole group this round (finish_p). What the members commanded before have
# already put on a group this round (FOCUS) moves the next member on to the next caster
# group once this one is likely dead (dead_p).
CASTER_FOCUS = True
CASTER_MIN = 3.0
# debuffs a monster casts at the party (dim.json): hit points a cast is reckoned to cost,
# roughly 3 an AC point over the rest of the fight. Dilto (5, AC +2), Morlis (6, AC +4
# and fear), Poba (65, +1), Mapoba (70, +2), Nofis (46, magic resistance -5%), Bacortu
# (14, a barrier the party's spells don't get through), Badumas (74, attack down)
DEBUFF_HP = {5: 6, 6: 12, 65: 3, 70: 6, 46: 3, 14: 6, 74: 6}
# the spells that make a group a caster group whatever their rated worth (the brief: sleep,
# paralysis, silence and other disabling spells, debuffs, group damage): Katino,
# Katiqurea, Montino, Lorks, Galtomas, the confusing Sios/Lios/Masios/Lasios, the death
# spells and Labadi, and DEBUFF_HP's; group damage by info's gdmg
CASTER_SPELLS = {0, 49, 25, 69, 81, 82, 63, 66, 72, 34, 40, 37, 59} | set(DEBUFF_HP)
CLOUDS = {45, 48, 51, 54, 57, 62}      # DAMAGE counts their three rounds; a third lands this round
FINISH_P = 0.5          # a spell "likely to finish" a group: every monster in it dies this round at this chance
DONE_P = 0.75           # a group the members before have likely killed this round
FOCUS = dict(round=None, dmg={}, spell={})      # this round: group -> melee expected, -> spells' kill chances


def focus_reset(rnd):
    if FOCUS['round'] != rnd:
        FOCUS.update(round=rnd, dmg={}, spell={})


def caster_danger(m):
    """Hit points a round one of group m's monsters costs the party by casting: its damage
    and death spells (info threat_spell), the members its sleep, paralysis and silence
    spells and spell abilities take out of the fight (disable() dis_hp_cast; 0 until
    disable has run on M), its debuffs (DEBUFF_HP, at its AI row's status-column
    chance), and the members it confuses (threat_conf)."""
    sts = m.get('sts', [])
    tot = sum(pr for pr, _ in sts) or 1
    deb = m.get('p_status', 0.0) * sum(pr / tot * DEBUFF_HP[sid] for pr, sid in sts if sid in DEBUFF_HP)
    return m.get('threat_spell', 0.0) + m.get('dis_hp_cast', 0.0) + deb + m.get('threat_conf', 0.0)


def is_caster(m):
    """Group m is a caster group: it casts one of CASTER_SPELLS (abilities included), group
    damage or paralysis, or its spells are worth CASTER_MIN a round anyway (a Dalosto)."""
    return bool(m.get('spells', set()) & CASTER_SPELLS or m.get('gdmg') or m.get('para')
                or caster_danger(m) >= CASTER_MIN)


def group_hp(m):
    return sum(max(0, hp) for _, hp, _ in m['mons'])


def caster_order(M, kill_first=None, skip_done=False):
    """The caster groups present, first to kill first: kill-first monsters (kill_rank:
    battle.KILL_FIRST by id, or by what they cast), then by danger (caster_danger of the
    monsters that can cast now: asleep, paralyzed or silenced ones count 0.3, they come
    back), in bands of a factor of two so near-equal casters tie, then the fewest hit
    points standing. skip_done: leave out groups the members commanded before have likely
    killed this round (dead_p)."""
    out = []
    for k, m in M.items():
        if not m['mons']:
            continue
        kf = kill_rank(m, kill_first)
        d = caster_danger(m)
        if kf == 9 and not is_caster(m):
            continue
        if skip_done and dead_p(k, m) >= DONE_P:
            continue
        act = sum(1.0 if st < 8 and j not in m.get('silenced', ()) else 0.3 for j, _, st in m['mons'])
        de = d * act / len(m['mons'])
        band = int(math.log2(de)) if de >= 1 else 0
        out.append(((kf, -band, group_hp(m), k), k))
    return [k for _, k in sorted(out)]


def dead_p(k, m):
    """The chance group k is dead by the end of this round from what the members commanded
    before put on it (FOCUS): melee counted as half a kill at the group's hit points and a
    sure one at 1.5 times them, each spell at its finish_p."""
    hp = group_hp(m)
    if hp <= 0:
        return 1.0
    x = FOCUS['dmg'].get(k, 0.0)
    q = 1 - min(1.0, max(0.0, x / hp - 0.5))
    for p in FOCUS['spell'].get(k, []):
        q *= 1 - p
    return 1 - q


def death_p(m, sid, clevel):
    """The chance a death spell sid kills one of group m's monsters (value()'s rules)."""
    kind, base = DEATH[sid]
    if sid == 15:
        return lands(m, sid) if m['flags'] & UNDEAD else 0.0
    if sid == 38:
        return lands(m, sid) * (1 - save_adj(base, m['level'], clevel)) if m['flags'] & SUMMONED else 0.0
    if sid == 59:
        return 0.0 if m['flags'] & UNDEAD or m['level'] > 8 else 1.0
    if m['flags'] & DEATH_IMMUNE:
        return 0.0
    return lands(m, sid) * (1 - save_adj(base, m['level'], clevel))


def finish_p(sid, m, clevel):
    """The chance sid cast at group m (or reaching it) kills every monster standing in it
    this round: for damage, each monster's chance it lands times value()'s kill rule (a
    kill at the monster's HP, half one at 70% of it; a cloud's first round only); a
    one-target spell only finishes a group of one."""
    mons = m['mons']
    if not mons:
        return 0.0
    if sid in DAMAGE:
        mean, kind, el = DAMAGE[sid]
        if kind == 'one' and len(mons) > 1:
            return 0.0
        f = 0.5 if m['resist'] & el and el else 2.0 if m['weak'] & el and el else 1.0
        d = mean * f / (3 if sid in CLOUDS else 1)
        p = 1.0
        for _, hp, _ in mons:
            p *= lands(m, sid) * (1.0 if d >= hp else 0.5 if d >= hp * 0.7 else 0.0)
        return p
    if sid in DEATH:
        if DEATH[sid][0] == 'one' and len(mons) > 1:
            return 0.0
        return death_p(m, sid, clevel) ** len(mons)
    return 0.0


def focus_commit(g, sid, k, M, clevel):
    """Put a cast of sid at group k on this round's FOCUS: its finish_p on each group it
    reaches."""
    if sid in DAMAGE or sid in DEATH:
        kind = DAMAGE[sid][1] if sid in DAMAGE else DEATH[sid][0]
        for t in targets(g, k, kind, M):
            FOCUS['spell'].setdefault(t, []).append(finish_p(sid, M[t], clevel))


# Dangerous casters by what they cast (bossfight, 2026-10-15). battle.KILL_FIRST names
# chapter 4's and chapter 10's Guardians by id; chapter 13's (Arch Mages 456, Arch Priests
# 440, Arch Lords 473 at Area C B4 E5 N11) weren't on it. kill_rank gives any group the
# same first places from its record: 0 for a monster that, at KILL_RANK_P a round or more,
# casts party-wide damage of Tiltowait's class (mean x members reached >= HEAVY_DMG:
# Tiltowait, Lasios, Galtomas, Ladalto), group death (Bakadi) or sleep on everyone
# (Katiqurea); 1 for Badi (death to one) at that chance; else 9, and caster_order's danger
# bands decide. The chapter 13 Arch Lords cast Badi and Bakadi 5% of their rounds and stay
# at 9.
KILL_RANK_BY_SPELLS = True
KILL_RANK_P = 0.1
HEAVY_DMG = 150
RANK_STATUS = {40: 0, 49: 0, 34: 1}


def spell_rank(sid):
    """kill_rank's place for a monster's spell sid, or 9."""
    if sid in DAMAGE:
        mean, kind, _ = DAMAGE[sid]
        if kind != 'one' and mean * (6 if kind == 'all' else ROW) >= HEAVY_DMG:
            return 0
        return 9
    return RANK_STATUS.get(sid, 9)


def kill_rank(m, kill_first=None):
    """Group m's place to kill or silence first: kill_first's (battle.KILL_FIRST by monster
    id) where it has one, else by its spells and how often it casts them (see above)."""
    kf = kill_first.get(m['id'], 9) if kill_first else 9
    if not KILL_RANK_BY_SPELLS or not SPELLS_ON:
        return kf
    p = {}
    for pr, sid in m.get('dcast', []):
        p[sid] = p.get(sid, 0.0) + pr
    sts = m.get('sts', [])
    tot = sum(pr for pr, _ in sts) or 1
    for pr, sid in sts:
        p[sid] = p.get(sid, 0.0) + m.get('p_status', 0.0) * pr / tot
    for sid, x in p.items():
        if x >= KILL_RANK_P:
            kf = min(kf, spell_rank(sid))
    return kf


# Cortu by what it adds (bossfight, 2026-10-15). Cortu sets the party's magic screen
# (battle_groups +7, group 0) to 3/4 of what it was + 2 x the caster's level, up to 90
# (D-battle.md), and every hostile spell, death spells included, is shrugged off at
# the target's resistance + that screen + 1 in 100. Above 10 the screen drops 5-10 a
# round (counters_tick). So a cast is worth the points of screen it adds, as the share
# of the casters' damage and death a round that stops landing, for CORTU_ROUNDS rounds;
# nothing once the screen is near 90 or the casters are down or silenced. The winning
# chains at chapter 13's Guardians kept a level-18 mage casting it every round.
CORTU_SCREEN = True
CORTU_ROUNDS = 3.0
SCREEN_CAP = 90
PARTY_SCREEN = GROUPS + 7


def screen_now(g):
    """The party's magic screen with this round's Cortu casts already chosen (PLAN)."""
    s = PLAN.get('screen')
    return g.u8(PARTY_SCREEN) if s is None else s


def casting_danger(M, drain=False, planned=False):
    """Hit points a round the monsters' spells cost the party, from the monsters that can
    cast now (not asleep, paralyzed or silenced): caster_danger each, with its death
    spells' part counted 1 + DEATH_EXTRA times: a member killed loses their turns for the
    rest of the fight as well as their hit points. planned: (silence) less the share this
    round's casts are likely to silence, put to sleep or paralyze (PLAN dis)."""
    t = 0.0
    for k, m in M.items():
        act = [j for j, _, st in m['mons'] if st < 8 and j not in m.get('silenced', ())]
        t += (caster_danger(m) + DEATH_EXTRA * m.get('threat_death', 0.0)
              + (m.get('threat_drain', 0.0) if drain else 0.0)) * len(act) * (
                  1 - PLAN['dis'].get(k, 0.0) if planned else 1.0)
    return t


def cortu_value(g, M, clevel, rounds=None, drain=False, planned=False):
    """rounds: the rounds the screen is counted over (CORTU_ROUNDS; battle's support plan
    passes the fight's expected length, since the screen lasts the fight); drain: Labadi
    counts (casting_danger); planned: this round's disabling casts count (casting_danger)."""
    s = screen_now(g)
    gain = min(SCREEN_CAP, 0.75 * s + 2 * clevel) - s
    if gain <= 0:
        return 0.0
    return gain / 100 * casting_danger(M, drain, planned) * (CORTU_ROUNDS if rounds is None else rounds)


def melee_in(g, M, pmod=None, mapo=None):
    """(support) The monsters' expected melee damage on the party a round (monster_melee
    0x800aaa04, D-battle.md "Melee: monsters attack"): for each monster that can act, its
    fight share (info fight_p) x each attack's use (attack 1 69% / attack 2 31% when it has
    one, attack 3 always, 2 harder) x swings (at most 11) x the chance a swing hits x the
    dice mean, spread evenly over the members it reaches (the front row, or everyone with
    the reach bit; groups 3-4 of a random fight without reach don't melee). The chance:
    T = 22 + Maporfic 2 - AC + AC modifier - (level / 2 + 1), 1..19, hits on rand(20) >= T.
    pmod: {slot: extra AC modifier} (Bamatu +3 each, Porfic +4 the caster); mapo: Maporfic
    on (True) or off, else as it is."""
    pmod = pmod or {}
    on = (g.u8(0x8007e82a) != 0) if mapo is None else mapo
    tgt = []
    for slot in range(6):
        ri = struct.unpack('<b', g.e.read(PARTY + slot, 1))[0]
        if ri < 0:
            continue
        c = g.e.read(COMBAT + slot * 0xe, 0xe)
        hp, st = struct.unpack_from('<h', c, 6)[0], struct.unpack_from('<H', c, 0xc)[0]
        if hp <= 0 or st >= 0x80:
            continue
        r = g.e.read(ROSTER + ri * ROSTER_LEN, ROSTER_LEN)
        ac = struct.unpack_from('<b', r, 0x86)[0] - struct.unpack_from('<b', c, 4)[0] - pmod.get(slot, 0)
        tgt.append((slot, ac))
    front = [x for x in tgt if x[0] < 3] or tgt
    tot = 0.0
    for k, m in M.items():
        r = rec(g, k)
        n = len([j for j, _, st in m['mons'] if st < 8])
        if not n:
            continue
        atk = [r[o:o + 10] for o in (0xac, 0xb6, 0xc0)]
        nouns = [struct.unpack_from('<H', a, 0)[0] for a in atk]
        ability = [0x100 <= x < 1621 for x in nouns]
        reach_any = bool((atk[0][7] | atk[1][7]) & BACK_REACH)
        if k > 2 and not g.u8(FIXED) and not reach_any:
            continue
        use1 = ability[1] or (nouns[1] < 0xff or nouns[1] >= 0x8000) and atk[1][3] > 0
        for i, u in ((0, 0.69 if use1 else 1.0), (1, 0.31 if use1 else 0.0), (2, 1.0 if atk[2][3] else 0.0)):
            a = atk[i]
            if not u or ability[i] or not a[3] or not a[4]:
                continue
            reach = tgt if a[7] & BACK_REACH else front
            if not reach:
                continue
            dice = a[4] * (a[5] + 1) / 2 + a[6]
            for slot, ac in reach:
                T = 22 + (2 if on else 0) - ac - (m['level'] // 2 + 1)
                T = min(19, max(1, T + (2 if i == 2 and T < 18 else 0)))
                tot += n * m['fight_p'] * u * min(11, a[3]) * (20 - T) / 20 * dice / len(reach)
    return tot


def cortu_commit(g, clevel):
    s = screen_now(g)
    PLAN['screen'] = min(SCREEN_CAP, 0.75 * s + 2 * clevel)


def incoming(g, M, party):
    """{slot: hit points member slot is expected to lose this round}: the monsters' spells
    (damage and death, info threat_spell) spread over the standing members and cut by the
    party's magic screen, their blows and breath (the rest of info threat) over the front
    row. party: [(slot, hp, max)]."""
    up = [s for s, hp, _ in party if hp > 0]
    if not up:
        return {}
    front = [s for s in up if s < 3] or up
    cut = 1 - min(SCREEN_CAP, screen_now(g)) / 100
    sp = ml = 0.0
    for m in M.values():
        act = [j for j, _, st in m['mons'] if st < 8]
        cast = [j for j in act if j not in m.get('silenced', ())]
        sp += m['threat_spell'] * len(cast)
        ml += (m['threat'] - m['threat_spell']) * len(act)
    return {s: sp * cut / len(up) + (ml / len(front) if s in front else 0.0) for s in up}
