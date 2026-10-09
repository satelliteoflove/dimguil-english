#!/usr/bin/env python3
"""Check every line castlecrawl.py saw against the script: cut off, packed, on screen.

    castlereport.py CRAWLDIR [--out DIR]

CRAWLDIR holds one castlecrawl.py output folder per start state. For each distinct line
on screen (or drawn on the way to one) this finds the translation string it came from,
then flags:

  cut       a full glyph layer refused part of it (from the glyph calls), or what's on
            screen stops short of the string's line
  unpacked  drawn in the 12 px font (the one with the letter pairs) without the
            pairs the encoder would use (the string lacks "compress"), so it takes more
            glyphs than it needs
  digraph   a letter-pair code in the 8 px or 6 px font, which has other glyphs in
            those cells (the bold menu labels draw "Sort Items" packed as "S∂/I3ms")
  edge      reaches past x = 336 or starts left of x = 8, the speech boxes' margin
            (the screen is 350 wide)
  japanese  a glyph code the English font doesn't have (untranslated text)
  unmatched no translation string has this text

Writes DIR/report.json and DIR/report.txt, plus one crop per line (the line's row in
the screenshot where it was seen) for review in DIR/crops/.
"""
import argparse, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from screentext import DEC, DIGRAPH_CODES
from castlecrawl import glyph_code
import descfit

ROOT = os.path.join(os.path.dirname(__file__), '..')
CTRL = re.compile(r'\{ff[0-9a-f]{2}\}')


