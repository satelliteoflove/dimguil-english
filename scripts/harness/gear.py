"""Gear: identify, uncurse, sell and buy at Boltac's, and equip from camp (2026-10-14).

Data (game RAM and code, docs/re; not other Wizardry games):
  item_table  0x80052bf2 + id * 0x4c (G-records.md "Item record"): +2 category (0 weapon,
              1 armor, 2 shield, 3 helm, 4 gauntlets, 5 boots, 6 instrument, 7 other),
              +3 subtype, +4 flags04 (bits 0-2 Good/Neutral/Evil use it uncursed, 3 male,
              4 female, 5 two-handed, 6 main hand, 7 sub hand), +5 specials (bit 7 cursed
              kind), +0x12 price, +0x1c class mask, +0x1e race mask, +0x35 AC (signed,
              lower is better), +0x36 to-hit, +0x37-0x39 damage dice n, sides, bonus,
              +0x3a extra swings
  boltac_stock 0x8008a0b0, a byte per id (0 none, 0xff unlimited)
  pack words  Roster +0x20, ten u16 (G-records.md "Pack slots"): 0x1ff id, 0x0800 sub
              hand, 0x1000 main hand, 0x2000 equipped, 0x4000 identified, 0x8000 cursed
  restricted  JOUKA/HAZURE item_restricted: class bit, race bit, male needs flags04 bit 3,
              female bit 4; equip_curse_check: an item whose alignment bit leaves out the
              wearer's alignment (Roster +0x0a >> 6), or a cursed kind, goes on cursed
  Boltac's    E-town.md: identify and uncurse cost price / 2, uncursing destroys the item,
              sell pays price / 2 and refuses unidentified or cursed items, buy lists the
              items of the chosen subtype with stock, in id order (JOUKA boltac_buy
              0x800bb914, shop_state 0x14)
  equip       MAZE equip_menu 0x800daa1c: one prompt per slot (0x80079b7a: 0 main hand,
              1 off hand, 2 armor, 3 helm, 4 gauntlets, 5 boots, 6 accessory), skipped
              when there's no candidate; at a prompt 0x80079562 = 1 and 0x8007956c = 0xf,
              the candidates' pack indexes are u16s at 0x800905e0 (count 0x8007990c), the
              cursor 0x80079c60 is 0 for none and k for candidate k - 1; "Unleash its
              special power?" is 0x8007956c = 0x78 (cross is No)
"""
import json, os, struct
from harness import ui, town, camp
from harness.game import Stuck

ITEMS, STOCK = 0x80052bf2, 0x8008a0b0
SHOP_LAST = 0x132                       # the shop lists ids 1-0x132
EQUIPPED, IDENT, CURSED, MAIN_H, SUB_H = 0x2000, 0x4000, 0x8000, 0x1000, 0x0800

_names = {}
try:
    for r in json.load(open(os.path.expanduser(
            '~/Documents/bartoks-trading-post/data/items/dim/ps.json')))['records']:
        _names[r['no']] = r['name']['en']
except Exception:
    pass


def name(i):
    return _names.get(i, '#%d' % i)


def item(g, i):
    r = g.e.read(ITEMS + i * 0x4c, 0x4c)
    return dict(id=i, cat=r[2], sub=r[3], f04=r[4], spec=r[5],
                price=struct.unpack_from('<I', r, 0x12)[0],
                classes=struct.unpack_from('<H', r, 0x1c)[0],
                races=struct.unpack_from('<H', r, 0x1e)[0],
                ac=struct.unpack_from('<b', r, 0x35)[0], hit=struct.unpack_from('<b', r, 0x36)[0],
                n=r[0x37], s=r[0x38], b=struct.unpack_from('<b', r, 0x39)[0], swings=r[0x3a])


def pack(g, ri):
    """[(pack index, word)] of roster index ri's pack."""
    c = g.char(ri)
    words = struct.unpack_from('<10H', c['raw'], 0x20)
    return [(k, w) for k, w in enumerate(words) if w != 0xffff]


