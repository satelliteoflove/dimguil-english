#!/usr/bin/env python3
"""The mechanical checks from docs/review-lessons.md, run over the NPC lines Chris hasn't
read yet (textstatus.py: anything not 'reviewed').

    python3 scripts/lessons.py            the hits, by lesson
    python3 scripts/lessons.py --all      every line, read or not
    python3 scripts/lessons.py --json     [{ref, lesson, match, text}] for the scene builders

A hit is a line to look at, not a verdict: the voice scenes and read-throughs decide.
"""
import json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import textstatus  # noqa: E402

# Speakers whose voice is formal or genteel, so "do feel free" is in character (L4).
FORMAL = {'Alba', 'Wolfish man', 'Alstron', 'Tall man', 'Rosea', 'Cat-eared woman', 'Fontana', 'Young samurai',
          'Cephala', 'Little elf', 'Cleo', 'Robed elf', 'Cresson', 'Robed man', 'Artemisia', 'Woman with a spear',
          'Mysterious figure', 'Mysterious man', 'Agan', "Man's voice"}

CHECKS = [
    ('L1', 'British idiom', r'\byou lot\b|\bfancy\b|\brubbish\b|\blad\b'),
    ('L2', 'connotation', r'\bcomrades?\b'),
    ('L3', 'coy address', r'\bgirlies\b|\blittle (boys|girls)\b|\bmissy\b'),
    ('L4', 'stiff filler', r'\bdo (feel free|be|come)\b'),
    ('L4a', 'stuffy', r'\bas regards\b'),
    ('L7', 'pointing, not naming', r'\bthis (sort|kind) of thing\b'),
    ('L10', 'caveman "Me"', r'(?:^|"|\n )Me, (?!I\b|I\')'),
    ('L14', 'line ends on a small word', r' (?:to|a|an|the|of)\n'),
    ('L15', 'spelling', r'\bfair(y|ies)\b'),
]


def strings(n):
    d = json.load(open(os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json'), encoding='utf-8'))
    return [s['translation'] for s in d['sections'][0]['strings']]


def speaker(text):
    head, _, rest = text.partition('\n')
    return head if rest.startswith('"') else None


def hits(every=False):
    status = textstatus.table()
    out = []
    for n in range(1, 6):
        for i, text in enumerate(strings(n)):
            if not every and status(f'NPC_MES{n}.OBJ', i)[0] == 'reviewed':
                continue
            who = speaker(text)
            speech = text.split('\n', 1)[1] if who else text
            for lesson, what, pat in CHECKS:
                flags = 0 if lesson == 'L10' else re.I   # "Me, Gaura", not "Me, I'm" or "me"
                if lesson == 'L4' and who in FORMAL:
                    continue
                m = re.search(pat, speech, flags)
                if m:
                    out.append({'ref': f'{n}:{i}', 'lesson': lesson, 'what': what, 'match': m.group(0).strip(),
                                'speaker': who, 'text': text})
    return out


def main():
    hs = hits('--all' in sys.argv)
    if '--json' in sys.argv:
        json.dump(hs, sys.stdout, ensure_ascii=False, indent=1)
        return
    by = {}
    for h in hs:
        by.setdefault((h['lesson'], h['what']), []).append(h)
    for (lesson, what), group in by.items():
        print(f'{lesson} {what}: {len(group)}')
        for h in group:
            print(f"  {h['ref']:7} {h['match']!r:22} {h['text'].replace(chr(10), ' / ')[:110]}")
    print(f'{len(hs)} hits')


if __name__ == '__main__':
    main()
