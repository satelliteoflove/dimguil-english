"""Walkthrough chapter 5, the moon door and the 2-Head Snake (2026-10-13).

Source: data/walkthrough/dim/05-moon-door.json, data/maps/dim/f05-f08.json and MAZE's
square_examine / square_arrive. Areas 5-8 are Underground B4-B1, 18 Area X. Site squares
E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  train_NN    training trips (B4 is the walkthrough's place to build levels)
  moon_door   past the moon door: B3 E19 N4 facing north (square_examine 0x15, p1 = the
              side), the Tablet opens it (EVENTMES 80); proved by standing at B3 E19 N5,
              behind it
  snake       story_flags bit 2 (0x80079b44): the winding machine on B1 E14 N12, facing
              west (square_examine 0x22, prompt 5), Yes. The 2-Head Snake's fight comes
              first, on arriving at E15 N12 (square_arrive 0x2b), behind a hidden door in
              the west wall of E16 N12. The prompt flips the bit each time it's answered
              Yes, so the goal answers it once and checks.
  area_x      in Area X (area 18): the new lift at B3 E15 N12, through the wall the chain
              hauled up at E13 N12 (nav plans the long way round)
"""
from harness import chapters, chapter1, maze, nav
from harness.game import Stuck

STORY = 0x80079b44
TRAIN_LEVEL = 13
TRAIN_AREAS = (5, 6)


@chapters.chapter
class Chapter5:
    n = 5
    title = 'The moon door and the 2-Head Snake'

    def goals(self, run):
        g = run.g

        def moon_door():
            if g.u8(maze.AREA) in (5, 8, 18) or (g.u8(maze.AREA),) + g.pos() == (6, 19, 18):
                return True
            run.fit()
            run.examine((6, 19, 19), 0)
            for _ in range(3):
                s = maze.step(g, 0)
                if s == 'interrupted':
                    run.after()
                    continue
                break
            return (g.u8(maze.AREA),) + g.pos() == (6, 19, 18)

        def snake():
            if nav.flag(g, STORY, 2):
                return True
            run.fit()
            if chapter1.needs_town(g):
                return 'not fit'
            run.go((8, 15, 11))
            run.after()
            if not run.all_home():
                return 'casualties'
            run.examine((8, 14, 11), 3)
            return nav.flag(g, STORY, 2)

        def area_x():
            run.fit()
            run.go((18, 13, 12))
            return g.u8(maze.AREA) == 18

        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'moon_door', moon_door
        yield 'snake', snake
        yield from run.recover_goals()
        yield 'area_x', area_x
