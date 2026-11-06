"""Run one regress stuck case on a chosen disc, outside rips/harness/regress (snakefail
investigation, 2026-11-06). Logs every change of g.where() with its frame, saves the end
state, and the game's messages.

    python3 scripts/snakefail_run.py DISC_CUE CASE_ID TAG
Output: rips/harness/snakefail/TAG/{trace.jsonl,result.json,end.state,messages.txt}
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'harness'))
from harness import game, regress
from harness.game import Game, Stuck

cue, cid, tag = sys.argv[1:4]
OUTD = os.path.join(regress.OUTR, 'snakefail', tag)
os.makedirs(OUTD, exist_ok=True)
case = next(c for c in regress.load_cases() if c['id'] == cid)
regress.SLPS = os.path.join(os.path.dirname(cue), 'dimguil', 'SLPS_026.91')
Game.__init__.__defaults__ = (cue, True, None)

tr = open(os.path.join(OUTD, 'trace.jsonl'), 'w')
last = [None]
step0 = Game.step


def step(self, n=1):
    step0(self, n)
    w = self.where()
    if w != last[0]:
        last[0] = w
        tr.write(json.dumps(dict(f=self.frame, **w)) + '\n')
        tr.flush()


Game.step = step
GG = []
init0 = Game.__init__


def init(self, *a, **k):
    init0(self, *a, **k)
    GG.append(self)


Game.__init__ = init
rec = dict(case=cid, disc=cue, main_overlay=regress.overlay_main())
t0 = time.time()
# run_stuck, with the run's out under snakefail/
from harness import chapters
g = Game(capture=True)
g.load(case['state'])
run = chapters.Run(g, seed=case.get('seed', 7), variant=case.get('variant', 0),
                   out='snakefail/%s/scratch' % tag, retries=1, auto_cases=False)
run.chapter = case['chapter']
fn = run.goal_fns(case['chapter'])[case['goal']]
g.budget_end = g.frame + int(os.environ.get("BUDGET", regress.BUDGET))
f0 = g.frame
try:
    r = fn()
    rec.update(result=str(r), frames=g.frame - f0)
except Stuck as e:
    rec.update(error='Stuck: ' + e.what, info={k: str(v) for k, v in e.info.items()},
               frames=g.frame - f0)
except Exception as e:
    rec.update(error=repr(e), frames=g.frame - f0)
rec['wall'] = round(time.time() - t0, 1)
g.e.save(os.path.join(OUTD, 'end.state'))
try:
    with open(os.path.join(OUTD, 'messages.txt'), 'w') as f:
        for m in g.cap.messages:
            f.write(json.dumps(m, default=str, ensure_ascii=False) + '\n')
except Exception as e:
    rec['msg_err'] = repr(e)
json.dump(rec, open(os.path.join(OUTD, 'result.json'), 'w'), indent=1)
print(json.dumps(rec))
