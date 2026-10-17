"""Walkthrough chapter 18, Area Z: the final battle, and the ending (2026-10-17).

Source: data/walkthrough/dim/18-area-z.json and 19-ending.json, data/maps/dim/f36.json (Area
E B4) and f43.json (Area Z, area 43), docs/event-map.md S52-S53, docs/npc-map.md 5.12, and
the code (rips/re/decomp): MAZE square_arrive 0x800ba48c, square_examine 0x800bb790,
maze_prompt_result 0x800befcc, the event follow-ups FUN_800c1070, the after-battle handler
FUN_800c0748, MCARD talk_scene_warning 0x800dbdd4, JOUKA town_main 0x800a2198 and
king_ending 0x800a52cc. Site squares E x N y are the game's (x, 23 - y).

What the code does:
- B4 E12 N13 (36, 12, 10) is a lift, record 0x17 [10, 17, 43, 0]: to Area Z (10, 17). nav
  plans it from town (probe_start.py on c17v6b/c17_end: 12 legs, no flag needed).
- Area Z E10 N8 (43, 10, 15), record 0x68 (square_arrive case 0x68): while bit 0x80 of
  maze_event_flags (0x80079b48) is clear and no party member has a title (roster +0xc5
  bit 0), it sets the bit and starts talk 26 (talk_party 0x1a), talk_scene_warning, which in
  area 0x2b (talk_script_status 4) says NPC_MES5 108-111. maze_event_flags is cleared on
  each floor load (square_arrive 0x800ba48c type 0x17 path, FUN_800a42c8 and others), so
  the bit is only a proof while the party is still in Area Z; the same record in Area B B2,
  D B1 and E B4 sets the same bit on those floors.
- Area Z E10 N10 (43, 10, 13), record 0x5d (square_examine case 0x5d), facing north: with
  the RING OF MEDIUM (item 0x142) in the party or a titled member, EVENTMES 232 (nothing
  happens); else EVENTMES 229 and prompt 0x1c. Yes: EVENTMES 230 and follow-up 0x25, which
  sets 0x80079bf1 = 0x12 (Quetzalcoatl's fixed fight) and 0x80079b5f = 0x10; No: 231.
  After the fight (FUN_800c0748, 0x80079b5f 0x10): EVENTMES 233, follow-up 0x2b: 234 (or
  236 for the golem route), 0x2c: 298 (RING OF MEDIUM), 0x2d: 299, 0x2e: the ring given
  (0x800cbb0c(0x142)), facing north, FUN_800ad040(2, 11, 11): Shrine 2F E11 N12, the altar.
- Town: town_main state 2 (0x800a2198, around 0x800a2f00) looks for 0x142 in the packs of
  the members still in the party, after the arrival step has moved every member at status
  0x20 or more (or HP 0) out of it, takes it, and sets town_state 45 (king_ending). So a
  ring on a dead member never starts the ending: the ring goes home with a living member.
- king_ending (0x800a52cc): camp_state 0 draws the audience (SISETU 360 on the bar), 5 waits,
  10 prints SISETU 322 and sets the title bit (+0xc5 bit 0) on every party member, 15 sets
  it again, adds 1,000,000 Gp to the first member (capped at 0x7fffffff), empties the
  party, snapshots roster and parties, plays DATA07/WIZAR07.STR, then rolls the credit
  pictures (0x80079c62 even strand, 0x80079c68 odd strand to 15) until START (pad 0x800 in
  0x80079740); then next_place 0xf8 (save from town) and town_state 0.

Found in the smoke runs (2026-10-17, ch18/smoke1, try_end1-3, try_cof1, ending_probe):
- The fight reads the party at (43, 10, 14), a square back from the relief, so both squares
  are BOSS_AT; with only the relief listed the fight wasn't a story fight (28 rounds, four
  dead). With both, the support plan runs: 20 of 20 won on the bench (ch18/qz, seeds 1-20,
  4-11 rounds, 27 deaths, 22 of them to its darkness breath).
- After a reload at the altar the last box stays drawn with nothing waiting (box_up true):
  clear_stale_box.
- A ring on a body: the walk home is ordinary, and the audience begins when the raised holder
  rejoins at the tavern (raise_then_ring). A standing holder with others down: the audience
  begins on arrival and those down get no title (the game's rule, town_main's arrival step).
- The audience: SISETU 360, then 322 in pages (0x80079a3e), the movie (about 4,100 frames),
  the credit roll (about 15,000), START, the Save screen saves by itself, then town state 1.
- Post-ending lock (a patch bug, fixed 2026-10-17 in asm/vwf_lut.inc): king_ending's DsPlay
  call (MAIN 0x800393f0) wrote into libds's play list at 0x80060f9c, where asm/vwf.asm had
  put the centering wrappers, and the next centered town text crashed (Reserved
  Instruction at 0x800a2004). docs/engine-notes.md has the story. The original Japanese
  disc goes from the save to the logo over an empty party, then the bar after circle;
  this goal's end check (town bar) is that.

Goals, each proved by RAM or a captured string:
  lift_z      the party in area 43 (maze.AREA).
  the_man     bit 0x80 of maze_event_flags in area 43 (talk 26 ran here), and NPC_MES5 110
              or 111 captured. Skipped by the game for a titled party: not expected here.
  coffin      the RING OF MEDIUM (0x142) in a pack, a won fight at (43, 10, 13) in the log
              (Quetzalcoatl, encounter 0x12: fixed, can't be run from), and EVENTMES 298
              captured. On BOSS_AT, so the support plan runs. ready()/door_ready()/heal()
              as chapter 17's control room. A wipe replays from the_man's state, which is in
              Area Z; after BOSS_WIPES failed tries each try trains on TRAIN_AREAS first.
  ending      the ring carried into town: every member's title bit (+0xc5 bit 0), the
              party's gold up by 1,000,000 or more, and SISETU 322 captured.
"""
import struct

