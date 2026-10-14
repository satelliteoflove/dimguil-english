"""summary.py SWEEP.jsonl...: per state and disc, results by cadence; checks every run's
fix words (new disc 'new' at the battle's start and end, old disc 'old')."""
import sys, json, collections
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip()]
bad = [r for r in rows if 'error' in r or r.get('words') != {'ca912fe8': 'old', 'ba2a42a6': 'new'}[r['disc']]]
print('runs', len(rows), 'word-check failures or errors', len(bad))
for r in bad[:5]: print('  ', str(r)[:300])
T = collections.defaultdict(collections.Counter)
for r in rows:
    if 'error' in r: continue
    T[(r['state'], r['disc'])][r['result'].split(' (')[0]] += 1
for k in sorted(T): print(k, dict(T[k]))
hangs = [r for r in rows if r.get('result') == 'HANG']
print('hangs', len(hangs), 'epc/cause', collections.Counter((r['epc'], r['cause']) for r in hangs),
      'pcs', collections.Counter(r['pcs'] for r in hangs), 'min vsync_still', min((r['vsync_still'] for r in hangs), default=None))
for r in hangs:
    c = [x[1] for x in r['casts'][-2:]]
    print('  %s cad %s off %s hang at %d after %s' % (r['state'], r['cad'], r['off'], r['hang_from'], c))
# matched pairs: same state/cad/off, old hung: what did the new run do at that point?
by = {(r['state'], r['cad'], r['off'], r['disc']): r for r in rows if 'error' not in r}
print('old-disc hangs vs the same inputs on the new disc:')
for r in hangs:
    if r['disc'] != 'ca912fe8': continue
    n = by.get((r['state'], r['cad'], r['off'], 'ba2a42a6'))
    if not n: continue
    same = n['casts'][:len(r['casts'])] == r['casts']
    print('  %s cad %s off %s: new %s, %d frames, casts identical up to the hang: %s, stops %d' % (
        r['state'], r['cad'], r['off'], n['result'], n['frames'], same, n['stops']))
