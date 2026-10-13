#!/usr/bin/env python3
"""Every event string through the real event box, captured for the T5 checks.

    python3 scripts/harness/t5events.py OUT K/N [INDEX ...]

Like scripts/evsweep.py: searching the Shrine door prints EVENTMES 11, so the string
under test is written over it (a diagnostic RAM write; the box, its code and the font
are the game's), and circle is pressed on every page once it has settled. Strings
k = K mod N (or the INDEXes given) are printed; harness.screens writes
rips/harness/OUT/screens.jsonl and shots for t5check.
"""
import json, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'rips', 'probe'))
from harness.game import Game
from harness.screens import Screens, read_sprites
from harness.t5bad import EVENT_BOX, EV_RAM, EVENTMES, ST, ev_offset

BOX_Y = 72                     # the event box's text rows are above this


def strings():
    d = open(EVENTMES, 'rb').read()
    n = struct.unpack_from('<I', d, 0)[0] // 4
    o = [struct.unpack_from('<I', d, 4 * k)[0] for k in range(n)] + [len(d)]
    return [d[o[k]:o[k + 1]] for k in range(n)]


def box_glyphs(e):
    return [s for s in read_sprites(e) if s['L'] == 1 and s['y'] < BOX_Y]


def show(g, s, text, limit=6000):
    """Print one string; press circle on each settled page until the box closes."""
    import fixstate
    e = g.e
    body = text[:-2] if text.endswith(b'\xff\x40') else text
    if not body.endswith(b'\xff\x26'):
        body += b'\xff\x26'
    test = body + b'\xff\x40'
    g.load(os.path.join(ST, 'shrine_door.state'))
    fixstate.fix(e)
    for a, v in EVENT_BOX:
        e.write(a, struct.pack('<I', v))
    e.run(2)
    at = EV_RAM + ev_offset(11)
    e.press('triangle', after=0)
    f0, shown, pages, idle, last = e.frame_no, False, 0, 0, 0
    while e.frame_no - f0 < limit:
        if e.frame_no - f0 < 600:
            e.write(at, test)
        e.run(1)
        if box_glyphs(e):
            shown, idle = True, 0
        elif shown:
            idle += 1
            if idle > 90:
                break                  # the box has closed
        if shown and s.hold_c >= 40 and e.frame_no - last >= 60 and box_glyphs(e):
            e.press('circle', hold=4, after=0)
            last = e.frame_no
            pages += 1
    return pages, e.frame_no - f0


def main():
    out, part = sys.argv[1], sys.argv[2]
    K, N = map(int, part.split('/'))
    ss = strings()
    todo = [int(x) for x in sys.argv[3:]] or [k for k in range(len(ss)) if k % N == K]
    g = Game(capture=True)
    s = Screens(g, out)
    log = open(os.path.join(s.dir, 'strings.jsonl'), 'a')
    t0 = time.time()
    for k in todo:
        f = g.e.frame_no
        pages, frames = show(g, s, ss[k])
        log.write(json.dumps(dict(idx=k, frame=f, pages=pages, frames=frames)) + '\n')
        log.flush()
    s.close()
    print(len(todo), 'strings', round(time.time() - t0), 's')


if __name__ == '__main__':
    main()