from harness import battle, chapters, chapter1, gear, maze, nav, tactics, town, ui
from harness.game import Stuck

EV_FLAGS = 0x80079b48           # maze_event_flags, cleared on each floor load
MAN_BIT = 0x80                  # talk_scene_warning sets it
AREA_Z = 43
LIFT = (36, 12, 10)             # B4 E12 N13, record 0x17 to (43, 10, 17)
LANDING = (43, 10, 17)          # Area Z E10 N6
MAN = (43, 10, 15)              # E10 N8, record 0x68
BEFORE = (43, 10, 14)           # E10 N9, the hall, a square short of the relief
COFFIN = (43, 10, 13)           # E10 N10, record 0x5d, the relief on the north wall
ALTAR = (2, 11, 11)             # Shrine 2F E11 N12, where 0x2e puts the party
RING = 0x142                    # RING OF MEDIUM
TITLE_OFS, TITLE_BIT = 0xc5, 0x01
TOWN_STATE = 0x80079b18
CAMP_STATE = 0x80079669
NEXT_PLACE = 0x800796d2
CREDIT_A, CREDIT_B, CREDIT_B_POS = 0x80079c62, 0x80079c68, 0x800795d0
CREDIT_FADE = 0x800795d2        # the last picture fades in to 0x80
BOX_PAGE = 0x80079a3e           # the audience's text box: nonzero while its pages show
ENDING_STATE = 45
ENDING_MOST = 40000             # frames for the audience, the movie and the credits
CREDITS_MOST = 24000            # the roll alone (ending_probe: about 15,000 after a 4,100-frame movie)
SAVE_MOST = 6000                # frames for the save screen and the logo afterwards
SAVE_SCREEN = 0x32              # game_state: the Save screen (MCARD)
OVERWRITE_WAIT = 300            # frames on it before "Overwrite it?" gets Yes
# a failed coffin try trains here first (boss_training, after BOSS_WIPES): Area E B4, the
# floor chapter 17 trained these parties on (Greater Demons, level 18). Area Z itself has no
# fights but the coffin (f43.json: no fight records, no roamers).
TRAIN_AREAS = (36,)
PUSH_AREAS = TRAIN_AREAS        # the train-after-running rule (the walk crosses Area E)
# rated as a story fight whatever FIXED says. The fight itself reads the party one square
# back, at E10 N9 (smoke1, 2026-10-17: the fought record's where is (43, 10, 14), and
# tactics.story_fight was False with only COFFIN listed); nothing else fights in Area Z
FIGHT_AT = (COFFIN, BEFORE)
tactics.BOSS_AT.update(FIGHT_AT)


