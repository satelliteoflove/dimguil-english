#!/usr/bin/env python3
"""The T5 text and screen checks, over what harness.screens captured.

    python3 scripts/harness/t5check.py DIR [DIR ...] [--out FILE]
    python3 scripts/harness/t5check.py --learn DIR [DIR ...]     (the centered rows)

DIR is a capture (rips/harness/<DIR>/screens.jsonl and shots/). Writes one finding per
line to --out (default rips/harness/t5/findings.jsonl) and prints counts.

Checks, per settled screen (see harness.screens for what "settled" means):
  cut        a full glyph layer refused part of a line (the game just stops drawing)
  missing    each line on screen against the lines of the strings drawn lately (as glyph
             codes): cut short, a glyph or two wrong, or going on differently partway
  page       a page's later line on screen without an earlier one (more lines than the
             box shows); not in battle, whose box scrolls
  offscreen  a glyph outside the 320 x 240 picture
  overlap    two glyphs' ink on the same pixels
  japanese   a glyph from the kana/kanji part of the fonts, a two-byte code, or the
             decoder's 〓 fallback in the expanded text
  garbage    a line with a run of 8 or more of the same glyph (not punctuation)
  overflow   an expanded string that fills the 576-byte buffer without its end
  lint       the expanded text: doubled or clashing punctuation (".!!", ",."), a space
             before punctuation, a wrapped battle line starting with a space, a double
             space inside a line
  center     in a row that centers its text (learned from captures, t5/centers.json):
             a line starting or ending with a space, or off the row's center by 1.5 to
             24 px (farther is taken for a line that isn't centered)
  render     the screenshot against the font: each glyph's ink must stand out from its
             own cell, and nothing else may be drawn inside its ink box (a box border,
             an icon, another line)

All but render work from RAM: the sprite pool, the glyph calls and the expanded text.
"""
import argparse, collections, json, os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from harness.screens import unpack, lines_of, XOFF
from harness.text import DEC, decode

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUTR = os.path.join(ROOT, 'rips/harness')
FONT = np.array(Image.open(os.path.join(ROOT, 'graphics/SYSCG_000001_04b_01c.png')))
SPACE = 0xba


def is_space(s):
    """A space sprite: 0xba, or 0x2c in the 6 px font (item names in lists)."""
    return s['code'] == SPACE or (s['w'] == 6 and s['code'] == 0x2c)
SCREEN_W, SCREEN_H = 320, 240
STATS = collections.Counter()      # coverage: what the checks looked at
SEEN = collections.defaultdict(set)

# Findings that are deliberate: (check, what starts with, string or None, reason)
ALLOW = [
    ('lint', 'double space inside a line', 'SISETU.OBJ 442',
     'the spaces leave room for the triangle icon drawn over them ("Press    to return")'),
]


# --- expected text ---

def tokens(exp_hex):
    """Expanded bytes -> list of ('g', code) glyphs and ('c', ffxx) controls."""
    b = bytes.fromhex(exp_hex or '')
    out, i = [], 0
    while i < len(b):
        c = b[i]
        if c >= 0xf7 and i + 1 < len(b):
            w = c << 8 | b[i + 1]
            out.append(('c', w) if c == 0xff else ('g', w))
            i += 2
            if w == 0xff30:                     # {ff30}xx: text color, xx isn't drawn
                i += 1
            elif w == 0xff35 and i < len(b):    # {ff35}xx: xx drawn as an ancient letter
                out.append(('g', 0x10000 | b[i]))
                i += 1
        else:
            out.append(('g', c))
            i += 1
    return out


