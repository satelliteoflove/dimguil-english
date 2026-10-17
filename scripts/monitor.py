#!/usr/bin/env python3
"""A live terminal monitor for bot chapter runs, suite rounds, fight benches and long jobs.

    python3 scripts/monitor.py              # full screen, refreshes every 2 s; Ctrl+C quits
    python3 scripts/monitor.py --once       # print one frame and exit
    python3 scripts/monitor.py --hours 24   # list runs started in the last 24 hours (default 12)

Reads only what the harness already writes, so nothing has to be started differently:
  chapter runs   rips/harness/**/NAME.pid, NAME.out (goal lines) and NAME/live.jsonl (events)
  suite rounds   rips/harness/regress/LOCK, results-*.jsonl, rounds.jsonl
  benches        running fightbench.py processes and the .jsonl they write; each one seen is
                 kept in rips/monitor/benches.json, so finished benches stay listed
  jobs           rips/monitor/jobs/*.json, written by anything using scripts/jobstatus.py
  agents         every rips/agents/*/STATUS.md and rips/harness/**/STATUS.md (main copy and
                 worktrees) changed in the last 24 hours
  processes      for any emulator or harness script, Enter shows its worktree, its agent's
                 status file and the files it has open for writing
Samples (CPU, emulators running, suite progress, each run's frames) go to
rips/monitor/history.jsonl every 10 s, so the graphs keep their history across restarts.
"""
import argparse, glob, json, os, re, statistics, time
from collections import deque
import psutil
import jobstatus
from rich import box
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
H = os.path.join(ROOT, 'rips', 'harness')
HIST = os.path.join(ROOT, 'rips', 'monitor', 'history.jsonl')
BENCHES = os.path.join(ROOT, 'rips', 'monitor', 'benches.json')
MAIN = jobstatus.main_root(ROOT) or ROOT        # the main copy, when this runs from a worktree
WORKTREES = os.path.join(os.path.dirname(MAIN), 'worktrees')
JOBS = jobstatus.jobs_dir()
USAGE = os.path.expanduser('~/.claude/state/usage.json')
BARS = '▁▂▃▄▅▆▇█'
FPS = 60.0


def spark(vals, width, lo=None, hi=None):
    """The last `width` values as a one-line block graph."""
    vals = [v for v in vals if v is not None][-width:]
    if not vals:
        return ''
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    span = (hi - lo) or 1
    return ''.join(BARS[min(7, max(0, int((v - lo) / span * 7.999)))] for v in vals)


def bar(frac, width, color='green'):
    frac = max(0.0, min(1.0, frac))
    n = int(round(frac * width))
    return Text('█' * n, style=color) + Text('·' * (width - n), style='grey35')


def hms(secs):
    secs = int(max(0, secs))
    h, r = divmod(secs, 3600)
    return f'{h}:{r // 60:02d}:{r % 60:02d}' if h else f'{r // 60}:{r % 60:02d}'


def ago(t):
    return hms(time.time() - t) + ' ago'


# --- incremental readers ---------------------------------------------------------------

class Tail:
    """Lines appended to a file since the last read."""
    def __init__(self, path):
        self.path, self.pos = path, 0

    def new(self):
        try:
            with open(self.path, 'rb') as f:
                f.seek(self.pos)
                data = f.read()
        except OSError:
            return []
        end = data.rfind(b'\n') + 1
        self.pos += end
        return data[:end].decode('utf-8', 'replace').splitlines()


class Run:
    """One chapter run: NAME.pid, NAME.out and NAME/live.jsonl."""
    GOAL = re.compile(r'^goal (\S+) (\S+): (\d+) frames, ([\d.]+) s, (\d+) tries')

    def __init__(self, pidfile):
        self.pidfile = pidfile
        self.dir = pidfile[:-4]
        self.name = os.path.basename(self.dir)
        self.chapter = os.path.basename(os.path.dirname(pidfile))
        self.out, self.live = Tail(self.dir + '.out'), Tail(os.path.join(self.dir, 'live.jsonl'))
        self.goals, self.frame, self.fights, self.deaths, self.temple, self.retries = [], 0, 0, 0, 0, 0
        self.boss_fights, self.boss_wins = 0, 0
        self.party, self.levels, self.where, self.last, self.goal_now = [], [], None, '', ''
        self.death_frames, self.result = [], None
        self.recent = deque(maxlen=3)      # the last three deaths and retries, newest last
        self.events = []                   # (frame, text) of every death and retry, for the detail view
        try:
            self.pid = int(open(pidfile).read().split()[0])
        except (OSError, ValueError, IndexError):
            self.pid = None
        self.started = os.path.getmtime(pidfile)

    def update(self):
        for line in self.out.new():
            m = self.GOAL.match(line)
            if m:
                self.goals.append((m.group(2), int(m.group(5)), float(m.group(4))))
            elif line.startswith('{') and '"stuck"' in line:
                try:
                    self.result = json.loads(line)
                except ValueError:
                    pass
        for line in self.live.new():
            try:
                f, kind, *rest = json.loads(line)
            except (ValueError, TypeError):
                continue
            self.frame = max(self.frame, f)
            d = rest[0] if rest else None
            if kind == 'fought' and isinstance(d, dict):
                self.fights += 1
                if d.get('story'):
                    self.boss_fights += 1
                    if d.get('hp_end'):
                        self.boss_wins += 1
            elif kind == 'death' and isinstance(d, dict):
                self.deaths += 1
                self.death_frames.append(f)
                self.last = f"{d.get('who')} {d.get('fell')} ({d.get('by')}, {d.get('what')})"
                self.recent.append(self.last)
                self.goal_now = d.get('goal') or self.goal_now
                w = d.get('where') or []
                self.events.append((f, f"{self.last}  at area {w[0] if w else '?'} {w[1:] if w else ''}"
                                       f"  [{d.get('goal', '')}]"))
            elif kind == 'temple':
                self.temple += 1
            elif kind == 'retry':
                self.retries += 1
                self.goal_now = rest[0] if rest else self.goal_now
                self.last = f'retry {rest[0]}: {rest[1]}' if len(rest) > 1 else 'retry'
                self.recent.append(self.last)
                self.events.append((f, self.last))
            elif kind in ('gate heal', 'home heal', 'hp heal') and rest and isinstance(rest[-1], list) \
                    and rest[-1] and isinstance(rest[-1][0], list) and len(rest[-1][0]) == 3:
                self.party = rest[-1]
            elif kind == 'trip home' and isinstance(d, list):
                self.levels = d
            if isinstance(d, dict) and 'area' in d:
                self.where = (d['area'], d.get('x'), d.get('y'), d.get('ovl'))

    def proc(self):
        try:
            p = psutil.Process(self.pid)
            if 'run_chapter' in ' '.join(p.cmdline()):
                return p
        except (psutil.Error, TypeError):
            pass
        return None

    def state(self):
        p = self.proc()
        if p:
            return 'running', p.create_time()
        if glob.glob(os.path.join(self.dir, '*_end.state')):
            return 'done', None
        err = (self.result or {}).get('error') or ''
        if err and 'SIGTERM' not in err:
            return 'failed', None
        return 'stopped', None


class Suite:
    LOCK = os.path.join(H, 'regress', 'LOCK')
    ROUNDS = os.path.join(H, 'regress', 'rounds.jsonl')

    def __init__(self):
        self.tail, self.done, self.ok, self.failed, self.file = None, 0, 0, [], None

    def history(self, n=20):
        out = []
        try:
            for line in open(self.ROUNDS):
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('cases'):
                    out.append(r)
        except OSError:
            pass
        return out[-n:]

    def running(self):
        try:
            pid, start = open(self.LOCK).read().split()[:2]
            return int(pid), start
        except (OSError, ValueError):
            return None

    def update(self, lock):
        if not lock:
            self.tail = None
            return
        stamp = lock[1].replace('-', '').replace(':', '')
        files = sorted(glob.glob(os.path.join(H, 'regress', 'results-*.jsonl')))
        cur = files[-1] if files else None
        if cur and cur != self.file:
            self.file, self.tail, self.done, self.ok, self.failed = cur, Tail(cur), 0, 0, []
        if self.tail:
            for line in self.tail.new():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                self.done += 1
                if r.get('ok'):
                    self.ok += 1
                else:
                    self.failed.append(r.get('id', '?'))


BENCH_SCRIPTS = ('fightbench.py', 'golembench.py')
# arm settings a bench takes from the environment, shown in the settings column
BENCH_ENV = ('OSLO', 'STACK', 'NOFIS', 'NOFIS_AWARE', 'FIRE', 'TROLL', 'MORLIS', 'CONFUSE')


def benches():
    out = []
    for p in psutil.process_iter(['pid', 'cmdline', 'cwd', 'create_time']):
        cl = p.info['cmdline'] or []
        if len(cl) > 4 and any(c.endswith(BENCH_SCRIPTS) for c in cl) and 'run' in cl:
            i = cl.index('run')
            path, seeds, states = cl[i + 1], cl[i + 2], cl[i + 3:]
            path = path if os.path.isabs(path) else os.path.join(p.info['cwd'] or ROOT, path)
            a, _, b = seeds.partition('-')
            try:
                total = (int(b or a) - int(a) + 1) * max(1, len(states))
            except ValueError:
                total = 0
            env = ''
            try:
                e = p.environ()
                env = ' '.join(([e['SET']] if e.get('SET') else []) + [f'{k}={e[k]}' for k in BENCH_ENV if e.get(k)])
            except psutil.Error:
                pass
            out.append(dict(path=path, total=total, since=p.info['create_time'], env=env, pid=p.info['pid']))
    return out


