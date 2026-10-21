#!/usr/bin/env python3
"""Rebuild the review tool's empty text box (rips/review/font/box.png) over a calmer backdrop.

    mkbox.py SHOT.png [Y]      (SHOT: a 350x240 maze screenshot; Y: the top row to take, default 60)

mkfont.py cuts box.png from its NPC state, where the box sits over the Shrine door with
Guy's head showing below it. This keeps the box's geometry and redraws it over 80 rows
of SHOT: the see-through window (x 27-320, y 17-62) darkens what's behind it to about a
quarter plus a little grey, as measured on mkfont's box across its top and bottom edges
(inside = 0.25 * behind + 20), and the frame is a 1 px grey line at x 26 and 321, y 16
and 63. Columns 0-13 and 334-349 stay black, as in the game's view. The old box is kept
as box-door.png.
"""
import os, sys, shutil
import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
FONT = os.path.join(ROOT, 'rips/review/font')
X0, X1, Y0, Y1 = 26, 321, 16, 63
K, C = 0.25, np.array([22.0, 19.0, 21.0])
FRAME = np.array([70.0, 70.0, 74.0])


def main():
    shot = Image.open(sys.argv[1]).convert('RGB')
    y = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    bg = np.asarray(shot.crop((0, y, 350, y + 80))).astype(float)
    out = bg.copy()
    out[Y0 + 1:Y1, X0 + 1:X1] = K * bg[Y0 + 1:Y1, X0 + 1:X1] + C
    out[[Y0, Y1], X0:X1 + 1] = FRAME
    out[Y0:Y1 + 1, [X0, X1]] = FRAME
    out[:, :14] = 0
    out[:, 334:] = 0
    box = os.path.join(FONT, 'box.png')
    keep = os.path.join(FONT, 'box-door.png')
    if not os.path.exists(keep):
        shutil.copy(box, keep)
    Image.fromarray(out.clip(0, 255).astype('uint8')).save(box)
    print('wrote', box)


if __name__ == '__main__':
    main()
