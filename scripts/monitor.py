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
            elif kind == 'temple':
                self.temple += 1
            elif kind == 'retry':
                self.retries += 1
                self.goal_now = rest[0] if rest else self.goal_now
                self.last = f'retry {rest[0]}: {rest[1]}' if len(rest) > 1 else 'retry'
                self.recent.append(self.last)
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
            if pf in self.runs or not (os.path.exists(pf[:-4] + '.out')
                                       or os.path.exists(os.path.join(pf[:-4], 'live.jsonl'))):
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

    def runs_panel(self):
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for col, kw in (('run', {}), ('state', {}), ('wall', {'justify': 'right'}), ('game', {'justify': 'right'}),
                        ('speed', {}), ('goals done', {'ratio': 2}), ('fights', {'justify': 'right'}),
                        ('boss', {'justify': 'right'}), ('deaths', {'justify': 'right'}),
                        ('temple', {'justify': 'right'}), ('death times', {}), ('levels', {}),
                        ('last events', {'ratio': 4, 'min_width': 44})):
            tb.add_column(col, **kw)
        rows = sorted(self.runs.values(), key=lambda r: (r.state()[0] != 'running', -r.started))
        for r in rows[:14]:
            st, since = r.state()
            color = {'running': 'green', 'done': 'cyan', 'failed': 'red', 'stopped': 'yellow'}[st]
            mark = {'running': '●', 'done': '✓', 'failed': '✗', 'stopped': '■'}[st]
            wall = hms(time.time() - since) if since else hms(os.path.getmtime(r.out.path) - r.started) \
                if os.path.exists(r.out.path) else '-'
            sp = self.speed.get(r.name) or []
            speed = Text(spark(sp, 12, 0, None), style='magenta')
            if st == 'running' and sp:
                speed.append(f' {sp[-1]:.1f}x')
            goals = Text(' '.join(f"{g}{'' if t == 1 else f'×{t}'}" for g, t, _ in r.goals) or '-')
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
                       Text(last, overflow='ellipsis', no_wrap=True))
        if not rows:
            tb.add_row('no runs in the last %d hours' % self.hours, *[''] * 12)
        return Panel(tb, title='chapter runs', title_align='left', box=box.ROUNDED, border_style='green')

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
        return Panel(Group(*lines), title='suite round', title_align='left', box=box.ROUNDED,
                     border_style='yellow')

    def bench_panel(self):
        bs = benches()
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for c, kw in (('bench output', {'ratio': 3}), ('settings', {'ratio': 2}), ('progress', {'no_wrap': True}),
                      ('won', {}), ('deaths/fight', {}), ('running', {})):
            tb.add_column(c, **kw)
        for b in bs:
            prog = Text(f"{b['n']}/{b['total']} ")
            prog.append_text(bar(b['n'] / b['total'] if b['total'] else 0, 12, 'magenta'))
            tb.add_row(b['file'], b['env'] or '-', prog, f"{b['won']}/{b['n']}",
                       f"{b['dead'] / b['n']:.2f}" if b['n'] else '-', hms(time.time() - b['since']))
        if not bs:
            tb.add_row('no benches running', '', '', '', '', '')
        return Panel(tb, title='fight benches', title_align='left', box=box.ROUNDED, border_style='magenta')

    def proc_panel(self):
        tb = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
        for c, kw in (('pid', {'min_width': 7}), ('kind', {'min_width': 7}), ('cpu', {'min_width': 5}),
                      ('mem', {'min_width': 5}), ('up', {'min_width': 7}), ('command', {'ratio': 1})):
            tb.add_column(c, no_wrap=True, **kw)
        for pid, kind, cpu, rss, ct, cl in sorted(self.emu_list, key=lambda x: x[1])[:12]:
            tb.add_row(str(pid), kind, f'{cpu:.0f}%', f'{rss / 2**20:.0f}M', hms(time.time() - ct),
                       Text(cl, overflow='ellipsis'))
        return Panel(tb, title='processes', title_align='left', box=box.ROUNDED, border_style='blue')

    def render(self):
        lay = Layout()
        lay.split_column(Layout(self.header(), size=4), Layout(self.runs_panel(), ratio=3),
                         Layout(self.suite_panel(), size=8),
                         Layout(name='bottom', ratio=2))
        lay['bottom'].split_row(Layout(self.bench_panel()), Layout(self.proc_panel()))
        return lay


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
        Console(width=200, height=50).print(m.render(), height=50)
        return
    with Live(m.render(), screen=True, refresh_per_second=4) as live:
        try:
            while True:
                time.sleep(a.every)
                m.tick()
                live.update(m.render())
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
