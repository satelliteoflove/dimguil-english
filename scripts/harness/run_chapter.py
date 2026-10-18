#!/usr/bin/env python3
"""Run walkthrough chapters, chained, in this process.

    python3 scripts/harness/run_chapter.py NAME --chapters 1-3 [--seed N] [--variant K]
                                           [--from STATE] [--screens DIR] [--no-cases]
                                           [--battle-rng] [--disc CUE] [--no-main-code]

Chapter 1 starts from power-on unless --from is given; a later first chapter needs
--from (the previous chapter's end state, e.g. chapters/c1v0/c1_end). Outputs go to
rips/harness/chapters/NAME/: result.json (per chapter: goals, frames, wall time, stuck),
log.jsonl, captured.jsonl, goal and stuck states, c<N>_end.state after each chapter;
shots to rips/harness/chapters/shots/ (shared, one per string id). --screens logs every
screen before each press for the T5 checks (harness.screens) to rips/harness/DIR.

Stuck states become regression cases in rips/harness/regress/pending/chapters.jsonl (added
to the live list between suite rounds), not in the live cases.jsonl; --no-cases makes
none. Each battle's BATTLE code is checked once in RAM against the disc under test's
BATTLE.BIN at the spell-sound fix's 36 words (bugs.md 1.15), so a run from a state made on
an older disc shows which code its fights ran: result.json 'battle_code'.

From a state, --seed changes nothing: it only times the boot and the character rerolls,
and the fights roll on battle_rng_state (0x80079a34, docs/engine-notes.md "Randomness"),
which the state keeps. --battle-rng writes a value from --seed there after loading (as
fightbench does), so runs from one state with different seeds get different fights.

Every 5 s of wall time the run writes NAME/now.json (RAM reads only): the current goal,
where the party is, and each member's roster index, name, class, level, HP, max HP and
status, for the monitor's run and chain views.

--disc runs on another disc image (its dimguil/BATTLE.BIN beside it) instead of
rips/harness/disc/. --no-main-code skips laying the disc's MAIN_CODE over a --from state:
for states made on that same disc (the full run, scripts/harness/fullrun.py).
"""
import argparse, json, os, random, struct, sys, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from harness.game import Game, OUT, DISC
from harness import chapters, regress, town

# the live case list is the suite runner's alone (docs/agent-workflow.md)
regress.CASES = os.path.join(regress.REG, 'pending', 'chapters.jsonl')
os.makedirs(os.path.dirname(regress.CASES), exist_ok=True)

# the spell-sound fix's words (asm/bugfix_spell_sound_reload.asm: three load sites and the
# stop routine in FUN_800c3188); BATTLE loads at 0x800a1000
FIX_WORDS = ([0x800a4204 + 4 * i for i in range(6)] + [0x800a4220]
             + [0x800a54c8 + 4 * i for i in range(9)] + [0x800a5510]
             + [0x800a5524 + 4 * i for i in range(10)] + [0x800a5578, 0x800a557c]
             + [0x800c3188 + 4 * i for i in range(7)])
assert len(FIX_WORDS) == 36

ap = argparse.ArgumentParser()
ap.add_argument('name')
ap.add_argument('--chapters', default='1-1')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--variant', type=int, default=0)
ap.add_argument('--from', dest='src')
ap.add_argument('--screens')
ap.add_argument('--battle-rng', action='store_true',
                help='with --from: seed battle_rng_state from --seed after loading')
ap.add_argument('--no-cases', action='store_true',
                help="don't add stuck states to the regression suite (dev runs, old-disc states)")
ap.add_argument('--disc', default=DISC, help='the disc image (cue) to run, default the harness disc')
ap.add_argument('--no-main-code', action='store_true',
                help="with --from: don't lay the disc's MAIN_CODE over the state")
ap.add_argument('--shots', default='chapters/shots',
                help='where the per-string shots go, under rips/harness (a dev run keeps its own)')
a = ap.parse_args()
first, _, last = a.chapters.partition('-')
first, last = int(first), int(last or first)
if first > 1 and not a.src:
    sys.exit('chapter %d needs --from (chapter %d end state)' % (first, first - 1))

out = 'chapters/' + a.name
d = os.path.join(OUT, out)
os.makedirs(d, exist_ok=True)
g = Game(disc=a.disc, capture=True, shots_dir=os.path.join(OUT, a.shots))
scr = None
if a.screens:
    from harness.screens import Screens
    scr = Screens(g, a.screens)
battle_code = dict(match=0, differ=0, first_differ=None)
_bin = open(os.path.join(os.path.dirname(a.disc), 'dimguil', 'BATTLE.BIN'), 'rb').read()
_want = [int.from_bytes(_bin[w - 0x800a1000:w - 0x800a1000 + 4], 'little') for w in FIX_WORDS]
_in_battle = [0]


