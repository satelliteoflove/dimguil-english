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
_back = {}          # id -> whether the weapon reaches from the back row (site range 'front,back')
try:
    for r in json.load(open(os.path.expanduser(
            '~/Documents/bartoks-trading-post/data/items/dim/ps.json')))['records']:
        _names[r['no']] = r['name']['en']
        if ',' in (r.get('range_ja') or ''):
            _back[r['no']] = r['range_ja'].split(',')[1].strip() != '-'
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


def back_reach(it):
    """A weapon that reaches from the back row: weapon_reach 0x800c94a8 (D-battle.md
    "Reach") gives short weapons nothing from the back, long ones groups 1-2, bows all;
    each item's class is the site's range column ('2,-' short, '4,2', '4,4')."""
    return _back.get(it['id'], ranged(it))


def back_row(g, ri):
    """Whether roster index ri stands in the back row (positions 3-5), in the maze or in
    town."""
    for slots in (g.party_slots(), town.town_slots(g)):
        if ri in slots:
            return slots.index(ri) >= 3
    return False


def worth(g, ri, it, slot):
    """score() for roster index ri where they stand: a weapon that can't reach from the
    back row is worth nothing to a back-row member (b1v3d chapter 9: a level-14 Mage in
    the back row with two daggers)."""
    if it is None:
        return 0
    if slot in (0, 1) and it['cat'] == 0 and back_row(g, ri) and not back_reach(it):
        return 0
    if slot == 0 and it['f04'] & 0x20:
        # a two-handed weapon gives up what's in the off hand now (b1v3d chapter 9: a
        # 10-gold Rod for a back-row Thief cost him his Shield of Defense)
        off = equipped(g, ri).get(1)
        lost = worth(g, ri, off, 1) if off is not None and off['id'] != it['id'] else 0
        return wscore(it) - max(TWO_HAND_COST, lost)
    return score(it, slot)


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


CLOAK = 22                 # subtype of the cloaks (Shadow, Night, Darkness, Cape of Hide): AC
                           # pieces any class wears in the accessory slot (G-records.md subtypes)


def cloak(it):
    return it['cat'] == 7 and it['sub'] == CLOAK


def fits_slot(it, slot, main=None):
    if slot == 6:
        return cloak(it)
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
    if slot == 6 and cur is not None and not cloak(cur):
        return False                # a ring or amulet that's on stays on (choose)
    if slot == 1:
        main = equipped(g, ri).get(0)
        if main is not None and main['f04'] & 0x20:
            return False
    return worth(g, ri, it, slot) > worth(g, ri, cur, slot)


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
        # the accessory slot: a cloak by AC (b1v3b chapter 4, 2026-10-14: two spare Shadow
        # Cloaks filled the Bishop's pack); anything else that was on stays on
        on = next((k for k in cands if before.get(k, 0) & EQUIPPED), None)
        if on is not None and not cloak(item(g, words.get(on, before[on]) & 0x1ff)):
            return on
        best, bs = on, score(item(g, before[on] & 0x1ff), 6) if on is not None else 0
        for k in cands:
            w = words.get(k)
            if w is None or not w & IDENT:
                continue
            it = item(g, w & 0x1ff)
            if cloak(it) and usable(g, ri, it) and score(it, 6) > bs:
                best, bs = k, score(it, 6)
        return best
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
        sc = worth(g, ri, it, slot)
        if bs is None or sc > bs:
            best, bs = k, sc
    return best


def items_menu(g, slot_pos):
    """Camp > Inspect > the member at party slot slot_pos > Items (Identify, Use, Give,
    Equip, Drop; camp_spell_state 5)."""
    camp.open_camp(g)
    ui.move_cursor(g, camp.ICON, 0, 'right', 'left', what='camp icon')
    ui.confirm_until(g, lambda: g.u8(camp.CAMP_STATE) == 10 and g.u8(camp.SUB) == 5, 300, 'Inspect')
    camp._pick_member(g, slot_pos, 'inspect')
    ui.confirm_until(g, lambda: g.u8(camp.SUB) == 15, 300, 'inspect member')
    ui.move_cursor(g, camp.MENU, 1, 'down', 'up', what='Items')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == 5 and g.u8(camp.SUB) != 15, 300, 'Items')


