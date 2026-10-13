#!/usr/bin/env python3
"""The T5 report: one self-contained HTML file from t5check findings.

    python3 scripts/harness/t5report.py --out rips/harness/t5/report.html \
        --set "Chapter 1 runs" t5/runs/findings.jsonl t5/runs/v0 ... \
        --set "Event sweep" t5/events/findings.jsonl t5/events/p0 ... \
        --bad t5/bad/results.json --triage rips/harness/t5/triage.json

Findings are grouped by what they say (check, kind, text), one shot per group with the
box marked. Each group is classed by the first triage rule that matches it (check, a
regex over "what | detail | string") as real issue, false alarm or needs a look;
unmatched groups are "needs a look". Allowed findings (t5check.ALLOW) are listed apart.
Passing screens are counted per overlay and per string file.
"""
import argparse, base64, collections, html, io, json, os, re, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from harness.screens import XOFF

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUTR = os.path.join(ROOT, 'rips/harness')
SHOW = 4             # shots per family of findings that share a triage note
CLASSES = [('real', 'Real issues'), ('look', 'Needs a look'), ('false', 'False alarms')]


def norm(f):
    """The group a finding belongs to: counts and frame-dependent numbers folded."""
    what = re.sub(r'^\d+ ', 'N ', f['what'])
    what = re.sub(r'[-+]?\d+(\.\d+)? px', 'X px', what)
    return (f['check'], what, f.get('detail', ''), f.get('string', ''))


def shot_uri(run, shot, box, scale=1):
    p = os.path.join(OUTR, run, 'shots', '%s.png' % shot)
    if not shot or not os.path.exists(p):
        return None
    im = Image.open(p).convert('RGB')
    if box:
        d = ImageDraw.Draw(im)
        d.rectangle([box[0] + XOFF - 2, box[1] - 2, box[2] + XOFF + 1, box[3] + 1], outline=(255, 40, 40))
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    b = io.BytesIO()
    im.save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def classify(key, rules):
    check, what, detail, sid = key
    hay = '%s | %s | %s' % (what, detail, sid)
    for r in rules:
        if r['check'] == check and re.search(r['match'], hay):
            return r['class'], r['note']
    return 'look', ''


def passing(dirs, flagged):
    """Screens with no finding, per overlay and per string file of what they showed."""
    by_ovl, by_file = collections.Counter(), collections.Counter()
    total = 0
    for d in dirs:
        for line in open(os.path.join(OUTR, d, 'screens.jsonl')):
            r = json.loads(line)
            if 'sprites' not in r:
                continue
            total += 1
            if (d, r['n']) in flagged:
                continue
            by_ovl[r['where']['ovl']] += 1
            files = {(m.get('file') or 'unnamed').split('.')[0] for m in r.get('msgs') or [] if m.get('fresh')}
            for f in files or {'(no new string)'}:
                by_file[f] += 1
    return total, by_ovl, by_file


