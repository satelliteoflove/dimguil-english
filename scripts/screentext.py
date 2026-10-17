#!/usr/bin/env python3
"""Log every line of text the game draws, from the glyph calls (emulator harness).

Each glyph goes through 0x8001f840 (a0 = x, a1 = y, a2 = layer); a full layer sends it
to 0x8001f9cc instead and the glyph is dropped (docs/engine-notes.md, "Glyph sprite
layers"). The code is in s0, with a two-byte code's first byte in s3, in every printer
seen so far. Before a glyph, 0x8001f4d4 reads the font flags at 0x80079705 (bit 0: the
large font, which has the digraphs). A line is a run of glyphs from one call site on
one layer and row.

    screentext.py STATE "KEYS" [--frames N]   print the lines drawn while KEYS play

As a module: Text(emu).start() ... .lines() -> [Line]
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import emu

ACCEPT, REFUSE = 0x8001f840, 0x8001f9cc
ALLOC = 0x8001f150                    # (size, layer): sets up one layer
FONTREAD = 0x8001f4ec                  # lbu v1, 0x80079705
FONTFLAG = 0x80079705
ROOT = os.path.join(os.path.dirname(__file__), '..')


def vwf_block():
    """VWF_LUT's address in MAIN, from asm/vwf_lut.inc (where vwf.asm puts it)."""
    m = re.search(r'^VWF_LUT_AT\s+equ\s+(0x[0-9a-fA-F]+)', open(os.path.join(ROOT, 'asm/vwf_lut.inc')).read(), re.M)
    return int(m.group(1), 16)


VWF = vwf_block()
s16 = lambda v: (v & 0xffff) - 0x10000 if v & 0x8000 else v & 0xffff


def _decoder():
    t = {}
    for line in open(os.path.join(ROOT, 'tables/dimguil_enc.tbl'), encoding='utf-8'):
        a, sep, b = line.rstrip('\n').partition('=')
        if sep:
            try:
                t.setdefault(int(a, 16), b)
            except ValueError:
                pass
    for line in open(os.path.join(ROOT, 'tables/compression.tbl'), encoding='utf-8'):
        line = line.rstrip('\n')
        if len(line) >= 4 and line[2] == '=':
            t[int(line[3:], 16)] = line[:2]
    return t


DEC = _decoder()
DIGRAPH_CODES = {int(l.rstrip('\n')[3:], 16) for l in
                 open(os.path.join(ROOT, 'tables/compression.tbl'), encoding='utf-8')
                 if len(l.rstrip('\n')) >= 4 and l[2] == '='}


class Line:
    def __init__(self, ra, layer, y, font):
        self.ra, self.layer, self.y, self.font = ra, layer, y, font
        self.glyphs = []                 # (x, code)
        self.cut = False                 # a glyph refused after some were drawn
        self.refused_first = False       # refused at its first glyph (static redraw)

    @property
    def codes(self):
        return [c for _, c in self.glyphs]

    @property
    def text(self):
        return ''.join(DEC.get(c, '<%x>' % c) if c < 0x100 else '<%04x>' % c
                       for c in self.codes)

    @property
    def x0(self):
        return self.glyphs[0][0] if self.glyphs else None

    @property
    def fixed(self):
        """Drawn on an 8 px grid (the fixed-width labels), not by the VWF."""
        xs = [g[0] for g in self.glyphs]
        steps = {b - a for a, b in zip(xs, xs[1:])}
        return len(xs) >= 3 and steps == {8}

    def x1(self, lut):
        """Right edge in pixels: the last glyph's x plus its advance."""
        if not self.glyphs:
            return None
        x, c = self.glyphs[-1]
        return x + (8 if self.fixed or c >= len(lut) else lut[c] + 1)

    def key(self):
        return (self.ra, self.layer, self.y, self.x0, tuple(self.codes))

    def __repr__(self):
        return (f'L{self.layer} y={self.y} x={self.x0} {"fixed " if self.fixed else ""}ra={self.ra:08x} '
                f'{"CUT " if self.cut else ""}{self.text!r}')


class Text:
    def __init__(self, e):
        self.e = e

    def start(self):
        e = self.e
        e.dbg_clear()
        e.bp(ACCEPT)
        e.bp(REFUSE)
        e.watch(FONTFLAG, FONTFLAG + 1, emu.Emu.READ)
        e.bp(ALLOC)
        self.lut = e.read(VWF, 0xd8)
        return self

    def lines(self):
        """Lines drawn since start() (or the last call), in order; repeats kept."""
        return self.lines_from(self.e.log())

    @staticmethod
    def lines_from(log):
        """Group glyph calls into lines: a run of calls from one call site on one layer
        and row, put in x order (right-aligned text is drawn from its end), split where
        the x positions repeat (a redraw) or jump by more than 24 px."""
        runs, cur, font = [], None, 0
        for i, x in enumerate(log):
            if x['type'] == 'R':
                if x['pc'] == FONTREAD:
                    font = x['value'] & 0xff
                continue
            if x['pc'] != ACCEPT:
                continue
            r = x['regs']
            ra, layer, gx, gy = r[31], r[6], s16(r[4]), s16(r[5])
            code = r[16] & 0xff
            if 0xf7 <= r[19] & 0xff < 0xff:
                code |= (r[19] & 0xff) << 8
            refused = i + 1 < len(log) and log[i + 1]['pc'] == REFUSE
            if cur is None or cur[0] != (ra, layer, gy):
                cur = [(ra, layer, gy), font, []]
                runs.append(cur)
            cur[2].append((gx, code, refused))
        out = []
        for (ra, layer, gy), font, gl in runs:
            groups, g, d = [], [], 0
            for item in gl:
                if g:
                    step = item[0] - g[-1][0]
                    sign = (step > 0) - (step < 0)
                    if sign == 0 or (d and sign != d):
                        groups.append(g); g, d = [], 0
                    elif not d:
                        d = sign
                g.append(item)
            groups.append(g)
            for g in groups:
                g.sort()
                piece = [g[0]]
                for item in g[1:]:
                    if item[0] - piece[-1][0] > 24:
                        out.append(Text._line(ra, layer, gy, font, piece)); piece = []
                    piece.append(item)
                out.append(Text._line(ra, layer, gy, font, piece))
        return out

    @staticmethod
    def _line(ra, layer, y, font, items):
        l = Line(ra, layer, y, font)
        l.glyphs = [(gx, c) for gx, c, ref in items if not ref]
        refused = [gx for gx, c, ref in items if ref]
        if refused:
            if l.glyphs and min(refused) > l.glyphs[0][0]:
                l.cut = True
            elif not l.glyphs:
                l.refused_first = True
            else:
                l.cut = True
        return l


def unique(lines):
    seen, out = set(), []
    for l in lines:
        k = l.key() + (l.cut,)
        if k not in seen and (l.glyphs or l.refused_first):
            seen.add(k)
            out.append(l)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('state')
    ap.add_argument('keys', nargs='?', default='')
    ap.add_argument('--frames', type=int, default=30)
    ap.add_argument('--shot')
    ap.add_argument('--cue', default=os.path.join(ROOT, 'rips/iso/dimguil-en.cue'))
    a = ap.parse_args()
    e = emu.Emu(a.cue)
    e.load(a.state)
    e.run(2)
    t = Text(e).start()
    e.seq(a.keys)
    e.run(a.frames)
    for l in unique(t.lines()):
        print(l, l.x1(t.lut))
    if a.shot:
        e.shot(a.shot, scale=1)


if __name__ == '__main__':
    main()
