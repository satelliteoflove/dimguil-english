"""One training trip (the chapter's train goal, as regress.run_stuck runs it) from a
state, then what its town visit did.  usage: trip_test.py STATE CHAPTER LABEL SEED VARIANT"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import chapters, chapter1, gear, town
state, ch, label, seed, variant = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
if '--no-backups' in sys.argv:
    chapter1.BACKUPS = False
out = open('rips/harness/mulerule/%s.txt' % label, 'w')
def p(*a):
    print(*a, file=out, flush=True); print(*a, flush=True)
g = Game(capture=True)
g.load(state)
run = chapters.Run(g, seed=seed, variant=variant, out='mulerule/run_' + label, retries=1, auto_cases=False)
run.chapter = ch
fns = run.goal_fns(ch)
name = next((k for k in fns if k.startswith('train_')), None)
if name is None:
    import importlib
    mod = importlib.import_module('harness.chapter%d' % ch)
    name = 'train (direct)'
    fns[name] = run.guarded(lambda: run.train(mod.TRAIN_AREAS))
p('state', state, 'goal', name, 'party', [(g.name(i), g.char(i)['level']) for i in town.town_party(g)],
  'gold', chapter1.party_gold(g), 'roster gold', chapter1.roster_gold(g))
t0, f0 = time.time(), g.frame
g.budget_end = g.frame + 200000
try:
    r = fns[name]()
except Exception as e:
    r = 'error %s: %s %s where %s' % (type(e).__name__, getattr(e, 'what', e), getattr(e, 'info', ''), g.where())
    import traceback; traceback.print_exc()
p('result', r, 'frames', g.frame - f0, 'secs', round(time.time() - t0))
KEEP = ('backups', 'backup put', 'backup take', 'equip edge', 'sell', 'buy', 'mule made', 'mule sell', 'gold',
        'backup stuck', 'backup away', 'removed', 'trip home', 'reserve')
for x in run.log:
    if x[1] in KEEP or 'stuck' in str(x[1]):
        p('  ', json.dumps(x, default=str)[:400])
m = town.town_party(g) if g.overlay() == 'JOUKA' else g.party()
p('end: overlay', g.overlay(), 'party', [g.name(i) for i in m], 'gold', chapter1.party_gold(g), 'roster gold', chapter1.roster_gold(g))
for i in range(g.roster_count()):
    if i not in m:
        p('  %-8s lv%2d pack %s' % (g.name(i), g.char(i)['level'], ', '.join(('*' if w & gear.EQUIPPED else '') + gear.name(w & 0x1ff) + ('' if w & gear.IDENT else '?') for _, w in gear.pack(g, i))))
g.save('mulerule/%s_end' % label)
