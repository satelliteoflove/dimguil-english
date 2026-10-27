#!/usr/bin/env python3
"""The translation review tool: a local web app for reviewing NPC scenes with Chris.

    rips/venv/bin/python scripts/reviewtool/server.py [--port 8777] [--host ADDR] [--root DIR]

Then open http://localhost:8777 (Firefox first). Binds to localhost only, unless
--host ADDR is given (--host 0.0.0.0 to use it from a phone on the home network).
--root DIR reads and writes the data of another copy of the repo (its translations/,
rips/ and docs/), so a worktree's server can run on the main copy's scenes.

What it reads:
  - scenes: rips/review/scenes/*.json, written by Claude per scene (the literal and
    faithful readings, notes, word notes, sources). They quote and gloss the Japanese,
    so they stay out of the repo, like the reviewers' reports.
  - the current English, live from translations/NPC_MESn.OBJ.json, and the Japanese
    from rips/stage/out/dumps (run scripts/build.sh once)
  - rips/dict/dict.sqlite (scripts/reviewtool/mkdict.py) and the role-language notes
    in roleterms.json; the font cut from the game by mkfont.py
  - the voice sheet in docs/npc-translation.md, and cast.json for speaker colors

What it writes, only when Chris applies a scene:
  - translations/NPC_MESn.OBJ.json, after every changed line passes npcfit's checks
    (the same function npcfit.py uses), in npcapply.py's formatting, with its quotes
    closed (npcquotes.py)
  - rips/review/decisions/<scene>.json: each line's choice, the text before and after,
    and Chris's note. Claude commits from that (one commit per scene) and marks it.
    A kept line's "carried" lists the ticked copies that already read the same: they
    count as read too, and later scenes show them collapsed (settled()).
    A line's "copies" lists the other refs written with it. Since the line page
    (2026-10-20) these are the ones Chris ticked, and can include a related line from
    the scene's "related" as well as a same-Japanese copy; the format is unchanged.
Questions Chris asks in the tool go to rips/review/questions.json for Claude to answer.
Each is {id, scene, ref, about, question, asked_at, answer}; Claude fills in answer (blank
lines between paragraphs) and answered_at. A paragraph that is a whole box, a speaker's
name on its own line and then the speech in quotes, gets a "Put this in the editor"
button; so does each string in an optional "suggest" (a string or a list). The page
polls for answers. A line shows the questions on its ref and on its copies.

The line page shows one block per line. A scene line can carry, besides ref and context
(the few words beside the speaker's name):
  literal     "Literally": a close English reading
  faithful    the proposed box text; a line has a proposal when it differs from current
  why         under the proposal, why it differs ("No change." is not shown)
  notes       "What's going on": [{title?, text, sources?: [{label, url?}]}]; Japanese in
              the text is set in mincho by itself
  plays       "When it plays": when and where the game shows the line
  related     "Elsewhere": [{ref, note}], lines worded to match that aren't copies
              (copies, the same Japanese, are found by the server). Each copy and
              related line shows where it plays, its English, and a tick for
              "Apply my change here too": copies start ticked, related lines not.
  words       older word notes, [{jp, reading, sense, register, confidence, sources}];
              without a gloss they go on the automatic word groups that contain them
  gloss       the interlinear gloss by hand: a list of pages, each a list of words
              {jp, rd?, en?, tone?, trap?, entry?}, in order. jp is the word as written,
              particles and endings included ("悪の"); rd its reading, over the kanji;
              en the short English under it. tone: true underlines a word that carries
              the speaker's voice; trap: true stars a sense that's easy to get wrong.
              Punctuation is its own item ({"jp": "。"}) and the page keeps it with the
              word before. {ff12} (the name) is written as is. The jp of each page,
              joined, must be that page's Japanese (line breaks and the opening 「 left
              out); if it isn't, the page falls back to the automatic gloss and says so.
              A single page can be given as a flat list of words.
  entries     what clicking a word opens: {key: {head, label?, lookup?, senses?, here?,
              note?}}, named by a word's entry (or given inline as entry: {...}). head
              is the headword, label the line after it ("みをかためる, verb"); senses a
              list of short glosses, or lookup names a word whose first JMdict senses
              to use instead; here the index of the sense that applies; note the
              explanation under them.
A line without a gloss gets one made here (gloss()): the splitter's words grouped with
their particles and endings, readings from the splitter, the first JMdict sense under
each, and the dictionary entries looked up on hover and click.

Needs fugashi and unidic-lite for the word splitter (rips/venv has them); without
them the Japanese still shows, just not split into words.
"""
import json, os, re, sqlite3, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
# --root DIR reads and writes another copy's data (translations/, rips/, docs/), so a
# worktree's server can work on the main copy's scenes and decisions.
ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1]) if '--root' in sys.argv else CODE_ROOT
sys.path.insert(0, os.path.join(CODE_ROOT, 'scripts'))
import descfit, npcfit, npcquotes  # noqa: E402
from reviewpage import load as load_commented  # noqa: E402  (some translation files have comments)

SCENES = os.path.join(ROOT, 'rips/review/scenes')
DECISIONS = os.path.join(ROOT, 'rips/review/decisions')
QUESTIONS = os.path.join(ROOT, 'rips/review/questions.json')
FONT = os.path.join(ROOT, 'rips/review/font')
FACES = os.path.join(ROOT, 'rips/review/faces')
DICT = os.path.join(ROOT, 'rips/dict/dict.sqlite')
STATIC = os.path.join(HERE, 'static')
NPC_FILES = range(1, 6)
LOCK = threading.Lock()

try:
    import fugashi
    TAGGER = fugashi.Tagger()
except Exception:  # noqa: BLE001 - the tool still works without the splitter
    TAGGER = None


# --- text -----------------------------------------------------------------------------

def tr_path(n):
    return os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json')


def load_tr(n):
    return json.load(open(tr_path(n), encoding='utf-8'))


def load_src(n):
    d = json.load(open(os.path.join(ROOT, f'rips/stage/out/dumps/NPC_MES{n}.OBJ.json'), encoding='utf-8'))
    return [s['source'] for s in d['sections'][0]['strings']]


def body(text):
    """The text after the speaker line, so 'Man in armor' and 'Balbo' versions match."""
    k = text.find('\n「')
    return text[k:] if k > 0 else text


def flat(text):
    """text without its page and line breaks, so copies broken differently still match
    (5:8 and 3:22 break their pages in different places)."""
    return re.sub(r'\s+', '', text)


SOURCES = {n: load_src(n) for n in NPC_FILES}
COPIES = {}  # Japanese body, breaks removed -> every ref that has it, whoever the speaker
for _n in NPC_FILES:
    for _i, _s in enumerate(SOURCES[_n]):
        COPIES.setdefault(flat(body(_s)), []).append(f'{_n}:{_i}')


def person(ref):
    """Who speaks ref, from its English speaker tag and cast.json, or None."""
    if not hasattr(person, 'tags'):
        cast = read_json(os.path.join(HERE, 'cast.json'), {'people': []})
        person.tags = {t: p['id'] for p in cast['people'] for t in p.get('tags', [])}
    return person.tags.get(current(ref).split('\n', 1)[0])


def copies_of(ref):
    """Refs with the same Japanese, or the same lines from the same person under another tag."""
    n, i = parse_ref(ref)
    out = []
    for r in COPIES[flat(body(SOURCES[n][i]))]:
        m, j = parse_ref(r)
        if r != ref and (flat(SOURCES[m][j]) == flat(SOURCES[n][i]) or (person(r) and person(r) == person(ref))):
            out.append(r)
    return out