def usable(g, ri, it):
    """Equips without being refused or cursed."""
    c = g.char(ri)
    raw = c['raw']
    cls, female = raw[0x0b] & 0x7f, bool(raw[0x0b] & 0x80)
    if not it['classes'] & (1 << cls) or not it['races'] & (1 << (raw[0x0a] & 0x1f)):
        return False
    if (female and not it['f04'] & 0x10) or (not female and not it['f04'] & 0x08):
        return False
    return bool(it['f04'] & (1 << (raw[0x0a] >> 6))) and not it['spec'] & 0x80


def wscore(it):
    return (it['n'] * (it['s'] + 1) / 2 + it['b']) * (1 + it['swings']) + 2 * it['hit']


def ranged(it):
    return it['sub'] in (7, 8)


SLOT_OF_CAT = {1: 2, 3: 3, 4: 4, 5: 5}          # armor pieces: category -> equip slot


TWO_HAND_COST = 4          # a two-handed weapon gives up the off hand: about a shield's AC point


def score(it, slot):
    if slot == 0:
        return wscore(it) - (TWO_HAND_COST if it['f04'] & 0x20 else 0)
    if slot == 1:
        return -it['ac'] * 4 if it['cat'] == 2 else wscore(it) * 0.5
    return -it['ac']


def equipped(g, ri):
    """{slot: item} of what's on now (slot 6, accessories, isn't scored)."""
    out = {}
    for k, w in pack(g, ri):
        if not w & EQUIPPED:
            continue
        it = item(g, w & 0x1ff)
        if it['cat'] == 0:
            out[1 if w & SUB_H else 0] = it
        elif it['cat'] == 2:
            out[1] = it
        elif it['cat'] in SLOT_OF_CAT:
            out[SLOT_OF_CAT[it['cat']]] = it
        elif it['cat'] == 7:
            out[6] = it
    return out


def fits_slot(it, slot, main=None):
    if slot == 0:
        return it['cat'] == 0
    if slot == 1:
        return it['cat'] == 2 or it['cat'] == 0 and it['f04'] & 0x80
    return SLOT_OF_CAT.get(it['cat']) == slot


def better(g, ri, it, slot, cur):
    """Is it an upgrade over cur (None: nothing on) for roster index ri in slot? A weapon
    keeps the kind the member uses now (ranged or melee): a back-row member's bow is
    what lets them fight."""
    if not usable(g, ri, it) or not fits_slot(it, slot):
        return False
    if slot == 0 and cur is not None and ranged(cur) != ranged(it):
        return False
    if slot == 1:
        main = equipped(g, ri).get(0)
        if main is not None and main['f04'] & 0x20:
            return False
    return score(it, slot) > (score(cur, slot) if cur else 0)


# --- equip from camp ---

EQ_SLOT, EQ_PROMPT, EQ_STATE, EQ_COUNT = 0x80079b7a, 0x80079562, 0x8007956c, 0x8007990c
EQ_CANDS, EQ_CURSOR = 0x800905e0, 0x80079c60
ITEMS_CURSOR = 0x80079c5e        # Identify, Use, Give, Equip, Drop
ITEMS_EQUIP = 3


def choose(g, ri, slot, cands, before):
    """The candidate (pack index) to put on in `slot`, or None: the best identified one
    the member can wear uncursed; the accessory that was on before stays on."""
    words = dict(pack(g, ri))
    if slot == 6:
        return next((k for k in cands if before.get(k, 0) & EQUIPPED), None)
    best, bs = None, None
    for k in cands:
        w = words.get(k)
        if w is None:
            continue
        it = item(g, w & 0x1ff)
        if not (w & IDENT or before.get(k, 0) & EQUIPPED) or not usable(g, ri, it):
            continue
        if slot == 0:
            cur = next((item(g, before[j] & 0x1ff) for j in before
                        if before[j] & EQUIPPED and before[j] & MAIN_H), None)
            if cur is not None and ranged(cur) != ranged(it):
                continue
        sc = score(it, slot)
        if bs is None or sc > bs:
            best, bs = k, sc
    return best


