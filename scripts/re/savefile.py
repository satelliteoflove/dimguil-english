#!/usr/bin/env python3
"""Decode a Wizardry: Dimguil save from a PlayStation memory card image.

    savefile.py CARD [--json] [--raw OUT]

CARD is a raw 128 KB card (.mcd, .mcr, Beetle's .srm) or a single-save file that starts
with the save's own "SC" header (.mcs/.psv style exports are not handled). --json prints
everything as JSON; --raw writes the 0x2400-byte save image to OUT.

The layout is read from the game's save and load code in MCARD.BIN (the writer at
0x800aa1f4, the reader at 0x800aa9e0); see docs/re/F-edge-save.md. The game keeps one
save, "BISLPS-02691PSWIZDIM", two blocks (0x4000 bytes): a 0x200-byte header with the
icon and title, then the 0x2400-byte image, then zeros.
"""
import json, os, struct, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gametext import dec  # noqa: E402

FILENAME = b'BISLPS-02691PSWIZDIM'
IMAGE_AT, IMAGE_LEN = 0x200, 0x2400

# Where each piece of the image comes from in RAM (MCARD 0x800aa1f4).
U32_GLOBALS = [  # image offset, RAM address, name
    (0x0f78, 0x80079628, 'g_79628'),
    (0x0f7c, 0x800795fc, 'g_795fc'),
    (0x0f80, 0x800796b0, 'g_796b0'),
    (0x0f84, 0x80079b48, 'g_79b48'),
    (0x0f88, 0x80079b44, 'story_flags'),   # bit 31: Dragon's Cave on the Edge of Town menu
    (0x0f8c, 0x80079754, 'g_79754'),
    (0x0f90, 0x80079b28, 'g_79b28'),
    (0x0f94, 0x80079618, 'g_79618'),
    (0x0f98, 0x8007986c, 'progress_bits'),
]
BLOCKS = [  # image offset, length, RAM address, name
    (0x0000, 0x438, 0x8008e620, 'parties'),          # 20 x 0x36, copied to 0x8008f8c8 on load
    (0x0438, 0xb40, 0x80086880, 'characters'),       # 20 x 0x90, rebuilt into the roster
    (0x0f9c, 0x020, 0x80079cb0, 'flags_79cb0'),      # 8 u32
    (0x0fbc, 0xd80, 0x8008c580, 'map_bits'),         # 48 maps x 24 rows x 3 bytes
    (0x1d3c, 0x01a, 0x80089b40, 'b_89b40'),          # 0xff on a new game
    (0x1d56, 0x133, 0x8008a0b0, 'boltac_stock'),     # one byte per item id 0-306
    (0x1e89, 0x027, 0x8008a040, 'items_seen'),       # bitfield (39 of its 40 bytes)
    (0x1eb0, 0x004, 0x80079700, 'g_79700'),
    (0x1eb4, 0x001, 0x80079891, 'roster_count'),
    (0x1eb5, 0x00c, 0x80096378, 'config'),           # settings, 12 bytes
    (0x1ec4, 0x4a4, 0x8008a260, 'card_game'),        # card battle config and card stock
    (0x2368, 0x009, 0x80087a30, 'b_87a30'),
    (0x2371, 0x01e, 0x80096720, 'b_96720'),          # 3 x 10, ff40 on a new game
    (0x238f, 0x046, 0x8008a068, 'monsters_seen'),    # bitfield
    (0x23d5, 0x020, 0x8008c4d0, 'b_8c4d0'),          # a few mode bytes (8001bd0c)
    (0x23f5, 0x001, 0x80079a28, 'g_79a28'),
    (0x23f6, 0x001, 0x80079b97, 'g_79b97'),
]
CONFIG_NAMES = ['item_names', 'monster_names', 'spell_names', 'status', 'sound_output',
                'music', 'effects', 'sound_effects', 'message_speed', 'cfg9', 'cfg10', 'cfg11']


def checksum(img):
    """The game zeroes the u32 at 0x23f8, then adds every byte of 0..0x23fb into it,
    so the last four bytes added are the running sum's own (MCARD 0x800aa1f4)."""
    s = sum(img[:0x23f8])
    for k in range(4):
        s = (s + ((s >> (8 * k)) & 0xff)) & 0xffffffff
    return s


def find_save(card):
    """Return the 0x4000-byte save from a raw card image, or the data itself."""
    if card[:2] == b'SC':
        return card
    if card[:2] != b'MC':
        raise SystemExit('not a raw memory card image (no MC header)')
    for i in range(1, 16):
        fr = card[i * 128:(i + 1) * 128]
        state = struct.unpack_from('<I', fr)[0]
        if state == 0x51 and fr[10:30] == FILENAME:
            data, blk = b'', i
            while True:
                data += card[blk * 0x2000:(blk + 1) * 0x2000]
                nxt = struct.unpack_from('<H', card, blk * 128 + 8)[0]
                if nxt == 0xffff:
                    break
                blk = nxt + 1
            return data
    raise SystemExit('no Dimguil save (BISLPS-02691PSWIZDIM) on this card')


