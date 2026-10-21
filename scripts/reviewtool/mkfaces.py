#!/usr/bin/env python3
"""Cut each cast member's face from the game's portraits, for the review tool.

    python3 scripts/reviewtool/mkfaces.py [--root DIR]

Reads rips/clean/dimguil/DATA06/NPC_nn.BIN: a 256-colour CLUT (512 bytes, 15-bit
PlayStation colour) then 256x256 8bpp pixels. The portrait file is the character id + 1
(ids in docs/re/C-talk.md section 3). Most portraits are a headless body with the face
as separate expression tiles beside it; the crop takes the first tile, the neutral face.
Gaura, the mysterious man and Agan have the face drawn on the body.

Writes rips/review/faces/<cast id>.png (the crop padded to a square with black, scaled
up by a whole number to at least 96 px, nearest neighbour) and contact.png, every face
with its name, for checking by eye. The crops for Balbo and Gaura are the ones the line
page mockup used (rips/review/mockup).
"""
import os, struct, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1]) if '--root' in sys.argv \
    else os.path.abspath(os.path.join(HERE, '..', '..'))

# cast id: (character id, (x, y, w, h) of the face in the 256x256 portrait)
FACES = {
    'guy':         (0,  (128, 4, 32, 44)),
    'linaria':     (1,  (132, 4, 52, 56)),
    'alstron':     (2,  (160, 0, 40, 48)),
    'lychee':      (3,  (0, 128, 48, 56)),
    'balbo':       (4,  (160, 0, 48, 48)),
    'alba':        (5,  (128, 0, 40, 56)),
    'rosea':       (6,  (128, 0, 64, 56)),
    'reiran':      (7,  (160, 0, 40, 40)),
    'gaura':       (8,  (64, 8, 48, 48)),
    'fontana':     (9,  (136, 0, 48, 56)),
    'zaril':       (10, (128, 4, 64, 64)),
    'artemisia':   (11, (96, 0, 32, 40)),
    'lilia':       (12, (128, 0, 48, 56)),
    'cephala':     (13, (108, 0, 48, 48)),
    'fritillaria': (14, (112, 0, 48, 40)),
    'cleo':        (15, (8, 128, 48, 48)),
    'bergamot':    (16, (104, 0, 56, 64)),
    'cresson':     (17, (8, 128, 48, 56)),
    'mystery':     (18, (32, 8, 48, 48)),
    'agan':        (19, (40, 0, 48, 48)),
}


def portrait(char_id):
    b = open(os.path.join(ROOT, f'rips/clean/dimguil/DATA06/NPC_{char_id + 1:02d}.BIN'), 'rb').read()
    clut = struct.unpack('<256H', b[:512])
    pal = []
    for c in clut:
        pal += [round((c & 31) * 255 / 31), round((c >> 5 & 31) * 255 / 31), round((c >> 10 & 31) * 255 / 31)]
    im = Image.frombytes('P', (256, 256), b[512:512 + 65536])
    im.putpalette(pal)
    return im.convert('RGB')


def face(cast_id):
    char_id, (x, y, w, h) = FACES[cast_id]
    crop = portrait(char_id).crop((x, y, x + w, y + h))
    side = max(w, h)
    sq = Image.new('RGB', (side, side))
    sq.paste(crop, ((side - w) // 2, (side - h) // 2))
    k = -(-96 // side)
    return sq.resize((side * k, side * k), Image.NEAREST)


def main():
    out = os.path.join(ROOT, 'rips/review/faces')
    os.makedirs(out, exist_ok=True)
    cell = 140
    sheet = Image.new('RGB', (cell * 5, (cell + 20) * 4), (23, 27, 34))
    d = ImageDraw.Draw(sheet)
    for k, cid in enumerate(FACES):
        im = face(cid)
        im.save(os.path.join(out, f'{cid}.png'))
        show = im.resize((128, 128), Image.NEAREST)
        x, y = (k % 5) * cell + 6, (k // 5) * (cell + 20) + 6
        sheet.paste(show, (x, y))
        d.text((x, y + 130), cid, fill=(227, 229, 233))
    sheet.save(os.path.join(out, 'contact.png'))
    print(f'{len(FACES)} faces in {out}')


if __name__ == '__main__':
    main()
