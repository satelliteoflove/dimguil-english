#!/usr/bin/env python3
"""Measure English text the way the game will see it: encoded bytes and pixel widths.

Mirrors the patcher's encoder (tables/dimguil_enc.tbl plus DigraphCompression: greedy
pairs inside each space-delimited word, the trailing space included) and prices each
glyph at VWF_LUT[code] + 1 px, read from the built executable (12 px past the table,
which is what both the main text engine and catalog_vwf.asm do).

    descfit.py FILE.json [--width 144] [--lines 7] [--budgets BUDGETS.json]
        FILE.json: {"<index>": "text with \\n line breaks", ...}; keys may be
        "<section>:<index>".
        Prints per-entry bytes, widest line and line count; flags anything over.
        BUDGETS.json: {"budgets": {"<section>": bytes}}; checks each section's total
        (terminators excluded, as the encoder counts it).

As a module: encode(text) -> list of codes, size(text) -> bytes incl. terminator,
line_widths(text) -> [px, ...].
"""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
EXE = os.path.join(ROOT, 'rips/dirty/dimguil/SLPS_026.91')
VWF_LUT = 0x80060e97 - 0x8000f800


def _table(path):
    out = {}
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if '=' not in line:
            continue
        code, ch = line.split('=', 1)
        out.setdefault(ch, int(code, 16))
    return out


CHARS = _table(os.path.join(ROOT, 'tables/dimguil_enc.tbl'))
DIGRAPHS = {}
for line in open(os.path.join(ROOT, 'tables/compression.tbl'), encoding='utf-8'):
    line = line.rstrip('\n')
    if len(line) >= 4 and line[2] == '=':
        DIGRAPHS[line[:2]] = int(line[3:], 16)
LUT = open(EXE, 'rb').read()[VWF_LUT:VWF_LUT + 0xd1]
NEWLINE = -1
CONTROL = -2


def encode(text):
    """Codes for text; NEWLINE marks a line break (2 bytes in the file), CONTROL one byte
    of a {xxxx} control code."""
    codes = []
    for word in re.findall(r'[^ ]* ?|[^ ]+', text):
        i = 0
        while i < len(word):
            m = re.match(r'\{([0-9a-f]{4})\}', word[i:])
            if m:  # control code, two bytes
                codes += [CONTROL, CONTROL]; i += m.end(); continue
            if word[i] == '\n':
                codes.append(NEWLINE); i += 1; continue
            pair = word[i:i + 2]
            if len(pair) == 2 and pair in DIGRAPHS:
                codes.append(DIGRAPHS[pair]); i += 2; continue
            if word[i] not in CHARS:
                raise ValueError(f'no glyph for {word[i]!r} in {text!r}')
            codes.append(CHARS[word[i]]); i += 1
    return codes


def size(text):
    codes = encode(text)
    return len(codes) + codes.count(NEWLINE) + 2  # newline {ff21} and terminator {ff40}


def line_widths(text):
    if '{ff40}' in text:  # string terminator: what follows is a separate string
        return [w for part in text.split('{ff40}') for w in line_widths(part)]
    widths, w = [], 0
    for c in encode(text):
        if c == NEWLINE:
            widths.append(w); w = 0
        elif c == CONTROL:
            pass
        else:
            w += LUT[c] + 1 if c < len(LUT) else 12
    return widths + [w]


def main():
    args = sys.argv[1:]
    width = int(args[args.index('--width') + 1]) if '--width' in args else 144
    lines = int(args[args.index('--lines') + 1]) if '--lines' in args else 7
    m = json.load(open(args[0], encoding='utf-8'))
    total = 0
    for key, text in m.items():
        lw = line_widths(text)
        b = size(text)
        total += b
        bad = max(lw) > width or len(lw) > lines
        print(f'{"!!" if bad else "  "} {key:>4} {b:4d}B {max(lw):3d}px {len(lw)} lines')
    print(f'total {total} bytes for {len(m)} strings')
    if '--budgets' in args:
        budgets = json.load(open(args[args.index('--budgets') + 1]))['budgets']
        for sec, limit in budgets.items():
            used = sum(size(t) - 2 for k, t in m.items() if k.split(':')[0] == sec)
            print(f'{"!!" if used > limit else "  "} section {sec}: {used} of {limit} bytes')


if __name__ == '__main__':
    main()
