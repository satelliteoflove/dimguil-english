#!/usr/bin/env python3
"""Close the quotes in NPC dialogue (NPC_MES1-5).

    npcquotes.py                  close them in translations/NPC_MESn.OBJ.json
    npcquotes.py --overlay FILE   close them in an overlay ({"n:idx": text}) in place
    npcquotes.py --check          list speech that isn't closed, change nothing

The Japanese opens each speech with 「 and never closes it; the English followed it, so
the box showed an opening " and no closing one. Every box of speech now opens and
closes its quote:
  - a box with a speaker line ("Balbo\\n\\"...") closes at the end of the speech;
  - a reply with no speaker line (shown after a yes/no prompt, or the next box of a long
    speech) opens with " in place of its leading space, where the Japanese has a space
    in place of 「, and closes too. Narration in the same files starts with two or
    more spaces in the Japanese and is left alone;
  - a healing box ends on the spell's name, centered and colored on its own line; the
    quote closes before it, since the spell isn't spoken;
  - {ff40} ends the string, so a quote closes before it.
A page break inside one box doesn't reopen the quote. npcapply.py runs this on what it
applies, so a reviewed scene keeps its closing quotes.
"""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
SPELL = re.compile(r'\n\r?[ ]*\{ff30\}2[^{\n]*\{ff30\}0\s*$')


def is_reply(source):
    """A speech box without a speaker line: one leading space, as in the Japanese."""
    return bool(re.match(r' [^ \n]', source or ''))


def close(text, source):
    if not text:
        return text
    speaker = '\n"' in text.split('\r')[0] and not text.startswith(' ')
    reply = not speaker and (text.startswith('"') or text.startswith(' ') and is_reply(source))
    # narration that turns into speech on a later page (4:55, the shadow's challenge)
    spoken = not (speaker or reply) and '\r"' in text
    if not (speaker or reply or spoken):
        return text
    if reply and not text.startswith('"'):
        text = '"' + text[1:]
    cut = len(text)
    if '{ff40}' in text:
        cut = text.index('{ff40}')
    else:
        m = SPELL.search(text)
        if m:
            cut = m.start()
    head, tail = text[:cut], text[cut:]
    body = head.rstrip()
    if body.endswith('"') and body.count('"') % 2 == 0:
        return text
    return body + '"' + head[len(body):] + tail


def sources(n):
    d = json.load(open(os.path.join(ROOT, f'rips/stage/out/dumps/NPC_MES{n}.OBJ.json'), encoding='utf-8'))
    return [s['source'] for s in d['sections'][0]['strings']]


def main():
    args = sys.argv[1:]
    if '--overlay' in args:
        path = args[args.index('--overlay') + 1]
        ov = json.load(open(path, encoding='utf-8'))
        src = {n: sources(n) for n in range(1, 6)}
        changed = 0
        for key, text in ov.items():
            n, idx = map(int, key.split(':'))
            new = close(text, src[n][idx])
            changed += new != text
            ov[key] = new
        open(path, 'w', encoding='utf-8').write(json.dumps(ov, ensure_ascii=False, indent=1))
        print(f'{path}: {changed} of {len(ov)} closed')
        return
    check = '--check' in args
    for n in range(1, 6):
        path = os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json')
        data = json.load(open(path, encoding='utf-8'))
        strings = data['sections'][0]['strings']
        changed = []
        for idx, (s, source) in enumerate(zip(strings, sources(n))):
            new = close(s.get('translation') or '', source)
            if new != (s.get('translation') or ''):
                changed.append(idx)
                s['translation'] = new
        if check:
            for idx in changed:
                print(f'{n}:{idx} not closed')
        elif changed:
            open(path, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=4))
        print(f'NPC_MES{n}: {len(changed)} {"to close" if check else "closed"}')


if __name__ == '__main__':
    main()