def pages(exp_hex):
    """Pages (split at {ff20}, and at a wait {ff26} that ends a line) of lines (split at
    {ff21}) of glyph codes."""
    pgs, lines, cur = [], [], []
    wait = False
    for kind, v in tokens(exp_hex):
        if kind == 'c':
            if v == 0xff21 and wait:
                lines.append(cur); pgs.append(lines); lines, cur = [], []
            elif v == 0xff21:
                lines.append(cur); cur = []
            elif v == 0xff20:
                lines.append(cur); pgs.append(lines); lines, cur = [], []
            elif v == 0xff40:
                break
            wait = v == 0xff26
        else:
            cur.append(v)
            wait = False
    lines.append(cur)
    pgs.append(lines)
    return [[ln for ln in pg] for pg in pgs]


def letters(codes):
    """Glyph codes as letters, spaces dropped: digraphs split, so "st" + "t " and "s" +
    "t" + "t" compare equal (the printers and the encoder don't always pick the same
    digraphs, and the 6 px font has its own space). Codes with no letter stay codes."""
    out = []
    for c in codes:
        t = DEC.get(c) if c is not None else None
        if c is None or not t or t.startswith('{'):
            out.append(c)
        else:
            out.extend(ch for ch in t if ch != ' ')
    return out


def word_starts(seq):
    """Letter indexes (as letters() counts) where a word starts, from codes with spaces."""
    starts, n, new = {0}, 0, True
    for c in seq:
        if c == SPACE:
            new = True
            continue
        t = DEC.get(c) if c is not None and c <= 0xff else None
        k = len(t.replace(' ', '')) if t and not t.startswith('{') else 1
        if new:
            starts.add(n)
        n += k
        new = bool(t) and t.endswith(' ')
    starts.add(n)
    return starts


def ink_codes(seq):
    """Glyph codes without spaces, two-byte codes as None (they're on another page)."""
    return [None if c > 0xff else c for c in seq if c != SPACE]


# --- the screen ---

def layer_streams(sp):
    """Per layer: the glyph codes in reading order without spaces, and the sprite each
    came from."""
    out = collections.defaultdict(lambda: ([], []))
    for ln in lines_of(sp):
        for s in ln:
            if is_space(s):
                continue
            codes, refs = out[s['L']]
            codes.append(s['code'] if s['tp'] == 0x0f else None)
            refs.append(s)
    return out


def find(needle, hay):
    """Index of needle in hay (None matches None), or -1."""
    n = len(needle)
    for i in range(len(hay) - n + 1):
        if hay[i:i + n] == needle:
            return i
    return -1


def best_overlap(needle, hay):
    """Longest run of needle (from its start) found in hay: how much of a line is drawn."""
    lo, hi = 0, len(needle)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if find(needle[:mid], hay) >= 0:
            lo = mid
        else:
            hi = mid - 1
    return lo


def ink(s):
    if s['tp'] != 0x0f:
        return None
    cell = FONT[s['v']:s['v'] + s['h'], s['u']:s['u'] + s['w']]
    return cell != 0


# --- checks ---

PUNCT_BAD = [(re.compile(r'[.!?,][.,]|[,][!?]|\.!|\?\.|!\.'), 'clashing punctuation'),
             (re.compile(r'(?<=\S) [.,!?;:](?!\.)'), 'space before punctuation'),
             (re.compile(r'(?<=[A-Za-z,.!?]) {2,}(?=[A-Za-z])'), 'double space inside a line')]


