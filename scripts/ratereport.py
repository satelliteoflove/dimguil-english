#!/usr/bin/env python3
"""ratereport.py RATETEST_DIR
Build RATETEST_DIR/recording-formats.html from ratebench.py's bench.json, the samples
and their encodes. Images are embedded, so the page works offline from file://."""
import base64, html, io, json, os, subprocess, sys
from PIL import Image

D = sys.argv[1]
R = json.load(open(os.path.join(D, 'bench.json')))
S = R['segments']
LABEL = {k: l for k, l, _ in R['video']}
MIX = {'dungeon': 0.5, 'battle': 0.2, 'town': 0.3}   # assumed share of an hour of play

def seg_rate(key, seg, field='gb_per_hour'):
    if seg == 'dungeon':
        return (S['jungle']['video'][key][field] + S['training']['video'][key][field]) / 2
    return S[seg]['video'][key][field]

def hour(key):
    return sum(seg_rate(key, s) * w for s, w in MIX.items())

AUDIO = {k: sum(S[s]['audio'][k]['gb_per_hour'] for s in S) / len(S) for k, _ in R['audio']}

def uri(im, fmt='PNG'):
    b = io.BytesIO(); im.save(b, fmt, **({'quality': 88} if fmt == 'JPEG' else {}))
    return f"data:image/{fmt.lower()};base64,{base64.b64encode(b.getvalue()).decode()}"

def frame(path, n):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'select=eq(n\\,{n})', '-vsync', '0',
                          '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    return Image.frombytes('RGB', (320, 240), out)

# --- sample thumbnails: four frames per segment ---
THUMBS = {}
for s in ('town', 'jungle', 'battle', 'training'):
    src = os.path.join(D, 'samples', s + '.mkv')
    ims = [frame(src, int(t * 59.826)) for t in (20, 50, 80, 110)]
    strip = Image.new('RGB', (320 * 4 + 6 * 3, 240), (20, 22, 28))
    for i, im in enumerate(ims):
        strip.paste(im, (i * 326, 0))
    THUMBS[s] = uri(strip)

# --- lossy close-ups ---
CMP = ['x264rgb-veryfast', 'x264rgb-crf8', 'x264rgb-crf12', 'x264rgb-crf16', 'x264rgb-crf20', 'x264-420-crf18']
CROPS = [('Dialogue text', 'battle', 6581, (8, 14, 120, 46)),
         ('Portrait and wall', 'battle', 6581, (20, 50, 100, 110)),
         ('Training maze wall', 'training', 4786, (120, 60, 200, 120))]
SCALE = 5
crop_html = []
for title, seg, n, box in CROPS:
    cells = []
    for key in CMP:
        im = frame(os.path.join(D, 'encodes', f'{seg}.{key}.mkv'), n).crop(box)
        im = im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)
        name = 'Lossless' if key == 'x264rgb-veryfast' else LABEL[key].replace('H.264 RGB, ', '')
        cells.append(f'<figure><img src="{uri(im)}" width="{im.width}" height="{im.height}" alt="{html.escape(title)}, {html.escape(name)}">'
                     f'<figcaption>{html.escape(name)}</figcaption></figure>')
    crop_html.append(f'<section class="crops"><h3>{html.escape(title)}</h3><div class="crop-grid">{"".join(cells)}</div></section>')

# --- tables ---
def gb(x): return f'{x:.2f}'
def fps_x(key):
    worst = min(S[s]['video'][key]['encode_fps'] for s in S)
    return f'{worst / 59.826:.1f}×'

rows = []
top = max(hour(k) for k, _, _ in R['video'] if k != 'ffv1')
CURRENT = 'x264rgb-veryfast'
for key, label, lossless in R['video']:
    h = hour(key)
    if key == 'ffv1':
        bar = '<span class="off">off the scale</span>'
    else:
        bar = f'<span class="bar" style="width:{h / top * 100:.1f}%"></span>'
    q = 'exact' if lossless else f"{min(S[s]['video'][key]['psnr'] for s in S):.0f}–{max(S[s]['video'][key]['psnr'] for s in S):.0f} dB"
    cls = ' class="current"' if key == CURRENT else ''
    rows.append(f'<tr{cls}><th scope="row">{html.escape(label)}</th>'
                f'<td>{gb(seg_rate(key, "town"))}</td><td>{gb(seg_rate(key, "battle"))}</td>'
                f'<td>{gb(S["jungle"]["video"][key]["gb_per_hour"])}</td><td>{gb(S["training"]["video"][key]["gb_per_hour"])}</td>'
                f'<td class="mix">{gb(h)}</td><td class="barcell">{bar}</td><td>{fps_x(key)}</td><td>{q}</td></tr>')