def equip(g, slot_pos, log=None):
    """Camp > Inspect > member at party slot slot_pos > Items > Equip, answering every slot
    prompt with choose(). Returns {slot: chosen item id or None}."""
    ri = g.party_slots()[slot_pos]
    before = dict(pack(g, ri))
    items_menu(g, slot_pos)
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
        for slot in (0, 1, 2, 3, 4, 5, 6):
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


# --- the Bishop's Identify and Give, in camp (Chris, 2026-10-14) ---
# MAZE camp_items_menu 0x800d579c: camp_spell_state 0x800799e6 = 10 Identify, 20 Give.
# camp_identify 0x800d5f24 (state 0x800799e7): 15 the list (cursor 0x80079c60, count
# 0x8007990c); a press rolls (0x14), then 0x2d identified, 0x19 failed, 0x1e/0x23/0x28
# touched (afraid; a cursed kind is put on cursed), each a message (0x80079565 = 1) that
# a press clears, then the list again; an afraid Bishop is put back on the Items menu.
# Chance (level - item +0x20 + 1) x 20, held to 5-75; on a miss a Bishop of at least
# twice the item's level just fails (exactly twice: the roll repeats until it passes),
# below that (95 - chance)/4 % of misses touch it. Traced 2026-10-14 (camp_probe.py).
# camp_give 0x800de578 (state 0x80079569): 5 "Give an item to whom?" (receiver
# camp_target 0x80079948 = party slot, right/left), circle -> 15 the giver's list
# (cursor 0x80079c60), circle gives into the receiver's first free slot; an equipped or
# cursed item gets a message (0x80079565); a full receiver asks for a swap (0x19).
ID_STATE, GIVE_STATE, CAMP_TARGET, CAMP_MSG, ITEM_CUR, LIST_COUNT = (
    0x800799e7, 0x80079569, 0x80079948, 0x80079565, 0x80079c60, 0x8007990c)
ITEMS_IDENTIFY, ITEMS_GIVE = 0, 2
BISHOP = 11
ID_RISKY_MIN = 55          # past ID_MIN_TRIES, a risky try needs this chance or more
ID_TRIES = 6               # tries per item per camp
ID_MIN_TRIES = 5           # the Bishop's tries at an item before the shop may (Chris, 2026-10-14)
TRIED = {}                 # item word -> the Bishop's tries at it, kept across town visits
TRIED_VISIT = {}           # item word -> risky tries past ID_MIN_TRIES since the last town visit
BLOCKED = set()            # unknowns left outside the Bishop's pack after camp (logs only)


def id_level(g, i):
    return g.u8(ITEMS + i * 0x4c + 0x20)


def id_odds(level, idl):
    """(chance, safe): the Bishop's chance and whether a miss is harmless."""
    return min(75, max(5, (level - idl + 1) * 20)), level >= 2 * idl


def bishops(g):
    """Party slots of Bishops who can identify now (not afraid, nothing worse)."""
    out = []
    for pos, ri in enumerate(g.party_slots()):
        if ri is not None:
            c = g.char(ri)
            if c['cls'] == BISHOP and c['status'] & ~0x04 == 0:
                out.append(pos)
    return out


RESERVE_PER_LEVEL = 500    # gold kept back per level of the highest member: two raises from
                           # death (temple_heal 0x800c95f0: dead = level x 250, ashes x 500)


def spare_gold(g, members):
    """The gold of roster indexes `members` over the raise reserve."""
    if not members:
        return 0
    top = max(g.char(ri)['level'] for ri in members)
    return sum(g.char(ri)['gold'] for ri in members) - RESERVE_PER_LEVEL * top


