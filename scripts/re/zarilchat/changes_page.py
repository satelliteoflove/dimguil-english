"""docs/work/zaril-chat-changes.html (2026-11-10): exactly what asm/bugfix_zaril_chat_topics.asm
changes in Zaril's chat table, block by block: the original table (rips/zarilfix/orig,
zpreview.py VARIANT=orig) beside the fixed one (rips/zarilfix/verify2, zpages.py), both on
disc ba9710114fc2f9472d0d72ecc80de59f, plus the halfwords themselves.

    changes_page.py OUT.html          (run from the repo root)
"""
import base64, glob, html, io, json, re, struct, sys
from PIL import Image
OUT = sys.argv[1]
SPEAKERS = ['Zaril', 'Fritillaria', 'Gaura']
RUNS = {'orig': ('rips/zarilfix/orig', 'orig'), 'fix': ('rips/zarilfix/verify2', 'force')}
CHANGED = [6, 9, 10, 13]
TABLE = 0x800a8988
FACE = {0: 'mild smile', 1: 'grin', 2: 'scowl', 3: 'pained, sorry look'}

ja = json.load(open('rips/stage/out/dumps/NPC_MES5.OBJ.json'))['sections'][0]['strings']
en = json.load(open('rips/stage/out/dumps/NPC_MES5.OBJ.json'.replace('rips/stage/out/dumps', 'translations')))
en = en['sections'][0]['strings']

runs = {}
for var, (d, prefix) in RUNS.items():
    for p in glob.glob(f'{d}/results_*.json'):
        for b, r in json.load(open(p)).items():
            runs[(var, int(b))] = (r['order'], d, f'{prefix}{int(b):02d}')


def pages(text):
    text = re.sub(r'\{ff(?!20)[0-9a-f]{2}\}', '', text)
    out = []
    for pg in re.split(r'\r|\{ff20\}', text):
        lines = [l.strip() for l in pg.split('\n') if l.strip()]
        if lines:
            out.append(lines)
    return out


def flat(text):
    return ' '.join(' '.join(p) for p in pages(text))


def b64(f):
    buf = io.BytesIO(); Image.open(f).save(buf, 'PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def column(var, b):
    order, d, prefix = runs[(var, b)]
    chat = [o for o in order if tuple(o['chat'] or ()) == (1, b)]
    bar = next(o for o in chat if o['op'] == 'bar')
    rows = {}
    for o in chat:
        if o['op'] != 'say':
            continue
        shots = []
        for f in sorted(glob.glob(f'{d}/{prefix}_p1_b{b}_*_{o["n"]}.png')):
            im = Image.open(f).convert('RGB')
            if sum(1 for p in im.crop((8, 14, 300, 62)).get_flattened_data() if min(p) > 185) > 40:
                shots.append(f)
        pg = pages(o['text'])
        assert len(pg) == len(shots), (var, b, o['n'], len(pg), len(shots))
        who = o['text'].split('\n', 1)[0]
        rows.setdefault(who, []).append((o['n'], list(zip(shots, pg))))
    return (bar['n'], pages(bar['text'])[0][0]), rows


# the halfwords, read from the clean and the built MCARD
cl = open('rips/clean/dimguil/MCARD.BIN', 'rb').read()
mc = open('rips/iso/dimguil/MCARD.BIN', 'rb').read()
OPN = {-1: 0, 0: 2, 1: 2, 2: 1, 3: 3, 4: 0, 5: 0, 6: 1, 7: 1, 8: 1, 9: 1, 10: 4, 11: 1}
diffs = []
for blk in range(14):
    p = TABLE - 0x800a1000 + blk * 200; end = p + 200
    while p < end:
        op = struct.unpack_from('<h', cl, p)[0]
        if op == -1:
            break
        for k in range(OPN[op]):
            q = p + 2 + 2 * k
            a, v = struct.unpack_from('<h', cl, q)[0], struct.unpack_from('<h', mc, q)[0]
            if a != v:
                what = {7: 'topic line', 2: 'line spoken', 3: 'expression'}[op]
                diffs.append((blk, 0x800a1000 + q, what, a, v))
        p += 2 + 2 * OPN[op]
assert len(diffs) == 7, diffs


def describe(what, a, v):
    if what == 'expression':
        return f'{a} ({FACE[a]})', f'{v} ({FACE[v]})'
    return f'5:{a} “{flat(en[a]["translation"]).split(chr(34))[-2] if chr(34) in en[a]["translation"] else flat(en[a]["translation"])}”', \
           f'5:{v} “{flat(en[v]["translation"]).split(chr(34))[-2] if chr(34) in en[v]["translation"] else flat(en[v]["translation"])}”'


NOTES = {
    6: 'The topic line changes; the three replies stay. All three are answers to being asked for '
       'information (Zaril’s and Gaura’s are copies of their lines under “new information” '
       'in Fontana’s and Balbo’s tables).',
    9: 'The topic line changes, and Fritillaria’s reply is swapped with his reply in block 10, '
       'with the expression each had in its own block: he now looks sorry here instead of grinning. '
       'Zaril’s and Gaura’s replies are copies of their lines under “new information”.',
    10: 'The other half of the swap: Fritillaria’s story of how Zaril saved him comes here from '
        'block 9, with its grin, in place of “nothing new to spill”. The topic stays.',
    13: 'The topic line changes; the three replies stay. Gaura’s “I heard it already” is a '
        'copy of his line under “told them” in Balbo’s table, and Fritillaria’s '
        '“Aw, that again” goes with it.',
}

css = """
:root { --bg:#15171c; --panel:#1f222a; --ink:#eceef2; --soft:#a6adba; --line:#2f343e; --chg:#e3b35a; --chgbg:#2b2618; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family: "Bitstream Charter", Charter, Georgia, serif; line-height:1.5; }
main { max-width: 1240px; margin: 0 auto; padding: 2rem 1.2rem 4rem; }
h1 { font-size: 1.9rem; margin: 0 0 .6rem; }
p { font-size: 1.15rem; max-width: 50rem; }
.soft { color: var(--soft); }
nav { font-size: 1.1rem; line-height: 2; }
nav a { color: var(--ink); margin-right: 1.2rem; }
table { border-collapse: collapse; font-size: 1.1rem; margin: 1rem 0; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: .5rem .7rem; border-bottom: 1px solid var(--line); }
th { color: var(--soft); font-weight: 400; }
td.to { color: var(--chg); }
.ja { font-size: 1.05rem; color: var(--soft); white-space: pre-line; margin-top: .35rem; }
section { margin-top: 3rem; border-top: 1px solid var(--line); padding-top: 1.4rem; }
h2 { font-size: 1.6rem; margin: 0 0 .3rem; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem 1.6rem; }
.head { font-size: 1.3rem; font-weight: 700; }
.topic { background: var(--panel); border-radius: 6px; padding: .7rem 1rem; font-size: 1.35rem; }
.topic .lab { display:block; font-size: .95rem; color: var(--soft); }
.changed { background: var(--chgbg); box-shadow: inset 4px 0 0 var(--chg); }
.cell { min-width: 0; }
figure { margin: 0 0 1rem; }
img { display:block; width:100%; max-width:560px; image-rendering: pixelated; border-radius: 4px; }
figcaption { margin-top: .5rem; background: var(--panel); border-radius: 6px; padding: .75rem 1rem; }
.box { font-size: 1.45rem; line-height: 1.35; white-space: pre-line; }
.ref { font-size: .95rem; color: var(--soft); margin-top: .35rem; }
.tag { font-size: .95rem; color: var(--chg); margin-top: .35rem; }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } table { font-size: .95rem; } }
"""
E = html.escape
H = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
     '<meta name="viewport" content="width=device-width, initial-scale=1">',
     "<title>Zaril's chat: exactly what the fix changes</title>", f'<style>{css}</style></head><body><main>',
     "<h1>Zaril's chat: exactly what the fix changes</h1>",
     '<p>The fix as rebuilt today (commit b38255a, disc ba971011). It changes four of the fourteen chat '
     'blocks and nothing else: blocks 0-5, 7, 8, 11 and 12 play exactly as the game shipped them. No text '
     'changes here; only which line plays where. Every line stays with its own speaker.</p>',
     '<p class="soft">The one related text change is separate and already reviewed: the topic line 5:98 now reads '
     '“We asked if they had any new information.” (it was “We asked if they had any news.”). It '
     'shows on both sides below, since both were captured on the current disc.</p>',
     '<h2>Every value the fix changes</h2>',
     '<p class="soft">Seven numbers in the chat table in MCARD, read from the original and the built file. '
     'A topic line or spoken line is an NPC_MES5 index; an expression picks Fritillaria’s portrait.</p>',
     '<table><tr><th>Block</th><th>What</th><th>Original</th><th>Now</th></tr>']