lossy_rows = []
for key in ['x264rgb-crf4', 'x264rgb-crf8', 'x264rgb-crf12', 'x264rgb-crf16', 'x264rgb-crf20', 'x264-420-crf18']:
    v = [S[s]['video'][key] for s in ('jungle', 'training')]
    lossy_rows.append(f'<tr><th scope="row">{html.escape(LABEL[key])}</th><td>{gb(hour(key))}</td>'
                      f'<td>{sum(x["psnr"] for x in v) / 2:.1f} dB</td><td>{sum(x["pct_changed"] for x in v) / 2:.0f}%</td>'
                      f'<td>{sum(x["pct_over8"] for x in v) / 2:.1f}%</td><td>{max(x["max_err"] for x in v)}</td></tr>')

audio_rows = ''.join(f'<tr><th scope="row">{html.escape(l)}</th>'
                     + ''.join(f'<td>{S[s]["audio"][k]["kbps"]:.0f}</td>' for s in ('town', 'battle', 'jungle', 'training'))
                     + f'<td class="mix">{AUDIO[k]:.2f}</td></tr>' for k, l in R['audio'])

now_total = hour(CURRENT) + AUDIO['flac']
slow_total = hour('x264rgb-veryslow') + AUDIO['flac']

page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dimguil play-through: recording size and format</title>
<style>
:root {{
  --stone: #2b2c30; --stone-lit: #3a3b40; --window: #151925; --rule: #6f7891;
  --ink: #ebe6da; --ink-dim: #b9b4a8; --gold: #d8b766; --cursor: #d04a35;
}}
* {{ box-sizing: border-box; }}
html {{ font-size: 20px; }}
body {{ margin: 0; background: var(--stone); color: var(--ink);
  font-family: "Palatino Linotype", Palatino, "URW Palladio L", "P052", "Book Antiqua", serif;
  line-height: 1.55; font-variant-numeric: lining-nums tabular-nums; }}