def equip(g, slot_pos, log=None):
    """Camp > Inspect > member at party slot slot_pos > Items > Equip, answering every slot
    prompt with choose(). Returns {slot: chosen item id or None}."""
    ri = g.party_slots()[slot_pos]
    before = dict(pack(g, ri))
    camp.open_camp(g)
    ui.move_cursor(g, camp.ICON, 0, 'right', 'left', what='camp icon')
    ui.confirm_until(g, lambda: g.u8(camp.CAMP_STATE) == 10 and g.u8(camp.SUB) == 5, 300, 'Inspect')
    camp._pick_member(g, slot_pos, 'inspect')
    ui.confirm_until(g, lambda: g.u8(camp.SUB) == 15, 300, 'inspect member')
    ui.move_cursor(g, camp.MENU, 1, 'down', 'up', what='Items')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == 5 and g.u8(camp.SUB) != 15, 300, 'Items')
    ui.move_cursor(g, ITEMS_CURSOR, ITEMS_EQUIP, 'down', 'up', what='Equip')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == 0x19, 300, 'Equip')
    chosen = {}
    end = g.frame + 3000
    while g.u8(camp.SPELL_STATE) == 0x19:
        if g.frame > end:
            raise Stuck('equip', slot=g.u8(EQ_SLOT), st=g.u8(EQ_STATE))
        if g.u8(EQ_PROMPT) == 1 and g.u8(EQ_STATE) == 0xf:
            g.step(2)
            s = g.u8(EQ_SLOT)
            n = g.u8(EQ_COUNT)
            cands = [struct.unpack('<h', g.e.read(EQ_CANDS + 2 * j, 2))[0] for j in range(n)]
            k = choose(g, ri, s, cands, before)
            want = cands.index(k) + 1 if k is not None else 0
            chosen[s] = (before[k] & 0x1ff) if k is not None else None
            ui.move_cursor(g, EQ_CURSOR, want, 'down', 'up', wrap=n + 1, what='equip slot %d' % s)
            sig = (s, g.u8(EQ_STATE), g.u8(EQ_PROMPT))
            ui.press_until(g, 'circle', lambda: (g.u8(EQ_SLOT), g.u8(EQ_STATE), g.u8(EQ_PROMPT)) != sig
                           or g.u8(camp.SPELL_STATE) != 0x19, 120, 'equip pick')
            continue
        if g.u8(EQ_STATE) == 0x78:
            ui.press_until(g, 'cross', lambda: g.u8(EQ_STATE) != 0x78, 120, 'no special power')
            continue
        g.step()
    if log is not None:
        log.append((g.frame, 'equip', g.char(ri)['name'],
                    {s: name(i) if i else None for s, i in chosen.items()}))
    return chosen


def wants_equip(g, ri):
    """Something identified in the pack that beats what's on (or an empty slot that a
    usable piece could fill)."""
    on = equipped(g, ri)
    for k, w in pack(g, ri):
        if w & EQUIPPED or not w & IDENT:
            continue
        it = item(g, w & 0x1ff)
        for slot in (0, 1, 2, 3, 4, 5):
            if better(g, ri, it, slot, on.get(slot)):
                return True
    return False


def equip_party(g, log=None, on_int=None):
    """Equip each member who carries an upgrade. In camp in the maze."""
    n = 0
    for pos, ri in enumerate(g.party_slots()):
        if ri is None or g.char(ri)['status'] >= 0x20 or not wants_equip(g, ri):
            continue
        try:
            equip(g, pos, log)
            n += 1
        except Stuck as s:
            if s.what != 'camp interrupted' or on_int is None:
                raise
            on_int(g)
    if camp.in_camp(g):
        camp.close_camp(g)
    return n


# --- Boltac's ---

SERVICE = dict(uncurse=(2, 99, 109), identify=(3, 101, 108))   # trade list row, pick prompt, yes/no prompt
SVC_ITEM, SVC_YN, GATHER_YN = 0x80079c60, 0x80079c65, 0x80079c6b


