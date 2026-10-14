"""Walkthrough chapter 1, the four pillars, as a goal list (T3, 2026-10-12).

Source: Bartok's Trading Post data/walkthrough/dim/01-four-pillars.json. The site gives
squares as E x N y; RAM's y runs the other way (y = 23 - N), so the start E10 N1 is
(10, 22), the pillars E2 N2, E2 N20, E20 N20, E20 N2 are (2, 21), (2, 3), (20, 3),
(20, 21), and the Shrine door E11 N4 is the north side of (11, 19).

Goals, each proved by RAM, with a save state after each (rips/harness/<run>/goal_*.state):
  party    a party of six in town (three created, three premade)
  pillar*  the pillar's guardian beaten: its bit in maze_event_flags (0x80079b48) set, or
           its stone (items 0x136-0x139) in a pack (A-maze.md §9, square_examine 0xe-0x11)
  tablet   the four stones joined into the Tablet of the Sun (item 0x143) at the door
  door     the party through the sealed door (north of (11, 19))

Between goals: heal with Dios from camp while a priest has the points; when no one can,
or someone is dead, go back to town (temple, Stables for the spell points) and set out
again. A wipe, or a Stuck, reloads the last goal's state and tries again with different
input timing (the RNG follows input timing).
"""
import json, os, random, struct, time
from harness import ui, maze, town, battle, play, camp, gear
from harness.game import Stuck, OUT

EV_FLAGS = 0x80079b48
PILLAR_BITS = (0x4000, 0x8000, 0x10000, 0x20000)
STONES = (0x136, 0x137, 0x138, 0x139)
TABLET = 0x143
PILLARS = [('bird', (2, 21)), ('tiger', (2, 3)), ('snake', (20, 3)), ('dog', (20, 21))]
DOOR = (11, 19)
PITS = {(9, 3), (20, 10), (18, 21)}      # E9 N20, E20 N13, E18 N2: a fall hurts
TRAIN_LEVEL = 7                          # train on the Grounds until every member is here
TRAIN_TRIP_FIGHTS = 6                    # fights per training trip before heading home
START_MENU = 0x34
DIOS = (1, 1)                # Priest, level 1, list index of spell id 21

# party variants for T4: the three new characters (all Good, to sit with the premade Good
# three); the class falls back to Fighter if the rolls never offer it
VARIANTS = [
    # every party: Mercury (premade Thief) and a Bishop among the three made (Chris,
    # 2026-10-14). A Bishop needs IQ 15 and Piety 15 (G-records.md class minimums): an
    # Elf or a Gnome starts nearest (10 bonus points), creation rerolls until it's offered
    [('Ace', 'Human', 'M', 'Good', 'Fighter'), ('Bea', 'Elf', 'F', 'Good', 'Mage'),
     ('Cy', 'Gnome', 'M', 'Good', 'Bishop')],
    [('Dax', 'Dwarf', 'M', 'Good', 'Fighter'), ('Eve', 'Gnome', 'F', 'Good', 'Bishop'),
     ('Fen', 'Elf', 'M', 'Good', 'Mage')],
    [('Gus', 'Human', 'M', 'Good', 'Fighter'), ('Hal', 'Human', 'M', 'Good', 'Fighter'),
     ('Ivy', 'Elf', 'F', 'Good', 'Bishop')],
    [('Jo', 'Hobbit', 'F', 'Neutral', 'Thief'), ('Kai', 'Elf', 'M', 'Good', 'Mage'),
     ('Lu', 'Gnome', 'F', 'Good', 'Bishop')],
    [('Max', 'Dracon', 'M', 'Good', 'Fighter'), ('Nia', 'Elf', 'F', 'Good', 'Mage'),
     ('Oz', 'Elf', 'M', 'Good', 'Bishop')],
    [('Pip', 'Human', 'F', 'Good', 'Fighter'), ('Quo', 'Gnome', 'M', 'Good', 'Priest'),
     ('Rex', 'Gnome', 'M', 'Good', 'Bishop')],
    [('Sam', 'Human', 'M', 'Good', 'Samurai'), ('Tia', 'Elf', 'F', 'Good', 'Mage'),
     ('Uma', 'Elf', 'F', 'Good', 'Bishop')],
    # a Lord needs about 30 bonus points on any race; a player would reroll for an hour
    [('Vic', 'Elf', 'M', 'Good', 'Bishop'), ('Wes', 'Human', 'M', 'Good', 'Fighter'),
     ('Xia', 'Gnome', 'F', 'Good', 'Priest')],
]
PREMADE_GOOD = ['Venus', 'Earth', 'Mercury']


def party_items(g):
    out = set()
    for i in g.party() or town.town_party(g):
        for it in g.char(i)['items']:
            out.add(it & 0xfff)
    return out


def pillars_done(g):
    f = g.u32(EV_FLAGS)
    have = party_items(g)
    return [b for b in PILLAR_BITS if f & b], sorted(i for i in have if i in STONES)


def stone_count(g):
    bits, stones = pillars_done(g)
    return max(len(bits), len(stones))


# --- maze actions ---

def investigate(g):
    """From calm: START -> Investigate (the menu's first entry). Returns when the menu
    has gone; whatever the side holds (an event box, a fight) follows."""
    if not maze.calm(g):
        maze.settle(g)
    # a fight can start instead of the menu (t3f: the bird's light came down on the START
    # press, game_state 1, battle overlay); the caller's after_event takes it from there
    ui.press_until(g, 'start', lambda: g.u8(maze.GAME_STATE) == START_MENU
                   or g.overlay() == 'BATTLE'
                   or (g.u8(maze.GAME_STATE) != 0 and maze.interrupted(g)), 300, 'START menu')
    if g.u8(maze.GAME_STATE) != START_MENU:
        return False
    ui.press_until(g, 'circle', lambda: g.u8(maze.GAME_STATE) != START_MENU, 600, 'Investigate')
    return True


QUIET = 360     # after "Searching...", the side's event box can take ~190 frames to open


def after_event(g, log, limit=30000, quiet=QUIET, policy=None):
    """Run whatever an Investigate started (boxes, a fight, a talk) back to calm, or a
    wipe. Calm only counts once nothing has opened for `quiet` frames. Returns 'calm',
    'wiped' or 'town'."""
    f0 = g.frame
    while g.frame - f0 < limit:
        if party_wiped(g):
            return 'wiped'
        if g.overlay() == 'JOUKA':
            return 'town'
        if maze.calm(g):
            for _ in range(quiet):
                g.step()
                if not maze.calm(g):
                    break
            else:
                return 'calm'
        if not play.handle_interrupt(g, policy or Ch1Policy, log):
            if party_wiped(g):
                return 'wiped'
            if g.overlay() == 'JOUKA':
                return 'town'
            g.step()
    raise Stuck('after event', where=g.where())