ROWS = {}


def bench_rows(path):
    """Every fight line in a bench file, re-read only when the file changes."""
    try:
        st = os.stat(path)
    except OSError:
        return []
    key = (st.st_mtime, st.st_size)
    if ROWS.get(path, (None,))[0] != key:
        rows = []
        for line in open(path, errors='replace'):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                rows.append(r)
        ROWS[path] = (key, rows)
    return ROWS[path][1]


def chain(r):
    """The fights of a chain row (a bench that plays several fights in a row, like the
    golem route), or None for an ordinary one-fight row."""
    f = r.get('fights')
    return [x for x in f if isinstance(x, dict)] if isinstance(f, list) else None


def dead(r):
    c = chain(r)
    if c is not None:
        return sum(dead(x) for x in c)
    return max(r.get('dead') or 0, len(r.get('deaths') or []))


def death_text(d):
    """A bench death record as one line: (who, what, by) from fightbench, or anything
    else a bench writes (longer tuples, dicts), so a new shape can't crash the view."""
    if isinstance(d, dict):
        who = d.get('who') or d.get('name') or '?'
        what = d.get('what') or d.get('how') or d.get('fell') or ''
        by_ = d.get('by')
        rest = {k: v for k, v in d.items() if k not in ('who', 'name', 'what', 'how', 'fell', 'by')}
        return f"{who}: {what}" + (f" from {by_}" if by_ else '') + (f"  {rest}" if rest else '')
    if isinstance(d, (list, tuple)):
        if len(d) >= 3:
            extra = ', '.join(map(str, d[3:]))
            return f"{d[0]}: {d[1]} from {d[2]}" + (f"  ({extra})" if extra else '')
        return ': '.join(map(str, d))
    return str(d)


def outcome(r):
    c = chain(r)
    if c is not None:       # won only if every fight in the chain was won and it ended clean
        if c and all(x.get('won') for x in c) and not r.get('error') and r.get('ring', True) is not False:
            return 'won'
        return 'wiped' if any(x.get('wiped') for x in c) else 'lost'
    if r.get('won'):
        return 'won'
    if r.get('wiped'):
        return 'wiped'
    if (r.get('fled') or [0])[0]:
        return 'fled'
    return 'lost'


def tally(rows):
    out = dict(n=len(rows), won=0, wiped=0, fled=0, lost=0, dead=0, rounds=0, hp=0)
    for r in rows:
        out[outcome(r)] += 1
        out['dead'] += dead(r)
        out['rounds'] += r.get('rounds') or sum(x.get('rounds') or 0 for x in chain(r) or [])
        out['hp'] += r.get('hp_lost') or 0
    return out


def counted(names):
    c = {}
    for n in names:
        c[n] = c.get(n, 0) + 1
    return ', '.join(f'{n}×{k}' if k > 1 else n for n, k in sorted(c.items(), key=lambda x: -x[1]))


PROCS = {}


def emulators():
    out = []
    for p in psutil.process_iter(['pid', 'cmdline', 'create_time', 'memory_info', 'cwd']):
        cl = ' '.join(p.info['cmdline'] or [])
        if 'python' not in cl or 'monitor.py' in cl:
            continue
        kind = ('chapter' if 'run_chapter' in cl else 'suite' if 'regress.py' in cl or 'spawn_main' in cl
                else 'bench' if any(s in cl for s in BENCH_SCRIPTS) else None)
        if not kind:
            # one-off scripts (an agent's verify or probe) still drive the emulator core
            try:
                with open('/proc/%d/maps' % p.info['pid']) as f:
                    kind = 'other' if 'mednafen_psx' in f.read() else None
            except OSError:
                pass
        if not kind and harness_script(p.info['cmdline'] or [], p.info['cwd']):
            kind = 'script'
        if not kind:
            continue
        if kind == 'suite' and 'spawn_main' in cl:
            try:
                if 'regress' not in ' '.join(p.parent().cmdline()):
                    continue
            except psutil.Error:
                continue
        q = PROCS.setdefault(p.info['pid'], p)
        try:
            cpu = q.cpu_percent(None)
        except psutil.Error:
            cpu = 0.0
        short = ' '.join(os.path.basename(c) if c.endswith('.py') else
                         '/'.join(c.split('/')[-3:]) if c.startswith('/') else c
                         for c in (p.info['cmdline'] or [])[1:])
        out.append((p.info['pid'], kind, cpu, (p.info['memory_info'].rss if p.info['memory_info'] else 0),
                    p.info['create_time'], short, p.info['cwd'], p.info['cmdline'] or []))
    return out


def harness_script(cmdline, cwd):
    """A python script of ours that doesn't drive the emulator: one under scripts/harness/,
    or one under rips/ or a worktree, started from this repo or a worktree."""
    if not cwd or not (cwd.startswith(MAIN) or cwd.startswith(WORKTREES)):
        return False
    for c in cmdline[1:]:
        if not c.endswith('.py'):
            continue
        path = os.path.abspath(os.path.join(cwd, c))
        if 'scripts/harness/' in path or '/rips/' in path or path.startswith(WORKTREES):
            return True
    return False


# --- jobs (scripts/jobstatus.py files) -------------------------------------------------

JOBFILES = {}


def job_workers():
    """Every jobstatus file of the last 72 hours, with each worker's state."""
    now, out = time.time(), []
    try:
        names = [n for n in os.listdir(JOBS) if n.endswith('.json')]
    except OSError:
        names = []
    for n in names:
        path = os.path.join(JOBS, n)
        try:
            st = os.stat(path)
        except OSError:
            continue
        if st.st_mtime < now - 72 * 3600:
            continue
        key = (st.st_mtime, st.st_size)
        if JOBFILES.get(path, (None,))[0] != key:
            try:
                d = json.load(open(path))
            except (OSError, ValueError):
                continue
            if not isinstance(d, dict) or 'name' not in d:
                continue
            JOBFILES[path] = (key, d)
        w = dict(JOBFILES[path][1], file=path)
        w['state'] = worker_state(w, now)
        out.append(w)
    return out


def worker_state(w, now):
    """finished, running, stale (alive but quiet far longer than its pace), exited (ended
    without finish) or dead (the process is gone with no word)."""
    if w.get('finished'):
        return 'finished'
    alive = False
    try:
        p = psutil.Process(w.get('pid'))
        alive = p.create_time() <= (w.get('start') or now) + 5 and p.status() != psutil.STATUS_ZOMBIE
    except (psutil.Error, TypeError, ValueError):
        pass
    if alive:
        upd, done = w.get('updated') or w.get('start') or now, w.get('done') or 0
        pace = (upd - (w.get('start') or upd)) / done if done else 0
        return 'stale' if now - upd > max(900, 3 * pace) else 'running'
    return 'exited' if w.get('exited') else 'dead'


def w_end(w):
    if w['state'] in ('running', 'stale'):
        return float('inf')
    return w.get('finished') or w.get('exited') or w.get('updated') or w.get('start') or 0


def job_groups(workers):
    """Workers grouped into jobs: same name and run; with no run given, a worker that
    starts after every worker so far has ended begins a new job (a later launch)."""
    by = {}
    for w in workers:
        by.setdefault((w['name'], w.get('run') or ''), []).append(w)
    groups = []
    for (name, run), ws in by.items():
        ws.sort(key=lambda w: w.get('start') or 0)
        clusters, cur, end = [], [], -1.0
        for w in ws:
            if cur and not run and (w.get('start') or 0) > end:
                clusters.append(cur)
                cur, end = [], -1.0
            cur.append(w)
            end = max(end, w_end(w))
        if cur:
            clusters.append(cur)
        groups += [job_sum(name, run, c) for c in clusters]
    return groups


def job_sum(name, run, ws):
    now = time.time()
    states = [w['state'] for w in ws]
    state = ('running' if 'running' in states else 'stale' if 'stale' in states else
             'finished' if all(s == 'finished' for s in states) else 'dead' if 'dead' in states else 'exited')
    tally, keys, events, outputs, arms = {}, [], [], [], {}
    for w in ws:
        for k, v in (w.get('tally') or {}).items():
            if isinstance(v, (int, float)):
                tally[k] = tally.get(k, 0) + v
        for k in (w.get('keys') or []):
            if k not in keys:
                keys.append(k)
        tag = (w.get('part') or str(w.get('pid'))) if len(ws) > 1 else ''
        events += [(e[0], tag, e[1]) for e in (w.get('events') or []) if isinstance(e, list) and len(e) > 1]
        outputs += [p for p in w.get('outputs') or [] if p not in outputs]
        if w.get('arm'):
            a = arms.setdefault(w['arm'], [0, 0])
            a[0] += w.get('done') or 0
            a[1] += w.get('total') or 0
    first = lambda k: next((w.get(k) for w in ws if w.get(k)), None)
    start = min(w.get('start') or now for w in ws)
    end = None if state in ('running', 'stale') else max(w_end(w) for w in ws)
    done = sum(w.get('done') or 0 for w in ws)
    totals = [w.get('total') for w in ws]
    total = sum(t for t in totals if t) if any(totals) else None
    el = (end or now) - start
    rate = done / el * 3600 if el > 0 and done else 0.0          # per hour
    eta = (total - done) / rate * 3600 if rate and total and end is None and total > done else None
    return dict(name=name, run=run, workers=ws, state=state, start=start, end=end, done=done, total=total,
                rate=rate, eta=eta, tally=tally, keys=keys or list(tally), arms=arms,
                events=sorted(events, key=lambda e: e[0]), outputs=outputs,
                purpose=first('purpose') or '', agent=first('agent'), worktree=first('worktree'),
                status=first('status'), summary=[w.get('summary') for w in ws if w.get('summary')],
                updated=max(w.get('updated') or 0 for w in ws))


