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
QUIET_TALK = 24                      # frames a quiet talk is left to settle before a press
HEAL_PICK = 0x32                     # the heal offer's "Whom shall I heal?" (C-talk.md §4)
PICK_COL, PICK_ROW = 0x800796cc, 0x800796cd   # its cursor: party slot = row x 3 + col (talk_cresson 0x800d65c8)
RAISE_TALKS = 40                     # mode 'raise': Talk presses before giving up (~560 frames each)
TALKS = [0]


def raise_target(g):
    """The party slot of a dead or ashed member (not lost), or None."""
    for k, ri in enumerate(g.party_slots()):
        if ri is not None and g.char(ri)['status'] & 0x180 and not g.char(ri)['status'] & 0x200:
            return k
    return None


def talk(g, mode='leave', limit=20000):
    """Press through an NPC talk; at the menu choose Leave; answer No at every yes/no.
    Returns the number of presses.

    The talk_state numbers mean different things in different handlers (C-talk.md §4 has
    the party handlers' menu at 10/0xf/0x14 and a chat at 0x28; Guy's fixed first meeting
    runs its whole scripted talk in 0xf), so the menu is found by what it does: when
    nothing is printing, tap right; if the menu cursor moves, the icon row (Talk, Fight,
    Leave) is up. A circle there would pick Talk and start another chat (T3: a random
    meeting with Guy's party chatted for ever).

    mode 'raise' (revision 9, agent 14): Talk instead of Leave while a member is dead or
    ashed, up to RAISE_TALKS times, and at a heal offer pick that member: an NPC's Kadorto
    is free and certain (C-talk.md §5; Cleo raised a dead Dax to full HP in the emulator,
    age and stats unchanged, 2026-10-14). TALKS[0] counts the Talk presses."""
    f0 = g.frame
    presses = 0
    TALKS[0] = 0
    ts = lambda: g.s16(TALK_STATE) & 0xffff
    talking = lambda: g.u8(maze.GAME_STATE) == TALK
    nmsg = lambda: len(g.cap.messages) if g.cap else 0
    while talking():
        if g.frame - f0 > limit:
            raise Stuck('talk too long', ts=hex(ts()))
        t = ts()
        if t == HEAL_PICK and mode == 'raise' and raise_target(g) is not None:
            k = raise_target(g)
            ui.move_cursor(g, PICK_ROW, k // 3, 'down', 'up', wrap=2, what='heal pick row')
            ui.move_cursor(g, PICK_COL, k % 3, 'right', 'left', wrap=3, what='heal pick column')
            ui.confirm_until(g, lambda: ts() != t or not talking(), 300, 'heal pick')
            presses += 1
            continue
        if t in YESNO_STATES:
            # mode 'fight' answers Yes to the fight warning (0x69) and No to the rest
            ui.move_cursor(g, YESNO, 0 if mode == 'fight' and t == 0x69 else 1, 'down', 'up',
                           what='talk yes/no')
            ui.confirm_until(g, lambda: ts() != t or not talking(), 300, 'answer no')
            presses += 1
            continue
        if g.u8(TALK_BOX) == 0:
            # quiet: let whatever ends here settle first. A chat topic (0x28) hands back
            # to the menu (0x14) some frames after its last line; a press in between
            # lands on the menu and picks Talk again (chapter 2, c2v6 and c2v1: Balbo's
            # party at Shrine 3F E11 N6 chatted for 20,000 frames).
            t0 = ts()
            for _ in range(QUIET_TALK):
                if ts() != t0 or g.u8(TALK_BOX) != 0 or not talking():
                    break
                g.step()
            if not talking():
                break
            if g.u8(TALK_BOX) != 0 or ts() != t0:
                continue
            # is it the menu?
            c0, m0 = g.u8(TALK_MENU_CURSOR), nmsg()
            g.tap('right')
            for _ in range(12):
                g.step()
                if g.u8(TALK_MENU_CURSOR) != c0 or not talking():
                    break
            if talking() and g.u8(TALK_MENU_CURSOR) != c0:
                opts = [k for k in range(3) if g.u8(TALK_MENU) & (1 << k)]
                want = opts.index(2) if 2 in opts else len(opts) - 1
                if mode == 'raise' and 0 in opts and TALKS[0] < RAISE_TALKS and raise_target(g) is not None:
                    want = opts.index(0)
                    TALKS[0] += 1
                if mode == 'fight' and 1 in opts:
                    # a meeting that has to be fought (chapter 8: the Jail Ogre comes as
                    # "You've met someone!" and Leave walks the party back a square)
                    want = opts.index(1)
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


SCENE = 0x80079878         # a maze scene in progress (5 a meeting's approach, 9 the jewel lift)
SCENE_COUNT = 0x8008a000   # its countdown
QUIET_WAIT = 900           # close_box's wait without presses before "not responding"
BOX_MAX = 20000            # frames one close_box may take in all
SCENE_MAX = 3000           # the longest wait on one (the B3 lift ride up is ~1,050 frames)


DROP_CURSOR = 0x80079c60     # "Drop which item?": the pack position under the cursor
DROP_YES = 0x80079c65        # "Really throw it away?": 0 Yes, 1 No (the default)


DROP_PROMPTS = (90, 36, 237)


def _drop_prompt_msg(g):
    """(position, idx) of the latest drop prompt among the SISETU lines since anything
    else printed (the list's item names print after "Drop which item?"), unless it was
    handled already."""
    if not g.cap:
        return None
    ms = g.cap.messages
    for j in range(len(ms) - 1, max(-1, len(ms) - 60), -1):
        m = ms[j]
        if m['file'] == 'SISETU.OBJ' and m['idx'] in DROP_PROMPTS:
            done = g.__dict__.setdefault('_drop_done', set())
            if j in done:
                return None
            done.add(j)
            return j, m['idx']
        if m['file'] not in ('SISETU.OBJ', 'STATUS.OBJ'):
            return None
    return None


def drop_choice(g):
    """The pack position to throw away: the last one that's spare loot (unequipped, an id
    under 0x100, so not the Tablet, a stone or a story item) in every full pack, since
    which member the game asks isn't known here."""
    full = [g.char(i)['items'] for i in g.party() if len(g.char(i)['items']) >= 10]
    ok = lambda k: all(k < len(p) and not p[k] & 0x2000 and (p[k] & 0x1ff) < 0x100 for p in full)
    return next((k for k in range(9, -1, -1) if ok(k)), 9)


def drop_prompt(g):
    """A story item found with a full pack: "Your pack is full. Who will drop it?" (92,
    303; the press picks the member under the cursor), "Drop which item?" (90), then
    "Really throw it away?" (36, cursor on No). Throws away spare loot so the item fits (r2v6b
    chapter 2, 2026-10-13: the jade mask with ten items in every pack; circle took the
    equipped breast plate, "It's equipped, so it can't be dropped.", for ever). Returns
    True if it acted."""
    p = _drop_prompt_msg(g)
    last = ('SISETU.OBJ', p[1]) if p else None
    if last == ('SISETU.OBJ', 90):
        ui.wait_until(g, lambda: g.u8(maze.PRINTER) != 4, 120, 'drop list')
        ui.move_cursor(g, DROP_CURSOR, drop_choice(g), 'down', 'up', what='drop item')
        n = len(g.cap.messages)
        ui.press_until(g, 'circle', lambda: len(g.cap.messages) > n, 120, 'pick drop item')
        g.step(20)
        return True
    if last == ('SISETU.OBJ', 36):
        g.step(20)
        ui.move_cursor(g, DROP_YES, 0, 'down', 'up', what='throw away yes')
        n = len(g.cap.messages)
        ui.press_until(g, 'circle', lambda: len(g.cap.messages) > n or g.u8(DROP_YES) != 0,
                       120, 'throw away')
        g.step(20)
        return True
    if last == ('SISETU.OBJ', 237):
        # "It's equipped, so it can't be dropped.": back to the list
        g.tap('cross', hold=6)
        g.step(40)
        return True
    return False


def close_box(g, limit=600, react=20):
    """Press a maze box away: one press, then wait up to `react` frames for it to react
    before pressing again. A retry press that lands just after the box closes counts as a
    fresh press on the square: facing a door, it opens "The door is locked." again
    (T3, 2026-10-12, the sealed Shrine door looped this way)."""
    closed = lambda: (g.u8(maze.MSG) not in (2, 3) and not g.u8(maze.EVENT_BOX)
                      and not maze.box_up(g)) or not maze.in_maze(g)
    f0 = g.frame            # restarts whenever the box changes: `limit` is frames
    dead = 0                # without progress, so long multi-page sequences can run
    scene_f = 0             # frames spent waiting on a scene's countdown
    start = g.frame
    while not closed():
        if g.frame - start > BOX_MAX:
            # progress that never ends: a menu the presses walk round (r2v6b's "Drop
            # which item?" at the jade mask with a full pack)
            raise Stuck('event box too long', where=g.where(), msg=g.u8(maze.MSG))
        if maze.wait_cd(g):
            # a stalled disc read (bugs.md 1.12 on an old MAIN): waited out, not progress
            # lost; the box timers start again
            f0 = g.frame
            dead = 0
            continue
        if g.frame - f0 > limit:
            raise Stuck('event box', where=g.where(), msg=g.u8(maze.MSG), ev=g.u8(maze.EVENT_BOX))
        if g.u8(SCENE) not in (0, 0xff) and scene_f < SCENE_MAX:
            # a scene may run under the box: the jewel lift rides down floor by floor
            # (0x80079878 = 9, its countdown at 0x8008a000) with "the floor begins to
            # move!" left up; presses do nothing until it ends (r2v3, 2026-10-13: called
            # "game not responding"). Wait only while its countdown moves; other scenes
            # leave the byte set with no countdown and want presses (the T5 round at
            # 03:24 failed 74 cases when this waited on the byte alone).
            # Capped at SCENE_MAX: some countdowns never stop moving (r2v6b's jade mask,
            # 2026-10-13, waited here without end).
            c = g.u16(SCENE_COUNT)
            g.step(8)
            scene_f += 8
            if g.u16(SCENE_COUNT) != c:
                f0 = g.frame
                dead = 0
                continue
        if drop_prompt(g):
            f0 = g.frame
            dead = 0
            continue
        in_scene = g.u8(SCENE) not in (0, 0xff)
        sig = lambda: (g.u8(maze.MSG), g.u8(maze.EVENT_BOX), g.u16(maze.BOX_GLYPHS), g.u8(maze.PRINTER),
                       g.u8(maze.FADE_B), g.u8(0x8007967e), g.overlay())
        s0 = sig()
        g.tap('circle')
        for _ in range(react):
            if closed() or sig() != s0:
                break
            g.step()
        if sig() == s0:
            # a scene with no countdown ignores presses too: the Shrine exit's fade
            # (0x80079878 = 8, ~220 frames) under "the door swings open", then a few
            # frames more (c1v0c train_05 cases, round 18: "game not responding")
            dead += 0 if in_scene else 1
        else:
            dead = 0
            f0 = g.frame
        if dead >= 3 and maze.calm_but_box(g):
            # presses do nothing, yet the party could walk: a leftover box
            maze.mark_stale_box(g)
            return
        if dead == 12:
            # before calling it hung, leave it alone a while: crossing the parted stream
            # on B2 (7, 11) blacks the screen with the box flags up and no scene byte, and
            # it comes back by itself about 200 frames later (f1v0 chapter 4, 2026-10-13:
            # "game not responding" six times)
            f1 = g.frame
            while g.frame - f1 < QUIET_WAIT and not closed() and sig() == s0:
                g.step(4)
            if closed() or sig() != s0:
                dead = 0
                f0 = g.frame
                continue
            dead += 1
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
