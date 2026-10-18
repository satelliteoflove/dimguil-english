"""Town macros: the icon bar, the Training Grounds' character creation, the tavern,
the inn, the temple, Boltac's, and the Edge of Town. RAM-checked throughout (ui.py).

RAM used (found with probe.py on the harness disc, 2026-10-12, plus docs/re/E-town.md and
F-edge-save.md):
  0x80079b18 town_state: 5 the icon bar, 1 a refusal message, 10 tavern, 15 inn,
             20 Boltac's, 25 temple, 30 Training Grounds, 40 Edge of Town (HAZURE)
  0x80079b8c town icon cursor (0 tavern, 1 inn, 2 Boltac's, 3 temple, 4 training,
             5 castle, 6 Edge of Town). 0x800797cd mirrors it on the bar but is the
             facility's own icon cursor inside one, and reads 0 for a few frames on return
  0x80079896 creation state (F-edge-save.md section 9): 10 name, 35 race, 45 sex,
             55 alignment, 60 bonus roll, 70 class, 80 distribute, 90 "Is this all
             right?", 105 "Use this character?", 0 done
  0x80079c5e list cursor in creation (race, sex, alignment, class, stat)
  0x80079c59 / 0x80079c5c name grid cursor x / y (17 x 4; row 3 ends with End at 15)
  0x80089ac0 the name being typed
  0x800798b4 bonus points rolled; 0x800796b5 still unassigned
  0x8008ff10 new_char, the work record
  creation's yes/no prompts use the list cursor 0x80079c5e (0 = Yes)
"""
import struct
from harness import ui
from harness.game import Stuck

TOWN_STATE = 0x80079b18
TOWN_CURSOR = 0x80079b8c   # the bar's own; 0x800797cd is reused by facility menus
ICON = dict(tavern=0, inn=1, boltac=2, temple=3, training=4, castle=5, edge=6)
FACILITY_STATE = dict(tavern=10, inn=15, boltac=20, temple=25, training=30, edge=40)
TOWN_BAR = 5

CS = 0x80079896
LIST = 0x80079c5e
NAME_X, NAME_Y = 0x80079c59, 0x80079c5c
NAME_BUF = 0x80089ac0
BONUS, BONUS_LEFT = 0x800798b4, 0x800796b5
NEW_CHAR = 0x8008ff10
YESNO = 0x80079c5a
ROSTER_COUNT = 0x80079891
CLASS_ALIGN = 0x8005e280
CLASS_MIN = 0x8005e22c

ENC = {}
for _l in open(__import__('os').path.join(__import__('harness.game', fromlist=['ROOT']).ROOT,
                                          'tables/dimguil_enc.tbl'), encoding='utf-8'):
    _k, _s, _v = _l.rstrip('\n').partition('=')
    if _s and len(_v) == 1 and len(_k) <= 2:
        ENC.setdefault(_v, int(_k, 16))

RACES = ['Human', 'Elf', 'Dwarf', 'Gnome', 'Hobbit', 'Faerie', 'Lizman', 'Dracon', 'Rawolf',
         'Mook', 'Felpurr']
CLASSES = ['Fighter', 'Mage', 'Priest', 'Thief', 'Samurai', 'Lord', 'Valkyrie', 'Ranger',
           'Bard', 'Alchemist', 'Psionic', 'Bishop', 'Ninja', 'Monk']
ALIGN = ['Good', 'Neutral', 'Evil']
# the name grid, row by row (row 3's 15 is End)
GRID = ['ABCDEFGHIJKLM123:', 'NOPQRSTUVWXYZ456.', 'abcdefghijklm789,', 'nopqrstuvwxyz0 ']
# where a class wants its spare bonus points, most wanted first (St IQ Pi Vi Ag Lu = 0-5)
STAT_PREF = {
    'Fighter': [0, 3, 4, 5], 'Mage': [1, 3, 4, 5], 'Priest': [2, 3, 4, 5],
    'Thief': [4, 5, 3, 0], 'Samurai': [0, 3, 4, 1], 'Lord': [0, 3, 2, 4],
    'Valkyrie': [0, 3, 2, 4], 'Ranger': [4, 0, 3, 5], 'Bard': [1, 4, 5, 3],
    'Alchemist': [1, 5, 3, 4], 'Psionic': [1, 3, 0, 5], 'Bishop': [1, 2, 3, 4],
    'Ninja': [4, 0, 3, 5], 'Monk': [0, 4, 3, 2]}


FAC_SUB = 0x80079669        # a facility's screen: 5 = its icon menu has the input
FAC_FADE = 0x800797d6       # not a fade: settles per facility (tavern 8, inn 5, Boltac 7,
                            # temple 5, training 8), likely its icon count
FAC_CURSOR = 0x800797cd     # the facility's icon cursor
TOWN_MSG = 0x800799bf       # nonzero while a town message waits for a press (or a screen opens)


def facility_ready(g):
    """The facility's icon menu has the input: sub-state 5 and the opening's message flag
    cleared (it clears with the icon cursor's reset, traced 2026-10-12)."""
    return g.u8(FAC_SUB) == 5 and g.u8(TOWN_MSG) == 0


BAR_HOLD = 30               # frames the town bar must hold after backing out to it


def in_town_bar(g):
    return g.overlay() == 'JOUKA' and g.u8(TOWN_STATE) == TOWN_BAR


def to_town_bar(g, limit=1200):
    """Back out (cross) until the town's icon bar has the input. One press at a time,
    waiting for it to land: cross at the bar itself means the Edge of Town, and a press
    tapped just before the bar came up landed there (f1v1, f1v3b 2026-10-13: after Pool
    Gold the party went to the Edge of Town and the temple was never reached; "town
    icon" and "no route" stucks). After a press the bar has to hold for BAR_HOLD frames;
    already at the bar, it returns at once (the hold changed creation's timing and so its
    rolls: party:t4v7, round 24)."""
    f0 = g.frame
    pressed = False
    while True:
        if in_town_bar(g):
            if not pressed:
                return 0
            f1 = g.frame
            while g.frame - f1 < BAR_HOLD and in_town_bar(g):
                g.step()
            if in_town_bar(g):
                return g.frame - f0
            continue
        if g.frame - f0 > limit:
            raise Stuck('back to the town bar', where=g.where(), state=g.u8(TOWN_STATE))
        sig = lambda: (g.overlay(), g.u8(TOWN_STATE), g.u8(FAC_SUB), g.u8(TOWN_MSG))
        s0 = sig()
        g.tap('cross')
        pressed = True
        f1 = g.frame
        while g.frame - f1 < 90 and sig() == s0 and not in_town_bar(g):
            g.step()
        g.step(6)