def as_copy(text, ref):
    """text with ref's own speaker line, for a copy whose speaker differs."""
    cur = current(ref)
    if '\n' not in text or '\n' not in cur or not cur.split('\n', 1)[1].startswith('"'):
        return text
    return cur.split('\n', 1)[0] + '\n' + text.split('\n', 1)[1]


def parse_ref(ref):
    m = re.fullmatch(r'([1-5]):(\d+)', ref or '')
    if not m or int(m.group(2)) >= len(SOURCES[int(m.group(1))]):
        raise ValueError(f'bad ref {ref!r}')
    return int(m.group(1)), int(m.group(2))


def current(ref):
    n, i = parse_ref(ref)
    return load_tr(n)['sections'][0]['strings'][i]['translation']


def layout(text):
    """Pages of lines, each line as glyph codes and width, as the box will draw them."""
    pages = []
    for pg in npcfit.pages(text):
        lines = []
        for line in pg.split('\n'):
            shown = npcfit.measurable(line)
            try:
                codes = [c for c in descfit.encode(shown) if c >= 0]
            except ValueError:
                codes = []
            lines.append({'codes': codes, 'width': sum(descfit.LUT[c] + 1 if c < len(descfit.LUT) else 12 for c in codes),
                          'placeholder': '{ff12}' in line})
        pages.append(lines)
    return pages


def fit(ref, text):
    n, i = parse_ref(ref)
    text = npcquotes.close(text, SOURCES[n][i])  # as apply() will write it
    problems = npcfit.string_problems(text, SOURCES[n][i])
    hard = [p for p in problems if 'fine if intended' not in p]
    return {'ok': not hard, 'problems': problems, 'hard': hard, 'pages': layout(text),
            'width': npcfit.WIDTH, 'lines': npcfit.LINES,
            'source_lines': [p.count('\n') + 1 for p in npcfit.pages(SOURCES[n][i])]}


WEAK_END = {'a', 'an', 'the', 'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'and', 'but', 'or',
            'nor', 'so', 'if', 'as', 'from', 'into', 'that', 'my', 'your', 'his', 'her', 'its', 'our',
            'their', 'this', 'these', 'those', 'i', "i'm", "i'll", "i'd", 'we', 'you', 'he', 'she', 'they'}


def line_px(s):
    return descfit.line_widths(npcfit.measurable(s))[0]


def balanced(words, first, lines):
    """Break words into exactly `lines` lines that fit the box: at sentence ends where
    possible (the Japanese and our hand-broken lines run a sentence or clause per line),
    then after commas, otherwise as even as possible, and never leaving an article or
    preposition at a line's end. Dynamic programming over break points; `first` is
    the first line's prefix ('"' or ' '). None if the words can't fill that many lines
    or don't fit in them."""
    n = len(words)
    if n < lines:
        return None
    total = line_px(first + ' '.join(words))
    target = total / lines
    best = {(0, 0): (0.0, None)}
    for k in range(lines):
        for i in range(n):
            if (i, k) not in best:
                continue
            for j in range(i + 1, n - (lines - k - 1) + 1):
                w = line_px((first if k == 0 else ' ') + ' '.join(words[i:j]))
                if w > npcfit.WIDTH:
                    break
                cost = best[(i, k)][0] + ((w - target) / 8) ** 2
                if j < n:
                    last = words[j - 1]
                    if last.lower().strip('"\'') in WEAK_END:
                        cost += 500
                    if last.endswith(('.', '!', '?', '.\'', '!\'', '?\'')):
                        cost -= 600   # a sentence per line, as the Japanese breaks them
                    elif last.endswith((',', ';', ':')):
                        cost -= 60
                if (j, k + 1) not in best or cost < best[(j, k + 1)][0]:
                    best[(j, k + 1)] = (cost, i)
    if (n, lines) not in best:
        return None
    out, j, k = [], n, lines
    while k:
        i = best[(j, k)][1]
        out.append(' '.join(words[i:j])); j, k = i, k - 1
    return out[::-1]


def rewrap(text, ref=None):
    """Refill each page with even, phrase-aware line breaks, keeping pages, the speaker's
    name, the opening quote and the one-space indent of following lines. A page keeps
    its line count if the words fit; otherwise it gets the next count that does."""
    m = re.match(r'([^\n"]*)\n"', text)
    head, body = (m.group(0)[:-1], text[m.end() - 1:]) if m else ('', text)
    out = []
    for k, pg in enumerate(body.split('\n\r')):
        # Lines set apart on purpose (an indented spell name, a colored line) stay as
        # they are; the ordinary lines between them are refilled.
        result, run = [], []

        def flush():
            if not run:
                return
            first = '"' if (m and k == 0 and not result) else ' '
            words = ' '.join(l.strip() for l in run).lstrip('"').split()
            have, lines = len(run), None
            for count in [have] + list(range(have + 1, have + 6)) + list(range(have - 1, 0, -1)):
                lines = balanced(words, first, count)
                if lines:
                    break
            lines = lines or [' '.join(words)]
            result.extend((first if j == 0 else ' ') + l for j, l in enumerate(lines))
            run.clear()

        for line in pg.split('\n'):
            if re.match(r'\s{2,}|\s*\{ff30\}', line.lstrip('"')) and line.strip():
                flush(); result.append(line)
            else:
                run.append(line)
        flush()
        out.append('\n'.join(result))
    return head + '\n\r'.join(out)


# --- dictionary -----------------------------------------------------------------------

def db():
    con = sqlite3.connect(f'file:{DICT}?mode=ro', uri=True, check_same_thread=False)
    return con


DB = db() if os.path.exists(DICT) else None
TAGS = dict(DB.execute('select tag, text from tags').fetchall()) if DB else {}
ROLE = json.load(open(os.path.join(HERE, 'roleterms.json'), encoding='utf-8'))
ROLE_BY = {m: t for t in ROLE['terms'] for m in t['match']}


def has_form(form):
    with LOCK:
        return bool(DB.execute('select 1 from form where form=? limit 1', (form,)).fetchone()
                    or DB.execute('select 1 from wikt_form where form=? limit 1', (form,)).fetchone())


def kata2hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def span_reading(form):
    """JMdict's reading for a word written form, if it has exactly one."""
    if not re.search(r'[\u4e00-\u9fff々]', form):
        return form
    with LOCK:
        rows = DB.execute("select e.kana from form f join entry e on e.id = f.id where f.form=? and f.kind='k'", (form,)).fetchall()
    readings = {r['r'] for row in rows for r in json.loads(row[0]) if not r['restr'] or form in r['restr']}
    return readings.pop() if len(readings) == 1 else None


CONTENT = ('名詞', '代名詞', '動詞', '形容詞', '形状詞', '副詞', '連体詞', '感動詞', '接頭辞')


def tokens(text):
    """Words for the Japanese: surface, dictionary form, reading, and the longest run of
    words starting here that is itself a dictionary entry (あの + 人 -> あの人)."""
    if not TAGGER:
        return [{'s': text, 'plain': True}]
    words = []
    for w in TAGGER(text):
        f = w.feature
        words.append({'s': w.surface, 'lemma': getattr(f, 'lemma', None) or w.surface,
                      'reading': kata2hira(getattr(f, 'kana', None) or ''),
                      'pos': getattr(f, 'pos1', '') or '', 'pos2': getattr(f, 'pos2', '') or '',
                      'form': getattr(f, 'cForm', '') or '',
                      'white': w.white_space})
    for k, w in enumerate(words):
        best = None
        if DB and w['pos'] in CONTENT:
            for j in range(min(len(words), k + 5), k + 1, -1):
                span = ''.join(x['s'] for x in words[k:j])
                if has_form(span):
                    best = (span, j - k)
                    break
        w['span'] = best
        if best and best[1] > 1:
            w['span_reading'] = span_reading(best[0])
        w['role'] = next((m for m in (w['s'], w['lemma']) if m in ROLE_BY), None)
        if best and best[0] in ROLE_BY:
            w['role'] = best[0]
    return words


