"""Run a macro many times in parallel, one emulator per process (at most 10), and record
success, frames and every failure (with a state and a shot).

    python3 scripts/harness/trials.py chain 100            # power-on to town, end to end
    python3 scripts/harness/trials.py fight 100 --procs 10

Each trial runs in a fresh process (Pool, maxtasksperchild=1), seeded by its number:
the seed sets start delays (the game's RNG advances every frame) and the macro's choices.
Output, under rips/harness/t2/trials/<macro>/:
  results.jsonl      one line per trial: ok, outcome, frames, legs, failure kind and info
  fail/<k>.state/.png  where a failed trial stopped
  captured/<k>.jsonl the text the trial printed
and the merged text goes to rips/harness/t2/captured.jsonl, first sightings' shots to
rips/harness/t2/shots/.
"""
import os, sys, json, time, random, argparse, statistics, multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
T2 = os.path.join(ROOT, 'rips/harness/t2')
SHOTS = os.path.join(T2, 'shots')
MAX_PROCS = 10


# --- the trials: each takes (g, k, rng) and returns a dict with 'legs' {name: frames}
# and optionally 'outcome'; it raises on failure ---

def t_chain(g, k, rng):
    from harness import flow
    r = flow.chain(g, seed=k)
    r['outcome'] = 'wipe' if r['wiped'] else 'ok'
    return r


def _maze_party_slot(g, roster_index):
    return g.party_slots().index(roster_index)


def t_fight(g, k, rng):
    from harness import battle, maze
    from harness.game import Stuck
    st = ['battle_cmd0', 'battle_cmd1', 'battle_r2'][k % 3]
    g.load('t2/states/' + st)
    g.step(rng.randrange(0, 60))
    f0 = g.frame
    r = battle.fight(g)
    if g.overlay() != 'MAZE':
        raise Stuck('fight: not back in the maze', where=g.where())
    from harness import flow
    wiped = flow.party_dead(g)
    if not wiped:
        maze.settle(g)
    return dict(legs={'fight': g.frame - f0}, rounds=r['rounds'], outcome='wipe' if wiped else 'ok', start=st)


def t_talk(g, k, rng):
    from harness import play, maze
    from harness.game import Stuck
    g.load('t2/states/talk_guy_door')
    g.step(rng.randrange(0, 60))
    f0 = g.frame
    n = play.talk(g)
    if not maze.calm(g) and not maze.settle(g):
        raise Stuck('talk: not calm after', where=g.where())
    return dict(legs={'talk': g.frame - f0}, presses=n)


def t_cast(g, k, rng):
    from harness import camp, maze
    from harness.game import Stuck
    st = ['maze_walk0', 'after_battle1'][k % 2]
    g.load('t2/states/' + st)
    g.step(rng.randrange(0, 60))
    cy = _maze_party_slot(g, 8)
    target = rng.choice([i for i, x in enumerate(g.party_slots()) if x is not None])
    sp0 = g.char(8)['sp'][1][0]
    f0 = g.frame
    camp.cast(g, cy, 1, 1, 0, target=target)
    camp.close_camp(g)
    if g.char(8)['sp'][1][0] != sp0 - 1:
        raise Stuck('cast: spell points unchanged', sp0=sp0, sp=g.char(8)['sp'][1][0])
    return dict(legs={'cast': g.frame - f0}, start=st)


def t_inn(g, k, rng):
    from harness import town
    from harness.game import Stuck
    g.load('t2/states/chain_town_7')
    g.step(rng.randrange(0, 60))
    slot = rng.randrange(6)
    room = rng.choice(['Stables', 'Cot', 'Economy'])
    weeks = rng.choice([None, 1, 2])
    gather = rng.random() < 0.5
    f0 = g.frame
    r = town.inn_stay(g, slot, room, weeks=weeks, gather=gather)
    town.to_town_bar(g)
    want = 1 if room == 'Stables' and weeks is None else weeks
    if not r['poor'] and want is not None and r['weeks'] != want:
        raise Stuck('inn: wrong number of weeks', want=want, got=r['weeks'])
    if r['poor'] and gather and r['weeks'] == 0:
        raise Stuck('inn: gathered but did not sleep')
    return dict(legs={'inn': g.frame - f0}, room=room, weeks=r['weeks'], poor=r['poor'], gather=gather)


