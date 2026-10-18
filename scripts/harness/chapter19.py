"""Walkthrough chapter 19, the ending, by the walkthrough's method (2026-10-17).

Plan: rips/harness/ch19/STATUS.md (its later sections: Chris's changes, the walkthrough's
method, the ring party, D1 settled: the story route). Source: data/walkthrough/dim/
19-ending.json, docs/re/postgame.md, docs/re/F-edge-save.md (creation), docs/re/ninja.md
(THIEVES DAGGER), and the code: JOUKA training_create 0x800af5d8, tavern_main 0x800a79d4
(its R2 shortcut), tavern_inspect 0x800aa444 with FUN_800cbddc (the status screen's menu),
equip_menu 0x800ccc94, inn_stay 0x800c5e34 with FUN_800c8b10 (one level a stay, when the EXP
is there), town_main 0x800a2198, king_ending 0x800a52cc, MAIN FUN_800124a8 (the soft reset).

From chapter 18's end (the main party titled, in town), a new untitled party wins a second
RING OF MEDIUM at the coffin, and the ring makes a level-5, age-18 female Elf Priest into
the Priestess without the King taking it.

What the probes found (rips/harness/ch19/probe, 2026-10-17, ch18's states):
- Creation: new_char (0x8008ff10) already holds the age at "Use this character?" (state
  105), so the age is rolled for: 18 is kept with Retrain declined, 15 with a bonus under
  10 is kept and retrained (+3 years, level 4); anything else is thrown away (p1).
- The soft reset: MAIN FUN_800124a8 resets when the held pad word is 0x90f (L2 R2 L1 R1
  SELECT START) and START is new. Held during the audience (town_state 45), the title's
  Continue comes back to the town bar with the ring in the holder's pack, nobody titled
  and the story flags as before, the party emptied into the tavern (p2). king_ending sets
  the title bits in RAM at camp_state 10, but the RAM save image Continue loads is rebuilt
  only after them (postgame.md), so the reset here comes at camp_state 5, before them.
- The tavern: Inspect (icon 2, 0x80079c1b 16 the pick, 20 the status screen) has
  Spellbook, Equip Items, Give Items, Drop Items, Sort Items (0x80079804 5, cursor
  0x80079c5e; a row runs at 10 + 5 x row). Give uses the camp's fields (0x80079569 5 the
  receiver 0x80079948, 15 the item 0x80079c60, one press gives one item). Equip runs
  equip_menu: at "Unleash its special power?" (state 0x78, Yes/No on 0x80079c60, No
  first) Yes on the ring set her six stats to 5/18/18/5/5/18 (p4). R2 at the tavern menu
  goes to Boltac's (town_state 20) without the town bar; Uncurse took 50,000 Gp from the
  trader and the ring was gone; the town bar after that started no audience.
- THIEVES DAGGER (Chris's watch-out): its effect 0x25 (become a Ninja) runs only through
  equip_menu's state 0x7d, after Yes at that same prompt (decomp lines 307-342, 392, 644);
  gear._equip_prompts answers No (cross) for everything but `unleash`, so the Thief can
  wield it and stays a Thief. The class is checked after outfit and logged.
- The Training Maze: the Edge of Town's icon 1 puts the party in camp on B1 (area 9) at
  E12 N9 (12, 14); triangle there goes back to town (p5), so maze.ENTRANCE[9].

Goals, each proved by RAM or a captured string:
  create       the five new records: the Priestess Luna (+0x0a & 0x3f == 1 Elf, +0x0b ==
               0x82 female Priest, +0x10 == 18), the Monk Pluto, the Priest Ceres, the
               Psionic Io (Neutral), the Thief Puck (Hobbit, Neutral).
  outfit       spares moved by tavern Give from the main party, Mars and the Mule (the
               Tablet to Io, Eve's WAND OF MYSTERY to Io, the GOLD GAUNTLETS and BOOTS to
               the Mule, a THIEVES DAGGER and the ROBINSWORD to Puck, an ANKH to Pluto,
               Latumofis potions), then the gold divided over Uranus, Eve and four of the
               ring party. Proof: each item in its receiver's pack, Puck still a Thief.
               Mars is the mule from here (gear.MULE_NAME).
  train_esc_NN escort trips (Uranus and Earth with the Mule, Pluto, Puck and Io) on the
               Underground (ESC_AREAS) until the trainees' median level is ESC_LEVEL.
  train_NN     the ring party alone (Jupiter, the Mule, Pluto | Puck, Ceres, Io), its floor
               by its median level (LADDER), until RING_LEVEL. Everyone else is on
               town.BENCH (never taken in as a standby).
  priestess_NN Training Maze B1 trips with Uranus, Dax and Venus as escorts (no Priest, so
               no camp Kadorto can age her); in town she stays at the Stables one night at a
               time only while a night raises her level, never past 5 (tm_town).
  priestess_l5 her level 5, EXP 4,396 or more, age 18, Elf female Priest, waiting in the
               tavern.
  lift_z, the_man, coffin
               chapter 18's goals with the ring party (no titled member).
  reset        the ring carried into town: the audience begins (town_state 45, SISETU 360
               captured), the soft reset at camp_state 5, Continue; proof: the ring in a
               ring-party pack in town, nobody of the ring party titled, the story flags
               unchanged. A holder down on arrival brings no audience (town_main moves the
               dead out first), so then there's nothing to reset: noted, and the temple
               raises the holder into the tavern.
  ring_on      in the tavern: the holder and the Priestess in a party, the ring given and
               equipped with Yes at "Unleash", the gold pooled on her, R2 to Boltac's and
               Uncurse; proof: her stats 5/18/18/5/5/18, level 5, age 18, the ring in no
               pack, no title, 50,000 Gp paid.
"""
import os, struct

