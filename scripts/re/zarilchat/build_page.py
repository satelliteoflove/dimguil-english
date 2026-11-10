"""docs/work/zaril-chat-table.html: every page of every Zaril chat block, as the emulator
showed it (zpages.py shots), with the on-screen text repeated below each shot."""
import base64, collections, glob, html, io, json, re, sys
from PIL import Image
OUT = sys.argv[1]
res = {}
for p in glob.glob('pages/results_*.json'):
    res.update(json.load(open(p)))
BAR = {98: 'We asked if they had any news.', 99: 'We told them everything we knew.',
       100: 'We asked them about themselves.', 101: 'We asked about other parties.',
       102: 'We asked them something personal.'}
PROPOSED = {6: (98, None), 7: (100, None), 8: (99, None), 9: (98, '87 in place of 84'),
            10: (102, '84 in place of 87'), 12: (100, '96 in place of 93'), 13: (99, '93 in place of 96')}

def pages(text):
    text = re.sub(r'\{ff(?!20)[0-9a-f]{2}\}', '', text)
    out = []
    for k, pg in enumerate(re.split(r'\r|\{ff20\}', text)):
        lines = [l.strip() for l in pg.split('\n') if l.strip()]
        if lines:
            out.append(lines)
    return out

def textshots(prefix):
    keep = collections.defaultdict(list)
    for f in sorted(glob.glob(f'pages/{prefix}_*.png')):
        idx = int(f.rsplit('_', 1)[1][:-4])
        im = Image.open(f).convert('RGB')
        if sum(1 for p in im.crop((8, 14, 300, 62)).getdata() if min(p) > 185) > 40:
            keep[idx].append(f)
    return keep

def b64(f):
    buf = io.BytesIO(); Image.open(f).save(buf, 'PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

blocks = []
for b in [0, 1] + list(range(2, 14)):
    src, chat = ('0', (2, 1)) if b == 1 else (str(b), (1, b))
    order = [o for o in res[src]['order'] if tuple(o['chat'] or ()) == chat]
    prefix = f'force{int(src):02d}_p{chat[0]}_b{chat[1]}'
    shots = textshots(prefix)
    bar = next(o['n'] for o in order if o['op'] == 'bar')
    figs, problems = [], []
    for o in order:
        if o['op'] != 'say':
            continue
        pg, sh = pages(o['text']), shots.get(o['n'], [])
        if len(pg) != len(sh):
            problems.append(f"line {o['n']}: {len(sh)} shots for {len(pg)} pages")
        for k, f in enumerate(sh):
            figs.append((f, o['n'], pg[k] if k < len(pg) else ['(page text not matched)']))
    blocks.append((b, bar, figs, problems))

css = """
:root { --bg:#14161b; --panel:#1d2027; --ink:#eceef2; --soft:#a9b0bc; --line:#2e333d; --warn:#e3b35a; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family: "Bitstream Charter", Charter, Georgia, serif; line-height:1.45; }
main { max-width: 760px; margin: 0 auto; padding: 2rem 1.2rem 4rem; }
h1 { font-size: 1.9rem; margin: 0 0 .6rem; }
.intro { color: var(--soft); font-size: 1.05rem; }
section { margin-top: 3.2rem; border-top: 1px solid var(--line); padding-top: 1.6rem; }
h2 { font-size: 1.6rem; margin: 0; }
.topic { font-size: 1.25rem; margin: .4rem 0 0; }
.topic b { font-weight: 700; }
.prop { font-size: 1.05rem; color: var(--warn); margin: .3rem 0 0; }
.same { font-size: 1.05rem; color: var(--soft); margin: .3rem 0 0; }
figure { margin: 1.8rem 0 0; }
img { display:block; width:100%; max-width:700px; image-rendering: pixelated; border-radius: 4px; }
figcaption { margin-top: .7rem; background: var(--panel); border-radius: 6px; padding: .9rem 1.1rem; }
.box { font-size: 1.55rem; line-height: 1.35; white-space: pre-line; }
.ref { font-size: .95rem; color: var(--soft); margin-top: .5rem; }
.bar { font-size: 1.15rem; color: var(--soft); margin-top: .35rem; }
.problem { color: var(--warn); }
nav { margin-top: 1.2rem; font-size: 1.05rem; line-height: 2; }
nav a { color: var(--ink); margin-right: .9rem; }
"""
H = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
     '<meta name="viewport" content="width=device-width, initial-scale=1">',
     "<title>Zaril's chat table, block by block</title>", f'<style>{css}</style></head><body><main>',
     "<h1>Zaril's chat table, block by block</h1>",
     '<p class="intro">Every chat block of Zaril\'s party as the game plays it now (the current English build, '
     'disc 756d4fb0, main 4a53dc4), from the emulator. Each block was forced in turn; block 1 is the second '
     'Talk press. Every page of every reply is shown, with the text on screen repeated below it. The topic '
     'line stays on the bottom bar while the replies play. Blocks 0 and 2-13 each come up 1 time in 13 '
     '(docs/re/bugs.md 2.10).</p>',
     '<nav>' + ''.join(f'<a href="#b{b}">Block {b}</a>' for b, *_ in blocks) + '</nav>']
for b, bar, figs, problems in blocks:
    H.append(f'<section id="b{b}"><h2>Block {b}</h2>')
    H.append(f'<p class="topic">Topic line: <b>{html.escape(BAR[bar])}</b> <span class="ref">(5:{bar})</span></p>')
    if b in PROPOSED:
        nb, swap = PROPOSED[b]
        bits = []
        if nb != bar:
            bits.append(f'topic line becomes “{BAR[nb][:-1]}”')
        if swap:
            bits.append(f'Fritillaria\'s {swap}')
        H.append(f'<p class="prop">Proposed: {html.escape("; ".join(bits)).rstrip(".")}.</p>')
    else:
        H.append('<p class="same">Proposed: no change.</p>')
    for p in problems:
        H.append(f'<p class="problem">{html.escape(p)}</p>')
    for f, n, lines in figs:
        H.append(f'<figure><img alt="Block {b}, line 5:{n}" src="data:image/png;base64,{b64(f)}">'
                 f'<figcaption><div class="box">{html.escape(chr(10).join(lines))}</div>'
                 f'<div class="bar">Bar: {html.escape(BAR[bar])}</div>'
                 f'<div class="ref">NPC_MES5 {n}</div></figcaption></figure>')
    H.append('</section>')
H.append('</main></body></html>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(H))
print('blocks', len(blocks), 'figures', sum(len(f) for _, _, f, _ in blocks))
for b, bar, figs, problems in blocks:
    if problems: print(b, problems)
