#!/usr/bin/env python3
"""Make fresh fight-start states on the bacortu build (rips/iso of the bacortu worktree):
from ch17's goal state (c17v2b/goal_02_area_e), run chapter 17's goal GOAL with the ch17
harness and save the start of the first two type-2 fights (encounter 0xfffe, fixed battles) and the first
ordinary fights (0x80079bde = 0) with 2+ groups, into rips/agents/bacortu/states/. HARNESS= picks the harness copy (default ../ch17 beside this one). Each fight starts in
the maze, so BATTLE.BIN is loaded from this disc; MAIN is checked against this disc's
SLPS_026.91 too.

    python3 -B scripts/re/bacortu/mkfights.py SEED GOAL [NORD]"""
import os, struct, sys, random, importlib
B = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
# the harness copy to import (wt/ch17's: fightbench, chapter 17's goals and states)
W = os.environ.get('HARNESS', os.path.join(os.path.dirname(B), 'ch17'))
sys.path.insert(0, W + '/scripts'); sys.path.insert(0, W + '/scripts/harness')
import fightbench as fb
from harness import battle, tactics, chapters
from harness.game import Game, OUT
D = os.path.join(B, 'rips', 'agents', 'bacortu')
seed, goal = int(sys.argv[1]), sys.argv[2]
NORD = int(sys.argv[3]) if len(sys.argv) > 3 else 3
g = Game(disc=B + '/rips/iso/dimguil-en.cue', capture=True)
state = 'ch17/c17v2b/goal_02_area_e'
fb.load(g, state)
g.e.write(0x80079a34, struct.pack('<I', random.Random(seed).getrandbits(32)))
importlib.import_module('harness.chapter17')
r = chapters.Run(g, seed=seed, variant=0, out=os.path.join(D, 'run'), auto_cases=False)
r.retries = 1
r.chapter = 17
base = os.path.join(OUT, state)
r.ckpt = base
r.full_points = chapters.load_points(g, base)
fns = dict(chapters.CHAPTERS[17]().goals(r))
orig = battle.fight
got = {'fixed': 0, 'ord': 0}


class Done(Exception):
    pass


def fight(g_, *a, **k):
    tactics.STORY[0] = None
    fixed = g_.u8(0x80079bde)
    ngroups = g_.u8(0x800798b8)
    kind = 'fixed' if g_.u16(battle.ENCOUNTER_ID) == 0xfffe else 'ord'
    if got[kind] < (2 if kind == 'fixed' else NORD) and (kind == 'fixed' or ngroups >= 2):
        got[kind] += 1
        name = os.path.join(D, 'states', '%s_s%d_%02d.state' % (kind, seed, got[kind]))
        g_.e.save(name)
        print('saved', name, 'enc %#x' % g_.u16(battle.ENCOUNTER_ID), 'groups', ngroups,
              'front', g_.u8(0x800796d3), 'back', g_.u8(0x8007967c), 'at', (g_.u8(0x8007e844),) + tuple(g_.pos()),
              'overlay', g_.overlay(), flush=True)
    res = orig(g_, *a, **k)
    print('  fought %s: rounds %d ran %d fled %s dead %s' % (kind, res['rounds'], res['ran'], res['fled'], res['dead_end']), flush=True)
    if got['fixed'] >= 2 and got['ord'] >= NORD:
        raise Done()
    return res


battle.fight = fight
try:
    fns[goal]()
    print('goal ended', got)
except Done:
    print('done', got)
