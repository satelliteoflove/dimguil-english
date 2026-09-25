#!/usr/bin/env python3
"""Export the card battle's card data and art for the reference site.

    cardref.py OUT.json IMGDIR [SCREENS.py] [--monsters MONSTERS.json]

Reads the unmodified extraction (rips/clean/dimguil) and the staged translation files
(rips/stage/translations, which carry both the Japanese source and the English), and
writes one JSON file plus LCARD.DAT's 58 images as lcard_NN.png. SCREENS.py, if given,
holds the Stock Card Details values read off the emulator screen; every decoded Lv 1
stat is checked against it and the export stops on any difference. MONSTERS.json (the
site's data/monsters/dim/ps.json) supplies, for each unit, the anchors of every monster
record with the same Japanese name.

Layouts, all verified against the game's screens (see the research note):
  CMENU.BIN 0x424  password table, 12 bytes per unit record (10 ASCII capitals + 2 zeros)
  CMENU.BIN 0x910  EXP scale, 16 bytes, x50 = EXP needed for Lv 2
  CMENU.BIN 0x920  Lv 1 templates, 12 bytes, indexed by record + 1 (entry 0 is empty):
                   +0 HP, +1 MP, +3 low nibble x2 Atk, +3 high nibble x2 Magic,
                   +4 low nibble x2 Def, +5..+8 M.Defense % (Mag Pri Alc Psi),
                   +9 high nibble EXP scale step, +9 low nibble Special
  CMENU.BIN 0xB00  Option Card level-up bonus, 6 bytes per kind (HP MP Atk Def Magic M.Def)
  CMENU.BIN 0xC5A  unit records, 0x32 bytes: 16 Japanese name, 16 English name,
                   +0x20 race, +0x21 size (1/2/4 = S/M/L), +0x24 move (0 walker, 1 flyer)
  CB/DAT/LCARD.DAT 58 TIMs at 0x3000 intervals
"""
import json, os, re, struct, sys, unicodedata
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), '..')
CLEAN = os.path.join(ROOT, 'rips/clean/dimguil')
PASSWORD_LETTERS = 'QAZWSXEDCRFVTGBYHNUJMIKOLP'   # glyph 1-26, top row then bottom
PACK_IN = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 11: 6, 12: 7, 13: 8, 14: 9, 15: 10, 20: 11,
           21: 12, 22: 13, 23: 14, 24: 15, 29: 16, 30: 17, 31: 18, 32: 19, 33: 20}
RULES = [  # MESSAGE.DAT section 4: heading string, body strings
    (5, range(25, 30)), (6, range(30, 34)), (10, range(35, 39)), (11, range(40, 44)),
    (12, range(45, 49)), (13, range(50, 55)), (14, range(55, 60)), (15, range(60, 63)),
    (19, range(65, 70)), (20, range(70, 73)), (21, range(75, 78)), (17, range(80, 85)),
    (9, range(85, 88)), (22, range(90, 94)), (23, range(95, 99)), (24, range(100, 105)),
    (18, range(105, 108))]


def load_json(path):
    raw = open(path, encoding='utf-8').read()
    tok = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)
    return json.loads(tok.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else '', raw))


def plain(s):
    """Game text without control codes; {f732} before a small ァ is the voiced ヴ."""
    s = s.replace('{f732}', 'ヴ')
    return re.sub(r'\{[0-9a-f]{4}\}\d?', '', s).strip()