def enter(g, place, limit=900):
    """From the town bar, open a facility. Returns its town_state."""
    to_town_bar(g)
    ui.move_cursor(g, TOWN_CURSOR, ICON[place], 'right', 'left', wrap=7, what='town icon')
    want = FACILITY_STATE.get(place)
    ui.confirm_until(g, lambda: g.u8(TOWN_STATE) != TOWN_BAR or g.overlay() != 'JOUKA',
                     limit, 'enter ' + place)
    if place == 'edge':
        ui.wait_until(g, lambda: g.overlay() == 'HAZURE', limit, 'load Edge of Town')
    elif want is not None:
        ui.wait_until(g, lambda: g.u8(TOWN_STATE) in (want, 1), limit, 'enter ' + place)
        if g.u8(TOWN_STATE) != want:
            raise Stuck('enter ' + place + ' refused', town=g.u8(TOWN_STATE))
    ui.wait_until(g, lambda: facility_ready(g), limit, 'open ' + place)
    return g.u8(TOWN_STATE)


# --- the Training Grounds ---

def class_list(g):
    """The classes the creation screen offers now, in its order (F-edge-save.md 5)."""
    nc = g.e.read(NEW_CHAR, 0x20)
    stats = list(nc[0x13:0x19])
    align = (nc[0x0a] >> 6) & 3
    female = bool(nc[0x0b] & 0x80)
    bonus = g.u8(BONUS)
    al = g.e.read(CLASS_ALIGN + align * 14, 14)
    mn = g.e.read(CLASS_MIN, 14 * 6)
    out = []
    for c in range(14):
        if al[c] == 0xff or (c == 6 and not female):
            continue
        need = sum(max(0, mn[c * 6 + k] - stats[k]) for k in range(6))
        if need <= bonus:
            out.append(c)
    return out


def _advance(g, what, limit=600):
    cs = g.u8(CS)
    ui.confirm_until(g, lambda: g.u8(CS) != cs, limit, what)
    return g.u8(CS)


def _settle_cs(g, want, limit=300, what='creation state'):
    ui.wait_until(g, lambda: g.u8(CS) in want, limit, what)


def type_name(g, name):
    for ch in name:
        row = next(r for r, s in enumerate(GRID) if ch in s)
        col = GRID[row].index(ch)
        ui.move_cursor(g, NAME_Y, row, 'down', 'up', what='name row')
        # no wrapping: left from the first column goes to the end of the row above, not
        # this row's (T4, 2026-10-12: "Jo" came out "w", "Max" "za")
        ui.move_cursor(g, NAME_X, col, 'right', 'left', what='name col')
        before = g.e.read(NAME_BUF, 10)
        ui.confirm_until(g, lambda: g.e.read(NAME_BUF, 10) != before, 120, 'type ' + ch)
    want = bytes(ENC[c] for c in name) + b'\xff\x40'
    got = g.e.read(NAME_BUF, len(want))
    if got != want:
        raise Stuck('name typed wrong', want=want.hex(), got=got.hex())
    ui.move_cursor(g, NAME_Y, 3, 'down', 'up', what='name row')
    ui.move_cursor(g, NAME_X, 15, 'right', 'left', what='End')


def choose_list(g, n, size=None, what='list'):
    ui.move_cursor(g, LIST, n, 'down', 'up', what=what)


def yes_no(g, yes, what='yes/no'):
    """Creation's yes/no prompts use the list cursor (0 = Yes)."""
    ui.move_cursor(g, LIST, 0 if yes else 1, 'down', 'up', what=what)


def create_character(g, name, race, sex, align, cls, retrain=None, reroll_limit=400,
                     reroll_delay=lambda k: 3 + (k * 7) % 23, accept=None):
    """Training Grounds -> Create Character, start to finish. race/sex/align/cls by name
    ('Human', 'M'/'F', 'Good', 'Fighter'). If the class isn't offered, finish the
    character as something else and answer No to "Use this character?" (it's thrown
    away), then start again, as a player rerolls: the class screen has no way back to
    the roll (T4, 2026-10-12: cross and every other button do nothing there). Waits
    reroll_delay(k) frames before each roll so they differ. retrain: True/False at
    "Retrain?", None = Yes only when asked. accept(g, new_char_bytes, bonus), when given,
    runs at "Use this character?" with the finished work record (new_char, age at +0x10):
    None throws the character away and rolls again, anything else is the answer to
    "Retrain?" (chapter 19's Priestess: 18, or 15 and retrained). Returns a dict: roster
    index, bonus, rerolls, retrained, frames."""
    f0 = g.frame
    rerolls = 0
    while True:
        r = _create_once(g, name, race, sex, align, cls, retrain, reroll_delay(rerolls), accept)
        if r is not None:
            r.update(rerolls=rerolls, frames=g.frame - f0)
            return r
        rerolls += 1
        if rerolls > reroll_limit:
            raise Stuck('class not offered', cls=cls, rerolls=rerolls)


def _spend_bonus(g, cls):
    """Spend what's left, in the class's order; a stat that won't take more is skipped."""
    for stat in STAT_PREF.get(cls, []) + [0, 1, 2, 3, 4, 5]:
        if not g.u8(BONUS_LEFT):
            break
        choose_list(g, stat, 6, 'stat')
        while g.u8(BONUS_LEFT):
            left = g.u8(BONUS_LEFT)
            try:
                ui.press_until(g, 'right', lambda: g.u8(BONUS_LEFT) != left, 40, 'add point')
            except Stuck:
                break


