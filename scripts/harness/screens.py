"""Screen capture for the text and screen checks (T5): what the game has drawn, each time
a screen settles, read three ways.

- The glyph sprites, from the sprite pool (the pool at *0x8007961c, layer table at
  0x8008b390, live counts at 0x80079938; docs/engine-notes.md, "Glyph sprite layers"):
  layer, position, size, texture cell (so the glyph code) and colour of every live glyph.
- Glyphs a full layer refused since the last snapshot (0x8001f840 takes a glyph,
  0x8001f9cc drops it), with the line they belonged to.
- The strings the game expanded lately (text.Capture records, with the expanded bytes),
  and a screenshot.

When: every frame the pool is hashed. A snapshot is taken before a press once the pool
has held 3 frames, when a screen settles by itself (held 4 frames, or 10 while text is
typing out, and the picture under the glyphs held too), and of the previous screen when
the pool changes after holding (a box closing on its own, a page turning), except while
text types out. The game draws at 30 fps, so the picture lags the pool by a frame or two:
hence the holds. Each glyph is also marked still or not (same pixels as two frames back);
a snapshot is "stable" when 80% are. Every snapshot goes to screens.jsonl; the screenshot
is kept once per screen key (the lines' text with digits folded), in shots/.

    from harness.screens import Screens
    s = Screens(g, 't5/runs/v0')      # g: Game(capture=True); keeps frames
    ... play ...
    s.close()
"""
import collections, hashlib, json, os, struct

