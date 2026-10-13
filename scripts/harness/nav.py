"""Getting about between floors: plan over the site's map data, walk floor by floor.

The site's data/maps/dim/fNN.json (read off the disc; area NN = cur_area) gives every
floor's walls and its event records. Rows are N (row r is y = 23 - r); event squares
and destinations are [x, N] too, so a site square (x, N) is the game's (x, 23 - N).

How the floors join (found 2026-10-13, rips/harness/chapters/dev/explore*.py):
  - stairs (event types 4, 5, ladders 8), chutes (6), teleports (1, 0x4c), lifts
    (0x17 'travel'): stepping onto the square moves the party at once, no prompt
    (Shrine 1F E11 N6 -> 2F E11 N7)
  - the Shrine's front door: from the Grounds (11, 19) facing north, Investigate with the
    Tablet ("...the door slowly begins to open."), then step north into 1F (11, 18);
    out again from 1F (11, 18) facing south, Investigate ("This must be the Shrine's
    exit") puts the party on the Grounds at (11, 19). A plain step south there gives
    "The door is locked." (SISETU 527).

`plan` runs Dijkstra over (area, x, y) with the site's walls: doors pass, hidden doors
(type 3, site wall '3') only once found (bit p1 of 0x80079628), sealed sides (types 29,
37, 45, 46, 99) only once their flag is set; squares that move or hurt the party are
closed unless they're the way. `travel` walks it a floor at a time (maze.walk_to) and
plans again after each change of floor.
"""
import heapq, json, os
from harness import maze, ui
from harness.game import Stuck

SITE = maze.SITE
HIDDEN_FOUND = 0x80079628
TRANSFER_KINDS = {1: 'teleport', 4: 'stairs', 5: 'stairs', 6: 'chute', 8: 'ladder',
                  23: 'lift', 25: 'lift', 76: 'teleport'}
# square_arrive's event types (A-maze.md 9): stepping on them does something. Avoided
# unless they're the target or the only way; 0x14 (fight squares) is just a fight.
ARRIVE = {1, 6, 8, 0xc, 0x13, 0x15, 0x17, 0x19, 0x1a, 0x2b, 0x3b, 0x41, 0x44, 0x45,
          0x4a, 0x4c, 0x61, 0x64, 0x65, 0x67, 0x68, 0x69, 0x6f, 4, 5, 23, 25, 76, 65}
SEALED = {29, 37, 45, 46, 99}
DIRS = {'n': 0, 'e': 1, 's': 2, 'w': 3}

# Joins the data doesn't show: Investigate facing `face` at (area, x, y), then (if
# `step`) a step that way, to arrive at (area2, x2, y2). `need` is an item the party must
# carry (the Tablet for the front door).
LINKS = [
    dict(at=(0, 11, 19), face=0, step=True, to=(1, 11, 18), need=0x143, what='Shrine door'),
    dict(at=(1, 11, 18), face=2, step=False, to=(0, 11, 19), what='Shrine exit'),
    # the jewel lift (event 0xc, square_examine): "Will you touch it?" Yes
    dict(at=(4, 11, 11), face=0, step=False, to=(6, 12, 11), what='jewel lift down'),
    # the moon door on B3 between E19 N4 and N5 (square_examine 0x15): shut both ways,
    # the Tablet opens it from the south each time (EVENTMES 80), and the party steps
    # through (f1v3g chapter 5, 2026-10-13: "no path" at (19, 19) on the way back)
    dict(at=(6, 19, 19), face=0, step=True, to=(6, 19, 18), need=0x143, what='moon door'),
]
# Area A's ladders (square_examine 0x09): B3 (area 20) and B4 (19), the same square on
# both, facing west; and B3's E12-E13 N20 pair facing north, down only (the walkthrough's
# way to the LABORATORY mural)
for _xy in ((10, 3), (10, 4), (10, 19), (10, 20)):
    LINKS.append(dict(at=(20,) + _xy, face=3, step=False, to=(19,) + _xy, what='ladder down'))
    LINKS.append(dict(at=(19,) + _xy, face=3, step=False, to=(20,) + _xy, what='ladder up'))
