"""Emulator check of the wipe handler (party_wiped 0x800c59a0, wipe_item_loss 0x800c5be8).
SETUP USES A RAM WRITE: at the second command phase of battle_wriggle.state, after the four
Defend commands are entered, every party combatant's status (+0xc) is set to 0x80 (dead) and
HP (+6) to 0. Everything after that is the game's own code. Logs which roster slots
wipe_item_loss rolls, items and gold before/after, and where the bodies are put.
    python3 rips/re/work/D/checks/wipe.py DELAY OUT.json"""
import sys, json
sys.path.insert(0, 'scripts')
import emu
delay, out = int(sys.argv[1]), sys.argv[2]
e = emu.Emu('rips/iso/dimguil-en.cue')
e.run(2)
e.load('rips/states/battle_wriggle.state'); e.run(5 + delay)
COMB = 0x8008e230
ph = lambda: e.read(0x800796fa, 1)[0]
s8 = lambda b: b - 256 if b > 127 else b
def roster(ri):
    r = 0x8007d708 + ri * 0xd0
    return dict(ri=ri, items=[int.from_bytes(e.read(r + 0x20 + 2 * k, 2), 'little') for k in range(10)],
                state=list(e.read(r + 0x34, 10)), gold=e.u32(r + 0x1c), status=int.from_bytes(e.read(r + 0xe, 2), 'little'),
                where=list(e.read(r + 0x7a, 4)))
def party():
    return [roster(s8(e.read(0x8007e812 + m, 1)[0])) for m in range(4)]
e.dbg_clear()
for pc in (0x800c59a0, 0x800c5be8, 0x800c5c2c, 0x800c5ca4, 0x800c4fc8):
    e.bp(pc)
for ri in range(4):
    e.watch(0x8007d708 + ri * 0xd0 + 0x1c, 0x8007d708 + ri * 0xd0 + 0x34, e.WRITE)
events = []
def pump(n):
    for f in range(n):
        e.run(1)
        for ent in e.log():
            r = ent['regs']
            events.append(dict(t=ent['type'], pc=ent['pc'], addr=ent['addr'], val=ent['value'], a0=r[4], v0=r[2], v1=r[3], am=e.read(0x800798c8, 1)[0], ph=ph()))
def to_cmd():
    left = False
    for i in range(2400):
        if ph() != 0x1c: left = True
        if left and ph() == 0x1c: return True
        if left and i % 25 == 0: e.press('circle', hold=4, after=0)
        pump(1)
    return False
def defend_all():
    pump(90)
    for k in range(4):
        for b in ('circle', 'down', 'circle'):
            e.press(b, hold=4, after=0); pump(25)
for i in range(900):
    if ph() == 0x1c: break
    if i % 20 == 0: e.press('circle', hold=4, after=0)
    pump(1)
defend_all(); e.press('circle', hold=4, after=0); pump(25)   # round 1, normal
to_cmd()
before = party()
loc = dict(area=e.read(0x8007e844, 1)[0])
defend_all()
for m in range(4):                                          # the RAM-write setup
    e.write(COMB + m * 0xe + 0xc, (0x80).to_bytes(2, 'little'))
    e.write(COMB + m * 0xe + 6, (0).to_bytes(2, 'little'))
e.press('circle', hold=4, after=0); pump(25)                # confirm
phases = []
for i in range(3000):
    if not phases or phases[-1] != ph(): phases.append(ph())
    if i % 30 == 0: e.press('circle', hold=4, after=0)
    pump(1)
    if any(ev['pc'] == 0x800c59a0 for ev in events): break
after = [roster(b['ri']) for b in before]
members_after = [s8(x) for x in e.read(0x8007e812, 6)]
e.shot(out.replace('.json', '.png'), scale=1)
json.dump(dict(before=before, after=after, events=events, phases=phases, loc=loc), open(out, 'w'))
print('phases', [hex(p) for p in phases])
for b, a in zip(before, after):
    print(b['ri'], 'gold', b['gold'], '->', a['gold'], 'status', hex(a['status']), 'where', b['where'], '->', a['where'])
    print('   items', [hex(x) for x in b['items']]); print('      ->', [hex(x) for x in a['items']])
print('members after', members_after)
for ev in events:
    if ev['t'] == 'W': print('  write', hex(ev['pc']), 'roster', (ev['addr'] - 0x7d708) // 0xd0, 'off', hex((ev['addr'] - 0x7d708) % 0xd0), 'val', hex(ev['val']))
    elif ev['pc'] != 0x800c5ca4: print(hex(ev['pc']), 'a0', hex(ev['a0']), 'v0', hex(ev['v0']), 'am', ev['am'])
print('rand(12) calls:', sum(ev['pc'] == 0x800c5ca4 and ev['t'] == 'X' for ev in events))
