#!/usr/bin/env python3
"""Print Dimguil's records with their fields named (layouts: scripts/re/types.h).

    recdump.py roster RAMDUMP [INDEX ...]   roster records from a 2 MB RAM dump
    recdump.py party RAMDUMP                the current party mirror and the party table
    recdump.py item ID [ID ...]             item records from the original executable
    recdump.py monster FILE ...             the record at the end of M_DTnnn.BIN / NPTnn.BIN
    recdump.py monster --profile            distinct values per byte over every M_DT record

RAM dumps are rips/probe/*.bin and rips/probe/bodies/*.bin (2 MB from 0x80000000).
"""
import collections, glob, os, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from gametext import dec

DISC = os.path.join(ROOT, 'rips/clean/dimguil')
RACES = 'Human Elf Dwarf Gnome Hobbit Faerie Lizardman Dracon Rawulf Mook Felpurr'.split()
CLASSES = ('Fighter Mage Priest Thief Samurai Lord Valkyrie Ranger Bard Alchemist Psionic '
           'Bishop Ninja Monk').split()
ALIGN = ['Good', 'Neutral', 'Evil', '?']
STATUS = ['afraid', 'confused', 'poisoned', 'asleep', 'KO', 'paralyzed', 'stoned', 'dead',
          'ashes', 'lost']
STATS = 'Str IQ Pie Vit Agi Luc'.split()


def ram_at(ram, addr, n):
    return ram[addr - 0x80000000:addr - 0x80000000 + n]


def exe_at(addr, n):
    exe = open(os.path.join(DISC, 'SLPS_026.91'), 'rb').read()
    return exe[addr - 0x8000f800:addr - 0x8000f800 + n]


def pack_slot(v):
    if v == 0xffff:
        return None
    flags = [n for b, n in ((0x8000, 'cursed'), (0x4000, 'id'), (0x2000, 'eq'), (0x1000, 'main'),
                            (0x0800, 'sub')) if v & b]
    return f'{v & 0x1ff}' + (f'({",".join(flags)})' if flags else '')


def roster(ram, idx):
    r = ram_at(ram, 0x8007d708 + idx * 0xd0, 0xd0)
    if r[0] == 0xff and r[1] == 0x40:
        return f'{idx:2d}: (empty)'
    st = struct.unpack_from('<H', r, 0xe)[0]
    gold, = struct.unpack_from('<I', r, 0x1c)
    items = [pack_slot(v) for v in struct.unpack_from('<10H', r, 0x20)]
    exp, = struct.unpack_from('<I', r, 0x40)
    lv, hp, mlv, mhp = struct.unpack_from('<HhHh', r, 0x44)
    kills, = struct.unpack_from('<I', r, 0xc0)
    lines = [f'{idx:2d}: {dec(r, 0)!r} {RACES[r[0xa] & 0x3f] if (r[0xa] & 0x3f) < 11 else r[0xa]} '
             f'{ALIGN[r[0xa] >> 6]} {CLASSES[r[0xb] & 0x7f] if (r[0xb] & 0x7f) < 14 else r[0xb]} '
             f'{"F" if r[0xb] & 0x80 else "M"}  age {r[0x10]}y {r[0x11]}w {r[0x12]}d  '
             f'status {",".join(n for b, n in enumerate(STATUS) if st >> b & 1) or "OK"}',
             '    ' + ' '.join(f'{n} {struct.unpack_from("b", r, 0x13 + k)[0]}' for k, n in enumerate(STATS))
             + f'  L{lv} (max {mlv})  HP {hp}/{mhp}  EXP {exp}  gold {gold}  AC {struct.unpack_from("b", r, 0x86)[0]}'
             + f'  regen {struct.unpack_from("b", r, 0x8b)[0]}  kills {kills}  deaths {r[0xc4]}',
             '    pack ' + ' '.join(f'{s}' + (f'x{r[0x34 + k]}' if r[0x34 + k] else '')
                                     for k, s in enumerate(items) if s),
             '    spells known ' + ' '.join(r[0x4c + 4 * k:0x50 + 4 * k].hex() for k in range(4)) +
             '  points ' + ' '.join(r[0x5c + 7 * k:0x63 + 7 * k].hex() for k in range(4)),
             f'    where {"town" if r[0x7a] == 0xff else f"area {r[0x7a]} x {r[0x7b]} y {r[0x7c]} facing {r[0x7d]}"}'
             f'  poison {r[0x78]}  met {r[0xc6:0xc9].hex()}  marks {r[0xca:0xcc].hex()}']
    return '\n'.join(lines)