def jmdict_only(q, lemma=None):
    """lookup()'s JMdict and Wiktionary parts, without the slow example search."""
    out = {'jmdict': [], 'wiktionary': []}
    if not DB:
        return out
    with LOCK:
        for f in dict.fromkeys(x for x in (q, lemma) if x):
            rows = DB.execute('select e.kanji, e.sense, e.rank, f.kind from form f join entry e on e.id = f.id where f.form=?', (f,)).fetchall()
            for k, sn, rank, kind in sorted(rows, key=lambda r: r[2]):
                kanji, senses = json.loads(k), json.loads(sn)
                if kind == 'r' and kanji and not any('uk' in x['misc'] for x in senses):
                    continue
                out['jmdict'].append({'senses': senses})
            if out['jmdict']:
                break
        if not out['jmdict']:
            for f in dict.fromkeys(x for x in (q, lemma) if x):
                for (data,) in DB.execute("select w.data from wikt_form f join wikt w on w.id = f.id where f.form=? and (f.kind='w' or w.word=f.form) limit 2", (f,)):
                    out['wiktionary'].append(json.loads(data))
    return out


def lookup(q, lemma=None):
    out = {'q': q, 'jmdict': [], 'wiktionary': [], 'kanji': [], 'examples': [], 'role': None}
    if not DB:
        return out
    forms = [f for f in dict.fromkeys([q, lemma]) if f]
    with LOCK:
        kana_q = not re.search(r'[\u4e00-\u9fff々]', q)
        ids = []
        for f in forms:
            for eid, kind in DB.execute('select distinct id, kind from form where form=?', (f,)):
                ids.append((eid, kind))
        for eid, kind in list(dict.fromkeys(ids)):
            k, r, s, rank = DB.execute('select kanji, kana, sense, rank from entry where id=?', (eid,)).fetchone()
            kanji, senses = json.loads(k), json.loads(s)
            # A reading match only counts for a word written in kana: no kanji, or 'usually kana'.
            if kind == 'r' and kanji and not any('uk' in x['misc'] for x in senses):
                continue
            for sense in senses:
                sense['tags'] = [{'tag': t, 'text': TAGS.get(t, t)} for t in sense['pos'] + sense['misc'] + sense['field'] + sense['dial']]
            out['jmdict'].append({'id': eid, 'kanji': kanji, 'kana': json.loads(r), 'senses': senses, 'rank': rank})
            if len(out['jmdict']) >= 6:
                break
        out['jmdict'].sort(key=lambda e: e['rank'])
        wids = []
        for f in forms:
            wids += [r[0] for r in DB.execute(
                "select distinct f.id from wikt_form f join wikt w on w.id = f.id where f.form=? and (f.kind='w' or w.word=f.form)", (f,))]
        for wid in list(dict.fromkeys(wids))[:6]:
            word, pos, data = DB.execute('select word, pos, data from wikt where id=?', (wid,)).fetchone()
            out['wiktionary'].append({'word': word, 'pos': pos, **json.loads(data)})
        for ch in dict.fromkeys(c for c in q if '一' <= c <= '鿿' or c in '々'):
            row = DB.execute('select data from kanji where lit=?', (ch,)).fetchone()
            if row:
                out['kanji'].append({'lit': ch, **json.loads(row[0])})
        key = forms[0] if len(forms[0]) > 1 or not lemma else lemma
        out['examples'] = [{'jp': a, 'en': b} for a, b in DB.execute(
            'select jp, en from example where jp like ? order by length(jp) limit 6', (f'%{key}%',))]
    role = ROLE_BY.get(q) or ROLE_BY.get(lemma or '')
    out['role'] = role
    return out


# --- the interlinear gloss -----------------------------------------------------------

PUNCT = set('。,、?!:・「」“”『』()?!,.')
TRAIL = set('~ー〜')   # stretch marks stay inside the word they stretch (う~)
ATTACH = ('助詞', '助動詞', '接尾辞')
PARTICLES = {'を': '(object)', 'は': '(topic)', 'が': '(subject)', 'に': 'to', 'で': 'at, with', 'の': "'s, of",
             'と': 'and, with', 'も': 'also', 'か': '(question)', 'ね': 'right?', 'よ': '(emphasis)', 'ぞ': '(emphasis)',
             'へ': 'toward', 'から': 'from, because', 'まで': 'until', 'な': '(emphasis)', 'さ': '(emphasis)'}
CONTROL = re.compile(r'\{ff12\}|\{ff11\}0|\{ff30\}.|\{ff[0-9a-f]{2}\}\r?')
_GLOSS_CACHE = {}


def jp_pages(src):
    """The Japanese a line shows, page by page, without the speaker's name, the opening
    bracket or the line breaks within a page."""
    m = re.match(r'[^\n「]*\n(?=「)', src)
    text = src[m.end():] if m else src
    pages = []
    for k, pg in enumerate(npcfit.pages(text)):
        pg = ''.join(line.strip() for line in pg.split('\n'))
        pages.append(pg[1:] if k == 0 and pg.startswith('「') else pg)
    return pages


# Where JMdict's first sense misleads under a word (すごい is "amazing" here, not
# "terrible"): what to show instead, by the group as written, the word, or its lemma.
# A plain string applies on every line, so it must hold everywhere; {"en", "only": [refs]}
# applies only on those lines (and their copies, which share the Japanese).
def load_gloss_fixes():
    try:
        raw = json.load(open(os.path.join(HERE, 'glossfix.json'), encoding='utf-8'))
    except FileNotFoundError:
        return {}, {}
    everywhere, scoped = {}, {}
    for k, v in raw.items():
        if k.startswith('_'):
            continue
        if isinstance(v, str):
            everywhere[k] = v
        else:
            pages = set()
            for r in v['only']:
                n, i = parse_ref(r)
                pages |= {flat(pg) for pg in jp_pages(SOURCES[n][i])}
            scoped[k] = (v['en'], pages)
    return everywhere, scoped


GLOSS_FIX, GLOSS_FIX_SCOPED = load_gloss_fixes()


def gloss_fix(keys, page):
    """The corrected gloss for a group on this page of Japanese, or None."""
    for k in keys:
        if k in GLOSS_FIX:
            return GLOSS_FIX[k]
        if k in GLOSS_FIX_SCOPED and flat(page) in GLOSS_FIX_SCOPED[k][1]:
            return GLOSS_FIX_SCOPED[k][0]
    return None


def short_gloss(q, lemma=None):
    """The first JMdict sense, cut short, for under a word."""
    r = jmdict_only(q, lemma)
    for e in r['jmdict']:
        for sense in e['senses']:
            if sense['gloss']:
                g = re.sub(r'\s*\(.*?\)', '', sense['gloss'][0]).strip()
                return g[:30] or sense['gloss'][0][:30]
    for w in r['wiktionary']:
        for sense in w.get('senses', []):
            if sense.get('glosses'):
                return sense['glosses'][0][:30]
    return ''


