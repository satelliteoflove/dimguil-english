#!/usr/bin/env python3
"""Build a memory card with a save set up for playtesting: rips/testsave.mcd.

The game writes the save itself (City Outskirts > Save Game), so the card is valid
without knowing the save format. Before saving, RAM is seeded with:

  - 500000 gold for every roster character (u32 at roster record + 0x1c)
  - every item marked seen, so Boltac's catalog lists them all (bitfield 0x8008a040)
  - every monster marked seen, so the Monster Compendium is complete (0x8008a068)
  - Card items, registered with the Card Master so the card game has a stock,
    plus a few more left in Jupiter's and Earth's packs to try registering by hand

The save holds game data, not text, so it stays usable across rebuilds.

    mktestsave.py [--verify]   --verify loads the card on a cold boot and checks it
"""
import ctypes as C, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from emu import Emu

CUE = 'rips/iso/dimguil-en.cue'
OUT = 'rips/testsave.mcd'
ROSTER, RECORD = 0x8007d708, 0xd0          # roster records; party copies are made from these
GOLD, PACK = 0x1c, 0x20                    # u32 gold; 10 u16 item slots (0xffff = empty)
ITEMS_SEEN, MONSTERS_SEEN = 0x8008a040, 0x8008a068
CARD, ALMIGHTY, CHANGE = 0x158, 0x159, 0x15a  # item ids 344-346
UNIDENTIFIED = 0x2000                      # flag bits the game gave dropped cards


def memcard(e):
    e.lib.retro_get_memory_data.restype = C.c_void_p
    return C.string_at(e.lib.retro_get_memory_data(0), 0x20000)


def pack(e, who):
    return list(struct.unpack('<10H', bytes(e.read(ROSTER + who * RECORD + PACK, 20))))


def give(e, who, *items):
    slots = pack(e, who)
    for it in items:
        slots[slots.index(0xffff)] = it | UNIDENTIFIED
    e.write(ROSTER + who * RECORD + PACK, struct.pack('<10H', *slots))


def cards_left(e):
    return sum(1 for w in range(6) for s in pack(e, w) if s != 0xffff and s & 0x1ff in (CARD, ALMIGHTY, CHANGE))


def build():
    e = Emu(CUE)
    e.run(3600)
    e.seq('circle w60 circle w60 circle w60 circle w60 circle w200')  # new game, into town
    e.seq('circle w60 circle w60')                                    # tavern, form party
    for _ in range(6):  # Mars and Mercury are refused (alignment), leaving 4
        e.seq('circle w60 circle w90')
    e.seq('w60 cross w60')                                            # back in the tavern

    for who in range(6):
        e.write(ROSTER + who * RECORD + GOLD, struct.pack('<I', 500000))
    e.write(ITEMS_SEEN, b'\xff' * (MONSTERS_SEEN - ITEMS_SEEN))
    e.write(MONSTERS_SEEN, b'\xff' * 60)
    give(e, 0, CARD, CARD, ALMIGHTY, CHANGE)
    give(e, 1, CARD, CARD, ALMIGHTY, CHANGE)

    # Table > Play Cards > Register Cards > Owned Cards, then register until none are left
    e.seq(' '.join(['right'] * 5) + ' w30 circle w150')
    e.seq('right right right w20 circle w500')
    e.seq('circle w150 circle w150')
    for _ in range(40):
        if not cards_left(e):
            break
        e.seq('circle w150')
    assert not cards_left(e), f'{cards_left(e)} cards still unregistered'
    e.seq('cross w60 cross w60 cross w60')      # back to the card game's menu
    e.seq('cross w400 cross w150')              # leave the card game, then the Table
    e.seq('cross w150')                         # tavern -> town

    give(e, 2, CARD, ALMIGHTY, CHANGE)
    give(e, 3, CARD, CARD)

    e.seq(' '.join(['right'] * 6) + ' w20 circle w150')   # City Outskirts
    e.seq('right w10 right w10 right w10 right w20 circle w150')  # Save Game
    # The save runs on its own; wait for the card to stop changing, then dismiss
    # "Save complete".
    prev, stable = None, 0
    for _ in range(100):
        e.run(60)
        card = memcard(e)
        stable = stable + 1 if card == prev else 0
        prev = card
        if stable >= 5 and b'BISLPS-02691' in card:
            break
    assert stable >= 5 and card[:2] == b'MC' and b'BISLPS-02691' in card, 'no Dimguil save on the card'
    e.seq('circle w150')
    open(OUT, 'wb').write(card)
    e.shot('/tmp/testsave_done.png')
    print('wrote', OUT)


def verify():
    e = Emu(CUE)
    card = open(OUT, 'rb').read()
    e.lib.retro_get_memory_data.restype = C.c_void_p
    C.memmove(e.lib.retro_get_memory_data(0), card, len(card))
    e.run(3600)
    e.seq('down w30 circle w120')               # Load Data
    shots = []
    for i in range(8):
        e.seq('circle w150')
        e.shot(f'/tmp/testsave_load{i}.png')
    gold = [struct.unpack('<I', bytes(e.read(ROSTER + w * RECORD + GOLD, 4)))[0] for w in range(6)]
    seen = bytes(e.read(ITEMS_SEEN, 100))
    print('gold', gold)
    print('seen bits set:', sum(bin(b).count('1') for b in seen), 'of', 800)
    print('card items left in packs:', cards_left(e))
    e.shot('/tmp/testsave_loaded.png')
    return e


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    if '--verify' in sys.argv:
        verify()
    else:
        build()
