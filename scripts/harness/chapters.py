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
import collections, json, os, struct, time
from harness import battle, camp, chapter1, gear, maze, nav, play, tactics, town
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
        self._floors = {}           # training floor ladder index by the chapter's TRAIN_AREAS
        self._pull = {}             # pulled-back training areas: area -> easier area, level, log index
        self._since = {}            # area -> log index of the last return to it (its window starts there)
        self._ch_l0 = 0             # log index where the chapter began
        self.resume_memory = None   # memory_path's side file of the --from state (agent 14)
        chapter1.CURE_LOG = self.log

    def checkpoint(self, name):
        """chapter1.Run.checkpoint, plus side files a run resumed from the goal state reads
        (agent 14): the casters' points (save_points) and the chapter's memory (save_memory)."""
        super().checkpoint(name)
        save_points(self.g, self.ckpt, self.full_points)
        save_memory(self, self.ckpt)

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
            battle.BOSS_KEEP.clear()
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
        self._ch_l0, self._pull, self._since = l0, {}, {}
        m, self.resume_memory = self.resume_memory, None
        if m and m.get('chapter') == n:
            # resumed mid-chapter (agent 14): the chapter's log so far, pull-backs and
            # returns, as the goal state's run left them; this run's trend starts after them
            self.log.extend(tuple(x) for x in m['log'])
            self._pull = {tuple(k): dict(v, to=tuple(v['to']), at=l0 + v['at']) for k, v in m['pull']}
            self._since = {tuple(k): l0 + v for k, v in m['since']}
            l0 = len(self.log)
            print('memory c%d: %d log lines, pulls %s' % (n, len(m['log']), sorted(self._pull)), flush=True)
        gold0 = chapter1.party_gold(g)
        if n == 1:
            # chapter 1 keeps its own loop (training trips until level 7, then the pillars)
            chapter1.Run.run(self, boot=boot)
        else:
            for name, fn in cls().goals(self):
                self.goal(name, fn)
        g.save('%s/c%d_end' % (self.out, n))
        self.ckpt = '%s/c%d_end' % (self.out, n)
        save_points(g, self.ckpt, self.full_points)
        res = dict(chapter=n, title=cls.title, frames=g.frame - f0,
                   secs=round(time.time() - t0, 1), goals=self.goals[k0:],
                   stuck=self.stuck[s0:], spells=self.spell_summary(l0),
                   party=self.party_gear(), chests=self.chest_summary(l0),
                   loot=self.loot_summary(l0), gold=self.gold_summary(l0, gold0))
        res['trend'] = self.trend_summary(l0, res)
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

    def trend_summary(self, l0, res):
        """The numbers Chris tabulates per chapter (2026-10-14): frames, training trips,
        fights, deaths and members down per 100 fights, raises and ashes, gold at the end,
        the party's levels and average AC, stuck count."""
        fights = dead = down = 0
        prev_dead, prev_down = set(), set()
        temple = collections.Counter()
        trips = 0
        uncurse = [0, 0]            # Boltac's uncurse fees after the Bishop's risky tries
        items = collections.Counter()   # battle items: used up, broke, kept (battle.item_choice)
        pulls = collections.Counter()   # agent 11: pull-backs and returns (pull_areas)
        dcat = collections.Counter()    # agent 11: deaths by category (tag_deaths)
        for x in self.log[l0:]:
            if len(x) < 2:
                continue
            if x[1] in ('pull back', 'pull return'):
                pulls[x[1]] += 1
            if x[1] == 'death' and len(x) > 2 and isinstance(x[2], dict):
                dcat[x[2].get('cat')] += 1
            if x[1] == 'uncurse' and len(x) > 5 and x[5] == 'done':
                uncurse[0] += 1
                uncurse[1] += x[4]
            if x[1] in ('temple', 'rejoined', 'trip home', 'stables'):
                prev_dead, prev_down = set(), set()
            if x[1] == 'temple' and len(x) > 3 and isinstance(x[3], dict):
                temple[x[3].get('outcome')] += 1
            if x[1] == 'trip end':
                trips += 1
            if x[1] == 'fought' and len(x) > 2 and isinstance(x[2], dict):
                fights += 1
                for u in x[2].get('items') or []:
                    items[u.get('result')] += 1
                d, w = set(x[2].get('dead_end', [])), set(x[2].get('down_end', []))
                dead += len(d - prev_dead)
                down += len(w - prev_down)
                prev_dead, prev_down = d, w
        party = res['party']
        return dict(frames=res['frames'], trips=trips,
                    train_goals=sum(1 for gl in res['goals'] if 'train' in str(gl)),
                    fights=fights, deaths=dead, downs=down,
                    deaths_per_100=round(100 * dead / fights, 1) if fights else None,
                    downs_per_100=round(100 * down / fights, 1) if fights else None,
                    raises=temple.get('alive', 0), ashes=temple.get('ashes', 0), lost=temple.get('lost', 0),
                    gold_end=sum(q['gold'] for q in party), levels=[q['level'] for q in party],
                    avg_ac=round(sum(q['ac'] for q in party) / len(party), 1) if party else None,
                    uncursed=uncurse[0], uncurse_gold=uncurse[1],
                    items_used=items['used'] + items['gone'], items_broke=items['broke'], items_kept=items['kept'],
                    pull_backs=pulls['pull back'], pull_returns=pulls['pull return'],
                    death_cats=dict(dcat),
                    stuck=len(res['stuck']), foundation=self.foundation())

    def foundation(self):
        """Chris's chapter-end check (2026-10-14): AC by row (party slots 0-2 front, 3-5
        back), unknowns still carried, identified upgrades left in a pack (gear.wants_equip),
        and in-stock shop items that beat what a member wears and the party could afford
        (gear.better), best gain first."""
        g = self.g
        slots = g.party_slots() if g.party() else [ri for ri in town.town_party(g)]
        ac = lambda ri: struct.unpack('b', g.char(ri)['raw'][0x86:0x87])[0]
        rows = [[ac(ri) for ri in slots[a:b] if ri is not None] for a, b in ((0, 3), (3, 6))]
        party = [ri for ri in slots if ri is not None]
        gold = sum(g.char(ri)['gold'] for ri in party)
        offers = []
        for ri in party:
            on = gear.equipped(g, ri)
            for sl in range(7):
                for i in range(1, gear.SHOP_LAST + 1):
                    if not g.u8(gear.STOCK + i):
                        continue
                    it = gear.item(g, i)
                    if it['price'] and it['price'] <= gold and gear.better(g, ri, it, sl, on.get(sl)):
                        gain = gear.score(it, sl) - (gear.score(on[sl], sl) if on.get(sl) else 0)
                        if gain > 0:
                            offers.append((round(gain, 1), it['price'], g.char(ri)['name'], gear.name(i)))
        offers.sort(reverse=True)
        return dict(ac_front=rows[0], ac_back=rows[1],
                    unknowns=sum(len(gear.unknowns(g, ri)) for ri in party),
                    upgrades_in_packs=[g.char(ri)['name'] for ri in party if gear.wants_equip(g, ri)],
                    shop_upgrades=len(offers), best_offers=offers[:5])

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

    def gold_summary(self, l0=0, start=None):
        """The chapter's gold: at the start and end, what the temple, the inn and the shop
        took (shop: sales less buys and fees), and what came home from the maze (each
        arrival in town against the gold the party left with). Sums over goals that
        counted and retries that were reloaded alike, so a reload shows as a gap."""
        g = self.g
        spent, income, last = {}, 0, start
        for x in self.log[l0:]:
            if len(x) > 5 and x[1] == 'gold':
                what, ch, now = x[2], x[3], x[4]
                if what == 'arrive':
                    if last is not None and now > last:
                        income += now - last
                elif ch is not None:
                    spent[what] = spent.get(what, 0) + ch
                last = now
        return dict(start=start, end=chapter1.party_gold(g),
                    roster_end=sum(g.char(i)['gold'] for i in range(g.roster_count())),
                    town=spent, maze_income=income)

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
        n = self.fights()
        dead0 = {i for i in g.party() if g.char(i)['status'] & HOME_DEAD}
        l1 = len(self.log)
        r = play.handle_interrupt(g, self.policy or LaterPolicy, self.log)
        self.tag_deaths(l1)
        if chapter1.party_wiped(g):
            raise chapter1.Wiped()
        if AVOID_FATAL and tactics.TRAINING and self.fights() > n:
            # a fixed fight that killed a member: the walk home keeps off its square
            f = next((x[2] for x in reversed(self.log) if len(x) > 2 and x[1] == 'fought'), None)
            if f and f.get('story') and f.get('where') and \
                    {i for i in g.party() if g.char(i)['status'] & HOME_DEAD} - dead0:
                self._fatal = getattr(self, '_fatal', set()) | {tuple(f['where'])}
        if getattr(self, '_homeward', False) and self.fights() > n:
            battle.RUN_OK = self.homeward_run()
        if HP_HEAL and tactics.TRAINING and self.fights() > n and not getattr(self, '_topping', False) \
                and g.overlay() not in ('JOUKA', 'HAZURE', 'BATTLE'):
            # Chris's HP lines after every training fight, the walk home included
            self._topping = True
            try:
                if chapter1.GEAR and LOOT_EACH_FIGHT and gear.loot_work(g):
                    # the chest's loot straight away (main, 2026-10-14): the Bishop's safe
                    # tries, gives and equipping, so the party fights the rest of the trip
                    # in it (risky tries stay for the setting-out camp)
                    gear.camp_loot(g, self.log, on_int=self.on_int)
                # (healspots) on the walk out, a heal spot nearer than home heals for free:
                # no spells, the train loop walks there (ToSpot)
                spot = HEAL_SPOT and getattr(self, '_walking_out', False) and self.spot_choice()
                critical = [] if spot else self.hp_heal()
            finally:
                self._topping = False
            if spot:
                raise ToSpot(spot)
            if critical and getattr(self, '_walking_out', False):
                raise TurnHome(critical)
        if HEALER_HOME and (getattr(self, '_walking_out', False) or getattr(self, '_goal_walk', False)) \
                and not getattr(self, '_homeward', False) and not getattr(self, '_gold', False) \
                and g.overlay() not in ('JOUKA', 'HAZURE', 'BATTLE') and self.healers_down():
            # (agent 16) a healer down on the walk out or a goal walk turns the party home, once
            # the party's own cures have had their try (n1v0r chapter 10: Earth died in the
            # red stone's fight and the walk on met a Were Centipede pack with no healer)
            chapter1.cure_in_camp(g, self.log, on_int=self.on_int)
            down = self.healers_down()
            if down and self.town_helps():
                raise TurnHome('healer down: ' + ', '.join(down))
        if ROAMER_DOOR and getattr(self, '_goal_walk', False) and self.fights() > n \
                and g.overlay() not in ('JOUKA', 'HAZURE', 'BATTLE'):
            areas = (g_area(g), getattr(self, '_dest', (None,))[0])
            if self.roamer_short(areas) and not getattr(self, '_topping', False):
                self._topping = True
                try:
                    self.hp_heal()
                finally:
                    self._topping = False
                short = self.roamer_short(areas)
                if short and self.town_helps():
                    raise TurnHome('short for roamers: %s' % (short,))
        if TOPUP and tactics.TRAINING and self.fights() > n and not getattr(self, '_topping', False) \
                and g.overlay() not in ('JOUKA', 'HAZURE', 'BATTLE'):
            # heal up after each training fight, not only at the next fight square: the
            # roamers met between squares came one after another (smoke2: Mercury at 14
            # of 68 HP into Area B's human party)
            self._topping = True
            try:
                if self.top_up():
                    self._heals_out = True
            finally:
                self._topping = False
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
                self.set_out_loot()
            chapter1.heal_in_camp(g, self.log, frac=0.95, on_int=self.on_int)
        elif not maze.calm(g):
            self.after(quiet=30)

    def set_out_loot(self, most=2):
        """The setting-out camp on the Grounds: the Bishop's risky tries too (gear.RISKY).
        Anyone left afraid or wearing a cursed item: back into town (fear clears there,
        Boltac's uncurses) and out again, at most `most` times, then a safe-only camp."""
        g = self.g
        if gear.EDGE_ID:
            # the risky tries happen at the Edge of Town now (gear.edge_identify, no fear)
            gear.camp_loot(g, self.log, on_int=self.on_int)
            return
        for _ in range(most):
            gear.RISKY = True
            try:
                gear.camp_loot(g, self.log, on_int=self.on_int)
            finally:
                gear.RISKY = False
            hit = gear.fallout(g)
            if not hit or g.overlay() in ('JOUKA', 'HAZURE', 'BATTLE'):
                return
            self.note('identify fallout', hit)
            nav.to_town(g, self.on_int, lambda g: self.after())
            chapter1.town_upkeep(g, self.log)
            for i in town.town_party(g):
                self.full_points[i] = list(g.char(i)['raw'][0x5c:0x78])
            town.begin_adventure(g)
        gear.camp_loot(g, self.log, on_int=self.on_int)

    def go(self, dest):
        """To dest = (area, x, y) from wherever the party is, town included. Without the
        Tablet past the Grounds there's no way in: NoTablet. A goal's walk (not training)
        that loses a healer goes home and walks again, HEALER_TRIPS times at most."""
        self.ensure_maze()
        if dest[0] != 0 and not self.has_tablet() and nav.plan(self.g, tuple(dest)) is None:
            raise NoTablet()
        if tactics.TRAINING or getattr(self, '_goal_walk', False):
            # a training walk to its own floors stays on them once there (train's _keep)
            keep = getattr(self, '_keep', None) if tactics.TRAINING else None
            if keep and (dest[0] not in keep or nav.plan(self.g, tuple(dest), keep=keep) is None):
                keep = None
            return nav.travel(self.g, tuple(dest), self.on_int, lambda g: self.after(), keep=keep)
        for k in range(HEALER_TRIPS + 1):
            self._goal_walk = k < HEALER_TRIPS
            self._dest = tuple(dest)
            short = self._goal_walk and self.roamer_short((g_area(self.g), dest[0]))
            if short and self.town_helps():
                # (agent 16) the roamers' door: short for the type-2 parties on the way
                self._goal_walk = False
                self.note('roamer door', short)
                self.trip_home('short for roamers')
                self.ensure_maze()
                continue
            try:
                return nav.travel(self.g, tuple(dest), self.on_int, lambda g: self.after())
            except TurnHome as t:
                self._goal_walk = False         # the walk home itself doesn't turn
                self.note('turn home', t.args[0])
                self.trip_home('healer down')
                self.ensure_maze()
            finally:
                self._goal_walk = False

    def roamer_short(self, areas, hp_only=False):
        """What the party lacks for the type-2 parties (roamer tokens, A-maze.md "Tokens")
        on the floors `areas`, or []: they are met anywhere on the floor, so a square can't
        be avoided (main, 2026-10-14). Against the worst one's rated threat a round
        (TYPE2_THREAT): the standing members' HP under TYPE2_ROUNDS rounds of it, and,
        unless hp_only, a member down or the heals short (boss_short's 'down' and 'heals')."""
        g = self.g
        T = max([TYPE2_THREAT.get(a, 0) for a in areas if a is not None and 0 <= a < 0x40
                 and g.u8(TYPE2_TOKENS + a * 2 + 1)] or [0])
        if not ROAMER_DOOR or not T or not maze.in_maze(g):
            return []
        hp = sum(max(0, g.char(i)['hp']) for i in g.party() if g.char(i)['status'] < 0x20)
        short = [('hp', hp, TYPE2_ROUNDS * T)] if hp < TYPE2_ROUNDS * T else []
        if not hp_only:
            short += [x for x in self.boss_short() if x == 'down' or x[0] == 'heals']
        return short

    def healers_down(self):
        """Names of the members who know a Priest heal (tactics.HEALS) and are out of
        action (chapter1.SERIOUS)."""
        g = self.g
        out = []
        for i in g.party():
            c = g.char(i)
            if c['status'] & chapter1.SERIOUS and any(
                    h in tactics.HEALS for lv in range(1, 8) for h in battle.known_spells(c['raw'], 1, lv)):
                out.append(c['name'])
        return out

    def cleo_why(self):
        """(revision 9, Chris) Why the walk home should go by Cresson's party for a free
        raise, or None: a member is dead or ashed, the detour is at most CLEO_DETOUR steps
        over the walk home (nav.cost), and the temple's expected fee (E-town.md: level x 250
        dead, 500 ashes; a failed raise turns the dead to ashes, 60 + 2 x VIT of 100 works)
        is more than the party's gold, or CLEO_GOLD_SHARE of it or more."""
        g = self.g
        dead = [g.char(i) for i in g.party()]
        dead = [c for c in dead if c['status'] & 0x180 and not c['status'] & 0x200]
        if not dead or not self.has_tablet() or not maze.in_maze(g):
            return None
        if self.roamer_short((g_area(g),), hp_only=True):
            # (agent 16) not deeper among the type-2 parties with the HP short (n1v1r chapter
            # 10: the detour took Earth alone, 134 HP, to a GremlinMother party at (25,4,17))
            return None
        home = (0,) + maze.ENTRANCE[0]
        a, b, c = nav.cost(g, home), nav.cost(g, CLEO), nav.cost(g, home, start=CLEO)
        if None in (a, b, c) or b + c - a > CLEO_DETOUR:
            return None
        fee = 0.0
        for ch in dead:
            L, vit = ch['level'], ch['stats'][3]
            fee += L * 500 if ch['status'] & 0x100 else L * 250 + (1 - min(1, (60 + 2 * vit) / 100)) * L * 500
        gold = sum(g.char(i)['gold'] for i in g.party())
        why = ('fee %d over gold %d' % (fee, gold) if fee > gold else
               'fee %d of gold %d' % (fee, gold) if fee >= CLEO_GOLD_SHARE * gold else None)
        return why and '%s, detour %d steps' % (why, b + c - a)

    def cleo_raise(self):
        """Walk to Cresson's party (CLEO) and Talk until Cleo or Bergamot raises the dead
        (play.talk mode 'raise'), when cleo_why says so. The meeting square's token is
        spent once met, until the party next arrives on the floor."""
        g = self.g
        why = self.cleo_why()
        if not why:
            return
        names = [g.char(i)['name'] for i in g.party() if g.char(i)['status'] & 0x180]
        f0, policy = g.frame, self.policy
        self.note('cleo', why, names)
        print('c%d cleo: %s %s' % (self.chapter, names, why), flush=True)
        self.policy = type('RaisePolicy', (policy or LaterPolicy,), dict(talk='raise'))
        try:
            nav.travel(g, CLEO, self.on_int, lambda g: self.after())
            for _ in range(600):            # the meeting starts some frames after the step
                if g.u8(maze.GAME_STATE) == play.TALK:
                    break
                g.step()
            if g.u8(maze.GAME_STATE) == play.TALK:
                self.on_int(g)
        finally:
            self.policy = policy
        left = [g.char(i)['name'] for i in g.party() if g.char(i)['status'] & 0x180]
        self.note('cleo done', dict(raised=[n for n in names if n not in left], left=left,
                                    talks=play.TALKS[0], frames=g.frame - f0))
        print('c%d cleo done: raised %s, %d talks, %d frames' % (
            self.chapter, [n for n in names if n not in left], play.TALKS[0], g.frame - f0), flush=True)

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
            self._homeward = tactics.TRAINING
            battle.RUN_OK = self._homeward and self.homeward_run()
            for a, x, y in getattr(self, '_fatal', ()):
                nav.TRIP_SOFT.setdefault(a, set()).add((x, y))
            try:
                if HOME_HEAL:
                    self.home_heal()
                if CLEO_RAISE:
                    self.cleo_raise()
                nav.to_town(g, self.on_int, lambda g: self.after())
            finally:
                self._homeward = False
                battle.RUN_OK = False
                nav.TRIP_SOFT.clear()
                self._fatal = set()
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
                # a caster whose points after the Stables aren't known (a run resumed from
                # a state without its points file): count as low, one Stables trip learns
                # them (n1v3i chapter 7, agent 8: the first trip after a resume left with
                # Earth at Priest points 0/2/4 and two died in a 16-round fight)
                if any(g.char(i)['raw'][0x4c:0x5c]) and g.char(i)['status'] < 0x20:
                    low.append((g.char(i)['name'], None, None))
                continue
            now = g.char(i)['raw'][0x5c:0x78]
            f = sum(full[s * 7 + l] for s in range(4) for l in range(2, 7))
            n = sum(now[s * 7 + l] for s in range(4) for l in range(2, 7))
            if f >= 4 and n < f * share:
                low.append((g.char(i)['name'], n, f))
        return low

    def points_spent(self, share=None):
        """Strategy revision 3 (Gaiden advice): a training trip heads home before the next
        square once the casters' points at levels 3-7 are under `share` of what they had
        after the last Stables, summed over the party, or the heals are (HEAL_OPTS points,
        each counted at its mean HP up to 40). Returns the shares when it's time, else None.
        Unknown full points (a resumed run) don't count here; points_low handles those."""
        g = self.g
        share = share or POINTS_HOME
        n = f = hn = hf = 0
        for i in g.party():
            full = self.full_points.get(i)
            if not full or g.char(i)['status'] >= 0x20:
                continue
            now = g.char(i)['raw'][0x5c:0x78]
            for sc in range(4):
                for lv in range(2, 7):
                    n += now[sc * 7 + lv]; f += full[sc * 7 + lv]
            for sid, sc, lv, mean in HEAL_OPTS:
                w = min(mean, 40)
                hn += now[sc * 7 + lv - 1] * w; hf += full[sc * 7 + lv - 1] * w
        out = dict(points=round(n / f, 2) if f >= 4 else None, heals=round(hn / hf, 2) if hf >= 40 else None)
        if any(v is not None and v < share for v in out.values()):
            self.note('points spent', out)
            return out
        return None

    def maporfic(self, keep=0):
        """Maporfic from camp before a boss (B-camp.md: party AC -2 for 1250 steps,
        0x8007e82a), if a priest knows it and it isn't running. keep: Priest level 4
        points the caster holds back (Dial is level 4 too)."""
        g = self.g
        if g.u8(0x8007e82a):
            return
        for slot, ri in enumerate(g.party_slots()):
            if ri is None:
                continue
            c = g.char(ri)
            ks = battle.known_spells(c['raw'], 1, 4)
            if c['status'] < 0x20 and 32 in ks and c['raw'][0x5c + 7 + 3] > keep:
                try:
                    camp.cast(g, slot, 1, 4, ks.index(32), done=lambda: g.u8(0x8007e82a) != 0)
                    self.note('maporfic', c['name'], g.u8(0x8007e82a))
                except Stuck as s:
                    # a spell with no target goes back to the level's list (state 10),
                    # not to 0 or 50, so camp.cast's last wait runs out though the
                    # spell is on (mapo_probe, 2026-10-14)
                    if not g.u8(0x8007e82a):
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

    def ready(self, home_below=None, train=True):
        """Before a boss: home if anyone is dead or under home_below of max HP once the
        priests have healed what they can (the Cots heal everyone to full there), else
        heal to READY_HP from camp. train=False after a door check's trip home (the
        boss training is done once a try)."""
        g = self.g
        home_below = home_below or READY_HOME
        self._ready_goal = getattr(self, '_goal_name', None)
        self._door_trips = 0 if train else getattr(self, '_door_trips', 0)
        if train:
            self.boss_training()
        self.fit()
        self.keep_for_boss()
        if g.overlay() in ('JOUKA', 'HAZURE'):
            self.raise_all()
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

    def boss_short(self):
        """What the boss fight would lack at the door: a member down (chapter1.SERIOUS), the
        Cortu stack (the Cortu mages' level-3 points under CORTU_STACK - 1, or what they had
        after the Stables if less: the n1v0q replay won with three), Madi (the Madi priests'
        level-6 points under 2, or their full), or the heals (the priests' Dial, Dialma and
        Madi levels 4-6 under POINTS_READY of what they had after the Stables)."""
        g = self.g
        short = []
        if chapter1.out_of_action(g):
            short.append('down')
        for sid, sch, lv, want in ((tactics.CORTU, 0, 3, tactics.CORTU_STACK - 1), (tactics.MADI, 1, 6, 2)):
            who = [i for i in g.party() if g.char(i)['status'] < 0x20
                   and sid in battle.known_spells(g.char(i)['raw'], sch, lv)]
            if not who:
                continue
            k = 0x5c + sch * 7 + lv - 1
            have = sum(g.char(i)['raw'][k] for i in who)
            full = sum(self.full_points[i][k - 0x5c] if self.full_points.get(i) else want for i in who)
            if have < min(want, full):
                short.append(('Cortu' if sid == tactics.CORTU else 'Madi', have, min(want, full)))
        have = full = 0
        for i in g.party():
            raw = g.char(i)['raw']
            if g.char(i)['status'] >= 0x20 or not self.full_points.get(i):
                continue
            if any(h in tactics.HEALS for lv in (4, 5, 6) for h in battle.known_spells(raw, 1, lv)):
                have += sum(raw[0x5c + 7 + lv - 1] for lv in (4, 5, 6))
                full += sum(self.full_points[i][7 + lv - 1] for lv in (4, 5, 6))
        if full and have < full * POINTS_READY:
            short.append(('heals', have, full))
        return short

    def door_ready(self):
        """At a boss's door after the walk (main, 2026-10-14): anyone down or the boss's
        points short (boss_short) send the party home to rest and walk back, at most
        DOOR_TRIPS times a try; then it fights as it stands. trip_home raises the dead
        at the temple, or from camp only where the temple is out of reach, as before.
        True when the party went home (ready(train=False) and walk again)."""
        short = self.boss_short()
        if not short:
            return False
        n = getattr(self, '_door_trips', 0)
        self.note('door short', getattr(self, '_goal_name', None), short, n)
        if n >= DOOR_TRIPS:
            return False
        self._door_trips = n + 1
        self.trip_home('short at a boss door')
        return True

    def keep_for_boss(self):
        """On the walk from ready() to a boss, each mage who knows Cortu keeps their share
        of CORTU_STACK level-3 points (battle.BOSS_KEEP); cleared when the goal ends. Main,
        2026-10-14: the n1v0q Guardians tries arrived with the mages' level-3 points spent
        on the walk's ten fights."""
        g = self.g
        who = [i for i in g.party() if g.char(i)['status'] < 0x20
               and tactics.CORTU in battle.known_spells(g.char(i)['raw'], 0, 3)]
        battle.BOSS_KEEP.clear()
        for k, i in enumerate(who):
            n = tactics.CORTU_STACK // len(who) + (1 if k < tactics.CORTU_STACK % len(who) else 0)
            battle.BOSS_KEEP[i] = {(0, 3): n}
        if who:
            self.note('boss keep', getattr(self, '_goal_name', None),
                      [(g.char(i)['name'], battle.BOSS_KEEP[i][(0, 3)]) for i in who])

    def replay_trains(self, name):
        """(main, 2026-10-14: n1v0o stopped on two identical wipes at chapter 10's
        Guardians) A boss goal (one that calls ready) on a chapter with training floors goes
        on after a replayed failure: its next try trains a level first (boss_training), so
        it isn't the same fight. At most BOSS_REPLAYS failed tries."""
        import sys
        mod = sys.modules.get('harness.chapter%d' % self.chapter)
        return (getattr(self, '_ready_goal', None) == name and bool(getattr(mod, 'TRAIN_AREAS', None))
                and self.boss_wipes() + 1 < BOSS_REPLAYS)

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
                if chapter1.anyone_dead(self.g):
                    # a status first: hurt() leaves out a poisoned member, so heal_strong
                    # never healed one (n1v0p chapter 10: Venus, poisoned on the way, went
                    # into the Guardians at 49 of 103 and Earth spent rounds on Madi)
                    chapter1.cure_in_camp(self.g, self.log, on_int=self.on_int)
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
            self.raise_all()
            if any(g.char(i)['status'] != 0 for i in town.town_party(g)) \
                    or len(town.town_party(g)) < 4:
                return False
        return True

    def raise_all(self):
        """In town with members the temple can't afford: gold trips on easier floors until
        it can (each ends at the temple). b1v1b chapter 3, 2026-10-14: the Ice Rocks
        killed two, the temple was too poor, and the party went on as three and a
        level-5 recruit."""
        for _ in range(GOLD_MOST):
            if not self.temple_short():
                return True
            self.gold_trip()
        return not self.temple_short()

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
        if POINTS_TRAIN and not getattr(self, '_gold', False) and g.overlay() not in ('JOUKA', 'HAZURE'):
            low = self.points_low()
            if low:
                # a training trip sets out with its casters' points, as a boss does (the
                # chapter's story goals can leave them spent in the maze)
                self.note('points low before training', low)
                self.trip_home('points before training')
        if not getattr(self, '_gold', False) and self.temple_short():
            # the trip home just now left a member the temple can't raise: this trip goes
            # for gold on easier floors instead, and counts (its checkpoint keeps the gold)
            self._gold = True
            try:
                self.gold_trip()
            finally:
                self._gold = False
            return True
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
        base, areas = areas, self.ladder_areas(self.pull_areas(areas))
        self.note('train area', tuple(areas), tuple(base))
        self._keep = tuple(areas)
        if MAPORFIC_TRIP:
            # the party's AC for the trip (Chris, 2026-10-14; B-camp.md: -2 for 1250 steps)
            self.maporfic()
        battle.TRIP_BLOW[:] = [0.0, 0.0]
        l0 = len(self.log)
        self._heals_out = False
        self._spot_bad = set()          # heal spots that didn't work this trip
        battle.RUN_WHEN_LOSING = True
        tactics.TRAINING = True
        battle.RUN_OK = True            # the walk to the first square may run (FLEE_RULE)
        why = 'squares done'
        try:
            for area in areas:
                F = nav.floor(area)
                # only squares reached without leaving the trip's floors: B4's west rooms
                # and two of B5's are reached through B3, B2 and B1, and the trip that
                # walked there met the Were Centipedes on B3 (n1v0j chapter 9, 2026-10-15)
                sqs = [sq for sq in F['fights'] if nav.plan(g, (area,) + sq, keep=areas)
                       is not None] or list(F['fights'])
                self.rng.shuffle(sqs)
                for sq in sqs:
                    if self.fights() - n0 >= fights:
                        why = 'fight count'
                        break
                    if HEAL_SPOT:
                        self.spot_heal()
                    if chapter1.needs_town(g) and self.town_helps():
                        why = None
                        break
                    if POINTS_HOME and self.points_spent():
                        why = 'points'
                        break
                    if MAPORFIC_TRIP:
                        # Maporfic all trip (strategy revision 5): again when its 1250
                        # steps run out, while the priest keeps two level 4 points for Dial
                        self.maporfic(keep=MAPORFIC_KEEP)
                    if HP_HEAL:
                        if self.hp_heal():
                            why = 'critical'
                            break
                    elif TOPUP:
                        if getattr(self, '_heals_out', False) or self.top_up():
                            why = 'heals out'
                            break
                    elif chapter1.hurt(g, 0.6) and chapter1.priests(g):
                        chapter1.heal_in_camp(g, self.log, on_int=self.on_int)
                    if nav.plan(g, (area,) + sq) is None:
                        continue
                    spot = None
                    self._walking_out = True
                    try:
                        self.go((area,) + sq)
                        battle.RUN_OK = False   # at the grinding spot: fight it out
                    except ToSpot as t:
                        spot = t.args[0]
                    except TurnHome as t:
                        self.note('turn home', t.args[0])
                        why = 'critical'
                        break
                    finally:
                        self._walking_out = False
                    if spot:
                        # (healspots) hurt on the walk out: the heal spot, then the next square
                        self.spot_heal(spot)
                else:
                    why = 'squares done'
                    continue
                break
            self.trip_home(why)
        finally:
            battle.RUN_WHEN_LOSING = False
            battle.RUN_OK = False
            tactics.TRAINING = False
        self.ladder_step(base, areas, l0)
        # a member swapped out alive for a raised one (raised_back) isn't a casualty
        # (b1v6c chapter 7, 2026-10-14: Jupiter, out for Tia, counted twice and reloaded)
        left = [i for i in setting_out if i not in town.town_party(g) and g.char(i)['status'] != 0]
        hurt = any(g.char(i)['status'] != 0 for i in town.town_party(g)) or len(town.town_party(g)) < 4
        # a death, not a cure: the temple raised or ashed them, or they wait there dead
        self.note('train trip', dict(died=any(g.char(i)['status'] & 0x380 for i in left) or any(
            x[1] == 'temple' and x[2] in setting_out and isinstance(x[3], dict)
            and x[3].get('outcome') in ('alive', 'ashes', 'lost') for x in self.log[l0:] if len(x) > 3)))
        if DEATH_RETRY and (hurt or areas != (0,) and left):
            if left:
                self.note('left at the temple', [g.char(i)['name'] for i in left])
            return 'casualties'
        # the party lives with a death (Chris, 2026-10-14: realistic play): the temple
        # raised them if the gold allowed, else they wait there and a standby fills in
        # (town_upkeep), and the next trip goes for the fee (temple_short -> gold_trip).
        # Only a wipe reloads.
        died = [g.char(i)['name'] for i in setting_out
                if any(x[1] == 'temple' and x[2] == i for x in self.log[l0:] if len(x) > 2)]
        if died or left or hurt:
            self.note('lived with', dict(temple=died, waiting=[g.char(i)['name'] for i in left],
                                         party=len(town.town_party(g))))
        return True

    def tag_deaths(self, l1):
        """(main, 2026-10-14) A 'death' note per member who fell in the fights logged since
        l1 (battle.death_tags), with a category: trap, confused ally, walking home hurt,
        sleep/paralysis (helpless before the blow), else the blow (melee, spell, breath,
        other); and the
        fight's monster groups. The second time a chapter has the same category and
        monster, a 'death pattern' note and a stdout line (for the agent to take to main)."""
        for x in self.log[l1:]:
            if not (len(x) > 2 and x[1] == 'fought' and isinstance(x[2], dict)):
                continue
            for d in x[2].get('deaths') or []:
                cat = ('trap' if d['how'] == 'trap' else 'confused ally' if d['how'] == 'ally'
                       else 'walking home hurt'
                       if getattr(self, '_homeward', False) else 'sleep/paralysis'
                       if d['helpless'] else d['how'])
                key = '%s: %s' % (cat, d['by'] or '?')
                groups = [(q.get('id'), q.get('level'), q.get('n'))
                          for q in (x[2].get('first') or {}).get('groups', [])]
                self.note('death', dict(d, cat=cat, key=key, where=x[2].get('where'),
                                        goal=getattr(self, '_goal_name', None), groups=groups))
                n = sum(1 for y in self.log[self._ch_l0:] if len(y) > 2 and y[1] == 'death'
                        and y[2].get('key') == key)
                if n == 2:
                    self.note('death pattern', key)
                    print('death pattern c%d %s x2: %s %s %s by %s at %s, groups %s' % (
                        self.chapter, key, d['who'], d['fell'], d['what'], d['how'],
                        x[2].get('where'), groups), flush=True)

    def homeward_run(self):
        """The walk home may run (FLEE_RULE): the casters are spent, or a member is dead,
        ash or lost (main, 2026-10-14: n1v3j c9 train_02 walked home with two dead, met a
        fixed caster party with the casters' points still up, couldn't run and was wiped)."""
        return self.casters_spent() or any(self.g.char(i)['status'] & HOME_DEAD for i in self.g.party())

    def casters_spent(self, frac=1 / 3):
        """The party's spell points (every school and level, the standing members') at
        frac or less of what they had after the last Stables: the walk home may run."""
        g = self.g
        now = full = 0
        for ri in g.party():
            c = g.char(ri)
            if c['status'] >= 0x20:
                continue
            f = self.full_points.get(ri)
            if not f:
                continue
            full += sum(f)
            now += sum(c['raw'][0x5c:0x78])
        return bool(full) and now <= full * frac

    def heal_reserve(self, ri, sch, lv):
        """Points a healer keeps at (school, level) on the walk home (main, 2026-10-14):
        one for their strongest heal (HEAL_OPTS) and one for a cure, Dialko if they know
        it, else Latumofis (chapter1.CURES)."""
        raw = self.g.char(ri)['raw']
        known = lambda sid, s_, l_: sid in battle.known_spells(raw, s_, l_)
        heals = [(mean, s_, l_) for sid, s_, l_, mean in HEAL_OPTS if known(sid, s_, l_)]
        cures = [(s_, l_) for sid, s_, l_, bits, party in chapter1.CURES
                 if bits in (0x20, 0x04) and known(sid, s_, l_)]
        r = 0
        if heals and max(heals)[1:] == (sch, lv):
            r += 1
        if cures and cures[0] == (sch, lv):
            r += 1
        return r

    def spot_choice(self):
        """(healspots) (steps, square, facing) of the nearest heal spot (HEAL_SPOTS) when the
        party wants one: a standing member under SPOT_LINE of max HP or with a status the
        switch clears (SPOT_FIX), nobody dead, ash or lost (that trip goes home), and the
        spot nearer than the Grounds' entrance (nav.cost). Else None."""
        g = self.g
        if not HEAL_SPOTS or not maze.in_maze(g) or g.overlay() in ('JOUKA', 'HAZURE', 'BATTLE'):
            return None
        cs = [g.char(i) for i in g.party()]
        if any(c['status'] & HOME_DEAD for c in cs) or not any(
                c['status'] & SPOT_FIX or c['max_hp'] and c['hp'] < c['max_hp'] * SPOT_LINE for c in cs):
            return None
        here = (g_area(g),) + g.pos()
        home = nav.cost(g, (0,) + maze.ENTRANCE[0])
        best = None
        for sq, face in HEAL_SPOTS.items():
            if sq in getattr(self, '_spot_bad', ()):
                continue
            b = 0 if sq == here else nav.cost(g, sq)
            if b is None or home is not None and b >= home:
                continue
            if best is None or b < best[0]:
                best = (b, sq, face)
        return best

    def spot_heal(self, choice=None):
        """(healspots) Walk to the heal spot spot_choice picks (or `choice`), face its
        switch, Investigate and answer Yes. Logged as 'heal spot'. True when everyone
        standing came out at full HP with no status."""
        g = self.g
        choice = choice or self.spot_choice()
        if not choice:
            return False
        steps, sq, face = choice
        hp = lambda: sum(max(0, g.char(i)['hp']) for i in g.party())
        hp0, f0, pol = hp(), g.frame, self.policy
        self.policy = type('SpotPolicy', (pol or LaterPolicy,), dict(prompt='yes'))
        try:
            self.examine(sq, face)
        finally:
            self.policy = pol
        cs = [g.char(i) for i in g.party()]
        ok = (g_area(g),) + g.pos() == sq and all(
            c['hp'] == c['max_hp'] and not c['status'] for c in cs if not c['status'] & HOME_DEAD)
        if not ok:
            self._spot_bad = getattr(self, '_spot_bad', set()) | {sq}
        self.note('heal spot', dict(at=sq, steps=steps, hp=[hp0, hp()], ok=ok, frames=g.frame - f0))
        print('c%d heal spot %s: %d steps, HP %d -> %d%s' % (
            self.chapter, sq, steps, hp0, hp(), '' if ok else ' (not healed)'), flush=True)
        return ok

    def home_heal(self):
        """(main, 2026-10-14: 5 of n1v6's 8 chapter 10 deaths came walking home hurt) A
        trip that turns home has no other use for its points: before the homeward leg,
        heal everyone to 2/3 of max HP, or to full when the points over each healer's
        reserve (heal_reserve) cover the whole gap. Logged as 'home heal'."""
        g = self.g
        if g.overlay() in ('JOUKA', 'HAZURE', 'BATTLE') or not maze.in_maze(g):
            return
        ups = [g.char(ri) for ri in g.party()]
        ups = [c for c in ups if c['status'] < 0x20 and c['hp'] > 0 and c['max_hp']]
        gap = sum(c['max_hp'] - c['hp'] for c in ups)
        if not gap:
            return
        spare = 0
        for ri in g.party():
            c = g.char(ri)
            if c['status'] & ~0x05:
                continue
            for sid, sch, lv, mean in HEAL_OPTS:
                if sid in battle.known_spells(c['raw'], sch, lv):
                    left = c['raw'][0x5c + sch * 7 + lv - 1] - self.heal_reserve(ri, sch, lv)
                    spare += max(0, left) * (min(mean, 100) if mean >= 999 else mean)
        line = 1.0 if spare >= gap else 2 / 3
        hp0 = sum(c['hp'] for c in ups)
        self.hp_heal(most=24, home_line=line)
        hp1 = sum(g.char(ri)['hp'] for ri in g.party() if g.char(ri)['status'] < 0x20)
        self.note('home heal', dict(line=round(line, 2), gap=gap, spare=round(spare), hp=[hp0, hp1]))

    def hp_heal(self, most=16, home_line=None):
        """Chris's HP lines (2026-10-14), per standing member: over 2/3 of max HP no heal;
        under 2/3 back over 2/3 only from points to spare (the caster keeps half that
        level's points from the last Stables, levels 1-5 only); under 1/2 back over 1/2
        before the next fight; under 1/3 critical. Each cast is the cheapest heal whose
        mean clears the gap (HEAL_OPTS), Madi or Kadios only under 1/2 when two of the
        best lower heals wouldn't. Returns the names still under 1/3 when the heals are
        out (the trip turns home), else []."""
        g = self.g
        poisoned = lambda: [g.char(ri)['name'] for ri in g.party()
                            if g.char(ri)['status'] & 0x04 and g.char(ri)['status'] < 0x20]
        if POISON_HOME and poisoned():
            # poison first: it takes HP every few steps, so heals spent on a poisoned
            # party drain away (n1v0 chapter 3, 2026-10-14: 14 Wing Lizards poisoned all
            # six, the bot healed HP for three more fights and five died walking home)
            chapter1.cure_in_camp(self.g, self.log, on_int=self.on_int)
        tried, n, k = set(), 0, 0
        while n < most and k < 40:
            k += 1
            if not camp.in_camp(g) and not maze.calm(g) and not maze.settle(g):
                break
            slots = g.party_slots()
            want = []
            for t, ri in enumerate(slots):
                if ri is None:
                    continue
                c = g.char(ri)
                if c['status'] >= 0x20 or c['hp'] <= 0 or not c['max_hp']:
                    continue
                f = c['hp'] / c['max_hp']
                if home_line and f < home_line:
                    want.append((f, t, ri, c['max_hp'] * home_line - c['hp'], True))
                elif home_line:
                    pass
                elif f < 0.5:
                    want.append((f, t, ri, c['max_hp'] * 0.5 - c['hp'], True))
                elif f < 2 / 3:
                    want.append((f, t, ri, c['max_hp'] * 2 / 3 - c['hp'], False))
            want.sort()
            pick = None
            for f, t, ri, gap, must in want:
                opts = []
                for sid, sch, lv, mean in HEAL_OPTS:
                    for cs, cri in enumerate(slots):
                        if cri is None or (sid, cs, t) in tried:
                            continue
                        c = g.char(cri)
                        if c['status'] & ~0x05 or not c['raw'][0x5c + sch * 7 + lv - 1]:
                            continue            # afraid and poisoned members cast in camp
                        left = c['raw'][0x5c + sch * 7 + lv - 1]
                        full = (self.full_points.get(cri) or c['raw'][0x5c:0x78])[sch * 7 + lv - 1]
                        if home_line:
                            if left - 1 < self.heal_reserve(cri, sch, lv):
                                continue        # the walk home keeps a heal and a cure
                        elif not must and (lv >= 6 or left - 1 < full / 2):
                            continue            # only points to spare above 1/2 HP
                        ks = battle.known_spells(c['raw'], sch, lv)
                        if sid in ks:
                            opts.append((lv, mean, sid, sch, cs, ks.index(sid)))
                            break
                if not opts:
                    continue
                small = sorted(o for o in opts if o[1] < 999)
                clear = [o for o in small if o[1] >= gap]
                best_small = max((o[1] for o in small), default=0)
                full_ok = [o for o in opts if o[1] >= 999 and must and 2 * best_small < gap]
                o = clear[0] if clear else full_ok[0] if full_ok else (small[-1] if small else None)
                if o:
                    pick = (o, t, gap)
                    break
            if not pick:
                break
            (lv, mean, sid, sch, cs, idx), t, gap = pick
            ri = slots[t]
            hp0 = g.char(ri)['hp']
            try:
                camp.cast(g, cs, sch, lv, idx, t)
            except Stuck as s:
                if s.what != 'camp interrupted':
                    raise
                self.on_int(g)
                continue
            if g.char(ri)['hp'] <= hp0:
                tried.add((sid, cs, t))         # nothing healed (the list place?): not again
            self.log.append((g.frame, 'hp heal', sid, lv, g.char(slots[cs])['name'],
                             g.char(ri)['name'], round(gap), g.char(ri)['hp'] - hp0))
            n += 1
        if camp.in_camp(g):
            camp.close_camp(g)
        low = [g.char(ri)['name'] for ri in g.party()
               if g.char(ri)['status'] < 0x20 and 0 < g.char(ri)['hp'] < g.char(ri)['max_hp'] / 3]
        # poison the party's cures couldn't clear: the trip goes home now (the walk home
        # keeps healing by the HP lines)
        left = poisoned() if POISON_HOME else []
        if left:
            self.note('poison home', left)
        return low + [x for x in left if x not in low]

    def top_up(self):
        """Between a training trip's fights: heal each member to what the worst monster
        seen this trip couldn't take in two hits (tactics blow, by row), at least 60% of
        max HP, with the cheapest heals (chapter1.heal_to). True when the heals ran out
        with someone still short: the trip goes home."""
        g = self.g
        blow = battle.TRIP_BLOW

        def need(slot, c):
            return max(c['max_hp'] * 0.6, 2 * blow[0 if slot < 3 else 1] + 1)
        short = chapter1.heal_to(g, self.log, need, on_int=self.on_int)
        if short:
            # short by a third or more of what they need: home (a little short goes on)
            for slot in short:
                ri = g.party_slots()[slot]
                if ri is not None:
                    c = g.char(ri)
                    if c['hp'] < min(c['max_hp'], need(slot, c)) * 0.67:
                        self.note('heals out', c['name'], c['hp'], round(need(slot, c)))
                        return True
        return False

    def ladder_areas(self, areas):
        """(Chris, 2026-10-14) The training floor by deaths per trip: one floor shallower
        after a trip that lost someone, one deeper after a clean one, between two floors
        above the chapter's first training floor and its deepest (LADDERS, shallow to deep
        by the site's floor labels). At the chapter's first floor the trip keeps all of its
        floors, as before."""
        lad = next((L for L in LADDERS if areas[0] in L), None)
        if not LADDER or not lad:
            return areas
        start = lad.index(areas[0])
        top = max(lad.index(a) for a in areas if a in lad)
        i = self._floors.setdefault(tuple(areas), start)
        while i < top and not any(nav.plan(self.g, (lad[i],) + sq) is not None
                                  for sq in sorted(nav.floor(lad[i])['fights'])[:6]):
            i += 1              # out of reach: the next floor down
        if i == start:
            return tuple(areas)
        self.note('training floor', lad[i], areas)
        return (lad[i],)

    def train_trips(self):
        """This chapter's training trips from the log: dict(key=area tuple, i=log index,
        died, downs, fights). A wipe (a 'retry' after 'train area') is a trip with a death."""
        out, cur, pd, pw = [], None, set(), set()
        for i in range(self._ch_l0, len(self.log)):
            x = self.log[i]
            if len(x) < 2:
                continue
            k = x[1]
            if k == 'train area':
                cur, pd, pw = dict(key=tuple(x[2]), i=i, died=False, downs=0, fights=0), set(), set()
            elif cur is None:
                continue
            elif k == 'fought' and len(x) > 2 and isinstance(x[2], dict):
                d, w = set(x[2].get('dead_end', [])), set(x[2].get('down_end', []))
                cur['fights'] += 1
                cur['died'] |= bool(d - pd)
                cur['downs'] += len(w - pw)
                pd, pw = d, w
            elif k in ('temple', 'rejoined', 'trip home', 'stables'):
                pd, pw = set(), set()
            elif k == 'train trip':
                cur['died'] |= bool(x[2].get('died'))
                out.append(cur)
                cur = None
            elif k == 'retry':
                cur['died'] |= len(x) > 3 and x[3] == 'wiped'
                if cur['died']:
                    out.append(cur)
                cur = None
        return out

    def pull_why(self, key):
        """Why `key` is too hard now, or None: a death on PULL_DEATHS of its last PULL_TRIPS
        trips, or its downs per 100 fights over them at PULL_DOWNS times the chapter's
        norm (its training trips before them, at least DOWN_NORM) with 3+ downs."""
        T = self.train_trips()
        own = [t for t in T if t['key'] == key and t['i'] >= self._since.get(key, 0)][-PULL_TRIPS:]
        if not own:
            return None
        died = sum(t['died'] for t in own)
        if died >= PULL_DEATHS:
            return 'deaths %d/%d' % (died, len(own))
        if len(own) < PULL_TRIPS:
            return None
        f, w = sum(t['fights'] for t in own), sum(t['downs'] for t in own)
        before = [t for t in T if t['i'] < own[0]['i']]
        bf, bw = sum(t['fights'] for t in before), sum(t['downs'] for t in before)
        norm = max(DOWN_NORM, 100 * bw / bf if bf else 0)
        if f and w >= 3 and 100 * w / f >= PULL_DOWNS * norm:
            return 'downs %.0f/100 vs %.0f' % (100 * w / f, norm)
        return None

    def pull_done(self, p):
        """Why a pull-back can end, or None: the party gained a level since it began, or
        the easier area's last PULL_TRIPS trips since then had no death and downs per 100
        at or under DOWN_NORM."""
        if self.party_level() > p['lv']:
            return 'level %d' % self.party_level()
        own = [t for t in self.train_trips() if t['key'] == p['to'] and t['i'] >= p['at']][-PULL_TRIPS:]
        f, w = sum(t['fights'] for t in own), sum(t['downs'] for t in own)
        if len(own) == PULL_TRIPS and not any(t['died'] for t in own) and 100 * w <= DOWN_NORM * max(f, 1):
            return 'rate %d downs/%d fights' % (w, f)
        return None

    def easier_area(self, key):
        """The training areas an earlier chapter used before `key` (the most recent
        distinct TRAIN_AREAS going back), or None."""
        import sys
        seq = []
        for n in range(self.chapter, 1, -1):
            a = getattr(sys.modules.get('harness.chapter%d' % n), 'TRAIN_AREAS', None)
            if a and tuple(a) not in seq:
                seq.append(tuple(a))
        return seq[seq.index(key) + 1] if key in seq and seq.index(key) + 1 < len(seq) else None

    def pull_areas(self, areas):
        """(Chris, 2026-10-14: if an area is too hard, pull back and train) The areas this
        trip trains in: `areas`, or the easier area it was pulled back to (pull_why), until
        pull_done says go back; a pulled-back area that is too hard pulls back again.
        Logged as 'pull back' and 'pull return' (the trend counts them)."""
        key = tuple(areas)
        if not PULL_BACK:
            return key
        seen = set()
        while key not in seen:
            seen.add(key)
            p = self._pull.get(key)
            if p is None:
                why = self.pull_why(key)
                to = why and self.easier_area(key)
                if not to:
                    return key
                self._pull[key] = dict(to=to, lv=self.party_level(), at=len(self.log))
                self.note('pull back', key, to, why, self.party_level())
                print('c%d pull back %s -> %s: %s' % (self.chapter, key, to, why), flush=True)
                key = to
                continue
            back = self.pull_done(p)
            if back:
                k = key
                while k in self._pull:          # the pulls below it end too
                    k = self._pull.pop(k)['to']
                self._since[key] = len(self.log)
                self.note('pull return', key, back, self.party_level())
                print('c%d pull return %s: %s' % (self.chapter, key, back), flush=True)
                return key
            key = p['to']
        return key

    def ladder_step(self, base, areas, l0):
        lad = next((L for L in LADDERS if base[0] in L), None)
        if not LADDER or not lad:
            return
        start = lad.index(base[0])
        top = max(lad.index(a) for a in base if a in lad)
        lost = sorted({n for x in self.log[l0:] if len(x) > 2 and x[1] == 'fought'
                       and isinstance(x[2], dict) for n in x[2].get('down_end', [])})
        i = self._floors.get(tuple(base), start)
        i = max(start - 2, i - 1) if lost else min(top, i + 1)
        self._floors[tuple(base)] = i
        self.note('next floor', lad[i], lost)

    def train_goals(self, areas, level, prefix='train', most=40):
        """(name, fn) training trips, yielded lazily while min level < level (a
        chapter's goals() can `yield from` this)."""
        k = gk = 0
        while k < most and self.party_level() < level:
            if self.temple_short() and gk < GOLD_MOST:
                # a member waits at the temple and the gold won't raise them: trips on
                # the last chapter's floors for gold first, each its own goal so the gold
                # is kept (b1v0 chapter 3, 2026-10-14: Earth dead since chapter 2, the
                # party too poor, and six training trips on B3 lost more members)
                gk += 1
                yield '%s_gold_%02d' % (prefix, gk), self.gold_trip
                continue
            k += 1
            yield '%s_%02d' % (prefix, k), (lambda: self.train(areas))

    def temple_short(self):
        """Names of this party's members at the temple whose fee (E-town.md: level x 100
        paralyzed, 200 stoned, 250 dead, 500 ashes) is more than the party's gold. Only
        members near the party's level count (not the tavern's level-5 premades)."""
        g = self.g
        if g.overlay() not in ('JOUKA', 'HAZURE'):
            return []
        gold = sum(g.char(i)['gold'] for i in town.town_party(g))
        out = []
        for ri in town.temple_patients(g):
            c = g.char(ri)
            if c['level'] < self.party_level() - 3:
                continue
            st = c['status']
            fee = c['level'] * (500 if st & 0x100 else 250 if st & 0x80 else 200 if st & 0x40
                                else 100 if st & 0x20 else 0)
            if fee > gold:
                out.append(c['name'])
        return out

    def gold_areas(self):
        """The floors an earlier chapter trained on (the Grounds before chapter 2's)."""
        import sys
        for n in range(self.chapter - 1, 1, -1):
            a = getattr(sys.modules.get('harness.chapter%d' % n), 'TRAIN_AREAS', None)
            if a:
                return a
        return (0,)

    def gold_trip(self):
        """One trip for gold on easier floors; it counts whatever the temple did."""
        areas = self.gold_areas()
        self.note('gold trip', areas, self.temple_short())
        keep, self._gold = getattr(self, '_gold', False), True
        try:
            self.train(areas)
        finally:
            self._gold = keep
        return True

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


