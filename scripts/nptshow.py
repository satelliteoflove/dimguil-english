#!/usr/bin/env python3
"""Start a battle against an NPC party, to see its names in the enemy panel.

    nptshow.py STATE OUT.png N [N ...]

STATE is a save state in the maze, free to walk (rips/states/maze_door.state). The
encounter loader (0x80021268) loads the enemy file as table 1 index id+0x2c; NPC parties
use id 379+N, i.e. DATA02/NPTnn.BIN. For each N, the id is forced in RAM, the party
steps back and forth until something attacks, and the screen is captured once the
command menu is up. OUT.png gets one row per N.
"""
import os, struct, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import emu

ROOT = os.path.join(os.path.dirname(__file__), '..')
LOAD = 0x80012f5c


def addiu(rt, imm):
    return struct.pack('<I', 9 << 26 | rt << 16 | imm)


def main():
    state, out, ns = sys.argv[1], sys.argv[2], [int(a) for a in sys.argv[3:]]
    e = emu.Emu(os.path.join(ROOT, 'rips/iso/dimguil-en.cue'))
    e.run(2)
    shots = []
    for n in ns:
        e.load(state); e.run(1)
        e.write(0x8002126c, addiu(5, 379 + n))  # a1 = id
        e.write(0x80021270, addiu(3, 379 + n))  # v1 = id
        e.bp(LOAD)
        for k in range(200):
            e.seq('down w30' if k % 2 == 0 else 'up w30')
            if any(x['regs'][5] == 423 + n for x in e.log()):
                break
        else:
            sys.exit(f'no encounter for NPT{n:02d}')
        e.dbg_clear()
        e.run(480)
        path = f'/tmp/nptshow_{n}.png'
        e.shot(path, scale=1)
        shots.append(Image.open(path))
    w, h = shots[0].size
    sheet = Image.new('RGB', (w, h * len(shots)))
    for k, im in enumerate(shots):
        sheet.paste(im, (0, k * h))
    sheet.save(out)
    print(f'{len(shots)} battles -> {out}')


if __name__ == '__main__':
    main()
