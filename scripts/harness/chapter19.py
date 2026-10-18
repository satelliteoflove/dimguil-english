"""Walkthrough chapter 19, the ending's ring kept from the King for the Priestess's Door
(2026-10-17). Runs after chapter 17 and before chapter 18: the chain is 17, 19, 18.

Plan: rips/harness/ch19/STATUS.md, section "Quicker path (Chris, 2026-10-17)": no new
party; the main party, still untitled after chapter 17, wins a ring at the coffin, the
soft reset keeps it, and the ring makes the Priestess, who opens the Priestess's Door on
Training Maze B8 (story_flags bit 31). The main party ends in town untitled and without a
ring, so chapter 18 runs unchanged afterwards: the coffin is repeatable for such a party
(docs/re/postgame.md section 3).

Source: data/walkthrough/dim/19-ending.json and 20-training-maze.json, data/maps/dim/f09,
f15, f16, f42.json, docs/re/postgame.md, docs/re/F-edge-save.md (creation), and the code:
JOUKA training_create 0x800af5d8, tavern_main 0x800a79d4 (its R2 shortcut), tavern_inspect
0x800aa444 with FUN_800cbddc (the status screen's menu), equip_menu 0x800ccc94, inn_stay
0x800c5e34 with FUN_800c8b10 (one level a stay, when the EXP is there), town_main 0x800a2198,
king_ending 0x800a52cc, MAIN FUN_800124a8 (the soft reset), MAZE square_examine 0x800bb790
(case 7 the Training Maze lift, case 0x59 the door), FUN_800b2e8c (the lift's floor menu),
FUN_800ac798 (the door's member picker), maze_prompt_result 0x800befcc case 0x19.

What the probes found (rips/harness/ch19/probe, 2026-10-17, ch18's states and dev run devA):
- Creation: new_char (0x8008ff10) already holds the age at "Use this character?" (state
  105), so the age is rolled for: 18 is kept with Retrain declined, 15 with a bonus under
  10 is kept and retrained (+3 years, level 4); anything else is thrown away (p1).
- The Training Maze: the Edge of Town's icon 1 puts the party in camp on B1 (area 9) at
  E12 N9 (12, 14); triangle there goes back to town (p5), so maze.ENTRANCE[9].
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
- The lift (B1 E9 N11, (9, 12), facing east, case 7): SISETU 443, then game_state 4 with
  the floor index in 0x80079797 (0 = B1 .. 6 = B7, area = index + 9; right/left move it,
  as far as the Tablet's stones allow, FUN_800b7248 bits 3, 7, 0, 1, 5, 2), circle rides
  (scene 0xb, about 330 frames) to the same square on that floor (p7, p8). B7's stairs at
  E10 N12 (10, 11) lead to B8 (10, 10); nav plans them.
- The door (B8 E10 N11, (16, 10, 12), facing west, case 0x59): EVENTMES 240 (the glyphs,
  the old script for the profile) and "Will someone try it?", then the member picker
  (game_state 0x11, FUN_800ac798: row in 0x8007b6f2, 0x48 front 0x62 back, column in
  0x8007b6f0 at -99, 1, 101; up/down and left/right move it, circle picks; the slot goes to
  0x8007e808). Her slot gave EVENTMES 239 and story bit 31, and the party went on through
  the opened wall onto the lift behind it to Dragon's Cave B1 (area 42) at (11, 12) (p8,
  p9). Triangle at Dragon's Cave B1 E12 N12 (12, 11) goes to town (p10).

Goals, each proved by RAM or a captured string:
  create       the Priestess Luna: +0x0a & 0x3f == 1 (Elf), +0x0b == 0x82 (female
               Priest), +0x10 == 18.
  priestess_NN Training Maze B1 trips with three of the main party as escorts (no Priest,
               so no camp Kadorto can age her); in town she stays at the Stables one night
               at a time only while a night raises her level, never past 5 (tm_town).
  priestess_l5 her level 5, EXP 4,396 or more, age 18, Elf female Priest, waiting in the
               tavern; the main party formed again.
  lift_z, the_man, coffin
               chapter 18's goals with the main party (untitled after chapter 17).
  reset        the ring carried into town: the audience begins (town_state 45, SISETU 360
               captured), the soft reset at camp_state 5, Continue; proof: the ring in a
               main-party pack in town, nobody of the main party titled, the story flags
               unchanged. A holder down on arrival brings no audience (town_main moves the
               dead out first), so then there's nothing to reset: noted, and the temple
               raises the holder into the tavern.
  ring_on      in the tavern: the holder and the Priestess in a party, the ring given and
               equipped with Yes at "Unleash", the gold pooled on her, R2 to Boltac's and
               Uncurse; proof: her stats 5/18/18/5/5/18, level 5, age 18, the ring in no
               pack, no title, 50,000 Gp paid.
  tm_b1        the door party (the main party less its lowest-level member without the
               Tablet, and the Priestess) on Training Maze B1 (area 9), with the Tablet and
               all six stones (its item_state) in the party.
  tm_lift      B7 (area 15) by the lift.
  tm_b8        B8 (area 16) at the door square, the Priestess standing.
  door         story_flags bit 31, EVENTMES 239 captured, 0x8007e808 her slot.
  home         back in town (through Dragon's Cave B1's exit), the Priestess out, the main
               party formed again: untitled, no ring anywhere, level 5 for her still.
"""
import os, struct

