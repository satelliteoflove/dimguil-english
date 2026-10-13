#!/usr/bin/env python3
"""Run walkthrough chapters, chained, in this process.

    python3 scripts/harness/run_chapter.py NAME --chapters 1-3 [--seed N] [--variant K]
                                           [--from STATE] [--screens DIR] [--no-cases]

Chapter 1 starts from power-on unless --from is given; a later first chapter needs
--from (the previous chapter's end state, e.g. chapters/c1v0/c1_end). Outputs go to
rips/harness/chapters/NAME/: result.json (per chapter: goals, frames, wall time, stuck),
log.jsonl, captured.jsonl, goal and stuck states, c<N>_end.state after each chapter;
shots to rips/harness/chapters/shots/ (shared, one per string id). --screens logs every
screen before each press for the T5 checks (harness.screens) to rips/harness/DIR.
"""
import argparse, json, os, sys, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from harness.game import Game, OUT
from harness import chapters

ap = argparse.ArgumentParser()
ap.add_argument('name')
ap.add_argument('--chapters', default='1-1')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--variant', type=int, default=0)
ap.add_argument('--from', dest='src')
ap.add_argument('--screens')
ap.add_argument('--no-cases', action='store_true',
                help="don't add stuck states to the regression suite (dev runs, old-disc states)")
a = ap.parse_args()
first, _, last = a.chapters.partition('-')
first, last = int(first), int(last or first)
if first > 1 and not a.src:
    sys.exit('chapter %d needs --from (chapter %d end state)' % (first, first - 1))

out = 'chapters/' + a.name
d = os.path.join(OUT, out)
os.makedirs(d, exist_ok=True)
g = Game(capture=True, shots_dir=os.path.join(OUT, 'chapters/shots'))
scr = None
if a.screens:
    from harness.screens import Screens
    scr = Screens(g, a.screens)
if a.src:
    g.load(a.src)
r = chapters.Run(g, seed=a.seed, variant=a.variant, out=out, auto_cases=not a.no_cases)
if a.src:
    r.ckpt = a.src
t0 = time.time()
ok = True
try:
    res = r.run_chapters(first, last, boot=not a.src)
except Exception as e:
    ok = False
    res = r.report()
    res['error'] = '%s: %s' % (type(e).__name__, e)
    res['info'] = {k: str(v) for k, v in getattr(e, 'info', {}).items()}
    res['trace'] = traceback.format_exc()
    res['failed_chapter'] = r.chapter
    try:
        g.shot(out + '/final_fail')
        g.save(out + '/final_fail')
    except Exception:
        pass
res['ok'] = ok
res['from'] = a.src
res['chapters_asked'] = [first, last]
res['wall'] = round(time.time() - t0, 1)
res['total_frames'] = g.frame
json.dump(res, open(os.path.join(d, 'result.json'), 'w'), indent=1, default=str)
with open(os.path.join(d, 'log.jsonl'), 'w') as f:
    for x in r.log:
        f.write(json.dumps(x, default=str) + '\n')
g.flush_shots()
if scr:
    scr.close()
g.dump_messages(os.path.join(d, 'captured.jsonl'))
print(json.dumps({k: v for k, v in res.items() if k not in ('trace', 'goals', 'chapters')}, default=str))
