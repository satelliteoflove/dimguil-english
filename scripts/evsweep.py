#!/usr/bin/env python3
"""Print event strings through the real event box and screenshot every page.

    evsweep.py OUTDIR [INDEX ... | K/N]     (after a build; default: all of EVENTMES)

Uses the Shrine door (rips/states/shrine_door.state): search there prints EVENTMES 11,
loaded at 0x801a0400. Its text is overwritten in RAM with the string under test (plus
{ff26} so the last page waits), the box is left to print, and each time it settles the
frame is saved and circle pressed. The state predates the current build, so the code
patches that touch this box are written into RAM after loading.

Writes OUTDIR/NNN_K.png (the box, 350x64) and OUTDIR/NNN.json: the pages, whether the
glyph layer filled up (the box's pool was used to the last sprite) and the frame count.
"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../rips/probe'))
import emu, fixstate

DIRTY = 'rips/dirty/dimguil'
EV_RAM, SHRINE = 0x801a0400, 11
USED, TABLE = 0x80079938, 0x8008b390
BOX = (0, 8, 350, 72)


def strings():
    d = open(f'{DIRTY}/DATA06/EVENTMES.BIN', 'rb').read()
    n = struct.unpack_from('<I', d, 0)[0] // 4
    o = [struct.unpack_from('<I', d, 4 * i)[0] for i in range(n)] + [len(d)]
    return [d[o[i]:o[i + 1]] for i in range(n)], o


def patches():
    exe = open(f'{DIRTY}/SLPS_026.91', 'rb').read()
    maze = open(f'{DIRTY}/MAZE.BIN', 'rb').read()
    return [(0x8001ffe8, exe[0x8001ffe8 - 0x8000f800:][:4]),
            (0x80021bfc, exe[0x80021bfc - 0x8000f800:][:4]),
            (0x800a3134, maze[0x800a3134 - 0x800a1000:][:8])]


def waits(s):
    """Pages the box stops on: each {ff26}, and a page break ({ff20}) with none before it."""
    n, i, last = 0, 0, None
    while i < len(s):
        if s[i] == 0xff:
            c = s[i + 1]
            n += c == 0x26 or (c == 0x20 and last != 0x26)
            last = c; i += 2
        else:
            last = None; i += 2 if s[i] >= 0xf7 else 1
    return n


def diff(a, b):
    return sum(1 for p, q in zip(a.getdata(), b.getdata()) if p != q)


def show(e, s, at, out, idx, P):
    body = s[:-2] if s.endswith(b'\xff\x40') else s
    if not body.endswith(b'\xff\x26'):
        body += b'\xff\x26'
    test = body + b'\xff\x40'
    want = waits(test)
    e.load('rips/states/shrine_door.state'); fixstate.fix(e); e.run(2)
    for a, b in P:
        e.write(a, b)
    blank = e.image().crop(BOX)
    e.press('triangle', after=0)
    pages, full, frames = [], False, 0
    prev, still, shown = None, 0, False
    while frames < 9000 and len(pages) < want:
        if frames < 330:
            e.write(at, test)
        e.run(1); frames += 1
        used = struct.unpack('<h', e.read(USED + 2, 2))[0]
        size = struct.unpack('<h', e.read(TABLE + 6 + 2, 2))[0]
        if size and used >= size:
            full = True
        im = e.image().crop(BOX)
        if prev is not None and diff(im, prev) == 0:
            still += 1
        else:
            still = 0
        prev = im
        if diff(im, blank) > 200:
            shown = True
        if still == 40:
            if not shown or diff(im, blank) < 200:
                if shown:
                    break            # the box has closed
                continue
            if pages and diff(im, pages[-1]) == 0:
                break
            pages.append(im)
            e.press('circle', after=0); frames += 4
            still = 0
    names = []
    for k, im in enumerate(pages):
        p = os.path.join(out, f'{idx:03d}_{k}.png'); im.save(p); names.append(os.path.basename(p))
    json.dump({'index': idx, 'pages': names, 'expected': want, 'pool_full': full, 'frames': frames},
              open(os.path.join(out, f'{idx:03d}.json'), 'w'))
    return names, full


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    ss, o = strings()
    args = sys.argv[2:]
    if args and '/' in args[0]:              # K/N: every Nth string from K, for parallel runs
        k, n = map(int, args[0].split('/'))
        want = range(k, len(ss), n)
    else:
        want = [int(a) for a in args] or range(len(ss))
    P = patches()
    e = emu.Emu(f'rips/iso/dimguil-en.cue'); e.run(2)
    for i in want:
        names, full = show(e, ss[i], EV_RAM + o[SHRINE], out, i, P)
        print(i, len(names), 'POOL FULL' if full else '', flush=True)


if __name__ == '__main__':
    main()