def rate_text(per_hour):
    if not per_hour:
        return '-'
    return f'{per_hour / 60:.1f}/min' if per_hour >= 120 else f'{per_hour:.1f}/h'


def tally_text(j, limit=None):
    keys = j['keys'][:limit] if limit else j['keys']
    return '  '.join(f'{k} {j["tally"].get(k, 0):g}' for k in keys)


JOB_COLOR = dict(running='green', stale='yellow', finished='cyan', exited='yellow', dead='red')
JOB_MARK = dict(running='●', stale='◌', finished='✓', exited='■', dead='✗')


# --- agent status files ----------------------------------------------------------------

STATUSES = {}


def status_info(path):
    """(task line, latest report heading, mtime) of a STATUS.md, re-read when it changes."""
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return None
    if STATUSES.get(path, (None,))[0] != mt:
        task = title = report = last_h = None
        more = False                # the task line goes on to the next lines of its paragraph
        try:
            for line in open(path, errors='replace'):
                s = line.strip()
                if title is None and s.startswith('# '):
                    title = s[2:]
                if more:
                    more = bool(s) and not re.match(r"^(#|[-*] |\w[\w ]{0,20}:|Worktree\b)", s) and len(task) < 300
                    if more:
                        task += ' ' + s
                m = re.match(r'^\**task\**\s*(?:\([^)]*\))?\s*:\s*\**\s*(.*)', s, re.I)
                if task is None and m:
                    task, more = m.group(1), True
                if s.startswith('## '):
                    last_h = s[3:]
                    if s[3:].lower().startswith('report'):
                        report = s[3:]
        except OSError:
            return None
        STATUSES[path] = (mt, dict(task=task or title or '', title=title or '', report=report or last_h or '',
                                   mtime=mt, path=path))
    return STATUSES[path][1]


def status_name(path):
    """A short name: agents/NAME, harness/ch19/golembench, or wt NAME: agents/X."""
    p = os.path.abspath(path)
    for base, pre in ((os.path.join(MAIN, 'rips'), ''), (WORKTREES, 'wt ')):
        if p.startswith(base + '/'):
            rel = os.path.dirname(os.path.relpath(p, base))
            if pre:
                wt, _, rest = rel.partition('/')
                rel = f'{wt}: {rest.replace("rips/", "", 1)}'
            return pre + rel
    return os.path.dirname(p)


def agent_files(age=24 * 3600):
    """Every agent STATUS.md changed in the last `age` seconds: rips/agents/*/ and up to
    three levels under rips/harness/, in the main copy and in each worktree's own rips/."""
    cut, found = time.time() - age, set()
    roots = [os.path.join(MAIN, 'rips')] + glob.glob(os.path.join(WORKTREES, '*', 'rips'))
    for r in roots:
        found.update(glob.glob(os.path.join(r, 'agents', '*', 'STATUS.md')))
        h = os.path.join(r, 'harness')
        if os.path.islink(h) or not os.path.isdir(h):
            continue
        for d, dirs, files in os.walk(h):
            depth = os.path.relpath(d, h).count('/') + (d != h)
            dirs[:] = [] if depth >= 3 else [x for x in dirs if not x.startswith('snap_') and x not in
                                             ('regress', 'disc', 'states') and not os.path.islink(os.path.join(d, x))]
            if 'STATUS.md' in files:
                found.add(os.path.join(d, 'STATUS.md'))
    out = []
    for p in found:
        i = status_info(p)
        if i and i['mtime'] >= cut:
            out.append(dict(i, name=status_name(p)))
    return sorted(out, key=lambda x: -x['mtime'])


def tail_lines(path, n, limit=1 << 16):
    try:
        with open(path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - limit))
            data = f.read()
    except OSError:
        return []
    return data.decode('utf-8', 'replace').splitlines()[-n:]


