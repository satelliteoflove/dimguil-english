#!/usr/bin/env python3
"""Check every item catalog description against the lines its picture leaves visible.

    itemfit.py [translations/ITEM.DAT.json]

The item catalog draws the picture, then the description below it, and clips the text
at the bottom of the parchment (y=227); it can't scroll. ITEM.DAT holds two picture sizes: 152x108 (text starts
at y=129, 7 lines of 13 px fit) and 152x152, where the original starts the text 39 px
lower and 4 lines fit. asm/catalog_tall_text.asm cuts that to 30 px and itempics.py cuts
the tall pictures to 143 rows, so 5 lines fit. Width is 144 px for both.

TALL lists the ITEM.DAT section 1 indices whose item uses a tall picture. Description k
belongs to item k up to 24 and to item k+1 from 25 on: entry 24 holds two strings, the
Battle Axe's, then after the {ff40} terminator the Nunchaka's (item 25). Each string is
checked on its own; both items have normal pictures. Picture per item comes from the Bartok's Trading Post item
table (data/items/dim/ps.json, from Emonoya): files 253-307.gif are the 152x152 set.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from reviewpage import load
from descfit import line_widths

TALL = {2, 6, 11, 23, 25, 50, 52, 62, 64, 76, 77, 81, 88, 94, 111, 116, 117, 122, 124,
        130, 141, 145, 147, 157, 159, 172, 178, 179, 180, 181, 182, 187, 191, 195, 197,
        199, 200, 201, 215, 222, 225, 226, 227, 231, 232, 233, 236, 237, 238, 244, 253,
        254, 256, 267, 298}
WIDTH = 144


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), '..', 'translations', 'ITEM.DAT.json')
    strings = load(path)['sections'][1]['strings']
    bad = 0
    for k, s in enumerate(strings):
        text = s['translation']
        if not text:
            continue
        for part, piece in enumerate(text.split('{ff40}')):
            lw = line_widths(piece)
            tall = k in TALL and part == 0
            cap = 5 if tall else 7
            if len(lw) > cap or max(lw) > WIDTH:
                bad += 1
                print(f'!! 1:{k:<4} {len(lw)} lines (max {cap}{", tall picture" if tall else ""}), '
                      f'widest {max(lw)}px  {piece.splitlines()[0]}')
    print(f'{bad} descriptions over budget')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