for _xy in ((12, 3), (13, 3)):
    LINKS.append(dict(at=(20,) + _xy, face=0, step=False, to=(19,) + _xy, what='ladder down'))
# Transfers the site doesn't decode: area -> {(x, y): (area, x, y)}. The jewel lift's
# B3 end (event 0xc with p3 = 4, square_arrive) takes the party up on arrival; its
# params give the destination in game coordinates (x 12, y 11, area 4).
EXTRA_TRANSFERS = {6: {(12, 11): (4, 11, 11)}}
# The lift rides (0x80079878 = 9 down, 10 up; countdown at 0x8008a000) pass through the
# floors between, with the area byte changing on the way: up from B3 it reads 1, 2, 3,
# then 4, and the party ends at 4F (11, 11) about 1,050 frames after stepping on.
RIDES = (9, 10, 15)         # 15: the lift to Area X (B3 E15 N12, ~500 frames)
SCENE, SCENE_COUNT = 0x80079878, 0x8008a000
# Sides the site doesn't decode as sealed: area -> {(x, y, side): [(addr, bit), ...]}.
# The stream on B2 west of E7 N12 (record type 0x24 at (7, 11)) lets nobody across until
# the Tablet parts it (npc_flags bit 28, chapter 4's stream goal); chapter 3's training
# walked into it (r2v1d, r2v3c 2026-10-13: "no path" at B2 (7, 11)).
# Sides that are shut though both the site's walls and RAM's wall map call them open:
# area -> {(x, y, side)}. The parted stream's bed on B3 (5, 11) is one square between two
# stairs (B3 (4, 11) up to B2's far bank (3, 11), B3 (6, 11) up to B2 (7, 11)); its north
# and south can't be walked (f1v0b chapter 4, 2026-10-13: "no path" to the rest of B3).
EXTRA_SHUT = {6: {(5, 11, 0), (5, 11, 2), (5, 10, 2), (5, 12, 0),
                 (19, 19, 0), (19, 18, 2)}}     # the moon door: a LINK, not a side
NPC_FLAGS = 0x80079754
EXTRA_SEALED = {7: {(7, 11, 3): [(NPC_FLAGS, 28)], (6, 11, 1): [(NPC_FLAGS, 28)]}}
# Sides that close once a flag is set: area -> {(x, y, side): (addr, bit)}. B2's passage
# between E13 N12 and E14 N12 shuts when the winding machine runs (story_flags bit 2):
# the wall it hauls up on B3 comes down here (walkthrough 05-moon-door; f1v3f 2026-10-13
# went up and down B1-B2's stairs 40 times, the site's map calling it open).
STORY_FLAGS = 0x80079b44
EXTRA_SHUT_AFTER = {7: {(13, 11, 1): (STORY_FLAGS, 2), (14, 11, 3): (STORY_FLAGS, 2)}}

_floor = {}