class Ch1Policy(play.Policy):
    chest = 'open'          # the island's chests are never trapped (walkthrough, traps data)


def party_wiped(g):
    """Nobody standing; or back in town with no party at all, which is where a wipe
    leaves the game (the bodies stay in the maze; c1v0c 2026-10-13 got 'walk
    interrupted' there)."""
    p = g.party()
    if not p:
        return g.overlay() == 'JOUKA' and g.roster_count() > 0
    # the game's own test (MAZE wipe_check 0x800cc718): every member paralyzed, stoned,
    # dead or ash (0x1e0). Poison, sleep, fear, confusion and K.O. still stand: n1v0d
    # chapter 3 fled 14 Wing Lizards with all six poisoned and was counted wiped, 6 times
    return all(g.char(i)['status'] & 0x1e0 for i in p)


def on_interrupt_factory(log):
    def on_int(g):
        r = play.handle_interrupt(g, Ch1Policy, log)
        if party_wiped(g):
            raise Wiped()
        return r
    return on_int


class Wiped(Exception):
    pass


def walk(g, xy, log):
    maze.walk_to(g, xy[0], xy[1], on_interrupt_factory(log))


def neighbours(g, xy):
    """Squares beside a pillar the party can stand on, nearest first, with the facing
    that looks at the pillar."""
    px, py = xy
    wm = maze.wallmap(g)
    here = g.pos()
    closed = maze.site_closed(g.u8(maze.AREA))
    out = []
    for d, (ax, ay) in ((3, (px + 1, py)), (1, (px - 1, py)), (0, (px, py + 1)), (2, (px, py - 1))):
        if not (0 <= ax < 24 and 0 <= ay < 24) or (ax, ay) in closed:
            continue
        p = maze.bfs(wm, here, (ax, ay), (), closed)
        if p is not None:
            out.append((len(p), (ax, ay), d))
    return [(a, d) for _, a, d in sorted(out)]


def do_pillar(g, name, xy, log):
    """Walk beside the pillar, face it, Investigate, win the fight. Returns True when the
    pillar's bit or stone count went up."""
    # whatever is on screen or about to open first (a resumed state can be mid-box,
    # mid-prompt, in camp, or just past "Searching..." with the side's box still to come)
    r = after_event(g, log)
    if r != 'calm':
        return r
    before = stone_count(g)
    for (a, d) in neighbours(g, xy):
        walk(g, a, log)
        if not maze.face(g, d):
            r = after_event(g, log)
            if r != 'calm':
                return r
            maze.face(g, d)
        investigate(g)
        r = after_event(g, log)
        if r != 'calm':
            return r
        if stone_count(g) > before:
            return True
        log.append((g.frame, 'pillar side gave nothing', a, d))
    return False


def do_door(g, log):
    """At the sealed door: face north from (11, 19), Investigate (the stones join into the
    Tablet), then step through."""
    if not maze.calm(g):
        r = after_event(g, log, quiet=30)
        if r != 'calm':
            return r
    if g.u8(maze.AREA) != 0:
        return True         # already through (a resumed state from the door's last box)
    for _ in range(4):
        # someone can meet the party at the door (t4v4: a talk, game_state 53, while
        # the harness pressed START); deal with it and try again
        walk(g, DOOR, log)
        if not maze.face(g, 0):
            r = after_event(g, log)
            if r != 'calm':
                return r
            continue
        took = investigate(g)
        r = after_event(g, log)
        if r != 'calm':
            return r
        if took:
            break
    have_tablet = TABLET in party_items(g)
    log.append((g.frame, 'tablet', have_tablet))
    if not have_tablet:
        return False
    for _ in range(3):
        s = maze.step(g, 0)
        if s == 'interrupted':
            after_event(g, log)
            continue
        break
    return g.pos() != DOOR or g.u8(maze.AREA) != 0


# --- upkeep ---

def priests(g):
    """(party slot, list index of Dios, points left at Priest level 1) for each member who
    knows Dios and can stand."""
    out = []
    for slot, ri in enumerate(g.party_slots()):
        if ri is None:
            continue
        c = g.char(ri)
        if c['status'] != 0:
            continue
        ks = battle.known_spells(c['raw'], 1, 1)
        if 21 in ks and c['raw'][0x5c + 7 + 0]:
            out.append((slot, ks.index(21), c['raw'][0x5c + 7]))
    return out


def hurt(g, frac=0.6):
    out = []
    for slot, ri in enumerate(g.party_slots()):
        if ri is None:
            continue
        c = g.char(ri)
        if c['status'] == 0 and c['max_hp'] and c['hp'] < c['max_hp'] * frac:
            out.append((c['hp'] / c['max_hp'], slot))
    return [s for _, s in sorted(out)]


def heal_in_camp(g, log, frac=0.6, max_casts=12, on_int=None):
    """Cast Dios on the most hurt member until no one is under frac or the points run
    out. Returns casts made. A fight or talk that comes first (a roamer stepping in;
    r2v1 2026-10-13 pressed cross for the camp into a battle) goes to on_int."""
    n = 0
    k = 0
    while n < max_casts and k < 40:
        k += 1
        if not camp.in_camp(g) and not maze.calm(g) and not maze.settle(g):
            (on_int or on_interrupt_factory(log))(g)
            continue
        h = hurt(g, frac)
        p = priests(g)
        if not h or not p:
            break
        slot, idx, _ = max(p, key=lambda x: x[2])
        try:
            camp.cast(g, slot, 1, 1, idx, h[0])
        except Stuck as s:
            if s.what != 'camp interrupted':
                raise
            (on_int or on_interrupt_factory(log))(g)
            continue
        n += 1
    if camp.in_camp(g):
        camp.close_camp(g)
    if n:
        log.append((g.frame, 'dios', n))
    return n


# camp heals, strongest first: (spell id, Priest level). Each is the first spell of its
# level, so its place in the level's list is 0 whatever else is known.
HEALS = [(36, 6), (33, 5), (30, 4), (21, 1)]     # Madi, Dialma, Dial, Dios


CAMP_HEAL_MEAN = {21: 5, 30: 9, 33: 13.5, 36: 999}   # Dios 2d4, Dial 2d8, Dialma 3d8, Madi full


