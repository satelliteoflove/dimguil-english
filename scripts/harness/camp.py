"""The camp: open it, cast a spell on a member, leave. RAM-checked.

RAM (docs/re/B-camp.md; cursors found with probe.py 2026-10-12):
  0x80079a13 game_state 3 while the camp is open
  0x80079669 camp_state: 5 the icon menu, 10 Inspect Character, 35 leaving
  0x80079964 camp_sub_state: 5 "Inspect whom?", 15 the member's menu, 20 casting
  0x800799e6 camp_spell_state: 5 realm/level grid, 10 the level's spells, 30 "Cast it on
             whom?", 45 "Spell cast", 50 done
  0x80079b8c the icon cursor (0 Inspect)
  0x800796cc / 0x800796cd member grid x / y (3 by 2), for "Inspect whom?" and targets
  0x80079c5c the member menu cursor (0 Cast Spell, 1 Items, 2 Pool Gold, 3 Back)
  0x80079c60 / 0x80079c5d the spell grid's realm row / level column
  0x80079c65 the spell list cursor
"""
from harness import ui, maze
from harness.game import Stuck

CAMP = 3
CAMP_STATE, SUB, SPELL_STATE = 0x80079669, 0x80079964, 0x800799e6
ICON = 0x80079b8c
MX, MY = 0x800796cc, 0x800796cd
MENU = 0x80079c5c
REALM, LEVEL, SLOT = 0x80079c60, 0x80079c5d, 0x80079c65


def in_camp(g):
    return g.u8(maze.GAME_STATE) == CAMP


def open_camp(g):
    if not in_camp(g):
        if not maze.calm(g):
            maze.settle(g)
        ui.cancel_until(g, lambda: in_camp(g), 300, 'open camp')
        ui.wait_until(g, lambda: g.u8(CAMP_STATE) == 5, 300, 'camp menu')
        return
    # already in camp, maybe still on a member's screen after a cast ("Cast the spell."):
    # back out to the icon menu, one screen at a time
    end = g.frame + 900
    while g.u8(CAMP_STATE) != 5:
        if g.frame > end:
            raise Stuck('camp menu', cs=g.u8(CAMP_STATE), sub=g.u8(SUB), sp=g.u8(SPELL_STATE))
        s0 = (g.u8(CAMP_STATE), g.u8(SUB), g.u8(SPELL_STATE))
        ui.press_until(g, 'cross', lambda: (g.u8(CAMP_STATE), g.u8(SUB), g.u8(SPELL_STATE)) != s0
                       or g.u8(CAMP_STATE) == 5, 120, 'camp back')


def close_camp(g):
    """Back out to the icon menu, then out of the camp, then wait for calm."""
    end = g.frame + 1200
    while in_camp(g):
        if g.frame > end:
            raise Stuck('close camp', cs=g.u8(CAMP_STATE), sub=g.u8(SUB))
        # one press, then up to 30 frames for it to land: a burst of presses can leave
        # one over after the camp closes, which opens it again (T4, t4v0 at the dog
        # pillar: camp, close, camp... for 6 retries)
        # From the icon menu (5) the camp takes several frames to close, and a cross
        # that lands after it has closed opens it again; so from there wait for the
        # walking state before anything else. Elsewhere, wait for the screen to settle
        # (8 frames unchanged) between presses.
        sig = lambda: (g.u8(CAMP_STATE), g.u8(SUB), g.u8(SPELL_STATE), g.u8(maze.GAME_STATE))
        at_menu = g.u8(CAMP_STATE) == 5
        g.tap('cross')
        if at_menu:
            for _ in range(90):
                if g.u8(maze.GAME_STATE) != 3:
                    break
                g.step()
            continue
        s, same = sig(), 0
        for _ in range(60):
            g.step()
            same = same + 1 if sig() == s else 0
            s = sig()
            if same >= 8:
                break
    ui.wait_until(g, lambda: maze.calm(g), 600, 'after camp')


def _pick_member(g, slot, what):
    ui.move_cursor(g, MY, slot // 3, 'down', 'up', what=what + ' row')
    ui.move_cursor(g, MX, slot % 3, 'right', 'left', what=what + ' col')


def cast(g, caster, school, level, index, target=None):
    """Cast from camp: party slot `caster`, realm/level, the spell's place in the level's
    list, on party slot `target` (if it asks). Returns the camp messages printed."""
    open_camp(g)
    n = len(g.cap.messages) if g.cap else 0
    ui.move_cursor(g, ICON, 0, 'right', 'left', what='camp icon')
    ui.confirm_until(g, lambda: g.u8(CAMP_STATE) == 10 and g.u8(SUB) == 5, 300, 'Inspect')
    _pick_member(g, caster, 'inspect')
    ui.confirm_until(g, lambda: g.u8(SUB) == 15, 300, 'inspect member')
    ui.move_cursor(g, MENU, 0, 'down', 'up', what='Cast Spell')
    ui.confirm_until(g, lambda: g.u8(SUB) == 20 and g.u8(SPELL_STATE) == 5, 300, 'Cast Spell')
    ui.move_cursor(g, REALM, school, 'down', 'up', what='realm')
    ui.move_cursor(g, LEVEL, level - 1, 'right', 'left', what='level')
    ui.confirm_until(g, lambda: g.u8(SPELL_STATE) == 10, 300, 'level')
    ui.move_cursor(g, SLOT, index, 'down', 'up', what='spell')
    ui.confirm_until(g, lambda: g.u8(SPELL_STATE) != 10, 300, 'spell')
    # the state passes through others before "Cast it on whom?" (30) comes up: wait for a
    # settled one, or the target pick is skipped and the confirm lands on the default
    # slot (T3, 2026-10-12: it landed on an empty slot and the cast never happened)
    ui.wait_until(g, lambda: g.u8(SPELL_STATE) in (30, 45, 50, 0) or g.u8(SUB) != 20
                  or not in_camp(g), 300, 'spell target screen')
    if g.u8(SPELL_STATE) == 30 and target is not None:
        _pick_member(g, target, 'target')
    # confirm the target and press through "Spell cast" and its result
    ui.confirm_until(g, lambda: g.u8(SPELL_STATE) in (0, 50) or g.u8(SUB) != 20
                     or not in_camp(g), 600, 'cast')
    msgs = [(m['file'], m['idx'], m['text']) for m in g.cap.messages[n:]] if g.cap else []
    return msgs
