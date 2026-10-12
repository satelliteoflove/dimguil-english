"""Input with no idle waits: press, then run only until RAM shows the game took it.

press_until(e, btn, changed) taps btn for HOLD frames and runs frame by frame until
changed() is true, retrying the tap every RETRY frames, up to `limit` frames. Every frame
also runs the tick callbacks (text capture). T1 (rips/harness/t1/) found 2-frame taps are
the shortest the menus take; a 1-frame tap is sometimes dropped.
"""
HOLD = 2
RETRY = 8

PHASE = 0x800796fa         # battle phase; 0x1c = waiting for commands
CMD_MEMBER = 0x80079786    # battle: party slot whose command is being chosen
CMD_LEVEL = 0x80079b15     # battle: command menu depth (2 command, 1 target, 0 done)
MODE = 0x8007967e          # 2 = battle
GAME_STATE = 0x80079a13


class Ticker:
    def __init__(self, e, *ticks):
        self.e = e
        self.ticks = list(ticks)

    def step(self, n=1):
        for _ in range(n):
            self.e.run(1)
            for t in self.ticks:
                t()

    def tap(self, *btns, hold=HOLD):
        self.e.run(hold, btns)
        for t in self.ticks:
            t()

    def press_until(self, btn, changed, limit=600, retry=RETRY):
        """Returns the frames spent, or None if nothing changed within limit."""
        f0 = self.e.frame_no
        while self.e.frame_no - f0 < limit:
            self.tap(btn)
            for _ in range(retry):
                if changed():
                    return self.e.frame_no - f0
                self.step()
        return None

    def wait_until(self, cond, limit=600):
        f0 = self.e.frame_no
        while self.e.frame_no - f0 < limit:
            if cond():
                return self.e.frame_no - f0
            self.step()
        return None


def sig(e, *addrs):
    return tuple(e.read(a, 1)[0] for a in addrs)