from harness import chapter1, chapter18, chapters, gear, maze, nav, town, ui
from harness.game import Stuck

RING = 0x142
TABLET = 0x143
STORY = 0x80079b44
TOWN_STATE = 0x80079b18
CAMP_STATE = 0x80079669

# --- the people ---
# (name, race, sex, alignment, class); the Priestess is rolled for her age (priestess_age)
PRIESTESS = ('Luna', 'Elf', 'F', 'Good', 'Priest')
NEW = [('Pluto', 'Gnome', 'M', 'Neutral', 'Monk'),       # 12 bonus points over Gnome's base
       ('Ceres', 'Dwarf', 'M', 'Good', 'Priest'),        # 3 points; Dwarf VIT 12
       ('Io', 'Mook', 'M', 'Neutral', 'Psionic'),        # 10 points: Neutral or Evil only
       ('Puck', 'Hobbit', 'M', 'Neutral', 'Thief')]      # 1 point; no Good Thief exists
RING_PARTY = ['Jupiter', 'Mule', 'Pluto', 'Puck', 'Ceres', 'Io']   # front three, back three
ESCORT_PARTY = ['Uranus', 'Mule', 'Pluto', 'Puck', 'Io', 'Earth']
TRAINEES = ['Mule', 'Pluto', 'Puck', 'Io']
TM_PARTY = ['Uranus', 'Dax', 'Venus', 'Luna']
NEW_MULE = 'Mars'

# --- training ---
ESC_AREAS = (6, 7)              # Underground B2, B3 (chapters 3-4's floors)
ESC_LEVEL = 8                   # the trainees' median level the escorts stay for
ESC_MOST = 30
# the ring party's floor by its median level: chapters 3-17's floors in their order
LADDER = [(11, (6, 7)), (14, (20, 19)), (17, (24, 23)), (20, (29,)), (99, (36,))]
RING_LEVEL = 23                 # the ring party's median level before the coffin
RING_MOST = 120
TRAIN_AREAS = (36,)             # boss_training at the coffin (Area E B4, as chapter 18)
PUSH_AREAS = (29,)              # the train-after-running rule: Area C B3

# --- the Priestess ---
TM_AREA = 9                     # Training Maze B1
TM_FIGHTS = 8                   # fights a Training Maze trip
TM_MOST = 30
PRIESTESS_LEVEL = 5
L5_EXP = 4396                   # table 0 (Elf Priest): level 5
L6_EXP = 7326

# --- the ring trick ---
AUDIENCE_MOST = 3000            # frames from the triangle to the audience's first box
UNCURSE_FEE = 50000
RESET_HOLD = ('l1', 'l2', 'r1', 'r2', 'select')

INSPECT_ICON = 2                # the tavern's icons: Form Party, Remove Member, Inspect, ...
INSP_STATE = 0x80079c1b         # tavern_inspect: 16 the member pick, 20 the status screen
ITEM_STATE = 0x80079804         # FUN_800cbddc: 5 its menu (cursor 0x80079c5e), 10 + 5 x row while a row runs
ITEM_CUR = 0x80079c5e           # Spellbook, Equip Items, Give Items, Drop Items, Sort Items
ROW_EQUIP, ROW_GIVE = 1, 2
GIVE_STATE = 0x80079569         # 5 "Give an item to whom?" (target 0x80079948), 15 "Give which item?" (0x80079c60)
GIVE_TARGET = 0x80079948
LIST_CUR = 0x80079c60

