#!/usr/bin/env python3
"""Render event script strings (EVENTMES) in the real dungeon text box.

    evshow.py STATE OUTDIR IDX [IDX ...]

Uses npcshow.py's scene: STATE stands at the maze's first door (rips/states/
maze_door.state), where the talk with Guy's party prints NPC_MES1 string 0 or 115. The
built EVENTMES string IDX is appended to the built NPC_MES1.OBJ and both hook strings
are pointed at it, so the box prints the event text instead. Pages break at {ff26};
one screenshot per page goes to OUTDIR/ev_IDX_p.png, plus OUTDIR/sheet_ev.png.
"""
import json, os, re, struct, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import emu
from npcshow import BUF, HOOKS, BOX

ROOT = os.path.join(os.path.dirname(__file__), '..')


def main():
    state, outdir, idxs = sys.argv[1], sys.argv[2], [int(a) for a in sys.argv[3:]]
    os.makedirs(outdir, exist_ok=True)
    npc = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA06/NPC_MES1.OBJ'), 'rb').read()
    ev = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA06/EVENTMES.BIN'), 'rb').read()
    n = struct.unpack('<I', ev[:4])[0] // 4
    offs = [struct.unpack('<I', ev[4 * i:4 * i + 4])[0] for i in range(n)] + [len(ev)]
    tr = json.load(open(os.path.join(ROOT, 'translations/EVENTMES.BIN.json'), encoding='utf-8'))
    strings = tr['sections'][0]['strings']
    e = emu.Emu(os.path.join(ROOT, 'rips/iso/dimguil-en.cue'))
    e.run(2)
    crops = []
    for idx in idxs:
        patched = bytearray(npc + ev[offs[idx]:offs[idx + 1]])
        for h in HOOKS:
            patched[4 * h:4 * h + 4] = struct.pack('<I', len(npc))
        patched = bytes(patched)
        e.load(state); e.run(1)
        e.seq('circle w240')
        for f in range(114):  # the talk reloads the file; keep the patch on top of it
            e.write(BUF, patched)
            e.run(1, ('circle',) if f < 4 else ())
        npages = len(re.split(r'\{ff26\}', strings[idx]['translation'].rstrip('\r').removesuffix('{ff26}')))
        for p in range(npages):
            if p:
                e.seq('circle w90')
            path = os.path.join(outdir, f'ev_{idx}_{p}.png')
            e.shot(path, scale=1)
            crops.append(Image.open(path).crop(BOX))
    sheet = Image.new('RGB', (BOX[2], BOX[3] * len(crops)))
    for k, im in enumerate(crops):
        sheet.paste(im, (0, k * BOX[3]))
    sheet.save(os.path.join(outdir, 'sheet_ev.png'))
    print(f'{len(crops)} pages -> {outdir}/sheet_ev.png')


if __name__ == '__main__':
    main()