def lint(m):
    out = []
    text = m.get('text') or ''
    body = re.sub(r'\{[0-9a-f]{4}\}', '', text)
    for line in body.split('\n'):
        for rx, what in PUNCT_BAD:
            for mm in rx.finditer(line):
                frag = line[max(0, mm.start() - 12):mm.end() + 12]
                if what == 'clashing punctuation' and mm.group(0) == '.,' and \
                        re.search(r'[A-Z]$', line[:mm.start()]):
                    continue                # an abbreviation, then a comma ("I.Q.,")
                if what == 'clashing punctuation' and re.search(r'\.\.\.|…', frag[max(0, mm.start() - max(0, mm.start() - 12) - 2):]):
                    if '..' in mm.group(0) and '...' in line:
                        continue
                out.append(dict(check='lint', what=what, detail=frag, string=_sid(m)))
    if m.get('wrap') == 1:
        if m.get('exp'):
            toks = tokens(m['exp'])
            lead = any(k == 'c' and v == 0xff21 and toks[i + 1] == ('g', SPACE)
                       for i, (k, v) in enumerate(toks[:-1]))
        else:                                   # older captures: the decoded text only
            lead = '\n ' in text
        if lead:
            out.append(dict(check='lint', what='wrapped line starts with a space',
                            detail=text.replace('\n', ' / '), string=_sid(m)))
    exp = bytes.fromhex(m.get('exp') or '')
    if len(exp) >= 0x240 and b'\xff\x40' not in exp:
        out.append(dict(check='overflow', what='the string fills the 576-byte expand buffer: '
                        'what follows is overwritten by live data', detail=text[-80:].replace('\n', ' / '),
                        string=_sid(m)))
    if '〓' in text:
        out.append(dict(check='japanese', what='decoder fallback 〓 in the text', detail=text,
                        string=_sid(m)))
    return out


def check_record(r, img=None):
    sp = unpack(r['sprites'])
    still = r.get('still') or ''
    out = []
    # cut: a glyph a full layer refused, that isn't on screen anyway (static text
    # redrawn every frame into a layer it already filled is refused harmlessly)
    have = {(s['L'], s['x'], s['y'], s['code']) for s in sp}
    for dl in r.get('drawn_lines') or []:
        gl = dl['glyphs']
        # most printers pass centered coordinates (recorded + 160, + 120), the event box
        # passes screen ones: take whichever puts this line's drawn glyphs on their sprites
        dx, dy = max(((0, 0), (-0xa0, -0x78)), key=lambda o: sum(
            (dl['L'], g[0] + o[0], dl['y'] + o[1], g[1]) in have for g in gl if not g[2]))
        y = dl['y'] + dy
        lost = [g for g in gl if g[2] and (dl['L'], g[0] + dx, y, g[1]) not in have
                and -12 < g[0] + dx < SCREEN_W and 0 <= y < SCREEN_H]
        took = [g for g in gl if not g[2]]
        on = [g for g in took if (dl['L'], g[0] + dx, y, g[1]) in have]
        # a line mostly not on screen belongs to a screen being left or not yet shown
        if lost and on and 2 * len(on) >= len(took):
            txt = ''.join(DEC.get(c, '?') for x, c, rf in sorted({(g[0], g[1], g[2]) for g in gl}))
            out.append(dict(check='cut', what='layer %d full: %d glyph(s) refused and not on screen' % (dl['L'], len(lost)),
                            detail=txt[-80:], box=_bbox([s for s in sp if s['L'] == dl['L'] and s['y'] == y])))
    # off screen
    offs = [s for s in sp if not is_space(s) and (s['x'] < 0 or s['y'] < 0 or
                                                     s['x'] + s['w'] > SCREEN_W + 6 or s['y'] + s['h'] > SCREEN_H)]
    if offs:
        out.append(dict(check='offscreen', what='%d glyph(s) outside the picture' % len(offs),
                        detail=_txt(offs), box=_bbox(offs)))
    # japanese glyphs
    jp = [s for s in sp if (s['tp'] == 0x0f and ((s['w'] == 8 and 64 <= s['code'] < 168) or
                                                  (s['w'] == 12 and s['code'] >= 237)))
          or s['tp'] == 0x1f]
    if jp:
        out.append(dict(check='japanese', what='%d glyph(s) from the kana/kanji cells' % len(jp),
                        detail=_txt(jp), box=_bbox(jp)))
    # garbage: a long run of one glyph (what overwrote the text buffer prints as zeros)
    for ln in lines_of(sp):
        run, prev = 0, None
        for g in ln:
            run = run + 1 if g['code'] == prev else 1
            prev = g['code']
            if run == 8 and not is_space(g) and DEC.get(g['code'], '?') not in '.-*=~':
                out.append(dict(check='garbage', what='a run of 8 or more of the same glyph',
                                detail=_dec([x['code'] for x in ln]), box=_bbox(ln)))
                break
    # ink overlap
    canvas = np.full((SCREEN_H + 40, SCREEN_W + 60), -1, dtype=np.int32)
    hits = collections.Counter()
    for k, s in enumerate(sp):
        m = ink(s)
        if m is None or not m.any():
            continue
        ys, xs = np.nonzero(m)
        ys = ys + s['y'] + 20
        xs = xs + s['x'] + 30
        ok = (ys >= 0) & (ys < canvas.shape[0]) & (xs >= 0) & (xs < canvas.shape[1])
        ys, xs = ys[ok], xs[ok]
        prev = canvas[ys, xs]
        for p in prev[prev >= 0]:
            if sp[int(p)]['L'] == s['L']:      # other layers are other windows, often covered
                hits[(int(p), k)] += 1
        canvas[ys, xs] = k
    pairs = [(a, b) for (a, b), n in hits.items() if n >= 2]
    if pairs:
        involved = sorted({i for p in pairs for i in p})
        gl = [sp[i] for i in involved]
        out.append(dict(check='overlap', what='%d pair(s) of glyphs share ink' % len(pairs),
                        detail=_txt(gl), box=_bbox(gl)))
    # lines: each line on screen against the strings drawn lately
    if not r.get('typing'):
        for m in r.get('msgs') or []:
            if m.get('fresh'):
                out += lint(m)
        files = {}
        out += line_check(sp, r.get('msgs') or [], r['where']['ovl'], files)
        out += center_check(sp, r['where']['ovl'], files)
    # render against the screenshot
    if img is not None and r.get('stable') and not r.get('typing'):
        out += render_check(sp, still, img)
    return out