def is_text(path):
    try:
        with open(path, 'rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4096))
            data = f.read()
    except OSError:
        return False
    return b'\0' not in data


# --- what a process is doing, for the ones that write no job file ----------------------

def worktree_of(path):
    """(copy root, branch) for a path inside the main copy or a worktree."""
    root = jobstatus.repo_root(path) if path else None
    if not root:
        return None, None
    branch = None
    try:
        g = os.path.join(root, '.git')
        gitdir = open(g).read().split(':', 1)[1].strip() if os.path.isfile(g) else g
        head = open(os.path.join(gitdir, 'HEAD')).read().strip()
        branch = head.split('refs/heads/', 1)[1] if 'refs/heads/' in head else head[:10]
    except (OSError, IndexError):
        pass
    return root, branch


def status_for(cwd, cmdlines, root):
    """The agent status files that belong to a process, best first: a STATUS.md in a folder
    above any path on its (or its parent's) command line, then rips/agents/WORKTREE/ in the
    main copy or the worktree, then any in the worktree's rips/agents/."""
    out = []

    def add(p):
        p = os.path.abspath(p)
        if os.path.isfile(p) and p not in out:
            out.append(p)
    top = root or cwd or '/'
    for cl in cmdlines:
        for c in cl[1:]:
            if '/' not in c or c.startswith('-'):
                continue
            for base in (cwd or ROOT, os.path.join(top, 'rips', 'harness')):
                d = os.path.dirname(os.path.abspath(os.path.join(base, c)))
                while d.startswith(top) and len(d) > len(top) and not os.path.basename(d) == 'rips':
                    if os.path.isfile(os.path.join(d, 'STATUS.md')):
                        add(os.path.join(d, 'STATUS.md'))
                        break
                    d = os.path.dirname(d)
    if root and root != MAIN:          # the main copy's rips/agents holds every agent's file
        name = os.path.basename(root)
        add(os.path.join(MAIN, 'rips', 'agents', name, 'STATUS.md'))
        add(os.path.join(root, 'rips', 'agents', name, 'STATUS.md'))
        for p in sorted(glob.glob(os.path.join(root, 'rips', 'agents', '*', 'STATUS.md')),
                        key=os.path.getmtime, reverse=True):
            add(p)
    return out


def write_files(pid):
    """Regular files the process has open for writing, newest first, as (path, size, mtime,
    is its stdout or stderr)."""
    out = []
    try:
        files = psutil.Process(pid).open_files()
    except psutil.Error:
        return out
    for f in files:
        if getattr(f, 'mode', 'r') == 'r' or not f.path.startswith('/') or f.path.startswith(('/dev/', '/proc/')):
            continue
        try:
            st = os.stat(f.path)
        except OSError:
            continue
        if not any(f.path == x[0] for x in out):
            out.append((f.path, st.st_size, st.st_mtime, f.fd in (1, 2)))
    return sorted(out, key=lambda x: -x[2])


def flat(s, n=300):
    """A command line on one line (an agent's `python3 -c` can hold a whole script)."""
    s = s.replace('\n', ' ⏎ ')
    return s if len(s) <= n else s[:n] + '…'


def rel(path):
    """A path as it reads best: inside the main copy (through a worktree's links too) relative
    to it, else as is."""
    rp = os.path.realpath(path)
    for p in (rp, os.path.abspath(path)):
        if p.startswith(MAIN + '/') or p.startswith(WORKTREES + '/'):
            return os.path.relpath(p, MAIN)
    return path


def size_text(n):
    for unit in ('B', 'K', 'M', 'G'):
        if n < 1024 or unit == 'G':
            return f'{n:.0f}{unit}' if unit == 'B' else f'{n:.1f}{unit}'
        n /= 1024


# --- the screen ------------------------------------------------------------------------

class Monitor:
    def __init__(self, hours):
        self.hours = hours
        self.runs = {}
        self.suite = Suite()
        self.cpu = deque(maxlen=600)
        self.emus = deque(maxlen=600)
        self.suite_done = deque(maxlen=600)
        self.speed = {}            # run name -> deque of x-realtime
        self.prev = {}             # run name -> (wall, frame)
        self.last_save = 0
        self.focus, self.sel, self.page = 'runs', {}, {}
        self.zoom = self.detail = self.only_running = False   # detail: False, 'run' or 'bench'
        self.detail_off = 0
        self.fight_sel = self.line_off = 0
        self.pinned = None         # the job key, process row or status path a detail view shows
        self.bench_list, self.job_list, self.agent_list, self.agents_at = [], [], [], 0
        try:
            self.bench_seen = json.load(open(BENCHES))
        except (OSError, ValueError):
            self.bench_seen = {}
        self.load_history()
        psutil.cpu_percent(percpu=True)

    def load_history(self):
        cut = time.time() - 6 * 3600
        try:
            for line in open(HIST):
                try:
                    s = json.loads(line)
                except ValueError:
                    continue
                if s.get('t', 0) < cut:
                    continue
                self.cpu.append(s.get('cpu'))
                self.emus.append(s.get('emus'))
                self.suite_done.append(s.get('suite'))
                for k, v in (s.get('speed') or {}).items():
                    self.speed.setdefault(k, deque(maxlen=300)).append(v)
        except OSError:
            pass

    def save(self, sample):
        if time.time() - self.last_save < 10:
            return
        self.last_save = time.time()
        os.makedirs(os.path.dirname(HIST), exist_ok=True)
        with open(HIST, 'a') as f:
            f.write(json.dumps(sample) + '\n')

    def scan(self):
        cut = time.time() - self.hours * 3600
        # os.walk, not glob('**'): the snapshots link rips/harness back into itself
        found = []
        for d, dirs, files in os.walk(H):
            dirs[:] = [x for x in dirs if not x.startswith('snap_') and not os.path.islink(os.path.join(d, x))
                       and x not in ('regress', 'disc', 'states')]
            found += [os.path.join(d, f) for f in files if f.endswith('.pid')]
        for pf in found:
            if pf in self.runs or not os.path.exists(os.path.join(pf[:-4], 'live.jsonl')):
                continue
            try:
                if os.path.getmtime(pf) >= cut:
                    self.runs[pf] = Run(pf)
            except OSError:
                pass

    def tick(self):
        self.scan()
        now = time.time()
        speeds = {}
        for r in self.runs.values():
            r.update()
            st, _ = r.state()
            if st == 'running':
                w0, f0 = self.prev.get(r.name, (now, r.frame))
                if now > w0 and r.frame >= f0:
                    x = (r.frame - f0) / FPS / (now - w0)
                    if now - w0 >= 8:
                        self.speed.setdefault(r.name, deque(maxlen=300)).append(round(x, 2))
                        speeds[r.name] = round(x, 2)
                        self.prev[r.name] = (now, r.frame)
                else:
                    self.prev[r.name] = (now, r.frame)
                self.prev.setdefault(r.name, (now, r.frame))
        lock = self.suite.running()
        self.suite.update(lock)
        cores = psutil.cpu_percent(percpu=True)
        self.cpu_cores = cores
        self.cpu.append(round(sum(cores) / len(cores), 1))
        self.emu_list = emulators()
        self.update_benches(benches())
        self.update_jobs()
        if now - self.agents_at >= 20:          # a walk of the status folders; they change slowly
            self.agent_list, self.agents_at = agent_files(), now
        self.emus.append(len(self.emu_list))
        self.suite_done.append(self.suite.done if lock else None)
        self.lock = lock
        self.save(dict(t=round(now), cpu=self.cpu[-1], emus=self.emus[-1],
                       suite=self.suite_done[-1], speed=speeds))

    def update_benches(self, running):
        now, live = time.time(), set()
        for b in running:
            live.add(b['path'])
            seen = self.bench_seen.setdefault(b['path'], {})
            seen.update(total=b['total'], env=b['env'], since=b['since'], pid=b['pid'], ended=None)
        changed = bool(running)
        for path, b in self.bench_seen.items():
            if path not in live and not b.get('ended'):
                b['ended'], changed = now, True
        cut = now - 72 * 3600
        for path in [p for p, b in self.bench_seen.items() if (b.get('ended') or now) < cut]:
            del self.bench_seen[path]
        if changed:
            try:
                with open(BENCHES + '.new', 'w') as f:
                    json.dump(self.bench_seen, f)
                os.replace(BENCHES + '.new', BENCHES)
            except OSError:
                pass
        cut = now - self.hours * 3600
        out = []
        for path, b in self.bench_seen.items():
            if b.get('ended') and b['ended'] < cut:
                continue
            rows = bench_rows(path)
            file = '/'.join(path.split('/')[-3:])
            out.append(dict(b, path=path, file=file[:-6] if file.endswith('.jsonl') else file, rows=rows,
                            **tally(rows)))
        self.bench_list = sorted(out, key=lambda b: (bool(b.get('ended')), -(b.get('ended') or b['since'])))

    def update_jobs(self):
        cut = time.time() - self.hours * 3600
        js = [j for j in job_groups(job_workers()) if j['end'] is None or j['end'] >= cut]
        self.job_list = sorted(js, key=lambda j: (j['end'] is not None, -(j['end'] or j['start'])))

    # panels
    def header(self):
        mem = psutil.virtual_memory()
        try:
            u = json.load(open(USAGE))
            usage = f"week {u.get('seven_day')}%  5h {u.get('five_hour')}%"
        except (OSError, ValueError):
            usage = 'usage n/a'
        t = Text()
        t.append(' Dimguil bot monitor ', style='bold black on cyan')
        t.append(f"  {time.strftime('%a %H:%M:%S')}   ", style='bold')
        t.append(f'CPU {self.cpu[-1]:5.1f}% ', style='bold')
        t.append(spark(self.cpu, 60, 0, 100), style='green')
        t.append(f'   mem {mem.percent:.0f}%   emulators {self.emus[-1]}   {usage}')
        cores = Text('  cores ')
        for c in self.cpu_cores:
            cores.append(BARS[min(7, int(c / 12.5))], style='red' if c > 85 else 'yellow' if c > 50 else 'green')
        cores.append(f"   emulators over time {spark(self.emus, 60, 0, None)}", style='cyan')
        return Panel(Group(t, cores), box=box.ROUNDED, border_style='cyan')

    # --- view state and keys ---
    PANELS = ['runs', 'suite', 'benches', 'jobs', 'procs', 'agents']

    def visible_runs(self):
        cut = time.time() - self.hours * 3600
        rows = [r for r in self.runs.values() if r.started >= cut]
        if self.only_running:
            rows = [r for r in rows if r.state()[0] == 'running']
        return sorted(rows, key=lambda r: (r.state()[0] != 'running', -r.started))

    def count(self, panel):
        return {'runs': len(self.visible_runs()), 'benches': len(self.bench_list), 'jobs': len(self.job_list),
                'procs': len(self.emu_list), 'agents': len(self.agent_list)}.get(panel, 0)

    def move(self, d):
        n = self.count(self.focus)
        if n:
            self.sel[self.focus] = max(0, min(n - 1, self.sel.get(self.focus, 0) + d))

    def key(self, k):
        """Returns False to quit."""
        page = max(1, self.page.get(self.focus, 5))
        if self.detail == 'bench':
            n = len(self.cur_bench()['rows']) if self.cur_bench() else 0
            if k in ('\x1b', '\r', '\n', 'q', 'LEFT'):
                self.detail = False
            elif k in ('UP', 'k', 'WHEELUP'):
                self.fight_sel -= 1
            elif k in ('DOWN', 'j', 'WHEELDOWN'):
                self.fight_sel += 1
            elif k == 'PGUP':
                self.fight_sel -= max(1, self.page.get('fights', 5))
            elif k == 'PGDN':
                self.fight_sel += max(1, self.page.get('fights', 5))
            elif k in ('HOME', 'g'):
                self.fight_sel = 0
            elif k in ('END', 'G'):
                self.fight_sel = n - 1
            elif k == ']':
                self.line_off += max(1, self.page.get('lines', 10) - 2)
            elif k == '[':
                self.line_off = max(0, self.line_off - max(1, self.page.get('lines', 10) - 2))
            if k not in ('[', ']'):
                self.line_off = 0
            self.fight_sel = max(0, min(n - 1, self.fight_sel))
            return True
        if self.detail:
            if k in ('\x1b', '\r', '\n', 'q', 'LEFT'):
                self.detail = False
            elif k in ('UP', 'k', 'WHEELUP'):
                self.detail_off += 1
            elif k in ('DOWN', 'j', 'WHEELDOWN'):
                self.detail_off = max(0, self.detail_off - 1)
            elif k == 'PGUP':
                self.detail_off += 10
            elif k == 'PGDN':
                self.detail_off = max(0, self.detail_off - 10)
            elif k in ('HOME', 'g'):
                self.detail_off = 10 ** 6       # trimmed to the list by the panel
            elif k in ('END', 'G'):
                self.detail_off = 0
            return True
        if k == 'q':
            return False
        n = len(self.PANELS)
        if k in ('\t', 'RIGHT'):
            self.focus = self.PANELS[(self.PANELS.index(self.focus) + 1) % n]
        elif k in ('BTAB', 'LEFT'):
            self.focus = self.PANELS[(self.PANELS.index(self.focus) - 1) % n]
        elif len(k) == 1 and k in '123456':
            self.focus = self.PANELS[int(k) - 1]
        elif k in ('UP', 'k', 'WHEELUP'):
            self.move(-1)
        elif k in ('DOWN', 'j', 'WHEELDOWN'):
            self.move(1)
        elif k == 'PGUP':
            self.move(-page)
        elif k == 'PGDN':
            self.move(page)
        elif k in ('HOME', 'g'):
            self.sel[self.focus] = 0
        elif k in ('END', 'G'):
            self.move(10 ** 6)
        elif k in ('\r', '\n') and self.focus == 'runs' and self.visible_runs():
            self.detail, self.detail_off = 'run', 0
        elif k in ('\r', '\n') and self.focus == 'benches' and self.bench_list:
            self.detail, self.fight_sel = 'bench', 0
        elif k in ('\r', '\n') and self.focus in ('jobs', 'procs', 'agents') and self.count(self.focus):
            # the item is pinned (by key or pid), so a list that reorders under it can't swap it
            self.detail, self.detail_off = self.focus[:-1], 0
            self.pinned = self.selected(self.focus)
        elif k == 'z':
            self.zoom = not self.zoom
        elif k == '\x1b':
            self.zoom = False
        elif k == 'r':
            self.only_running = not self.only_running
            self.sel['runs'] = 0
        elif k == 'H':
            self.hours = {12: 24, 24: 72, 72: 12}.get(self.hours, 12)
            self.sel['runs'] = 0
        return True

    def frame(self, panel, body, title, color):
        on = panel == self.focus
        n = self.count(panel)
        pos = f'  [{self.sel.get(panel, 0) + 1}/{n}]' if n and panel != 'suite' else ''
        return Panel(body, title=(f'▶ {title}' if on else title) + pos, title_align='left',
                     box=box.HEAVY if on else box.ROUNDED, border_style=f'bold {color}' if on else color)

    @staticmethod
    def window(n, sel, size):
        """The slice [a, b) of n rows to show so that row sel is visible."""
        size = max(1, size)
        a = min(max(0, sel - size // 2), max(0, n - size))
        return a, min(n, a + size)

    def runs_panel(self, height=30):
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for col, kw in (('run', {}), ('state', {}), ('wall', {'justify': 'right'}), ('game', {'justify': 'right'}),
                        ('speed', {}), ('goals done', {'ratio': 2}), ('fights', {'justify': 'right'}),
                        ('boss', {'justify': 'right'}), ('deaths', {'justify': 'right'}),
                        ('temple', {'justify': 'right'}), ('death times', {}), ('levels', {}),
                        ('last events', {'ratio': 4, 'min_width': 44})):
            tb.add_column(col, **kw)
        rows = self.visible_runs()
        per = max(1, (height - 5) // 3)       # a run takes up to three lines
        self.page['runs'] = per
        sel = self.sel['runs'] = min(self.sel.get('runs', 0), max(0, len(rows) - 1))
        a, b = self.window(len(rows), sel, per)
        for i, r in enumerate(rows[a:b], a):
            st, since = r.state()
            color = {'running': 'green', 'done': 'cyan', 'failed': 'red', 'stopped': 'yellow'}[st]
            mark = {'running': '●', 'done': '✓', 'failed': '✗', 'stopped': '■'}[st]
            wall = hms(time.time() - since) if since else hms(os.path.getmtime(r.out.path) - r.started) \
                if os.path.exists(r.out.path) else '-'
            sp = self.speed.get(r.name) or []
            speed = Text(spark(sp, 12, 0, None), style='magenta')
            if st == 'running' and sp:
                speed.append(f' {sp[-1]:.1f}x')
            # the count and the last two; the detail view (Enter) lists them all
            names = [f"{g}{'' if t == 1 else f'×{t}'}" for g, t, _ in r.goals]
            goals = Text(f'{len(names)} done', style='cyan')
            if names:
                goals.append(': ' + ('… ' if len(names) > 2 else '') + ' '.join(names[-2:]))
            if st == 'running' and r.goal_now and (not r.goals or r.goals[-1][0] != r.goal_now):
                goals.append(f' → {r.goal_now}', style='bold yellow')
            bins = [0] * 16
            for f in r.death_frames:
                bins[min(15, int(f / max(r.frame, 1) * 16))] += 1
            dg = Text(spark(bins, 16, 0, max(3, max(bins))) if r.deaths else '', style='red')
            lv = ' '.join(str(l) for _, l in r.levels[:6]) or '-'
            last = '\n'.join(r.recent)
            if st == 'failed' and r.result:
                last = f"{r.result.get('error')} {(r.result.get('info') or {}).get('goal', '')}\n" + last
            tb.add_row(Text(f'{r.chapter}/{r.name}'), Text(f'{mark} {st}', style=color), wall,
                       hms(r.frame / FPS), speed, goals, str(r.fights),
                       f'{r.boss_wins}/{r.boss_fights}' if r.boss_fights else '-',
                       Text(str(r.deaths), style='red' if r.deaths else ''), str(r.temple), dg, lv,
                       Text(last, overflow='ellipsis', no_wrap=True),
                       style='on grey23' if i == sel and self.focus == 'runs' else None)
        if not rows:
            tb.add_row('no runs in the last %g hours' % self.hours, *[''] * 12)
        title = 'chapter runs' + (' (running only)' if self.only_running else '') + f' · last {self.hours:g} h'
        return self.frame('runs', tb, title, 'green')

    def detail_panel(self, height):
        rows = self.visible_runs()
        if not rows:
            self.detail = False
            return Panel('')
        r = rows[min(self.sel['runs'], len(rows) - 1)]
        st, since = r.state()
        out = [Text(f'{r.chapter}/{r.name}   {st}   game {hms(r.frame / FPS)}   pid {r.pid}   '
                    f'fights {r.fights}   deaths {r.deaths}   temple {r.temple}   retries {r.retries}', style='bold')]
        if r.result and r.result.get('error'):
            out.append(Text(f"result: {r.result.get('error')}  {json.dumps(r.result.get('info'))[:150]}",
                            style='red'))
        lv = '  '.join(f'{n} {l}' for n, l in r.levels) or '-'
        out.append(Text(f'party levels: {lv}'))
        gt = Table(box=box.SIMPLE_HEAD, pad_edge=False)
        for c in ('goal', 'tries', 'wall'):
            gt.add_column(c, justify='left' if c == 'goal' else 'right')
        for g, t, secs in r.goals:
            gt.add_row(g, str(t), hms(secs))
        out.append(gt)
        ev = r.events
        size = max(1, height - 12 - len(r.goals))
        self.detail_off = max(0, min(self.detail_off, max(0, len(ev) - size)))
        a = max(0, len(ev) - size - self.detail_off)
        out.append(Text(f'deaths and retries, newest last ({a + 1}-{min(len(ev), a + size)} of {len(ev)}):',
                        style='bold'))
        for f, txt in ev[a:a + size]:
            bad = any(w in txt for w in ('dies', 'stone', 'decapitated', 'ashes', 'lost'))
            out.append(Text(f'  {hms(f / FPS):>8}  {txt}', style='red' if bad else 'yellow',
                            overflow='ellipsis', no_wrap=True))
        if not ev:
            out.append(Text('  none'))
        rel = os.path.relpath(r.dir, ROOT)
        out.append(Text(f'  files: {rel}.out   {rel}/live.jsonl', style='grey50'))
        return Panel(Group(*out), title=f'▶ run detail · {r.chapter}/{r.name}', title_align='left',
                     box=box.HEAVY, border_style='bold green')

    def suite_panel(self):
        hist = self.suite.history()
        walls = [r.get('wall') for r in hist if not r.get('partial')]
        lines = []
        if self.lock:
            total = next((r['cases'] for r in reversed(hist) if not r.get('partial')), 344)
            start = time.mktime(time.strptime(self.lock[1][:19], '%Y-%m-%dT%H:%M:%S'))
            el = time.time() - start
            done = self.suite.done
            eta = (el / done * (total - done)) if done else (statistics.median(walls[-5:]) - el if walls else 0)
            t = Text(' running ', style='bold black on green')
            t.append(f'  {done}/{total}  ')
            t.append_text(bar(done / total if total else 0, 40))
            t.append(f'  ok {self.suite.ok}  ', style='green')
            t.append(f'failed {len(self.suite.failed)}', style='red' if self.suite.failed else '')
            t.append(f'   elapsed {hms(el)}   eta {hms(eta)}')
            lines.append(t)
            prog = [v for v in self.suite_done if v is not None]
            rate = [b - a for a, b in zip(prog, prog[1:])][-60:]
            lines.append(Text(f'  cases per tick {spark(rate, 60, 0, None)}', style='cyan'))
            if self.suite.failed:
                lines.append(Text('  failed: ' + ', '.join(self.suite.failed[-6:]), style='red'))
        else:
            lines.append(Text(' idle ', style='bold black on grey50'))
        if hist:
            marks = Text('  last rounds ')
            for r in hist:
                good = r.get('passed') == r.get('cases') and r.get('valid', True)
                marks.append('✓' if good else '✗', style='green' if good else 'red')
            marks.append(f"   wall {spark(walls, 20, 0, None)}  median {hms(statistics.median(walls[-5:]))}"
                         if walls else '')
            lines.append(marks)
            r = hist[-1]
            lines.append(Text(f"  latest {r['date'][5:16]}  {r.get('passed')}/{r.get('cases')}"
                              f"{'  partial' if r.get('partial') else ''}  {(r.get('note') or '')[:90]}",
                              style='grey70'))
        return self.frame('suite', Group(*lines), 'suite round', 'yellow')

    def bench_panel(self, height=12):
        bs = self.bench_list
        self.page['benches'] = max(1, height - 5)
        sel = self.sel['benches'] = min(self.sel.get('benches', 0), max(0, len(bs) - 1))
        a, b = self.window(len(bs), sel, height - 5)
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for c, kw in (('bench output', {'ratio': 3, 'no_wrap': True, 'overflow': 'ellipsis'}),
                      ('settings', {'ratio': 2, 'no_wrap': True, 'overflow': 'ellipsis'}), ('progress', {'no_wrap': True}),
                      ('won', {}), ('wiped', {}), ('deaths/fight', {}), ('time', {'no_wrap': True})):
            tb.add_column(c, **kw)
        for i, b in enumerate(bs[a:b], a):
            prog = Text(f"{b['n']}/{b['total']} ")
            prog.append_text(bar(b['n'] / b['total'] if b['total'] else 0, 12, 'magenta' if not b.get('ended')
                                 else 'grey50'))
            when = (Text(f"done {ago(b['ended'])}", style='grey50') if b.get('ended')
                    else Text(hms(time.time() - b['since']), style='magenta'))
            tb.add_row(b['file'], b['env'] or '-', prog, f"{b['won']}/{b['n']}", str(b['wiped']),
                       f"{b['dead'] / b['n']:.2f}" if b['n'] else '-', when,
                       style='on grey23' if i == sel and self.focus == 'benches' else None)
        if not bs:
            tb.add_row(f'no benches in the last {self.hours:g} hours', '', '', '', '', '', '')
        return self.frame('benches', tb, f'fight benches · last {self.hours:g} h', 'magenta')

    def cur_bench(self):
        bs = self.bench_list
        return bs[min(self.sel.get('benches', 0), len(bs) - 1)] if bs else None

    def bench_detail_panel(self, height):
        b = self.cur_bench()
        if not b:
            self.detail = False
            return Panel('')
        rows, t = b['rows'], tally(b['rows'])
        n = t['n'] or 1
        state = f"done {ago(b['ended'])}" if b.get('ended') else f"running {hms(time.time() - b['since'])}"
        out = [Text(f"{b['file']}   {state}   settings {b['env'] or '-'}   fights {t['n']}/{b['total']}   "
                    f"won {t['won']}   wiped {t['wiped']}   fled {t['fled']}   other {t['lost']}   "
                    f"deaths/fight {t['dead'] / n:.2f}   rounds/fight {t['rounds'] / n:.1f}", style='bold')]

        # by state
        by = {}
        for r in rows:
            by.setdefault(r.get('state', '?'), []).append(r)
        st = Table(box=box.SIMPLE_HEAD, pad_edge=False, expand=True)
        for c in ('fight state', 'fights', 'won', 'wiped', 'fled', 'deaths/fight', 'rounds', 'hp lost', 'casts'):
            st.add_column(c, justify='left' if c in ('fight state', 'casts') else 'right',
                          ratio=2 if c == 'casts' else None, no_wrap=True, overflow='ellipsis')
        for name, rs in sorted(by.items()):
            s_ = tally(rs)
            k = s_['n'] or 1
            st.add_row(name, str(s_['n']), str(s_['won']), str(s_['wiped']), str(s_['fled']),
                       f"{s_['dead'] / k:.2f}", f"{s_['rounds'] / k:.1f}", f"{s_['hp'] / k:.0f}",
                       counted(c[1] for r in rs for c in (r.get('casts') or []) if len(c) > 1))
        out.append(st)

        # the fight list
        left = height - 4 - len(by) - 4
        list_h = max(3, min(len(rows), left // 2 - 2))
        self.page['fights'] = list_h
        self.fight_sel = max(0, min(len(rows) - 1, self.fight_sel))
        a, z = self.window(len(rows), self.fight_sel, list_h)
        ft = Table(box=box.SIMPLE_HEAD, pad_edge=False, expand=True)
        for c in ('#', 'fight state', 'seed', 'result', 'rounds', 'dead', 'down', 'hp lost', 'why', 'casts'):
            ft.add_column(c, justify='right' if c in ('#', 'rounds', 'dead', 'down', 'hp lost') else 'left',
                          ratio=2 if c == 'casts' else None, no_wrap=True, overflow='ellipsis')
        color = dict(won='green', wiped='red', fled='yellow', lost='magenta')
        for i, r in enumerate(rows[a:z], a):
            o = outcome(r)
            ft.add_row(str(i + 1), str(r.get('state', '?')), str(r.get('seed', '')), Text(o, style=color[o]),
                       str(r.get('rounds', '')), str(dead(r)), str(r.get('down', '')),
                       str(r.get('hp_lost', '')), str(r.get('why') or ''),
                       counted(c[1] for c in (r.get('casts') or []) if len(c) > 1),
                       style='on grey23' if i == self.fight_sel else None)
        out.append(Text(f'fights ({a + 1}-{z} of {len(rows)}), ↑↓ to select:', style='bold'))
        out.append(ft if rows else Text('  none yet'))

        # the selected fight
        if rows:
            r = rows[self.fight_sel]
            o = outcome(r)
            out.append(Text(f"fight {self.fight_sel + 1}: {r.get('state')} seed {r.get('seed')}   {o}   "
                            f"rounds {r.get('rounds') or sum(x.get('rounds') or 0 for x in chain(r) or []) or '-'}   policy {r.get('policy') or '-'}   "
                            f"spell levels spent {r.get('spent_lv') or '-'}", style='bold ' + color[o]))
            lines = []
            for k, x in enumerate(chain(r) or [], 1):
                xo = 'won' if x.get('won') else 'wiped' if x.get('wiped') else 'lost'
                lines.append((f"  fight {k}   enc {x.get('enc')} at {x.get('where')}   {xo}   rounds "
                              f"{x.get('rounds')}   deaths {dead(x)}   spell levels {x.get('spent_lv') or '-'}",
                              color[xo]))
                for d in x.get('deaths') or []:
                    lines.append((f'    died    {death_text(d)}', 'red'))
                if x.get('drained'):
                    lines.append(('    drained ' + ', '.join(map(str, x['drained'])), 'red'))
                if x.get('casts'):
                    lines.append(('    casts   ' + ', '.join(f'{c[0]} {c[1]}' if isinstance(c, (list, tuple))
                                                           and len(c) > 1 else str(c) for c in x['casts']), 'cyan'))
            if chain(r) is not None and r.get('error'):
                lines.append((f"  error     {r['error']}", 'red'))
            for d in r.get('deaths') or []:
                lines.append((f'  died      {death_text(d)}', 'red'))
            for run in r.get('runs') or []:
                lines.append((f"  ran       round {run[0]}, {run[1]}% chance, {run[2] if len(run) > 2 else ''}",
                              'yellow'))
            if r.get('fled'):
                lines.append((f"  run tries {r['fled'][0]} got away, {r['fled'][1]} failed", 'yellow'))
            if r.get('casts'):
                lines.append(('  casts     ' + ', '.join(f'{c[0]} {c[1]}' for c in r['casts']), 'cyan'))
            if r.get('items'):
                lines.append(('  items     ' + ', '.join(map(str, r['items'])), 'cyan'))
            sup = [p for p in r.get('support') or [] if isinstance(p, dict)]
            for p in sup:
                if p.get('stacks') or p.get('dropped'):
                    lines.append((f"  support   round {p.get('r')}: stacks {p.get('stacks') or '-'}"
                                  f"{', dropped ' + str(p['dropped']) if p.get('dropped') else ''}", 'grey70'))
            if sup and not any(p.get('stacks') or p.get('dropped') for p in sup):
                lines.append((f"  support   planned rounds {', '.join(str(p.get('r')) for p in sup)}, no stacks",
                              'grey70'))
            for line in r.get('text') or []:
                lines.append(('  text      ' + str(line), 'white'))
            if not r.get('text'):
                lines.append(('  (battle text only recorded with TEXT=1)', 'grey50'))
            room = max(1, height - 4 - (len(by) + 4) - (list_h + 4) - 3)
            self.page['lines'] = room
            self.line_off = max(0, min(self.line_off, len(lines) - room))
            for txt, style in lines[self.line_off:self.line_off + room]:
                out.append(Text(txt, style=style, no_wrap=True, overflow='ellipsis'))
            if len(lines) > room:
                out.append(Text(f'  lines {self.line_off + 1}-{min(len(lines), self.line_off + room)} of '
                                f'{len(lines)}; [ and ] scroll', style='grey50'))
        out.append(Text(f"  file: {os.path.relpath(b['path'], ROOT)}", style='grey50'))
        return Panel(Group(*out), title=f"▶ bench detail · {b['file']}", title_align='left',
                     box=box.HEAVY, border_style='bold magenta')

    def proc_rows(self):
        return sorted(self.emu_list, key=lambda x: (x[1], x[0]))

    def selected(self, panel):
        """What's selected in a panel, as a key that survives the list changing."""
        i = self.sel.get(panel, 0)
        if panel == 'jobs' and self.job_list:
            j = self.job_list[min(i, len(self.job_list) - 1)]
            return (j['name'], j['run'], j['start'])
        if panel == 'procs' and self.emu_list:
            ps = self.proc_rows()
            return ps[min(i, len(ps) - 1)]
        if panel == 'agents' and self.agent_list:
            return self.agent_list[min(i, len(self.agent_list) - 1)]['path']
        return None

    def jobs_panel(self, height=12):
        js = self.job_list
        per = max(1, (height - 5) // 2)       # a job takes two lines
        self.page['jobs'] = per
        sel = self.sel['jobs'] = min(self.sel.get('jobs', 0), max(0, len(js) - 1))
        a, b = self.window(len(js), sel, per)
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        # two lines a job: name over purpose, done/total over rate and eta, state over age
        for c, kw in (('job', {'ratio': 3}), ('progress', {'no_wrap': True}), ('tally', {'ratio': 4}),
                      ('state', {'no_wrap': True})):
            tb.add_column(c, overflow='ellipsis', **kw)
        for i, j in enumerate(js[a:b], a):
            name = Text(j['name'], style='bold')
            name.append('\n' + (j['purpose'] or ' '), style='grey62')
            name.no_wrap, name.overflow = True, 'ellipsis'
            keys = j['keys']
            half = (len(keys) + 1) // 2
            tl = Text(tally_text(dict(j, keys=keys[:half])) + '\n' + tally_text(dict(j, keys=keys[half:])),
                      no_wrap=True, overflow='ellipsis')
            running = j['end'] is None
            prog = Text(f"{j['done']}/{j['total'] or '?'} ")
            prog.append_text(bar(j['done'] / j['total'] if j['total'] else 0, 12, 'green' if running else 'grey50'))
            prog.append(f"\n{rate_text(j['rate'])}" + (f"  eta {hms(j['eta'])}" if j['eta'] else ''), style='grey62')
            n = len(j['workers'])
            alive = sum(w['state'] in ('running', 'stale') for w in j['workers'])
            st = Text(f"{JOB_MARK[j['state']]} {j['state']}", style=JOB_COLOR[j['state']])
            if n > 1:
                st.append(f' {alive}/{n}' if running else f' ×{n}', style='grey62')
            st.append(f"\nup {hms(time.time() - j['start'])}" if running else f"\ndone {ago(j['end'])}",
                      style='grey62')
            tb.add_row(name, prog, tl, st, style='on grey23' if i == sel and self.focus == 'jobs' else None)
        if not js:
            tb.add_row(f'no jobs in the last {self.hours:g} hours (scripts/jobstatus.py)', '', '', '')
        return self.frame('jobs', tb, f'jobs · last {self.hours:g} h', 'green')

    def scrolled(self, lines, room):
        """The `room` lines to show of a list scrolled by detail_off from its end."""
        self.detail_off = max(0, min(self.detail_off, max(0, len(lines) - room)))
        a = max(0, len(lines) - room - self.detail_off)
        return a, lines[a:a + room]

    def job_detail_panel(self, height):
        j = next((x for x in self.job_list if (x['name'], x['run'], x['start']) == self.pinned), None)
        if not j:
            self.detail = False
            return Panel('')
        now = time.time()
        running = j['end'] is None
        out = []
        t = Text(f"{j['name']}", style='bold')
        t.append(f"   {JOB_MARK[j['state']]} {j['state']}", style=JOB_COLOR[j['state']])
        t.append(f"   started {time.strftime('%H:%M', time.localtime(j['start']))}, "
                 + (f"running {hms(now - j['start'])}" if running else
                    f"took {hms(j['end'] - j['start'])}, done {ago(j['end'])}"))
        if j['run']:
            t.append(f"   run {j['run']}", style='grey62')
        out.append(t)
        if j['purpose']:
            out.append(Text(j['purpose'], style='grey70'))
        p = Text(f"  {j['done']}/{j['total'] or '?'}  ")
        p.append_text(bar(j['done'] / j['total'] if j['total'] else 0, 40, 'green' if running else 'grey50'))
        p.append(f"   {rate_text(j['rate'])}   eta {hms(j['eta']) if j['eta'] else '-'}   "
                 f"last update {ago(j['updated'])}")
        out.append(p)
        for s in j['summary']:
            out.append(Text(f'  summary: {s}', style='cyan'))

        # the workers, and the done/total per arm
        ws = j['workers']
        wt = Table(box=box.SIMPLE_HEAD, pad_edge=False, expand=True)
        for c in ('worker', 'pid', 'state', 'done', 'now doing', 'since', 'updated'):
            wt.add_column(c, no_wrap=True, overflow='ellipsis', ratio=3 if c == 'now doing' else None)
        for w in ws:
            stp = w.get('step') or (w.get('summary') or '' if w['state'] == 'finished' else '')
            wt.add_row(w.get('part') or w['name'], str(w.get('pid')),
                       Text(f"{JOB_MARK[w['state']]} {w['state']}", style=JOB_COLOR[w['state']]),
                       f"{w.get('done') or 0}/{w.get('total') or '?'}", str(stp),
                       hms(now - w['step_since']) if w.get('step_since') and w.get('step') else '',
                       ago(w['updated']) if w.get('updated') else '')
        out.append(wt)
        if j['arms']:
            arm = Text('  by arm  ')
            for k, (d, tot) in sorted(j['arms'].items()):
                arm.append(f'{k} ', style='bold')
                arm.append(f'{d}/{tot or "?"}   ', style='green' if tot and d >= tot else '')
            out.append(arm)

        # the full tally, as rows of key value
        if j['tally']:
            keys = j['keys'] + [k for k in j['tally'] if k not in j['keys']]
            tt = Text('  tally   ')
            for k in keys:
                tt.append(f'{k} ', style='grey70')
                tt.append(f"{j['tally'].get(k, 0):g}", style='bold')
                tt.append('    ')
            out.append(tt)

        # files
        tail = []
        for path in j['outputs']:
            try:
                st = os.stat(path)
                tail.append(Text(f'  output  {rel(path)}   {size_text(st.st_size)}, '
                                 f'changed {ago(st.st_mtime)}', style='grey62', overflow='ellipsis', no_wrap=True))
            except OSError:
                tail.append(Text(f'  output  {rel(path)}   (not written yet)', style='grey50',
                                 overflow='ellipsis', no_wrap=True))
        if j['status']:
            i = status_info(j['status'])
            tail.append(Text(f"  status  {rel(j['status'])}"
                             + (f"   {i['report']}   changed {ago(i['mtime'])}" if i else '   (missing)'),
                             style='grey62', overflow='ellipsis', no_wrap=True))
        who = '   '.join(x for x in (f"agent {j['agent']}" if j['agent'] else '',
                                     f"worktree {j['worktree']}" if j['worktree'] else '') if x)
        if who:
            tail.append(Text(f'  {who}', style='grey50', overflow='ellipsis', no_wrap=True))
        tail.append(Text('  job files: ' + ', '.join(os.path.basename(w['file']) for w in ws), style='grey50',
                         overflow='ellipsis', no_wrap=True))

        # the recent events, newest last, scrollable
        ev = j['events']
        room = max(1, height - 2 - len(out) - len(ws) - 4 - 2 - len(tail))
        a, shown = self.scrolled(ev, room)
        out.append(Text(f'events, newest last ({a + 1}-{a + len(shown)} of {len(ev)}; '
                        f'each worker keeps its last {jobstatus.EVENTS}):' if ev else 'events: none yet', style='bold'))
        for ts, tag, txt in shown:
            line = Text(f"  {time.strftime('%H:%M:%S', time.localtime(ts))}  ", style='grey62')
            if tag:
                line.append(f'[{tag}] ', style='magenta')
            line.append(txt)
            line.no_wrap, line.overflow = True, 'ellipsis'
            out.append(line)
        out += tail
        return Panel(Group(*out), title=f"▶ job detail · {j['name']}", title_align='left',
                     box=box.HEAVY, border_style='bold green')

    def proc_detail_panel(self, height):
        pid, kind, cpu, rss, ct, short, cwd, cmdline = self.pinned
        now = time.time()
        live = next((x for x in self.emu_list if x[0] == pid), None)
        if live:
            pid, kind, cpu, rss, ct, short, cwd, cmdline = live
        out = [Text(f"pid {pid}   {kind}   " + (f"running {hms(now - ct)}   cpu {cpu:.0f}%   mem {rss / 2**20:.0f}M"
                                                 if live else 'ended'), style='bold' if live else 'bold red')]
        out.append(Text('  ' + flat(' '.join(cmdline), 600), style='grey70', overflow='fold'))
        parent = []
        try:
            pp = psutil.Process(pid).parent()
            parent = pp.cmdline() if pp else []
            if parent:
                out.append(Text(f'  parent {pp.pid}: ' + flat(' '.join(parent)), style='grey50', no_wrap=True,
                                overflow='ellipsis'))
        except psutil.Error:
            pass
        root, branch = worktree_of(cwd)
        out.append(Text(f'  cwd {cwd}', overflow='ellipsis', no_wrap=True))
        if root:
            out.append(Text(f"  {'main copy' if root == MAIN else 'worktree'} {root}" +
                            (f'   branch {branch}' if branch else ''), overflow='ellipsis', no_wrap=True))

        # a job file, if it writes one
        mine = [j for j in self.job_list if any(w.get('pid') == pid for w in j['workers'])]
        for j in mine:
            out.append(Text(f"  job {j['name']}: {j['done']}/{j['total'] or '?'}, {tally_text(j, 6)}"
                            f"   (Enter on it in the jobs panel)", style='green', overflow='ellipsis', no_wrap=True))

        # the agent's status file
        sts = status_for(cwd, [cmdline, parent], root)
        if sts:
            i = status_info(sts[0])
            out.append(Text(f'status file {rel(sts[0])}   changed {ago(i["mtime"])}',
                            style='bold', overflow='ellipsis', no_wrap=True))
            out.append(Text(f"  task    {i['task']}", overflow='ellipsis', no_wrap=True))
            out.append(Text(f"  latest  {i['report'] or '-'}", overflow='ellipsis', no_wrap=True))
            if len(sts) > 1:
                out.append(Text('  also    ' + ', '.join(rel(p) for p in sts[1:4]),
                                style='grey50', overflow='ellipsis', no_wrap=True))
        else:
            out.append(Text('status file: none found (rips/agents/*/STATUS.md, rips/harness/*/STATUS.md, '
                            'or one in the worktree)', style='grey50'))

        # files open for writing, and the end of the newest text one
        wf = write_files(pid) if live else []
        out.append(Text(f'open for writing ({len(wf)}):' if wf else
                        'open for writing: none' + ('' if live else ' (process ended)'), style='bold'))
        for path, size, mt, std in wf[:6]:
            out.append(Text(f'  {rel(path)}   '
                            f"{size_text(size)}, changed {ago(mt)}{'   (its output)' if std else ''}",
                            style='grey70', overflow='ellipsis', no_wrap=True))
        # the end of the newest text file it writes, and of its output (stdout) if that's another
        texts = [x for x in wf if 0 < x[1] < 1 << 30 and is_text(x[0])]
        show = texts[:1] + [x for x in texts[1:] if x[3]][:1]
        room = max(2, height - 2 - len(out) - 2 * len(show))
        for k, (path, *_rest) in enumerate(show):
            lines = tail_lines(path, 200)
            n = max(1, min(len(lines), room // len(show) if k == 0 else room - room // len(show)))
            if k == 0:                  # the newest one scrolls
                a, shown = self.scrolled(lines, n)
            else:
                a, shown = max(0, len(lines) - n), lines[-n:]
            out.append(Text(f'{os.path.basename(path)}, lines {a + 1}-{a + len(shown)} of the last {len(lines)}:',
                            style='bold'))
            for line in shown:
                out.append(Text('  ' + line, no_wrap=True, overflow='ellipsis'))
        return Panel(Group(*out), title=f'▶ process detail · {pid}', title_align='left',
                     box=box.HEAVY, border_style='bold blue')

    def agents_panel(self, height=12):
        ag = self.agent_list
        self.page['agents'] = max(1, height - 5)
        sel = self.sel['agents'] = min(self.sel.get('agents', 0), max(0, len(ag) - 1))
        a, b = self.window(len(ag), sel, height - 5)
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for c, kw in (('status file', {'ratio': 2}), ('task', {'ratio': 4}), ('latest', {'ratio': 3}),
                      ('changed', {'min_width': 8})):
            tb.add_column(c, no_wrap=True, overflow='ellipsis', **kw)
        for i, x in enumerate(ag[a:b], a):
            fresh = time.time() - x['mtime'] < 3600
            tb.add_row(Text(x['name'], style='bold' if fresh else ''), x['task'], x['report'],
                       Text(hms(time.time() - x['mtime']), style='cyan' if fresh else 'grey50'),
                       style='on grey23' if i == sel and self.focus == 'agents' else None)
        if not ag:
            tb.add_row('no status file changed in the last 24 hours', '', '', '')
        return self.frame('agents', tb, 'agent status files · last 24 h', 'cyan')

    def agent_detail_panel(self, height):
        path = self.pinned
        i = status_info(path)
        if not i:
            self.detail = False
            return Panel('')
        lines = tail_lines(path, 400, 1 << 18)
        room = max(1, height - 4)
        a, shown = self.scrolled(lines, room)
        out = [Text(f"{rel(path)}   changed {ago(i['mtime'])}   "
                    f"lines {a + 1}-{a + len(shown)} of the last {len(lines)}", style='bold')]
        for line in shown:
            st = 'bold cyan' if line.startswith('#') else None
            out.append(Text(line, style=st, no_wrap=True, overflow='ellipsis'))
        return Panel(Group(*out), title=f"▶ status file · {status_name(path)}", title_align='left',
                     box=box.HEAVY, border_style='bold cyan')

    def proc_panel(self, height=12):
        ps = self.proc_rows()
        self.page['procs'] = max(1, height - 5)
        sel = self.sel['procs'] = min(self.sel.get('procs', 0), max(0, len(ps) - 1))
        a, b = self.window(len(ps), sel, height - 5)
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for c, kw in (('pid', {'min_width': 7}), ('kind', {'min_width': 7}), ('cpu', {'min_width': 5}),
                      ('mem', {'min_width': 5}), ('up', {'min_width': 7}), ('command', {'ratio': 1})):
            tb.add_column(c, no_wrap=True, **kw)
        for i, (pid, kind, cpu, rss, ct, cl, _, _) in enumerate(ps[a:b], a):
            tb.add_row(str(pid), kind, f'{cpu:.0f}%', f'{rss / 2**20:.0f}M', hms(time.time() - ct),
                       Text(flat(cl), overflow='ellipsis'), style='on grey23' if i == sel and self.focus == 'procs' else None)
        return self.frame('procs', tb, 'processes', 'blue')

    def footer(self):
        t = Text(' ')
        keys = ([('Esc/Enter', 'back'), ('↑↓ j/k wheel', 'select fight'), ('PgUp/PgDn g/G', 'page'),
                 ('[ ]', 'scroll fight')]
                if self.detail == 'bench' else
                [('Esc/Enter', 'back'), ('↑↓ wheel PgUp/PgDn g/G', 'scroll ' + {
                    'run': 'events', 'job': 'events', 'proc': 'file', 'agent': 'file'}.get(self.detail, ''))]
                if self.detail else
                [('Tab/1-6/click', 'panel'), ('↑↓ j/k wheel', 'select'), ('PgUp/PgDn g/G', 'page'),
                 ('Enter', 'detail'), ('z', 'zoom'), ('r', 'running only'), ('H', 'hours'), ('q', 'quit')])
        for k, what in keys:
            t.append(f' {k} ', style='bold black on cyan')
            t.append(f' {what}  ')
        return t

    def render(self, size=(200, 50)):
        w, h = size
        lay = Layout()
        body = max(10, h - 4 - 1)
        if self.detail:
            p = {'bench': self.bench_detail_panel, 'run': self.detail_panel, 'job': self.job_detail_panel,
                 'proc': self.proc_detail_panel, 'agent': self.agent_detail_panel}[self.detail](body)
            if not self.detail:         # the item went away
                return self.render(size)
            lay.split_column(Layout(self.header(), size=4), Layout(p, size=body),
                             Layout(self.footer(), size=1))
            return lay
        if self.zoom:
            p = {'runs': lambda: self.runs_panel(body), 'suite': self.suite_panel,
                 'benches': lambda: self.bench_panel(body), 'jobs': lambda: self.jobs_panel(body),
                 'procs': lambda: self.proc_panel(body), 'agents': lambda: self.agents_panel(body)}[self.focus]()
            lay.split_column(Layout(self.header(), size=4), Layout(p, size=body), Layout(self.footer(), size=1))
            return lay
        suite_h = 8
        rest = max(12, body - suite_h)
        # the runs panel takes what its runs need (three lines each), at most half the rest;
        # below it two rows: benches and jobs, then processes and agents
        runs_h = max(7, min(rest // 2, 5 + 3 * len(self.visible_runs())))
        mid_h = max(5, (rest - runs_h) // 2)
        low_h = max(5, rest - runs_h - mid_h)
        self.regions = (4, 4 + runs_h, 4 + runs_h + suite_h, 4 + runs_h + suite_h + mid_h, w // 2)
        lay.split_column(Layout(self.header(), size=4), Layout(self.runs_panel(runs_h), size=runs_h),
                         Layout(self.suite_panel(), size=suite_h), Layout(name='mid', size=mid_h),
                         Layout(name='low', size=low_h), Layout(self.footer(), size=1))
        lay['mid'].split_row(Layout(self.bench_panel(mid_h)), Layout(self.jobs_panel(mid_h)))
        lay['low'].split_row(Layout(self.proc_panel(low_h)), Layout(self.agents_panel(low_h)))
        return lay

    def click(self, x, y):
        if self.detail or self.zoom or not hasattr(self, 'regions'):
            return
        top, runs_end, suite_end, mid_end, half = self.regions
        if y > top:
            self.focus = ('runs' if y <= runs_end else 'suite' if y <= suite_end else
                          ('benches' if x <= half else 'jobs') if y <= mid_end else
                          'procs' if x <= half else 'agents')


KEYS = [('\x1b[A', 'UP'), ('\x1b[B', 'DOWN'), ('\x1b[C', 'RIGHT'), ('\x1b[D', 'LEFT'), ('\x1b[5~', 'PGUP'),
        ('\x1b[6~', 'PGDN'), ('\x1b[H', 'HOME'), ('\x1b[1~', 'HOME'), ('\x1b[F', 'END'), ('\x1b[4~', 'END'),
        ('\x1b[Z', 'BTAB'), ('\x1bOA', 'UP'), ('\x1bOB', 'DOWN'), ('\x1bOH', 'HOME'), ('\x1bOF', 'END')]
MOUSE = re.compile(r'\x1b\[<(\d+);(\d+);(\d+)([mM])')


def parse_keys(data):
    out, i = [], 0
    while i < len(data):
        m = MOUSE.match(data, i)
        if m:
            btn = int(m.group(1))
            if m.group(4) == 'M' and btn in (64, 65):
                out.append('WHEELUP' if btn == 64 else 'WHEELDOWN')
            elif m.group(4) == 'M' and btn == 0:
                out.append(('CLICK', int(m.group(2)), int(m.group(3))))
            i = m.end()
            continue
        for seq, name in KEYS:
            if data.startswith(seq, i):
                out.append(name)
                i += len(seq)
                break
        else:
            if data[i] == '\x1b' and i + 1 < len(data) and data[i + 1] in '[O':
                j = i + 2
                while j < len(data) and not data[j].isalpha() and data[j] != '~':
                    j += 1
                i = j + 1          # an escape sequence we don't use
            else:
                out.append(data[i])
                i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--hours', type=float, default=12)
    ap.add_argument('--every', type=float, default=2.0)
    a = ap.parse_args()
    m = Monitor(a.hours)
    m.tick()
    if a.once:
        time.sleep(1)
        m.tick()
        Console(width=200, height=50).print(m.render((200, 50)), height=50)
        return
    import select, sys, termios, tty
    con = Console()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write('\x1b[?1000h\x1b[?1006h')      # mouse clicks and wheel, SGR format
        sys.stdout.flush()
        with Live(m.render(con.size), screen=True, auto_refresh=False, console=con) as live:
            next_tick = time.time() + a.every
            while True:
                r, _, _ = select.select([fd], [], [], max(0.05, next_tick - time.time()))
                redraw = False
                if r:
                    data = os.read(fd, 1024).decode('utf-8', 'replace')
                    for k in parse_keys(data):
                        if isinstance(k, tuple):
                            m.click(k[1], k[2])
                        elif not m.key(k):
                            return
                    redraw = True
                if time.time() >= next_tick:
                    m.tick()
                    next_tick = time.time() + a.every
                    redraw = True
                if redraw:
                    live.update(m.render(con.size), refresh=True)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\x1b[?1006l\x1b[?1000l')
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == '__main__':
    main()