def heal_to(g, log, need, max_casts=16, on_int=None):
    """Heal from camp each member below need(slot, char) HP, most short first, with the
    cheapest heal that covers what's short (Dios, Dial, Dialma; Madi only for half a
    member's HP or more), else the strongest under Madi. Returns the slots still short
    when the points ran out (empty when everyone's there)."""
    n = k = 0
    short = []
    while n < max_casts and k < 40:
        k += 1
        if not camp.in_camp(g) and not maze.calm(g) and not maze.settle(g):
            (on_int or on_interrupt_factory(log))(g)
            continue
        short = []
        for slot, ri in enumerate(g.party_slots()):
            if ri is None:
                continue
            c = g.char(ri)
            want = min(c['max_hp'], need(slot, c))
            if c['status'] < 0x20 and c['hp'] < want:
                short.append((c['hp'] - want, slot, want - c['hp'], c['max_hp']))
        if not short:
            break
        _, tslot, gap, mx = min(short)
        have = []
        for sid, lv in HEALS:
            for slot, ri in enumerate(g.party_slots()):
                if ri is None:
                    continue
                c = g.char(ri)
                if c['status'] != 0 or not c['raw'][0x5c + 7 + lv - 1]:
                    continue
                ks = battle.known_spells(c['raw'], 1, lv)
                if sid in ks:
                    have.append((lv, slot, ks.index(sid), sid))
                    break
        have.sort()
        if gap < mx / 2:
            have = [h for h in have if h[3] != 36] or []
        if not have:
            break
        pick = next((h for h in have if CAMP_HEAL_MEAN[h[3]] >= gap), have[-1])
        try:
            camp.cast(g, pick[1], 1, pick[0], pick[2], tslot)
        except Stuck as s:
            if s.what != 'camp interrupted':
                raise
            (on_int or on_interrupt_factory(log))(g)
            continue
        log.append((g.frame, 'heal to', pick[3], pick[1], tslot, gap))
        n += 1
    if camp.in_camp(g):
        camp.close_camp(g)
    return [x[1] for x in short]


def heal_strong(g, log, frac=0.9, max_casts=12, on_int=None):
    """Heal everyone to frac of max HP from camp with the strongest heal a priest still
    has points for (Madi, Dialma, Dial, Dios). Returns casts made."""
    n = k = 0
    while n < max_casts and k < 40:
        k += 1
        if not camp.in_camp(g) and not maze.calm(g) and not maze.settle(g):
            (on_int or on_interrupt_factory(log))(g)
            continue
        h = hurt(g, frac)
        if not h:
            break
        pick = None
        for sid, lv in HEALS:
            for slot, ri in enumerate(g.party_slots()):
                if ri is None:
                    continue
                c = g.char(ri)
                if c['status'] != 0 or not c['raw'][0x5c + 7 + lv - 1]:
                    continue
                ks = battle.known_spells(c['raw'], 1, lv)
                if sid in ks:
                    pick = (slot, lv, ks.index(sid), sid)
                    break
            if pick:
                break
        if not pick:
            break
        try:
            camp.cast(g, pick[0], 1, pick[1], pick[2], h[0])
        except Stuck as s:
            if s.what != 'camp interrupted':
                raise
            (on_int or on_interrupt_factory(log))(g)
            continue
        log.append((g.frame, 'heal', pick[3], pick[0], h[0]))
        n += 1
    if camp.in_camp(g):
        camp.close_camp(g)
    return n


def anyone_dead(g):
    return any(g.char(i)['status'] != 0 for i in g.party())


# statuses (docs/re/B-camp.md, status_has 0x800d5504): afraid 0x01, confused 0x02,
# poison 0x04, asleep 0x08, KO 0x10, paralysis 0x20, stone 0x40, dead 0x80, ash 0x100,
# lost 0x200. SERIOUS ones keep a member out of the fighting; the rest wait for a cure.
SERIOUS = 0x10 | 0x20 | 0x40 | 0x80 | 0x100 | 0x200
# camp cures, cheapest first (B-camp.md "The 26 camp spells", camp_spell_effect):
# (spell id, school, level, status bits it clears, whole party)
CURES = [(28, 1, 3, 0x20, False),      # Dialko: paralysis
         (31, 1, 4, 0x04, False),      # Latumofis: poison
         (56, 2, 5, 0x3f, True),       # Morfis: bits 0-5 for the party, stone stays
         (36, 1, 6, 0x7f, False),      # Madi: all but death and ash
         (39, 1, 7, 0x80, False)]      # Kadorto: the dead (a miss turns them to ash)
CURE_LOG = []           # chapters.Run points this at its log


def cure_in_camp(g, log=None, on_int=None, most=12):
    """Cure from camp what the party's spells can: for each member with a status (the
    out-of-action ones first, the dead last), the cheapest cure a standing caster has
    points for. Ash and the lost wait for the temple. Returns the casts made. The camp
    list's place for a spell is taken as its place among the caster's known spells of
    that level; a cast that changes nothing is tried once at the spell's slot instead."""
    log = CURE_LOG if log is None else log
    n = k = 0
    tried = set()
    while n < most and k < 30:
        k += 1
        if g.overlay() in ('JOUKA', 'HAZURE', 'BATTLE'):
            break
        if not camp.in_camp(g) and not maze.calm(g) and not maze.settle(g):
            (on_int or on_interrupt_factory(log))(g)
            continue
        slots = g.party_slots()
        pats = []
        for slot, ri in enumerate(slots):
            if ri is None:
                continue
            # fear alone isn't worth a point: an afraid member loses a turn 1 in 8 and
            # recovers in battle at min(3 x level, 35)% a round (D-battle.md), and town
            # clears it; a Madi went on it (b1v3d goal_10, 2026-10-14)
            st = g.char(ri)['status'] & ~0x01
            if st and not st & 0x300:
                pats.append((st & 0x80 != 0, -(st & SERIOUS), slot, ri, st))
        pick = None
        for _, _, tslot, tri, st in sorted(pats):
            for sid, sch, lv, bits, party in CURES:
                if not st & bits or (sid, tri) in tried:
                    continue
                if sid == 39 and sum(g.char(i)['gold'] for i in g.party()) >= \
                        250 * g.char(tri)['level']:
                    # Kadorto raises the dead on rand_upto(80) < Vit x 4 and turns a miss
                    # to ash (B-camp.md); the temple raises on rand_upto(99) < 60 + 2 x Vit
                    # (E-town.md). Mercury went to ash in camp after the Jail Ogre
                    # (2026-10-14). Kadorto only when the temple's fee is out of reach.
                    continue
                for cslot, cri in enumerate(slots):
                    if cri is None or cri == tri and st >= 0x20:
                        continue
                    c = g.char(cri)
                    if c['status'] >= 0x20 or not c['raw'][0x5c + sch * 7 + lv - 1]:
                        continue
                    ks = battle.known_spells(c['raw'], sch, lv)
                    if sid in ks:
                        pick = (cslot, sch, lv, ks.index(sid), sid % 3, None if party else tslot,
                                tri, st, sid)
                        break
                if pick:
                    break
            if pick:
                break
        if not pick:
            break
        cslot, sch, lv, idx, slot_idx, tslot, tri, st, sid = pick
        tried.add((sid, tri))
        for i in ([idx] if idx == slot_idx else [idx, slot_idx]):
            try:
                camp.cast(g, cslot, sch, lv, i, tslot)
            except Stuck as s:
                if s.what != 'camp interrupted':
                    raise
                (on_int or on_interrupt_factory(log))(g)
                break
            n += 1
            if g.char(tri)['status'] != st:
                break
        log.append((g.frame, 'cure', sid, g.char(tri)['name'], st, g.char(tri)['status']))
    # poison the spells couldn't cure: a Potion of Latumofis (Chris, 2026-10-14)
    if g.overlay() not in ('JOUKA', 'HAZURE', 'BATTLE') and (camp.in_camp(g) or maze.calm(g)):
        try:
            n += gear.potion_cure(g, log)
        except Stuck as s:
            if s.what != 'camp interrupted':
                raise
            (on_int or on_interrupt_factory(log))(g)
    if camp.in_camp(g):
        camp.close_camp(g)
    return n


