"""Emulator check of the party to-hit threshold, swing rolls, party and monster initiative.
Loads battle_wriggle.state, waits `delay` frames (to vary the RNG), then presses circle
(Fight for everyone) round after round. Breakpoints only; no RAM writes.
    python3 rips/re/work/D/checks/melee_init.py DELAY OUT.json"""
import sys, json
sys.path.insert(0, 'scripts')
import emu
delay, out = int(sys.argv[1]), sys.argv[2]
e = emu.Emu('rips/iso/dimguil-en.cue')
e.run(2)
e.load('rips/states/battle_wriggle.state'); e.run(5 + delay)
COMB = 0x8008e230
s8 = lambda b: b - 256 if b > 127 else b
def snap():
    party = []
    for m in range(6):
        ri = s8(e.read(0x8007e812 + m, 1)[0])
        if ri < 0: party.append(None); continue
        r = 0x8007d708 + ri * 0xd0
        c = COMB + m * 0xe
        party.append(dict(ri=ri, agi=e.read(r + 0x17, 1)[0], tohit=int.from_bytes(e.read(r + 0x84, 2), 'little', signed=True),
                          extra=e.read(c + 8, 1)[0], acmod=s8(e.read(c + 4, 1)[0]), status=int.from_bytes(e.read(c + 0xc, 2), 'little')))
    mons = []
    for g in range(1, 5):
        rec = 0x8008a918 + g * 0xd0
        mons.append(dict(g=g, id=int.from_bytes(e.read(0x8008c480 + g * 8 + 2, 2), 'little'), count=e.read(0x8008c480 + g * 8 + 4, 1)[0],
                         ac=s8(e.read(rec + 0x7a, 1)[0]), acmod=[s8(e.read(COMB + g * 0x7e + m * 0xe + 4, 1)[0]) for m in range(9)]))
    return dict(party=party, mons=mons, oslo=e.read(0x8007e830, 1)[0])
e.dbg_clear()
for pc in (0x800a9224, 0x800a9250, 0x800cf990, 0x800cf9c4, 0x800cfa38):
    e.bp(pc)
# initiative tick writes, party and groups 1-4
e.watch(COMB, COMB + 5 * 0x7e, e.WRITE)
events, snaps = [], []
for rnd in range(12):
    snaps.append(snap())
    for p in range(8):
        e.press('circle', hold=4, after=0)
        for f in range(40):
            e.run(1)
            am = e.read(0x800798c8, 1)[0]; ph = e.read(0x800796fa, 1)[0]
            for ent in e.log():
                r = ent['regs']
                if ent['type'] == 'X':
                    events.append(dict(k='X', pc=ent['pc'], v0=r[2], t1=r[9], s1=r[17], a2=r[6], am=am, ph=ph, rnd=rnd))
                elif ent['type'] == 'W':
                    off = (ent['addr'] - (COMB & 0x1fffffff))
                    g, rem = divmod(off, 0x7e); m, fld = divmod(rem, 0xe)
                    if fld == 9 and ent['size'] == 1:
                        events.append(dict(k='tick', g=g, m=m, v=ent['value'] & 0xff, pc=ent['pc'], rnd=rnd, ph=ph))
    if e.read(0x800796fa, 1)[0] >= 0x3e: break
json.dump(dict(snaps=snaps, events=events, final_phase=e.read(0x800796fa, 1)[0]), open(out, 'w'))
e.shot(out.replace('.json', '.png'), scale=1)
print(len(events), 'events; final phase', hex(e.read(0x800796fa, 1)[0]))