def bishop_can(g, bpos, w):
    """Whether the Bishop at bpos should try unidentified word w in camp. The Bishop tries
    every unknown first, ID_MIN_TRIES times at least, risks included (Chris, 2026-10-14):
    below twice the item's level a miss touches it at (95 - chance) / 4 percent (afraid,
    and a cursed kind goes on cursed; camp_identify 0x800d5f24). Past those tries a safe
    item is tried on, a risky one only at ID_RISKY_MIN or better, three times a visit; the
    rest wait for the shop (shop()) or for the Bishop's next levels."""
    c = g.char(g.party_slots()[bpos])
    chance, safe = id_odds(c['level'], id_level(g, w & 0x1ff))
    if safe:
        return True
    if not RISKY:
        return False            # risky tries only in the setting-out camp (RISKY)
    if TRIED.get(w, 0) < ID_MIN_TRIES:
        return True
    return chance >= ID_RISKY_MIN and TRIED_VISIT.get(w, 0) < 3


# Risky tries happen only in the camp on the Grounds as a trip sets out
# (chapters.Run.ensure_maze), where a touch costs nothing: the party steps back into town,
# which clears fear (town_main, E-town.md), and Boltac's uncurses. In the maze a touch
# cost the trip: b1v3d goal_10, 2026-10-14, the Epee of Dismay went on Lu cursed and
# afraid, cure_in_camp spent a Madi on the fear, the points ran low after three fights
# and two members died on the walk home.
RISKY = False


def fallout(g):
    """Party members left afraid or wearing a cursed item, by name."""
    out = []
    for ri in g.party():
        c = g.char(ri)
        if c['status'] & 1 or any(w & CURSED and w & EQUIPPED for _, w in pack(g, ri)):
            out.append(c['name'])
    return out


def unknowns(g, ri):
    return [(k, w) for k, w in pack(g, ri) if not w & (IDENT | EQUIPPED | CURSED)]


def _back_to_list(g, state_addr, list_state, limit=300):
    """Clear a message (one press) and wait for the list again, or for the screen to go."""
    end = g.frame + limit
    while g.frame < end:
        if g.u8(state_addr) == list_state and g.u8(CAMP_MSG) == 0:
            g.step(4)
            if g.u8(state_addr) == list_state:
                return True
        if g.u8(camp.SPELL_STATE) not in (10, 20):
            return False
        if g.u8(CAMP_MSG):
            ui.press_until(g, 'circle', lambda: g.u8(CAMP_MSG) == 0, 60, 'camp message')
        g.step()
    raise Stuck('camp list', st=g.u8(state_addr), sp=g.u8(camp.SPELL_STATE))


def identify_in_camp(g, bpos, log=None):
    """The Bishop at bpos identifies what's unknown in their own pack (bishop_can).
    Returns [(item name, outcome)]."""
    ri = g.party_slots()[bpos]
    todo = [(k, w) for k, w in unknowns(g, ri) if bishop_can(g, bpos, w)]
    if not todo:
        return []
    # best odds first: a miss turns the Bishop afraid at (95 - chance) / 4 percent, which
    # ends their tries until town clears it, so a 5% item first can use up a camp
    # (idbf6_v6b: Uma afraid on the Shihou Shuriken's first or second try each visit)
    lv = g.char(ri)['level']
    todo.sort(key=lambda kw: (-id_odds(lv, id_level(g, kw[1] & 0x1ff))[1],
                              -id_odds(lv, id_level(g, kw[1] & 0x1ff))[0]))
    items_menu(g, bpos)
    ui.move_cursor(g, ITEMS_CURSOR, ITEMS_IDENTIFY, 'down', 'up', what='Identify')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == 10 and g.u8(ID_STATE) == 15, 300,
                     'Identify')
    g.step(8)
    out = []
    for _, w in todo:
        for t in range(ID_TRIES):
            words = dict(pack(g, ri))
            k = next((j for j, x in words.items() if x == w), None)
            if k is None or g.u8(camp.SPELL_STATE) != 10 or not bishop_can(g, bpos, w):
                break
            c = g.char(ri)
            chance, safe = id_odds(c['level'], id_level(g, w & 0x1ff))
            ui.move_cursor(g, ITEM_CUR, k, 'down', 'up', wrap=max(1, g.u8(LIST_COUNT)),
                           what='identify item')
            ui.press_until(g, 'circle', lambda: g.u8(ID_STATE) != 15, 60, 'identify')
            _back_to_list(g, ID_STATE, 15)
            nw = dict(pack(g, ri)).get(k, 0)
            afraid = bool(g.char(ri)['status'] & 1)
            res = ('identified' if nw & IDENT else 'cursed on' if nw & CURSED else
                   'afraid' if afraid else 'failed')
            if TRIED.get(w, 0) >= ID_MIN_TRIES and not safe:
                TRIED_VISIT[w] = TRIED_VISIT.get(w, 0) + 1
            TRIED[w] = TRIED.get(w, 0) + 1
            out.append((name(w & 0x1ff), res, chance, safe))
            if log is not None:
                log.append((g.frame, 'identify camp', c['name'], name(w & 0x1ff), chance, safe, res))
            if res != 'failed':
                break
        if g.u8(camp.SPELL_STATE) != 10 or g.char(ri)['status'] & 1:
            break
    camp.close_camp(g)
    return out


