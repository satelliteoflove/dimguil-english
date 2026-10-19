#!/usr/bin/env python3
"""Build rips/playplan/npc-by-chapter.json: paused NPC lines placed along the play order."""
import json, os, re, sys, glob, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import textstatus
from textbuf import strings

PAUSE = textstatus.PAUSE
status = textstatus.table()
SIZES = {}
for f in ['EVENTMES.BIN'] + [f'NPC_MES{n}.OBJ' for n in range(1, 6)]:
    d = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA06', f), 'rb').read()
    SIZES[f] = len(strings(d))
PLAY = list(range(1, 18)) + [19, 18]
ORD = {c: i for i, c in enumerate(PLAY)}
PARTY = {'NPC_MES1.OBJ': "Guy's party", 'NPC_MES2.OBJ': "Balbo's party", 'NPC_MES3.OBJ': "Fontana's party",
         'NPC_MES4.OBJ': "Cleo's group (the scholars)", 'NPC_MES5.OBJ': "Zaril's party", 'EVENTMES.BIN': 'Event script'}

# ---- npc-map sections
doc = open(os.path.join(ROOT, 'docs/npc-map.md'), encoding='utf-8').read()
SEC = {}      # (file, idx) -> section id
SECINFO = {}  # id -> dict(title, party, wt, generic)
GENERIC = re.compile(r'greeting|farewell|introduction|healing|identify|recovering|selling|practice fight|fight challenge|talk|told me|menu|lineup|ask the others|glyph check', re.I)
parts = re.split(r'^## NPC_MES(\d)', doc, flags=re.M)
for i in range(1, len(parts), 2):
    n, body = int(parts[i]), parts[i + 1].split('\n## ')[0]
    f = f'NPC_MES{n}.OBJ'
    blocks = re.split(r'(?=^\*\*\d+\.\d+ )', body, flags=re.M)
    for b in blocks:
        m = re.match(r'\*\*(\d+\.\d+) ([^*]*)\*\*', b)
        if not m:
            continue
        sid = f'{n}.{m.group(1).split(".")[1]}'
        title = m.group(2).strip().rstrip('.')
        head = m.group(0)
        title_plain = re.sub(r'\s*\([^)]*\)', '', title).strip(' .')
        wts = sorted({int(x) for x in re.findall(r'WT ch\. (\d+)', b)})
        party = PARTY[f]
        if f == 'NPC_MES5.OBJ':
            if sid in ('5.10',): party = 'The shadow'
            elif sid in ('5.11', '5.12'): party = 'The mysterious man'
            elif sid == '5.13': party = 'Agan'
        SECINFO[sid] = dict(title=f'{sid} {title_plain}', party=party, wt=wts, generic=bool(GENERIC.search(title_plain)), file=f)
        for grp in re.findall(r'\(([^)]*)\)', head):
            for a, bb in re.findall(r'(\d+)(?:-(\d+))?', grp):
                for k in range(int(a), int(bb or a) + 1):
                    SEC.setdefault((f, k), sid)

def wt_to_plan(c):
    return 18 if c == 19 else c   # WT 19 (the ending) is played inside the bot's chapter 18

# ---- walkthrough json
WT = {}   # (file, idx) -> plan chapter (earliest in play order)
def addwt(f, k, ch):
    if ch is None or ch not in ORD: return
    if (f, k) not in WT or ORD[ch] < ORD[WT[(f, k)]]:
        WT[(f, k)] = ch
wj = json.load(open(os.path.join(ROOT, 'docs/walkthrough-npcs.json')))
for ch in wj['chapters']:
    no = ch['no']
    if no is None: continue
    pc = wt_to_plan(no)
    for npc in ch['npcs']:
        for seg in npc['strings'].split(';'):
            seg = seg.strip()
            m = re.match(r'(NPC_MES\d|EVENTMES)\s+(.*)', seg)
            if not m: continue
            f = m.group(1) + ('.OBJ' if m.group(1).startswith('NPC') else '.BIN')
            rest = re.sub(r'\([^)]*\)', '', m.group(2))
            for a, b in re.findall(r'(\d+)(?:-(\d+))?', rest.split('/')[0] if f == 'EVENTMES.BIN' else rest):
                for k in range(int(a), int(b or a) + 1): addwt(f, k, pc)
        for q in npc.get('quotes', []):
            fq = q['file'] + ('.OBJ' if q['file'].startswith('NPC') else '.BIN')
            addwt(fq, q['idx'], pc)

# ---- bot
H = os.path.join(ROOT, 'rips/harness')
exact = collections.defaultdict(lambda: collections.defaultdict(set))   # (f,i) -> chapter -> runs
ranged = collections.defaultdict(lambda: collections.defaultdict(set))  # (f,i) -> (a,b) -> runs
def scan(path, rec):
    try:
        fh = open(path, encoding='utf-8')
    except OSError:
        return
    for line in fh:
        if '"NPC_MES' not in line and '"EVENTMES' not in line: continue
        try: r = json.loads(line)
        except ValueError: continue
        f = r.get('file')
        if f and (f.startswith('NPC_MES') or f == 'EVENTMES.BIN'):
            rec(f, r['idx'])
runs_seen = 0
def doexact(ch, d):
    global runs_seen
    runs_seen += 1
    scan(os.path.join(d, 'captured.jsonl'), lambda f, i: exact[(f, i)][ch].add(os.path.relpath(d, H)))
for a in 'abc':
    for d in sorted(glob.glob(os.path.join(H, 'fullrun', a, 'c*_try*'))):
        if os.path.isdir(d): doexact(int(re.match(r'c(\d+)_', os.path.basename(d)).group(1)), d)