main {{ max-width: 64rem; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
.prose {{ max-width: 38rem; }}
h1 {{ font-size: 2.1rem; line-height: 1.2; font-weight: normal; margin: 0 0 0.6rem; max-width: 30rem; }}
h2 {{ font-size: 1.4rem; font-weight: normal; margin: 3rem 0 0.8rem; color: var(--gold); }}
h3 {{ font-size: 1.05rem; font-weight: bold; margin: 1.6rem 0 0.6rem; }}
p {{ margin: 0 0 1rem; }}
.lede {{ font-size: 1.15rem; color: var(--ink); }}
.window {{ background: var(--window); border: 1px solid var(--rule); outline: 3px solid var(--stone-lit);
  padding: 1.1rem 1.4rem; margin: 1.5rem 0; }}
.window p:last-child {{ margin-bottom: 0; }}
.window strong {{ color: var(--gold); font-weight: normal; }}
.seg {{ margin: 1.4rem 0; }}
.seg img {{ width: 100%; height: auto; display: block; image-rendering: pixelated; border: 1px solid var(--rule); }}
.seg p {{ margin: 0.4rem 0 0; color: var(--ink-dim); max-width: 44rem; }}
.seg b {{ color: var(--ink); font-weight: bold; }}
.tablewrap {{ overflow-x: auto; margin: 1rem 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
th, td {{ padding: 0.35rem 0.6rem; text-align: right; border-bottom: 1px solid #44464e; white-space: nowrap; }}
thead th {{ color: var(--ink-dim); font-weight: normal; vertical-align: bottom; white-space: normal; }}
tbody th {{ text-align: left; font-weight: normal; white-space: normal; min-width: 13rem; }}
td.mix {{ color: var(--gold); }}
tr.current th::before {{ content: "▶ "; color: var(--cursor); }}
tr.current {{ background: #33343a; }}
td.barcell {{ width: 9rem; min-width: 9rem; text-align: left; }}
.bar {{ display: inline-block; height: 0.7rem; background: var(--gold); vertical-align: middle; }}
.off {{ color: var(--ink-dim); font-style: italic; font-size: 0.8rem; }}
.crop-grid {{ display: flex; flex-wrap: wrap; gap: 1rem 1.2rem; }}
figure {{ margin: 0; }}
figure img {{ display: block; image-rendering: pixelated; border: 1px solid var(--rule); max-width: 100%; height: auto; }}
figcaption {{ font-size: 0.85rem; color: var(--ink-dim); margin-top: 0.25rem; }}
code {{ font-family: "DejaVu Sans Mono", monospace; font-size: 0.8rem; background: var(--window); padding: 0.05rem 0.3rem; }}
pre {{ background: var(--window); border: 1px solid var(--rule); padding: 0.8rem 1rem; overflow-x: auto; font-size: 0.8rem; }}
pre code {{ background: none; padding: 0; }}
ul {{ padding-left: 1.2rem; }} li {{ margin-bottom: 0.4rem; }}
.note {{ color: var(--ink-dim); font-size: 0.9rem; }}
</style>
</head>
<body>
<main>
<h1>Recording Dimguil: how much disk an hour of play really takes</h1>
<p class="lede prose">Eight minutes of scripted play, encoded every way that seemed worth considering. The 3.5&nbsp;GB an hour from the first test came from the PlayStation logo and title animation, which change nearly every pixel every frame. Real play comes in lower, but the 3D mazes are genuinely expensive.</p>

<div class="window prose">
<p>With the current setting (lossless, x264 <i>veryfast</i>), an hour mixing maze, battle and town comes to about <strong>{now_total:.1f}&nbsp;GB</strong>, sound included. Re-compressing each finished session with x264 <i>veryslow</i> gives back exactly the same pixels in about <strong>{slow_total:.1f}&nbsp;GB</strong>. Lossy recording only beats that once it starts visibly changing the dithered maze textures, so I'd keep recording lossless and shrink it afterward.</p>
</div>

<h2>What was recorded</h2>
<div class="prose">
<p>The headless emulator harness played four two-minute segments from the test states, with the same 320×240 picture RetroArch records. The input was scripted and keeps the party moving almost all the time, so these figures run higher than real play, where you stop to think and read.</p>
</div>
<div class="seg"><img src="{THUMBS['town']}" alt="Town segment frames"><p><b>Town.</b> Moving between facilities, opening menus, a save screen. Mostly still pictures.</p></div>
<div class="seg"><img src="{THUMBS['jungle']}" alt="Jungle segment frames"><p><b>Jungle.</b> Walking and turning in the outdoor maze around the first door.</p></div>
<div class="seg"><img src="{THUMBS['battle']}" alt="Battle segment frames"><p><b>Battle.</b> A fight with Giant Mosquitoes, then walking, including Lychee's party encounter.</p></div>
<div class="seg"><img src="{THUMBS['training']}" alt="Training maze segment frames"><p><b>Training maze.</b> Stone corridors, constant stepping and turning.</p></div>

<h2>Size per hour of footage</h2>
<div class="prose">
<p>Video only, in GB per hour. The estimated hour assumes half maze walking (the average of the two maze segments), a fifth battles and the rest town and menus. Speed is how many times faster than real time the encoder ran on the hardest segment with two threads, which is what RetroArch gives it; anything under about 3× is risky to record live. Quality is the PSNR range across segments (higher is closer; above 45&nbsp;dB is hard to tell apart even zoomed).</p>
</div>
<div class="tablewrap"><table>
<thead><tr><th scope="col" style="text-align:left">Format</th><th scope="col">Town</th><th scope="col">Battle</th><th scope="col">Jungle</th><th scope="col">Training maze</th><th scope="col">Estimated hour</th><th scope="col"></th><th scope="col">Speed</th><th scope="col">Quality</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>
<div class="prose">
<p>The maze is where the space goes. Every step moves dithered textures across the whole screen, so even the best lossless encoder needs about 2&nbsp;GB an hour for it, while the town needs a quarter of a gigabyte. FFV1 compresses each frame on its own and can't use the fact that most of the picture repeats; it's listed only because it's the usual archival choice.</p>
</div>

<h2>What lossy recording costs</h2>
<div class="prose">
<p>Measured on the two maze segments, where lossy compression matters most. “Pixels changed” counts any difference at all; “more than 8” counts differences of more than 8 out of 255 in any color, roughly where a change becomes visible when blown up 8×.</p>
</div>
<div class="tablewrap"><table>
<thead><tr><th scope="col" style="text-align:left">Format</th><th scope="col">Estimated hour</th><th scope="col">PSNR</th><th scope="col">Pixels changed</th><th scope="col">More than 8</th><th scope="col">Worst pixel</th></tr></thead>
<tbody>{''.join(lossy_rows)}</tbody>
</table></div>
<div class="prose">
<p>CRF&nbsp;8 already costs about as much space as lossless <i>veryslow</i>, so it buys nothing. CRF&nbsp;12–16 is where lossy starts saving real space, and the close-ups below show what it does: text stays clean, but the dithered wall textures lose their fine pattern and get a little smeared. Ordinary 4:2:0 video is far smaller, but it stores color at half resolution, and its worst errors (up to 156 out of 255) sit on sharp color edges such as Lychee's red hood.</p>
</div>

<h2>Close-ups at 5×</h2>
<p class="prose note">The same frame from each encode, scaled with hard pixel edges. Lossless is the reference.</p>
{''.join(crop_html)}

<h2>Sound</h2>
<div class="prose"><p>In kbit/s per segment, and GB per hour on average. Dimguil's music keeps FLAC busier than the logo test suggested; it's about a seventh of a lossless hour. Opus at 192&nbsp;kbit/s would save about 0.2&nbsp;GB an hour, but FLAC can be cut and joined at any sample when a redo is spliced in, so it seems worth keeping.</p></div>
<div class="tablewrap"><table>
<thead><tr><th scope="col" style="text-align:left">Format</th><th scope="col">Town</th><th scope="col">Battle</th><th scope="col">Jungle</th><th scope="col">Training maze</th><th scope="col">GB per hour</th></tr></thead>
<tbody>{audio_rows}</tbody>
</table></div>

<h2>The suggestion</h2>
<div class="prose">
<ul>
<li>Keep recording lossless with <i>veryfast</i>. It runs about {min(S[s]['video']['x264rgb-veryfast']['encode_fps'] for s in S) / 59.826:.0f}× faster than real time on the hardest footage, so it won't drop frames under load.</li>
<li>After each session, re-encode to <i>veryslow</i> lossless. Every pixel is verified identical, and it saves 35–40% on maze footage. On this machine it runs about {min(S[s]['video']['x264rgb-veryslow']['encode_fps'] for s in S) / 59.826:.1f}× real time with two threads, faster with all of them.</li>
<li>A 50-hour play-through would then need roughly {slow_total * 50:.0f}&nbsp;GB, against 710&nbsp;GB free on the drive.</li>
</ul>
</div>

<h2>Files and method</h2>
<div class="prose">
<p>Everything is in <code>playthrough/ratetest/</code>: the lossless samples with their sound and starting states in <code>samples/</code>, every encode in <code>encodes/</code>, and the measurements in <code>bench.json</code>. To watch an encode the way it will be scaled, with hard pixel edges:</p>
</div>
<pre><code>mpv --scale=nearest --fs encodes/training.x264rgb-crf16.mkv</code></pre>
<div class="prose">
<p class="note">Samples were made with <code>scripts/ratesample.py</code>, measured with <code>scripts/ratebench.py</code>, and this page was built by <code>scripts/ratereport.py</code>. Quality figures compare every tenth frame against the lossless original. The harness runs the standard Beetle PSX core with its software renderer, which is the same renderer the RetroArch setup uses; the RetroArch test recording had the same 320×240 RGB format.</p>
</div>
</main>
</body>
</html>
'''
open(os.path.join(D, 'recording-formats.html'), 'w').write(page)
print('wrote', os.path.join(D, 'recording-formats.html'))