def tim(d, off):
    magic, flag = struct.unpack_from('<II', d, off)
    assert magic == 0x10 and flag & 8 and flag & 3 == 1, 'expected an 8-bit TIM with a CLUT'
    p = off + 8
    ln, _, _, cw, ch = struct.unpack_from('<IHHHH', d, p)
    clut = []
    for v in struct.unpack_from(f'<{cw * ch}H', d, p + 12):
        r, g, b = (v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3
        clut.append((r | r >> 5, g | g >> 5, b | b >> 5, 0 if v == 0 else 255))
    p += ln
    ln, _, _, iw, ih = struct.unpack_from('<IHHHH', d, p)
    im = Image.new('RGBA', (iw * 2, ih))
    im.putdata([clut[i] for i in d[p + 12:p + 12 + iw * 2 * ih]])
    return im


def main():
    args = sys.argv[1:]
    monsters = None
    if '--monsters' in args:
        i = args.index('--monsters')
        monsters = json.load(open(args[i + 1], encoding='utf-8'))['monsters']
        del args[i:i + 2]
    out, imgdir = args[0], args[1]
    screens = None
    if len(args) > 2:
        sys.path.insert(0, os.path.dirname(os.path.abspath(args[2])))
        screens = __import__(os.path.splitext(os.path.basename(args[2]))[0]).S
    nfkc = lambda s: unicodedata.normalize('NFKC', s or '')
    cmenu = open(os.path.join(CLEAN, 'CMENU.BIN'), 'rb').read()
    msg = load_json(os.path.join(ROOT, 'rips/stage/translations/MESSAGE.DAT.json'))['sections']
    ja = lambda s, i: plain(msg[s]['strings'][i]['source'])
    en = lambda s, i: plain(msg[s]['strings'][i]['translation'] or msg[s]['strings'][i]['source'])
    label = lambda s, i: {'ja': ja(s, i), 'en': en(s, i)}

    lcard = open(os.path.join(CLEAN, 'CB/DAT/LCARD.DAT'), 'rb').read()
    os.makedirs(imgdir, exist_ok=True)
    for n in range(len(lcard) // 0x3000):
        tim(lcard, n * 0x3000).save(os.path.join(imgdir, f'lcard_{n:02d}.png'), optimize=True)

    scale = [b * 50 for b in cmenu[0x910:0x920]]
    units = []
    for k in range(40):
        rec = cmenu[0xC5A + 0x32 * k:0xC5A + 0x32 * (k + 1)]
        u = {
            'record': k,
            'pack_in_card': PACK_IN.get(k),
            'name': {'ja': ja(23, k + 1) or None, 'en_game': en_game(msg, k)},
            'record_names': {'ja': rec[:16].split(b'\0')[0].decode('cp932'),
                             'en': rec[16:32].split(b'\0')[0].decode('ascii')},
            'lcard': f'lcard_{k + 1:02d}.png' if k < 39 else None,
            'record_bytes': rec[32:].hex(' '),
        }
        if monsters is not None:
            u['monster_anchors'] = [m['anchor'] for m in monsters
                                    if u['name']['ja'] and nfkc(m['name'].get('ja')) == nfkc(u['name']['ja'])]
        if k < 39:
            pw = cmenu[0x424 + 12 * k:0x424 + 12 * k + 10].decode('ascii')
            t = cmenu[0x920 + 12 * (k + 1):0x920 + 12 * (k + 2)]
            u['password'] = {'letters': pw, 'glyphs': [PASSWORD_LETTERS.index(c) + 1 for c in pw]}
            u['template_bytes'] = t.hex(' ')
            u['lv1'] = {
                'hp': t[0], 'mp': t[1], 'atk': (t[3] & 15) * 2, 'def': (t[4] & 15) * 2,
                'magic': (t[3] >> 4) * 2,
                'mdef': {'mag': t[5], 'pri': t[6], 'alc': t[7], 'psi': t[8]},
                'next_exp': scale[t[9] >> 4],
                'size': 'SML'[[1, 2, 4].index(rec[0x21])],
                'race': label(11, 4 + rec[0x20]),
                'move': label(11, 9 + rec[0x24]),
                'special': label(11, 11 + (t[9] & 15)),
            }
            if screens:
                s = screens[k]
                l = u['lv1']
                got = (l['hp'], l['mp'], l['next_exp'], l['size'], l['move']['en'], l['race']['en'],
                       l['special']['en'], l['atk'], l['def'], l['magic'], *l['mdef'].values())
                assert got == s[1:], (k, got, s)
        else:
            u['password'] = None
            u['lv1'] = None
        units.append(u)

    masters = [{'kind': k, 'name': label(12, k), 'lcard': f'lcard_{40 + k:02d}.png',
                'effect': {'ja': ''.join(plain(x['source']) for x in msg[13 + k]['strings']),
                           'en': ' '.join(plain(x['translation']) for x in msg[13 + k]['strings']
                                          if plain(x['translation']))}}
               for k in range(6)]
    keys = ['hp', 'mp', 'atk', 'def', 'magic', 'mdef']
    options = [{'kind': k, 'name': label(19, k), 'lcard': f'lcard_{48 + k:02d}.png',
                'level_up_bonus': dict(zip(keys, cmenu[0xB00 + 6 * k:0xB06 + 6 * k]))}
               for k in range(10)]
    rules = [{'heading': label(4, h), 'string': h,
              'body': {'ja': ''.join(ja(4, i) for i in body),
                       'en': ' '.join(en(4, i) for i in body if en(4, i))},
              'strings': [body.start, body.stop - 1]} for h, body in RULES]
    labels = {n: label(10, i) for n, i in [('size', 2), ('atk', 6), ('def', 7), ('magic', 8),
              ('mdef', 9), ('move', 14), ('race', 15), ('special', 16), ('action', 17), ('status', 18)]}

    json.dump({'game': 'dim', 'platform': 'ps', 'disc': 'SLPS-02691 Rev 1',
               'units': units, 'masters': masters, 'options': options,
               'rules': rules, 'labels': labels, 'field_sources': FIELD_SOURCES,
               'lcard_extra': {'00': 'card back', '46': 'same image as 45', '47': 'same image as 45'}},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'wrote {out}: {len(units)} units, {len(masters)} masters, {len(options)} options; '
          f'{len(lcard) // 0x3000} images in {imgdir}')


# Keys defined in the research note (docs/research/dimguil-cards.md on the site).
FIELD_SOURCES = {
    'units[].record_names, units[].record_bytes, lv1.size, lv1.race, lv1.move': 'cmenu_record',
    'units[].password': 'cmenu_password',
    'units[].template_bytes, lv1.hp, lv1.mp, lv1.atk, lv1.def, lv1.magic, lv1.mdef, lv1.special': 'cmenu_template',
    'lv1.next_exp': 'cmenu_template + cmenu_exp_scale',
    'lv1 (every field)': 'screen_stock_details',
    'units[].name.ja, units[].name.en_game': 'message_names',
    'lv1.race/move/special labels, labels': 'message_labels',
    'units[].lcard, masters[].lcard, options[].lcard': 'lcard',
    'units[].monster_anchors': 'site_monsters',
    'masters[].name, masters[].effect': 'message_masters',
    'options[].name': 'message_options',
    'options[].level_up_bonus': 'cmenu_option_bonus + screen_option_details',
    'rules': 'message_rules',
    '.en of any game text other than name.en_game': 'patch_translation',
}


def en_game(msg, k):
    """The Japanese release's own English name list (MESSAGE.DAT section 23, 41-80)."""
    return plain(msg[23]['strings'][41 + k]['source']) if k < 39 else None


if __name__ == '__main__':
    main()
