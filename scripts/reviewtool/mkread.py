#!/usr/bin/env python3
"""Read-through scenes for the review tool: the NPC lines the reviewers read against the
Japanese and didn't flag (textstatus.py's 'ai-reviewed'), for Chris to read as they stand.

    python3 scripts/reviewtool/mkread.py N [N ...]     NPC_MESn files, e.g. 2 3

Lines are grouped by the topics in docs/npc-map.md ("**2.14 Healing (114-135, 267).**"),
consecutive topics merged up to about MAX lines, and written as
rips/review/scenes/readN-KK.json with kind "readthrough": no literal and no proposal, the
server fills in the current English as both. A file whose read-throughs already exist is
skipped; --force rewrites them, but not once any of them has a decision.
Once a read-through is applied, textstatus.py counts its lines as reviewed.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import textstatus  # noqa: E402

SCENES = os.path.join(ROOT, 'rips/review/scenes')
DECISIONS = os.path.join(ROOT, 'rips/review/decisions')
MAX = 24


def topics(n):
    """[(title, paragraph, [indices])] for NPC_MESn, from npc-map.md's headings."""
    doc = open(os.path.join(ROOT, 'docs/npc-map.md'), encoding='utf-8').read()
    body = re.split(rf'^## NPC_MES{n}\b', doc, flags=re.M)[1].split('\n## ')[0]
    out = []
    for m in re.finditer(r'^\*\*\d+\.\d+ ([^*]*)\*\*(.*?)(?=\n\n|\Z)', body, flags=re.M | re.S):
        head = m.group(1).strip()
        seen = []
        for grp in re.findall(r'\(([^)]*)\)', head):
            for a, b in re.findall(r'(\d+)(?:-(\d+))?', grp):
                seen += [i for i in range(int(a), int(b or a) + 1) if i not in seen]
        title = re.sub(r'\s*\([^)]*\)\.?$', '', head).rstrip('.')
        para = ' '.join(m.group(2).split())
        para = re.sub(r'(?:Not flagged|Flagged)\b[^.]*\.\s*', '', para)   # the review's bookkeeping
        out.append((title, para, sorted(seen)))
    return out


def main():
    import glob
    force = '--force' in sys.argv
    status = textstatus.table()
    for n in (int(a) for a in sys.argv[1:] if a != '--force'):
        f = f'NPC_MES{n}.OBJ'
        have = glob.glob(os.path.join(SCENES, f'read{n}-*.json'))
        if have and (not force or any(os.path.exists(os.path.join(DECISIONS, os.path.basename(h)))
                                       for h in have)):
            print(f'NPC_MES{n}: read-throughs exist, skipped' + (' (some have decisions)' if force else ''))
            continue
        for h in have:
            os.remove(h)
        groups, used = [], set()
        for t, p, idx in topics(n):          # a line under two topics goes with the first
            keep = [i for i in idx if status(f, i)[0] == 'ai-reviewed' and i not in used]
            used.update(keep)
            if keep:
                groups.append((t, p, keep))
        chunks, cur = [], []
        for g in groups:
            if cur and sum(len(x[2]) for x in cur) + len(g[2]) > MAX:
                chunks.append(cur)
                cur = []
            cur.append(g)
        if cur:
            chunks.append(cur)
        made = 0
        for k, chunk in enumerate(chunks, 1):
            sid = f'read{n}-{k:02d}'
            names = [t for t, _, _ in chunk]
            lines = [{'ref': f'{n}:{i}', 'context': t} for t, _, idx in chunk for i in idx]
            scene = {
                'id': sid, 'kind': 'readthrough', 'file': n, 'number': None, 'order': 500 + k,
                'title': 'Read-through: ' + (names[0] if len(names) == 1 else
                                             f'{names[0]} and {names[1]}' if len(names) == 2 else
                                             f'{names[0]}, {names[1]} and {len(names) - 2} more'),
                'where': ' '.join(f'{t}: {p}' for t, p, _ in chunk if p),
                'summary': f'{len(lines)} lines the reviewers read against the Japanese and left as '
                           'they are. Read each in its box; edit it or leave a note if something is off, '
                           'then mark the group reviewed.',
                'lines': lines, 'notes': [],
            }
            json.dump(scene, open(os.path.join(SCENES, sid + '.json'), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
            made += 1
        print(f'NPC_MES{n}: {sum(len(g[2]) for g in groups)} lines in {len(chunks)} read-throughs '
              f'({made} written)')


if __name__ == '__main__':
    main()
