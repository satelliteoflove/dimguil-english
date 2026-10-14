"""Walkthrough chapter 7, Area A and the green stone (2026-10-13).

Source: data/walkthrough/dim/07-area-a-green-stone.json, data/maps/dim/f19-f20.json and
MAZE's square_examine (rips/re/decomp/MAZE/800bb790, case 0x33). Areas 20 Area A B3,
19 Area A B4. Site squares E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  green_stone  the Tablet's stone bit 5 (MAZE 0x800b7310(5)): the hollow in the west wall
               of the coffin room, Area A B4 E5 N13 (5, 10), Investigate facing west
               (square_examine 0x33). The way down is B3's stairs at E7 N15 (7, 8);
               nav plans it.
"""
from harness import chapters, chapter3

GREEN = 0x20
TRAIN_LEVEL = 12  # lowered 2026-10-14 for the geared Bishop parties; boss_training adds levels after 2 failed tries
TRAIN_AREAS = (20, 19)      # Area A B3, B4


@chapters.chapter
class Chapter7:
    n = 7
    title = 'Area A and the green stone'

    def goals(self, run):
        g = run.g

        def green_stone():
            if chapter3.tablet_stones(g) & GREEN:
                return True
            # Area A is busy (85% fight squares, adventurer parties): start healed
            run.ready()
            run.examine((19, 5, 10), 3)
            return bool(chapter3.tablet_stones(g) & GREEN)

        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'green_stone', green_stone
