"""The harness's view of the game: one emulator on the harness disc copy, RAM reads only.

    from harness.game import Game
    g = Game()                      # boots nothing; load a state or call g.boot()
    g.load('t2/states/town')        # rips/harness/<path>.state
    g.where()                       # mode, state, overlay, area, x, y, facing

Every frame the game runs goes through g.step()/g.tap() (inputs.Ticker), which polls the
text capture (text.Capture) when it's on. One Game per process: the core's debug hooks are
global, so a second emulator in the same process would share the breakpoints.
"""
import os, struct, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from harness.emu import Emu
from harness.inputs import Ticker
from harness import text as T

DISC = os.path.join(ROOT, 'rips/harness/disc/dimguil-en.cue')
OUT = os.path.join(ROOT, 'rips/harness')

# RAM (docs/re/*.md, scripts/re/symbols/*.csv)
GAME_MODE = 0x8007967e      # queued overlay switch, cleared by main
GAME_STATE = 0x80079a13     # which overlay routine runs
RESIDENT = 0x800798b3       # 1 JOUKA, 2 MAZE, 3 BATTLE, 4 HAZURE, 5 MCARD
OVL_NAME = {1: 'JOUKA', 2: 'MAZE', 3: 'BATTLE', 4: 'HAZURE', 5: 'MCARD'}
TOWN_STATE = 0x80079b18     # 10 tavern, 15 inn, 20 Boltac, 25 temple, 30 training, 40 edge
CUR_AREA = 0x80079668
POS_X, POS_Y = 0x80079906, 0x80079916
FACING = 0x80079b34
BATTLE_PHASE = 0x800796fa
CAMP_STATE = 0x80079669
TALK_STATE = 0x8007981c
ROSTER = 0x8007d708
ROSTER_LEN = 0xd0
PARTIES = 0x8008f8c8
CUR_PARTY = 0x8007e810      # the party in the maze (0x36 bytes, same layout)
NAME_DEC = {}
for l in open(os.path.join(ROOT, 'tables/dimguil_dec.tbl'), encoding='utf-8'):
    k, _, v = l.rstrip('\n').partition('=')
    if k and len(k) <= 2:
        NAME_DEC[int(k, 16)] = v


class Stuck(Exception):
    """A macro made no progress within its frame budget. .info has the details."""
    def __init__(self, what, **info):
        super().__init__(what)
        self.what = what
        self.info = info


