#!/usr/bin/env python3
"""Walk the castle's menus from a save state and log every line of text they draw.

    castlecrawl.py STATE OUTDIR [--max-nodes N] [--max-depth D] [--actions "up down ..."]

Breadth first: from each screen, press each action, wait for the text to settle, and
keep the result as a new screen if what's on screen differs. "What's on screen" is the
live glyph sprites in the four text layers (the pool at *0x8007961c, layer table at
0x8008b390, counts at 0x80079938), so a cursor move that changes no text is the same
screen. START turns the help line on where there is one, which makes a cursor move a new
screen there. Screens outside the town (JOUKA.BIN not loaded at 0x800a1000) are logged
but not expanded.

Writes OUTDIR/nodes.jsonl, one record per screen: the path to it, a screenshot, the
lines on screen (read from the sprite pool, since the game only redraws glyphs that
change) and the lines drawn on the way there (from the glyph calls, with any glyph a
full layer refused). OUTDIR/edges.jsonl has the same for actions that led back to a
known screen but drew something new on the way.
"""
import argparse, ctypes as C, hashlib, json, os, sys, time, zlib
sys.path.insert(0, os.path.dirname(__file__))
import emu
from screentext import Text, ACCEPT, REFUSE, DEC, ALLOC

POOL_PTR, LAYERS, COUNTS = 0x8007961c, 0x8008b390, 0x80079938
JOUKA_MARK = (0x800cbec0, bytes.fromhex('46010424'))   # asm/status_text_pool.asm's addiu a0, 326
s16 = lambda v: v - 0x10000 if v & 0x8000 else v


def sprites(e):
    """Live glyph sprites: (layer, x, y, texture key, colour), in screen coordinates."""
    pool = e.u32(POOL_PTR)
    tab = e.read(LAYERS, 24)
    cnt = e.read(COUNTS, 8)
    out = []
    if not pool:
        return out
    for L in range(4):
        start, size, head = (int.from_bytes(tab[6 * L + k:6 * L + k + 2], 'little') for k in (0, 2, 4))
        n = int.from_bytes(cnt[2 * L:2 * L + 2], 'little')
        if not size or n > size:
            continue
        for k in range(n):
            b = e.read(pool + (start + (head + k) % size) * 36, 0x17)
            x = s16(int.from_bytes(b[4:6], 'little')) + 0xa0
            y = s16(int.from_bytes(b[6:8], 'little')) + 0x78
            out.append((L, x, y, b[8:0x14], b[0x14:0x17]))
    return out


def signature(sp):
    return hashlib.md5(b'|'.join(sorted(bytes([L]) + x.to_bytes(2, 'little', signed=True) +
                                        y.to_bytes(2, 'little', signed=True) + k + c
                                        for L, x, y, k, c in sp))).hexdigest()


