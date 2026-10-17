"""Walkthrough chapter 13, past the snake door in Area C (2026-10-15).

Source: data/walkthrough/dim/13-snake-door.json, data/maps/dim/f28-f31.json (Area C B4 to
B1, areas 28-31), and MAZE: square_arrive 0x800ba48c (0x4a the damage floor, 0x65 the
Guardians, 0x4c the way out), square_examine 0x800bb790 (0x48 the red floor's device, 0x5c
the floor switch, 3 the hidden door, 0x20 signs), maze_prompt_result 0x800befcc (prompts
0x12 and 0x1b) and the fight reward 0x800c0748. Site squares E x N y are the game's
(x, 23 - y).

The chain plays it before Area D, so the moving floors still run: the walkthrough's other
way in, door C with switches 7, 8 and 9 on mountain, mountain, moon. In panel rows that's
switch indexes 6-8 at 2, 0, 0: nav's carry model (offline, from n1v3s/c12_end) finds no
other setting of the three that reaches the snake door, and with this one door C's ride
sets the party down on the snake door's square, B4 E9 N2 (9, 21), after 62 squares.

Goals, each proved by RAM:
  panel      the turning tiles' settings, bytes 0x80087a30 + 6..8 = 2, 0, 0 (chapter 12's
             panel, C-B1 E10 N6 facing west; chapter 12 left index 7 at 1).
  snake_door the party on B4 E9 N2 (9, 21), where the ride ends, and Investigate facing
             west reads the snakes on the door (0x20, EVENTMES 184).
  danger     the party on B4 E2 N2 (2, 21), Investigate facing south: the DANGER sign (0x20,
             EVENTMES 170). Off the damage floor, along the room's south row.
  guardians  story_flags (0x80079b44) bit 17: the Guardians' fixed fight on arriving at
             B4 E5 N11 (5, 12) (square_arrive 0x65 with p1 17, EVENTMES 283, encounter
             17 + 0x13; the win sets bit p1, 0x800c0748 case 0x11). The way there crosses
             the room past the snake door, whose 28 type 0x4a squares hurt the party on
             arrival unless story bit 22 is set; nav prices event squares at 40 a step, so
             its walk is the walkthrough's 32-step safe path. The Jade Mask only shows
             which squares are red; the harness doesn't put it on.
  fire       story_flags bit 22: B4 E5 N12 (5, 11), Investigate facing east (0x48, EVENTMES
             197), Yes (prompt 0x12 toggles the bit, so it's pressed only while clear). It
             puts out the damage floor.
  energy     ENERGY: the mural on the west wall of B4 E2 N12 (2, 11) (0x20, EVENTMES 198).
             No flag; proved as chapter 8's mural is, by the captured string.
  floor_switch
             story_flags bit 27: B4 E2 N20 (2, 3), Investigate facing west (0x5c, EVENTMES
             197), Yes (prompt 0x1b toggles bit 27; pressed only while clear). With bit 27
             set square_arrive skips 0x44 and 0x45, so Area C's floors stop (nav.belts_on).
             The way is the hidden door north of E4 N13 (4, 10) (type 3, bit 19 of
             0x80079628), which nav finds with an Investigate facing north.
  out        the party on C-B1 E15 N3 (15, 20): the small room at B4 E5 N21 (5, 2) is a
             0x4c teleport there.
"""
from harness import chapters, chapter1, chapter12, maze, nav

STORY = 0x80079b44
PANEL_WANT = {6: 2, 7: 0, 8: 0}
TRAIN_AREAS = (24, 23)      # boss training only (Area B B4, B5, as chapter 10's)


def panel_ok(g):
    return all(g.u8(nav.PANEL + i) == k for i, k in PANEL_WANT.items())


def said(g, n, idx):
    return not g.cap or any(m['file'] == 'EVENTMES.BIN' and m['idx'] == idx
                            for m in g.cap.messages[n:])


@chapters.chapter
class Chapter13:
    n = 13
    title = 'Past the snake door in Area C'

    def goals(self, run):
        g = run.g

        def here():
            return (g.u8(maze.AREA),) + g.pos()

        def panel():
            if panel_ok(g):
                return True
            run.fit()
            for _ in range(3):
                run.go((31, 10, 17))
                if not maze.face(g, 3):
                    run.after()
                if here() == (31, 10, 17) and g.u8(maze.FACE) == 3:
                    break
            chapter1.investigate(g)
            chapter12.drive_panel(g, run.log, PANEL_WANT)
            run.after()
            run.note('panel', [g.u8(nav.PANEL + i) for i in range(9)])
            return panel_ok(g)

        def sign(at, facing, idx):
            def goal():
                if not panel_ok(g) and not nav.flag(g, STORY, 27) and not panel():
                    return False
                n = len(g.cap.messages) if g.cap else 0
                run.fit()
                run.examine(at, facing)
                return here() == at and said(g, n, idx)
            return goal

        def guardians():
            if nav.flag(g, STORY, 17):
                return True
            if not panel_ok(g) and not panel():
                return False
            run.ready()
            run.go((28, 5, 13))
            while run.door_ready():
                run.ready(train=False)
                run.go((28, 5, 13))
            run.heal()
            run.go((28, 5, 12))
            run.after()
            if not nav.flag(g, STORY, 17):
                return False
            return run.all_home() or 'casualties'

        def press(bit, at, facing):
            def goal():
                if nav.flag(g, STORY, bit):
                    return True
                if not nav.flag(g, STORY, 17):
                    return False
                run.fit()
                run.examine(at, facing)
                return nav.flag(g, STORY, bit)
            return goal

        def out():
            run.fit()
            run.go((31, 15, 20))
            run.after()
            return here() == (31, 15, 20)

        yield from run.recover_goals()
        yield 'panel', panel
        yield 'snake_door', sign((28, 9, 21), 3, 184)
        yield 'danger', sign((28, 2, 21), 2, 170)
        yield from run.recover_goals()
        yield 'guardians', guardians
        yield 'fire', press(22, (28, 5, 11), 1)
        yield 'energy', sign((28, 2, 11), 3, 198)
        yield 'floor_switch', press(27, (28, 2, 3), 3)
        yield 'out', out
