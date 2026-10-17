#!/usr/bin/env python3
"""Cast the Bishop's Bacortu at one group on round 1 (everyone else parries) and print each
group's sealing level (battle_groups 0x8008c480 + g*8 + 6) before the cast and at the next
command phase, with the fixed-battle flag and the row split. Also checks the fix words in
RAM (spell_handlers[14] and the routine at 0x800c31a4) against this build's BATTLE.BIN.

    python3 -B scripts/re/bacortu/verify.py DISC STATE GROUP [SEED]
DISC: 'new' (this worktree's rips/iso) or 'old' (rips/harness/disc, the suite's disc).
The results in docs/re/bugs.md 1.16 came from rips/agents/bacortu/states/ (made by mkfights.py)."""
import os, struct, sys, random
B = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
# the harness copy to import (wt/ch17's: fightbench, chapter 17's goals and states)
W = os.environ.get('HARNESS', os.path.join(os.path.dirname(B), 'ch17'))
sys.path.insert(0, W + '/scripts'); sys.path.insert(0, W + '/scripts/harness')
import fightbench as fb
from harness import battle, tactics
from harness.game import Game, DISC
disc = B + "/rips/iso/dimguil-en.cue" if sys.argv[1] == "new" else DISC
st, G = sys.argv[2], int(sys.argv[3])
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
os.environ['TEXT'] = '1'
g = Game(disc=disc, capture=True)
SEAL = lambda k: g.u8(0x8008c480 + k * 8 + 6)
g.load(os.path.abspath(st) if st.endswith(".state") else st)
g.e.write(0x80079a34, struct.pack('<I', random.Random(seed).getrandbits(32)))
assert fb.to_command(g), 'no command phase'
bat = open(B + '/rips/dirty/dimguil/BATTLE.BIN', 'rb').read()
ram = lambda a, n: g.e.read(a, n)
fix_tab = struct.unpack('<I', ram(0x800d83c4, 4))[0]
fix_code = ram(0x800c31a4, 0x800c325c - 0x800c31a4) == bat[0x800c31a4 - 0x800a1000:0x800c325c - 0x800a1000]
code_same = sum(1 for a in range(0x800a1000, 0x800d5000, 4) if ram(a, 4) != bat[a - 0x800a1000:a - 0x800a1000 + 4])
print('disc', os.path.basename(os.path.dirname(os.path.dirname(disc))), 'state', os.path.basename(st))
print('RAM: spell_handlers[14] = %#x, routine at 0x800c31a4 %s; BATTLE code 0x800a1000-0x800d5000 words differing from this build: %d'
      % (fix_tab, 'matches this build' if fix_code else 'differs', code_same))
print('fixed %d  groups %d  front-row groups %d  back-row groups %d  target group %d' % (
    g.u8(0x80079bde), g.u8(0x800798b8), g.u8(0x800796d3), g.u8(0x8007967c), G))
ids = battle.party_ids(g)
for k in tactics.groups(g):
    print('  group %d: id %d %s x%d, seal %d' % (k, battle.group_id(g, k), fb.NAMES.get(battle.group_id(g, k), '?'),
                                                 len(tactics.info(g, k)['mons']), SEAL(k)))
before = {k: SEAL(k) for k in range(1, 7)}
aimed = battle.group_id(g, G)
done = []


def policy(g_, m, opts):
    c = g_.char(ids[m])
    if not done and battle.SPELL in opts and c['cls'] == 11:
        by = {x[0]: x for x in battle.castable(g_, ids[m])}
        if 14 in by:
            x = by[14]
            done.append((c['name'], c['level']))
            return ('spell', 14, x[1], x[2], x[3], ('group', G))
    if battle.ROUND >= 2:
        after = {k: SEAL(k) for k in range(1, 7)}
        print('caster', done, 'round', battle.ROUND)
        print('seal before', before)
        print('seal after ', after)
        print('sealed groups', [k for k in range(1, 7) if after[k] > before[k]])
        print('aimed at monster id', aimed, '; sealed groups now hold ids',
              [battle.group_id(g_, k) for k in range(1, 7) if after[k] > before[k]],
              '; groups now', {k: battle.group_id(g_, k) for k in tactics.groups(g_)})
        raise SystemExit(0)
    return ('parry',)


try:
    battle.fight(g, policy=policy, chest_mode='leave')
except SystemExit:
    pass
txt = [t['text'] for t in (g.cap.messages if g.cap else []) if t.get('file') == 'FIGHTMSG.OBJ']
print('battle text', txt)
