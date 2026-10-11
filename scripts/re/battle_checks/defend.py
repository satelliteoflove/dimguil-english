"""Emulator check of monster initiative and the monster to-hit threshold.
battle_wriggle.state; every character chooses Defend each round; the Wriggle Objects attack.
Breakpoints and watchpoints only, no RAM writes.
    python3 rips/re/work/D/checks/defend.py DELAY ROUNDS OUT.json"""
import sys, json
sys.path.insert(0, 'scripts')
import emu
delay, rounds, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
e = emu.Emu('rips/iso/dimguil-en.cue')
e.run(2)
e.load('rips/states/battle_wriggle.state'); e.run(5 + delay)
COMB = 0x8008e230
ph = lambda: e.read(0x800796fa, 1)[0]
s8 = lambda b: b - 256 if b > 127 else b
e.dbg_clear()
e.bp(0x800ab2ec)            # monster swing: v0 roll, s4 threshold
e.bp(0x800aaed0)            # monster_attack_roll(a0 attack, a1 T)
e.bp(0x800d00a4)            # monster tick roll: v0 = rand(255)
e.watch(COMB + 0x7e, COMB + 5 * 0x7e, e.WRITE)   # monster combatant records
events, snaps = [], []
def pump(frames):
    for f in range(frames):
        e.run(1)
        tm = e.read(0x800797a5, 1)[0]; ag = e.read(0x8007979a, 1)[0]
        for ent in e.log():
            r = ent['regs']
            if ent['type'] == 'X':
                events.append(dict(k='X', pc=ent['pc'], v0=r[2], a0=r[4], a1=r[5], s4=r[20], tm=tm, ag=ag, rnd=len(snaps)))
            elif ent['type'] == 'W':
                off = ent['addr'] - (COMB & 0x1fffffff)
                g, rem = divmod(off, 0x7e); m, fld = divmod(rem, 0xe)
                if fld == 9:
                    events.append(dict(k='tick', g=g, m=m, v=ent['value'] & 0xff, size=ent['size'], pc=ent['pc'], rnd=len(snaps)))
# get to the first command phase
for i in range(900):
    if ph() == 0x1c: break
    if i % 20 == 0: e.press('circle', hold=4, after=0)
    pump(1)
for rnd in range(rounds):
    pump(90)
    party = []
    for m in range(4):
        ri = s8(e.read(0x8007e812 + m, 1)[0]); rr = 0x8007d708 + ri * 0xd0; c = COMB + m * 0xe
        party.append(dict(ac=s8(e.read(rr + 0x86, 1)[0]), acmod=s8(e.read(c + 4, 1)[0]),
                          hp=int.from_bytes(e.read(c + 6, 2), 'little', signed=True), status=int.from_bytes(e.read(c + 0xc, 2), 'little')))
    mons = [dict(level=int.from_bytes(e.read(COMB + 0x7e + m * 0xe, 2), 'little'), hp=int.from_bytes(e.read(COMB + 0x7e + m * 0xe + 6, 2), 'little', signed=True)) for m in range(9)]
    snaps.append(dict(party=party, mons=mons, maporfic=e.read(0x8007e82a, 1)[0], count=e.read(0x8008c488 + 4, 1)[0]))
    for k in range(4):
        for b in ('circle', 'down', 'circle'):
            e.press(b, hold=4, after=0); pump(25)
    e.press('circle', hold=4, after=0); pump(25)   # "Confirm actions?" Yes
    left = False
    for i in range(2400):
        if ph() != 0x1c: left = True
        if left and ph() == 0x1c: break
        pass
        if left and i % 25 == 0: e.press('circle', hold=4, after=0)
        pump(1)
    if ph() != 0x1c: break
json.dump(dict(snaps=snaps, events=events, final_phase=ph()), open(out, 'w'))
e.shot(out.replace('.json', '.png'), scale=1)
print(len(snaps), 'rounds', len(events), 'events; final phase', hex(ph()))