def strings():
    """(file, index, line no, English line, compress) for every translated line."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'translations/*.json'))):
        # some files carry // comments, which the encoder allows
        d = json.loads(re.sub(r'(?m)//[^"\n]*$', '', open(f, encoding='utf-8').read()))
        i = 0
        for sec in d.get('sections', []):
            for x in sec.get('strings', []):
                tr = x.get('translation') or ''
                for k, line in enumerate(tr.split('\n')):
                    if line.strip():
                        out.append((os.path.basename(f), i, k, line, bool(x.get('compress'))))
                i += 1
    # The card game's unit and spell names, and the strings cb_strings.asm writes in
    # place, are ASCII in its overlays; keep every NUL-ended run of 3 or more.
    for name in ('CMENU.BIN', 'CMAIN.BIN'):
        d = open(os.path.join(ROOT, 'rips/dirty/dimguil', name), 'rb').read()
        for i, m in enumerate(re.finditer(rb'(?<![\x20-\x7e])[\x20-\x7e]{3,}(?=\0)', d)):
            line = m.group().decode().strip()
            if re.search('[A-Za-z]{2}', line):
                out.append((name, m.start(), 0, line, False))
    return out


def pattern(line):
    """A regex for an English line as drawn: control codes (names, numbers, button
    icons) match anything."""
    parts = CTRL.split(line)
    return re.compile('^' + '.*?'.join(re.escape(p) for p in parts) + '$')


def sheets(crawl, out, rows, per=20):
    """Crops of each line's row from its screenshot, 2x, labelled, `per` to a sheet."""
    from PIL import Image, ImageDraw
    pick = [r for r in rows if r['flags'] or r['y'] == 166 or len(r['text']) > 12]
    seen, items = set(), []
    for r in pick:
        if (r['text'], r['y']) in seen:
            continue
        seen.add((r['text'], r['y']))
        items.append(r)
    os.makedirs(os.path.join(out, 'sheets'), exist_ok=True)
    for f in glob.glob(os.path.join(out, 'sheets', '*.png')):
        os.remove(f)
    for s0 in range(0, len(items), per):
        part = items[s0:s0 + per]
        sheet = Image.new('RGB', (700, per * 52), 'white')
        d = ImageDraw.Draw(sheet)
        for j, r in enumerate(part):
            w = r['where'][0]
            nodes = os.path.join(crawl, w['crawl'], f"n{w['node']:04d}.png")
            if os.path.exists(nodes):
                im = Image.open(nodes).convert('RGB')
                top = max(0, r['y'] - 3)
                crop = im.crop((0, top, im.width, min(im.height, top + 16)))
                sheet.paste(crop.resize((crop.width * 2, crop.height * 2)), (0, j * 52 + 18))
            d.text((2, j * 52 + 3), f"{s0 + j}: {','.join(r['flags']) or 'ok'} L{r['layer']} "
                   f"y={r['y']} x={r['x0']}-{r['x1']} {w['crawl']} n{w['node']}", fill='black')
        sheet.save(os.path.join(out, 'sheets', f'{s0 // per:03d}.png'))
    json.dump(items, open(os.path.join(out, 'sheets', 'index.json'), 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('crawl')
    ap.add_argument('--out')
    a = ap.parse_args()
    out = a.out or os.path.join(a.crawl, 'report')
    os.makedirs(os.path.join(out, 'crops'), exist_ok=True)

    def decode(keys, codes):
        cs = [glyph_code(bytes.fromhex(k)) for k in keys]
        return cs, ''.join(DEC.get(c, '?') for c in cs)

    seen = {}           # (text, layer, y, x0) -> record

    def add(crawl, node, path, text, codes, layer, y, x0, x1, fixed, cut, source):
        k = (text, layer, y, x0)
        r = seen.get(k)
        if r is None:
            r = seen[k] = dict(text=text, codes=codes, layer=layer, y=y, x0=x0, x1=x1,
                               fixed=fixed, cut=False, where=[], source=source)
        r['cut'] |= bool(cut)
        if len(r['where']) < 4:
            r['where'].append(dict(crawl=crawl, node=node, path=' '.join(path)))

    lut = descfit.LUT
    screens = {}
    for d in sorted(glob.glob(os.path.join(a.crawl, '*/nodes.jsonl'))):
        crawl = os.path.basename(os.path.dirname(d))
        for l in open(d):
            n = json.loads(l)
            pieces = []
            for s in n['screen']:            # split again at 14 px (older crawls used 24)
                start = 0
                for j in range(1, len(s['xs']) + 1):
                    if j == len(s['xs']) or s['xs'][j] - s['xs'][j - 1] > 14:
                        pieces.append(dict(s, xs=s['xs'][start:j], keys=s['keys'][start:j],
                                           x0=s['xs'][start]))
                        start = j
            for s in pieces:
                codes, text = decode(s['keys'], s['codes'])
                xs = s['xs']
                steps = {b - a for a, b in zip(xs, xs[1:])}
                fixed = s['keys'][0][:2] != '0c'      # not the 12 px font
                x1 = xs[-1] + (8 if fixed or codes[-1] < 0 or codes[-1] >= len(lut) else lut[codes[-1]] + 1)
                add(crawl, n['id'], n['path'], text, codes, s['layer'], s['y'], s['x0'], x1,
                    fixed, False, 'screen')
                seen[(text, s['layer'], s['y'], s['x0'])]['cell'] = s['keys'][0][:2]
            screens[(crawl, n['id'])] = [(p['layer'], p['y'], decode(p['keys'], p['codes'])[1])
                                         for p in pieces]
            for s in n['drawn']:
                if s['cut']:
                    add(crawl, n['id'], n['path'], s['text'], None, s['layer'], s['y'],
                        s['x0'], s['x1'], s['fixed'], True, 'drawn')
        e = os.path.join(os.path.dirname(d), 'edges.jsonl')
        if os.path.exists(e):
            for l in open(e):
                g = json.loads(l)
                for s in g['drawn']:
                    if s['cut']:
                        add(crawl, g['node'], g['path'], s['text'], None, s['layer'], s['y'],
                            s['x0'], s['x1'], s['fixed'], True, 'drawn')

    S = strings()
    pats = [(pattern(line), f, i, k, line, comp) for f, i, k, line, comp in S
            if len(CTRL.sub('', line).strip()) >= 2]
    by_text = {}
    for r in seen.values():
        t = r['text'].strip()
        if not t or re.fullmatch(r'[\d\s/:.,()GHP%+-]*', t):
            continue
        if t not in by_text:
            m = [(f, i, k, line, comp) for p, f, i, k, line, comp in pats if p.match(t)]
            if not m:   # cut short: the line drawn is the start of a string's line
                m = [(f, i, k, line, comp) for p, f, i, k, line, comp in pats
                     if len(t) >= 4 and CTRL.sub('', line).startswith(t) and line != t]
                m = [x + ('prefix',) for x in m]
            by_text[t] = m
        r['match'] = by_text[t]

    full = set()
    for p, f, i, k, line, comp in pats:
        if not CTRL.search(line):
            full.add(line)

    def redraw_only(r):
        """A refusal while static text is redrawn: the screen there shows a whole line."""
        for w in r['where']:
            for L, y, text in screens.get((w['crawl'], w['node']), []):
                if L == r['layer'] and y == r['y'] and text.strip() in full \
                        and text.strip().startswith(r['text'].strip()[:4]):
                    return True
        return False

    rows = []
    for r in seen.values():
        if 'match' not in r:
            continue
        flags = []
        exact = [m for m in r['match'] if len(m) == 5]
        if r['cut'] and r['source'] == 'drawn' and redraw_only(r):
            r['cut'] = False
            continue
        if r['cut']:
            flags.append('cut')
        elif r['match'] and not exact and len(r['text'].strip()) >= 12:
            flags.append('cut')
        if not r['match']:
            flags.append('unmatched')
        codes = r['codes']
        if codes is not None:
            if any(c >= 0xd8 or c < 0 for c in codes):
                flags.append('japanese')
            bold = r.get('cell') == '08'
            # codes that are also single characters ("<" and ">" share cells with
            # "ta" and "'s") are the bold font's own glyphs
            if bold and any(c in DIGRAPH_CODES - set(descfit.CHARS.values()) for c in codes):
                flags.append('digraph')
            inserted = any(CTRL.search(m[3]) for m in r['match'])   # names come in raw
            if not r['fixed'] and len(codes) >= 3 and not inserted:
                try:
                    packed = [c for c in descfit.encode(r['text']) if c >= 0]
                except ValueError:
                    packed = codes
                if len(packed) < len(codes):
                    flags.append('unpacked')
        if r['x1'] is not None and (r['x1'] > 336 or r['x0'] < 8):
            flags.append('edge')
        r['flags'] = flags
        rows.append(r)
    rows.sort(key=lambda r: (not r['flags'], r['where'][0]['crawl'], r['y'], r['text']))
    json.dump(rows, open(os.path.join(out, 'report.json'), 'w'), indent=1)
    with open(os.path.join(out, 'report.txt'), 'w') as f:
        for r in rows:
            src = '; '.join(f'{m[0].split(".")[0]} {m[1]}' + ('(prefix)' if len(m) > 5 else '')
                            for m in r['match'][:3])
            w = r['where'][0]
            f.write(f"{','.join(r['flags']) or 'ok':18s} L{r['layer']} y={r['y']:3d} "
                    f"x={r['x0']}-{r['x1']} {'small ' if r['fixed'] else ''}{r['text']!r}  "
                    f"[{src}]  ({w['crawl']} n{w['node']}: {w['path']})\n")
    sheets(a.crawl, out, rows)
    print(len(rows), 'lines;', sum(1 for r in rows if r['flags']), 'flagged ->',
          os.path.join(out, 'report.txt'))


if __name__ == '__main__':
    main()
