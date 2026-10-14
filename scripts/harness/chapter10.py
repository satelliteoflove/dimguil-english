"""Walkthrough chapter 10, the vault in Area B and the red stone (2026-10-14).

Source: data/walkthrough/dim/10-red-stone.json, data/maps/dim/f23.json to f27.json (Area B
B5 to B1, areas 23-27), and MAZE: square_examine 0x800bb790 (0x3e the dial, 0x3d the
Ruby Hands, 0x3c the hollow, 0x42 switches, 0x03 hidden doors), square_arrive 0x800ba48c
(0x65 the Guardians, 0x41 circles, 0x68 the shadow), maze_prompt_result 0x800befcc (0xd
the dial, 0x10 switches), the dial's frame handlers FUN_800b47f4 / FUN_800b49a8 and the
floor-load walls 0x800a8f1c. Site squares E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  guardians  story_flags (0x80079b44) bit 16: the Guardians' fixed fight (encounter 0x23,
             a level-15 party of four) on arriving at B5 E9 N12 (9, 11), the square south
             of the west stairs' foot (9, 10). After the fight MAZE 0x800c0748 sets the bit.
             The way: up through B3's and B2's circles (nav's circle links: switch, then
             circle), B2's shadow at E17 N11 (17, 12; talk once a trip), B1's hidden door
             north of E11 N4 (11, 19), and down the west stairs from B1 (5, 13).
  dial       story_flags bit 26: the vault door, west side of B5 E7 N11 (7, 12),
             Investigate facing west (0x3e), EVENTMES 158, Yes (prompt 0xd). Then
             game_state 0x0f and a stage byte 0x80079790: 0/2/4 show a ring's line, 1/3/5
             turn the small/middle/large ring (u16 angles 0x8008a006 / 0x8008a004 /
             0x8008a002, Right +5 and Left -5, last-press direction bytes 0x80079793 /
             0x80079792 / 0x80079791: 1 Right, 0 Left), Circle goes on, 6 checks: small 135
             with Right last, middle 45 with Left last, large 90 with Right last. Balbo's
             party stands on the square while bit 26 is clear (a talk on arrival).
  red_stone  the Tablet's stone bit 1 (0x02, MAZE 0x800b7310(1)): B5 E5 N12 (5, 11),
             Investigate facing west (0x3d, EVENTMES 149) wakes the Ruby Hands (encounter
             0xa3, level 22, AC -20, stoning fists) and sets maze_event_flags bit 19,
             which opens (5, 11)'s west side into the hollow (4, 11); there Investigate
             facing west (0x3c, EVENTMES 275). maze_event_flags is cleared on each entry
             from town, so the stone is taken right after the fight, in the same trip.
Training: Area B B4 and B5 (areas 24, 23), as chapter 9.
Not done: WAREHOUSE on B1's pillar (E13 N7 south; chapter 11's word, read there).
"""
from harness import chapters, chapter1, chapter3, maze, nav, play, ui
from harness.game import Stuck

STORY = 0x80079b44
MAZE_EVENTS = 0x80079b48
RED = 0x02
TRAIN_LEVEL = 17   # first draft: the Guardians are level 15, the Ruby Hands 22 (2-6 of them)
TRAIN_AREAS = (24, 23)      # Area B B4, B5

DIAL_STATE = 0x0f
STAGE = 0x80079790
# stage that turns the ring: (angle u16, last-press byte, target, last press Right?)
RINGS = {1: (0x8008a006, 0x80079793, 135, True),     # small: the snakes, clockwise
         3: (0x8008a004, 0x80079792, 45, False),     # middle: the people, counterclockwise
         5: (0x8008a002, 0x80079791, 90, True)}      # large: the birds, clockwise


def turn(g, addr, last, target, right_last):
    """Turn one ring to target, the last press in the wanted direction."""
    def tap(btn):
        v = g.u16(addr)
        for _ in range(3):
            g.tap(btn)
            for _ in range(20):
                if g.u16(addr) != v:
                    g.step(2)
                    return
                g.step()
        raise Stuck('dial ring did not turn', ring=hex(addr), at=v, stage=g.u8(STAGE))
    # Right +5 a press: come up to the target from below (or one past it and back, for a
    # counterclockwise last press)
    stop = target if right_last else (target + 5) % 360
    for _ in range(80):
        if g.u16(addr) == stop:
            break
        tap('right')
    if not right_last:
        tap('left')
    if g.u16(addr) != target or bool(g.u8(last)) != right_last:
        raise Stuck('dial ring off', ring=hex(addr), at=g.u16(addr), last=g.u8(last))