def out_of_action(g):
    return [i for i in g.party() if g.char(i)['status'] & SERIOUS]


def needs_town(g):
    """Go home when someone is out of action and the party's own spells can't bring them
    back (cure_in_camp is tried first), or someone is badly hurt and no priest has
    points. A poisoned, afraid, confused or sleeping member carries on (2026-10-14:
    before, any status ended the trip)."""
    if anyone_dead(g):
        cure_in_camp(g)
        if out_of_action(g):
            return True
    return bool(hurt(g, 0.5)) and not priests(g)


def town_trip(g, log):
    """Walk out, raise the dead at the temple if the gold allows, Stables for everyone
    (spell points), back to the maze, then heal with Dios."""
    on_int = on_interrupt_factory(log)
    if GEAR:
        gear.camp_loot(g, log, on_int)
    maze.to_town(g, on_int)
    town_upkeep(g, log)
    town.begin_adventure(g)
    if GEAR:
        gear.camp_loot(g, log)
    heal_in_camp(g, log, frac=0.95)


def town_upkeep(g, log):
    """In town after a trip: pool the gold on the first member, raise the dead at the
    temple and put them back in the party, then a week in the Stables for each member
    (spell points; the Stables restore no HP). Members are picked by grid position: a
    death leaves a hole."""
    def first_pos():
        return next(k for k, x in enumerate(town.town_slots(g)) if x is not None)
    gold_note(g, log, 'arrive')
    g0 = party_gold(g)
    roster0 = roster_gold(g)
    if _DEPART[0] is not None:
        INCOME.append(roster0 - _DEPART[0])
    # the Thief first, then the Bishop, then by level (Chris, 2026-10-14: the chests and
    # the identifying need them)
    # A patient carrying their own fee comes first: the raise gives the gold back (b1v0f
    # chapter 6, 2026-10-14: 8,577 gold on a dead member, the temple "poor" for the rest)
    def carries_fee(ri):
        c = g.char(ri)
        return c['gold'] >= c['level'] * temple_rate(c['status'])
    def temple_pass():
        raised = []
        patients = sorted(town.temple_patients(g), key=lambda ri: (
            not carries_fee(ri), g.char(ri)['cls'] not in (3, 12), g.char(ri)['cls'] != 11,
            -g.char(ri)['level']))
        if patients:
            try:
                town.pool_gold(g, first_pos(), 'tavern')
            except Stuck as s:
                log.append((g.frame, 'pool stuck', s.what))
                town.to_town_bar(g)
            for ri in patients:
                try:
                    r = town.temple_heal(g, ri, first_pos())
                    log.append((g.frame, 'temple', ri, r))
                    if r.get('outcome') in ('healed', 'alive') if isinstance(r, dict) else r in ('healed', 'alive'):
                        raised.append(ri)
                        if ri in WAIT_FROM:
                            log.append((g.frame, 'raised after standby', g.char(ri)['name'],
                                        len(INCOME) - WAIT_FROM.pop(ri)))
                        if g.char(ri)['gold'] and len(town.town_party(g)) < 6:
                            # back in the party now, and their gold pooled for the next patient
                            town.to_town_bar(g)
                            town.form_party(g, [ri])
                            log.append((g.frame, 'rejoined', ri))
                            raised.remove(ri)
                            town.to_town_bar(g)
                            town.pool_gold(g, first_pos(), 'tavern')
                except Stuck as s:
                    log.append((g.frame, 'temple stuck', ri, s.what))
                town.to_town_bar(g)
            town.to_town_bar(g)
            for ri in raised:
                try:
                    town.form_party(g, [ri])
                    log.append((g.frame, 'rejoined', ri))
                except Stuck as s:
                    log.append((g.frame, 'rejoin stuck', ri, s.what))
                town.to_town_bar(g)

    gear.TRIED_VISIT.clear()
    temple_pass()
    gold_note(g, log, 'temple', g0)
    tablet_back(g, log)
    raised_back(g, log)
    # recruit only for a member who can't come back (refused, "Their alignments won't
    # mix."): one who is merely dead stays out of the party so they can rejoin once the
    # temple can raise them (r2v0: the Tablet's holder was replaced and the Shrine shut)
    refused = [x for x in log if len(x) > 3 and x[1] == 'rejoin stuck' and 'mix' in str(x[3])]
    # a member the temple can't raise yet waits there and a standby fills the place
    # (Chris, 2026-10-14: early on a player grinds the raise's gold with a stand-in)
    waiting_dead = [ri for ri in town.temple_patients(g) if g.char(ri)['status'] & 0x180]
    if refused or waiting_dead or len(town.town_party(g)) < 4:
        n0 = len(town.town_party(g))
        fill_party(g, log, size=6 if refused or waiting_dead else 4)
        if waiting_dead and len(town.town_party(g)) > n0:
            for ri in waiting_dead:
                WAIT_FROM.setdefault(ri, len(INCOME))
            log.append((g.frame, 'standby', [g.char(ri)['name'] for ri in waiting_dead],
                        len(town.town_party(g)) - n0))
    g1 = party_gold(g)
    healer = party_heals(g)
    for pos, ri in enumerate(town.town_slots(g)):
        if ri is None or g.char(ri)['status'] != 0:
            continue
        c = g.char(ri)
        if c['max_hp'] and c['hp'] < c['max_hp'] * COT_BELOW and not healer:
            # the Stables restore spell points but no HP: a member left at 1 HP with no
            # healer's points sent every trip straight home (f1v1c chapter 2, 2026-10-13:
            # 30 recover trips of 2,800 frames). A Cot heals, week by week, while the
            # gold lasts (gathered from the party)
            try:
                r = town.inn_stay(g, pos, 'Cot', weeks=None, gather=True)
                log.append((g.frame, 'cot', pos, r['weeks'], r['hp']))
                town.to_town_bar(g)
                continue
            except Stuck as s:
                log.append((g.frame, 'cot stuck', pos, s.what))
                town.to_town_bar(g)
        r = town.inn_stay(g, pos, 'Stables', weeks=1)
        log.append((g.frame, 'stables', pos, r['weeks']))
        town.to_town_bar(g)
    town.to_town_bar(g)
    if healer:
        heal_at_gate(g, log)
    gold_note(g, log, 'inn', g1)
    reorder_party(g, log)
    g2 = party_gold(g)
    if GEAR:
        # Boltac's: identify, uncurse, sell, buy (gear.shop), keeping a dead member's
        # raise in reserve; the party equips in camp once it sets out (Chris, 2026-10-14)
        try:
            # the reserve also holds the fees of members still at the temple (b1v0f
            # chapter 6, 2026-10-14: a hammer for a recruit with the Bishop in ashes)
            top = max(g.char(i)['level'] for i in town.town_party(g))
            waiting = sum(g.char(ri)['level'] * temple_rate(g.char(ri)['status'])
                          for ri in town.temple_patients(g) if g.char(ri)['level'] >= top - 3)
            res = raise_reserve(top)
            log.append((g.frame, 'reserve', res, waiting, round(sum(INCOME[-4:]) / max(1, len(INCOME[-4:])))))
            gear.shop(g, log, res + waiting)
        except Stuck as s:
            log.append((g.frame, 'shop stuck', s.what))
            town.to_town_bar(g)
        gold_note(g, log, 'shop', g2)
    # Boltac's sales can pay a raise the temple turned down: back to the temple (n1v1
    # chapter 7, agent 8, 2026-10-14: Eve's raise failed to ashes, Venus and Earth were
    # "poor" at 1,970, the sales made it 5,270 for their 5,250, and they waited a trip)
    gold_now = party_gold(g)
    if SECOND_TEMPLE and any(g.char(ri)['level'] * temple_rate(g.char(ri)['status']) <= gold_now
                             for ri in town.temple_patients(g)):
        before = set(town.town_party(g))
        log.append((g.frame, 'temple again', gold_now))
        temple_pass()
        raised_back(g, log)
        for pos, ri in enumerate(town.town_slots(g)):
            if ri is not None and ri not in before and g.char(ri)['status'] == 0:
                r = town.inn_stay(g, pos, 'Stables', weeks=1)
                log.append((g.frame, 'stables', pos, r['weeks']))
                town.to_town_bar(g)
        reorder_party(g, log)
        town.to_town_bar(g)
    # the gold rides with the member least likely to die (back row, the Bishop first),
    # not split six ways: a mass death no longer locks the raise money in the dead (n1v0
    # chapter 3, 2026-10-14: five dead with 1,300 each, the temple 'poor'). The shop
    # pools it on whoever buys
    try:
        k = gold_keeper(g)
        if k is not None:
            town.pool_gold(g, k, 'tavern')
            if SECOND_PURSE:
                second_purse(g, log, k)
    except Stuck as s:
        log.append((g.frame, 'pool stuck', s.what))
        town.to_town_bar(g)
        missing = [ri for ri in _PURSE_ORDER if ri not in town.town_party(g)]
        if missing:
            town.form_party(g, missing)
        _PURSE_ORDER.clear()
    town.to_town_bar(g)
    _DEPART[0] = roster_gold(g)