# --- centering ---

CENTERS = os.path.join(OUTR, 't5/centers.json')
_centers = None


def ink_span(gl):
    """Leftmost and rightmost ink column of a line's glyphs (spaces have none)."""
    xs = []
    for g in gl:
        m = ink(g)
        if m is not None and m.any():
            c = np.nonzero(m.any(0))[0]
            xs += [g['x'] + int(c.min()), g['x'] + int(c.max()) + 1]
    return (min(xs), max(xs)) if xs else None


def row_key(ovl, ln, file):
    """A row: overlay, layer, y and the string file its line was found in (so a list
    of names in a row the help bar also uses isn't taken for centered help text)."""
    return '%s/%d/%d/%s' % (ovl, ln[0]['L'], ln[0]['y'], (file or 'unnamed').split('.')[0])


def learn_centers(dirs, out_path=CENTERS):
    """Which rows center their text, from captures: a row (overlay, layer, y, string file)
    is centered when at least 8 different texts of different widths drawn there share an
    ink center (70% of its texts within 1 px of the median). Only lines found in a string
    count. Writes {row: center}."""
    rows = collections.defaultdict(dict)
    for d in dirs:
        for line in open(os.path.join(OUTR, d, 'screens.jsonl')):
            r = json.loads(line)
            if 'sprites' not in r or r.get('typing'):
                continue
            sp_ = unpack(r['sprites'])
            files = {}
            line_check(sp_, r.get('msgs') or [], r['where']['ovl'], files)
            for ln in lines_of(sp_):
                if sum(1 for g in ln if not is_space(g)) < 3 or id(ln[0]) not in files:
                    continue
                sp = ink_span(ln)
                if sp:
                    rows[row_key(r['where']['ovl'], ln, files[id(ln[0])])][_dec([g['code'] for g in ln])] = sp
    out = {}
    for k, texts in rows.items():
        if len(texts) < 8:
            continue
        cs = np.array([(a + b) / 2 for a, b in texts.values()])
        ws = np.array([b - a for a, b in texts.values()])
        med = float(np.median(cs))
        near = np.abs(cs - med) <= 1
        # the texts that agree must differ in width, or it's a left- or right-aligned
        # column of same-width fields
        if near.mean() >= 0.7 and near.sum() >= 8 and len(set(ws[near])) >= 4 and \
                ws[near].max() - ws[near].min() >= 24:
            out[k] = round(med * 2) / 2
    json.dump(dict(sorted(out.items())), open(out_path, 'w'), indent=1)
    return out


