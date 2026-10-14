"""diag_enc.py DISC STATE: replay hunt.py inputs from STATE, printing every 60 frames the
resident overlay byte, game mode, and whether 0x800a1000 holds BATTLE's or MAZE's head."""
import os, sys, json
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
cue, st = sys.argv[1], sys.argv[2]
BH = open('rips/re/work/spellfix/discs/ca912fe8/BATTLE.BIN', 'rb').read(16)
MH = open('rips/clean/dimguil/MAZE.BIN', 'rb').read(16)
g = Game(disc=cue, capture=False); e = g.e
e.load(st)
ins = json.load(open(st.replace('.state', '.inputs.json')))['inputs']
last = None
for k, b in enumerate(ins):
    e.run(1, tuple(b))
    h = e.read(0x800a1000, 16)
    s = (g.u8(0x800798b3), g.u8(0x8007967e), 'B' if h == BH else 'M' if h == MH else '?', g.u8(0x800796fa))
    if s != last:
        print(k, s); last = s
print('end', len(ins), s)
