"""Maze macros: a RAM "calm" test, turning and stepping, doors, and walking to a square.

RAM (MAZE resident; found 2026-10-12 with probe.py and the decomp of maze_frame and
maze_walk):
  0x80079a13 game_state: 0 walking, 3 camp, 8 the locked-door menu, 0x34 START menu ...
  0x800798e2 a move in progress: 1 a step, 2 a turn, 0 none
  0x800796b4 the maze message box: 0 none; 1 closes when the party moves away; 2 and 3
             close on a press (maze_walk)
  0x80079838 an event box with a countdown is open (maze_frame)
  0x80079a90 queued game mode (2 battle, 9 talk) for the approach jingle; it isn't
             cleared afterwards, so it says nothing about now
  0x80079906 / 0x80079916 x, y; 0x80079b34 facing (0 N, 1 E, 2 S, 3 W); 0x80079668 area
  0x8005ac50 the floor's 24x24 wall-type map; 0x8005de54 the wall-type table: low nibble
             walls, high nibble doors, bits N 4, E 2, S 1, W 8

The site's map data (Bartok's Trading Post data/maps/dim/fNN.json, read off the disc) is
the same as RAM with the rows flipped: site row r is y = 23 - r. Its walls are '1', its
doors '2' (RAM: door bit, no wall bit). site_check() compares the two for the floor
the party is on.
"""
import json, os
from collections import deque
from harness import ui
from harness.game import Stuck

GAME_STATE = 0x80079a13
MOVING = 0x800798e2
MSG = 0x800796b4
EVENT_BOX = 0x80079838
QUEUED_MODE = 0x80079a90
X, Y, FACE, AREA = 0x80079906, 0x80079916, 0x80079b34, 0x80079668
SQ_MAP, WALL_TBL = 0x8005ac50, 0x8005de54
BIT = {0: 4, 1: 2, 2: 1, 3: 8}
DIRV = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
SITE = os.path.expanduser('~/Documents/bartoks-trading-post/data/maps/dim')


def in_maze(g):
    return g.overlay() == 'MAZE'


FADE_A, FADE_B = 0x80079854, 0x800796ab   # nonzero while the view fades in (after the
                                          # camp, 81 frames; after a battle, 34): input
                                          # is ignored until both clear (found 2026-10-12)


def calm(g):
    """Ready for a step: walking state, nothing moving, no box that needs a press, no
    fade-in."""
    return (in_maze(g) and g.u8(GAME_STATE) == 0 and g.u8(MOVING) == 0
            and g.u8(MSG) in (0, 1) and g.u8(EVENT_BOX) == 0 and g.u8(0x8007967e) == 0
            and g.u8(FADE_A) == 0 and g.u8(FADE_B) == 0)


def interrupted(g):
    """Something other than walking has the game: battle, talk, an event, a box."""
    return (not in_maze(g) or g.u8(GAME_STATE) != 0 or g.u8(0x8007967e) != 0
            or g.u8(MSG) in (2, 3) or g.u8(EVENT_BOX) != 0)


def wallmap(g):
    sq = g.e.read(SQ_MAP, 576)
    wt = g.e.read(WALL_TBL, 256)
    return [wt[sq[i]] for i in range(576)]


def side(wm, x, y, d):
    """0 open, 1 wall, 2 door."""
    v = wm[x + y * 24]
    if (v >> 4) & BIT[d]:
        return 2
    return 1 if v & BIT[d] else 0


_site = {}


def site_map(area):
    if area not in _site:
        p = os.path.join(SITE, 'f%02d.json' % area)
        _site[area] = json.load(open(p)) if os.path.exists(p) else None
    return _site[area]


def site_check(g):
    """Compare the site's walls and doors with RAM's for this floor. Returns the list of
    (x, y, side, site, ram) that differ (empty when they agree)."""
    d = site_map(g.u8(AREA))
    if not d:
        return None
    wm = wallmap(g)
    out = []
    for r in range(24):
        y = 23 - r
        for x in range(24):
            for k, s in enumerate('nesw'):
                sv = int(d['walls'][s][r][x])
                rv = side(wm, x, y, k)
                if sv != rv:
                    out.append((x, y, s, sv, rv))
    return out


