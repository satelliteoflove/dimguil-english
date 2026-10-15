#!/usr/bin/env python3
"""One training trip by the bot from a town state, the way a chapter's train goal runs it,
optionally serving the emulator's RAM over UDP as RetroArch's network commands would, so
scripts/humanwatch.py can watch the bot the way it watches a person.

    python3 scripts/harness/bot_trip.py STATE --out DIR [--chapter 9] [--seed N] [--variant K]
                                        [--name train_05] [--serve PORT] [--fps 60] [--idle FRAMES]

STATE is a .state path (a chapter's goal state in town). The trip is chapters.Run.train on
the chapter's TRAIN_AREAS, inside Run.goal (the chain's goal path), with one try: a wipe
ends it instead of reloading. With the chapter's memory side file beside STATE (agent 14),
the run starts from it, so pull-backs carry over as they would in the chain.

Writes to DIR: trip_log.jsonl (the run log, [frame, kind, ...]), captured.jsonl (every
message, from the text hooks), result.json, end.state.

--serve PORT answers READ_CORE_MEMORY (physical address, byte count) and GET_STATUS once
per emulated frame, and paces the emulator to --fps (RetroArch's own timing); any other
command is counted in result.json's 'other_commands' and not obeyed. --idle FRAMES just
loads STATE and runs that many frames with no input (a responder for a quick test).
"""
import argparse, json, os, socket, sys, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from harness.game import Game, Stuck
from harness import chapters, chapter1, battle

ap = argparse.ArgumentParser()
ap.add_argument('state')
ap.add_argument('--out', required=True)
ap.add_argument('--chapter', type=int, default=9)
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--variant', type=int, default=0)
ap.add_argument('--name', default='train')
ap.add_argument('--serve', type=int)
ap.add_argument('--fps', type=float, default=60.0)
ap.add_argument('--idle', type=int)
a = ap.parse_args()

out = os.path.abspath(a.out)
os.makedirs(out, exist_ok=True)
state = os.path.abspath(a.state)
g = Game(capture=True)


class Responder:
    """RetroArch's network commands, read-only, from the harness emulator's RAM."""

    def __init__(self, port, fps):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(('127.0.0.1', port))
        self.s.setblocking(False)
        self.dt = 1.0 / fps if fps else 0
        self.t = time.perf_counter()
        self.counts = {}
        self.other = {}

    def frame(self):
        while True:
            try:
                data, addr = self.s.recvfrom(65536)
            except (BlockingIOError, OSError):
                break
            cmd = data.decode('ascii', 'replace').split()
            if not cmd:
                continue
            self.counts[cmd[0]] = self.counts.get(cmd[0], 0) + 1
            if cmd[0] == 'READ_CORE_MEMORY' and len(cmd) == 3:
                ad, n = int(cmd[1], 16), int(cmd[2])
                b = g.e.read(ad & 0x1fffff, min(n, 0x200000 - (ad & 0x1fffff)))
                rep = 'READ_CORE_MEMORY %x %s' % (ad, ' '.join('%02X' % x for x in b))
            elif cmd[0] == 'GET_STATUS':
                rep = 'GET_STATUS PLAYING psx,Wizardry - Dimguil (English WIP),crc32=00000000'
            else:
                self.other[cmd[0]] = self.other.get(cmd[0], 0) + 1
                continue
            self.s.sendto(rep.encode(), addr)
        if self.dt:
            self.t += self.dt
            d = self.t - time.perf_counter()
            if d > 0:
                time.sleep(d)
            elif d < -0.5:
                self.t = time.perf_counter()


resp = None
if a.serve:
    resp = Responder(a.serve, a.fps)
    _run = g.e.run

    def run(frames=1, hold=()):
        for _ in range(frames):
            _run(1, hold)
            resp.frame()
    g.e.run = run

g.load(state)
t0, f0 = time.time(), g.frame
res = dict(state=state, chapter=a.chapter, seed=a.seed, variant=a.variant, name=a.name,
           game_frame0=g.u32(0x80060788), emu_frame0=f0)
r = None
try:
    if a.idle:
        g.step(a.idle)
        res['ok'] = True
    else:
        mod = sys.modules['harness.chapter%d' % a.chapter]
        r = chapters.Run(g, seed=a.seed, variant=a.variant, out=out, auto_cases=False)
        r.retries = 1
        r.chapter = a.chapter
        r.ckpt = state
        base = state[:-len('.state')]
        r.full_points = chapters.load_points(g, base)
        m = chapters.load_memory(g, base)
        if m and m.get('chapter') == a.chapter:
            r.log.extend(tuple(x) for x in m['log'])
            r._pull = {tuple(k): dict(v, to=tuple(v['to']), at=v['at']) for k, v in m['pull']}
            r._since = {tuple(k): v for k, v in m['since']}
        l0 = len(r.log)
        res['memory'] = bool(m)
        res['areas'] = list(mod.TRAIN_AREAS)
        try:
            r.goal(a.name, lambda: r.train(mod.TRAIN_AREAS))
            res['ok'] = True
        except Stuck as e:
            res['ok'] = False
            res['error'] = '%s: %s' % (e.what, {k: str(v) for k, v in e.info.items()})
        with open(os.path.join(out, 'trip_log.jsonl'), 'w') as f:
            for x in r.log[l0:]:
                f.write(json.dumps(x, default=str) + '\n')
except Exception as e:
    res['ok'] = False
    res['error'] = '%s: %s' % (type(e).__name__, e)
    res['trace'] = traceback.format_exc()
finally:
    res['frames'] = g.frame - f0
    res['wall'] = round(time.time() - t0, 1)
    if resp:
        res['commands'] = resp.counts
        res['other_commands'] = resp.other
    try:
        g.save(os.path.join(out, 'end'))
    except Exception:
        pass
    if g.cap:
        with open(os.path.join(out, 'captured.jsonl'), 'w', encoding='utf-8') as f:
            for x in g.cap.messages:
                f.write(json.dumps({k: v for k, v in x.items() if k != 'shot_pending'},
                                   ensure_ascii=False) + '\n')
    json.dump(res, open(os.path.join(out, 'result.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != 'trace'}, default=str), flush=True)
