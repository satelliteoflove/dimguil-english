"""docs/work/zaril-chat-compare.html (2026-11-10): Zaril's chat as the fixed disc plays it
(rips/zarilfix/verify, disc adc20ddd) beside the recommended table (rips/zarilfix/rec,
zpreview.py VARIANT=rec on the same disc), for the blocks where they differ, with the
evidence from the tables Zaril's and Gaura's lines were copied from.

    recommend_page.py OUT.html          (run from the repo root)
"""
import base64, glob, html, io, json, re, sys
from PIL import Image
OUT = sys.argv[1]
SPEAKERS = ['Zaril', 'Fritillaria', 'Gaura']
RUNS = {'now': ('rips/zarilfix/verify', 'force'), 'rec': ('rips/zarilfix/rec', 'rec')}

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
            if sum(1 for p in im.crop((8, 14, 300, 62)).getdata() if min(p) > 185) > 40:
                shots.append(f)
        pg = pages(o['text'])
        assert len(pg) == len(shots), (var, b, o['n'], len(pg), len(shots))
        who = o['text'].split('\n', 1)[0]
        rows.setdefault(who, []).append((o['n'], list(zip(shots, pg))))
    return (bar['n'], pages(bar['text'])[0][0]), rows


# block -> (title, what changes, why)
SECTIONS = [
    (8, 'Block 8: back to the original',
     'On the disc now, the topic is “We told them everything we knew” and Gaura says “Mmm...” '
     '(his block 1 line). Recommended: the original, topic “We asked them something personal” with '
     'Gaura’s own “I’m slow, but the rest, great.”',
     'Zaril’s line here is a copy of one of his lines in Fontana’s party table, and there it sits under '
     '“We asked them something personal”, right after Fontana says “......A sword is about all I’m '
     'good for.” So the writers meant it as part of a talk about what each of them is good at: Fontana is only '
     'good with a sword, Zaril says they’re all still green, the party included. Gaura’s line is a copy from '
     'Balbo’s table, also under “something personal”, beside Balbo’s “I’m a heck of a '
     'swimmer” and Reiran’s “I’m pretty good with a sword.” Read that way, block 8 is one '
     'talk about strengths, and Fritillaria’s “you guys are way tougher than you look” fits it too. '
     'Two of the three lines have the writers’ own topic on record, and it’s the one block 8 already shows.'),
    (11, 'Block 11: back to the original',
     'On the disc now, Gaura says “I’m slow, but the rest, great”, moved here from block 8. '
     'Recommended: the original, his “I’m gonna be a Samurai. Someday.”',
     'This change only existed to give Gaura’s block 8 line somewhere to play. With block 8 back as it was, '
     'it isn’t needed. The Samurai line is the same Japanese as his reply in block 10, but block 11 was '
     'consistent as the game shipped it: all three are about themselves, under “something personal”.'),
    (13, 'Block 13: keep the new topic line, but Zaril keeps his own line',
     'On the disc now, the topic is “We told them everything we knew” and Zaril says “Well, same goes '
     'for us, but I guess you guys are still greenhorns too” (his block 8 line). Recommended: the same topic '
     'line, with Zaril’s own “Sorry. Nothing new to tell.” and its own expression.',
     'This block really is mixed in the original. Zaril’s line is a copy of his line in Fontana’s table '
     'under “We asked if they had any new information”; Gaura’s “I heard it already” is a '
     'copy from Balbo’s table under “We told them everything we knew”, and Fritillaria’s '
     '“Aw, that again” goes with Gaura’s. Fontana’s table also has an unused Zaril line for that '
     'topic, “Heard that one before”, so the writers most likely meant Zaril to say that here and copied '
     'the wrong line. That line isn’t in Zaril’s own text file, so it can’t be used without adding '
     'text. Of the lines that are there, his own one is the smallest change: only the topic line moves, and '
     '“Sorry. Nothing new to tell” reads naturally as having nothing new to give back. His '
     '“greenhorns” line is a “something personal” line by the same evidence as block 8, and with '
     'block 8 back it would play under two different topics.'),
]

