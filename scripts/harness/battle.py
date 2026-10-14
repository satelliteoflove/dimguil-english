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
HEAL_ONE = [21, 30, 33, 36, 58, 64]     # weakest first
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
# on and was wiped on six retries running.)
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


def default_policy(g, m, opts):
    """What member m (party slot) does this round. Returns ('fight',), ('parry',),
    ('run',), ('spell', sid, school, level, index, target) with target ('group', g) or
    ('member', slot), or ('first',) to take the first option."""
    if ROUND > RUN_AFTER and RUN in opts:
        return ('run',)
    if RUN_WHEN_LOSING and RUN in opts and losing(g):
        return ('run',)
    ids = party_ids(g)
    ri = ids[m]
    me = g.char(ri)
    cast = castable(g, ri) if SPELL in opts else []
    by_id = {c[0]: c for c in cast}
    M = {k: tactics.info(g, k) for k in tactics.groups(g)}
    M = {k: v for k, v in M.items() if v['mons']}
    party_hp = sum(max(member_state(g, k)[0], 0) for k, rk in enumerate(ids) if rk is not None)
    big = tactics.matters(g, M, party_hp) or losing(g)
    FIGHT_INFO['matters'] = FIGHT_INFO['matters'] or bool(big)
    # support spells (the party's AC and magic screen, the monsters' AC) only in a fixed
    # fight or one that's going badly (Chris, 2026-10-14: not in trash fights)
    boss = bool(g.u8(FIXED)) or losing(g)
    # heal the most hurt member below 40%
    hurt = []
    for k, rk in enumerate(ids):
        if rk is None:
            continue
        hp, st = member_state(g, k)
        mx = g.char(rk)['max_hp']
        if st < 0x20 and mx and hp * 10 < mx * 4:
            hurt.append((hp / mx, k))
    if hurt:
        for sid in reversed(HEAL_ONE):
            if sid in by_id:
                c = by_id[sid]
                return ('spell', sid, c[1], c[2], c[3], ('member', min(hurt)[1]))
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
            if rec[0x5c + sch * 7 + lv - 1] <= 1 and any(
                    h in tactics.HEALS for h in known_spells(rec, sch, lv)):
                continue
        if sid in tactics.DAMAGE or sid in tactics.DEATH or sid in tactics.DISABLE:
            for k in M:
                v = tactics.value(g, sid, k, M, me['level'], CAST)
                if v > 0:
                    cands.append((v, ('spell', sid, sch, lv, c[3], ('group', k)), (sid, k)))
        elif boss and sid in (tactics.BAMATU, tactics.MAPORFIC, tactics.CORTU):
            v = tactics.support_value(g, sid, M, CAST, party_hp)
            if v > 0 and M:
                k = min(M)
                cands.append((v, ('spell', sid, sch, lv, c[3], ('group', k)), (sid, None)))
        elif boss and sid in (tactics.DILTO, tactics.MORLIS, tactics.BADUMAS):
            for k in M:
                v = tactics.armor_value(g, sid, k, M, CAST)
                if v > 0:
                    cands.append((v, ('spell', sid, sch, lv, c[3], ('group', k)), (sid, k)))
    if DISPEL in opts:
        for k in M:
            v = tactics.dispel_value(g, k, M, me['cls'], me['level'])
            if v > 0:
                cands.append((v, ('dispel', ('group', k)), ('dispel', k)))
    fight_v = 3 * me['level'] if FIGHT in opts else 0
    if cands:
        cands.sort(key=lambda x: -x[0])
        pick_ = cands[0]
        if len(cands) > 1 and _vary():
            pick_ = cands[1]
        v, act, key = pick_
        if v > fight_v and v >= MIN_SPELL_VALUE:
            CAST[key[0]] = CAST.get(key[0], 0) + 1
            if key[1] is not None:
                CAST[key] = CAST.get(key, 0) + 1
            return act
    if FIGHT in opts:
        return ('fight',)
    return ('parry',) if PARRY in opts else ('first',)


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


def fight(g, policy=default_policy, chest_mode='leave', limit=60000):
    """Fight the battle on screen to its end. Returns a dict: rounds, frames, outcome
    ('won' back in the maze, 'town' after a wipe or escape to town, 'other'), actions."""
    f0 = g.frame
    rounds = 0
    log = []
    CAST.clear()
    FIGHT_INFO['matters'], FIGHT_INFO['casts'] = False, []
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
                    # the Grounds' chests are never trapped; elsewhere a Thief or Ninja
                    # inspects and opens only an untrapped one; else leave it
                    who = thief_slot(g)
                    mode = 'open' if g.u8(0x80079668) == 0 else 'inspect' if who is not None else 'leave'
                    if mode == 'open':
                        who = 0
                    if mode != 'leave' and (who is None or pack_full(g, who)
                                            or g.char(g.party_slots()[who])['status'] != 0):
                        # nowhere to put what's inside, or nobody standing where the
                        # opener's cursor starts (slot 0; moving it isn't reliable): leave
                        # it (f1v6c chapter 4, 2026-10-13: "Who will open the chest?" on
                        # an empty slot 0, then "opening" six times)
                        mode = 'leave'
                    who = who or 0
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
                matters=FIGHT_INFO['matters'], casts=list(FIGHT_INFO['casts']))
