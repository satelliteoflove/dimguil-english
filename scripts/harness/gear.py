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
    town (a backup equipping in town, _FRONT: no)."""
    if ri in _FRONT:
        return False
    for slots in (g.party_slots(), town.town_slots(g)):
        if ri in slots:
            return slots.index(ri) >= 3
    return False


AC_BY_HP = True            # agent 13 (strategy revision 7): AC weighs more on low-HP members
AC_HP_MAX = 2.0            # ... up to this many times over


def ac_weight(g, ri):
    """How much a point of AC is worth on roster index ri against the party's median
    member: median max HP / theirs, held to 1-AC_HP_MAX. The monster AI's column 1
    fights the reachable member with the least HP (monster_ai 0x800cffb0 ->
    monster_target_weakest), and a hit costs a low-HP member more of their life, so
    the back row's 45-HP mages at AC 5-6 get their armor before the 150-HP fighters."""
    if not AC_BY_HP:
        return 1.0
    for slots in (g.party_slots(), town.town_slots(g)):
        if ri in slots:
            hp = sorted(g.char(r)['max_hp'] for r in slots if r is not None)
            mine = g.char(ri)['max_hp']
            if not mine or not hp:
                return 1.0
            return max(1.0, min(AC_HP_MAX, hp[len(hp) // 2] / mine))
    return 1.0


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
        # and the best shield they could carry instead (agent 8, 2026-10-14: Earth in the
        # back row with a Rod, worth 7 against the flat 4, while a Bullwhip and a Target
        # Shield, 6.5 + 12, were in stock; with the Rod on, a shield was never offered)
        return wscore(it) - max(TWO_HAND_COST, lost, best_shield(g, ri))
    if slot >= 2 or slot == 1 and it['cat'] == 2:
        v = score(it, slot) * ac_weight(g, ri)          # armor and shields: AC by HP
        if g.char(ri)['cls'] in HEALER_CLASSES and cure_item(g, it['id'] | IDENT):
            v += CURE_WORN          # a Ring of Madi is only on the battle Use list worn
        return v
    return score(it, slot)


_SHIELDS = []
_BEST_SHIELD = {}


def best_shield(g, ri):
    """score() of the best shield roster index ri can use that's in a party pack
    (identified, not cursed) or in Boltac's stock; 0 if none."""
    key = (ri, g.frame)
    if key in _BEST_SHIELD:
        return _BEST_SHIELD[key]
    if not _SHIELDS:
        _SHIELDS.extend(i for i in range(1, SHOP_LAST + 1) if g.u8(ITEMS + i * 0x4c + 2) == 2)
    ids = {i for i in _SHIELDS if g.u8(STOCK + i)}
    for rj in (g.party() or town.town_party(g)):
        ids |= {w & 0x1ff for k, w in pack(g, rj) if w & IDENT and not w & CURSED
                and (rj == ri or not w & EQUIPPED)}
    best = 0
    for i in ids:
        sh = item(g, i)
        if sh['cat'] == 2 and usable(g, ri, sh):
            best = max(best, score(sh, 1))
    if len(_BEST_SHIELD) > 500:
        _BEST_SHIELD.clear()
    _BEST_SHIELD[key] = best
    return best


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


def choose(g, ri, slot, cands, before, prefer=None):
    """The candidate (pack index) to put on in `slot`, or None: the best identified one
    the member can wear uncursed; the accessory that was on before stays on. prefer: item
    ids put on whenever they're candidates (the gold set for the small door, chapter 14)."""
    words = dict(pack(g, ri))
    for k in cands:
        if prefer and words.get(k, 0) & 0x1ff in prefer:
            return k
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


def equip(g, slot_pos, log=None, none=False, prefer=None):
    """Camp > Inspect > member at party slot slot_pos > Items > Equip, answering every slot
    prompt with choose() (none: with nothing, to take everything off; prefer: choose's).
    Returns {slot: chosen item id or None}."""
    ri = g.party_slots()[slot_pos]
    before = dict(pack(g, ri))
    items_menu(g, slot_pos)
    ui.move_cursor(g, ITEMS_CURSOR, ITEMS_EQUIP, 'down', 'up', what='Equip')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == 0x19, 300, 'Equip')
    chosen = _equip_prompts(g, ri, before, lambda: g.u8(camp.SPELL_STATE) == 0x19, none, EQ_CURSOR,
                            prefer)
    if log is not None:
        log.append((g.frame, 'equip', g.char(ri)['name'],
                    {s: name(i) if i else None for s, i in chosen.items()}))
    return chosen


def _equip_prompts(g, ri, before, running, none=False, cursor=EQ_CURSOR, prefer=None):
    """Answer equip_menu's slot prompts (MAZE 0x800daa1c, HAZURE 0x800afa9c: the same
    fields but the cursor, camp's 0x80079c60 and the Edge's 0x80079c6b, each 0 for none
    and k for candidate k - 1) while running() holds."""
    chosen = {}
    end = g.frame + 3000
    while running():
        if g.frame > end:
            raise Stuck('equip', slot=g.u8(EQ_SLOT), st=g.u8(EQ_STATE))
        if g.u8(EQ_PROMPT) == 1 and g.u8(EQ_STATE) == 0xf:
            g.step(2)
            s = g.u8(EQ_SLOT)
            n = g.u8(EQ_COUNT)
            cands = [struct.unpack('<h', g.e.read(EQ_CANDS + 2 * j, 2))[0] for j in range(n)]
            k = None if none else choose(g, ri, s, cands, before, prefer)
            want = cands.index(k) + 1 if k is not None else 0
            chosen[s] = (before[k] & 0x1ff) if k is not None else None
            ui.move_cursor(g, cursor, want, 'down', 'up', wrap=n + 1, what='equip slot %d' % s)
            sig = (s, g.u8(EQ_STATE), g.u8(EQ_PROMPT))
            ui.press_until(g, 'circle', lambda: (g.u8(EQ_SLOT), g.u8(EQ_STATE), g.u8(EQ_PROMPT)) != sig
                           or not running(), 120, 'equip pick')
            continue
        if g.u8(EQ_STATE) == 0x78:
            ui.press_until(g, 'cross', lambda: g.u8(EQ_STATE) != 0x78, 120, 'no special power')
            continue
        if g.u8(CAMP_MSG) and g.u8(EQ_PROMPT) == 0:
            # "Cursed!": a slot held by a cursed item (a Bishop's touch put the Axe of Woe on
            # Lu cursed; n1v3c chapter 2, 2026-10-14, stuck here). The message waits for a
            # press, then the flow goes on to the next slot
            ui.press_until(g, 'circle', lambda: g.u8(CAMP_MSG) == 0, 120, 'equip message')
            continue
        g.step()
    return chosen


_FRONT = set()      # roster indexes worth() treats as front-row (a backup equipping in town)


def edge_equip(g, pos, log=None, stay=False):
    """At the Edge of Town: Prepare > Inspect the member at party position pos > Items >
    Equip (HAZURE equip_menu 0x800afa9c, camp's prompt fields but the cursor at
    0x80079c6b: EQ_STATE runs 5, 10, 15 at each slot's prompt, 20, ... 110, then 0; the
    Edge's state 0x800796e1 stays 45; mulerule probes, 2026-10-15). Used on a backup in town, scored as if it
    stood in the front row. Back at the town bar after (stay: at "Inspect whom?")."""
    ri = town.town_slots(g)[pos]
    before = dict(pack(g, ri))
    _edge_items(g, pos)
    ui.move_cursor(g, EDGE_ITEMS_CUR, ITEMS_EQUIP, 'down', 'up', what='edge Equip')
    _FRONT.add(ri)
    try:
        _edge_press(g, lambda: g.u8(EQ_STATE) != 0, 'edge Equip')
        chosen = _equip_prompts(g, ri, before, lambda: g.u8(EQ_STATE) != 0, cursor=EDGE_ITEM_CUR)
    finally:
        _FRONT.discard(ri)
    g.step(8)
    if log is not None:
        log.append((g.frame, 'equip edge', g.char(ri)['name'],
                    {s: name(i) if i else None for s, i in chosen.items()}))
    _edge_back(g) if stay else edge_leave(g)
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
ID_SAFE_TRIES = 40         # a safe item (no touch on a miss): tried until it's identified
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


ID_RISKY_FLOOR = 20        # risky tries each visit only from this chance up, or a risen one
LAST_CHANCE = {}           # item word -> the Bishop's chance at its last try
FAILED5 = set()            # item words whose ID_MIN_TRIES tries in a visit all failed


def risky_ok(chance, w):
    """A risky item worth the Bishop's tries this visit (main, 2026-10-14): a chance of
    ID_RISKY_FLOOR or better, or one that has risen since its last tries (the Bishop
    levelled). An item at the 5% floor waits: five tries there identify about 23% of the
    time and touch (fear, or a cursed kind put on) about 70% (idmeasure, chapters 1-2)."""
    return chance >= ID_RISKY_FLOOR or (w in LAST_CHANCE and chance > LAST_CHANCE[w])


def bishop_can(g, bpos, w):
    """Whether the Bishop at bpos should try unidentified word w in camp. A safe item (the
    Bishop at least twice its level: a miss does nothing) any time; a risky one only in the
    setting-out camp (RISKY), ID_MIN_TRIES tries a visit, when risky_ok (below twice the
    item's level a miss touches it at (95 - chance) / 4 percent: afraid, and a cursed kind
    goes on cursed; camp_identify 0x800d5f24). The rest wait for the Bishop's levels, or
    for the shop (shop(): a likely upgrade, gold allowing)."""
    c = g.char(g.party_slots()[bpos])
    chance, safe = id_odds(c['level'], id_level(g, w & 0x1ff))
    if safe:
        return True
    if not RISKY:
        return False            # risky tries only in the setting-out camp (RISKY)
    return TRIED_VISIT.get(w, 0) < ID_MIN_TRIES and risky_ok(chance, w)


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
    # an item not tried yet before one that has been (main, 2026-10-14: three Round
    # Shield-1s and a Leather of Loss rode two chapters with no try)
    todo.sort(key=lambda kw: (-id_odds(lv, id_level(g, kw[1] & 0x1ff))[1], TRIED.get(kw[1], 0) > 0,
                              -id_odds(lv, id_level(g, kw[1] & 0x1ff))[0]))
    items_menu(g, bpos)
    ui.move_cursor(g, ITEMS_CURSOR, ITEMS_IDENTIFY, 'down', 'up', what='Identify')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == 10 and g.u8(ID_STATE) == 15, 300,
                     'Identify')
    g.step(8)
    out = []
    for _, w in todo:
        # a safe try has no touch (camp_identify 0x800d5f24: only a miss below twice the
        # item's level touches it), so a safe item is tried until it's identified
        safe0 = id_odds(lv, id_level(g, w & 0x1ff))[1]
        for t in range(ID_SAFE_TRIES if safe0 else ID_TRIES):
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
            if not safe:
                TRIED_VISIT[w] = TRIED_VISIT.get(w, 0) + 1
                LAST_CHANCE[w] = chance
                FAILED5.discard(w)
                if res == 'failed' and TRIED_VISIT[w] >= ID_MIN_TRIES:
                    FAILED5.add(w)
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


def plan_gives(g, members, to=None):
    """[(holder ri, item word, receiver ri, slot, gain)]: each identified weapon or armor
    not worn goes to the member it helps most (the holder keeps it if that's them), best
    gains first, one piece per member and slot."""
    cands = []
    lv = sorted(g.char(x)['level'] for x in members)
    mid = lv[len(lv) // 2] if lv else 0
    for ri in members:
        for k, w in pack(g, ri):
            if w & (EQUIPPED | CURSED) or not w & IDENT:
                continue
            it = item(g, w & 0x1ff)
            if it['cat'] > 5 and not cloak(it):
                continue
            for rj in (to or members):
                if g.char(rj)['status'] >= 0x20:
                    continue
                if w & 0x1ff >= IMPORTANT_ID and g.char(rj)['level'] < mid:
                    # quest gear stays off the low-level fill-ins a rejoin takes out (n1v6u
                    # chapter 14: Venus gave the gold set to recruit Sam, level 1, who left
                    # wearing it)
                    continue
                gain, s = gear_value(g, rj, it)
                if s is not None:
                    cands.append((gain, ri, w, rj, s, k))
    cands.sort(key=lambda x: -x[0])
    taken, used, out = {}, set(), []
    # by pack index: two of the same item in one pack have the same word (n1v1, agent 8:
    # Eve's second Bullwhip, bought for Earth, counted as hers)
    for gain, ri, w, rj, s, k in cands:
        if (ri, k) in used or (rj, s) in taken:
            continue
        it = item(g, w & 0x1ff)
        cur = taken.get((rj, s))
        if cur is not None and worth(g, rj, it, s) <= worth(g, rj, cur, s):
            continue
        taken[(rj, s)] = it
        used.add((ri, k))
        out.append((ri, w, rj, s, gain))
    return out


# --- the Bishop's Identify at the Edge of Town (agent 13, strategy revision 1) ---
# Prepare for Adventure > Inspect Character > Items > Identify (HAZURE): edge_prepare
# 0x800a3be0, edge_inspect 0x800a3f50 (0x800796e1: 25 "Inspect whom?", party grid column
# 0x80079c5b and row 0x80079c5e; 35 its menu, cursor 0x80079c60, 0 Spells 1 Items; 45 the
# Items menu, cursor 0x80079c65: Identify Use Give Equip Drop), edge_identify_item
# 0x800a982c (0x800796e5: 15 the list, cursor 0x80079c6b over every pack slot; a press
# rolls, then a message 0x80079565 = 1, a press back to the list). Same odds as camp: (level
# - item level + 1) x 20 held to 5-75, none above the Bishop's level; but a miss never
# makes the Bishop afraid. Below twice the item's level (95 - chance) / 4 % of misses on a
# cursed kind put it on cursed (0xa000), which Boltac's uncurses right after. So the Bishop
# tries each item until it's known, before the shop, and the risky camp tries go.
EDGE_ID = True
EDGE_TRIES = 60            # tries an item a visit: 95% of 5% items identified
EDGE_STATE, EDGE_GX, EDGE_GY, EDGE_CUR, EDGE_ITEMS_CUR = (
    0x800796e1, 0x80079c5b, 0x80079c5e, 0x80079c60, 0x80079c65)
EDGE_ID_STATE, EDGE_ITEM_CUR, EDGE_MSG = 0x800796e5, 0x80079c6b, 0x80079565


def _edge_press(g, cond, what, wait=120):
    """One circle, then wait for cond; a press that didn't land is repeated (each screen
    takes a few frames to come up, and a second press there opens its first entry)."""
    for _ in range(4):
        g.tap('circle')
        f0 = g.frame
        while g.frame - f0 < wait:
            if cond():
                g.step(8)
                return
            g.step()
    raise Stuck(what, st=g.u8(EDGE_STATE), id=g.u8(EDGE_ID_STATE))


def will_try(g, bpos, w):
    """The Bishop at bpos will work on unknown w: in camp now (bishop_can), or with
    EDGE_ID at the Edge of Town on the next town visit (any item at or below their level),
    so camp gathers it into their pack."""
    if bishop_can(g, bpos, w):
        return True
    return EDGE_ID and id_level(g, w & 0x1ff) <= g.char(g.party_slots()[bpos])['level']


def edge_targets(g, ri):
    lv = g.char(ri)['level']
    return [(k, w) for k, w in unknowns(g, ri) if id_level(g, w & 0x1ff) <= lv]


def edge_identify(g, log=None):
    """In town: the Bishop (alive, not afraid) identifies the unknowns in their own pack at
    the Edge of Town, each until it's known or EDGE_TRIES. Back at the town bar after.
    Returns [(item name, outcome, tries)]."""
    if not EDGE_ID:
        return []
    slots = town.town_slots(g)
    pos = next((p for p, ri in enumerate(slots) if ri is not None and g.char(ri)['cls'] == BISHOP
                and g.char(ri)['status'] == 0), None)
    if pos is None or not edge_targets(g, slots[pos]):
        return []
    ri = slots[pos]
    town.enter(g, 'edge')
    ui.wait_until(g, lambda: g.u8(town.FAC_SUB) == 5 or g.u8(town.EDGE_CURSOR) == 0, 300, 'edge menu')
    ui.move_cursor(g, town.EDGE_CURSOR, 0, 'down', 'up', what='edge row')
    ui.move_cursor(g, town.EDGE_ICON, 3, 'right', 'left', what='Prepare icon')
    _edge_press(g, lambda: g.u8(EDGE_STATE) == 25, 'Prepare > Inspect')
    g.step(8)
    ui.move_cursor(g, EDGE_GY, pos // 3, 'down', 'up', what='inspect row')
    ui.move_cursor(g, EDGE_GX, pos % 3, 'right', 'left', what='inspect col')
    _edge_press(g, lambda: g.u8(EDGE_STATE) == 35, 'inspect the Bishop')
    g.step(8)
    ui.move_cursor(g, EDGE_CUR, 1, 'down', 'up', what='Items')
    _edge_press(g, lambda: g.u8(EDGE_STATE) == 45, 'Items')
    g.step(8)
    ui.move_cursor(g, EDGE_ITEMS_CUR, ITEMS_IDENTIFY, 'down', 'up', what='Identify')
    _edge_press(g, lambda: g.u8(EDGE_ID_STATE) == 15, 'Identify')
    g.step(8)
    c = g.char(ri)
    out = []
    for _, w in sorted(edge_targets(g, ri), key=lambda kw: -id_level(g, kw[1] & 0x1ff)):
        chance, safe = id_odds(c['level'], id_level(g, w & 0x1ff))
        res, t = 'failed', 0
        while t < EDGE_TRIES:
            k = next((j for j, x in pack(g, ri) if x == w), None)
            if k is None:
                break
            ui.move_cursor(g, EDGE_ITEM_CUR, k, 'down', 'up', wrap=max(1, g.u8(LIST_COUNT)),
                           what='edge identify item')
            ui.press_until(g, 'circle', lambda: g.u8(EDGE_ID_STATE) != 15, 60, 'edge identify')
            t += 1
            ui.wait_until(g, lambda: g.u8(EDGE_MSG) or g.u8(EDGE_ID_STATE) == 15, 120, 'edge result')
            ui.press_until(g, 'circle', lambda: g.u8(EDGE_ID_STATE) == 15 and not g.u8(EDGE_MSG), 120,
                           'edge result away')
            g.step(4)
            nw = dict(pack(g, ri)).get(k, 0)
            res = 'identified' if nw & IDENT else 'cursed on' if nw & CURSED else 'failed'
            if res != 'failed':
                break
        TRIED[w] = TRIED.get(w, 0) + t
        out.append((name(w & 0x1ff), res, t))
        if log is not None:
            log.append((g.frame, 'identify edge', c['name'], name(w & 0x1ff), chance, safe, res, t))
    edge_leave(g)
    return out


def edge_leave(g, limit=900):
    """Back out of the Edge of Town's Prepare screens to the town bar (Back to Town)."""
    f0 = g.frame
    while g.overlay() == 'HAZURE' and g.u8(town.FAC_SUB) != 5:
        if g.frame - f0 > limit:
            raise Stuck('edge back out', st=g.u8(EDGE_STATE), sub=g.u8(town.FAC_SUB))
        g.tap('cross')
        g.step(20)
    if g.overlay() == 'HAZURE':
        ui.move_cursor(g, town.EDGE_CURSOR, 0, 'down', 'up', what='edge row')
        ui.move_cursor(g, town.EDGE_ICON, 7, 'right', 'left', wrap=8, what='Back to Town icon')
        ui.confirm_until(g, lambda: g.overlay() == 'JOUKA', limit, 'Back to Town')
    town.to_town_bar(g)


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
            if will_try(g, bpos, w):
                ch, safe = id_odds(blv, id_level(g, w & 0x1ff))
                cands.append((-safe, TRIED.get(w, 0) > 0, -ch, pos, ri, w))
    cands.sort(key=lambda c: c[:4])
    for _, _, _, pos, ri, w in cands:
        if not will_try(g, bpos, w):
            continue
        if len(pack(g, bri)) >= 10 - room_keep:
            # the Bishop's pack is full: hand the giver something the Bishop can't
            # work on (an unknown beyond them, else a known piece not worn) first,
            # or trade it for the unknown when the giver's pack is full too
            # (an unknown with worse odds than this one goes too, the worst first)
            odds = lambda x: id_odds(blv, id_level(g, x & 0x1ff))[::-1]
            spare = [(j, x) for j, x in pack(g, bri) if not x & (EQUIPPED | CURSED)
                     and (x & IDENT or not will_try(g, bpos, x) or odds(x) < odds(w))]
            if not spare:
                break
            spare.sort(key=lambda jx: (2 if jx[1] & IDENT else 0 if not will_try(g, bpos, jx[1]) else 1,
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


def swap_back(g, rj, w_in):
    """Pack index of what full receiver rj hands back in a Give trade: identified, not
    worn, not cursed, not a Latumofis, nothing rj gains from; what rj can't use first."""
    cands = []
    for j, x in pack(g, rj):
        if x & (EQUIPPED | CURSED) or not x & IDENT or x == w_in or x & 0x1ff == LATUMOFIS or cure_item(g, x):
            continue
        it = item(g, x & 0x1ff)
        if (it['cat'] <= 5 or cloak(it)) and gear_value(g, rj, it)[1] is not None:
            continue
        cands.append((usable(g, rj, it), it['price'], j))
    return min(cands)[2] if cands else None


ROOM_KEEP = 7       # make_room gives only to a pack with at most this many items


def room_move(g):
    """(from roster index, pack index, to roster index) to take an item out of a full
    pack, or None. n1v1/n1v6/n1v0 chapter 4 (agent 8, 2026-10-14): Earth's pack sat at
    10 (starting potions, a spare Sword of Slashing, an unknown), so Boltac's skipped
    him and camp Give couldn't reach him: five Shadow Cloaks bought, Earth without one.
    The item: unequipped, identified, not cursed, not a Latumofis (the potion holders),
    the ones the holder can't use first; to the emptiest pack."""
    members = [ri for ri in g.party() if g.char(ri)['status'] < 0x20]
    full = [ri for ri in members if len(pack(g, ri)) >= 10]
    if not full:
        return None
    to = min(members, key=lambda ri: len(pack(g, ri)))
    if len(pack(g, to)) > ROOM_KEEP:
        return None
    cands = []
    for ri in full:
        for k, w in pack(g, ri):
            if w & (EQUIPPED | CURSED) or not w & IDENT or w & 0x1ff == LATUMOFIS or cure_item(g, w):
                continue
            if w & 0x1ff >= IMPORTANT_ID:
                # quest items stay with their holder: the emptiest pack can be a recruit's
                # who leaves the party later (n1v3u, 2026-10-15: three gold pieces went to
                # Jo and Kai on a gold trip and left with them; chapter 14's crystal
                # failed six times on "gold piece missing")
                continue
            it = item(g, w & 0x1ff)
            cands.append((usable(g, ri, it) and it['cat'] <= 6, not usable(g, to, it), ri, k))
    if not cands:
        return None
    _, _, ri, k = min(cands)
    return ri, k, to


def make_room(g, log=None, most=4):
    n = 0
    for _ in range(most):
        mv = room_move(g)
        if not mv:
            break
        ri, k, rj = mv
        slots = g.party_slots()
        if give(g, slots.index(ri), k, slots.index(rj), log) != 'given':
            break
        n += 1
    return n


def throwable(g, w):
    """An item the full-pack drop picker can throw away without a question: unequipped,
    priced, and under the important ids (camp_drop's "This is an important item")."""
    i = w & 0x1ff
    return not w & (EQUIPPED | CURSED) and i < IMPORTANT_ID and item(g, i)['price'] > 0


def room_for_find(g, log=None):
    """Before a story item that may come with every pack full: a member whose full pack
    holds nothing throwable hands an unequipped item to the emptiest pack, or trades it
    for a throwable one. The game picks who drops, not the player (n1v0t chapter 11,
    2026-10-15: Uranus, three gold pieces and seven worn items, asked to drop for the
    boots; "This is an important item" for ever). Returns the gives made."""
    n = 0
    members = [ri for ri in g.party() if g.char(ri)['status'] < 0x20]
    for ri in members:
        p = pack(g, ri)
        if len(p) < 10 or any(throwable(g, w) for _, w in p):
            continue
        k = next((k for k, w in p if not w & (EQUIPPED | CURSED)), None)
        if k is None:
            continue
        others = [rj for rj in members if rj != ri]
        to = min(others, key=lambda rj: len(pack(g, rj)), default=None)
        swap = None
        if to is None:
            continue
        if len(pack(g, to)) >= 10:
            trade = [(rj, k2) for rj in others for k2, w2 in pack(g, rj) if throwable(g, w2)]
            if not trade:
                continue
            to, swap = trade[-1]
        slots = g.party_slots()
        if give(g, slots.index(ri), k, slots.index(to), log, swap=swap) in ('given', 'swapped'):
            n += 1
    return n


# --- confusion cures (main, 2026-10-14) ---
# Only Madi (spell_madi 0x800ae6e8) and Morfis (spell_morfis 0x800af20c) cure confusion in
# battle, and Boltac stocks no item that casts them but the 75,000 gold Staff of Curing
# (Potion of Madi 10,000, Ring of Madi 15,000, Golden Rod 30,000; items.txt). One that turns
# up is never sold, rides with the Priest or Bishop, and is Used on a confused member
# (battle.cure_item_choice).
CURE_SIDS = (36, 56)        # Madi, Morfis
HEALER_CLASSES = (2, 11)    # Priest, Bishop (town.CLASSES)
CURE_WORN = 3               # worth() of a worn cure item (not a weapon) to a Priest or Bishop


def cure_item(g, w):
    """An identified item whose battle spell (+0x1b) is Madi or Morfis."""
    bs = g.u8(ITEMS + (w & 0x1ff) * 0x4c + 0x1b)
    return bool(w & IDENT) and bs != 0xff and bs & 0x7f in CURE_SIDS


def cure_moves(g):
    """[(from roster index, pack index, to roster index)]: a cure item that isn't worn, in
    the pack of someone who isn't a Priest or Bishop, to the one with the most room."""
    healers = [ri for ri in g.party() if g.char(ri)['cls'] in HEALER_CLASSES
               and g.char(ri)['status'] < 0x20]
    if not healers:
        return []
    to = min(healers, key=lambda ri: len(pack(g, ri)))
    if len(pack(g, to)) >= 10:
        return []
    return [(ri, k, to) for ri in g.party() if ri not in healers
            for k, w in pack(g, ri) if not w & (EQUIPPED | CURSED) and cure_item(g, w)]


def place_cures(g, log=None):
    n = 0
    for _ in range(3):
        mv = cure_moves(g)
        if not mv:
            break
        ri, k, rj = mv[0]
        slots = g.party_slots()
        if give(g, slots.index(ri), k, slots.index(rj), log) != 'given':
            break
        n += 1
    return n


def spare(g, w, members):
    """Item word w is one Boltac's would take off the party: identified, not worn, cursed
    or a Madi/Morfis item, with a price, and an instrument no member can equip, or weapon,
    armor or cloak no member in `members` (roster indexes) can use or gains from (Chris,
    2026-10-14; camp Give passes it on otherwise)."""
    if w & (EQUIPPED | CURSED) or not w & IDENT or cure_item(g, w):
        return False
    it = item(g, w & 0x1ff)
    if not it['price']:
        return False
    alive = [rj for rj in members if g.char(rj)['status'] < 0x20]
    if it['cat'] == 6:
        # an instrument nobody here can equip (b1v3d: a Harp of Silence, 5,000 gold to
        # identify, carried for good)
        return not any(usable(g, rj, it) for rj in alive)
    if it['cat'] > 5 and not cloak(it):
        return False
    return not any(better(g, rj, it, s, equipped(g, rj).get(s)) for rj in alive for s in range(7))


# --- the mule (Chris, 2026-10-14) ---
# A player rarely sells a valuable item unless they must: a character who stays in town
# holds the spares. Valuable: Boltac pays VALUABLE_SELL or more (item +0x16), or it has a
# spell (+0x1b battle spell, the site's 使) or a special power (+0x0d use/equip effect, the
# site's SP, the game's "Unleash its special power?"). The on-hit bits (+0x05 bits 0-6,
# the site's 付: KO 5% on a 5 gold Anointed Mace) don't count. Such an item is sold only
# for gold the party really needs (chapter1.mule_sell).
# The trade runs at the Edge of Town (no maze trip): Prepare > Inspect a member > Items >
# Give, edge_give_item 0x800b3c6c (state 0x80079569): 5 "to whom?" (camp_target
# 0x80079948, a party position, right/left), circle -> 15 two lists side by side (column
# 0x80079c64: 0 the inspected member's pack, 1 the receiver's; row 0x80079c6b), circle
# moves the item under the cursor into the other pack's first free slot (0x14) or asks
# for a swap when that pack is full (0x19); a worn (0x2000) or cursed (0x8000) item gets
# a message (0x80079565). It opens only when the inspected member has an item (state 0
# returns at once on an empty pack), so the party member is inspected, not the mule.
# Roster members keep their packs out of the party: tavern_remove_member (JOUKA
# 0x800aa0a4, state 0x19) writes only the party record (0x8007e812 slot = 0xff and the
# parties table), never the roster (0x8007d708, 0xd0 a record, pack words at +0x20).
VALUABLE_SELL = 5000
MULE_NAME = 'Mule'
EDGE_COL = 0x80079c64


def valuable(g, w):
    r = g.e.read(ITEMS + (w & 0x1ff) * 0x4c, 0x4c)
    return struct.unpack_from('<I', r, 0x16)[0] >= VALUABLE_SELL or r[0x1b] != 0xff or r[0x0d] != 0


def battle_use(g, w):
    """An identified potion or scroll the battle code would use (battle.item_choice:
    attack, death or disabling spells), or a Madi/Morfis item."""
    if not w & IDENT:
        return False
    if cure_item(g, w):
        return True
    from harness import tactics
    a = ITEMS + (w & 0x1ff) * 0x4c
    bs = g.u8(a + 0x1b)
    return bs != 0xff and g.u8(a + 3) in (20, 21) and (
        bs & 0x7f in tactics.DAMAGE or bs & 0x7f in tactics.DEATH or bs & 0x7f in tactics.DISABLE)


def knows(g, members, sid):
    """A standing member of `members` can cast spell id sid (school * 21 + (level - 1) * 3
    + k, battle.known_spells)."""
    from harness import battle
    school, rest = divmod(sid, 21)
    if school > 3:
        return False
    return any(sid in battle.known_spells(g.char(ri)['raw'], school, rest // 3 + 1)
               for ri in members if g.char(ri)['status'] == 0)


def worth_keeping(g, w, members):
    """Not sold whatever nobody uses (Chris, 2026-10-15: he sold his Rings of Jewels,
    "basically useless except at the very early part of the game"). An unknown: valuable()
    (the item table gives its price, spell and power away). An identified item: only a
    special power (+0x0d) or a spell (+0x1b) no member of `members` can cast already
    (the Ring of Jewels' Dumapic is a level-1 Mage spell); the price alone keeps nothing."""
    if not w & IDENT:
        return valuable(g, w)
    r = g.e.read(ITEMS + (w & 0x1ff) * 0x4c, 0x4c)
    if r[0x0d]:
        return True
    return r[0x1b] != 0xff and not knows(g, members, r[0x1b] & 0x7f)


def sellable(g, w, members):
    """Boltac's would take it off the party: a spare (spare()), or an identified ring,
    amulet or other charm (category 7, not a cloak) not worn, that battle never casts
    and that isn't a potion, scroll or important item (party_keeps)."""
    if spare(g, w, members):
        return True
    if w & (EQUIPPED | CURSED) or not w & IDENT:
        return False
    it = item(g, w & 0x1ff)
    return it['cat'] == 7 and not cloak(it) and bool(it['price']) and not party_keeps(g, w)


def keeper(g, w, members):
    """A spare (Boltac's would take it) worth keeping: a backup holds it."""
    return sellable(g, w, members) and worth_keeping(g, w, members)


def mule(g):
    """Roster index of the mule, or None."""
    return next((i for i in range(g.roster_count()) if g.name(i) == MULE_NAME), None)


def sell_value(g, w):
    return g.u32(ITEMS + (w & 0x1ff) * 0x4c + 0x16)


def mule_use(g, w, members, taken=None):
    """(gain, roster index, why, slot) of the mule's item w for the party, the member it
    helps most (gear_value over what they wear or `taken` plans): an upgrade, else a
    battle item for the member with the most room; (0, None, None, None) if neither."""
    if not w & IDENT or w & CURSED:
        return (0, None, None, None)
    it = item(g, w & 0x1ff)
    alive = [rj for rj in members if g.char(rj)['status'] == 0]
    best = (0, None, None, None)
    if it['cat'] <= 6 or cloak(it):
        for rj in alive:
            gain, s = gear_value(g, rj, it, taken)
            if s is not None and gain > best[0]:
                best = (gain, rj, 'upgrade', s)
    if best[1] is None and battle_use(g, w) and alive:
        rj = min(alive, key=lambda x: len(pack(g, x)))
        best = (0, rj, 'battle', None)
    return best


# --- backups (Chris, 2026-10-15, from his own play) ---
# "If the item is very expensive and I can't identify it yet, then I have to leave it
# behind unless I have extra space. If the item is good enough but not as good as my
# current equipment, I'll usually leave it behind, preferably in a lower-level backup
# character." Everything else is sold. In his play test the party's spares went to Ace, a
# low-level standby Fighter, before setting out.
# So, each town visit after Boltac's (backup_plan, carried out by chapter1.backup_visit):
#   wear     a spare piece of gear (no member gains from it) that a standby gains at least
#            BACKUP_GAIN from goes to the standby it helps most (the lower level on a tie)
#            and is put on there at the Edge of Town (edge_equip): the standbys become
#            better stand-ins. Boltac's doesn't sell those (gear.shop).
#   keep     a spare worth keeping (worth_keeping: a spell the party can't cast or a
#            special power; an instrument a standby can play) is stored on a standby.
#            Anything else identified that nobody uses is sold, whatever its price
#            (Chris sold his Rings of Jewels).
#   room     when the party's packs have fewer than ROOM_MIN free slots: valuable unknowns
#            the Bishop can't try yet (above their level), then identified charms worth
#            keeping that the party never equips or casts in battle, the most valuable
#            first, are stored the same way until the room is back.
#   take     a standby's or the Mule's unworn item that's now an upgrade for a member
#            comes back (mule_use). While the room stays at ROOM_MIN or more, so do battle
#            items, the unknowns the Bishop can now try (to the Bishop) and a standby's
#            unworn leftovers nobody gains from (sold at the next visit).
# Storage goes to a standby with room past BACKUP_KEEP free slots (one already coming in
# first, then one who can use the item, then the most room), then the Mule if it exists,
# then a standby's reserve; only when none has room, to the Mule, made then (the overflow:
# standbys' packs fill with their own gear and a trip's leftovers, and valuables gather
# over eleven chapters). Potions, scrolls, items whose spell the battle code casts (attack,
# death, disabling, Madi/Morfis) and important items (no price, ids 310 on) stay with the
# party. A backup must be alive, in the tavern, and of an alignment that mixes with the
# party's (Good and Evil don't).
ROOM_MIN = 12           # free pack slots the party keeps for a trip's loot
BACKUP_KEEP = 2         # free slots a standby keeps for the loot of a trip it fills in on
BACKUP_GAIN = 1.0       # least gain (gear_value) worth handing a piece down for
IMPORTANT_ID = 310      # camp_drop 0x800e0a5c: ids 310 on are "an important item"
STORE_MAX = 10          # storage moves a visit, beyond the hand-downs


def mixes(g, ri, members):
    """Roster index ri may join a party of `members`: Good and Evil don't mix."""
    al = {g.char(m)['align'] for m in members}
    a = g.char(ri)['align']
    return not (a == 0 and 2 in al or a == 2 and 0 in al)


def backups(g, members):
    """The standbys a town visit can hand items to: alive, in the tavern, not the Mule,
    their alignment mixing with the party's; the lowest level first."""
    out = [i for i in town.tavern_candidates(g) if g.name(i) != MULE_NAME and mixes(g, i, members)]
    return sorted(out, key=lambda i: (g.char(i)['level'], i))


def party_keeps(g, w):
    """An item that rides with the party whatever the room: no price or an important id
    (the Tablet, the Jade Mask), a potion or scroll (subtypes 20, 21), a Madi/Morfis item,
    or an identified item whose spell battle.item_choice casts."""
    from harness import tactics
    i = w & 0x1ff
    it = item(g, i)
    if not it['price'] or i >= IMPORTANT_ID or it['sub'] in (20, 21) or cure_item(g, w):
        return True
    bs = g.u8(ITEMS + i * 0x4c + 0x1b)
    return bool(w & IDENT) and bs != 0xff and (
        bs & 0x7f in tactics.DAMAGE or bs & 0x7f in tactics.DEATH or bs & 0x7f in tactics.DISABLE)


def backup_gain(g, w, backs, taken=None):
    """(gain, backup ri, slot) of the standby a piece of gear helps most (gear_value over
    what they wear, or what `taken` already plans for them), at least BACKUP_GAIN; the
    lower level on a tie. (0, None, None) if none."""
    it = item(g, w & 0x1ff)
    if not w & IDENT or w & CURSED or (it['cat'] > 5 and not cloak(it)):
        return (0, None, None)
    best = (0, None, None)
    for b in backs:             # lowest level first: a tie stays with the first
        _FRONT.add(b)
        try:
            gain, s = gear_value(g, b, it, taken)
        finally:
            _FRONT.discard(b)
        if s is not None and gain >= BACKUP_GAIN and gain > best[0]:
            best = (gain, b, s)
    return best


def room(g, members):
    return sum(10 - len(pack(g, ri)) for ri in members if g.char(ri)['status'] == 0)


def bishop_level(g, members):
    return max([g.char(ri)['level'] for ri in members
                if g.char(ri)['cls'] == BISHOP and g.char(ri)['status'] == 0] or [0])


def backup_plan(g, members=None):
    """[(backup ri or None, member ri, 'put' | 'take', item word, why, value)]: what this
    town visit moves between the party and its backups (see above). None stands for the
    Mule when it hasn't been made yet and storage needs it. Plans only; RAM reads."""
    members = list(members or town.town_party(g))
    alive = [ri for ri in members if g.char(ri)['status'] == 0]
    if not alive:
        return []
    backs = backups(g, members)
    mi = mule(g)
    free = {ri: 10 - len(pack(g, ri)) for ri in alive}
    broom = {b: 10 - len(pack(g, b)) for b in backs}
    if mi is not None and mi not in members and g.char(mi)['status'] == 0 and mixes(g, mi, members):
        broom[mi] = 10 - len(pack(g, mi))
    elif mi is None and MULE_OK[0] and g.roster_count() < 20:
        broom[None] = 8             # a new mule: a Long Sword and Leather Armor of its own
    plan = []

    def move(b, ri, kind, w, why, v):
        plan.append((b, ri, kind, w, why, v))
        d = 1 if kind == 'put' else -1
        free[ri] += d
        broom[b] -= d

    # what's in a pack already goes to its member in camp: counted as worn (as gear.shop)
    taken = {(rj, s): item(g, w & 0x1ff) for _, w, rj, s, _ in plan_gives(g, alive)}
    # take: a backup's unworn item that's now an upgrade for a member (a battle item
    # comes back further down, only while the room allows)
    battle = []
    for b in [x for x in broom if x is not None]:
        for _, w in pack(g, b):
            if w & EQUIPPED:
                continue
            if w & 0x1ff >= IMPORTANT_ID:
                # a quest item a standby carries comes back first (n1v3u: the gold set)
                rj = max(alive, key=lambda x: free[x])
                if free[rj] > 0:
                    move(b, rj, 'take', w, 'quest', 1e6)
                continue
            gain, rj, why, s = mule_use(g, w, alive, taken)
            if rj is None or free[rj] <= 0:
                continue
            if why == 'battle':
                battle.append((b, w))
                continue
            if s is not None:
                taken[(rj, s)] = item(g, w & 0x1ff)
            move(b, rj, 'take', w, why, round(gain, 1))
    # wear: the party's spare gear to the standby it helps most
    btaken, store, crowd = {}, [], []
    blv = bishop_level(g, alive)
    for ri in alive:
        for _, w in pack(g, ri):
            if w & (EQUIPPED | CURSED) or party_keeps(g, w):
                continue
            v = sell_value(g, w)
            it = item(g, w & 0x1ff)
            if w & IDENT and spare(g, w, members):
                gain, b, s = backup_gain(g, w, [x for x in backs if broom[x] > 0], btaken)
                if b is not None:
                    btaken[(b, s)] = it
                    move(b, ri, 'put', w, 'wear', round(gain, 1))
                elif worth_keeping(g, w, alive) or it['cat'] == 6 and any(usable(g, x, it) for x in backs):
                    # (an instrument a standby Bard can play is gear a standby can use)
                    store.append((v, ri, w, 'keep'))
            elif w & IDENT and it['cat'] == 7 and not cloak(it) and worth_keeping(g, w, alive):
                crowd.append((1, -v, ri, w, 'room'))
            elif not w & IDENT and valuable(g, w) and id_level(g, w & 0x1ff) > blv:
                crowd.append((0, -v, ri, w, 'unknown'))

    def store_to(w):
        it = item(g, w & 0x1ff)
        cands = [b for b in backs if broom[b] > BACKUP_KEEP]
        if cands:
            # a backup already coming in first: each one in costs a tavern swap
            used = {p[0] for p in plan}
            return max(cands, key=lambda b: (b in used, usable(g, b, it), broom[b], -b))
        if mi is not None and mi in broom and broom[mi] > 0:
            return mi
        # a standby's reserve before a new Mule (making one costs a Training Grounds trip)
        cands = [b for b in backs if broom[b] > 0]
        if cands:
            used = {p[0] for p in plan}
            return max(cands, key=lambda b: (b in used, usable(g, b, it), broom[b], -b))
        if None in broom and broom[None] > 0:
            return None
        return False

    n = 0
    for v, ri, w, why in sorted(store, key=lambda x: -x[0]):
        b = store_to(w)
        if b is False or n >= STORE_MAX:
            break
        move(b, ri, 'put', w, why, v)
        n += 1
    short = sum(free.values()) < ROOM_MIN
    for _, negv, ri, w, why in sorted(crowd, key=lambda x: x[:2]):
        if sum(free.values()) >= ROOM_MIN or n >= STORE_MAX:
            break
        b = store_to(w)
        if b is False:
            break
        move(b, ri, 'put', w, why, -negv)
        n += 1
    # with room to spare: battle items, then the unknowns the Bishop can now try (to the
    # Bishop), then a standby's unworn leftovers come back
    if not short:
        for b, w in battle:
            rj = max(alive, key=lambda x: free[x])
            if free[rj] <= 0 or sum(free.values()) - 1 < ROOM_MIN:
                break
            move(b, rj, 'take', w, 'battle', 0)
    bish = next((ri for ri in alive if g.char(ri)['cls'] == BISHOP), None)
    if not short and bish is not None:
        for b in [x for x in broom if x is not None]:
            for _, w in pack(g, b):
                if w & (EQUIPPED | IDENT) or id_level(g, w & 0x1ff) > blv:
                    continue
                if free[bish] <= 0 or sum(free.values()) - 1 < ROOM_MIN:
                    break
                move(b, bish, 'take', w, 'identify', sell_value(g, w))
    # a standby's unworn leftovers nobody gains from (what a hand-down replaced, the
    # starting kit) come back to be sold at the next visit
    if not short:
        for b in [x for x in broom if x is not None]:
            for _, w in pack(g, b):
                if w & (EQUIPPED | CURSED) or not w & IDENT or party_keeps(g, w) \
                        or worth_keeping(g, w, alive) or any(p[3] == w and p[0] == b for p in plan):
                    continue
                it = item(g, w & 0x1ff)
                if not sellable(g, w, alive) or backup_gain(g, w, backs)[1] is not None \
                        or it['cat'] == 6 and any(usable(g, x, it) for x in backs):
                    continue
                rj = max(alive, key=lambda x: free[x])
                if free[rj] <= 0 or sum(free.values()) - 1 < ROOM_MIN:
                    break
                move(b, rj, 'take', w, 'sell', sell_value(g, w))
    return plan


MULE_OK = [True]        # chapter1.MULE: the Mule may be made for storage


def _edge_items(g, pos):
    """To the Items menu of the member at party position pos: from the town bar through
    Edge of Town > Prepare > Inspect (edge_identify's path), or straight from "Inspect
    whom?" (state 25) when a session is already there (_edge_back)."""
    if not (g.overlay() == 'HAZURE' and g.u8(EDGE_STATE) == 25):
        town.enter(g, 'edge')
        ui.wait_until(g, lambda: g.u8(town.FAC_SUB) == 5 or g.u8(town.EDGE_CURSOR) == 0, 300, 'edge menu')
        ui.move_cursor(g, town.EDGE_CURSOR, 0, 'down', 'up', what='edge row')
        ui.move_cursor(g, town.EDGE_ICON, 3, 'right', 'left', what='Prepare icon')
        _edge_press(g, lambda: g.u8(EDGE_STATE) == 25, 'Prepare > Inspect')
        g.step(8)
    ui.move_cursor(g, EDGE_GY, pos // 3, 'down', 'up', what='inspect row')
    ui.move_cursor(g, EDGE_GX, pos % 3, 'right', 'left', what='inspect col')
    _edge_press(g, lambda: g.u8(EDGE_STATE) == 35, 'inspect member')
    g.step(8)
    ui.move_cursor(g, EDGE_CUR, 1, 'down', 'up', what='Items')
    _edge_press(g, lambda: g.u8(EDGE_STATE) == 45, 'Items')
    g.step(8)


def _edge_back(g, limit=600):
    """Back to "Inspect whom?" (state 25) with cross, one screen a press (the Give lists
    -> to whom -> Items -> the member's menu -> 25; mulerule probe, 2026-10-15), for the
    next member in the same Edge of Town visit."""
    end = g.frame + limit
    while g.u8(EDGE_STATE) != 25:
        if g.frame > end or g.overlay() != 'HAZURE':
            raise Stuck('edge back to inspect', st=g.u8(EDGE_STATE), give=g.u8(GIVE_STATE))
        sig = (g.u8(EDGE_STATE), g.u8(GIVE_STATE), g.u8(EQ_STATE))
        g.tap('cross')
        f0 = g.frame
        while g.frame - f0 < 60 and (g.u8(EDGE_STATE), g.u8(GIVE_STATE), g.u8(EQ_STATE)) == sig:
            g.step()
        g.step(6)


def edge_trade(g, pos, mpos, moves, log=None, stay=False):
    """At the Edge of Town, between the member at party position pos and the backup (a
    standby or the Mule) at mpos: moves [('put', word, *note): member to backup, ('take',
    word, *note): backup to member], each logged ('backup put' / 'backup take', member,
    backup, item, outcome, *note). A move into a full pack is skipped. Back at the town
    bar after, or with stay at "Inspect whom?" for the next trade (_edge_back). Returns
    [(kind, name, out)]."""
    slots = town.town_slots(g)
    ri, mi = slots[pos], slots[mpos]
    out = []
    _edge_items(g, pos)
    ui.move_cursor(g, EDGE_ITEMS_CUR, ITEMS_GIVE, 'down', 'up', what='Give')
    _edge_press(g, lambda: g.u8(GIVE_STATE) == 5, 'edge Give')
    g.step(8)
    ui.move_cursor(g, CAMP_TARGET, mpos, 'right', 'left', wrap=6, what='give to the backup')
    _edge_press(g, lambda: g.u8(GIVE_STATE) == 15, 'edge give lists')
    g.step(8)
    for kind, w, *note in moves:
        src, dst, col = (ri, mi, 0) if kind == 'put' else (mi, ri, 1)
        k = next((j for j, x in pack(g, src) if x == w), None)
        res = 'gone' if k is None else 'full' if len(pack(g, dst)) >= 10 else None
        if res is None and g.u8(GIVE_STATE) != 15:
            res = 'closed'
        if res is None:
            n0 = len(pack(g, dst))
            ui.move_cursor(g, EDGE_COL, col, 'right', 'left', wrap=2, what='edge give column')
            ui.move_cursor(g, EDGE_ITEM_CUR, k, 'down', 'up', wrap=max(1, g.u8(LIST_COUNT)),
                           what='edge give item')
            ui.press_until(g, 'circle', lambda: g.u8(GIVE_STATE) != 15 or g.u8(EDGE_MSG), 60, 'edge give')
            ui.wait_until(g, lambda: len(pack(g, dst)) > n0 or g.u8(EDGE_MSG)
                          or g.u8(GIVE_STATE) in (0, 0x19), 180, 'edge give result')
            res = 'moved' if len(pack(g, dst)) > n0 else 'refused'
            if g.u8(EDGE_MSG) or g.u8(GIVE_STATE) == 0x19:
                ui.press_until(g, 'cross' if g.u8(GIVE_STATE) == 0x19 else 'circle',
                               lambda: not g.u8(EDGE_MSG) and g.u8(GIVE_STATE) in (0, 15), 180,
                               'edge give message')
            if res == 'moved':
                ui.wait_until(g, lambda: g.u8(GIVE_STATE) in (0, 15), 120, 'edge give back')
                g.step(8)
        out.append((kind, name(w & 0x1ff), res))
        if log is not None:
            log.append((g.frame, 'backup put' if kind == 'put' else 'backup take',
                        g.char(ri)['name'], g.char(mi)['name'], name(w & 0x1ff), res) + tuple(note))
    _edge_back(g) if stay else edge_leave(g)
    return out


def camp_loot(g, log=None, on_int=None):
    """In camp in the maze: the Bishop identifies (gathering the others' unknown items
    first), identified gear goes to whoever gains most (Give), then everyone equips
    upgrades. Cheap when there's nothing to do."""
    done = 0
    try:
        done += make_room(g, log)
        for _ in range(4):
            b = bishops(g)
            if not b:
                break
            bpos = b[0]
            bri = g.party_slots()[bpos]
            if not any(will_try(g, bpos, w) for ri in g.party() for k, w in unknowns(g, ri)):
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
            sw = None
            if len(pack(g, rj)) >= 10:
                # a full receiver trades back something they gain nothing from (agent 8,
                # 2026-10-14: n1v6 chapter 6, all six packs at 10, a Kabuto for Venus and
                # a Sword of Slashing for Uranus (+20) stuck in others' packs)
                sw = swap_back(g, rj, w)
                if sw is None:
                    members = [m for m in members if m != rj]
                    continue
            k = next((j for j, x in pack(g, ri) if x == w), None)
            if give(g, g.party_slots().index(ri), k, g.party_slots().index(rj), log,
                    swap=sw) not in ('given', 'swapped'):
                break
            done += 1
        done += equip_party(g, log, on_int=on_int)
        done += place_potions(g, log)
        done += place_cures(g, log)
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
    if any(p[0] != p[2] and (len(pack(g, p[2])) < 10 or swap_back(g, p[2], p[1]) is not None)
           for p in plan_gives(g, g.party())):
        return True
    return (any(wants_equip(g, i) for i in g.party()) or bool(potion_moves(g)) or bool(room_move(g))
            or bool(cure_moves(g)))


# --- potions (Chris, 2026-10-14) ---
# Two Potions of Latumofis ride on two members who aren't healers, restocked at Boltac's
# above the reserve, and used in camp on poison the party's spells can't cure. The shop
# sells a potion with 5 doses in its item_state byte (Roster +0x34 + slot; G-records.md);
# camp_use_item 0x800d7150 takes one per use and empties the slot at 0, and uses the dose
# even if the target wasn't poisoned (B-camp.md).
LATUMOFIS = 243
RESTOCK = []                  # (roster index, item id) of battle items used up (battle._items_after)
POTIONS_KEEP = 2
HEALERS = {2, 5, 6, 11}       # Priest, Lord, Valkyrie, Bishop: the classes with priest spells
USE_STATE = 0x800799e7        # camp_use_item: 5 the list (cursor USE_CUR), 0xe/0xf the target
USE_CUR = 0x80079c6b          # grid (column USE_COL 0-2, row USE_ROW 0-1: party slot row*3+col),
USE_COL, USE_ROW = 0x800796cc, 0x800796cd   # 0x14 the effect, 0x19/0x1e the message, 0 redraw
ITEMS_USE = 1
SPELL_USE = 15                # camp_spell_state while Use runs (camp_items_menu 0x800d579c)
POTION_LOG = []               # (what, member, doses left) for result.json; the run log has them too


def doses(g, ri, k):
    return g.char(ri)['raw'][0x34 + k]


def potions(g, ri):
    """[(pack index, doses)] of Latumofis potions in roster index ri's pack."""
    return [(k, doses(g, ri, k)) for k, w in pack(g, ri) if w & 0x1ff == LATUMOFIS]


def potion_holders(g, members):
    """The POTIONS_KEEP members meant to carry a potion: standing non-healers, those
    already carrying one first, then the most pack room; healers only if there aren't
    enough others."""
    ok = [ri for ri in members if ri is not None and g.char(ri)['status'] < 0x20]
    key = lambda ri: (g.char(ri)['cls'] in HEALERS, not potions(g, ri), len(pack(g, ri)))
    return sorted(ok, key=key)[:POTIONS_KEEP]


def potion_moves(g):
    """[(from roster index, pack index, to roster index)]: a potion carried by someone who
    isn't a holder (or a holder's second one) to a holder without one (camp Give)."""
    members = g.party()
    hold = potion_holders(g, members)
    need = [ri for ri in hold if not potions(g, ri) and len(pack(g, ri)) < 10]
    spare = []
    for ri in members:
        if g.char(ri)['status'] >= 0x20:
            continue
        p = potions(g, ri)
        spare += [(ri, k) for k, _ in (p if ri not in hold else p[1:])]
    return [(ri, k, rj) for (ri, k), rj in zip(spare, need)]


def place_potions(g, log=None):
    n = 0
    for _ in range(POTIONS_KEEP):
        mv = potion_moves(g)
        if not mv:
            break
        ri, k, rj = mv[0]
        slots = g.party_slots()
        if give(g, slots.index(ri), k, slots.index(rj), log) != 'given':
            break
        n += 1
    return n


def use_item(g, from_pos, k, to_pos, log=None):
    """Camp > Items > Use: pack index k of the member at party slot from_pos, on the one
    at to_pos (camp_use_item 0x800d7150; the effect is hard-coded by item id). Returns
    the target's status after."""
    ri, rj = g.party_slots()[from_pos], g.party_slots()[to_pos]
    w = dict(pack(g, ri))[k]
    d0, st0 = doses(g, ri, k), g.char(rj)['status']
    items_menu(g, from_pos)
    ui.move_cursor(g, ITEMS_CURSOR, ITEMS_USE, 'down', 'up', what='Use')
    ui.confirm_until(g, lambda: g.u8(camp.SPELL_STATE) == SPELL_USE and g.u8(USE_STATE) == 5,
                     300, 'Use')
    g.step(8)
    ui.move_cursor(g, USE_CUR, k, 'down', 'up', wrap=len(pack(g, ri)), what='use item')
    ui.press_until(g, 'circle', lambda: g.u8(USE_STATE) == 0xf, 120, 'use target')
    g.step(8)
    ui.move_cursor(g, USE_COL, to_pos % 3, 'right', 'left', wrap=3, what='use column')
    ui.move_cursor(g, USE_ROW, to_pos // 3, 'down', 'up', wrap=2, what='use row')
    ui.press_until(g, 'circle', lambda: g.u8(USE_STATE) != 0xf, 120, 'use on')
    end = g.frame + 600
    while g.frame < end:
        if g.u8(camp.SPELL_STATE) != SPELL_USE:
            break                       # the pack's last item went: back to the menu
        if g.u8(USE_STATE) == 5 and not g.u8(CAMP_MSG):
            break
        if g.u8(CAMP_MSG):
            ui.press_until(g, 'circle', lambda: g.u8(CAMP_MSG) == 0, 60, 'use message')
        g.step()
    else:
        raise Stuck('use item', st=g.u8(USE_STATE), sp=g.u8(camp.SPELL_STATE))
    left = sum(d for _, d in potions(g, ri)) if w & 0x1ff == LATUMOFIS else None
    st = g.char(rj)['status']
    if log is not None:
        log.append((g.frame, 'use item', g.char(ri)['name'], name(w & 0x1ff), g.char(rj)['name'],
                    st0, st, d0, left))
    camp.close_camp(g)
    return st


def potion_cure(g, log=None):
    """Latumofis potions on every poisoned member who isn't dead (after the spells: the
    caller's cure_in_camp has tried them). Returns the doses used."""
    n = 0
    for _ in range(8):
        slots = g.party_slots()
        sick = [t for t, ri in enumerate(slots) if ri is not None and
                g.char(ri)['status'] & 0x04 and not g.char(ri)['status'] & 0x380]
        have = [(d, t, k) for t, ri in enumerate(slots) if ri is not None and
                g.char(ri)['status'] < 0x20 for k, d in potions(g, ri)]
        if not sick or not have:
            break
        _, t, k = min(have)             # the emptiest potion first: it frees the slot
        tgt = slots[sick[0]]
        st = use_item(g, t, k, sick[0], log)
        n += 1
        POTION_LOG.append(('used', g.char(tgt)['name'], st))
        if st & 0x04:
            break                       # it didn't take: don't spend more
    return n


def potions_to_buy(g, members):
    """(roster index, count) of Latumofis potions to buy so POTIONS_KEEP holders carry one,
    counting spares that camp Give will pass on."""
    hold = potion_holders(g, members)
    need = [ri for ri in hold if not potions(g, ri)]
    spare = sum(len(potions(g, ri)) - (1 if ri in hold else 0)
                for ri in members if g.char(ri)['status'] < 0x20 and potions(g, ri))
    return need[spare:] if spare < len(need) else []


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
        ch, safe = id_odds(c['level'], id_level(g, w & 0x1ff))
        if c['cls'] == BISHOP and c['status'] < 0x20 and (
                safe or risky_ok(ch, w) and w not in FAILED5):
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
    party's gold over `reserve`), sell identified weapons and armor nobody would wear
    (spare) unless they're valuable or a standby would wear them (backup_plan), then buy, best gain per gold first, the upgrades the gold over `reserve` allows. The
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
    # sell what nobody would wear or use, unless it's worth keeping (worth_keeping: a
    # spell the party can't cast, a special power) or a backup takes it (backup_plan's
    # hand-downs and storage; Chris 2026-10-15)
    from collections import Counter
    handed = Counter((ri, w) for b, ri, kind, w, why, v in backup_plan(g, [ri for _, ri in members])
                     if kind == 'put')
    for pos, ri in members:
        keep = Counter({w: n for (rj, w), n in handed.items() if rj == ri})
        sells = []
        for k, w in pack(g, ri):
            mem = [rj for _, rj in members]
            if not sellable(g, w, mem) or worth_keeping(g, w, mem):
                continue
            if keep[w] > 0:
                keep[w] -= 1
                continue
            sells.append(w)
        for w in sells:
            k = next((j for j, x in pack(g, ri) if x == w), None)
            sell = None if k is None else (k, w)
            if sell is None:
                continue
            r = town.boltac_sell(g, pos, sell[0])
            done.append(('sell', g.char(ri)['name'], name(sell[1] & 0x1ff), r['outcome']))
            log.append((g.frame, 'sell', g.char(ri)['name'], name(sell[1] & 0x1ff), r['outcome']))
            if r['outcome'] != 'sold':
                break
        trade_done()
    # potions first (Chris, 2026-10-14): POTIONS_KEEP Latumofis on non-healers, above the
    # reserve like any purchase
    price = item(g, LATUMOFIS)['price']
    for ri in potions_to_buy(g, [ri for _, ri in members]):
        pos = slots.index(ri)
        if gold(g) - price < reserve or len(pack(g, ri)) >= 10 or not g.u8(STOCK + LATUMOFIS):
            continue
        trade_done()
        pool(pos)
        r = buy(g, pos, LATUMOFIS)
        done.append(('potion buy', g.char(ri)['name'], name(LATUMOFIS), price, r))
        log.append((g.frame, 'potion buy', g.char(ri)['name'], name(LATUMOFIS), price, r))
        POTION_LOG.append(('bought', g.char(ri)['name'], r))
    trade_done()
    # battle items used up since the last visit, bought back for their user when the shop
    # sells them, above the reserve like any purchase (Chris, 2026-10-14; battle.item_choice)
    for ri, i in list(RESTOCK):
        RESTOCK.remove((ri, i))
        if ri not in slots:
            continue
        pos = slots.index(ri)
        price = item(g, i)['price']
        if gold(g) - price < reserve or len(pack(g, ri)) >= 10 or not g.u8(STOCK + i):
            continue
        trade_done()
        pool(pos)
        r = buy(g, pos, i)
        done.append(('restock', g.char(ri)['name'], name(i), price, r))
        log.append((g.frame, 'restock', g.char(ri)['name'], name(i), price, r))
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
            for sub in list(range(0, 19)) + [CLOAK]:   # 22: cloaks (slot 6) were never offered
                for i in shop_list(g, sub):
                    it = item(g, i)
                    if not it['price'] or not better(g, ri, it, s, cur):
                        continue
                    gain = worth(g, ri, it, s) - worth(g, ri, cur, s)
                    offers.append((gain / it['price'], gain, pos, ri, s, i))
    # one offer per member and slot, the biggest gain (the cheaper on a tie): by gain per
    # gold alone a 10 gold Anointed Mace (+1, no reach from the back row) beat a 100 gold
    # Bullwhip (+7.5) for Earth (agent 8, 2026-10-14, n1v3 chapter 6)
    top = {}
    spend = gold(g) - reserve
    for o in offers:
        if item(g, o[5])['price'] > spend:
            continue                    # (the Staff of Curing, 75,000 gold, won every slot)
        key = (o[3], o[4])
        if key not in top or (o[1], -item(g, o[5])['price']) > (top[key][1], -item(g, top[key][5])['price']):
            top[key] = o
    offers = sorted(top.values(), reverse=True)
    # buying keeps back the same two raises at the top level as identify (`reserve`).
    # A raise for every member (6599867) kept 12,000 gold back at level 8: the n1 chains
    # ended chapter 1 with 7,000-8,000 gold, nothing bought, mages at AC 7-9 and a 10 gold
    # Anointed Mace on the shelf (agent 7, 2026-10-14)
    buy_reserve = reserve
    taken = set()
    for _, gain, pos, ri, s, i in offers:
        if (ri, s) in taken:
            continue
        it = item(g, i)
        if gold(g) - it['price'] < buy_reserve or not g.u8(STOCK + i):
            continue
        bpos, bri = pos, ri
        if len(pack(g, ri)) >= 10:
            # a full pack (Earth's, n1v1 chapter 6: starting potions): someone with room
            # who could wear it carries it, and camp Give passes it on
            room = [(len(pack(g, rj)), p, rj) for p, rj in members if rj != ri
                    and len(pack(g, rj)) < 10 and usable(g, rj, it) and g.char(rj)['status'] < 0x20]
            if not room:
                continue
            _, bpos, bri = min(room)
        trade_done()
        pool(bpos)
        r = buy(g, bpos, i)
        done.append(('buy', g.char(ri)['name'], name(i), it['price'], r))
        log.append((g.frame, 'buy', g.char(ri)['name'], name(i), it['price'], r)
                   + ((g.char(bri)['name'],) if bri != ri else ()))
        if r == 'bought':
            taken.add((ri, s))
    trade_done()
    town.to_town_bar(g)
    return done
