#!/usr/bin/env python3
"""Render battle messages in the real battle box without waiting for them to happen.

    battleshow.py STATE OUT.png [--monster NAME] TEMPLATE,VERB,NOUN [...]

STATE is a battle state where the party gets the first move (rips/states/battle_wriggle
.state: two Wriggle Objects, preemptive). The built FIGHTMSG.OBJ (resident at 0x801d7000)
and I_NAME_E.OBJ (0x801d1000) from rips/dirty are written into RAM with offsets
redirected, so the party's first attack prints the combination asked for:
  TEMPLATE  FIGHTMSG string used in place of the party attack line (98/99); use 108 for a
            monster's attack, or a whole-sentence string such as 88 (breath) or 152
  VERB      FIGHTMSG string used for every weapon verb (1-21)
  NOUN      I_NAME_E string used for every item name (0-426); monster nouns are 558+
The party member stands in for {ff18} and the Wriggle Object for {ff13}; --monster
renames the Wriggle Objects (all four English name slots) to test other name lengths.
The state's copy of the text printer's word wrap (asm/word_wrap.asm) is replaced with
the built one, so older states show the current wrapping.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import emu
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), '..')
EXE_BASE = 0x8000f800
WRAP = (0x8001e19c, 0x8001e410)  # asm/word_wrap.asm patches within this range
MONSTERS = 0x801b0680            # this battle's monster record; English names at slots 2-5
GLYPH = {}
for line in open(os.path.join(ROOT, 'tables/dimguil_enc.tbl'), encoding='utf-8'):
    k, sep, v = line.rstrip('\n').partition('=')
    if sep and len(v) == 1 and len(k) <= 2 and v not in GLYPH:
        GLYPH[v] = int(k, 16)


def main():
    state, out, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    monster = None
    if args[:1] == ['--monster']:
        monster, args = args[1], args[2:]
    combos = [tuple(map(int, c.split(','))) for c in args]
    exe = open(os.path.join(ROOT, 'rips/dirty/dimguil/SLPS_026.91'), 'rb').read()
    wrap = exe[WRAP[0] - EXE_BASE:WRAP[1] - EXE_BASE]
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
        e.write(WRAP[0], wrap)
        if monster:
            name = bytes(GLYPH[c] for c in monster) + b'\xff\x40'
            for slot in range(2, 6):
                e.write(MONSTERS + slot * 0x12, name.ljust(0x12, b'\0'))
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
