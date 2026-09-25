#!/usr/bin/env python3
"""Regenerate the standard test states from a cold boot of rips/iso/dimguil-en.cue.

Save states hold RAM, including text files the game has already loaded, so states made
before a rebuild show stale text. Run this after every build that changes text.

States (rips/states/): boot, town, tavern, party (in tavern, 4 premade members),
town_party, fac1p..fac6p (inside each facility with the party), outskirts = fac6p.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from emu import Emu

S = 'rips/states/'
e = Emu('rips/iso/dimguil-en.cue')
e.run(3600); e.save(S + 'boot.state')
e.seq('circle w60 circle w60 circle w60 circle w60 circle w200'); e.save(S + 'town.state')
e.seq('circle w60'); e.save(S + 'tavern.state')
e.seq('circle w60')
for _ in range(6):  # Mars and Mercury are refused (alignment), leaving 4
    e.seq('circle w60 circle w90')
e.seq('w60 cross w60'); e.save(S + 'party.state')
e.seq('cross w120'); e.save(S + 'town_party.state')
for i in range(1, 7):
    e.load(S + 'town_party.state')
    e.seq(' '.join(['right'] * i) + ' w20 circle w150')
    e.save(S + f'fac{i}p.state')
os.replace(S + 'fac6p.state', S + 'outskirts.state')
print('states regenerated')