SWAP_CUR = 0x80079c65       # the receiver's list cursor when a full pack offers a swap


def give(g, from_pos, k, to_pos, log=None, swap=None):
    """Camp > Items > Give: pack index k of the member at party slot from_pos to the one
    at to_pos. Returns 'given', 'swapped', 'refused' (equipped, cursed) or 'full'. A full
    receiver offers a swap (camp_give 0x800de578: state 0x19, the receiver's list, cursor
    0x80079c65; circle on an item that isn't equipped or cursed trades the two, state
    0x1e): swap = the receiver's pack index to trade back, else it's left."""
    ri, rj = g.party_slots()[from_pos], g.party_slots()[to_pos]
    w = dict(pack(g, ri))[k]
    n0 = len(pack(g, rj))
    items_menu(g, from_pos)
    ui.move_cursor(g, ITEMS_CURSOR, ITEMS_GIVE, 'down', 'up', what='Give')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == 20 and g.u8(GIVE_STATE) == 5, 300, 'Give')
    ui.move_cursor(g, CAMP_TARGET, to_pos, 'right', 'left', wrap=6, what='give to')
    ui.press_until(g, 'circle', lambda: g.u8(GIVE_STATE) == 15, 120, 'give list')
    g.step(8)
    ui.move_cursor(g, ITEM_CUR, k, 'down', 'up', wrap=max(1, g.u8(LIST_COUNT)), what='give item')
    ui.press_until(g, 'circle', lambda: g.u8(GIVE_STATE) != 15 or g.u8(CAMP_MSG), 60, 'give')
    end = g.frame + 300
    while g.frame < end and len(pack(g, rj)) == n0 and not g.u8(CAMP_MSG) \
            and g.u8(GIVE_STATE) != 0x19:
        g.step()
    out = 'given' if len(pack(g, rj)) > n0 else 'full' if g.u8(GIVE_STATE) == 0x19 else 'refused'
    if out == 'full' and swap is not None:
        g.step(8)
        ui.move_cursor(g, SWAP_CUR, swap, 'down', 'up', wrap=10, what='swap item')
        ui.press_until(g, 'circle', lambda: g.u8(GIVE_STATE) != 0x19 or g.u8(CAMP_MSG), 60, 'swap')
        g.step(30)
        out = 'swapped' if dict(pack(g, rj)).get(swap) == w else 'refused'
    if log is not None:
        log.append((g.frame, 'give', g.char(ri)['name'], name(w & 0x1ff), g.char(rj)['name'], out))
    camp.close_camp(g)
    return out


def gear_value(g, rj, it, taken=None):
    """(gain, slot) of item `it` for roster index rj over what they wear (or what's
    already been planned for them in `taken`), or (0, None)."""
    on = equipped(g, rj)
    best = (0, None)
    for s in range(7):
        cur = (taken or {}).get((rj, s), on.get(s))
        if better(g, rj, it, s, cur):
            gain = worth(g, rj, it, s) - worth(g, rj, cur, s)
            if gain > best[0]:
                best = (gain, s)
    return best


