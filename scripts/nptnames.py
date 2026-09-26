#!/usr/bin/env python3
"""Write binary patches that give the dungeon NPC parties English names.

    nptnames.py          write binary/NPTnn.BIN.json for DATA02/NPT00-15.BIN
    nptnames.py --list   print each file's records and names

Each NPTnn.BIN is one NPC party encounter. Its members are 0xd0-byte records at the end
of the file, laid out like the monster records in M_DTnnn.BIN: six 18-byte name slots
(Japanese, Japanese unidentified, English, English unidentified, English plural, English
unidentified plural), glyph codes ending in {ff40}. The disc has these names in katakana
in every slot, English ones included. We write the English name into all six, as
Remisse's original NPT00 patch did, using single-letter glyph codes (no digraphs, like
the monster names). NPT15's four Arch class records already have English and are left
alone.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gametext import dec

ROOT = os.path.join(os.path.dirname(__file__), '..')
CLEAN = os.path.join(ROOT, 'rips/clean/dimguil/DATA02')
REC, SLOT = 0xd0, 0x12

# Spellings follow docs/npc-translation.md. The NPT files call him アルストン, but all 59
# mentions in the dialogue say アルストロン, so the name matches the dialogue.
NAMES = {
    'ガイ': 'Guy', 'リナリア': 'Linaria', 'アルストン': 'Alstron', 'ライチ': 'Lychee',
    'フリチラリア': 'Fritillaria', 'リリア': 'Lilia', 'バルボ': 'Balbo',
    'レイラン': 'Reiran', 'アルバ': 'Alba', 'ロゼア': 'Rosea', 'ガウラ': 'Gaura',
    'アルテミシア': 'Artemisia', 'フォンタナ': 'Fontana', 'ザリル': 'Zaril',
    'セファラ': 'Cephala', 'クレオ': 'Cleo', 'ベルガモット': 'Bergamot',
}

GLYPH = {}
for line in open(os.path.join(ROOT, 'tables/dimguil_enc.tbl'), encoding='utf-8'):
    k, sep, v = line.rstrip('\n').partition('=')
    if sep and len(v) == 1 and len(k) <= 2 and v not in GLYPH:
        GLYPH[v] = int(k, 16)


def encode(name):
    b = bytes(GLYPH[c] for c in name) + b'\xff\x40'
    assert len(b) <= SLOT, name
    return b.ljust(SLOT, b'\0')


def records(d):
    """Offsets of the member records, found by walking back from the end."""
    out, o = [], len(d) - REC
    while o >= 0 and d[o:o + SLOT].find(b'\xff\x40') > 0 and '<' not in dec(d, o):
        out.insert(0, o)
        o -= REC
    return out


def main():
    for n in range(16):
        f = f'NPT{n:02d}.BIN'
        d = open(os.path.join(CLEAN, f), 'rb').read()
        edits = {}
        for o in records(d):
            jp = dec(d, o)
            en = NAMES.get(jp)
            if '--list' in sys.argv:
                print(f'{f} {o:#07x} {jp} -> {en or dec(d, o + 2 * SLOT)}')
            if en:
                for k in range(6):
                    edits[f'{o + k * SLOT:x}'] = encode(en).hex(' ')
        if edits and '--list' not in sys.argv:
            path = os.path.join(ROOT, 'binary', f'{f}.json')
            json.dump({'file': f'DATA02/{f}', 'edits': edits}, open(path, 'w'), indent=4)
            open(path, 'a').write('\n')


if __name__ == '__main__':
    main()