for blk, addr, what, a, v in diffs:
    fa, fv = describe(what, a, v)
    H.append(f'<tr><td>{blk}</td><td>{E(what)}{" (Fritillaria)" if what != "topic line" else ""}</td>'
             f'<td>{E(fa)}</td><td class="to">{E(fv)}</td></tr>')
H.append('</table>')
H.append('<nav>' + ''.join(f'<a href="#b{b}">Block {b}</a>' for b in CHANGED) + '</nav>')
H.append('<p class="soft">Each block below: left, the original table; right, the fixed one. Both captured in the '
         'emulator on the same disc, the left with the original table laid back into memory. Every page of '
         'every reply has its own shot, with the text below it. Whatever differs from the left is marked in '
         'gold.</p>')

for b in CHANGED:
    data = [column('orig', b), column('fix', b)]
    H.append(f'<section id="b{b}"><h2>Block {b}</h2><p>{E(NOTES[b])}</p>'
             '<div class="grid"><div class="head">The original game</div><div class="head">With the fix</div>')
    for k, ((bn, btxt), _) in enumerate(data):
        chg = ' changed' if k and bn != data[0][0][0] else ''
        H.append(f'<div class="topic{chg}"><span class="lab">Topic line on the bottom bar (5:{bn})</span>{E(btxt)}'
                 f'<div class="ja">{E(ja[bn]["source"])}</div></div>')
    for who in SPEAKERS:
        for k, (_, rows) in enumerate(data):
            refs = [n for n, _ in rows.get(who, [])]
            chg = k and refs != [n for n, _ in data[0][1].get(who, [])]
            H.append('<div class="cell">')
            for n, figs in rows.get(who, []):
                for i, (f, lines) in enumerate(figs):
                    jtxt = ja[n]['source'].replace('\r', '').split('\n', 1)[1] if i == len(figs) - 1 else ''
                    H.append(f'<figure><img alt="{who}, NPC_MES5 {n}" src="data:image/png;base64,{b64(f)}">'
                             f'<figcaption class="{"changed" if chg else ""}"><div class="box">{E(chr(10).join(lines))}</div>'
                             + (f'<div class="ja">{E(jtxt)}</div>' if jtxt else '') +
                             f'<div class="ref">{who}, NPC_MES5 {n}</div>'
                             + ('<div class="tag">Changed from the left</div>' if chg else '') +
                             '</figcaption></figure>')
            H.append('</div>')
    H.append('</div></section>')
H.append('</main></body></html>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(H))
print('wrote', OUT)