def glyph_code(k):
    """The glyph code a sprite shows, from its size and texture cell, as 0x8001f4d4 lays
    the fonts out: 8 px cells 21 to a row; 12 px cells 21 to a row from v = 0x50; the
    6 px font puts codes below 0x3e 11 to a row from u = 0xa8."""
    k = bytes(k)
    w, u, v = k[0], k[6], k[7]
    if w == 8:
        return (v // 8) * 21 + u // 8
    if w == 12 and v >= 0x50:
        return ((v - 0x50) // 12) * 21 + u // 12
    if w == 6:
        if u >= 0xa8:
            return (v // 8) * 11 + (u - 0xa8) // 8
        return (v // 8) * 21 + u // 8
    return -1


class Glyphs:
    """Kept for the report: texture key -> code, from glyph_code."""
    def __init__(self):
        self.map = {}

    def learn(self, sp, raw):
        pass

    def code(self, k):
        return glyph_code(k)


def screen_lines(sp, glyphs):
    """What's on screen, as lines: sprites grouped by layer and row, in x order, split
    where the gap is over 14 px."""
    rows, last = {}, {}
    for L, x, y, k, c in sp:            # a fading copy can sit under the new one
        last[(L, x, y)] = (k, c)
    for (L, x, y), (k, c) in last.items():
        rows.setdefault((L, y), []).append((x, glyphs.code(k), c, bytes(k).hex()))
    out = []
    for (L, y), g in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        g.sort()
        piece = [g[0]]
        for item in g[1:]:
            if item[0] - piece[-1][0] > 14:
                out.append((L, y, piece)); piece = []
            piece.append(item)
        out.append((L, y, piece))
    return [dict(layer=L, y=y, x0=p[0][0], xs=[q[0] for q in p], codes=[q[1] for q in p],
                 keys=[q[3] for q in p], text=''.join(DEC.get(q[1], '?') for q in p),
                 colour=p[0][2].hex())
            for L, y, p in out]


def in_town(e):
    a, mark = JOUKA_MARK
    return e.read(a, 4) == mark


def snapshot(e):
    n = e.lib.retro_serialize_size()
    buf = C.create_string_buffer(n)
    assert e.lib.retro_serialize(buf, C.c_size_t(n))
    return zlib.compress(buf.raw, 1)


def restore(e, blob):
    d = zlib.decompress(blob)
    e.run(1) if e.frame_no == 0 else None
    assert e.lib.retro_unserialize(d, C.c_size_t(len(d)))


def settle(e, t, quiet=40, least=24, most=600):
    """Run until no new glyph (position and code) has been drawn for `quiet` frames.
    Some screens redraw the party panel every frame, so repeats don't count."""
    raw, idle, n, seen = [], 0, 0, set()
    while n < most:
        e.run(6)
        n += 6
        new = False
        for x in e.log():
            if x['pc'] == ACCEPT:
                r = x['regs']
                k = (r[31], r[6], r[4] & 0xffff, r[5] & 0xffff, r[16] & 0xff)
                if k in seen:
                    continue
                seen.add(k)
                new = True
            raw.append(x)
        idle = 0 if new else idle + 6
        # a blank screen is a load or a fade still going, not a settled screen
        if n >= least and idle >= quiet and int.from_bytes(e.read(0x80079c38, 2), 'little') \
                and any(e.read(COUNTS, 8)):
            break
    t.raw = raw
    return n


FACILITIES = {"Gilgamesh's Tavern", "Adventurer's Inn", "Boltac's Trading Post", 'Temple of Cant',
              'Training Grounds', 'Edge of Town', 'Audience with the King'}


def at_town_map(lines):
    """The town map captions the facility under the cursor at y = 166; inside, the name
    is a title at the top."""
    return any(l.y == 166 and l.text in FACILITIES for l in lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('state')
    ap.add_argument('out')
    ap.add_argument('--max-nodes', type=int, default=400)
    ap.add_argument('--max-depth', type=int, default=8)
    ap.add_argument('--actions', default='start circle down up right left cross triangle square')
    ap.add_argument('--town-map', action='store_true', help='expand the town map too')
    ap.add_argument('--stop', action='append', default=[],
                    help="don't expand a screen showing this line (e.g. the title you came from)")
    ap.add_argument('--anywhere', action='store_true',
                    help='expand screens outside JOUKA.BIN too (the card game)')
    ap.add_argument('--prefix', default='', help='keys to press from STATE first')
    ap.add_argument('--cue', default=os.path.join(os.path.dirname(__file__), '../rips/iso/dimguil-en.cue'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    acts = a.actions.split()
    e = emu.Emu(a.cue)
    e.load(a.state)
    e.run(2)
    t = Text(e).start()
    if a.prefix:
        e.seq(a.prefix)
    settle(e, t)
    nodes_f = open(os.path.join(a.out, 'nodes.jsonl'), 'w')
    edges_f = open(os.path.join(a.out, 'edges.jsonl'), 'w')
    glyphs, drawn_seen = Glyphs(), set()

    def drawn():
        """Lines drawn during the last action (transient ones included), refusals."""
        out, keys = [], set()
        for l in t.lines_from(t.raw):
            k = l.key() + (l.cut,)
            if k in keys or not (l.glyphs or l.refused_first):
                continue
            keys.add(k)
            out.append(dict(text=l.text, layer=l.layer, y=l.y, x0=l.x0, x1=l.x1(t.lut),
                            fixed=l.fixed, ra=l.ra, cut=l.cut, refused_first=l.refused_first))
        return out

    def screen():
        sp = sprites(e)
        glyphs.learn(sp, t.raw)
        return sp, screen_lines(sp, glyphs)

    def write_node(nid, pid, p, town, sp_lines, dr):
        shot = f'n{nid:04d}.png'
        e.shot(os.path.join(a.out, shot), scale=1)
        tab, cnt = e.read(LAYERS, 24), e.read(COUNTS, 8)
        layers = [(int.from_bytes(tab[6 * L + 2:6 * L + 4], 'little'),
                   int.from_bytes(cnt[2 * L:2 * L + 2], 'little')) for L in range(4)]
        allocs = [(x['regs'][31], x['regs'][4], x['regs'][5]) for x in t.raw if x['pc'] == ALLOC]
        nodes_f.write(json.dumps(dict(id=nid, parent=pid, path=p, depth=len(p), town=town,
                                      shot=shot, screen=sp_lines, drawn=dr, layers=layers,
                                      allocs=allocs,
                                      total=int.from_bytes(e.read(0x80079c38, 2), 'little'))) + '\n')
        nodes_f.flush()

    sp, lines = screen()
    seen = {signature(sp): 0}
    write_node(0, None, [], in_town(e), lines, drawn())
    queue = [(0, [], snapshot(e))]
    nid, t0 = 0, time.time()
    while queue and nid < a.max_nodes:
        pid, path, blob = queue.pop(0)
        if len(path) >= a.max_depth:
            continue
        for act in acts:
            restore(e, blob)
            t.start()
            e.press(act, hold=4, after=0)
            settle(e, t)
            sp, lines = screen()
            sig = signature(sp)
            p = path + [act]
            dr = drawn()
            if sig in seen:
                new = [d for d in dr if d['cut'] or (d['text'], d['y'], d['x0']) not in drawn_seen]
                if new:
                    edges_f.write(json.dumps(dict(path=p, node=seen[sig], drawn=new)) + '\n')
                    edges_f.flush()
                drawn_seen.update((d['text'], d['y'], d['x0']) for d in dr)
                continue
            drawn_seen.update((d['text'], d['y'], d['x0']) for d in dr)
            nid += 1
            seen[sig] = nid
            town = (a.anywhere or in_town(e)) and (a.town_map or not at_town_map(t.lines_from(t.raw))) \
                and not any(l['text'].strip() in a.stop for l in lines)
            write_node(nid, pid, p, town, lines, dr)
            if town:
                queue.append((nid, p, snapshot(e)))
            if nid >= a.max_nodes:
                break
        print(f'{nid} nodes, queue {len(queue)}, depth {len(path)}, {time.time() - t0:.0f}s',
              flush=True)
    json.dump({k.hex(): v for k, v in glyphs.map.items()}, open(os.path.join(a.out, 'glyphs.json'), 'w'))
    print('done', nid, 'nodes; unexpanded', len(queue))


if __name__ == '__main__':
    main()
