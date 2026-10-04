#!/usr/bin/env python3
"""Cut the 55 tall item pictures in ITEM.DAT to HEIGHT rows, in place.

    itempics.py ITEM.DAT [--height 143] [--report]

Boltac's catalog draws an item's picture, then the description below it. Under the tall
(152x152) pictures that left room for 4 lines; asm/catalog_tall_text.asm starts the
text 9 px higher, so the pictures have to end 9 px sooner. Each picture is a copy of the
catalog's parchment with the item drawn on it, so:

- the item is found by comparing the picture with the bare parchment
  (graphics/item_panel_bg.png, the panel behind the picture, captured from the game);
- if it already ends above HEIGHT, the picture is just trimmed and every pixel stays;
- otherwise only the item is moved up and, if it still doesn't fit, scaled down, then
  laid back onto the bare parchment, so the texture stays lined up with the panel
  around it. Untouched parchment keeps its original palette indices.

The game takes the upload size from the TIM header, so a shorter TIM in the same slot
displays cleanly. --report prints what happens to each picture without writing.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import tim
from PIL import Image, ImageFilter

ROOT = os.path.join(os.path.dirname(__file__), '..')
BG = os.path.join(ROOT, 'graphics', 'item_panel_bg.png')
FIRST_TALL, N_TALL = 252, 55       # TIM order: picture 0 placeholder, 251 normal, 55 tall
MARGIN = 2                         # px kept clear above and below a moved item


def tims(d):
    offs = []
    for off in range(0, len(d) - 20, 4):
        m, fl = struct.unpack_from('<II', d, off)
        if m == 0x10 and fl in (8, 9):
            j = off + 8
            L, cx, cy, cw, ch = struct.unpack_from('<I4H', d, j)
            if L == 12 + 2 * cw * ch and cw:
                L2, x, y, w, h = struct.unpack_from('<I4H', d, j + L)
                if L2 == 12 + w * 2 * h and h and h <= 512:
                    offs.append(off)
    return offs


def item_mask(o, bg):
    """Pixels that differ from the bare parchment by more than palette rounding,
    with gaps closed and speckle (blobs under 40 px) dropped."""
    W, H = o.size
    q5 = lambda c: tuple(v >> 3 for v in c)
    m = Image.new('L', (W, H))
    M, O, B = m.load(), o.load(), bg.load()
    for y in range(H):
        for x in range(W):
            a, b = q5(O[x, y]), q5(B[x, y])
            M[x, y] = 255 if sum(abs(a[i] - b[i]) for i in range(3)) > 4 else 0
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    M = m.load()
    seen = set()
    for y in range(H):
        for x in range(W):
            if M[x, y] and (x, y) not in seen:
                comp, i = [(x, y)], 0
                seen.add((x, y))
                while i < len(comp):
                    cx, cy = comp[i]
                    i += 1
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            p = (cx + dx, cy + dy)
                            if 0 <= p[0] < W and 0 <= p[1] < H and M[p] and p not in seen:
                                seen.add(p)
                                comp.append(p)
                if len(comp) < 40:
                    for p in comp:
                        M[p] = 0
    return m


def shorten(d, off, bg, height):
    t = tim.parse(d, off)
    W, H = t['w'], t['h']
    raw = bytes(d[t['pix_off']:t['pix_off'] + W * H])
    clut = t['clut'][:256]
    pal = [tim.rgb(c) for c in clut]
    orig = Image.frombytes('P', (W, H), raw)
    orig.putpalette(sum(pal, ()))
    o = orig.convert('RGB')
    mask = item_mask(o, bg)
    x0, y0, x1, y1 = mask.getbbox()
    if y1 <= height:
        out, what = raw[:W * height], 'trimmed'
    else:
        art, am = o.crop((x0, y0, x1, y1)), mask.crop((x0, y0, x1, y1))
        s = min(1.0, (height - 2 * MARGIN) / (y1 - y0))
        if s < 1.0:
            size = (max(1, round(art.width * s)), max(1, round(art.height * s)))
            art, am = art.resize(size, Image.LANCZOS), am.resize(size, Image.LANCZOS)
        nx = round((x0 + x1) / 2 - art.width / 2)
        ny = max(MARGIN if s < 1.0 else 0, min(y0, height - MARGIN - art.height))
        canvas = bg.crop((0, 0, W, height)).copy()
        canvas.paste(art, (nx, ny), am)
        usable = [i for i, c in enumerate(clut) if c != 0]   # 0x0000 is transparent
        remap = [usable[i] if i < len(usable) else usable[0] for i in range(256)]
        pimg = Image.new('P', (1, 1))
        pimg.putpalette(sum((pal[i] for i in remap), ()))
        qz = canvas.quantize(palette=pimg, dither=Image.Dither.NONE).tobytes()
        out = bytearray(W * height)
        Mk = mask.load()
        for y in range(height):
            for x in range(W):
                inside = nx <= x < nx + art.width and ny <= y < ny + art.height
                out[y * W + x] = raw[y * W + x] if not inside and not Mk[x, y] else remap[qz[y * W + x]]
        what = 'moved up' if s == 1.0 else f'scaled {s:.3f}'
    hdr = t['pix_off'] - 12
    L, vx, vy, vw, vh = struct.unpack_from('<I4H', d, hdr)
    struct.pack_into('<I4H', d, hdr, 12 + vw * 2 * height, vx, vy, vw, height)
    d[t['pix_off']:t['pix_off'] + len(out)] = out
    return what


def main():
    path = sys.argv[1]
    height = int(sys.argv[sys.argv.index('--height') + 1]) if '--height' in sys.argv else 143
    d = bytearray(open(path, 'rb').read())
    offs = tims(d)
    assert len(offs) >= FIRST_TALL + N_TALL, len(offs)
    bg = Image.open(BG).convert('RGB')
    counts = {}
    for k in range(FIRST_TALL, FIRST_TALL + N_TALL):
        h = tim.parse(d, offs[k])['h']
        if h != 152:
            what = f'already {h} rows'
        else:
            what = shorten(d, offs[k], bg, height)
        counts[what.split()[0]] = counts.get(what.split()[0], 0) + 1
        if '--report' in sys.argv:
            print(f'picture {k}: {what}')
    if '--report' not in sys.argv:
        open(path, 'wb').write(d)
    print('tall pictures:', ', '.join(f'{v} {k}' for k, v in counts.items()))


if __name__ == '__main__':
    main()
