#!/usr/bin/env python3
"""The harness's regression suite: the ratchet (Chris, 2026-10-12: "a solid
self-improving system", not stumbling through tests).

    python3 scripts/harness/regress.py              # run every case, log a round
    python3 scripts/harness/regress.py --trials 10  # T2 trials per macro (default 10)
    python3 scripts/harness/regress.py --only stuck # just the stuck-state cases
    python3 scripts/harness/regress.py --collect    # add stuck states not yet in cases

The loop: a run gets stuck -> the stuck state is saved and added here as a case
(automatically, chapter1.Run and trials.run_one call add_case) -> the harness is fixed ->
this suite runs -> only a change that passes every case is committed -> the next run.

Cases live in rips/harness/regress/cases.jsonl, one JSON object per line:
  id        unique name
  kind      'trial' (a T2 macro trial: macro, k) or 'stuck' (a saved stuck state)
  state     for 'stuck': the state to load (rips/harness/<state>.state); none for the
            party goal, which starts from power-on (creation can't resume midway)
  variant, seed   the chapter-1 run's party variant and seed
  goal      for 'stuck': the chapter-1 goal that got stuck (party, enter, train_NN,
            pillar_<name>, tablet_door) or a T2 macro name
  what      the stuck kind when it was added
  expect    'handled': pass if the goal/macro, run from the state, ends without a Stuck
            (any defined outcome: True, 'casualties', 'wiped' ...);
            'proof': pass only if the goal returns True (its RAM proof);
            'frozen': a state where the game itself stops responding; pass only if the
            harness reports 'game not responding' (an open issue, not a harness fault)
  added     date added; source: the run that produced it
A case runs in its own process (one emulator per process; the core's debug hooks are
global), at most 10 at once, with a frame budget. Each round appends to
rips/harness/regress/rounds.jsonl: date, the harness code hash, cases passed and failed
(by case), stuck counts by cause from the latest chapter-1 runs, frames and wall time.
"""
import argparse, glob, hashlib, json, os, random, sys, time, multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUTR = os.path.join(ROOT, 'rips/harness')
REG = os.path.join(OUTR, 'regress')
CASES = os.path.join(REG, 'cases.jsonl')
ROUNDS = os.path.join(REG, 'rounds.jsonl')
MAX_PROCS = 10
BUDGET = 90000            # frames per stuck case (about 7 minutes of game time)


def code_hash():
    h = hashlib.sha1()
    for p in sorted(glob.glob(os.path.join(HERE, '*.py'))):
        h.update(os.path.basename(p).encode())
        h.update(open(p, 'rb').read())
    return h.hexdigest()[:12]


def load_cases():
    if not os.path.exists(CASES):
        return []
    return [json.loads(l) for l in open(CASES) if l.strip()]


def add_case(case):
    """Append a case unless one with the same id or state is there. Safe to call from any
    run (appends a line; duplicates by id/state are skipped)."""
    os.makedirs(REG, exist_ok=True)
    have = load_cases()
    if any(c['id'] == case['id'] or (case.get('state') and c.get('state') == case['state'])
           for c in have):
        return False
    case.setdefault('added', time.strftime('%Y-%m-%d'))
    case.setdefault('expect', 'handled')
    with open(CASES, 'a') as f:
        f.write(json.dumps(case) + '\n')
    return True


def collect():
    """Every stuck state saved by chapter-1 runs (rips/harness/t3/<run>/stuck_*.state),
    with its goal and kind from the run's result.json when there is one."""
    n = 0
    for st in sorted(glob.glob(os.path.join(OUTR, 't3/*/stuck_*.state'))):
        rel = os.path.relpath(st, OUTR)[:-6]
        run = rel.split('/')[1]
        base = os.path.basename(rel)                  # stuck_02_pillar_bird_3
        parts = base.split('_')
        goal = '_'.join(parts[2:-1])
        if goal == 'party':
            continue        # creation can't resume midway; the run adds these from power-on
        what = None
        res = os.path.join(OUTR, 't3', run, 'result.json')
        if os.path.exists(res):
            for s in json.load(open(res)).get('stuck', []):
                if s.get('state') == rel:
                    what = s.get('what')
        n += add_case(dict(id='stuck:' + rel, kind='stuck', state=rel, goal=goal, what=what,
                           source=run))
    return n


def trial_cases(n):
    from harness import trials
    return [dict(id='trial:%s:%d' % (m, k), kind='trial', macro=m, k=k)
            for m in sorted(trials.TRIALS) for k in range(n)]


# --- running a case (in a child process) ---