def t_temple(g, k, rng):
    from harness import town
    from harness.game import Stuck
    g.load('t2/states/town_dead3_rich')
    g.step(rng.randrange(0, 60))
    patient = rng.choice([6, 7, 8])
    f0 = g.frame
    r = town.temple_heal(g, patient, 0)
    town.to_town_bar(g)
    cost_ok = patient != 8                    # Cy (1000 G) is more than Uranus's 331
    if cost_ok and r['outcome'] not in ('alive', 'ashes'):
        raise Stuck('temple: expected a raise', outcome=r['outcome'])
    if not cost_ok and r['outcome'] != 'poor':
        raise Stuck('temple: expected not enough gold', outcome=r['outcome'])
    if r['outcome'] == 'alive' and r['status'] != 0:
        raise Stuck('temple: alive but status set', status=r['status'])
    return dict(legs={'temple': g.frame - f0}, result=r['outcome'], patient=patient)


def t_boltac(g, k, rng):
    from harness import town
    from harness.game import Stuck
    g.load('t2/states/chain_town_7')
    g.step(rng.randrange(0, 60))
    slot = rng.randrange(6)
    item = rng.randrange(4)
    f0 = g.frame
    b = town.boltac_buy(g, slot, 0, 0, item)
    f1 = g.frame
    idx = town.town_party(g)[slot]
    s = town.boltac_sell(g, slot, len(g.char(idx)['items']) - 1)
    town.boltac_leave(g)
    town.to_town_bar(g)
    price = [10, 10, 400, 25000][item]
    if b['outcome'] == 'bought' and b['gold0'] - b['gold'] != price:
        raise Stuck('boltac: wrong price', paid=b['gold0'] - b['gold'], price=price)
    if (b['outcome'] == 'poor') != (b['gold0'] < price):
        raise Stuck('boltac: poor mismatch', gold=b['gold0'], price=price, outcome=b['outcome'])
    if s['outcome'] != 'sold' or s['gold'] <= s['gold0']:
        raise Stuck('boltac: sale', **s)
    return dict(legs={'buy': f1 - f0, 'sell': g.frame - f1}, bought=b['outcome'], sold_for=s['gold'] - s['gold0'])


def t_door(g, k, rng):
    """The Grounds' only reachable doors: through the Shrine-front door (11,20)<->(11,19)
    both ways, then into the locked one north of (11,19)."""
    from harness import maze, play
    from harness.game import Stuck
    g.load('t2/states/maze_good')
    g.step(rng.randrange(0, 60))
    f0 = g.frame
    maze.walk_to(g, 11, 19, play.handle_interrupt)
    f1 = g.frame
    maze.walk_to(g, 11, 21, play.handle_interrupt)
    maze.walk_to(g, 11, 19, play.handle_interrupt)
    f2 = g.frame
    r = None
    for _ in range(5):
        r = maze.step(g, 0)
        if r != 'interrupted':
            break
        play.handle_interrupt(g)
    if r != 'locked':
        raise Stuck('door: locked door not seen', got=r)
    return dict(legs={'door_walk_in': f1 - f0, 'door_back_and_in': f2 - f1, 'locked': g.frame - f2})


TRIALS = dict(chain=t_chain, fight=t_fight, talk=t_talk, cast=t_cast, inn=t_inn,
              temple=t_temple, boltac=t_boltac, door=t_door)


