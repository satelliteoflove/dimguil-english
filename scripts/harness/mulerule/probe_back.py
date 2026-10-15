"""Probe: from the Edge's Give lists, back out with cross one press at a time; then time the pieces."""
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import gear, town, ui
g = Game(capture=True)
g.load('mulerule/c9_n1v0j_town')
town.to_town_bar(g)
f = g.frame
town.enter(g, 'edge')
ui.wait_until(g, lambda: g.u8(town.FAC_SUB) == 5 or g.u8(town.EDGE_CURSOR) == 0, 300, 'edge menu')
print('enter edge', g.frame - f); f = g.frame
gear._edge_items(g, 0)  # re-enters? _edge_items calls town.enter
print('edge items', g.frame - f); f = g.frame
ui.move_cursor(g, gear.EDGE_ITEMS_CUR, gear.ITEMS_GIVE, 'down', 'up', what='Give')
gear._edge_press(g, lambda: g.u8(gear.GIVE_STATE) == 5, 'edge Give')
g.step(8)
ui.move_cursor(g, gear.CAMP_TARGET, 1, 'right', 'left', wrap=6, what='give to')
gear._edge_press(g, lambda: g.u8(gear.GIVE_STATE) == 15, 'edge give lists')
print('to lists', g.frame - f); f = g.frame
for k in range(6):
    g.tap('cross')
    for _ in range(40):
        g.step()
    print('cross', k, 'edge', g.u8(gear.EDGE_STATE), 'give', g.u8(gear.GIVE_STATE), 'sub', g.u8(town.FAC_SUB), 'ovl', g.overlay(), 'gy', g.u8(gear.EDGE_GY), 'gx', g.u8(gear.EDGE_GX))
    if g.u8(gear.EDGE_STATE) == 25:
        break
f = g.frame
gear.edge_leave(g)
print('edge_leave from 25', g.frame - f)
