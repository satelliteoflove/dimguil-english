#!/usr/bin/env python3
"""A live map for a person playing Dimguil in RetroArch: the floor the party is on, where
it stands and faces, and the way to a chosen square, drawn in the browser and kept up to
date as the party walks.

    livemap.py [--port 8778] [--ra-port 55355]

then open http://localhost:8778/ . Like humanwatch.py it only ever sends
READ_CORE_MEMORY and GET_STATUS (its Reader), so it can run beside the watcher.

The walls and events are the site's map data (maze.SITE, data/maps/dim/fNN.json), with
RAM's wall map for the floor the party is on; the route is the harness's own planner
(nav.plan: stairs, chutes, lifts, the Investigate joins, hidden doors once found, sealed
sides by their flags). Coordinates on the page are the game's: E = x, N = 23 - y.
"""
import argparse, heapq, http.server, json, os, struct, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from humanwatch import Reader                                            # noqa: E402
from harness import maze, nav                                            # noqa: E402
from harness.game import OVL_NAME, RESIDENT                              # noqa: E402

TABLET = 0x143
NAMES = {0: 'the Grounds', 1: 'Shrine 1F', 2: 'Shrine 2F', 3: 'Shrine 3F', 4: 'Shrine 4F',
         5: 'Underground B4', 6: 'Underground B3', 7: 'Underground B2', 8: 'Underground B1',
         18: 'Area X', 19: 'Area A B4', 20: 'Area A B3', 21: 'Area A B2', 22: 'Area A B1',
         23: 'Area B B5', 24: 'Area B B4', 25: 'Area B B3', 26: 'Area B B2', 27: 'Area B B1'}
# Where the page can send the party: (label, (area, x, y)). The Area B squares are where
# the stairs from the floor above (B5: Area X's way down) set the party down.
PLACES = [('Area B B4 (training)', (24, 14, 18)), ('Area B B5', (23, 19, 12)),
          ('Area B B3', (25, 19, 12)), ('Area B B2', (26, 5, 18)), ('Area B B1', (27, 17, 11)),
          ('Area X', (18, 13, 12)), ('Underground B3', (6, 12, 11)),
          ('Home: the Grounds', (0, 11, 19))]
FACE = 'NESW'
FACE_WORD = ['north', 'east', 'south', 'west']
BLOCKS = [(0x79600, 0x680), (0x5ac50, 576), (0x5de54, 256)]     # globals, wall map, wall types


def name(area):
    if area in NAMES:
        return NAMES[area]
    p = os.path.join(maze.SITE, 'f%02d.json' % area)
    if os.path.exists(p):
        d = json.load(open(p))
        return '%s %s' % (d['area'].get('en', ''), d.get('floor_label') or '')
    return 'area %d' % area


def en(x, y):
    return 'E%d N%d' % (x, 23 - y)


def present(area):
    """present[y][x]: the square is part of the floor (the site's grid; rows are N)."""
    p = os.path.join(maze.SITE, 'f%02d.json' % area)
    rows = json.load(open(p)).get('present') if os.path.exists(p) else None
    if not rows or not any('1' in r for r in rows):
        return [[1] * 24 for _ in range(24)]
    return [[int(rows[23 - y][x] != '0') for x in range(24)] for y in range(24)]


class Mem:
    """RAM through the Reader, the blocks the planner reads cached once per look (it asks
    for flags thousands of times a plan; each live read costs a frame)."""

    def __init__(self, ra):
        self.ra = ra
        self.c = {}

    def refresh(self, walls=True):
        for a, n in BLOCKS if walls else BLOCKS[:1]:
            b = self.ra.read(a, n)
            if b is None or len(b) < n:
                return False
            self.c[a] = b
        return True

    def read(self, addr, n):
        a = addr & 0x1fffff
        for base, b in self.c.items():
            if base <= a and a + n <= base + len(b):
                return b[a - base:a - base + n]
        return self.ra.read(a, n) or bytes(n)

    def u32(self, addr):
        return struct.unpack('<I', self.read(addr, 4))[0]