POOL_PTR, LAYERS, COUNTS = 0x8007961c, 0x8008b390, 0x80079938
ACCEPT, REFUSE = 0x8001f840, 0x8001f9cc
FONTFLAG, FONTREAD = 0x80079705, 0x8001f4ec
POOL_SIZE, REC = 720, 36
XOFF = 14            # screen x 0 is image column 14 (crop overscan on, 350 px frame)


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def glyph_code(w, u, v):
    """The glyph code a sprite shows, from its size and texture cell, as 0x8001f4d4 lays
    the fonts out: 8 px cells 21 to a row; 12 px cells 21 to a row from v = 0x50; the
    6 px font puts codes below 0x3e 11 to a row from u = 0xa8."""
    if w == 8:
        return (v // 8) * 21 + u // 8
    if w == 12 and v >= 0x50:
        return ((v - 0x50) // 12) * 21 + u // 12
    if w == 6:
        if u >= 0xa8:
            return (v // 8) * 11 + (u - 0xa8) // 8
        return (v // 8) * 21 + u // 8
    return -1


def read_pool(e):
    """The raw sprite pool, layer table and live counts (one read each)."""
    pool = e.u32(POOL_PTR)
    if not pool or not (0x80000000 <= pool < 0x80200000 - POOL_SIZE * REC):
        return None
    return e.read(pool, POOL_SIZE * REC), e.read(LAYERS, 24), e.read(COUNTS, 8)


def parse_pool(st):
    """Live glyph sprites as dicts: L (layer), x, y (screen), w, h, tp (texture page),
    u, v, clut, rgb, code. A sprite under a newer one at the same place (a fading copy)
    is dropped."""
    if not st:
        return []
    raw, tab, cnt = st
    out = {}
    for L in range(4):
        start, size, head = struct.unpack_from('<3H', tab, 6 * L)
        n = struct.unpack_from('<H', cnt, 2 * L)[0]
        if not size or n > size or start + size > POOL_SIZE:
            continue
        for k in range(n):
            o = (start + (head + k) % size) * REC
            attr = struct.unpack_from('<I', raw, o)[0]
            x, y, w, h, tp = struct.unpack_from('<hhHHH', raw, o + 4)
            u, v = raw[o + 14], raw[o + 15]
            clut = struct.unpack_from('<I', raw, o + 16)[0]
            out[(L, x, y)] = dict(L=L, x=x + 0xa0, y=y + 0x78, w=w, h=h, tp=tp & 0x3f, u=u, v=v,
                                  clut=clut, rgb=raw[o + 20:o + 23].hex(), attr=attr,
                                  code=glyph_code(w, u, v) if (tp & 0x3f) == 0x0f else -1)
    return list(out.values())


def read_sprites(e):
    return parse_pool(read_pool(e))


FIELDS = ('L', 'x', 'y', 'w', 'h', 'tp', 'u', 'v', 'code', 'clut', 'rgb', 'attr')


def pack(sp):
    return [[s[k] for k in FIELDS] for s in sp]


def unpack(rows):
    return [dict(zip(FIELDS, r)) for r in rows]


def lines_of(sp, gap=14):
    """Sprites grouped into lines: by layer and row, in x order, split where the gap is
    over `gap` px."""
    rows = {}
    for s in sp:
        rows.setdefault((s['L'], s['y']), []).append(s)
    out = []
    for (L, y), g in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        g.sort(key=lambda s: s['x'])
        piece = [g[0]]
        for s in g[1:]:
            if s['x'] - piece[-1]['x'] > gap:
                out.append(piece); piece = []
            piece.append(s)
        out.append(piece)
    return out


class Screens:
    def __init__(self, g, out, shots=True):
        from harness.game import OUT
        self.g, self.e = g, g.e
        self.dir = os.path.join(OUT, out)
        self.shot_dir = os.path.join(self.dir, 'shots')
        os.makedirs(self.shot_dir, exist_ok=True)
        self.f = open(os.path.join(self.dir, 'screens.jsonl'), 'a')
        self.shots = shots
        if shots:
            self.e.keep_frames = True
        self.keys = {}               # screen key -> shot name
        self.last_sig = None
        self.last_frame = 0
        self.nmsg = 0
        self.glyph_events = []       # (frame, ra, layer, x, y, code, font, refused)
        self.font = 0
        self.n = 0
        e = self.e
        e.bp(ACCEPT)
        e.bp(REFUSE)
        e.watch(FONTFLAG, FONTFLAG + 1, e.READ)
        self._log = e.log
        e.log = self._siphon
        self._run = e.run
        e.run = self._run_hook
        self.held = False
        self.ring = collections.deque(maxlen=12)     # (frame, image, pool) per frame
        self.hold_c = 0              # frames the sprite pool has held unchanged
        self.last_hash = None
        self.typing_until = 0
        self.pending = False
        self.kept_since_change = False

    # --- hooks ---
    def _siphon(self, reset=True):
        L = self._log(reset)
        keep = []
        prev_accept = None
        for x in sorted(L, key=lambda x: x['seq']):
            pc = x['pc']
            if x['type'] == 'R' and pc == FONTREAD:
                self.font = x['value'] & 0xff
                continue
            if x['type'] == 'R' and (x['addr'] & 0x1fffffff) == (FONTFLAG & 0x1fffffff):
                continue
            if x['type'] == 'X' and pc == ACCEPT:
                r = x['regs']
                code = r[16] & 0xff
                if 0xf7 <= r[19] & 0xff < 0xff:
                    code |= (r[19] & 0xff) << 8
                prev_accept = [self.e.frame_no, r[31], r[6], s16(r[4] & 0xffff), s16(r[5] & 0xffff),
                               code, self.font, False]
                self.glyph_events.append(prev_accept)
                if len(self.glyph_events) > 20000:
                    del self.glyph_events[:10000]
                continue
            if x['type'] == 'X' and pc == REFUSE:
                if prev_accept is not None:
                    prev_accept[7] = True
                continue
            keep.append(x)
        return keep

    def _run_hook(self, frames=1, hold=()):
        try:
            if hold and not self.held and self.ring and self.hold_c >= self.PRESS_HOLD:
                self.snapshot('press', self.ring[-1])
        except Exception as ex:              # the checks never stop a run
            self.f.write(json.dumps(dict(error=repr(ex), frame=self.e.frame_no)) + '\n')
        self.held = bool(hold)
        for _ in range(frames):              # frame by frame: e.press(after=20) is one call
            self._run(1, hold)
            try:
                self._after_frame()
            except Exception as ex:
                self.f.write(json.dumps(dict(error=repr(ex), frame=self.e.frame_no)) + '\n')

    # The picture lags the sprite pool by a frame or two (the game draws at 30 fps), so a
    # snapshot pairs the pool with the picture only once the pool has held a while.
    PRESS_HOLD = 3      # pool unchanged this many frames for a pre-press snapshot
    SETTLE = 4          # ... for a snapshot of a screen that has settled by itself
    TYPING_SETTLE = 10  # ... when text was typing out (a glyph or two every few frames)

    def _after_frame(self):
        e = self.e
        st = read_pool(e)
        cnt = st[2] if st else b''
        h = hashlib.md5(b''.join(st)).digest() if st else b''
        entry = (e.frame_no, e.frame, st)
        prev = self.ring[-1] if self.ring else None
        self.ring.append(entry)
        pcnt = prev[2][2] if prev and prev[2] else b''
        if cnt != pcnt:
            tot = lambda c: sum(struct.unpack('<4H', c)) if len(c) == 8 else 0
            d = tot(cnt) - tot(pcnt)
            if 0 < d <= 2:
                self.typing_until = e.frame_no + self.TYPING_SETTLE
        if h == self.last_hash:
            self.hold_c += 1
        else:
            # the screen before a change, if it had held and wasn't kept (a box closing
            # by itself once typed out, a page turning)
            # (not while text types out: that would be a snapshot per glyph)
            if self.hold_c >= self.PRESS_HOLD and prev and prev[2] and not self.kept_since_change \
                    and e.frame_no > self.typing_until:
                self.snapshot('before-change', prev)
            self.hold_c = 0
            self.kept_since_change = False
            self.pending = True
            self.last_hash = h
        if self.pending and not self.kept_since_change:
            need = self.TYPING_SETTLE if e.frame_no < self.typing_until else self.SETTLE
            if self.hold_c >= need:
                if self._pixels_held(entry) >= 2 or self.hold_c >= 60:
                    self.snapshot('settle', entry)
                    self.pending = False

    def _pixels_held(self, entry):
        sp = parse_pool(entry[2])
        n = 0
        fr = list(self.ring)
        while n + 1 < len(fr) and self._same(fr[-1][1], fr[-2 - n][1], sp):
            n += 1
        return n

    # --- snapshots ---
    def snapshot(self, why, entry):
        g, e = self.g, self.e
        frame_no, img, st = entry
        if g.cap:
            g.cap.poll()                    # pick up glyph and text events up to now
        else:
            e.log()
        sp = parse_pool(st)
        sig = hashlib.md5(json.dumps(sorted((s['L'], s['x'], s['y'], s['code'], s['u'], s['v'])
                                            for s in sp)).encode()).hexdigest()
        new_msgs = g.cap.messages[self.nmsg:] if g.cap else []
        # strings drawn lately: 'fresh' if drawn since the last snapshot, the rest are
        # candidates for what else is on screen (a box typed out over many presses)
        live = [m for m in (g.cap.messages if g.cap else [])[-80:] if m['last'] >= frame_no - 900]
        events = [ev for ev in self.glyph_events if ev[0] >= self.last_frame]
        refused = [ev for ev in events if ev[7]]
        self.kept_since_change = True
        if sig == self.last_sig and not new_msgs and not refused:
            return None
        self.last_sig = sig
        text = []
        for ln in lines_of(sp):
            t = ''.join(chr(0x100 + s['code']) if s['code'] >= 0 else '?' for s in ln)
            text.append('%d:%s' % (ln[0]['L'], t))
        key = hashlib.md5('|'.join(sorted(''.join('#' if '0' <= c <= '9' else c for c in t)
                                          for t in text)).encode()).hexdigest()[:16]
        still = self._still(entry, sp)
        held = sum(still)
        stable = bool(sp) and held >= 0.8 * len(sp)
        shot, was_stable = self.keys.get(key, (None, False))
        new = shot is None or (stable and not was_stable)
        if new and self.shots and img is not None and sp:
            shot = shot or 's%05d_%d' % (len(self.keys), frame_no)
            self.keys[key] = (shot, stable)
            self._write_shot(os.path.join(self.shot_dir, shot + '.png'), img)
        rec = dict(n=self.n, frame=frame_no, why=why, where=g.where(), sig=sig, key=key,
                   shot=shot, new=new, stable=stable, held=[self.hold_c, held],
                   sprites=pack(sp), still=''.join('1' if k else '0' for k in still),
                   typing=frame_no < self.typing_until,
                   msgs=[dict(self._msg(m), fresh=m['last'] >= self.last_frame - 2) for m in live],
                   refused=[ev[:7] for ev in refused],
                   drawn_lines=_drawn_lines(events) if refused else None)
        self.f.write(json.dumps(rec, default=str) + '\n')
        self.n += 1
        self.nmsg = len(g.cap.messages) if g.cap else 0
        self.last_frame = frame_no
        return rec

    def _still(self, entry, sp, back=2):
        """Per glyph: are the pixels under it the same as `back` frames before?"""
        fr = list(self.ring)
        i = next((k for k, x in enumerate(fr) if x is entry), None)
        if i is None or i < back:
            return [False] * len(sp)
        a, b = fr[i][1], fr[i - back][1]
        return [self._same(a, b, [s]) for s in sp]

    def _same(self, a, b, sp):
        if a is None or b is None or a[1:] != b[1:]:
            return False
        data_a, w, h, pitch = a
        data_b = b[0]
        bpp = 4 if self.e.pixfmt == 1 else 2
        for s in sp:
            x0 = max(0, s['x'] + XOFF) * bpp
            x1 = min(w, s['x'] + XOFF + s['w']) * bpp
            for yy in range(max(0, s['y']), min(h, s['y'] + s['h'])):
                o = yy * pitch
                if data_a[o + x0:o + x1] != data_b[o + x0:o + x1]:
                    return False
        return True

    @staticmethod
    def _msg(m):
        return {k: m.get(k) for k in ('frame', 'last', 'idx', 'base', 'wrap', 'ra', 'file',
                                       'inferred', 'text', 'exp')}

    def _write_shot(self, p, frame):
        from PIL import Image
        data, w, h, pitch = frame
        if self.e.pixfmt == 1:
            im = Image.frombuffer('RGB', (w, h), data, 'raw', 'BGRX', pitch, 1)
        else:
            im = Image.frombuffer('RGB', (w, h), data, 'raw', 'BGR;16', pitch, 1)
        im.save(p)

    def close(self):
        try:
            if self.ring:
                self.snapshot('end', self.ring[-1])
        except Exception:
            pass
        self.f.close()


def _drawn_lines(events):
    """Glyph calls grouped into lines (call site, layer, row), with refused glyphs marked:
    for the cut check."""
    runs = {}
    for fr, ra, L, x, y, code, font, ref in events:
        runs.setdefault((ra, L, y), []).append((x, code, ref))
    out = []
    for (ra, L, y), gl in runs.items():
        if any(r for _, _, r in gl):
            out.append(dict(ra='%08x' % ra, L=L, y=y + 0x78,
                            glyphs=[[x + 0xa0, c, r] for x, c, r in gl[-200:]]))
    return out