def site_locked(area):
    """Locked doors from the site's data, as blocked (x, y, dir) steps in game coordinates,
    both sides of each door. The site's rows run y = 23 - row and its n/s sides are the
    game's S/N (checked on the Grounds: (11,4,n) and (11,5,n) are RAM's doors at
    (11,19,S) and (11,18,S), the Shrine's two front doors)."""
    d = site_map(area)
    if not d:
        return set()
    flip = {'n': 2, 'e': 1, 's': 0, 'w': 3}
    out = set()
    for L in d.get('locked', []):
        x, y, k = L['x'], 23 - L['y'], flip[L['side']]
        out.add((x, y, k))
        out.add((x + DIRV[k][0], y + DIRV[k][1], (k + 2) % 4))
    return out


def site_closed(area):
    """Squares the site's no_entry layer marks 'f' (no side can be entered: water, trees,
    rock). Partly closed squares are left to walk_to, which learns a refused step."""
    d = site_map(area)
    if not d or 'no_entry' not in d:
        return set()
    return {(x, 23 - r) for r, row in enumerate(d['no_entry']) for x, c in enumerate(row)
            if c == 'f'}


def bfs(wm, start, goal, blocked=(), closed=()):
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        if c == goal:
            break
        x, y = c
        for d in range(4):
            if side(wm, x, y, d) == 1 or (x, y, d) in blocked:
                continue
            nx, ny = x + DIRV[d][0], y + DIRV[d][1]
            if not (0 <= nx < 24 and 0 <= ny < 24) or (nx, ny) in prev or (nx, ny) in closed:
                continue
            prev[(nx, ny)] = (c, d)
            q.append((nx, ny))
    if goal not in prev:
        return None
    path, c = [], goal
    while prev[c]:
        c, d = prev[c]
        path.append(d)
    return path[::-1]


def settle(g, limit=600, on_box=None):
    """Run until calm. A box that needs a press gets one (or on_box(g) decides)."""
    f0 = g.frame
    while not calm(g):
        if g.frame - f0 > limit:
            raise Stuck('maze settle', where=g.where(), msg=g.u8(MSG), ev=g.u8(EVENT_BOX))
        if interrupted(g) and not (in_maze(g) and g.u8(GAME_STATE) == 0
                                   and g.u8(MSG) in (2, 3)):
            return False
        if in_maze(g) and g.u8(GAME_STATE) == 0 and g.u8(MSG) in (2, 3):
            if on_box and on_box(g):
                continue
            ui.confirm_until(g, lambda: g.u8(MSG) not in (2, 3) or interrupted(g) and g.u8(MSG) == 0,
                             240, 'close maze box')
            continue
        g.step()
    return True


def face(g, d):
    """Turn to face d. Returns True, or False if something interrupted the turn."""
    while g.u8(FACE) != d:
        if not calm(g) and not settle(g):
            return False
        cur = g.u8(FACE)
        btn = 'right' if (d - cur) % 4 in (1, 2) else 'left'
        ui.press_until(g, btn, lambda: g.u8(FACE) != cur or interrupted(g), 120, 'turn')
        ui.wait_until(g, lambda: g.u8(MOVING) == 0 or interrupted(g), 120, 'turn end')
        if interrupted(g):
            return False
    return True


MET_WAIT = 60


