#!/usr/bin/env python3
"""Bench the golem route as one chain (decision D1, chapter 19 plan; 2026-10-17).

    python3 scripts/harness/golembench.py prep STATE OUTREL SEED
    python3 scripts/harness/golembench.py run OUT.jsonl SEEDS STATE...   (SEEDS: 1-20)

prep: from a town state (a chapter 17 end), walk the party to the Shrine 2F altar (2, 11,
11) the way a goal walks to a boss (Run.ready, Run.go, Run.heal: camp heals and Maporfic),
face north, and save rips/harness/OUTREL.state there, before the Investigate.

run: for each (state, seed): load, seed the battle RNG (0x80079a34), apply the arm, then
Investigate the altar and let the game play on: EVENTMES 35, Yes (Policy.prompt), the Fire
Golem (encounter 150), the floor load to Underground B3 and the Shadow Golem (151) at once,
the load to Area Z's coffin and Quetzalcoatl (169), then the ring and the warp back to the
altar. No camp anywhere in the chain (the game gives none): HP, MP, deaths and drained
levels carry from fight to fight. One line a chain, with a record for each fight met.

Arms, by environment (all investigation only, nothing in the game files):
  OSLO=1      buff_oslo_level 0x8007e830 = 2 and buff_oslo_steps 0x8007e832 = 2500 before
              the Investigate: exactly what a Maoslo cast in camp writes (MAZE buff_maoslo
              0x800e8480). The main party has no Alchemist, so this stands in for one.
  STACK=N     the golem fights get battle.crystal_policy (the Crystal Men's AC stack:
              Morlis then Dilto from the mages until the group's mean AC modifier is
              CM_STACK_TO, Bamatu to the cap, Madi on the low) with CM_STACK_TO = -N.
  SET=K=V,... battle/tactics flags (fightbench.apply_set).
SAVEAT=REL saves each fight's start to rips/harness/REL_ENC.state.
DISC= a .cue to run on (default the harness disc; its dimguil/SLPS_026.91 beside it for
the code lay); TEXT=1 keeps the FIGHTMSG lines.
"""
import json, os, struct, sys, random
H = os.environ.get('HARNESS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(H, 'scripts'))
from harness.game import Game, OUT, DISC, Stuck
from harness import battle, tactics, chapters, chapter1, maze, play
from harness import chapter18
from harness.fightbench import apply_set, seeds, points, points_lv, sp

ALTAR = (2, 11, 11)             # Shrine 2F E11 N12, facing north (square_examine case 0x21)
RING = 0x142
FIRE, SHADOW, QUETZ = 150, 151, 169
OSLO_LEVEL, OSLO_STEPS = 0x8007e830, 0x8007e832
RNG = 0x80079a34
# the chain's fights, rated as story fights whatever FIXED says (the squares are filled in
# from the first runs: the fight can read the party a square back, as at the coffin)
FIGHT_AT = {ALTAR, (2, 11, 12), (6, 19, 11), (6, 20, 11), (6, 18, 11)} | set(chapter18.FIGHT_AT)
tactics.BOSS_AT.update(FIGHT_AT)
CHAIN_MOST = 4
# EVENTMES 36's last box to the Fire Golem's battle: about 3,000 calm frames (altar_probe,
# 2026-10-17: Investigate at 0, 36 closed by 1,292, the fight's load from 4,075)
CHAIN_WAIT = 6000


def run_obj(g, state, seed, out):
    r = chapters.Run(g, seed=seed, variant=0, out=out, auto_cases=False)
    r.retries = 1
    r.chapter = 18
    base = state[:-6] if state.endswith('.state') else os.path.join(OUT, state)
    r.ckpt = base
    try:
        r.full_points = chapters.load_points(g, base)
    except Exception:
        r.full_points = {}
    return r


def here(g):
    return (g.u8(maze.AREA),) + tuple(g.pos())


ORNATE = (1, 11, 15)            # Shrine 1F E11 N8: the ornate door on its north side (event
ORNATE_BIT = 1                  # 0x1e, EVENTMES 33, lock bit 1 of 0x800795fc, difficulty 1)


def unlock_ornate(r):
    """The ornate door on the way to the altar's stairs (Shrine 1F (11, 13) up to (2, 11,
    12)): the lock menu's Pick the lock with the Thief, as chapter 14's B2 door. A picked
    lock's bit is saved with the game, so this is once per party file."""
    from harness import chapter14, nav, ui
    g = r.g
    if nav.flag(g, nav.DOOR_BITS, ORNATE_BIT):
        return True
    r.go(ORNATE)
    for k in range(8):
        maze.face(g, 0)
        chapter1.investigate(g)
        slots = g.party_slots()
        who = next((p for p, ri in enumerate(slots) if ri is not None and g.char(ri)['cls'] == 3
                    and not g.char(ri)['status']), None)
        if who is None:
            who = next(p for p, ri in enumerate(slots) if ri is not None and not g.char(ri)['status'])

        def step(g):
            if g.u8(maze.GAME_STATE) != chapter14.LOCK_STATE:
                return False
            sub = g.u8(chapter14.SUB)
            if sub == 2:
                g.step(10)
                chapter14.pick_slot(g, who, 'lock picker')
            elif sub == 4 and chapter14.s16(g, chapter14.LOCK_CUR) != chapter14.PICK_LOCK:
                c = chapter14.s16(g, chapter14.LOCK_CUR)
                ui.press_until(g, 'up', lambda: chapter14.s16(g, chapter14.LOCK_CUR) != c, 60, 'lock menu')
            elif sub in (0, 4):
                g.step(10)
                ui.press_until(g, 'circle', lambda: g.u8(chapter14.SUB) != sub
                               or g.u8(maze.GAME_STATE) != chapter14.LOCK_STATE, 120, 'lock menu')
            else:
                g.step()
            return True
        chapter14.drive(g, step)
        r.after()
        ok = nav.flag(g, nav.DOOR_BITS, ORNATE_BIT)
        print('pick lock', k, ok, flush=True)
        if ok:
            return True
    return False


def prep(g, state, outrel, seed):
    g.load(state[:-6] if state.endswith('.state') else state)
    r = run_obj(g, state, seed, os.path.dirname(outrel))
    r.ready(train=False)
    if not unlock_ornate(r):
        sys.exit('the ornate door stayed locked')
    r.go(ALTAR)
    while r.door_ready():
        r.ready(train=False)
        r.go(ALTAR)
    r.heal()
    maze.face(g, 0)
    if here(g) != ALTAR:
        r.after()
        r.go(ALTAR)
        maze.face(g, 0)
    g.save(outrel)
    print('saved', outrel, 'at', here(g), 'facing', g.facing() if hasattr(g, 'facing') else '?',
          'party', members(g), flush=True)


def members(g):
    out = []
    for s, ri in enumerate(battle.party_ids(g)):
        if ri is None:
            continue
        c = g.char(ri)
        out.append(dict(slot=s, name=c['name'], hp=c['hp'], max_hp=c['max_hp'], status=c['status'],
                        level=c['level'], sp=sum(c['raw'][0x5c:0x78])))
    return out


def ring_held(g):
    return any(any(it & 0x1ff == RING for it in g.char(i)['items']) for i in g.party())


def bench_one(g, st, seed):
    g.load(st[:-6] if st.endswith('.state') else st)
    if seed:
        g.e.write(RNG, struct.pack('<I', random.Random(seed).getrandbits(32)))
    if os.environ.get('OSLO'):
        g.e.write(OSLO_LEVEL, b'\x02')
        g.e.write(OSLO_STEPS, struct.pack('<H', 2500))
    stack = int(os.environ.get('STACK') or 0)
    if stack:
        battle.CM_STACK_TO = -stack
    fights = []
    orig = battle.fight
    msg0 = len(g.cap.messages) if g.cap else 0

    def fight(g_, policy=battle.default_policy, chest_mode='leave', **k):
        enc = g_.u16(tactics.ENCOUNTER_ID)
        where = here(g_)
        if stack and where in FIGHT_AT and policy is battle.default_policy:
            policy = battle.crystal_policy
        if os.environ.get('SAVEAT'):
            g_.save('%s_%d' % (os.environ['SAVEAT'], enc))
        pre = members(g_)
        p0, pl0 = points(g_), points_lv(g_)
        m0 = len(g_.cap.messages) if g_.cap else 0
        res = orig(g_, policy, chest_mode, **k)
        post = members(g_)
        wiped = all(m['hp'] <= 0 or m['status'] >= 0x20 for m in post)
        won = res['ovl'] == 'MAZE' and not wiped and not (res['fled'] or (0, 0))[0]
        fights.append(dict(
            enc=enc, where=where, story=res['story'], won=won, wiped=wiped, rounds=res['rounds'],
            pre=pre, post=post, spent=p0 - points(g_), spent_lv=[a - b for a, b in zip(pl0, points_lv(g_))],
            casts=[(c[0], sp(c[1])) for c in res['casts']],
            deaths=[(d['who'], d['what'], d['by'], d.get('how')) for d in res.get('deaths') or []],
            drained=[(a['name'], a['level'], b['level']) for a, b in zip(pre, post) if b['level'] < a['level']],
            items=[(u['who'], u['item'], u['round']) for u in battle.FIGHT_INFO.get('items') or []],
            acts=[a for a in res['actions'] if a[1] in ('spell', 'fight', 'aim', 'run', 'parry', 'use', 'dispel')],
            policy=res.get('policy'), support=res.get('support'), cm=res.get('cm'),
            oslo=g_.u8(OSLO_LEVEL),
            text=[battle._flat(x['text']) for x in g_.cap.messages[m0:]
                  if x['file'] == 'FIGHTMSG.OBJ'] if os.environ.get('TEXT') and g_.cap else None))
        print('  fight enc %d at %s: won %s wiped %s rounds %d dead %s drained %s' % (
            enc, where, won, wiped, res['rounds'], [d[0] for d in fights[-1]['deaths']],
            fights[-1]['drained']), flush=True)
        return res
    battle.fight = fight
    r = run_obj(g, st, seed, os.path.join('ch19', 'golembench', 'runs'))
    err = None
    try:
        chapter1.investigate(g)
        res = r.after()
        for _ in range(CHAIN_MOST):
            if g.overlay() == 'JOUKA' or ring_held(g):
                break
            # a fight that starts after a long quiet gap
            for _ in range(CHAIN_WAIT):
                if g.overlay() == 'BATTLE' or not maze.calm(g):
                    break
                g.step()
            if maze.calm(g) and g.overlay() != 'BATTLE':
                break
            res = r.after()
    except chapter1.Wiped:
        res = 'wiped'
    except Stuck as s:
        err = 'stuck %s %s' % (s.what, getattr(s, 'info', ''))
    except Exception as e:
        err = '%s: %s' % (type(e).__name__, e)
    finally:
        battle.fight = orig
    ring = g.overlay() != 'JOUKA' and bool(g.party()) and ring_held(g)
    evs = [m['idx'] for m in g.cap.messages[msg0:] if m['file'] == 'EVENTMES.BIN'] if g.cap else []
    return dict(state=st, seed=seed, arm=dict(oslo=bool(os.environ.get('OSLO')), stack=stack,
                                              set=os.environ.get('SET', '')),
                ring=ring, end=here(g) if g.overlay() not in ('JOUKA', 'HAZURE') else g.overlay(),
                fights=fights, won=sum(f['won'] for f in fights), events=evs, error=err,
                party=members(g) if g.overlay() not in ('JOUKA', 'HAZURE') else None)


if __name__ == '__main__':
    apply_set()
    # states made on an older disc keep its MAIN; every load lays this disc's fix words and
    # MAIN_CODE over it, as suite cases and run_chapter --from do (regress.overlay_main)
    from harness import regress
    if os.environ.get('DISC'):
        regress.SLPS = os.path.join(os.path.dirname(os.environ['DISC']), 'dimguil', 'SLPS_026.91')
    print('fix words on disc:', regress.overlay_main(), 'MAIN_CODE pieces:', len(regress.disc_main_code()),
          flush=True)
    g = Game(disc=os.environ.get('DISC') or DISC, capture=True)
    if sys.argv[1] == 'prep':
        prep(g, sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif sys.argv[1] == 'run':
        out, ss = sys.argv[2], seeds(sys.argv[3])
        for st in sys.argv[4:]:
            for s in ss:
                x = bench_one(g, st, s)
                with open(out, 'a') as f:
                    f.write(json.dumps(x, default=str) + '\n')
                print(json.dumps(dict(state=x['state'], seed=s, ring=x['ring'], won=x['won'],
                                      fights=[(f['enc'], f['won'], f['rounds']) for f in x['fights']],
                                      end=x['end'], error=x['error'])), flush=True)
