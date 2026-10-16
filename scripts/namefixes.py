#!/usr/bin/env python3
"""Write binary patches that fix misspellings in the developer's English names.

    namefixes.py          write binary/<file>.json for the files that need a fix
    namefixes.py --list   print each slot that would change

The names are the game's built-in English (docs/translation-notes.md, "Series spellings
checked"); only plain typos and garbled names are fixed, never the series' own
spellings (NUNCHAKA, Maelific, Halycon). The monster records in DATA02/M_DTnnn.BIN, MPTnn.BIN
and NPTnn.BIN are the 0xd0-byte records described in nptnames.py, with six 18-byte name
slots ending in {ff40}, so a name can't pass 16 glyphs. ITEM.DAT's English item list
isn't in a translation file, so its fixes are byte edits too. The same names live in
M_CATALG, I_NAME_E and MESSAGE.DAT (translations/*.json) and in BATTLE.BIN
(asm/name_fixes.asm).

Two-word names in the party records (MPT, NPT) are stored with a bare {ff21} between the
words, for the two-line enemy grid. Battle messages drop the break, so "Arch{ff21}Ninja"
printed "ArchNinja kicks Venus." spaced() puts a space before the break, as "Man in
{ff21}Robe" already had; the grid draws the same two lines. Breaks inside one word
(Nex{ff21}tepehua, Tepe{ff21}yollotl) stay bare, and Goblin{ff21}Assassin has no room.
NPT patches go in binary/NPTnn.BIN.names.json; nptnames.py owns NPTnn.BIN.json.
"""
import glob, json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from gametext import dec
from nptnames import ROOT, CLEAN, REC, SLOT, GLYPH, records

# Whole slot text -> fixed text ({ff21} is the line break the party pictures use).
SLOTS = {
    'Dragonare': 'Dragonaire',
    'Dragonares': 'Dragonaires',
    'Old{ff21}Drumer': 'Old{ff21}Drummer',
    # "Small Silhouettes" is 17 glyphs; Small Shadow is the literal ちいさなかげ and fits.
    'Small Silhoutte': 'Small Shadow',
    'Small Silhouttes': 'Small Shadows',
    'Small{ff21}Silhoutte': 'Small{ff21}Shadow',
    # Mesoamerican names, romanized from the katakana or garbled; no Wizardry precedent.
    'Shocitnal': 'Xochitonal',
    'Shocitnals': 'Xochitonals',
    'Oserotoru': 'Ocelotl',
    'Inkuintori': 'Itzcuintli',
    'Cuautori': 'Cuauhtli',
    # Plurals of -y names; Dragon Flies and Vorpal Bunnies are the series' own.
    'Dragon Flys': 'Dragon Flies',
    'Faerie Flys': 'Faerie Flies',
    'Vorpal Bunnys': 'Vorpal Bunnies',
    'Beautys': 'Beauties',
    'Stone Sentrys': 'Stone Sentries',
    # The rest of the bestiary: a typo, and names garbled from their sources.
    'Web Spiner': 'Web Spinner',
    'Web Spiners': 'Web Spinners',
    'Allo Saurus': 'Allosaurus',
    'Allo Sauruses': 'Allosauruses',
    'Uthiu': 'Utiu',
    'Uthius': 'Utius',
    'Sopirote': 'Zopilote',
    'Sopirotes': 'Zopilotes',
    'Ispusteke': 'Ixpuztec',
    'Ispustekes': 'Ixpuztecs',
    # Broken where the Nahuatl words meet: nex(tli) "ash" + tepehua "scatterer",
    # tepe(tl) "mountain" + yollotl "heart".
    'Neshu{ff21}teper': 'Nex{ff21}tepehua',
    'Neshu{ff21}tepers': 'Nex{ff21}tepehuas',
    'Tepeyo{ff21}ryotl': 'Tepe{ff21}yollotl',
    'Tepeyo{ff21}ryotls': 'Tepe{ff21}yollotls',
    # A developer slip; Hobgoblin is one word everywhere else in the series.
    'HobGoblin': 'Hobgoblin',
    'HobGoblins': 'Hobgoblins',
}
# Two-word names that can't take the space: a slot holds 16 glyphs and these fill it.
NO_ROOM = {'Goblin{ff21}Assassin'}
# Unidentified names (slots 3 and 5) by the record's English name, so the same text can
# change on one monster and not another. Named by the picture the player sees (Chris,
# 2026-10-13, docs/unidentified-flyers.md option B): the bat-winged figure is a Flying
# Figure, as on Fake Cupid and Halycon, and Marchosias shows the great demon of every
# other Greater Demon.
UNIDENTIFIED = {
    'Vampire Bat': ('Flying Figure', 'Flying Figures'),
    'Wing Lizard': ('Flying Figure', 'Flying Figures'),
    'Were Bat': ('Flying Figure', 'Flying Figures'),
    'Marchosias': ('Greater Demon', 'Greater Demons'),
}
# ITEM.DAT's English list, the Item Catalog's names ({ff21} is two bytes, and the
# catalog draws it as a line break). The list has no spare bytes, so a name that grows
# takes the room from the space before a break, which the catalog never shows:
# BREASTPLATE, FAERIE'S and GLOVE OF drop theirs, and GLOVE OF THE DEAD's three extra
# letters come from the three robes after it. PRIEST'S MACE's apostrophe uses the byte
# IRON GLOVES gave up. See item_list() for how the list is read.
ITEM_DAT = 'DATA07/ITEM.DAT', [
    ('DISPLASER {ff21}ROBE', 'DISPLACER {ff21}ROBE'),
    ('B-PLATE OF {ff21}GOODNESS', 'BREASTPLATE{ff21}OF BOONS'),
    ('STEEL GLOVES', 'IRON GLOVES'),
    ('PRIESTS MACE', "PRIEST'S MACE"),
    ("FAERIE'S {ff21}CLOTHE", "FAERIE'S{ff21}CLOTHES"),
    ('GLOVE OF {ff21}DEAD', 'GLOVE OF{ff21}THE DEAD'),
    ('EMERALD {ff21}ROBES', 'EMERALD{ff21}ROBES'),
    ('SAPPHIRE {ff21}ROBES', 'SAPPHIRE{ff21}ROBES'),
    ('SCARLET {ff21}ROBES', 'SCARLET{ff21}ROBES'),
]
ITEM_LIST, ITEM_COUNT = 0x5c234a, 349     # sections.json, ITEM.DAT section 5


