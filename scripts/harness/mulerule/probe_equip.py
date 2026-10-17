"""Probe: the Edge of Town's Inspect > Items > Equip (HAZURE equip_menu 0x800afa9c)."""
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import gear, town, ui, chapter1, camp
g = Game(capture=True)
g.load('chapters/n1v0j/goal_06_train_04')
log = []
town.to_town_bar(g)
chapter1.leave_party(g, log, 5)
town.to_town_bar(g)
town.form_party(g, [6])
town.to_town_bar(g)
pos = town.town_slots(g).index(6)
print('party', town.town_slots(g), 'ace at', pos)
gear._edge_items(g, pos)
ui.move_cursor(g, gear.EDGE_ITEMS_CUR, gear.ITEMS_EQUIP, 'down', 'up', what='Equip')
A = dict(edge=gear.EDGE_STATE, eid=gear.EDGE_ID_STATE, sp=camp.SPELL_STATE, slot=gear.EQ_SLOT, prompt=gear.EQ_PROMPT,
         st=gear.EQ_STATE, cnt=gear.EQ_COUNT, cur=gear.EQ_CURSOR, msg=gear.CAMP_MSG, sub=town.FAC_SUB)
def snap():
    return {k: g.u8(a) for k, a in A.items()}
print('before', snap())
g.tap('circle')
last = None
for f in range(1500):
    g.step()
    s = snap()
    if s != last:
        print(g.frame, s)
        last = s
    if s['prompt'] == 1 and s['st'] == 0xf and f % 40 == 39:
        n = s['cnt']
        import struct
        cands = [struct.unpack('<h', g.e.read(gear.EQ_CANDS + 2 * j, 2))[0] for j in range(n)]
        print('  prompt slot', s['slot'], 'cands', cands, 'cursor', s['cur'])
        g.tap('circle')
print('pack after', [(k, gear.name(w & 0x1ff), hex(w)) for k, w in gear.pack(g, 6)])
