#!/usr/bin/env python3
"""4/8bpp TIM helpers for images embedded in container files.

tim.py export FILE OFFSET OUT.png          -- indexed PNG using the TIM's first CLUT row
tim.py import FILE OFFSET IN.png OUTFILE   -- replace pixel data from an indexed PNG
                                              (PNG palette indices are written as-is)
"""
import struct, sys
from PIL import Image


def parse(d, off):
    magic, flags = struct.unpack_from('<II', d, off)
    assert magic == 0x10, 'not a TIM'
    bpp = [4, 8, 16, 24][flags & 3]
    j = off + 8
    clut = None
    if flags & 8:
        L, cx, cy, cw, ch = struct.unpack_from('<I4H', d, j)
        clut = [struct.unpack_from('<H', d, j + 12 + 2 * k)[0] for k in range(cw * ch)]
        j += L
    L, x, y, w, h = struct.unpack_from('<I4H', d, j)
    return dict(bpp=bpp, clut=clut, pix_off=j + 12, words_w=w, h=h,
                w={4: w * 4, 8: w * 2}.get(bpp, w), vram=(x, y))


def rgb(c):
    return ((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31)


def export(d, off, out):
    t = parse(d, off)
    assert t['bpp'] in (4, 8)
    n = t['w'] * t['h']
    raw = d[t['pix_off']:t['pix_off'] + t['words_w'] * 2 * t['h']]
    if t['bpp'] == 4:
        idx = bytearray()
        for b in raw:
            idx += bytes((b & 15, b >> 4))
    else:
        idx = bytearray(raw)
    im = Image.frombytes('P', (t['w'], t['h']), bytes(idx[:n]))
    pal = []
    for c in (t['clut'] or [])[: 1 << t['bpp']]:
        pal += rgb(c)
    im.putpalette(pal + [0] * (768 - len(pal)))
    im.save(out)


def import_(d, off, png):
    t = parse(d, off)
    im = Image.open(png)
    assert im.mode == 'P' and im.size == (t['w'], t['h']), (im.mode, im.size, t['w'], t['h'])
    px = im.tobytes()
    if t['bpp'] == 4:
        assert max(px) < 16
        raw = bytes(px[i] | (px[i + 1] << 4) for i in range(0, len(px), 2))
    else:
        raw = px
    d = bytearray(d)
    d[t['pix_off']:t['pix_off'] + len(raw)] = raw
    return bytes(d)


if __name__ == '__main__':
    cmd, f, off = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
    d = open(f, 'rb').read()
    if cmd == 'export':
        export(d, off, sys.argv[4])
    elif cmd == 'import':
        open(sys.argv[5], 'wb').write(import_(d, off, sys.argv[4]))