MAPORFIC_TRIP = True         # Maporfic from camp as a training trip sets out, and again when it lapses (agent 13, revision 5)
MAPORFIC_KEEP = 2            # ... the recast keeps this many Priest level 4 points (Dial)
TOPUP = False                # heal to what the trip's worst monster can't take in two hits
HOME_HEAL = True             # (main) before the homeward leg, heal to 2/3 or full (Run.home_heal)
HP_HEAL = True               # Chris's HP lines after every training fight (Run.hp_heal)
HOME_DEAD = 0x80 | 0x100 | 0x200  # dead, ash, lost: the walk home may run (Run.homeward_run)
HEALER_HOME = True           # (agent 16) a healer down on the walk out or a goal walk turns the party home
HEALER_TRIPS = 2             # ... a goal walk goes home and back at most this many times
ROAMER_DOOR = True           # (agent 16) a goal walk short for the floor's type-2 parties goes home first (Run.roamer_short)
TYPE2_ROUNDS = 2             # ... the standing HP must cover this many rounds of the worst one's threat
TYPE2_TOKENS = 0x8005e654    # npc_tokens_per_area: 2 bytes an area, the second the type-2 tokens placed
# the worst type-2 party's rated threat a round by area (tactics.info at the first command, every
# chain's logs to 2026-10-14; the parties are the area group's type2_groups, 0x8005a3dc)
TYPE2_THREAT = dict([(a, 15) for a in (3, 4)] + [(a, 80) for a in (5, 6, 7, 8)] +
                    [(a, 95) for a in (19, 20, 21, 22)] + [(a, 153) for a in (23, 24, 25, 26, 27)])
