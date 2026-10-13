"""Walkthrough chapter 4, the lake machine (2026-10-13).

Source: data/walkthrough/dim/04-lake-machine.json, data/maps/dim/f07.json and MAZE's
square_examine / square_arrive (rips/re/decomp/MAZE/800bb790, 800ba48c). Area 7 is
Underground B2. Site squares E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  train_NN    training trips over the Underground's fight squares until every member is
              TRAIN_LEVEL (the Guardians are level 10, the Gas Clouds 12)
  stream      npc_flags (0x80079754) bit 28: the Tablet (blue stone set) in the hole at
              B2 E7 N12 (square_examine 0x24; EVENTMES 88), the stream parts
  guardians   story_flags (0x80079b44) bit 14: the Guardians' fixed fight on arriving at
              B2 E7 N22 (square_arrive 0x65, p1 14; encounter 14 + 0x13)
  machine     story_flags bit 3: B2 E11 N22 facing south (square_examine 0x2a), "Will you
              pull the lever?" Yes, then the Gas Clouds; the machine stops. The room is
              behind a hidden door in the east wall of E9 N23 (nav finds it).
"""
from harness import chapters, chapter1, maze, nav
from harness.game import Stuck

NPC_FLAGS = 0x80079754
STORY = 0x80079b44
TRAIN_LEVEL = 12  # 2026-10-13: the Guardians (Arch Mage, Madalto for up to 64 on everyone) wiped f1v0 at 11 and 12 with every blow on the front row; aimed at the mage first (battle.aim) the same party won at 11-12 (dev/qtest_guard_f1v0c.out)
TRAIN_AREAS = (6, 7)


@chapters.chapter
class Chapter4:
    n = 4
    title = 'The lake machine'

    def goals(self, run):
        g = run.g

        def stream():
            if nav.flag(g, NPC_FLAGS, 28):
                return True
            run.fit()
            run.examine((7, 7, 11), 3)
            return nav.flag(g, NPC_FLAGS, 28)

        def guardians():
            if nav.flag(g, STORY, 14):
                return True
            run.fit()
            if chapter1.needs_town(g):
                return 'not fit'
            run.go((7, 7, 1))
            run.after()
            if not nav.flag(g, STORY, 14):
                return False
            return run.all_home() or 'casualties'

        def machine():
            if nav.flag(g, STORY, 3):
                return True
            run.fit()
            if chapter1.needs_town(g):
                return 'not fit'
            run.examine((7, 11, 1), 2, fight=True)
            if not nav.flag(g, STORY, 3):
                return False
            return run.all_home() or 'casualties'

        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'stream', stream
        yield 'guardians', guardians
        yield from run.recover_goals()
        yield 'machine', machine
