"""Walkthrough chapter 2, the Shrine and the jade mask, as a goal list (2026-10-13).

Source: Bartok's Trading Post data/walkthrough/dim/02-shrine-jade-mask.json, with the
event records of data/maps/dim/f01-f04.json and MAZE's square_examine/square_arrive
(rips/re/decomp/MAZE/800bb790, 800ba48c). Site squares E x N y are the game's (x, 23 - y).
Areas 1-4 are Shrine 1F-4F, 6 Underground B3.

Goals, each proved by RAM:
  shrine_3f    on 3F (area 3): the stairs 1F E11 N6 -> 2F E11 N7, 2F E11 N8 -> 3F E11 N9
  train_NN     training trips over the Shrine's fight squares until every member is level
               TRAIN_LEVEL (the walkthrough: about level 9 before the Underground Shrine)
  switches     story_flags (0x80079b44) bit 1: the two-switch side doors unlocked.
               Stepping onto the west switch (3F E7 N8) starts Balbo's meeting
               (square_arrive 0x61, talk_party 11, once: maze_event_flags 0x4000000); his
               "Wanna lend us a hand?" yes/no has the cursor on Yes, and Yes runs the
               countdown (EVENTMES 301-302) and sets the bit.
  hidden_door  bit 1 of 0x80079628: Investigate facing east at 3F E9 N6 ("Found a secret
               door!", square_examine case 3; no Thief needed for the examine itself)
  jade_mask    item 0x13c (JADE MASK) in a pack: 4F E14 N7 facing south, Investigate,
               "Will you take it?" Yes, then the Chany Mask's fight (level 10, AC -10)
  jewel        on Underground B3 (area 6): 4F E11 N12, Investigate, "Will you touch it?"
               Yes; the lift sets the party down at B3 E12 N12
"""
from harness import chapters, chapter1, maze, nav, town
from harness.game import Stuck

STORY = 0x80079b44
JADE_MASK = 0x13c
TRAIN_LEVEL = 8  # lowered 2026-10-14 for the geared Bishop parties; boss_training adds levels after 2 failed tries
TRAIN_AREAS = (3,)          # 3F's corridor and rooms: eight 95% fight squares


def story(g, bit):
    return nav.flag(g, STORY, bit)


@chapters.chapter
class Chapter2:
    n = 2
    title = 'The Shrine and the jade mask'

    def goals(self, run):
        g = run.g

        def shrine_3f():
            run.fit()
            run.go((3, 11, 14))
            return g.u8(maze.AREA) == 3

        def switches():
            if story(g, 1):
                return True
            run.fit()
            run.go((3, 7, 15))
            run.after()
            return story(g, 1)

        def hidden_door():
            if nav.hidden_found(g, 1):
                return True
            run.fit()
            run.examine((3, 9, 17), 1)
            return nav.hidden_found(g, 1)

        def jade_mask():
            if JADE_MASK in chapter1.party_items(g):
                return True
            run.fit()
            if chapter1.needs_town(g):
                return 'not fit'
            run.examine((4, 14, 16), 2, fight=True)
            if JADE_MASK not in chapter1.party_items(g):
                return False
            return run.all_home() or 'casualties'

        def jewel():
            if g.u8(maze.AREA) == 6 and g.overlay() != 'JOUKA':
                return True
            run.fit()
            run.examine((4, 11, 11), 0)
            return g.u8(maze.AREA) == 6

        yield from run.recover_goals()
        yield 'shrine_3f', shrine_3f
        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'switches', switches
        yield 'hidden_door', hidden_door
        yield from run.recover_goals()
        yield 'jade_mask', jade_mask
        yield 'jewel', jewel