def center_check(sp, ovl, files):
    """In a row that centers its text: a line starting or ending with a space (the game
    centers spaces too, so it's pulled sideways), or whose ink is off the row's center."""
    global _centers
    if _centers is None:
        _centers = json.load(open(CENTERS)) if os.path.exists(CENTERS) else {}
    out = []
    lines = lines_of(sp)
    per_row = collections.Counter((ln[0]['L'], ln[0]['y']) for ln in lines)
    for ln in lines:
        if id(ln[0]) not in files or per_row[(ln[0]['L'], ln[0]['y'])] > 1:
            continue
        c = _centers.get(row_key(ovl, ln, files[id(ln[0])]))
        if c is None and files[id(ln[0])] is None:
            # a string the capture couldn't place (a test string, say): the row's center
            # if only one file's text is known there
            pre = row_key(ovl, ln, None).rsplit('/', 1)[0] + '/'
            known = [v for k, v in _centers.items() if k.startswith(pre)]
            c = known[0] if len(known) == 1 else None
        if c is None or sum(1 for g in ln if not is_space(g)) < 3:
            continue
        span = ink_span(ln)
        if not span:
            continue
        STATS['centered lines checked'] += 1
        off = (span[0] + span[1]) / 2 - c
        ends = [w for w, g in (('starts', ln[0]), ('ends', ln[-1])) if is_space(g)]
        if abs(off) > 24:
            continue                    # a left-aligned line or another box in the row
        if ends or abs(off) >= 1.5:
            what = 'line %s with a space' % ' and '.join(ends) if ends else 'line off center'
            out.append(dict(check='center', what='%s: %+.1f px from the row\'s center %.1f' % (what, off, c),
                            detail=_dec([g['code'] for g in ln]), box=_bbox(ln)))
    return out


def candidates(msgs):
    """Every line of every string drawn lately, as glyph codes without spaces (reversed
    for the right-aligned sets, {ff23}), with the string it came from."""
    out = []
    for m in msgs:
        if not m.get('exp'):
            continue
        rev = 'ff23' in m['exp'][:4]
        for pi, pg in enumerate(pages(m['exp'])):
            lines = [letters(ink_codes(ln)) for ln in pg]
            for i, ln in enumerate(lines):
                if ln:
                    out.append((ln[::-1] if rev else ln, m,
                                (pi, i, lines, set() if rev else word_starts(pg[i]))))
    return out


