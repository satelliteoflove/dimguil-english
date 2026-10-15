"""Walkthrough chapter 16, Area A: the gold stone (2026-10-15).

Source: data/walkthrough/dim/16-gold-stone.json, data/maps/dim/mimicry/f20.json and
f21.json (Area A B3 and B2 after mimicry mode, areas 20 and 21; nav reads them once story
bit 10 is set), and MAZE: square_examine 0x800bb790 (0x5e the altar, 3 hidden doors), the
dispatcher 0x800c1070 (0x1d the pad, 0x26-0x27 the Crystal Man's fight), the glyph pad
0x800b989c (word 6 GAME, area 21 only), the stone check 0x800b7248 and the fight reward
0x800c0748 (type 0xd: FUN_800b7310(3)). Site squares E x N y are the game's (x, 23 - y).

nav plans the walkthrough's route by itself: the lift from Area X (E16 N12) to B3 E2 N12,
B3's new door south of E2 N9, the stairs up at E3 N3 to B2 E2 N3, the door east of E2 N6,
the hidden door, the altar.

Goals, each proved by RAM:
  hidden_door  bit 31 of the hidden doors found (0x80079628): B2's hidden door east of E4
               N5 (4, 18) (type 3, p1 31, only in the post-mimicry file), found by nav's
               walk to the room beyond, E5 N5 (5, 18).
  gold_stone   the Tablet's stone bit 3 (its item_state byte): the altar at B2 E6 N5 (6,
               18), Investigate facing north (0x5e) with the Tablet and no gold stone:
               EVENTMES 108 and the glyph pad (dispatcher 0x1d). GAME (word 6, counted
               only in area 21) brings EVENTMES 109 and 110, then the Crystal Man's fight
               (fight type 0x13, reward type 0xd); the win sets bit 3 (EVENTMES 111). Any
               other word gets EVENTMES 104. Without the Tablet, or with the stone in it,
               the altar prints EVENTMES 103 only.
  out          back in town.
Not done: Guy's party (NPC_MES1 287) is a random meeting, not a goal.
"""
from harness import chapters, chapter3, chapter6, chapter14, maze, nav

STORY = 0x80079b44
ROOM = (21, 5, 18)              # past the hidden door
ALTAR = (21, 6, 18)             # Investigate facing north
DOOR_P1 = 31
GOLD_BIT = 3
PAD_WORDS = 0x800ef3a4          # seven words of ten glyphs (A = 0, 0xff pad)
RIDDLE = 'GAME'


def here(g):
    return (g.u8(maze.AREA),) + g.pos()


def has_stone(g):
    return bool(chapter3.tablet_stones(g) >> GOLD_BIT & 1)


@chapters.chapter
class Chapter16:
    n = 16
    title = 'Area A: the gold stone'

    def goals(self, run):
        g = run.g

        def hidden_door():
            if nav.hidden_found(g, DOOR_P1):
                return True
            if not nav.flag(g, STORY, 10):
                return False
            run.fit()
            run.go(ROOM)
            run.after()
            return nav.hidden_found(g, DOOR_P1)

        def gold_stone():
            if has_stone(g):
                return True
            if not nav.hidden_found(g, DOOR_P1):
                return False
            word = list(g.e.read(PAD_WORDS + 60, len(RIDDLE)))
            if word != [ord(c) - ord('A') for c in RIDDLE]:
                run.note('pad word 6 is not GAME', word)
            run.ready()
            run.go(ALTAR)
            while run.door_ready():
                run.ready(train=False)
                run.go(ALTAR)
            run.heal()
            for _ in range(3):
                run.go(ALTAR)
                if here(g) == ALTAR and (g.u8(maze.FACE) == 0 or maze.face(g, 0)):
                    break
                run.after()
            if here(g) != ALTAR or g.u8(maze.FACE) != 0:
                return False
            from harness import chapter1
            chapter1.investigate(g)
            typed = []

            def step(g):
                if g.u8(maze.GAME_STATE) == chapter6.PAD_STATE and not typed:
                    g.step(20)
                    chapter6.pad_type(g, RIDDLE)
                    typed.append(g.frame)
                    run.log.append((g.frame, 'altar', RIDDLE))
                    return True
                return False
            chapter14.drive(g, step)
            run.after()
            if not has_stone(g):
                return False
            return run.all_home() or 'casualties'

        def out():
            if g.overlay() in ('JOUKA', 'HAZURE'):
                return True
            run.trip_home('chapter end')
            return g.overlay() in ('JOUKA', 'HAZURE')

        yield from run.recover_goals()
        yield 'hidden_door', hidden_door
        yield 'gold_stone', gold_stone
        yield 'out', out
