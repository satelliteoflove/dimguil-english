#!/usr/bin/env python3
"""Wrap a description to the box width, and optionally write it into a translation file.

    descwrap.py "flat text" [--width 108]
        Print the wrapped text with its line widths, bytes and line count.
    descwrap.py "flat text" --apply FILE.json SECTION INDEX [--width 108]
        Also replace that string's translation in FILE.json. The edit is made on the
        raw file text, so // comments (M_CATALG has one) survive.

Greedy wrap by pixel width (descfit.line_widths). 108 px is the widest line in the
monster catalog, and 13 lines its longest entry; item descriptions differ, so check
the existing entries before using another file.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from descfit import line_widths, size
from reviewpage import load


def wrap(text, width=108):
    out, cur = [], ''
    for word in text.split(' '):
        cand = f'{cur} {word}' if cur else word
        if cur and line_widths(cand)[0] > width:
            out.append(cur)
            cur = word
        else:
            cur = cand
    out.append(cur)
    return '\n'.join(out)


def main():
    args = sys.argv[1:]
    width = int(args[args.index('--width') + 1]) if '--width' in args else 108
    text = wrap(args[0], width)
    if '--apply' in args:
        i = args.index('--apply')
        path, sec, idx = args[i + 1], int(args[i + 2]), int(args[i + 3])
        old = load(path)['sections'][sec]['strings'][idx]['translation']
        raw = open(path, encoding='utf-8').read()
        o, n = json.dumps(old, ensure_ascii=False), json.dumps(text, ensure_ascii=False)
        if raw.count(o) != 1:
            sys.exit(f'old text found {raw.count(o)} times in {path}; not changed')
        open(path, 'w', encoding='utf-8').write(raw.replace(o, n))
    print(text)
    lw = line_widths(text)
    print(f'{lw} widest {max(lw)}px, {size(text)} bytes, {len(lw)} lines')


if __name__ == '__main__':
    main()