# outfit, in order (dev run devB, 2026-10-17: the Mule's and Jupiter's packs were full, so
# the gives to them failed): ('sell', item, holder) at Boltac's (the cursed kinds the plan
# sends there), then (item, receiver, givers), the giver being the first of `givers` (None:
# any spare outside the ring party, OUTFIT_GIVERS) holding one unequipped. Mars, the new
# mule, takes the Mule's spares (the plan's section 4)
SCREWY_SHIELD, EPEE_DISMAY, MACE_MISFORTUNE = 0xa9, 0x14, 0x1b
LATUMOFIS, DIAL = 0xf3, 0xfa
OUTFIT = [('sell', SCREWY_SHIELD, 'Mule'),       # (the EPEE OF DISMAY, unidentified, Boltac refuses)
          (TABLET, 'Io', None), (0x6c, 'Io', None),            # Tablet, WAND OF MYSTERY
          (0x44, 'Puck', None), (0x63, 'Puck', None),          # THIEVES DAGGER, ROBINSWORD
          (0xb1, 'Puck', None),                                # FEAT GLOVES (c18v2c's Mars)
          (DIAL, 'Ceres', ['Mars']),
          (0x115, 'Pluto', ['Mule']),                          # ANKH OF POWER
          (0xf8, 'Mars', ['Mule']), (0xf8, 'Mars', ['Mule']),  # ANGEL FLUTE x2
          (0x13e, 'Mule', None), (0x13f, 'Mule', None),        # GOLD GAUNTLETS, GOLD BOOTS
          (LATUMOFIS, 'Pluto', None), (LATUMOFIS, 'Ceres', None),
          (LATUMOFIS, 'Io', None), (LATUMOFIS, 'Puck', None)]
OUTFIT_GIVERS = ['Uranus', 'Earth', 'Eve', 'Mars', 'Dax', 'Venus', 'Mercury', 'Fen']
GOLD_PARTY = ['Uranus', 'Eve', 'Jupiter', 'Mule', 'Pluto', 'Io']
DIVIDE_ICON = 3


def here(g):
    return (g.u8(maze.AREA),) + g.pos()


def said(g, n, name, idx):
    return bool(g.cap) and any(m['file'] == name and m['idx'] in idx for m in g.cap.messages[n:])


def idx(g, name):
    return next((i for i in range(g.roster_count()) if g.name(i) == name), None)


def titled(g, i):
    return chapter18.titled(g, i)


def holders(g, item=RING):
    """Roster indices (anyone, in the party or not) with `item` in their pack."""
    return [i for i in range(g.roster_count()) if any(it & 0x1ff == item for it in g.char(i)['items'])]


