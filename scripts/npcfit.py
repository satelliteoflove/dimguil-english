#!/usr/bin/env python3
"""Check translated NPC dialogue (NPC_MES1-5.OBJ) against the dungeon text box.

    npcfit.py [N ...] [--all] [--overlay FILE.json]

N picks files (default 1-5). Reads translations/NPC_MESn.OBJ.json and the JP dump in
rips/stage/out/dumps (run scripts/build.sh once so it exists). Reports, per string:
  - a line wider than WIDTH px ({ff12} priced as an 8-letter name, {ff11}0 as 5 digits)
  - a page with more lines than the box holds (3; menu pages keep the source's count)
  - control codes that differ from the source
and per file the encoded size against the 32-sector load buffer (see relocate.py).
--all also lists untranslated strings. --overlay applies {"n:idx": "text", ...} on top of
the translation files first, to check proposed edits without writing them.

Box measured in the emulator: text starts at x=27, the frame is at x=321 (350-px mode).
Pages are split by "\\n\\r"; lines after the first on a page start with one space,
as in the Japanese.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import descfit

ROOT = os.path.join(os.path.dirname(__file__), '..')
WIDTH = 288
LINES = 3
LIMIT = 32 * 2048
CODE = re.compile(r'\{ff[0-9a-f]{2}\}')


def measurable(text):
    text = text.replace('{ff12}', 'Mmmmmmmm').replace('{ff11}0', '99999')
    text = re.sub(r'\{ff30\}\w', '', text)
    return CODE.sub('', text).replace('\r', '')


def pages(text):
    return [p for p in re.split(r'\n\r|\{ff40\}\r', text)]


def check(n, show_all, overlay=None):
    tr = json.load(open(os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json'), encoding='utf-8'))
    for key, text in (overlay or {}).items():
        if int(key.split(':')[0]) == n:
            tr['sections'][0]['strings'][int(key.split(':')[1])]['translation'] = text
    dump = json.load(open(os.path.join(ROOT, f'rips/stage/out/dumps/NPC_MES{n}.OBJ.json'), encoding='utf-8'))
    ts, ds = tr['sections'][0]['strings'], dump['sections'][0]['strings']
    total, bad, todo = 4 * len(ts), 0, 0
    for i, (t, d) in enumerate(zip(ts, ds)):
        text, src = t['translation'], d['source']
        if not text:
            todo += 1
            total += d['length'] + 2
            if show_all:
                print(f'   {n}:{i:3d} untranslated')
            continue
        problems = []
        try:
            total += descfit.size(text.replace('\r', '{ff20}'))
            srcpages = pages(src)
            for k, pg in enumerate(pages(text)):
                limit = max(LINES, srcpages[k].count('\n') + 1) if k < len(srcpages) else LINES
                if pg.count('\n') + 1 > limit:
                    problems.append(f'page {k + 1} has {pg.count(chr(10)) + 1} lines')
                for w, line in zip(descfit.line_widths(measurable(pg)), pg.split('\n')):
                    if w > WIDTH:
                        problems.append(f'{w}px: {line!r}')
            if len(pages(text)) != len(srcpages):
                problems.append(f'{len(pages(text))} pages, source has {len(srcpages)} (fine if intended)')
        except ValueError as e:
            problems.append(str(e))
        if sorted(CODE.findall(text)) != sorted(CODE.findall(src)):
            problems.append(f'codes {CODE.findall(text)} vs source {CODE.findall(src)}')
        hard = [p for p in problems if 'fine if intended' not in p]
        bad += bool(hard)
        for p in problems:
            print(f'{"!!" if p in hard else "  "} {n}:{i:3d} {p}')
    print(f'NPC_MES{n}: {len(ts) - todo}/{len(ts)} translated, {bad} with problems, '
          f'~{total} of {LIMIT} bytes{" !! OVER" if total > LIMIT else ""}')
    return bad


if __name__ == '__main__':
    args = sys.argv[1:]
    overlay = None
    if '--overlay' in args:
        k = args.index('--overlay')
        overlay = json.load(open(args[k + 1], encoding='utf-8'))
        del args[k:k + 2]
    files = [int(a) for a in args if a.isdigit()] or range(1, 6)
    sys.exit(1 if sum(check(n, '--all' in args, overlay) for n in files) else 0)
