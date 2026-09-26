#!/usr/bin/env python3
"""Check battle messages (translations/FIGHTMSG.OBJ.json) against the battle text box.

    fightfit.py

The box holds 3 lines of 24 glyph codes (a digraph is one code), centred. The printer
moves an inserted name ({ff13} and friends) to a new line when it won't fit on the
current one, and with asm/word_wrap.asm it also looks ahead at each space and breaks
there if the next word won't fit. The layout depends on the lengths of the names, so
every combination is tried: monster 3-17 ("Skeleton Warriors"), character 1-8, item or
attack noun 3-18, spell 3-9, number 1-5, and each length the verbs actually have.
Reports messages that can run past 3 lines, or split a word (only possible for text
stuck to a name with no space, like "{ff13}'s"). String 297 (the Tree of Stillness
mural) is shown in the event box and is skipped.
"""
import itertools, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import descfit
from cardref import load_json

ROOT = os.path.join(os.path.dirname(__file__), '..')
CAP = 24
RANGES = {'ff13': range(3, 18), 'ff18': range(1, 9), 'ff12': range(1, 9),
          'ff16': range(3, 10), 'ff14': range(3, 19), 'ff11': range(1, 6)}
VERBS = range(1, 78)  # FIGHTMSG strings inserted as {ff15}
SKIP = {297}
# a plain space, and the digraphs that end in one (see asm/word_wrap.asm)
SPACES = set(range(0x8b, 0x93)) | {0xad, 0xae, 0xb2, 0xb7, 0xba}


def tokens(text):
    """[('var', name) | ('nl',) | ('code', c)]"""
    text = re.sub(r'\{ancient_\w\}', 'X', text)
    out = []
    for tok in re.findall(r'\{ff[0-9a-f]{2}\}\d?|\n|\r|[^{\n\r]+', text):
        m = re.match(r'\{(ff[0-9a-f]{2})\}', tok)
        if m:
            out.append(('var', m.group(1)))
        elif tok == '\n':
            out.append(('nl',))
        elif tok != '\r':
            out += [('code', c) for c in descfit.encode(tok)]
    return out


def simulate(toks, lens):
    """(lines, a word was split)"""
    lines, col, split = 1, 0, False
    for k, t in enumerate(toks):
        if t[0] == 'nl':
            lines, col = lines + 1, 0
        elif t[0] == 'var':
            n = lens.get(t[1], 0)
            if n and col + n > CAP and col:
                lines, col = lines + 1, 0
            col += n
        else:
            col += 1
            if t[1] in SPACES:
                w = col
                for u in toks[k + 1:]:
                    if u[0] != 'code':
                        break
                    if u[1] in SPACES:
                        w += u[1] != 0xba
                        break
                    w += 1
                if col >= CAP or w > CAP:
                    lines, col = lines + 1, 0
            elif col >= CAP:
                lines, col = lines + 1, 0
                nxt = toks[k + 1] if k + 1 < len(toks) else None
                split |= bool(nxt and nxt[0] == 'code' and nxt[1] not in SPACES)
    return lines, split


def main():
    strings = load_json(os.path.join(ROOT, 'translations/FIGHTMSG.OBJ.json'))['sections'][0]['strings']
    ranges = dict(RANGES, ff15=sorted({len(descfit.encode(strings[i].get('translation') or ''))
                                       for i in VERBS} - {0}))
    bad = 0
    for i, s in enumerate(strings):
        text = s.get('translation') or ''
        if i in SKIP or not re.search('[a-z]', text):
            continue
        toks = tokens(text)
        names = sorted({t[1] for t in toks if t[0] == 'var' and t[1] in ranges})
        for combo in itertools.product(*(ranges[n] for n in names)):
            lens = dict(zip(names, combo))
            lines, split = simulate(toks, lens)
            if split or lines > 3:
                bad += 1
                print(f'!! {i:3d} {lines} lines{", splits a word" if split else ""} '
                      f'with lengths {lens}: {text!r}')
                break
    print(f'{bad} battle messages can overflow or split a word')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
