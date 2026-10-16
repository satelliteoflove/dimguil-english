#!/usr/bin/env python3
"""Fight a chosen enemy group on the built disc and keep each battle message it prints.

    fightshow.py OUTDIR ID [--rounds N] [--seed S] [--until IDX,IDX...] [--state STATE]

A cold boot of rips/iso/dimguil-en.cue, New Game, the premade party
(Uranus, Venus, Jupiter, Earth), Begin Adventure, then a walk on the Grounds until a
fight. Before the walk, every group id in the maze's encounter tables is set to ID in RAM
(wander_groups 0x8005a530 and the fight squares' three tiers 0x80059ec4-0x8005a3af, MAIN
data; docs/re/A-maze.md, "Encounters"), so the fight is with table 1 index ID + 0x2c
(DATA02/M_DTnnn.BIN for ID 1-339). Nothing else is written: the code, the text and the
monster records all come from the disc, and FIGHTMSG.OBJ is loaded at boot and again on
entering the maze.

Groups away from their own floors can hang at the battle's start (phase 4, the same on
the original disc), so for those use --state: a maze save state on a floor where the
group appears, made on a build with the same MAIN code (checked). FIGHTMSG.OBJ in its RAM
is from that build's disc, so the built one (rips/dirty) is written over it at 0x801d7000
(data only; the monster files still load from this disc, whose file tables match when
the executables match).

The party defends for N rounds (default 10) so the monsters get turns, then fights with
the harness's default policy. Each message is captured as the game expands it (the
harness's text capture, scripts/harness/text.py), with names filled in:
OUTDIR/ID/messages.txt lists them, and OUTDIR/ID/FIGHTMSG_<index>.png is the screen
showing each FIGHTMSG string the first time it printed. --until stops at the next command
menu once all the FIGHTMSG strings listed have printed. One ID per run: the core's debug
hooks are global, so the harness allows one Game per process.
"""
import os, random, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from harness.game import Game
from harness import battle, flow, maze, play, town

CUE = os.path.join(ROOT, 'rips/iso/dimguil-en.cue')
TABLES = [(0x80059ec4, 0x8005a3b0), (0x8005a530, 0x8005a530 + 378 * 2)]
PARTY = ['Uranus', 'Venus', 'Jupiter', 'Earth']


class Done(Exception):
    pass


def run(out, gid, rounds, seed, until=(), state=None):
    os.makedirs(out, exist_ok=True)
    g = Game(disc=CUE, shots_dir=out)
    rng = random.Random(seed)
    if state:
        exe = open(os.path.join(ROOT, 'rips/dirty/dimguil/SLPS_026.91'), 'rb').read()
        g.load(state)
        lo, hi = 0x800114d8, 0x80024bf0
        if g.e.read(lo, hi - lo) != exe[lo - 0x8000f800:hi - 0x8000f800]:
            sys.exit(f'{state} has MAIN code from another build')
        fm = open(os.path.join(ROOT, 'rips/dirty/dimguil/DATA01/FIGHTMSG.OBJ'), 'rb').read()
        g.e.write(0x801d7000, fm)
    else:
        g.step(rng.randrange(0, 120))
        town.new_game(g)
        names = {g.name(i): i for i in range(g.roster_count())}
        town.form_party(g, [names[n] for n in PARTY])
        town.begin_adventure(g)
    for lo, hi in TABLES:
        g.e.write(lo, struct.pack('<H', gid) * ((hi - lo) // 2))
    # the group's record ids, to tell its fights from others (type-2 tokens, events)
    sys.path.insert(0, os.path.join(HERE, 're'))
    from attackverbs import records
    fn = 'DATA02/' + ('M_DT%03d.BIN' % gid if gid < 340 else 'MPT%02d.BIN' % (gid - 339))
    d = open(os.path.join(ROOT, 'rips/iso/dimguil', fn), 'rb').read()
    ids = {struct.unpack_from('<H', d, o + 0x6c)[0] for o in records(d)}
    start = [None]

    def ours(g):
        return any(g.u16(0x8008a918 + k * 0xd0 + 0x6c) in ids for k in range(1, 5))

    def policy(g, m, opts):
        if start[0] is None:
            start[0] = len(g.cap.messages)
        seen = {x['idx'] for x in g.cap.messages[start[0]:] if x['file'] == 'FIGHTMSG.OBJ'}
        if until and set(until) <= seen and ours(g):
            raise Done
        if not ours(g):
            return battle.default_policy(g, m, opts)
        if battle.ROUND <= rounds and battle.PARRY in opts:
            return ('parry',)
        return battle.default_policy(g, m, opts)

    class Policy(play.Policy):
        battle = staticmethod(policy)

    fought = []

    def on_int(g):
        f0 = g.frame
        start[0] = None
        r = play.handle_interrupt(g, Policy)
        fought.append(g.frame - f0)
        return r

    try:
        for _ in range(40):
            for tx, ty in flow.walk_targets(g, rng, 1):
                maze.walk_to(g, tx, ty, on_int)
            if fought and battle.ROUND and not until:
                break
    except Done:
        print(f'{gid}: printed {until}')
    except Exception as x:
        print(f'{gid}: stopped: {x!r} at {g.where()}')
        g.e.save(os.path.join(out, 'stopped.state'))
        g.e.shot(os.path.join(out, 'stopped.png'), scale=1)
    g.flush_shots()
    with open(os.path.join(out, 'messages.txt'), 'w', encoding='utf-8') as f:
        for m in g.cap.messages:
            f.write(f"{m['frame']:7d} {m['file']} {m['idx']:3d}  {m.get('text', '')!r}\n")
    print(f'{gid}: {sum(1 for m in g.cap.messages if m["file"] == "FIGHTMSG.OBJ")} battle '
          f'messages -> {out}')


def main():
    a = sys.argv[1:]
    rounds, seed = 10, 0
    if '--rounds' in a:
        k = a.index('--rounds'); rounds = int(a[k + 1]); del a[k:k + 2]
    if '--seed' in a:
        k = a.index('--seed'); seed = int(a[k + 1]); del a[k:k + 2]
    until = ()
    if '--until' in a:
        k = a.index('--until'); until = tuple(int(x) for x in a[k + 1].split(',')); del a[k:k + 2]
    state = None
    if '--state' in a:
        k = a.index('--state'); state = a[k + 1]; del a[k:k + 2]
    run(os.path.join(a[0], a[1]), int(a[1]), rounds, seed, until, state)


if __name__ == '__main__':
    main()