def _prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def line_check(sp, msgs, ovl=None, files=None):
    """Each line on screen (glyph codes without spaces) against the lines of the strings
    drawn lately. A screen line that is the start of a string's line, with the rest
    neither on the screen line nor at the start of the next line of its layer, is cut
    short; one that matches a string's line all but a glyph or two is garbled. Lines no
    string explains (static labels, names, numbers drawn directly) aren't judged here.
    `files` gets, per line found in a string (by id of its first sprite), the string's file.

    Two more from the same matching: a line that starts like a string's line (8 glyphs
    or more) and then goes on differently is corrupted (the expand buffer overrun shows
    this way); and when a page's later line is on screen but an earlier one of the same
    page isn't, the page had more lines than the box shows (a line scrolled off). Not in
    battle, where the message box scrolls like a log."""
    cands = candidates(msgs)
    if not cands:
        return []
    rows = []
    for ln in lines_of(sp):
        codes = letters([s['code'] if s['tp'] == 0x0f else None for s in ln if not is_space(s)])
        if codes:
            rows.append((ln[0]['L'], ln[0]['y'], codes, ln))
    allcodes = {}
    for L, y, codes, ln in rows:
        allcodes.setdefault(L, []).extend(codes)
    out = []
    shown = collections.defaultdict(set)      # (string, page) -> its lines found on screen
    pagel = {}                                 # (string, page) -> its lines
    for i, (L, y, codes, ln) in enumerate(rows):
        if len(codes) < 3:
            continue
        nxt = next((c for (L2, y2, c, _) in rows[i + 1:] if L2 == L and y2 > y), [])
        exact = False
        trunc = garbled = differs = None
        # the longest string line inside this one (a name inside a sentence is a line
        # of its own string too)
        best = max(((len(want), m, pi, li, pl) for want, m, (pi, li, pl, _) in cands
                    if len(want) * 2 >= len(codes) and find(want, codes) >= 0),
                   key=lambda t: t[0], default=None)
        if best:
            exact = True
            k = (_sid(best[1]), best[2])
            shown[k].add(best[3])
            pagel[k] = (best[4], best[1])
            # centering is judged on whole lines only (not a line put together from
            # several strings, like the Temple's "Murmur- Chant- Pray-")
            if files is not None and best[0] == len(codes):
                files[id(ln[0])] = best[1].get('file')
        for want, m, (pi, li, plines, starts) in ([] if exact else cands):
            if len(want) > len(codes) and want[:len(codes)] == codes and \
                    (2 * len(codes) >= len(want) or len(codes) >= 8):
                rest = want[len(codes):]
                if nxt[:len(rest)] == rest or find(rest, allcodes.get(L, [])) >= 0:
                    exact = True          # the game wrapped it onto the next line
                    shown[(_sid(m), pi)].add(li)
                    pagel[(_sid(m), pi)] = (plines, m)
                    if files is not None:
                        files[id(ln[0])] = m.get('file')
                    break
                if len(codes) in starts:
                    continue              # ends on a whole word: a label ("Purchase",
                                          # a name) that starts a sentence, or a cut the
                                          # cut check sees from the refused glyphs
                if trunc is None or len(want) > len(trunc[0]):
                    trunc = (want, m)
            elif abs(len(want) - len(codes)) <= 1 and len(codes) >= 6:
                diff = sum(1 for a, b in zip(want, codes) if a != b)
                if 0 < diff <= 2 and (garbled is None or diff < garbled[2]):
                    garbled = (want, m, diff)
            else:
                p = _prefix(want, codes)
                if p >= 8 and p < min(len(want), len(codes)) and p not in starts and \
                        (differs is None or p > differs[2]):
                    differs = (want, m, p)
        STATS['screen lines compared'] += 1
        if exact:
            STATS['screen lines found in a string'] += 1
            continue
        if trunc:
            want, m = trunc
            out.append(dict(check='missing', what='line cut short: %d of %d glyphs drawn' % (len(codes), len(want)),
                            detail='%s|%s' % (_dec(codes), _dec(want[len(codes):])), string=_sid(m),
                            box=_bbox(ln)))
        elif garbled:
            want, m, diff = garbled
            out.append(dict(check='missing', what='%d wrong glyph(s) in a line' % diff,
                            detail='%s  (expected %s)' % (_dec(codes), _dec(want)), string=_sid(m),
                            box=_bbox(ln)))
        elif differs:
            want, m, p = differs
            out.append(dict(check='missing', what='line differs from its string after %d glyphs' % p,
                            detail='%s  (expected %s)' % (_dec(codes), _dec(want)), string=_sid(m),
                            box=_bbox(ln)))
    # every line of each string (all pages), to leave out lines a string has twice
    per = collections.defaultdict(collections.Counter)
    for want, m, (pi, li, pl, _) in cands:
        per[id(m)][tuple(map(str, want))] += 1
    texts = collections.defaultdict(collections.Counter)    # sid -> line -> most in one copy
    for want, m, x in cands:
        texts[_sid(m)] |= per[id(m)]
    for (sid, pi), got in shown.items():
        if ovl == 'BATTLE':
            break                       # the battle box scrolls: old lines leave by design
        if sid.startswith('None'):
            continue                    # item names and the like, drawn in pieces
        if any(k[0] == sid and k[1] > pi for k in shown):
            continue                    # a later part is up: the box scrolled after a wait
        plines, m = pagel[(sid, pi)]
        pgs = pages(m['exp'])
        if pi + 1 < len(pgs) and not any(ink_codes(x) for x in pgs[pi + 1]):
            continue                    # blank lines after a wait scroll the page out
        if sid.startswith('NPC_MES'):
            got = got | {0}             # the speaker's name, shown in the name plate
        # only a line the string has once says which page is up
        got = {li for li in got if li == 0 or texts[sid][tuple(map(str, plines[li]))] <= 1}
        if not got:
            continue
        gone = [li for li in range(max(got)) if li not in got and len(plines[li]) >= 3]
        if gone:
            out.append(dict(check='page', what='page %d: line(s) %s not on screen while a later line is'
                            % (pi + 1, ','.join(str(li + 1) for li in gone)),
                            detail=' / '.join(_dec(plines[li]) for li in gone), string=sid))
    return out


