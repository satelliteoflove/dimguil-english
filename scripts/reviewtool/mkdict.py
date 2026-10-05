#!/usr/bin/env python3
"""Build the review tool's dictionary: rips/dict/dict.sqlite.

    mkdict.py

Downloads (once) into rips/dict/, none of it into the repo:
  - JMdict_e and KANJIDIC2 (EDRDG, CC BY-SA 4.0): glosses and part-of-speech tags,
    kanji readings and meanings
  - English Wiktionary's Japanese entries, as extracted by kaikki.org (CC BY-SA 4.0):
    more senses than JMdict (あの人 "my husband, partner (of a female speaker)"),
    usage labels, etymology and examples
  - Tatoeba's Japanese sentences with their English translations (CC BY 2.0 FR): words
    in real use
The tool credits each source on every lookup. None of this replaces the researched
notes in a scene; it's a way to check them.

JMdict's entity tags (arch, hon, male, fem, col, ...) are kept with their DTD
descriptions: for role language they matter as much as the glosses.
"""
import bz2, gzip, json, os, re, sqlite3, sys, tarfile, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
DIR = os.path.join(ROOT, 'rips/dict')
SOURCES = {'JMdict_e.gz': 'http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz',
           'kanjidic2.xml.gz': 'http://www.edrdg.org/kanjidic/kanjidic2.xml.gz',
           'wiktionary-ja.jsonl.gz': 'https://kaikki.org/dictionary/Japanese/kaikki.org-dictionary-Japanese.jsonl.gz',
           'jpn_sentences.tsv.bz2': 'https://downloads.tatoeba.org/exports/per_language/jpn/jpn_sentences.tsv.bz2',
           'eng_sentences.tsv.bz2': 'https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2',
           'links.tar.bz2': 'https://downloads.tatoeba.org/exports/links.tar.bz2'}


def fetch():
    os.makedirs(DIR, exist_ok=True)
    for name, url in SOURCES.items():
        path = os.path.join(DIR, name)
        if not os.path.exists(path):
            print('downloading', url)
            urllib.request.urlretrieve(url, path)


def parse_jmdict(db):
    raw = gzip.open(os.path.join(DIR, 'JMdict_e.gz'), 'rt', encoding='utf-8').read()
    ents = dict(re.findall(r'<!ENTITY (\S+) "([^"]*)">', raw))
    # ElementTree can't expand DTD entities; keep the tag name, look the text up later.
    body = re.sub(r'&([\w-]+);', lambda m: m.group(1) if m.group(1) in ents else m.group(0),
                  raw[raw.index('<JMdict>'):])
    db.execute('create table tags (tag text primary key, text text)')
    db.executemany('insert into tags values (?, ?)', ents.items())
    db.execute('create table entry (id integer primary key, kanji text, kana text, sense text, rank integer)')
    db.execute('create table form (form text, id integer, kind text)')
    n = 0
    for el in ET.fromstring(body).iter('entry'):
        eid = int(el.findtext('ent_seq'))
        kanji = [{'k': k.findtext('keb'), 'pri': [p.text for p in k.findall('ke_pri')],
                  'inf': [p.text for p in k.findall('ke_inf')]} for k in el.findall('k_ele')]
        kana = [{'r': r.findtext('reb'), 'pri': [p.text for p in r.findall('re_pri')],
                 'inf': [p.text for p in r.findall('re_inf')],
                 'restr': [p.text for p in r.findall('re_restr')]} for r in el.findall('r_ele')]
        senses = []
        for s in el.findall('sense'):
            senses.append({'pos': [p.text for p in s.findall('pos')],
                           'gloss': [g.text for g in s.findall('gloss')],
                           'misc': [p.text for p in s.findall('misc')],
                           'field': [p.text for p in s.findall('field')],
                           'dial': [p.text for p in s.findall('dial')],
                           'info': [p.text for p in s.findall('s_inf')],
                           'xref': [p.text for p in s.findall('xref')]})
        pri = {p for k in kanji for p in k['pri']} | {p for r in kana for p in r['pri']}
        rank = 0 if pri & {'news1', 'ichi1', 'spec1', 'gai1'} else 1 if pri else 2
        db.execute('insert into entry values (?, ?, ?, ?, ?)', (eid, json.dumps(kanji, ensure_ascii=False),
                   json.dumps(kana, ensure_ascii=False), json.dumps(senses, ensure_ascii=False), rank))
        db.executemany('insert into form values (?, ?, ?)',
                       [(k['k'], eid, 'k') for k in kanji] + [(r['r'], eid, 'r') for r in kana])
        n += 1
    db.execute('create index form_i on form (form)')
    return n


