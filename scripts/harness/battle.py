"""Battle: the command phase driven from RAM, a simple rule policy, and the narration
advanced as fast as the game takes it.

RAM (BATTLE resident; docs/re/D-battle.md, and probe.py on the harness disc 2026-10-12):
  0x800796fa battle_phase: 0x1c the party's commands, 0x3e the end
  0x80079786 the member being commanded; 0x80079b15 command level (1 a member's menu,
             2 or 0 between members)
  0x800796e0 the menu screen: 9 the command list, 49 the spell grid (rows school,
             columns level), 50 the level's spell list, 51 "Cast it on whom?" (party grid),
             5 the members overview, 32 "Is this all right?", 6 its Yes/No; 4, 8, 16 are transitions,
             and a press made during one is read by the screen that follows
  0x800797a8 the command list on screen, ids 1 Fight 2 Parry 3 Spell 4 Dispel 5 Use
             6 Run 7 Ambush 8 Hide 9 Breath (STATUS 404 + id), 0 ends it
  0x80079b95 list cursor (commands, spell school row, spell list); 0x80079b8c spell level
  0x80079c58 / 0x80079c5a the party-grid cursor x / y (3 by 2)
  0x8008e230 combatants: 14 bytes each, group g at +g*0x7e; +6 HP, +0xa action,
             +0xb target, +0xc status
  0x8008c480 battle_groups: 8 bytes per group, +4 count, +5 standing
  0x8007e812 the party's roster indices
"""
import random, struct
from harness import ui, pick, tactics
from harness.game import Stuck

PHASE = 0x800796fa
MEMBER = 0x80079786
LEVEL = 0x80079b15
SCREEN = 0x800796e0
OPTS = 0x800797a8
LIST = 0x80079b95
COL = 0x80079b8c
PGRID_X, PGRID_Y = 0x80079c58, 0x80079c5a
COMBAT = 0x8008e230
GROUPS = 0x8008c480
PARTY_IDS = 0x8007e812
CMD_PHASE = 0x1c
WAITING = (5, 6, 32)   # SCREEN values that wait for a press: overview, "Is this all right?", its Yes/No
TRANSIENT = (4, 8, 16)
FIGHT, PARRY, SPELL, DISPEL, USE, RUN, AMBUSH, HIDE, BREATH = range(1, 10)

GROUP_DAMAGE = [3, 7, 10, 13, 16, 20, 45, 48, 51, 54, 57, 62, 66, 72, 80, 81, 82]
ONE_DAMAGE = [1, 9, 17, 22, 60, 63, 77]
HEAL_ONE = [64, 21, 30, 33, 36, 58]     # weakest first (Diomas, Dios, Dial, Dialma, Madi, Kadios)
# mean HP healed in battle (D-battle.md "Healing and buffs": Dios 2d4, Dial 2d8, Dialma
# 3d8, Diomas 3d2; Madi and Kadios to full)
HEAL_MEAN = {64: 4.5, 21: 5, 30: 9, 33: 13.5, 36: 999, 58: 999}
HEAL_RISK = False       # (d) heal a member who couldn't survive another hit
TRIP_BLOW = [0.0, 0.0]  # the worst one-action damage seen this trip, front and back row (chapters.train)
KEEP_LEVEL = 6         # (c) spell levels kept for story/boss fights and fights going badly
CHEAPEST = False        # (c) in a fight that matters, the cheapest spell that does most of the job
CHEAP_SHARE = 0.6      # ... "most": this share of the best candidate's value
PLANNING = False        # a later caster in a round sees what the earlier ones' spells will likely do
# attack spells: id -> (mean damage per target, 'one' | 'group' | 'all'), from the site's
# data/chara/spells/dim.json (clouds count their three rounds)
SPELL_DAMAGE = {
    1: (4.5, 'one'), 3: (4.5, 'group'), 7: (14, 'group'), 9: (41, 'one'), 10: (32, 'group'),
    13: (36, 'group'), 16: (71, 'group'), 17: (72, 'one'), 20: (80, 'all'),
    22: (4.5, 'one'), 45: (7.5, 'group'), 48: (15, 'group'), 51: (22.5, 'group'),
    54: (36, 'group'), 57: (67.5, 'group'), 60: (105, 'one'), 62: (96, 'group'),
    63: (5.5, 'one'), 66: (6, 'group'), 72: (9, 'group'), 77: (50, 'one'), 80: (36, 'group'),
    34: (40, 'one'), 40: (40, 'group'),      # Badi, Bakadi: death (not the undead)
    81: (30, 'all'), 82: (40, 'all'),
}
SPELL_NAME = {}
# spells the battle's spell list never shows (no battle-use flag): they don't count for
# the list index (rips/re/work/grouppick/README.md: the priest's level 2 list showed only
# Montino, so 62 sat one lower than castable() counted when 61 was known)
NOT_IN_BATTLE = {2, 11, 24, 26, 39, 61, 67, 68, 78, 83}
FIXED = 0x80079bde          # 1 in a fixed battle (up to 6 groups on a 3x2 grid)
# monsters to kill first, by battle_groups +2 id: lower goes first. Walkthrough chapter 4
# (04-lake-machine.json): at the Guardians "Kill the mage first" (Madalto over the whole
# party for up to 64), and the priest's Badi kills a character outright.
KILL_FIRST = {366: 0, 358: 1,       # Arch Mage, Arch Priest (Underground B2 E7 N22)
              454: 0, 438: 1}       # the same pair at Area A B1 E16 N11
# against a kill-first monster: Montino (25, silence a group; in a fixed battle it takes
# the row, so at the Guardians it reaches the Arch Priest and the Arch Mage both) up to
# MONTINO_TRIES times a battle, then Badi (34, death to one). The B2 Arch Mage shrugs off
# mage spells 60% of the time but priest spells only 20% (data/monsters/dim/ps.json,
# P34-2).
MONTINO, BADI, BAKADI, CORTU = 25, 34, 40, 8
MONTINO_TRIES = 2
CORTU_TRIES = 2     # Cortu (8): a barrier against enemy spells and breath; it stacks
CAST = {}          # this battle's casts by spell id (fight() clears it)
# this battle's record for the trip logs (Chris, 2026-10-14): did it count as a fight that
# matters (tactics.matters, or losing) at any command phase, and each cast as
# (member name, spell id, school, level)
FIGHT_INFO = dict(matters=False, casts=[])
# VARY > 0: a goal's retry (chapter1.Run.goal sets it to the try number - 1). The game's
# rolls don't move with time, only with what's done, so a retry has to choose
# differently or it replays the same fight: then a fighter may take another group on
# offer and a caster the next-best spell, at random from a seed of VARY.
VARY = 0
VARY_P = 0.3
_vrng = random.Random(0)


def _vary():
    return VARY > 0 and _vrng.random() < VARY_P


def in_battle(g):
    return g.overlay() == 'BATTLE'


def party_ids(g):
    """Roster index per combatant slot 0-5 (None for an empty slot)."""
    return g.party_slots()


def member_state(g, m):
    c = COMBAT + m * 0xe
    hp = struct.unpack('<h', g.e.read(c + 6, 2))[0]
    st = struct.unpack('<H', g.e.read(c + 0xc, 2))[0]
    return hp, st