class G:
    """Just enough of harness.game.Game for nav.plan and maze.in_maze."""

    def __init__(self, mem):
        self.e = mem

    def u8(self, a): return self.e.read(a, 1)[0]
    def u16(self, a): return struct.unpack('<H', self.e.read(a, 2))[0]
    def u32(self, a): return self.e.u32(a)
    def pos(self): return self.u8(maze.X), self.u8(maze.Y)
    def overlay(self): return OVL_NAME.get(self.u8(RESIDENT), '?')


def floor_walk(g, F, wm, start, goal, area):
    """The squares from start to goal on one floor, by the planner's rules (its costs,
    its shut and hidden sides, transfer squares only as the goal)."""
    dist, prev, q = {start: 0}, {}, [(0, start)]
    while q:
        c, n = heapq.heappop(q)
        if n == goal:
            break
        if c > dist[n]:
            continue
        x, y = n
        for d in range(4):
            st = nav.side_state(g, F, x, y, d, wm)
            if st == 'shut':
                continue
            nx, ny = x + maze.DIRV[d][0], y + maze.DIRV[d][1]
            m = (nx, ny)
            if not (0 <= nx < 24 and 0 <= ny < 24) or m in F['closed'] or m in F['voids']:
                continue
            if m in F['transfers'] and m != goal:
                continue
            cost = 40 if m in F['arrive'] and m != goal else 1
            if st == 'hidden':
                cost += nav.FIND_COST
            if c + cost < dist.get(m, 1e9):
                dist[m] = c + cost
                prev[m] = n
                heapq.heappush(q, (c + cost, m))
    if goal != start and goal not in prev:
        return None
    path, n = [goal], goal
    while n != start:
        n = prev[n]
        path.append(n)
    return path[::-1]


def leg_text(leg, here_area):
    if leg[0] == 'walk':
        _, area, x, y = leg
        F = nav.floor(area)
        to = F['transfers'].get((x, y)) if F else None
        where = '' if area == here_area else ' on %s' % name(area)
        if to:
            return 'Walk to %s%s: it takes you to %s.' % (en(x, y), where, name(to[0]))
        return 'Walk to %s%s.' % (en(x, y), where)
    if leg[0] == 'link':
        L = leg[1]
        a, x, y = L['at']
        how = 'Investigate' + (' (the Tablet), then step forward' if L.get('step') else '')
        if L.get('kind') == 'circle':
            how = 'Investigate the switch'
            a, x, y = L['switch']
        return 'At %s, face %s and %s: %s, to %s.' % (en(x, y), FACE_WORD[L['face']], how,
                                                    L['what'], name(L['to'][0]))
    if leg[0] == 'find':
        _, area, x, y, d = leg
        return 'At %s, face %s and Investigate: there is a hidden door.' % (
            en(x, y), FACE_WORD[d])
    return str(leg)


