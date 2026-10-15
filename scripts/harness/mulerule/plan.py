"""Print gear.backup_plan for a state (RAM only)."""
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import gear, town
g = Game(capture=False)
for st in sys.argv[1:]:
    g.load(st)
    m = town.town_party(g)
    print(st, 'room', gear.room(g, m), 'backups', [(g.name(b), 10 - len(gear.pack(g, b))) for b in gear.backups(g, m)], 'mule', gear.mule(g))
    for b, ri, kind, w, why, v in gear.backup_plan(g):
        print('   ', kind, g.name(ri), '<->', g.name(b) if b is not None else '(new Mule)', gear.name(w & 0x1ff), why, v)
