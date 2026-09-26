#!/usr/bin/env python3
"""Check battle messages (translations/FIGHTMSG.OBJ.json) against the battle text box.

    fightfit.py

The box holds 3 lines of 24 glyph codes (a digraph is one code), centred. The printer
moves an inserted name ({ff13} and friends) to a new line when it won't fit on the
current one, but plain text simply breaks at the 24th code, mid-word if need be. Names
are priced at their longest: monster 17 ("Skeleton Warriors"), character 8, item or
attack noun 18, spell 9, number 5. Reports lines that would break inside a word or run
past 3 lines. String 297 (the Tree of Stillness mural) is shown in the event box and is
skipped.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import descfit
from cardref import load_json

ROOT = os.path.join(os.path.dirname(__file__), '..')
CAP = 24
VARS = {'ff13': 17, 'ff18': 8, 'ff12': 8, 'ff16': 9, 'ff14': 18, 'ff11': 5,
        'ff15': len(descfit.encode('tries to choke out '))}
SKIP = {297}


def simulate(text):
    """(lines, words broken across a line)"""
    text = re.sub(r'\{ancient_\w\}', 'X', text)
    lines, col, broken = 1, 0, []
    for tok in re.findall(r'\{ff[0-9a-f]{2}\}\d?|\n|\r|[^{\n\r]+', text):
        if tok == '\n':
            lines, col = lines + 1, 0
            continue
        if tok == '\r':
            continue
        m = re.match(r'\{(ff[0-9a-f]{2})\}', tok)
        if m:
            n = VARS.get(m.group(1), 0)
            if n and col + n > CAP:
                lines, col = lines + 1, 0
            col += n
            continue
        for word in re.findall(r'[^ ]* ?', tok):
            n = len(descfit.encode(word)) if word else 0
            if col + n > CAP and col:
                if col + n - word.endswith(' ') > CAP:
                    broken.append(word.strip())
                lines, col = lines + 1, max(0, col + n - CAP)
            else:
                col += n
    return lines, broken


def main():
    t = load_json(os.path.join(ROOT, 'translations/FIGHTMSG.OBJ.json'))
    bad = 0
    for i, s in enumerate(t['sections'][0]['strings']):
        text = s.get('translation') or ''
        if i in SKIP or not re.search('[a-z]', text):
            continue
        lines, broken = simulate(text)
        if broken or lines > 3:
            bad += 1
            print(f'!! {i:3d} {lines} lines, breaks {broken}: {text!r}')
    print(f'{bad} battle messages need a line break')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