def floor(area):
    """The site's data for one floor, digested: walls[x][y][d] (0 open, 1 wall, 2 door,
    3 hidden door), transfers {(x, y): (area, x, y)}, arrive squares, voids, secret and
    sealed sides."""
    if area in _floor:
        return _floor[area]
    p = os.path.join(SITE, 'f%02d.json' % area)
    if not os.path.exists(p):
        _floor[area] = None
        return None
    d = json.load(open(p))
    W = d['walls']
    walls = {}
    for N in range(24):
        for x in range(24):
            walls[(x, 23 - N)] = [int(W[s][N][x]) for s in 'nesw']
    transfers, arrive, voids, secret, sealed, fights = {}, set(), set(), {}, {}, set()
    for e in d['events']:
        t = e['raw']['type']
        sq = [(x, 23 - N) for x, N in e.get('squares', [])]
        if t in TRANSFER_KINDS and e.get('to') and e['to'].get('floor', -1) >= 0:
            to = (e['to']['floor'], e['to']['x'], 23 - e['to']['y'])
            for s in sq:
                transfers[s] = to
        if t in ARRIVE:
            arrive.update(sq)
        if t == 0x14:
            fights.update(sq)
        if e['kind'] == 'void':
            voids.update(sq)
        if t == 3:
            p1, p3 = e['raw']['params'][0], e['raw']['params'][2]
            for s in sq:
                secret[(s[0], s[1], p3)] = p1
        if t in SEALED and e.get('until_flag'):
            fl = [(int(f['at'], 16), f['bit']) for f in e['until_flag']]
            for s in sq:
                for side in e.get('sides', []):
                    sealed[(s[0], s[1], DIRS[side])] = fl
    transfers.update(EXTRA_TRANSFERS.get(area, {}))
    sealed.update(EXTRA_SEALED.get(area, {}))
    shut = set(EXTRA_SHUT.get(area, ()))
    closed = {(x, 23 - r) for r, row in enumerate(d.get('no_entry', [])) for x, c in enumerate(row)
              if c == 'f'}
    _floor[area] = dict(walls=walls, transfers=transfers, arrive=arrive, voids=voids,
                        secret=secret, sealed=sealed, closed=closed, fights=fights, shut=shut,
                        shut_after=dict(EXTRA_SHUT_AFTER.get(area, {})))
    return _floor[area]