def max_group(g):
    # random fights have up to 4 groups; a fixed one up to 6 (the Guardians have 5, and
    # the Arch Mage, group 5, went uncounted before)
    return 6 if g.u8(FIXED) else 4


def monsters_standing(g):
    return sum(g.u8(GROUPS + k * 8 + 5) for k in range(1, max_group(g) + 1))


def groups_alive(g):
    return [k for k in range(1, max_group(g) + 1) if g.u8(GROUPS + k * 8 + 5)]


def group_id(g, k):
    return struct.unpack('<H', g.e.read(GROUPS + k * 8 + 2, 2))[0]


def choose_group(g, offered, prefer=None, spread=False):
    """The group to aim at, among the groups the pick offers: a kill-first monster, then
    the policy's choice, then (group spells) the most monsters standing, then the lowest
    number, so the party's blows stay on one group. Groups reorder between rounds, so
    this goes by what stands now."""
    alive = [k for k in offered if g.u8(GROUPS + k * 8 + 5)] or list(offered)
    if not alive:
        return None
    if len(alive) > 1 and _vary():
        return _vrng.choice(alive)
    if prefer in alive:
        return prefer               # a spell's or Dispel's chosen group (tactics.py)
    return min(alive, key=lambda k: (KILL_FIRST.get(group_id(g, k), 9), k != prefer,
                                     -g.u8(GROUPS + k * 8 + 5) if spread else 0, k))


def aim(g, m, prefer, log):
    """At a group pick (Fight, a spell, Dispel...): choose the group and confirm it,
    checked in the member's command record (pick.pick_group). False if it couldn't."""
    try:
        lay = pick.layout(g)
    except pick.PickError:
        return False
    want = choose_group(g, lay['choices'], prefer, spread=lay['screen'] in (0x34, 0x54))
    if want is None:
        return False
    gid = group_id(g, want)
    try:
        r = pick.pick_group(g, want)
    except pick.PickError as e:
        log.append((m, 'aim failed', want, gid, str(e)[:80]))
        return False
    log.append((m, 'aim', want, gid, r['target'], lay['mode']))
    return True


