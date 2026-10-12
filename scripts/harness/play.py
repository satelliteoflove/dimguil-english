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


YESNO_STATES = (0x3d, 0x42, 0x69)    # sale, rescue, fight-warning yes/no


def talk(g, mode='leave', limit=20000):
    """Press through an NPC talk; at the menu choose Leave; answer No at every yes/no.
    Returns the number of presses.

    The talk_state numbers mean different things in different handlers (C-talk.md §4 has
    the party handlers' menu at 10/0xf/0x14 and a chat at 0x28; Guy's fixed first meeting
    runs its whole scripted talk in 0xf), so the menu is found by what it does: when
    nothing is printing, tap right; if the menu cursor moves, the icon row (Talk, Fight,
    Leave) is up. A circle there would pick Talk and start another chat (T3: a random
    meeting with Guy's party chatted for ever)."""
    f0 = g.frame
    presses = 0
    ts = lambda: g.s16(TALK_STATE) & 0xffff
    talking = lambda: g.u8(maze.GAME_STATE) == TALK
    nmsg = lambda: len(g.cap.messages) if g.cap else 0
    while talking():
        if g.frame - f0 > limit:
            raise Stuck('talk too long', ts=hex(ts()))
        t = ts()
        if t in YESNO_STATES:
            ui.move_cursor(g, YESNO, 1, 'down', 'up', what='talk yes/no')
            ui.confirm_until(g, lambda: ts() != t or not talking(), 300, 'answer no')
            presses += 1
            continue
        if g.u8(TALK_BOX) == 0:
            # quiet: is it the menu?
            c0, m0 = g.u8(TALK_MENU_CURSOR), nmsg()
            g.tap('right')
            for _ in range(12):
                g.step()
                if g.u8(TALK_MENU_CURSOR) != c0 or not talking():
                    break
            if talking() and g.u8(TALK_MENU_CURSOR) != c0:
                opts = [k for k in range(3) if g.u8(TALK_MENU) & (1 << k)]
                want = opts.index(2) if 2 in opts else len(opts) - 1
                ui.move_cursor(g, TALK_MENU_CURSOR, want, 'right', 'left', wrap=len(opts),
                               what='talk menu')
                t1 = ts()
                ui.confirm_until(g, lambda: ts() != t1 or not talking(), 300, 'leave talk')
                presses += 1
                continue
            if not talking():
                break
        # a line, or a gap that waits: press once, then let the talk react
        sig = lambda: (ts(), g.u8(TALK_BOX), nmsg(), g.u8(maze.GAME_STATE))
        s0 = sig()
        g.tap('circle')
        presses += 1
        for _ in range(24):
            if sig() != s0:
                break
            g.step()
    return presses


PROMPT = 6                    # game_state while an event's Yes/No waits ("Will you touch it?")
PROMPT_CURSOR = 0x8007e800    # maze_prompt_answer: 0 Yes, 1 No


class Policy:
    chest = 'leave'
    battle = staticmethod(battle.default_policy)
    talk = 'leave'
    prompt = 'yes'            # event Yes/No prompts: 'yes' or 'no'


def close_box(g, limit=600, react=20):
    """Press a maze box away: one press, then wait up to `react` frames for it to react
    before pressing again. A retry press that lands just after the box closes counts as a
    fresh press on the square: facing a door, it opens "The door is locked." again
    (T3, 2026-10-12, the sealed Shrine door looped this way)."""
    closed = lambda: (g.u8(maze.MSG) not in (2, 3) and not g.u8(maze.EVENT_BOX)
                      and not maze.box_up(g)) or not maze.in_maze(g)
    f0 = g.frame            # restarts whenever the box changes: `limit` is frames
    dead = 0                # without progress, so long multi-page sequences can run
    while not closed():
        if g.frame - f0 > limit:
            raise Stuck('event box', where=g.where(), msg=g.u8(maze.MSG), ev=g.u8(maze.EVENT_BOX))
        sig = lambda: (g.u8(maze.MSG), g.u8(maze.EVENT_BOX), g.u16(maze.BOX_GLYPHS), g.u8(maze.PRINTER),
                       g.u8(maze.FADE_B), g.u8(0x8007967e), g.overlay())
        s0 = sig()
        g.tap('circle')
        for _ in range(react):
            if closed() or sig() != s0:
                break
            g.step()
        if sig() == s0:
            dead += 1
        else:
            dead = 0
            f0 = g.frame
        if dead >= 3 and maze.calm_but_box(g):
            # presses do nothing, yet the party could walk: a leftover box
            maze.mark_stale_box(g)
            return
        if dead >= 12:
            # nothing on screen reacts to presses: the game (or the emulator) has hung.
            # Seen once (t3c retry 2): "The pillar begins to shake..." with the box driver
            # never called again. Report it as such instead of retrying blindly.
            raise Stuck('game not responding', where=g.where(), printer=hex(g.u8(maze.PRINTER)),
                        glyphs=g.u16(maze.BOX_GLYPHS))


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
        if maze.in_maze(g):
            if maze.calm(g):
                return 'calm'
            if g.u8(maze.GAME_STATE) == 3:
                return 'camp'
            if g.u8(maze.GAME_STATE) == PROMPT:
                return 'prompt'
            if g.u8(maze.GAME_STATE) == 0 and g.u8(maze.MSG) in (2, 3):
                return 'box'
            if g.u8(maze.EVENT_BOX) or maze.box_up(g):
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
            close_box(g)
            continue
        if what == 'camp':
            from harness import camp
            camp.close_camp(g)
            continue
        if what == 'prompt':
            want = 0 if policy.prompt == 'yes' else 1
            ui.move_cursor(g, PROMPT_CURSOR, want, 'down', 'up', what='event yes/no')
            ui.confirm_until(g, lambda: g.u8(maze.GAME_STATE) != PROMPT, 300, 'answer prompt')
            if log is not None:
                log.append((g.frame, 'prompt', policy.prompt))
            continue
        if what == 'talk':
            n = talk(g, policy.talk)
            if log is not None:
                log.append((g.frame, 'talked', n))
            continue
        return False
    return False
