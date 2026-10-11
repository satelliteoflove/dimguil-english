#!/usr/bin/env python3
"""Print each item's catalog description beside what its record says, for checking claims.

    desccheck.py items [ID ...]    record summary, the Japanese and our English
    desccheck.py flags [ID ...]    only items whose description makes a claim the
                                   automatic checks can test, with the result
    desccheck.py monsters [NAME ...]
                                   the battle fields of each distinct monster record
                                   (DATA02/M_DTnnn.BIN, MPTnn.BIN), with its category bit

Records come from the original executable (rips/clean, layout in types.h `Item` and
docs/re/G-records.md). Description k is item k up to 24 and item k+1 from 25 on; entry
24 holds the Battle Axe's and, after {ff40}, the Nunchaka's (engine-notes, "Item
catalog"). Monster class bits (slay_mask) are the 14 classes, then the Compendium's
categories: 14 Giants, 15 Mythical, 16 Dragons, 17 Animals, 18 Beastfolk, 19 Undead,
20 Demons, 21 Insects, 22 Magical, 23 Mysterious (from the monster records carrying
each bit; see docs/re/description-check.md).
"""
import json, os, re, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import reviewpage
from gametext import dec

EXE = os.path.join(ROOT, 'rips/clean/dimguil/SLPS_026.91')
RACES = 'Human Elf Dwarf Gnome Hobbit Faerie Lizardman Dracon Rawulf Mook Felpurr'.split()
CLASSES = ('Fighter Mage Priest Thief Samurai Lord Valkyrie Ranger Bard Alchemist Psionic '
           'Bishop Ninja Monk').split()
FAMILIES = CLASSES + ['Giants', 'Mythical', 'Dragons', 'Animals', 'Beastfolk', 'Undead', 'Demons',
                      'Insects', 'Magical', 'Mysterious']
CATEGORY = 'weapon armor shield helm gauntlets boots instrument other'.split()
SUBTYPE = {0: 'sword', 1: 'katana', 2: 'wand/dagger', 3: 'axe/hammer', 4: 'mace/whip', 5: 'staff',
           6: 'spear/pole', 7: 'bow', 8: 'thrown', 9: 'leather', 10: 'robe', 11: 'chain',
           12: 'breastplate/scale', 13: 'plate', 14: 'shield', 15: 'helm', 16: 'hat',
           17: 'gauntlets', 18: 'boots', 19: 'instrument', 20: 'potion', 21: 'scroll',
           22: 'cloak', 23: 'ankh', 24: 'ring', 25: 'amulet', 26: 'other', 28: 'card'}
HIT = ['sleep', 'poison', 'stone', 'confusion', 'paralysis', 'knock-out', 'decapitation']
# Item +0x28.. adds to Roster +0xb0..: percent resistances, in the same order as the
# resist bits below (index 10, +0xba, is level drain: D).
RESIST = HIT + ['fire', 'cold', 'bit9', 'level drain', 'bit11', 'bit12']
# Item +0x26 is ORed into Roster +0xac, copied to the battle resist bits +0xae (D). Bits
# 0-6 line up with the hit effects and 7/8 with the fire and cold spells' element bits
# (0x80, 0x100: D's damage spell table); 0x4000 is Tiltowait's. The pairing of each bit
# with the percentage at the same index is read from the records (inferred).
ELEMENT = {**{1 << b: n for b, n in enumerate(HIT)},
           0x80: 'fire', 0x100: 'cold', 0x400: 'level drain', 0x4000: 'Tiltowait element'}
EFFECT = {1: 'Str+1', 2: 'IQ+1', 3: 'Pie+1', 4: 'Vit+1', 5: 'Agi+1', 6: 'Luc+1', 7: 'Str-1',
          8: 'IQ-1', 9: 'Pie-1', 10: 'Vit-1', 11: 'Agi-1', 12: 'Luc-1', 0xd: 'age-1', 0xe: 'age+1',
          0xf: 'cure user', 0x10: 'cure party', 0x11: 'max HP+1..4', 0x12: 'max HP-1..5, age-1',
          0x13: 'all spell points 9', 0x14: 'all spell points 0', 0x15: 'forget spells',
          0x16: 'poison, max HP down', 0x17: 'Pie+1, ashes', 0x18: 'death', 0x19: 'paralysis',
          0x1a: 'stone', 0x1b: 'Vit+1 age+1', 0x1c: 'max HP down, Vit+1',
          0x1d: 'max HP up then ashes', 0x1e: 'become Bishop', 0x1f: 'max HP up, Vit-1',
          0x20: 'Str+1 Agi+1 Luc+1', 0x21: 'full HP', 0x22: 'Str-1 Agi+1', 0x23: 'Str+1 Luc-1',
          0x24: 'Pie-1 age-1', 0x25: 'become Ninja', 0x26: 'become Lord', 0x27: 'Vit+1 age-1',
          0x28: 'Vit-1 age+1', 0x29: 'Agi+1 Luc+1', 0x2a: 'become Monk', 0x2b: 'max HP up, age+1'}
