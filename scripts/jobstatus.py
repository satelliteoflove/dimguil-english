#!/usr/bin/env python3
"""A progress file for any long job, so scripts/monitor.py can show it (jobs panel).

    import sys; sys.path.insert(0, 'scripts')       # or wherever scripts/ is
    from jobstatus import Job
    j = Job('golembench', purpose='golem chain, arms x states x seeds', total=20,
            outputs=['rips/harness/ch19/golembench/bench/b_v6b_1-10.jsonl'])
    for seed in seeds:
        j.step(f'seed {seed}')                     # what it's doing now
        ...
        j.tally('FG won')                          # counters, summed across workers
        j.event(f'seed {seed}: FG won r16')        # a line in the recent-events list
        j.done_one({'seed': seed, 'won': 1})       # one unit of `total` finished
        j.section('now', ['party: ...', 'where: ...'])  # named text blocks, replaced each call
    j.finish('12/20 won')

Each process writes its own rips/monitor/jobs/NAME-PID.json in the main copy (found from a
worktree through git's commondir), atomically, at most about once a second, plus at
finish and at exit. Several workers of one job use the same NAME (and, for a launch that
should stay apart from an earlier one of the same name, the same `run`, or JOB_RUN in the
environment); the monitor sums them. `part` labels a worker ('n5 v6b 1-10') and `arm`
groups workers for a done/total per arm. Sections are a worker's own live view (a chain's
current chapter, party and place, a table of times): the job detail shows each worker's
sections in full, under the worker's part. No dependencies beyond the standard library.

Environment, read when the argument isn't given: JOB_AGENT (agent), JOB_RUN (run),
JOB_PART (part), JOB_ARM (arm), JOB_STATUS (the agent's STATUS.md), JOBSTATUS_DIR (where
the files go).
"""
import atexit, json, os, re, threading, time

EVENTS = 50
EVERY = 1.0


def repo_root(start=None):
    """The copy this file (or `start`) is in."""
    d = os.path.abspath(start or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    while True:
        if os.path.exists(os.path.join(d, '.git')):
            return d
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def main_root(start=None):
    """The main copy: a worktree's .git file points at main/.git/worktrees/NAME, whose
    commondir file leads back to main/.git."""
    root = repo_root(start)
    if not root:
        return None
    g = os.path.join(root, '.git')
    if os.path.isfile(g):
        try:
            line = open(g).read().strip()
            gitdir = line.split(':', 1)[1].strip() if line.startswith('gitdir:') else None
            if gitdir:
                gitdir = os.path.join(root, gitdir)
                common = os.path.join(gitdir, open(os.path.join(gitdir, 'commondir')).read().strip())
                return os.path.dirname(os.path.realpath(common))
        except (OSError, IndexError):
            pass
    return root


def jobs_dir():
    if os.environ.get('JOBSTATUS_DIR'):
        return os.environ['JOBSTATUS_DIR']
    root = main_root() or os.getcwd()
    return os.path.join(root, 'rips', 'monitor', 'jobs')


class Job:
    def __init__(self, name, purpose='', total=None, outputs=(), agent=None, worktree=None,
                 part=None, arm=None, run=None, status=None, keys=None, every=EVERY):
        """keys: the tally keys the monitor's list shows, in order (default: all)."""
        self.every = every
        self.lock = threading.Lock()
        self.last_write = 0.0
        self.timer = None
        cwd = os.getcwd()
        wt = worktree or repo_root(cwd) or cwd
        agent = agent or os.environ.get('JOB_AGENT')
        status = status or os.environ.get('JOB_STATUS')
        if not status and agent:
            for base in {wt, main_root(cwd) or wt}:
                p = os.path.join(base, 'rips', 'agents', agent, 'STATUS.md')
                if os.path.exists(p):
                    status = p
                    break
        self.d = dict(
            name=name, purpose=purpose, run=run or os.environ.get('JOB_RUN'),
            part=part or os.environ.get('JOB_PART'), arm=arm or os.environ.get('JOB_ARM'),
            agent=agent, worktree=os.path.abspath(wt), cwd=cwd,
            status=os.path.abspath(status) if status else None,
            pid=os.getpid(), start=time.time(), updated=None, total=total, done=0,
            step=None, step_since=None, tally={}, keys=list(keys) if keys else None, events=[],
            done_times=[], last_result=None,
            outputs=[os.path.abspath(p) for p in outputs], finished=None, summary=None, exited=None,
            sections={})
        safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', name)[:60]
        self.dir = jobs_dir()
        self.path = os.path.join(self.dir, f'{safe}-{os.getpid()}.json')
        atexit.register(self._exit)
        self._write(force=True)

    # --- the API ---
    def step(self, note):
        with self.lock:
            self.d['step'], self.d['step_since'] = str(note), time.time()
        self._write()

    def done_one(self, result=None, n=1):
        with self.lock:
            self.d['done'] += n
            self.d['done_times'] = (self.d['done_times'] + [round(time.time(), 1)])[-200:]
            if result is not None:
                self.d['last_result'] = result
        self._write()

    def tally(self, key, n=1):
        with self.lock:
            t = self.d['tally']
            t[key] = t.get(key, 0) + n
        self._write()

    def event(self, text):
        with self.lock:
            self.d['events'] = (self.d['events'] + [[round(time.time(), 1), str(text)]])[-EVENTS:]
        self._write()

    def section(self, title, lines):
        """Replace the text block `title` (a list of lines; None drops it)."""
        with self.lock:
            if lines is None:
                self.d['sections'].pop(title, None)
            else:
                self.d['sections'][title] = [str(x) for x in lines]
        self._write()

    def set_total(self, total):
        with self.lock:
            self.d['total'] = total
        self._write()

    def add_output(self, path):
        with self.lock:
            p = os.path.abspath(path)
            if p not in self.d['outputs']:
                self.d['outputs'].append(p)
        self._write()

    def finish(self, summary=None):
        with self.lock:
            self.d['finished'], self.d['summary'], self.d['step'] = time.time(), summary, None
        self._write(force=True)

    # --- writing ---
    def _exit(self):
        if not self.d['finished']:
            self.d['exited'] = time.time()
        self._write(force=True)

    def _write(self, force=False):
        now = time.time()
        if not force and now - self.last_write < self.every:
            # rate-limited: a timer writes the latest state when the second is up
            with self.lock:
                if self.timer is None:
                    self.timer = threading.Timer(self.every - (now - self.last_write), self._flush)
                    self.timer.daemon = True
                    self.timer.start()
            return
        self._flush()

    def _flush(self):
        with self.lock:
            self.timer = None
            self.last_write = time.time()
            self.d['updated'] = self.last_write
            data = json.dumps(self.d, default=str)
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = f'{self.path}.tmp{os.getpid()}'
            with open(tmp, 'w') as f:
                f.write(data)
            os.replace(tmp, self.path)
        except OSError:
            pass            # progress reporting never stops the job


if __name__ == '__main__':
    print(jobs_dir())
