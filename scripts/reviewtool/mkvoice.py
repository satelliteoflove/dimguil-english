#!/usr/bin/env python3
"""Voice scenes for the review tool: every line one character speaks, across all five NPC
files, in one place, so Chris settles the character's voice once (as Gaura's scene did,
2026-10-20). Lines he has already read are included too; the tool shows them collapsed,
as context for the voice. The topic read-throughs then show these lines collapsed as
"You'll read this in ...", and once the voice scene is applied, as read.

    rips/venv/bin/python scripts/reviewtool/mkvoice.py list PERSON      the lines, as JSON
    rips/venv/bin/python scripts/reviewtool/mkvoice.py build SPEC.json  write the scenes

PERSON is a cast.json id (guy, alstron, ...). list gives, per line: ref, speaker tag,
read (Chris has read it), context (the NPC map's topic), plays (when it plays), jp,
current, copies, lessons (docs/review-lessons.md checks it trips) and auto_gloss (what
the tool would show under the Japanese without a hand gloss, word=first sense).

SPEC is {person, title, summary, notes?, lines: [{ref, context?, literal, faithful?,
why?, notes?, gloss?, entries?, confidence?}]}, every line from list in the order to
show them. faithful is the whole proposed box (speaker line included), or null to keep
the current line; why says what the proposal changes and why. The scene fields are the
review tool's (server.py's docstring). build checks every proposal fits the box and
every hand gloss matches its Japanese, and writes rips/review/scenes/voice-PERSON-K.json,
split so each part has at most MAX lines still to read. It refuses to rewrite a part
that already has a decision.
"""
import importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MAX = 25

_argv, sys.argv = sys.argv, [sys.argv[0]]
spec = importlib.util.spec_from_file_location('reviewserver', os.path.join(HERE, 'server.py'))
srv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(srv)
sys.argv = _argv
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import lessons, textstatus  # noqa: E402


def cast():
    return json.load(open(os.path.join(HERE, 'cast.json'), encoding='utf-8'))


def lines_of(person):
    status = textstatus.table()
    hits = {}
    for h in lessons.hits(every=True):
        hits.setdefault(h['ref'], []).append(f"{h['lesson']} {h['what']}: {h['match']}")
    places = srv.map_places()
    out = []
    for n in srv.NPC_FILES:
        for i in range(len(srv.SOURCES[n])):
            ref = f'{n}:{i}'
            if srv.person(ref) != person:
                continue
            cur = srv.current(ref)
            g = srv.gloss(ref)
            auto = [' '.join(f"{w['jp']}={w.get('en', '')}" for w in pg if not w.get('punct')) for pg in g['pages'] or []]
            out.append({'ref': ref, 'tag': cur.split('\n', 1)[0],
                        'read': status(f'NPC_MES{n}.OBJ', i)[0] == 'reviewed',
                        'context': places.get(ref), 'plays': srv.auto_plays(ref),
                        'jp': srv.SOURCES[n][i], 'current': cur, 'copies': srv.copies_of(ref),
                        'lessons': hits.get(ref, []), 'auto_gloss': auto})
    return out


def build(path):
    sp = json.load(open(path, encoding='utf-8'))
    who = sp['person']
    people = {p['id']: p for p in cast()['people']}
    party = cast()['parties'][people[who]['party']]
    known = {x['ref']: x for x in lines_of(who)}
    errors = []
    for ln in sp['lines']:
        ref = ln['ref']
        if ref not in known:
            errors.append(f'{ref}: not a line {who} speaks')
            continue
        cur = known[ref]['current']
        if ln.get('faithful') and ln['faithful'] != cur:
            f = srv.fit(ref, ln['faithful'])
            if not f['ok']:
                errors.append(f"{ref}: doesn't fit: {'; '.join(f['hard'])}")
            if ln['faithful'].split('\n', 1)[0] != cur.split('\n', 1)[0]:
                errors.append(f'{ref}: the proposal changes the speaker line')
        if ln.get('gloss'):
            g = srv.gloss(ref, ln)
            if g['error']:
                errors.append(f"{ref}: {g['error']}")
    missing = [r for r in known if r not in {x['ref'] for x in sp['lines']}]
    if missing:
        errors.append(f"lines left out: {', '.join(missing)}")
    if errors:
        sys.exit('not written:\n  ' + '\n  '.join(errors))
    parts, cur_part, unread = [], [], 0
    for ln in sp['lines']:
        u = not known[ln['ref']]['read']
        if cur_part and u and unread >= MAX:
            parts.append(cur_part)
            cur_part, unread = [], 0
        cur_part.append(ln)
        unread += u
    if cur_part:
        parts.append(cur_part)
    for k, part in enumerate(parts, 1):
        sid = f'voice-{who}-{k}'
        if os.path.exists(os.path.join(srv.DECISIONS, f'{sid}.json')):
            sys.exit(f'{sid} has a decision; not rewriting it')
    old = [f for f in os.listdir(srv.SCENES) if f.startswith(f'voice-{who}-')]
    for f in old:
        os.remove(os.path.join(srv.SCENES, f))
    for k, part in enumerate(parts, 1):
        sid = f'voice-{who}-{k}'
        lines = []
        for ln in part:
            x = {key: v for key, v in ln.items() if v not in (None, '', [])}
            x.setdefault('context', known[ln['ref']]['context'] or '')
            if not ln.get('faithful'):
                x['faithful'] = known[ln['ref']]['current']
            x.setdefault('why', 'No change.')
            lines.append(x)
        scene = {'id': sid, 'kind': 'voice', 'file': party['file'], 'number': None, 'order': k,
                 'party': people[who]['party'],
                 'title': sp['title'] + (f' (part {k} of {len(parts)})' if len(parts) > 1 else ''),
                 'where': f"Every line {people[who]['name']} speaks, in all five NPC files. Lines you've "
                          "already read are shown collapsed, for the voice.",
                 'assembled': 'Lines play on their own.',
                 'summary': sp['summary'], 'notes': sp.get('notes', []) if k == 1 else [], 'lines': lines}
        json.dump(scene, open(os.path.join(srv.SCENES, f'{sid}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    props = sum(1 for ln in sp['lines'] if ln.get('faithful') and ln['faithful'] != known[ln['ref']]['current'])
    print(f"{who}: {len(sp['lines'])} lines ({sum(not x['read'] for x in known.values())} unread), "
          f'{props} proposals, {len(parts)} scene(s)')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == 'list':
        json.dump(lines_of(sys.argv[2]), sys.stdout, ensure_ascii=False, indent=1)
    elif len(sys.argv) == 3 and sys.argv[1] == 'build':
        build(sys.argv[2])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
