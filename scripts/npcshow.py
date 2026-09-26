#!/usr/bin/env python3
"""Render NPC dialogue strings in the real dungeon text box, without reaching each NPC.

    npcshow.py STATE OUTDIR N IDX [IDX ...]

STATE is a save state standing at the first door of the maze, facing it, before
pressing circle (Guy's party is behind it; NPC_MES1 string 0 or 115 opens the talk).
For each IDX the scene is replayed: once the game has loaded NPC_MES1 to 0x801a0400,
the built NPC_MESn.OBJ from rips/dirty is written over it every frame (the talk
reloads it) with the offsets of strings 0 and 115 pointed at IDX, so IDX is what the box prints.
One screenshot per page goes to OUTDIR/n_IDX_p.png, plus OUTDIR/sheet_n.png with
every page stacked.
"""
import json, os, re, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import emu

ROOT = os.path.join(os.path.dirname(__file__), '..')
BUF = 0x801a0400
HOOKS = (0, 115)  # the scene opens with 0 on a fresh save, 115 once greeted
BOX = (0, 0, 350, 70)


def main():
    state, outdir, n, idxs = sys.argv[1], sys.argv[2], int(sys.argv[3]), [int(a) for a in sys.argv[4:]]
    os.makedirs(outdir, exist_ok=True)
    data = open(os.path.join(ROOT, f'rips/dirty/dimguil/DATA06/NPC_MES{n}.OBJ'), 'rb').read()
    tr = json.load(open(os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json'), encoding='utf-8'))
    strings = tr['sections'][0]['strings']
    e = emu.Emu(os.path.join(ROOT, 'rips/iso/dimguil-en.cue'))
    e.run(2)
    crops = []
    for idx in idxs:
        e.load(state); e.run(1)
        e.seq('circle w240')
        patched = bytearray(data)
        for h in HOOKS:
            patched[4 * h:4 * h + 4] = data[4 * idx:4 * idx + 4]
        patched = bytes(patched)
        for f in range(114):  # the talk reloads the file; keep the patch on top of it
            e.write(BUF, patched)
            e.run(1, ('circle',) if f < 4 else ())
        text = strings[idx]['translation']
        npages = len(re.split(r'\n\r|\{ff40\}\r', text)) if text else 1
        for p in range(npages):
            if p:
                e.seq('circle w90')
            path = os.path.join(outdir, f'{n}_{idx}_{p}.png')
            e.shot(path, scale=1)
            crops.append(Image.open(path).crop(BOX))
    sheet = Image.new('RGB', (BOX[2], BOX[3] * len(crops)))
    for k, im in enumerate(crops):
        sheet.paste(im, (0, k * BOX[3]))
    sheet.save(os.path.join(outdir, f'sheet_{n}.png'))
    print(f'{len(crops)} pages -> {outdir}/sheet_{n}.png')


if __name__ == '__main__':
    main()
