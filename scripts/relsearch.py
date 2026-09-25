#!/usr/bin/env python3
"""Relative search: find sequences whose code deltas match those of a SJIS kana string.
relsearch.py file string  -- tries 8-bit, 16-bit LE/BE."""
import sys, struct
def codes(s):
    # unicode ordering works for kana; relative to unicode
    return [ord(c) for c in s]
def search(data, s, base=0):
    c = codes(s); d = [x - c[0] for x in c]
    out = []
    for width, fmt in ((1, 'B'), (2, '<H'), (2, '>H')):
        for align in range(width):
            n = (len(data) - align) // width
            vals = struct.unpack_from(f'{"<" if fmt[0]!=">" else ">"}{n}{fmt[-1]}', data, align)
            L = len(d)
            for i in range(n - L):
                v0 = vals[i]
                if all(vals[i + k] - v0 == d[k] for k in range(1, L)):
                    out.append((base + align + i * width, fmt, v0))
    return out
if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    base = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
    for off, fmt, v0 in search(data, sys.argv[2], base)[:50]:
        print(f'{off:08x} {fmt} first=0x{v0:x}')