AVOID_FATAL = True           # the walk home keeps off the square of the trip's fatal fixed fight (nav.TRIP_SOFT)
POINTS_HOME = 0.5           # agent 13 (strategy revision 3): a training trip goes home when points or heals are this low (Run.points_spent)
POINTS_TRAIN = True         # agent 8: a training trip from the maze goes home first when points are low
DEATH_RETRY = False         # agent 8, 2026-10-14 (Chris): a training trip with a death isn't reloaded
POISON_HOME = True          # agent 7, 2026-10-14: cure poison first after a fight; home if it stays
LOOT_EACH_FIGHT = True      # agent 7, 2026-10-14: camp_loot after a training fight that left work
# camp heals, cheapest first: (spell id, school, level, mean HP; 999 = full). B-camp.md:
# Dios 2d4, Diomas 3d2, Dial 2d8, Dialma 3d8, Madi and Kadios full
HEAL_OPTS = [(21, 1, 1, 5), (64, 3, 1, 4.5), (30, 1, 4, 9), (33, 1, 5, 13.5),
             (36, 1, 6, 999), (58, 2, 6, 999)]


def g_area(g):
    return g.u8(maze.AREA)


class TurnHome(Exception):
    """A member stays under 1/3 of max HP with the heals gone: the walk out ends."""


