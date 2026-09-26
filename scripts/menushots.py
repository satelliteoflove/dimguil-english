#!/usr/bin/env python3
"""Screenshot a facility's icon menu for review: each icon's caption, then what opens.

    menushots.py STATE NICONS OUT [STEPS]

For each icon i: load STATE (with the cursor on the first icon, as mkstates leaves it),
move right i times and capture the caption, then press each token of STEPS (default "circle circle")
and capture after each one. Writes rips/shots/OUT.png, one row per icon. Waits are
generous because facilities load files and fade in.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from emu import Emu

state, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
steps = (sys.argv[4] if len(sys.argv) > 4 else 'circle circle').split()
e = Emu('rips/iso/dimguil-en.cue')
shots = []
for i in range(n):
    e.load(state)
    e.run(30)
    if i:
        e.seq(' '.join(['right w6'] * i) + ' w30')
    shots.append(e.shot(f'rips/shots/{out}_{i}_0.png', scale=1))
    for k, tok in enumerate(steps, 1):
        e.seq(tok if tok.startswith('w') else f'{tok} w120')
        shots.append(e.shot(f'rips/shots/{out}_{i}_{k}.png', scale=1))
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'sheet.py'),
                f'rips/shots/{out}.png', str(len(steps) + 1)] + shots, check=True)
print(f'rips/shots/{out}.png')
