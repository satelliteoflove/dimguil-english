#!/usr/bin/env python3
"""Render battle messages in the real battle box without waiting for them to happen.

    battleshow.py STATE OUT.png [--monster NAME] TEMPLATE,VERB,NOUN [...]

STATE is a battle state at the party's command menu, made on a build with the same code as
the one being checked. The built FIGHTMSG.OBJ (resident at 0x801d7000)
and I_NAME_E.OBJ (0x801d1000) from rips/dirty are written into RAM with offsets
redirected, so the party's first attack prints the combination asked for:
  TEMPLATE  FIGHTMSG string used in place of the party attack line (98/99); use 108 for a
            monster's attack, or a whole-sentence string such as 88 (breath) or 152
  VERB      FIGHTMSG string used for every weapon verb (1-21)
  NOUN      I_NAME_E string used for every item name (0-426); monster nouns are 558+
The party member stands in for {ff18} and the monster for {ff13}; --monster renames the
monsters (all four English name slots of groups 1-4) to test other name lengths. Every
member is told to attack, and the shot is taken 60 frames after battle_box_print (BATTLE
0x800d1d98) starts on 98 or 99, whoever acts first.

A state keeps the text printer's code from the build it was made on. An older state
would show older wrapping, so the script stops if the state's MAIN code differs from the
build's (until 2026-10-15 it copied the word wrap's old range over instead, which broke
once asm/word_wrap.asm grew). Make a fresh one on the build, e.g. with fightshow.py's
steps (the verbfix work used rips/verbfix/states/battle_m001.state, Pink Mushroom).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import emu
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), '..')
EXE_BASE = 0x8000f800
CODE = (0x800114d8, 0x80024bf0)  # MAIN's game code
MONSTERS = 0x8008a918            # monster_records: group g at +g*0xd0, English names slots 2-5
PRINT = 0x800d1d98               # battle_box_print(3, FIGHTMSG index, 1)
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
    code = exe[CODE[0] - EXE_BASE:CODE[1] - EXE_BASE]
    fm0 = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA01/FIGHTMSG.OBJ'), 'rb').read()
    nm0 = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA06/I_NAME_E.OBJ'), 'rb').read()
    e = emu.Emu(os.path.join(ROOT, 'rips/iso/dimguil-en.cue'))
    e.run(2)
    crops = []
    for tpl, verb, noun in combos:
        e.load(state); e.run(1)
        if e.read(CODE[0], CODE[1] - CODE[0]) != code:
            sys.exit(f'{state} has MAIN code from another build; make a fresh state')
        fm, nm = bytearray(fm0), bytearray(nm0)
        for i in (98, 99):
            fm[4 * i:4 * i + 4] = fm0[4 * tpl:4 * tpl + 4]
        for i in range(1, 22):
            fm[4 * i:4 * i + 4] = fm0[4 * verb:4 * verb + 4]
        for i in range(427):
            nm[4 * i:4 * i + 4] = nm0[4 * noun:4 * noun + 4]
        e.write(0x801d7000, bytes(fm)); e.write(0x801d1000, bytes(nm))
        if monster:
            name = bytes(GLYPH[c] for c in monster) + b'\xff\x40'
            if len(name) > 0x12:
                sys.exit(f'{monster!r}: a name slot holds 16 letters')
            for grp in range(1, 5):
                for slot in range(2, 6):
                    e.write(MONSTERS + grp * 0xd0 + slot * 0x12, name.ljust(0x12, b'\0'))
        e.dbg_clear(); e.bp(PRINT); e.log()
        for _ in range(40):  # commands for each member, confirm, until the party's line
            if any(x['regs'][5] in (98, 99) for x in e.log()):
                break
            e.seq('circle w20')
        else:
            sys.exit(f'no party attack line for {tpl},{verb},{noun}')
        e.dbg_clear()
        e.run(60)
        crops.append(e.image().crop((0, 160, 350, 230)))
    sheet = Image.new('RGB', (700, 70 * ((len(crops) + 1) // 2)))
    for i, im in enumerate(crops):
        sheet.paste(im, ((i % 2) * 350, (i // 2) * 70))
    sheet.save(out)
    print(f'{len(crops)} lines -> {out}')


if __name__ == '__main__':
    main()
