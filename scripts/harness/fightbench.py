#!/usr/bin/env python3
"""Bench the battle policy on pre-fight states with the battle RNG seeded (casterfocus,
2026-10-15).

    python3 scripts/harness/fightbench.py probe STATE...
    python3 scripts/harness/fightbench.py run OUT.jsonl SEEDS STATE...   (SEEDS: 1-20)
    python3 scripts/harness/fightbench.py prefight STATE OUTREL SEED CHAPTER [NAME]
    python3 scripts/harness/fightbench.py table DIR [by-state]

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
copy (default: this one). CHAPTER=N imports chapterN first (its BOSS_AT and POLICY_AT
registrations); TEXT=1 keeps each fight's FIGHTMSG lines in the output.

goalfight: a chapter goal run from a goal state, stopped at its first boss or story
fight, whose start is saved to OUTREL (goalfight STATE OUTREL SEED CHAPTER GOAL). With
TYPE2=N it saves the start of each type-2 party fight instead (encounter id 0xfffe, the
roamer tokens) as OUTREL_NN, fights them out, and stops after N.
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


def points_lv(g):
    """The party's spell points by level 1-7, all schools."""
    out = [0] * 7
    for ri in battle.party_ids(g):
        if ri is not None:
            r = g.char(ri)['raw']
            for sch in range(4):
                for lv in range(7):
                    out[lv] += r[0x5c + sch * 7 + lv]
    return out


def hp(g):
    return sum(max(battle.member_state(g, s)[0], 0) for s, ri in enumerate(battle.party_ids(g)) if ri is not None)


def run_one(g, st, seed):
    load(g, st)
    if seed:
        g.e.write(0x80079a34, struct.pack('<I', random.Random(seed).getrandbits(32)))
    msg0 = len(g.cap.messages) if g.cap else 0
    if not to_command(g):
        return dict(state=st, seed=seed, skip='no command phase')
    ids = battle.party_ids(g)
    p0, h0, pl0 = points(g), hp(g), points_lv(g)
    # caster groups by monster id (groups renumber as they fall), the same rule for every
    # harness version: paralysis, group damage, death or a disabling spell
    casters0 = {tactics.info(g, k)['id'] for k in tactics.groups(g) if caster_group(tactics.info(g, k))}
    gone = []
    orig = battle.command_phase

    def cp(g_, policy, log):
        if not gone and casters0 and not any(tactics.standing(g_, k) for k in tactics.groups(g_)
                                             if battle.group_id(g_, k) in casters0):
            gone.append(battle.ROUND - 1 if battle.ROUND else 0)
        return orig(g_, policy, log)
    battle.command_phase = cp
    try:
        res = battle.fight(g, chest_mode='leave')
    except Exception as e:
        return dict(state=st, seed=seed, error='%s: %s' % (type(e).__name__, e))
    finally:
        battle.command_phase = orig
    if casters0 and not gone and res['ovl'] == 'MAZE' and not res['ran']:
        gone.append(res['rounds'])
    st_all = [battle.member_state(g, s) for s, ri in enumerate(ids) if ri is not None]
    wiped = all(h <= 0 or s >= 0x20 for h, s in st_all)
    won = res['ovl'] == 'MAZE' and not wiped and not (res['fled'] or (0, 0))[0]
    return dict(state=st, seed=seed, won=won, wiped=wiped, rounds=res['rounds'], spent=p0 - points(g),
                spent_lv=[a - b for a, b in zip(pl0, points_lv(g))],
                hp_lost=h0 - hp(g), down=len(res['down_end']), dead=len(res['dead_end']),
                ran=res['ran'], fled=res['fled'], runs=res['runs'], runs_skipped=res.get('runs_skipped'),
                casts=[(c[0], sp(c[1])) for c in res['casts']], casters=sorted(casters0),
                caster_down=gone[0] if gone else None,
                deaths=[(d['who'], d['what'], d['by'], d.get('how')) for d in res.get('deaths') or []],
                heals=battle.FIGHT_INFO.get('heals'),
                items=[(u['who'], u['item'], u['round']) for u in battle.FIGHT_INFO.get('items') or []],
                ll=bool(res['likely_loss']), matters=res['matters'], story=res['story'],
                why=(res.get('first') or {}).get('why'),
                acts=[a for a in res['actions'] if a[1] in ('spell', 'fight', 'aim', 'run', 'parry', 'use', 'dispel')],
                policy=res.get('policy'), cm=res.get('cm'), cr=res.get('cr'), support=res.get('support'),
                text=[battle._flat(x['text']) for x in g.cap.messages[msg0:]
                      if x['file'] == 'FIGHTMSG.OBJ'] if os.environ.get('TEXT') and g.cap else None)


def caster_group(m):
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


class _AtFight(Exception):
    pass


