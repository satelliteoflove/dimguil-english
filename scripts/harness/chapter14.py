"""Walkthrough chapter 14, Area D: the god's name and the small door (2026-10-15).

Source: data/walkthrough/dim/14-area-d.json, data/maps/dim/f18.json and f32-f34.json (Area
D B3 to B1, areas 32-34; mimicry/ for the maps after the crystal), and MAZE: square_examine
0x800bb790 (0x2c the altar, 2 the locked doors, 0x51 the small door), the glyph pad
0x800b989c (word 3 ENERGY sets story bit 7 at Area X's pedestal, FUN_800ba32c; word 5
DIMGUIL at the altar), the dispatcher 0x800c1070 (0x1c Mother's fight, 0x1f the small
door's member pick), the locked-door menu 0x800ae1c8, maze_prompt_result 0x800befcc
(0x16 the altar's Tablet, 0x18 the crystal), the gold check 0x800b7508, the fight reward
0x800c0748 and the floor load 0x800a8f1c. Site squares E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  energy     story_flags (0x80079b44) bit 7: ENERGY at Area X's pedestal (chapter6.
             pedestal_word; it needs the silver stone). It unseals the side south of Area X
             (12, 15), the way to the lift at E12 N7 (12, 16) down to D-B3 E12 N23 (12, 0).
  mother     story_flags bit 23: the altar at B3 E11 N19 (11, 4), Investigate facing south,
             with the Tablet: EVENTMES 199, Yes, EVENTMES 203 and 201, then the glyph pad;
             DIMGUIL, END, EVENTMES 205 and Mother's fight (fight type 0xd; the win is
             reward type 0xb, bit 23). With bit 23 the floor load opens every wall of
             (11, 5), the only way on (nav.EXTRA_OPEN_AFTER).
  guardians  story_flags bit 18: the fifth Guardians' fixed fight on arriving at B3 E10 N9
             (10, 14) (square_arrive 0x65 p1 18, EVENTMES 284), past the CORE door.
  unlock     bit 6 of 0x800795fc: B2's locked door south of E13 N12 (13, 11), the way from
             B3's ladder (13, 10) to B2's ladder up at (13, 13). Investigate facing south
             opens the locked-door menu (game_state 8): a member, then Pick the lock (the
             menu's first line) or Calnova (the second); nobody here knows Calnova.
  warning    the carved warning on the door north of B1 E10 N11 (10, 12) (0x20, EVENTMES
             130). No flag; proved by the captured string.
  crystal    story_flags bit 10, mimicry mode off: B1 E10 N12 (10, 11), Investigate facing
             north (0x51) with the Gold Gauntlets in the party: EVENTMES 222, then "who
             goes in" (game_state 0x11, the party picker). The one picked must wear all
             four gold pieces (0x13d-0x140 with the equipped bit, 0x800b7508), else they're
             ashes. The goal puts the set on the member who can wear all four and holds
             the most (dress: Give with a swap when packs are full, then Equip preferring
             the gold).
  out        back in town over the new maps (nav reads mimicry/ once bit 10 is set).
Not done: COCKPIT (B2 E2 N14, after the change) and the dreamland doors; the King's
reward.
"""
import struct
from harness import chapters, chapter1, chapter6, gear, maze, nav, play, ui
from harness.game import Stuck

STORY = 0x80079b44
DOORS = nav.DOOR_BITS
GOLD = (0x13d, 0x13e, 0x13f, 0x140)    # armor, gauntlets, boots, helm
ALTAR = (32, 11, 4)
GUARDS = (32, 10, 14)
B2_DOOR = (33, 13, 11)
SMALL = (34, 10, 11)
LOCK_STATE, PICK_STATE = 8, 0x11
SUB = 0x80079790                        # the locked-door menu's step
LOCK_CUR = 0x8007b716                   # its cursor (s16): -0x26 Pick, -0x1a Calnova, -0xe leave
PICK_LOCK = -0x26
PENDING = 0x80079907                    # maze_prompt_pending
PICK_X, PICK_Y = 0x8007b6f0, 0x8007b6f2   # party picker (s16): x -99/1/101, y 0x48 front, 0x62 back


