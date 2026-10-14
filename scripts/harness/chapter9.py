"""Walkthrough chapter 9, Area B and the black stone (2026-10-13).

Source: data/walkthrough/dim/09-area-b-black-stone.json, data/maps/dim/f18.json and
f23-f25.json, and MAZE's square_examine (rips/re/decomp/MAZE/800bb790, case 0x43). Areas
23-27 are Area B B5-B1. Site squares E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  laboratory   story_flags (0x80079b44) bit 5, door B: at the pedestal of small tablets
               in Area X (chapter6.pedestal_word), type LABORATORY. Door B is the west
               side of Area X E8 N11 (8, 12) (f18 event 32, sealed until bit 5).
  area_b       in Area B (area 23): the lift past door B, E6-E7 N11, sets the party
               down on B5 E19 N11 (19, 12).
  chimera      past Zaril's party at B3 E12 N11 (12, 12) (event 0x69 = 105 on arrival):
               they become the Chimera Warrior, level 20, 170-210 HP, AC -8. The way
               up is B5's stairs at E14 N6, then B4's right-hand pair at E18 N11, then
               the LABORATORY door at B3 E13 N11; nav plans it. Proof: the party standing
               on (12, 12) with nobody down.
  black_stone  the Tablet's stone bit 0 (0x01, MAZE 0x800b7310(0)): B3 E10 N12 (10, 11),
               Investigate facing west (square_examine 0x43, its record's facing 3).
  switch       B3 E5 N8 (5, 15) (event type 0x42 = 66, params 0, 27): the switch that
               lights the magic circle at E5 N5 (5, 18) up to B2 (area 26). Proof: the
               party in area 26 after stepping on the circle.
Training: B4 (area 24), which has the HEAL room at E5 N18 (5, 5) (event type 0x3f).
Not done: the book on B4 E15 N12.
"""
from harness import chapters, chapter3, chapter6, maze, nav

STORY = 0x80079b44
BLACK = 0x01
TRAIN_LEVEL = 16   # lowered 2026-10-14 for the geared Bishop parties; boss_training adds levels after 2 failed tries
#           before: the Chimera Warrior is level 20; Were Centipedes from B3
TRAIN_AREAS = (24, 23)      # Area B B4, B5


@chapters.chapter
class Chapter9:
    n = 9
    title = 'Area B and the black stone'

    def goals(self, run):
        g = run.g

        def laboratory():
            if nav.flag(g, STORY, 5):
                return True
            run.fit()
            return chapter6.pedestal_word(run, 'LABORATORY', 5)

        def area_b():
            if g.u8(maze.AREA) in (23, 24, 25, 26, 27):
                return True
            run.fit()
            run.go((23, 19, 12))
            return g.u8(maze.AREA) == 23

        def chimera():
            if chapter3.tablet_stones(g) & BLACK:
                return True
            run.ready()
            run.go((25, 13, 12))
            run.heal()
            run.go((25, 12, 12))
            run.after()
            if (g.u8(maze.AREA),) + g.pos() != (25, 12, 12):
                return False
            return run.all_home() or 'casualties'

        def black_stone():
            if chapter3.tablet_stones(g) & BLACK:
                return True
            run.fit()
            run.examine((25, 10, 11), 3)
            return bool(chapter3.tablet_stones(g) & BLACK)

        def switch():
            if g.u8(maze.AREA) == 26:
                return True
            run.fit()
            run.examine((25, 5, 15), 0)
            run.go((25, 5, 18))
            run.after()
            return g.u8(maze.AREA) == 26

        yield from run.recover_goals()
        yield 'laboratory', laboratory
        yield 'area_b', area_b
        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'chimera', chimera
        yield 'black_stone', black_stone
        yield 'switch', switch
