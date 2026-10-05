#!/usr/bin/env python3
"""Check the spell descriptions against the spell bar's limit.

    spellfit.py [translations/STATUS.OBJ.json]

Inspect Character > Cast Spell shows the highlighted spell's description in a one-line
bar. The bar prints the first 30 glyph codes and drops the rest (checked in the
emulator: 30 codes print whole, the 31st never shows; the cut is by codes, not pixels).
Digraphs count as one code, so this counts codes the way the encoder does, not
characters. The descriptions are STATUS.OBJ strings 420-503.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from reviewpage import load
from descfit import encode

FIRST, LAST, LIMIT = 420, 503, 30


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), '..', 'translations', 'STATUS.OBJ.json')
    strings = load(path)['sections'][0]['strings']
    bad = 0
    for k in range(FIRST, LAST + 1):
        text = strings[k]['translation']
        n = len(encode(text)) if text else 0
        if n > LIMIT:
            bad += 1
            print(f'!! {k} {n} codes (max {LIMIT})  {text}')
    print(f'{bad} spell descriptions over {LIMIT} codes')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