# Rows (main, 2026-10-14): the three best front-liners in front, by class first, then by
# how much they can take. Class ids: town.CLASSES.
MELEE = {0, 4, 5, 6, 7, 12, 13}     # Fighter, Samurai, Lord, Valkyrie, Ranger, Ninja, Monk
FRONT_NEXT = {2}                    # then the Priest; Thief, Mage, Bishop and the rest behind


def front_rank(g, ri):
    """Sort key for the front row: class tier, then max HP weighed by AC (lower AC first)."""
    c = g.char(ri)
    tier = 0 if c['cls'] in MELEE else 1 if c['cls'] in FRONT_NEXT else 2
    ac = struct.unpack('b', c['raw'][0x86:0x87])[0]
    return (tier, -c['max_hp'] * (1 + (10 - ac) / 10))


def reorder_party(g, log):
    """In town before setting out (town_upkeep, ahead of Boltac's so the gear follows the
    rows): put the three best front-liners (front_rank) in positions 0-2 and the rest
    behind, each row keeping its current order. The party is re-formed at the tavern from
    the first position that changes (members after it leave, then rejoin in order). Skipped
    while a death leaves a hole in the party."""
    slots = town.town_slots(g)
    party = [ri for ri in slots if ri is not None]
    if len(party) < 4 or None in slots[:len(party)]:
        return
    front = set(sorted(party, key=lambda ri: front_rank(g, ri))[:3])
    if set(party[:3]) == front:
        return
    want = [ri for ri in party if ri in front] + [ri for ri in party if ri not in front]
    k = next(i for i in range(len(party)) if party[i] != want[i])
    try:
        for pos in range(len(party) - 1, k - 1, -1):
            town.remove_member(g, pos)
        town.to_town_bar(g)
        town.form_party(g, want[k:])
        log.append((g.frame, 'reorder', [g.char(ri)['name'] for ri in party],
                    [g.char(ri)['name'] for ri in town.town_party(g)]))
    except Stuck as s:
        log.append((g.frame, 'reorder stuck', s.what))
        town.to_town_bar(g)
        missing = [ri for ri in want if ri not in town.town_party(g)]
        if missing:
            town.form_party(g, missing)
    town.to_town_bar(g)


def temple_rate(st):
    """The temple's fee per level for a status (E-town.md, temple_heal 0x800c95f0)."""
    return 500 if st & 0x100 else 250 if st & 0x80 else 200 if st & 0x40 else 100 if st & 0x20 else 0


def party_heals(g):
    """Someone in the party who stands and knows Dios: after the Stables they heal the
    rest from camp."""
    return any(g.char(ri)['status'] == 0 and 21 in battle.known_spells(g.char(ri)['raw'], 1, 1)
               for ri in town.town_party(g))


GATE_HEALS = 3              # rounds of heal-at-the-gate, Stables between


def heal_at_gate(g, log, on_int=None):
    """In town, someone under COT_BELOW of max HP: step out onto the Grounds, heal from
    camp with the strongest heals the priests have (heal_strong), step back in and take
    the Stables for the points; again while it helps. A Cot heals 1 HP a week, for 10
    gold and a week of age each (E-town.md; b1v3b chapter 4, 2026-10-14: about 19 Cot
    stays, some 5,000 gold, while the party couldn't pay for raises)."""
    for _ in range(GATE_HEALS):
        party = town.town_party(g)
        if not any(g.char(i)['status'] == 0 and g.char(i)['max_hp']
                   and g.char(i)['hp'] < g.char(i)['max_hp'] * COT_BELOW for i in party):
            return
        town.begin_adventure(g)
        n = heal_strong(g, log, frac=0.95, max_casts=20, on_int=on_int)
        maze.to_town(g, on_int)
        town.to_town_bar(g)
        log.append((g.frame, 'gate heal', n, [(g.char(i)['name'], g.char(i)['hp'], g.char(i)['max_hp'])
                                              for i in town.town_party(g)]))
        for pos, ri in enumerate(town.town_slots(g)):
            if ri is None or g.char(ri)['status'] != 0:
                continue
            town.inn_stay(g, pos, 'Stables', weeks=1)
            town.to_town_bar(g)
        if not n:
            return


