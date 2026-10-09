#!/usr/bin/env python3
"""Write binary patches that fix misspellings in the developer's English names.

    namefixes.py          write binary/<file>.json for the files that need a fix
    namefixes.py --list   print each slot that would change

The names are the game's built-in English (docs/translation-notes.md, "Series spellings
checked"); only plain typos are fixed, never the series' own spellings (NUNCHAKA,
Maelific, Halycon). The monster records in DATA02/M_DTnnn.BIN and MPTnn.BIN are the
0xd0-byte records described in nptnames.py, with six 18-byte name slots ending in
{ff40}, so a name can't pass 16 glyphs. ITEM.DAT's English item list isn't in a
translation file, so its one fix is a byte edit too. The same names live in M_CATALG,
I_NAME_E and MESSAGE.DAT (translations/*.json) and in BATTLE.BIN (asm/name_fixes.asm).
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gametext import dec
from nptnames import ROOT, CLEAN, REC, SLOT, GLYPH, records

# Whole slot text -> fixed text ({ff21} is the line break the party pictures use).
SLOTS = {
    'Dragonare': 'Dragonaire',
    'Dragonares': 'Dragonaires',
    'Old{ff21}Drumer': 'Old{ff21}Drummer',
    # "Small Silhouettes" is 17 glyphs; Small Shadow is the literal ちいさなかげ and fits.
    'Small Silhoutte': 'Small Shadow',
    'Small Silhouttes': 'Small Shadows',
    'Small{ff21}Silhoutte': 'Small{ff21}Shadow',
}
ITEM_DAT = ('DATA07/ITEM.DAT', 'DISPLASER', 'DISPLACER')


def encode(name):
    b = bytearray()
    for part in name.split('{ff21}'):
        if b:
            b += b'\xff\x21'
        b += bytes(GLYPH[c] for c in part)
    b += b'\xff\x40'
    assert len(b) <= SLOT, name
    return bytes(b).ljust(SLOT, b'\0')


def write(f, edits):
    path = os.path.join(ROOT, 'binary', os.path.basename(f) + '.json')
    json.dump({'file': f, 'edits': edits}, open(path, 'w'), indent=4)
    open(path, 'a').write('\n')


def main():
    listing = '--list' in sys.argv
    for p in sorted(glob.glob(os.path.join(CLEAN, 'M_DT*.BIN')) + glob.glob(os.path.join(CLEAN, 'MPT*.BIN'))):
        d = open(p, 'rb').read()
        edits = {}
        for o in records(d):
            for k in range(6):
                s = o + k * SLOT
                new = SLOTS.get(dec(d, s))
                if new:
                    edits[f'{s:x}'] = encode(new).hex(' ')
                    if listing:
                        print(f'{os.path.basename(p)} {s:#07x} {dec(d, s)} -> {new}')
        if edits and not listing:
            write('DATA02/' + os.path.basename(p), edits)

    f, old, new = ITEM_DAT
    d = open(os.path.join(ROOT, 'rips/clean/dimguil', f), 'rb').read()
    pat = bytes(GLYPH[c] for c in old)
    assert d.count(pat) == 1, f
    o = d.find(pat)
    if listing:
        print(f'{f} {o:#07x} {old} -> {new}')
    else:
        write(f, {f'{o:x}': bytes(GLYPH[c] for c in new).hex(' ')})


if __name__ == '__main__':
    main()