CSS = """
body{font:15px/1.45 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif;margin:0;background:#f4f2ee;color:#222}
main{max-width:1180px;margin:0 auto;padding:28px 32px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:20px;margin:36px 0 10px;border-bottom:2px solid #ccc;padding-bottom:4px}
h3{font-size:16px;margin:22px 0 8px}
.sub{color:#666;margin-bottom:18px}
table{border-collapse:collapse;margin:8px 0 16px;background:#fff}
td,th{border:1px solid #ddd;padding:4px 10px;text-align:left;vertical-align:top}
th{background:#ece9e2;font-weight:600}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.grp{background:#fff;border:1px solid #ddd;border-radius:6px;margin:14px 0;padding:12px 14px;display:flex;gap:16px}
.grp img{image-rendering:pixelated;width:700px;height:auto;border:1px solid #999;flex:none}
.grp .t{flex:1;min-width:0}
.tag{display:inline-block;font-size:12px;padding:1px 7px;border-radius:9px;background:#ddd;margin-right:6px}
.real .tag.c{background:#e8b4b4}.look .tag.c{background:#ecd9a0}.false .tag.c{background:#c4d8c0}
code,.mono{font-family:'DejaVu Sans Mono',Consolas,monospace;font-size:13px;background:#f1efe9;padding:1px 4px;border-radius:3px;word-break:break-word}
.note{margin-top:6px;color:#333}.meta{color:#777;font-size:13px;margin-top:6px}
.fam{margin:18px 0 6px;padding:8px 12px;border-left:4px solid #bbb;background:#fbfaf7}
.real.fam{border-color:#c77}.look.fam{border-color:#cb5}.false.fam{border-color:#7a7}
table.rest td{font-size:13px}
.ok{color:#2d6a2d;font-weight:600}.bad{color:#a33;font-weight:600}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--set', nargs='+', action='append', default=[],
                    metavar='NAME FINDINGS DIR', help='a named set: its findings file and capture dirs')
    ap.add_argument('--bad', help='t5bad results.json')
    ap.add_argument('--triage', help='rules: [{check, match, class, note}]')
    ap.add_argument('--stats', help='JSON with coverage stats per set name')
    ap.add_argument('--title', default='T5: text and screen checks')
    ap.add_argument('--intro', default='')
    a = ap.parse_args()
    rules = json.load(open(a.triage)) if a.triage and os.path.exists(a.triage) else []
    stats = json.load(open(a.stats)) if a.stats and os.path.exists(a.stats) else {}
    H = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>%s</title><style>%s</style></head><body><main>'
         % (html.escape(a.title), CSS), '<h1>%s</h1><div class="sub">%s</div>' % (html.escape(a.title), a.intro)]
    sets = []
    for s in a.set:
        name, fpath, dirs = s[0], s[1], s[2:]
        fs = [json.loads(l) for l in open(os.path.join(OUTR, fpath) if not os.path.isabs(fpath) else fpath)]
        groups = collections.OrderedDict()
        for f in fs:
            groups.setdefault(norm(f), []).append(f)
        flagged = {(f['run'], f['n']) for f in fs if not f.get('allowed')}
        total, by_ovl, by_file = passing(dirs, flagged)
        sets.append((name, fs, groups, total, by_ovl, by_file, dirs))
    # summary
    H.append('<h2>Summary</h2><table><tr><th>Set</th><th>Screens</th><th>Passing</th>'
             '<th>Real issues</th><th>Needs a look</th><th>False alarms</th><th>Allowed</th></tr>')
    for name, fs, groups, total, by_ovl, by_file, dirs in sets:
        cnt = collections.Counter()
        for k, g in groups.items():
            if all(f.get('allowed') for f in g):
                cnt['allowed'] += 1
            else:
                cnt[classify(k, rules)[0]] += 1
        H.append('<tr><td>%s</td><td class="n">%d</td><td class="n">%d</td><td class="n">%d</td><td class="n">%d</td>'
                 '<td class="n">%d</td><td class="n">%d</td></tr>' % (
                     html.escape(name), total, sum(by_ovl.values()), cnt['real'], cnt['look'], cnt['false'],
                     cnt['allowed']))
    H.append('</table><p>Issue counts are distinct findings (the same text flagged on many screens counts once); '
             'each lists how many screens it was on.</p>')
    if stats:
        H.append('<h3>What the checks looked at</h3><table><tr><th>Set</th>%s</tr>' %
                 ''.join('<th>%s</th>' % html.escape(k) for k in next(iter(stats.values()))))
        for name, st in stats.items():
            H.append('<tr><td>%s</td>%s</tr>' % (html.escape(name), ''.join('<td class="n">%s</td>' % v for v in st.values())))
        H.append('</table>')
    if a.bad and os.path.exists(a.bad):
        res = json.load(open(a.bad))
        caught = sum(1 for r in res.values() if r['caught'])
        H.append('<h2>Known-bad set</h2><p>Each case puts a fixed bug back (a RAM write, for testing only) and '
                 'runs the same screen with the fix and without. A case is caught when the bad run has a finding '
                 'of the expected kind that the fixed run doesn\'t. Caught: <b>%d of %d</b>. Findings the fixed '
                 'runs do have are ones the two share: the centering issue below, the menu cursor frame, the '
                 'allowed spaces in the return prompt. The two old-disc cases have no fixed run; the current '
                 'disc\'s runs are their comparison. These cases are in the ratchet (regress.py, kind '
                 '<code>screen</code>).</p>' % (caught, len(res)))
        H.append('<table><tr><th>Case</th><th>What was put back</th><th>Fix</th><th>Expected</th><th>Bad variant flagged</th>'
                 '<th>Fixed variant flagged</th><th></th></tr>')
        for k, r in res.items():
            H.append('<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td></tr>' % (
                html.escape(k), html.escape(r['what']), html.escape(r['fix']), ', '.join(r['expect']),
                ', '.join(r['bad_checks']) or '-', ', '.join(r['fixed_checks']) or '-',
                'ok' if r['caught'] else 'bad', 'caught' if r['caught'] else 'missed'))
        H.append('</table>')
        # the first catching finding of each case, with its shot
        base = os.path.dirname(a.bad)
        for k, r in res.items():
            fp = os.path.join(base, k + '_bad', 'findings.jsonl')
            hits = r.get('hits') or []
            if not os.path.exists(fp) or not hits:
                continue
            fs = [json.loads(l) for l in open(fp)]
            f = next((x for x in fs if x['check'] + ': ' + x['what'] + ' | ' + str(x.get('detail'))[:60] == hits[0]), None)
            if not f:
                continue
            uri = shot_uri(f['run'], f.get('shot'), f.get('box'))
            H.append('<div class="grp real">%s<div class="t"><span class="tag">%s</span><b>%s</b><div style="margin-top:6px">'
                     '<code>%s</code></div><div class="note">%s</div></div></div>' % (
                         '<img src="%s">' % uri if uri else '', html.escape(k), html.escape(f['what']),
                         html.escape(f.get('detail', '')), html.escape(r['what'])))
    for name, fs, groups, total, by_ovl, by_file, dirs in sets:
        H.append('<h2>%s</h2>' % html.escape(name))
        for cls, title in CLASSES:
            items = [(k, g) for k, g in groups.items()
                     if not all(f.get('allowed') for f in g) and classify(k, rules)[0] == cls]
            if not items:
                continue
            H.append('<h3>%s (%d)</h3>' % (title, len(items)))
            # findings that share a triage note are one family: the note once, shots for
            # the first SHOW of them, the rest as rows
            fams = collections.OrderedDict()
            for k, g in items:
                fams.setdefault(classify(k, rules)[1], []).append((k, g))
            for note, members in fams.items():
                if note:
                    H.append('<div class="fam %s"><b>%d finding(s), %d screen(s).</b> %s</div>' % (
                        cls, len(members), sum(len(g) for k, g in members), html.escape(note)))
                for i, (k, g) in enumerate(members):
                    f = next((x for x in g if x.get('stable') and x.get('shot')), g[0])
                    runs = sorted({x['run'].split('/')[-1] for x in g})
                    where = '%d screen(s) in %s; first at frame %d (%s, %s)' % (
                        len(g), ', '.join(runs[:6]) + (' ...' if len(runs) > 6 else ''), f['frame'], f['ovl'], f.get('why'))
                    if i >= SHOW:
                        if i == SHOW:
                            H.append('<table class="rest"><tr><th>Also</th><th>What</th><th>Where</th></tr>')
                        H.append('<tr><td><code>%s</code></td><td>%s</td><td>%s</td></tr>' % (
                            html.escape(f.get('detail', '')), html.escape(f['what']), where))
                        if i == len(members) - 1:
                            H.append('</table>')
                        continue
                    uri = shot_uri(f['run'], f.get('shot'), f.get('box'))
                    H.append('<div class="grp %s">%s<div class="t"><span class="tag c">%s</span><span class="tag">%s</span>'
                             '<b>%s</b><div style="margin-top:6px">%s</div>%s<div class="meta">%s</div></div></div>' % (
                                 cls, '<img src="%s">' % uri if uri else '', title.lower().rstrip('s'), k[0],
                                 html.escape(f['what']), '<code>%s</code>' % html.escape(f.get('detail', '')) if f.get('detail') else '',
                                 '<div class="meta">string: %s</div>' % html.escape(f['string']) if f.get('string') else '',
                                 where))
        allowed = [(k, g) for k, g in groups.items() if all(x.get('allowed') for x in g)]
        if allowed:
            H.append('<h3>Allowed (%d)</h3><ul>' % len(allowed))
            for k, g in allowed:
                H.append('<li><code>%s</code> %s: %s (%d screens)</li>' % (
                    html.escape(k[2]), html.escape(k[1]), html.escape(g[0]['allowed']), len(g)))
            H.append('</ul>')
        H.append('<h3>Passing screens</h3><p>%d of %d screens had no finding.</p><table><tr><th>Section (overlay)</th><th>Screens</th></tr>%s</table>'
                 % (sum(by_ovl.values()), total, ''.join('<tr><td>%s</td><td class="n">%d</td></tr>' % (html.escape(k), v)
                                                         for k, v in sorted(by_ovl.items()))))
        H.append('<table><tr><th>String file (new text on the screen)</th><th>Screens</th></tr>%s</table>'
                 % ''.join('<tr><td>%s</td><td class="n">%d</td></tr>' % (html.escape(k), v) for k, v in sorted(by_file.items())))
    H.append('</main></body></html>')
    open(a.out, 'w').write('\n'.join(H))
    print('wrote', a.out, os.path.getsize(a.out) // 1024, 'KB')


if __name__ == '__main__':
    main()
