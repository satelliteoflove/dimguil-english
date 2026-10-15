"""Hand-down test: from the chapter 4 town state (after the first visit), Mercury buys a
Shadow Cloak at Boltac's (everyone in the party wears one already, so it's spare; the
level-1 standbys Jo and Kai wear none). Then Boltac's sell step (a reserve so high
nothing else is bought or identified) must keep it, and backup_visit must hand it to a
standby and put it on there."""
import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import gear, town, chapter1
out = open('rips/harness/mulerule/wear_c4.txt', 'w')
def p(*a):
    print(*a, file=out, flush=True); print(*a, flush=True)
g = Game(capture=True)
g.load('mulerule/c4_n1v3e_town')
town.to_town_bar(g)
log = []
pos = town.town_slots(g).index(5)          # Mercury
town.pool_gold(g, pos, 'tavern'); town.to_town_bar(g)
g0 = chapter1.party_gold(g)
r = gear.buy(g, pos, 245)
town.boltac_leave(g) if town._at_trade_menu(g) else None
town.to_town_bar(g)
p('bought', r, 'gold', g0, '->', chapter1.party_gold(g))
for b, ri, kind, w, why, v in gear.backup_plan(g):
    p('plan', kind, g.name(ri), g.name(b) if b is not None else 'new Mule', gear.name(w & 0x1ff), why, v)
gear.shop(g, log, 10 ** 9)
p('after the sell step: Mercury', [gear.name(w & 0x1ff) for _, w in gear.pack(g, 5)], 'gold', chapter1.party_gold(g))
f = g.frame
chapter1.backup_visit(g, log)
p('backup_visit frames', g.frame - f)
for x in log:
    p('  ', json.dumps(x, default=str)[:300])
for i in (6, 7):
    p(g.name(i), [('*' if w & gear.EQUIPPED else '') + gear.name(w & 0x1ff) for _, w in gear.pack(g, i)])
p('party', [g.name(i) for i in town.town_party(g)], 'gold', chapter1.party_gold(g))
g.save('mulerule/wear_c4_after')
