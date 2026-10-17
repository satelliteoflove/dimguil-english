#!/usr/bin/env python3
"""A live terminal monitor for bot chapter runs, suite rounds and fight benches.

    python3 scripts/monitor.py              # full screen, refreshes every 2 s; Ctrl+C quits
    python3 scripts/monitor.py --once       # print one frame and exit
    python3 scripts/monitor.py --hours 24   # list runs started in the last 24 hours (default 12)

Reads only what the harness already writes, so nothing has to be started differently:
  chapter runs   rips/harness/**/NAME.pid, NAME.out (goal lines) and NAME/live.jsonl (events)
  suite rounds   rips/harness/regress/LOCK, results-*.jsonl, rounds.jsonl
  benches        running fightbench.py processes and the .jsonl they write
Samples (CPU, emulators running, suite progress, each run's frames) go to
rips/monitor/history.jsonl every 10 s, so the graphs keep their history across restarts.
"""
import argparse, glob, json, os, re, statistics, time
from collections import deque
import psutil
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


def benches():
    out = []
    for p in psutil.process_iter(['pid', 'cmdline', 'cwd', 'create_time']):
        cl = p.info['cmdline'] or []
        if len(cl) > 4 and any(c.endswith('fightbench.py') for c in cl) and 'run' in cl:
            i = cl.index('run')
            path, seeds, states = cl[i + 1], cl[i + 2], cl[i + 3:]
            path = path if os.path.isabs(path) else os.path.join(p.info['cwd'] or ROOT, path)
            a, _, b = seeds.partition('-')
            try:
                total = (int(b or a) - int(a) + 1) * max(1, len(states))
            except ValueError:
                total = 0
            won = dead = n = 0
            try:
                for line in open(path):
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    n += 1
                    won += bool(r.get('won'))
                    dead += r.get('dead') or 0
            except OSError:
                pass
            env = ''
            try:
                env = p.environ().get('SET', '')
            except psutil.Error:
                pass
            out.append(dict(file='/'.join(path.split('/')[-3:]), n=n, total=total, won=won, dead=dead,
                            since=p.info['create_time'], env=env))
    return out


PROCS = {}