def run_stuck(case):
    from harness.game import Game, Stuck
    from harness import chapter1, town
    g = Game(capture=True)
    if case.get('state'):
        g.load(case['state'])               # else power-on (the party goal)
    run = chapter1.Run(g, seed=case.get('seed', 7), variant=case.get('variant', 0),
                       out='regress/scratch/%d' % os.getpid(), retries=1, auto_cases=False)
    goal = case['goal']
    if goal.startswith('pillar_'):
        name = goal[len('pillar_'):]
        xy = dict(chapter1.PILLARS)[name]
        fn = lambda: run.pillar(name, xy)
    elif goal == 'tablet_door':
        fn = run.door
    elif goal.startswith('train'):
        fn = run.train_trip
    elif goal == 'enter':
        fn = lambda: town.begin_adventure(g) is not None
    elif goal == 'party':
        fn = run.make_party
    else:
        raise ValueError('no runner for goal %r' % goal)
    g.budget_end = g.frame + BUDGET
    f0 = g.frame
    r = fn()
    return dict(result=r if r in (True, False) else str(r), frames=g.frame - f0)


def run_trial(case):
    from harness import trials
    from harness.game import Game
    g = Game(capture=True)
    rng = random.Random(1000003 * case['k'] + 17)
    f0 = g.frame
    r = trials.TRIALS[case['macro']](g, case['k'], rng)
    return dict(result=r.get('outcome', 'ok'), frames=g.frame - f0)


def run_case(case):
    t0 = time.time()
    rec = dict(id=case['id'], kind=case['kind'])
    try:
        r = run_stuck(case) if case['kind'] == 'stuck' else run_trial(case)
        rec.update(r)
        ok = r['result'] is True if case.get('expect') == 'proof' else True
        if case.get('expect') == 'frozen':
            ok = False                    # it should have been reported as frozen
        rec['ok'] = ok
    except Exception as e:
        what = getattr(e, 'what', str(e))
        rec.update(ok=case.get('expect') == 'frozen' and what == 'game not responding',
                   error='%s: %s' % (type(e).__name__, what),
                   info={k: str(v)[:200] for k, v in getattr(e, 'info', {}).items()})
    rec['wall'] = round(time.time() - t0, 1)
    return rec


def latest_stuck_causes():
    """Stuck counts by cause over the latest chapter-1 runs (their result.json files)."""
    out = {}
    for res in glob.glob(os.path.join(OUTR, 't3/*/result.json')):
        for s in json.load(open(res)).get('stuck', []):
            out[s.get('what')] = out.get(s.get('what'), 0) + 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trials', type=int, default=10, help='T2 trials per macro')
    ap.add_argument('--only', choices=['stuck', 'trial'])
    ap.add_argument('--procs', type=int, default=MAX_PROCS)
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--note', default='')
    a = ap.parse_args()
    added = collect()
    if a.collect:
        print('added', added)
        return
    saved = load_cases()
    cases = []
    if a.only != 'trial':
        cases += [c for c in saved if c['kind'] == 'stuck']
    if a.only != 'stuck':
        gen = trial_cases(a.trials)
        ids = {c['id'] for c in gen}
        cases += gen + [c for c in saved if c['kind'] == 'trial' and c['id'] not in ids]
    # long cases first, so the pool isn't left waiting on one at the end
    cases.sort(key=lambda c: (c['kind'] != 'stuck', c['id']))
    procs = min(a.procs, MAX_PROCS)
    t0 = time.time()
    recs = []
    ctx = mp.get_context('spawn')
    os.makedirs(REG, exist_ok=True)
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
    with ctx.Pool(procs, maxtasksperchild=1) as pool, \
            open(os.path.join(REG, 'results-%s.jsonl' % stamp.replace(':', '')), 'w') as f:
        for rec in pool.imap_unordered(run_case, cases):
            recs.append(rec)
            f.write(json.dumps(rec, default=str) + '\n'); f.flush()
            print('PASS' if rec['ok'] else 'FAIL', rec['id'], rec.get('result', ''),
                  rec.get('error', ''), rec['wall'], flush=True)
    failed = sorted(r['id'] for r in recs if not r['ok'])
    rnd = dict(date=stamp, code=code_hash(), note=a.note, cases=len(recs),
               passed=len(recs) - len(failed), failed=failed,
               by_kind={k: dict(n=sum(1 for r in recs if r['kind'] == k),
                                ok=sum(1 for r in recs if r['kind'] == k and r['ok']))
                        for k in ('stuck', 'trial')},
               frames=sum(r.get('frames', 0) for r in recs), wall=round(time.time() - t0),
               stuck_causes=latest_stuck_causes())
    with open(ROUNDS, 'a') as f:
        f.write(json.dumps(rnd) + '\n')
    print(json.dumps({k: v for k, v in rnd.items() if k != 'failed'}, indent=1))
    print('FAILED:', failed)
    sys.exit(0 if not failed else 1)


if __name__ == '__main__':
    main()