# what the writers' own tables say: Zaril's lines are copied from Fontana's party table
# (NPC_MES3), Gaura's from Balbo's (NPC_MES2); Fritillaria's are new to this table.
# block: (original topic, Zaril source topic, Gaura source topic, disc now, recommended)
SUMMARY = [
    (0, 'new information', 'new information', 'new information', 'unchanged', 'unchanged'),
    (1, 'told them', 'told them', 'told them', 'unchanged', 'unchanged'),
    (2, 'told them', 'told them', 'about themselves (humming)', 'unchanged', 'unchanged'),
    (3, 'other parties', 'other parties', '(not a copy)', 'unchanged', 'unchanged'),
    (4, 'other parties', 'other parties', 'other parties', 'unchanged', 'unchanged'),
    (5, 'other parties', 'other parties', 'other parties', 'unchanged', 'unchanged'),
    (6, 'told them', 'new information', 'new information', 'topic: new information', 'keep'),
    (7, 'something personal', 'something personal', 'about themselves', 'unchanged', 'unchanged'),
    (8, 'something personal', 'something personal', 'something personal',
     'topic: told them; Gaura says “Mmm...”', 'back to the original'),
    (9, 'told them', 'new information', 'new information',
     'topic: new information; Fritillaria’s “nothing new” from block 10', 'keep'),
    (10, 'something personal', 'something personal', 'about themselves',
     'Fritillaria’s story of Zaril saving him from block 9', 'keep'),
    (11, 'something personal', 'something personal', 'about themselves',
     'Gaura’s “I’m slow” from block 8', 'back to the original'),
    (12, 'about themselves', 'about themselves', 'something personal', 'unchanged', 'unchanged'),
    (13, 'new information', 'new information', 'told them',
     'topic: told them; Zaril’s “greenhorns” from block 8', 'keep the topic; Zaril’s own line back'),
]

