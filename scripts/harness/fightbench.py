#!/usr/bin/env python3
"""Bench the battle policy on pre-fight states with the battle RNG seeded (casterfocus,
2026-10-15).

    python3 scripts/harness/fightbench.py probe STATE...
    python3 scripts/harness/fightbench.py run OUT.jsonl SEEDS STATE...   (SEEDS: 1-20)
    python3 scripts/harness/fightbench.py prefight STATE OUTREL SEED CHAPTER [NAME]

STATE is a path under rips/harness without .state (or a full .state path), saved at a
fight's start (trip_log.py's PREFIGHT=, or tools/prefight.py here). The battle's rolls follow
battle_rng_state (0x80079a34, docs/engine-notes.md), not input timing, so each seed writes a
value there after the load and gives a different fight from the same state. A RAM write of
data, for testing only.

probe: advances to the first command phase and prints each group: monster id and name,
count, level, threat, the spells its record can cast (damage and status), para/gdmg, and
whether the fight is fixed and fleeable.

run: one line per (state, seed): won, rounds, the party's spell points spent, HP lost,
members down or dead, runs, casts, and the round the last caster group fell. SET=K=V,...
sets battle/tactics flags first (ints, or floats with a dot). HARNESS= picks the harness
copy (default: this one).
"""
import json, os, struct, sys, random
H = os.environ.get('HARNESS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(H, 'scripts'))
from harness.game import Game, OUT
from harness import battle, tactics

NAMES = {}
try:
    _d = json.load(open(os.path.expanduser('~/Documents/bartoks-trading-post/data/monsters/dim/ps.json')))
    for _m in _d['monsters']:
        NAMES.setdefault(_m['no'], _m['name']['en'])
except Exception:
    pass
SPELL = {}
try:
    for _l in open(os.path.join(OUT, '../agents/chapters/spells_table.txt'), encoding='utf-8'):
        _p = _l.split()
        SPELL[int(_p[0])] = _p[3]
except Exception:
    pass


def sp(sid):
    return SPELL.get(sid, str(sid))


def apply_set():
    for kv in filter(None, os.environ.get('SET', '').split(',')):
        k, v = kv.split('=')
        v = float(v) if '.' in v else int(v)
        hit = False
        for mod in (battle, tactics):
            if hasattr(mod, k):
                setattr(mod, k, type(getattr(mod, k))(v) if isinstance(getattr(mod, k), (bool, int, float)) else v)
                hit = True
        if not hit:
            sys.exit('no flag ' + k)


def load(g, st):
    g.load(st[:-6] if st.endswith('.state') else st)


def to_command(g, limit=3000):
    f0 = g.frame
    while g.frame - f0 < limit:
        if not battle.in_battle(g):
            return False
        if g.u8(battle.PHASE) == battle.CMD_PHASE:
            return True
        if g.u8(battle.PHASE) == battle.FRIENDLY_PHASE:
            return False
        g.tap('circle')
        g.step(4)
    return False


def spells_of(g, k):
    r = tactics.rec(g, k)
    dmg = tactics.monster_spells(g, r, 0, tactics.F_DAMAGE)
    sts = tactics.monster_spells(g, r, 1, tactics.F_STATUS)
    return sorted({sid for _, sid in dmg}), sorted({sid for _, sid in sts}), r


def probe(g, st):
    load(g, st)
    if not to_command(g):
        print(st, 'no command phase (friendly or over)')
        return
    print('%s fixed=%d enc=%04x fleeable=%s flee=%d' % (st, g.u8(battle.FIXED), g.u16(battle.ENCOUNTER_ID),
                                                         battle.fleeable(g), battle.flee_chance(g)))
    for k in tactics.groups(g):
        m = tactics.info(g, k)
        d, s, r = spells_of(g, k)
        ai = struct.unpack_from('<H', r, 0x88)[0]
        w = list(g.e.read(tactics.AI_WEIGHTS + (ai - 1) * 13, 13)) if ai else []
        print('  g%d %3d %-18s n=%d lv=%2d hp=%3d thr=%5.1f sp=%5.1f para=%d gdmg=%d death=%d dmg=%s sts=%s ai=%s' % (
            k, m['id'], NAMES.get(m['id'], '?')[:18], len(m['mons']), m['level'],
            sum(h for _, h, _ in m['mons']), m['threat'], m['threat_spell'], m['para'], m['gdmg'], m['death'],
            [sp(x) for x in d], [sp(x) for x in s], w))


def points(g):
    return sum(sum(g.char(ri)['raw'][0x5c:0x78]) for ri in battle.party_ids(g) if ri is not None)


def hp(g):
    return sum(max(battle.member_state(g, s)[0], 0) for s, ri in enumerate(battle.party_ids(g)) if ri is not None)


def run_one(g, st, seed):
    load(g, st)
    if seed:
        g.e.write(0x80079a34, struct.pack('<I', random.Random(seed).getrandbits(32)))
    if not to_command(g):
        return dict(state=st, seed=seed, skip='no command phase')
    ids = battle.party_ids(g)
    p0, h0 = points(g), hp(g)
    casters0 = {k for k in tactics.groups(g) if caster_group(tactics.info(g, k))}
    gone = {}
    orig = battle.command_phase

    def cp(g_, policy, log):
        for k in casters0:
            if k not in gone and not tactics.standing(g_, k):
                gone[k] = battle.ROUND - 1 if battle.ROUND else 0
        return orig(g_, policy, log)
    battle.command_phase = cp
    try:
        res = battle.fight(g, chest_mode='leave')
    except Exception as e:
        return dict(state=st, seed=seed, error='%s: %s' % (type(e).__name__, e))
    finally:
        battle.command_phase = orig
    for k in casters0:
        gone.setdefault(k, res['rounds'] if res['ovl'] == 'MAZE' and not res['ran'] else None)
    st_all = [battle.member_state(g, s) for s, ri in enumerate(ids) if ri is not None]
    wiped = all(h <= 0 or s >= 0x20 for h, s in st_all)
    won = res['ovl'] == 'MAZE' and not wiped and not (res['fled'] or (0, 0))[0]
    return dict(state=st, seed=seed, won=won, wiped=wiped, rounds=res['rounds'], spent=p0 - points(g),
                hp_lost=h0 - hp(g), down=len(res['down_end']), dead=len(res['dead_end']),
                ran=res['ran'], fled=res['fled'], runs=res['runs'],
                casts=[(c[0], sp(c[1])) for c in res['casts']], casters=sorted(casters0),
                caster_down=max(gone.values(), default=0) if all(v is not None for v in gone.values()) else None,
                ll=bool(res['likely_loss']), matters=res['matters'], story=res['story'],
                why=(res.get('first') or {}).get('why'),
                acts=[a for a in res['actions'] if a[1] in ('spell', 'fight', 'aim', 'run', 'parry', 'use', 'dispel')])


def caster_group(m):
    f = getattr(tactics, 'caster_danger', None)
    if f:
        return f(m) > 0
    return bool(m['para'] or m['gdmg'] or m['death'] or any(s[1][0] == 'spell' for s in m['dsrc']))


def prefight(g, state, outrel, seed, chapter, name):
    """One training trip from a town goal state (chapters.Run.train in Run.goal, one try,
    as humanplay's bot_trip.py runs it), saving a state at each fight's start to
    rips/harness/OUTREL/fNN; the battle RNG seeded from SEED first, so trips differ."""
    import importlib
    from harness import chapters
    from harness.game import Stuck
    load(g, state)
    if seed:
        g.e.write(0x80079a34, struct.pack('<I', random.Random(seed).getrandbits(32)))
    mod = importlib.import_module('harness.chapter%d' % chapter)
    r = chapters.Run(g, seed=seed, variant=0, out=outrel, auto_cases=False)
    r.retries = 1
    r.chapter = chapter
    base = state[:-6] if state.endswith('.state') else os.path.join(OUT, state)
    r.ckpt = base
    r.full_points = chapters.load_points(g, base)
    m = None if os.environ.get('NOMEM') else chapters.load_memory(g, base)
    if m and m.get('chapter') == chapter:
        r.log.extend(tuple(x) for x in m['log'])
        r._pull = {tuple(k): dict(v, to=tuple(v['to']), at=v['at']) for k, v in m['pull']}
        r._since = {tuple(k): v for k, v in m['since']}
    l0 = len(r.log)
    orig = battle.fight
    n = [0]

    def fight(g_, *a, **k):
        n[0] += 1
        g_.save('%s/f%02d' % (outrel, n[0]))
        return orig(g_, *a, **k)
    battle.fight = fight
    try:
        r.goal(name, lambda: r.train(mod.TRAIN_AREAS))
        res = 'ok'
    except Stuck as e:
        res = 'stuck %s' % e.what
    finally:
        battle.fight = orig
    with open(os.path.join(OUT, outrel, 'trip_log.jsonl'), 'w') as f:
        for x in r.log[l0:]:
            f.write(json.dumps(x, default=str)[:20000] + '\n')
    print(res, n[0], 'fights')


def seeds(s):
    a, _, b = s.partition('-')
    return list(range(int(a), int(b or a) + 1))


if __name__ == '__main__':
    apply_set()
    g = Game(capture=True)
    if sys.argv[1] == 'probe':
        for st in sys.argv[2:]:
            probe(g, st)
    elif sys.argv[1] == 'prefight':
        # prefight STATE OUTREL SEED CHAPTER [NAME]
        prefight(g, sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]),
                 sys.argv[6] if len(sys.argv) > 6 else 'train')
    elif sys.argv[1] == 'run':
        out, ss = sys.argv[2], seeds(sys.argv[3])
        for st in sys.argv[4:]:
            for s in ss:
                r = run_one(g, st, s)
                with open(out, 'a') as f:
                    f.write(json.dumps(r, default=str) + '\n')
                print(json.dumps({k: r.get(k) for k in ('state', 'seed', 'won', 'rounds', 'spent', 'hp_lost', 'down',
                                                        'ran', 'caster_down', 'error', 'skip')}), flush=True)