def drive_dial(g, log):
    """From the Investigate: answer Yes to EVENTMES 158, turn the three rings, confirm."""
    f0 = g.frame
    while g.u8(maze.GAME_STATE) != DIAL_STATE:
        if g.frame - f0 > 3000:
            raise Stuck('no dial', where=g.where())
        if g.u8(maze.GAME_STATE) == play.PROMPT:
            ui.move_cursor(g, play.PROMPT_CURSOR, 0, 'down', 'up', what='dial yes/no')
            ui.confirm_until(g, lambda: g.u8(maze.GAME_STATE) != play.PROMPT, 300, 'dial yes')
            continue
        if maze.calm(g):
            # "Searching..." leaves the view calm a while before EVENTMES 158's box opens
            # (~310 frames to the prompt, 2026-10-14)
            for _ in range(chapter1.QUIET):
                g.step()
                if not maze.calm(g):
                    break
            else:
                return False            # no prompt: open already, or not the dial
            continue
        if g.u8(maze.EVENT_BOX) or maze.box_up(g):
            play.close_box(g)
            continue
        g.step()
    # stages 0, 2 and 4 (a ring's line) go on to the next by themselves within a few
    # frames; at 1, 3 and 5 the ring is turned and Circle moves on (probe 2026-10-14: one
    # Right tap = +5, the angle changes 2 frames after the press)
    done = set()
    f0 = g.frame
    while g.u8(maze.GAME_STATE) == DIAL_STATE and g.frame - f0 < 6000:
        st = g.u8(STAGE)
        if st == 6:
            break
        if st not in RINGS or st in done:
            g.step()
            continue
        g.step(10)
        turn(g, *RINGS[st])
        log.append((g.frame, 'dial ring', st, g.u16(RINGS[st][0])))
        done.add(st)
        ui.press_until(g, 'circle', lambda: g.u8(STAGE) != st
                       or g.u8(maze.GAME_STATE) != DIAL_STATE, 120, 'dial next')
    return True


@chapters.chapter
class Chapter10:
    n = 10
    title = 'The vault in Area B and the red stone'

    def goals(self, run):
        g = run.g

        def guardians():
            if nav.flag(g, STORY, 16):
                return True
            run.ready()
            run.go((23, 9, 10))
            run.heal()
            run.go((23, 9, 11))
            run.after()
            if not nav.flag(g, STORY, 16):
                return False
            return run.all_home() or 'casualties'

        def dial():
            if nav.flag(g, STORY, 26):
                return True
            run.fit()
            run.go((23, 7, 12))         # Balbo's talk on arrival runs in go's on_int
            run.after()
            if not maze.face(g, 3):
                run.after()
                maze.face(g, 3)
            if (g.u8(maze.AREA),) + g.pos() != (23, 7, 12):
                return False
            chapter1.investigate(g)
            drive_dial(g, run.log)
            run.after()
            run.note('dial', nav.flag(g, STORY, 26))
            return nav.flag(g, STORY, 26)

        def red_stone():
            if chapter3.tablet_stones(g) & RED:
                return True
            run.ready()
            run.go((23, 5, 11))
            run.heal()
            run.examine((23, 5, 11), 3, fight=True)
            if chapter1.party_wiped(g):
                return False
            if not g.u32(MAZE_EVENTS) & (1 << 19):
                return False
            # the hollow: (5, 11)'s west side is open while bit 19 is set
            for _ in range(3):
                if g.pos() == (4, 11):
                    break
                maze.face(g, 3)
                if maze.step(g, 3) == 'interrupted':
                    run.after()
            if (g.u8(maze.AREA),) + g.pos() != (23, 4, 11):
                return False
            for _ in range(2):
                maze.face(g, 3)
                chapter1.investigate(g)
                run.after()
                if chapter3.tablet_stones(g) & RED:
                    break
            if not chapter3.tablet_stones(g) & RED:
                return False
            run.all_home()
            return True

        yield from run.recover_goals()
        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'guardians', guardians
        yield 'dial', dial
        yield from run.recover_goals()
        yield 'red_stone', red_stone