def here(g):
    return (g.u8(maze.AREA),) + g.pos()


def said(g, n, name, idx):
    return not g.cap or any(m['file'] == name and m['idx'] in idx for m in g.cap.messages[n:])


def ring_holders(g):
    """Roster indices of the members (maze party, or town party) with 0x142 in their pack."""
    out = []
    for i in g.party() or town.town_party(g):
        if any(it & 0x1ff == RING for it in g.char(i)['items']):
            out.append(i)
    return out


def titled(g, i):
    return bool(g.char(i)['raw'][TITLE_OFS] & TITLE_BIT)


def won_at(run, l0, where):
    """A fight at one of the squares in where since log index l0 that ended with nobody fled."""
    for x in run.log[l0:]:
        if len(x) > 2 and x[1] == 'fought' and isinstance(x[2], dict) \
                and tuple(x[2].get('where') or ()) in where:
            r = x[2]
            if r.get('ovl') not in ('JOUKA', 'HAZURE') and not (r.get('fled') or (0,))[0]:
                return True
    return False


def standing(g, i):
    """In the party after town_main's arrival step: status under 0x20 and HP above 0."""
    c = g.char(i)
    return c['status'] < 0x20 and c['hp'] > 0


def clear_stale_box(run):
    """After a reload at the altar the last box (EVENTMES 299) is still drawn with nothing
    waiting on it (game_state 0, no message, no event box): box_up() stays true and every
    wait reads it as a box (smoke1, ending try 2: "event box too long" at (2, 11, 11)). The
    first pass had it marked stale in Python, which a state doesn't keep. Mark it again."""
    g = run.g
    if maze.calm_but_box(g) and maze.box_up(g):
        maze.mark_stale_box(g)
        run.note('stale box marked', here(g))


