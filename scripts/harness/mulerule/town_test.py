"""One town visit (chapter1.town_upkeep) from a state with the backup rule, then the next
trip's setting out (begin_adventure, the set-out camp). Writes LABEL.txt and states under
rips/harness/mulerule/.  usage: town_test.py STATE LABEL [--no-backups]"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import gear, town, chapter1
state, label = sys.argv[1], sys.argv[2]
if '--no-backups' in sys.argv:
    chapter1.BACKUPS = False
OUTD = 'mulerule'
out = open(os.path.join('rips/harness', OUTD, label + '.txt'), 'w')
def p(*a):
    print(*a, file=out, flush=True); print(*a, flush=True)
g = Game(capture=True)
g.load(state)
town.to_town_bar(g)

def snap(tag):
    m = town.town_party(g)
    who = m + [b for b in range(g.roster_count()) if b not in m]
    p('--- %s: party gold %d, roster gold %d, party room %d' % (tag, chapter1.party_gold(g), chapter1.roster_gold(g), gear.room(g, m)))
    for i in who:
        c = g.char(i)
        p('  %-8s %s lv%2d st=%#x gold=%6d pack %2d: %s' % (c['name'], 'P' if i in m else '-', c['level'], c['status'], c['gold'], len(gear.pack(g, i)),
          ', '.join(('*' if w & gear.EQUIPPED else '') + gear.name(w & 0x1ff) + ('' if w & gear.IDENT else '?') for _, w in gear.pack(g, i))))
snap('before')
bv = [0]
orig = chapter1.backup_visit
def timed(g_, log_):
    f = g_.frame; orig(g_, log_); bv[0] += g_.frame - f
chapter1.backup_visit = timed
log = []
f0, t0 = g.frame, time.time()
chapter1.town_upkeep(g, log)
f1 = g.frame
p('--- town visit: %d frames (%.0f s), backup_visit %d frames' % (f1 - f0, time.time() - t0, bv[0]))
KEEP = ('backups', 'backup put', 'backup take', 'equip edge', 'sell', 'buy', 'mule made', 'mule sell', 'gold',
        'identify edge', 'identify', 'uncurse', 'backup stuck', 'backup away', 'removed', 'mule make stuck', 'shop stuck', 'potion buy', 'restock', 'reserve')
for x in log:
    if x[1] in KEEP or 'stuck' in str(x[1]):
        p('  ', json.dumps(x, default=str))
snap('after town')
g.save(OUTD + '/' + label + '_town')
town.begin_adventure(g)
log2 = []
gear.camp_loot(g, log2)
chapter1.heal_in_camp(g, log2, frac=0.95)
p('--- set out: overlay %s, party %s, frames %d' % (g.overlay(), [g.name(i) for i in g.party()], g.frame - f1))
for x in log2:
    p('  ', json.dumps(x, default=str))
g.save(OUTD + '/' + label + '_setout')
p('done')