def parse_kanjidic(db):
    root = ET.parse(gzip.open(os.path.join(DIR, 'kanjidic2.xml.gz'))).getroot()
    db.execute('create table kanji (lit text primary key, data text)')
    n = 0
    for c in root.iter('character'):
        rm = c.find('reading_meaning')
        d = {'grade': c.findtext('misc/grade'), 'strokes': c.findtext('misc/stroke_count'),
             'freq': c.findtext('misc/freq'), 'jlpt': c.findtext('misc/jlpt'),
             'on': [], 'kun': [], 'meanings': [], 'nanori': []}
        if rm is not None:
            for g in rm.findall('rmgroup'):
                d['on'] += [r.text for r in g.findall('reading') if r.get('r_type') == 'ja_on']
                d['kun'] += [r.text for r in g.findall('reading') if r.get('r_type') == 'ja_kun']
                d['meanings'] += [m.text for m in g.findall('meaning') if m.get('m_lang') is None]
            d['nanori'] = [n_.text for n_ in rm.findall('nanori')]
        db.execute('insert into kanji values (?, ?)', (c.findtext('literal'), json.dumps(d, ensure_ascii=False)))
        n += 1
    return n


def parse_wiktionary(db):
    db.execute('create table wikt (id integer primary key, word text, pos text, data text)')
    db.execute('create table wikt_form (form text, id integer, kind text)')  # w headword, r reading
    n = 0
    for line in gzip.open(os.path.join(DIR, 'wiktionary-ja.jsonl.gz'), 'rt', encoding='utf-8'):
        d = json.loads(line)
        senses = [{'glosses': x.get('glosses', []), 'tags': x.get('tags', []),
                   'qualifier': x.get('qualifier'),
                   'examples': [{'text': e.get('text'), 'english': e.get('english') or e.get('translation')}
                                for e in x.get('examples', [])[:3]]}
                  for x in d.get('senses', []) if x.get('glosses')]
        if not senses:
            continue
        n += 1
        heads = {d['word']} | {f['form'] for f in d.get('forms', []) if 'canonical' in f.get('tags', [])}
        reads = {f['form'] for f in d.get('forms', []) if 'hiragana' in f.get('tags', [])}
        for f in d.get('forms', []):  # the reading, built from the ruby
            if f.get('ruby') and 'canonical' in f.get('tags', []):
                reads.add(''.join(r[1] for r in f['ruby']))
        data = {'senses': senses, 'etymology': (d.get('etymology_text') or '')[:600]}
        db.execute('insert into wikt values (?, ?, ?, ?)', (n, d['word'], d.get('pos'), json.dumps(data, ensure_ascii=False)))
        db.executemany('insert into wikt_form values (?, ?, ?)',
                       [(f, n, 'w') for f in heads if f] + [(f, n, 'r') for f in reads - heads if f])
    db.execute('create index wikt_form_i on wikt_form (form)')
    return n


def parse_tatoeba(db):
    def sentences(name):
        out = {}
        for line in bz2.open(os.path.join(DIR, name), 'rt', encoding='utf-8'):
            sid, _, text = line.rstrip('\n').split('\t', 2)
            out[int(sid)] = text
        return out
    jpn, eng = sentences('jpn_sentences.tsv.bz2'), sentences('eng_sentences.tsv.bz2')
    pairs = {}
    with tarfile.open(os.path.join(DIR, 'links.tar.bz2')) as t:
        f = t.extractfile([m for m in t.getmembers() if m.name.endswith('.csv')][0])
        for line in f:
            a, b = line.split(b'\t')[:2]
            a, b = int(a), int(b)
            if a in jpn and b in eng and a not in pairs:
                pairs[a] = eng[b]
    db.execute('create table example (jp text, en text)')
    db.executemany('insert into example values (?, ?)', [(jpn[a], e) for a, e in pairs.items()])
    return len(pairs)


def main():
    fetch()
    path = os.path.join(DIR, 'dict.sqlite')
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    print('JMdict entries:', parse_jmdict(db))
    print('KANJIDIC2 characters:', parse_kanjidic(db))
    print('Wiktionary entries:', parse_wiktionary(db))
    print('Tatoeba pairs:', parse_tatoeba(db))
    db.commit()


if __name__ == '__main__':
    main()