BOLTAC_SCREEN = 0x80079738   # 15 "What will you do?", 35 identify, 5/6 "Who will do business?"
SHOP_STATE = 0x800797a4      # identify/uncurse: 5 the item list, 0x19 "Identify/Uncurse
                             # this item?" (yes/no SVC_YN), 0x23 "Gather gold?" (GATHER_YN)


def service(g, pos, k, which, limit=600):
    """Identify or uncurse pack index k of the member at town position pos (traced
    2026-10-14 with svc_probe.py: one press per screen, read from SHOP_STATE and the
    message flag, since the list's prompt isn't always captured again). Returns the
    outcome: 'done', 'poor' or 'refused'."""
    row, pick_p, yn_p = SERVICE[which]
    if not town._at_trade_menu(g):
        town.boltac_trade(g, pos)
    ri = town.town_slots(g)[pos]
    w0 = dict(pack(g, ri)).get(k)
    msg = lambda: g.u8(town.TOWN_MSG)
    ready = lambda st: (lambda: g.u8(SHOP_STATE) == st and msg() == 0)
    ui.move_cursor(g, town.LIST, row, 'down', 'up', what=which)
    ui.press_then_wait(g, 'circle', msg, lambda: ready(5)() and g.u8(BOLTAC_SCREEN) != 15,
                       limit, which)
    ui.move_cursor(g, SVC_ITEM, k, 'down', 'up', what='item')
    ui.press_then_wait(g, 'circle', lambda: (msg(), g.u8(SHOP_STATE)),
                       lambda: msg() == 0 and g.u8(SHOP_STATE) in (0x19, 15), limit, 'pick item')
    out = 'refused'
    if g.u8(SHOP_STATE) == 0x19:
        g.step(10)                      # the yes/no takes a press only once it's drawn
        ui.move_cursor(g, SVC_YN, 0, 'down', 'up', what='yes')
        # one press: the answer goes straight back to the item list, where a second
        # press would pick the next item
        ui.press_then_wait(g, 'circle', lambda: g.u8(SHOP_STATE),
                           lambda: msg() == 0 and g.u8(SHOP_STATE) in (5, 0x23), limit, 'pay')
        if dict(pack(g, ri)).get(k) != w0:
            out = 'done'
        else:
            out = 'poor'
            if g.u8(SHOP_STATE) == 0x23:
                g.step(10)
                ui.move_cursor(g, GATHER_YN, 1, 'down', 'up', what='gather no')
                ui.press_then_wait(g, 'circle', lambda: (msg(), g.u8(SHOP_STATE)),
                                   lambda: msg() == 0 and g.u8(SHOP_STATE) == 5, limit, 'gather no')
    elif g.u8(SHOP_STATE) == 15:
        # "Already identified." / "not cursed" with the item shown: a press returns
        ui.press_then_wait(g, 'circle', lambda: (msg(), g.u8(SHOP_STATE)), ready(5), limit, 'back')
    # one cross back to "What will you do?" (BOLTAC_SCREEN 15; its prompt isn't always
    # captured again)
    ui.press_then_wait(g, 'cross', msg, lambda: g.u8(BOLTAC_SCREEN) == 15 and msg() == 0,
                       limit, 'back to trade')
    return out


BUY_CAT, BUY_TYPE, BUY_ITEM, BUY_YN = 0x80079c60, 0x80079c65, 0x80079c64, 0x800795d5


def back_to_trade(g, limit=600):
    """Cross, one screen at a time, to "What will you do?" (BOLTAC_SCREEN 15)."""
    msg = lambda: g.u8(town.TOWN_MSG)
    for _ in range(6):
        if g.u8(BOLTAC_SCREEN) == 15 and msg() == 0:
            return
        s0 = (g.u8(SHOP_STATE), g.u8(BOLTAC_SCREEN))
        ui.press_then_wait(g, 'cross', lambda: (g.u8(SHOP_STATE), g.u8(BOLTAC_SCREEN)),
                           lambda: (g.u8(SHOP_STATE), g.u8(BOLTAC_SCREEN)) != s0, limit, 'back')
        ui.wait_until(g, lambda: msg() == 0 or g.u8(SHOP_STATE) == 25, limit, 'back settles')
        g.step(4)
    raise Stuck('back to trade', scr=g.u8(BOLTAC_SCREEN), st=g.u8(SHOP_STATE))