def plan_gives(g, members):
    """[(holder ri, item word, receiver ri, slot, gain)]: each identified weapon or armor
    not worn goes to the member it helps most (the holder keeps it if that's them), best
    gains first, one piece per member and slot."""
    cands = []
    for ri in members:
        for k, w in pack(g, ri):
            if w & (EQUIPPED | CURSED) or not w & IDENT:
                continue
            it = item(g, w & 0x1ff)
            if it['cat'] > 5 and not cloak(it):
                continue
            for rj in members:
                if g.char(rj)['status'] >= 0x20:
                    continue
                gain, s = gear_value(g, rj, it)
                if s is not None:
                    cands.append((gain, ri, w, rj, s))
    cands.sort(key=lambda x: -x[0])
    taken, used, out = {}, set(), []
    for gain, ri, w, rj, s in cands:
        if (ri, w) in used or (rj, s) in taken:
            continue
        it = item(g, w & 0x1ff)
        cur = taken.get((rj, s))
        if cur is not None and worth(g, rj, it, s) <= worth(g, rj, cur, s):
            continue
        taken[(rj, s)] = it
        used.add((ri, w))
        out.append((ri, w, rj, s, gain))
    return out


def gather_for_bishop(g, bpos, log=None, room_keep=0):
    """Give unknown items from the others to the Bishop while their pack has room."""
    bri = g.party_slots()[bpos]
    n = 0
    # the best odds first (identify_in_camp), from whoever carries them
    blv = g.char(bri)['level']
    cands = []
    for pos, ri in enumerate(g.party_slots()):
        if ri is None or pos == bpos or g.char(ri)['status'] >= 0x20:
            continue
        for k, w in unknowns(g, ri):
            if bishop_can(g, bpos, w):
                ch, safe = id_odds(blv, id_level(g, w & 0x1ff))
                cands.append((-safe, -ch, pos, ri, w))
    cands.sort(key=lambda c: c[:3])
    for _, _, pos, ri, w in cands:
        if not bishop_can(g, bpos, w):
            continue
        if len(pack(g, bri)) >= 10 - room_keep:
            # the Bishop's pack is full: hand the giver something the Bishop can't
            # work on (an unknown beyond them, else a known piece not worn) first,
            # or trade it for the unknown when the giver's pack is full too
            # (an unknown with worse odds than this one goes too, the worst first)
            odds = lambda x: id_odds(blv, id_level(g, x & 0x1ff))[::-1]
            spare = [(j, x) for j, x in pack(g, bri) if not x & (EQUIPPED | CURSED)
                     and (x & IDENT or not bishop_can(g, bpos, x) or odds(x) < odds(w))]
            if not spare:
                break
            spare.sort(key=lambda jx: (2 if jx[1] & IDENT else 0 if not bishop_can(g, bpos, jx[1]) else 1,
                                       odds(jx[1]), jx[0]))
            if len(pack(g, ri)) >= 10:
                k = next((j for j, x in pack(g, ri) if x == w), None)
                if k is not None and give(g, pos, k, bpos, log, swap=spare[0][0]) == 'swapped':
                    n += 1
                continue
            if give(g, bpos, spare[0][0], pos, log) != 'given':
                continue
        k = next((j for j, x in pack(g, ri) if x == w), None)
        if k is None:
            continue
        if give(g, pos, k, bpos, log) == 'given':
            n += 1
    return n