def auto_page(text):
    """Word groups for one page of Japanese: each content word with the particles and
    endings that hang on it, punctuation as its own item (the page keeps it with the
    word before), {ff12} as the name."""
    groups = []
    pos = 0
    pieces = []
    for m in CONTROL.finditer(text):
        pieces.append(('text', text[pos:m.start()]))
        pieces.append(('code', m.group(0)))
        pos = m.end()
    pieces.append(('text', text[pos:]))
    for kind, piece in pieces:
        if not piece:
            continue
        if kind == 'code':
            if piece == '{ff12}':
                groups.append({'jp': piece, 'show': '(name)', 'en': "a character's name", 'name': True})
            elif piece == '{ff11}0':
                groups.append({'jp': piece, 'show': '(number)', 'en': 'a number', 'name': True})
            else:
                groups.append({'jp': piece, 'show': '', 'code': True})
            continue
        toks = tokens(piece)
        if toks and toks[0].get('plain'):
            groups.append({'jp': piece, 'en': ''})
            continue
        # one dictionary word made of several pieces (あの + 人) is one token
        merged, k = [], 0
        while k < len(toks):
            t = toks[k]
            if t.get('span') and t['span'][1] > 1:
                merged.append({**t, 's': t['span'][0], 'lemma': t['span'][0],
                               'reading': t.get('span_reading') or ''.join(x['reading'] for x in toks[k:k + t['span'][1]]),
                               'merged': True})
                k += t['span'][1]
            else:
                merged.append(t); k += 1
        cur, prefix, prev = None, False, None
        for t in merged:
            surf = t['s']
            if t['pos'] in ('補助記号', '記号') or not re.search(r'[\w〜~ー]', surf):
                for ch in surf:
                    if ch in TRAIL and cur:
                        cur['jp'] += ch
                    else:
                        groups.append({'jp': ch, 'punct': True}); cur = None
                prev = t
                continue
            attach = cur is not None and not prefix and (
                t['pos'] in ATTACH or (t['pos'] == '形状詞' and t['pos2'] == '助動詞語幹')
                or (t['pos'] in ('動詞', '形容詞') and t['pos2'] == '非自立可能' and prev is not None
                    and (prev['pos'] in ('動詞', '助動詞') or (prev['pos'] == '助詞' and prev['pos2'] == '接続助詞'))))
            if prefix and cur is not None:   # お + 持ち
                cur['toks'].append(t); cur['jp'] += surf; prefix = False
            elif attach:
                cur['toks'].append(t); cur['jp'] += surf
            else:
                cur = {'jp': surf, 'toks': [t]}
                groups.append(cur)
                prefix = t['pos'] == '接頭辞'
            prev = t
    for g in groups:
        toks = g.pop('toks', None)
        if not toks:
            continue
        head = next((t for t in toks if t['pos'] not in ('接頭辞',) + ATTACH), toks[0])
        g['q'], g['lemma'] = head['s'], head['lemma']
        g['pos'] = head['pos']
        kan = [i for i, t in enumerate(toks) if re.search(r'[一-鿿々]', t['s'])]
        g['rd'] = ''.join(t['reading'] for t in toks[:kan[-1] + 1]) if kan else ''
        if head['pos'] in ATTACH:
            g['en'] = PARTICLES.get(head['s'], '')
        elif head['pos2'] == '固有名詞':
            g['en'] = 'name'
        else:
            g['en'] = short_gloss(head['s'], head['lemma'])
        fix = gloss_fix([g['jp']] + [w for w in (head['s'], head['lemma']) if len(w) > 1], text)   # や alone, not the particle
        if fix and fix != g['en']:
            g['dict_en'], g['en'], g['fixed'] = g['en'], fix, True
        if any(t.get('role') for t in toks):
            g['role'] = next(t['role'] for t in toks if t.get('role'))
            g['tone'] = True
    return groups


def resolve_entry(e):
    """A hand-written entry, with its senses from JMdict when it names a lookup word
    instead of listing them."""
    e = dict(e)
    if 'senses' not in e and e.get('lookup'):
        r = lookup(e['lookup'])
        e['senses'] = ['; '.join(sn['gloss'][:3]) for sn in (r['jmdict'][0]['senses'][:3] if r['jmdict'] else [])]
    return e


def gloss(ref, line=None):
    """The interlinear gloss for ref: the scene's hand annotation if it has one and it
    covers the Japanese exactly, otherwise word groups made from the splitter and JMdict."""
    n, i = parse_ref(ref)
    pages = jp_pages(SOURCES[n][i])
    line = line or {}
    out = {'ref': ref, 'pages': None, 'source': 'auto', 'error': None}
    hand = line.get('gloss')
    if hand:
        if hand and isinstance(hand[0], dict):
            hand = [hand]
        entries = line.get('entries', {})
        flat_hand = [''.join(w['jp'] for w in pg) for pg in hand]
        if [flat(p) for p in flat_hand] != [flat(p) for p in pages]:
            out['error'] = ("The hand gloss doesn't match the Japanese, so this is the automatic one. "
                            f"Gloss: {' / '.join(flat_hand)}; Japanese: {' / '.join(pages)}")
        else:
            res = []
            for pg in hand:
                items = []
                for w in pg:
                    w = dict(w)
                    if not re.search(r'[\w{]', w['jp']) or (w['jp'] in PUNCT):
                        w['punct'] = True
                    e = w.get('entry')
                    if isinstance(e, str):
                        if e not in entries:
                            out['error'] = f'entry {e!r} is named but not given'
                        e = entries.get(e)
                    if e:
                        w['entry'] = resolve_entry(e)
                    if w['jp'] == '{ff12}':
                        w.setdefault('show', '(name)'); w['name'] = True
                    w.setdefault('q', (w.get('entry') or {}).get('lookup') or w['jp'])
                    items.append(w)
                res.append(items)
            out['pages'], out['source'] = res, 'hand'
            return out
    key = tuple(pages)
    if key not in _GLOSS_CACHE:
        _GLOSS_CACHE[key] = [auto_page(p) for p in pages]
    out['pages'] = json.loads(json.dumps(_GLOSS_CACHE[key]))
    # the scene's older word notes ("words") go on the groups they cover
    for w in line.get('words') or []:
        jp = (w.get('jp') or '').strip('〜~')
        for pg in out['pages']:
            for g in pg:
                if jp and not g.get('punct') and (jp in g['jp'] or (len(g['jp']) > 1 and g['jp'] in jp)):
                    g.setdefault('notes', []).append({'jp': w.get('jp'), 'sense': w.get('sense'), 'register': w.get('register')})
                    if w.get('register'):
                        g['tone'] = True
    return out


_CORPUS = None


def corpus():
    """Every translated string in the game: (file, section, index, Japanese, English)."""
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = []
        dumps = os.path.join(ROOT, 'rips/stage/out/dumps')
        for name in sorted(os.listdir(dumps)):
            tp = os.path.join(ROOT, 'translations', name)
            if not os.path.exists(tp):
                continue
            ds = json.load(open(os.path.join(dumps, name), encoding='utf-8'))['sections']
            ts = load_commented(tp)['sections']
            for k, (dsec, tsec) in enumerate(zip(ds, ts)):
                for i, (d, t) in enumerate(zip(dsec['strings'], tsec['strings'])):
                    _CORPUS.append((name.replace('.json', ''), k, i, d['source'], t['translation']))
    return _CORPUS


def concordance(q, ref=None, limit=12):
    """Other strings with the same Japanese, and how they were translated."""
    out, seen = [], set()
    for name, k, i, jp, en in corpus():
        if q in jp and en and jp not in seen:
            r = f'{name[7]}:{i}' if name.startswith('NPC_MES') else f'{name} {k}:{i}'
            if r == ref:
                continue
            seen.add(jp)
            out.append({'ref': r, 'jp': jp, 'en': en})
    total = len(out)
    out.sort(key=lambda x: (not x['ref'][0].isdigit(), len(x['jp'])))
    return {'q': q, 'total': total, 'hits': out[:limit]}