def goalfight(g, state, outrel, seed, chapter, goal):
    """A chapter goal run from a goal state (as run_chapter --from runs it), stopped at its
    first fight that counts as a boss or story fight there (tactics.BOSS_AT, a fixed grid):
    the state at the fight's start goes to rips/harness/OUTREL.state (chapter 16's Crystal
    Men: goalfight ch16/c16v1b/goal_01_hidden_door ch16/bench/cm_pre 1 16 gold_stone)."""
    import importlib
    from harness import chapters
    load(g, state)
    if seed:
        g.e.write(0x80079a34, struct.pack('<I', random.Random(seed).getrandbits(32)))
    importlib.import_module('harness.chapter%d' % chapter)
    r = chapters.Run(g, seed=seed, variant=0, out=os.path.dirname(outrel), auto_cases=False)
    r.retries = 1
    r.chapter = chapter
    base = state[:-6] if state.endswith('.state') else os.path.join(OUT, state)
    r.ckpt = base
    r.full_points = chapters.load_points(g, base)
    fns = dict(chapters.CHAPTERS[chapter]().goals(r))
    orig = battle.fight
    t2 = int(os.environ.get('TYPE2') or 0)
    n = [0]

    def fight(g_, *a, **k):
        tactics.STORY[0] = None
        if t2:
            if g_.u16(battle.ENCOUNTER_ID) == 0xfffe:
                n[0] += 1
                g_.save('%s_%02d' % (outrel, n[0]))
                print('saved %s_%02d at' % (outrel, n[0]), (g_.u8(0x8007e844),) + tuple(g_.pos()), flush=True)
                res = orig(g_, *a, **k)
                print('  fought: rounds %d ran %d fled %s dead %s' % (res['rounds'], res['ran'], res['fled'],
                                                                     res['dead_end']), flush=True)
                if n[0] >= t2:
                    raise _AtFight()
                return res
            return orig(g_, *a, **k)
        if tactics.story_fight(g_):
            g_.save(outrel)
            raise _AtFight()
        return orig(g_, *a, **k)
    battle.fight = fight
    try:
        fns[goal]()
        print('goal ended with no boss fight')
    except _AtFight:
        print('saved', outrel, 'at', (g.u8(0x8007e844),) + tuple(g.pos()), 'maporfic', g.u8(battle.MAPORFIC_ON))
    finally:
        battle.fight = orig


def table(d, by_state=False):
    """Sum a bench directory's VARIANT_rN_STATE.jsonl files: per variant and run setting
    (and per state with by_state), fights, won, wiped, mean rounds, points spent (all, levels
    4-5, levels 6-7; fights not wiped: a wiped party's points read as spent), HP lost,
    members down and dead at the end, fights run from, likely losses, mean round the last
    caster group fell."""
    import glob, collections
    rows = collections.defaultdict(list)
    for fn in sorted(glob.glob(os.path.join(d, '*_r[01]_*.jsonl'))):
        b = os.path.basename(fn)[:-6]
        v, r, st = b.split('_', 2)
        for l in open(fn):
            x = json.loads(l)
            if 'skip' in x or 'error' in x:
                rows[(v, r, st if by_state else '')].append(None)
                continue
            rows[(v, r, st if by_state else '')].append(x)
    print('%-8s %-3s %-34s %4s %4s %4s %6s %6s %5s %5s %7s %5s %5s %4s %4s %6s %5s' % (
        'variant', 'run', 'state', 'n', 'won', 'wipe', 'rounds', 'spent', 'L4-5', 'L6-7', 'hp_lost', 'down', 'dead',
        'ran', 'll', 'c_down', 'err'))
    for key in sorted(rows, key=lambda k: (k[1], k[2], ['base', 'story', 'new'].index(k[0]) if k[0] in ('base', 'story', 'new') else 9, k[0])):
        xs = [x for x in rows[key] if x]
        err = len(rows[key]) - len(xs)
        n = len(xs) or 1
        cd = [x['caster_down'] for x in xs if x.get('caster_down') is not None]
        sl = [x.get('spent_lv') for x in xs if x.get('spent_lv') and not x['wiped']]
        sp = [x['spent'] for x in xs if not x['wiped']] or [0]
        l45 = '%.2f' % (sum(v[3] + v[4] for v in sl) / len(sl)) if sl else '-'
        l67 = '%.2f' % (sum(v[5] + v[6] for v in sl) / len(sl)) if sl else '-'
        print('%-8s %-3s %-34s %4d %4d %4d %6.2f %6.2f %5s %5s %7.1f %5d %5d %4d %4d %6s %5d' % (
            key[0], key[1], key[2][-34:], len(xs), sum(x['won'] for x in xs), sum(x['wiped'] for x in xs),
            sum(x['rounds'] for x in xs) / n, sum(sp) / len(sp), l45, l67, sum(x['hp_lost'] for x in xs) / n,
            sum(x['down'] for x in xs), sum(x['dead'] for x in xs), sum(1 for x in xs if x['ran']),
            sum(1 for x in xs if x['ll']), '%.2f' % (sum(cd) / len(cd)) if cd else '-', err))


def seeds(s):
    a, _, b = s.partition('-')
    return list(range(int(a), int(b or a) + 1))


if __name__ == '__main__':
    apply_set()
    if sys.argv[1] == 'table':
        table(sys.argv[2], by_state=len(sys.argv) > 3)
        sys.exit()
    g = Game(capture=True)
    if sys.argv[1] == 'probe':
        for st in sys.argv[2:]:
            probe(g, st)
    elif sys.argv[1] == 'prefight':
        # prefight STATE OUTREL SEED CHAPTER [NAME]
        prefight(g, sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]),
                 sys.argv[6] if len(sys.argv) > 6 else 'train')
    elif sys.argv[1] == 'goalfight':
        # goalfight STATE OUTREL SEED CHAPTER GOAL
        goalfight(g, sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6])
    elif sys.argv[1] == 'run':
        if os.environ.get('CHAPTER'):
            # the chapter's own registrations (tactics.BOSS_AT, battle.POLICY_AT)
            import importlib
            importlib.import_module('harness.chapter%s' % os.environ['CHAPTER'])
            apply_set()
        out, ss = sys.argv[2], seeds(sys.argv[3])
        for st in sys.argv[4:]:
            for s in ss:
                r = run_one(g, st, s)
                with open(out, 'a') as f:
                    f.write(json.dumps(r, default=str) + '\n')
                print(json.dumps({k: r.get(k) for k in ('state', 'seed', 'won', 'rounds', 'spent', 'hp_lost', 'down',
                                                        'ran', 'caster_down', 'error', 'skip')}), flush=True)