INCOME = []         # roster gold each trip brought home (arrival less the last departure)
_DEPART = [None]    # roster gold as the party last left town
WAIT_FROM = {}      # roster index -> len(INCOME) when a standby took their place
RAISE_TRIPS = 2     # a raise costing under this many trips' income keeps no reserve


def roster_gold(g):
    return sum(g.char(i)['gold'] for i in range(g.roster_count()))


def raise_reserve(top):
    """The gold Boltac's keeps back (Chris, 2026-10-14): none while a raise from death
    (temple: level x 250) costs less than RAISE_TRIPS trips' income (the last four trips'
    mean): a standby fills in and the party grinds the raise; above that line two raises
    at the top level (GEAR_RESERVE). With no trips measured yet, the two raises."""
    inc = INCOME[-4:]
    if inc and 250 * top < RAISE_TRIPS * sum(inc) / len(inc):
        return 0
    return GEAR_RESERVE * top


def gold_keeper(g):
    """Party position to hold the gold: the Bishop in the back row, else the back-row
    member with the most HP, else the first member."""
    slots = town.town_slots(g)
    here = [(p, ri) for p, ri in enumerate(slots) if ri is not None and g.char(ri)['status'] == 0]
    if not here:
        return None
    back = [(p, ri) for p, ri in here if p >= 3]
    for p, ri in back:
        if g.char(ri)['cls'] == gear.BISHOP:
            return p
    if back:
        return max(back, key=lambda x: g.char(x[1])['max_hp'])[0]
    return here[0][0]


SECOND_PURSE = True
SECOND_TEMPLE = True       # agent 8: the temple again after Boltac's when a fee is affordable
_PURSE_ORDER = []


def purse_holder(g, k):
    """Party position for the second purse: the standing back-row member other than the
    keeper with the most HP, else any other standing member."""
    slots = town.town_slots(g)
    here = [(p, ri) for p, ri in enumerate(slots) if ri is not None and p != k
            and g.char(ri)['status'] == 0]
    back = [x for x in here if x[0] >= 3] or here
    return max(back, key=lambda x: g.char(x[1])['max_hp'])[0] if back else None