def known_spells(rec, school, level):
    """Spell ids the character knows at school/level, in list order."""
    nib = (rec[0x4c + school * 4 + (level - 1) // 2] >> (4 * ((level - 1) % 2))) & 0xf
    return [school * 21 + (level - 1) * 3 + k for k in range(3) if nib & (1 << k)]


def castable(g, roster_i):
    """[(spell id, school, level, list index)] the character can cast now."""
    rec = g.char(roster_i)['raw']
    out = []
    for school in range(4):
        for level in range(1, 8):
            if rec[0x5c + school * 7 + level - 1] == 0:
                continue
            ks = [s for s in known_spells(rec, school, level) if s not in NOT_IN_BATTLE]
            for i, sid in enumerate(ks):
                out.append((sid, school, level, i))
    return out


MIN_SPELL_VALUE = 8   # expected damage under which a member who can Fight fights instead
RUN_AFTER = 15     # rounds; a battle still going after this many tries to run away
                   # (T3 chapter 2 dev run, 2026-10-13: Fuzzballs on Shrine 3F call for
                   # help every round and the fight never ended in 60,000 frames)
ROUND = 0          # the round being commanded (set by fight)
# Run from a fight that's going badly: someone down or the party under LOSING_HP of its
# hit points, with LOSING_MONSTERS or more standing. Only while training (chapters.train
# sets it), never in the fixed fights a goal needs to win. (r3v3 chapter 3, 2026-10-13:
# Wing Lizards on Underground B3 breathe on everyone and call for help; the party fought
# on and was wiped on six retries running.) Benched 2026-10-14 against judging only the
# fight in progress (5 of 6 trips wiped vs 1 of 6) and against at most 2 runs per fight
# (no better); rips/agents/chapters/bench_run/table.txt.
RUN_WHEN_LOSING = False
LOSING_HP = 0.45
LOSING_MONSTERS = 3


def losing(g):
    down = hp = mx = 0
    for k, rk in enumerate(party_ids(g)):
        if rk is None:
            continue
        h, st = member_state(g, k)
        if st >= 0x20 or h <= 0:
            down += 1
        hp += max(h, 0)
        mx += g.char(rk)['max_hp']
    return (down or (mx and hp < mx * LOSING_HP)) and monsters_standing(g) >= LOSING_MONSTERS


ENCOUNTER_ID = 0x800797f4   # u16: 0xffff / 0xfffe for a random encounter
ALARM_FIGHT = 0x80079784    # set by the alarm chest trap's fight (chest_trap_effect 0x800c7010 case 10)


def fleeable(g):
    """Whether Run can work in this fight. party_commands (BATTLE 0x800cbec8, case 0x60)
    rolls party_flee_roll (0x800d1380) only when ALARM_FIGHT is 0, and the roll fails
    outright unless encounter_id is 0xffff or 0xfffe. A failed run, there or on the roll,
    gives every member nothing for the round (FIGHTMSG 206). FIXED (0x80079bde) is a
    different flag."""
    return (g.u16(ENCOUNTER_ID) + 2) & 0xffff < 2 and not g.u8(ALARM_FIGHT)


FLEE_PENALTY = 0x800da6c8   # BATTLE byte table by map type (party_flee_roll)
MAP_TYPE = 0x8005a824       # map_type_of_area, a byte per area
PARTY_AREA = 0x8007e844
FLEE_RULE = True            # Chris, 2026-10-14: running rare, by the computed chance
RUN_OK = False              # chapters: the walk to the first square, or home with casters spent
FLEE_MIN = 70               # the chance a run needs
MANY = 6                    # standing monsters that make a fight costly without matters()


def flee_chance(g):
    """party_flee_roll's chance (BATTLE 0x800d1380) as a percentage for this round: M = 1 +
    the levels of the monsters that can act (status < 8), P = 1 + the party's; 80, or
    80 + 5 x (P / M) if P >= M (at most 255), minus 2 x flee_penalty[map type of the
    area], and success on rand(100) + 1 < chance, so (chance - 1)%. 0 when it can't be
    fled (fleeable)."""
    if not fleeable(g):
        return 0
    M = 1
    for k in range(1, 5):
        lv = g.u16(tactics.MREC + k * 0xd0 + 0x74)
        for j in range(g.u8(tactics.GROUPS + k * 8 + 5) if g.u8(tactics.GROUPS + k * 8 + 5) < 0x80 else 0):
            if g.u16(0x8008e23c + k * 0x7e + j * 0xe) < 8:
                M += lv
    P = 1
    for i in range(6):
        if g.u8(0x8007e812 + i) != 0xff and g.u16(tactics.COMBAT + i * 14 + 12) < 8:
            P += g.u16(tactics.COMBAT + i * 14)
    c = 80 if P < M else min(255, 80 + 5 * (P // M))
    c = max(0, c - 2 * g.u8(FLEE_PENALTY + g.u8(MAP_TYPE + g.u8(PARTY_AREA))))
    return max(0, min(100, c - 1))


LOSS_RUN = True             # Chris, 2026-10-14: run from a likely loss, round 1 only, anywhere
LOSS_FLEE_ABOVE = 25        # Chris, 2026-10-14: a likely loss runs at a flee chance above this


def _kill(x, hp):
    # tactics.value's kill rule: a sure kill at the monster's HP, half a kill at 70% of it
    return 1.0 if x >= hp else 0.5 if x >= hp * 0.7 else 0.0


def likely_loss(g, M, party_hp):
    """A fight the party expects to lose, judged at round 1 before anyone acts: the rated
    monster damage a round (tactics.info threat, as matters() sums it) is at least the
    party's HP, and is still at least the party's HP after the party's best round. That
    round: each standing member in turn takes what removes the most threat, given what the
    members before it already did: its best damage spell it has points for (tactics.DAMAGE
    mean x the chance it lands, against each target's HP), or, front row (slots 0-2), its
    weapon (gear.wscore, half landing) at group 1; kills by tactics.value's rule (a kill at
    the monster's HP, half a kill at 70% of it). Returns the numbers when it's a likely
    loss, else None."""
    from harness import gear
    T = sum(M[k]['threat'] * len(M[k]['mons']) for k in M)
    if T < party_hp:
        return None
    done = {}                          # (group, monster) -> expected damage so far

    def gain(hits):
        v = 0.0
        for t, j, hp, d in hits:
            x = done.get((t, j), 0.0)
            v += (_kill(x + d, hp) - _kill(x, hp)) * M[t]['threat']
        return v
    for slot, ri in enumerate(party_ids(g)):
        if ri is None:
            continue
        hp, st = member_state(g, slot)
        if hp <= 0 or st >= 0x20:
            continue
        options = []
        for sid, school, level, i in castable(g, ri):
            if sid not in tactics.DAMAGE:
                continue
            mean, kind, el = tactics.DAMAGE[sid]
            for k in M:
                hits = []
                for t in tactics.targets(g, k, kind, M):
                    m = M[t]
                    f = 0.5 if m['resist'] & el and el else 2.0 if m['weak'] & el and el else 1.0
                    mons = m['mons'][:1] if kind == 'one' else m['mons']
                    hits += [(t, j, h, mean * f * tactics.lands(m, sid)) for j, h, _ in mons]
                options.append(hits)
        if slot < 3 and M:
            w = gear.equipped(g, ri).get(0)
            k = min(M)
            j, h, _ = M[k]['mons'][0]
            options.append([(k, j, h, gear.wscore(w) * 0.5 if w else 2.0)])
        if options:
            best = max(options, key=gain)
            for t, j, h, d in best:
                done[(t, j)] = done.get((t, j), 0.0) + d
    killed = sum(_kill(x, h) * M[t]['threat'] for t in M for j, h, _ in M[t]['mons']
                 for x in [done.get((t, j), 0.0)])
    left = T - killed
    if left < party_hp:
        return None
    return dict(threat=round(T), party_hp=party_hp, threat_left=round(left))


def default_policy(g, m, opts):
    """What member m (party slot) does this round. Returns ('fight',), ('parry',),
    ('run',), ('spell', sid, school, level, index, target) with target ('group', g) or
    ('member', slot), or ('first',) to take the first option."""
    if 'first' not in FIGHT_INFO:
        # the rating's inputs at the first command phase (brief item 6), run or not
        ids0 = party_ids(g)
        M0 = {k: tactics.info(g, k) for k in tactics.groups(g)}
        M0 = {k: v for k, v in M0.items() if v['mons']}
        if M0:
            lv0 = sorted(g.char(rk)['level'] for rk in ids0 if rk is not None)
            hp0 = sum(max(member_state(g, k)[0], 0) for k, rk in enumerate(ids0) if rk is not None)
            P0 = [(k, member_state(g, k)[0], g.char(rk)['max_hp']) for k, rk in enumerate(ids0)
                  if rk is not None and member_state(g, k)[1] < 0x20]
            FIGHT_INFO['first'] = tactics.matters_detail(g, M0, hp0, lv0[len(lv0) // 2] if lv0 else None, P0)
            FIGHT_INFO['first']['party_max'] = sum(g.char(rk)['max_hp'] for rk in ids0 if rk is not None)
    if ROUND > RUN_AFTER and RUN in opts and fleeable(g):
        return ('run',)
    if not FLEE_RULE and RUN_WHEN_LOSING and RUN in opts and fleeable(g) and losing(g):
        return ('run',)
    tactics.plan_reset(ROUND)
    ids = party_ids(g)
    ri = ids[m]
    me = g.char(ri)
    cast = castable(g, ri) if SPELL in opts else []
    by_id = {c[0]: c for c in cast}
    M = {k: tactics.info(g, k) for k in tactics.groups(g)}
    M = {k: v for k, v in M.items() if v['mons']}
    party_hp = sum(max(member_state(g, k)[0], 0) for k, rk in enumerate(ids) if rk is not None)
    party = [(k, member_state(g, k)[0], g.char(rk)['max_hp']) for k, rk in enumerate(ids)
             if rk is not None and member_state(g, k)[1] < 0x20]
    for k in M:
        for row in (0, 1):
            TRIP_BLOW[row] = max(TRIP_BLOW[row], M[k]['blow'][row])
    lv = sorted(g.char(rk)['level'] for rk in ids if rk is not None)
    bad = losing(g)
    why = tactics.matters(g, M, party_hp, lv[len(lv) // 2] if lv else None, party)
    big = bool(why) or bad
    FIGHT_INFO['matters'] = FIGHT_INFO['matters'] or bool(big)
    if LOSS_RUN and not FIGHT_INFO.get('loss_checked') and M:
        # anywhere, grinding included: a fight the party expects to lose may be run from,
        # only at the fight's first command (round 1, before the party acts; ROUND can
        # read 2 there when the first command phase is entered twice) and only at
        # a flee chance above LOSS_FLEE_ABOVE (Chris, 2026-10-14; FLEE_MIN stays for the
        # walk out and the walk home); never mid-fight
        FIGHT_INFO['loss_checked'] = True
        if RUN in opts:
            ll = likely_loss(g, M, party_hp)
            if ll:
                ch = flee_chance(g)
                FIGHT_INFO['likely_loss'] = dict(ll, chance=ch)
                if ch > LOSS_FLEE_ABOVE:
                    FIGHT_INFO.setdefault('runs', []).append((1, ch, 'likely loss'))
                    return ('run',)
    if FLEE_RULE and RUN_OK and RUN in opts:
        # run only where it saves something (on the way to the grinding spot, or home with
        # the casters spent), from a costly fight, at FLEE_MIN or better; the losing state
        # heals and fights (Chris, 2026-10-14)
        many = sum(len(v['mons']) for v in M.values()) >= MANY
        if why or many:
            ch = flee_chance(g)
            if ch >= FLEE_MIN:
                FIGHT_INFO.setdefault('runs', []).append((ROUND, ch, why or 'many'))
                return ('run',)
    if 'first' not in FIGHT_INFO and M:
        # the rating's inputs at the first command phase (brief item 6)
        FIGHT_INFO['first'] = tactics.matters_detail(g, M, party_hp, lv[len(lv) // 2] if lv else None, party)
        FIGHT_INFO['first']['party_max'] = sum(g.char(rk)['max_hp'] for rk in ids if rk is not None)
    # support spells (the party's AC and magic screen, the monsters' AC) and spell levels
    # 6-7 only in a story or boss fight or one that's going badly (Chris, 2026-10-14):
    # someone down or the party under 45% (losing), or monsters that could take half the
    # party's HP in two rounds (smoke2, 2026-10-14: Area B's five-member human party, rated
    # cheap, wiped a level-14 party in 8 rounds that Tiltowait had beaten with one loss)
    boss = why in (tactics.HEAVY if CHEAPEST else ('story',)) or bad
    # heal: (d) a member who couldn't survive another hit of the worst monster that
    # reaches them, or anyone below 40%; the cheapest heal that lifts them clear of it,
    # else the strongest there is
    hurt = []
    risk = {s_: b for s_, h, b in tactics.danger(g, M, party)} if HEAL_RISK else {}
    if not HEAL_RISK:
        # the old rule: the most hurt member below 40%, the strongest heal there is
        old = [(hp / mx, k) for k, hp, mx in party if mx and hp * 10 < mx * 4]
        if old:
            for sid in (64, 58, 36, 33, 30, 21):    # as it was (Diomas first: see HEAL_RISK)
                if sid in by_id:
                    c = by_id[sid]
                    return ('spell', sid, c[1], c[2], c[3], ('member', min(old)[1]))
    for k, hp, mx in (party if HEAL_RISK else []):
        need = max(mx * 0.4, risk.get(k, 0) + 1)
        if mx and hp < need and CAST.get(('healed', k), -1) != ROUND:
            hurt.append((hp - need, k, need - hp, mx - hp))
    if hurt:
        _, k, short, room = min(hurt)
        heals = [sid for sid in HEAL_ONE if sid in by_id]
        enough = [sid for sid in heals if HEAL_MEAN.get(sid, 999) >= min(short, room)]
        sid = enough[0] if enough else (heals[-1] if heals else None)
        if sid is not None and (enough or HEAL_MEAN.get(sid, 999) * 2 >= short or hp_frac(party, k) < 0.4):
            c = by_id[sid]
            CAST[('healed', k)] = ROUND
            return ('spell', sid, c[1], c[2], c[3], ('member', k))
    # a member out of the fight in one that matters: Dialko for paralysis or sleep, Madi
    # for stone too (dim.json: Dialko cures paralysis and sleep in battle; Madi all but
    # death and ash)
    if big and len(M):
        for k, rk in enumerate(ids):
            if rk is None or k == m:
                continue
            st = member_state(g, k)[1]
            if st >= 0x80:
                continue
            for sid, bits in ((tactics.DIALKO, 0x28), (tactics.MADI, 0x68)):
                if st & bits and sid in by_id and CAST.get(('cure', k), 0) < ROUND:
                    CAST[('cure', k)] = ROUND
                    c = by_id[sid]
                    return ('spell', sid, c[1], c[2], c[3], ('member', k))
    # every spell and target, valued in hit points (tactics.py): in a fight that doesn't
    # matter, nothing above CHEAP_LEVEL and no support spells, and a healer keeps the last
    # point of a level holding a heal they know
    rec = me['raw']
    cands = []
    for sid, c in by_id.items():
        sch, lv = c[1], c[2]
        if not big:
            if lv > tactics.CHEAP_LEVEL:
                continue
        elif CHEAPEST and lv >= KEEP_LEVEL and not boss:
            continue                    # (c) levels 6-7 wait for bosses and bad fights
        if rec[0x5c + sch * 7 + lv - 1] <= 1 and (not boss if CHEAPEST else not big) and any(
                h in tactics.HEALS for h in known_spells(rec, sch, lv)):
            continue
        if sid in tactics.DAMAGE or sid in tactics.DEATH or sid in tactics.DISABLE:
            for k in M:
                v = tactics.value(g, sid, k, M, me['level'], CAST)
                if v > 0:
                    cands.append((v, ('spell', sid, sch, lv, c[3], ('group', k)), (sid, k), lv))
        elif boss and sid in (tactics.BAMATU, tactics.MAPORFIC, tactics.CORTU):
            v = tactics.support_value(g, sid, M, CAST, party_hp)
            if v > 0 and M:
                k = min(M)
                cands.append((v, ('spell', sid, sch, lv, c[3], ('group', k)), (sid, None), lv))
        elif boss and sid in (tactics.DILTO, tactics.MORLIS, tactics.BADUMAS):
            for k in M:
                v = tactics.armor_value(g, sid, k, M, CAST)
                if v > 0:
                    cands.append((v, ('spell', sid, sch, lv, c[3], ('group', k)), (sid, k), lv))
    if DISPEL in opts:
        for k in M:
            v = tactics.dispel_value(g, k, M, me['cls'], me['level'])
            if v > 0:
                cands.append((v, ('dispel', ('group', k)), ('dispel', k), 0))
    fight_v = 3 * me['level'] if FIGHT in opts else 0
    if cands:
        cands.sort(key=lambda x: -x[0])
        pick_ = cands[0]
        if CHEAPEST and big and not boss:
            # (c) the cheapest spell that does most of what the best one would
            ok = [c_ for c_ in cands if c_[0] >= CHEAP_SHARE * cands[0][0]]
            pick_ = min(ok, key=lambda c_: (c_[3], -c_[0]))
        if len(cands) > 1 and _vary():
            pick_ = cands[1]
        v, act, key, _ = pick_
        if v > fight_v and v >= MIN_SPELL_VALUE:
            CAST[key[0]] = CAST.get(key[0], 0) + 1
            if key[1] is not None:
                CAST[key] = CAST.get(key, 0) + 1
            if PLANNING and (key[0] in tactics.DAMAGE or key[0] in tactics.DEATH or key[0] in tactics.DISABLE):
                tactics.value(g, key[0], key[1], M, me['level'], CAST, commit=True)
            return act
    if FIGHT in opts:
        return ('fight',)
    return ('parry',) if PARRY in opts else ('first',)


def _flee_msgs(g, n0):
    """(escaped, failed) runs this fight: FIGHTMSG 205 and 206 (battle_main 0x800a2cd8)."""
    if not g.cap:
        return None
    M = [m for m in g.cap.messages[n0:] if m['file'] == 'FIGHTMSG.OBJ']
    return (sum(1 for m in M if m['idx'] == 205), sum(1 for m in M if m['idx'] == 206))


def hp_frac(party, k):
    for s_, hp, mx in party:
        if s_ == k:
            return hp / mx if mx else 1
    return 1


def sig(g):
    return (g.u8(PHASE), g.u8(MEMBER), g.u8(LEVEL), g.u8(SCREEN))


def _press_change(g, btn, limit=180, what='battle input'):
    s0 = sig(g)
    return ui.press_until(g, btn, lambda: sig(g) != s0 or not in_battle(g), limit, what)


def _options(g):
    o = []
    for b in g.e.read(OPTS, 9):
        if b == 0 or (o and b == o[-1]):
            break
        o.append(b)
    return o


def command_member(g, policy, log):
    m = g.u8(MEMBER)
    ui.wait_until(g, lambda: g.u8(SCREEN) == 9 and g.u8(OPTS) != 0, 120, 'command list')
    g.step(1)
    opts = _options(g)
    if member_state(g, m)[1] & 0x02:
        # confused: the list shows Fight alone and its cursor won't move, but the option
        # bytes keep the full list (chapter 2 dev run, 2026-10-13: Ghosts' Lios)
        opts = opts[:1]
    act = policy(g, m, opts)
    log.append((m, act[0], act[1] if len(act) > 1 else None))
    if act[0] == 'spell':
        ri = party_ids(g)[m]
        FIGHT_INFO['casts'].append((g.char(ri)['name'] if ri is not None else m,
                                    act[1], act[2], act[3]))
    if act[0] == 'first':
        _press_change(g, 'circle')
        return
    want = {'fight': FIGHT, 'parry': PARRY, 'spell': SPELL, 'run': RUN, 'dispel': DISPEL}[act[0]]
    k = opts.index(want)
    try:
        # five or more commands sit in two columns of four (Fight Parry Spell Use | Run):
        # the column is COL (right/left), the row LIST (c1v0c, 2026-10-13: Run was out
        # of reach of up/down)
        if len(opts) > 4:
            ui.move_cursor(g, COL, k // 4, 'right', 'left', limit=120, what='command column')
        ui.move_cursor(g, LIST, k % 4, 'down', 'up', limit=120, what='command')
        _press_change(g, 'circle', what='choose command')
    except Stuck:
        # a list shorter than its option bytes (a status we haven't met): take what's
        # under the cursor, then whatever target step follows
        log.append((m, 'cursor stuck', act[0]))
        _press_change(g, 'circle')
        act = ('first',)
    if act[0] == 'spell':
        sid, school, level, idx, target = act[1:]
        ui.wait_until(g, lambda: g.u8(SCREEN) == 49, 120, 'spell grid')
        ui.move_cursor(g, LIST, school, 'down', 'up', what='spell school')
        ui.move_cursor(g, COL, level - 1, 'right', 'left', what='spell level')
        _press_change(g, 'circle', what='spell level')
        ui.wait_until(g, lambda: g.u8(SCREEN) == 50, 120, 'spell list')
        ui.move_cursor(g, LIST, idx, 'down', 'up', what='spell')
        _press_change(g, 'circle', what='spell')
        ui.wait_until(g, lambda: g.u8(SCREEN) not in TRANSIENT, 120, 'after spell')
        if g.u8(SCREEN) == 51 and target[0] == 'member':
            slot = target[1]
            ui.move_cursor(g, PGRID_Y, slot // 3, 'down', 'up', what='target row')
            ui.move_cursor(g, PGRID_X, slot % 3, 'right', 'left', what='target col')
    # a target step: an enemy group pick is aimed (aim); anything else (a member) takes
    # what's selected. Stop at the next member or the overview.
    prefer = act[-1][1] if act[0] in ('spell', 'dispel') and act[-1][0] == 'group' else None
    end = g.frame + 600
    while in_battle(g) and g.u8(PHASE) == CMD_PHASE and g.u8(MEMBER) == m \
            and g.u8(SCREEN) not in WAITING:
        if g.frame > end:
            raise Stuck('target step', sig=sig(g))
        if g.u8(SCREEN) in TRANSIENT or g.u8(SCREEN) == 9:
            g.step(1)
            continue
        if pick.pick_screen(g) is not None:
            if not aim(g, m, prefer, log) and pick.pick_screen(g) is not None \
                    and g.u8(MEMBER) == m:
                _press_change(g, 'circle', what='target')
            continue
        _press_change(g, 'circle', what='target')


def command_phase(g, policy, log):
    end = g.frame + 6000
    still, last = 0, None
    while in_battle(g) and g.u8(PHASE) == CMD_PHASE:
        if g.frame > end:
            raise Stuck('command phase', sig=sig(g))
        if g.u8(LEVEL) == 1 and g.u8(SCREEN) == 9:
            command_member(g, policy, log)
        elif g.u8(SCREEN) in WAITING:
            # the members overview, or "Is this all right?" (cursor on Yes)
            _press_change(g, 'circle', 120, 'command flow')
        else:
            # a screen in transition: a press now would carry into the next menu. One
            # that stays put isn't a transition but a pick left waiting (a group pick,
            # screen 17, after a cut-short command; c1v0c 2026-10-13): take what's
            # selected.
            s = sig(g)
            still = still + 1 if s == last else 0
            last = s
            if still >= 8 and pick.pick_screen(g) is not None:
                # a group pick left waiting (a state saved on one): aim it
                if not aim(g, g.u8(MEMBER), None, log) and pick.pick_screen(g) is not None:
                    _press_change(g, 'circle', 120, 'waiting pick')
                still = 0
                continue
            if still >= 60 and g.u8(SCREEN) not in TRANSIENT:
                _press_change(g, 'circle', 120, 'waiting pick')
                still = 0
                continue
            g.step(1)


CHEST_PHASE = 0x42
# "A friendly monster appears. What will you do?" (FIGHTMSG 263): battle_phase 0x66,
# its menu up while 0x800795fa is 0, LIST 0 Fight, 1 Leave. Fighting turns Good members
# Evil (7% each), leaving turns Evil ones Good (5%), so the bot always leaves.
FRIENDLY_PHASE = 0x66
FRIENDLY_STEP = 0x800795fa
FRIENDLY_LEAVE = 1
FRIENDLY = 0x8007963c       # friendly_encounter: 1 from the setup to the menu
BLIND_WAIT = 120             # frames of chest phase with no new text before going by RAM
# the chest menu: Inspect Calfo Calnova Disarm Open Leave (LIST 0-5); LEVEL 1 while it
# has the input, 2 while a member is being picked
CHEST_LEAVE, CHEST_OPEN, CHEST_INSPECT = 5, 4, 0
LOOT_MSGS = (198, 261, 262, 240, 241, 242) + tuple(range(221, 234))


def _since(g, n, file, idxs):
    return [m for m in g.cap.messages[n:] if m['file'] == file and m['idx'] in idxs] if g.cap else []


def _chest_pick_member(g, slot):
    ui.move_cursor(g, PGRID_Y, slot // 3, 'down', 'up', what='chest member row')
    ui.move_cursor(g, PGRID_X, slot % 3, 'right', 'left', what='chest member')


def chest_menu_ready(g, since=0):
    """The chest menu has the input: chest phase, LEVEL 1, and "A chest! What will you
    do?" (FIGHTMSG 245) printed since message number `since`."""
    return (in_battle(g) and g.u8(PHASE) == CHEST_PHASE and g.u8(LEVEL) == 1
            and bool(_since(g, since, 'FIGHTMSG.OBJ', (245,))))


def _chest_tap_until(g, cond, limit=900, what='chest'):
    """Tap through the chest's messages until cond(); 16 frames between taps."""
    f0 = g.frame
    while not cond():
        if g.frame - f0 > limit:
            raise Stuck(what, sig=sig(g))
        g.tap('circle')
        for _ in range(16):
            if cond():
                return
            g.step()


def chest(g, mode='leave', who=0, since=None):
    """The chest menu after a battle. mode 'leave', 'open' (open at once: only where the
    chests are known to be untrapped), or 'inspect' (inspect with member `who`; open only
    if it reports no trap; leave a named trap). Returns what happened."""
    if since is None:
        since = max(0, len(g.cap.messages) - 40)
    ui.wait_until(g, lambda: chest_menu_ready(g, since), 600, 'chest menu')
    gone = lambda: not in_battle(g) or g.u8(PHASE) != CHEST_PHASE
    if mode == 'leave':
        ui.move_cursor(g, LIST, CHEST_LEAVE, 'down', 'up', what='chest option')
        ui.confirm_until(g, gone, 300, 'leave chest')
        return 'left'
    if mode == 'open':
        # open straight away (for chests known to be untrapped, e.g. on the Grounds)
        n3 = len(g.cap.messages)
        ui.move_cursor(g, LIST, CHEST_OPEN, 'down', 'up', what='chest option')
        ui.confirm_until(g, lambda: _since(g, n3, 'FIGHTMSG.OBJ', (250,)) or gone(), 120, 'open')
        if not gone():
            _chest_pick_member(g, who)
            _chest_tap_until(g, gone, what='opening')
        return 'opened'
    n = len(g.cap.messages)
    ui.move_cursor(g, LIST, CHEST_INSPECT, 'down', 'up', what='chest option')
    ui.confirm_until(g, lambda: _since(g, n, 'FIGHTMSG.OBJ', (246,)), 120, 'inspect')
    _chest_pick_member(g, who)
    ui.confirm_until(g, lambda: _since(g, n, 'FIGHTMSG.OBJ', range(221, 234)) or gone(),
                     300, 'inspect result')
    res = _since(g, n, 'FIGHTMSG.OBJ', range(221, 234))
    oops = _since(g, n, 'FIGHTMSG.OBJ', (242,))
    n2 = len(g.cap.messages)
    # back at the menu (A chest! What will you do? again) or the chest went off and opened
    _chest_tap_until(g, lambda: gone() or chest_menu_ready(g, n2), what='after inspect')
    if gone():
        return 'oops' if oops else 'gone'
    trap = res[0]['idx'] if res else None
    if (trap == 221 or trap in MILD_TRAPS and OPEN_MILD) and not oops:
        n3 = len(g.cap.messages)
        ui.move_cursor(g, LIST, CHEST_OPEN, 'down', 'up', what='chest option')
        ui.confirm_until(g, lambda: _since(g, n3, 'FIGHTMSG.OBJ', (250,)) or gone(), 120, 'open')
        if not gone():
            _chest_pick_member(g, who)
            _chest_tap_until(g, gone, what='opening')
        return 'opened'
    ui.move_cursor(g, LIST, CHEST_LEAVE, 'down', 'up', what='chest option')
    ui.confirm_until(g, gone, 300, 'leave chest')
    return 'left trap %s' % trap


# --- every chest: inspect (or Calfo), disarm, open (Chris, 2026-10-14) ---
# The rules, all from BATTLE (docs/re/lock-test.md "Chests", D-battle.md "Chests and traps"):
#   Inspect (FUN_800c697c): right with chance Agility x 6 Thief, 5 Ninja, 4 Ranger or Bard,
#     1 anyone else, held to 1-95; a miss names a random trap when rand_below(20) <= Agility,
#     else the trap goes off on the inspector.
#   Calfo (Priest 2, id 24): 95% right, never sets it off.
#   Calnova (Alchemist 7, id 61): 85% disarms, else 90% nothing, 10% it goes off.
#   Disarm: a wrong name sets it off; the right one disarms with chance 80 (Thief, Ninja),
#     60 (Ranger, Bard), 0 (anyone else) + level - the area's danger; a miss sets it off
#     when rand_below(20) + (5 for the others) > Agility, else "Couldn't disarm the trap."
#     and the menu again. A disarmed or sprung chest gives its loot (chest_open 0x1e/0x28
#     -> 0x50 chest_loot).
#   Items go to a random member with room (FUN_800c8388), not to the opener.
#   danger = area_danger[map_type_of_area[area]] (chest_trap_pick 0x800c6768).
CLS_INSPECT = {3: 6, 12: 5, 7: 4, 8: 4}
CLS_DISARM = {3: 80, 12: 80, 7: 60, 8: 60}
AREA_DANGER, MAP_TYPE_OF_AREA, MAZE_AREA = 0x800d7cec, 0x8005a824, 0x80079668
CALFO, CALNOVA = 24, 61
# traps by number (FIGHTMSG 221 + n): those that hit only the opener or poison are
# opened if they can't be disarmed; the rest are left unless the odds of springing them
# while disarming are low (SPRING_RISK)
MILD = {1, 2, 4, 9}
SPRING_RISK = 0.25
DISARM_TRIES = 8
CHESTS = []             # one record per chest met (fight() returns the last)


def area_danger(g):
    t = struct.unpack('b', bytes([g.u8(MAP_TYPE_OF_AREA + g.u8(MAZE_AREA))]))[0]
    return g.u8(AREA_DANGER + t)


def _can_act(c):
    # paralysis and worse can't be chosen; asleep or out cold can't act either
    return c['status'] & ~0x05 == 0


def inspect_chance(c):
    return min(95, max(1, c['stats'][4] * CLS_INSPECT.get(c['cls'], 1)))


def disarm_odds(c, danger):
    """(chance it's disarmed, chance a miss springs it) for one try with the right name."""
    p = max(0, min(100, CLS_DISARM.get(c['cls'], 0) + c['level'] - danger)) / 100
    b = 0 if c['cls'] in CLS_DISARM else 5
    q = sum(1 for r in range(20) if r + b > c['stats'][4]) / 20
    return p, q


def spring_risk(p, q):
    """Chance the trap goes off before it's disarmed, trying until one or the other."""
    return 1.0 if p + (1 - p) * q == 0 else (1 - p) * q / (p + (1 - p) * q)


def _caster(g, members, sid, school, level):
    for slot, c in members:
        if sid in known_spells(c['raw'], school, level) and c['raw'][0x5c + school * 7 + level - 1] \
                and c['status'] & ~0x04 == 0:
            return slot, c
    return None


CHEST_PROMPTS = {0: 246, 1: 247, 2: 248, 3: 249, 4: 250}
CHEST_REFUSED = (234, 235, 236, 237, 238, 243, 244)


def _chest_act(g, opt, slot, trap=None):
    """One chest menu action by party slot `slot` (trap: the name to disarm, 1-12).
    Returns (new FIGHTMSG (idx, text) list, gone)."""
    gone = lambda: not in_battle(g) or g.u8(PHASE) != CHEST_PHASE
    n = len(g.cap.messages)
    ui.move_cursor(g, LIST, opt, 'down', 'up', what='chest option')
    ui.confirm_until(g, lambda: _since(g, n, 'FIGHTMSG.OBJ', (CHEST_PROMPTS[opt],) + CHEST_REFUSED)
                     or gone(), 120, 'chest option %d' % opt)
    if not gone() and not _since(g, n, 'FIGHTMSG.OBJ', CHEST_REFUSED):
        ui.wait_until(g, lambda: g.u8(LEVEL) == 2 or gone(), 120, 'chest member pick')
        _chest_pick_member(g, slot)
        if opt == 3:
            ui.confirm_until(g, lambda: _since(g, n, 'FIGHTMSG.OBJ', (251,)) or gone(), 120,
                             'disarm member')
            g.step(8)
            ui.move_cursor(g, LIST, trap - 1, 'down', 'up', what='trap name')
        lv = g.u8(LEVEL)
        n2 = len(g.cap.messages)
        ui.confirm_until(g, lambda: gone() or g.u8(LEVEL) != lv
                         or len([m for m in g.cap.messages[n2:] if m['file'] == 'FIGHTMSG.OBJ']),
                         120, 'chest action %d' % opt)
    n3 = len(g.cap.messages)
    _chest_tap_until(g, lambda: gone() or chest_menu_ready(g, n3), limit=1500, what='chest result')
    out = [(m['idx'], m['text'].replace('\n', ' ')) for m in g.cap.messages[n:]
           if m['file'] == 'FIGHTMSG.OBJ']
    return out, gone()


def chest_full(g, since=None):
    """Every chest: find out the trap (the best inspector at 95%, else Calfo, else the
    best inspector), disarm a trap with the best disarmer (Calnova first if anyone has
    it), then open it. A trap that only hurts the opener or poisons is opened if it can't
    be disarmed; a worse one is left only when nobody can disarm it at decent odds.
    Returns the chest's record (also appended to CHESTS)."""
    if since is None:
        since = max(0, len(g.cap.messages) - 40)
    ui.wait_until(g, lambda: chest_menu_ready(g, since), 600, 'chest menu')
    danger = area_danger(g)
    members = [(slot, g.char(ri)) for slot, ri in enumerate(g.party_slots()) if ri is not None]
    members = [(s, c) for s, c in members if _can_act(c)]
    # the chest's real trap (0x80079a59), for the log only: the choices go by what the
    # party is told
    rec = dict(area=g.u8(MAZE_AREA), pos=g.pos(), danger=danger, acts=[], trap=None,
               went_off=None, loot=[], result=None, real_trap=g.u8(0x80079a59))
    CHESTS.append(rec)
    if not members:
        _chest_act_leave(g)
        rec['result'] = 'left (nobody can act)'
        return rec

    def act(opt, slot, trap=None, why=''):
        msgs, gone = _chest_act(g, opt, slot, trap)
        rec['acts'].append(dict(act=['inspect', 'calfo', 'calnova', 'disarm', 'open'][opt],
                                who=g.char(g.party_slots()[slot])['name'], trap=trap, why=why,
                                msgs=[i for i, t in msgs]))
        for i, t in msgs:
            if i == 242:
                rec['went_off'] = t
            elif i in (261, 262) or 252 <= i <= 260:
                rec['loot'].append(t)
        return msgs, gone

    def named(msgs):
        k = [i for i, t in msgs if 221 <= i <= 233]
        return k[-1] - 221 if k else None

    # what's the trap?
    best_i = max(members, key=lambda m: (inspect_chance(m[1]), m[1]['stats'][4]))
    calfo = _caster(g, members, CALFO, 1, 2)
    if inspect_chance(best_i[1]) >= 95 or calfo is None:
        msgs, gone = act(0, best_i[0], why='inspect %d%%' % inspect_chance(best_i[1]))
    else:
        msgs, gone = act(1, calfo[0], why='calfo 95%')
        if named(msgs) is None and not gone:
            msgs, gone = act(0, best_i[0], why='inspect %d%% (calfo failed)' % inspect_chance(best_i[1]))
    if gone:
        rec['result'] = 'sprung inspecting'
        return rec
    trap = named(msgs)
    rec['trap'] = trap
    if trap is None:
        _chest_act_leave(g)
        rec['result'] = 'left (no answer)'
        return rec
    if trap and trap not in MILD:
        # a wrong name sets the trap off at once, and these hit everyone (q8 loot test
        # l1b, 2026-10-14: an inspect read Spell Blaster and four casters died disarming
        # it): ask others until two answers agree (each member answers once a chest;
        # Calfo casters, then members who inspect at 50% or more), else leave it. In l3b
        # Calfo misread 2 of 4 where the Thief was right, so one answer each isn't enough
        votes = {trap: 1}
        used = {a['who'] for a in rec['acts']}
        while max(votes.values()) < 2:
            m = None
            for slot, c in members:
                if c['name'] in used:
                    continue
                if CALFO in known_spells(c['raw'], 1, 2) and g.char(c['i'])['raw'][0x5c + 7 + 1] \
                        and c['status'] & ~0x04 == 0:
                    m = (1, slot, c, 'calfo')
                    break
            if m is None:
                others = [(s_, c) for s_, c in members if c['name'] not in used
                          and inspect_chance(c) >= 50]
                if others:
                    s_, c = max(others, key=lambda sc: inspect_chance(sc[1]))
                    m = (0, s_, c, 'inspect %d%%' % inspect_chance(c))
            if m is None:
                break
            used.add(m[2]['name'])
            msgs2, gone = act(m[0], m[1], why='another opinion, ' + m[3])
            if gone:
                rec['result'] = 'sprung inspecting'
                return rec
            t2 = named(msgs2)
            if t2 is not None:
                votes[t2] = votes.get(t2, 0) + 1
        rec['votes'] = votes
        best = max(votes, key=votes.get)
        if votes[best] < 2:
            _chest_act_leave(g)
            rec['result'] = 'left (answers differ: %s)' % votes
            return rec
        trap = best
        rec['trap'] = trap
    if trap:
        nova = _caster(g, members, CALNOVA, 2, 7)
        disarmers = sorted(members, key=lambda m: -disarm_odds(m[1], danger)[0])
        p, q = disarm_odds(disarmers[0][1], danger)
        risk = spring_risk(p, q)
        rec['odds'] = dict(who=disarmers[0][1]['name'], p=p, q=q, risk=round(risk, 3))
        for k in range(DISARM_TRIES):
            nova = _caster(g, members, CALNOVA, 2, 7)
            if nova is not None:
                msgs, gone = act(2, nova[0], why='calnova')
            elif p > 0 and (trap in MILD or risk <= SPRING_RISK):
                msgs, gone = act(3, disarmers[0][0], trap, why='disarm %d%%, springs %d%% of misses'
                                 % (p * 100, q * 100))
            else:
                break
            if gone:
                rec['result'] = ('disarmed' if any(i in (240, 241) for i, t in msgs) else
                                 'sprung disarming' if rec['went_off'] else 'gone disarming')
                return rec
        if trap not in MILD:
            _chest_act_leave(g)
            rec['result'] = 'left trap %d (risk %.2f)' % (trap, risk)
            return rec
    # open it: an untrapped chest, or a mild trap that couldn't be disarmed (the opener
    # takes it: the one with the most hit points)
    opener = max(members, key=lambda m: m[1]['hp'])
    msgs, gone = act(4, opener[0], why='open' if not trap else 'open mild trap %d' % trap)
    rec['result'] = 'opened' if not rec['went_off'] else 'opened, sprung'
    if not gone:
        _chest_act_leave(g)
        rec['result'] += ' (then left?)'
    return rec


def _chest_act_leave(g):
    gone = lambda: not in_battle(g) or g.u8(PHASE) != CHEST_PHASE
    if gone():
        return
    ui.move_cursor(g, LIST, CHEST_LEAVE, 'down', 'up', what='chest option')
    ui.confirm_until(g, gone, 300, 'leave chest')


# Inspect's answers, FIGHTMSG 221-233 in the order of data/traps/dim.json: no trap,
# Stone Shot, Poison Needle, Magic Drain, Poison Gas, Bomb, Ghost Swarm, Demon Eye,
# Rainbow Ray, Goddess's Kiss, Spell Blaster, Alarm, Teleporter. The loot is worth a
# trap that hurts one member or poisons (the party cures poison from camp now): open
# those too (Chris, 2026-10-14: weigh the loot). Not the ones that hit everyone hard,
# stone, kill casters, lose the chest or move the party.
MILD_TRAPS = {222, 223, 225, 230}
OPEN_MILD = True
THIEVES = (3, 12)            # Thief, Ninja (G-records class ids)


def pack_full(g, slot):
    ri = g.party_slots()[slot]
    return ri is None or len(g.char(ri)['items']) >= 10


def thief_slot(g):
    """Party slot of a standing Thief or Ninja, or None."""
    for slot, ri in enumerate(g.party_slots()):
        if ri is not None:
            c = g.char(ri)
            if c['cls'] in THIEVES and c['status'] == 0:
                return slot
    return None


def _party_hp(g):
    return sum(max(g.char(ri)['hp'], 0) for ri in g.party())


def fight(g, policy=default_policy, chest_mode='leave', limit=60000):
    """Fight the battle on screen to its end. Returns a dict: rounds, frames, outcome
    ('won' back in the maze, 'town' after a wipe or escape to town, 'other'), actions."""
    f0 = g.frame
    rounds = 0
    log = []
    CAST.clear()
    FIGHT_INFO['matters'], FIGHT_INFO['casts'] = False, []
    FIGHT_INFO.pop('first', None)
    FIGHT_INFO.pop('runs', None)
    FIGHT_INFO.pop('loss_checked', None)
    FIGHT_INFO.pop('likely_loss', None)
    msg0 = len(g.cap.messages) if g.cap else 0
    tactics.STORY[0] = None
    where = (g.u8(MAZE_AREA),) + tuple(g.pos())
    _vrng.seed(VARY * 7919 + 1)
    chest_result = None
    chest_mark = len(g.cap.messages) if g.cap else 0
    blind = None            # (frame, messages) when the chest phase began with no new text
    while True:
        if g.frame - f0 > limit:
            raise Stuck('battle too long', sig=sig(g))
        if not in_battle(g):
            break
        ph = g.u8(PHASE)
        if ph == CMD_PHASE:
            global ROUND
            rounds += 1
            ROUND = rounds
            command_phase(g, policy, log)
            continue
        if ph == CHEST_PHASE:
            # the chest menu, or a loot message ("Each survivor gains N gold!") when there's
            # no chest. Tap only for a message: a press would pick from the chest menu.
            if _since(g, chest_mark, 'FIGHTMSG.OBJ', (245,)):
                mode, who = chest_mode, 0
                if mode == 'auto':
                    # every chest (Chris, 2026-10-14): the Grounds' are never trapped and
                    # are opened by the first member who can act; elsewhere chest_full
                    if g.u8(MAZE_AREA) == 0:
                        who = next((s for s, ri in enumerate(g.party_slots()) if ri is not None
                                    and _can_act(g.char(ri))), None)
                        mode = 'open' if who is not None else 'leave'
                        who = who or 0
                    else:
                        mode = 'full'
                if mode == 'full':
                    chest_result = chest_full(g, since=chest_mark)
                else:
                    chest_result = chest(g, mode, who=who, since=chest_mark)
                continue
            last = [m for m in g.cap.messages[chest_mark:] if m['file'] == 'FIGHTMSG.OBJ']
            if last and last[-1]['idx'] in LOOT_MSGS:
                n = len(g.cap.messages)
                ui.press_until(g, 'circle', lambda: not in_battle(g) or g.u8(PHASE) != CHEST_PHASE
                               or len(g.cap.messages) > n, 300, 'loot message')
                chest_mark = len(g.cap.messages)
            else:
                n = len(g.cap.messages) if g.cap else 0
                if blind is None or blind[1] != n:
                    blind = (g.frame, n)
                if g.frame - blind[0] > BLIND_WAIT:
                    # nothing printed for BLIND_WAIT frames in the chest phase: the text
                    # capture can't see this disc's text (the Japanese original; its fights
                    # sat on "each survivor gains N gold" until "battle too long",
                    # t3/metlock/jp_chapter_attempt). Go by RAM: LEVEL 1 is the chest
                    # menu (leave the chest), anything else a message waiting for a press.
                    if g.u8(LEVEL) == 1:
                        chest_result = 'left (blind)'
                        ui.move_cursor(g, LIST, CHEST_LEAVE, 'down', 'up', what='chest option')
                        ui.confirm_until(g, lambda: not in_battle(g) or g.u8(PHASE) != CHEST_PHASE
                                         or g.u8(LEVEL) != 1, 300, 'leave chest')
                    elif g.u8(LEVEL) == 2:
                        # a member pick ("Who will open the chest?"): back to the menu
                        # (a state saved there, f1v6c, comes up with no text seen)
                        g.tap('cross', hold=6)
                        g.step(30)
                    else:
                        g.tap('circle')
                        g.step(16)
                    continue
                g.step()
            continue
        blind = None
        chest_mark = len(g.cap.messages) if g.cap else 0
        if ph == 1 and g.u8(FRIENDLY) == 1:
            g.step()            # the menu is coming: a tap now would pick Fight
            continue
        if ph == FRIENDLY_PHASE and g.u8(FRIENDLY_STEP) == 0 and g.u8(LIST) != FRIENDLY_LEAVE:
            ui.move_cursor(g, LIST, FRIENDLY_LEAVE, 'down', 'up', what='friendly leave')
            log.append((None, 'friendly', 'leave'))
            continue
        # narration and everything else waits for a press; tap it along (4-frame floor)
        g.tap('circle')
        for _ in range(4):
            if not in_battle(g) or g.u8(PHASE) == CMD_PHASE:
                break
            g.step()
    return dict(rounds=rounds, frames=g.frame - f0, actions=log, ovl=g.overlay(), chest=chest_result,
                where=where, story=tactics.STORY[0],
                matters=FIGHT_INFO['matters'], casts=list(FIGHT_INFO['casts']),
                ran=sum(1 for a in log if a[1] == 'run'),
                runs=FIGHT_INFO.get('runs', []), likely_loss=FIGHT_INFO.get('likely_loss'),
                fled=_flee_msgs(g, msg0),
                first=FIGHT_INFO.get('first'), hp_end=_party_hp(g),
                down_end=[g.char(ri)['name'] for ri in g.party() if g.char(ri)['status'] >= 0x20],
                dead_end=[g.char(ri)['name'] for ri in g.party() if g.char(ri)['status'] & 0x380])
