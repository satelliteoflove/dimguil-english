#!/usr/bin/env python3
"""Count the Japanese text that's still untranslated.

    jpinventory.py            per-file counts and overall percentages
    jpinventory.py --list     also print each string that still needs translating (JP)
    jpinventory.py --report   write every Japanese string with its status to
                              rips/jpinventory.txt (local only: it quotes the Japanese)

Reads the JP dumps in rips/stage/out/dumps (made by scripts/build.sh) and the committed
translations/. Every dumped string whose source has kana or kanji is one of:

  translated     the translation is non-empty, differs from the source and is mostly
                 not Japanese (EVENTMES uses the kanji for one as a dash, so a stray kanji is allowed)
  deliberate     Japanese that doesn't need translating; see EXCLUDE below for why
  needed         everything else

Percentages are translated / (translated + needed), by string and by the number of
Japanese characters in the source. Nothing Japanese is printed without --list/--report.

Text outside the dumped files was checked by hand; OTHER_TEXT lists what was found.
"""
import glob, json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
DUMPS = os.path.join(ROOT, 'rips/stage/out/dumps')
TL = os.path.join(ROOT, 'translations')
REPORT = os.path.join(ROOT, 'rips/jpinventory.txt')

JP = re.compile(r'[\u3040-\u30fb\u30fd-\u30ff\u3400-\u9fff]')  # kana and kanji, not the long-vowel mark
CODE = re.compile(r'\{[0-9a-f]{4}\}|\{[a-z_0-9]+\}')

# Whole files nothing loads: no executable or overlay names them (the card game opens
# CB\ files by name: dat\message.dat, DAT\LCARD.DAT, UNIT0\nn, UNIT1\nn, SND\, TIM\).
UNUSED_FILES = {
    'ITEM_SE.DAT': 'CB/DAT, never opened; 306 item descriptions, an older copy of ITEM.DAT section 6',
    'ITEM_CA.DAT': 'CB/DAT, never opened; item names, already in English',
}

# (file, section firstHeaderAddress, first index, last index, reason)
EXCLUDE = [
    # asm/english_defaults.asm switches Items/Monsters/Spells/Menus to English, so the
    # game reads the built-in English list that sits beside each Japanese one.
    ('STATUS.OBJ', 0, 306, 389, 'Japanese spell names; English list is 222-305'),
    ('STATUS.OBJ', 0, 505, 624, 'Japanese status-screen labels; English set is 102-221'),
    ('STATUS.OBJ', 0, 636, 646, 'Japanese ailment labels; English set is 625-635'),
    ('SISETU.OBJ', 0, 67, 78, 'stat gain/loss with Japanese stat names; English-name set is 44-55'),
    ('ITEM.DAT', 0x5c0eaa, 0, 27, 'Japanese catalog labels (alignment, sex...); English section 0x5c1023'),
    ('ITEM.DAT', 0x5c11bf, 0, 348, 'Japanese item names; the catalog shows English section 0x5c234a'),
    ('M_CATALG.DAT', 0x3bf, 0, 389, 'Japanese monster names; English section 0x1817'),
]
PLACEHOLDERS = {'\u3042\u307e\u308a', '\u30c0\u30df\u30fc'}  # unused slots: amari ("left over"), damii ("dummy")

# Checked outside the dumped files (the Kotlin dumper only reads sections.json):
OTHER_TEXT = [
    ('DATA02 M_DTnnn/MPTnn', 'monster records carry English name slots beside the Japanese'),
    ('DATA02 NPTnn', 'English slots held katakana; fixed by binary/NPTnn.BIN.json'),
    ('BATTLE.BIN', 'embedded monster records (summons); each has English names beside the Japanese'),
    ('JOUKA.BIN', 'debug menu (shop stock, max EXP, story items) and debug names; not reachable'),
    ('MCARD.BIN', 'name-entry blocklist of rude words; never displayed'),
    ('CMENU/CMAIN.BIN', 'Shift-JIS unit records show their English field; prompts patched in asm/cb_strings.asm'),
    ('SLPS_026.91, MAZE.BIN, HAZURE.BIN', 'no Japanese strings found'),
    ('graphics', 'title, copyright, card game READY/START/YOU WIN/YOU LOSE are already English; '
                 'STAFF1/2, LOAD, KODAI, SUNITA, SISETU_0-2 are not plain TIMs and were not checked'),
]