def king_ending(run, from_town=False):
    """From the Grounds' entrance square: triangle into town with the ring (from_town: the
    audience has already begun in town), then the King's audience, the movie and the
    credits (START once the last picture is up), then out of the save screen. Returns a
    dict of what it saw."""
    g = run.g
    seen = dict(states=[], credits_done=False)
    if not from_town:
        ui.press_until(g, 'triangle', lambda: g.u8(0x8007967e) == 3 or not maze.in_maze(g), 120,
                       'triangle to town')
    end = g.frame + ENDING_MOST
    started = None
    last = None
    k = 0
    while g.frame < end:
        k += 1
        ts, cs = g.u8(TOWN_STATE), g.u8(CAMP_STATE)
        st = (g.overlay(), ts, cs, g.u8(BOX_PAGE))
        if st != last:
            seen['states'].append((g.frame,) + st)
            last = st
        if g.overlay() == 'JOUKA' and ts == ENDING_STATE:
            if 'party' not in seen:
                # who stands in the party as the audience begins, and their gold before the
                # award (camp_state 15 adds it and empties the party)
                seen['party'] = [i for i in g.party() or town.town_party(g)]
                seen['gold0'] = sum(g.char(i)['gold'] for i in seen['party'])
            roll = g.u16(CREDIT_B) in range(1, 16) and started is not None
            if cs == 0x0f and not g.u8(BOX_PAGE):
                # the movie, then the credits: no presses (one might cut the movie short).
                # The roll begins with the odd strand at 1 (0x80079c68); it's done when that
                # strand's last picture ("The End", 15) has stopped at 0 and faded in
                if started is None and g.u16(CREDIT_B) == 1 and s16(g, CREDIT_B_POS) > 0:
                    started = g.frame
                    seen['credits_start'] = g.frame
                done = roll and g.u16(CREDIT_B) == 15 and s16(g, CREDIT_B_POS) == 0 \
                    and s16(g, CREDIT_FADE) >= 0x80
                if done:
                    seen['credits_done'] = g.frame
                    g.step(60)
                    try:
                        g.shot('%s/ending_last' % run.out)
                    except Exception:
                        pass
                if done or (started is not None and g.frame - started > CREDITS_MOST):
                    ui.press_until(g, 'start', lambda: g.u8(TOWN_STATE) != ENDING_STATE, 600,
                                   'START after the credits')
                    break
                g.step()
                continue
            # the audience's boxes (SISETU 360's bar, then 322 in pages, 0x80079a3e counting
            # the page): circle, every 20 frames
            if k % 20 == 0:
                g.tap('circle')
            g.step()
            continue
        if g.overlay() == 'JOUKA' and g.u8(town.TOWN_MSG) and ts == 2:
            # arrival messages ("X was carried to the temple.") before the ring is found
            s0 = (g.u8(town.TOWN_MSG), ts, len(g.cap.messages) if g.cap else 0)
            ui.confirm_until(g, lambda: (g.u8(town.TOWN_MSG), g.u8(TOWN_STATE),
                                         len(g.cap.messages) if g.cap else 0) != s0, 240,
                             'town arrival message')
            continue
        g.step()
    seen['next_place'] = g.u8(NEXT_PLACE)
    # next_place 0xf8: the Save screen (MCARD, game_state 0x32) saves to the card by itself
    # ("Checking the memory card...", "Saving...": ending_probe, 2026-10-17), then town
    # state 1 shows the logo over an empty party and waits for circle (town_main gate on pad
    # 0x20). No presses during the save; circle after it until the bar has the input. A card
    # that already holds a save stops the screen at "Overwrite it?" with No selected: still
    # there after OVERWRITE_WAIT frames, up and circle once (vwffix endingrun, 2026-10-17).
    # The Japanese disc goes through the same states to the same bar (vwffix stage D).
    end = g.frame + SAVE_MOST
    in_save, seen['overwrite'] = None, False
    while g.frame < end and not town.in_town_bar(g):
        st = (g.overlay(), g.u8(maze.GAME_STATE), g.u8(TOWN_STATE))
        if st != last:
            seen['states'].append((g.frame,) + st)
            last = st
        if st[0] == 'MCARD' and st[1] == SAVE_SCREEN:
            in_save = g.frame if in_save is None else in_save
            if not seen['overwrite'] and g.frame - in_save >= OVERWRITE_WAIT:
                g.tap('up'); g.step(20); g.tap('circle')
                seen['overwrite'] = True
        if g.overlay() == 'JOUKA' and g.u8(TOWN_STATE) in (1, 2, 3, 4):
            g.tap('circle')
        g.step(20)
    seen['town_bar'] = town.in_town_bar(g)
    seen['end'] = (g.frame, g.overlay(), g.u8(maze.GAME_STATE), g.u8(TOWN_STATE))
    # (2026-10-17) before the VWF move (asm/vwf_lut.inc) the credits' DsPlay overwrote the
    # JOUKA centering wrapper and the next centered town text crashed here
    seen['locked'] = not seen['town_bar']
    if not seen['town_bar']:
        print('c18 ending: no town bar %d frames after the save (end %s)'
              % (SAVE_MOST, seen['end'],), flush=True)
    return seen


def s16(g, a):
    return struct.unpack('<h', g.e.read(a, 2))[0]


