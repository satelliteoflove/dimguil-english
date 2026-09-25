#!/usr/bin/env python3
"""Apply translations to translations/<FILE>.json from a mapping file.

tl_apply.py FILE MAPPING.json [--force]

MAPPING.json: {"<string index>": "English text", ...} (section 0), or
              {"<section>:<index>": "..."} for other sections, where <section> is the
              position in the translation file's own "sections" list.
Existing non-empty translations are only replaced with --force.

Values are replaced in place in the raw text, so // comments and formatting in the
translation file survive.
"""
import json, re, sys

name, mapping = sys.argv[1], sys.argv[2]
force = '--force' in sys.argv
path = f'translations/{name}.json'
raw = open(path, encoding='utf-8').read()

STR = r'"(?:\\.|[^"\\])*"'
# Every "translation" value, in file order; comments and strings are skipped as tokens.
tokens = re.compile(STR + r'|//[^\n]*|/\*.*?\*/', re.S)
d = json.loads(tokens.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else '', raw))
spans = []
it = tokens.finditer(raw)
for m in it:
    if m.group(0) == '"translation"':
        v = re.compile(r'\s*:\s*(' + STR + ')', re.S).match(raw, m.end())
        spans.append(v.span(1))
flat = [(si, i) for si, sec in enumerate(d['sections']) for i in range(len(sec['strings']))]
assert len(flat) == len(spans), (len(flat), len(spans))
where = dict(zip(flat, spans))

m = json.load(open(mapping, encoding='utf-8'))
edits, changed, skipped = [], 0, 0
for key, text in m.items():
    sec, idx = (key.split(':') if ':' in key else ('0', key))
    cur = d['sections'][int(sec)]['strings'][int(idx)]['translation']
    if cur and cur != text and not force:
        print(f'skip {key}: already "{cur[:40]}"'); skipped += 1; continue
    edits.append((where[(int(sec), int(idx))], json.dumps(text, ensure_ascii=False)))
    changed += 1
for (a, b), val in sorted(edits, reverse=True):
    raw = raw[:a] + val + raw[b:]
open(path, 'w', encoding='utf-8').write(raw)
print(f'{name}: {changed} set, {skipped} skipped')
