#!/usr/bin/env python3
"""The release gate: one chain from power-on to the ending, chapter by chapter, on one disc.

    python3 scripts/harness/fullrun.py CHAIN --seed S --variant K --disc CUE
                                       [--chapters 1-18] [--retries 2] [--resume]

Each chapter is its own run_chapter.py process: chapter 1 from power-on, chapter N --from
chapter N-1's end state of this same chain, with --battle-rng --no-cases --no-main-code
(nothing is laid over a state: every state here was made on CUE from power-on). A chapter
that fails (stuck, out of tries, an error) runs again from the same start state with a new
seed, up to --retries times; if every try fails the chain stops there.

Outputs under rips/harness/fullrun/CHAIN/: cNN_tK/ (run_chapter's outputs for chapter NN,
try K), cNN_tK.out, failures.jsonl (every chapter failure and every goal retry inside a
chapter: chapter, try, goal, what, stuck state), chain.json (per chapter: tries, seeds,
wall, frames, result). Progress goes to the monitor's jobs panel (jobstatus, job 'fullrun').
"""
import argparse, json, os, signal, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from jobstatus import Job

OUT = os.path.join(ROOT, 'rips', 'harness')

ap = argparse.ArgumentParser()
ap.add_argument('chain')
ap.add_argument('--seed', type=int, required=True, help='base seed; try K of chapter N uses seed+10*N+K')
ap.add_argument('--variant', type=int, required=True)
ap.add_argument('--disc', required=True)
ap.add_argument('--chapters', default='1-18')
ap.add_argument('--retries', type=int, default=2)
ap.add_argument('--resume', action='store_true', help='skip chapters chain.json already passed')
ap.add_argument('--status', help="the agent's STATUS.md for the jobs panel")
a = ap.parse_args()
first, _, last = a.chapters.partition('-')
first, last = int(first), int(last or first)

base = 'fullrun/' + a.chain                 # under rips/harness
d = os.path.join(OUT, base)
os.makedirs(d, exist_ok=True)
chain_p = os.path.join(d, 'chain.json')
fail_p = os.path.join(d, 'failures.jsonl')
chain = json.load(open(chain_p)) if (a.resume and os.path.exists(chain_p)) else dict(
    chain=a.chain, seed=a.seed, variant=a.variant, disc=a.disc, chapters={}, started=time.time())
chain['code'] = ROOT

job = Job('fullrun', purpose='release gate: power-on to the ending on the shipping disc',
          total=last - first + 1, outputs=[chain_p, fail_p], part='chain %s v%d' % (a.chain, a.variant),
          arm=a.chain, status=a.status, keys=['passed', 'retried', 'failed'])

child = [None]


def _term(signum, frame):
    if child[0] and child[0].poll() is None:
        child[0].terminate()
        try:
            child[0].wait(120)
        except subprocess.TimeoutExpired:
            child[0].kill()
    chain['stopped'] = 'SIGTERM'
    save()
    job.finish('stopped (SIGTERM)')
    sys.exit(1)


def save():
    json.dump(chain, open(chain_p + '.new', 'w'), indent=1, default=str)
    os.replace(chain_p + '.new', chain_p)


def log_fail(x):
    with open(fail_p, 'a') as f:
        f.write(json.dumps(x, default=str) + '\n')


signal.signal(signal.SIGTERM, _term)

src = None
if first > 1:
    prev = chain['chapters'].get(str(first - 1))
    if not prev or not prev.get('passed'):
        sys.exit('chapter %d needs chapter %d passed in %s' % (first, first - 1, chain_p))
    src = prev['end']

for n in range(first, last + 1):
    rec = chain['chapters'].get(str(n))
    if a.resume and rec and rec.get('passed'):
        src = rec['end']
        job.done_one({'chapter': n, 'skipped': True})
        continue
    rec = chain['chapters'][str(n)] = dict(tries=[], passed=False, start=src)
    for k in range(a.retries + 1):
        seed = a.seed + 10 * n + k
        name = '%s/c%02d_t%d' % (base, n, k)
        cmd = [sys.executable, os.path.join(HERE, 'run_chapter.py'), '../' + name,
               '--chapters', str(n), '--seed', str(seed), '--variant', str(a.variant),
               '--disc', a.disc, '--no-cases', '--shots', base + '/shots']
        if src:
            cmd += ['--from', src, '--battle-rng', '--no-main-code']
        job.step('c%d try %d (seed %d)' % (n, k, seed))
        t0 = time.time()
        with open(os.path.join(OUT, name + '.out'), 'w') as fo:
            child[0] = subprocess.Popen(cmd, cwd=ROOT, stdout=fo, stderr=subprocess.STDOUT)
            rc = child[0].wait()
        wall = round(time.time() - t0, 1)
        rp = os.path.join(OUT, name, 'result.json')
        try:
            res = json.load(open(rp))
        except Exception as e:
            res = dict(ok=False, error='no result.json (rc %d): %s' % (rc, e))
        end = '%s/c%d_end' % (name, n)
        ok = bool(res.get('ok')) and rc == 0 and os.path.exists(os.path.join(OUT, end + '.state'))
        for s in res.get('stuck') or []:
            log_fail(dict(chain=a.chain, chapter=n, try_=k, seed=seed, kind='goal retry',
                          goal=s.get('goal'), goal_try=s.get('try_'), what=s.get('what'),
                          info=s.get('info'), where=s.get('where'),
                          state=os.path.join(OUT, str(s.get('state'))) + '.state',
                          chapter_passed=ok))
        t = dict(try_=k, seed=seed, ok=ok, rc=rc, wall=wall, frames=res.get('total_frames'),
                 run=name, error=res.get('error'), stuck=len(res.get('stuck') or []),
                 main_code_laid=res.get('main_code_laid'), battle_code=res.get('battle_code'))
        rec['tries'].append(t)
        if ok:
            rec.update(passed=True, end=end, wall=wall, frames=t['frames'])
            save()
            job.tally('passed')
            job.event('c%d passed on try %d, %.0f min' % (n, k, wall / 60))
            job.done_one({'chapter': n, 'tries': k + 1, 'wall': wall})
            break
        fs = os.path.join(OUT, name, 'final_fail.state')
        last_stuck = (res.get('stuck') or [{}])[-1]
        log_fail(dict(chain=a.chain, chapter=n, try_=k, seed=seed, kind='chapter failed',
                      goal=(res.get('info') or {}).get('goal') or last_stuck.get('goal'),
                      what=res.get('error'), info=res.get('info'), rc=rc,
                      state=fs if os.path.exists(fs) else None, out=os.path.join(OUT, name + '.out')))
        save()
        job.tally('retried' if k < a.retries else 'failed')
        job.event('c%d try %d failed: %s' % (n, k, (res.get('error') or 'rc %d' % rc)[:80]))
    if not rec['passed']:
        chain['stopped_at'] = n
        chain['finished'] = time.time()
        save()
        job.finish('stopped at chapter %d after %d tries' % (n, a.retries + 1))
        sys.exit(2)
    src = rec['end']

chain['finished'] = time.time()
chain['reached_end'] = last == 18
save()
tot = sum(c.get('wall') or 0 for c in chain['chapters'].values())
job.finish('chapters %d-%d passed, %.1f h of passing runs' % (first, last, tot / 3600))
