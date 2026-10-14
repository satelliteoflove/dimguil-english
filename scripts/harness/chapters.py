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
import json, os, struct, time
from harness import battle, camp, chapter1, gear, maze, nav, play, town
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
        self.full_points = {}       # roster index -> spell points after the last Stables
        chapter1.CURE_LOG = self.log

    def guarded(self, fn):
        """fn, with NoTablet handled where it happens: Grounds trips for gold until the
        temple raises the Tablet's holder (recover), then fn again; 'no tablet' after
        RECOVER_MOST of them. (b1v1 chapter 2, 2026-10-14: Venus died in the jade mask
        goal, the temple was too poor, and the jewel goal's retries reloaded a checkpoint
        with her dead six times; the recover goals only come before some goals.)"""
        def run():
            for k in range(RECOVER_MOST + 1):
                try:
                    return fn()
                except NoTablet:
                    if k == RECOVER_MOST:
                        return 'no tablet'
                    self.note('recover in goal', getattr(self, '_goal_name', None), k + 1)
                    self.recover()
        return run

    def goal(self, name, fn):
        """chapter1.Run.goal, with a progress line on stdout (runs are long)."""
        k = len(self.stuck)
        self._goal_name = name
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
        t0, f0, k0, s0, l0 = time.time(), g.frame, len(self.goals), len(self.stuck), len(self.log)
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
                   stuck=self.stuck[s0:], spells=self.spell_summary(l0),
                   party=self.party_gear(), chests=self.chest_summary(l0),
                   loot=self.loot_summary(l0))
        self.chapter_results.append(res)
        # a line per chapter as it ends, and the log so far (result.json and log.jsonl
        # are only written when the run ends)
        d = os.path.join(chapter1.OUT, self.out)
        with open(os.path.join(d, 'chapters.jsonl'), 'a') as f:
            f.write(json.dumps({k: v for k, v in res.items() if k != 'goals'}, default=str) + '\n')
        with open(os.path.join(d, 'log_c%d.jsonl' % n), 'w') as f:
            for x in self.log[l0:]:
                f.write(json.dumps(x, default=str) + '\n')
        return res

    def party_gear(self):
        """Each member's level, AC (+0x86), HP, gold and what's worn, by slot (Chris,
        2026-10-14: does the gear keep up with what a player would have)."""
        g = self.g
        out = []
        names = ['main', 'off', 'armor', 'helm', 'gloves', 'boots', 'other']
        for ri in (g.party() or town.town_party(g)):
            c = g.char(ri)
            on = gear.equipped(g, ri)
            out.append(dict(name=c['name'], cls=c['cls'], level=c['level'],
                            ac=struct.unpack('b', c['raw'][0x86:0x87])[0], hp=c['max_hp'],
                            gold=c['gold'], status=c['status'],
                            gear={names[s]: gear.name(it['id']) for s, it in sorted(on.items())},
                            pack=[gear.name(w & 0x1ff) + ('' if w & gear.IDENT else '?')
                                  for k, w in gear.pack(g, ri) if not w & gear.EQUIPPED]))
        return out

    def chest_summary(self, l0=0):
        """The chapter's chests: how each ended, traps met, and what came out."""
        chests = [x[2].get('chest') for x in self.log[l0:] if len(x) > 2 and x[1] == 'fought'
                  and isinstance(x[2], dict) and x[2].get('chest')]
        res, traps, loot = {}, {}, []
        for c in chests:
            if isinstance(c, dict):
                r = c.get('result') or '?'
                k = r.split(' (')[0].split(' trap')[0]
                res[k] = res.get(k, 0) + 1
                if c.get('trap'):
                    traps[c['trap']] = traps.get(c['trap'], 0) + 1
                loot += [t for t in c.get('loot', []) if 'obtains' in t]
            else:
                res[str(c)] = res.get(str(c), 0) + 1
        return dict(chests=len(chests), results=res, traps=traps, items=loot)

    def loot_summary(self, l0=0):
        """Identifying (camp and shop), gives, sales and buys in the chapter."""
        out = {}
        for x in self.log[l0:]:
            if len(x) > 1 and x[1] in ('identify camp', 'identify', 'give', 'sell', 'buy', 'uncurse', 'equip'):
                out.setdefault(x[1], []).append(x[2:])
        return out

    def spell_summary(self, l0=0):
        """The chapter's fights and casts (by spell level, and in fights that matter or
        not) and its trips (why each ended, and the lowest share of points at levels 3-7
        a caster came home with), from the log since entry l0."""
        fights = [x[2] for x in self.log[l0:] if len(x) > 2 and x[1] == 'fought' and isinstance(x[2], dict)]
        by_level = {}
        for f in fights:
            for name, sid, sch, lv in f.get('casts', []):
                k = '%s L%d %s' % ('MPAS'[sch], lv, 'matters' if f.get('matters') else 'trash')
                by_level[k] = by_level.get(k, 0) + 1
        trips = [x[2] for x in self.log[l0:] if len(x) > 2 and x[1] == 'trip end']
        reasons, low = {}, []
        for t in trips:
            reasons[t['reason']] = reasons.get(t['reason'], 0) + 1
            for name, per in t['points'].items():
                n = f = 0
                for a, b in per.values():
                    if b:
                        n += sum(a[2:]); f += sum(b[2:])
                if f >= 4:
                    low.append(round(n / f, 2))
        return dict(fights=len(fights), matters=sum(1 for f in fights if f.get('matters')),
                    casts=sum(len(f.get('casts', [])) for f in fights), casts_by=by_level,
                    trips=len(trips), trip_reasons=reasons,
                    points_home_min=min(low) if low else None,
                    points_home_median=sorted(low)[len(low) // 2] if low else None)

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
            if chapter1.GEAR:
                gear.camp_loot(g, self.log, on_int=self.on_int)
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

    def trip_end(self, reason=None):
        """Log the end of a trip (Chris, 2026-10-14): why it ended and each caster's points
        by school and level against what they had after the last Stables."""
        g = self.g
        if reason is None:
            reason = ('down' if chapter1.out_of_action(g) else
                      'HP' if chapter1.hurt(g, 0.5) and not chapter1.priests(g) else 'other')
        pts = {}
        for i in g.party():
            c = g.char(i)
            now, full = list(c['raw'][0x5c:0x78]), self.full_points.get(i)
            per = {}
            for sch in range(4):
                a = now[sch * 7:sch * 7 + 7]
                b = full[sch * 7:sch * 7 + 7] if full else None
                if any(a) or b and any(b):
                    per['MPAS'[sch]] = [a, b]
            if per:
                pts[c['name']] = per
        self.note('trip end', dict(reason=reason, fights=self.fights() - getattr(self, '_trip_f0', 0),
                                   points=pts))

    def trip_home(self, reason=None):
        """Back to town from anywhere: temple for the dead, the Stables for points."""
        g = self.g
        if g.overlay() not in ('JOUKA', 'HAZURE'):
            self.trip_end(reason)
            if chapter1.GEAR and not chapter1.party_wiped(g):
                gear.camp_loot(g, self.log, on_int=self.on_int)
            nav.to_town(g, self.on_int, lambda g: self.after())
        chapter1.town_upkeep(g, self.log)
        for i in town.town_party(g):
            self.full_points[i] = list(g.char(i)['raw'][0x5c:0x78])
        self._trip_f0 = self.fights()
        self.note('trip home', [(g.char(i)['name'], g.char(i)['level']) for i in town.town_party(g)])

    def points_low(self, share=None):
        """Casters whose spell points at levels 3-7 are under `share` of what they had
        after the last Stables (none known yet: not low)."""
        g = self.g
        share = share or POINTS_READY
        low = []
        for i in g.party():
            full = self.full_points.get(i)
            if not full:
                continue
            now = g.char(i)['raw'][0x5c:0x78]
            f = sum(full[s * 7 + l] for s in range(4) for l in range(2, 7))
            n = sum(now[s * 7 + l] for s in range(4) for l in range(2, 7))
            if f >= 4 and n < f * share:
                low.append((g.char(i)['name'], n, f))
        return low

    def maporfic(self):
        """Maporfic from camp before a boss (B-camp.md: party AC -2 for 1250 steps,
        0x8007e82a), if a priest knows it and it isn't running."""
        g = self.g
        if g.u8(0x8007e82a):
            return
        for slot, ri in enumerate(g.party_slots()):
            if ri is None:
                continue
            c = g.char(ri)
            ks = battle.known_spells(c['raw'], 1, 4)
            if c['status'] < 0x20 and 32 in ks and c['raw'][0x5c + 7 + 3]:
                try:
                    camp.cast(g, slot, 1, 4, ks.index(32))
                    self.note('maporfic', c['name'], g.u8(0x8007e82a))
                except Stuck as s:
                    self.note('maporfic stuck', s.what)
                if camp.in_camp(g):
                    camp.close_camp(g)
                return

    def fit(self):
        """Before a step of the route: go home if someone is down or badly hurt with no
        healer left; else heal with Dios from camp."""
        g = self.g
        if g.overlay() in ('JOUKA', 'HAZURE'):
            return
        if chapter1.needs_town(g):
            self.trip_home()
        else:
            if chapter1.GEAR and gear.loot_work(g):
                # something to identify, pass on or put on
                gear.camp_loot(g, self.log, on_int=self.on_int)
            chapter1.heal_in_camp(g, self.log, on_int=self.on_int)

    def ready(self, home_below=None):
        """Before a boss: home if anyone is dead or under home_below of max HP once the
        priests have healed what they can (the Cots heal everyone to full there), else
        heal to READY_HP from camp."""
        g = self.g
        home_below = home_below or READY_HOME
        self.boss_training()
        self.fit()
        if g.overlay() in ('JOUKA', 'HAZURE'):
            return
        if chapter1.anyone_dead(g):
            chapter1.cure_in_camp(g, self.log, on_int=self.on_int)
        self.heal()
        low = self.points_low()
        if low:
            # the casters spent their points on the way: a Stables trip first, as for HP
            # (Chris, 2026-10-14)
            self.note('points low before a boss', low)
        if chapter1.out_of_action(g) or chapter1.hurt(g, home_below) or low:
            keep = chapter1.COT_BELOW
            chapter1.COT_BELOW = READY_HP
            try:
                self.trip_home('points before a boss' if low and not chapter1.out_of_action(g)
                               and not chapter1.hurt(g, home_below) else
                               'down before a boss' if chapter1.out_of_action(g) else 'HP before a boss')
            finally:
                chapter1.COT_BELOW = keep

    def boss_wipes(self):
        """Tries of the goal under way that ended in a wipe or casualties."""
        name = getattr(self, '_goal_name', None)
        return sum(1 for x in self.log if len(x) > 3 and x[1] == 'retry' and x[2] == name
                   and x[3] in ('wiped', 'casualties'))

    def boss_training(self):
        """The training targets are set low and measured (Chris, 2026-10-14: a geared party
        needn't grind like the starting-gear one did): after BOSS_WIPES failed tries at a
        goal, each further try trains one level more first, on the chapter's training
        floors, and the run's log says so."""
        w = self.boss_wipes()
        if w < BOSS_WIPES:
            return
        import sys
        mod = sys.modules.get('harness.chapter%d' % self.chapter)
        areas = getattr(mod, 'TRAIN_AREAS', None)
        if not areas:
            return
        want = self.party_level() + w - BOSS_WIPES + 1
        self.note('boss training', getattr(self, '_goal_name', None), self.party_level(), want)
        print('c%d %s: %d failed tries, training to %d' % (self.chapter, self._goal_name, w, want),
              flush=True)
        for _ in range(12):
            if self.party_level() >= want:
                break
            self.train(areas)
        self.ensure_maze()

    def heal(self, frac=None):
        """Heal to frac (READY_HP) from camp, where the party stands."""
        if self.g.overlay() not in ('JOUKA', 'HAZURE'):
            try:
                chapter1.heal_strong(self.g, self.log, frac or READY_HP, on_int=self.on_int)
                # heal() comes just before a boss: the party's AC too (Chris, 2026-10-14)
                self.maporfic()
            except Stuck as s:
                # the camp won't open everywhere: just after the stream parts the screen
                # stays black until the party steps on (f1v3e, 2026-10-13)
                self.note('heal stuck', s.what)

    def examine(self, dest, facing, fight=False):
        """Walk to dest, face, Investigate, run what it starts. Returns after's result.
        fight: the event ends in a fixed fight that can start long after its last box
        (the jade mask's animation runs past after()'s quiet wait; c2v6 2026-10-13), so
        wait up to FIGHT_WAIT frames for the battle and run that too."""
        g = self.g
        for _ in range(3):
            self.go(dest)
            if not maze.face(g, facing):
                self.after()
            if (g.u8(maze.AREA),) + g.pos() == tuple(dest):
                maze.face(g, facing)
                if (g.u8(maze.AREA),) + g.pos() == tuple(dest):
                    break
        self._fights0 = self.fights()
        for _ in range(3):
            # a roamer met on the square can take the Investigate's place: its fight runs
            # and the event never does (r2v6b chapter 2, 2026-10-13: Xecotcovachs at 4F
            # (14, 16), then "jade_mask False" six times). No event text: look again.
            n = len(g.cap.messages) if g.cap else 0
            f1 = self.fights()
            chapter1.investigate(g)
            r = self.after()
            said = not g.cap or any(m['file'] == 'EVENTMES.BIN' for m in g.cap.messages[n:])
            if said or self.fights() == f1 or (g.u8(maze.AREA),) + g.pos() != tuple(dest):
                break
            self._fights0 = self.fights()
            if not maze.face(g, facing):
                self.after()
                maze.face(g, facing)
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
        # the members setting out: a trip that leaves one of them at the temple doesn't
        # count, and the goal's retry reloads (q8v7-q8v9 chapter 8, 2026-10-13: trips that
        # passed with two level-14s dead and level-5 recruits in their places, the gold
        # gone to the temple with the dead, and the party wore down trip by trip)
        setting_out = [i for i in g.party() if g.char(i)['status'] == 0]
        battle.RUN_WHEN_LOSING = True
        why = 'squares done'
        try:
            for area in areas:
                F = nav.floor(area)
                sqs = list(F['fights'])
                self.rng.shuffle(sqs)
                for sq in sqs:
                    if self.fights() - n0 >= fights:
                        why = 'fight count'
                        break
                    if chapter1.needs_town(g) and self.town_helps():
                        why = None
                        break
                    if chapter1.hurt(g, 0.6) and chapter1.priests(g):
                        chapter1.heal_in_camp(g, self.log, on_int=self.on_int)
                    if nav.plan(g, (area,) + sq) is None:
                        continue
                    self.go((area,) + sq)
                else:
                    why = 'squares done'
            self.trip_home(why)
        finally:
            battle.RUN_WHEN_LOSING = False
        if any(g.char(i)['status'] != 0 for i in town.town_party(g)) or len(town.town_party(g)) < 4:
            return 'casualties'
        if areas != (0,) and any(i not in town.town_party(g) for i in setting_out):
            self.note('left at the temple', [g.char(i)['name'] for i in setting_out
                                             if i not in town.town_party(g)])
            return 'casualties'
        return True

    def train_goals(self, areas, level, prefix='train', most=40):
        """(name, fn) training trips, yielded lazily while min level < level (a
        chapter's goals() can `yield from` this)."""
        k = 0
        while k < most and self.party_level() < level:
            k += 1
            yield '%s_%02d' % (prefix, k), (lambda: self.train(areas))

    def town_helps(self):
        """Whether a trip home can do anything: with under TOWN_GOLD in the party the
        temple and the Cots turn everyone away, and a hurt party with no healer's points
        went home and straight back out thirty times running (f1v1d chapter 2,
        2026-10-13: 2,600-frame recover trips, no fights). Then it fights on for gold."""
        g = self.g
        gold = sum(g.char(i)['gold'] for i in (g.party() or town.town_party(g)))
        return gold >= TOWN_GOLD

    def party_level(self):
        """The median member's level: a recruit taken on at level 5 or 6 held the minimum
        down for dozens of trips (f1v6b chapter 4, 2026-10-13: [6, 11, 7, 12, 12, 12])."""
        lv = sorted(self.levels())
        return lv[len(lv) // 2]


RECOVER_MOST = 30           # Grounds trips for the Tablet's holder inside one goal
BOSS_WIPES = 2              # failed tries at a goal before each further try trains a level
FIGHT_WAIT = 2400
READY_HP = 0.9              # a boss fight starts with everyone at this share of max HP
READY_HOME = 0.7            # ... or the party goes home first if healing can't reach this
POINTS_READY = 0.6          # ... or the casters' points at levels 3-7 are under this share
TOWN_GOLD = 100             # party gold under which a trip home can't buy anything


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


from harness import chapter2, chapter3, chapter4, chapter5, chapter6, chapter7, chapter8, chapter9  # noqa: E402,F401  (register the chapters)
