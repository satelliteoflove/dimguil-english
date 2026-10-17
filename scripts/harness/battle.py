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
import math, random, struct
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
USE_LIST = 81                # SCREEN: the Use item list (cursor LIST; agent 10 probe, 2026-10-14)
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
HEAL_WORTH = True       # (bossfight) in a fight that matters, a heal only where it keeps someone alive (heal_worth)
HEAL_SHARE = 0.5        # ... and heals at least this share of what they're expected to lose this round
HEAL_CLEAR = 1.25       # ... and lifts them to this many times it and past the worst one blow (a Dial from 7 to 16
                        # against 10 expected left Mercury to a Beast's club, chdev/a7_pf/f07 seed 7)
CASTER_BOSS = True      # (bossfight) a fight that matters with kill-rank-0 casters counts as a boss for Cortu and BOSS_FOCUS_SHARE
BOSS_FOCUS_SHARE = 0.5  # (bossfight) a boss fight's focus_pick finisher gives way to a turn worth twice as much
TRIP_BLOW = [0.0, 0.0]  # the worst one-action damage seen this trip, front and back row (chapters.train)
KEEP_LEVEL = 6         # (c) spell levels kept for story/boss fights and fights going badly
BOSS_KEEP = {}         # roster index -> {(school, level): points} kept on the walk to a boss
                       # (chapters.Run.keep_for_boss): spent only in the story fight or one
                       # going badly (n1v0q chapter 10: the walk to the Guardians took the
                       # mages' level-3 points, one Cortu instead of four, two wipes)
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
CASTER_FIRST = True         # fighters' blows on a lone para/group-damage caster first (choose_group)
KILL_FIRST = {366: 0, 358: 1,       # Arch Mage, Arch Priest (Underground B2 E7 N22)
              454: 0, 438: 1,       # the same pair at Area A B1 E16 N11
              455: 0, 439: 1}       # and at Area B B1 E9 N11, chapter 10's Guardians (n1v0o: their
                                    # Tiltowait and Badi wiped the party in 3 rounds, twice)
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
OUT_BITS = 0x04 | 0x20 | 0x40 | 0x80 | 0x100 | 0x200   # poison, paralysis, stone, dead, ash, lost
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
    rank = {}
    kr = {}
    if FOCUS_M[0] == ROUND and FOCUS_M[1]:
        # kill-first by id or by what the group casts (tactics.kill_rank)
        kr = {k: tactics.kill_rank(v, KILL_FIRST) for k, v in FOCUS_M[1].items()}
    if tactics.CASTER_FOCUS and not spread and FOCUS_M[0] == ROUND and FOCUS_M[1]:
        # (casterfocus) the caster groups first, in tactics.caster_order; one the members
        # before have likely killed this round goes after every other group
        M = FOCUS_M[1]
        order = tactics.caster_order(M, KILL_FIRST)
        live = tactics.caster_order(M, KILL_FIRST, skip_done=True)
        for i, k in enumerate(order):
            rank[k] = live.index(k) if k in live else 100 + i
    lone = set()
    if CASTER_FIRST and not spread and not rank:
        # a lone monster that paralyzes a row or casts group damage: one kill removes it
        # (tactics.first_weight; agent 13, main's call)
        for k in alive:
            try:
                m = tactics.info(g, k)
            except Exception:
                continue
            if (m.get('para') or m.get('gdmg')) and len(m['mons']) == 1:
                lone.add(k)
    return min(alive, key=lambda k: (kr.get(k, KILL_FIRST.get(group_id(g, k), 9)), rank.get(k, 99), k not in lone, k != prefer,
                                     -g.u8(GROUPS + k * 8 + 5) if spread else 0, k))


def aim(g, m, prefer, log, fight=False):
    """At a group pick (Fight, a spell, Dispel...): choose the group and confirm it,
    checked in the member's command record (pick.pick_group). False if it couldn't.
    fight: a Fight's blows go on this round's tactics.FOCUS (casterfocus)."""
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
    if fight and tactics.CASTER_FOCUS:
        tactics.focus_reset(ROUND)
        tactics.FOCUS['dmg'][want] = tactics.FOCUS['dmg'].get(want, 0.0) + tactics.member_melee(g, m, want)
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


LONG_FIGHT = True           # agent 7 / main, 2026-10-14: long_fight() makes a fight matter
LOSS_RUN = True             # Chris, 2026-10-14: run from a likely loss, round 1 only, anywhere
LOSS_FLEE_ABOVE = 25        # Chris, 2026-10-14: a likely loss runs at a flee chance above this
LOSS_EVERY_ROUND = True     # Chris, 2026-10-14: re-rate a likely loss every round, from the HP of
                            # the members who can still act ("try it out and see if it helps")
FIGHT_AFTER_FAILED_RUN = False  # Chris, 2026-10-16 (to test): after one failed run the fight is
                                # fought out with no more runs, and counts as a likely loss for
                                # the support plan (each failed run hands the monsters a round)


def run_failed(g):
    """Whether a run has failed in this fight: FIGHTMSG 206 since its start (_flee_msgs), or,
    with no message capture, a run chosen in an earlier round of a fight still going."""
    f = _flee_msgs(g, FIGHT_INFO.get('msg0', 0))
    if f is not None:
        return f[1] > 0
    return any(r[0] < ROUND for r in FIGHT_INFO.get('runs', []))


def _kill(x, hp):
    # tactics.value's kill rule: a sure kill at the monster's HP, half a kill at 70% of it
    return 1.0 if x >= hp else 0.5 if x >= hp * 0.7 else 0.0


FOCUS_ROUNDS = 3            # the weakest member must outlast this many rounds of focused blows
LONG_SHARE = 0.25           # a fight whose cheap win costs this share of party HP matters


def cheap_round(g, M):
    """The party's damage in a round with cheap means only: each standing member's best
    damage spell of level CHEAP_LEVEL or less it has points for (DAMAGE mean x the chance it
    lands, capped at each target's HP), or for the front row its weapon (half landing)."""
    from harness import gear
    D = 0.0
    for slot, ri in enumerate(party_ids(g)):
        if ri is None:
            continue
        hp, st = member_state(g, slot)
        if hp <= 0 or st >= 0x20:
            continue
        best = 0.0
        for sid, school, level, i in castable(g, ri):
            if sid not in tactics.DAMAGE or level > tactics.CHEAP_LEVEL:
                continue
            mean, kind, el = tactics.DAMAGE[sid]
            for k in M:
                d = 0.0
                for t in tactics.targets(g, k, kind, M):
                    m = M[t]
                    f = 0.5 if m['resist'] & el and el else 2.0 if m['weak'] & el and el else 1.0
                    mons = m['mons'][:1] if kind == 'one' else m['mons']
                    d += tactics.lands(m, sid) * sum(min(mean * f, h) for _, h, _ in mons)
                best = max(best, d)
        if slot < 3:
            w = gear.equipped(g, ri).get(0)
            best = max(best, gear.wscore(w) * 0.5 if w else 2.0)
        D += best
    return D


def members(g):
    """[(slot, roster raw, level)] for the members standing (tactics.disable)."""
    out = []
    for slot, ri in enumerate(party_ids(g)):
        if ri is None:
            continue
        hp, st = member_state(g, slot)
        if hp > 0 and st < 0x20:
            c = g.char(ri)
            out.append((slot, c['raw'], c['level']))
    return out


def long_fight(g, M, party_hp, lost=None):
    """A fight that costs too much won the cheap way (main, 2026-10-14: ten level-7 priests,
    rated 22 a round, fought with cheap spells for 10 rounds and Kai went down; fought hard
    it was won in 2 with nobody down): the rated damage a round times the rounds the cheap
    means need to clear the monsters' HP reaches LONG_SHARE of the party's HP, the rounds
    stretched by the actions the monsters take away (lost, tactics.disable). The numbers,
    or None. Once a round (FIGHT_INFO)."""
    key = ('long', ROUND)
    if key not in FIGHT_INFO:
        T = sum(M[k]['threat'] * len(M[k]['mons']) for k in M)
        H = sum(hp for k in M for _, hp, _ in M[k]['mons'])
        D = cheap_round(g, M)
        rounds = H / max(D, 1.0) * (lost['L'] if lost else 1.0)
        FIGHT_INFO[key] = (dict(threat=round(T, 1), mon_hp=H, cheap_round=round(D), rounds=round(rounds, 1))
                           if T * rounds >= party_hp * LONG_SHARE else None)
    return FIGHT_INFO[key]


PARA_RUSH = 0               # (agent 16) 1: a paralysis rush (para_rush) is a likely loss and runs; 2: it's
                            # fought out. Off: on f07 (the 17 Were Centipedes, 30 battle-RNG seeds) running
                            # wiped 9, fighting as before 6, fighting it out 5 of 11; running left far fewer
                            # members down (15 against 65 in the fights survived). Main's call.
MAPORFIC_ON = 0x8007e82a    # the party's Maporfic: monsters' to-hit 2 worse (D-battle.md "Melee: monsters attack")


def _poisson_ge(mu, k):
    """P(Poisson(mu) >= k)."""
    if k <= 0:
        return 1.0
    t, c = math.exp(-mu), 0.0
    for i in range(k):
        c += t
        t *= mu / (i + 1)
    return max(0.0, 1.0 - c)