def name(b):
    end = b.find(b'\xff\x40')
    return dec(b[:end if end >= 0 else len(b)])


def character(r):
    items = struct.unpack_from('<10H', r, 0x20)
    return {
        'name': name(r[:0x0e]),
        'status': r[0x0e] | r[0x0f] << 8,
        'b10_18': r[0x10:0x19].hex(),
        'gold': struct.unpack_from('<I', r, 0x1c)[0],
        # id in the low 9 bits; the high bits are flags (0x2000 is on the premade
        # characters' starting gear; its meaning is for the records doc)
        'items': [None if it == 0xffff else {'id': it & 0x1ff, 'flags': it & ~0x1ff & 0xffff,
                                             'state': r[0x34 + k]}
                  for k, it in enumerate(items)],
        'exp': struct.unpack_from('<I', r, 0x40)[0],
        'level': struct.unpack_from('<H', r, 0x44)[0],
        'hp': struct.unpack_from('<H', r, 0x46)[0],
        'max_level': struct.unpack_from('<H', r, 0x48)[0],
        'max_hp': struct.unpack_from('<H', r, 0x4a)[0],
        'b4c_77': r[0x4c:0x78].hex(),
        'b78_79': r[0x78:0x7a].hex(),
        'area': r[0x7a], 'x': r[0x7b], 'y': r[0x7c], 'facing': r[0x7d],
        'u80': struct.unpack_from('<I', r, 0x80)[0],
        'b84': r[0x84],
        'met_bits': r[0x86:0x89].hex(),       # roster +0xc6..+0xc8
        'b85_8e': r[0x85:0x8f].hex(),
    }


def decode(data):
    hdr, img = data[:IMAGE_AT], data[IMAGE_AT:IMAGE_AT + IMAGE_LEN]
    out = {
        'title': hdr[4:68].split(b'\0')[0].decode('shift_jis', 'replace'),
        'checksum_stored': struct.unpack_from('<I', img, 0x23f8)[0],
        'checksum_calc': checksum(img),
    }
    out['checksum_ok'] = out['checksum_stored'] == out['checksum_calc']
    for off, addr, nm in U32_GLOBALS:
        out[nm] = struct.unpack_from('<I', img, off)[0]
    for off, ln, addr, nm in BLOCKS:
        if nm in ('parties', 'characters', 'config'):
            continue
        out[nm] = img[off:off + ln].hex()
    out['config'] = dict(zip(CONFIG_NAMES, img[0x1eb5:0x1ec1]))
    out['roster_count'] = img[0x1eb4]
    parties = []
    for i in range(20):
        p = img[i * 0x36:(i + 1) * 0x36]
        if p[0] == 0xff:
            continue
        parties.append({'slot': i, 'id': p[0], 'count': p[1],
                        'members': [m for m in p[2:8] if m != 0xff], 'rest': p[8:].hex()})
    out['parties'] = parties
    chars = []
    for i in range(20):
        r = img[0x438 + i * 0x90:0x438 + (i + 1) * 0x90]
        if r[:2] == b'\xff\x40' or not any(r):
            continue
        c = character(r)
        c['slot'] = i
        chars.append(c)
    out['characters'] = chars
    return out, img


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    data = find_save(open(args[0], 'rb').read())
    out, img = decode(data)
    if '--raw' in args:
        open(args[args.index('--raw') + 1], 'wb').write(img)
    if '--json' in args:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    print(f"{out['title']}  checksum {'ok' if out['checksum_ok'] else 'BAD'} "
          f"({out['checksum_stored']:#x})")
    print(f"progress_bits {out['progress_bits']:#x}  story_flags {out['story_flags']:#x}  "
          f"config {list(out['config'].values())}")
    for p in out['parties']:
        print(f"party slot {p['slot']}: id {p['id']} count {p['count']} members {p['members']}")
    for c in out['characters']:
        where = 'town' if c['area'] == 0xff else f"area {c['area']} ({c['x']},{c['y']}) facing {c['facing']}"
        items = ' '.join(f"{it['id'] | it['flags']:#06x}" for it in c['items'] if it)
        print(f"{c['slot']:2d} {c['name']:10s} status {c['status']:#06x} L{c['level']} "
              f"HP {c['hp']}/{c['max_hp']} gold {c['gold']} {where}  items: {items}")


if __name__ == '__main__':
    main()
