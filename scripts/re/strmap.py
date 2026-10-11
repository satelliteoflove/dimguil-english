#!/usr/bin/env python3
"""List the town text each decompiled function prints.

    strmap.py [MOD]        (default JOUKA)

Reads rips/re/decomp/MOD/*.c and finds calls to the town print helpers (town_print,
town_bar_print, town_text_expand, and text_expand with sisetu_text), then shows each
constant string index with its Japanese text: S = SISETU.OBJ (text file 4), T =
STATUS.OBJ (file 0). Indexes the C computes are shown as [file, expression]. Needs the
build's dumps in rips/stage/out/dumps.
"""
import glob, json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
CALLS = {  # helper: (index of the file argument, index of the string argument)
    'town_print': (2, 3), 'FUN_800dbd7c': (2, 3),
    'town_bar_print': (1, 2), 'FUN_800dba48': (1, 2),
    'town_text_expand': (0, 1), 'FUN_800dbac8': (0, 1),
}


def strings(name):
    d = json.load(open(os.path.join(ROOT, 'rips/stage/out/dumps', name), encoding='utf-8'))
    return [s['source'] for s in d['sections'][0]['strings']]


def args(text):
    return [a.strip() for a in re.split(r',(?![^()]*\))', text)]


def main():
    mod = sys.argv[1] if len(sys.argv) > 1 else 'JOUKA'
    files = {'4': ('S', strings('SISETU.OBJ.json')), '0': ('T', strings('STATUS.OBJ.json'))}
    for path in sorted(glob.glob(os.path.join(ROOT, 'rips/re/decomp', mod, '*.c'))):
        src = open(path).read()
        hits = []
        for fn, (fi, si) in CALLS.items():
            for m in re.finditer(fn + r'\(([^;]*?)\);', src, re.S):
                a = args(m.group(1))
                if len(a) > max(fi, si):
                    hits.append((a[fi], a[si]))
        for m in re.finditer(r'text_expand\(([^;]*?)\)', src, re.S):
            a = args(m.group(1))
            if len(a) >= 2 and 'sisetu' in a[1]:
                hits.append(('4', a[0]))
        if not hits:
            continue
        print(os.path.basename(path)[:-2])
        for fi, ix in dict.fromkeys(hits):
            try:
                n = int(ix, 0)
            except ValueError:
                n = None
            if fi in files and n is not None and n < len(files[fi][1]):
                tag, table = files[fi]
                print(f'    {tag}{n}: {table[n][:40]!r}')
            else:
                print(f'    [{fi}, {ix}]')


if __name__ == '__main__':
    main()
