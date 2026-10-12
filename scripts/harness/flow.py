"""The end-to-end chain: power-on -> new characters -> party -> maze -> walk -> a fight ->
back to town. Crude on purpose (Chris, 2026-10-12: get the whole chain working first,
then tune). Each leg is timed; any Stuck propagates with the leg's name added."""
import random
from harness import town, maze, battle, play
from harness.game import Stuck

# Good party: three new characters plus three of the new game's premade Good ones
NEW = [('Ace', 'Human', 'M', 'Good', 'Fighter'),
       ('Bea', 'Elf', 'F', 'Good', 'Mage'),
       ('Cy', 'Dwarf', 'M', 'Good', 'Priest')]
PREMADE_GOOD = ['Venus', 'Earth', 'Mercury']


def _leg(legs, name, fn):
    g = legs['_g']
    if legs.get('_rng'):
        g.step(legs['_rng'].randrange(0, 24))     # vary the RNG by input timing
    f0 = g.frame
    try:
        out = fn()
    except Exception as e:
        if not isinstance(e, Stuck):
            e = Stuck('%s: %s' % (type(e).__name__, e))
        e.info['leg'] = name
        e.info['legs_done'] = {k: v for k, v in legs.items() if not k.startswith('_')}
        raise e
    legs[name] = legs['_g'].frame - f0
    return out


def walk_targets(g, rng, n=6):
    """Squares reachable from here on the Grounds, a few steps off, for a random walk."""
    wm = maze.wallmap(g)
    x0, y0 = g.pos()
    out = []
    for _ in range(200):
        tx, ty = rng.randrange(1, 23), rng.randrange(1, 23)
        p = maze.bfs(wm, (x0, y0), (tx, ty), (), maze.site_closed(g.u8(maze.AREA)))
        if p and 4 <= len(p) <= 14:
            out.append((tx, ty))
            if len(out) >= n:
                break
    return out


def party_dead(g):
    """True when no one in the party can stand (status 0 = OK)."""
    return all(g.char(i)['status'] != 0 for i in g.party())


def chain(g, seed=0, boot=True, log=None):
    rng = random.Random(seed)
    legs = {'_g': g, '_rng': rng}
    fights = []
    if boot:
        g.step(rng.randrange(0, 120))
        _leg(legs, 'new_game', lambda: town.new_game(g))
    made = []
    for spec in NEW:
        name, race, sex, align, cls = spec
        r = _leg(legs, 'create_' + name, lambda: town.create_character(
            g, name, race, sex, align, cls,
            reroll_delay=lambda k: 3 + (k * 7 + seed) % 23))
        made.append(r['index'])
    names = {g.name(i): i for i in range(g.roster_count())}
    members = [names[n] for n in PREMADE_GOOD] + made
    _leg(legs, 'form_party', lambda: town.form_party(g, members))
    _leg(legs, 'begin_adventure', lambda: town.begin_adventure(g))

    def on_int(g):
        f0 = g.frame
        r = play.handle_interrupt(g, log=log)
        fights.append(g.frame - f0)
        return r

    # walk until at least one fight has happened (or the walk budget runs out)
    walked = 0
    def walk():
        nonlocal walked
        for _ in range(8):
            for t in walk_targets(g, rng, 1):
                maze.walk_to(g, t[0], t[1], on_int)
                walked += 1
            if fights:
                return
            if party_dead(g):
                return
    _leg(legs, 'walk_fight', walk)
    wiped = party_dead(g)
    if not wiped:
        _leg(legs, 'to_town', lambda: maze.to_town(g, on_int))
    legs = {k: v for k, v in legs.items() if not k.startswith('_')}
    return dict(legs=legs, fights=len(fights), walks=walked, wiped=wiped,
                frames=sum(legs.values()))
