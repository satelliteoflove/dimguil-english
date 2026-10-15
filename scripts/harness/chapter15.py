"""Walkthrough chapter 15, Area C: the Demon's Statue (2026-10-15).

Source: data/walkthrough/dim/15-demons-statue.json, data/maps/dim/mimicry/f28-f31.json
(Area C B4 to B1 after mimicry mode, areas 28-31; nav reads them once story bit 10 is
set), and MAZE: square_examine 0x800bb790 (0x20 signs, 0x4b the lift, 0x49 the wreck),
FUN_800ce108 (the lift's scene), maze_prompt_result 0x800befcc (prompt 0x13) and the item
give 0x800cbb0c. Site squares E x N y are the game's (x, 23 - y).

The chain plays it after Area D, so the moving floors are gone and nav plans the
walkthrough's route by itself: B1's door B, down at B1 E11 N18, B2 E11 N17 down, B3 E8
N14 up, B2 E11 N8 down, B3 E13 N8 up, then B2's lift at E21 N8 (nav.LINKS, 'C lift down').

Goals, each proved by RAM or a captured string:
  door_b     the carving on door B, north of B1 E11 N7 (11, 16) (0x20, EVENTMES 147). No
             flag; proved by the captured string.
  statue     the Demon's Statue (item 0x13a) in a pack: the wreck at B4 E21 N6 (21, 17),
             Investigate from E20 N6 (20, 17) facing east (record 0x49, p1 = the facing it
             wants). With story bit 10 set and no statue carried: EVENTMES 186, prompt
             0x13; Yes gives 0x13a with bit 0x4000 (EVENTMES 187) to the first free pack
             slot, else the drop picker (game_state 3). Before bit 10 the wreck prints
             EVENTMES 185 only. The statue is used in the Dragon's Cave (B3's hidden door).
  teleporter the party on B1 E15 N3 (15, 20): B4 E18 N5 (18, 18) is a 0x4c teleport there.
  out        back in town.
Not done: leaving the statue with someone in the tavern, as the walkthrough suggests.
"""
from harness import chapters, gear, maze, nav

STORY = 0x80079b44
STATUE = 0x13a
WRECK_SIDE = (28, 20, 17)       # west of the wreck, facing east
DOOR_B = (31, 11, 16)
OUT = (31, 15, 20)


def said(g, n, idx):
    return not g.cap or any(m['file'] == 'EVENTMES.BIN' and m['idx'] == idx
                            for m in g.cap.messages[n:])


def here(g):
    return (g.u8(maze.AREA),) + g.pos()


def has_statue(g):
    from harness import town
    for ri in g.party() or town.town_party(g):
        if any(w & 0x1ff == STATUE and w & gear.IDENT for _, w in gear.pack(g, ri)):
            return True
    return False


@chapters.chapter
class Chapter15:
    n = 15
    title = "Area C: the Demon's Statue"

    def goals(self, run):
        g = run.g

        def door_b():
            n = len(g.cap.messages) if g.cap else 0
            run.fit()
            run.examine(DOOR_B, 0)
            return here(g) == DOOR_B and said(g, n, 147)

        def statue():
            if has_statue(g):
                return True
            if not nav.flag(g, STORY, 10):
                return False
            run.fit()
            gear.room_for_find(g, run.log)
            run.examine(WRECK_SIDE, 1)
            run.after()
            return has_statue(g)

        def teleporter():
            if not has_statue(g):
                return False
            run.fit()
            run.go(OUT)
            run.after()
            return here(g) == OUT

        def out():
            if g.overlay() in ('JOUKA', 'HAZURE'):
                return True
            run.trip_home('chapter end')
            return g.overlay() in ('JOUKA', 'HAZURE')

        yield from run.recover_goals()
        yield 'door_b', door_b
        yield 'statue', statue
        yield 'teleporter', teleporter
        yield 'out', out