ITEM_FIELDS = [('category', 2, 'B'), ('subtype', 3, 'B'), ('flags04', 4, 'B'), ('specials', 5, 'B'),
               ('equip_effect', 0xd, 'B'), ('break_chance', 0xe, 'H'), ('break_into', 0x10, 'H'),
               ('price', 0x12, 'I'), ('sell', 0x16, 'I'), ('stock', 0x1a, 'B'),
               ('battle_spell', 0x1b, 'B'), ('class_mask', 0x1c, 'H'), ('race_mask', 0x1e, 'H'),
               ('regen', 0x21, 'b'), ('ac', 0x35, 'b'), ('to_hit', 0x36, 'b'), ('dice_n', 0x37, 'B'),
               ('dice_sides', 0x38, 'B'), ('dice_bonus', 0x39, 'b'), ('extra_swings', 0x3a, 'b'),
               ('slay_mask', 0x3e, 'I')]


def item(i):
    r = exe_at(0x80052bf2 + i * 0x4c, 0x4c)
    f = {n: struct.unpack_from('<' + t, r, o)[0] for n, o, t in ITEM_FIELDS}
    hexy = {'flags04', 'specials', 'class_mask', 'race_mask', 'slay_mask', 'battle_spell'}
    return f'{i:3d}: ' + ' '.join(f'{n}={v:#x}' if n in hexy else f'{n}={v}' for n, v in f.items()) + \
        f'\n     unknown +06 {r[6:0xd].hex()} +20 {r[0x20]:02x} +22 {r[0x22:0x35].hex()} ' \
        f'+3b {r[0x3b:0x3e].hex()} +42 {r[0x42:0x4c].hex()}'


def monster(path):
    d = open(path, 'rb').read()[-0xd0:]
    names = [dec(d, o) for o in range(0, 0x6c, 0x12)]
    return f'{os.path.basename(path)}: id {struct.unpack_from("<H", d, 0x6c)[0]} {names[2]!r} ' \
        f'({names[0]}) family {struct.unpack_from("<I", d, 0xa8)[0]:#010x}\n' + \
        '\n'.join(f'   +{o:02x}: ' + ' '.join(f'{b:02x}' for b in d[o:o + 16]) for o in range(0x6c, 0xd0, 16))


def profile():
    recs = {open(f, 'rb').read()[-0xd0:] for f in glob.glob(os.path.join(DISC, 'DATA02/M_DT*.BIN'))}
    print(f'{len(recs)} distinct records')
    for o in range(0x6c, 0xd0):
        c = collections.Counter(r[o] for r in recs)
        if len(c) > 1:
            print(f'+{o:02x} {len(c):3d}  ' + ' '.join(f'{v}:{n}' for v, n in c.most_common(10)))


def main():
    a = sys.argv[1:]
    if len(a) < 1:
        print(__doc__); return 1
    if a[0] == 'roster':
        ram = open(a[1], 'rb').read()
        for i in ([int(x, 0) for x in a[2:]] or range(20)):
            print(roster(ram, i))
    elif a[0] == 'party':
        ram = open(a[1], 'rb').read()
        print('current', ram_at(ram, 0x8007e810, 0x36).hex())
        for p in range(20):
            r = ram_at(ram, 0x8008f8c8 + p * 0x36, 0x36)
            if r[0] != 0xff:
                print(f'party {p:2d}', r.hex())
    elif a[0] == 'item':
        for x in a[1:]:
            print(item(int(x, 0)))
    elif a[0] == 'monster':
        if a[1:] == ['--profile']:
            profile()
        else:
            for f in a[1:]:
                print(monster(f))
    else:
        print(__doc__); return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
