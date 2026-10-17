"""Walkthrough chapter 17, Area E: the door marked BRIDGE (2026-10-16).

Source: data/walkthrough/dim/17-area-e.json, data/maps/dim/mimicry/f18.json (Area X after
mimicry mode) and f36-f38.json (Area E B4 to B2, areas 36-38), the glyph pad 0x800b989c
(word 4 COCKPIT, FUN_800ba32c), npc_availability (MAIN 0x80018bd4) and fixed_meet_table
(0x8005e6ac; A-maze.md "Which party, where"), and MCARD talk_scene_control_room
0x800d97e4. Site squares E x N y are the game's (x, 23 - y).

nav plans the walkthrough's route by itself once story bit 20 is set: Area X's middle
door east of E12 N13 (12, 10) (record 0x2d sealed until bit 20), the lift at E13 N12 (13,
11) to E-B2 E12 N11 (12, 12), north through the ENTER door, round to the stairs at E12 N6
(12, 17), B3 E12 N5 to the ladder at E10 N5 (10, 18), B4's hidden door, the BRIDGE door.

Goals, each proved by RAM or a captured string:
  cockpit      story_flags (0x80079b44) bit 20: COCKPIT at Area X's pedestal (chapter6.
               pedestal_word; word 4 of the pad's list, 0x800ef3a4 + 40, needs the gold
               stone, bit 3 of the Tablet).
  area_e       the party on E-B2 E12 N11 (38, 12, 12), the lift's landing. On the way the
               party meets Cleo at B2 E12 N14 (12, 9) (fixed meeting 0x18, talk 24, "Cleo
               reporting to the King", while npc_flags bit 24 is clear): talked through.
  hidden_door  bit 23 of the hidden doors found (0x80079628): B4's hidden door north of E11
               N21 (11, 2) (type 3, p1 23), found by nav's walk to the passage beyond, E11
               N22 (11, 1).
  bridge       the glyphs on the door north of B4 E12 N6 (12, 17) (0x20, EVENTMES 245).
               No flag; proved by the captured string.
  control_room the fixed meeting 0x19, party 3 at B4 E12 N12 (12, 11), placed while
               npc_flags (0x80079754) bit 2 is clear: talk 25, NPC_MES4 45-54, then fight
               encounter 0xf (encounter_source 4). The talk sets bit 2 before the fight
               starts, so the proof is bit 2 and a won fight at (36, 12, 11) in the log
               (back in the maze, nobody fled). encounter_id 0xf can't be run from
               (battle.fleeable). A wipe replays the goal from its start state.
  train_easy_NN (Chris, 2026-10-17) before the control room, training trips on Area C B3
               (EASY_AREAS) until every member is TRAIN_UP levels above the level they
               reached the training at (train_goals' need).
  train_NN     then trips on B4 (TRAIN_AREAS: its fight squares meet the Greater Demons,
               level 18, over 25,000 experience each, six at a time and calling more) for
               TRAIN_UP_B4 levels more.
  out          back in town.
Not done: B3's magic switch past the hidden door east of E2 N11 (a detour), B2's
transporter at E11 N7 (record 0x1a), and the lift on to Area Z.
"""
from harness import battle, chapters, chapter6, maze, nav, tactics, town

STORY = 0x80079b44
NPC_FLAGS = nav.NPC_FLAGS
PAD_WORDS = 0x800ef3a4          # seven words of ten glyphs (A = 0, 0xff pad)
COCKPIT_BIT = 20
LANDING = (38, 12, 12)          # E-B2 E12 N11, the lift from Area X lands here
DOOR_P1 = 23                    # B4's hidden door north of E11 N21
BEYOND = (36, 11, 1)            # E11 N22, past it
BRIDGE = (36, 12, 17)           # E12 N6, the door marked BRIDGE on its north side
BEFORE = (36, 12, 12)           # E12 N11, a square short of the meeting
MEET = (36, 12, 11)             # E12 N12, Cleo, Bergamot and the last Guardians
MEET_BIT = 2                    # npc_flags: set by talk 25 as the fight starts
TRAIN_AREAS = (36,)             # Area E B4: the Greater Demons (boss training)
# (Chris, 2026-10-17, c17v4) the first TRAIN_UP levels come on an easier floor, away from
# Area E's roaming caster parties: Area C B3 (area 29, chapter 15's Area C). Its room and
# roaming tables have no spellcasters (Were Amoeba, Blob, Dark Kong, Shocitnal) and its
# roaming parties (P4, P5: Blade Master, Fay, Ixtah, a level-11 Mad Psionic with Lios and
# Masios) have no Tiltowait, Lasios or Galtomas. Area D's floors pay more (D B3 about
# 27,500 a room fight by the site's spawn data, C B3 16,000) but Area D's roaming party P6
# is Area E's P7 two levels down (Kel with Tiltowait, a Mad Psionic with Lasios and
# Galtomas): chapter 14's runs had 0.75 deaths a fight on D B3, nearly a quarter to a
# confused ally. C B3's runs: 0.26. Area A B3/B2 (chapter 16's floors) pay 6,000.
EASY_AREAS = (29,)
PUSH_AREAS = EASY_AREAS         # the train-after-running rule trains there too (push_train)
TRAIN_UP = 2                    # levels every member gains on EASY_AREAS first
TRAIN_UP_B4 = 2                 # then on B4 (TRAIN_AREAS), from the levels the easy floor left
TRAIN_MOST = 40                 # training trips at most for each
tactics.BOSS_AT.add(MEET)       # rated as a story fight whatever FIXED says
# battle.control_policy for the meeting (Report 6) is off (Chris, 2026-10-17): the bench had
# it at 12/36 won against the default with the support plan's 15/29, Arch Bishop kills 11 ->
# 44. The code stays; CR_POLICY = True registers it again.
CR_POLICY = False
if CR_POLICY:
    battle.POLICY_AT[MEET] = battle.control_policy