def glyphs(name):
    return b'\xff\x21'.join(bytes(GLYPH[c] for c in part) for part in name.split('{ff21}'))


def encode(name):
    b = glyphs(name) + b'\xff\x40'
    assert len(b) <= SLOT, name
    return bytes(b).ljust(SLOT, b'\0')


def spaced(name):
    """A space before the break of a two-word name, if the slot has room."""
    head, sep, tail = name.partition('{ff21}')
    if not sep or head.endswith(' ') or not tail[:1].isupper() or name in NO_ROOM:
        return name
    return head + ' {ff21}' + tail


def item_list(d, fixes):
    """ITEM.DAT's English item names: u32 offsets from ITEM_LIST, then the strings. The
    catalog (0x800e1d20 in its overlay) takes only the first offset and reads the names
    one after another to each {ff40}, so the strings must stay in order with nothing
    between them: a gap or a dropped duplicate shifts every later name, and the last
    read runs off the list and crashes the catalog. Rewrites the strings and offsets from
    the first changed name until the run ends where the original did; anything left over
    goes after the last name. Returns {offset: bytes} edits."""
    ptr = [struct.unpack_from('<I', d, ITEM_LIST + 4 * i)[0] for i in range(ITEM_COUNT)]
    old = [d[ITEM_LIST + p:d.index(b'\xff\x40', ITEM_LIST + p)] for p in ptr]
    assert all(ptr[i + 1] == ptr[i] + len(old[i]) + 2 for i in range(ITEM_COUNT - 1))
    end = ptr[-1] + len(old[-1]) + 2
    new = list(old)
    for a, b in fixes:
        pat, rep = glyphs(a), glyphs(b)
        assert old.count(pat) == 1, a
        new[old.index(pat)] = rep
    changed = [i for i in range(ITEM_COUNT) if new[i] != old[i]]
    first, last = changed[0], changed[-1]
    out, newptr, i = bytearray(), [], first
    while True:
        newptr.append(ptr[first] + len(out))
        out += new[i] + b'\xff\x40'
        i += 1
        if i == ITEM_COUNT or (i > last and ptr[first] + len(out) == ptr[i]):
            break
    stop = ptr[i] if i < ITEM_COUNT else end
    assert ptr[first] + len(out) <= stop, 'ITEM.DAT item list: no room'
    out += bytes(stop - ptr[first] - len(out))
    return {ITEM_LIST + ptr[first]: bytes(out),
            ITEM_LIST + 4 * first: b''.join(struct.pack('<I', p) for p in newptr)}


def write(f, edits, suffix='.json'):
    path = os.path.join(ROOT, 'binary', os.path.basename(f) + suffix)
    json.dump({'file': f, 'edits': edits}, open(path, 'w'), indent=4)
    open(path, 'a').write('\n')


def main():
    listing = '--list' in sys.argv
    for p in sorted(glob.glob(os.path.join(CLEAN, 'M_DT*.BIN')) + glob.glob(os.path.join(CLEAN, 'MPT*.BIN'))
                    + glob.glob(os.path.join(CLEAN, 'NPT*.BIN'))):
        d = open(p, 'rb').read()
        edits = {}
        for o in records(d):
            unid = UNIDENTIFIED.get(dec(d, o + 2 * SLOT))
            for k in range(2, 6):
                s = o + k * SLOT
                cur = dec(d, s)
                new = SLOTS.get(cur, cur)
                if unid and k in (3, 5):
                    new = unid[k == 5]
                new = spaced(new)
                if new != cur:
                    edits[f'{s:x}'] = encode(new).hex(' ')
                    if listing:
                        print(f'{os.path.basename(p)} {s:#07x} {dec(d, s)} -> {new}')
        if edits and not listing:
            nm = os.path.basename(p)
            write('DATA02/' + nm, edits, '.names.json' if nm.startswith('NPT') else '.json')

    f, fixes = ITEM_DAT
    d = open(os.path.join(ROOT, 'rips/clean/dimguil', f), 'rb').read()
    edits = item_list(d, fixes)
    if listing:
        for old, new in fixes:
            print(f'{f} {old} -> {new}')
        for o, b in sorted(edits.items()):
            print(f'{f} {o:#07x} {len(b)} bytes')
    else:
        write(f, {f'{o:x}': b.hex(' ') for o, b in sorted(edits.items())})


if __name__ == '__main__':
    main()