def camp_loot(g, log=None, on_int=None):
    """In camp in the maze: the Bishop identifies (gathering the others' unknown items
    first), identified gear goes to whoever gains most (Give), then everyone equips
    upgrades. Cheap when there's nothing to do."""
    done = 0
    try:
        for _ in range(4):
            b = bishops(g)
            if not b:
                break
            bpos = b[0]
            bri = g.party_slots()[bpos]
            if not any(bishop_can(g, bpos, w) for ri in g.party() for k, w in unknowns(g, ri)):
                break
            gather_for_bishop(g, bpos, log)
            got = identify_in_camp(g, bpos, log)
            done += len(got)
            # what's still out of the Bishop's reach after gathering (b1v3d chapter 9,
            # 2026-10-14: six packs at 10/10, nine unknowns), for the logs: these wait for
            # the Bishop's tries too, the shop doesn't take them early (Chris, 5 tries first)
            BLOCKED.clear()
            BLOCKED.update(w for ri in g.party() if ri != bri for k, w in unknowns(g, ri)
                           if bishop_can(g, bpos, w))
            # the Bishop's own pack full of known things: pass them on before the next
            # round of gathering
            if not got:
                break
        members = [ri for ri in g.party()]
        for _ in range(12):
            plan = [p for p in plan_gives(g, members) if p[0] != p[2]]
            if not plan:
                break
            ri, w, rj, s, gain = plan[0]
            if len(pack(g, rj)) >= 10:
                members = [m for m in members if m != rj]
                continue
            k = next((j for j, x in pack(g, ri) if x == w), None)
            if give(g, g.party_slots().index(ri), k, g.party_slots().index(rj), log) != 'given':
                break
            done += 1
        done += equip_party(g, log, on_int=on_int)
    except Stuck as s:
        if s.what != 'camp interrupted' or on_int is None:
            raise
        on_int(g)
    if camp.in_camp(g):
        camp.close_camp(g)
    return done


def loot_work(g):
    """Whether camp_loot has anything to do (RAM only)."""
    b = bishops(g)
    if b and any(bishop_can(g, b[0], w) for ri in g.party() for k, w in unknowns(g, ri)):
        return True
    if any(p[0] != p[2] and len(pack(g, p[2])) < 10 for p in plan_gives(g, g.party())):
        return True
    return any(wants_equip(g, i) for i in g.party())


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


def bishop_will(g, members, w):
    """A Bishop in the party who still has camp work on w: it's safe for them (at least
    twice its level), or they haven't had their ID_MIN_TRIES at it yet."""
    for _, ri in members:
        c = g.char(ri)
        if c['cls'] == BISHOP and c['status'] < 0x20 and (
                id_odds(c['level'], id_level(g, w & 0x1ff))[1] or TRIED.get(w, 0) < ID_MIN_TRIES):
            return True
    return False


def kind_usable(g, ri, sub):
    """Whether any item of subtype `sub` (what an unidentified item's name shows) is one
    roster index ri's class may equip (Item +0x1c class mask)."""
    cls = g.char(ri)['raw'][0x0b] & 0x7f
    key = (cls, sub)
    if key not in _KIND:
        _KIND[key] = any(g.u8(ITEMS + i * 0x4c + 3) == sub and
                         g.u16(ITEMS + i * 0x4c + 0x1c) & (1 << cls) for i in range(1, 0x133))
    return _KIND[key]


_KIND = {}


def gold(g):
    return sum(g.char(i)['gold'] for i in town.town_party(g))