# 0x17 and 0x20-0x2a read from JOUKA equip_menu 0x800ccc94 (stat changes through
# 0x800cfc4c(stat, delta)); the rest from G-records.md.


def load_items():
    exe = open(EXE, 'rb').read()
    out = []
    for i in range(382):
        r = exe[0x80052bf2 - 0x8000f800 + i * 0x4c:][:0x4c]
        f = dict(zip('category subtype flags specials'.split(), r[2:6]))
        f['effect'] = r[0xd]
        f['break_chance'], f['break_into'] = struct.unpack_from('<HH', r, 0xe)
        f['price'], f['sell'] = struct.unpack_from('<II', r, 0x12)
        f['stock'], f['spell'] = r[0x1a], r[0x1b]
        f['class_mask'], f['race_mask'] = struct.unpack_from('<HH', r, 0x1c)
        f['regen'], f['ac'], f['to_hit'] = struct.unpack_from('<bbb', r, 0x21)[0], *struct.unpack_from('<bb', r, 0x35)
        f['dice'] = struct.unpack_from('<BBb', r, 0x37)
        f['swings'] = struct.unpack_from('<b', r, 0x3a)[0]
        f['slay'] = struct.unpack_from('<I', r, 0x3e)[0]
        f['effect_pct'] = list(r[6:0xd])
        f['protect'] = struct.unpack_from('<I', r, 0x22)[0]
        f['resist_bits'] = struct.unpack_from('<H', r, 0x26)[0]
        f['resist'] = list(r[0x28:0x35])
        f['magic_resist'] = list(r[0x42:0x46])
        f['reach'] = r[0x46]
        out.append(f)
    return out


def names():
    d = json.load(open(os.path.join(ROOT, 'rips/stage/out/dumps/I_NAME_E.OBJ.json'), encoding='utf-8'))
    t = reviewpage.load(os.path.join(ROOT, 'translations/I_NAME_E.OBJ.json'))
    src = [s['source'] for s in d['sections'][0]['strings']]
    tr = [s.get('translation') or '' for s in t['sections'][0]['strings']]
    return [(tr[i] or src[i]).replace('{ff22}', '').replace('\n', ' ') for i in range(382)]


def spell_names():
    d = json.load(open(os.path.join(ROOT, 'rips/stage/out/dumps/STATUS.OBJ.json'), encoding='utf-8'))
    t = reviewpage.load(os.path.join(ROOT, 'translations/STATUS.OBJ.json'))
    return [t['sections'][0]['strings'][222 + s].get('translation') or d['sections'][0]['strings'][222 + s]['source']
            for s in range(84)]


def descriptions():
    """{item id: (jp, en)} from ITEM.DAT's description section."""
    d = json.load(open(os.path.join(ROOT, 'rips/stage/out/dumps/ITEM.DAT.json'), encoding='utf-8'))
    t = reviewpage.load(os.path.join(ROOT, 'translations/ITEM.DAT.json'))
    jp = [s['source'] for s in d['sections'][6]['strings']]
    en = [s.get('translation') or '' for s in t['sections'][1]['strings']]
    out = {}
    for k in range(len(jp)):
        if k == 24:
            a, _, b = jp[k].partition('{ff40}')
            c, _, e = en[k].partition('{ff40}')
            out[24], out[25] = (a, c), (b, e)
        else:
            out[k if k < 24 else k + 1] = (jp[k], en[k])
    return out


def bits(mask, labels):
    return [labels[b] for b in range(len(labels)) if mask >> b & 1]