css = """
:root { --bg:#15171c; --panel:#1f222a; --ink:#eceef2; --soft:#a6adba; --line:#2f343e; --chg:#e3b35a; --chgbg:#2b2618; --ok:#8fc79a; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family: "Bitstream Charter", Charter, Georgia, serif; line-height:1.5; }
main { max-width: 1240px; margin: 0 auto; padding: 2rem 1.2rem 4rem; }
h1 { font-size: 1.9rem; margin: 0 0 .6rem; }
p { font-size: 1.15rem; max-width: 48rem; }
.soft { color: var(--soft); }
table { border-collapse: collapse; font-size: 1.05rem; margin: 1rem 0 0; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: .45rem .7rem; border-bottom: 1px solid var(--line); }
th { color: var(--soft); font-weight: 400; }
td.n { font-weight: 700; }
tr.diff td { background: var(--chgbg); }
td.rec { font-weight: 700; }
tr.diff td.rec { color: var(--chg); }
.miss { color: var(--chg); }
section { margin-top: 3rem; border-top: 1px solid var(--line); padding-top: 1.4rem; }
h2 { font-size: 1.6rem; margin: 0 0 .3rem; }
.what { font-size: 1.2rem; max-width: 52rem; margin: .4rem 0 .6rem; }
.why { font-size: 1.1rem; color: var(--soft); max-width: 52rem; margin: 0 0 1.4rem; }
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
     "<title>Zaril's chat: the disc now and what I'd recommend</title>", f'<style>{css}</style></head><body><main>',
     "<h1>Zaril's chat: the disc now and what I'd recommend</h1>",
     '<p>The fix on the current disc (adc20ddd, the one that passed the suite) changes blocks 6, 8, 9, 10, 11 '
     'and 13. Going back over it against the Japanese, I’d keep 6, 9 and 10, put 8 and 11 back the way the '
     'game shipped them, and in 13 keep the new topic line but give Zaril his own line back. That leaves three '
     'topic lines changed (blocks 6, 9 and 13) and one swap of Fritillaria’s lines between blocks 9 and 10. '
     'No other line moves.</p>',
     '<p>The evidence I should have weighed more heavily the first time: Zaril used to be in Fontana’s party and '
     'Gaura in Balbo’s, and nearly all of their chat lines here are word-for-word copies of their lines in those '
     'parties’ chat tables. Those tables show which topic the writers gave each line. Where a block’s Zaril '
     'and Gaura lines both come from the same topic, that topic is very likely what the writers meant. '
     'Fritillaria’s lines are new to this table, so his can only be judged by reading.</p>',
     '<table><tr><th>Block</th><th>Topic in the original</th><th>Zaril’s line, in Fontana’s table</th>'
     '<th>Gaura’s line, in Balbo’s table</th><th>On the disc now</th><th>Recommended</th></tr>']
for b, orig, z, g, now, rec in SUMMARY:
    diff = rec.startswith('back') or rec.startswith('keep the topic')
    same = lambda t: t.split(' (')[0].replace('about themselves', 'something personal')
    zc = ' class="miss"' if same(z) != same(orig) and not z.startswith('(') else ''
    gc = ' class="miss"' if same(g) != same(orig) and not g.startswith('(') else ''
    H.append(f'<tr class="{"diff" if diff else ""}"><td class="n">{b}</td><td>{E(orig)}</td><td{zc}>{E(z)}</td>'
             f'<td{gc}>{E(g)}</td><td>{E(now)}</td><td class="rec">{E(rec)}</td></tr>')
H.append('</table>')
H.append('<p class="soft">Gold in the source columns marks a line whose topic in the other party’s table differs '
         'from the topic the original game shows it under. “Something personal” and “about '
         'themselves” are used interchangeably in all the tables, so a difference between those two isn’t '
         'marked. Blocks 6 and 9 are the clear ones: both lines come from “new information” '
         'and the game showed “told them”. Block 13 is split.</p>')
H.append('<p class="soft">Below, the three blocks where my recommendation differs from the disc. Left: the disc as '
         'built, captured in the emulator. Right: the same disc with the recommended table laid into memory. '
         'Whatever differs from the left is marked in gold. The right column for blocks 8 and 11 is exactly what '
         'the game played before the fix.</p>')

for b, title, what, why in SECTIONS:
    data = [column('now', b), column('rec', b)]
    H.append(f'<section id="b{b}"><h2>{E(title)}</h2><p class="what">{E(what)}</p><p class="why">{E(why)}</p>'
             '<div class="grid"><div class="head">On the disc now</div><div class="head">Recommended</div>')
    for k, ((bn, btxt), _) in enumerate(data):
        chg = ' changed' if k and bn != data[0][0][0] else ''
        H.append(f'<div class="topic{chg}"><span class="lab">Topic line on the bottom bar (5:{bn})</span>{E(btxt)}</div>')
    for who in SPEAKERS:
        for k, (_, rows) in enumerate(data):
            refs = [n for n, _ in rows.get(who, [])]
            chg = k and refs != [n for n, _ in data[0][1].get(who, [])]
            H.append('<div class="cell">')
            for n, figs in rows.get(who, []):
                for f, lines in figs:
                    H.append(f'<figure><img alt="{who}, NPC_MES5 {n}" src="data:image/png;base64,{b64(f)}">'
                             f'<figcaption class="{"changed" if chg else ""}"><div class="box">{E(chr(10).join(lines))}</div>'
                             f'<div class="ref">{who}, NPC_MES5 {n}</div>'
                             + ('<div class="tag">Changed from the left</div>' if chg else '') +
                             '</figcaption></figure>')
            H.append('</div>')
    H.append('</div></section>')
H.append('</main></body></html>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(H))
print('wrote', OUT)