def check_battle_code():
    if g.overlay() != 'BATTLE':
        _in_battle[0] = 0
        return
    _in_battle[0] += 1
    if _in_battle[0] != 30:         # once per battle, after the overlay is in
        return
    if [g.u32(w) for w in FIX_WORDS] == _want:
        battle_code['match'] += 1
        if battle_code['match'] == 1:
            print('BATTLE code in RAM matches the disc (first battle, frame %d)' % g.frame, flush=True)
    else:
        battle_code['differ'] += 1
        if battle_code['first_differ'] is None:
            battle_code['first_differ'] = g.frame
            print('BATTLE code in RAM differs from the disc at frame %d' % g.frame, flush=True)


g.t.ticks.append(check_battle_code)
if a.src:
    g.load(a.src)
    # a state made before the VWF move keeps the old MAIN while the overlays it loads jump to
    # the new home (regress.MAIN_CODE): lay the disc's code over it, as suite cases do
    for adr, code in ([] if a.no_main_code else regress.disc_main_code()):
        g.e.write(adr, code)
    if a.battle_rng:
        g.e.write(0x80079a34, struct.pack('<I', random.Random(a.seed).getrandbits(32)))
r = chapters.Run(g, seed=a.seed, variant=a.variant, out=out, auto_cases=not a.no_cases)
if a.src:
    r.ckpt = a.src
    # the casters' points after the last Stables, saved beside cN_end (agent 8)
    r.full_points = chapters.load_points(g, a.src)
    print('points known for', sorted(r.full_points))
    # the chapter's log and pull-backs, saved beside goal states (agent 14)
    r.resume_memory = chapters.load_memory(g, a.src)


NOW = os.path.join(d, 'now.json')
_now = dict(goal=None, t=0.0)


def now_tick():
    """now.json: what the run is doing and the party as RAM has it. Reads only."""
    t = time.time()
    if t - _now['t'] < 5:
        return
    _now['t'] = t
    try:
        party = []
        for i in g.party() or town.town_party(g):
            c = g.char(i)
            cls = town.CLASSES[c['cls']] if c['cls'] < len(town.CLASSES) else str(c['cls'])
            party.append([i, c['name'], cls, c['level'], c['hp'], c['max_hp'], c['status']])
        x = dict(t=round(t, 1), frame=g.frame, chapter=getattr(r, 'chapter', None), goal=_now['goal'],
                 where=g.where(), party=party)
        with open(NOW + '.new', 'w') as f:
            json.dump(x, f)
        os.replace(NOW + '.new', NOW)
    except Exception:
        pass


_goal = r.goal


def goal_named(name, fn):
    # the goal now, for now.json; the goal itself runs unchanged
    _now['goal'], _now['t'] = name, 0.0
    return _goal(name, fn)


r.goal = goal_named
g.t.ticks.append(now_tick)


class Stopped(Exception):
    """SIGTERM (agent 16): a run stopped by PID ends as an error does, so result.json,
    log.jsonl and the final state are still written."""


_STOP = []


def _stop(signum, frame):
    # raised from the next frame tick: a signal landing in the emulator's ctypes callback
    # would only print the exception and run on
    _STOP.append(signum)


def _stop_tick():
    if _STOP:
        raise Stopped('SIGTERM')


import signal
signal.signal(signal.SIGTERM, _stop)
g.t.ticks.append(_stop_tick)
t0 = time.time()
ok = True
try:
    res = r.run_chapters(first, last, boot=not a.src)
except Exception as e:
    ok = False
    res = r.report()
    res['error'] = '%s: %s' % (type(e).__name__, e)
    res['info'] = {k: str(v) for k, v in getattr(e, 'info', {}).items()}
    res['trace'] = traceback.format_exc()
    res['failed_chapter'] = r.chapter
    try:
        g.shot(out + '/final_fail')
        g.save(out + '/final_fail')
    except Exception:
        pass
res['ok'] = ok
res['from'] = a.src
res['battle_rng'] = bool(a.src and a.battle_rng)
res['disc'] = a.disc
res['main_code_laid'] = bool(a.src and not a.no_main_code)
res['chapters_asked'] = [first, last]
res['wall'] = round(time.time() - t0, 1)
res['total_frames'] = g.frame
res['battle_code'] = battle_code
json.dump(res, open(os.path.join(d, 'result.json'), 'w'), indent=1, default=str)
with open(os.path.join(d, 'log.jsonl'), 'w') as f:
    for x in r.log:
        f.write(json.dumps(x, default=str) + '\n')
g.flush_shots()
if scr:
    scr.close()
g.dump_messages(os.path.join(d, 'captured.jsonl'))
print(json.dumps({k: v for k, v in res.items() if k not in ('trace', 'goals', 'chapters')}, default=str))