def summary(f, spells):
    s = [CATEGORY[f['category']] if f['category'] < 8 else f'cat{f["category"]}',
         SUBTYPE.get(f['subtype'], f'sub{f["subtype"]}')]
    al = ''.join(c for b, c in enumerate('GNE') if f['flags'] >> b & 1)
    s.append(f'align-ok {al or "none"}')
    sex = ''.join(c for b, c in ((3, 'M'), (4, 'F')) if f['flags'] >> b & 1)
    if sex != 'MF':
        s.append(f'sex {sex or "none"}')
    if f['category'] == 0:
        s.append('/'.join(n for b, n in ((5, '2-hand'), (6, 'main'), (7, 'sub')) if f['flags'] >> b & 1) or 'no hand')
    if f['specials'] & 0x80:
        s.append('CURSED')
    if f['specials'] & 0x7f:
        s.append('hits: ' + ','.join(f'{HIT[b]} {f["effect_pct"][b]}%' for b in range(7) if f['specials'] >> b & 1))
    if f['effect']:
        s.append(f'effect {EFFECT.get(f["effect"], hex(f["effect"]))}')
    if f['spell'] != 0xff:
        s.append(f'spell {spells[f["spell"] & 0x7f]}' + (f' (+{f["spell"] & 0x80:#x})' if f['spell'] & 0x80 else ''))
    if f['break_chance']:
        s.append(f'breaks {f["break_chance"]}% -> {f["break_into"]}')
    cl = bits(f['class_mask'], CLASSES)
    if len(cl) < 14:
        s.append('classes ' + (','.join(cl) or 'none'))
    rc = bits(f['race_mask'], RACES)
    if len(rc) < 11:
        s.append('races ' + (','.join(rc) or 'none'))
    if f['regen']:
        s.append(f'regen {f["regen"]:+d}')
    if f['ac']:
        s.append(f'AC {f["ac"]:+d}')
    if f['to_hit']:
        s.append(f'hit {f["to_hit"]:+d}')
    n, sides, bonus = f['dice']
    if n:
        s.append(f'dmg {n}d{sides}{bonus:+d}'.replace('+0', '') + f' ({n + bonus}-{n * sides + bonus})')
    if f['swings']:
        s.append(f'swings +{f["swings"]}')
    if f['slay']:
        s.append('slays ' + ','.join(bits(f['slay'], FAMILIES)))
    if f['protect']:
        s.append('protects vs ' + ','.join(bits(f['protect'], FAMILIES)))
    if f['resist_bits']:
        s.append('resist bits ' + ','.join(ELEMENT.get(1 << b, hex(1 << b)) for b in range(16) if f['resist_bits'] >> b & 1))
    if any(f['resist']):
        s.append('resists ' + ','.join(f'{RESIST[k] if k < len(RESIST) else k} {v}%' for k, v in enumerate(f['resist']) if v))
    if any(f['magic_resist']):
        s.append('magic resist ' + '/'.join(map(str, f['magic_resist'])) + ' (Mage/Priest/Alch/Psi)')
    if f['category'] == 0:
        s.append(f'reach {f["reach"]}')
    s.append(f'price {f["price"]}' + (f' stock {f["stock"]}' if f['stock'] not in (0, 255) else
                                      ' not sold' if f['stock'] == 0 else ''))
    return '; '.join(s)


# Automatic checks: (name, description test, record test). A hit is a description that
# mentions the claim while the record disagrees.
def checks(f, jp):
    out = []
    def claim(name, said, true):
        if said and not true:
            out.append(name)
    claim('cursed?', re.search(r'呪われ|呪い', jp), f['specials'] & 0x80 or f['effect'] in (0x16, 0x17, 0x18))
    claim('heals while carried?', re.search(r'HPが?(徐々|少しずつ|自然)?に?回復|体力が回復', jp), f['regen'] > 0 or f['effect'] in (0xf, 0x10, 0x21))
    claim('drains HP?', re.search(r'HPを?(吸|奪|減)', jp), f['regen'] < 0)
    claim('breaks?', re.search(r'壊れ|割れ|砕け|なくな|消え', jp), f['break_chance'])
    claim('slays something?', re.search(r'倍|特効|威力を発揮|効果的|強い', jp), f['slay'])
    claim('casts a spell?', re.search(r'「[ァ-ヴー]+」', jp), f['spell'] != 0xff or f['effect'])
    return out


# +0xcc/+0xce: the hit effects and elements as for items; 0x400 and 0x800 are the flee and
# call-for-help switches (D-battle.md)
MON_BITS = HIT + ['fire', 'cold', 'bit9', 'flees', 'calls help', 'bit12', 'bit13', 'bit14', 'bit15']
MONSTER_FLAGS = {0x80000: 'undead', 0x100000: 'summoned', 0x400000: 'death-immune (Magical)',
                 0x1000000: 'death/decap-immune'}


