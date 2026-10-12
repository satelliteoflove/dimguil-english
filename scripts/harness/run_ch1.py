#!/usr/bin/env python3
"""Run walkthrough chapter 1 from a cold boot (T3) in this process.

    python3 scripts/harness/run_ch1.py RUN_NAME [--seed N] [--variant K] [--from STATE]

Outputs go to rips/harness/t3/RUN_NAME/: result.json, log.jsonl, captured.jsonl, goal and
stuck states; shots to rips/harness/t3/shots/ (shared, one per string id). --from starts
from a saved goal state instead of power-on (skips the party goals).
"""
import argparse, json, os, sys, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from harness.game import Game, OUT, Stuck
from harness import chapter1

ap = argparse.ArgumentParser()
ap.add_argument('name')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--variant', type=int, default=0)
ap.add_argument('--from', dest='src')
a = ap.parse_args()

out = 't3/' + a.name
d = os.path.join(OUT, out)
os.makedirs(d, exist_ok=True)
g = Game(capture=True, shots_dir=os.path.join(OUT, 't3/shots'))
if a.src:
    g.load(a.src)
r = chapter1.Run(g, seed=a.seed, variant=a.variant, out=out)
if a.src:
    r.ckpt = a.src
t0 = time.time()
ok = True
try:
    res = r.run(boot=not a.src)
except Exception as e:
    ok = False
    res = r.report()
    res['error'] = '%s: %s' % (type(e).__name__, e)
    res['info'] = {k: str(v) for k, v in getattr(e, 'info', {}).items()}
    res['trace'] = traceback.format_exc()
    try:
        g.shot(out + '/final_fail')
        g.save(out + '/final_fail')
    except Exception:
        pass
res['ok'] = ok
res['wall'] = round(time.time() - t0, 1)
res['total_frames'] = g.frame
json.dump(res, open(os.path.join(d, 'result.json'), 'w'), indent=1, default=str)
with open(os.path.join(d, 'log.jsonl'), 'w') as f:
    for x in r.log:
        f.write(json.dumps(x, default=str) + '\n')
g.flush_shots()
g.dump_messages(os.path.join(d, 'captured.jsonl'))
print(json.dumps({k: v for k, v in res.items() if k != 'trace'}, default=str))
