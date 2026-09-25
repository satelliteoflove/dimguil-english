#!/usr/bin/env python3
"""explore.py STATE NICONS OUT [extra-seq]
For each icon i: load STATE, move right i times, then circle, circle, (extra) with a
screenshot after each step. Writes OUT_sheet.png (one row per icon)."""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from emu import Emu
st, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
extra = sys.argv[4] if len(sys.argv) > 4 else ''
e = Emu('rips/iso/dimguil-en.cue')
P = []
for i in range(n):
    e.load(st)
    if i: e.seq(' '.join(['right'] * i) + ' w20')
    for k, tok in enumerate(('circle w90 circle w90 ' + extra).split()):
        e.seq(tok)
        if not tok.startswith('w'):
            e.run(1); P.append(e.shot(f'/tmp/dg/{out}_{i}_{k}.png', scale=1))
    e.save(f'rips/states/{out}_{i}.state')
steps = len([t for t in ('circle circle ' + extra).split() if not t.startswith('w')])
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'sheet.py'), f'/tmp/dg/{out}_sheet.png', str(steps)] + P)
