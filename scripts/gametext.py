#!/usr/bin/env python3
"""Decode raw game text bytes with tables/dimguil_dec.tbl, and map disc files to the
executable's load tables.

    gametext.py FILE OFFSET [LENGTH]   decode bytes (to the next {ff40} if no LENGTH)
    gametext.py --files [PATTERN]      list (table, index) -> file, sectors

Single bytes below 0xf7 are glyphs; 0xf7xx-0xfexx are two-byte glyphs; 0xffxx are
control codes, printed as {ffxx} ({ff40} ends a string, {ff21} is a line break).
The file loaders take (dest, index, table); the four tables are listed in relocate.py.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from relocate import TABLES, TABLE_LEN, EXE_BASE, unbcd

ROOT = os.path.join(os.path.dirname(__file__), '..')
T = {}
for line in open(os.path.join(ROOT, 'tables/dimguil_dec.tbl'), encoding='utf-8'):
    k, sep, v = line.rstrip('\n').partition('=')
    if sep:
        T[int(k, 16)] = v


def dec(d, i=0, n=None):
    out, end = [], len(d) if n is None else i + n
    while i < end:
        b = d[i]
        if b >= 0xf7 and i + 1 < len(d):
            c = b << 8 | d[i + 1]
            if n is None and c == 0xff40:
                break
            out.append('{%04x}' % c if b == 0xff else T.get(c, '〓'))
            i += 2
        else:
            out.append(T.get(b, '<%02x>' % b))
            i += 1
    return ''.join(out)


def file_map():
    clean = os.path.join(ROOT, 'rips/clean')
    xml = open(os.path.join(clean, 'dimguil.xml'), encoding='utf-8').read()
    by_lba = {int(m.group(2)): m.group(1)
              for m in re.finditer(r'source="dimguil/([^"]+)"[^>]*offs="(\d+)"', xml)}
    exe = open(os.path.join(clean, 'dimguil/SLPS_026.91'), 'rb').read()
    out = {}
    for t, (mb, cb, w) in enumerate(TABLES):
        for i in range(TABLE_LEN[t]):
            e = exe[mb - EXE_BASE + 3 * i:mb - EXE_BASE + 3 * i + 3]
            lba = unbcd(e[0]) * 4500 + unbcd(e[1]) * 75 + unbcd(e[2]) - 150
            count = int.from_bytes(exe[cb - EXE_BASE + w * i:cb - EXE_BASE + w * (i + 1)], 'little')
            out[(t, i)] = (by_lba.get(lba, f'LBA {lba}'), count)
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--files':
        for (t, i), (path, n) in file_map().items():
            if len(a) < 2 or a[1].lower() in path.lower():
                print(f'table {t} index {i:3d}  {path}  {n} sectors')
    else:
        d = open(a[0], 'rb').read()
        print(dec(d, int(a[1], 0), int(a[2], 0) if len(a) > 2 else None))