def flag(g, addr, bit):
    return bool(g.u32(addr + 4 * (bit // 32)) & (1 << (bit % 32)))


def hidden_found(g, p1):
    return flag(g, HIDDEN_FOUND, p1)


def side_state(g, F, x, y, d, wm=None):
    """'open', 'shut' or 'hidden' (an unfound hidden door: Investigate facing it finds
    it). wm: RAM's wall map, used for the floor the party is on (events can change
    walls); the site's walls for the others."""
    if wm is not None:
        w = maze.side(wm, x, y, d)
    else:
        w = F['walls'][(x, y)][d]
    if w == 1 or (x, y, d) in F['shut']:
        return 'shut'
    after = F.get('shut_after', {}).get((x, y, d))
    if after and flag(g, *after):
        return 'shut'
    p1 = F['secret'].get((x, y, d))
    if p1 is not None:
        if not hidden_found(g, p1):
            return 'hidden'
    elif w == 3:
        return 'shut'          # drawn hidden, no record for this side
    # (a found one is open: r2v1c/r2v3b 2026-10-13 had "no route" from Shrine 4F down,
    # through 3F's found hidden doors, because the site draws them '3')
    fl = F['sealed'].get((x, y, d))
    if fl and not all(flag(g, a, b) for a, b in fl):
        return 'shut'
    return 'open'


def side_open(g, F, x, y, d, wm=None):
    return side_state(g, F, x, y, d, wm) == 'open'


FIND_COST = 12


def plan(g, dest, start=None, items=None):
    """Cheapest way from start (default: here) to dest = (area, x, y). Returns a list of
    legs: ('walk', area, x, y) to reach a square on the same floor (a transfer square
    included), ('link', link) for an Investigate join. None if no way is known."""
    if start is None:
        start = (g.u8(maze.AREA),) + g.pos()
    if items is None:
        from harness import chapter1
        items = chapter1.party_items(g)
    dist = {start: 0}
    prev = {}
    q = [(0, start)]
    here_area = g.u8(maze.AREA)
    wm_here = maze.wallmap(g) if maze.in_maze(g) else None
    while q:
        c, node = heapq.heappop(q)
        if node == dest:
            break
        if c > dist.get(node, 1e9):
            continue
        area, x, y = node
        F = floor(area)
        if F is None:
            continue
        nxt = []
        # a transfer square moves the party as soon as it's walked onto; not the start,
        # and not where a link or a ride sets the party down (the jewel lift lands on
        # B3 (12, 11), the square that rides back up: r3v1 chapter 3, 2026-10-13, had
        # "no route" from the Grounds to anywhere on B3 past it)
        placed = node == start or prev.get(node, (None, ('step',)))[1][0] in ('link', 'jump')
        if not placed and (x, y) in F['transfers']:
            nxt.append((F['transfers'][(x, y)], 1, ('jump',)))
        else:
            for L in LINKS:
                if L['at'] == node and (L.get('need') is None or L['need'] in items):
                    nxt.append((L['to'], 3, ('link', L)))
            for d in range(4):
                st = side_state(g, F, x, y, d, wm_here if area == here_area else None)
                if st == 'shut':
                    continue
                nx, ny = x + maze.DIRV[d][0], y + maze.DIRV[d][1]
                if not (0 <= nx < 24 and 0 <= ny < 24) or (nx, ny) in F['closed'] \
                        or (nx, ny) in F['voids']:
                    continue
                cost = 1
                if (nx, ny) in F['arrive'] and (nx, ny) not in F['transfers'] \
                        and (area, nx, ny) != dest:
                    cost = 40
                if st == 'hidden':
                    nxt.append(((area, nx, ny), cost + FIND_COST, ('find', (x, y, d))))
                else:
                    nxt.append(((area, nx, ny), cost, ('step',)))
        for n2, cost, how in nxt:
            c2 = c + cost
            if c2 < dist.get(n2, 1e9):
                dist[n2] = c2
                prev[n2] = (node, how)
                heapq.heappush(q, (c2, n2))
    if dest not in prev and dest != start:
        return None
    # walk back and cut into legs
    path = []
    n = dest
    while n != start:
        p, how = prev[n]
        path.append((p, how, n))
        n = p
    path.reverse()
    legs = []
    for p, how, n in path:
        if how[0] == 'step':
            if legs and legs[-1][0] == 'walk' and legs[-1][1] == n[0]:
                legs[-1] = ('walk',) + n
            else:
                legs.append(('walk',) + n)
        elif how[0] == 'link':
            legs.append(('link', how[1]))
        elif how[0] == 'find':
            # walk to the side's square, find the door; the plan is made again after
            legs.append(('find', p[0]) + how[1])
            break
        # 'jump': the walk onto the transfer square already ends the leg
    return legs


def avoid_squares(g, area, target):
    """Squares to keep off on this floor: transfers, voids and other event squares,
    except the target."""
    F = floor(area)
    if not F:
        return set(), set()
    hard = (set(F['transfers']) | F['voids']) - {target}
    soft = F['arrive'] - set(F['transfers']) - {target}
    return hard, soft


def hidden_blocked(g, area):
    """Sides that RAM draws as doors but are still hidden, sealed ones, and EXTRA_SHUT
    (walk_to's avoid)."""
    F = floor(area)
    out = set()
    if not F:
        return out
    out |= F['shut']
    for (x, y, d), p1 in F['secret'].items():
        if not hidden_found(g, p1):
            out.add((x, y, d))
    for (x, y, d), fl in F['sealed'].items():
        if not all(flag(g, a, b) for a, b in fl):
            out.add((x, y, d))
    for (x, y, d), fl in F.get('shut_after', {}).items():
        if flag(g, *fl):
            out.add((x, y, d))
    return out


def do_link(g, L, on_int, after):
    """Walk to a link's square, face, Investigate, let the event run, step if it says."""
    from harness import chapter1
    a, x, y = L['at']
    walk_floor(g, x, y, on_int)
    if not maze.face(g, L['face']):
        after(g)
        maze.face(g, L['face'])
    chapter1.investigate(g)
    after(g)
    if L['step'] and (g.u8(maze.AREA),) + g.pos() == L['at']:
        for _ in range(3):
            s = maze.step(g, L['face'])
            if s == 'interrupted':
                after(g)
                continue
            break
        after(g)


def find_door(g, leg, on_int, after):
    """Walk beside a hidden door, face it, Investigate ("Found a secret door!")."""
    from harness import chapter1
    area, x, y, d = leg
    walk_floor(g, x, y, on_int)
    if (g.u8(maze.AREA),) + g.pos() != (area, x, y):
        return
    if not maze.face(g, d):
        after(g)
        maze.face(g, d)
    chapter1.investigate(g)
    after(g)
    F = floor(area)
    p1 = F['secret'].get((x, y, d))
    if p1 is not None and not hidden_found(g, p1):
        raise Stuck('hidden door not found', at=(area, x, y), side=d)


def walk_floor(g, x, y, on_int):
    area = g.u8(maze.AREA)
    hard, soft = avoid_squares(g, area, (x, y))
    return maze.walk_to(g, x, y, on_int, avoid=hidden_blocked(g, area), closed=hard,
                        soft=soft, stop_area=True)


def travel(g, dest, on_int, after=None, max_legs=40):
    """Walk to dest = (area, x, y) across floors. on_int handles interruptions (battles,
    talks, boxes); after(g) runs an Investigate's event to calm. Returns legs taken."""
    from harness import chapter1
    if after is None:
        log = []
        after = lambda g: chapter1.after_event(g, log)
    legs = 0
    while legs < max_legs:
        ride(g)
        here = (g.u8(maze.AREA),) + g.pos()
        if here == tuple(dest):
            return legs
        p = plan(g, tuple(dest))
        if not p:
            for _ in range(15):
                g.step(8)
                if g.u8(SCENE) in RIDES:
                    break
            ride(g)
            here = (g.u8(maze.AREA),) + g.pos()
            if here == tuple(dest):
                return legs
            p = plan(g, tuple(dest))
        if not p and step_off(g, on_int):
            here = (g.u8(maze.AREA),) + g.pos()
            p = plan(g, tuple(dest))
        if not p:
            raise Stuck('no route', at=here, dest=dest)
        leg = p[0]
        legs += 1
        if leg[0] == 'link':
            do_link(g, leg[1], on_int, after)
            continue
        if leg[0] == 'find':
            find_door(g, leg[1:], on_int, after)
            continue
        _, area, x, y = leg
        walk_floor(g, x, y, on_int)
    raise Stuck('travel too long', dest=dest)


def step_off(g, on_int):
    """On a transfer square: walk to an open neighbor that isn't one. True if it did."""
    area = g.u8(maze.AREA)
    F = floor(area)
    x, y = g.pos()
    if not F or (x, y) not in F['transfers']:
        return False
    wm = maze.wallmap(g) if maze.in_maze(g) else None
    for d in range(4):
        nx, ny = x + maze.DIRV[d][0], y + maze.DIRV[d][1]
        if side_state(g, F, x, y, d, wm) != 'open' or (nx, ny) in F['transfers'] \
                or (nx, ny) in F['closed'] or (nx, ny) in F['voids']:
            continue
        walk_floor(g, nx, ny, on_int)
        return g.pos() != (x, y)
    return False


def ride(g, limit=3000):
    """Wait out a lift ride. Planning mid-ride sees a floor the party is only passing
    (r2v3c chapter 3, 2026-10-13: "no route" from Shrine 1F (11, 11), the shaft)."""
    f0 = g.frame
    while g.u8(SCENE) in RIDES and g.frame - f0 < limit:
        g.step(8)
    if g.frame != f0:
        maze.settle(g)


def to_town(g, on_int, after=None):
    """From anywhere in the maze back to the Fortress City (via the Grounds' entrance)."""
    if g.u8(maze.AREA) != 0:
        travel(g, (0,) + maze.ENTRANCE[0], on_int, after)
    return maze.to_town(g, on_int)
