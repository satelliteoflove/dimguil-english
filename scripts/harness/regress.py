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
  kind      'trial' (a T2 macro trial: macro, k), 'stuck' (a saved stuck state),
            'screen' (a T5 known-bad screen, scripts/harness/t5bad.py: case; with expect
            'proof' it passes when the checks catch the bug put back), 'pick' (a battle
            state at its command phase: one round of commands, every enemy group pick
            aimed and confirmed in RAM; want_id, a monster id some member must aim at;
            min_aims, default 1: a lone group's Fight shows no pick),
            'cdrace' (a state just before a disc read that the DsPacket race stalls on
            the old MAIN, docs/re/bugs.md 1.12; main 'state' keeps the state's MAIN and
            expect 'stall' wants the stall and the game's own retry, main 'disc' lays the
            disc under test's DsPacket words over MAIN and expect 'read' wants a normal
            read), 'friendly' (a battle state at or just before "A friendly monster
            appears": battle.fight must choose Leave, with no fight rounds, and end
            back in the maze), or 'boot' (made each round, not saved: see below)
Every case that loads a state gets the disc under test's 14 DsPacket fix words
(asm/bugfix_dspacket_race.asm) laid over its MAIN on each load (overlay_main): a state
keeps the MAIN it was saved with, and the t3/t4 states predate the fix (0ef275c), so
without it they could stall on the race and waste up to 1,500 frames a read. The words
are checked against DSPACKET_WORDS first; a disc without them gets no overlay (and the
cdrace disc_main case fails). The one case left without the overlay is cdrace main
'state' (cdrace:t4v1_f3066:old_main), which exercises the stall itself. Boot cases load
no state and run the disc's own MAIN.
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
Boot cases (--boots N, default 4): chapter 1 from power-on to the tablet door
(chapter1.Run.run, T3 style: party, training, the four pillars, the door), seed and party
variant from BOOTS. A save state keeps the MAIN executable's code (SLPS) of the build it
was made on, while overlays load fresh from the disc; so stuck and trial cases never run
a change to MAIN, and boot cases are the ones that do (2026-10-13: the voicing-mark build
2212979 hung on a MAIN change no state-based case could reach). A boot case passes when
the run gets through the tablet door, retries included.
A case runs in its own process (one emulator per process; the core's debug hooks are
global), at most 10 at once, with a frame budget. Each round appends to
rips/harness/regress/rounds.jsonl: date, the harness code hash at the start and at the end
(`valid` false when they differ: the code changed mid-round, so the round can't count;
rips/harness/regress/LOCK holds the running round's PID meanwhile), cases passed and failed
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


BOOTS = [(81, 0), (82, 1), (83, 3), (84, 6)]     # (seed, party variant)
BOOT_BUDGET = 600000      # frames per boot case (chapter 1 took 240,000-335,000)
DISC_BUILD = os.path.join(OUTR, 'disc', 'BUILD.txt')


def disc_build():
    try:
        return open(DISC_BUILD).read().strip()
    except OSError:
        return None


def disc_md5():
    """md5 of the bin under test (rips/harness/disc/dimguil-en.bin): BUILD.txt is a label
    and was wrong once (2026-10-13: rounds 21 and 22 ran on the fix2 build, labelled
    bf1eac6)."""
    h = hashlib.md5()
    try:
        with open(os.path.join(OUTR, 'disc', 'dimguil-en.bin'), 'rb') as f:
            for b in iter(lambda: f.read(1 << 22), b''):
                h.update(b)
    except OSError:
        return None
    return h.hexdigest()


def boot_cases(n):
    return [dict(id='boot:s%d:v%d' % sv, kind='boot', seed=sv[0], variant=sv[1], expect='proof')
            for sv in (BOOTS * (n // len(BOOTS) + 1))[:n]]


def run_boot(case):
    """Chapter 1 from power-on on the disc under test, to the tablet door."""
    from harness.game import Game
    from harness import chapter1
    g = Game(capture=True)
    run = chapter1.Run(g, seed=case['seed'], variant=case['variant'],
                       out='regress/scratch/boot_%d' % os.getpid(), auto_cases=False)
    g.budget_end = g.frame + BOOT_BUDGET
    f0 = g.frame
    run.run(boot=True)
    done = [x['goal'] for x in run.goals]
    return dict(result='tablet_door' in done or str(done[-1:]), frames=g.frame - f0,
                goals=len(done), stuck=len(run.stuck))


def run_pick(case):
    """One command phase from a battle state: every group pick aimed (battle.aim), none
    failed, and if the case names want_id, some member aimed at that monster."""
    from harness.game import Game
    from harness import battle, ui
    g = Game(capture=True)
    g.load(case['state'])
    f0 = g.frame
    ui.wait_until(g, lambda: battle.in_battle(g) and g.u8(battle.PHASE) == battle.CMD_PHASE,
                  1200, 'command phase')
    log = []
    battle.command_phase(g, battle.default_policy, log)
    aims = [x for x in log if x[1] == 'aim']
    bad = [x for x in log if x[1] == 'aim failed']
    ok = len(aims) >= case.get('min_aims', 1) and not bad and (not case.get('want_id')
                                     or any(x[3] == case['want_id'] for x in aims))
    return dict(result=True if ok else 'aims %s failed %s' % (aims, bad), frames=g.frame - f0,
                aims=[list(x) for x in aims])


def run_friendly(case):
    """battle.fight from a state at or before the friendly-monster menu: it must leave
    (no fight rounds, ('friendly', 'leave') in its actions) and end in the maze."""
    from harness.game import Game
    from harness import battle
    g = Game(capture=True)
    g.load(case['state'])
    f0 = g.frame
    r = battle.fight(g)
    left = any(x[1] == 'friendly' and x[2] == 'leave' for x in r['actions'])
    ok = left and r['rounds'] == 0 and r['ovl'] == 'MAZE'
    return dict(result=True if ok else 'rounds %d ovl %s actions %s' % (
        r['rounds'], r['ovl'], r['actions'][:6]), frames=g.frame - f0)


# DsPacket's two fill loops (asm/bugfix_dspacket_race.asm): (address, bytes)
DSPACKET_FIX = [(0x80036a10, 4), (0x80036a58, 0x18), (0x80036b08, 4), (0x80036b50, 0x18)]
# the 14 words of the fix (rips/harness/t3/metlock/idlast.py; docs/re/bugs.md 1.12)
DSPACKET_WORDS = {
    0x80036a10: 0x00000000, 0x80036a58: 0x3c10800a, 0x80036a5c: 0x8e0286f0,
    0x80036a60: 0x26730001, 0x80036a64: 0xae350000, 0x80036a68: 0x24420001,
    0x80036a6c: 0xae0286f0, 0x80036b08: 0x00000000, 0x80036b50: 0x3c10800a,
    0x80036b54: 0x8e0286f0, 0x80036b58: 0x26730001, 0x80036b5c: 0xae350000,
    0x80036b60: 0x24420001, 0x80036b64: 0xae0286f0}
SLPS = os.path.join(OUTR, 'disc/dimguil/SLPS_026.91')


def disc_fix_words():
    """{address: word} for the 14 fix words as the disc under test's SLPS holds them, or
    None if it doesn't hold exactly DSPACKET_WORDS (or isn't there)."""
    import struct
    try:
        d = open(SLPS, 'rb').read()
    except OSError:
        return None
    t_addr = struct.unpack_from('<I', d, 0x18)[0]
    got = {a: struct.unpack_from('<I', d, a - t_addr + 0x800)[0] for a in DSPACKET_WORDS}
    return got if got == DSPACKET_WORDS else None


# MAIN code a state made before the VWF move (2026-10-17, asm/vwf_lut.inc) doesn't hold:
# the table and wrappers at their new home, and catalog_vwf.asm's `la VWF_LUT` words. The
# overlays a state loads afterwards jump to the new home, so every state case needs these.
# Code only: the old home (0x80060e97) is libds's play state now and is left alone.
# 0x80073c3c-0x80073c47: the width lookup's bound (2026-10-17, vwf review finding 1).
MAIN_CODE = [(0x800159b8, 0x80015b04), (0x80073c34, 0x80073c48), (0x80073cc4, 0x80073cd0)]


def disc_main_code():
    """[(address, bytes)] for MAIN_CODE as the disc under test's SLPS holds it, or []."""
    import struct
    try:
        d = open(SLPS, 'rb').read()
    except OSError:
        return []
    t_addr = struct.unpack_from('<I', d, 0x18)[0]
    return [(a, d[a - t_addr + 0x800:b - t_addr + 0x800]) for a, b in MAIN_CODE]


def overlay_main():
    """From now on in this (case) process, every Game.load lays the disc's fix words and
    MAIN_CODE over MAIN. Returns True if the disc holds the fix words."""
    import struct
    from harness import game
    words = disc_fix_words()
    code = disc_main_code()
    if getattr(game.Game, '_overlaid', False):
        return bool(words)
    load = game.Game.load

    def load_fixed(self, name):
        load(self, name)
        for a, w in sorted((words or {}).items()):
            self.e.write(a, struct.pack('<I', w))
        for a, b in code:
            self.e.write(a, b)
    game.Game.load = load_fixed
    game.Game._overlaid = True
    return bool(words)


def run_cdrace(case):
    """No input from the state for case['frames'] (default 2,000); the longest run of
    frames with a read issued and commands stuck in the CD queue, and when it finished."""
    import struct
    from harness.game import Game
    g = Game(capture=False)
    g.load(case['state'])           # main 'disc': run_case has set the overlay
    run = longest = 0
    issued = done = None
    for f in range(case.get('frames', 2000)):
        bc2, cnt = g.u8(0x80079bc2), g.e.u32(0x800986f0)
        if bc2 == 2 and issued is None:
            issued = f
        run = run + 1 if bc2 == 2 and cnt else 0
        longest = max(longest, run)
        if bc2 == 3 and issued is not None and done is None:
            done = f
        g.e.run(1)
    if case['expect'] == 'stall':
        ok = longest >= 1000 and done is not None
    else:
        ok = done is not None and done - issued < 200 and longest < 60
    return dict(result=True if ok else 'issued %s done %s longest stall %d' % (issued, done, longest),
                frames=case.get('frames', 2000), issued=issued, done=done, longest=longest)


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
    if case.get('chapter', 1) > 1:
        # chapter 2 on (chapters.py): the chapter's own goal list, by name
        from harness import chapters
        run = chapters.Run(g, seed=case.get('seed', 7), variant=case.get('variant', 0),
                           out='regress/scratch/%d' % os.getpid(), retries=1, auto_cases=False)
        run.chapter = case['chapter']
        fns = run.goal_fns(case['chapter'])
        if goal not in fns and goal.startswith('train_'):
            fn = next(f for k, f in fns.items() if k.startswith('train_')) if any(
                k.startswith('train_') for k in fns) else (lambda: True)
        elif goal not in fns and goal.startswith('recover_'):
            fn = run.guarded(run.recover)
        else:
            fn = fns[goal]
    elif goal.startswith('pillar_'):
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
    try:
        r = fn()
    except chapter1.Wiped:
        r = 'wiped'           # a defined outcome: the run reloads its goal state
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
    if case['kind'] != 'boot' and case.get('main') != 'state':
        rec['main_overlay'] = overlay_main()
    try:
        if case['kind'] == 'screen':
            from harness import t5bad
            r = t5bad.ratchet(case['case'])
        else:
            r = run_stuck(case) if case['kind'] == 'stuck' else \
                run_boot(case) if case['kind'] == 'boot' else \
                run_pick(case) if case['kind'] == 'pick' else \
                run_cdrace(case) if case['kind'] == 'cdrace' else \
                run_friendly(case) if case['kind'] == 'friendly' else run_trial(case)
        rec.update(r)
        ok = r['result'] is True if case.get('expect') in ('proof', 'stall', 'read') else True
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
    for res in glob.glob(os.path.join(OUTR, 't3/*/result.json')) + \
            glob.glob(os.path.join(OUTR, 'chapters/*/result.json')):
        for s in json.load(open(res)).get('stuck', []):
            out[s.get('what')] = out.get(s.get('what'), 0) + 1
    return out


LOCK = os.path.join(REG, 'LOCK')


def take_lock():
    """rips/harness/regress/LOCK holds the round's PID and start time while it runs:
    nobody edits scripts/harness/*.py while it's there (the round tests the code as it
    was at the start). A lock left by a dead process is taken over."""
    os.makedirs(REG, exist_ok=True)
    if os.path.exists(LOCK):
        try:
            pid = int(open(LOCK).read().split()[0])
            os.kill(pid, 0)
            sys.exit('regress: a round is already running (LOCK, pid %d)' % pid)
        except (ValueError, IndexError, ProcessLookupError):
            pass                       # stale
    with open(LOCK, 'w') as f:
        f.write('%d %s\n' % (os.getpid(), time.strftime('%Y-%m-%dT%H:%M:%S')))


def drop_lock():
    try:
        if os.path.exists(LOCK) and open(LOCK).read().split()[0] == str(os.getpid()):
            os.remove(LOCK)
    except OSError:
        pass


ROUND = {}         # the round in progress (_main fills it), for an aborted round's line


def record_aborted(reason):
    """A round that stops before its end (killed, or an error in the runner) still gets
    a line in rounds.jsonl: aborted, why, the code hash at its start and now, and the
    cases done so far. It can't count for a commit."""
    if not ROUND or ROUND.get('written'):
        return
    recs = ROUND.get('recs', [])
    failed = sorted(r['id'] for r in recs if not r['ok'])
    rnd = dict(date=ROUND.get('stamp'), code=ROUND.get('hash0'), code_end=code_hash(),
               valid=False, disc=ROUND.get('disc'), disc_md5=ROUND.get('disc_md5'), aborted=reason, note=ROUND.get('note', ''),
               cases_planned=ROUND.get('planned'), cases=len(recs),
               passed=len(recs) - len(failed), failed=failed,
               frames=sum(r.get('frames', 0) for r in recs),
               wall=round(time.time() - ROUND.get('t0', time.time())))
    with open(ROUNDS, 'a') as f:
        f.write(json.dumps(rnd) + '\n')
    ROUND['written'] = True
    print('ABORTED ROUND recorded: %s (%d of %s cases done)' % (reason, len(recs),
                                                              ROUND.get('planned')), flush=True)


def main():
    if '--collect' in sys.argv:
        return _main()
    take_lock()
    import signal
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))   # so `finally` drops the lock
    try:
        return _main()
    except SystemExit as e:
        if e.code == 143:
            record_aborted('killed (SIGTERM)')
        raise
    except KeyboardInterrupt:
        record_aborted('interrupted (SIGINT)')
        raise
    except BaseException as e:
        record_aborted('%s: %s' % (type(e).__name__, e))
        raise
    finally:
        drop_lock()


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trials', type=int, default=10, help='T2 trials per macro')
    ap.add_argument('--only', choices=['stuck', 'trial', 'screen', 'boot', 'pick', 'cdrace', 'friendly'])
    ap.add_argument('--boots', type=int, default=len(BOOTS), help='cold-boot chapter 1 cases')
    ap.add_argument('--procs', type=int, default=MAX_PROCS)
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--note', default='')
    ap.add_argument('--quick', action='store_true',
                    help='fast feedback, about a quarter of the time: every boot, pick, cdrace, '
                         'friendly and screen case, 2 trials per macro, and every 8th stuck case. '
                         "Recorded as partial; it can't count for a publish or a commit")
    a = ap.parse_args()
    if a.quick:
        a.trials = min(a.trials, 2)
    added = collect()
    if a.collect:
        print('added', added)
        return
    saved = load_cases()
    cases = []
    if a.only in (None, 'boot'):
        cases += boot_cases(a.boots)
    if a.only in (None, 'stuck'):
        stuck = sorted((c for c in saved if c['kind'] == 'stuck'), key=lambda c: c['id'])
        cases += stuck[::8] if a.quick else stuck
    if a.only in (None, 'screen'):
        cases += [c for c in saved if c['kind'] == 'screen']
    if a.only in (None, 'pick'):
        cases += [c for c in saved if c['kind'] == 'pick']
    if a.only in (None, 'cdrace'):
        cases += [c for c in saved if c['kind'] == 'cdrace']
    if a.only in (None, 'friendly'):
        cases += [c for c in saved if c['kind'] == 'friendly']
    if a.only in (None, 'trial'):
        gen = trial_cases(a.trials)
        ids = {c['id'] for c in gen}
        cases += gen + [c for c in saved if c['kind'] == 'trial' and c['id'] not in ids]
    # long cases first, so the pool isn't left waiting on one at the end
    cases.sort(key=lambda c: ({'boot': 0, 'stuck': 1}.get(c['kind'], 2), c['id']))
    procs = min(a.procs, MAX_PROCS)
    hash0 = code_hash()
    ROUND.update(hash0=hash0, note=a.note, planned=len(cases), t0=time.time(), disc=disc_build(),
                 disc_md5=disc_md5())
    t0 = time.time()
    recs = []
    ROUND['recs'] = recs
    ctx = mp.get_context('spawn')
    os.makedirs(REG, exist_ok=True)
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
    ROUND['stamp'] = stamp
    with ctx.Pool(procs, maxtasksperchild=1) as pool, \
            open(os.path.join(REG, 'results-%s.jsonl' % stamp.replace(':', '')), 'w') as f:
        for rec in pool.imap_unordered(run_case, cases):
            recs.append(rec)
            f.write(json.dumps(rec, default=str) + '\n'); f.flush()
            print('PASS' if rec['ok'] else 'FAIL', rec['id'], rec.get('result', ''),
                  rec.get('error', ''), rec['wall'], flush=True)
    failed = sorted(r['id'] for r in recs if not r['ok'])
    hash1 = code_hash()
    valid = hash0 == hash1
    if not valid:
        print('!' * 78 + '\nWARNING: scripts/harness/*.py changed during this round (%s at the start, '
              '%s at the end).\nThe round ran on mixed code and is recorded as invalid: it '
              "can't count for a commit.\n" % (hash0, hash1) + '!' * 78, flush=True)
    md5_end = disc_md5()
    if md5_end != ROUND.get('disc_md5'):
        valid = False
        print('WARNING: the disc changed during this round (%s -> %s): invalid'
              % (ROUND.get('disc_md5'), md5_end), flush=True)
    rnd = dict(date=stamp, code=hash0, code_end=hash1, valid=valid, disc=ROUND.get('disc'),
               disc_md5=ROUND.get('disc_md5'), disc_md5_end=md5_end,
               note=a.note, cases=len(recs),
               partial=bool(a.only or a.quick or a.boots < len(BOOTS) or a.trials < 10),
               passed=len(recs) - len(failed), failed=failed,
               by_kind={k: dict(n=sum(1 for r in recs if r['kind'] == k),
                                ok=sum(1 for r in recs if r['kind'] == k and r['ok']))
                        for k in ('boot', 'stuck', 'trial', 'screen', 'pick', 'cdrace',
                                  'friendly')},
               frames=sum(r.get('frames', 0) for r in recs), wall=round(time.time() - t0),
               stuck_causes=latest_stuck_causes())
    ROUND['written'] = True
    with open(ROUNDS, 'a') as f:
        f.write(json.dumps(rnd) + '\n')
    print(json.dumps({k: v for k, v in rnd.items() if k != 'failed'}, indent=1))
    print('FAILED:', failed)
    if not valid:
        print('INVALID ROUND: code changed during the round (%s -> %s)' % (hash0, hash1))
    sys.exit(0 if not failed and valid else 1)


if __name__ == '__main__':
    main()