def raise_then_ring(run, party, h):
    """In town after an ordinary arrival with the ring on a body (try_end1, 2026-10-17: the
    trip home was quiet, and the audience began the moment the raised holder rejoined the
    party at the tavern, town_main's ring check running again on the way back to the bar).
    So the other members of the coffin's party are raised and rejoin first, the holder
    last, and the audience runs from there. Returns king_ending's dict, or None."""
    g = run.g
    first = lambda: next(k for k, x in enumerate(town.town_slots(g)) if x is not None)
    try:
        town.pool_gold(g, first(), 'tavern')
    except Stuck as s:
        run.note('pool stuck', s.what)
    town.to_town_bar(g)
    order = [i for i in party if i != h and i not in town.town_party(g)] + [h]
    for ri in order:
        for _ in range(3):
            if g.char(ri)['status'] == 0:
                break
            try:
                r = town.temple_heal(g, ri, first())
            except Stuck as s:
                run.note('temple stuck', g.char(ri)['name'], s.what)
                break
            run.log.append((g.frame, 'temple', ri, r))
            town.to_town_bar(g)
            if (r.get('outcome') if isinstance(r, dict) else r) in ('poor', 'lost'):
                break
        if g.char(ri)['status'] != 0:
            run.note('ending: not raised', g.char(ri)['name'], hex(g.char(ri)['status']))
            if ri == h:
                return None
            continue
        try:
            town.form_party(g, [ri])
            run.log.append((g.frame, 'rejoined', ri))
            town.to_town_bar(g)
        except Stuck as s:
            if g.u8(TOWN_STATE) != ENDING_STATE:
                run.note('rejoin stuck', g.char(ri)['name'], s.what)
                if ri == h:
                    return None
        if g.u8(TOWN_STATE) == ENDING_STATE or g.u8(TOWN_STATE) == 2:
            break
    if not ui_wait(g, lambda: g.u8(TOWN_STATE) == ENDING_STATE, 600):
        run.note('ending: no audience after the holder rejoined', g.u8(TOWN_STATE))
        return None
    return king_ending(run, from_town=True)


def ui_wait(g, cond, limit):
    for _ in range(limit):
        if cond():
            return True
        g.step()
    return cond()


