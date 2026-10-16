#!/usr/bin/env python3
"""Check battle messages (translations/FIGHTMSG.OBJ.json) against the battle text box.

    fightfit.py [--digraphs]

The box holds 3 lines of 24 glyph codes (a digraph is one code), centred. The printer
moves an inserted name ({ff13} and friends) to a new line when it won't fit on the
current one, and with asm/word_wrap.asm it also looks ahead at each space and breaks
there if the next word won't fit. The layout depends on the lengths of the names, so
every combination is tried: monster 3-17 ("Skeleton Warriors"), character 1-8, item or
attack noun 3-18, spell 3-9, number 1-5, and each length the verbs actually have (the
verbs only monster abilities use, in TARGETLESS, are tried in 214 alone).
Every automatic break replaces a plain space just before it, and a plain space that comes
straight after a break in plain text is dropped (word_wrap.asm), so neither end of a line
gets one. Reports messages that can run past 3 lines, split a word (only possible for text
stuck to a name with no space, like "{ff13}'s"), or start or end a line with a plain
space (an explicit line break in a template can still end one). A digraph ending in a
space ("s ", "A ") at an automatic break is drawn as its letter alone (word_wrap.asm),
so that isn't an issue either; one before an explicit line break, or at the end of a
message, is. --digraphs lists the messages where an automatic break can land after such
a digraph (the lines word_wrap.asm's digraph rule fixes). A string without "compress":
true in the JSON is encoded letter by letter, as the encoder leaves it. String 297 (the
Tree of Stillness mural) is shown in the event box and is skipped.
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
# Verbs only monster abilities use, so they only ever appear in 214 "{ff13} {ff15} {ff14}."
# (scripts/re/attackverbs.py lists who uses which verb in which template).
TARGETLESS = {46, 65, 66, 67, 68, 69, 70, 71, 74, 76}
SKIP = {297}
# a plain space, and the digraphs that end in one (see asm/word_wrap.asm)
SPACES = set(range(0x8b, 0x93)) | {0xad, 0xae, 0xb2, 0xb7, 0xba}
DIGRAPHS = SPACES - {0xba}


def tokens(text, compress=True):
    """[('var', name) | ('nl',) | ('code', c)]; compress=False for a string the encoder
    leaves without digraphs (no "compress": true in the JSON)."""
    text = re.sub(r'\{ancient_\w\}', 'X', text)
    out = []
    for tok in re.findall(r'\{ff[0-9a-f]{2}\}\d?|\n|\r|[^{\n\r]+', text):
        m = re.match(r'\{(ff[0-9a-f]{2})\}', tok)
        if m:
            out.append(('var', m.group(1)))
        elif tok == '\n':
            out.append(('nl',))
        elif tok != '\r':
            codes = descfit.encode(tok) if compress else [descfit.CHARS[ch] for ch in tok]
            out += [('code', c) for c in codes]
    return out


def simulate(toks, lens):
    """(lines, a word was split, a line starts with a space, a line ends with one,
    an automatic break lands after a digraph ending in a space)"""
    lines, col, split, lead, trail, dig = 1, 0, False, False, False, False
    skip = None
    last = None  # the last code on the current line ('var' for a name)
    for k, t in enumerate(toks):
        if k == skip:
            continue
        if t[0] == 'nl':
            trail |= last in SPACES
            lines, col, last = lines + 1, 0, None
        elif t[0] == 'var':
            n = lens.get(t[1], 0)
            if n and col + n > CAP and col:
                dig |= last in DIGRAPHS  # drawn as its letter
                lines, col = lines + 1, 0  # a plain space before it is replaced
            col += n
            last = 'var' if n else last
        else:
            if col == 0 and lines > 1 and t[1] == 0xba:
                lead = True
            col += 1
            last = t[1]
            brk = False
            if t[1] in SPACES:
                w = col
                for u in toks[k + 1:]:
                    if u[0] != 'code':
                        break
                    if u[1] in SPACES:
                        w += u[1] != 0xba
                        break
                    w += 1
                brk = col >= CAP or w > CAP
            elif col >= CAP:
                brk = True
                nxt = toks[k + 1] if k + 1 < len(toks) else None
                split |= bool(nxt and nxt[0] == 'code' and nxt[1] not in SPACES)
            if brk:  # after a plain space, the break replaces it
                dig |= t[1] in DIGRAPHS  # drawn as its letter
                lines, col, last = lines + 1, 0, None
                nxt = toks[k + 1] if k + 1 < len(toks) else None
                if nxt == ('code', 0xba):
                    skip = k + 1
    trail |= last in SPACES  # the end of the message
    return lines, split, lead, trail, dig


def main():
    strings = load_json(os.path.join(ROOT, 'translations/FIGHTMSG.OBJ.json'))['sections'][0]['strings']
    def verb_lens(verbs):
        return sorted({len(descfit.encode(strings[i].get('translation') or '')) for i in verbs} - {0})
    targeted = dict(RANGES, ff15=verb_lens(set(VERBS) - TARGETLESS))
    every = dict(RANGES, ff15=verb_lens(VERBS))
    digraphs = '--digraphs' in sys.argv[1:]
    bad = ndig = 0
    for i, s in enumerate(strings):
        text = s.get('translation') or ''
        if i in SKIP or not re.search('[a-z]', text):
            continue
        toks = tokens(text, s.get('compress') is True)
        ranges = every if i == 214 else targeted
        names = sorted({t[1] for t in toks if t[0] == 'var' and t[1] in ranges})
        hit = None
        for combo in itertools.product(*(ranges[n] for n in names)):
            lens = dict(zip(names, combo))
            lines, split, lead, trail, dig = simulate(toks, lens)
            if dig and hit is None:
                hit = lens
            if split or lead or trail or lines > 3:
                bad += 1
                print(f'!! {i:3d} {lines} lines{", splits a word" if split else ""}'
                      f'{", starts a line with a space" if lead else ""}'
                      f'{", ends a line with a space" if trail else ""} '
                      f'with lengths {lens}: {text!r}')
                break
        if hit is not None:
            ndig += 1
            if digraphs:
                print(f'.. {i:3d} a break after a digraph ending in a space with lengths {hit}: {text!r}')
    if digraphs:
        print(f'{ndig} battle messages can break after a digraph ending in a space '
              '(drawn as its letter, word_wrap.asm)')
    print(f'{bad} battle messages can overflow, split a word or start or end a line with a space')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