def s16(g, a):
    return struct.unpack('<h', g.e.read(a, 2))[0]


def said(g, n, idx):
    return not g.cap or any(m['file'] == 'EVENTMES.BIN' and m['idx'] == idx
                            for m in g.cap.messages[n:])


def here(g):
    return (g.u8(maze.AREA),) + g.pos()


def pick_slot(g, slot, what):
    """The party picker (MAZE 0x800ac798) to party slot `slot`, then circle."""
    want_y = 0x62 if slot >= 3 else 0x48
    want_x = (-99, 1, 101)[slot % 3]
    for _ in range(12):
        if s16(g, PICK_Y) == want_y:
            break
        y = s16(g, PICK_Y)
        ui.press_until(g, 'down', lambda: s16(g, PICK_Y) != y, 60, what + ' row')
    for _ in range(12):
        if s16(g, PICK_X) == want_x:
            break
        x = s16(g, PICK_X)
        ui.press_until(g, 'right' if want_x > x else 'left', lambda: s16(g, PICK_X) != x, 60,
                       what + ' column')
    if (s16(g, PICK_X), s16(g, PICK_Y)) != (want_x, want_y):
        raise Stuck('party picker', want=slot, at=(s16(g, PICK_X), s16(g, PICK_Y)))
    g.tap('circle')
    g.step(10)


def drive(g, step, limit=4000):
    """Press an event along: step(g) handles the states this event owns (True when it
    did something); boxes are closed and Yes/No answered Yes. Returns once the maze has
    been calm for chapter1.QUIET frames (or the overlay leaves the maze)."""
    f0 = g.frame
    while g.frame - f0 < limit:
        if g.overlay() == 'BATTLE':
            return
        if step(g):
            continue
        if g.u8(maze.GAME_STATE) == play.PROMPT:
            ui.move_cursor(g, play.PROMPT_CURSOR, 0, 'down', 'up', what='event yes')
            ui.confirm_until(g, lambda: g.u8(maze.GAME_STATE) != play.PROMPT, 300, 'event yes')
            continue
        if g.u8(PENDING) and g.u8(maze.GAME_STATE) == 0:
            # a prompt's outcome still to run: after the small door's pick, prompt 0x18
            # waits ~1,200 calm frames (the crystal's movie loading) before EVENTMES 224
            # (c14v3s: the drive called that calm and the goal failed twice)
            g.step()
            continue
        if maze.calm(g):
            for _ in range(chapter1.QUIET):
                g.step()
                if not maze.calm(g):
                    break
            else:
                return
            continue
        if g.u8(maze.EVENT_BOX) or maze.box_up(g):
            play.close_box(g)
            continue
        if g.u8(maze.GAME_STATE) == 0 and g.u8(maze.MSG) == 2:
            # a help-bar line that waits for a press ("* Success! *" after a picked lock:
            # c14v3r, "event drive" with the door open; neither box test sees it)
            g.step(20)
            if g.u8(maze.GAME_STATE) == 0 and g.u8(maze.MSG) == 2:
                ui.press_until(g, 'circle', lambda: g.u8(maze.MSG) != 2, 120, 'help line')
            continue
        g.step()
    raise Stuck('event drive', where=g.where())


def wearer(g):
    """Party slot of the member to wear the gold set: standing, able to wear all four
    (the armor: Fighter, Samurai or Lord), holding the most pieces, then the most HP."""
    best = None
    for pos, ri in enumerate(g.party_slots()):
        if ri is None or g.char(ri)['status']:
            continue
        if not all(gear.usable(g, ri, gear.item(g, i)) for i in GOLD):
            continue
        held = sum(1 for _, w in gear.pack(g, ri) if w & 0x1ff in GOLD)
        key = (held, g.char(ri)['max_hp'])
        if best is None or key > best[0]:
            best = (key, pos)
    return None if best is None else best[1]