def load_monsters():
    """Distinct monster records by id. M_DTnnn.BIN and MPTnn.BIN end in one 0xd0-byte record per
    group, the first group last; walk back while the English name reads as a name."""
    d = os.path.join(ROOT, 'rips/clean/dimguil/DATA02')
    recs = {}
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith(('M_DT', 'MPT')) and fn.endswith('.BIN')):
            continue
        data = open(os.path.join(d, fn), 'rb').read()
        for k in range(1, 9):
            b = data[len(data) - k * 0xd0:len(data) - (k - 1) * 0xd0]
            i = struct.unpack_from('<H', b, 0x6c)[0]
            if len(b) < 0xd0 or not 0 < i < 1000 or \
                    not re.fullmatch(r"[A-Za-z0-9' .\-]+|[A-Za-z0-9' .\-]+\{ff21\}[A-Za-z0-9' .\-]+",
                                     dec(b, 0x24)):
                break
            recs.setdefault(i, b)
    return recs


def monster_summary(b):
    u8 = lambda o: b[o]
    u16 = lambda o: struct.unpack_from('<H', b, o)[0]
    flags = struct.unpack_from('<I', b, 0xa8)[0]
    out = [f'L{u16(0x74)}', f'HP {u16(0x74)}d{u16(0x76)}+{u16(0x78)}',
           f'AC {struct.unpack_from("<h", b, 0x7a)[0]}']
    if u8(0x80):
        out.append(f'drains {u8(0x80)}')
    if u8(0x81):
        out.append(f'regen {u8(0x81)}')
    if any(b[0xa3:0xa7]):
        out.append('MR M/P/A/Ps ' + '/'.join(str(x) for x in b[0xa3:0xa7]))
    fl = [n for m, n in MONSTER_FLAGS.items() if flags & m]
    if fl:
        out.append(' '.join(fl))
    for k in range(3):
        a = b[0xac + 10 * k:0xac + 10 * k + 10]
        noun = struct.unpack_from('<H', a, 0)[0]
        if not a[3] and not a[4]:
            continue
        if noun >= 683 and noun < 2000:
            out.append(f'atk{k}: innate spell {a[6]}')
            continue
        eff = ','.join(bits(a[7] & 0x7f, HIT))
        out.append(f'atk{k}: {a[3]}x {a[4]}d{a[5]}+{a[6]}' + (f' {eff} {a[8]}%' if eff else '')
                   + (' back row' if a[7] & 0x80 else ''))
    if u8(0xca):
        out.append(f'breath 0x{u8(0xc9):02x} (effect {','.join(bits(u8(0xc9) & 0x1f, HIT)) or "none"}, '
                   f'element 0x{u8(0xc9) & 0xe0:02x})')
    if u16(0xcc):
        out.append('resists ' + ','.join(bits(u16(0xcc), MON_BITS)))
    if u16(0xcc) & 0x800:
        out.append(f'calls help {u8(0x8b)}/90')
    if u16(0xce):
        out.append('weak ' + ','.join(bits(u16(0xce), RESIST + ['bit13', 'bit14', 'bit15'])))
    sp = [(n, [x for x in b[0x8f + 5 * k:0x94 + 5 * k] if x != 0xff])
          for k, n in enumerate(('M', 'P', 'A', 'Ps'))]
    if any(v for _, v in sp):
        out.append('spells ' + ' '.join(f'{n}{v}' for n, v in sp if v))
    return '; '.join(out)


def monsters(want):
    recs = load_monsters()
    seen = {}
    for i, b in sorted(recs.items()):
        name = dec(b, 0x24).replace('{ff21}', ' ')
        if want and name not in want:
            continue
        flags = struct.unpack_from('<I', b, 0xa8)[0]
        cat = next((FAMILIES[k] for k in range(14, 24) if flags >> k & 1), '-')
        if cat == '-' and i >= 340:
            cat = 'humanoid'
        line = monster_summary(b)
        if seen.get(name) == line:
            continue
        seen[name] = line
        print(f'{cat:10s} {i:3d} {name}: {line}')
    return 0


def main():
    a = sys.argv[1:]
    if a and a[0] == 'monsters':
        return monsters(set(a[1:]))
    if not a or a[0] not in ('items', 'flags'):
        print(__doc__); return 1
    items, nm, sp, desc = load_items(), names(), spell_names(), descriptions()
    ids = [int(x, 0) for x in a[1:]] or sorted(desc)
    for i in ids:
        jp, en = desc.get(i, ('', ''))
        hits = checks(items[i], jp)
        if a[0] == 'flags' and not hits:
            continue
        print(f'{i:3d} {nm[i]}: {summary(items[i], sp)}')
        if hits:
            print('    CHECK: ' + ', '.join(hits))
        print('    JP: ' + jp.replace('\n', ''))
        print('    EN: ' + en.replace('\n', ' '))
    return 0


if __name__ == '__main__':
    sys.exit(main())