def second_purse(g, log, k):
    """With the gold pooled on the keeper (position k): a second member holds at least one
    raise (temple: 250 x the top level) where the gold allows (main, 2026-10-14: Cy, the
    Bishop and keeper, died on a walk home with all 17,036 gold; the temple's payer must
    be in the party, temple_heal 0x800c95f0, so the dead keep theirs until raised). The
    tavern only pools or divides evenly, so the divide runs m ways (m = gold // raise,
    2-6) with the others out of the party, the purse member steps out while the rest is
    pooled back on the keeper, and the tail is re-formed in its old order."""
    slots = town.town_slots(g)
    order = [ri for ri in slots if ri is not None]
    if len(order) < 2 or None in slots[:len(order)]:
        return
    top = max(g.char(ri)['level'] for ri in order)
    fee = 250 * top
    total = sum(g.char(ri)['gold'] for ri in order)
    p = purse_holder(g, k)
    if p is None or total < fee:
        return
    m = min(len(order), max(2, total // fee))
    leave = [pos for pos in range(len(order) - 1, -1, -1) if pos not in (k, p)][:len(order) - m]
    j = min(leave + [p])
    _PURSE_ORDER[:] = order
    for pos in leave:                       # highest first: removing leaves a hole
        town.remove_member(g, pos)
    town.to_town_bar(g)
    town.divide_gold(g)
    town.to_town_bar(g)
    town.remove_member(g, p)
    town.to_town_bar(g)
    town.pool_gold(g, k, 'tavern')
    town.to_town_bar(g)
    for pos in range(len(order) - 1, j - 1, -1):
        if town.town_slots(g)[pos] is not None:
            town.remove_member(g, pos)
    town.to_town_bar(g)
    town.form_party(g, order[j:])
    town.to_town_bar(g)
    if [ri for ri in town.town_slots(g) if ri is not None] != order:
        log.append((g.frame, 'purse order', [g.char(ri)['name'] for ri in town.town_party(g)]))
    pr, kr = order[p], order[k]
    log.append((g.frame, 'purse', g.char(pr)['name'], g.char(pr)['gold'], g.char(kr)['name'],
                g.char(kr)['gold'], fee, m))
    _PURSE_ORDER.clear()


def party_gold(g):
    return sum(g.char(i)['gold'] for i in (g.party() or town.town_party(g)))


def gold_note(g, log, what, before=None):
    """('gold', what, change, party gold, roster gold): where the gold goes (b1v3b chapter
    4, 2026-10-14, ended with none; the logs had no gold in them)."""
    now = party_gold(g)
    roster = sum(g.char(i)['gold'] for i in range(g.roster_count()))
    log.append((g.frame, 'gold', what, None if before is None else now - before, now, roster))


def leave_party(g, log, pos):
    """Take party position pos out, after pooling the gold on another member (b1v3b
    chapter 4, 2026-10-14: Uranus left with the party's 706 gold)."""
    slots = town.town_slots(g)
    ri = slots[pos]
    other = next((p for p, x in enumerate(slots) if x is not None and p != pos), None)
    if other is not None and g.char(ri)['gold']:
        try:
            town.pool_gold(g, other, 'tavern')
        except Stuck as s:
            log.append((g.frame, 'pool stuck', s.what))
        town.to_town_bar(g)
    town.remove_member(g, pos)
    log.append((g.frame, 'removed', ri, g.char(ri)['name']))
    return ri


RAISED_BACK = 2             # a member in the tavern this many levels above the party's lowest swaps in


def raised_back(g, log):
    """A member the temple raised who couldn't rejoin a full party (recruits filled the
    places of the dead) takes the place of its lowest-level member (b1v3b chapter 4,
    2026-10-14: Earth, a level-11 Priest, was raised for 2,750 gold and sat in the tavern
    while a level-8 recruit played on). The Tablet's holder stays."""
    tried = set()
    for _ in range(6):
        slots = town.town_slots(g)
        here = [p for p, ri in enumerate(slots) if ri is not None]
        if len(here) < 6:
            return
        cands = [i for i in town.tavern_candidates(g)
                 if i not in tried and g.char(i)['status'] == 0]
        if not cands:
            return
        ri = max(cands, key=lambda i: (g.char(i)['level'], -i))
        def only_one(p):
            # the party's only Thief (or Ninja) or only Bishop stays (Chris, 2026-10-14)
            for kind in ((3, 12), (11,)):
                if g.char(slots[p])['cls'] in kind and sum(
                        1 for q in here if g.char(slots[q])['cls'] in kind) == 1:
                    return True
            return False
        out = [p for p in here if not only_one(p)
               and not any((it & 0xfff) == TABLET for it in g.char(slots[p])['items'])]
        if not out:
            return
        pos = min(out, key=lambda p: (g.char(slots[p])['level'], -p))
        if g.char(ri)['level'] < g.char(slots[pos])['level'] + RAISED_BACK:
            return
        tried.add(ri)
        try:
            gone = leave_party(g, log, pos)
            town.to_town_bar(g)
            town.form_party(g, [ri])
            log.append((g.frame, 'raised back', ri, g.char(ri)['name'], g.char(gone)['name']))
        except Stuck as s:
            log.append((g.frame, 'raised back stuck', ri, s.what))
            town.to_town_bar(g)
            if len(town.town_party(g)) < 6:
                try:
                    town.form_party(g, [gone])
                except Stuck:
                    pass
        town.to_town_bar(g)


GEAR = True
GEAR_RESERVE = gear.RESERVE_PER_LEVEL   # gold kept back per level of the highest member: two raises (250 a level).
                            # At 300 (one raise) the chains were too poor for the temple in chapter 3


COT_BELOW = 0.6               # a member under this share of max HP rests in a Cot


def tablet_back(g, log):
    """The Tablet's holder raised and waiting in the tavern while the party is full of
    recruits: take out the lowest-level member and put the holder back (r3v0 chapter 3,
    2026-10-13: Mercury came back from the temple with the Tablet, "rejoin stuck", and
    30 recover trips followed)."""
    if TABLET in party_items(g):
        return
    holder = next((i for i in town.tavern_candidates(g)
                   if any((it & 0xfff) == TABLET for it in g.char(i)['items'])), None)
    if holder is None:
        return
    try:
        slots = town.town_slots(g)
        if len(town.town_party(g)) >= 6:
            pos = min((p for p, ri in enumerate(slots) if ri is not None),
                      key=lambda p: g.char(slots[p])['level'])
            leave_party(g, log, pos)
            town.to_town_bar(g)
        town.form_party(g, [holder])
        log.append((g.frame, 'tablet back', holder, g.char(holder)['name']))
    except Stuck as s:
        log.append((g.frame, 'tablet back stuck', holder, s.what))
        town.to_town_bar(g)
        if 'mix' in str(s.what):
            make_room_for(g, holder, log)
    town.to_town_bar(g)


def make_room_for(g, holder, log):
    """Take members out, lowest level first, until the game lets `holder` join; then
    fill the party back up with whoever it will take."""
    for _ in range(6):
        slots = town.town_slots(g)
        here = [p for p, ri in enumerate(slots) if ri is not None]
        if not here:
            break
        pos = min(here, key=lambda p: g.char(slots[p])['level'])
        try:
            leave_party(g, log, pos)
        except Stuck as s:
            log.append((g.frame, 'remove stuck', slots[pos], s.what))
            break
        town.to_town_bar(g)
        try:
            town.form_party(g, [holder])
            log.append((g.frame, 'tablet back', holder, g.char(holder)['name']))
            town.to_town_bar(g)
            break
        except Stuck as s:
            town.to_town_bar(g)
            if 'mix' not in str(s.what):
                log.append((g.frame, 'tablet back stuck', holder, s.what))
                break
    fill_party(g, log)


def fill_party(g, log, size=6):
    """Fill the party from the tavern, highest level first, when a member can't come back
    (still dead, or "Their alignments won't mix."; c2v3 2026-10-13 kept failing every
    goal with five members)."""
    tried = set()
    while len(town.town_party(g)) < size:
        cand = [i for i in town.tavern_candidates(g) if i not in tried]
        if not cand:
            break
        ri = max(cand, key=lambda i: (g.char(i)['level'], -i))
        tried.add(ri)
        try:
            town.form_party(g, [ri])
            log.append((g.frame, 'recruited', ri, g.char(ri)['name'], g.char(ri)['level']))
        except Stuck as s:
            log.append((g.frame, 'recruit stuck', ri, s.what))
        town.to_town_bar(g)


# --- the run ---

class Run:
    def __init__(self, g, seed=0, variant=0, out='t3/run0', retries=6, auto_cases=True):
        self.g = g
        self.seed = seed
        self.variant = variant % len(VARIANTS)
        self.out = out
        self.rng = random.Random(seed)
        self.log = []
        self.goals = []
        self.stuck = []
        self.retries = retries
        self.ckpt = None
        self.auto_cases = auto_cases
        os.makedirs(os.path.join(OUT, out), exist_ok=True)

    def checkpoint(self, name):
        self.ckpt = '%s/goal_%02d_%s' % (self.out, len(self.goals), name)
        self.g.save(self.ckpt)

    def note(self, *a):
        self.log.append((self.g.frame,) + a)

    def fail_sig(self, r):
        """What a failed try ended on: its result and its last fight (place, monster groups,
        rounds, runs, HP and who was down at the end), or None without a fight."""
        for x in reversed(self.log):
            if len(x) > 1 and x[1] == 'retry':
                return None
            if len(x) > 2 and x[1] == 'fought' and isinstance(x[2], dict):
                f = x[2]
                mons = tuple((q.get('id'), q.get('n')) for q in (f.get('first') or {}).get('groups', []))
                return (r, mons, f.get('rounds'), str(f.get('runs')), f.get('hp_end'),
                        tuple(f.get('down_end') or ()))
        return None

    def goal(self, name, fn):
        """Run goal fn until it returns True; a Stuck, a wipe or a False reloads the last
        checkpoint and tries again (up to retries)."""
        g = self.g
        t0, f0 = time.time(), g.frame
        tries = 0
        while True:
            tries += 1
            battle.VARY = tries - 1
            try:
                r = fn()
            except Wiped:
                r = 'wiped'
            except Stuck as s:
                tag = '%s/stuck_%02d_%s_%d' % (self.out, len(self.goals), name, tries)
                try:
                    g.shot(tag)
                    g.save(tag)
                except Exception:
                    pass
                self.stuck.append(dict(goal=name, try_=tries, what=s.what,
                                       info={k: str(v) for k, v in s.info.items()},
                                       where=g.where(), state=tag))
                if self.auto_cases:
                    # the ratchet: every stuck state becomes a permanent regression case
                    from harness import regress
                    # the party goal can't resume mid-creation: its case starts from
                    # power-on with this run's variant and seed
                    regress.add_case(dict(id='stuck:' + tag, kind='stuck',
                                          state=None if name == 'party' else tag,
                                          goal=name, what=s.what, source=self.out,
                                          variant=self.variant, seed=self.seed,
                                          chapter=getattr(self, 'chapter', 1)))
                r = 'stuck'
            if r is True:
                break
            if tries >= self.retries:
                raise Stuck('goal failed', goal=name, last=r)
            # the game's rolls don't move with time (battle.VARY), so a try that ended on
            # the same fight the same way as the last one is a replay: n1v0d chapter 3 ran
            # from the same 14 Wing Lizards at 178 HP six times. Stop instead of replaying
            sig_ = self.fail_sig(r)
            if sig_ is not None and sig_ == getattr(self, '_last_fail', None) and self._last_fail_goal == name:
                raise Stuck('goal replays', goal=name, last=r, sig=str(sig_))
            self._last_fail, self._last_fail_goal = sig_, name
            self.note('retry', name, r)
            if self.ckpt:
                g.load(self.ckpt)
            g.step(self.rng.randrange(1, 40))     # different timing, different rolls
        battle.VARY = 0
        self.goals.append(dict(goal=name, frames=g.frame - f0, secs=round(time.time() - t0, 1),
                               tries=tries))
        self.checkpoint(name)

    def run(self, boot=True):
        g = self.g
        if boot:
            # the party goal retries from power-on: creation can't be resumed midway
            g.step(1)
            self.ckpt = '%s/boot' % self.out
            g.save(self.ckpt)
            self.goal('party', self.make_party)
            self.goal('enter', lambda: town.begin_adventure(g) is not None)
        # train first (the guardians kill level 4-5 parties); each trip is a goal
        k = 0
        while not self.trained() and k < 60:
            k += 1
            self.goal('train_%02d' % k, self.train_trip)
        # resuming from a goal state: the pillars are done in order, so skip as many as
        # there are stones already
        done = stone_count(g)
        for name, xy in PILLARS[done:]:
            self.goal('pillar_' + name, lambda name=name, xy=xy: self.pillar(name, xy))
        self.goal('tablet_door', lambda: self.door())
        g.flush_shots()
        return self.report()

    def make_party(self):
        g = self.g
        g.step(self.rng.randrange(0, 120))
        town.new_game(g)
        made = []
        for k, (name, race, sex, align, cls) in enumerate(VARIANTS[self.variant]):
            try:
                r = town.create_character(g, name, race, sex, align, cls,
                                          reroll_delay=lambda j: 3 + (j * 7 + self.seed + k) % 23)
            except Stuck as s:
                if 'class' not in s.what and 'reroll' not in s.what:
                    raise
                town.to_town_bar(g)
                r = town.create_character(g, name, race, sex, align, 'Fighter',
                                          reroll_delay=lambda j: 3 + (j * 7 + self.seed + k) % 23)
                self.note('class fallback', name, cls)
            made.append(r['index'])
        names = {g.name(i): i for i in range(g.roster_count())}
        town.form_party(g, [names[n] for n in PREMADE_GOOD] + made)
        return True

    def upkeep(self):
        g = self.g
        if needs_town(g):
            town_trip(g, self.log)
        else:
            heal_in_camp(g, self.log)

    def train_trip(self):
        """One training trip on the Grounds: fight until TRAIN_TRIP_FIGHTS fights or
        someone needs town, then a town trip (Stables: spell points and level-ups;
        temple). Counts only if everyone comes home alive or is raised."""
        g = self.g
        if g.overlay() == 'JOUKA':
            town.begin_adventure(g)
            if GEAR:
                if hasattr(self, 'set_out_loot'):
                    # chapters.Run: the setting-out camp with the Bishop's risky tries
                    # (n1 chains, 2026-10-14: chapter 1 never had one, so 1-5 risky unknowns
                    # stayed in the packs all chapter)
                    self.set_out_loot()
                else:
                    gear.camp_loot(g, self.log)
            heal_in_camp(g, self.log, frac=0.95)
        fights = []
        log = self.log
        def on_int(g):
            n = sum(1 for x in log if len(x) > 1 and x[1] == 'fought')
            r = play.handle_interrupt(g, Ch1Policy, log)
            if party_wiped(g):
                raise Wiped()
            if sum(1 for x in log if len(x) > 1 and x[1] == 'fought') > n:
                fights.append(g.frame)
            return r
        avoid = set()
        for (x, y) in PITS:
            for d in range(4):
                nx, ny = x - maze.DIRV[d][0], y - maze.DIRV[d][1]
                avoid.add((nx, ny, d))
        walks = 0
        while len(fights) < TRAIN_TRIP_FIGHTS and walks < 40:
            if needs_town(g):
                break
            if hurt(g, 0.6) and priests(g):
                heal_in_camp(g, log)
            wm = maze.wallmap(g)
            here = g.pos()
            closed = maze.site_closed(0) | PITS
            for _ in range(100):
                t = (self.rng.randrange(1, 23), self.rng.randrange(1, 23))
                p = maze.bfs(wm, here, t, avoid, closed)
                if p and 3 <= len(p) <= 12:
                    break
            else:
                t = None
            if t:
                try:
                    maze.walk_to(g, t[0], t[1], on_int, avoid=avoid)
                except Stuck as e:
                    # a step refused on the way can leave a random target unreachable;
                    # any other square will do for training
                    if e.what != 'no path':
                        raise
            walks += 1
        if GEAR:
            gear.camp_loot(g, log, on_int)
        maze.to_town(g, on_int)
        town_upkeep(g, log)
        if anyone_dead(g) or any(g.char(i)['status'] != 0 for i in town.town_party(g)):
            return 'casualties'
        if len(town.town_party(g)) < 6:
            return 'casualties'
        return True

    def trained(self):
        g = self.g
        return min(g.char(i)['level'] for i in (g.party() or town.town_party(g))) >= TRAIN_LEVEL

    def pillar(self, name, xy):
        """Set out rested (a town trip unless the party has just entered), take the
        pillar, and count it only if nobody died: the dead carry their stones to the
        temple, and an early party can't pay to raise them. A death reloads the last
        goal state, as a player would reload."""
        g = self.g
        if g.overlay() == 'JOUKA':
            town.begin_adventure(g)
            heal_in_camp(g, self.log, frac=0.95)
        elif self.goals and self.goals[-1]['goal'] != 'enter':
            town_trip(g, self.log)
        r = do_pillar(g, name, xy, self.log)
        if r is True and anyone_dead(g):
            # won with losses: it counts if the temple can bring everyone back
            town_trip(g, self.log)
            if anyone_dead(g) or len(g.party()) < 6:
                return 'casualties'
        return r

    def door(self):
        g = self.g
        if g.overlay() == 'JOUKA':
            town.begin_adventure(g)
        self.upkeep()
        return do_door(g, self.log)

    def report(self):
        g = self.g
        return dict(seed=self.seed, variant=self.variant, goals=self.goals, stuck=self.stuck,
                    frames=sum(x['frames'] for x in self.goals),
                    secs=round(sum(x['secs'] for x in self.goals), 1),
                    party=[(g.char(i)['name'], g.char(i)['level'], g.char(i)['status'])
                           for i in (g.party() or town.town_party(g))],
                    messages=len(g.cap.messages) if g.cap else 0)
