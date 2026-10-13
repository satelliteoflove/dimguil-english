"""Walkthrough chapter 3, the Underground Shrine and the blue stone (2026-10-13).

Source: data/walkthrough/dim/03-blue-stone.json, data/maps/dim/f06-f07.json and
square_examine (rips/re/decomp/MAZE/800bb790). Areas 6 Underground B3, 7 B2. Site squares
E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  train_NN     training trips over the Underground's fight squares (B3 and B2) until every
               member is TRAIN_LEVEL (its monsters are level 6 to 11)
  freezer      npc_flags (0x80079754) bit 29: the ice pillar on B3 E20 N20, Investigate
               facing west (square_examine 0x27), then the Ice Rocks' fight; the pillar
               melts. The way in is the chute on B2 E22 N19 (nav plans it).
  blue_stone   the Tablet's stone bit 2 (its item_state byte, roster +0x34, set by MAZE
               0x800b7310): B2 E21 N21, Investigate facing west (square_examine 0x28)
  stream       at B2 E7 N12 (7, 11), by the stream, where chapter 4 starts. The way back
               runs through a hidden door in the east wall of B2 E17 N19 (nav finds it).
"""
from harness import chapters, chapter1, maze, nav
from harness.game import Stuck

NPC_FLAGS = 0x80079754
TABLET = 0x143
TRAIN_LEVEL = 10  # one lower 2026-10-13: r3v0 and r3v1 were still short of 11 after 24 trips of ~22k frames on B3 and B2
TRAIN_AREAS = (6, 7)


def tablet_stones(g):
    """The Tablet of the Sun's stone bits (item_state of the first Tablet in the party)."""
    from harness import town
    for i in (g.party() or town.town_party(g)):
        c = g.char(i)
        raw = c['raw']
        for k in range(10):
            it = int.from_bytes(raw[0x20 + 2 * k:0x22 + 2 * k], 'little')
            if it != 0xffff and it & 0x1ff == TABLET:
                return raw[0x34 + k]
    return 0


@chapters.chapter
class Chapter3:
    n = 3
    title = 'The Underground Shrine and the blue stone'

    def goals(self, run):
        g = run.g

        def freezer():
            if nav.flag(g, NPC_FLAGS, 29):
                return True
            run.fit()
            if chapter1.needs_town(g):
                return 'not fit'
            run.examine((6, 20, 3), 3, fight=True)
            if not nav.flag(g, NPC_FLAGS, 29):
                return False
            return run.all_home() or 'casualties'

        def blue_stone():
            if tablet_stones(g) & 4:
                return True
            run.fit()
            run.examine((7, 21, 2), 3)
            return bool(tablet_stones(g) & 4)

        def stream():
            run.fit()
            run.go((7, 7, 11))
            return (g.u8(maze.AREA),) + g.pos() == (7, 7, 11)

        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'freezer', freezer
        yield 'blue_stone', blue_stone
        yield from run.recover_goals()
        yield 'stream', stream