class Game:
    def __init__(self, disc=DISC, capture=True, shots_dir=None):
        self.e = Emu(disc)
        # with shots on, every frame is kept (about 1% of speed, T1) so the frame before a
        # press is at hand
        self.e.keep_frames = bool(shots_dir)
        self.cap = None
        self.shots_dir = shots_dir
        self.seen_shot = set()
        ticks = []
        if capture:
            self.cap = T.Capture(self.e)
            ticks.append(self._poll)
        self.t = Ticker(self.e, *ticks)
        self._nmsg = 0
        self._due = []            # (frame, key, message) shots still to take

    # --- frames ---
    SETTLE = 6                # a press this soon after a string's first print is too early

    def _poll(self):
        """Every frame: poll the capture and note strings seen for the first time (by
        file and index) as wanting a shot."""
        c = self.cap
        c.poll()
        if not self.shots_dir or len(c.messages) <= self._nmsg:
            return
        for m in c.messages[self._nmsg:]:
            key = (m['file'], m['idx'])
            if m['file'] and key not in self.seen_shot:
                self.seen_shot.add(key)
                p = os.path.join(self.shots_dir, '%s_%d.png' % (m['file'].split('.')[0], m['idx']))
                if not os.path.exists(p):
                    self._due.append([m['frame'], p, None])
        self._nmsg = len(c.messages)

    def _before_press(self):
        """Shot timing (2026-10-12, T3). The game shows a message until a press moves it
        on, so the screen just before a press shows whatever is waiting. A string still
        wanting a shot takes the frame before every press while no newer string has
        been printed; its last such frame is its shot. Strings printed together (a
        battle box's "Hits 1 times!" and "takes 4 damage.") share one. A string printed
        early ("Oops!...", 90 frames before it shows) first gets the previous box, then
        the right one at the press that dismisses it."""
        if not self._due:
            return
        newest = self.cap.messages[-1]['frame'] if self.cap.messages else 0
        keep = []
        for d in self._due:
            first, p, img = d
            if first < newest:                      # superseded: final
                if img is not None:
                    self._write_shot(p, img)
                continue
            if self.frame - first >= self.SETTLE and self.e.frame:
                d[2] = self.e.frame
            keep.append(d)
        self._due = keep

    def _write_shot(self, p, frame):
        from PIL import Image
        data, w, h, pitch = frame
        if self.e.pixfmt == 1:
            im = Image.frombuffer('RGB', (w, h), data, 'raw', 'BGRX', pitch, 1)
        else:
            im = Image.frombuffer('RGB', (w, h), data, 'raw', 'BGR;16', pitch, 1)
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            im.save(p)
        except Exception:
            pass

    def flush_shots(self):
        """Write the shots still pending (end of a run)."""
        for first, p, img in self._due:
            if img is not None:
                self._write_shot(p, img)
        self._due = []

    budget_end = None         # a frame past which step/tap raise Stuck('frame budget')

    def _check_budget(self):
        if self.budget_end is not None and self.e.frame_no > self.budget_end:
            self.budget_end = None
            raise Stuck('frame budget', where=self.where())

    def step(self, n=1):
        self._check_budget()
        self.t.step(n)

    def tap(self, *btns, hold=None):
        self._check_budget()
        if self.shots_dir and self.cap:
            self._before_press()
        self.t.tap(*btns, **({} if hold is None else {'hold': hold}))

    @property
    def frame(self):
        return self.e.frame_no

    # --- states ---
    def path(self, name, ext='.state'):
        return os.path.join(OUT, name + ext)

    def save(self, name):
        p = self.path(name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        self.e.save(p)
        return p

    def load(self, name):
        self.e.load(self.path(name) if not name.endswith('.state') else name)
        self.e.run(1)
        if self.cap:
            self.e.log()          # drop hook hits from the load
            self.cap._recent.clear()

    def shot(self, name, scale=1):
        """Draw a frame with frame copying on and save it (rips/harness/<name>.png)."""
        keep = self.e.keep_frames
        self.e.keep_frames = True
        self.step(1)
        p = self.path(name, '.png')
        self.e.shot(p, scale=scale)
        self.e.keep_frames = keep
        return p

    # --- RAM ---
    def u8(self, a): return self.e.read(a, 1)[0]
    def s8(self, a): return struct.unpack('<b', self.e.read(a, 1))[0]
    def u16(self, a): return struct.unpack('<H', self.e.read(a, 2))[0]
    def s16(self, a): return struct.unpack('<h', self.e.read(a, 2))[0]
    def u32(self, a): return self.e.u32(a)

    def overlay(self):
        return OVL_NAME.get(self.u8(RESIDENT), '?')

    def where(self):
        return dict(ovl=self.overlay(), state=self.u8(GAME_STATE), mode=self.u8(GAME_MODE),
                    town=self.u8(TOWN_STATE), area=self.u8(CUR_AREA), x=self.u8(POS_X),
                    y=self.u8(POS_Y), face=self.u8(FACING), phase=self.u8(BATTLE_PHASE))

    def pos(self):
        return self.u8(POS_X), self.u8(POS_Y)

    def name(self, i):
        out = ''
        for c in self.e.read(ROSTER + i * ROSTER_LEN, 10):
            if c == 0xff:
                break
            out += NAME_DEC.get(c, '?')
        return out

    def char(self, i):
        d = self.e.read(ROSTER + i * ROSTER_LEN, ROSTER_LEN)
        return dict(i=i, name=self.name(i), status=struct.unpack_from('<H', d, 0x0e)[0],
                    race=d[0x0a] & 0x3f, align=d[0x0a] >> 6, cls=d[0x0b] & 0x7f,
                    female=bool(d[0x0b] & 0x80), age=d[0x10], stats=list(d[0x13:0x19]),
                    level=struct.unpack_from('<H', d, 0x44)[0],
                    exp=struct.unpack_from('<I', d, 0x40)[0],
                    sp=[list(d[0x5c + 7 * k:0x63 + 7 * k]) for k in range(4)],
                    gold=struct.unpack_from('<I', d, 0x1c)[0],
                    items=[x for x in struct.unpack_from('<10H', d, 0x20) if x != 0xffff],
                    hp=struct.unpack_from('<h', d, 0x46)[0], max_hp=struct.unpack_from('<h', d, 0x4a)[0],
                    area=d[0x7a], x=d[0x7b], y=d[0x7c], raw=d)

    def roster_count(self):
        n = 0
        while n < 20 and self.e.read(ROSTER + n * ROSTER_LEN, 1)[0] not in (0, 0xff):
            n += 1
        return n

    def party_slots(self):
        """The maze party's six positions (front row 0-2, back row 3-5): roster index or
        None. Members can sit in any slot; a death can move the rows round."""
        d = self.e.read(CUR_PARTY, 8)
        return [None if b == 0xff else b for b in d[2:8]]

    def party(self):
        """The maze party's roster indices, in slot order."""
        return [i for i in self.party_slots() if i is not None]

    def parties(self):
        out = []
        for p in range(20):
            d = self.e.read(PARTIES + p * 0x36, 0x36)
            pid = struct.unpack('<b', d[0:1])[0]
            if pid != -1 and d[1]:
                out.append(dict(slot=p, id=pid, count=d[1],
                                members=[struct.unpack('<b', d[2 + k:3 + k])[0] for k in range(d[1])]))
        return out

    # --- text ---
    def messages_since(self, n):
        return self.cap.messages[n:] if self.cap else []

    def dump_messages(self, path, since=0):
        if not self.cap:
            return
        with open(path, 'a', encoding='utf-8') as f:
            for m in self.cap.messages[since:]:
                f.write(json.dumps({k: v for k, v in m.items() if k != 'shot_pending'},
                                   ensure_ascii=False) + '\n')