@chapters.chapter
class Chapter18:
    n = 18
    title = 'Area Z: the final battle'

    def goals(self, run):
        g = run.g
        memo = {}

        def lift_z():
            if g.overlay() not in ('JOUKA', 'HAZURE') and g.u8(maze.AREA) == AREA_Z:
                return True
            run.fit()
            run.go(LANDING)
            run.after()
            return g.u8(maze.AREA) == AREA_Z

        def the_man():
            if g.u8(maze.AREA) == AREA_Z and g.u32(EV_FLAGS) & MAN_BIT:
                return True
            if any(titled(g, i) for i in g.party() or town.town_party(g)):
                run.note('the man: a titled member, the game skips him')
                return True
            n = len(g.cap.messages) if g.cap else 0
            run.go(MAN)
            run.after()
            if g.u8(maze.AREA) != AREA_Z or not g.u32(EV_FLAGS) & MAN_BIT:
                run.note('the man: no talk', here(g), hex(g.u32(EV_FLAGS)))
                return False
            if not said(g, n, 'NPC_MES5.OBJ', (110, 111)):
                run.note('the man: talk ran, NPC_MES5 110/111 not captured')
            return True

        def coffin():
            if ring_holders(g):
                return True
            if any(titled(g, i) for i in g.party() or town.town_party(g)):
                raise chapter1.Blocked('a titled member: the relief stays silent (EVENTMES 232)')
            l0 = len(run.log)
            n = len(g.cap.messages) if g.cap else 0
            run.ready()
            run.go(BEFORE)
            while run.door_ready():
                run.ready(train=False)
                run.go(BEFORE)
            run.heal()
            run.examine(COFFIN, 0, fight=True)
            # 233, 234, 298, 299 and the move to the altar come after the fight
            if g.overlay() not in ('JOUKA', 'HAZURE') and not maze.calm(g):
                run.after()
            if not ring_holders(g):
                run.note('coffin: no ring', here(g))
                return False
            if not won_at(run, l0, FIGHT_AT):
                run.note('coffin: ring but no won fight in the log', here(g))
            if not said(g, n, 'EVENTMES.BIN', (298,)):
                run.note('coffin: EVENTMES 298 not captured')
            if here(g) != ALTAR:
                run.note('coffin: not at the altar', here(g))
            return True

        def ending():
            ids = memo.get('ids')
            if ids and all(titled(g, i) for i in ids):
                return True
            if g.overlay() in ('JOUKA', 'HAZURE') and not ring_holders(g):
                run.note('ending: in town without the ring')
                return False
            if not ring_holders(g):
                run.note('ending: no ring')
                return False
            if g.overlay() not in ('JOUKA', 'HAZURE'):
                clear_stale_box(run)
                if not maze.calm(g):
                    run.after()
                chapter1.cure_in_camp(g, run.log, on_int=run.on_int)
            h = ring_holders(g)[0]
            if g.overlay() not in ('JOUKA', 'HAZURE') and not standing(g, h):
                # the ring on a body: an ordinary walk home (town_main moves the dead out of
                # the party before it looks for the ring, so no audience on arrival), then
                # the temple; the audience begins when the raised holder rejoins
                party = list(g.party())
                memo['ids'] = party
                run.note('ending: ring holder down, temple first', g.char(h)['name'],
                         [g.char(i)['name'] for i in party if not standing(g, i)])
                run.trip_end('ring holder down')
                nav.to_town(g, run.on_int, lambda g: run.after())
                n = len(g.cap.messages) if g.cap else 0
                gold0 = sum(g.char(i)['gold'] for i in party)
                seen = raise_then_ring(run, party, h)
                if seen is None:
                    return False
                return proved(party, gold0, seen, n)
            if g.overlay() in ('JOUKA', 'HAZURE'):
                run.ensure_maze()
            party = g.party()
            down = [i for i in party if not standing(g, i)]
            if down:
                # the holder stands, so a trip home is the ending: those down get no title
                run.note('ending: members down, no title for them', [g.char(i)['name'] for i in down])
            ids = [i for i in party if standing(g, i)]
            gold0 = sum(g.char(i)['gold'] for i in ids)
            memo['ids'] = ids
            run.note('ending: party', [(g.char(i)['name'], g.char(i)['level']) for i in ids],
                     'ring on', g.char(h)['name'], 'gold', gold0)
            if chapter1.GEAR and gear.loot_work(g):
                gear.camp_loot(g, run.log, on_int=run.on_int)
            chapter1.heal_in_camp(g, run.log, on_int=run.on_int)
            if g.u8(maze.AREA) != 0:
                nav.travel(g, (0,) + maze.ENTRANCE[0], run.on_int, lambda g: run.after())
            hs = [i for i in ring_holders(g) if standing(g, i)]
            if not hs:
                # lost on the way (a death to a roamer): the next try starts from the coffin
                run.note('ending: no standing ring holder at the entrance', ring_holders(g))
                return False
            maze.walk_to(g, *maze.ENTRANCE[0], run.on_int)
            if not maze.calm(g):
                maze.settle(g)
            n = len(g.cap.messages) if g.cap else 0
            ids = [i for i in g.party() if standing(g, i)]
            gold0 = sum(g.char(i)['gold'] for i in ids)
            memo['ids'] = ids
            seen = king_ending(run)
            return proved(ids, gold0, seen, n)

        def proved(ids, gold0, seen, n):
            """Every member in the party at the audience titled, their gold up 1,000,000
            (all of it on the first member), SISETU 322 captured."""
            if seen.get('party'):
                ids, gold0 = seen['party'], seen['gold0']
            got = [titled(g, i) for i in ids]
            gold1 = sum(g.char(i)['gold'] for i in ids)
            run.note('ending', dict(seen, titled=[(g.char(i)['name'], t) for i, t in zip(ids, got)],
                                    gold=(gold0, gold1), k322=said(g, n, 'SISETU.OBJ', (322,))))
            print('c18 ending: titles %s, gold %d -> %d, credits %s, states %s' % (
                got, gold0, gold1, seen['credits_done'], seen['states'][:12]), flush=True)
            if not all(got):
                return False
            if gold1 - gold0 < 1000000 and gold1 < 0x7fffffff:
                run.note('ending: gold short', gold0, gold1)
                return False
            if not said(g, n, 'SISETU.OBJ', (322,)):
                run.note('ending: SISETU 322 not captured')
            return True

        yield from run.recover_goals()
        yield 'lift_z', lift_z
        yield 'the_man', the_man
        yield 'coffin', coffin
        yield 'ending', ending
