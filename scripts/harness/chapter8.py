"""Walkthrough chapter 8, Area A: the yellow stone and the Jail Ogre (2026-10-13).

Source: data/walkthrough/dim/08-area-a-yellow-stone.json, data/maps/dim/f19-f22.json and
MAZE: square_examine (rips/re/decomp/MAZE/800bb790: 0x09 ladder, 0x35 altar, 0x3a switch,
0x34 yellow stone, 0x32 bars), square_arrive (800ba48c: 0x3b chute, 0x65 Guardians),
maze_prompt_result (800befcc: 8 ladder, 9-11 the light, 0xc the switch) and the altar's
dispatcher case 0x16 (800c1070). Areas 19-22 are Area A B4-B1. Site squares E x N y are
the game's (x, 23 - y).

Goals, each proved by RAM:
  light        story_flags (0x80079b44) bit 9 or 8, the light's color: the altar at B4
               E11 N11 (11, 12), Investigate facing west (0x35), Yes. Which prompt comes
               depends on the Tablet's stones 5 (green) and 1: green without 1 asks
               prompt 10, whose Yes sets bit 9 and clears bit 8. The way there is B3's
               ladder at E10 N4 (nav.LINKS) and B4's hidden door west of E14 N11.
  guardians    story_flags bit 15: the Guardians' fixed fight on arriving at B1 E16 N11
               (16, 12) (square_arrive 0x65, p1 15), past the green door on the east
               side of E15 N11.
  switch       story_flags bit 25: B1 E18 N11 (18, 12), Investigate facing west (0x3a),
               Yes (prompt 0xc toggles it). It opens the chute at E17 N11 (17, 12)
               (square_arrive 0x3b acts only while bit 25 is set). Beyond the Guardians
               a hidden door in the south wall of E19 N13 (nav finds it).
  ogre         in the Jail Ogre's den, B4 E19 N12 (19, 11): down the chute to B4
               (17, 12), the Ogre's fight on E17 N12 (17, 11).
  yellow_stone the Tablet's stone bit 6 (0x34, MAZE 0x800b7310(6)): B4 E19 N13 (19, 10),
               Investigate facing north.
  out          outside the pen, B4 E18 N8 (18, 15), by the teleporter at E20 N10 (20, 13).
Not done: Guy's Ruby Slippers; the mural with LABORATORY (the word is in MAZE's table).
"""
from harness import chapters, chapter3, maze, nav

STORY = 0x80079b44
YELLOW = 0x40
TRAIN_LEVEL = 14            # the Guardians (12) beat a party of 11-13 six times in six
                            # with the old spell choice (pending_AE); with tactics.py a
                            # party of 13-14 won 12 of 12 (bench g14b, 2026-10-14). The
                            # Jail Ogre is level 17
TRAIN_AREAS = (20, 19)


@chapters.chapter
class Chapter8:
    n = 8
    title = 'Area A: the yellow stone and the Jail Ogre'

    def goals(self, run):
        g = run.g

        def light():
            if nav.flag(g, STORY, 9) or nav.flag(g, STORY, 8):
                return True
            run.fit()
            run.examine((19, 11, 12), 3)
            return nav.flag(g, STORY, 9) or nav.flag(g, STORY, 8)

        def guardians():
            if nav.flag(g, STORY, 15):
                return True
            run.ready()
            run.go((22, 15, 12))
            run.heal()
            run.go((22, 16, 12))
            run.after()
            if not nav.flag(g, STORY, 15):
                return False
            return run.all_home() or 'casualties'

        def switch():
            if nav.flag(g, STORY, 25):
                return True
            run.fit()
            run.examine((22, 18, 12), 3)
            return nav.flag(g, STORY, 25)

        def ogre():
            if (g.u8(maze.AREA),) + g.pos() == (19, 19, 11) or chapter3.tablet_stones(g) & YELLOW:
                return True
            if g.u8(maze.AREA) != 19:
                run.ready()
                # walking to the chute square itself drops the party to B4 mid-walk, and
                # travel then plans a way back up to it (q8w4, 2026-10-14: "no path" to
                # the B4 ladder): stand on the switch square east of it and step west
                run.go((22, 18, 12))
                for _ in range(3):
                    if g.u8(maze.AREA) != 22:
                        break
                    if maze.step(g, 3) == 'interrupted':
                        run.after()
                run.after()
            # into the den: the iron bars on the east side of (17, 11), Investigate facing
            # east (MAZE square_examine case 0x32: while story bit 10 and event flag 0x20
            # are clear it shows message 99 and moves the party two squares east, to
            # (19, 11)). A plain walk finds no way in (q8w4, 2026-10-14: "no path").
            run.examine((19, 17, 11), 1, fight=True)
            run.note('ogre', (g.u8(maze.AREA),) + g.pos(), run.fights())
            return (g.u8(maze.AREA),) + g.pos() == (19, 19, 11)

        def yellow_stone():
            if chapter3.tablet_stones(g) & YELLOW:
                return True
            run.fit()
            for _ in range(2):
                # Guy's meeting on arriving at (19, 10) can take the first Investigate's
                # place (2026-10-14)
                run.examine((19, 19, 10), 0)
                if chapter3.tablet_stones(g) & YELLOW:
                    break
            return bool(chapter3.tablet_stones(g) & YELLOW)

        def out():
            run.fit()
            run.go((19, 18, 15))
            return (g.u8(maze.AREA),) + g.pos() == (19, 18, 15)

        yield from run.train_goals(TRAIN_AREAS, TRAIN_LEVEL)
        yield from run.recover_goals()
        yield 'light', light
        yield 'guardians', guardians
        yield 'switch', switch
        yield from run.recover_goals()
        yield 'ogre', ogre
        yield 'yellow_stone', yellow_stone
        yield 'out', out