def here(g):
    return (g.u8(maze.AREA),) + g.pos()


def said(g, n, idx):
    return not g.cap or any(m['file'] == 'EVENTMES.BIN' and m['idx'] == idx
                            for m in g.cap.messages[n:])


def won_here(run, l0):
    """A fight at MEET in the log since l0 that ended back in the maze with nobody fled."""
    for x in run.log[l0:]:
        if len(x) > 2 and x[1] == 'fought' and isinstance(x[2], dict) \
                and tuple(x[2].get('where') or ()) == MEET:
            r = x[2]
            # fled is (escaped, failed) run counts, so (0, 0) is a tuple, and truthy
            if r.get('ovl') not in ('JOUKA', 'HAZURE') and not (r.get('fled') or (0,))[0]:
                return True
    return False


@chapters.chapter
class Chapter17:
    n = 17
    title = 'Area E: the door marked BRIDGE'

    def goals(self, run):
        g = run.g

        def cockpit():
            if nav.flag(g, STORY, COCKPIT_BIT):
                return True
            word = list(g.e.read(PAD_WORDS + 40, 7))
            if word != [ord(c) - ord('A') for c in 'COCKPIT']:
                run.note('pad word 4 is not COCKPIT', word)
            run.fit()
            return chapter6.pedestal_word(run, 'COCKPIT', COCKPIT_BIT)

        def area_e():
            if not nav.flag(g, STORY, COCKPIT_BIT):
                return False
            if g.overlay() not in ('JOUKA', 'HAZURE') and g.u8(maze.AREA) in (36, 37, 38, 39):
                return True
            run.fit()
            run.go(LANDING)
            run.after()
            return g.u8(maze.AREA) == 38

        def hidden_door():
            if nav.hidden_found(g, DOOR_P1):
                return True
            if not nav.flag(g, STORY, COCKPIT_BIT):
                return False
            run.fit()
            run.go(BEYOND)
            run.after()
            return nav.hidden_found(g, DOOR_P1)

        def bridge():
            if not nav.hidden_found(g, DOOR_P1):
                return False
            n = len(g.cap.messages) if g.cap else 0
            run.fit()
            run.examine(BRIDGE, 0)
            return here(g) == BRIDGE and said(g, n, 245)

        def control_room():
            if nav.flag(g, NPC_FLAGS, MEET_BIT):
                return True
            if not nav.hidden_found(g, DOOR_P1):
                return False
            l0 = len(run.log)
            run.ready()
            run.go(BEFORE)
            while run.door_ready():
                run.ready(train=False)
                run.go(BEFORE)
            run.heal()
            for _ in range(3):
                run.go(MEET)
                run.after()
                if nav.flag(g, NPC_FLAGS, MEET_BIT):
                    break
            if not nav.flag(g, NPC_FLAGS, MEET_BIT):
                run.note('no meeting at the control room', here(g))
                return False
            if not won_here(run, l0):
                run.note('control room: no won fight in the log', here(g))
                return False
            return run.all_home() or 'casualties'

        def out():
            if g.overlay() in ('JOUKA', 'HAZURE'):
                return True
            run.trip_home('chapter end')
            return g.overlay() in ('JOUKA', 'HAZURE')

        yield from run.recover_goals()
        yield 'cockpit', cockpit
        yield 'area_e', area_e
        yield 'hidden_door', hidden_door
        yield 'bridge', bridge
        if not nav.flag(g, NPC_FLAGS, MEET_BIT):
            # every member `up` levels above where they stand now (the generator runs this
            # once the previous goal is done, so "now" is the party that reached it): first
            # TRAIN_UP on the easy floor, then TRAIN_UP_B4 more on B4
            for areas, up, prefix in ((EASY_AREAS, TRAIN_UP, 'train_easy'),
                                      (TRAIN_AREAS, TRAIN_UP_B4, 'train')):
                want = {i: g.char(i)['level'] + up for i in (g.party() or town.town_party(g))}
                run.note('train target', 'control_room', areas,
                         [(g.char(i)['name'], g.char(i)['level'], w) for i, w in want.items()])

                def need(want=want):
                    here_ = set(g.party() or town.town_party(g))
                    return [i for i, w in want.items() if i in here_ and g.char(i)['level'] < w]
                yield from run.train_goals(areas, 0, prefix=prefix, most=TRAIN_MOST, need=need)
        yield 'control_room', control_room
        yield 'out', out
