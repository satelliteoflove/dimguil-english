#!/usr/bin/env python3
"""Flag quotes in public-facing docs that the patch no longer says.

A quote is flagged when it appears in some earlier version of a translation (any
"translation" line git history has removed) but not in the current translations.
That catches a README or announcement still quoting a line that review has since
changed, such as Lilia's "seventeen and holding".

Quotes that were never translation text (section names, file names, the Japanese)
are ignored. So are old quotes a doc gives on purpose: a quote followed by "→" or
"(now" (the release notes' "old" → "new"), one after "dropped", "stopped at" or
"formerly" and a quote in a paragraph that says "Before:". Single words are skipped
(names and labels). To quote old text on purpose, use one of those markers.

  python3 scripts/pubquotes.py          report flagged quotes; exit 1 if any
"""
import glob, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ['README.md', 'CHANGELOG.md', 'docs/README.md',
        'docs/announcement-outline.md', 'docs/release-notes-outline.md']

norm = lambda s: re.sub(r'\s+', ' ', s.replace('\\n', ' ').replace('\\r', ' ')
                        .replace('\\"', '"')).strip().lower().strip(' .,!?…')

def current_text():
    out = []
    for f in glob.glob(os.path.join(ROOT, 'translations', '*.json')):
        s = open(f, encoding='utf-8').read()
        out += re.findall(r'"translation":\s*"((?:[^"\\]|\\.)*)"', s)
    return norm(' | '.join(out))

def removed_text():
    log = subprocess.run(['git', '-C', ROOT, 'log', '-p', '--no-color', '--format=',
                          '--', 'translations/'], capture_output=True, text=True).stdout
    return norm(' | '.join(re.findall(r'^-\s*"translation":\s*"((?:[^"\\]|\\.)*)"',
                                      log, re.M)))

cur, old = current_text(), removed_text()
bad = 0
for doc in DOCS:
    path = os.path.join(ROOT, doc)
    if not os.path.exists(path):
        continue
    para = ''
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        # a list item or blank line starts a new paragraph
        if not line.strip() or re.match(r'\s*(\d+\.|-|\*|#)\s', line):
            para = ''
        for m in re.finditer(r'[“"]([^"”\n]{6,160})[”"]', line):
            q = norm(m.group(1))
            if len(q) < 6 or not re.search(r'[a-z]{3}', q) or ' ' not in q:
                continue
            if q in cur or q not in old:
                continue
            if re.match(r'[^\w]{0,4}(→|\(now\b)', line[m.end():]):
                continue
            if re.search(r'\b(dropped|stopped at|formerly)\W{0,3}$', line[:m.start()].lower()):
                continue
            if 'before' in (para + line[:m.start()]).lower():
                continue
            bad += 1
            print(f'{doc}:{n}: "{m.group(1)}" was in the translation and is not any more')
        para += line
print(f'{bad} stale quote(s)' if bad else 'no stale quotes in the public docs')
sys.exit(1 if bad else 0)
