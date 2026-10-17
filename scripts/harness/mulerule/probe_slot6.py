"""Probe: Jo's equip at the Edge, the accessory prompt (slot 6): which byte is the cursor."""
import sys, os, struct
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import gear, town, ui, chapter1
g = Game(capture=True)
g.load('mulerule/wear_c4_after')
town.to_town_bar(g)
log = []
chapter1._mule_in(g, log, 6, ())
pos = town.town_slots(g).index(6)
print('party', town.town_slots(g), 'jo at', pos, 'pack', [(k, gear.name(w & 0x1ff), hex(w)) for k, w in gear.pack(g, 6)])
gear._edge_items(g, pos)
ui.move_cursor(g, gear.EDGE_ITEMS_CUR, gear.ITEMS_EQUIP, 'down', 'up', what='Equip')
gear._edge_press(g, lambda: g.u8(gear.EQ_STATE) != 0, 'edge Equip')
for _ in range(400):
    if g.u8(gear.EQ_PROMPT) == 1 and g.u8(gear.EQ_STATE) == 0xf:
        s = g.u8(gear.EQ_SLOT)
        n = g.u8(gear.EQ_COUNT)
        cands = [struct.unpack('<h', g.e.read(gear.EQ_CANDS + 2 * j, 2))[0] for j in range(n)]
        print('slot', s, 'n', n, 'cands', cands, 'cursor', g.u8(gear.EQ_CURSOR))
        if s == 6:
            snap = g.e.read(0x80079000, 0x1000)
            g.tap('down'); g.step(20)
            snap2 = g.e.read(0x80079000, 0x1000)
            print('changed after down:', [(hex(0x80079000 + i), snap[i], snap2[i]) for i in range(0x1000) if snap[i] != snap2[i] and 0x80079000 + i >= 0x80079500])
            print('cursor', g.u8(gear.EQ_CURSOR), 'state', g.u8(gear.EQ_STATE), 'prompt', g.u8(gear.EQ_PROMPT), 'slot', g.u8(gear.EQ_SLOT))
            for k in range(4):
                g.tap('down'); g.step(20)
                print(' down -> cursor', g.u8(gear.EQ_CURSOR), [hex(0x80079000 + i) for i in range(0xb00, 0xd00) if g.e.read(0x80079000 + i, 1)[0] != snap2[i]])
            break
        sig = (s, g.u8(gear.EQ_STATE), g.u8(gear.EQ_PROMPT))
        ui.press_until(g, 'circle', lambda: (g.u8(gear.EQ_SLOT), g.u8(gear.EQ_STATE), g.u8(gear.EQ_PROMPT)) != sig, 120, 'pick')
        continue
    g.step()
