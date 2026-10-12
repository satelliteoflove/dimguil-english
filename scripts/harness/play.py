"""Putting the macros together: what to do when a walk is interrupted.

handle_interrupt(g) is walk_to's on_interrupt: it fights battles (battle.fight), walks
away from NPC parties (Leave), and presses through event boxes. It returns True when the
party is back to walking, False when it can't tell what the game wants (the caller stops
with a report).
"""
from harness import ui, maze, battle
from harness.game import Stuck

TALK_STATE = 0x8007981c       # s16: 0x28 the talk menu, 0x41 an offer, 0x42 yes/no; <0 done
TALK_MENU = 0x80079b50        # the talk menu's options: bit 0 Talk, bit 1 Fight, bit 2 Leave
TALK_MENU_CURSOR = 0x80079b8c
TALK_BOX = 0x80079a3e         # the talk box's state (1-3 opening and shown, 0 closed)
YESNO = 0x80079c5a            # 0 = Yes
TALK = 0x35                   # game_state while an NPC talk runs (MCARD)


def talk(g, mode='leave', limit=20000):
    """Press through an NPC talk. At the talk menu choose Leave (mode 'leave'); answer
    No to offers. Returns the number of presses."""
    f0 = g.frame
    presses = 0
    while g.u8(maze.GAME_STATE) == TALK:
        if g.frame - f0 > limit:
            raise Stuck('talk too long', ts=g.s16(TALK_STATE))
        ts = g.s16(TALK_STATE)
        if ts == 0x28:
            opts = [k for k in range(3) if g.u8(TALK_MENU) & (1 << k)]
            want = opts.index(2) if 2 in opts else len(opts) - 1
            ui.move_cursor(g, TALK_MENU_CURSOR, want, 'down', 'up', what='talk menu')
            ui.confirm_until(g, lambda: g.s16(TALK_STATE) != 0x28
                             or g.u8(maze.GAME_STATE) != TALK, 300, 'leave talk')
            presses += 1
            continue
        if ts == 0x42:
            ui.move_cursor(g, YESNO, 1, 'down', 'up', what='talk yes/no')
            ui.confirm_until(g, lambda: g.s16(TALK_STATE) != 0x42
                             or g.u8(maze.GAME_STATE) != TALK, 300, 'answer no')
            presses += 1
            continue
        # anything else waits for a press: tap until the talk moves on
        sig = lambda: (g.s16(TALK_STATE), g.u8(TALK_BOX), len(g.cap.messages) if g.cap else 0,
                       g.u8(maze.GAME_STATE))
        s0 = sig()
        ui.press_until(g, 'circle', lambda: sig() != s0, 600, 'talk')
        presses += 1
    return presses


class Policy:
    chest = 'leave'
    battle = staticmethod(battle.default_policy)
    talk = 'leave'


def wait_settled(g, limit=1800):
    """Run until something definite: walking, a battle's command phase or chest, a talk,
    or an event box. Returns a label."""
    f0 = g.frame
    while g.frame - f0 < limit:
        o = g.overlay()
        if o == 'BATTLE':
            return 'battle'
        if g.u8(maze.GAME_STATE) == TALK:
            return 'talk'
        if o == 'MAZE':
            if maze.calm(g):
                return 'calm'
            if g.u8(maze.GAME_STATE) == 0 and g.u8(maze.MSG) in (2, 3):
                return 'box'
            if g.u8(maze.EVENT_BOX):
                return 'box'
        g.step()
    return 'unknown'


def handle_interrupt(g, policy=Policy, log=None):
    for _ in range(20):
        what = wait_settled(g)
        if log is not None:
            log.append((g.frame, what, g.where()))
        if what == 'calm':
            return True
        if what == 'battle':
            r = battle.fight(g, policy.battle, policy.chest)
            if log is not None:
                log.append((g.frame, 'fought', {k: v for k, v in r.items() if k != 'actions'}))
            continue
        if what == 'box':
            ui.confirm_until(g, lambda: g.u8(maze.MSG) not in (2, 3) and not g.u8(maze.EVENT_BOX)
                             or g.overlay() != 'MAZE', 600, 'event box')
            continue
        if what == 'talk':
            n = talk(g, policy.talk)
            if log is not None:
                log.append((g.frame, 'talked', n))
            continue
        return False
    return False
