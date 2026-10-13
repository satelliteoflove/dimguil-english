"""Walkthrough chapter 6, Area X and the white stone (2026-10-13).

Source: data/walkthrough/dim/06-area-x.json, data/maps/dim/f18.json and MAZE's
square_examine (rips/re/decomp/MAZE/800bb790, cases 0x2c and 0x2f) and the glyph pad
(FUN_800b957c and its dispatcher 800c1070 case 0x10). Area 18 is Area X, 20 Area A B3.
Site squares E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  white_stone  the Tablet's stone bit 4 (MAZE 0x800b7310(4)): Area X E15 N16 (15, 7),
               Investigate facing north (square_examine 0x2f). Fontana's party talks on
               arriving and can leave the party a square off; examine walks back.
  staff        story_flags (0x80079b44) bit 4, door A: the pedestal of small tablets at
               E11 N12 (11, 11), Investigate facing south (0x2c), with the Tablet. Its
               boxes end on the glyph pad (game_state 13): two rows of 13 ancient
               letters, the cursor 0x80079790 = row * 14 + column (column 13: C, which
               deletes the last letter, on the top row; END on the bottom), the letters
               typed at 0x80089f90 (u8[10], 0xff empty) and their count at 0x80079791.
               Pad place p holds ancient letter 0x800ef388[p]; ancient letter i is A-Z
               letter i (decipher_score, MCARD 0x800d9ae4), and the words follow the
               table at 0x800ef3a4 in A-Z indices (STAFF, LABORATORY, WAREHOUSE,
               ENERGY). Type STAFF, then END.
  area_a       in Area A (area 20): door A at E15 N12 opens east, and the lift at E16 N12
               (16, 11) takes the party to B3 E2 N12.
Not done here: the walkthrough's Ruby Slippers (1,600 Gp at Boltac's), wanted in Area A.
"""
from harness import chapters, chapter1, chapter3, maze, nav, ui
from harness.game import Stuck

STORY = 0x80079b44
WHITE = 0x10
PAD_STATE = 13
PAD_CURSOR = 0x80079790
PAD_COUNT = 0x80079791
PAD_TYPED = 0x80089f90
PAD_LETTERS = 0x800ef388
PAD_DELETE, PAD_END = 13, 27


def pad_place(g, letter):
    """Pad place holding A-Z `letter`."""
    table = list(g.e.read(PAD_LETTERS, 28))
    k = ord(letter) - ord('A')
    for p, v in enumerate(table):
        if p not in (PAD_DELETE, PAD_END) and v == k:
            return p
    raise Stuck('no pad place', letter=letter, table=table)


def pad_move(g, p):
    """Cursor to pad place p: the row with up/down, then the column with left/right."""
    for _ in range(40):
        cur = g.u8(PAD_CURSOR)
        if cur == p:
            return
        if cur // 14 != p // 14:
            btn = 'down' if p // 14 > cur // 14 else 'up'
        else:
            btn = 'right' if p % 14 > cur % 14 else 'left'
        ui.press_until(g, btn, lambda: g.u8(PAD_CURSOR) != cur, 120, 'pad cursor')
    raise Stuck('pad cursor', at=g.u8(PAD_CURSOR), want=p)


def pad_type(g, word):
    """Clear the pad, type `word`, check it in PAD_TYPED, press END."""
    pad_move(g, PAD_DELETE)
    for _ in range(12):
        n = g.u8(PAD_COUNT)
        if not n:
            break
        ui.press_until(g, 'circle', lambda: g.u8(PAD_COUNT) != n, 120, 'pad delete')
    for ch in word:
        pad_move(g, pad_place(g, ch))
        n = g.u8(PAD_COUNT)
        ui.press_until(g, 'circle', lambda: g.u8(PAD_COUNT) != n, 120, 'pad letter')
    typed = list(g.e.read(PAD_TYPED, len(word)))
    if typed != [ord(c) - ord('A') for c in word]:
        raise Stuck('pad typed', typed=typed, word=word)
    pad_move(g, PAD_END)
    ui.press_until(g, 'circle', lambda: g.u8(maze.GAME_STATE) != PAD_STATE, 120, 'pad END')


@chapters.chapter
class Chapter6:
    n = 6
    title = 'Area X and the white stone'

    def goals(self, run):
        g = run.g

        def white_stone():
            if chapter3.tablet_stones(g) & WHITE:
                return True
            run.fit()
            run.examine((18, 15, 7), 0)
            return bool(chapter3.tablet_stones(g) & WHITE)

        def staff():
            if nav.flag(g, STORY, 4):
                return True
            run.fit()
            for _ in range(3):
                run.go((18, 11, 11))
                if not maze.face(g, 2):
                    run.after()
                if (g.u8(maze.AREA),) + g.pos() == (18, 11, 11) and g.u8(maze.FACE) == 2:
                    break
            chapter1.investigate(g)
            # press through the pedestal's boxes up to the pad, no further: a press on
            # the pad types a letter
            end = g.frame + 3000
            quiet = 0
            while g.u8(maze.GAME_STATE) != PAD_STATE:
                if g.frame > end:
                    raise Stuck('glyph pad', where=g.where())
                quiet = quiet + 1 if maze.calm(g) else 0
                if quiet > 40:
                    # calm 800 frames and no pad (no Tablet?). "Searching..." alone
                    # takes ~340 frames before the pedestal's box comes up
                    return False
                if maze.calm(g):
                    g.step(20)
                    continue
                g.tap('circle')
                for _ in range(20):
                    if g.u8(maze.GAME_STATE) == PAD_STATE:
                        break
                    g.step()
            pad_type(g, 'STAFF')
            run.after()
            return nav.flag(g, STORY, 4)

        def area_a():
            if g.u8(maze.AREA) == 20:
                return True
            run.fit()
            run.go((20, 2, 11))
            return g.u8(maze.AREA) == 20

        yield from run.recover_goals()
        yield 'white_stone', white_stone
        yield 'staff', staff
        yield 'area_a', area_a