def buy(g, pos, i, limit=600):
    """Buy item id i for the member at town position pos, from the trade menu, by the buy
    screens' states (JOUKA boltac_buy: 5 categories, 15 types, 25 items; after a pick 30
    checks, 50/60 buys and prints, 65-70 wait, then 20/25 the list again; 35/40 "Gather
    gold?" (yes/no BUY_YN), 55 "They can't equip it. Buy anyway?"). Returns 'bought',
    'poor', 'full' or 'refused'."""
    it = item(g, i)
    cat, typ = shop_slot(it)
    lst = shop_list(g, it['sub'])
    if i not in lst:
        return 'refused'
    if not town._at_trade_menu(g):
        town.boltac_trade(g, pos)
    ri = town.town_slots(g)[pos]
    n0 = len(pack(g, ri))
    msg = lambda: g.u8(town.TOWN_MSG)
    at = lambda st: (lambda: g.u8(SHOP_STATE) == st and msg() == 0 and g.u8(BOLTAC_SCREEN) == 20)
    ui.move_cursor(g, town.LIST, 0, 'down', 'up', what='Buy')
    ui.press_then_wait(g, 'circle', msg, at(5), limit, 'Buy')
    ui.move_cursor(g, BUY_CAT, cat, 'down', 'up', what='category')
    ui.press_then_wait(g, 'circle', lambda: g.u8(SHOP_STATE), at(15), limit, 'category')
    ui.move_cursor(g, BUY_TYPE, typ, 'down', 'up', what='type')
    # the item list keeps the message flag up (traced 2026-10-14)
    ui.press_then_wait(g, 'circle', lambda: g.u8(SHOP_STATE), lambda: g.u8(SHOP_STATE) == 25,
                       limit, 'type')
    g.step(6)
    ui.move_cursor(g, BUY_ITEM, lst.index(i), 'down', 'up', what='item')
    # the list's state (25) is also where a purchase ends: press until it leaves it, then
    # wait for it to come back or for a yes/no
    ui.press_until(g, 'circle', lambda: g.u8(SHOP_STATE) != 25, 120, 'item')
    ui.wait_until(g, lambda: g.u8(SHOP_STATE) in (25, 15) or msg() == 0 and g.u8(SHOP_STATE) in (40, 55),
                  900, 'item (ready)')
    out = 'bought' if len(pack(g, ri)) > n0 else 'full' if n0 >= 10 else 'poor'
    if g.u8(SHOP_STATE) in (40, 55):
        out = 'refused' if g.u8(SHOP_STATE) == 55 else 'poor'
        g.step(10)
        ui.move_cursor(g, BUY_YN, 1, 'down', 'up', what='no')
        ui.press_until(g, 'circle', lambda: g.u8(SHOP_STATE) not in (40, 55), 120, 'no')
        ui.wait_until(g, lambda: g.u8(SHOP_STATE) in (25, 15), limit, 'no (ready)')
    back_to_trade(g)
    if out == 'bought':
        got = pack(g, ri)[-1][1] & 0x1ff
        if got != i:
            raise Stuck('bought the wrong item', want=i, got=got)
    return out


def shop_slot(it):
    """(category, type) of the buy menus for an item's subtype (boltac_buy shop_state 0x14)."""
    sub = it['sub']
    if sub <= 8:
        return 0, sub
    if sub <= 13:
        return 1, sub - 9
    if sub == 14:
        return 2, 0
    if sub <= 16:
        return 3, sub - 15
    if sub <= 19:
        return sub - 13, 0
    return 7, sub - 20


def shop_list(g, sub):
    return [i for i in range(1, SHOP_LAST + 1)
            if g.u8(STOCK + i) and g.u8(ITEMS + i * 0x4c + 3) == sub]


