"""Generic menu moves, every one checked against RAM.

Each helper presses a button, runs only until the RAM it expects has changed (retrying
the press every RETRY frames, as inputs.press_until does), and raises game.Stuck when the
frame budget runs out. Nothing here waits a fixed number of frames.
"""
from harness.game import Stuck

RETRY = 8


def press_until(g, btn, cond, limit=600, what=None):
    """Tap btn until cond() is true. Returns frames spent; raises Stuck."""
    f0 = g.frame
    while g.frame - f0 < limit:
        if cond():
            return g.frame - f0
        g.tap(btn)
        for _ in range(RETRY):
            if cond():
                return g.frame - f0
            g.step()
    if cond():
        return g.frame - f0
    raise Stuck(what or 'press %s' % btn, frames=g.frame - f0, where=g.where())


def wait_until(g, cond, limit=600, what='wait'):
    f0 = g.frame
    while g.frame - f0 < limit:
        if cond():
            return g.frame - f0
        g.step()
    if cond():
        return g.frame - f0
    raise Stuck(what, frames=g.frame - f0, where=g.where())


def move_cursor(g, addr, target, fwd, back, limit=600, wrap=None, what=None):
    """Move a one-byte cursor at addr to target with fwd/back presses, one step at a time
    (each step waits for the byte to change). wrap = the number of positions, to take
    the shorter way round."""
    f0 = g.frame
    while True:
        cur = g.u8(addr)
        if cur == target:
            return g.frame - f0
        if g.frame - f0 > limit:
            raise Stuck(what or 'cursor %#x -> %d' % (addr, target), cur=cur, where=g.where())
        btn = fwd if target > cur else back
        if wrap:
            d = (target - cur) % wrap
            btn = fwd if d <= wrap - d else back
        press_until(g, btn, lambda: g.u8(addr) != cur, limit=max(60, limit - (g.frame - f0)),
                    what=what or 'cursor %#x' % addr)


def confirm_until(g, cond, limit=600, what='confirm'):
    return press_until(g, 'circle', cond, limit, what)


def cancel_until(g, cond, limit=600, what='cancel'):
    return press_until(g, 'cross', cond, limit, what)


def press_then_wait(g, btn, sig, ready, limit=600, what='menu'):
    """Press btn until the game reacts (sig() changes), then wait, without pressing again,
    until ready(). For menus whose next screen takes longer than RETRY frames to come up:
    a retry press there would land on the next screen and pick its first option."""
    s0 = sig()
    press_until(g, btn, lambda: sig() != s0 or ready(), limit, what)
    return wait_until(g, ready, limit, what + ' (ready)')