class Live:
    def __init__(self, ra):
        self.mem = Mem(ra)
        self.g = G(self.mem)
        self.dest = PLACES[0][1]
        self.state = {'ok': False, 'why': 'starting'}
        self.lock = threading.Lock()
        self.key = None

    def look(self):
        if not self.mem.refresh():
            return {'ok': False, 'why': 'no answer from RetroArch'}
        g = self.g
        area, (x, y), face = g.u8(maze.AREA), g.pos(), g.u8(maze.FACE) & 3
        ovl = g.overlay()
        town = ovl == 'JOUKA' or (ovl == 'MCARD' and g.u8(0x80079b18) != 0xff)
        mode = 'town' if town else 'battle' if ovl == 'BATTLE' else 'maze'
        key = (area, x, y, face, mode, self.dest, bytes(self.mem.c[0x79600]))
        if key == self.key:
            return self.state
        self.key = key
        st = {'ok': True, 'mode': mode, 'area': area, 'floor': name(area), 'x': x, 'y': y,
              'face': face, 'where': '%s, %s facing %s' % (name(area), en(x, y), FACE_WORD[face]),
              'dest': list(self.dest), 'dest_name': '%s, %s' % (name(self.dest[0]),
                                                                 en(*self.dest[1:])),
              'places': [[l, list(p)] for l, p in PLACES]}
        F = nav.floor(area)
        wm = maze.wallmap(g) if mode == 'maze' else None
        st['walls'] = self.walls(F, wm)
        st['marks'] = self.marks(F) if F else []
        st['present'] = present(area)
        legs = None
        if town:
            st['steps'] = ['In town. The map comes back once you set out.']
        else:
            legs = nav.plan(g, tuple(self.dest), (area, x, y), items={TABLET})
            if legs is None:
                st['steps'] = ['No known way from here to there.']
            elif not legs:
                st['steps'] = ['You are there.']
            else:
                st['steps'] = [leg_text(l, area) for l in legs]
        st['path'] = []
        if legs and F:
            first = legs[0]
            goal = None
            if first[0] == 'walk' and first[1] == area:
                goal = first[2:]
            elif first[0] == 'link' and first[1]['at'][0] == area:
                L = first[1]
                goal = (L['switch'] if L.get('kind') == 'circle' else L['at'])[1:]
            elif first[0] == 'find' and first[1] == area:
                goal = first[2:4]
            if goal:
                p = floor_walk(g, F, wm, (x, y), tuple(goal), area)
                st['path'] = [list(s) for s in p] if p else []
                st['goal'] = list(goal)
        return st

    def walls(self, F, wm):
        """walls[y][x] = [n, e, s, w]: 0 open, 1 wall, 2 door, 3 hidden (unfound)."""
        out = []
        for y in range(24):
            row = []
            for x in range(24):
                if F is None and wm is None:
                    row.append([0, 0, 0, 0])
                    continue
                cell = []
                for d in range(4):
                    w = maze.side(wm, x, y, d) if wm is not None else F['walls'][(x, y)][d]
                    if F is not None:
                        s = nav.side_state(self.g, F, x, y, d, wm)
                        if s == 'hidden':
                            w = 3
                        elif s == 'shut' and w == 0:
                            w = 1
                        elif s == 'open' and w == 3:
                            w = 0
                    cell.append(w)
                row.append(cell)
            out.append(row)
        return out

    def marks(self, F):
        out = []
        for (x, y), to in F['transfers'].items():
            out.append({'x': x, 'y': y, 'kind': 'go', 'tip': 'to %s, %s' % (name(to[0]), en(*to[1:]))})
        for L in nav.LINKS:
            if L['at'][0] == self.g.u8(maze.AREA):
                out.append({'x': L['at'][1], 'y': L['at'][2], 'kind': 'link',
                            'tip': '%s: face %s, Investigate' % (L['what'], FACE_WORD[L['face']])})
        return out

    def loop(self):
        while True:
            try:
                st = self.look()
            except Exception as e:                  # keep serving; say what broke
                st = {'ok': False, 'why': '%s: %s' % (type(e).__name__, e)}
            with self.lock:
                self.state = st
            time.sleep(0.25)


PAGE = os.path.join(HERE, 'livemap.html')


def serve(live, port):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, body, ctype):
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith('/state'):
                with live.lock:
                    self.send(json.dumps(live.state).encode(), 'application/json')
            else:
                self.send(open(PAGE, 'rb').read(), 'text/html; charset=utf-8')

        def do_POST(self):
            n = int(self.headers.get('Content-Length', 0))
            d = json.loads(self.rfile.read(n) or b'{}')
            if self.path.startswith('/dest') and len(d.get('dest', [])) == 3:
                live.dest = tuple(int(v) for v in d['dest'])
                live.key = None
            self.send(b'{}', 'application/json')

    http.server.ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8778)
    ap.add_argument('--ra-port', type=int, default=55355)
    a = ap.parse_args()
    live = Live(Reader(port=a.ra_port))
    threading.Thread(target=live.loop, daemon=True).start()
    print('live map on http://localhost:%d/' % a.port, flush=True)
    serve(live, a.port)


if __name__ == '__main__':
    main()
