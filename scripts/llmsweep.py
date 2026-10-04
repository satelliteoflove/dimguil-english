#!/usr/bin/env python3
"""Sweep the English in translations/*.json for habits that read as LLM prose.

Prints hits grouped by pattern, with file:section:index and the line. This is a
screening aid only: every hit needs a human look, and most will be fine.

  python3 scripts/llmsweep.py            # all patterns
  python3 scripts/llmsweep.py --ngrams   # also repeated 4-word phrases
"""
import glob
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from jpinventory import load  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')

# Words and phrases that LLMs lean on far more than people do.
STOCK = r'''testament tapestry delve delves delving realm realms embark embarks
resonate resonates intricate myriad beacon unwavering palpable ethereal unravel
unravels navigate landscape symphony cacophony amidst amongst whilst nestled
bustling vibrant serene profound solemn otherworldly enigmatic eerie eerily
looming lingering linger lingers shimmer shimmers shimmering flicker flickers
flickering whisper whispers whispered whispering echo echoes echoing
reverberate reverberates steel steeled visceral tangible ominous ominously
foreboding inexorable relentless relentlessly indomitable boundless timeless
essence fabric undeniable undeniably meticulous meticulously seamless pivotal
crucial paramount endeavor endeavour weave weaves woven unspoken'''.split()

PHRASES = [
    r'a sense of', r'an air of', r'the weight of', r'hangs? in the air',
    r"can'?t help but", r"couldn'?t help but", r'sends? a shiver', r'a chill',
    r'little did', r'in the depths of', r'bated breath', r'heart (?:pounds|races)',
    r'not just\b', r'not merely', r'more than just', r'not only\b',
    r'it seems', r'seems? to be', r'as if\b', r'as though', r'somehow',
    r'every fiber', r'deep within', r'from within', r'beckon', r'await(?:s)? you',
    r'stands? as', r'serves? as', r'a reminder', r'a mix of', r'a blend of',
    r'at the heart of', r'the very\b', r'once and for all', r'truly',
    r'indeed', r'perhaps', r'utterly', r'deeply', r'incredibly', r'absolutely',
]

BRITISH = r'''fancy rubbish lad lads mate bloody reckon whilst amongst towards
colour colours honour honours favour favours armour armoured behaviour
neighbour labour rumour rumours valour vigour splendour clamour harbour
centre metre theatre grey cheers cheerio blimey brilliant proper quite
learnt spelt dreamt burnt spoilt leapt knelt fortnight queue arse'''.split()

DASH = r'—|–|(?<=\w) - (?=\w)|--'
TRIAD = r"\b[\w'-]+(?: [\w'-]+){0,2}, [\w'-]+(?: [\w'-]+){0,2},? and [\w'-]+"
NOTXBUTY = r"\bnot (?:a |an |the )?\w+(?: \w+)?, but\b|\bisn'?t \w+[.;] it'?s\b"


def clean(t):
    t = re.sub(r'\{[^}]*\}', ' ', t)
    t = t.replace('\r', ' ').replace('\n', ' ')
    return re.sub(r'\s+', ' ', t).strip()


def strings():
    for f in sorted(glob.glob(os.path.join(ROOT, 'translations', '*.json'))):
        name = os.path.basename(f).split('.')[0]
        d = load(f)
        for si, sec in enumerate(d['sections']):
            for i, st in enumerate(sec['strings']):
                t = st.get('translation') or ''
                if re.search('[A-Za-z]{3}', t):
                    yield f'{name}:{si}:{i}', clean(t)


def main():
    hits = defaultdict(list)
    words = lambda ws: re.compile(r'\b(?:' + '|'.join(ws) + r')\b', re.I)
    pats = {
        'stock words': words(STOCK),
        'stock phrases': re.compile('|'.join(PHRASES), re.I),
        'British': words(BRITISH),
        'dashes': re.compile(DASH),
        'triads': re.compile(TRIAD),
        'not X, but Y': re.compile(NOTXBUTY, re.I),
        'semicolons': re.compile(r';'),
    }
    all_strings = list(strings())
    for ref, t in all_strings:
        for k, p in pats.items():
            ms = [m.group(0) for m in p.finditer(t)]
            if ms:
                hits[k].append((ref, ms, t))
    for k in pats:
        print(f'\n## {k} ({len(hits[k])})')
        for ref, ms, t in hits[k]:
            print(f'{ref}  [{", ".join(ms)}]  {t}')

    if '--ngrams' in sys.argv:
        grams = defaultdict(set)
        for ref, t in all_strings:
            if not re.match(r'(EVENTMES|NPC_MES|M_CATALG|ITEM)', ref):
                continue
            w = re.findall(r"[a-z']+", t.lower())
            for j in range(len(w) - 3):
                grams[' '.join(w[j:j + 4])].add(ref)
        print('\n## repeated 4-word phrases (6+ strings)')
        for g, refs in sorted(grams.items(), key=lambda x: -len(x[1])):
            if len(refs) >= 6:
                print(f'{len(refs):4}  {g}')


if __name__ == '__main__':
    main()