# --- voice sheet ----------------------------------------------------------------------

def voices():
    text = open(os.path.join(ROOT, 'docs/npc-translation.md'), encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'^- \*\*(.+?)\*\*\.?(.*?)(?=^- \*\*|^#|\Z)', text, re.M | re.S):
        name = re.sub(r'\s*\(.*\)', '', m.group(1)).strip()
        out[name] = ' '.join(m.group(2).split())
    return out


# --- scenes and decisions -------------------------------------------------------------

def read_json(path, default=None):
    try:
        return json.load(open(path, encoding='utf-8'))
    except FileNotFoundError:
        return default


def all_scenes():
    """{id: scene} for every prepared scene."""
    out = {}
    for name in sorted(os.listdir(SCENES)) if os.path.isdir(SCENES) else []:
        if name.endswith('.json'):
            s = read_json(os.path.join(SCENES, name))
            if s:
                out[s['id']] = s
    return out


def review_index(scenes):
    """Where each ref has been read: {ref: (scene id, the ref it was read as)} from every
    decision (its lines, the copies written with them, and the copies carried along
    unchanged), and {ref: scene id} for the lines of voice scenes not yet applied."""
    done, voice = {}, {}
    for name in sorted(os.listdir(DECISIONS)) if os.path.isdir(DECISIONS) else []:
        d = read_json(os.path.join(DECISIONS, name)) if name.endswith('.json') else None
        for rec in [d, *d.get('earlier', [])] if d else []:
            for ln in rec.get('lines', []):
                done.setdefault(ln['ref'], (d['scene'], ln['ref']))
                for r in ln.get('copies', []) + ln.get('carried', []):
                    done.setdefault(r, (d['scene'], ln['ref']))
    for sid, s in scenes.items():
        if s.get('kind') == 'voice' and not os.path.exists(os.path.join(DECISIONS, f'{sid}.json')):
            for ln in s['lines']:
                voice.setdefault(ln['ref'], sid)
    return done, voice


def settled(sid, scenes, index=None):
    """For each line of scene sid, None if Chris reads it here, or where he reads it
    instead: {scene, title, index, as, pending, here}. A line is read elsewhere when
    another scene's decision has it, or has a copy of it (same Japanese, same speaker)
    whose English is the same; when a voice scene still to come has it (pending); or
    when it's a copy of a line above it in this scene (here), whose choice covers it."""
    done, voice = index or review_index(scenes)
    s = scenes[sid]
    own = read_json(os.path.join(DECISIONS, f'{sid}.json'))
    own_refs = {ln['ref'] for rec in ([own, *own.get('earlier', [])] if own else []) for ln in rec.get('lines', [])}
    cur = {}
    def now(r):
        if r not in cur:
            cur[r] = current(r)
        return cur[r]
    def where(other, as_ref, **kw):
        lines_ = scenes.get(other, {}).get('lines', [])
        k = next((j for j, x in enumerate(lines_) if x['ref'] == as_ref), 0)
        return {'scene': other, 'title': scenes.get(other, {}).get('title', other), 'index': k,
                'as': as_ref, 'pending': False, 'here': False, **kw}
    out, above = [], {}
    for k, ln in enumerate(s['lines']):
        ref, res = ln['ref'], None
        if ref not in own_refs:
            copies = copies_of(ref)
            if ref in done and done[ref][0] != sid:
                res = where(done[ref][0], done[ref][1])
            for c in copies:
                if not res and c in done and done[c][0] != sid and now(ref) == as_copy(now(c), ref):
                    res = where(done[c][0], c)
            if not res and voice.get(ref, sid) != sid:
                res = where(voice[ref], ref, pending=True)
            for c in copies:
                if not res and c in above and now(ref) == as_copy(now(c), ref):
                    res = where(sid, c, here=True)
        out.append(res)
        above.setdefault(ref, k)
    return out


def progress():
    """Lines read of all the NPC lines, by textstatus.py's count (decisions in this tool,
    and Guy's flagged scenes), for the bar over the scene list."""
    import textstatus
    status = textstatus.table()
    total = sum(len(SOURCES[n]) for n in NPC_FILES)
    read = sum(1 for n in NPC_FILES for i in range(len(SOURCES[n]))
               if status(f'NPC_MES{n}.OBJ', i)[0] == 'reviewed')
    return {'read': read, 'total': total}


def scene_list():
    out = []
    scenes = all_scenes()
    index = review_index(scenes)
    for sid, s in scenes.items():
        d = read_json(os.path.join(DECISIONS, f'{sid}.json'), {})
        where = settled(sid, scenes, index)
        left = sum(1 for x in where if not x)
        status = d.get('status', 'open')
        if status == 'open' and not left:   # nothing to read here: every line was read
            status = 'moved' if any(x['pending'] for x in where) else 'covered'   # or waits in a voice scene
        out.append({'id': s['id'], 'file': s['file'], 'number': s.get('number'), 'title': s['title'],
                    'kind': s.get('kind', 'scene'),
                    'priority': s.get('priority'), 'order': s.get('order', 999),
                    'status': status, 'lines': len(s['lines']), 'left': left})
    # within a party: voice scenes (each character's parts together), then scenes, then read-throughs
    rank = {'voice': 0, 'readthrough': 2}
    return sorted(out, key=lambda s: (s['file'], rank.get(s['kind'], 1), s['id'] if s['kind'] == 'voice' else '',
                                      s['order'], s['number'] or 0))


def scene(sid):
    scenes = all_scenes()
    s = scenes.get(sid)
    if not s:
        return None
    for line, where in zip(s['lines'], settled(sid, scenes)):
        line['done_in'] = where
        n, i = parse_ref(line['ref'])
        line['jp'] = SOURCES[n][i]
        line['current'] = current(line['ref'])
        line['copies'] = copies_of(line['ref'])
        if not line.get('plays'):
            line['plays_auto'] = auto_plays(line['ref'])
        line['others'] = others_asked(line['ref'])
        if s.get('kind') == 'readthrough':   # Chris reads the lines as they are, unless a
            line.setdefault('faithful', line['current'])   # lesson proposes a fix (lessons.py)
            line.setdefault('literal', '')
    s['decision'] = read_json(os.path.join(DECISIONS, f'{sid}.json'))
    qs = read_json(QUESTIONS, [])
    s['questions'] = [q for q in qs if q.get('scene') == sid]
    for line in s['lines']:   # a line's thread: questions on it or on its copies, from any scene
        refs = [line['ref']] + line['copies']
        line['questions'] = [q for q in qs if q.get('ref') in refs]
    places = scene_places()
    places['map'] = map_places()
    for line in s['lines']:
        line['elsewhere'] = [elsewhere(line, r, 'copy', None, places) for r in line['copies']] + \
            [elsewhere(line, x['ref'], 'related', x.get('note'), places) for x in line.get('related') or []
             if x.get('ref') and x['ref'] not in line['copies'] and x['ref'] != line['ref']]
    return s


ARRAY_WORDS = {'chat': 'Talk', 'greeting': 'Greeting', 'farewell': 'Leaving', 'introductions': 'Introductions',
               'healing': 'Healing offer', 'sale': 'Sale offer', 'rescue': 'Rescue offer', 'fight': 'Fight'}