class ToSpot(Exception):
    """A training fight left the party hurt and a heal spot is nearer than home: the walk
    out stops and the party goes to the spot (Run.spot_choice), then on with the trip."""


# (healspots) the heal switches, square event 0x3f (MAZE square_examine 0x800bb790 case 0x3f,
# maze_prompt_result 0x800befcc prompt 0xe; A-maze.md "Heal spots"): Investigate facing the
# record's p1 and answer Yes, and every member not dead, ash or lost gets full HP, status
# 0 and poison 0. Free, no flag, repeatable. (area, x, y) in RAM coordinates: facing
# (0 N, 1 E, 2 S, 3 W). Area B B4 E5 N18, Area E B3 E12 N4, Dragon B1 E10 N13.
HEAL_SPOTS = {(24, 5, 5): 3, (37, 12, 19): 0, (42, 10, 10): 3}
HEAL_SPOT = True            # use them on training trips when one is nearer than home (Run.spot_choice)
SPOT_LINE = 2 / 3           # ... for a standing member under this share of max HP, or a status the switch clears
SPOT_FIX = 0x7f             # afraid, confused, poisoned, asleep, K.O., paralyzed, stoned
LADDER = False              # training floor by deaths per trip (ladder_areas)
PULL_BACK = True             # agent 11 (Chris): too hard an area -> train in the easier one (pull_areas)
PULL_TRIPS = 3               # ... judged on its last few trips
PULL_DEATHS = 2              # ... a death on this many of them
PULL_DOWNS = 2               # ... or downs/100 this many times the chapter's norm
DOWN_NORM = 10               # downs per 100 training fights taken as normal (old chains c4-c9: 6-13)
# each dungeon's floors, shallow to deep (the site's floor labels: Underground B1-B4,
# Area A B1-B4, Area B B1-B5)
LADDERS = [(8, 7, 6, 5), (22, 21, 20, 19), (27, 26, 25, 24, 23)]
GOLD_MOST = 15              # gold trips a chapter's training may insert
# (revision 9, agent 14) Cresson's party's fixed meeting on Underground B3 (fixed_meet_table
# 0x8005e6ac, talk id 0x16, in RAM coordinates; the docs' "E8 N6"), placed whenever the
# party arrives on the floor (npc_availability 0x80018bd4). Cleo's Kadorto is free and
# certain (C-talk.md §5; emulator check 2026-10-14, rips/agents/chapters/cleo/).
CLEO = (6, 8, 17)
CLEO_RAISE = True
CLEO_DETOUR = 150           # plan steps the detour may add to the walk home
CLEO_GOLD_SHARE = 0.25      # ... for a temple fee this share of the party's gold or more
RECOVER_MOST = 30           # Grounds trips for the Tablet's holder inside one goal
BOSS_REPLAYS = 6            # failed tries at a boss goal before a replayed one stops the run
BOSS_WIPES = 2              # failed tries at a goal before each further try trains a level
FIGHT_WAIT = 2400
READY_HP = 0.9              # a boss fight starts with everyone at this share of max HP
READY_HOME = 0.7            # ... or the party goes home first if healing can't reach this
POINTS_READY = 0.6          # ... or the casters' points at levels 3-7 are under this share
DOOR_TRIPS = 2              # home trips from a boss's door (door_ready) before it fights as it stands
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


