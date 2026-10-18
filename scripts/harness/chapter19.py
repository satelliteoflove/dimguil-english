"""Chapter 19 (draft): tavern helpers for the ring trick."""
import struct

from harness import gear, town, ui
from harness.game import Stuck

RING = 0x142
INSPECT_ICON = 2                # the tavern's icons: Form Party, Remove Member, Inspect, ...
INSP_STATE = 0x80079c1b         # tavern_inspect (JOUKA 0x800aa444): 16 the member pick, 20 the status screen
ITEM_STATE = 0x80079804         # FUN_800cbddc: 5 its menu (cursor 0x80079c5e), 10 + 5 x row while a row runs
ITEM_CUR = 0x80079c5e           # Spellbook, Equip Items, Give Items, Drop Items, Sort Items
ROW_EQUIP, ROW_GIVE = 1, 2
GIVE_STATE = 0x80079569         # 5 "Give an item to whom?" (target 0x80079948), 15 "Give which item?" (0x80079c60)
GIVE_TARGET = 0x80079948
LIST_CUR = 0x80079c60


def tavern_items(g, pos, limit=600):
    """Tavern > Inspect > the member at party position pos: its status screen's menu
    (ITEM_STATE 5)."""
    if g.u8(town.TOWN_STATE) != 10 or g.overlay() != 'JOUKA':
        town.enter(g, 'tavern')
    ui.wait_until(g, lambda: town.facility_ready(g), limit, 'tavern menu')
    ui.move_cursor(g, town.FAC_CURSOR, INSPECT_ICON, 'right', 'left', what='Inspect')
    ui.confirm_until(g, lambda: g.u8(INSP_STATE) == 16, limit, 'open Inspect')
    g.step(10)
    town._pick_party_member(g, pos, 'inspect')
    ui.confirm_until(g, lambda: g.u8(INSP_STATE) == 20 and g.u8(ITEM_STATE) == 5, limit, 'inspect member')
    g.step(10)


def tavern_leave_items(g, limit=600):
    """Back from the status screen (or a row of it) to the tavern's menu."""
    ui.cancel_until(g, lambda: town.facility_ready(g) and g.u8(town.TOWN_STATE) == 10, limit,
                    'back to the tavern menu')


def tavern_give(g, from_pos, item, to_pos, limit=600):
    """Give the first `item` (id) in the pack of the member at from_pos to the member at
    to_pos (tavern Inspect > Give Items, the camp's give fields). True once it moved."""
    slots = town.town_slots(g)
    gi, ri = slots[from_pos], slots[to_pos]
    k = next((k for k, w in gear.pack(g, gi) if w & 0x1ff == item), None)
    if k is None:
        return False
    n0 = sum(1 for _, w in gear.pack(g, ri) if w & 0x1ff == item)
    tavern_items(g, from_pos)
    ui.move_cursor(g, ITEM_CUR, ROW_GIVE, 'down', 'up', what='Give Items')
    ui.confirm_until(g, lambda: g.u8(GIVE_STATE) == 5, limit, 'Give Items')
    g.step(10)
    ui.move_cursor(g, GIVE_TARGET, to_pos, 'right', 'left', wrap=6, what='give to')
    ui.confirm_until(g, lambda: g.u8(GIVE_STATE) == 15, limit, 'give to')
    g.step(10)
    ui.move_cursor(g, LIST_CUR, k, 'down', 'up', wrap=len(gear.pack(g, gi)), what='give which')
    ui.press_until(g, 'circle', lambda: sum(1 for _, w in gear.pack(g, ri) if w & 0x1ff == item) > n0,
                   limit, 'give')
    tavern_leave_items(g)
    return True


def tavern_equip(g, pos, prefer=(), unleash=(), limit=600):
    """Tavern Inspect > Equip Items for the member at pos (JOUKA equip_menu 0x800ccc94),
    with gear's choices, `prefer` put on, and Yes to "Unleash its special power?" for the
    ids in `unleash`. Returns gear._equip_prompts' dict."""
    ri = town.town_slots(g)[pos]
    before = dict(gear.pack(g, ri))
    tavern_items(g, pos)
    ui.move_cursor(g, ITEM_CUR, ROW_EQUIP, 'down', 'up', what='Equip Items')
    ui.confirm_until(g, lambda: g.u8(ITEM_STATE) != 5, limit, 'Equip Items')
    chosen = gear._equip_prompts(g, ri, before, lambda: g.u8(ITEM_STATE) == 10 + 5 * ROW_EQUIP,
                                 prefer=set(prefer), unleash=set(unleash))
    tavern_leave_items(g)
    return chosen


def to_boltac_r2(g, limit=600):
    """R2 at the tavern's menu: straight to Boltac's (tavern_main's shortcut, town_state
    0x14), never by the town bar, where town_main's ring check would start the audience."""
    ui.wait_until(g, lambda: town.facility_ready(g) and g.u8(town.TOWN_STATE) == 10, limit, 'tavern menu')
    ui.press_until(g, 'r2', lambda: g.u8(town.TOWN_STATE) == 20, limit, 'R2 to Boltac')
    ui.wait_until(g, lambda: town.facility_ready(g), limit, "Boltac's menu")