# The code map's conditions (docs/re/C-talk-lines.md) in a player's words. A party's
# story stage moves on the first time you reach a deeper area (MAZE 0x800a45b0); Zaril's
# leaving (Fontana handler 20) moves Fontana to 3 and Balbo to 2, and the control-room
# battle (handler 25) moves Cresson to 2 (docs/re/C-talk.md, npc_stage).
STAGES = {
    'Guy': {'1': 'before you reach the Underground Shrine',
            '2': 'after you reach the Underground Shrine, before Area B',
            '3': 'after you reach Area B',
            '12': 'before you reach Area B', '23': 'after you reach the Underground Shrine'},
    'Balbo': {'1': 'before you reach Area B or see Zaril leave Fontana\'s party',
              '2': 'after you reach Area B or see Zaril leave Fontana\'s party, before Area C',
              '3': 'after you reach Area C',
              '12': 'before you reach Area C', '23': 'after you reach Area B or see Zaril leave'},
    'Fontana': {'1': 'before you reach Area A',
                '2': 'after you reach Area A, before Area B or Zaril leaving',
                '3': 'after you reach Area B or Zaril leaves the party',
                '12': 'before you reach Area B or Zaril leaves', '23': 'after you reach Area A'},
    'scholars': {'1': 'before the control-room battle', '2': 'after the control-room battle'},
}
TABLET = "while the matching stone isn't set in the Tablet of the Sun yet"
PLAIN = {
    # healing offers
    'healthy': "when you pick someone who doesn't need healing",
    'cancelled': 'when you turn the offer down',
    "can't treat": "when they can't treat what's wrong",
    'out of magic (20%)': "when they're out of magic, a 1-in-5 chance each time",
    'out of magic, or stage 1 stone/dead': "when they're out of magic, or when someone is stoned or dead {1}",
    'stage 1 HP': 'when someone is hurt, {1}',
    'stage 2 HP': 'when someone is hurt, {2}',
    'stage 3 HP': 'when someone is hurt, {3}',
    'stages 1-2 HP': 'when someone is hurt, {12}',
    'stage 1, any status': 'when someone has a status ailment, {1}',
    'stage 1, paralysis': 'when someone is paralyzed, {1}',
    'stage 1, poison': 'when someone is poisoned, {1}',
    'stage 1, stone/dead': 'when someone is stoned or dead, {1}',
    'stage 2, dead': 'when someone is dead, {2}',
    'stage 2, paralysis': 'when someone is paralyzed, {2}',
    'stage 2, stone/dead/poison': 'when someone is stoned, dead or poisoned, {2}',
    'stage 3, paralysis': 'when someone is paralyzed, {3}',
    'stage 3, poison': 'when someone is poisoned, {3}',
    'stage 3, stone/dead': 'when someone is stoned or dead, {3}',
    'stage 3, poison/paralysis/stone': 'when someone is poisoned, paralyzed or stoned, {3}',
    'stage 3, dead or ashes: Kadorto (always works)': 'when someone is dead or ashes, {3}; they cast Kadorto, which always works',
    'stage 2, dead or ashes: Kadorto (always works)': 'when someone is dead or ashes, {2}; they cast Kadorto, which always works',
    'stages 1-2, dead or ashes': 'when someone is dead or ashes, {12}',
    'stages 1-2, paralysis': 'when someone is paralyzed, {12}',
    'stages 1-2, poison': 'when someone is poisoned, {12}',
    'paralysis (stages 2-3)': 'when someone is paralyzed, {23}',
    'HP: Madi': 'when someone is hurt; they cast Madi',
    'status: Madi': 'when someone has a status ailment; they cast Madi',
    'poison/paralysis/stone: Madi': 'when someone is poisoned, paralyzed or stoned; they cast Madi',
    'dead or ashes: Kadorto (always works)': 'when someone is dead or ashes; they cast Kadorto, which always works',
    'never (needs stages 2 and 3 at once)': ('when someone is poisoned, paralyzed or stoned, {23}. The original game '
                                              'never played it, because its check could never pass; the patch fixed that'),
    'stage 3 HP in the original game (bug: 2:135 with Madi; 2:134 meant; the patch plays 2:134 there, 54596b4)':
        ('when someone was hurt {3}, in the original game only, by mistake; '
         'the patch plays the right line (2:134) there'),
    # greetings
    'first meeting': 'the first time you meet them',
    'first meeting, Guy Good': 'the first time you meet them, while Guy is Good',
    'first meeting, Guy Evil': 'the first time you meet them, while Guy is Evil',
    'first meeting, compatible': "the first time you meet them, if your party's alignments sit well with Balbo's",
    'first meeting, incompatible': "the first time you meet them, if your party's alignments don't sit well with Balbo's",
    'Guy turned Evil, compatible, met before': ("after Guy turns Evil, if you've met before and your party's "
                                                "alignments sit well with his"),
    'Balbo turned Good': 'after Balbo turns Good',
    'Balbo back to Evil': 'after Balbo turns back to Evil',
    'maze changed': 'after the maze changes',
    'maze changed, introduced': "after the maze changes, if they've introduced themselves",
    'maze changed, not introduced': "after the maze changes, if they haven't introduced themselves",
    'not introduced': "before they've introduced themselves",
    'seen, not introduced': "if you've seen them before but they haven't introduced themselves",
    'first visit': 'your first visit',
    'stage 2, Cresson alone, met': "{2}, when Cresson is alone and you've met him",
    'stage 2, Cresson alone, not met': "{2}, when Cresson is alone and you haven't met him",
    'Zaril greets': 'when Zaril is the one who greets you',
    'Gaura or Fritillaria greets': 'when Gaura or Fritillaria is the one who greets you',
    'Fritillaria introduces himself': 'when Fritillaria introduces himself',
    'Lilia introduces herself': 'when Lilia introduces herself',
    'the reward: gave the Ruby Slippers, not yet rewarded (+10,000 G)':
        'the first time you meet them after giving Guy the Ruby Slippers; they pay you 10,000 G',
    'never picked': 'the game never picks this one',
    # chat
    'stage 1 special (90%)': '{1}; a special topic, picked 9 times in 10 when it comes up',
    'stage 1, progress_bits < 0x200, outside the location areas': '{1}, anywhere without a topic of its own',
    'progress_bits & 0x200 and a member with flag +0xc5 bit 0':
        "after the ending, when someone in your party has the King's title",
    'areas 1-4 before the walls change': 'in the Shrine Interior, before the walls change',
    'areas 0x13-0x16 after the maze changes': 'in Area A, after the maze changes',
    "areas 0x17-0x1b without the Tablet's stone bit 2": f'in Area B, {TABLET}',
    'areas 0x20-0x23 before the maze changes': 'in Area D, before the maze changes',
    'stage 3, areas 5-8, Tablet stone bit 4 missing': f'{{3}}, in the Underground Shrine, {TABLET}',
    'stage 3, areas 0x13-0x16, stone bit 0x20 missing': f'{{3}}, in Area A, {TABLET}',
    'stage 3, areas 0x1c-0x1f, stone bit 0x80 missing': f'{{3}}, in Area C, {TABLET}',
}
# Blocks the original game never picked and the patch opened up (bugs.md).
REOPENED = {'h2 Fontana chat [8]': 'The original game never picked this topic; the patch adds it at Fontana\'s '
                                   'last stage (bugs.md 2.5)'}


def plain(note, key):
    """A code-map condition in a player's words, or the note itself if it isn't in PLAIN."""
    text = PLAIN.get(note)
    if text is None:
        return note
    who = next((p for p in STAGES if f' {p} ' in key), None)
    stages = STAGES.get(who, {})
    return re.sub(r'\{(\d+)\}', lambda m: stages.get(m.group(1), f'at stage {m.group(1)}'), text)