def emulators():
    out = []
    for p in psutil.process_iter(['pid', 'cmdline', 'create_time', 'memory_info']):
        cl = ' '.join(p.info['cmdline'] or [])
        if 'python' not in cl or 'monitor.py' in cl:
            continue
        kind = ('chapter' if 'run_chapter' in cl else 'suite' if 'regress.py' in cl or 'spawn_main' in cl
                else 'bench' if 'fightbench' in cl else None)
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
                    p.info['create_time'], short))
    return out


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
        self.zoom = self.detail = self.only_running = False
        self.detail_off = 0
        self.bench_list = []
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
        self.bench_list = benches()
        self.emus.append(len(self.emu_list))
        self.suite_done.append(self.suite.done if lock else None)
        self.lock = lock
        self.save(dict(t=round(now), cpu=self.cpu[-1], emus=self.emus[-1],
                       suite=self.suite_done[-1], speed=speeds))

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
    PANELS = ['runs', 'suite', 'benches', 'procs']

    def visible_runs(self):
        cut = time.time() - self.hours * 3600
        rows = [r for r in self.runs.values() if r.started >= cut]
        if self.only_running:
            rows = [r for r in rows if r.state()[0] == 'running']
        return sorted(rows, key=lambda r: (r.state()[0] != 'running', -r.started))

    def count(self, panel):
        return {'runs': len(self.visible_runs()), 'benches': len(self.bench_list),
                'procs': len(self.emu_list)}.get(panel, 0)

    def move(self, d):
        n = self.count(self.focus)
        if n:
            self.sel[self.focus] = max(0, min(n - 1, self.sel.get(self.focus, 0) + d))

    def key(self, k):
        """Returns False to quit."""
        page = max(1, self.page.get(self.focus, 5))
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
            return True
        if k == 'q':
            return False
        if k in ('\t', 'RIGHT'):
            self.focus = self.PANELS[(self.PANELS.index(self.focus) + 1) % 4]
        elif k in ('BTAB', 'LEFT'):
            self.focus = self.PANELS[(self.PANELS.index(self.focus) - 1) % 4]
        elif len(k) == 1 and k in '1234':
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
            self.detail, self.detail_off = True, 0
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
        for c, kw in (('bench output', {'ratio': 3}), ('settings', {'ratio': 2}), ('progress', {'no_wrap': True}),
                      ('won', {}), ('deaths/fight', {}), ('running', {})):
            tb.add_column(c, **kw)
        for i, b in enumerate(bs[a:b], a):
            prog = Text(f"{b['n']}/{b['total']} ")
            prog.append_text(bar(b['n'] / b['total'] if b['total'] else 0, 12, 'magenta'))
            tb.add_row(b['file'], b['env'] or '-', prog, f"{b['won']}/{b['n']}",
                       f"{b['dead'] / b['n']:.2f}" if b['n'] else '-', hms(time.time() - b['since']),
                       style='on grey23' if i == sel and self.focus == 'benches' else None)
        if not bs:
            tb.add_row('no benches running', '', '', '', '', '')
        return self.frame('benches', tb, 'fight benches', 'magenta')

    def proc_panel(self, height=12):
        ps = sorted(self.emu_list, key=lambda x: (x[1], x[0]))
        self.page['procs'] = max(1, height - 5)
        sel = self.sel['procs'] = min(self.sel.get('procs', 0), max(0, len(ps) - 1))
        a, b = self.window(len(ps), sel, height - 5)
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for c, kw in (('pid', {'min_width': 7}), ('kind', {'min_width': 7}), ('cpu', {'min_width': 5}),
                      ('mem', {'min_width': 5}), ('up', {'min_width': 7}), ('command', {'ratio': 1})):
            tb.add_column(c, no_wrap=True, **kw)
        for i, (pid, kind, cpu, rss, ct, cl) in enumerate(ps[a:b], a):
            tb.add_row(str(pid), kind, f'{cpu:.0f}%', f'{rss / 2**20:.0f}M', hms(time.time() - ct),
                       Text(cl, overflow='ellipsis'), style='on grey23' if i == sel and self.focus == 'procs' else None)
        return self.frame('procs', tb, 'processes', 'blue')

    def footer(self):
        t = Text(' ')
        keys = ([('Esc/Enter', 'back'), ('↑↓ wheel PgUp/PgDn', 'scroll events')] if self.detail else
                [('Tab/1-4/click', 'panel'), ('↑↓ j/k wheel', 'select'), ('PgUp/PgDn g/G', 'page'),
                 ('Enter', 'run detail'), ('z', 'zoom'), ('r', 'running only'), ('H', 'hours'), ('q', 'quit')])
        for k, what in keys:
            t.append(f' {k} ', style='bold black on cyan')
            t.append(f' {what}  ')
        return t

    def render(self, size=(200, 50)):
        w, h = size
        lay = Layout()
        body = max(10, h - 4 - 1)
        if self.detail:
            lay.split_column(Layout(self.header(), size=4), Layout(self.detail_panel(body), size=body),
                             Layout(self.footer(), size=1))
            return lay
        if self.zoom:
            p = {'runs': lambda: self.runs_panel(body), 'suite': self.suite_panel,
                 'benches': lambda: self.bench_panel(body), 'procs': lambda: self.proc_panel(body)}[self.focus]()
            lay.split_column(Layout(self.header(), size=4), Layout(p, size=body), Layout(self.footer(), size=1))
            return lay
        suite_h = 8
        rest = max(6, body - suite_h)
        runs_h = max(6, rest * 3 // 5)
        bottom_h = max(5, rest - runs_h)
        self.regions = (4, 4 + runs_h, 4 + runs_h + suite_h, w // 2)
        lay.split_column(Layout(self.header(), size=4), Layout(self.runs_panel(runs_h), size=runs_h),
                         Layout(self.suite_panel(), size=suite_h), Layout(name='bottom', size=bottom_h),
                         Layout(self.footer(), size=1))
        lay['bottom'].split_row(Layout(self.bench_panel(bottom_h)), Layout(self.proc_panel(bottom_h)))
        return lay

    def click(self, x, y):
        if self.detail or self.zoom or not hasattr(self, 'regions'):
            return
        top, runs_end, suite_end, mid = self.regions
        if y > top:
            self.focus = ('runs' if y <= runs_end else 'suite' if y <= suite_end else
                          'benches' if x <= mid else 'procs')


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
