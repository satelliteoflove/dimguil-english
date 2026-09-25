#!/usr/bin/env python3
"""play.py DISC STATE_IN "seq" OUTPREFIX [STATE_OUT]
Load state, run button sequence (see Emu.seq), screenshot after every token, make a sheet."""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from emu import Emu
disc, st, seq, pre = sys.argv[1:5]
e = Emu(disc)
if st != '-': e.load(st)
paths = []
for k, tok in enumerate(seq.split()):
    e.seq(tok)
    paths.append(e.shot(f'{pre}_{k:02d}_{tok.replace("+","_")}.png', scale=1))
if len(sys.argv) > 5: e.save(sys.argv[5])
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'sheet.py'), pre + '_sheet.png', '4'] + paths)
print(pre + '_sheet.png')