def _class_bonus(g, cls):
    """Take the class on the cursor and spend what bonus is left, to "Is this all right?"
    (90). A class whose minimums use the whole bonus skips the distribution (70 -> 85 ->
    90 with no press): circles pressed waiting for 80 then ran on through 105 and
    registered the character (suite round 2026-10-15, party:t4v4/t4v6: a Bishop rolled
    with exactly its minimums, thrown away and registered all the same)."""
    ui.press_until(g, 'circle', lambda: g.u8(CS) != 70, 300, 'class')
    ui.wait_until(g, lambda: g.u8(CS) in (80, 90), 300, 'class (ready)')
    if g.u8(CS) == 80:
        _spend_bonus(g, cls)
        ui.confirm_until(g, lambda: g.u8(CS) == 90, 300, 'distribute')


def _create_once(g, name, race, sex, align, cls, retrain, delay, accept=None):
    """One pass through creation. None if the roll didn't offer cls (the character was
    finished and thrown away), else the registered character's dict."""
    if g.overlay() != 'JOUKA' or g.u8(TOWN_STATE) != 30:
        enter(g, 'training')
    count0 = g.u8(ROSTER_COUNT)
    # Create Character is the first icon; wait for the name entry
    ui.confirm_until(g, lambda: g.u8(CS) == 10, 600, 'open creation')
    ui.wait_until(g, lambda: g.u8(0x80079965) == 4, 300, 'name entry ready')
    type_name(g, name)
    ui.confirm_until(g, lambda: g.u8(CS) == 35, 300, 'name End')
    choose_list(g, RACES.index(race), 11, 'race')
    ui.confirm_until(g, lambda: g.u8(CS) == 45, 300, 'race')
    choose_list(g, 0 if sex == 'M' else 1, 2, 'sex')
    ui.confirm_until(g, lambda: g.u8(CS) == 55, 300, 'sex')
    want = CLASSES.index(cls)
    choose_list(g, ALIGN.index(align), 3, 'alignment')
    ui.confirm_until(g, lambda: g.u8(CS) == 60, 300, 'alignment')
    g.step(delay)
    ui.confirm_until(g, lambda: g.u8(CS) == 70, 300, 'bonus roll')
    offered = class_list(g)
    if want not in offered:
        choose_list(g, 0, len(offered), 'class')
        _class_bonus(g, CLASSES[offered[0]])
        yes_no(g, True, 'is this all right')
        ui.confirm_until(g, lambda: g.u8(CS) == 105, 300, 'all right')
        return _throw_away(g, count0)

    bonus = g.u8(BONUS)
    choose_list(g, offered.index(want), len(offered), 'class')
    _class_bonus(g, cls)
    yes_no(g, True, 'is this all right')
    ui.confirm_until(g, lambda: g.u8(CS) == 105, 300, 'all right')
    if accept is not None:
        verdict = accept(g, g.e.read(NEW_CHAR, 0xd0), bonus)
        if verdict is None:
            return _throw_away(g, count0)
        retrain = verdict
    yes_no(g, True, 'use this character')
    retrained = False
    asked = False
    nmsg = len(g.cap.messages) if g.cap else 0
    cs = g.u8(CS)
    ui.confirm_until(g, lambda: g.u8(CS) != cs, 300, 'use this character')
    # "Retrain?" comes only for a bonus under 10; then up to three training years
    end = g.frame + 3000
    while g.u8(CS) != 0:
        if g.frame > end:
            raise Stuck('after use this character', cs=g.u8(CS))
        cs = g.u8(CS)
        if bonus < 10 and not asked and _is_retrain_prompt(g, nmsg):
            asked = True
            take = True if retrain is None else retrain
            yes_no(g, take, 'retrain')
            retrained = take
        ui.confirm_until(g, lambda: g.u8(CS) != cs or g.u8(CS) == 0, 600, 'creation end')
    ui.wait_until(g, lambda: g.u8(ROSTER_COUNT) == count0 + 1, 120, 'registered')
    return dict(index=count0, name=name, cls=cls, bonus=bonus, retrained=retrained)


def _throw_away(g, count0):
    """At "Use this character?" (state 105): No, so nothing is registered. Returns None."""
    # cancel is No here (state 'n', 110); moving the list cursor to No and confirming
    # registered the character anyway (state 's', 115) in the Bishop reroll test
    ui.cancel_until(g, lambda: g.u8(CS) != 105, 300, 'throw away')
    if g.u8(CS) == 115:
        raise Stuck('throw away took Yes')
    ui.press_until(g, 'circle', lambda: g.u8(CS) == 0 and facility_ready(g), 1200,
                   'back to the Training Grounds')
    g.step(30)
    if g.u8(ROSTER_COUNT) != count0:
        raise Stuck('thrown-away character registered', count=g.u8(ROSTER_COUNT))
    return None


def _is_retrain_prompt(g, since):
    """True once "Retrain?" (SISETU 167) has been printed since message number `since`."""
    if g.cap:
        for m in g.cap.messages[since:]:
            if m['file'] == 'SISETU.OBJ' and m['idx'] == 167:
                return True
        return False
    raise Stuck('retrain prompt needs text capture')


# --- the tavern ---

TAVERN_LIST = 10            # FAC_SUB while "Who will join the party?" is up
GRID_X, GRID_Y = 0x80079c59, 0x80079c5c
PARTY_REC = 0x8007e810      # [id, count, members x6, ...]


def town_slots(g):
    """The party's six positions, as the member grids show them: roster index or None.
    A member who died leaves a hole (0xff, "Empty" in the grid) and the count drops, but
    the others keep their positions (seen 2026-10-12: [1, None, 5, 6, 7, 8] with count 5)."""
    d = g.e.read(PARTY_REC, 8)
    return [None if x == 0xff else x for x in d[2:8]]


def town_party(g):
    """The party's roster indices, in position order (holes skipped). To pick a member in a
    grid, use the position from town_slots."""
    return [x for x in town_slots(g) if x is not None]


