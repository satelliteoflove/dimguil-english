"""Tally won fights in the harness chapter logs: chest or not, by area, by encounter kind
(fight square from the site's map data, MPT party by group id >= 340, else token)."""
import json, glob, os, collections, sys
sys.path.insert(0, 'rips/agents/chests')
SITE = os.path.expanduser('~/Documents/bartoks-trading-post/data/maps/dim')
fs = {}  # floor -> set of (x, y) in both conventions
for p in glob.glob(f'{SITE}/f*.json'):
    d = json.load(open(p))
    s = set()
    for e in d['events']:
        if e['raw']['type'] == 0x14:
            for x, y in e['squares']:
                s.add((x, y))
    fs[d['floor']] = s
tb = json.load(open('rips/agents/chests/trebox.json'))
r83 = {m['n']: m['r83'] for m in tb['monsters'] if m['idok']}
AREA = {0: 'Grounds', 1: 'Shrine 1F', 2: 'Shrine 2F', 3: 'Shrine 3F', 4: 'Shrine 4F', 5: 'Und B4', 6: 'Und B3', 7: 'Und B2', 8: 'Und B1',
        18: 'Area X', 19: 'A-B4', 20: 'A-B3', 21: 'A-B2', 22: 'A-B1', 23: 'B-B5', 24: 'B-B4', 25: 'B-B3', 26: 'B-B2', 27: 'B-B1',
        28: 'C-B4', 29: 'C-B3', 30: 'C-B2', 31: 'C-B1', 32: 'D-B3', 33: 'D-B2', 34: 'D-B1', 36: 'E-B4', 37: 'E-B3', 38: 'E-B2', 39: 'E-B1',
        40: 'Dragon B3', 41: 'Dragon B2', 42: 'Dragon B1', 43: 'Area Z'}
for a in range(9, 17): AREA[a] = f'Training B{a-8}'
rows = []
for p in sorted(glob.glob('rips/harness/chapters/*/log.jsonl')):
    run = p.split('/')[-2]
    for l in open(p):
        try: r = json.loads(l)
        except Exception: continue
        if not (isinstance(r, list) and len(r) > 2 and r[1] == 'fought'): continue
        f = r[2]
        if f.get('fled') and any(f['fled']): continue
        if f.get('dead_end') and False: pass
        w = f.get('where'); fi = f.get('first') or {}
        gs = fi.get('groups') or []
        g1 = gs[0]['id'] if gs else None
        chest = f.get('chest') is not None
        rows.append(dict(run=run, frame=r[0], where=w, g1=g1, chest=chest, story=f.get('story'), fixed=fi.get('fixed'),
                         sig=(tuple(w) if w else None, tuple(g['id'] for g in gs), tuple(g.get('n') for g in gs))))
def kind(r):
    if r['g1'] is None: return 'unknown'
    if r['story']: return 'story'
    if r['g1'] >= 340: return 'party (type-2 token)'
    w = r['where']
    if not w: return 'monster, square unknown'
    a, x, y = w[:3]
    s = fs.get(a, set())
    on_a = (x, y) in s; on_b = (x, 23 - y) in s
    return 'monster on fight square' if on_b else 'monster off fight square'
if __name__ == '__main__':
    print('fights (not fled):', len(rows))
    # convention check: chest fights on fight squares
    c = collections.Counter()
    for r in rows:
        if r['where'] and r['chest'] and r['g1'] is not None and r['g1'] < 340:
            a, x, y = r['where'][:3]; s = fs.get(a, set())
            c[('code-y' if (x, y) in s else '-', 'flip-y' if (x, 23 - y) in s else '-')] += 1
    print('chest fights vs fight squares, y as is / flipped:', c)
    # dedupe replays: same run, same where and groups and counts
    seen = set(); ded = []
    for r in rows:
        k = (r['run'], r['sig'], r['chest'])
        if k in seen: continue
        seen.add(k); ded.append(r)
    for name, rs in (('all', rows), ('deduped', ded)):
        print(f'\n== {name}: {len(rs)} fights')
        byk = collections.defaultdict(lambda: [0, 0])
        for r in rs:
            byk[kind(r)][0] += 1; byk[kind(r)][1] += r['chest']
        for k, (n, ch) in sorted(byk.items()): print(f'  {k:28s} {n:6d} fights {ch:5d} chests {100*ch/n:5.1f}%')
        z = collections.defaultdict(lambda: [0, 0])
        for r in rs:
            if kind(r) == 'monster on fight square':
                z['r83=0' if r83.get(r['g1'], -1) == 0 else 'r83>0'][0] += 1
                z['r83=0' if r83.get(r['g1'], -1) == 0 else 'r83>0'][1] += r['chest']
        print('  fight squares by monster chest byte:', dict(z))
        ba = collections.defaultdict(lambda: [0, 0, 0, 0])
        for r in rs:
            if not r['where']: continue
            a = r['where'][0]; k = kind(r)
            ba[a][0] += 1; ba[a][1] += r['chest']; ba[a][2] += k == 'monster on fight square'; ba[a][3] += k == 'party (type-2 token)'
        print('  area: fights, chests, %, on fight square, party fights')
        for a in sorted(ba):
            n, ch, sq, pt = ba[a]
            print(f'  {AREA.get(a, a):12s} {n:5d} {ch:5d} {100*ch/n:5.1f}% {sq:5d} {pt:5d}')
    # odd ones: chest off a fight square or party with chest
    odd = [r for r in ded if r['chest'] and kind(r) not in ('monster on fight square',)]
    print('\nchests not on a fight square:', len(odd))
    for r in odd[:20]: print('  ', r['run'], r['frame'], r['where'], r['g1'], r['story'], kind(r))
    json.dump(rows, open('rips/agents/chests/fights.json', 'w'))
