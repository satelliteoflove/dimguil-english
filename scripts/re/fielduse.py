#!/usr/bin/env python3
"""Which functions use which fields of a typed global, from the decompiled C.

    fielduse.py GLOBAL [FIELD] [--mod MOD,...]

GLOBAL is a typed global's name (roster, item_table, parties ...). With no FIELD, prints
each field (and constant subscript, e.g. unk10[6]) with a count and the functions using
it; with FIELD, lists every line that touches it, function by function. Reads
rips/re/decomp/<MOD>/*.c; the card game modules are left out unless named.
"""
import collections, glob, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODS = ['MAIN', 'MAZE', 'BATTLE', 'MCARD', 'JOUKA', 'HAZURE']


def main():
    args = sys.argv[1:]
    mods = MODS
    if '--mod' in args:
        k = args.index('--mod'); mods = args[k + 1].upper().split(','); del args[k:k + 2]
    if not args:
        print(__doc__); return 1
    name, field = args[0], (args[1] if len(args) > 1 else None)
    pat = re.compile(re.escape(name) + r'\[[^\]]*\]\.([a-z_0-9]+)(\[(0x[0-9a-f]+|\d+)\])?')
    uses = collections.defaultdict(collections.Counter)
    for mod in mods:
        for path in sorted(glob.glob(os.path.join(ROOT, 'rips/re/decomp', mod, '*.c'))):
            fn = mod + ':' + os.path.basename(path)[:-2]
            for ln, line in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
                for m in pat.finditer(line):
                    key = m.group(1) + (f'[{m.group(3)}]' if m.group(3) else '')
                    if field is None:
                        uses[key][fn] += 1
                    elif m.group(1) == field or key == field:
                        print(f'{fn}:{ln}: {line.strip()[:160]}')
                        break
    if field is None:
        def order(k):
            base, _, sub = k.partition('[')
            return (base, int(sub[:-1], 0) if sub else -1)
        for key in sorted(uses, key=order):
            fns = uses[key]
            print(f'{key:16s} {sum(fns.values()):4d}  ' +
                  ' '.join(f'{f}({n})' for f, n in fns.most_common(6)) +
                  (f' +{len(fns) - 6} more' if len(fns) > 6 else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