def load(path):
    """json.load that tolerates // and /* */ comments."""
    src = open(path, encoding='utf-8').read()
    tok = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)
    return json.loads(tok.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else '', src))


def jpcount(s):
    return len(JP.findall(s or ''))


def is_translated(src, tr):
    if not tr or tr == src:
        return False
    body = re.sub(r'\s', '', CODE.sub('', tr))
    return jpcount(body) <= 0.2 * max(1, len(body))


def excluded(f, addr, i, src):
    if f in UNUSED_FILES:
        return UNUSED_FILES[f]
    if CODE.sub('', src).strip() in PLACEHOLDERS:
        return 'placeholder slot'
    for ef, ea, lo, hi, why in EXCLUDE:
        if ef == f and ea == addr and lo <= i <= hi:
            return why
    return None


def main():
    if not os.path.isdir(DUMPS):
        sys.exit('no dumps in rips/stage/out/dumps: run scripts/build.sh first')
    listing = '--list' in sys.argv
    lines = []
    tot = {k: [0, 0] for k in ('translated', 'deliberate', 'needed')}
    print(f'{"file":14} {"strings":>7} {"JP":>5} {"done":>5} {"delib":>5} {"needed":>6} {"needed JP chars":>15}')
    for d in sorted(glob.glob(os.path.join(DUMPS, '*.json'))):
        f = os.path.basename(d)[:-5]
        tp = os.path.join(TL, f + '.json')
        T = {s['firstHeaderAddress']: s for s in load(tp)['sections']} if os.path.exists(tp) else {}
        c = {k: [0, 0] for k in tot}
        n = 0
        for s in load(d)['sections']:
            a = s['firstHeaderAddress']
            for i, x in enumerate(s['strings']):
                n += 1
                src = x.get('source') or ''
                if not jpcount(src):
                    continue
                t = T[a]['strings'][i].get('translation') if a in T else None
                why = None
                if is_translated(src, t):
                    k = 'translated'
                elif (why := excluded(f, a, i, src)):
                    k = 'deliberate'
                else:
                    k = 'needed'
                c[k][0] += 1
                c[k][1] += jpcount(src)
                lines.append(f'{k:10} {f} {a:#x}:{i} {why or ""}\n    {src!r}')
                if listing and k == 'needed':
                    print(f'  needed {f} {a:#x}:{i} {src!r}')
        for k in tot:
            tot[k][0] += c[k][0]
            tot[k][1] += c[k][1]
        jp = sum(v[0] for v in c.values())
        print(f'{f:14} {n:7} {jp:5} {c["translated"][0]:5} {c["deliberate"][0]:5} '
              f'{c["needed"][0]:6} {c["needed"][1]:15}')
    done, need = tot['translated'], tot['needed']
    print(f'\nJapanese strings: {sum(v[0] for v in tot.values())}, '
          f'deliberately left: {tot["deliberate"][0]} ({tot["deliberate"][1]} chars)')
    for label, j in (('strings', 0), ('JP characters', 1)):
        pct = 100 * done[j] / max(1, done[j] + need[j])
        print(f'translated by {label}: {done[j]} of {done[j] + need[j]} ({pct:.1f}%), '
              f'needed: {need[j]}')
    print('\nOutside the dumped files:')
    for what, note in OTHER_TEXT:
        print(f'  {what}: {note}')
    if '--report' in sys.argv:
        open(REPORT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
        print(f'\nwrote {os.path.relpath(REPORT, ROOT)}')


if __name__ == '__main__':
    main()
