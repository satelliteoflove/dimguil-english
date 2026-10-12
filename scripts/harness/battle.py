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
import struct
from harness import ui
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
SPELL_NAME = {}


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


def monsters_standing(g):
    return sum(g.u8(GROUPS + k * 8 + 5) for k in range(1, 5))


def groups_alive(g):
    return [k for k in range(1, 5) if g.u8(GROUPS + k * 8 + 5)]


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
            ks = known_spells(rec, school, level)
            for i, sid in enumerate(ks):
                out.append((sid, school, level, i))
    return out


def default_policy(g, m, opts):
    """What member m (party slot) does this round. Returns ('fight',), ('parry',),
    ('spell', sid, school, level, index, target) with target ('group', g) or
    ('member', slot), or ('first',) to take the first option."""
    ids = party_ids(g)
    ri = ids[m]
    cast = castable(g, ri) if SPELL in opts else []
    by_id = {c[0]: c for c in cast}
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
    if cast:
        many = monsters_standing(g) > 1
        order = (GROUP_DAMAGE + ONE_DAMAGE) if many else (ONE_DAMAGE + GROUP_DAMAGE)
        best = [sid for sid in order if sid in by_id]
        if best:
            # the strongest in the preferred kind: the lists run weakest to strongest
            kind = GROUP_DAMAGE if best[0] in GROUP_DAMAGE else ONE_DAMAGE
            pick = max((s for s in best if s in kind), key=lambda s: kind.index(s))
            c = by_id[pick]
            alive = groups_alive(g)
            return ('spell', pick, c[1], c[2], c[3], ('group', alive[0] if alive else 1))
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
    act = policy(g, m, opts)
    log.append((m, act[0], act[1] if len(act) > 1 else None))
    if act[0] == 'first':
        _press_change(g, 'circle')
        return
    want = {'fight': FIGHT, 'parry': PARRY, 'spell': SPELL}[act[0]]
    ui.move_cursor(g, LIST, opts.index(want), 'down', 'up', what='command')
    _press_change(g, 'circle', what='choose command')
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
    # a target step (a group, a member) takes what's selected; stop at the next member
    # or the overview
    end = g.frame + 600
    while in_battle(g) and g.u8(PHASE) == CMD_PHASE and g.u8(MEMBER) == m \
            and g.u8(SCREEN) not in WAITING:
        if g.frame > end:
            raise Stuck('target step', sig=sig(g))
        if g.u8(SCREEN) in TRANSIENT or g.u8(SCREEN) == 9:
            g.step(1)
            continue
        _press_change(g, 'circle', what='target')


def command_phase(g, policy, log):
    end = g.frame + 6000
    while in_battle(g) and g.u8(PHASE) == CMD_PHASE:
        if g.frame > end:
            raise Stuck('command phase', sig=sig(g))
        if g.u8(LEVEL) == 1 and g.u8(SCREEN) == 9:
            command_member(g, policy, log)
        elif g.u8(SCREEN) in WAITING:
            # the members overview, or "Is this all right?" (cursor on Yes)
            _press_change(g, 'circle', 120, 'command flow')
        else:
            # a screen in transition: a press now would carry into the next menu
            g.step(1)


CHEST_PHASE = 0x42
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
    if trap == 221 and not oops:
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


def fight(g, policy=default_policy, chest_mode='leave', limit=60000):
    """Fight the battle on screen to its end. Returns a dict: rounds, frames, outcome
    ('won' back in the maze, 'town' after a wipe or escape to town, 'other'), actions."""
    f0 = g.frame
    rounds = 0
    log = []
    chest_result = None
    chest_mark = len(g.cap.messages)
    while True:
        if g.frame - f0 > limit:
            raise Stuck('battle too long', sig=sig(g))
        if not in_battle(g):
            break
        ph = g.u8(PHASE)
        if ph == CMD_PHASE:
            rounds += 1
            command_phase(g, policy, log)
            continue
        if ph == CHEST_PHASE:
            # the chest menu, or a loot message ("Each survivor gains N gold!") when there's
            # no chest. Tap only for a message: a press would pick from the chest menu.
            if _since(g, chest_mark, 'FIGHTMSG.OBJ', (245,)):
                chest_result = chest(g, chest_mode, since=chest_mark)
                continue
            last = [m for m in g.cap.messages[chest_mark:] if m['file'] == 'FIGHTMSG.OBJ']
            if last and last[-1]['idx'] in LOOT_MSGS:
                n = len(g.cap.messages)
                ui.press_until(g, 'circle', lambda: not in_battle(g) or g.u8(PHASE) != CHEST_PHASE
                               or len(g.cap.messages) > n, 300, 'loot message')
                chest_mark = len(g.cap.messages)
            else:
                g.step()
            continue
        chest_mark = len(g.cap.messages)
        # narration and everything else waits for a press; tap it along (4-frame floor)
        g.tap('circle')
        for _ in range(4):
            if not in_battle(g) or g.u8(PHASE) == CMD_PHASE:
                break
            g.step()
    return dict(rounds=rounds, frames=g.frame - f0, actions=log, ovl=g.overlay(), chest=chest_result)