from harness import chapter2, chapter3, chapter4, chapter5, chapter6, chapter7, chapter8, chapter9, chapter10, chapter11  # noqa: E402,F401  (register the chapters)


def points_path(g, name):
    return os.path.splitext(g.path(name))[0] + '.points.json'


def save_points(g, name, full):
    """The casters' points after the last Stables beside a state (agent 8): a run resumed
    from it knows them (load_points)."""
    with open(points_path(g, name), 'w') as f:
        json.dump({str(k): v for k, v in full.items()}, f)


def memory_path(g, name):
    return os.path.splitext(g.path(name))[0] + '.memory.json'


def save_memory(r, name):
    """The chapter's log since it began, its pull-backs (Run._pull) and returns
    (Run._since), with log indices counted from the chapter's start, beside a goal state
    (agent 14): a run resumed from it trains and pulls back as this one would have."""
    l0 = r._ch_l0
    m = dict(chapter=r.chapter, log=r.log[l0:],
             pull=[[list(k), dict(v, to=list(v['to']), at=v['at'] - l0)] for k, v in r._pull.items()],
             since=[[list(k), v - l0] for k, v in r._since.items()])
    with open(memory_path(r.g, name), 'w') as f:
        json.dump(m, f, default=str)


def load_memory(g, name):
    try:
        with open(memory_path(g, name)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_points(g, name):
    try:
        with open(points_path(g, name)) as f:
            return {int(k): v for k, v in json.load(f).items()}
    except (OSError, ValueError):
        return {}