from harness import chapter1, chapter3, chapter18, chapters, gear, maze, nav, town, ui
from harness.game import Stuck

RING = 0x142
TABLET = 0x143
STORY = 0x80079b44
DOOR_BIT = 31
TOWN_STATE = 0x80079b18
CAMP_STATE = 0x80079669

PRIESTESS = ('Luna', 'Elf', 'F', 'Good', 'Priest')
MAIN_LEVEL = 15                 # the main party: every roster member at this level or more
                                # (the spares, Jupiter, Mars, Fen and the Mule, are 1-10)
ESCORTS = 3                     # main-party members with her in the Training Maze

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

# --- the door ---
TM_LIFT = (9, 9, 12)            # B1 E9 N11, facing east
LIFT_FACE = 1
LIFT_FLOOR = 0x80079797         # the floor menu's index (talk_party): area = index + 9
B7 = 15
B8 = 16
DOOR = (16, 10, 12)             # B8 E10 N11, facing west
DOOR_FACE = 3
PICK_ROW, PICK_COL = 0x8007b6f2, 0x8007b6f0
PICKED = 0x8007e808
DC_B1 = 42
ALL_STONES = 0xff               # the Tablet's item_state with every stone set (chapter 16 on)

TM_PARTY = []                   # set by the priestess goals: the escorts and her


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
    title = "The ending's ring kept for the Priestess's Door"

    def goals(self, run):
        g = run.g
        memo = {}
        job = make_job(run)

        def main_ids():
            if 'main' not in memo:
                memo['main'] = [g.name(i) for i in range(g.roster_count())
                                if g.char(i)['level'] >= MAIN_LEVEL and g.name(i) != PRIESTESS[0]]
                run.note('main party', memo['main'])
            return [idx(g, n) for n in memo['main']]

        def main_names():
            main_ids()
            return memo['main']

        def escorts():
            ids = sorted(main_ids(), key=lambda i: (g.char(i)['cls'] not in chapter1.MELEE,
                                                    -g.char(i)['max_hp']))
            return [g.name(i) for i in ids[:ESCORTS]]

        def door_party():
            ids = main_ids()
            tab = holders(g, TABLET)
            drop = min((i for i in ids if i not in tab), key=lambda i: (g.char(i)['level'], -i))
            # the three with the most HP in front, the rest and her behind (formed in order)
            rest = sorted((i for i in ids if i != drop), key=lambda i: -g.char(i)['max_hp'])
            return [g.name(i) for i in rest] + [PRIESTESS[0]]

        def create():
            if idx(g, PRIESTESS[0]) is not None:
                return proved_create()
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                run.trip_home('create')
            main_ids()
            town.to_town_bar(g)
            r = town.create_character(g, *PRIESTESS, accept=priestess_age)
            town.to_town_bar(g)
            c = g.char(r['index'])
            run.note('created', dict(r, age=c['age'], level=c['level'], stats=c['stats'], hp=c['max_hp'],
                                     exp=c['exp']))
            print('c19 created %s: age %d, level %d, %d rerolls, retrained %s' % (
                PRIESTESS[0], c['age'], c['level'], r['rerolls'], r['retrained']), flush=True)
            return proved_create()

        def proved_create():
            L = idx(g, PRIESTESS[0])
            raw = g.char(L)['raw']
            ok = raw[0x0a] & 0x3f == 1 and raw[0x0b] == 0x82 and raw[0x10] == 18
            if not ok:
                run.note('create: the Priestess', hex(raw[0x0a]), hex(raw[0x0b]), raw[0x10])
            return ok

        def priestess_trip():
            global TM_PARTY
            L = idx(g, PRIESTESS[0])
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                run.trip_home('priestess')
            TM_PARTY = escorts() + [PRIESTESS[0]]
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
            want_party(run, main_names())
            return L not in town.town_party(g)

        def reset():
            if memo.get('reset') and g.overlay() == 'JOUKA' and not any(titled(g, i) for i in main_ids()):
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
            ring = main_ids()
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
            # the holder, the Priestess and the main party's purses, formed in the tavern;
            # nobody goes out to the bar with the ring
            others = [i for i in main_ids() if i != h and g.char(i)['status'] == 0][:4]
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
            # the gold back on the purses (it was pooled on her for the fee)
            town.divide_gold(g)
            town.to_town_bar(g)
            return proved_ring()

        def proved_ring():
            L = idx(g, PRIESTESS[0])
            c = g.char(L)
            raw = c['raw']
            ok = (c['stats'] == [5, 18, 18, 5, 5, 18] and c['level'] == PRIESTESS_LEVEL and raw[0x10] == 18
                  and raw[0x0a] & 0x3f == 1 and raw[0x0b] == 0x82 and not holders(g)
                  and not titled(g, L) and not any(titled(g, i) for i in main_ids())
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
                want_party(run, main_names())       # in the maze: the bench only
                return fns[name]()
            return run_it

        # --- the door ---

        def her_standing():
            c = g.char(idx(g, PRIESTESS[0]))
            return c['status'] == 0 and c['hp'] > 0

        def tm_b1():
            if g.overlay() not in ('JOUKA', 'HAZURE') and g.u8(maze.AREA) in range(9, 17) \
                    and idx(g, PRIESTESS[0]) in g.party():
                return proved_tablet()
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                return False
            names = door_party()
            want_party(run, names)
            run.note('door party', names)
            town.to_town_bar(g)
            enter_tm(g)
            return g.u8(maze.AREA) == TM_AREA and proved_tablet()

        def proved_tablet():
            st = chapter3.tablet_stones(g)
            ok = run.has_tablet() and st == ALL_STONES
            run.note('tablet', dict(holder=[g.name(i) for i in holders(g, TABLET)], stones=st, ok=ok))
            return ok

        def tm_lift():
            if g.u8(maze.AREA) in (B7, B8):
                return her_standing()
            if g.u8(maze.AREA) != TM_AREA:
                return False
            nav.travel(g, TM_LIFT, run.on_int, lambda g: run.after())
            if not maze.face(g, LIFT_FACE):
                run.after()
                maze.face(g, LIFT_FACE)
            n = len(g.cap.messages) if g.cap else 0
            chapter1.investigate(g)
            ui.wait_until(g, lambda: g.u8(maze.GAME_STATE) == 4, 900, 'lift menu')
            ui.move_cursor(g, LIFT_FLOOR, B7 - 9, 'right', 'left', what='lift floor')
            ui.press_until(g, 'circle', lambda: g.u8(maze.GAME_STATE) != 4, 120, 'ride')
            ui.wait_until(g, lambda: g.u8(maze.AREA) == B7 and maze.calm(g), 3000, 'ride to B7')
            run.note('lift', dict(said=said(g, n, 'SISETU.OBJ', (443,)), at=here(g)))
            return g.u8(maze.AREA) == B7 and her_standing()

        def tm_b8():
            if here(g) == DOOR:
                return her_standing()
            if g.u8(maze.AREA) not in (B7, B8):
                return False
            nav.travel(g, DOOR, run.on_int, lambda g: run.after())
            if not maze.calm(g):
                run.after()
            return here(g) == DOOR and her_standing()

        def door():
            if nav.flag(g, STORY, DOOR_BIT):
                return True
            if here(g) != DOOR or not her_standing():
                return False
            L = idx(g, PRIESTESS[0])
            slot = g.party_slots().index(L)
            if not maze.face(g, DOOR_FACE):
                run.after()
                maze.face(g, DOOR_FACE)
            n = len(g.cap.messages) if g.cap else 0
            chapter1.investigate(g)
            # the box (EVENTMES 240), "Will someone try it?" (Yes, the cursor's first), then
            # the member picker
            end = g.frame + 6000
            k = 0
            while g.u8(maze.GAME_STATE) != 0x11:
                if g.frame > end:
                    raise Stuck('door picker', gs=g.u8(maze.GAME_STATE))
                k += 1
                if g.u8(maze.GAME_STATE) == 6:
                    ui.move_cursor(g, 0x8007e800, 0, 'up', 'down', what='try it: yes')
                    g.tap('circle')
                    g.step(10)
                    continue
                if k % 30 == 0 and not maze.calm(g):
                    g.tap('circle')
                if maze.calm(g) and k > 600:
                    run.note('door: no picker', said(g, n, 'EVENTMES.BIN', (240,)))
                    return False
                g.step()
            ui.press_until(g, 'down' if slot >= 3 else 'up',
                           lambda: g.u8(PICK_ROW) == (0x62 if slot >= 3 else 0x48), 200, 'picker row')
            want = (-99, 1, 101)[slot % 3]
            ui.press_until(g, 'right', lambda: g.s16(PICK_COL) == want, 300, 'picker column')
            ui.press_until(g, 'circle', lambda: g.u8(maze.GAME_STATE) != 0x11, 120, 'pick her')
            picked = g.u8(PICKED)
            run.after()
            ok = nav.flag(g, STORY, DOOR_BIT) and picked == slot and said(g, n, 'EVENTMES.BIN', (239,))
            run.note('door', dict(picked=picked, slot=slot, bit31=nav.flag(g, STORY, DOOR_BIT),
                                  k240=said(g, n, 'EVENTMES.BIN', (240,)), k239=said(g, n, 'EVENTMES.BIN', (239,)),
                                  at=here(g)))
            print('c19 door: bit 31 %s, picked %d (her slot %d), at %s' % (
                nav.flag(g, STORY, DOOR_BIT), picked, slot, here(g)), flush=True)
            return ok

        def home():
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                if not maze.calm(g):
                    run.after()
                if g.u8(maze.AREA) not in (DC_B1, TM_AREA):
                    nav.travel(g, (DC_B1,) + maze.ENTRANCE[DC_B1], run.on_int, lambda g: run.after())
                maze.to_town(g, run.on_int)
            town.to_town_bar(g)
            # anyone down comes back from the temple before the main party forms again
            pats = [ri for ri in town.temple_patients(g) if ri in main_ids() + [idx(g, PRIESTESS[0])]]
            for ri in pats:
                first = next((k for k, x in enumerate(town.town_slots(g)) if x is not None), None)
                if first is None:
                    break
                try:
                    town.pool_gold(g, first, 'tavern')
                    town.to_town_bar(g)
                    run.log.append((g.frame, 'temple', ri, town.temple_heal(g, ri, first)))
                except Stuck as s:
                    run.note('temple stuck', g.name(ri), s.what)
                town.to_town_bar(g)
            want_party(run, main_names())
            town.to_town_bar(g)
            L = idx(g, PRIESTESS[0])
            c = g.char(L)
            ok = (g.overlay() == 'JOUKA' and nav.flag(g, STORY, DOOR_BIT) and not holders(g)
                  and not any(titled(g, i) for i in main_ids() + [L])
                  and set(town.town_party(g)) == {i for i in main_ids() if g.char(i)['status'] == 0}
                  and c['level'] == PRIESTESS_LEVEL)
            run.note('home', dict(ok=ok, party=[g.name(i) for i in town.town_party(g)],
                                  her=dict(level=c['level'], age=c['raw'][0x10], status=c['status'],
                                           stats=c['stats'])))
            return ok

        yield from jobbed(job, [('create', create)])
        n = 0
        while n < TM_MOST and g.char(idx(g, PRIESTESS[0]))['level'] < PRIESTESS_LEVEL:
            n += 1
            yield from jobbed(job, [('priestess_%02d' % n, priestess_trip)])
        yield from jobbed(job, [('priestess_l5', priestess_l5)])
        fns = dict(x for x in chapter18.Chapter18().goals(run) if x[0] in ('lift_z', 'the_man', 'coffin'))
        yield from jobbed(job, [(k, ch18_goal(k, fns)) for k in ('lift_z', 'the_man', 'coffin')])
        yield from jobbed(job, [('reset', reset), ('ring_on', ring_on), ('tm_b1', tm_b1),
                                ('tm_lift', tm_lift), ('tm_b8', tm_b8), ('door', door), ('home', home)])
        job.finish('home reached')


def make_job(run):
    """The monitor's jobs panel: one job per run (scripts/jobstatus.py)."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from jobstatus import Job
    name = os.path.basename(run.out.rstrip('/'))
    return Job('ch19', purpose='chapter 19: Priestess, coffin, reset, ring, the door', part=name,
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