CHEAP_ID = 50              # a shop identify this cheap is paid to make room when packs are full
SURPLUS = 20               # gold over the reserve this many times a fee is truly surplus


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

    # identify and uncurse. The Bishop goes first (Chris, 2026-10-14: at least
    # ID_MIN_TRIES tries an item, risks included; bishop_can). The shop identifies only
    # what the Bishop has had those tries at, and only an item that matters (its kind is
    # one a member's class could use: a player sees the unidentified name, SWORD, ROBE)
    # while the fee fits in the gold over the reserve, or anything when the gold is truly
    # surplus (SURPLUS times the fee). Boltac's fee is price / 2, the same as the sale
    # price (boltac_identify 0x800c1de8, boltac_sell 0x800bf9ec), so the sell step below
    # gets back the fee of what nobody wears. Packs full to the last slot stop the Bishop
    # gathering and drop chest loot, so a cheap unknown (<= CHEAP_ID) is done then too.
    alive = [ri for _, ri in members if g.char(ri)['status'] < 0x20]
    bishop_full = any(g.char(ri)['cls'] == BISHOP and len(pack(g, ri)) >= 10 for ri in alive)
    budget = gold(g) - reserve
    cands = []
    for pos, ri in members:
        for k, w in pack(g, ri):
            it = item(g, w & 0x1ff)
            if w & CURSED:
                cands.append((0, it['price'] // 2, pos, ri, k, 'uncurse', w, False))
            elif not w & IDENT and it['price']:
                if bishop_will(g, members, w):
                    continue            # the Bishop's to do in camp first
                cheap = it['price'] // 2 <= CHEAP_ID and (len(pack(g, ri)) >= 10 or bishop_full)
                hope = any(kind_usable(g, rj, it['sub']) for rj in alive)
                cands.append((1 if hope else 2, it['price'] // 2, pos, ri, k, 'identify', w, cheap))
    cands.sort(key=lambda c: c[:2])
    todo = {}
    for rank, cost, pos, ri, k, which, w, cheap in cands:
        if which == 'identify' and not cheap and (
                cost > budget or rank == 2 and budget < SURPLUS * cost):
            continue
        budget -= cost
        todo.setdefault((pos, ri), []).append((cost, k, which, w))
    for (pos, ri), jobs in todo.items():
        trade_done()
        pool(pos)
        jobs.sort(key=lambda j: j[2] == 'uncurse')     # uncurse last: it shifts the pack
        for cost, k, which, w in jobs:
            if cost > g.char(ri)['gold']:
                continue
            k = next((j for j, x in pack(g, ri) if x == w), None)
            if k is None:
                continue
            r = service(g, pos, k, which)
            done.append((which, g.char(ri)['name'], name(w & 0x1ff), cost, r))
            log.append((g.frame, which, g.char(ri)['name'], name(w & 0x1ff), cost, r))
        trade_done()
    # sell what nobody would wear
    for pos, ri in members:
        while True:
            sell = None
            for k, w in pack(g, ri):
                if w & (EQUIPPED | CURSED) or not w & IDENT:
                    continue
                it = item(g, w & 0x1ff)
                if not it['price']:
                    continue
                if it['cat'] == 6:
                    # an instrument nobody here can equip (b1v3d: a Harp of Silence, 5,000
                    # gold to identify, carried for good)
                    if any(usable(g, rj, it) for _, rj in members if g.char(rj)['status'] < 0x20):
                        continue
                    sell = (k, w)
                    break
                if it['cat'] > 5 and not cloak(it):
                    continue
                # sold only if no member in the party can use it, or everyone who can
                # has better (Chris, 2026-10-14); camp Give passes it on otherwise
                if any(better(g, rj, it, s, equipped(g, rj).get(s))
                       for _, rj in members if g.char(rj)['status'] < 0x20 for s in range(7)):
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
    # what's already in a pack goes to its member in camp: count it as worn
    planned = {(rj, s): item(g, w & 0x1ff) for _, w, rj, s, _ in plan_gives(g, [ri for _, ri in members])}
    for pos, ri in members:
        on = dict(equipped(g, ri))
        on.update({s: it for (rj, s), it in planned.items() if rj == ri})
        for s in range(7):              # 6: cloaks (b1v3d chapter 8: 54,000 gold, three bare)
            cur = on.get(s)
            for sub in range(0, 19):
                for i in shop_list(g, sub):
                    it = item(g, i)
                    if not it['price'] or not better(g, ri, it, s, cur):
                        continue
                    gain = worth(g, ri, it, s) - worth(g, ri, cur, s)
                    offers.append((gain / it['price'], gain, pos, ri, s, i))
    offers.sort(reverse=True)
    # buying keeps back a raise from death for every member (temple_heal: level x 250),
    # more than the two raises identify keeps: a bought item's gold doesn't come back
    buy_reserve = max(reserve, sum(250 * g.char(ri)['level'] for _, ri in members))
    taken = set()
    for _, gain, pos, ri, s, i in offers:
        if (ri, s) in taken:
            continue
        it = item(g, i)
        if gold(g) - it['price'] < buy_reserve or len(pack(g, ri)) >= 10 or not g.u8(STOCK + i):
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
