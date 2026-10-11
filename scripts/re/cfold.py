#!/usr/bin/env python3
"""Fold the decompiler's most repetitive idioms in a decompiled C file, for reading.

    cfold.py FILE.c [> folded.c]

The talk code inlines the same few things hundreds of times. This prints the file with
them folded into one line each:
  - loading a portrait into one of the two slots (the body of MCARD 0x800c5a54):
      PORTRAIT(n);
  - a loop over the six members of your party (party copy 0x8007e810, members at
    0x8007e812) that ORs or ANDs a roster field:
      FOR_PARTY roster[m].met_bits[1] |= 8;
  - byte loop counters, `iVar * 0x1000000 >> 0x18 < n`, as `(char)iVar < n`
Nothing else changes, so line meanings stay the same; line numbers do not.
"""
import re, sys

PORTRAIT = re.compile(
    r'( *)if \(\(DAT_8007957c != (?P<a>[^)]+)\) && \(DAT_8007957d != (?P=a)\)\) \{\n'
    r' *load_file\(&npc_text,[^\n]*\n'
    r' *\}\n'
    r' *if \(DAT_8007957c == (?:0xff|-1)\) \{\n'
    r'(?: *tim_upload[^\n]*\n){2}'
    r' *DAT_8007957c = (?P=a);\n'
    r' *\}\n'
    r' *else if \(DAT_8007957d == (?:0xff|-1)\) \{\n'
    r'(?: *tim_upload[^\n]*\n){2}'
    r' *DAT_8007957d = (?P=a);\n'
    r' *\}\n')

PARTY = re.compile(
    r'( *)(?P<i>iVar\d+) = 0;\n'
    r' *(?P<j>iVar\d+) = 0;\n'
    r' *do \{\n'
    r' *(?P=j) = \(int\)\(char\)\(&DAT_8007e812\)\[(?P=j) >> 0x18\];\n'
    r' *if \((?P=j) != -1\) \{\n'
    r' *roster\[(?P=j)\]\.(?P<f>[\w\[\]0-9x]+) = roster\[(?P=j)\]\.(?P=f) (?P<op>[|&]) (?P<v>[^;]+);\n'
    r' *\}\n'
    r' *(?P=i) = (?P=i) \+ 1;\n'
    r' *(?P=j) = (?P=i) \* 0x1000000;\n'
    r' *\} while \((?P=i) \* 0x1000000 >> 0x18 < 6\);\n')


def fold(src):
    src = PORTRAIT.sub(lambda m: f'{m.group(1)}PORTRAIT({m.group("a")});\n', src)
    src = PARTY.sub(lambda m: f'{m.group(1)}FOR_PARTY roster[m].{m.group("f")} '
                              f'{m.group("op")}= {m.group("v")};\n', src)
    src = re.sub(r'(\w+) \* 0x1000000 >> 0x18', r'(char)\1', src)
    return src


if __name__ == '__main__':
    sys.stdout.write(fold(open(sys.argv[1], encoding='utf-8').read()))