def step(g, d):
    """Face d and step once. A door takes circle (it opens and walks through; up does
    nothing at a door). Returns 'moved', 'blocked', 'locked' ("The door is locked.",
    closed again), 'door' (a door that didn't open), or 'interrupted' (battle, talk,
    event, a box)."""
    if not face(g, d) or (not calm(g) and not settle(g)):
        return 'interrupted'
    a = g.pos()
    wm = wallmap(g)
    door = side(wm, a[0], a[1], d) == 2
    n = len(g.cap.messages) if g.cap else 0
    locked = lambda: g.cap and any(m['file'] == 'SISETU.OBJ' and m['idx'] in (516, 527)
                                   for m in g.cap.messages[n:])
    # press until the game takes it: a move starts, the square changes, or something
    # interrupts; a wall bump starts nothing
    taken = lambda: g.pos() != a or g.u8(MOVING) == 1 or interrupted(g)
    try:
        ui.press_until(g, 'circle' if door else 'up', taken, 24, 'step')
    except Stuck:
        if door:
            return 'door'
        # a roaming party in the way shows "You've met someone!" and starts the battle or
        # talk ~40 frames later without moving us: watch for that before calling the
        # side blocked
        try:
            ui.wait_until(g, lambda: interrupted(g), MET_WAIT, 'met someone')
            return 'interrupted'
        except Stuck:
            return 'blocked'
    ui.wait_until(g, lambda: g.u8(MOVING) == 0 or interrupted(g), 120, 'step end')
    if door and locked():
        settle(g)
        return 'locked'
    if interrupted(g):
        return 'interrupted'
    return 'moved' if g.pos() != a else ('door' if door else 'blocked')


def walk_to(g, tx, ty, on_interrupt=None, limit_moves=400, avoid=()):
    """Walk to (tx, ty) on this floor by BFS over RAM's walls. on_interrupt(g) handles
    whatever stops the walk (a battle, a talk, an event); it returns True to carry on.
    Without it, an interruption raises Stuck. A locked door, or one that won't open, is
    avoided from then on.
    Returns a dict: moves, frames, interruptions, blocked."""
    f0 = g.frame
    blocked = set(avoid)
    moves = inter = 0
    last = None
    while True:
        if not calm(g):
            if not settle(g):
                inter += 1
                if not on_interrupt or not on_interrupt(g):
                    raise Stuck('walk interrupted', where=g.where(), at=g.pos())
                continue
        x, y = g.pos()
        if (x, y) == (tx, ty):
            return dict(moves=moves, frames=g.frame - f0, interruptions=inter, blocked=sorted(blocked))
        if moves > limit_moves:
            raise Stuck('walk too long', at=(x, y), goal=(tx, ty))
        p = bfs(wallmap(g), (x, y), (tx, ty), blocked, site_closed(g.u8(AREA)))
        if not p:
            raise Stuck('no path', at=(x, y), goal=(tx, ty), blocked=sorted(blocked))
        d = p[0]
        r = step(g, d)
        moves += 1
        if r == 'moved':
            continue
        if r == 'interrupted':
            continue
        blocked.add((x, y, d))
        nx, ny = x + DIRV[d][0], y + DIRV[d][1]
        blocked.add((nx, ny, (d + 2) % 4))


ENTRANCE = {0: (10, 22)}     # the Grounds' entry square: triangle there goes back to town


def to_town(g, on_interrupt=None, limit=1200):
    """Walk to the floor's entrance and press triangle to go back to the Fortress City.
    Waits for the town's icon bar. Returns frames."""
    from harness import town
    f0 = g.frame
    tx, ty = ENTRANCE[g.u8(AREA)]
    walk_to(g, tx, ty, on_interrupt)
    if not calm(g):
        settle(g)
    ui.press_until(g, 'triangle', lambda: g.u8(0x8007967e) == 3 or not in_maze(g), 120,
                   'triangle to town')
    # arriving, "X was carried to the temple." waits for a press for each dead member
    # (town_state 2, TOWN_MSG set); press only then, never at the icon bar
    end = g.frame + limit
    while not town.in_town_bar(g):
        if g.frame > end:
            raise Stuck('arrive in town', where=g.where(), msg=g.u8(town.TOWN_MSG))
        if g.overlay() == 'JOUKA' and g.u8(town.TOWN_MSG) and g.u8(town.TOWN_STATE) != town.TOWN_BAR:
            n = len(g.cap.messages) if g.cap else 0
            sig = lambda: (g.u8(town.TOWN_MSG), g.u8(town.TOWN_STATE), len(g.cap.messages) if g.cap else 0)
            s0 = sig()
            ui.confirm_until(g, lambda: sig() != s0, 240, 'town arrival message')
            continue
        g.step()
    return g.frame - f0
