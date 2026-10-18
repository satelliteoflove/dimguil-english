#!/usr/bin/env python3
"""The translation review tool: a local web app for reviewing NPC scenes with Chris.

    rips/venv/bin/python scripts/reviewtool/server.py [--port 8777]

Then open http://localhost:8777 (Firefox first). Binds to localhost only, unless
--host ADDR is given (--host 0.0.0.0 to use it from a phone on the home network).

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
Questions Chris asks in the tool go to rips/review/questions.json for Claude to answer.

Needs fugashi and unidic-lite for the word splitter (rips/venv has them); without
them the Japanese still shows, just not split into words.
"""
import json, os, re, sqlite3, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import descfit, npcfit, npcquotes  # noqa: E402
from reviewpage import load as load_commented  # noqa: E402  (some translation files have comments)

SCENES = os.path.join(ROOT, 'rips/review/scenes')
DECISIONS = os.path.join(ROOT, 'rips/review/decisions')
QUESTIONS = os.path.join(ROOT, 'rips/review/questions.json')
FONT = os.path.join(ROOT, 'rips/review/font')
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


SOURCES = {n: load_src(n) for n in NPC_FILES}
COPIES = {}  # Japanese body -> every ref that has it, whoever the speaker
for _n in NPC_FILES:
    for _i, _s in enumerate(SOURCES[_n]):
        COPIES.setdefault(body(_s), []).append(f'{_n}:{_i}')


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
    for r in COPIES[body(SOURCES[n][i])]:
        m, j = parse_ref(r)
        if r != ref and (SOURCES[m][j] == SOURCES[n][i] or (person(r) and person(r) == person(ref))):
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
                      'pos': getattr(f, 'pos1', '') or '', 'form': getattr(f, 'cForm', '') or '',
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


def scene_list():
    out = []
    for name in sorted(os.listdir(SCENES)) if os.path.isdir(SCENES) else []:
        if not name.endswith('.json'):
            continue
        s = read_json(os.path.join(SCENES, name))
        d = read_json(os.path.join(DECISIONS, name), {})
        out.append({'id': s['id'], 'file': s['file'], 'number': s.get('number'), 'title': s['title'],
                    'kind': s.get('kind', 'scene'),
                    'priority': s.get('priority'), 'order': s.get('order', 999),
                    'status': d.get('status', 'open'), 'lines': len(s['lines'])})
    return sorted(out, key=lambda s: (s['order'], s['file'], s['number'] or 0))


def scene(sid):
    s = read_json(os.path.join(SCENES, f'{sid}.json'))
    if not s:
        return None
    for line in s['lines']:
        n, i = parse_ref(line['ref'])
        line['jp'] = SOURCES[n][i]
        line['current'] = current(line['ref'])
        line['copies'] = copies_of(line['ref'])
        if s.get('kind') == 'readthrough':   # nothing proposed: Chris reads the lines as they are
            line['faithful'] = line['current']
            line.setdefault('literal', '')
    s['decision'] = read_json(os.path.join(DECISIONS, f'{sid}.json'))
    qs = read_json(QUESTIONS, [])
    s['questions'] = [q for q in qs if q.get('scene') == sid]
    return s


def apply(body):
    sid, lines, note = body['scene'], body['lines'], body.get('note', '')
    if not read_json(os.path.join(SCENES, f'{sid}.json')):
        raise ValueError('no such scene')
    with LOCK:
        changes, record = {}, []
        for ln in lines:
            refs = [ln['ref']] + [r for r in ln.get('copies', []) if r in copies_of(ln['ref'])]
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
            record.append({'ref': ln['ref'], 'choice': ln['choice'], 'before': before, 'after': text,
                           'copies': refs[1:] if text != before else [], 'note': ln.get('note', '')})
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
            if u.path == '/api/state':
                return self.send(200, {'cast': read_json(os.path.join(HERE, 'cast.json')), 'voices': voices(),
                                       'scenes': scene_list(), 'splitter': bool(TAGGER), 'dictionary': bool(DB),
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
            if u.path == '/api/fit':
                return self.send(200, fit(body['ref'], body['text']))
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
