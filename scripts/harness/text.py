"""Game text for the harness: decode the patched build's bytes, and capture every message
the game expands, from RAM, as it happens.

Capture: a breakpoint on text_expand (MAIN 0x8001dfc0; a0 = string index, a1 = the
loaded text file's base, a2 = 1 for the battle box's wrapping) plus a write watch on
text_buffer (0x8008b400, 576 bytes). In log order, each breakpoint hit starts a message
and the buffer writes after it are its expanded bytes, names and numbers included. The
hooks are patched into the core's interpreter, so this needs the dynarec off.

Menus and the battle's command labels call text_expand on every frame they're drawn.
A message counts once while it's being redrawn: a (base, index, caller, text) repeat
within GAP frames of its last sighting extends the earlier record instead of adding one.

The text file at a base can change as overlays load. Each record's file is the one whose
string at that index matches the unexpanded text; when none matches exactly (the
disc's own text, numbers), the base's last confirmed file is used and marked inferred.
"""
import json, os, re, struct

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
TEXT_EXPAND = 0x8001dfc0
TEXT_BUFFER = 0x8008b400
TEXT_BUFFER_LEN = 0x240

# code -> text: the English font and digraphs, then the Japanese table for the rest
DEC = {}
for line in open(os.path.join(ROOT, 'tables/dimguil_dec.tbl'), encoding='utf-8'):
    k, sep, v = line.rstrip('\n').partition('=')
    if sep:
        DEC[int(k, 16)] = v
for line in open(os.path.join(ROOT, 'tables/dimguil_enc.tbl'), encoding='utf-8'):
    k, sep, v = line.rstrip('\n').partition('=')
    if sep and len(k) <= 2 and int(k, 16) < 0xd8:
        DEC[int(k, 16)] = v
for line in open(os.path.join(ROOT, 'tables/compression.tbl'), encoding='utf-8'):
    line = line.rstrip('\n')
    if len(line) >= 4 and line[2] == '=':
        DEC[int(line[3:], 16)] = line[:2]


def decode(b):
    """Bytes to text. {ff21} becomes a newline; other control codes stay as {ffxx}."""
    out, i = [], 0
    while i < len(b):
        c = b[i]
        if c >= 0xf7 and i + 1 < len(b):
            w = c << 8 | b[i + 1]
            if w == 0xff40:
                break
            out.append('\n' if w == 0xff21 else ('{%04x}' % w if c == 0xff else DEC.get(w, '〓')))
            i += 2
        else:
            out.append(DEC.get(c, '<%02x>' % c))
            i += 1
    return ''.join(out)


def raw_string(e, base, idx, maxlen=1200):
    """The unexpanded bytes of string idx in the text file loaded at base."""
    off = struct.unpack('<i', e.read(base + idx * 4, 4))[0]
    b = e.read(base + off, maxlen)
    j = 0
    while j < len(b) - 1:
        if b[j] >= 0xf7:
            if b[j] == 0xff and b[j + 1] == 0x40:
                break
            j += 2
        else:
            j += 1
    return b[:j]


def _norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def _fuzzy(s):
    """A looser key for text whose JSON and disc forms differ in markup: the JSON writes a
    page break as \r and the ancient letters as {ancient_x}, the disc as {ff20} and glyph
    codes. Keep letters and digits outside braces, up to 60 of them."""
    s = re.sub(r'\{[^}]*\}', '', s)
    return re.sub(r'[^A-Za-z0-9]', '', s)[:60]


class StringIndex:
    """Text -> [(file, index)] over translations/*.json (the English, or the Japanese
    where the disc's own text is kept)."""

    def __init__(self):
        self.by_text = {}
        self.by_fuzzy = {}
        tdir = os.path.join(ROOT, 'translations')
        for fn in sorted(os.listdir(tdir)):
            if not fn.endswith('.json'):
                continue
            raw = open(os.path.join(tdir, fn), encoding='utf-8').read()
            d = json.loads(re.sub(r'(?m)(?<=,)\s*//[^\n]*$', '', raw))
            n = 0
            for s in d.get('sections', []):
                for st in s.get('strings', []):
                    t = st.get('translation') or st.get('source') or ''
                    for part in t.split('{ff40}'):
                        self.by_text.setdefault(_norm(part), []).append((fn[:-5], n))
                        k = _fuzzy(part)
                        if len(k) >= 12:
                            self.by_fuzzy.setdefault(k, []).append((fn[:-5], n))
                    n += 1

    def find(self, text):
        hit = self.by_text.get(_norm(text), [])
        if not hit:
            k = _fuzzy(text)
            if len(k) >= 12:
                hit = self.by_fuzzy.get(k, [])
        return hit


class Capture:
    """Install on an Emu; call poll() after running frames. New messages land in .messages
    as dicts: frame, last, idx, base, wrap, ra, src (unexpanded text), text (expanded),
    where (list of (file, index) matches)."""

    GAP = 12   # a repeat within this many frames is the same message being redrawn

    def __init__(self, e, index=None):
        self.e = e
        self.index = index or StringIndex()
        self.messages = []
        self._recent = {}
        self._last_poll = -1
        self.base_file = {}
        e.bp(TEXT_EXPAND)
        e.watch(TEXT_BUFFER, TEXT_BUFFER + TEXT_BUFFER_LEN, e.WRITE)

    def poll(self):
        e = self.e
        log = sorted(e.log(), key=lambda x: x['seq'])
        cur = None
        recs = []
        for x in log:
            if x['type'] == 'X' and x['pc'] == TEXT_EXPAND:
                r = x['regs']
                cur = dict(idx=r[4] & 0xffff, base=r[5], wrap=r[6], ra=x['ra'], buf={})
                recs.append(cur)
            elif x['type'] == 'W' and cur is not None:
                off = (x['addr'] & 0x1fffffff) - (TEXT_BUFFER & 0x1fffffff)
                for k in range(x['size']):
                    cur['buf'][off + k] = (x['value'] >> (8 * k)) & 0xff
        f = e.frame_no
        for r in recs:
            n = 0
            while n in r['buf']:
                n += 1
            exp = bytes(r['buf'][k] for k in range(n))
            text = decode(exp)
            key = (r['idx'], r['base'], r['ra'], text)
            prev = self._recent.get(key)
            if prev is not None and f - prev['last'] <= self.GAP:
                prev['last'] = f
                continue
            try:
                src = decode(raw_string(e, r['base'], r['idx']))
            except Exception:
                src = None
            where = self.index.find(src) if src else []
            files = sorted({fn for fn, n in where if n == r['idx']})
            if len(files) == 1:
                self.base_file[r['base']] = files[0]
                fn, inferred = files[0], False
            else:
                fn, inferred = self.base_file.get(r['base']), True
            m = dict(frame=f, last=f, idx=r['idx'], base=r['base'], wrap=r['wrap'], ra=r['ra'],
                     file=fn, inferred=inferred, src=src, text=text)
            self._recent[key] = m
            self.messages.append(m)
        self._last_poll = f
        return len(recs)
