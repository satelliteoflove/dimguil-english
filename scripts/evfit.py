#!/usr/bin/env python3
"""Check the event script (translations/EVENTMES.BIN.json) against the dungeon text box.

    evfit.py [--overlay FILE.json] [--all]

Like npcfit.py, for EVENTMES: pages break at {ff26} (wait for a button) and \\r, each
page holds 3 lines (or as many as the Japanese page has), each line at most 288 px.
Also flags a mid-line " (see npcfit.py), control codes that differ from the Japanese
({ancient_x} counts as {ff35}X), and the file's encoded size against its original
25,721 bytes. --overlay applies {"idx": "text"} on top of the file first.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import descfit, npcfit

ROOT = os.path.join(os.path.dirname(__file__), '..')
WIDTH, LINES, LIMIT = 288, 3, 25721
CODE = re.compile(r'\{ff[0-9a-f]{2}\}')


def pages(text):
    return re.split(r'\{ff26\}|\r', text)


def codes(text):
    text = re.sub(r'\{ancient_(\w)\}', lambda m: '{ff35}', text)
    return sorted(c for c in CODE.findall(text) if c != '{ff35}'), text.count('{ff35}')


def main():
    args = sys.argv[1:]
    tr = npcfit.json.load(open(os.path.join(ROOT, 'translations/EVENTMES.BIN.json'), encoding='utf-8'))
    ts = tr['sections'][0]['strings']
    if '--overlay' in args:
        for k, v in json.load(open(args[args.index('--overlay') + 1], encoding='utf-8')).items():
            ts[int(k)]['translation'] = v
    ds = json.load(open(os.path.join(ROOT, 'rips/stage/out/dumps/EVENTMES.BIN.json'), encoding='utf-8'))['sections'][0]['strings']
    total, bad, todo = 4 * len(ts), 0, 0
    for i, (t, d) in enumerate(zip(ts, ds)):
        text, src = t['translation'], d['source']
        if not text:
            todo += 1
            total += d['length'] + 2
            if '--all' in args:
                print(f'   {i:3d} untranslated')
            continue
        problems = []
        orig, text = text, re.sub(r'\{ancient_\w\}', 'O', text)  # one glyph, one byte
        try:
            total += descfit.size(text.replace('\r', '{ff20}'))
            sp = pages(src)
            for k, pg in enumerate(pages(text)):
                limit = max(LINES, sp[k].count('\n') + 1) if k < len(sp) else LINES
                if pg.count('\n') + 1 > limit:
                    problems.append(f'page {k + 1} has {pg.count(chr(10)) + 1} lines')
                for w, line in zip(descfit.line_widths(npcfit.measurable(pg)), pg.split('\n')):
                    if w > WIDTH:
                        problems.append(f'{w}px: {line!r}')
            enc = descfit.encode(text.replace('\r', '{ff20}'))
            for a, b in zip(enc, enc[1:]):
                if b == descfit.CHARS['"'] and a in npcfit._KANA:
                    problems.append(f'" after code {a:#x} prints as {npcfit._KANA[a]}; use \' inside a line')
        except ValueError as e:
            problems.append(str(e))
        if [m.group(1) for m in re.finditer(r'\{ff26\}(\r?)', orig)] != \
                [m.group(1) for m in re.finditer(r'\{ff26\}(\r?)', src)]:
            problems.append('page breaks differ: each {ff26} needs the \\r the Japanese has after it')
        if codes(orig) != codes(src):
            problems.append(f'codes {codes(orig)} vs source {codes(src)}')
        bad += bool(problems)
        for p in problems:
            print(f'!! {i:3d} {p}')
    print(f'EVENTMES: {len(ts) - todo}/{len(ts)} translated, {bad} with problems, '
          f'~{total} of {LIMIT} bytes{" !! OVER" if total > LIMIT else ""}')
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
