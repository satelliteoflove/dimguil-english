#!/usr/bin/env python3
"""Apply translations to translations/<FILE>.json from a mapping file.

tl_apply.py FILE MAPPING.json [--force]

MAPPING.json: {"<string index>": "English text", ...} (section 0), or
              {"<section>:<index>": "..."} for other sections.
Existing non-empty translations are only replaced with --force.
"""
import json, sys

name, mapping = sys.argv[1], sys.argv[2]
force = '--force' in sys.argv
path = f'translations/{name}.json'
raw = open(path, encoding='utf-8').read()
d = json.loads(raw)
m = json.load(open(mapping, encoding='utf-8'))
changed = skipped = 0
for key, text in m.items():
    sec, idx = (key.split(':') if ':' in key else ('0', key))
    s = d['sections'][int(sec)]['strings'][int(idx)]
    if s['translation'] and s['translation'] != text and not force:
        print(f'skip {key}: already "{s["translation"][:40]}"'); skipped += 1; continue
    s['translation'] = text; changed += 1
open(path, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=4))
print(f'{name}: {changed} set, {skipped} skipped')
