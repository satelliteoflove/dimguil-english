"""Which review-tool scene a line still to review sits in: {ref: scene id}, for the play plan.
A line counts for the first unfinished scene that shows it in full (not folded away as
read elsewhere); a line folded into a pending voice scene counts for that voice scene."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import textstatus

REVIEW = os.path.join(ROOT, 'rips/review')


def where():
    srv = textstatus.review_server()
    out, titles = {}, {}
    for name in sorted(os.listdir(os.path.join(REVIEW, 'scenes'))):
        if not name.endswith('.json'):
            continue
        sid, dp = name[:-5], os.path.join(REVIEW, 'decisions', name)
        dec = json.load(open(dp, encoding='utf-8')) if os.path.exists(dp) else None
        if dec and not dec.get('partial'):
            continue
        sc = srv.scene(sid)
        titles[sid] = sc['title']
        done = {l['ref'] for rec in ([dec, *dec.get('earlier', [])] if dec else []) for l in rec.get('lines', [])}
        for l in sc['lines']:
            if l['ref'] in done:
                continue
            d = l.get('done_in')
            if d is None or d.get('here'):
                out.setdefault(l['ref'], sid)
            elif d.get('pending'):
                out.setdefault(l['ref'], d['scene'])
    for sid in set(out.values()) - set(titles):
        titles[sid] = json.load(open(os.path.join(REVIEW, 'scenes', sid + '.json'), encoding='utf-8'))['title']
    return out, titles
