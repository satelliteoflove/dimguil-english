"""Walkthrough chapter 12, Area C's moving floors and the silver stone (2026-10-15).

Source: data/walkthrough/dim/12-silver-stone.json, data/maps/dim/f18.json and f28-f31.json
(Area C B4 to B1, areas 28-31), and MAZE: square_arrive 0x800ba48c (0x44 turning tiles,
0x45 moving floors: nav.carry), square_examine 0x800bb790 (0x4e the panel, 0x47 the B4
switch, 0x4d the Golem's door, 0x46 the device), maze_prompt_result 0x800befcc (prompt
0x15 opens the panel, 0x11 toggles the switch's bit), the panel's frame handler
0x800c8640, the floor-load locks 0x800a8f1c and the fight reward 0x800c0748. Site squares
E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  warehouse  story_flags (0x80079b44) bit 6: WAREHOUSE at the pedestal in Area X
             (chapter6.pedestal_word); it unseals the side north of Area X (11, 8), the way
             to the lift at E11 N16 (11, 7) down to C-B1 (11, 21).
  panel      the nine turning tiles' settings, bytes 0x80087a30 + i (0-2): Investigate
             facing west at C-B1 E10 N6 (10, 17) (0x4e, EVENTMES 183), Yes, and the panel
             is game_state 0x10: 0x80079790 the switch under the cursor (Right +1, Left -1,
             0-8 round), 0x80079791 the picture row (Down +1, Up -1, 0-2 round), Circle sets
             the switch to the row, Cross leaves. A tile turns the party to
             nav.TILE_DIRS[i * 3 + setting]; the walkthrough's pictures (mountain south,
             sun east) for switches 4-8 are rows 0, 2, 1, 2, 1.
  switch     story_flags bit 21: B4 E8 N12 (8, 11), Investigate facing east (0x47,
             EVENTMES 197), Yes. Prompt 0x11 toggles the bit, so it's pressed only while
             clear. The way is door C (west side of the three, north of C-B1 (10, 16)):
             the floors carry the party to C-B2 E16 N13, the warp at E14 N15 goes to B4
             E14 N20, and B4's floor beyond the north door sets it down at E7 N13.
  golem      story_flags bit 11: C-B2 E11 N10 (11, 13), Investigate facing north (0x4d,
             EVENTMES 181) starts the Greater Golem's fight (fight type 10); the win sets
             bit 11, which unlocks the door (both its squares, at every floor load). Door
             B's ride sets the party down at C-B2 E10 N10 (10, 13), next to it.
  silver     the Tablet's stone bit 7 (0x80, MAZE 0x800b7310(7)): B4 E9 N12 (9, 11),
             Investigate facing west (0x46, EVENTMES 271/272), only with bit 21 set.
Litofeit would carry the party over door B's chute on B2; the harness never casts it.
Not done: ENERGY (Area D's word, chapter 13 types it); the trash rooms and the Dust.
"""
from harness import chapters, chapter1, chapter3, chapter6, maze, nav, play, ui
from harness.game import Stuck

STORY = 0x80079b44
SILVER = 0x80
PANEL_STATE = 0x10
SEL, ROW = 0x80079790, 0x80079791
# switch index (0-8) -> row, for door B (switches 4-6) and door C (7-8)
PANEL_WANT = {3: 0, 4: 2, 5: 1, 6: 2, 7: 1}
DOOR_B = (31, 11, 16)       # C-B1 E11 N7, south of door B


def panel_ok(g):
    return all(g.u8(nav.PANEL + i) == k for i, k in PANEL_WANT.items())


def drive_panel(g, log, want=None):
    """From the Investigate: Yes to EVENTMES 183, set want (PANEL_WANT), leave the panel."""
    want = PANEL_WANT if want is None else want
    f0 = g.frame
    while g.u8(maze.GAME_STATE) != PANEL_STATE:
        if g.frame - f0 > 3000:
            raise Stuck('no panel', where=g.where())
        if g.u8(maze.GAME_STATE) == play.PROMPT:
            ui.move_cursor(g, play.PROMPT_CURSOR, 0, 'down', 'up', what='panel yes/no')
            ui.confirm_until(g, lambda: g.u8(maze.GAME_STATE) != play.PROMPT, 300, 'panel yes')
            continue
        if maze.calm(g):
            for _ in range(chapter1.QUIET):
                g.step()
                if not maze.calm(g):
                    break
            else:
                return False
            continue
        if g.u8(maze.EVENT_BOX) or maze.box_up(g):
            play.close_box(g)
            continue
        g.step()
    g.step(30)
    for i, k in sorted(want.items()):
        ui.move_cursor(g, SEL, i, 'right', 'left', wrap=9, what='panel switch')
        ui.move_cursor(g, ROW, k, 'down', 'up', wrap=3, what='panel row')
        if g.u8(nav.PANEL + i) != k:
            ui.press_until(g, 'circle', lambda: g.u8(nav.PANEL + i) == k, 120, 'panel set')
        log.append((g.frame, 'panel', i, k))
    ui.press_until(g, 'cross', lambda: g.u8(maze.GAME_STATE) != PANEL_STATE, 300, 'panel leave')
    return True


@chapters.chapter
class Chapter12:
    n = 12
    title = "Area C's moving floors and the silver stone"

    def goals(self, run):
        g = run.g

        def warehouse():
            if nav.flag(g, STORY, 6):
                return True
            run.fit()
            return chapter6.pedestal_word(run, 'WAREHOUSE', 6)

        def panel():
            if panel_ok(g):
                return True
            run.fit()
            for _ in range(3):
                run.go((31, 10, 17))
                if not maze.face(g, 3):
                    run.after()
                if (g.u8(maze.AREA),) + g.pos() == (31, 10, 17) and g.u8(maze.FACE) == 3:
                    break
            chapter1.investigate(g)
            drive_panel(g, run.log)
            run.after()
            run.note('panel', [g.u8(nav.PANEL + i) for i in range(9)])
            return panel_ok(g)

        def switch():
            if nav.flag(g, STORY, 21):
                return True
            if not panel_ok(g) and not panel():
                return False
            run.fit()
            run.examine((28, 8, 11), 1)
            return nav.flag(g, STORY, 21)

        def golem():
            if nav.flag(g, STORY, 11):
                return True
            if not panel_ok(g) and not panel():
                return False
            # the boss checks happen at door B: its ride ends in a pocket (C-B2 E10 N10
            # and the Golem's door) whose only other way out, the stairs down at E10 N9,
            # lands on B3's floor that carries the party straight back up (n1v0u, 2026-10-15:
            # "short at a boss door" there, then "no route" home six times)
            run.ready()
            run.go(DOOR_B)
            while run.door_ready():
                run.ready(train=False)
                run.go(DOOR_B)
            run.go((30, 10, 13))
            run.heal()
            run.examine((30, 11, 13), 0, fight=True)
            run.after()
            if not nav.flag(g, STORY, 11):
                return False
            return run.all_home() or 'casualties'

        def silver():
            if chapter3.tablet_stones(g) & SILVER:
                return True
            if not nav.flag(g, STORY, 21) or not nav.flag(g, STORY, 11):
                return False
            run.fit()
            run.examine((28, 9, 11), 3)
            if not chapter3.tablet_stones(g) & SILVER:
                return False
            run.all_home()
            return True

        yield from run.recover_goals()
        yield 'warehouse', warehouse
        yield 'panel', panel
        yield 'switch', switch
        yield from run.recover_goals()
        yield 'golem', golem
        yield 'silver', silver
