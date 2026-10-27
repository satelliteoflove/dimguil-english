#!/usr/bin/env python3
"""Where each game string stands in review, for the play-through monitor (playwatch.py).

    textstatus.py              counts per file and status
    textstatus.py FILE INDEX   one string's status and why
    textstatus.py --json OUT   the whole table, for looking at

Statuses, and whether the monitor pauses on them:
  reviewed     reviewed with Chris (the event script, Guy's party, finished NPC scenes)
  ai-reviewed  read against the Japanese by the NPC reviewers and not flagged, so never
               reviewed with Chris                                   -> pause
  open         in an NPC scene still to review with Chris            -> pause
  check        reviewed, but its wording depends on what the player
               sees; confirm in play                                 -> pause
  first-pass   menus, castle and battle text: translated fresh in
               September, screen-checked, no line-by-line second look

The NPC scenes come from the items under "Remaining scenes" in docs/npc-review.md:
unticked ones are open, ticked ones reviewed, so ticking a scene there is what marks it
reviewed. A scene's indices are taken from the parenthesis after its title, up to the
first ';'. Lines applied one at a time with Chris (rips/review/approved.json, on the
build machine) and every line of a scene or read-through applied in the review tool
(rips/review/decisions/) count as reviewed too.
"""
import json, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), '..')
PAUSE = {'open', 'check', 'ai-reviewed'}

# Lines to confirm in play (docs/event-review.md, "To check in play or in the code").
CHECK = {
    ('EVENTMES.BIN', 288): 'which switch this is: "set into the wall" is wrong if it is the frog statue',
}
# Reviewed scenes that the list names only in prose.
EXTRA_REVIEWED = {('NPC_MES3.OBJ', i): 'NPC_MES3 scene 5: Lilia wants out' for i in (257, 258)}
# Open lines that the scene list names only in a note ("17 shared with NPC_MES1 79").
EXTRA_OPEN = {
    ('NPC_MES1.OBJ', 79): 'shared with NPC_MES5 17, in NPC_MES5 scene 3 (reputation greetings)',
}
DEFAULTS = {
    'EVENTMES.BIN': ('reviewed', 'event script reviewed scene by scene (finished 2026-10-03)'),
    'NPC_MES1.OBJ': ('ai-reviewed', "not flagged; Guy's flagged scenes were finished with Chris "
                     "(2026-09-26), the rest gets a read-through like the other files"),
    'NPC_MES2.OBJ': ('ai-reviewed', 'not flagged by the NPC reviewers'),
    'NPC_MES3.OBJ': ('ai-reviewed', 'not flagged by the NPC reviewers'),
    'NPC_MES4.OBJ': ('ai-reviewed', 'not flagged by the NPC reviewers'),
    'NPC_MES5.OBJ': ('ai-reviewed', 'not flagged by the NPC reviewers'),
    'SISETU.OBJ': ('first-pass', 'castle and menu text, no second look yet'),
    'STATUS.OBJ': ('first-pass', 'status screen text, no second look yet'),
    'FIGHTMSG.OBJ': ('first-pass', 'battle messages, no second look yet'),
}


def scenes():
    """{(file, index): (ticked, 'NPC_MESn scene k: title')} from the scenes in npc-review.md."""
    text = open(os.path.join(ROOT, 'docs/npc-review.md'), encoding='utf-8').read()
    text = text[text.index('## Remaining scenes'):]
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r'(NPC_MES\d)\b', line)
        if m:
            cur = m.group(1) + '.OBJ'
            continue
        m = re.match(r'- \[([ x])\] (\d+)\. ([^(]*)\(([^)]*)\)', line)
        if not (m and cur):
            continue
        ticked, m = m.group(1) == 'x', m.groups()[1:]
        label = f'{cur[:-4]} scene {m[0]}: {m[1].strip()}'
        for tok in re.split(r'[ ,/]+', m[2].split(';')[0]):
            r = re.fullmatch(r'(\d+)(?:-(\d+))?', tok)
            if r:
                a = int(r.group(1))
                for i in range(a, int(r.group(2) or a) + 1):
                    out[(cur, i)] = (ticked, label)
    return out


def approved():
    """{(file, index)} reviewed with Chris outside the scene list, if the review folder is
    here: lines applied one at a time (approved.json), and every line of a scene or
    read-through applied in the review tool (decisions/*.json)."""
    def key(ref):
        n, i = ref.split(':')
        return f'NPC_MES{n}.OBJ', int(i)
    out = set()
    p = os.path.join(ROOT, 'rips/review/approved.json')
    if os.path.exists(p):
        out |= {key(k) for k in json.load(open(p))}
    d = os.path.join(ROOT, 'rips/review/decisions')
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if name.endswith('.json'):
            dec = json.load(open(os.path.join(d, name), encoding='utf-8'))
            out |= {key(ln['ref']) for ln in dec.get('lines', [])}
            out |= {key(r) for ln in dec.get('lines', []) for r in ln.get('copies', []) + ln.get('carried', [])}
    return out


def table():
    """status(file, index) -> (status, why); file is the bare name, e.g. 'NPC_MES3.OBJ'."""
    sc, done = scenes(), approved()

    def status(f, i):
        if (f, i) in CHECK:
            return 'check', CHECK[(f, i)]
        if (f, i) in sc:
            ticked, label = sc[(f, i)]
            return ('reviewed', label + ' (done)') if ticked else ('open', label)
        if (f, i) in EXTRA_REVIEWED:
            return 'reviewed', EXTRA_REVIEWED[(f, i)] + ' (done)'
        if (f, i) in done:
            return 'reviewed', 'reviewed with Chris in the review tool'
        if (f, i) in EXTRA_OPEN:
            return 'open', EXTRA_OPEN[(f, i)]
        return DEFAULTS.get(f, ('unknown', 'not a tracked file'))
    return status


def counts():
    sys.path.insert(0, os.path.dirname(__file__))
    from textbuf import strings
    status = table()
    out = defaultdict(Counter)
    for path in ['DATA06/EVENTMES.BIN', 'DATA06/SISETU.OBJ', 'DATA01/STATUS.OBJ',
                 'DATA01/FIGHTMSG.OBJ'] + [f'DATA06/NPC_MES{n}.OBJ' for n in range(1, 6)]:
        d = open(os.path.join(ROOT, 'rips/dirty/dimguil', path), 'rb').read()
        f = os.path.basename(path)
        for i in range(len(strings(d))):
            out[f][status(f, i)[0]] += 1
    return out


def main():
    a = sys.argv[1:]
    if len(a) == 2 and a[0] != '--json':
        f = next((k for k in DEFAULTS if k.startswith(a[0].upper())), a[0].upper())
        st, why = table()(f, int(a[1]))
        print(f'{st}: {why}' + ('  (monitor pauses)' if st in PAUSE else ''))
    elif a and a[0] == '--json':
        sys.path.insert(0, os.path.dirname(__file__))
        status = table()
        c = counts()
        json.dump({f: {i: status(f, i) for i in range(sum(c[f].values()))} for f in c},
                  open(a[1], 'w'), indent=1)
    else:
        for f, c in counts().items():
            print(f'{f:14} ' + ', '.join(f'{k} {v}' for k, v in sorted(c.items())))


if __name__ == '__main__':
    main()