def para_rush(g, M):
    """The monsters' next round counted in paralysis (agent 16, from the Were Centipede
    packs: a 17-pack paralyzed a full-HP L17-20 party in round 1 of n1v0q/r, and a party
    with nobody below status 0x20 is wiped, party_wiped 0x800c59a0; their damage never came
    into it). For each member who can act: the expected paralyzing events on it this
    round (lam), from
      - melee: monsters that can act x the fight share x the attack's use (69/31%, attack
        3 always) x swings x the chance a swing hits this member (monster_melee 0x800aaa04:
        T = 22 + Maporfic 2 - AC + AC modifier - (level / 2 + 1), 1..19, (20 - T) x 5%) x
        the attack's effect chance x (99 - the member's resistance) / 100, spread over the
        members the attack reaches (front row without the reach bit; groups 3-4 of a random
        fight don't melee);
      - Lorks and other paralysis spells (tactics.DIS_SPELL 'para'): casters that can cast x
        the status share x tactics.status_lands for this member, half when it picks one of
        two rows; one cast takes the whole row, so the events compound per member;
    and the chance it goes down to the damage spells (tactics.info dcast: Dalosto, mean
    50, one target at random): casters x cast share, its hits Poisson, down at
    ceil(hp / mean) of them, past magic resistance. A rush: the expected events on the
    members left standing reach the members standing. Returns the numbers, or None when
    there's nothing paralyzing."""
    ids = party_ids(g)
    tgt, act = [], []                 # (slot, raw, level, hp, AC + modifier)
    for slot, ri in enumerate(ids):
        if ri is None:
            continue
        hp, st = member_state(g, slot)
        if hp <= 0 or st >= 0x20:
            continue
        c = g.char(ri)
        ac = struct.unpack('b', c['raw'][0x86:0x87])[0] + struct.unpack('b', g.e.read(tactics.COMBAT + slot * 0xe + 4, 1))[0]
        x = (slot, c['raw'], c['level'], hp, ac)
        tgt.append(x)
        if st < 8:
            act.append(x)
    if not act or not M:
        return None
    front = [x for x in tgt if x[0] < 3]
    rows2 = bool(front) and len(front) < len(tgt)
    tbl = g.e.read(tactics.EFFECT_RES, 8)
    screen = g.u8(tactics.GROUPS + 7)
    mapo = 2 if g.u8(MAPORFIC_ON) else 0
    lam = {x[0]: 0.0 for x in act}
    hits = {x[0]: 0.0 for x in act}   # damage-spell hits expected
    dmg = {x[0]: 0.0 for x in act}    # and their damage
    para = False
    for k, m in M.items():
        r = tactics.rec(g, k)
        mons = [j for j, hp, st in m['mons'] if st < 8]
        n_all = len(mons)
        n_spell = len([j for j in mons if j not in m['silenced']])
        atk = [r[o:o + 10] for o in (0xac, 0xb6, 0xc0)]
        nouns = [struct.unpack_from('<H', a, 0)[0] for a in atk]
        ability = [0x100 <= n < 1621 for n in nouns]
        reach_any = bool((atk[0][7] | atk[1][7]) & tactics.BACK_REACH)
        if not (k > 2 and not g.u8(tactics.FIXED) and not reach_any):
            use1 = ability[1] or (nouns[1] < 0xff or nouns[1] >= 0x8000) and atk[1][3] > 0
            for i, u in ((0, 0.69 if use1 else 1.0), (1, 0.31 if use1 else 0.0), (2, 1.0 if atk[2][3] else 0.0)):
                a = atk[i]
                if not u or ability[i] or not a[3] or not a[8]:
                    continue
                reach = tgt if a[7] & tactics.BACK_REACH else front
                if not reach:
                    continue
                for bit, (kind, idx) in tactics.DIS_HIT.items():
                    if kind != 'para' or not a[7] & bit:
                        continue
                    para = True
                    for slot, raw, lv, hp, ac in act:
                        if not any(x[0] == slot for x in reach):
                            continue
                        T = min(19, max(1, 22 + mapo - ac - (m['level'] // 2 + 1) + (2 if i == 2 else 0)))
                        lam[slot] += (n_all * m['fight_p'] * u * min(11, a[3]) * (20 - T) / 20 * a[8] / 100
                                      * max(0, 99 - raw[0xb0 + idx]) / 100 / len(reach))
        for rate, src, reach in m['dsrc']:
            if src[0] != 'spell' or tactics.DIS_SPELL[src[1]][0] != 'para':
                continue
            para = True
            sid, silenceable = src[1], src[2]
            n = n_spell if silenceable else n_all
            share = 0.5 if tactics.DIS_SPELL[sid][4] == 'row' and rows2 else 1.0
            for slot, raw, lv, hp, ac in act:
                lam[slot] += n * rate * share * tactics.status_lands(raw, lv, sid, m['level'], tbl, screen)
        for rate, sid in m.get('dcast', []):
            mean, kind, _ = tactics.DAMAGE[sid]
            casts = n_spell * rate
            for slot, raw, lv, hp, ac in act:
                land = max(0.0, 1 - min(255, raw[0x87 + tactics.school(sid)] + screen + 1) / 100)
                f = 1.0 / len(tgt) if kind == 'one' else (0.5 if rows2 else 1.0) if kind == 'group' else 1.0
                hits[slot] += casts * f * land
                dmg[slot] += casts * f * land * mean
    if not para:
        return None
    down = {}
    for slot, raw, lv, hp, ac in act:
        h = hits[slot]
        down[slot] = _poisson_ge(h, int(-(-hp * h // dmg[slot]))) if h and dmg[slot] else 0.0
    standing = sum(1 - down[s] for s in lam)
    events = sum(lam[s] * (1 - down[s]) for s in lam)
    # paralysis doesn't wear off (party_upkeep 0x800a73f4), so it compounds: the monsters'
    # next two rounds, less a cure from each Dialko or Madi caster still acting in between
    cures = sum(math.exp(-lam[s]) * (1 - down[s]) for s, raw, lv, hp, ac in act
                if any(c[0] in (tactics.DIALKO, tactics.MADI) for c in castable(g, ids[s])))
    events2 = 2 * events - cures
    return dict(events=round(events, 2), events2=round(events2, 2), cures=round(cures, 2),
                standing=round(standing, 2), rush=events2 >= standing,
                lam={s: round(v, 2) for s, v in lam.items()}, down={s: round(v, 2) for s, v in down.items() if v >= 0.01})


def likely_loss(g, M, party_hp):
    """A fight the party expects to lose, judged at round 1 before anyone acts: the rated
    monster damage a round (tactics.info threat, as matters() sums it) is at least the
    party's HP, and is still at least the party's HP after the party's best round. That
    round: each standing member in turn takes what removes the most threat, given what the
    members before it already did: its best damage spell it has points for (tactics.DAMAGE
    mean x the chance it lands, against each target's HP), or, front row (slots 0-2), its
    weapon (gear.wscore, half landing) at group 1; kills by tactics.value's rule (a kill at
    the monster's HP, half a kill at 70% of it). Returns the numbers when it's a likely
    loss, else None. Actions the monsters take away (tactics.disable, fix 1) stretch both
    sides: the threat counts L times over, before the party's round and again after it with
    the monsters it expects to kill gone; a member already asleep or worse doesn't act."""
    from harness import gear
    # with the records' real odds (tactics.SPELLS_ON) threat is a round's mean, so the bar
    # is two rounds of it; the old rating (every breather breathing every round) one
    rounds = 2 if tactics.SPELLS_ON else 1
    T = sum(M[k]['threat'] * len(M[k]['mons']) for k in M)
    if PARA_RUSH and tactics.SPELLS_ON:
        pr = para_rush(g, M)
        if pr and pr['rush']:
            if PARA_RUSH == 2:
                # test mode: a rush is fought out, never run from (a failed run hands the
                # monsters a free round of Lorks)
                FIGHT_INFO.setdefault('para_rush', []).append((ROUND, pr['events2'], pr['standing']))
                return None
            return dict(threat=round(T), party_hp=party_hp, threat_left=round(T), para=pr)
    mem = members(g)
    M = {k: dict(v) for k, v in M.items()}          # tactics.disable writes dis_hp
    lost = tactics.disable(g, M, mem)
    if T * rounds * lost['L'] < party_hp:
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
        if hp <= 0 or st >= (8 if tactics.LOST_ACTIONS else 0x20):
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
    scale = {t: 1 - sum(_kill(done.get((t, j), 0.0), h) for j, h, _ in M[t]['mons']) / len(M[t]['mons'])
             for t in M if M[t]['mons']}
    lost2 = tactics.disable(g, M, mem, scale)
    if left * rounds * lost2['L'] < party_hp:
        return None
    return dict(threat=round(T), party_hp=party_hp, threat_left=round(left), lost=lost['share'],
                lost_after=lost2['share'])


ITEMS_IN_BATTLE = True      # Chris, 2026-10-14: attack items (scrolls, rods, orbs) in battle, by rule
ITEM_FREE_MARGIN = 1.5      # a flush party's rebuyable consumable in a fight that doesn't matter:
                            # this many times the member's own best action
ITEM_FLUSH_PRICES = 5       # flush: gold over the reserve at least the reserve and this many prices


def item_options(g, ri):
    """The battle Use list of roster index ri: pack items with a battle spell (item +0x1b
    != 0xff), potions and scrolls (+3 = 20, 21) or worn gear, in pack order (f07 probe,
    2026-10-14: Uranus's list was his Latumofis potion,
    Cape of Hide and Demonic Chimes, pack slots 2, 7, 8; screen 81, cursor LIST). Each is a
    dict: idx (list row), k (pack slot), w (word), id, sid, cons (potion or scroll, or a sure
    break into nothing: used up), br (break chance), eq (equipped), stock (Boltac's), price,
    ident."""
    from harness import gear
    out = []
    for k, w in gear.pack(g, ri):
        i = w & 0x1ff
        a = gear.ITEMS + i * 0x4c
        bs = g.u8(a + 0x1b)
        if not i or bs == 0xff:
            continue
        sub, br = g.u8(a + 3), g.u8(a + 0x0e)
        if sub not in (20, 21) and not w & gear.EQUIPPED:
            # the list skips gear that isn't worn (agent 11, n1v3k c9 state: Mercury's two
            # unworn Rings of Jewels weren't on it, his worn Shadow Cloak, potions and
            # scroll were; the scroll's row was 3, not 5, and the cursor stuck)
            continue
        out.append(dict(idx=len(out), k=k, w=w, id=i, sid=bs & 0x7f, br=br, eq=bool(w & gear.EQUIPPED),
                        cons=sub in (20, 21) or (br >= 100 and g.u16(a + 0x10) == 0),
                        stock=g.u8(gear.STOCK + i), price=g.u32(a + 0x12), ident=bool(w & gear.IDENT)))
    return out


def confused_harm(g, k):
    """Whether confused member k can really hurt someone (main, 2026-10-14): two rounds of
    its weapon (gear.wscore; 4 bare-handed) reach the HP of the weakest other member still
    standing. Half its swings go to a random ally in either row (party_melee 0x800a8c2c)."""
    from harness import gear
    ids = party_ids(g)
    w = gear.equipped(g, ids[k]).get(0)
    d = gear.wscore(w) if w else 4
    hp = [member_state(g, j)[0] for j, rj in enumerate(ids) if rj is not None and j != k
          and member_state(g, j)[1] < 0x80 and member_state(g, j)[0] > 0]
    return bool(hp) and 2 * d >= min(hp)


def gear_cures():
    from harness import gear
    return tuple(gear.CURE_SIDS)


def cure_item_choice(g, ri, k, sids=None, harm=True):
    """A Madi or Morfis item on roster index ri's battle Use list, Used on confused member k
    (party slot), or None. Only when k can really hurt someone (confused_harm), and never a
    worn item that can break and that its wearer relies on (a weapon, or gear worth
    something without the cure: the battle-item rule). Logged with the battle items.
    (support) sids: the cures to look for (gear.CURE_SIDS); harm=False skips confused_harm
    (a paralyzed member)."""
    from harness import gear
    if harm and not confused_harm(g, k):
        return None
    eq = gear.equipped(g, ri)
    for it in item_options(g, ri):
        if it['sid'] not in (sids or gear.CURE_SIDS) or not harm and not it['ident']:
            continue
        if it['eq'] and it['br']:
            rec = gear.item(g, it['id'])
            slot = next((s_ for s_, x in eq.items() if x and x['id'] == it['id']), None)
            if rec['cat'] == 0 or slot is None or gear.score(rec, slot) > 0:
                continue
        FIGHT_INFO.setdefault('items', []).append(dict(who=g.char(ri)['name'], ri=ri, item=gear.name(it['id']),
                                                       id=it['id'], k=it['k'], w=it['w'], sid=it['sid'],
                                                       cons=it['cons'], v=None, round=ROUND, cure=k))
        return ('use', it['idx'], it['sid'], it['id'], ('member', k))
    return None


def item_choice(g, ri, me, M, big, best_own):
    """A Use action for an attack item, or None (Chris, 2026-10-14). The item's spell is
    valued as tactics values the spell (resistances, saves, group size; the user's level
    as the caster level). Identified items only. A consumable (potion, scroll, or a sure
    break) in a fight that matters or a likely loss, when it beats the member's own best
    action; a flush party (gold over the reserve by the reserve and ITEM_FLUSH_PRICES of
    its price) uses one the shop sells in any fight at ITEM_FREE_MARGIN times that. Gear
    that can break: only in a likely loss, when no consumable or own action does as well,
    and never a piece someone wears."""
    from harness import gear
    ll = bool(FIGHT_INFO.get('likely_loss'))
    party = [x for x in party_ids(g) if x is not None]
    spare = gear.spare_gold(g, party)
    reserve = gear.RESERVE_PER_LEVEL * max(g.char(x)['level'] for x in party)
    best = None
    for it in item_options(g, ri):
        sid = it['sid']
        if not it['ident'] or not (sid in tactics.DAMAGE or sid in tactics.DEATH or sid in tactics.DISABLE):
            continue
        if it['cons']:
            if big or ll:
                bar = best_own
            elif it['stock'] and spare >= reserve and spare >= ITEM_FLUSH_PRICES * it['price']:
                bar = best_own * ITEM_FREE_MARGIN
            else:
                continue
        elif ll and not it['eq']:
            bar = best_own
        else:
            continue
        for k in M:
            v = tactics.value(g, sid, k, M, me['level'], CAST)
            if v > bar and v >= MIN_SPELL_VALUE:
                key = (it['cons'], v)
                if best is None or key > best[0]:
                    best = (key, it, k, v)
    if not best:
        return None
    _, it, k, v = best
    sid = it['sid']
    CAST[sid] = CAST.get(sid, 0) + 1
    CAST[(sid, k)] = CAST.get((sid, k), 0) + 1
    if PLANNING:
        tactics.value(g, sid, k, M, me['level'], CAST, commit=True)
    FIGHT_INFO.setdefault('items', []).append(dict(who=me['name'], ri=ri, item=gear.name(it['id']), id=it['id'],
                                                   k=it['k'], w=it['w'], sid=sid, cons=it['cons'], v=round(v, 1),
                                                   round=ROUND))
    return ('use', it['idx'], sid, it['id'], ('group', k))


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
            lost0 = tactics.disable(g, M0, members(g))
            FIGHT_INFO['first'] = tactics.matters_detail(g, M0, hp0, lv0[len(lv0) // 2] if lv0 else None, P0, lost0)
            FIGHT_INFO['first']['party_max'] = sum(g.char(rk)['max_hp'] for rk in ids0 if rk is not None)
    if ROUND > RUN_AFTER and RUN in opts and fleeable(g):
        return ('run',)
    # (failrun) after a failed run, fight it out (FIGHT_AFTER_FAILED_RUN): no more runs from a
    # likely loss or a costly walk fight, and the fight gets the likely loss's support plan,
    # heals and items. RUN_AFTER, the stuck-fight valve above, stays.
    no_run = FIGHT_AFTER_FAILED_RUN and run_failed(g)
    if no_run and not FIGHT_INFO.get('likely_loss'):
        FIGHT_INFO['likely_loss'] = dict(failed_run=True, round=ROUND)
    can_run = RUN in opts and not no_run
    if not FLEE_RULE and RUN_WHEN_LOSING and can_run and fleeable(g) and losing(g):
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
    lost = tactics.disable(g, M, members(g))
    FOCUS_M[:] = [ROUND, M]
    why = tactics.matters(g, M, party_hp, lv[len(lv) // 2] if lv else None, party, lost)
    if not why and LONG_FIGHT and M and tactics.SPELLS_ON and party:
        # the weakest member under the monsters' 'fight the weakest' blows (AI column 1):
        # ten level-7 priests put Kai (36 HP, back row) down in two rounds while the fight
        # was rated 22 a round in all (main, 2026-10-14)
        for slot, hp, mx in sorted(party, key=lambda x: x[1])[:1]:
            fo = sum(M[k]['focus'][0 if slot < 3 else 1] * len(M[k]['mons']) for k in M)
            if hp > 0 and hp < FOCUS_ROUNDS * fo:
                why = 'focus'
                FIGHT_INFO['focus'] = (slot, hp, round(fo, 1))
    if not why and LONG_FIGHT and M and long_fight(g, M, party_hp, lost):
        why = 'long fight'
        FIGHT_INFO['long'] = FIGHT_INFO[('long', ROUND)]
    big = bool(why) or bad
    FIGHT_INFO['matters'] = FIGHT_INFO['matters'] or bool(big)
    if (LOSS_RUN and M and FIGHT_INFO.get('loss_checked') != ROUND
            and (LOSS_EVERY_ROUND or not FIGHT_INFO.get('loss_checked'))):
        # anywhere, grinding included: a fight the party expects to lose may be run from, at
        # a flee chance above LOSS_FLEE_ABOVE (Chris, 2026-10-14; FLEE_MIN stays for the walk
        # out and the walk home). Rated at each round's first command (ROUND can read 2 at
        # the fight's first one when that phase is entered twice), from the HP of the members
        # who can still act: asleep, paralyzed, stoned and dead don't count (Chris,
        # 2026-10-14: re-rated every round, not reflex running, only fights rated as lost).
        # flee_chance is 0 where a run can't work (fixed fights, alarms).
        FIGHT_INFO['loss_checked'] = ROUND
        if can_run:
            act_hp = sum(max(h, 0) for h, st in (member_state(g, k) for k, rk in enumerate(ids)
                                                 if rk is not None) if st < 8)
            ll = likely_loss(g, M, act_hp)
            if ll:
                ch = flee_chance(g)
                FIGHT_INFO.setdefault('likely_loss', dict(ll, chance=ch, round=ROUND))
                FIGHT_INFO.setdefault('loss_rounds', []).append((ROUND, ch, ll['threat_left'], act_hp))
                if ch > LOSS_FLEE_ABOVE:
                    FIGHT_INFO.setdefault('runs', []).append((ROUND, ch, 'likely loss'))
                    return ('run',)
    if FLEE_RULE and RUN_OK and can_run:
        # run only where it saves something (on the way to the grinding spot, or home with
        # the casters spent), from a costly fight, at FLEE_MIN or better; the losing state
        # heals and fights (Chris, 2026-10-14)
        many = sum(len(v['mons']) for v in M.values()) >= MANY
        costly = why or many
        if costly and why != 'story' and not bad and tactics.CASTER_FOCUS:
            # (casterfocus) a caster party the party's first round likely clears of its
            # casters isn't costly unless what's left is: the walk out ran from Area B's
            # human parties as 'threat', 'many' and 'long fight' once they stopped being
            # story fights (trip_new_c9_s101), and a failed run hands their Madalto a round
            cr = caster_round(g, M, party_hp)
            if cr and not cr['costly']:
                sk = FIGHT_INFO.setdefault('runs_skipped', [])
                if not sk or sk[-1][0] != ROUND:
                    sk.append((ROUND, why or 'many', cr))
                costly = False
        if costly:
            ch = flee_chance(g)
            if ch >= FLEE_MIN:
                FIGHT_INFO.setdefault('runs', []).append((ROUND, ch, why or 'many'))
                return ('run',)
    if 'first' not in FIGHT_INFO and M:
        # the rating's inputs at the first command phase (brief item 6)
        FIGHT_INFO['first'] = tactics.matters_detail(g, M, party_hp, lv[len(lv) // 2] if lv else None, party, lost)
        FIGHT_INFO['first']['party_max'] = sum(g.char(rk)['max_hp'] for rk in ids if rk is not None)
    # support spells (the party's AC and magic screen, the monsters' AC) and spell levels
    # 6-7 only in a story or boss fight or one that's going badly (Chris, 2026-10-14):
    # someone down or the party under 45% (losing), or monsters that could take half the
    # party's HP in two rounds (smoke2, 2026-10-14: Area B's five-member human party, rated
    # cheap, wiped a level-14 party in 8 rounds that Tiltowait had beaten with one loss)
    boss = why in (tactics.HEAVY if CHEAPEST else ('story',)) or bad
    if HEAL_WORTH and FIGHT_INFO.get('likely_loss'):
        boss = True                     # (bossfight) a likely loss gets what a boss does
    # (bossfight) a fight that matters against casters of kill rank 0 (Tiltowait-class
    # damage, Bakadi, Katiqurea: tactics.kill_rank) gets a boss's Cortu and turn choice
    # too (n1v6t chapter 14: Area D's human parties, Blaze's Tiltowait and the
    # MadPsionic's Lasios and Galtomas, wiped the party as random fights)
    casters_boss = boss or (CASTER_BOSS and big and any(tactics.kill_rank(v, KILL_FIRST) == 0 for v in M.values()))
    # (support) buffs and debuffs only in the special fights (Chris, 2026-10-16): a story or
    # boss fight met outside a training trip (or on a chapter's BOSS_AT square), or one rated
    # a likely loss; ordinary fights, a training trip's fixed fight squares and fights merely
    # going badly (losing) play as before. And not when the plain plan wins quickly anyway.
    special = SUPPORT and bool(M) and (why == 'story' and (not tactics.TRAINING or tactics.at_boss(g))
                                       or bool(FIGHT_INFO.get('likely_loss')))
    sup = support_plan(g, M) if special else None
    if sup and sup['quick']:
        sup = None
    # heal: (d) a member who couldn't survive another hit of the worst monster that
    # reaches them, or anyone below 40%; the cheapest heal that lifts them clear of it,
    # else the strongest there is
    hurt = []
    risk = {s_: b for s_, h, b in tactics.danger(g, M, party)} if HEAL_RISK else {}
    if HEAL_WORTH and big and M:
        # (bossfight) in a fight that matters a heal has to be worth the turn (Chris,
        # 2026-10-15: "If I'm in battle, and my characters are level 15+, I'm not going to
        # be spending my time casting small heals... it's hardly worth a turn, at that
        # level, in a battle that critical"): only for a member likely to die this round
        # (HP below what they're expected to lose, tactics.incoming), with a heal that
        # keeps them above it and is at least HEAL_SHARE of it; the cheapest such heal,
        # the most hurt such member. Otherwise the turn goes to offense or protection
        # (n1v0w's four losses at chapter 13's Guardians: Dial nearly every round from the
        # Bishop, Madi and Dialma from the Priest, against Tiltowait at ~80 a member).
        act = heal_worth(g, M, party, by_id)
        if act:
            return act
    elif not HEAL_RISK:
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
    # a confused member's stray blows kill allies in any fight, so their cure doesn't wait
    # for the fight to matter. Any row: half a confused member's swings go to a random ally
    # in either row, and the reach check passes for the party (party_melee 0x800a8c2c), so
    # a back-row member with a short weapon still hits allies (main, 2026-10-14)
    wild = any(rk is not None and member_state(g, k)[1] & 0x02 and member_state(g, k)[1] < 0x80
               for k, rk in enumerate(ids))
    if (big or wild) and len(M):
        for k, rk in enumerate(ids):
            if rk is None or k == m:
                continue
            st = member_state(g, k)[1]
            if st >= 0x80:
                continue
            # a confused member (0x02) too: half their blows go to a random target,
            # allies included (party_melee 0x800a8c2c), for about 13 rounds (counter 127,
            # -10 a round); in battle only Madi (spell_madi 0x800ae6e8: status cleared
            # below 0x80) and Morfis (party) cure it, Dialko doesn't (0x38 only,
            # FUN_800b2974). n1v1m chapter 9: confused Dax killed Uranus twice.
            for sid, bits in ((tactics.DIALKO, 0x28), (tactics.MADI, 0x6a)):
                if st & bits and sid in by_id and CAST.get(('cure', k), 0) < ROUND:
                    CAST[('cure', k)] = ROUND
                    c = by_id[sid]
                    return ('spell', sid, c[1], c[2], c[3], ('member', k))
            if special and st & 0x28 and USE in opts and CAST.get(('cure', k), 0) < ROUND:
                # (support) a Dialko potion or a Madi or Morfis item on the paralyzed or
                # asleep, where this member has no spell for it (crystal_policy's Thief)
                act = cure_item_choice(g, ri, k, sids=(tactics.DIALKO,) + gear_cures(), harm=False)
                if act:
                    CAST[('cure', k)] = ROUND
                    return act
            if st & 0x02 and USE in opts and CAST.get(('cure', k), 0) < ROUND:
                act = cure_item_choice(g, ri, k)
                if act:
                    CAST[('cure', k)] = ROUND
                    return act
    # every spell and target, valued in hit points (tactics.py): in a fight that doesn't
    # matter, nothing above CHEAP_LEVEL and no support spells, and a healer keeps the last
    # point of a level holding a heal they know
    rec = me['raw']
    cands = []
    finish = []         # (casterfocus) spells above CHEAP_LEVEL in a cheap fight, for focus_pick only
    sup_ok = {}         # (support) support spells past the point rules, for support_cands
    for sid, c in by_id.items():
        sch, lv = c[1], c[2]
        capped = False
        if not big:
            if lv > tactics.CHEAP_LEVEL:
                # (casterfocus) a caster group a level 4-5 spell kills this round is worth
                # that point even in a fight that doesn't matter (Tzalik at a lone Lorks
                # caster, where Mahalito and Montino took three rounds)
                if not (tactics.CASTER_FOCUS and lv < KEEP_LEVEL
                        and (sid in tactics.DAMAGE or sid in tactics.DEATH)):
                    continue
                capped = True
        elif CHEAPEST and lv >= KEEP_LEVEL and not boss:
            continue                    # (c) levels 6-7 wait for bosses and bad fights
        keep = BOSS_KEEP.get(ri, {}).get((sch, lv), 0)
        if keep and why != 'story' and not bad and rec[0x5c + sch * 7 + lv - 1] <= keep:
            continue                    # the boss's points (BOSS_KEEP)
        if rec[0x5c + sch * 7 + lv - 1] <= 1 and (not boss if CHEAPEST else not big) and any(
                h in tactics.HEALS for h in known_spells(rec, sch, lv)):
            continue
        if sid in tactics.DAMAGE or sid in tactics.DEATH or sid in tactics.DISABLE:
            for k in M:
                v = tactics.value(g, sid, k, M, me['level'], CAST)
                if v > 0:
                    (finish if capped else cands).append((v, ('spell', sid, sch, lv, c[3], ('group', k)), (sid, k), lv))
        elif casters_boss and sid == tactics.CORTU and tactics.CORTU_SCREEN:
            v = (tactics.cortu_value(g, M, me['level'], min(CORTU_SUP_ROUNDS, max(tactics.CORTU_ROUNDS, sup['horizon'])),
                                     drain=True) if sup
                 else tactics.cortu_value(g, M, me['level']))
            if v > 0 and M:
                cands.append((v, ('spell', sid, sch, lv, c[3], ('group', min(M))), (sid, None), lv))
        elif special and sid in SUPPORT_SIDS:
            if sup:
                sup_ok[sid] = c         # (support) valued in support_cands; none in a quick win
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
    if sup:
        cands += support_cands(g, m, ri, me, sup_ok, M, sup, opts)
    if DISPEL in opts:
        for k in M:
            v = tactics.dispel_value(g, k, M, me['cls'], me['level'])
            if v > 0:
                cands.append((v, ('dispel', ('group', k)), ('dispel', k), 0))
    fight_v = 3 * me['level'] if FIGHT in opts else 0
    if big and m >= 3 and FIGHT in opts:
        # (fix 2) a back-row member's Fight is its weapon's reach and damage, not its
        # level: in the n1v1 chapter 8 near-wipe the Mage and the Bishop, rated 33 for
        # a Fight, never cast at the 18 Nightmares
        from harness import gear
        w = gear.equipped(g, ri).get(0)
        fight_v = gear.wscore(w) * 0.5 if w and gear.back_reach(w) else 0
    if sup and FIGHT_REAL and m < 3 and FIGHT in opts:
        # (support) once the stack lands a front-liner's blows are worth more than 3 x level
        # (crystal_policy's Venus fights after the stack)
        fight_v = max(fight_v, max([tactics.member_melee(g, m, k, M) for k in M] + [0.0]))
    if sup and sup['stacks'] and STACK_FIRST:
        # (support) the stack is the plan (support_plan's simulation: it takes rounds off
        # killing the group), so a stack cast still needed goes ahead of this member's damage
        # spells and its Fight; Cortu, the party's AC and heals still weigh in by value (the
        # threat behind the stack's worth leaves out what kills outright, the Crystal Men's
        # decapitating beams)
        covered = CORTU_COVER and tactics.screen_now(g) >= 2 * me['level']
        other = max([c_[0] for c_ in cands if c_[2][0] not in SUPPORT_SIDS
                     and (c_[2][0] != tactics.CORTU or covered)] + [fight_v]) + 1
        # (bench 2) plus a hundredth of their own value, so Morlis's 4 points still beat
        # Dilto's 2 (bench 1's max(v, other) tied them, and Dilto came first)
        cands = [(max(v, other) + v / 100 if STACK_V.get((m, key[0], key[1]), 0) > 0 else v, act, key, lv)
                 for v, act, key, lv in cands]
    if ITEMS_IN_BATTLE and USE in opts and M:
        best_own = max([c_[0] for c_ in cands] + [fight_v])
        it_act = item_choice(g, ri, me, M, big, best_own)
        if it_act:
            return it_act
    fp = focus_pick(g, m, me, M, cands + finish, opts) if tactics.CASTER_FOCUS and M and (cands or finish) else None
    if fp and fp not in ('fight', 'cheap') and not cands:
        cands = [fp]
    if cands:
        cands.sort(key=lambda x: -x[0])
        pick_ = cands[0]
        if fp == 'fight':
            return ('fight',)
        if fp == 'cheap':
            # (casterfocus) the caster groups are likely dead this round already: what's
            # left is a fight without them, so no spells above CHEAP_LEVEL for it (a
            # Tiltowait after Badi and Tzalik had the casters, pf_c9_s101/f05), unless
            # it's a story fight or going badly
            fp = None
            # and spells valued without the groups the members before have likely killed
            # (Montino twice at a lone mage the Fighter's blows were taking,
            # trip_new_c9_s101)
            M2 = {k: v for k, v in M.items() if tactics.dead_p(k, v) < tactics.DONE_P}
            c2 = []
            for v, act, key, lv in cands:
                if key[1] is not None and key[1] not in M2:
                    continue
                if key[0] in tactics.DAMAGE or key[0] in tactics.DEATH or key[0] in tactics.DISABLE:
                    v = tactics.value(g, key[0], key[1], M2, me['level'], CAST)
                if v > 0:
                    c2.append((v, act, key, lv))
            cands = sorted(c2, key=lambda x: -x[0])
            if not (why == 'story' or bad):
                cands = [c_ for c_ in cands if c_[3] <= tactics.CHEAP_LEVEL]
            if not cands:
                return ('fight',) if FIGHT in opts else ('parry',) if PARRY in opts else ('first',)
            pick_ = cands[0]
        if fp and casters_boss and HEAL_WORTH and fp[0] < BOSS_FOCUS_SHARE * cands[0][0]:
            # (bossfight) in a boss fight or a likely loss the cheap finisher doesn't
            # stand against a much better turn: Tzalik to finish an Arch Priest left
            # chapter 13's Arch Mage casting Tiltowait into a thin magic screen
            fp = None
        if fp:
            pick_ = fp
        elif CHEAPEST and big and not boss:
            # (c) the cheapest spell that does most of what the best one would
            ok = [c_ for c_ in cands if c_[0] >= CHEAP_SHARE * cands[0][0]]
            pick_ = min(ok, key=lambda c_: (c_[3], -c_[0]))
        if not fp and len(cands) > 1 and _vary():
            pick_ = cands[1]
        v, act, key, _ = pick_
        if fp or v > fight_v and (v >= MIN_SPELL_VALUE or big):
            CAST[key[0]] = CAST.get(key[0], 0) + 1
            if key[1] is not None:
                CAST[key] = CAST.get(key, 0) + 1
            if PLANNING and (key[0] in tactics.DAMAGE or key[0] in tactics.DEATH or key[0] in tactics.DISABLE):
                tactics.value(g, key[0], key[1], M, me['level'], CAST, commit=True)
            if tactics.CASTER_FOCUS and key[1] is not None and key[0] != 'dispel':
                tactics.focus_commit(g, key[0], key[1], M, me['level'])
            if key[0] == tactics.CORTU and tactics.CORTU_SCREEN:
                tactics.cortu_commit(g, me['level'])
            if sup and key[0] in SUPPORT_SIDS:
                support_commit(m, key[0], key[1], g, M)
            return act
    if FIGHT in opts:
        return ('fight',)
    return ('parry',) if PARRY in opts else ('first',)


# (chapter 16) fight-specific policies by the square the fight starts on (area, x, y):
# battle.fight uses one in place of default_policy there, while FIGHT_POLICIES is on
FIGHT_POLICIES = True
POLICY_AT = {}

# (chapter 16) the Crystal Men at Area A B2's altar: AC -30, Mage 30% / Priest 70%
# resistant, death-immune, five 6-swing eye beams (25% decapitation) and 3-swing hand rays
# (40% paralysis) that reach the back row, Labadi. Party to-hit on group 1 is
# T = 50 + AC modifier - to-hit, held to 19 (5% a swing): Dax (28) needs the modifier
# below -3 to hit more, Uranus (24) below -7. Each Morlis (-4 a monster, Mage, nullified
# per monster) or Dilto (-2, never nullified) past that adds 10-20% a swing for the three
# front-liners for the rest of the fight. Monster to-hit on the party is
# 11 - AC + AC modifier with Maporfic on, also held to 19: Bamatu (+3) until every member
# is at the cap; past it, nothing lowers their hits further. So: stack the AC
# modifier down, keep the magic screen (Cortu) up against Labadi, Madi the Labadi'd and
# the paralyzed, potions of Dial (Dialko) from the Thief.
CM_STACK_TO = -24       # stack Morlis/Dilto until the standing monsters' mean modifier is this
CM_CORTU_BELOW = 30     # a Cortu when the party's screen (this round's casts counted) is below this
CM_CORTU_FIRST = 0      # Venus opens with Cortu (1); 0 opens on the AC stack
CM_HEAL_HP = 30         # Madi a member at or below this many HP (or CM_HEAL_FRAC of max)
CM_HEAL_FRAC = 0.3
CM_MAPOBA = 1           # the Thief reads the Scroll of Mapoba in round 1
CM_MORLIS = 1           # Morlis before Dilto (0: Dilto only)
CM_VENUS_AFTER = 'fight'  # Venus once the stack is done: 'fight' or 'spell' (Madalto)
CM_PARTY_CAP = 1        # Bamatu until every member's monster to-hit threshold is held to 19
CM_PLAN = dict(round=None, mod=0.0, screen=None)


def _cm_mods(g, k):
    """[(member, HP, AC modifier)] of group k's standing monsters."""
    out = []
    for j, h, st in tactics.info(g, k)['mons']:
        c = g.e.read(COMBAT + k * 0x7e + j * 0xe, 0xe)
        out.append((j, h, struct.unpack_from('<b', c, 4)[0]))
    return out


def _cm_party_mod(g, s):
    return struct.unpack_from('<b', g.e.read(COMBAT + s * 0xe, 0xe), 4)[0]


def crystal_policy(g, m, opts):
    """The Crystal Men's fight (chapter 16): see CM_STACK_TO and the notes above it.
    Anything it has no rule for goes to default_policy."""
    ids = party_ids(g)
    ri = ids[m]
    me = g.char(ri)
    M = {k: tactics.info(g, k) for k in tactics.groups(g)}
    M = {k: v for k, v in M.items() if v['mons']}
    if not M:
        return default_policy(g, m, opts)
    k = min(M)
    mods = _cm_mods(g, k)
    if CM_PLAN['round'] != ROUND:
        CM_PLAN.update(round=ROUND, mod=0.0, screen=g.u8(tactics.PARTY_SCREEN), bamatu=0)
        FIGHT_INFO.setdefault('cm', []).append(dict(
            r=ROUND, mons=[(h, a) for _, h, a in mods], screen=g.u8(tactics.PARTY_SCREEN),
            party=[(member_state(g, s)[0], member_state(g, s)[1], _cm_party_mod(g, s))
                   for s, r_ in enumerate(ids) if r_ is not None]))
    cast = castable(g, ri) if SPELL in opts else []
    by_id = {c[0]: c for c in cast}

    def spell(sid, target):
        c = by_id[sid]
        CAST[sid] = CAST.get(sid, 0) + 1
        return ('spell', sid, c[1], c[2], c[3], target)
    mean_mod = sum(a for _, _, a in mods) / len(mods) + CM_PLAN['mod']
    # members: (slot, HP, status, max HP, AC) for the living
    party = []
    for s, r_ in enumerate(ids):
        if r_ is None:
            continue
        h, st = member_state(g, s)
        if st & 0x3c0 or h <= 0:
            continue
        c_ = g.char(r_)
        party.append((s, h, st, c_['max_hp'], struct.unpack_from('<b', c_['raw'], 0x86)[0]))
    mapo = 2 if g.u8(MAPORFIC_ON) else 0
    # the members a monster's swing still hits more than 5% of the time
    uncapped = [s for s, h, st, mx, ac in party
                if 22 + mapo - ac + _cm_party_mod(g, s) + 3 * CM_PLAN['bamatu'] - 13 < 19]
    low = sorted((h / mx, s) for s, h, st, mx, ac in party
                 if (h <= CM_HEAL_HP or h <= CM_HEAL_FRAC * mx) and CAST.get(('healed', s), -1) != ROUND)
    para = [s for s, h, st, mx, ac in party if st & 0x28 and CAST.get(('cure', s), -1) != ROUND]
    is_cls = me['cls']
    # the healer (a Priest): Madi on the most hurt, then the paralyzed (Dialko, Madi, the
    # Staff of Curing's Morfis for two or more), then Bamatu to the cap
    if is_cls == 2:
        if low and 36 in by_id:
            CAST[('healed', low[0][1])] = ROUND
            CAST[('cure', low[0][1])] = ROUND
            return spell(36, ('member', low[0][1]))
        if len(para) >= 2 and USE in opts:
            for it in item_options(g, ri):
                if it['sid'] == 56:
                    for s in para:
                        CAST[('cure', s)] = ROUND
                    return ('use', it['idx'], 56, it['id'], ('group', k))
        if para:
            for sid in (tactics.DIALKO, tactics.MADI):
                if sid in by_id:
                    CAST[('cure', para[0])] = ROUND
                    return spell(sid, ('member', para[0]))
        if CM_PARTY_CAP and uncapped and tactics.BAMATU in by_id:
            CM_PLAN['bamatu'] += 1
            return spell(tactics.BAMATU, ('group', k))
        return ('fight',) if FIGHT in opts else ('parry',)
    # the Thief: Mapoba in round 1, then Dialko potions on the paralyzed
    if is_cls == 3:
        its = item_options(g, ri) if USE in opts else []
        if CM_MAPOBA and not CAST.get('cm_mapoba'):
            for it in its:
                if it['sid'] == 70:
                    CAST['cm_mapoba'] = 1
                    CM_PLAN['mod'] -= 2
                    return ('use', it['idx'], 70, it['id'], ('group', k))
        if para:
            for it in its:
                if it['sid'] == tactics.DIALKO:
                    CAST[('cure', para[0])] = ROUND
                    return ('use', it['idx'], it['sid'], it['id'], ('member', para[0]))
        return ('parry',) if PARRY in opts else ('first',)
    # the mages (Venus, Eve): Cortu below CM_CORTU_BELOW, the AC stack, then damage
    if by_id and any(sid in by_id for sid in (tactics.CORTU, tactics.MORLIS, tactics.DILTO)):
        scr = CM_PLAN['screen']
        first_cortu = CM_CORTU_FIRST and ROUND == 1 and is_cls != 0xb
        if tactics.CORTU in by_id and (first_cortu or scr < CM_CORTU_BELOW):
            CM_PLAN['screen'] = min(90, 0.75 * scr + 2 * me['level'])
            return spell(tactics.CORTU, ('group', k))
        # the Bishop: Bamatu when the healer can't (dead) and the party isn't capped
        if is_cls == 0xb and CM_PARTY_CAP and uncapped and tactics.BAMATU in by_id and not any(
                g.char(ids[s])['cls'] == 2 for s, *_ in party):
            CM_PLAN['bamatu'] += 1
            return spell(tactics.BAMATU, ('group', k))
        if mean_mod > CM_STACK_TO:
            if CM_MORLIS and tactics.MORLIS in by_id:
                CM_PLAN['mod'] -= 4 * (1 - M[k]['mr'][0] / 100)
                return spell(tactics.MORLIS, ('group', k))
            if tactics.DILTO in by_id:
                CM_PLAN['mod'] -= 2
                return spell(tactics.DILTO, ('group', k))
        if m < 3 and CM_VENUS_AFTER == 'fight' and FIGHT in opts:
            return ('fight',)
        for sid in (13, 10, 9):          # Madalto, Lahalito, Tzalik
            if sid in by_id:
                return spell(sid, ('group', k))
    if FIGHT in opts:
        return ('fight',)
    return default_policy(g, m, opts)


# (support) Buffs and debuffs in the fights that need them (Chris, 2026-10-16: they can
# decide a fight, especially in later chapters, where the player is expected to use every
# advantage). crystal_policy showed the way at chapter 16's Crystal Men (0 of 40 wins under
# the old default, 39 of 40 with it): no extra damage, but Morlis and Dilto stacked until
# the front line hit their AC -30, Bamatu and Mapoba until the monsters' swings sat at the
# 5% floor, Cortu against Labadi, and Madi and Dialko for the drained and the paralyzed.
# Here the same ideas are valued from what RAM gives, in a story or boss fight, one going
# badly or a likely loss (default_policy's boss), and only when the party's plain plan
# (support_plan) needs more than SUPPORT_QUICK rounds:
#   - the enemy AC stack (Morlis -4 a monster past mage resistance, Dilto -2, Mapoba -2 on
#     every group), on a group where the front line's melee is under STACK_FLOOR of what
#     it would be with every swing at 95% (tactics.member_melee with dmod), up to STACK_TO
#     of it, when simulating the fight with the stack (_sim) takes STACK_SAVE rounds or more
#     off killing the group: worth the rounds saved times the threat those rounds carry
#     (the group's at STACK_LEFT, it dies down, and the other groups' in full), shared
#     over the AC points the stack needs;
#   - the party's AC (Bamatu +3, Mapoba +2, Maporfic, Porfic +4 the caster): the monsters'
#     melee it takes off (tactics.melee_in) times the rounds left (horizon);
#   - Cortu: tactics.cortu_value over the same horizon instead of CORTU_ROUNDS;
#   - Dialko, Madi and Morfis items on the paralyzed and asleep, where no one's spell does.
SUPPORT = True
SUPPORT_QUICK = 2.0     # a fight the plain plan wins in this many rounds or fewer gets no buffs
SUPPORT_HORIZON = 8.0   # rounds a lasting buff is counted over at most
SIM_CAP = 20            # _sim gives up here (a fight the party can't win as it fights)
STACK_FLOOR = 0.3       # stack a group's AC when the party's melee on it is under this share of its most
STACK_TO = 0.9          # ... up to this share
STACK_SAVE = 1.0        # ... when the stack takes this many rounds or more off killing the group
STACK_LEFT = 0.5        # the stacked group's threat share counted in the rounds saved
STACK_DMAX = 48         # AC points the stack looks down to
MAPOBA = 70
SUPPORT_SIDS = (tactics.BAMATU, tactics.MAPORFIC, tactics.PORFIC, tactics.DILTO, tactics.MORLIS, MAPOBA,
                tactics.BADUMAS)
SPLAN = dict(round=None, by={})     # this round's support chosen so far: slot -> (sid, k)
STACK_V = {}            # (slot, sid, k) -> the AC-stack part of support_value's last rating
CORTU_SUP_ROUNDS = 5.0  # Cortu's horizon in a support fight at most (test fight: 10 Cortus over 8 rounds)
FIGHT_REAL = True       # in a support fight a front-liner's Fight is rated at its real melee (member_melee)
STACK_FIRST = True      # a stack cast the plan wants outranks the member's damage and its Fight
STACK_KEEP = 0.0        # (bench 2) a stack begun stays in the plan while it saves more rounds than this
                        # (STACK_SAVE is for starting one; bench 1: stacks dropped at -12 of -24 when the
                        # plain plan's rounds fell to 4-5, and Madalto went on at AC still near the floor)
STACK_NEAR = True       # (bench 2) while the front line's melee on the group is under STACK_FLOOR of its
                        # most, the group's threat counts in full in the rounds saved (it isn't dying down)
CORTU_COVER = True      # (bench 2) with a stack in the plan, Cortu goes ahead of a stack cast only while
                        # the screen (this round's casts counted) is below what one cast of the caster's
                        # puts up from nothing (2 x level); bench 1: 7 Cortus a fight against crystal's 3


def _spell_dmg(g, sid, k, M, clevel):
    """One cast of a damage or death spell on group k: its expected damage there (the
    chance it lands, the element, each monster's HP as the cap)."""
    m = M[k]
    if sid in tactics.DAMAGE:
        mean, kind, el = tactics.DAMAGE[sid]
        f = 0.5 if m['resist'] & el and el else 2.0 if m['weak'] & el and el else 1.0
        mons = m['mons'][:1] if kind == 'one' else m['mons']
        return tactics.lands(m, sid) * sum(min(mean * f, h) for _, h, _ in mons)
    if sid in tactics.DEATH:
        mons = m['mons'][:1] if tactics.DEATH[sid][0] == 'one' else m['mons']
        return tactics.death_p(m, sid, clevel) * sum(h for _, h, _ in mons)
    return 0.0


def _use_ok(it):
    """A battle item support may Use: identified, and used up (potion, scroll) or never
    breaking."""
    return it['ident'] and (it['cons'] or not it['br'])


def _sim_members(g, M):
    """The members who can act, for _sim: their melee group (the lowest their weapon
    reaches), melee there now, damage and death spells as (damage on each group, school,
    level), spell points by (school, level), and their enemy-AC debuffs as (AC points on
    each group, school, level), Mapoba items as ('item', index)."""
    out = []
    for slot, ri in enumerate(party_ids(g)):
        if ri is None:
            continue
        hp, st = member_state(g, slot)
        if hp <= 0 or st >= 8:
            continue
        c = g.char(ri)
        rec = c['raw']
        own, mel = None, 0.0
        for k in sorted(M):
            x = tactics.member_melee(g, slot, k, M)
            if x > 0:
                own, mel = k, x
                break
        spells, deb, pts = [], [], {}
        for sid, school, level, i in castable(g, ri):
            pts[(school, level)] = rec[0x5c + school * 7 + level - 1]
            if sid in tactics.DAMAGE or sid in tactics.DEATH:
                spells.append(({k: _spell_dmg(g, sid, k, M, c['level']) for k in M}, school, level))
            elif sid == tactics.MORLIS:
                deb.append(({k: 4 * tactics.lands(M[k], sid) for k in M}, school, level))
            elif sid == tactics.DILTO:
                deb.append(({k: 2.0 for k in M}, school, level))
            elif sid == MAPOBA:
                deb.append(({k: 2.0 for k in M}, school, level))
        items = 0
        for it in item_options(g, ri):
            if it['sid'] == MAPOBA and _use_ok(it):
                items += 1 if it['cons'] else SIM_CAP
        out.append(dict(slot=slot, own=own, mel=mel, curve=None, spells=spells, deb=deb, pts=pts, items=items))
    return out


def _curve(g, x, k, M):
    """Member x's melee on group k with the group's AC modifier d points lower, d = 0..STACK_DMAX."""
    if x['curve'] is None or x['curve'][0] != k:
        if x['own'] != k:
            x['curve'] = (k, [0.0] * (STACK_DMAX + 1))
        else:
            x['curve'] = (k, [tactics.member_melee(g, x['slot'], k, M, dmod=-d) for d in range(STACK_DMAX + 1)])
    return x['curve'][1]


def _sim(g, mem, M, k, target=0, stack=False):
    """Rounds the party needs to take group k's HP (all groups' when k is None), fractional,
    SIM_CAP when it doesn't: each member who can act, in turn each round, takes its melee
    (at the stack reached so far) or its best spell it still has points for, whichever does
    more; with stack, the members with a debuff cast it first while the AC points so far
    are short of target, at the most points a cast."""
    H = sum(tactics.group_hp(M[t]) for t in (M if k is None else [k]))
    if H <= 0:
        return 0.0
    pts = [dict(x['pts']) for x in mem]
    items = [x['items'] for x in mem]
    d = 0.0
    for r in range(1, SIM_CAP + 1):
        dmg, dd = 0.0, 0.0
        for i, x in enumerate(mem):
            if stack and d + dd < target:
                best = None
                for steps, school, level in x['deb']:
                    if pts[i].get((school, level), 0) > 0 and (best is None or steps[k] > best[0]):
                        best = (steps[k], (school, level))
                if items[i] and (best is None or 2.0 > best[0]):
                    best = (2.0, None)
                if best and best[0] > 0:
                    dd += best[0]
                    if best[1] is None:
                        items[i] -= 1
                    else:
                        pts[i][best[1]] -= 1
                    continue
            if k is None:
                mel = x['mel']
            else:
                mel = _curve(g, x, k, M)[min(STACK_DMAX, int(d))] if x['own'] == k else 0.0
            best = (mel, None)
            for dk, school, level in x['spells']:
                v = max(dk.values()) if k is None else dk[k]
                if v > best[0] and pts[i].get((school, level), 0) > 0:
                    best = (v, (school, level))
            if best[1]:
                pts[i][best[1]] -= 1
            dmg += best[0]
        d += dd
        if dmg >= H:
            return r - 1 + H / dmg
        H -= dmg
    return float(SIM_CAP)


def support_plan(g, M):
    """(support) This round's plan, once a round (FIGHT_INFO): R the rounds the plain plan
    needs to clear the fight (_sim), quick when that's SUPPORT_QUICK or fewer; stacks
    {group: dict(target AC points, rounds saved, vpt the worth of an AC point)} for the
    groups worth an AC stack; horizon, the rounds a lasting buff is counted over."""
    key = ('support', ROUND)
    if key in FIGHT_INFO:
        return FIGHT_INFO[key]
    mem = _sim_members(g, M)
    R = _sim(g, mem, M, None)
    plan = dict(R=round(R, 1), quick=R <= SUPPORT_QUICK, stacks={})
    if not plan['quick']:
        threat = {k: (tactics.danger_of(M[k]) + M[k].get('threat_drain', 0.0)) * len(M[k]['mons']) for k in M}
        for k in sorted(M):
            if not any(x['own'] == k for x in mem) or not any(x['deb'] or x['items'] for x in mem):
                continue
            f = [sum(v) for v in zip(*[_curve(g, x, k, M) for x in mem if x['own'] == k])]
            # a stack begun (on this monster id) goes on to STACK_TO; a new one starts only
            # near the floor (test fight: it stopped at 67 of 368 once past the floor share)
            begun = M[k]['id'] in FIGHT_INFO.get('stacked', ())
            if not f or f[-1] <= 0 or f[0] >= (STACK_TO if begun else STACK_FLOOR) * f[-1]:
                continue
            target = next(d for d, v in enumerate(f) if v >= STACK_TO * f[-1])
            r0 = _sim(g, mem, M, k)
            r1 = _sim(g, mem, M, k, target, stack=True)
            saved = r0 - r1
            if target <= 0 or saved <= STACK_KEEP or saved < STACK_SAVE and not begun:
                plan.setdefault('dropped', {})[k] = (target, round(r0, 1), round(r1, 1), round(f[0]), round(f[-1]))
                continue
            near = STACK_NEAR and f[0] < STACK_FLOOR * f[-1]
            worth = saved * ((1.0 if near else STACK_LEFT) * threat[k] + sum(v for t, v in threat.items() if t != k))
            FIGHT_INFO.setdefault('stacked', set()).add(M[k]['id'])
            plan['stacks'][k] = dict(target=target, r0=round(r0, 1), r1=round(r1, 1),
                                     melee=(round(f[0]), round(f[target]), round(f[-1])),
                                     vpt=worth / target, near=near)
    saved = max([s_['r0'] - s_['r1'] for s_ in plan['stacks'].values()] + [0])
    plan['horizon'] = min(SUPPORT_HORIZON, max(0.0, R - saved - 0.5))
    FIGHT_INFO[key] = plan
    FIGHT_INFO.setdefault('support', []).append(dict(r=ROUND, R=plan['R'], quick=plan['quick'],
                                                     horizon=round(plan['horizon'], 1),
                                                     stacks={k: dict(v, vpt=round(v['vpt'], 1))
                                                             for k, v in plan['stacks'].items()},
                                                     dropped=plan.get('dropped')))
    return plan


def _splan(m):
    """This round's support chosen by the members before m: (enemy AC points by group,
    party AC modifier by slot, Maporfic cast)."""
    if SPLAN['round'] != ROUND:
        SPLAN.update(round=ROUND, by={})
    acm, pm, mapo = {}, {}, False
    for slot, (sid, k, e) in SPLAN['by'].items():
        if slot == m:
            continue
        for t, v in e.get('ac', {}).items():
            acm[t] = acm.get(t, 0.0) + v
        for t, v in e.get('party', {}).items():
            pm[t] = pm.get(t, 0) + v
        mapo = mapo or e.get('mapo', False)
    return acm, pm, mapo


def _support_effect(g, m, sid, k, M):
    """What a support cast does: enemy AC points by group, party AC modifier by slot, Maporfic."""
    slots = [s_ for s_, ri in enumerate(party_ids(g)) if ri is not None]
    if sid == tactics.MORLIS:
        return dict(ac={k: 4 * tactics.lands(M[k], sid)})
    if sid == tactics.DILTO:
        return dict(ac={k: 2.0})
    if sid == MAPOBA:
        return dict(ac={t: 2.0 for t in M}, party={s_: 2 for s_ in slots})
    if sid == tactics.BAMATU:
        return dict(party={s_: 3 for s_ in slots})
    if sid == tactics.PORFIC:
        return dict(party={m: 4})
    if sid == tactics.MAPORFIC:
        return dict(mapo=True)
    return {}


def support_value(g, m, sid, k, M, plan):
    """(support) What support spell sid on group k (None: the party) is worth this round,
    in hit points, after what the members before m chose (SPLAN)."""
    acm, pm, mapo = _splan(m)
    e = _support_effect(g, m, sid, k, M)
    v = 0.0
    for t, pts_ in e.get('ac', {}).items():
        st = plan['stacks'].get(t)
        if st:
            v += st['vpt'] * max(0.0, min(pts_, st['target'] - acm.get(t, 0.0)))
    STACK_V[(m, sid, k)] = v
    if e.get('party') or e.get('mapo'):
        on = bool(g.u8(MAPORFIC_ON)) or mapo
        if e.get('mapo') and on:
            return v
        base = tactics.melee_in(g, M, pm, on)
        pm2 = dict(pm)
        for t, x in e.get('party', {}).items():
            pm2[t] = pm2.get(t, 0) + x
        v += (base - tactics.melee_in(g, M, pm2, on or e.get('mapo', False))) * plan['horizon']
    if sid == tactics.BADUMAS:
        v = tactics.armor_value(g, sid, k, M, CAST)
    return v


def support_commit(m, sid, k, g, M):
    SPLAN['by'][m] = (sid, k, _support_effect(g, m, sid, k, M))


def support_cands(g, m, ri, me, by_id, M, plan, opts):
    """(support) The candidates default_policy weighs for support spells and items:
    (value, action, key, level)."""
    out = []
    for sid in SUPPORT_SIDS:
        if sid not in by_id:
            continue
        c = by_id[sid]
        for k in (sorted(M) if sid in (tactics.MORLIS, tactics.DILTO, tactics.BADUMAS) else [min(M)]):
            v = support_value(g, m, sid, k, M, plan)
            if v > 0:
                out.append((v, ('spell', sid, c[1], c[2], c[3], ('group', k)), (sid, k), c[2]))
    if USE in opts:
        seen = set()
        for it in item_options(g, ri):
            sid = it['sid']
            if sid not in SUPPORT_SIDS or sid in by_id or sid in seen or not _use_ok(it):
                continue
            seen.add(sid)
            k = min(M)
            v = support_value(g, m, sid, k, M, plan)
            if v > 0:
                out.append((v, ('use', it['idx'], sid, it['id'], ('group', k)), (sid, k), 0))
    return out


def heal_worth(g, M, party, by_id):
    """(bossfight) The heal worth a turn in a fight that matters, or None: for the most
    hurt member likely to die this round (HP at or below tactics.incoming), the cheapest
    heal they know of (HEAL_ONE order) whose mean, capped at the HP they're missing,
    lifts them to HEAL_CLEAR times that, and past the worst single action that reaches them
    (tactics.danger), and is at least HEAL_SHARE of it."""
    inc = tactics.incoming(g, M, party)
    blow = {s_: b for s_, _, b in tactics.danger(g, M, party)}
    for k, hp, mx in sorted(party, key=lambda x: x[1] / x[2] if x[2] else 1):
        d = inc.get(k, 0.0)
        if hp <= 0 or hp > d or CAST.get(('healed', k), -1) == ROUND:
            continue
        clear = max(HEAL_CLEAR * d, blow.get(k, 0.0))
        for sid in HEAL_ONE:
            if sid not in by_id:
                continue
            eff = min(HEAL_MEAN.get(sid, 999), mx - hp)
            if hp + eff >= clear and eff >= HEAL_SHARE * d:
                c = by_id[sid]
                CAST[('healed', k)] = ROUND
                FIGHT_INFO.setdefault('heals', []).append((ROUND, k, sid, hp, round(d)))
                return ('spell', sid, c[1], c[2], c[3], ('member', k))
    return None


FOCUS_M = [None, None]      # (round, M) the policy last rated, for choose_group (casterfocus)
CASTER_KILL_MARGIN = 1.25   # caster_round: the party's best round reaches the casters' HP this many times over


def caster_round(g, M, party_hp):
    """(casterfocus) Whether the party's first round likely kills every caster group
    (tactics.caster_order), and whether the fight left after that is still costly for the
    walk-out run rule. The round: each member that can act adds its best against one
    caster group, its blows (tactics.member_melee) or a damage or death spell below
    KEEP_LEVEL it has points for (mean x the chance it lands, a death spell's chance x the
    HP; capped at the group's HP); 'killed' when that reaches CASTER_KILL_MARGIN times
    the casters' HP. Costly after: the other groups' rated threat over two rounds,
    stretched by the actions they take away (tactics.disable), reaches half the party's
    HP, or MANY or more of them stand. None without caster groups."""
    order = tactics.caster_order(M, KILL_FIRST)
    if not order:
        return None
    hp_c = sum(tactics.group_hp(M[k]) for k in order)
    D = 0.0
    for slot, ri in enumerate(party_ids(g)):
        if ri is None:
            continue
        hp, st = member_state(g, slot)
        if hp <= 0 or st >= 8:
            continue
        lvl = g.char(ri)['level']
        best = max(tactics.member_melee(g, slot, k) for k in order)
        for sid, school, level, i in castable(g, ri):
            if level >= KEEP_LEVEL or not (sid in tactics.DAMAGE or sid in tactics.DEATH):
                continue
            for k in order:
                m = M[k]
                ghp = tactics.group_hp(m)
                if sid in tactics.DAMAGE:
                    mean, kind, el = tactics.DAMAGE[sid]
                    f = 0.5 if m['resist'] & el and el else 2.0 if m['weak'] & el and el else 1.0
                    mons = m['mons'][:1] if kind == 'one' else m['mons']
                    d = tactics.lands(m, sid) * sum(min(mean * f / (3 if sid in tactics.CLOUDS else 1), h)
                                                    for _, h, _ in mons)
                else:
                    mons = m['mons'][:1] if tactics.DEATH[sid][0] == 'one' else m['mons']
                    d = tactics.death_p(m, sid, lvl) * sum(h for _, h, _ in mons)
                best = max(best, min(d, ghp))
        D += best
    killed = D >= CASTER_KILL_MARGIN * hp_c
    rest = {k: dict(v) for k, v in M.items() if k not in order}
    T = sum(v['threat'] * len(v['mons']) for v in rest.values())
    L = tactics.disable(g, rest, members(g))['L'] if rest else 1.0
    n = sum(len(v['mons']) for v in rest.values())
    costly = not killed or T * 2 * L >= party_hp / 2 or n >= MANY
    return dict(casters=order, caster_hp=hp_c, dmg=round(D), killed=killed, rest_threat=round(T, 1),
                rest_L=round(L, 2), rest_n=n, costly=costly)


def focus_pick(g, m, me, M, cands, opts):
    """(casterfocus) This member's part in taking out the caster groups (tactics.caster_order,
    leaving out those the members before have likely killed this round): 'fight' when its
    blows on the first such group, with what's already on it, likely kill it (no points
    spent); else the cheapest damage or death spell among cands (by level, then the
    better chance) likely to kill every monster of a caster group this round
    (tactics.finish_p >= FINISH_P), trying the groups in order; else None, and the
    policy's best value stands (a fight with no caster groups, or casters no spell
    finishes this round: Montino, Katino, a big spell at a pack); 'cheap' when every caster
    group is likely dead this round already."""
    order = tactics.caster_order(M, KILL_FIRST, skip_done=True)
    if not order:
        return 'cheap' if tactics.caster_order(M, KILL_FIRST) else None
    k0 = order[0]
    if FIGHT in opts:
        x = tactics.member_melee(g, m, k0)
        if x > 0:
            tactics.FOCUS['dmg'][k0] = tactics.FOCUS['dmg'].get(k0, 0.0) + x
            alone = tactics.dead_p(k0, M[k0])
            tactics.FOCUS['dmg'][k0] -= x
            if alone >= tactics.DONE_P:
                return 'fight'
    for k in order:
        fin = []
        for c_ in cands:
            sid, t = c_[2]
            if t != k or not (sid in tactics.DAMAGE or sid in tactics.DEATH):
                continue
            p = tactics.finish_p(sid, M[k], me['level'])
            if p >= tactics.FINISH_P:
                fin.append((c_[3], -p, -c_[0], c_))
        if fin:
            return min(fin, key=lambda x: x[:3])[3]
    return None


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
    want = {'fight': FIGHT, 'parry': PARRY, 'spell': SPELL, 'run': RUN, 'dispel': DISPEL, 'use': USE}[act[0]]
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
    if act[0] == 'use':
        ui.wait_until(g, lambda: g.u8(SCREEN) == USE_LIST, 120, 'use list')
        ui.move_cursor(g, LIST, act[1], 'down', 'up', what='use item')
        _press_change(g, 'circle', what='use item')
        if act[-1][0] == 'member':
            # a cure item on a member: the same member grid as a spell's (screen 51)
            ui.wait_until(g, lambda: g.u8(SCREEN) not in TRANSIENT, 120, 'after use')
            if g.u8(SCREEN) == 51:
                slot = act[-1][1]
                ui.move_cursor(g, PGRID_Y, slot // 3, 'down', 'up', what='target row')
                ui.move_cursor(g, PGRID_X, slot % 3, 'right', 'left', what='target col')
    # a target step: an enemy group pick is aimed (aim); anything else (a member) takes
    # what's selected. Stop at the next member or the overview.
    prefer = act[-1][1] if act[0] in ('spell', 'dispel', 'use') and act[-1][0] == 'group' else None
    end = g.frame + 600
    while in_battle(g) and g.u8(PHASE) == CMD_PHASE and g.u8(MEMBER) == m \
            and g.u8(SCREEN) not in WAITING:
        if g.frame > end:
            raise Stuck('target step', sig=sig(g))
        if g.u8(SCREEN) in TRANSIENT or g.u8(SCREEN) == 9:
            g.step(1)
            continue
        if pick.pick_screen(g) is not None:
            if not aim(g, m, prefer, log, fight=act[0] == 'fight') and pick.pick_screen(g) is not None \
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
            # the members overview, or "Is this all right?" (cursor on Yes). On the
            # overview a press on a member who can't act (asleep) does nothing: move to
            # the next member and press again (n1v1m chapter 9, agent 13: the cursor sat
            # on Dax asleep, screen 5, and circle never changed it)
            try:
                _press_change(g, 'circle', 120, 'command flow')
            except Stuck:
                if g.u8(SCREEN) != 5:
                    raise
                for b in ('right', 'down', 'left', 'up'):
                    try:
                        _press_change(g, b, 40, 'command flow, next member')
                        break
                    except Stuck:
                        pass
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
    members = _standing(g)
    # the chest's real trap (0x80079a59), for the log only: the choices go by what the
    # party is told
    rec = dict(area=g.u8(MAZE_AREA), pos=g.pos(), danger=danger, acts=[], trap=None,
               went_off=None, loot=[], result=None, real_trap=g.u8(0x80079a59))
    CHESTS.append(rec)
    if not members:
        _chest_act_leave(g)
        rec['result'] = 'left (nobody can act)'
        return rec

    rec['answers'] = []     # (who, 'inspect' or 'calfo', trap named) per answer

    def act(opt, slot, trap=None, why=''):
        msgs, gone = _chest_act(g, opt, slot, trap)
        ri = g.party_slots()[slot]
        who = g.char(ri)['name'] if ri is not None else None
        rec['acts'].append(dict(act=['inspect', 'calfo', 'calnova', 'disarm', 'open'][opt],
                                who=who, trap=trap, why=why,
                                msgs=[i for i, t in msgs]))
        if opt in (0, 1):
            k = [i for i, t in msgs if 221 <= i <= 233]
            rec['answers'].append((who, ['inspect', 'calfo'][opt], k[-1] - 221 if k else None))
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
    used = {(w, m) for w, m, _ in rec['answers']}

    def calfo_left():
        # a Calfo answer not had yet: each member's answer is kept per chest and method
        # (BATTLE 0x800c697c, table 0x800da7c0 + member + 6 x method), and a repeat cast
        # by the same member spends the point and gives the same answer
        return any((c['name'], 'calfo') not in used and CALFO in known_spells(c['raw'], 1, 2)
                   and g.char(c['i'])['raw'][0x5c + 7 + 1] and c['status'] & ~0x04 == 0
                   for _, c in members)

    # any name is confirmed before a Disarm while a Calfo answer is to be had (main, agent
    # 8, 2026-10-14: n1v0h chapter 9, a Thief's Inspect named Goddess's Kiss, a mild trap
    # that went straight to Disarm; it was a Demon's Eye, a wrong name springs it at once,
    # and it stoned the party). Inspect misses about 5% and then names a random trap;
    # Calfo is right 95% and never springs. Without Calfo a mild name goes ahead as before,
    # and a worse one still needs two answers that agree or the chest is left
    if trap and (trap not in MILD or calfo_left()):
        # a wrong name sets the trap off at once, and these hit everyone (q8 loot test
        # l1b, 2026-10-14: an inspect read Spell Blaster and four casters died disarming
        # it): ask others until two answers agree (each member answers once a chest;
        # Calfo casters, then members who inspect at 50% or more), else leave it. In l3b
        # Calfo misread 2 of 4 where the Thief was right, so one answer each isn't enough
        votes = {trap: 1}
        while max(votes.values()) < 2:
            m = None
            for slot, c in members:
                if (c['name'], 'calfo') in used:
                    continue
                if CALFO in known_spells(c['raw'], 1, 2) and g.char(c['i'])['raw'][0x5c + 7 + 1] \
                        and c['status'] & ~0x04 == 0:
                    m = (1, slot, c, 'calfo')
                    break
            if m is None:
                others = [(s_, c) for s_, c in members if (c['name'], 'inspect') not in used
                          and inspect_chance(c) >= 50]
                if others:
                    s_, c = max(others, key=lambda sc: inspect_chance(sc[1]))
                    m = (0, s_, c, 'inspect %d%%' % inspect_chance(c))
            if m is None:
                break
            used.add((m[2]['name'], 'calfo' if m[0] == 1 else 'inspect'))
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
            # who can act now: a try can leave the disarmer's slot empty (n1v0h chapter 9,
            # agent 8, 2026-10-14: the next try used the stale slot and the run crashed)
            members = _standing(g)
            if not members:
                _chest_act_leave(g)
                rec['result'] = 'left (nobody can act)'
                return rec
            disarmers = sorted(members, key=lambda m: -disarm_odds(m[1], danger)[0])
            p, q = disarm_odds(disarmers[0][1], danger)
            risk = spring_risk(p, q)
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
    members = _standing(g)
    if not members:
        _chest_act_leave(g)
        rec['result'] = 'left (nobody can act)'
        return rec
    opener = max(members, key=lambda m: m[1]['hp'])
    msgs, gone = act(4, opener[0], why='open' if not trap else 'open mild trap %d' % trap)
    rec['result'] = 'opened' if not rec['went_off'] else 'opened, sprung'
    if not gone:
        _chest_act_leave(g)
        rec['result'] += ' (then left?)'
    return rec


def _standing(g):
    """[(party slot, char)] of the members who can act at a chest."""
    members = [(slot, g.char(ri)) for slot, ri in enumerate(g.party_slots()) if ri is not None]
    return [(s_, c) for s_, c in members if _can_act(c)]


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


def _items_after(g):
    """The fight's item uses, each marked 'used' (a consumable with uses left: potions and
    scrolls carry a count, item_use_after 0x800ac7c4), 'gone' (its last use; queued for
    gear.RESTOCK), 'broke' (gear no longer in its pack slot) or 'kept'."""
    from harness import gear
    out = []
    for u in FIGHT_INFO.get('items', []):
        held = any(w & 0x1ff == u['id'] for _, w in gear.pack(g, u['ri']))
        words = dict(gear.pack(g, u['ri']))
        if u['cons']:
            res = 'used' if held else 'gone'
            if not held:
                gear.RESTOCK.append((u['ri'], u['id']))
        else:
            res = 'kept' if (words.get(u['k'], 0xffff) & 0x1ff) == u['id'] else 'broke'
        out.append(dict(who=u['who'], item=u['item'], sid=u['sid'], round=u['round'], v=u['v'], result=res))
    return out


# death-cause tags (agent 11, 2026-10-14), by FIGHTMSG.OBJ row: a member's fall, what left
# them helpless earlier, and the actor rows that can be the cause
M_DOWN = (132, 136, 138, 139, 140, 141)        # stone, decapitated, lost, dies, ashes, dust
M_DOWN_AS_MON = (154, 158, 159, 160, 161)       # the same on the monster rows: a member hit by a
                                                # confused member is named on those (n1v3k c9 test)
M_HELPLESS = (130, 134, 135)                    # asleep, paralyzed, knocked out
M_BREATH = tuple(range(78, 98))                 # breathes fire, spits venom, deadly scream...
M_HIT = (108, 109)                              # {mon} {verb} {member} with {weapon}.
M_CAST = 112                                    # {mon} casts {spell}.
M_TRAP = 242                                    # Oops! {trap}!!
M_PARTY = (98, 99, 100, 102)                    # a member's own action: the cause isn't before it
VERBS = sorted({'attacks', 'slashes at', 'stabs', 'cuts', 'rips into', 'runs through', 'slams',
                'swings at', 'bashes', 'clubs', 'hits', 'strikes', 'thrusts at', 'sweeps', 'shoots',
                'takes aim at', 'peppers', 'looses at', 'claws', 'bites', 'scratches',
                'tries to pin down', 'fans', 'whips', 'touches', 'headbutts', 'tries to crush',
                'tries to deal with', 'burns', 'kicks', 'tries to blow away', 'stings', 'kicks at',
                'squeezes', 'pecks at', 'gnaws on', 'pinches', 'smacks', 'slaps', 'thrashes',
                'tries to bowl over', 'glares at', 'tries to lull', 'startles', 'tries to melt',
                'tries to engulf', 'bops', 'batters', 'tries to chomp', 'grabs', 'tries to choke out',
                'sprays', 'pelts', 'slams into', 'stares at', 'wallops'}, key=len, reverse=True)


def _flat(t):
    return ' '.join((t or '').split())


def death_tags(g, msg0):
    """Each member who fell in this fight (dead, ashes, lost, or stoned), from the battle
    text since msg0: dict(who, fell (the row's words), how ('melee', 'spell', 'breath',
    'trap', 'ally' (a confused member's blow) or 'other'), by (the monster's name as
    shown, the member, or the trap), what (the spell,
    breath or weapon), helpless (asleep, paralyzed or knocked out earlier in the fight))."""
    if not g.cap:
        return []
    ms = [m for m in g.cap.messages[msg0:] if m['file'] == 'FIGHTMSG.OBJ']
    names = {g.char(ri)['name'] for ri in g.party()}
    out = []
    for j, m in enumerate(ms):
        t = _flat(m['text'])
        if not (m['idx'] in M_DOWN or m['idx'] in M_DOWN_AS_MON and t.split(' ')[0] in names):
            continue
        tail = _flat(m.get('src')).replace('{ff18}', '').replace('{ff13}', '').strip()
        who = t[:-len(tail)].strip() if tail and t.endswith(tail) else t.split(' ')[0]
        d = dict(who=who, fell=tail.rstrip('.!'), how='other', by=None, what=None,
                 helpless=next((_flat(x.get('src')).replace('{ff18}', '').strip().rstrip('.')
                                for x in ms[:j] if x['idx'] in M_HELPLESS
                                and _flat(x['text']).startswith(who + ' ')), None))
        for x in reversed(ms[:j]):
            i, xt = x['idx'], _flat(x['text'])
            if i in M_HIT:
                k = xt.find(' %s ' % who)
                left = xt[:k] if k > 0 else xt
                v = next((v for v in VERBS if left.endswith(' ' + v)), None)
                d.update(how='melee', by=left[:-len(v) - 1] if v else left,
                         what=xt.split(' with ', 1)[1].rstrip('.') if ' with ' in xt else None)
            elif i == M_CAST:
                by, _, sp = xt.partition(' casts ')
                d.update(how='spell', by=by, what=sp.rstrip('.'))
            elif i in M_BREATH:
                bt = _flat(x.get('src')).replace('{ff13}', '').strip()
                d.update(how='breath', by=xt[:-len(bt)].strip() if xt.endswith(bt) else xt, what=bt.rstrip('.'))
            elif i == M_TRAP:
                d.update(how='trap', by=xt.replace('Oops!', '').strip(' !'), what=None)
            elif i in (98, 99) and (' %s ' % who in xt or xt.endswith(' ' + who + '.')):
                d.update(how='ally', by=xt.split(' ')[0],
                         what=xt.split(' with ', 1)[1].rstrip('.') if ' with ' in xt else None)
            elif i not in M_PARTY:
                continue
            break
        out.append(d)
    return out


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
    FIGHT_INFO.pop('runs_skipped', None)
    FIGHT_INFO.pop('loss_checked', None)
    FIGHT_INFO.pop('likely_loss', None)
    FIGHT_INFO.pop('loss_rounds', None)
    FIGHT_INFO.pop('items', None)
    FIGHT_INFO.pop('heals', None)
    for k_ in [k_ for k_ in FIGHT_INFO if isinstance(k_, tuple) and k_[0] == 'long'] + ['long', 'focus']:
        FIGHT_INFO.pop(k_, None)
    FIGHT_INFO.pop('cm', None)
    for k_ in [k_ for k_ in FIGHT_INFO if isinstance(k_, tuple) and k_[0] == 'support'] + ['support', 'stacked']:
        FIGHT_INFO.pop(k_, None)
    SPLAN.update(round=None, by={})
    STACK_V.clear()
    msg0 = len(g.cap.messages) if g.cap else 0
    FIGHT_INFO['msg0'] = msg0
    # (nodead) who started the fight dead, stoned, ashed, lost, paralyzed or poisoned
    # (Chris, 2026-10-15: the party shouldn't carry on with them; harness/nodead.py)
    out_start = [[g.char(ri)['name'], g.char(ri)['status'] & OUT_BITS] for ri in g.party()
                 if g.char(ri)['status'] & OUT_BITS]
    tactics.STORY[0] = None
    where = (g.u8(MAZE_AREA),) + tuple(g.pos())
    if FIGHT_POLICIES and policy is default_policy and where in POLICY_AT:
        policy = POLICY_AT[where]
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
                where=where, story=tactics.STORY[0], policy=policy.__name__, cm=FIGHT_INFO.get('cm'),
                support=FIGHT_INFO.get('support'),
                matters=FIGHT_INFO['matters'], casts=list(FIGHT_INFO['casts']),
                ran=sum(1 for a in log if a[1] == 'run'),
                runs=FIGHT_INFO.get('runs', []), runs_skipped=FIGHT_INFO.get('runs_skipped', []), likely_loss=FIGHT_INFO.get('likely_loss'), loss_rounds=FIGHT_INFO.get('loss_rounds', []), long=FIGHT_INFO.get('long'), focus=FIGHT_INFO.get('focus'),
                fled=_flee_msgs(g, msg0),
                first=FIGHT_INFO.get('first'), hp_end=_party_hp(g), items=_items_after(g),
                down_end=[g.char(ri)['name'] for ri in g.party() if g.char(ri)['status'] >= 0x20],
                dead_end=[g.char(ri)['name'] for ri in g.party() if g.char(ri)['status'] & 0x380],
                deaths=death_tags(g, msg0), out_start=out_start)