def _dec(codes):
    return ''.join(c if isinstance(c, str) else DEC.get(c, '?') if c is not None else '#' for c in codes)


def visibility(sp, img):
    """Per glyph: contrast of its ink against the rest of its cell in the shot (None
    for glyphs with no ink or off the picture)."""
    H, W = img.shape
    allink = np.zeros((H, W), bool)
    masks = []
    for s in sp:
        m = ink(s)
        masks.append(m)
        if m is None:
            continue
        ys, xs = np.nonzero(m)
        ys = ys + s['y']; xs = xs + s['x'] + XOFF
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        allink[ys[ok], xs[ok]] = True
    con = []
    for k, s in enumerate(sp):
        m = masks[k]
        x0, y0 = s['x'] + XOFF, s['y']
        if m is None or not m.any() or x0 < 0 or y0 < 0 or x0 + s['w'] > W or y0 + s['h'] > H:
            con.append(None)
            continue
        cell = img[y0:y0 + s['h'], x0:x0 + s['w']]
        other = allink[y0:y0 + s['h'], x0:x0 + s['w']] & ~m
        bg = cell[~m & ~other]
        if len(bg) < 4:
            con.append(None)
            continue
        # drawn: nearly all of its ink brighter than nearly all of the rest of its cell
        c = float(np.mean(cell[m] > np.percentile(bg, 90) + 8))
        con.append(c)
    return con, masks


VISIBLE = 0.75      # share of a glyph's ink brighter than the rest of its cell: drawn


def render_check(sp, still, img):
    """img: the shot as a float luminance array. A line whose glyphs mostly don't show
    is taken as not drawn (a window covers it, or its layer isn't shown) and left out.
    In the lines that are drawn: a glyph that doesn't show, and a glyph with something
    else bright inside its ink box (not its ink, not another drawn glyph's ink): a box
    border, an icon, other text."""
    H, W = img.shape
    con, masks = visibility(sp, img)
    drawn = [False] * len(sp)
    weak = []
    idx = {id(s): k for k, s in enumerate(sp)}
    for ln in lines_of(sp):
        ks = [idx[id(s)] for s in ln if con[idx[id(s)]] is not None]
        if not ks:
            continue
        vis = [k for k in ks if con[k] >= VISIBLE]
        if len(vis) < 0.7 * len(ks):
            continue                                  # not drawn (covered, or not shown)
        STATS['glyphs render-checked'] += len(ks)
        for k in ks:
            drawn[k] = True
            if con[k] < VISIBLE and (not still or still[k] == '1'):
                weak.append(sp[k])
    explained = np.zeros((H, W), bool)
    for k, s in enumerate(sp):
        if drawn[k]:
            ys, xs = np.nonzero(masks[k])
            ys = ys + s['y']; xs = xs + s['x'] + XOFF
            explained[ys, xs] = True
    foreign = []
    for k, s in enumerate(sp):
        if not drawn[k] or con[k] is None or con[k] < VISIBLE or (still and still[k] != '1'):
            continue
        m = masks[k]
        ys, xs = np.nonzero(m)
        x0, y0 = s['x'] + XOFF, s['y']
        Y0, Y1, X0, X1 = y0 + ys.min(), y0 + ys.max() + 1, x0 + xs.min(), x0 + xs.max() + 1
        sub = img[Y0:Y1, X0:X1]
        free = ~explained[Y0:Y1, X0:X1]
        cell = img[y0:y0 + s['h'], x0:x0 + s['w']]
        rest = cell[~explained[y0:y0 + s['h'], x0:x0 + s['w']]]
        if not len(rest):
            continue
        bgv = np.median(rest)
        thr = bgv + 0.6 * (img[y0 + ys, x0 + xs].mean() - bgv)
        if int(((sub > thr) & free).sum()) >= 3:
            foreign.append(s)
    out = []
    if weak:
        out.append(dict(check='render', what='%d glyph(s) in a drawn line not visible' % len(weak),
                        detail=_txt(weak), box=_bbox(weak)))
    if foreign:
        out.append(dict(check='render', what='%d glyph(s) with something else drawn in them' % len(foreign),
                        detail=_txt(foreign), box=_bbox(foreign)))
    return out


