"""docs/work/zaril-chat-compare.html: Zaril's chat blocks side by side, as the game plays
them now and with a proposed table change, each captured in the emulator (zpages.py for
"now", zpreview.py VARIANT=prop|alt for the changes). Rows line up by speaker.

    compare_page.py OUT.html
"""
import base64, glob, html, io, json, re, sys
from PIL import Image
OUT = sys.argv[1]
ONLY = [int(x) for x in sys.argv[2:]]     # indexes into COMPARES to show; default all
INTRO2 = ('Open: blocks 1 and 12, which go together. Below them, blocks 9, 10 and 13 as approved, now with each '
          'moved line keeping the expression its own block gave it. Blocks 6, 8 and 11 change no expressions and '
          'are left off; block 7 stays as it is.') if ONLY else ''
BAR = {98: 'We asked if they had any news.', 99: 'We told them everything we knew.',
       100: 'We asked them about themselves.', 101: 'We asked about other parties.',
       102: 'We asked them something personal.'}
SPEAKERS = ['Zaril', 'Fritillaria', 'Gaura']

runs = {}   # (variant, block) -> order list
for p in glob.glob('pages/results_*.json'):
    for b, r in json.load(open(p)).items():
        runs[('now', int(b))] = (r['order'], 'pages', f'force{int(b):02d}')
for p in glob.glob('preview/results_*.json'):
    var = p.split('_')[1]
    for b, r in json.load(open(p)).items():
        runs[(var, int(b))] = (r['order'], 'preview', f'{var}{int(b):02d}')


def pages(text):
    text = re.sub(r'\{ff(?!20)[0-9a-f]{2}\}', '', text)
    out = []
    for pg in re.split(r'\r|\{ff20\}', text):
        lines = [l.strip() for l in pg.split('\n') if l.strip()]
        if lines:
            out.append(lines)
    return out