def worn_gold(g, ri):
    return {w & 0x1ff for _, w in gear.pack(g, ri) if w & gear.EQUIPPED and w & 0x1ff in GOLD}


def gold_out(g):
    """{piece name: holder} for gold pieces not in the party (a standby's, a lost
    member's), or {} if all four ride with it. Not in the roster at all: 'nobody'."""
    from harness import town
    party = set(g.party() or town.town_party(g))
    have = {w & 0x1ff for ri in party for _, w in gear.pack(g, ri)}
    out = {}
    for i in GOLD:
        if i in have:
            continue
        who = [g.char(ri)['name'] for ri in range(g.roster_count())
               if any(w & 0x1ff == i for _, w in gear.pack(g, ri))]
        out[gear.name(i)] = who[0] if who else 'nobody'
    return out


def holder(g, piece, but):
    for pos, ri in enumerate(g.party_slots()):
        if ri is None or pos == but:
            continue
        for k, w in gear.pack(g, ri):
            if w & 0x1ff == piece:
                return pos, k
    return None


def dress(run, pos):
    """All four gold pieces onto the member at party slot pos, in camp where the party
    stands. True once they're worn."""
    g, log = run.g, run.log
    ri = g.party_slots()[pos]
    for _ in range(10):
        if worn_gold(g, ri) == set(GOLD):
            return True
        held = {w & 0x1ff for _, w in gear.pack(g, ri)}
        missing = [i for i in GOLD if i not in held]
        if not missing:
            gear.equip(g, pos, log, prefer=GOLD)
            continue
        h = holder(g, missing[0], pos)
        if h is None:
            raise chapter1.Blocked('gold piece missing: %s' % gear.name(missing[0]))
        hpos, k = h
        if len(gear.pack(g, ri)) < 10:
            gear.give(g, hpos, k, pos, log)
            continue
        spare = [j for j, w in gear.pack(g, ri)
                 if not w & (gear.EQUIPPED | gear.CURSED) and w & 0x1ff not in GOLD]
        if not spare:
            if held & set(GOLD) - worn_gold(g, ri):
                # wearing the pieces it holds frees what they replace
                gear.equip(g, pos, log, prefer=GOLD)
                continue
            run.note('no spare slot for the gold', g.char(ri)['name'])
            return False
        gear.give(g, pos, spare[0], hpos, log, swap=k)
    return worn_gold(g, ri) == set(GOLD)


