"""Write docs/playthrough-review-plan.md from rips/playplan/npc-by-chapter.json (build_plan.py):
which review-tool scenes to finish before each chapter of the play-through."""
import json, collections, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
d = json.load(open(os.path.join(ROOT, 'rips/playplan/npc-by-chapter.json')))
TITLES = {1: 'The four pillars', 2: 'The Shrine and the jade mask', 3: 'The Underground Shrine and the blue stone',
          4: 'The lake machine', 5: 'The moon door and the 2-Head Snake', 6: 'Area X and the white stone',
          7: 'Area A: the green stone', 8: 'Area A: the yellow stone and the Jail Ogre', 9: 'Area B: the black stone',
          10: 'Area B: the red stone', 11: 'Area A: the gold armor', 12: 'Area C: the silver stone',
          13: 'Area C: the moving floors', 14: 'Area D: mimicry mode released', 15: 'Area C: the demon statue',
          16: 'Area A: the gold stone', 17: 'Area E: the control room',
          19: "The ring for the Priestess's Door (bot-only detour)", 18: 'Area Z and the ending (walkthrough 18-19)'}
PLAY = [str(c) for c in list(range(1, 18)) + [19, 18]]
ORD = {c: i for i, c in enumerate(PLAY)}
STATUS = {'open': 'open', 'proposed': 'change proposed', 'ai-reviewed': 'not yet read', 'check': 'check in play'}


def rng(ix):
    ix = sorted(ix); out = []; s = p = ix[0]
    for x in ix[1:] + [None]:
        if x is not None and x == p + 1:
            p = x; continue
        out.append(str(s) if s == p else f'{s}-{p}')
        if x is not None:
            s = p = x
    return ','.join(out)


def fnum(f):
    return f[-5] if f.startswith('NPC') else 'EV'


def refs(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[fnum(r['file'])].append(r['index'])
    return '; '.join(f'{n}:{rng(ix)}' for n, ix in sorted(by.items()))


placed = [r for c in PLAY for r in d[c]]
unp = d['unplaced']
allrows = placed + unp

# Each review scene's deadline: the first chapter where one of its lines is placed, or,
# for lines with no chapter, where their party is first met.
scene = collections.defaultdict(lambda: {'rows': [], 'due': None, 'how': set(), 'title': ''})
for r in allrows:
    sid = r.get('review_scene') or 'none'
    s = scene[sid]
    s['rows'].append(r)
    s['title'] = r.get('review_title', 'No open review scene')
    ch = r.get('chapter') or r.get('party_first_chapter')
    ch = str(ch) if ch is not None else None
    if ch and (s['due'] is None or ORD[ch] < ORD[s['due']]):
        s['due'] = ch
    s['how'].add('placed' if r.get('chapter') else 'party met')

out = [f"""# Play-through review plan: what to review before each chapter

Chris plays with the monitor (`scripts/playwatch.py`) pausing on every NPC line not yet
reviewed with him: lines in a review-tool scene still open, lines with a change proposed
there, and lines only the AI reviewers have read (`scripts/textstatus.py`). There are
{len(allrows)} such lines now, in {len([k for k in scene if k != 'none'])} review-tool scenes. This plan
says which scenes to finish before each chapter, so the monitor rarely stops. Built by
`scripts/playplan/build_plan.py` and `write_md.py` from the review tool's scenes and
decisions; rerun both after a review session.

{len(d.get('behind', []))} more lines are reviewed and committed but newer than the published disc; the
monitor pauses on those too ("behind") until the next build and publish, so build before
each session.

A scene's chapter is the first chapter where one of its lines is placed (seen by a bot
run there, or named by the site walkthrough or `docs/npc-map.md`), or, for talk-menu
lines nobody can place, the chapter where the party is first met. Chapters are in play
order: 1 to 17, then 19 (the ring for the Priestess's Door), then 18 (Area Z and the
ending).

## Scenes to finish, by chapter
"""]
by_due = collections.defaultdict(list)
for sid, s in scene.items():
    by_due[s['due'] or 'any'].append((sid, s))
for c in PLAY + ['any']:
    if c not in by_due:
        continue
    head = f'### Before chapter {c}: {TITLES[int(c)]}' if c != 'any' else '### No chapter known'
    out.append(head + '\n')
    out.append('| Review-tool scene | Lines | Count | Why this chapter |')
    out.append('|---|---|---|---|')
    for sid, s in sorted(by_due[c], key=lambda x: (-len(x[1]['rows']), x[0])):
        st = collections.Counter(STATUS.get(r['status'], r['status']) for r in s['rows'])
        why = 'no chapter: confirm in play' if c == 'any' else 'lines placed here' if 'placed' in s['how'] and any(str(r.get('chapter')) == c for r in s['rows']) \
            else 'party first met here'
        out.append(f"| {s['title']} (`{sid}`) | {refs(s['rows'])} | {len(s['rows'])} "
                   f"({', '.join(f'{v} {k}' for k, v in st.most_common())}) | {why} |")
    out.append('')

out.append('## Lines placed in each chapter\n')
out.append('The lines a bot run or the walkthrough puts in a chapter, for knowing what the monitor '
           'will stop on there. Evidence is bot, walkthrough or map.\n')
for c in PLAY:
    rows = d[c]
    if not rows:
        continue
    out.append(f'### Chapter {c}: {TITLES[int(c)]}\n')
    out.append('| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |')
    out.append('|---|---|---|---|---|')
    g = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r['file'], r['scene'], r['index'])):
        g.setdefault((r['party'], r['scene'], r.get('review_title', '-')), []).append(r)
    for (party, topic, rt), rs in g.items():
        ev = collections.Counter(r.get('evidence', '-') for r in rs)
        out.append(f"| {party} | {topic.replace('|', '/')} | {refs(rs)} | {rt} | "
                   f"{', '.join(f'{k} {v}' for k, v in ev.items())} |")
    out.append('')

pf = collections.Counter()
for r in unp:
    pf[(r['party'], r.get('party_first_chapter'))] += 1
out.append(f'## Lines with no chapter ({len(unp)})\n')
out.append('Talk-menu, healing, identify, shop and greeting lines that play whenever a party is met '
           'and a topic picked. They count toward the chapter where the party is first met:\n')
for (party, ch), n in sorted(pf.items(), key=lambda x: ORD.get(str(x[0][1]), 99)):
    out.append(f'- {party}: {n} lines, from chapter {ch}')
out.append('')
open(os.path.join(ROOT, 'docs/playthrough-review-plan.md'), 'w', encoding='utf-8').write('\n'.join(out))
print(len(allrows), 'lines,', len(scene), 'scenes')
