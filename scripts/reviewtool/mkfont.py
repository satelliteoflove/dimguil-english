#!/usr/bin/env python3
"""Cut the game's dialogue font out of the real text box, for the review tool's preview.

    mkfont.py            (after a build; writes rips/review/font/)

Every glyph code below 0xd8 (letters, punctuation and digraphs) is printed in the
dungeon NPC box by pointing NPC_MES1 strings 0 and 115 at a made-up string, as
npcshow.py does. Each page is shot twice, with and without the glyphs; the pixels
that differ are the glyphs, so the box's see-through background drops out. Glyphs
are cut at the advance the VWF table gives (LUT + 1 px, as descfit.py prices them).

Writes atlas.png (16 cells of 32 px per row), font.json (code -> cell x, y and advance;
the text origin, the cell top of a page's second line, and the line pitch) and box.png
(the empty box, for the preview backdrop). A page's lines start at the box's first line,
the speaker's name included: line j's cell top is top + (j - 1) * pitch.
"""
import json, os, struct, sys
from PIL import Image, ImageChops
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import emu, descfit

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
OUT = os.path.join(ROOT, 'rips/review/font')
STATE = os.path.join(ROOT, 'rips/states/npc_door.state')
BUF = 0x801a0400
X0, MAXW = 27, 280
PITCH = 12  # line pitch; a cell is one line tall, from 2 px above the cap height
NL, END, QUOTE = b'\xff\x21', b'\xff\x40', 0xb6


def adv(c):
    return descfit.LUT[c] + 1


def pages():
    """Codes packed into pages of three lines; the quote opens a line (see npcfit)."""
    codes = [QUOTE] + [c for c in range(0xd8) if c != QUOTE]
    lines, cur, w = [], [], 0
    for c in codes:
        if cur and w + adv(c) > MAXW:
            lines.append(cur); cur, w = [], 0
        cur.append(c); w += adv(c)
    lines.append(cur)
    return [lines[i:i + 3] for i in range(0, len(lines), 3)]


def render(e, data, body):
    data = bytearray(data)
    off = len(data)
    data += body + END
    for h in (0, 115):
        data[4 * h:4 * h + 4] = struct.pack('<I', off)
    data = bytes(data)
    e.load(STATE); e.run(1)
    e.seq('circle w240')
    for f in range(114):
        e.write(BUF, data); e.run(1, ('circle',) if f < 4 else ())
    path = os.path.join(OUT, 'tmp.png')
    e.shot(path, scale=1)
    return Image.open(path).convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    data = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA06/NPC_MES1.OBJ'), 'rb').read()
    e = emu.Emu(os.path.join(ROOT, 'rips/iso/dimguil-en.cue')); e.run(2)
    name = bytes([0x0b])  # "A"
    render(e, data, bytes([0xba])).crop((0, 0, 350, 80)).save(os.path.join(OUT, 'box.png'))
    blank = render(e, data, name)
    cells, rows = {}, None
    for page in pages():
        shot = render(e, data, name + b''.join(NL + bytes(l) for l in page))
        diff = ImageChops.difference(shot, blank).convert('L').point(lambda v: 255 if v > 24 else 0)
        if rows is None:  # line bands from the row profile: name line, then three
            prof = [sum(diff.getpixel((x, y)) for x in range(X0, X0 + MAXW)) for y in range(80)]
            bands, y = [], 0
            while y < 80:
                if prof[y]:
                    y0 = y
                    while y < 80 and prof[y]: y += 1
                    bands.append((y0, y))
                y += 1
            rows = bands
        for k, line in enumerate(page):
            y0, y1 = rows[k]
            x = X0
            for c in line:
                box = (x, y0 - 2, x + adv(c), y0 - 2 + PITCH)
                g = shot.crop(box).convert('RGBA')
                g.putalpha(diff.crop(box))
                cells[c] = g
                x += adv(c)
    h = PITCH
    atlas = Image.new("RGBA", (16 * 32, h * 14), (0, 0, 0, 0))
    meta = {'origin_x': X0, 'top': rows[0][0] - 2, 'pitch': PITCH, 'cell_h': h, 'glyphs': {}}
    for c, g in sorted(cells.items()):
        ax, ay = (c % 16) * 32, (c // 16) * h
        atlas.paste(g, (ax, ay))
        meta['glyphs'][c] = [ax, ay, g.size[0]]
    atlas.save(os.path.join(OUT, 'atlas.png'))
    json.dump(meta, open(os.path.join(OUT, 'font.json'), 'w'))
    os.remove(os.path.join(OUT, 'tmp.png'))
    print(f'{len(cells)} glyphs, rows {rows}, cell height {h}')


if __name__ == '__main__':
    main()
