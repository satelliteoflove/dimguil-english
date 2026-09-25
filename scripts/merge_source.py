#!/usr/bin/env python3
"""Restore redacted JP `source` fields in Remisse-format translation JSON from a fresh dump.
merge_source.py DUMP.json TRANSLATION.json OUT.json [--no-compress]
Strings must line up 1:1 (same section/index); lengths are cross-checked.
Needed because the encoder falls back to `source` for untranslated strings."""
import json, re, sys


def load(path):
    """json.load that tolerates // and /* */ comments (the Kotlin side allows them)."""
    src = open(path, encoding='utf-8').read()
    tok = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)
    return json.loads(tok.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else '', src))


dump, tr, out = sys.argv[1:4]
nocomp = '--no-compress' in sys.argv
D = load(dump); T = load(tr)
assert len(D['sections']) == len(T['sections'])
for ds, ts in zip(D['sections'], T['sections']):
    assert len(ds['strings']) == len(ts['strings']), (len(ds['strings']), len(ts['strings']))
    if nocomp:
        ts['compress'] = False
    for i, (a, b) in enumerate(zip(ds['strings'], ts['strings'])):
        if a['length'] != b['length']:
            sys.exit(f'length mismatch at {i}: {a} vs {b}')
        b['source'] = a['source']
        if nocomp:
            b['compress'] = False
json.dump(T, open(out, 'w'), ensure_ascii=False, indent=1)