def tavern_candidates(g):
    """The tavern's "Who will join" grid, in order: characters in town and not in the
    party (inferred from what the grid showed, 2026-10-12)."""
    party = town_party(g)
    out = []
    for i in range(g.u8(ROSTER_COUNT)):
        c = g.e.read(0x8007d708 + i * 0xd0 + 0x7a, 1)[0]
        status = struct.unpack('<H', g.e.read(0x8007d708 + i * 0xd0 + 0x0e, 2))[0]
        # the dead (and anyone else with a status) wait at the temple, not the tavern
        if c == 0xff and i not in party and status == 0:
            out.append(i)
    return out


BENCH = set()               # roster indices never taken in as standbys (chapter 19: the titled
                            # main party and the Priestess, out of the ring party's way)


def standbys(g):
    """tavern_candidates without the BENCH: who fill_party, raised_back, tablet_back and
    the backups may bring into the party."""
    return [i for i in tavern_candidates(g) if i not in BENCH]


def form_party(g, members, limit=900):
    """Add roster indices to the party at the tavern, in order. Raises Stuck if the
    tavern refuses one (alignment) or the grid holds someone else."""
    f0 = g.frame
    if g.u8(TOWN_STATE) != 10 or g.overlay() != 'JOUKA':
        enter(g, 'tavern')
    for idx in members:
        if idx in town_party(g):
            continue
        if g.u8(FAC_SUB) != TAVERN_LIST:
            ui.wait_until(g, lambda: facility_ready(g), limit, 'tavern menu')
            ui.move_cursor(g, FAC_CURSOR, 0, 'right', 'left', what='Form Party')
            ui.confirm_until(g, lambda: g.u8(FAC_SUB) == TAVERN_LIST, limit, 'open Form Party')
        cand = tavern_candidates(g)
        if idx not in cand:
            raise Stuck('not in the tavern', idx=idx, cand=cand)
        k = cand.index(idx)
        ui.move_cursor(g, GRID_Y, k // 4, 'down', 'up', what='tavern row')
        ui.move_cursor(g, GRID_X, k % 4, 'right', 'left', what='tavern col')
        n = len(town_party(g))
        m0 = len(g.cap.messages) if g.cap else 0
        said = lambda i: g.cap and any(m['file'] == 'SISETU.OBJ' and m['idx'] == i
                                       for m in g.cap.messages[m0:])
        ui.confirm_until(g, lambda: len(town_party(g)) != n or said(9) or said(27), limit,
                         'add member')
        if said(9):
            # "Their alignments won't mix." (a member whose alignment changed, c2v3
            # 2026-10-13: Mercury came back from the temple Evil): back to the menu
            ui.press_until(g, 'circle', lambda: g.u8(TOWN_MSG) == 0 and not said(9) or
                           facility_ready(g) or g.u8(FAC_SUB) == TAVERN_LIST and g.u8(TOWN_MSG) == 0,
                           limit, 'alignment message')
            if not facility_ready(g):
                ui.cancel_until(g, lambda: facility_ready(g), limit, 'back to the tavern menu')
            raise Stuck('alignments won\'t mix', idx=idx, party=town_party(g))
        if said(27) and idx not in town_party(g):
            # "Which position?": a death left a hole; the cursor starts on it
            ui.confirm_until(g, lambda: idx in town_party(g), limit, 'which position')
        p = town_party(g)
        if idx not in p:
            raise Stuck('wrong member joined', want=idx, party=p)
        # "X joined the party." waits for a press
        ui.wait_until(g, lambda: g.u8(TOWN_MSG) != 0, 60, 'join message')
        ui.confirm_until(g, lambda: g.u8(TOWN_MSG) == 0, limit, 'dismiss join message')
    if not facility_ready(g):
        ui.cancel_until(g, lambda: facility_ready(g), limit, 'back to the tavern menu')
    return dict(party=town_party(g), frames=g.frame - f0)


# --- the Edge of Town ---

EDGE_CURSOR = 0x80079c5a    # the Edge of Town's menu (0 Begin Adventure)
EDGE_ICON = 0x80079c58      # its icon row: 0 Begin Adventure, 1 Go to the Training Maze,
                            # 2 Resume, 3 Prepare, 4 Suspend Game, 5 Book of Movement,
                            # 6 Change Settings, 7 Back to Town (dev/edge_captions.png)


def remove_member(g, pos, limit=600):
    """Tavern, Remove Member (icon 1, "Who will leave the party?", the party grid MX/MY):
    take party position `pos` out; they wait in the tavern. Each press removes the member
    under the cursor and the screen stays up for the next, so it's left with cross
    (traced 2026-10-13, dev/remove_probe.py)."""
    if g.u8(TOWN_STATE) != 10 or g.overlay() != 'JOUKA':
        enter(g, 'tavern')
    ui.wait_until(g, lambda: facility_ready(g), limit, 'tavern menu')
    ui.move_cursor(g, FAC_CURSOR, 1, 'right', 'left', what='Remove Member')
    ui.confirm_until(g, lambda: g.u8(FAC_SUB) != 5, limit, 'open Remove Member')
    g.step(20)
    _pick_party_member(g, pos, 'leaver')
    ui.press_until(g, 'circle', lambda: town_slots(g)[pos] is None, limit, 'remove member')
    if not town_party(g):
        # the last member out: the screen may close by itself, and a cross landing after
        # that left the tavern for the bar and the Edge of Town (ch19 outfit, 2026-10-17)
        for _ in range(60):
            if facility_ready(g) and g.u8(TOWN_STATE) == 10:
                break
            g.step()
    if not (facility_ready(g) and g.u8(TOWN_STATE) == 10):
        ui.cancel_until(g, lambda: facility_ready(g), limit, 'back to the tavern menu')
    return town_party(g)


def begin_adventure(g, limit=1800):
    """From town with a party formed: Edge of Town -> Begin Adventure. The party arrives
    in camp on the Grounds; leave the camp and wait for calm. Returns frames."""
    from harness import camp, maze
    f0 = g.frame
    if g.overlay() != 'HAZURE':
        enter(g, 'edge')
    ui.wait_until(g, lambda: g.u8(FAC_SUB) == 5 or g.u8(EDGE_CURSOR) == 0, 300, 'edge menu')
    ui.move_cursor(g, EDGE_CURSOR, 0, 'down', 'up', what='Begin Adventure')
    # the icon row's own cursor: left on Go to the Training Maze (icon 1), the confirm
    # took the party to area 9 (f1v1, f1v6 2026-10-13: "no route" home from there)
    ui.move_cursor(g, EDGE_ICON, 0, 'right', 'left', what='Begin Adventure icon')
    ui.confirm_until(g, lambda: g.overlay() == 'MAZE', limit, 'Begin Adventure')
    ui.wait_until(g, lambda: camp.in_camp(g) and g.u8(camp.CAMP_STATE) == 5, limit, 'arrive in camp')
    if g.u8(0x80079668) != 0:
        raise Stuck('Begin Adventure went elsewhere', area=g.u8(0x80079668))
    camp.close_camp(g)
    return g.frame - f0


# --- power-on to town ---

GAME_MODE = 0x8007967e


def new_game(g, limit=6000):
    """From power-on: the logos don't skip, so tap circle (every RETRY frames) until the
    title's New Game (the cursor's default) sends the game to town (game mode 3), then
    wait for the town's icon bar. Returns frames."""
    f0 = g.frame
    ui.confirm_until(g, lambda: g.u8(GAME_MODE) == 3 or g.overlay() == 'JOUKA', limit, 'title New Game')
    ui.wait_until(g, lambda: in_town_bar(g), limit, 'town after New Game')
    return g.frame - f0


# --- the inn ---
#   Stay -> "Who will stay?" (FAC_SUB 10, 0x800797d6 = 1, member grid MX/MY as in camp)
#   -> "Which room?" (0x80079b15 = 1, list cursor LIST: 0 Stables .. 5 Special Room, 6 Quit)
#   -> confirm a room: one week's sleep (0x80079b15 = 0, TOWN_MSG set, "Sleeping...",
#   level-up or "To the next level..."), a press back to "Which room?" (traced 2026-10-12)

MX, MY = 0x800796cc, 0x800796cd
FAC_PANEL = 0x800797d6       # per facility; in the inn 5 icons, 1 member pick, 0 rooms
ROOM_LEVEL = 0x80079b15      # 1 the room list has the input, 0 sleeping
SLEEP_WAIT = 0x80079b96      # 1 while a week's messages print, 0 once one waits for a press
ROOMS = ['Stables', 'Cot', 'Economy', 'Merchant', 'Royal', 'Special']


def _pick_party_member(g, slot, what):
    ui.move_cursor(g, MY, slot // 3, 'down', 'up', what=what + ' row')
    ui.move_cursor(g, MX, slot % 3, 'right', 'left', what=what + ' col')


def _last_sisetu(g, since):
    for m in reversed(g.cap.messages[since:]):
        if m['file'] == 'SISETU.OBJ':
            return m['idx']
    return None


def inn_stay(g, slot, room='Stables', weeks=None, gather=False, limit=600):
    """Party slot `slot` stays at the inn. weeks=None: until HP is full (Stables: one
    week). When the gold runs short the inn offers to gather the party's gold on them
    (SISETU 84; yes/no cursor 0x80079c60, 0 Yes): `gather` answers it; without the gold
    the stay ends. Returns weeks slept, hp, gold, poor, frames and the messages printed."""
    f0 = g.frame
    if not g.cap:
        raise Stuck('inn needs text capture')
    if g.overlay() != 'JOUKA' or g.u8(TOWN_STATE) != 15:
        enter(g, 'inn')
    idx = town_slots(g)[slot]
    n = len(g.cap.messages)
    ui.move_cursor(g, FAC_CURSOR, 0, 'right', 'left', wrap=4, what='Stay')
    ui.confirm_until(g, lambda: g.u8(FAC_SUB) == 10 and g.u8(FAC_PANEL) == 1, limit, 'Stay')
    _pick_party_member(g, slot, 'who will stay')
    room_ready = lambda: g.u8(ROOM_LEVEL) == 1 and g.u8(FAC_PANEL) == 0 and g.u8(TOWN_MSG) == 0
    ui.confirm_until(g, lambda: g.u8(ROOM_LEVEL) == 1 and g.u8(FAC_PANEL) == 0, limit, 'pick member')
    ui.wait_until(g, room_ready, limit, 'room list')
    ui.move_cursor(g, LIST, ROOMS.index(room), 'down', 'up', what='room')
    slept = 0
    poor = False
    while True:
        c = g.char(idx)
        if weeks is not None and slept >= weeks:
            break
        if weeks is None and slept and (room == 'Stables' or c['hp'] >= c['max_hp']):
            break
        nm = len(g.cap.messages)
        sig = lambda: (g.u8(ROOM_LEVEL), g.u8(TOWN_MSG), g.u8(SLEEP_WAIT), len(g.cap.messages))
        ui.confirm_until(g, lambda: g.u8(ROOM_LEVEL) == 0 or len(g.cap.messages) > nm, limit, 'book room')
        answered = False
        end = g.frame + 3000
        # run the week: a press only where a message waits (SLEEP_WAIT 0, or "Not enough
        # gold." with TOWN_MSG set); an early press carries into the room list and books
        # another week
        while True:
            if g.frame > end:
                raise Stuck('inn week', last=_last_sisetu(g, nm), sig=sig())
            last = _last_sisetu(g, nm)
            if last == 40 and room_ready():
                break
            if last == 84 and not answered and g.u8(TOWN_MSG) == 0:
                poor = True
                ui.move_cursor(g, 0x80079c60, 0 if gather else 1, 'down', 'up', what='gather gold')
                k = len(g.cap.messages)
                ui.confirm_until(g, lambda: len(g.cap.messages) > k, limit, 'answer gather')
                answered = True
                continue
            if last == 57:
                poor = True
            if (g.u8(SLEEP_WAIT) == 0 or last == 57 or any(
                    m['file'] == 'SISETU.OBJ' and m['idx'] == 42 for m in g.cap.messages[nm:])) \
                    and g.u8(TOWN_MSG):
                s0 = sig()
                ui.confirm_until(g, lambda: sig() != s0, 300, 'inn message')
                continue
            g.step()
        if any(m['file'] == 'SISETU.OBJ' and m['idx'] == 41 for m in g.cap.messages[nm:]):
            slept += 1
        else:
            break
    ui.cancel_until(g, lambda: facility_ready(g) and g.u8(TOWN_STATE) == 15, limit, 'leave rooms')
    c = g.char(idx)
    msgs = [(m['file'], m['idx'], m['text']) for m in g.cap.messages[n:] if m['file'] == 'SISETU.OBJ']
    return dict(weeks=slept, hp=c['hp'], max_hp=c['max_hp'], gold=c['gold'], poor=poor,
                frames=g.frame - f0, msgs=msgs)


# --- gold ---

POOL_ICON = dict(tavern=4, inn=1, boltac=2)
POOL_PICK = 30               # FAC_SUB while "Who will hold the gold?" is up


def pool_gold(g, slot, place='tavern', limit=600):
    """Pool the party's gold on party slot `slot`. Returns the holder's gold."""
    if g.overlay() != 'JOUKA' or g.u8(TOWN_STATE) != FACILITY_STATE[place]:
        enter(g, place)
    ui.wait_until(g, lambda: facility_ready(g), limit, 'facility menu')
    icons = dict(tavern=7, inn=4, boltac=6)[place]
    ui.move_cursor(g, FAC_CURSOR, POOL_ICON[place], 'right', 'left', wrap=icons, what='Pool Gold')
    ui.confirm_until(g, lambda: g.u8(FAC_SUB) == POOL_PICK and g.u8(TOWN_MSG) == 0, limit, 'Pool Gold')
    _pick_party_member(g, slot, 'gold holder')
    idx = town_slots(g)[slot]
    total = sum(g.char(i)['gold'] for i in town_party(g))
    ui.confirm_until(g, lambda: g.char(idx)['gold'] == total, limit, 'pool')
    ui.wait_until(g, lambda: facility_ready(g) or g.u8(FAC_SUB) == POOL_PICK and g.u8(TOWN_MSG) == 0,
                  limit, 'after pooling')
    if not facility_ready(g):
        ui.cancel_until(g, lambda: facility_ready(g), limit, 'back to the menu')
    return g.char(idx)['gold']


DIVIDE_ICON = 3             # the tavern's icons: Form Party, Remove Member, Inspect, Divide Gold,
                            # Pool Gold, Visit the Tables (SISETU; JOUKA tavern_main camp_state 0x19)


def divide_gold(g, limit=600):
    """Tavern, Divide Gold: the party's gold split evenly (JOUKA FUN_800aa848 calls
    FUN_800ad8a0, total / members; no member pick, back to the menu after 16 frames).
    Gold pooled on one member who then dies waits at the temple with them (b1v6c chapter
    5, 2026-10-14: 824 gold in the party, 18,500 on the dead). Returns the members' gold."""
    party = town_party(g)
    if len(party) < 2:
        return [g.char(i)['gold'] for i in party]
    if g.u8(TOWN_STATE) != 10 or g.overlay() != 'JOUKA':
        enter(g, 'tavern')
    ui.wait_until(g, lambda: facility_ready(g), limit, 'tavern menu')
    total = sum(g.char(i)['gold'] for i in party)
    even = lambda: max(g.char(i)['gold'] for i in party) - min(g.char(i)['gold'] for i in party) <= total % len(party) + 1
    ui.move_cursor(g, FAC_CURSOR, DIVIDE_ICON, 'right', 'left', wrap=7, what='Divide Gold')
    ui.confirm_until(g, even, limit, 'Divide Gold')
    ui.wait_until(g, lambda: facility_ready(g), limit, 'after dividing')
    return [g.char(i)['gold'] for i in party]


# --- the temple ---
#   Heal Character -> "Help whom?" (SISETU 147; grid cursor x 0x80079c59, y 0x80079c5c, 3
#   per row, the patients in roster order) -> "Who will pay?" (148; the party grid MX/MY)
#   -> "Not enough gold." (57) or the outcome: 153 healed, 155 alive again, 156 ashes,
#   157 lost. (Traced 2026-10-12.)

TEMPLE_GRID_X, TEMPLE_GRID_Y = 0x80079c59, 0x80079c5c
PAY_X, PAY_Y = 0x80079c5d, 0x80079c60      # "Who will pay?" (traced 2026-10-13)


def temple_patients(g):
    """Roster indices waiting at the temple (in town with a status), in roster order."""
    out = []
    for i in range(g.u8(ROSTER_COUNT)):
        c = g.char(i)
        if c['area'] == 0xff and c['status'] != 0 and i not in town_party(g):
            out.append(i)
    return out


def temple_heal(g, patient, payer_slot=0, limit=600):
    """Heal (or raise) roster index `patient`, paid by party slot `payer_slot`. Returns
    the outcome: 'healed', 'alive', 'ashes', 'lost' or 'poor', with frames."""
    f0 = g.frame
    if not g.cap:
        raise Stuck('temple needs text capture')
    if g.overlay() != 'JOUKA' or g.u8(TOWN_STATE) != 25:
        enter(g, 'temple')
    ui.wait_until(g, lambda: facility_ready(g), limit, 'temple menu')
    pts = temple_patients(g)
    if patient not in pts:
        raise Stuck('not at the temple', patient=patient, patients=pts)
    k = pts.index(patient)
    ui.move_cursor(g, FAC_CURSOR, 0, 'right', 'left', wrap=4, what='Heal Character')
    n = len(g.cap.messages)
    said = lambda i: any(m['file'] == 'SISETU.OBJ' and m['idx'] == i for m in g.cap.messages[n:])
    ui.confirm_until(g, lambda: said(147) and g.u8(TOWN_MSG) == 0 and g.u8(FAC_PANEL) == 1,
                     limit, 'Heal Character')
    # four patients to a row (f1v1 2026-10-13: the fourth, at k // 3 = 1, was "patient
    # row" stuck; the grid's x runs 0-3 and down doesn't move with four)
    ui.move_cursor(g, TEMPLE_GRID_Y, k // 4, 'down', 'up', what='patient row')
    ui.move_cursor(g, TEMPLE_GRID_X, k % 4, 'right', 'left', what='patient col')
    n = len(g.cap.messages)
    ui.confirm_until(g, lambda: said(148) and g.u8(TOWN_MSG) == 0 and g.u8(FAC_PANEL) == 1,
                     limit, 'pick patient')
    # "Who will pay?" has its own cursor, PAY_X/PAY_Y; MX/MY don't move with it. Only
    # slot 0 worked before (the cursor starts there): f1v3d chapter 3, 2026-10-13, with
    # slot 0 empty after a death, sat on "Empty" for 16 recover trips holding 56,824 gold
    # while the Tablet's holder waited at the temple ('temple stuck', 'pay').
    ui.move_cursor(g, PAY_Y, payer_slot // 3, 'down', 'up', what='payer row')
    ui.move_cursor(g, PAY_X, payer_slot % 3, 'right', 'left', what='payer col')
    n = len(g.cap.messages)
    OUT = {153: 'healed', 155: 'alive', 156: 'ashes', 157: 'lost', 57: 'poor'}
    ui.confirm_until(g, lambda: any(said(i) for i in OUT), limit, 'pay')
    outcome = next(OUT[i] for i in OUT if said(i))
    # press through the outcome back to the temple's menu or "Help whom?"
    end = g.frame + 3000
    while not facility_ready(g):
        if g.frame > end:
            raise Stuck('after the temple', outcome=outcome)
        if g.u8(TOWN_MSG) == 0 and g.u8(FAC_PANEL) == 1:
            ui.cancel_until(g, lambda: facility_ready(g), limit, 'back to the temple menu')
            break
        if g.u8(TOWN_MSG):
            sig = lambda: (g.u8(TOWN_MSG), g.u8(FAC_PANEL), g.u8(FAC_SUB), len(g.cap.messages))
            s0 = sig()
            ui.confirm_until(g, lambda: sig() != s0, 300, 'temple message')
            continue
        g.step()
    c = g.char(patient)
    return dict(outcome=outcome, status=c['status'], hp=c['hp'], frames=g.frame - f0)


# --- Boltac's ---
#   Trade -> "Who will do business?" (79, party grid MX/MY) -> "What will you do?" (5;
#   FAC_PANEL 6, list cursor LIST: 0 Buy, 1 Sell, 2 Uncurse, 3 Identify, 4 Compare).
#   Buy: "Choose a category." (80, cursor 0x80079c60) -> "Choose a type." (81, 0x80079c65)
#   -> "Buy which item?" (82, 0x80079c64) -> maybe "They can't equip it. Buy anyway?"
#   (83, yes/no 0x800795d5, 0 Yes) -> "I'm sure you'll like it." (123) or "Sorry, you
#   can't afford it." (85) / pack full (86, 91).
#   Sell: "Sell which item?" (87, cursor 0x80079c60) -> "Sell this item?" (111) or
#   "That's equipped. Sell it anyway?" (98) (yes/no 0x80079c65, 0 Yes); 96, 97 refuse.
#   (Traced 2026-10-12.)

BUY_CAT, BUY_TYPE, BUY_ITEM, BUY_YN = 0x80079c60, 0x80079c65, 0x80079c64, 0x800795d5
SELL_ITEM, SELL_YN = 0x80079c60, 0x80079c65
# A list's prompt isn't always captured again on a second visit (2026-10-14), so the
# screens are also read from RAM: BOLTAC_SCREEN 0x80079738 is 15 at "What will you do?",
# 20 Buy, 25 Sell, 30 Uncurse, 35 Identify; SHOP_STATE 0x800797a4 within Buy is 5 the
# categories, 15 the types, 25 the items, and 5 the item list in Sell
BOLTAC_SCREEN, SHOP_STATE = 0x80079738, 0x800797a4


def _screen(g, scr, st):
    return g.u8(BOLTAC_SCREEN) == scr and g.u8(SHOP_STATE) == st and _settled(g)


def _said(g, since, *ids):
    return any(m['file'] == 'SISETU.OBJ' and m['idx'] in ids for m in g.cap.messages[since:])


def _settled(g):
    return g.u8(TOWN_MSG) == 0


PROMPTS = {5, 57, 79, 80, 81, 82, 83, 84, 85, 86, 87, 91, 96, 97, 98, 99, 100, 101, 108, 109, 110, 111,
           123, 126}


def _sig(g):
    """What a taken press changes in Boltac's menus: TOWN_MSG goes 4 two frames after it,
    a yes/no sets 0x80079b15, and the next prompt prints. (Any message count would also
    move with the status lines reprinting after a cursor move.)"""
    k = sum(1 for m in g.cap.messages[-40:] if m['file'] == 'SISETU.OBJ' and m['idx'] in PROMPTS)
    return (g.u8(TOWN_MSG), g.u8(ROOM_LEVEL), k)


def _ok(g, ready, limit, what):
    ui.press_then_wait(g, 'circle', lambda: _sig(g), ready, limit, what)


def boltac_trade(g, slot, limit=600):
    """Open Trade for party slot `slot`; ends at "What will you do?"."""
    if not g.cap:
        raise Stuck("Boltac's needs text capture")
    if g.overlay() != 'JOUKA' or g.u8(TOWN_STATE) != 20:
        enter(g, 'boltac')
    ui.wait_until(g, lambda: facility_ready(g), limit, "Boltac's menu")
    ui.move_cursor(g, FAC_CURSOR, 0, 'right', 'left', wrap=6, what='Trade')
    n = len(g.cap.messages)
    _ok(g, lambda: _said(g, n, 79) and _settled(g), limit, 'Trade')
    _pick_party_member(g, slot, 'trader')
    n = len(g.cap.messages)
    _ok(g, lambda: _said(g, n, 5) and _settled(g), limit, 'trader')


def _at_trade_menu(g):
    """"What will you do?" is up (the last facility line printed) and settled. (0x800797d6
    isn't a screen id here: it holds the trader's pack count.)"""
    return g.u8(TOWN_STATE) == 20 and _settled(g) and g.u8(FAC_SUB) == 10 and (
        g.u8(0x80079738) == 15 or _last_sisetu(g, max(0, len(g.cap.messages) - 60)) in (5, 129))


def _to_trade_menu(g, limit=600):
    """Cross back, one screen per press (each prints its prompt), to "What will you do?"."""
    if _at_trade_menu(g):
        return
    for _ in range(6):
        n = len(g.cap.messages)
        ui.press_then_wait(g, 'cross', lambda: _sig(g), lambda: _said(g, n, 5, 80, 81, 82, 87, 99, 101) or g.u8(BOLTAC_SCREEN) == 15,
                           limit, 'back a screen')
        if _said(g, n, 5) or g.u8(BOLTAC_SCREEN) == 15:
            ui.wait_until(g, lambda: _settled(g), limit, 'What will you do?')
            return
    raise Stuck('back to What will you do?')


def boltac_leave(g, limit=600):
    ui.cancel_until(g, lambda: facility_ready(g), limit, "leave Boltac's trade")


def boltac_buy(g, slot, cat, typ, item, limit=600):
    """Buy the item at list position `item` of category `cat`, type `typ` for party
    slot `slot`. Returns outcome ('bought', 'poor', 'full'), gold before/after, frames."""
    f0 = g.frame
    if not _at_trade_menu(g):
        boltac_trade(g, slot)
    idx = town_slots(g)[slot]
    gold0, items0 = g.char(idx)['gold'], len(g.char(idx)['items'])
    ui.move_cursor(g, LIST, 0, 'down', 'up', what='Buy')
    n = len(g.cap.messages)
    _ok(g, lambda: _said(g, n, 80) and _settled(g) or _screen(g, 20, 5), limit, 'Buy')
    ui.move_cursor(g, BUY_CAT, cat, 'down', 'up', what='category')
    n = len(g.cap.messages)
    _ok(g, lambda: _said(g, n, 81) and _settled(g) or _screen(g, 20, 15), limit, 'category')
    ui.move_cursor(g, BUY_TYPE, typ, 'down', 'up', what='type')
    n = len(g.cap.messages)
    _ok(g, lambda: _said(g, n, 82) or _screen(g, 20, 25), limit, 'type')
    ui.move_cursor(g, BUY_ITEM, item, 'down', 'up', what='item')
    n = len(g.cap.messages)
    ENDS = (123, 85, 86, 91, 126, 84, 57)
    _ok(g, lambda: _said(g, n, 83, *ENDS), limit, 'item')
    if _said(g, n, 83):
        ui.wait_until(g, lambda: _settled(g), limit, 'buy anyway?')
        ui.move_cursor(g, BUY_YN, 0, 'down', 'up', what='buy anyway yes')
        _ok(g, lambda: _said(g, n, *ENDS), limit, 'buy anyway')
    if _said(g, n, 57) and not _said(g, n, 84):
        m = len(g.cap.messages)
        _ok(g, lambda: _said(g, m, 84, 82, 5), limit, 'not enough gold')
    if _said(g, n, 84):
        # "Not enough gold." then "Gather gold on this character?" (yes/no BUY_YN): No
        ui.wait_until(g, lambda: _settled(g), limit, 'gather gold?')
        ui.move_cursor(g, BUY_YN, 1, 'down', 'up', what='gather no')
        m = len(g.cap.messages)
        _ok(g, lambda: _said(g, m, 82, 5), limit, 'gather no')
        _to_trade_menu(g)
        c = g.char(idx)
        return dict(outcome='poor', gold0=gold0, gold=c['gold'], frames=g.frame - f0)
    outcome = 'bought' if _said(g, n, 123) else 'poor' if _said(g, n, 85, 126) else 'full'
    # the answer waits for a press; then "Buy which item?" again
    m = len(g.cap.messages)
    _ok(g, lambda: _said(g, m, 82, 5),
                     limit, 'after buying')
    _to_trade_menu(g)
    c = g.char(idx)
    if outcome == 'bought' and not (c['gold'] < gold0 and len(c['items']) == items0 + 1):
        raise Stuck('bought but no change', gold=(gold0, c['gold']), items=(items0, len(c['items'])))
    return dict(outcome=outcome, gold0=gold0, gold=c['gold'], frames=g.frame - f0)


def boltac_sell(g, slot, item, limit=600):
    """Sell the item at pack position `item` of party slot `slot` (equipped ones too).
    Returns outcome ('sold', 'refused'), gold before/after, frames."""
    f0 = g.frame
    if not _at_trade_menu(g):
        boltac_trade(g, slot)
    idx = town_slots(g)[slot]
    gold0, items0 = g.char(idx)['gold'], len(g.char(idx)['items'])
    pack0 = g.char(idx)['items']
    ui.move_cursor(g, LIST, 1, 'down', 'up', what='Sell')
    n = len(g.cap.messages)
    _ok(g, lambda: _said(g, n, 87) and _settled(g) or _screen(g, 25, 5), limit, 'Sell')
    ui.move_cursor(g, SELL_ITEM, item, 'down', 'up', what='item to sell')
    n = len(g.cap.messages)
    _ok(g, lambda: _said(g, n, 111, 98, 96, 97, 110), limit, 'pick item')
    outcome = 'refused'
    if _said(g, n, 111, 98):
        ui.wait_until(g, lambda: _settled(g), limit, 'sell this?')
        ui.move_cursor(g, SELL_YN, 0, 'down', 'up', what='sell yes')
        _ok(g, lambda: g.char(idx)['gold'] != gold0, limit, 'sell')
        outcome = 'sold'
    m = len(g.cap.messages)
    ui.wait_until(g, lambda: _settled(g) or g.u8(TOWN_MSG), 60, 'after selling')
    _to_trade_menu(g)
    c = g.char(idx)
    if outcome == 'sold' and len(c['items']) != items0 - 1:
        raise Stuck('sold but pack unchanged', items=(items0, len(c['items'])))
    return dict(outcome=outcome, gold0=gold0, gold=c['gold'], item=pack0[item] if item < len(pack0) else None,
                left=c['items'], frames=g.frame - f0)