def run_one(args):
    macro, k, out = args
    from harness.game import Game, Stuck
    rng = random.Random(1000003 * k + 17)
    g = Game(capture=True, shots_dir=SHOTS)
    t0 = time.time()
    rec = dict(macro=macro, k=k)
    try:
        r = TRIALS[macro](g, k, rng)
        rec.update(ok=True, outcome=r.pop('outcome', 'ok'), legs=r.pop('legs', {}), extra=r)
    except Exception as e:
        info = getattr(e, 'info', {})
        rec.update(ok=False, outcome='fail', kind=getattr(e, 'what', '%s: %s' % (type(e).__name__, e)),
                   leg=info.get('leg'), legs=info.get('legs_done', {}),
                   info={a: b for a, b in info.items() if a not in ('legs_done',)})
        try:
            g.save(os.path.relpath(os.path.join(out, 'fail', str(k)), os.path.join(ROOT, 'rips/harness')))
            g.shot(os.path.relpath(os.path.join(out, 'fail', str(k)), os.path.join(ROOT, 'rips/harness')))
        except Exception as e2:
            rec['save_error'] = str(e2)
    rec['frames'] = g.frame
    rec['wall'] = round(time.time() - t0, 1)
    os.makedirs(os.path.join(out, 'captured'), exist_ok=True)
    with open(os.path.join(out, 'captured', '%d.jsonl' % k), 'w', encoding='utf-8') as f:
        for m in g.cap.messages:
            f.write(json.dumps({a: b for a, b in m.items() if a != 'shot_pending'}, ensure_ascii=False, default=str) + '\n')
    return rec


def merge_captured():
    """All trials' text into t2/captured.jsonl: one line per distinct (file, idx, text),
    with how often and in which trials it was seen."""
    seen = {}
    base = os.path.join(T2, 'trials')
    for macro in sorted(os.listdir(base)):
        d = os.path.join(base, macro, 'captured')
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            for line in open(os.path.join(d, fn), encoding='utf-8'):
                m = json.loads(line)
                key = (m.get('file'), m.get('idx'), m.get('text'))
                if key not in seen:
                    seen[key] = dict(file=key[0], idx=key[1], text=key[2], count=0,
                                     first='%s/%s' % (macro, fn[:-6]))
                seen[key]['count'] += 1
    with open(os.path.join(T2, 'captured.jsonl'), 'w', encoding='utf-8') as f:
        for v in seen.values():
            f.write(json.dumps(v, ensure_ascii=False) + '\n')
    return len(seen)


def summarize(recs):
    legs = {}
    for r in recs:
        for name, fr in r['legs'].items():
            legs.setdefault(name, dict(ok=[], fail=0))['ok'].append(fr)
        if not r['ok'] and r.get('leg'):
            legs.setdefault(r['leg'], dict(ok=[], fail=0))['fail'] += 1
    out = {}
    for name, v in legs.items():
        n = len(v['ok']) + v['fail']
        out[name] = dict(n=n, ok=len(v['ok']), rate=round(len(v['ok']) / n, 3) if n else None,
                         median=statistics.median(v['ok']) if v['ok'] else None,
                         worst=max(v['ok']) if v['ok'] else None)
    kinds = {}
    for r in recs:
        if not r['ok']:
            kinds.setdefault('%s | %s' % (r.get('leg'), r['kind']), []).append(r['k'])
    outcomes = {}
    for r in recs:
        outcomes[r['outcome']] = outcomes.get(r['outcome'], 0) + 1
    return dict(trials=len(recs), outcomes=outcomes, legs=out, failures=kinds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('macro', choices=sorted(TRIALS))
    ap.add_argument('n', type=int)
    ap.add_argument('--procs', type=int, default=MAX_PROCS)
    ap.add_argument('--start', type=int, default=0)
    a = ap.parse_args()
    procs = min(a.procs, MAX_PROCS)
    out = os.path.join(T2, 'trials', a.macro)
    os.makedirs(os.path.join(out, 'fail'), exist_ok=True)
    os.makedirs(SHOTS, exist_ok=True)
    t0 = time.time()
    recs = []
    ctx = mp.get_context('spawn')
    with ctx.Pool(procs, maxtasksperchild=1) as pool, open(os.path.join(out, 'results.jsonl'), 'a') as f:
        for rec in pool.imap_unordered(run_one, [(a.macro, k, out) for k in range(a.start, a.start + a.n)]):
            recs.append(rec)
            f.write(json.dumps(rec, default=str) + '\n'); f.flush()
            print(rec['k'], rec['outcome'], rec.get('leg') or '', rec.get('kind') or '', rec['wall'], flush=True)
    s = summarize(recs)
    s['wall'] = round(time.time() - t0)
    s['captured_distinct'] = merge_captured()
    json.dump(s, open(os.path.join(out, 'summary-%d-%d.json' % (a.start, a.start + a.n)), 'w'), indent=1)
    print(json.dumps(s, indent=1))


if __name__ == '__main__':
    main()
