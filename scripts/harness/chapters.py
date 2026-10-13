"""Walkthrough chapters chained: chapter N starts from chapter N-1's end state.

    from harness import chapters
    r = chapters.Run(g, seed=31, variant=0, out='chapters/c1v0')
    r.run_chapters(1, 3)            # cold boot through chapter 3

Each chapter is a class with `n`, `title` and `goals(run)`, which yields (name, fn) pairs
in order; fn() returns True once its RAM proof holds (anything else, or a Stuck, reloads
the last goal state and tries again, chapter1.Run.goal). A chapter's goals are written to
be resumable: each starts from wherever the previous goal left the party (town or maze)
and skips work its proof shows already done, so a stuck case can rerun one goal from its
saved state (regress.run_stuck, by `chapter` and `goal`).

After the last goal of chapter N the run saves `<out>/c<N>_end.state`; the next chapter
(or a later run, --from) starts there. States keep the code they were saved with, so end
states only count for the disc they were made on (rips/harness/disc/BUILD.txt).
"""
import time
from harness import chapter1, maze, nav, play, town
from harness.game import Stuck

CHAPTERS = {}


def chapter(cls):
    CHAPTERS[cls.n] = cls
    return cls


class Run(chapter1.Run):
    """chapter1.Run's goal and checkpoint machinery, run chapter by chapter."""

    def __init__(self, g, **kw):
        super().__init__(g, **kw)
        self.chapter = 1
        self.chapter_results = []

    def guarded(self, fn):
        """fn, with NoTablet turned into the outcome 'no tablet' (the goal isn't reached;
        the recover goals deal with it)."""
        def run():
            try:
                return fn()
            except NoTablet:
                return 'no tablet'
        return run

    def goal(self, name, fn):
        """chapter1.Run.goal, with a progress line on stdout (runs are long)."""
        k = len(self.stuck)
        try:
            super().goal(name, self.guarded(fn))
        finally:
            for s in self.stuck[k:]:
                print('stuck c%d %s try %d: %s %s' % (self.chapter, name, s['try_'], s['what'],
                                                      s['where']), flush=True)
        x = self.goals[-1]
        print('goal c%d %s: %d frames, %.0f s, %d tries, levels %s' % (
            self.chapter, name, x['frames'], x['secs'], x['tries'], self.levels()), flush=True)

    def goal_fns(self, n):
        """{goal name: fn} for chapter n (regress.run_stuck)."""
        return {k: self.guarded(f) for k, f in CHAPTERS[n]().goals(self)}

    def run_chapter(self, n, boot=False):
        g = self.g
        self.chapter = n
        cls = CHAPTERS[n]
        t0, f0, k0, s0 = time.time(), g.frame, len(self.goals), len(self.stuck)
        if n == 1:
            # chapter 1 keeps its own loop (training trips until level 7, then the pillars)
            chapter1.Run.run(self, boot=boot)
        else:
            for name, fn in cls().goals(self):
                self.goal(name, fn)
        g.save('%s/c%d_end' % (self.out, n))
        self.ckpt = '%s/c%d_end' % (self.out, n)
        res = dict(chapter=n, title=cls.title, frames=g.frame - f0,
                   secs=round(time.time() - t0, 1), goals=self.goals[k0:],
                   stuck=self.stuck[s0:])
        self.chapter_results.append(res)
        return res

    def run_chapters(self, first, last, boot=None):
        if boot is None:
            boot = first == 1
        for n in range(first, last + 1):
            self.run_chapter(n, boot=boot and n == first)
        self.g.flush_shots()
        return self.report()

    def report(self):
        r = super().report()
        r['chapters'] = self.chapter_results
        return r

    # --- helpers for chapter 2 on ---

    policy = None             # set per chapter (play.Policy subclass)

    def on_int(self, g):
        if chapter1.party_wiped(g):
            raise chapter1.Wiped()
        r = play.handle_interrupt(g, self.policy or LaterPolicy, self.log)
        if chapter1.party_wiped(g):
            raise chapter1.Wiped()
        return r

    def after(self, g=None, quiet=chapter1.QUIET):
        g = self.g
        r = chapter1.after_event(g, self.log, quiet=quiet, policy=self.policy or LaterPolicy)
        if r == 'wiped':
            raise chapter1.Wiped()
        return r

    def ensure_maze(self):
        """In town: set out (the party arrives in camp on the Grounds) and heal up."""
        g = self.g
        if chapter1.party_wiped(g):
            raise chapter1.Wiped()
        if g.overlay() in ('JOUKA', 'HAZURE'):
            town.to_town_bar(g) if g.overlay() == 'JOUKA' else None
            town.begin_adventure(g)
            chapter1.heal_in_camp(g, self.log, frac=0.95, on_int=self.on_int)
        elif not maze.calm(g):
            self.after(quiet=30)

    def go(self, dest):
        """To dest = (area, x, y) from wherever the party is, town included. Without the
        Tablet past the Grounds there's no way in: NoTablet."""
        self.ensure_maze()
        if dest[0] != 0 and not self.has_tablet() and nav.plan(self.g, tuple(dest)) is None:
            raise NoTablet()
        return nav.travel(self.g, tuple(dest), self.on_int, lambda g: self.after())

    def has_tablet(self):
        return chapter1.TABLET in chapter1.party_items(self.g)

    def recover(self):
        """One trip for gold on the Grounds (chests opened there), home through the
        temple: the goal while the Tablet's holder waits at the temple and the gold
        won't raise them (r2v0 2026-10-13). Each trip is its own goal, so the gold it
        earns is kept in the checkpoint."""
        if self.has_tablet():
            return True
        self.train((0,))
        return True

    def recover_goals(self, most=30):
        """(name, fn) recover trips, yielded while the party has no Tablet."""
        k = 0
        while k < most and not self.has_tablet():
            k += 1
            self._recover_k = getattr(self, '_recover_k', 0) + 1
            yield 'recover_%02d' % self._recover_k, self.recover

    def trip_home(self):
        """Back to town from anywhere: temple for the dead, the Stables for points."""
        g = self.g
        if g.overlay() not in ('JOUKA', 'HAZURE'):
            nav.to_town(g, self.on_int, lambda g: self.after())
        chapter1.town_upkeep(g, self.log)
        self.note('trip home', [(g.char(i)['name'], g.char(i)['level']) for i in town.town_party(g)])

    def fit(self):
        """Before a step of the route: go home if someone is down or badly hurt with no
        healer left; else heal with Dios from camp."""
        g = self.g
        if g.overlay() in ('JOUKA', 'HAZURE'):
            return
        if chapter1.needs_town(g):
            self.trip_home()
        else:
            chapter1.heal_in_camp(g, self.log, on_int=self.on_int)

    def examine(self, dest, facing, fight=False):
        """Walk to dest, face, Investigate, run what it starts. Returns after's result.
        fight: the event ends in a fixed fight that can start long after its last box
        (the jade mask's animation runs past after()'s quiet wait; c2v6 2026-10-13), so
        wait up to FIGHT_WAIT frames for the battle and run that too."""
        g = self.g
        self.go(dest)
        if not maze.face(g, facing):
            self.after()
            maze.face(g, facing)
        self._fights0 = self.fights()
        chapter1.investigate(g)
        r = self.after()
        if fight and r == 'calm' and self.fights() == self._fights0:
            for _ in range(FIGHT_WAIT):
                if g.overlay() == 'BATTLE' or not maze.calm(g):
                    break
                g.step()
            r = self.after()
        return r

    _fights0 = 0

    def all_home(self):
        """After a fight that counts: everyone alive (a town trip raises the dead); False
        if the temple couldn't."""
        g = self.g
        if chapter1.anyone_dead(g):
            self.trip_home()
            if any(g.char(i)['status'] != 0 for i in town.town_party(g)) \
                    or len(town.town_party(g)) < 4:
                return False
        return True

    def levels(self):
        g = self.g
        return [g.char(i)['level'] for i in (g.party() or town.town_party(g))] or [0]

    def fights(self):
        return sum(1 for x in self.log if len(x) > 1 and x[1] == 'fought')

    def train(self, areas, fights=8):
        """One training trip: walk to the fight squares (95% once per visit to a floor)
        of `areas`, in random order, until `fights` fights or someone needs town; then
        home (temple, Stables: spell points and level-ups). True when everyone came home
        standing; the chapter loops trips until its level is reached."""
        g = self.g
        n0 = self.fights()
        self.fit()
        self.ensure_maze()
        if not any(nav.plan(g, (a,) + sq) is not None
                   for a in areas for sq in sorted(nav.floor(a)['fights'])[:6]):
            # the floors are out of reach (the Tablet's holder waits at the temple and
            # the gold won't raise them; r2v0 2026-10-13 ran 40 empty trips): fight on
            # the Grounds for gold until the temple can
            self.note('train on the Grounds', areas)
            areas = (0,)
        for area in areas:
            F = nav.floor(area)
            sqs = list(F['fights'])
            self.rng.shuffle(sqs)
            for sq in sqs:
                if self.fights() - n0 >= fights or chapter1.needs_town(g):
                    break
                if chapter1.hurt(g, 0.6) and chapter1.priests(g):
                    chapter1.heal_in_camp(g, self.log, on_int=self.on_int)
                if nav.plan(g, (area,) + sq) is None:
                    continue
                self.go((area,) + sq)
        self.trip_home()
        if any(g.char(i)['status'] != 0 for i in town.town_party(g)) or len(town.town_party(g)) < 4:
            return 'casualties'
        return True

    def train_goals(self, areas, level, prefix='train', most=40):
        """(name, fn) training trips, yielded lazily while min level < level (a
        chapter's goals() can `yield from` this)."""
        k = 0
        while k < most and min(self.levels()) < level:
            k += 1
            yield '%s_%02d' % (prefix, k), (lambda: self.train(areas))


FIGHT_WAIT = 2400


class NoTablet(Exception):
    """The way on needs the Tablet and nobody in the party has it."""


class LaterPolicy(play.Policy):
    """Chapter 2 on: chests opened on the Grounds (never trapped), inspected by a Thief
    or Ninja elsewhere and opened only when there's no trap, else left (battle.fight
    'auto'); event prompts answered Yes (the mask, the jewel)."""
    chest = 'auto'


@chapter
class Chapter1:
    n = 1
    title = 'The four pillars'

    def goals(self, run):
        """Chapter 1's goals for stuck cases (its run uses chapter1.Run.run)."""
        import harness.town as town
        out = [('party', run.make_party),
               ('enter', lambda: town.begin_adventure(run.g) is not None)]
        out += [('train_%02d' % k, run.train_trip) for k in range(1, 61)]
        out += [('pillar_' + nm, (lambda nm=nm, xy=xy: run.pillar(nm, xy)))
                for nm, xy in chapter1.PILLARS]
        out.append(('tablet_door', run.door))
        return out


from harness import chapter2, chapter3, chapter4, chapter5  # noqa: E402,F401  (register the chapters)
