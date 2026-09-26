#!/usr/bin/env python3
"""Apply reviewed NPC dialogue to translations/NPC_MESn.OBJ.json.

    npcapply.py OVERLAY.json [KEY ...]

OVERLAY maps "n:idx" to the full new translation of string idx in NPC_MESn (the same
format `npcfit.py --overlay` checks). With KEYs, only those entries are applied;
otherwise all of them. The files keep their formatting (4-space JSON, no trailing
newline), so a commit shows only the changed strings.
"""
import json, os, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')


def main():
    overlay = json.load(open(sys.argv[1], encoding='utf-8'))
    keys = sys.argv[2:] or list(overlay)
    files = {}
    for key in keys:
        n, idx = map(int, key.split(':'))
        if n not in files:
            path = os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json')
            files[n] = (path, json.load(open(path, encoding='utf-8')))
        files[n][1]['sections'][0]['strings'][idx]['translation'] = overlay[key]
    for path, data in files.values():
        open(path, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=4))
    print(f'applied {len(keys)} strings to {len(files)} files')


if __name__ == '__main__':
    main()