def gold(g):
    return sum(g.char(i)['gold'] for i in town.town_party(g))


def shop(g, log, reserve):
    """One visit to Boltac's after a trip: for each member, identify unknown items and
    uncurse cursed ones (cheapest first, each while it costs at most a quarter of the
    party's gold over `reserve`), sell identified weapons and armor nobody would wear,
    then buy, best gain per gold first, the upgrades the gold over `reserve` allows. The
    gold is pooled on the member being served first. Returns a list of what was done."""
    done = []
    slots = town.town_slots(g)
    members = [(pos, ri) for pos, ri in enumerate(slots) if ri is not None]

    def pool(pos):
        # Boltac's own Pool Gold didn't come up from its icon menu (2026-10-14); the
        # tavern's is what town_upkeep uses
        town.pool_gold(g, pos, 'tavern')
        town.to_town_bar(g)

    def trade_done():
        if town._at_trade_menu(g):
            town.boltac_leave(g)

    # identify and uncurse
    for pos, ri in members:
        todo = []
        for k, w in pack(g, ri):
            it = item(g, w & 0x1ff)
            if w & CURSED:
                todo.append((it['price'] // 2, k, 'uncurse', w))
            elif not w & IDENT and it['price']:
                todo.append((it['price'] // 2, k, 'identify', w))
        todo.sort()
        if not todo:
            continue
        trade_done()
        pool(pos)
        for cost, k, which, w in todo:
            if cost > max(0, gold(g) - reserve) / 4 and which == 'identify':
                continue
            if cost > g.char(ri)['gold']:
                continue
            r = service(g, pos, k, which)
            done.append((which, g.char(ri)['name'], name(w & 0x1ff), cost, r))
            log.append((g.frame, which, g.char(ri)['name'], name(w & 0x1ff), cost, r))
            if which == 'uncurse' and r == 'done':
                break                   # the pack has shifted: the rest next trip
        trade_done()
    # sell what nobody would wear
    for pos, ri in members:
        while True:
            sell = None
            for k, w in pack(g, ri):
                if w & (EQUIPPED | CURSED) or not w & IDENT:
                    continue
                it = item(g, w & 0x1ff)
                if it['cat'] > 5 or not it['price']:
                    continue
                # kept only if its owner would wear it: there's no Give between members
                # yet, and a piece kept for someone else sat in the pack while they bought
                # their own (2026-10-14: Kai's BUCKLER, Lu bought one)
                if any(better(g, ri, it, s, equipped(g, ri).get(s)) for s in range(6)):
                    continue
                sell = (k, w)
                break
            if sell is None:
                break
            r = town.boltac_sell(g, pos, sell[0])
            done.append(('sell', g.char(ri)['name'], name(sell[1] & 0x1ff), r['outcome']))
            log.append((g.frame, 'sell', g.char(ri)['name'], name(sell[1] & 0x1ff), r['outcome']))
            if r['outcome'] != 'sold':
                break
        trade_done()
    # buy
    offers = []
    for pos, ri in members:
        on = equipped(g, ri)
        for s in range(6):
            cur = on.get(s)
            for sub in range(0, 19):
                for i in shop_list(g, sub):
                    it = item(g, i)
                    if not it['price'] or not better(g, ri, it, s, cur):
                        continue
                    gain = score(it, s) - (score(cur, s) if cur else 0)
                    offers.append((gain / it['price'], gain, pos, ri, s, i))
    offers.sort(reverse=True)
    taken = set()
    for _, gain, pos, ri, s, i in offers:
        if (ri, s) in taken:
            continue
        it = item(g, i)
        if gold(g) - it['price'] < reserve or len(pack(g, ri)) >= 10 or not g.u8(STOCK + i):
            continue
        trade_done()
        pool(pos)
        r = buy(g, pos, i)
        done.append(('buy', g.char(ri)['name'], name(i), it['price'], r))
        log.append((g.frame, 'buy', g.char(ri)['name'], name(i), it['price'], r))
        if r == 'bought':
            taken.add((ri, s))
    trade_done()
    town.to_town_bar(g)
    return done
