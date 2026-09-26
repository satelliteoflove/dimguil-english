#!/usr/bin/env python3
"""Build a self-contained HTML review page: screenshots plus the strings under review.

    reviewpage.py OUT.html TITLE --shots A.png B.png ... --strings FILE:RANGES ...

FILE is a translation file name (SISETU.OBJ), RANGES a comma list of indices or
ranges in its first section, or SECTION:INDEX pairs ("0:0-15"). Each string is shown
in English with the Japanese beside it, so the page quotes Japanese: write it under
rips/review/ (ignored), never into the repo.
"""
import base64, html, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TOK = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)


def load(path):
    src = open(path, encoding='utf-8').read()
    return json.loads(TOK.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else '', src))


def indices(spec):
    for part in spec.split(','):
        sec, _, rng = part.rpartition(':') if part.count(':') else ('', '', part)
        a, _, b = rng.partition('-')
        for i in range(int(a), int(b or a) + 1):
            yield int(sec or 0), i


def main():
    out, title = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    shots = args[args.index('--shots') + 1:args.index('--strings')]
    specs = args[args.index('--strings') + 1:]

    imgs = ''.join(
        f'<figure><img src="data:image/png;base64,{base64.b64encode(open(p, "rb").read()).decode()}">'
        f'<figcaption>{html.escape(os.path.basename(p))}</figcaption></figure>' for p in shots)

    rows = []
    for spec in specs:
        name, _, rng = spec.partition(':')
        tr = load(os.path.join(ROOT, f'translations/{name}.json'))['sections']
        jp = {s['firstHeaderAddress']: s for s in load(os.path.join(ROOT, f'rips/stage/out/dumps/{name}.json'))['sections']}
        for sec, i in indices(rng):
            s = tr[sec]
            en = s['strings'][i].get('translation') or ''
            src = jp[s['firstHeaderAddress']]['strings'][i]['source']
            ref = f'{name} {i}' if sec == 0 else f'{name} {sec}:{i}'
            fmt = lambda t: html.escape(t).replace('\\n', '<br>').replace('\n', '<br>').replace('\r', '')
            rows.append(f'<tr><td class="ref">{ref}</td><td>{fmt(en)}</td><td class="jp">{fmt(src)}</td></tr>')

    page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{margin:0;padding:2rem 3rem;background:#16161a;color:#e8e4da;font:15px/1.5 "Iowan Old Style",Palatino,Georgia,serif}}
h1{{font-weight:normal;letter-spacing:.02em;margin:0 0 .3rem}} .sub{{color:#9a958a;margin:0 0 2rem}}
.shots{{display:grid;grid-template-columns:repeat(auto-fill,minmax(480px,1fr));gap:1.2rem;margin-bottom:2.5rem}}
figure{{margin:0}} img{{width:100%;image-rendering:pixelated;border:1px solid #33322e}}
figcaption{{color:#77736a;font-size:12px;font-family:ui-monospace,monospace}}
table{{border-collapse:collapse;width:100%}} td{{border-top:1px solid #2c2b27;padding:.35rem .6rem;vertical-align:top}}
.ref{{color:#77736a;font:12px ui-monospace,monospace;white-space:nowrap}} .jp{{color:#a9a394;font-family:"Noto Serif CJK JP",serif}}
</style></head><body>
<h1>{html.escape(title)}</h1><p class="sub">Screens from the current build, then every string in this group.</p>
<div class="shots">{imgs}</div>
<table>{''.join(rows)}</table>
</body></html>'''
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(page)
    print(out)


if __name__ == '__main__':
    main()