@chapters.chapter
class Chapter14:
    n = 14
    title = "Area D: the god's name and the small door"

    def goals(self, run):
        g = run.g

        def energy():
            if nav.flag(g, STORY, 7):
                return True
            run.fit()
            return chapter6.pedestal_word(run, 'ENERGY', 7)

        def at(dest, facing):
            for _ in range(3):
                run.go(dest)
                if not maze.face(g, facing):
                    run.after()
                if here(g) == dest and g.u8(maze.FACE) == facing:
                    return True
            return False

        def mother():
            if nav.flag(g, STORY, 23):
                return True
            if not nav.flag(g, STORY, 7):
                return False
            run.ready()
            run.go(ALTAR)
            while run.door_ready():
                run.ready(train=False)
                run.go(ALTAR)
            run.heal()
            if not at(ALTAR, 2):
                return False
            chapter1.investigate(g)
            typed = []

            def step(g):
                if g.u8(maze.GAME_STATE) == chapter6.PAD_STATE and not typed:
                    g.step(20)
                    chapter6.pad_type(g, 'DIMGUIL')
                    typed.append(g.frame)
                    run.log.append((g.frame, 'altar', 'DIMGUIL'))
                    return True
                return False
            drive(g, step)
            run.after()
            if not nav.flag(g, STORY, 23):
                return False
            return run.all_home() or 'casualties'

        def guardians():
            if nav.flag(g, STORY, 18):
                return True
            if not nav.flag(g, STORY, 23):
                return False
            run.ready()
            run.go((32, 10, 15))
            while run.door_ready():
                run.ready(train=False)
                run.go((32, 10, 15))
            run.heal()
            run.go(GUARDS)
            run.after()
            if not nav.flag(g, STORY, 18):
                return False
            return run.all_home() or 'casualties'

        def unlock():
            if nav.flag(g, DOORS, 6):
                return True
            if not nav.flag(g, STORY, 18):
                return False
            run.fit()
            for k in range(8):
                if not at(B2_DOOR, 2):
                    return False
                chapter1.investigate(g)
                slots = g.party_slots()
                thief = next((p for p, ri in enumerate(slots) if ri is not None
                              and g.char(ri)['cls'] == 3 and not g.char(ri)['status']), None)
                who = thief if thief is not None else next(
                    p for p, ri in enumerate(slots) if ri is not None and not g.char(ri)['status'])

                def step(g):
                    if g.u8(maze.GAME_STATE) != LOCK_STATE:
                        return False
                    sub = g.u8(SUB)
                    if sub == 2:
                        g.step(10)
                        pick_slot(g, who, 'lock picker')
                    elif sub == 4 and s16(g, LOCK_CUR) != PICK_LOCK:
                        c = s16(g, LOCK_CUR)
                        ui.press_until(g, 'up', lambda: s16(g, LOCK_CUR) != c, 60, 'lock menu')
                    elif sub in (0, 4):
                        g.step(10)
                        ui.press_until(g, 'circle', lambda: g.u8(SUB) != sub
                                       or g.u8(maze.GAME_STATE) != LOCK_STATE, 120, 'lock menu')
                    else:
                        g.step()
                    return True
                drive(g, step)
                run.after()
                ok = nav.flag(g, DOORS, 6)
                run.log.append((g.frame, 'pick lock', k, ok))
                if ok:
                    return True
            return False

        def warning():
            if not nav.flag(g, DOORS, 6) and not nav.flag(g, STORY, 10):
                return False
            n = len(g.cap.messages) if g.cap else 0
            run.fit()
            run.examine((34, 10, 12), 0)
            return here(g) == (34, 10, 12) and said(g, n, 130)

        def crystal():
            if nav.flag(g, STORY, 10):
                return True
            if not nav.flag(g, DOORS, 6):
                return False
            out = gold_out(g)
            if out:
                # a standby holds pieces: a town visit's backups bring them back
                # (gear.backup_plan's quest takes)
                run.note('gold set out of the party', out)
                run.trip_home('gold set')
                out = gold_out(g)
                if out:
                    raise chapter1.Blocked('gold set out of the party: %s' % out)
            run.fit()
            run.go(SMALL)
            run.after()
            pos = wearer(g)
            if pos is None:
                run.note('nobody can wear the gold set')
                return False
            if not dress(run, pos):
                return False
            ri = g.party_slots()[pos]
            run.note('gold set on', g.char(ri)['name'])
            if not at(SMALL, 0):
                return False
            chapter1.investigate(g)

            def step(g):
                if g.u8(maze.GAME_STATE) != PICK_STATE:
                    return False
                g.step(10)
                p = g.party_slots().index(ri)
                pick_slot(g, p, 'small door')
                run.log.append((g.frame, 'small door', g.char(ri)['name']))
                return True
            drive(g, step, limit=12000)
            run.after()
            return nav.flag(g, STORY, 10)

        def out():
            if g.overlay() in ('JOUKA', 'HAZURE'):
                return True
            run.trip_home('chapter end')
            return g.overlay() in ('JOUKA', 'HAZURE')

        yield from run.recover_goals()
        yield 'energy', energy
        yield from run.recover_goals()
        yield 'mother', mother
        yield 'guardians', guardians
        yield 'unlock', unlock
        yield 'warning', warning
        yield 'crystal', crystal
        yield 'out', out
