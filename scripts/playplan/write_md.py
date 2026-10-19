import json, re, collections, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
d = json.load(open(os.path.join(ROOT, 'rips/playplan/npc-by-chapter.json')))
rev = open(os.path.join(ROOT, 'docs/npc-review.md'), encoding='utf-8').read()
rev = rev[rev.index('## Remaining scenes'):]
PRI, cur = {}, None
for line in rev.splitlines():
    m = re.match(r'(NPC_MES\d)\b', line)
    if m: cur = m.group(1); continue
    m = re.match(r'- \[ \] (\d+)\. .*?\),\s*([A-Z]+(?:-[A-Z]+)?)', line)
    if m and cur: PRI[f'{cur} scene {m.group(1)}'] = m.group(2)
TITLES = {1:'The four pillars',2:'The Shrine and the jade mask',3:'The Underground Shrine and the blue stone',4:'The lake machine',5:'The moon door and the 2-Head Snake',6:'Area X and the white stone',7:'Area A: the green stone',8:'Area A: the yellow stone and the Jail Ogre',9:'Area B: the black stone',10:'Area B: the red stone',11:'Area A: the gold armor',12:'Area C: the silver stone',13:'Area C: the moving floors',14:'Area D: mimicry mode released',15:'Area C: the demon statue',16:'Area A: the gold stone',17:'Area E: the control room',19:'The ring for the Priestess\'s Door (bot-only detour)',18:'Area Z and the ending (walkthrough 18-19)'}
def rng(ix):
    ix = sorted(ix); out = []; s = p = ix[0]
    for x in ix[1:]+[None]:
        if x is not None and x == p+1: p = x; continue
        out.append(str(s) if s == p else f'{s}-{p}')
        if x is not None: s = p = x
    return ','.join(out)
def revlabel(rs):
    m = re.match(r'(NPC_MES\d) scene (\d+): (.*)', rs or '')
    if not m: return ''
    k = f'{m.group(1)} scene {m.group(2)}'
    return f'{m.group(1)[-1]}/{m.group(2)} {m.group(3)[:34]} ({PRI.get(k, "?")})'
def fnum(f): return f[-5] if f.startswith('NPC') else 'EV'
def table(rows, ev_col=True):
    g = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r['file'], r['scene'], r['index'])):
        g.setdefault((r['party'], r['scene'], revlabel(r.get('review_scene')), r['file']), []).append(r)
    L = ['| Party | Scene | Lines (n:k) | Count | Open scene (priority) |' + (' Evidence |' if ev_col else ''), '|---|---|---|---|---|' + ('---|' if ev_col else '')]
    for (party, scene, rl, f), rs in g.items():
        ev = collections.Counter(r.get('evidence', '-') + ('*' if r.get('chapter_range') else '') for r in rs)
        evs = ', '.join(f'{k} {v}' for k, v in ev.items())
        n = len(rs)
        L.append(f'| {party} | {scene.replace("|","/")} | {fnum(f)}:{rng([r["index"] for r in rs])} | {n} | {rl or ("ai-reviewed" if rs[0]["status"]=="ai-reviewed" else rs[0]["status"])} |' + (f' {evs} |' if ev_col else ''))
    return L
PLAY = [str(c) for c in list(range(1, 18)) + [19, 18]]
placed = [r for c in PLAY for r in d[c]]
unp = d['unplaced']
tot = len(placed) + len(unp)
ev = collections.Counter(r['evidence'] for r in placed)
nstar = sum(1 for r in placed if r.get('chapter_range'))
op = lambda rows: sum(1 for r in rows if r['status'] == 'open')
out = []
_n = [c for c in PLAY if not d[c]]
NONE = 'Chapters ' + ', '.join(_n[:-1]) + ' and ' + _n[-1] + ' have none placed.'
out.append(f"""# Play-through review plan: paused NPC lines by chapter

Chris plays through with the monitor pausing on every NPC line that is `open`, `ai-reviewed`
or `check` (`scripts/textstatus.py`). There are {tot} such lines. This plan puts them in
play order so a chapter or two can be reviewed ahead of where he is. Chapters follow the
walkthrough's numbering and the bot's order: 1 to 17, then 19 (the ring for the
Priestess's Door), then 18 (Area Z and the ending). {NONE} Machine-readable version: `rips/playplan/npc-by-chapter.json`; the scripts that
built it are `scripts/playplan/build_plan.py` and `write_md.py`.

## How much is evidence

{len(placed)} of the {tot} lines are placed in a chapter and {len(unp)} are not.
Of the placed lines, {ev['bot']} were seen on screen by a bot run in that chapter (of which
{nstar} come from older multi-chapter runs, marked `*`, and sit at the earliest chapter the run
covered), {ev['walkthrough']} come from the site walkthrough's NPC placements
(`docs/walkthrough-npcs.json`), and {ev['map']} from a chapter named in `docs/npc-map.md`.
Nothing is placed by guesswork alone ({ev.get('inferred', 0)} inferred), but the walkthrough
and map placements are sources' claims, not seen in play. Where the bot and the walkthrough
disagree the earlier chapter wins, since an early review is harmless.

The bot only reaches a handful of NPC lines per chapter, because it rarely talks to them.
That is why most paused lines are unplaced: they are talk-menu, healing, identify, shop
and greeting-variant lines that play whenever a party is met and a topic is chosen, and
the code that picks them is not decoded. They are listed by party at the end with the
first chapter the party can be met. The placed lines are the scenes that trigger on a
place or event, plus whatever greetings the bots happened to hit.

## Chapter by chapter, in play order

Lines are `n:k`, NPC_MESn string k, as in `docs/npc-map.md`. Open scene is `n/scene number title (priority)` from `docs/npc-review.md`; \"ai-reviewed\" means no scene is open for the line, but Chris hasn't seen it. Evidence is bot, walkthrough or map (`*` = from a multi-chapter run).
""")
for c in PLAY:
    rows = d[c]
    if not rows:
        out.append(f'### Chapter {c}: {TITLES[int(c)]}\n\nNo paused NPC lines placed here.\n')
        continue
    pc = collections.Counter(r['party'] for r in rows)
    out.append(f"### Chapter {c}: {TITLES[int(c)]}\n\n{len(rows)} paused lines, {op(rows)} of them in open scenes. " + '; '.join(f'{k} {v}' for k, v in pc.most_common()) + '.\n')
    out += table(rows)
    out.append('')

