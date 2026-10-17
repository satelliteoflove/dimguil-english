"""Walkthrough chapter 11, the gold armor in Area A (2026-10-14).

Source: data/walkthrough/dim/11-gold-armor.json, data/maps/dim/f19-f22.json (Area A B4-B1,
areas 19-22), and MAZE: square_examine 0x800bb790 (0x35 the altar, 0x38 the beds), the
altar's dispatcher 0x800c1070 (case 0x16 picks the prompt from the Tablet's stones, case
0x15 the Red/Green menu), maze_prompt_result 0x800befcc (case 0xb), the floor-load locks
0x800a8f1c, party_lacks_item 0x800b73e0 and the reward 0x800c0748 / 0x800cbb0c. Site
squares E x N y are the game's (x, 23 - y).

Goals, each proved by RAM:
  red_light  story_flags (0x80079b44) bit 9: the altar at B4 E11 N11 (11, 12), Investigate
             facing west. With the green (Tablet bit 5) and red (bit 1) stones set it shows
             EVENTMES 97 and a Red/Green menu, cursor on Red (maze_prompt_answer 0x8007e800
             = 0); Circle takes it. Red sets bit 9 and clears bit 8, which locks the green
             door on B1 again and unlocks the red-crested door, west side of B1 E11 N11
             (11, 12) (square_flags lock bit 25, put back at each floor load while bit 9 is
             clear; nav.EXTRA_SEALED).
  helm, armor, gauntlets, boots
             the gold piece in a party member's pack (item id with the identified bit
             0x4000, what party_lacks_item checks). Each bed on B1 is a 0x38 square:
             Investigate facing the bed starts its zombie's fight (no prompt), and a win
             puts the piece straight into the first member with a free pack slot (a full
             party gets the drop picker, play.drop_prompt). With the piece already carried
             the bed gives a High Zombie and nothing, so the goal looks first.
               helm       bed (8, 12) [E8 N11], from (9, 12) facing west, id 0x140
               armor      bed (8, 7)  [E8 N16], from (9, 7) facing west,  id 0x13d
               gauntlets  bed (8, 15) [E8 N8],  from (9, 15) facing west, id 0x13e
               boots      bed (15, 8) [E15 N15], from (14, 8) facing east, id 0x13f
             Every bed room has a teleport trap beside the bed (0x4c, to B3): nav keeps off.
The armor fits only a Fighter, Samurai or Lord (class mask 0x31), the rest a Valkyrie as
well; all four have price 0, so Boltac's never takes them, and the battle policy never
Uses an item (their battle spells break them half the time).
"""
from harness import chapters, chapter1, gear, maze, nav, play, ui
from harness.game import Stuck

STORY = 0x80079b44
CHOICE = 0x0e       # game_state while the altar's Red/Green menu waits (0x800c1070 case 0x15)


def altar(g, log):
    """From the Investigate: through EVENTMES 97 to the Red/Green menu, Red (cursor
    0x8007e800 = 0), Circle. after_event doesn't know game_state 0x0e (n1v3r/n1v6p
    chapter 11, 2026-10-15: "after event" six times with the menu open on Red)."""
    f0 = g.frame
    while g.u8(maze.GAME_STATE) != CHOICE:
        if g.frame - f0 > 3000:
            raise Stuck('no altar menu', where=g.where())
        if g.u8(maze.GAME_STATE) == play.PROMPT:
            ui.move_cursor(g, play.PROMPT_CURSOR, 0, 'down', 'up', what='altar yes/no')
            ui.confirm_until(g, lambda: g.u8(maze.GAME_STATE) != play.PROMPT, 300, 'altar yes')
            continue
        if maze.calm(g):
            for _ in range(chapter1.QUIET):
                g.step()
                if not maze.calm(g):
                    break
            else:
                return False
            continue
        if g.u8(maze.EVENT_BOX) or maze.box_up(g):
            play.close_box(g)
            continue
        g.step()
    g.step(20)
    if g.u8(play.PROMPT_CURSOR) != 0:
        ui.move_cursor(g, play.PROMPT_CURSOR, 0, 'down', 'up', limit=120, what='altar red')
    ui.confirm_until(g, lambda: g.u8(maze.GAME_STATE) != CHOICE, 300, 'altar red')
    log.append((g.frame, 'altar', 'red'))
    return True
PIECES = (('helm', 0x140, (22, 9, 12), 3), ('armor', 0x13d, (22, 9, 7), 3),
          ('gauntlets', 0x13e, (22, 9, 15), 3), ('boots', 0x13f, (22, 14, 8), 1))


def has_piece(g, i):
    from harness import town
    for ri in g.party() or town.town_party(g):
        if any(w & 0x1ff == i and w & gear.IDENT for _, w in gear.pack(g, ri)):
            return True
    return False


@chapters.chapter
class Chapter11:
    n = 11
    title = 'The gold armor in Area A'

    def goals(self, run):
        g = run.g

        def red_light():
            if nav.flag(g, STORY, 9):
                return True
            run.fit()
            for _ in range(3):
                run.go((19, 11, 12))
                if not maze.face(g, 3):
                    run.after()
                if (g.u8(maze.AREA),) + g.pos() == (19, 11, 12) and g.u8(maze.FACE) == 3:
                    break
            chapter1.investigate(g)
            altar(g, run.log)
            run.after()
            return nav.flag(g, STORY, 9)

        def bed(i, at, facing):
            def goal():
                if has_piece(g, i):
                    return True
                run.ready()
                gear.room_for_find(g, run.log)
                run.examine(at, facing, fight=True)
                run.after()
                if not has_piece(g, i):
                    return False
                return run.all_home() or 'casualties'
            return goal

        yield from run.recover_goals()
        yield 'red_light', red_light
        for name, i, at, facing in PIECES:
            yield name, bed(i, at, facing)