def b64(f):
    buf = io.BytesIO(); Image.open(f).save(buf, 'PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def column(var, b):
    """bar index, and per speaker: (line index, [(shot, page lines)])."""
    press = 2 if b == 1 else 1          # block 1 is the second Talk press of a block-0 run
    order, d, prefix = runs[(var, 0 if b == 1 else b)]
    chat = [o for o in order if tuple(o['chat'] or ()) == (press, b)]
    bar = next(o['n'] for o in chat if o['op'] == 'bar')
    rows = {}
    for o in chat:
        if o['op'] != 'say':
            continue
        shots = []
        for f in sorted(glob.glob(f'{d}/{prefix}_p{press}_b{b}_*_{o["n"]}.png')):
            im = Image.open(f).convert('RGB')
            if sum(1 for p in im.crop((8, 14, 300, 62)).getdata() if min(p) > 185) > 40:
                shots.append(f)
        pg = pages(o['text'])
        assert len(pg) == len(shots), (var, b, o['n'], len(pg), len(shots))
        who = o['text'].split('\n', 1)[0]
        rows.setdefault(who, []).append((o['n'], list(zip(shots, pg))))
    return bar, rows


# (title, note, [(left label, variant, block), (right label, variant, block)])
COMPARES = [
    ('Block 6', 'Approved: the topic line changes; the replies stay.',
     [('Now', 'now', 6), ('Proposed', 'prop', 6)]),
    ('Block 9', "Approved: the topic line changes, and Fritillaria's reply comes from block 10.",
     [('Now', 'now', 9), ('Proposed', 'prop', 9)]),
    ('Block 10', "Fritillaria's reply comes from block 9 (the other half of the block 9 swap); the topic stays.",
     [('Now', 'now', 10), ('Proposed', 'prop', 10)]),
    ('Block 13', "Proposed: the topic line becomes “We told them everything we knew”, and the replies stay.",
     [('Now', 'now', 13), ('Proposed', 'prop', 13)]),
    ('Block 13: which Zaril line?', "Block 13's topic line becomes \u201cWe told them everything we knew\u201d either way; "
     "Fritillaria's and Gaura's replies fit it. Left, Zaril keeps his own line. Right, he gets his line from "
     "block 8, and the swap changes block 8 too (below).",
     [('Proposed', 'prop', 13), ('Alternative', 'alt', 13)]),
    ('Block 8 under the alternative', "What the alternative does to block 8: Zaril's line from block 13 replaces his "
     "own; the topic stays “something personal”.",
     [('Now', 'now', 8), ('Alternative', 'alt', 8)]),
    ('Block 8', "Proposed: the topic line becomes \u201cWe told them everything we knew\u201d, which Zaril's and "
     "Fritillaria's replies answer. Gaura's line about himself moves to block 11, and he says \u201cMmm...\u201d, his reply "
     "from block 1. Zaril's line also plays in block 13 now, as you chose.",
     [('Now', 'now', 8), ('Proposed', 'v3', 8)]),
    ('Block 11', "Gaura's line from block 8 replaces his \u201cI'm gonna be a Samurai. Someday.\u201d, which is word for "
     "word the same line as his reply in block 10, so it still plays there.",
     [('Now', 'now', 11), ('Proposed', 'v3', 11)]),
    ('Block 1', "Fritillaria's \u201cWhoa, awesome! You guys are good!\u201d comes here from block 12, under \u201cWe told "
     "them everything we knew\u201d. Block 1 is what the second Talk press always plays.",
     [('Now', 'now', 1), ('Proposed', 'v4f', 1)]),
    ('Block 12', "Fritillaria's \u201cWhaaat? You got business with me or something?\u201d comes here from block 1, "
     "a brush-off beside Zaril's \u201cWhy should I have to tell you that?\u201d.",
     [('Now', 'now', 12), ('Proposed', 'v4f', 12)]),
    ('Block 9, approved', "As approved, with the fix now moving each line's expression with it: Fritillaria's "
     "\u201cnothing new to spill, sorry\u201d brings his sorry look from block 10.",
     [('Now', 'now', 9), ('Approved', 'final', 9)]),
    ('Block 10, approved', "Fritillaria's story of how Zaril saved him brings his grin from block 9.",
     [('Now', 'now', 10), ('Approved', 'final', 10)]),
    ('Block 13, approved', "Zaril's line from block 8 brings its expression (Zaril's expressions differ only slightly).",
     [('Now', 'now', 13), ('Approved', 'final', 13)]),
]

css = """
:root { --bg:#15171c; --panel:#1f222a; --ink:#eceef2; --soft:#a6adba; --line:#2f343e; --chg:#e3b35a; --chgbg:#2b2618; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family: "Bitstream Charter", Charter, Georgia, serif; line-height:1.45; }
main { max-width: 1240px; margin: 0 auto; padding: 2rem 1.2rem 4rem; }
h1 { font-size: 1.9rem; margin: 0 0 .6rem; }
.intro { color: var(--soft); font-size: 1.1rem; max-width: 46rem; }
nav { margin-top: 1rem; font-size: 1.05rem; line-height: 2; }
nav a { color: var(--ink); margin-right: 1rem; }
section { margin-top: 3rem; border-top: 1px solid var(--line); padding-top: 1.4rem; }
h2 { font-size: 1.6rem; margin: 0; }
.note { font-size: 1.1rem; color: var(--soft); margin: .35rem 0 1.2rem; max-width: 50rem; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem 1.6rem; }
.head { font-size: 1.3rem; font-weight: 700; }
.topic { background: var(--panel); border-radius: 6px; padding: .7rem 1rem; font-size: 1.35rem; }
.topic .lab, .who .lab { display:block; font-size: .95rem; color: var(--soft); }
.changed { background: var(--chgbg); box-shadow: inset 4px 0 0 var(--chg); }
.who { padding: .2rem .1rem; }
.cell { min-width: 0; }
figure { margin: 0 0 1rem; }
img { display:block; width:100%; max-width:560px; image-rendering: pixelated; border-radius: 4px; }
figcaption { margin-top: .5rem; background: var(--panel); border-radius: 6px; padding: .75rem 1rem; }
.box { font-size: 1.45rem; line-height: 1.35; white-space: pre-line; }
.ref { font-size: .95rem; color: var(--soft); margin-top: .35rem; }
.tag { font-size: .95rem; color: var(--chg); margin-top: .35rem; }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
"""
H = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
     '<meta name="viewport" content="width=device-width, initial-scale=1">',
     "<title>Zaril's chat: the proposed changes side by side</title>", f'<style>{css}</style></head><body><main>',
     "<h1>Zaril's chat: the proposed changes side by side</h1>",
     '<p class="intro">Each pair shows a chat block as the game plays it now and with the change, both '
     'captured in the emulator from the current English build (main 4a53dc4). The changed version was '
     'played with the table edit laid into MCARD in RAM; no disc was built. Rows line up by speaker, and '
     'every page of a reply has its own shot with the text below it. Whatever differs from the left '
     'column is marked in gold.</p>',
     '<p class="intro">' + INTRO2 + '</p>',
     '<nav>' + ''.join(f'<a href="#c{i}">{html.escape(t)}</a>' for i, (t, _, _) in enumerate(COMPARES)
                       if not ONLY or i in ONLY) + '</nav>']
for i, (title, note, cols) in enumerate(COMPARES):
    if ONLY and i not in ONLY:
        continue
    data = [column(v, b) for _, v, b in cols]
    H.append(f'<section id="c{i}"><h2>{html.escape(title)}</h2><p class="note">{html.escape(note)}</p><div class="grid">')
    for label, _, b in cols:
        H.append(f'<div class="head">{html.escape(label)} (block {b})</div>')
    for k, (bar, _) in enumerate(data):
        chg = ' changed' if k and bar != data[0][0] else ''
        H.append(f'<div class="topic{chg}"><span class="lab">Topic line on the bottom bar (5:{bar})</span>'
                 f'{html.escape(BAR[bar])}</div>')
    for who in SPEAKERS:
        for k, (bar, rows) in enumerate(data):
            refs = [n for n, _ in rows.get(who, [])]
            chg = k and refs != [n for n, _ in data[0][1].get(who, [])]
            H.append(f'<div class="cell">')
            for n, figs in rows.get(who, []):
                for f, lines in figs:
                    H.append(f'<figure><img alt="{who}, NPC_MES5 {n}" src="data:image/png;base64,{b64(f)}">'
                             f'<figcaption class="{"changed" if chg else ""}"><div class="box">{html.escape(chr(10).join(lines))}</div>'
                             f'<div class="ref">{who}, NPC_MES5 {n}</div>'
                             + (f'<div class="tag">Changed from the left</div>' if chg else '') +
                             '</figcaption></figure>')
            H.append('</div>')
    H.append('</div></section>')
H.append('</main></body></html>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(H))
print('wrote', OUT, len(COMPARES), 'comparisons')
