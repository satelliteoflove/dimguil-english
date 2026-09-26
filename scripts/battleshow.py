#!/usr/bin/env python3
"""Render battle messages in the real battle box without waiting for them to happen.

    battleshow.py STATE OUT.png TEMPLATE,VERB,NOUN [...]

STATE is a battle state where the party gets the first move (rips/states/battle_wriggle
.state: two Wriggle Objects, preemptive). The built FIGHTMSG.OBJ (resident at 0x801d7000)
and I_NAME_E.OBJ (0x801d1000) from rips/dirty are written into RAM with offsets
redirected, so the party's first attack prints the combination asked for:
  TEMPLATE  FIGHTMSG string used in place of the party attack line (98/99); use 108 for a
            monster's attack, or a whole-sentence string such as 88 (breath) or 152
  VERB      FIGHTMSG string used for every weapon verb (1-21)
  NOUN      I_NAME_E string used for every item name (0-426); monster nouns are 558+
The party member stands in for {ff18} and the Wriggle Object for {ff13}.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import emu
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), '..')


def main():
    state, out = sys.argv[1], sys.argv[2]
    combos = [tuple(map(int, c.split(','))) for c in sys.argv[3:]]
    fm0 = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA01/FIGHTMSG.OBJ'), 'rb').read()
    nm0 = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA06/I_NAME_E.OBJ'), 'rb').read()
    e = emu.Emu(os.path.join(ROOT, 'rips/iso/dimguil-en.cue'))
    e.run(2)
    crops = []
    for tpl, verb, noun in combos:
        e.load(state); e.run(1)
        fm, nm = bytearray(fm0), bytearray(nm0)
        for i in (98, 99):
            fm[4 * i:4 * i + 4] = fm0[4 * tpl:4 * tpl + 4]
        for i in range(1, 22):
            fm[4 * i:4 * i + 4] = fm0[4 * verb:4 * verb + 4]
        for i in range(427):
            nm[4 * i:4 * i + 4] = nm0[4 * noun:4 * noun + 4]
        e.write(0x801d7000, bytes(fm)); e.write(0x801d1000, bytes(nm))
        for _ in range(13):  # commands for four members, confirm, first attack
            e.seq('circle w50')
        crops.append(e.image().crop((0, 160, 350, 230)))
    sheet = Image.new('RGB', (700, 70 * ((len(crops) + 1) // 2)))
    for i, im in enumerate(crops):
        sheet.paste(im, ((i % 2) * 350, (i // 2) * 70))
    sheet.save(out)
    print(f'{len(crops)} lines -> {out}')


if __name__ == '__main__':
    main()