RUN_TIME = [('farewell', 'When you leave them'),
            ('introduced greeting', 'A greeting once you know them, picked by who is in your party'),
            ('greetings by speaker', 'A greeting when you meet them')]


def talk_blocks():
    """ref -> [(block key, note)] and block key -> [refs], from docs/re/C-talk-lines.md
    (scripts/re/talklines.py), read once. A block key is like "h1 Balbo chat [6]"."""
    if not hasattr(talk_blocks, 'by_ref'):
        by_ref, by_block = {}, {}
        path = os.path.join(CODE_ROOT, 'docs/re/C-talk-lines.md')
        for row in open(path, encoding='utf-8') if os.path.exists(path) else []:
            m = re.match(r'\| ([1-5]:\d+) \| .*? \| (.*) \|\s*$', row)
            if not m:
                continue
            for place in m.group(2).split('<br>'):
                key, _, note = place.partition(':')
                key = key.strip()
                if not re.search(r'\[\d+\]$', key):   # picked at run time: say what kind of moment
                    for word, said in RUN_TIME:
                        if word in place:
                            by_ref.setdefault(m.group(1), []).append((None, said))
                            break
                    continue
                by_ref.setdefault(m.group(1), []).append((key, note.strip()))
                by_block.setdefault(key, []).append(m.group(1))
        talk_blocks.by_ref, talk_blocks.by_block = by_ref, by_block
    return talk_blocks.by_ref, talk_blocks.by_block


def auto_plays(ref):
    """'When it plays' from the code map, for lines without a hand-written one: the kind of
    exchange and the narration line that sets it up ("We asked about other parties.")."""
    by_ref, by_block = talk_blocks()
    out, seen = [], set()
    for key, note in by_ref.get(ref, []):
        if key is None:
            if note not in seen:
                seen.add(note)
                out.append(note)
            continue
        kind = next((w for a, w in ARRAY_WORDS.items() if f' {a} [' in key), None)
        if not kind:
            continue
        narr = [r for r in by_block.get(key, []) if r != ref and '"' not in current(r)
                and '\n' not in current(r).strip()]
        said = ''.join(f'"{current(r).strip()}" ({r}), then this line' for r in narr[:1])
        text = (f'When you Talk: {said}' if kind == 'Talk' else f'{kind}: {said}') if said else kind
        if 'rerolled' in note:
            text += '. The original game never played this topic; the patch reopened it (bugs.md 1.8)'
        elif '(shifted' in note:   # Cephala's healing blocks, one off in the original (34cd45c)
            text += ('. The original game played this one case off, for the next situation along; '
                     'the patch fixed that, so it plays where its words say')
        elif key in REOPENED:
            text += '. ' + REOPENED[key]
        elif note in PLAIN:
            p = plain(note, key)
            text += f'. {p[0].upper()}{p[1:]}' if said else f', {p}'
        elif note and 'run time' not in note:
            text += f' ({note})'
        if text not in seen:
            seen.add(text)
            out.append(text)
    never = [t for t in out if t.endswith(', ' + PLAIN['never picked'])]
    if len(never) < len(out):   # another block plays it, so the unpicked copy says nothing
        out = [t for t in out if t not in never]
    out.sort(key=lambda t: 'original game' in t)   # the usual case first, the bug note after
    merged = []   # "Healing offer, when A" and "Healing offer, when B" read as one
    for t in out:
        kind, sep, cond = t.partition(', ')
        prev = next((i for i, m in enumerate(merged) if sep and (m.startswith(kind + ', ') or m == kind)), None)
        if prev is None:
            merged.append(t)
        elif merged[prev] == kind:   # a block with no condition, and one with
            merged[prev] += f'; also {cond}'
        else:
            merged[prev] += f'; or {cond}'
    return '. '.join(merged[:2]) + '.' if merged else ''


def moments():
    """docs/re/moments.json: greetings, farewells and services grouped by the game moment
    they play in, across all five files: {key: {label, refs}}. Read once."""
    if not hasattr(moments, 'by_ref'):
        data = read_json(os.path.join(ROOT, 'docs/re/moments.json'), {}).get('moments', {})
        moments.data, moments.by_ref = data, {}
        for key, m in data.items():
            for r in m.get('refs', []):
                moments.by_ref.setdefault(r, []).append(key)
    return moments.data, moments.by_ref


def others_asked(ref):
    """How the other characters speak at the same point, so a line can be read against its
    siblings: [{title, lines: [{ref, speaker, party, current}]}]. The rest of the party's
    answers in the same talk exchange (a chat topic or the introductions), and the other
    characters' lines in the same moment (moments()), in any party. Narration and the
    speaker's own other lines are left out."""
    by_ref, by_block = talk_blocks()
    me, groups, seen = person(ref), [], {ref}

    def item(r):
        cur = current(r)
        who = cur.split('\n', 1)[0] if '\n' in cur and cur.split('\n', 1)[1].startswith('"') else None
        if r in seen or (me and person(r) == me):
            return None
        seen.add(r)
        n, _ = parse_ref(r)
        return {'ref': r, 'speaker': who or '(no speaker line)', 'party': FILE_PARTY.get(n), 'current': cur}

    talk = []
    for key, _ in by_ref.get(ref, []):
        if key and any(f' {w} [' in key for w in ('chat', 'introductions')):
            talk += [x for x in (item(r) for r in by_block.get(key, []) if '"' in current(r)) if x]
    if talk:
        groups.append({'title': 'Others asked the same', 'lines': talk})
    data, mby = moments()
    for key in mby.get(ref, []):
        lines = [x for x in (item(r) for r in data[key]['refs']) if x]
        if lines:
            groups.append({'title': 'Same moment, other characters', 'about': data[key].get('label', ''), 'lines': lines})
    return groups


FILE_PARTY = {1: "Guy's party", 2: "Balbo's party", 3: "Fontana's party", 4: 'The scholars', 5: "Zaril's party"}


def scene_places():
    """Every ref a scene has: the first scene (by id) and line index, and its context."""
    out = {}
    for name in sorted(os.listdir(SCENES)) if os.path.isdir(SCENES) else []:
        if name.endswith('.json'):
            sc = read_json(os.path.join(SCENES, name)) or {'lines': []}
            for k, ln in enumerate(sc.get('lines', [])):
                out.setdefault(ln['ref'], {'scene': sc.get('id'), 'title': sc.get('title'), 'index': k,
                                           'context': ln.get('context')})
    return out


def map_places():
    """Each ref's section in docs/npc-map.md ("**5.1 Unnamed greetings and farewells
    (0-7).**"), for lines no scene has."""
    out = {}
    try:
        text = open(os.path.join(ROOT, 'docs/npc-map.md'), encoding='utf-8').read()
    except FileNotFoundError:
        return out
    for m in re.finditer(r'^\*\*([1-5])\.\d+ ([^*]+?) \(([\d, -]+)\)\.\*\*', text, re.M):
        n, title = int(m.group(1)), m.group(2).strip()
        for part in m.group(3).split(','):
            a, _, b = part.strip().partition('-')
            if a.isdigit():
                for i in range(int(a), int(b or a) + 1):
                    out.setdefault(f'{n}:{i}', title)
    return out


def elsewhere(line, ref, kind, note, places):
    """What the page shows about another line from this one's Elsewhere row."""
    n, i = parse_ref(ref)
    cur = current(ref)
    place = places.get(ref) or {}
    return {'ref': ref, 'kind': kind, 'note': note, 'file': n, 'party': FILE_PARTY.get(n, f'NPC_MES{n}'),
            'speaker': cur.split('\n', 1)[0] if '\n' in cur and cur.split('\n', 1)[1].startswith('"') else None,
            'context': place.get('context') or places.get('map', {}).get(ref), 'scene': place.get('scene'), 'scene_title': place.get('title'),
            'index': place.get('index'), 'jp': SOURCES[n][i], 'current': cur,
            'same_now': cur == as_copy(line['current'], ref)}