# high-priority open scenes at a glance
def scene_key(rs):
    m = re.match(r'(NPC_MES\d) scene (\d+): (.*)', rs or '')
    return (f'{m.group(1)} scene {m.group(2)}', m.group(3)) if m else None
hi = collections.OrderedDict()
for c in PLAY:
    for r in d[c]:
        k = scene_key(r.get('review_scene'))
        if k and PRI.get(k[0], '').startswith('HIGH'): hi.setdefault(k, {'ch': collections.Counter(), 'un': 0})['ch'][c] += 1
for r in unp:
    k = scene_key(r.get('review_scene'))
    if k and PRI.get(k[0], '').startswith('HIGH'): hi.setdefault(k, {'ch': collections.Counter(), 'un': 0})['un'] += 1
out.append('## The HIGH-priority open scenes at a glance\n')
out.append('| Scene | Priority | Placed lines by chapter | Unplaced lines |')
out.append('|---|---|---|---|')
def firstch(v): return min((ORD_[c] for c in v['ch']), default=99)
ORD_ = {c: i for i, c in enumerate(PLAY)}
for k, v in sorted(hi.items(), key=lambda kv: (firstch(kv[1]), kv[0])):
    out.append(f"| {k[0][7]}/{k[0].split()[-1]} {k[1]} | {PRI[k[0]]} | " + (', '.join(f'ch. {c}: {n}' for c, n in sorted(v['ch'].items(), key=lambda x: ORD_[x[0]])) or '-') + f" | {v['un']} |")
out.append('')

nconf = sum(1 for r in placed if r.get('walkthrough_chapter'))
nbotearly = sum(1 for r in placed if r['evidence'] == 'walkthrough' and 'bot first saw' in r.get('note', ''))
out.append(f"""## Things to know

- For {nbotearly} lines the bot first saw them in a later chapter than the walkthrough names, and those are placed by the walkthrough; the bot never saw one earlier than the walkthrough ({nconf}). Most are Cleo's group, who turn up as greetings and gossip in Areas A to D, well away from the library, so they roam.
- The two ending chapters are swapped in play order (19, then 18), as the bot plays them. Chapter 19 only adds three lines the bot met on the way (two Fontana's party greetings and Agan); the mysterious man in Area Z is placed in chapter 18, where the bot saw it as well.
- Three of the HIGH scenes are not tied to any chapter: the tea cakes (scholars), the fight challenge and the Fritillaria loyalty talk (Zaril's party). They are talk-menu topics, so they are met whenever the party is.
- Zaril's party is the biggest block of lines nobody can place: 96 lines, 69 of them open, from chapter 9 on.
""")
# unplaced
out.append(f"## Not placed in a chapter ({len(unp)} lines)\n")
out.append("These have no chapter evidence. Grouped by party, then by the scene they sit in in `docs/npc-map.md`. \"From\" is the first chapter in which the party's file was seen or placed by the evidence above; the lines can turn up in any chapter after that when the party is met and a topic chosen.\n")
byp = collections.OrderedDict()
for r in unp: byp.setdefault((r['party'], r['file']), []).append(r)
for (party, f), rows in sorted(byp.items(), key=lambda x: x[0][1]):
    pf = rows[0].get('party_first_chapter')
    out.append(f"### {party} ({fnum(f)}): {len(rows)} lines, {op(rows)} open" + (f", from chapter {pf}" if pf else '') + '\n')
    out += table(rows, ev_col=False)
    out.append('')
open(os.path.join(ROOT, 'docs/playthrough-review-plan.md'), 'w', encoding='utf-8').write('\n'.join(out))
print(len('\n'.join(out)))