def _txt(gl):
    return ''.join(DEC.get(s['code'], '?') if s['code'] >= 0 else '#' for s in sorted(gl, key=lambda s: (s['y'], s['x'])))[:80]


def _bbox(gl):
    if not gl:
        return None
    return [min(s['x'] for s in gl), min(s['y'] for s in gl),
            max(s['x'] + s['w'] for s in gl), max(s['y'] + s['h'] for s in gl)]


def _sid(m):
    return '%s %s' % (m.get('file'), m.get('idx'))


def lum(path):
    return np.asarray(Image.open(path).convert('L'), dtype=float)


def run(dirs, out_path):
    nrec = 0
    counts = collections.Counter()
    with open(out_path, 'w') as fo:
        for d in dirs:
            base = os.path.join(OUTR, d)
            shots = {}
            for line in open(os.path.join(base, 'screens.jsonl')):
                try:
                    r = json.loads(line)
                except ValueError:
                    continue                    # a run still writing its last line
                if 'sprites' not in r:
                    continue
                nrec += 1
                img = None
                if r.get('stable') and r.get('shot'):
                    p = os.path.join(base, 'shots', r['shot'] + '.png')
                    if r['new'] and os.path.exists(p):
                        img = lum(p)
                STATS['screens'] += 1
                STATS['screens with a checked shot'] += img is not None
                SEEN['screen keys'].add(r['key'])
                for m in r.get('msgs') or []:
                    if m.get('fresh'):
                        SEEN['strings'].add(_sid(m))
                for f in check_record(r, img):
                    f.update(run=d, n=r['n'], frame=r['frame'], shot=r.get('shot'),
                             ovl=r['where']['ovl'], stable=r.get('stable'), why=r.get('why'))
                    for chk, what, sid, why in ALLOW:
                        if f['check'] == chk and f['what'].startswith(what) and \
                                (sid is None or f.get('string') == sid):
                            f['allowed'] = why
                    counts[f['check'] + (' (allowed)' if f.get('allowed') else '')] += 1
                    fo.write(json.dumps(f, ensure_ascii=False) + '\n')
    return nrec, counts


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('dirs', nargs='+')
    ap.add_argument('--out', default=os.path.join(OUTR, 't5/findings.jsonl'))
    ap.add_argument('--learn', action='store_true', help='learn the centered rows from DIRs')
    a = ap.parse_args()
    if a.learn:
        rows = learn_centers(a.dirs)
        print(len(rows), 'centered rows:', rows)
        sys.exit()
    n, c = run(a.dirs, a.out)
    print(n, 'screens;', dict(c))
    print(dict(STATS), {k: len(v) for k, v in SEEN.items()})