def median_level(g, names):
    lv = sorted(g.char(idx(g, n))['level'] for n in names if idx(g, n) is not None)
    return lv[len(lv) // 2] if lv else 0


# --- the tavern ---

def clear_party(g):
    """Everyone out of the town party (they wait in the tavern)."""
    for ri in list(town.town_party(g))[::-1]:
        town.remove_member(g, town.town_slots(g).index(ri))


def want_party(run, names):
    """In town: the party is exactly `names` (in that order when it's formed again), and
    every other roster member is on town.BENCH. Members at the temple are left out."""
    g = run.g
    ids = [idx(g, n) for n in names if idx(g, n) is not None]
    town.BENCH.clear()
    town.BENCH.update(i for i in range(g.roster_count()) if i not in ids)
    if g.overlay() not in ('JOUKA', 'HAZURE'):
        return
    if g.overlay() == 'HAZURE':
        town.to_town_bar(g)
    ok = [i for i in ids if g.char(i)['status'] == 0]
    if set(town.town_party(g)) == set(ok):
        return
    town.to_town_bar(g)
    clear_party(g)
    town.form_party(g, ok)
    town.to_town_bar(g)
    run.note('party', [g.name(i) for i in town.town_party(g)])


def tavern_items(g, pos, limit=600):
    """Tavern > Inspect > the member at party position pos: its status screen's menu."""
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
    ui.cancel_until(g, lambda: town.facility_ready(g) and g.u8(town.TOWN_STATE) == 10, limit,
                    'back to the tavern menu')


def tavern_give(g, from_pos, item, to_pos, limit=600):
    """Give the first `item` in the pack of the member at from_pos to the one at to_pos.
    True once it's in the receiver's pack."""
    slots = town.town_slots(g)
    gi, ri = slots[from_pos], slots[to_pos]
    k = next((k for k, w in gear.pack(g, gi) if w & 0x1ff == item and not w & gear.EQUIPPED), None)
    if k is None or len(gear.pack(g, ri)) >= 10:
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
    ok = ui.press_until(g, 'circle', lambda: sum(1 for _, w in gear.pack(g, ri) if w & 0x1ff == item) > n0
                        or g.u8(gear.CAMP_MSG), limit, 'give')
    if g.u8(gear.CAMP_MSG):
        ui.press_until(g, 'circle', lambda: not g.u8(gear.CAMP_MSG), 120, 'give message')
    tavern_leave_items(g)
    return sum(1 for _, w in gear.pack(g, ri) if w & 0x1ff == item) > n0


def tavern_equip(g, pos, prefer=(), unleash=(), limit=600):
    """Tavern Inspect > Equip Items for the member at pos, with gear's choices, `prefer`
    put on, and Yes at "Unleash its special power?" for the ids in `unleash`."""
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


# --- creation ---

def priestess_age(g, rec, bonus):
    """At "Use this character?": 18 kept (Retrain declined), 15 with a bonus under 10 kept
    and retrained (+3 years and 3 levels: 18 and level 4), else thrown away."""
    age = rec[0x10]
    if age == 18:
        return False
    if age == 15 and bonus < 10:
        return True
    return None


# --- the Training Maze ---

def enter_tm(g, limit=1800):
    """Edge of Town > icon 1, Go to the Training Maze: the party lands in camp on B1 at
    E12 N9; leave the camp."""
    from harness import camp
    if g.overlay() != 'HAZURE':
        town.enter(g, 'edge')
    ui.wait_until(g, lambda: g.u8(town.FAC_SUB) == 5 or g.u8(town.EDGE_CURSOR) == 0, 300, 'edge menu')
    ui.move_cursor(g, town.EDGE_CURSOR, 0, 'down', 'up', what='Begin Adventure row')
    ui.move_cursor(g, town.EDGE_ICON, 1, 'right', 'left', what='Training Maze icon')
    ui.confirm_until(g, lambda: g.overlay() == 'MAZE', limit, 'Go to the Training Maze')
    ui.wait_until(g, lambda: camp.in_camp(g) and g.u8(camp.CAMP_STATE) == 5, limit, 'arrive in camp')
    if g.u8(maze.AREA) != TM_AREA:
        raise Stuck('Training Maze went elsewhere', area=g.u8(maze.AREA))
    camp.close_camp(g)


def tm_town(run, L):
    """In town after a Training Maze trip: the temple raises anyone down (paid by the
    first member, the party's gold pooled there); the Priestess stays at the Stables a
    night at a time while a night raises her level (FUN_800c8b10: one level a stay, when
    the EXP is there), never past PRIESTESS_LEVEL; still under it and hurt, a Cot heals her
    (no night there can raise her: the last Stables night didn't)."""
    g = run.g
    town.to_town_bar(g)
    first = lambda: next(k for k, x in enumerate(town.town_slots(g)) if x is not None)
    ids = [idx(g, n) for n in TM_PARTY]
    pats = [ri for ri in town.temple_patients(g) if ri in ids]
    if pats:
        try:
            town.pool_gold(g, first(), 'tavern')
        except Stuck as s:
            run.note('pool stuck', s.what)
        town.to_town_bar(g)
        for ri in pats:
            try:
                r = town.temple_heal(g, ri, first())
                run.log.append((g.frame, 'temple', ri, r))
            except Stuck as s:
                run.note('temple stuck', g.name(ri), s.what)
            town.to_town_bar(g)
        for ri in pats:
            if g.char(ri)['status'] == 0 and ri not in town.town_party(g):
                town.form_party(g, [ri])
                run.log.append((g.frame, 'rejoined', ri))
                town.to_town_bar(g)
    if L not in town.town_party(g):
        return
    for _ in range(PRIESTESS_LEVEL):
        c = g.char(L)
        if c['level'] >= PRIESTESS_LEVEL or c['status'] != 0:
            break
        r = town.inn_stay(g, town.town_slots(g).index(L), 'Stables', weeks=1)
        town.to_town_bar(g)
        c1 = g.char(L)
        run.note('priestess night', dict(level=(c['level'], c1['level']), exp=c1['exp'], age=c1['age'],
                                         weeks=c1['raw'][0x11]))
        if c1['level'] == c['level']:
            break
    c = g.char(L)
    if c['level'] < PRIESTESS_LEVEL and c['status'] == 0 and c['hp'] < c['max_hp'] * 0.6:
        lv = c['level']
        r = town.inn_stay(g, town.town_slots(g).index(L), 'Cot', weeks=None, gather=True)
        town.to_town_bar(g)
        run.note('priestess cot', dict(weeks=r['weeks'], hp=r['hp'], level=(lv, g.char(L)['level'])))


def tm_trip(run, L):
    """One Training Maze B1 trip with TM_PARTY: the fight squares (85% each) in random
    order until TM_FIGHTS fights, the Priestess down or under half her HP, or an escort
    down; back to E12 N9 and town; then tm_town."""
    g = run.g
    want_party(run, TM_PARTY)
    town.to_town_bar(g)
    if any(ri in town.temple_patients(g) for ri in (idx(g, n) for n in TM_PARTY)):
        tm_town(run, L)         # someone (her too) waits at the temple: raised first
        want_party(run, TM_PARTY)
    if L not in town.town_party(g):
        run.note('tm trip: the Priestess is not in the party', g.char(L)['status'])
        return False
    enter_tm(g)
    sqs = sorted(nav.floor(TM_AREA)['fights'])
    run.rng.shuffle(sqs)
    n0 = run.fights()
    for sq in sqs:
        if run.fights() - n0 >= TM_FIGHTS:
            break
        c = g.char(L)
        if c['status'] != 0 or c['hp'] < c['max_hp'] * 0.5:
            break
        if any(g.char(i)['status'] >= 0x20 for i in g.party()):
            break
        nav.travel(g, (TM_AREA,) + sq, run.on_int, lambda g: run.after())
    if not maze.calm(g):
        run.after()
    run.note('tm trip', dict(fights=run.fights() - n0, exp=g.char(L)['exp'], hp=g.char(L)['hp'],
                             status=g.char(L)['status']))
    if chapter1.GEAR and gear.loot_work(g):
        gear.camp_loot(g, run.log, on_int=run.on_int)
    nav.travel(g, (TM_AREA,) + maze.ENTRANCE[TM_AREA], run.on_int, lambda g: run.after())
    maze.to_town(g, run.on_int)
    tm_town(run, L)
    return True


# --- the soft reset ---

def soft_reset(g, limit=6000):
    """Hold L1 L2 R1 R2 SELECT, then START with them (MAIN FUN_800124a8: the held word
    0x90f and START new), then the title: circle (Continue is the cursor's default when a
    save image is valid) until the town bar."""
    g.e.run(10, RESET_HOLD)
    g.e.run(10, RESET_HOLD + ('start',))
    ui.wait_until(g, lambda: g.overlay() != 'JOUKA' or g.u8(TOWN_STATE) == 0, 600, 'reset')
    ui.confirm_until(g, lambda: g.u8(0x8007967e) == 3 or g.overlay() == 'JOUKA' and g.u8(TOWN_STATE) != 0,
                     limit, 'title Continue')
    ui.wait_until(g, lambda: town.in_town_bar(g), limit, 'town after Continue')


@chapters.chapter
class Chapter19:
    n = 19
    title = 'The ending: a second ring for the Priestess'

    def goals(self, run):
        g = run.g
        gear.MULE_NAME = NEW_MULE           # the Mule fights in the ring party now
        memo = {}
        job = make_job(run)
        dev_overrides()

        def ring_ids():
            return [idx(g, n) for n in RING_PARTY]

        def create():
            names = [PRIESTESS[0]] + [x[0] for x in NEW]
            if all(idx(g, n) is not None for n in names):
                return proved_create()
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                run.trip_home('create')
            town.to_town_bar(g)
            if town.town_party(g):
                clear_party(g)
                town.to_town_bar(g)
            for spec in [PRIESTESS] + NEW:
                if idx(g, spec[0]) is not None:
                    continue
                kw = dict(accept=priestess_age) if spec is PRIESTESS else dict(retrain=False)
                r = town.create_character(g, *spec, **kw)
                town.to_town_bar(g)
                c = g.char(r['index'])
                run.note('created', dict(r, age=c['age'], level=c['level'], stats=c['stats'],
                                         hp=c['max_hp']))
                print('c19 created %s: %s, age %d, level %d, %d rerolls' % (
                    spec[0], spec[4], c['age'], c['level'], r['rerolls']), flush=True)
            return proved_create()

        def proved_create():
            out = True
            for name, race, sex, al, cls in [PRIESTESS] + NEW:
                i = idx(g, name)
                c = g.char(i) if i is not None else None
                if c is None or town.CLASSES[c['cls']] != cls or town.RACES[c['race']] != race \
                        or town.ALIGN[c['align']] != al or c['female'] != (sex == 'F'):
                    run.note('create: wrong record', name, c and (c['race'], c['cls'], c['align']))
                    out = False
            L = idx(g, PRIESTESS[0])
            raw = g.char(L)['raw']
            if raw[0x0a] & 0x3f != 1 or raw[0x0b] != 0x82 or raw[0x10] != 18:
                run.note('create: the Priestess', hex(raw[0x0a]), hex(raw[0x0b]), raw[0x10])
                out = False
            return out

        def outfit():
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                return outfit_done()
            town.to_town_bar(g)
            ring = ring_ids()
            for step in OUTFIT:
                if step[0] == 'sell':
                    _, item, who = step
                    ri = idx(g, who)
                    k = next((k for k, w in gear.pack(g, ri) if w & 0x1ff == item), None)
                    if k is None:
                        continue
                    clear_party(g)
                    town.form_party(g, [ri])
                    try:
                        r = town.boltac_sell(g, 0, k)
                        run.log.append((g.frame, 'outfit sell', who, gear.name(item), r['outcome']))
                    except Stuck as e:
                        run.note('outfit sell stuck', who, gear.name(item), e.what)
                    town.to_town_bar(g)
                    continue
                item, to, givers = step
                ri = idx(g, to)
                if outfit_has(item, to, givers):
                    continue
                cands = [idx(g, n) for n in (givers or OUTFIT_GIVERS)]
                giver = next((i for i in cands if i is not None and i != ri and i not in
                              (ring if givers is None else ()) and any(
                                  w & 0x1ff == item and not w & gear.EQUIPPED for _, w in gear.pack(g, i))), None)
                if giver is None:
                    run.note('outfit: nobody has', gear.name(item), 'for', to)
                    continue
                clear_party(g)
                town.form_party(g, [giver, ri])
                ok = tavern_give(g, 0, item, 1)
                run.log.append((g.frame, 'outfit give', g.name(giver), gear.name(item), to, ok))
                town.to_town_bar(g)
            if any(g.char(idx(g, n))['gold'] < 1000 for n in GOLD_PARTY if idx(g, n) in ring):
                clear_party(g)
                town.form_party(g, [idx(g, n) for n in GOLD_PARTY])
                g0 = {n: g.char(idx(g, n))['gold'] for n in GOLD_PARTY}
                town.pool_gold(g, 0, 'tavern')
                town.divide_gold(g)
                town.to_town_bar(g)
                run.note('outfit gold', {n: (g0[n], g.char(idx(g, n))['gold']) for n in GOLD_PARTY})
            clear_party(g)
            town.to_town_bar(g)
            return outfit_done()

        def outfit_has(item, to, givers=None):
            """A step is done when the receiver holds one; a step from named givers (the
            Mule's spares to Mars) when no giver has one left unequipped."""
            if givers:
                return not any(w & 0x1ff == item and not w & gear.EQUIPPED
                               for n in givers for _, w in gear.pack(g, idx(g, n)))
            return any(w & 0x1ff == item for _, w in gear.pack(g, idx(g, to)))

        def outfit_done():
            puck = g.char(idx(g, 'Puck'))
            if town.CLASSES[puck['cls']] != 'Thief':
                run.note('outfit: Puck is a', town.CLASSES[puck['cls']])
                return False
            if not any(i in ring_ids() for i in holders(g, TABLET)):
                run.note('outfit: the Tablet is not with the ring party', holders(g, TABLET))
                return False
            missing = [(gear.name(st[0]), st[1]) for st in OUTFIT if st[0] != 'sell' and not outfit_has(*st)]
            if missing:
                run.note('outfit: missing', missing)
            return True

        def stage_party(names):
            def fit():
                if g.overlay() in ('JOUKA', 'HAZURE'):
                    want_party(run, names)
                else:
                    ids = [idx(g, n) for n in names]
                    if any(i not in ids for i in g.party()):
                        run.trip_home('party change')
                        want_party(run, names)
                    else:
                        want_party(run, names)  # the bench
            return fit

        def escort_trip():
            stage_party(ESCORT_PARTY)()
            return run.train(ESC_AREAS)

        def ring_trip():
            stage_party(RING_PARTY)()
            lv = median_level(g, RING_PARTY)
            areas = next(a for top, a in LADDER if lv < top)
            return run.train(areas)

        def priestess_trip():
            L = idx(g, PRIESTESS[0])
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                run.trip_home('priestess')
            return tm_trip(run, L)

        def priestess_l5():
            L = idx(g, PRIESTESS[0])
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                run.trip_home('priestess')
            c = g.char(L)
            raw = c['raw']
            ok = (c['level'] == PRIESTESS_LEVEL and c['exp'] >= L5_EXP and raw[0x10] == 18
                  and raw[0x0a] & 0x3f == 1 and raw[0x0b] == 0x82 and c['status'] == 0)
            run.note('priestess', dict(level=c['level'], exp=c['exp'], age=raw[0x10], weeks=raw[0x11],
                                       days=raw[0x12], status=c['status'], stats=c['stats']))
            if not ok:
                return False
            want_party(run, RING_PARTY)
            return L not in town.town_party(g)

        def reset():
            if memo.get('reset') and g.overlay() == 'JOUKA' and not any(titled(g, i) for i in ring_ids()):
                return proved_reset()
            if g.overlay() in ('JOUKA', 'HAZURE'):
                return proved_reset() if holders(g) else False
            hs = [i for i in holders(g) if i in g.party()]
            if not hs:
                run.note('reset: no ring in the party')
                return False
            memo['story'] = g.u32(STORY)
            chapter18.clear_stale_box(run)
            if not maze.calm(g):
                run.after()
            chapter1.cure_in_camp(g, run.log, on_int=run.on_int)
            if chapter1.GEAR and gear.loot_work(g):
                gear.camp_loot(g, run.log, on_int=run.on_int)
            chapter1.heal_in_camp(g, run.log, on_int=run.on_int)
            if g.u8(maze.AREA) != 0:
                nav.travel(g, (0,) + maze.ENTRANCE[0], run.on_int, lambda g: run.after())
            maze.walk_to(g, *maze.ENTRANCE[0], run.on_int)
            if not maze.calm(g):
                maze.settle(g)
            standing = [i for i in holders(g) if i in g.party() and chapter18.standing(g, i)]
            if not standing:
                # the ring on a body: town_main moves the dead out before its ring check, so
                # the walk home brings no audience and there's nothing to reset
                run.note('reset: ring holder down, no audience', [g.name(i) for i in holders(g)])
                maze.to_town(g, run.on_int)
                memo['reset'] = 'no audience'
                return raise_holder()
            n = len(g.cap.messages) if g.cap else 0
            ui.press_until(g, 'triangle', lambda: g.u8(0x8007967e) == 3 or not maze.in_maze(g), 120,
                           'triangle to town')
            end = g.frame + AUDIENCE_MOST
            seen = []
            while g.frame < end:
                st = (g.overlay(), g.u8(TOWN_STATE), g.u8(CAMP_STATE))
                if not seen or seen[-1][1:] != st:
                    seen.append((g.frame,) + st)
                if st[0] == 'JOUKA' and st[1] == chapter18.ENDING_STATE and st[2] == 5:
                    break
                if st[0] == 'JOUKA' and g.u8(town.TOWN_MSG) and st[1] == 2:
                    s0 = (g.u8(town.TOWN_MSG), st[1], len(g.cap.messages) if g.cap else 0)
                    ui.confirm_until(g, lambda: (g.u8(town.TOWN_MSG), g.u8(TOWN_STATE),
                                                 len(g.cap.messages) if g.cap else 0) != s0, 240,
                                     'town arrival message')
                    continue
                if st[0] == 'JOUKA' and st[1] == 5 and town.in_town_bar(g):
                    break
                g.step()
            memo['audience'] = said(g, n, 'SISETU.OBJ', (360,))
            if not (g.u8(TOWN_STATE) == chapter18.ENDING_STATE and g.u8(CAMP_STATE) == 5):
                run.note('reset: no audience', seen[-8:])
                return False
            titles_ram = [titled(g, i) for i in g.party() or town.town_party(g)]
            try:
                g.shot('%s/c19_audience' % run.out)
            except Exception:
                pass
            soft_reset(g)
            memo['reset'] = 'reset'
            run.note('reset', dict(states=seen[-8:], audience=memo['audience'], titles_before=titles_ram,
                                   party=town.town_party(g)))
            return proved_reset()

        def raise_holder():
            for _ in range(3):
                h = next((i for i in holders(g) if g.char(i)['status'] != 0), None)
                if h is None:
                    break
                first = next((k for k, x in enumerate(town.town_slots(g)) if x is not None), None)
                if first is None:
                    break
                try:
                    town.pool_gold(g, first, 'tavern')
                    town.to_town_bar(g)
                    r = town.temple_heal(g, h, first)
                    run.log.append((g.frame, 'temple', h, r))
                except Stuck as s:
                    run.note('temple stuck', g.name(h), s.what)
                town.to_town_bar(g)
            return proved_reset()

        def proved_reset():
            hs = holders(g)
            ring = ring_ids()
            ok = g.overlay() == 'JOUKA' and bool(hs) and any(h in ring for h in hs) \
                and not any(titled(g, i) for i in ring) and g.u8(TOWN_STATE) != chapter18.ENDING_STATE
            if memo.get('story') is not None and g.u32(STORY) != memo['story']:
                run.note('reset: story flags changed', hex(memo['story']), hex(g.u32(STORY)))
                ok = False
            run.note('reset proof', dict(ok=ok, holders=[g.name(i) for i in hs], how=memo.get('reset'),
                                         audience=memo.get('audience'),
                                         titled=[g.name(i) for i in ring if titled(g, i)]))
            print('c19 reset: %s, ring on %s, audience %s, titled %s' % (
                memo.get('reset'), [g.name(i) for i in hs], memo.get('audience'),
                [g.name(i) for i in ring if titled(g, i)]), flush=True)
            return ok

        def ring_on():
            L = idx(g, PRIESTESS[0])
            if not holders(g) and g.char(L)['stats'] == [5, 18, 18, 5, 5, 18]:
                return proved_ring()
            h = next((i for i in holders(g) if g.char(i)['status'] == 0), None)
            if h is None or g.overlay() != 'JOUKA':
                run.note('ring_on: no standing holder in town', holders(g))
                return False
            town.to_town_bar(g)
            if g.u8(TOWN_STATE) == chapter18.ENDING_STATE:
                return False
            # the holder, the Priestess and the ring party's purses, formed in the tavern;
            # nobody goes out to the bar with the ring
            others = [i for i in ring_ids() if i != h and g.char(i)['status'] == 0][:4]
            clear_party(g)
            town.form_party(g, [h, L] + others)
            gold0 = sum(g.char(i)['gold'] for i in town.town_party(g))
            pos = lambda ri: town.town_slots(g).index(ri)
            if h != L:
                if not tavern_give(g, pos(h), RING, pos(L)):
                    run.note('ring_on: give failed')
                    return False
            ch = tavern_equip(g, pos(L), prefer={RING}, unleash={RING})
            c = g.char(L)
            run.note('ring_on equip', dict(chosen={k: (gear.name(v) if isinstance(v, int) else v)
                                                   for k, v in ch.items()}, stats=c['stats']))
            town.pool_gold(g, pos(L), 'tavern')
            to_boltac_r2(g)
            k = next((k for k, w in gear.pack(g, L) if w & 0x1ff == RING), None)
            out = gear.service(g, pos(L), k, 'uncurse') if k is not None else 'no ring'
            town.boltac_leave(g)
            town.to_town_bar(g)
            memo['fee'] = gold0 - sum(g.char(i)['gold'] for i in town.town_party(g))
            run.note('ring_on uncurse', out, memo['fee'])
            return proved_ring()

        def proved_ring():
            L = idx(g, PRIESTESS[0])
            c = g.char(L)
            raw = c['raw']
            ok = (c['stats'] == [5, 18, 18, 5, 5, 18] and c['level'] == PRIESTESS_LEVEL and raw[0x10] == 18
                  and raw[0x0a] & 0x3f == 1 and raw[0x0b] == 0x82 and not holders(g)
                  and not titled(g, L) and not any(titled(g, i) for i in ring_ids())
                  and g.u8(TOWN_STATE) != chapter18.ENDING_STATE)
            if memo.get('fee') is not None and memo['fee'] < UNCURSE_FEE:
                run.note('ring_on: fee short', memo['fee'])
            run.note('priestess made', dict(ok=ok, stats=c['stats'], level=c['level'], age=raw[0x10],
                                            fee=memo.get('fee'), holders=holders(g)))
            print('c19 ring_on: %s, stats %s, level %d, age %d, fee %s' % (
                ok, c['stats'], c['level'], raw[0x10], memo.get('fee')), flush=True)
            return ok

        def ch18_goal(name, fns):
            def run_it():
                want_party(run, RING_PARTY)     # in the maze: the bench only
                return fns[name]()
            return run_it

        yield from jobbed(job, [('create', create)])
        if not os.environ.get('CH19_SKIP_OUTFIT'):
            yield from jobbed(job, [('outfit', outfit)])
        n = 0
        while n < ESC_MOST and median_level(g, TRAINEES) < ESC_LEVEL:
            n += 1
            yield from jobbed(job, [('train_esc_%02d' % n, escort_trip)])
        n = 0
        while n < RING_MOST and median_level(g, RING_PARTY) < RING_LEVEL:
            n += 1
            yield from jobbed(job, [('train_%02d' % n, ring_trip)])
        n = 0
        while n < TM_MOST and g.char(idx(g, PRIESTESS[0]))['level'] < PRIESTESS_LEVEL:
            n += 1
            yield from jobbed(job, [('priestess_%02d' % n, priestess_trip)])
        yield from jobbed(job, [('priestess_l5', priestess_l5)])
        fns = dict(x for x in chapter18.Chapter18().goals(run) if x[0] in ('lift_z', 'the_man', 'coffin'))
        yield from jobbed(job, [(k, ch18_goal(k, fns)) for k in ('lift_z', 'the_man', 'coffin')])
        yield from jobbed(job, [('reset', reset), ('ring_on', ring_on)])
        job.finish('ring_on reached')


def dev_overrides():
    """Development runs only (none of these is set for a real run): CH19_ESC_LEVEL,
    CH19_RING_LEVEL, CH19_RING_PARTY (comma-separated names), CH19_SKIP_OUTFIT."""
    global ESC_LEVEL, RING_LEVEL, RING_PARTY
    e = os.environ
    ESC_LEVEL = int(e.get('CH19_ESC_LEVEL', ESC_LEVEL))
    RING_LEVEL = int(e.get('CH19_RING_LEVEL', RING_LEVEL))
    if e.get('CH19_RING_PARTY'):
        RING_PARTY = e['CH19_RING_PARTY'].split(',')


def make_job(run):
    """The monitor's jobs panel: one job per run (scripts/jobstatus.py)."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from jobstatus import Job
    name = os.path.basename(run.out.rstrip('/'))
    return Job('ch19', purpose='chapter 19: ring party, Priestess, coffin, reset, ring', part=name,
               run=os.environ.get('JOB_RUN') or name, agent='ch19',
               outputs=[os.path.join(chapter1.OUT, run.out, 'live.jsonl')])


def jobbed(job, pairs):
    """Each goal reports to the job: its name as the step, an event and a tally after."""
    for name, fn in pairs:
        def wrapped(name=name, fn=fn):
            job.step(name)
            r = fn()
            job.tally('pass' if r is True else 'retry')
            job.event('%s: %s' % (name, 'pass' if r is True else r))
            if r is True:
                job.done_one(name)
            return r
        yield name, wrapped