def allowed_copies(sid, ref):
    """Refs an apply may change along with ref: its copies, and the lines its scene lists
    as related (when Chris ticks them)."""
    sc = read_json(os.path.join(SCENES, f'{sid}.json')) or {'lines': []}
    rel = [x.get('ref') for ln in sc['lines'] if ln['ref'] == ref for x in ln.get('related') or []]
    return set(copies_of(ref)) | set(r for r in rel if r)


def cast():
    c = read_json(os.path.join(HERE, 'cast.json'))
    for p in c['people']:
        if os.path.exists(os.path.join(FACES, f"{p['id']}.png")):
            p['face'] = f"/faces/{p['id']}.png"
    return c


def fontpack():
    """What the page needs to draw the box itself as you type: descfit's encoder tables
    and the glyph widths (the same ones fit() measures with)."""
    return {'chars': descfit.CHARS, 'digraphs': descfit.DIGRAPHS, 'lut': list(descfit.LUT),
            'width': npcfit.WIDTH, 'lines': npcfit.LINES}


def apply(body):
    sid, lines, note = body['scene'], body['lines'], body.get('note', '')
    if not read_json(os.path.join(SCENES, f'{sid}.json')):
        raise ValueError('no such scene')
    with LOCK:
        changes, record = {}, []
        for ln in lines:
            ok = allowed_copies(sid, ln['ref'])
            refs = [ln['ref']] + [r for r in ln.get('copies', []) if r in ok and r != ln['ref']]
            before = current(ln['ref'])
            text = before if ln['choice'] == 'current' else ln['text']
            if ln['choice'] != 'current':
                n, i = parse_ref(ln['ref'])
                text = npcquotes.close(text, SOURCES[n][i])
            if text != before:
                for r in refs:
                    changes[r] = as_copy(text, r) if r != ln['ref'] else text
            for r in (refs if text != before else refs[:1]):
                f = fit(r, changes.get(r, text))
                if not f['ok']:
                    raise ValueError(f"{r} doesn't fit: {'; '.join(f['hard'])}")
            rec = {'ref': ln['ref'], 'choice': ln['choice'], 'before': before, 'after': text,
                   'copies': refs[1:] if text != before else [], 'note': ln.get('note', '')}
            if text == before:   # ticked copies that already read the same were read with it
                rec['carried'] = [r for r in refs[1:] if current(r) == as_copy(text, r)]
            record.append(rec)
        prior = read_json(os.path.join(DECISIONS, f'{sid}.json'))
        if prior and not changes:
            return prior  # nothing new; keep the earlier record (and its commit)
        files = {}
        for r, text in changes.items():
            n, i = parse_ref(r)
            files.setdefault(n, load_tr(n))['sections'][0]['strings'][i]['translation'] = text
        for n, data in files.items():
            open(tr_path(n), 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=4))
        os.makedirs(DECISIONS, exist_ok=True)
        decision = {'scene': sid, 'status': 'applied' if changes else 'kept',
                    'applied_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'note': note,
                    'changed': sorted(changes), 'lines': record}
        if prior:  # a follow-up apply: keep what came before
            decision['earlier'] = [{k: v for k, v in prior.items() if k != 'earlier'}] + prior.get('earlier', [])
        json.dump(decision, open(os.path.join(DECISIONS, f'{sid}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
    return decision


def ask(body):
    with LOCK:
        qs = read_json(QUESTIONS, [])
        q = {'id': (max((x['id'] for x in qs), default=0) + 1), 'scene': body.get('scene'),
             'ref': body.get('ref'), 'about': body.get('about', ''), 'question': body['question'].strip(),
             'asked_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'answer': None}
        qs.append(q)
        json.dump(qs, open(QUESTIONS, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return q


# --- HTTP -----------------------------------------------------------------------------

TYPES = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
         '.js': 'text/javascript; charset=utf-8', '.png': 'image/png', '.json': 'application/json',
         '.svg': 'image/svg+xml'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if '/api/' in (args[0] if args else '') and ' 200 ' not in fmt % args:
            sys.stderr.write(fmt % args + '\n')

    def send(self, code, body, ctype='application/json'):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def file(self, base, rel):
        path = os.path.realpath(os.path.join(base, rel))
        if not path.startswith(os.path.realpath(base) + os.sep) or not os.path.isfile(path):
            return self.send(404, {'error': 'not found'})
        self.send(200, open(path, 'rb').read(), TYPES.get(os.path.splitext(path)[1], 'application/octet-stream'))

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == '/':
                return self.file(STATIC, 'index.html')
            if u.path.startswith('/static/'):
                return self.file(STATIC, u.path[len('/static/'):])
            if u.path.startswith('/font/'):
                return self.file(FONT, u.path[len('/font/'):])
            if u.path.startswith('/faces/'):
                return self.file(FACES, u.path[len('/faces/'):])
            if u.path == '/api/fontpack':
                return self.send(200, fontpack())
            if u.path == '/api/gloss':
                sc = read_json(os.path.join(SCENES, f"{q.get('scene', '')}.json"), {'lines': []})
                line = next((ln for ln in sc['lines'] if ln['ref'] == q.get('ref')), None)
                return self.send(200, gloss(q.get('ref', ''), line))
            if u.path == '/api/state':
                return self.send(200, {'cast': cast(), 'voices': voices(),
                                       'scenes': scene_list(), 'progress': progress(), 'splitter': bool(TAGGER), 'dictionary': bool(DB),
                                       'role_sources': ROLE['sources'], 'role_about': ROLE['about']})
            if u.path == '/api/scene':
                s = scene(q.get('id', ''))
                return self.send(200, s) if s else self.send(404, {'error': 'no such scene'})
            if u.path == '/api/tokens':
                return self.send(200, tokens(q.get('text', '')))
            if u.path == '/api/lookup':
                return self.send(200, lookup(q.get('q', ''), q.get('lemma')))
            if u.path == '/api/concordance':
                return self.send(200, concordance(q.get('q', ''), q.get('ref')))
            if u.path == '/api/questions':
                return self.send(200, read_json(QUESTIONS, []))
            self.send(404, {'error': 'not found'})
        except ValueError as e:
            self.send(400, {'error': str(e)})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
            if u.path == '/api/fit':   # as_copy: the text as ref would show it, with ref's own speaker
                text = as_copy(body['text'], body['ref']) if body.get('as_copy') else body['text']
                return self.send(200, {**fit(body['ref'], text), 'text': text})
            if u.path == '/api/rewrap':
                text = rewrap(body['text'])
                return self.send(200, {'text': text, **fit(body['ref'], text)})
            if u.path == '/api/apply':
                return self.send(200, apply(body))
            if u.path == '/api/ask':
                return self.send(200, ask(body))
            self.send(404, {'error': 'not found'})
        except (ValueError, KeyError) as e:
            self.send(400, {'error': str(e)})


def main():
    port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 8777
    host = sys.argv[sys.argv.index('--host') + 1] if '--host' in sys.argv else '127.0.0.1'
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f'review tool on http://localhost:{port}  (splitter: {"on" if TAGGER else "off"}, '
          f'dictionary: {"on" if DB else "off; run mkdict.py"})')
    srv.serve_forever()


if __name__ == '__main__':
    main()
