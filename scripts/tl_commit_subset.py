#!/usr/bin/env python3
"""Stage only some strings of translation files that carry more uncommitted work.

    tl_commit_subset.py FILE:RANGES [FILE:RANGES ...]

For each FILE (e.g. SISETU.OBJ), takes the committed version, copies in the working
copy's translations for the listed strings (RANGES as in reviewpage.py), and stages
the result with git, leaving the working copy as it was. Lets a batch of translated
screens go in as one commit per approved screen.
"""
import json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from reviewpage import load, indices

for spec in sys.argv[1:]:
    name, _, rng = spec.partition(':')
    path = f'translations/{name}.json'
    work = load(path)['sections']
    keys = {f'{s}:{i}' if s else str(i): work[s]['strings'][i]['translation'] for s, i in indices(rng)}
    working = open(path, encoding='utf-8').read()
    committed = subprocess.run(['git', 'show', f'HEAD:{path}'], capture_output=True, text=True, check=True).stdout
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as m:
        json.dump(keys, m, ensure_ascii=False)
    try:
        open(path, 'w', encoding='utf-8').write(committed)
        subprocess.run([sys.executable, 'scripts/tl_apply.py', name, m.name, '--force'], check=True)
        subprocess.run(['git', 'add', path], check=True)
    finally:
        open(path, 'w', encoding='utf-8').write(working)
        os.remove(m.name)