for d in sorted(glob.glob(os.path.join(H, 'fullrun', 'test', 'c*_try*'))):
    doexact(int(re.match(r'c(\d+)_', os.path.basename(d)).group(1)), d)
for sub in ['ch12', 'ch13', 'ch14', 'ch15', 'ch16', 'ch17', 'ch18', 'ch19', 'chapters']:
    for d in sorted(glob.glob(os.path.join(H, sub, '*'))):
        rp = os.path.join(d, 'result.json')
        if not os.path.isfile(rp): continue
        try: ca = json.load(open(rp)).get('chapters_asked')
        except ValueError: continue
        if not ca: continue
        if ca[0] == ca[1]:
            doexact(ca[0], d)
        else:
            runs_seen += 1
            scan(os.path.join(d, 'captured.jsonl'), lambda f, i, ca=tuple(ca), d=d: ranged[(f, i)][ca].add(os.path.relpath(d, H)))
for d in sorted(glob.glob(os.path.join(H, 't3', '*'))) + [os.path.join(H, 't2')]:
    doexact(1, d)   # the chapter 1 pilot runs

# ---- combine
def first(chs):
    return min(chs, key=lambda c: ORD[c])
evid = {}   # (f,i) -> dict(chapter, evidence, note)
sections_chapters = collections.defaultdict(list)
for f in SIZES:
    for i in range(SIZES[f]):
        k = (f, i)
        e = None
        if exact.get(k):
            chs = sorted(exact[k], key=lambda c: ORD[c])
            if 18 in chs and 19 in chs: chs.remove(19)   # chapter 19 (the ring) revisits Area Z; 18 is where it belongs
            e = dict(chapter=chs[0], evidence='bot', also=[c for c in chs[1:]], runs=sum(len(v) for v in exact[k].values()))
            if k in WT and ORD[WT[k]] < ORD[e['chapter']]:
                e.update(chapter=WT[k], evidence='walkthrough', note=f'the bot first saw it in ch. {chs[0]}', also=[c for c in chs if c != WT[k]])
            elif k in WT and WT[k] != e['chapter']:
                e['walkthrough_chapter'] = WT[k]
        elif k in WT:
            e = dict(chapter=WT[k], evidence='walkthrough')
        else:
            sid = SEC.get(k)
            wts = SECINFO[sid]['wt'] if sid else []
            if wts:
                ch = first([wt_to_plan(c) for c in wts if wt_to_plan(c) in ORD])
                e = dict(chapter=ch, evidence='map', note=f'npc-map {sid}: WT ch. {",".join(map(str, wts))}')
        if e is None and ranged.get(k):
            a = min(r[0] for r in ranged[k]); b = max(r[1] for r in ranged[k])
            e = dict(chapter=a, evidence='bot', chapter_range=f'{a}-{b}', note=f'seen only in runs that covered ch. {a}-{b} together; placed at the earliest')
        if e:
            if ranged.get(k) and 'chapter_range' not in e:
                e['ranges'] = sorted({f'{a}-{b}' for a, b in ranged[k]})
            evid[k] = e
            if SEC.get(k): sections_chapters[SEC[k]].append(e['chapter'])
# party first appearance from bot/walkthrough evidence
party_first = {}
for (f, i), e in evid.items():
    if 'chapter_range' not in e and e['evidence'] in ('bot', 'walkthrough') and f.startswith('NPC'):
        if f not in party_first or ORD[e['chapter']] < ORD[party_first[f]]:
            party_first[f] = e['chapter']

for (f, i), e in evid.items():
    if 'chapter_range' in e and f in party_first:
        a, b = map(int, e['chapter_range'].split('-'))
        pf = party_first[f]
        if ORD[pf] > ORD[e['chapter']] and pf <= b:
            e['chapter'] = pf
            e['note'] += f"; moved to ch. {pf}, where the party first appears"
out = collections.defaultdict(list)
unplaced = []
allpaused = 0
for f in SIZES:
    for i in range(SIZES[f]):
        st, why = status(f, i)
        if st not in PAUSE: continue
        allpaused += 1
        sid = SEC.get((f, i))
        si = SECINFO.get(sid, {})
        scene = si.get('title', 'unmapped')
        party = si.get('party', PARTY[f])
        if f == 'EVENTMES.BIN': scene = 'Event script: ' + why
        row = dict(file=f, index=i, status=st, scene=scene, party=party)
        if st == 'open': row['review_scene'] = why
        e = evid.get((f, i))
        if e:
            row.update(chapter=e['chapter'], evidence=e['evidence'])
            for k in ('also', 'note', 'ranges', 'runs', 'chapter_range', 'walkthrough_chapter'):
                if k in e: row[k] = e[k]
            if 'walkthrough_chapter' in e: row['walkthrough_chapter'] = e['walkthrough_chapter']
        elif sid and not si['generic'] and sections_chapters.get(sid):
            ch = first(sections_chapters[sid])
            row.update(chapter=ch, evidence='inferred', note=f'same scene ({sid}) is placed at ch. {ch} by other lines')
        else:
            row['party_first_chapter'] = party_first.get(f)
            row['generic_scene'] = bool(si.get('generic'))
            unplaced.append(row)
            continue
        out[str(row['chapter'])].append(row)

res = {str(c): out.get(str(c), []) for c in PLAY}
res['unplaced'] = unplaced
json.dump(res, open(os.path.join(ROOT, 'rips/playplan/npc-by-chapter.json'), 'w'), indent=1, ensure_ascii=False)
print('runs scanned', runs_seen, 'paused total', allpaused, 'unplaced', len(unplaced))
for c in PLAY:
    r = res[str(c)]
    print(c, len(r), dict(collections.Counter(x['evidence'] for x in r)))
print(party_first)
