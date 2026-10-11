#!/usr/bin/env python3
"""Write docs/re/C-talk-lines.md: where and when every NPC_MES1-5 string plays.

    talkscripts.py --json rips/re/work/C/scripts.json      (first, to dump the scripts)
    talklines.py [--json rips/re/work/C/scripts.json] [--out docs/re/C-talk-lines.md]

The script arrays come from talkscripts.py, which runs each talk handler over a RAM
dump. What each array is for and when each block is picked was read by hand from the
decompiled handlers (docs/re/C-talk.md) and is written down below, in ARRAYS, BLOCKS
and VARS. Strings a script takes from a global at run time (talk_str_a 0x800795d6,
talk_str_b 0x80079c6c, talk_topic_str 0x800796d0) are listed in VARS, from the code
that stores them.
"""
import json, os, sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
NAMES = {0: 'Guy', 1: 'Balbo', 2: 'Fontana', 3: 'scholars', 4: 'Zaril'}

# (handler, array base) -> (what it is, how the block is chosen)
ARRAYS = {
    (0, 0x18): ('greeting', 'greet_guy picks the block on meeting'),
    (0, 0xba8): ('chat', 'Talk with everyone introduced and no service: rand_upto(11) topic, block by stage (1/2/3); 33 and 40-44 are location or story topics kept 90%'),
    (0, 0x2ed0): ('farewell', 'Leave: by speaker, alignment and dead members'),
    (0, 0x3768): ('introductions', 'Talk with nobody introduced to Guy: block by stage'),
    (0, 0x39c0): ('healing', 'heal offer (someone hurt, 50%): Guy blocks 0-12, Alstron 13-24'),
    (0, 0x3cb0): ('sale', 'sale offer: 0 offer, 1 pick, 2 can\'t pay, 3 declined, 4 obtained'),
    (0, 0x3d48): ('rescue', 'rescue offer: 0 offer, 1 yes (fee: all gold), 2 no; 3-4 are the sale\'s tail, not run here'),
    (0, 0x3de0): ('fight', 'Fight: 0 warning and question, 1 declined'),
    (1, 0x18): ('greeting', 'greet_balbo picks the block on meeting'),
    (1, 0xbf8): ('introductions', 'Talk with nobody introduced: 0-2 Balbo Evil by stage, 3-5 Balbo Good by stage; 6-8 re-introduction when only some are'),
    (1, 0x1300): ('farewell', 'Leave: talk_str_b picked by speaker, alignment and dead members'),
    (1, 0x1350): ('healing', 'heal offer: Balbo blocks 0-11, Rosea 12-23'),
    (1, 0x1620): ('sale', 'sale offer (needs progress_bits & 4): 0 offer, 1 pick, 2 can\'t pay, 3 declined, 4 obtained'),
    (1, 0x16b8): ('rescue', 'rescue offer: 0 offer, 1 yes (fee: every item), 2 no; 3-4 are the sale\'s tail'),
    (1, 0x17d8): ('chat', 'rand_upto(11) topic pair, first block for stage 1, second for stages 2-3; 29-31 location topics at stage 3'),
    (1, 0x30d8): ('fight', 'Fight: 0 warning and question, 1 declined'),
    (2, 0x18): ('greeting', 'greet_fontana picks the block on meeting'),
    (2, 0x568): ('introductions', 'Talk with nobody introduced: block by stage'),
    (2, 0x7c0): ('farewell', 'Leave: by speaker'),
    (2, 0x838): ('healing', 'heal offer: Artemisia 0-8, Cephala 9-20 (stage 3 always Cephala; her table is off by one)'),
    (2, 0xab8): ('chat', 'rand_upto(7) topic pair (stages 1-2, stage 3); stage-1 specials; 24 in areas 0x20-0x23 before the maze changes'),
    (2, 0x1e40): ('sale', 'sale offer (needs progress_bits & 4): 0 offer, 1 pick, 2 can\'t pay, 3 declined, 4 obtained'),
    (2, 0x1ed8): ('rescue', 'rescue offer: 0 offer, 1 yes (fee: half the gold, odd slots), 2 no; 3-4 are the sale\'s tail'),
    (2, 0x1f70): ('fight', 'Fight: 0 warning and question, 1 declined'),
    (3, 0x10): ('greeting', 'greet_cresson picks the block on meeting'),
    (3, 0x560): ('introductions', 'Talk: 0/1 nobody introduced (stage 1/2), 2/3 only some'),
    (3, 0x880): ('farewell', 'Leave: talk_str_b 7 or 5 (stage 1), 0x9b or 0x9a (stage 2)'),
    (3, 0x8a8): ('healing', 'heal offer: Cleo blocks 0-6, Bergamot 7-13'),
    (3, 0xa50): ('decipher check', 'Talk, 50%: 0 under 100% (shows the match), 1 at 100% (sets marks[0] bit 1)'),
    (3, 0xab0): ('chat', 'Talk: by stage, story_flags bits 5-6 and progress_bits'),
    (3, 0x1e38): ('primer', 'first Talk after the introductions while story_flags bit 29 is clear: 0 Cresson, 1 nameless (turns on camp Decipher)'),
    (4, 0x18): ('greeting', 'greet_zaril picks the block on meeting'),
    (4, 0x1f8): ('introductions', 'Talk: 0 nobody introduced to Zaril, 1 only some'),
    (4, 0x388): ('farewell', 'Leave: talk_str_b by speaker and dead members'),
    (4, 0x3d8): ('chat', 'Talk: rand_upto(13), 1 rerolled; block 1 on the second Talk press'),
    (4, 0xec8): ('sale', 'sale offer (progress_bits > 0xd): 0 offer, 1 pick, 2 can\'t pay, 3 declined, 4 obtained'),
    (4, 0xf60): ('fight', 'Fight: 0 warning and question, 1 declined (then a battle, encounter 0xe)'),
}

SCENES = {
    6: 'scene: Guy\'s party and Lychee, then the seal explanation (block by stage)',
    7: 'scene: Guy\'s statue warning (talk_str_b: 1:88 met Guy, 1:89 not; bug, 1:87 meant)',
    8: 'scene: Guy\'s statue warning (1:86 met Guy, 1:295 not)',
    9: 'scene: the Ruby Slippers',
    10: 'scene: Guy resting before the trap room; block 0 met Guy, 1 not',
    11: 'scene: Balbo\'s two-switch door; 0-2 other alignment, 3-5 same; 1/4 yes, 2/5 no',
    12: 'scene: Balbo after the switches, then his menu',
    13: 'scene: Balbo, blue stone (2:83 met, 2:82 not)',
    14: 'scene: Balbo, center room (2:85 met, 2:84 not)',
    15: 'scene: Balbo, iron bars (2:87 met, 2:86 not)',
    16: 'scene: Balbo, three discs (2:89 met, 2:88 not)',
    17: 'scene: Balbo, the treasure ahead (2:264 met, 2:265 not)',
    18: 'scene: Fontana met in the maze, then his menu',
    19: 'scene: the statue with a slot for the Tablet of the Sun; 0/2 not met Fontana, 1/3 met',
    20: 'scene: Fontana\'s party splits up; 0 not met Fontana, 1 met',
    21: 'scene: the pit; 0 the fall (talk_str_b 93/97 base), 2 Guy, 3 Balbo, 4 man in armor; 1 never',
    22: 'scene: Cresson on Cleo and Bergamot',
    23: 'scene: the 26-glyph tablet; 0 met Cleo, 1 not',
    24: 'scene: Cleo going to the King (talk_str_b: 4:42 met, 4:43 not)',
    25: 'scene: the control room; 1 met Cleo (the reveal), 0 not; then a battle',
    26: 'scene: the mysterious man\'s warning',
    27: 'scene: Agan',
    28: 'scene: Zaril\'s party attacked',
}

# handler 18's script is built behind a branch the dumper doesn't follow; read by hand
MANUAL = {18: [(0x10, 0, [[0, 'say', 74]])]}

# (handler, base, block) -> when that block plays, where it isn't plain from ARRAYS
BLOCKS = {
    (0, 0x18): {0: 'Guy turned Evil, compatible, met before', 2: 'maze changed', 3: 'maze changed',
                4: 'the reward: gave the Ruby Slippers, not yet rewarded (+10,000 G)',
                5: 'first meeting, Guy Good', 6: 'first meeting, Guy Evil',
                37: 'Fritillaria introduces herself', 40: 'Lilia introduces herself',
                38: 'never picked', 39: 'never picked', 41: 'never picked', 42: 'never picked'},
    (0, 0xba8): {9: 'never played (rerolled)', 10: 'never played (rerolled)', 11: 'never played (rerolled)',
                 33: 'stage 1, progress_bits < 0x200, outside the location areas',
                 40: 'areas 1-4 before the walls change', 41: 'areas 0x13-0x16 after the maze changes',
                 42: 'areas 0x17-0x1b without the Tablet\'s stone bit 2', 43: 'areas 0x20-0x23 before the maze changes',
                 44: 'progress_bits & 0x200 and a member with flag +0xc5 bit 0'},
    (0, 0x39c0): {1: 'healthy', 2: 'stage 1, any status', 3: 'out of magic (20%)', 4: 'stage 2, stone/dead/poison',
                  5: 'stage 2, paralysis', 6: 'stage 3, stone/dead', 7: 'stage 3, paralysis', 8: 'stage 3, poison',
                  9: 'stage 1 HP', 10: 'stage 2 HP', 11: 'stage 3 HP', 12: 'cancelled', 14: 'healthy',
                  15: 'out of magic (20%)', 16: 'stage 1, stone/dead', 17: 'stage 1, paralysis', 18: 'stage 1, poison',
                  19: 'never (needs stages 2 and 3 at once)', 20: 'stage 2, dead', 21: 'stage 3, dead or ashes: Kadorto (always works)',
                  22: 'stages 1-2 HP', 23: 'stage 3 HP', 24: 'cancelled'},
    (1, 0x18): {0: 'Balbo turned Good', 1: 'Balbo back to Evil', 2: 'maze changed', 3: 'maze changed',
                4: 'first meeting, incompatible', 5: 'first meeting, compatible'},
    (1, 0x1350): {1: 'healthy', 2: 'out of magic (20%)', 3: 'stage 1, any status', 4: 'stage 2, stone/dead/poison',
                  5: 'stage 3, stone/dead', 6: 'paralysis (stages 2-3)', 7: 'stage 3, poison', 8: 'stage 1 HP',
                  9: 'stage 2 HP', 10: 'stage 3 HP', 11: 'cancelled', 13: 'healthy', 14: 'stages 1-2, dead or ashes',
                  15: 'stages 1-2, paralysis', 16: 'stages 1-2, poison', 17: 'stage 3, poison/paralysis/stone',
                  18: 'stage 3, dead or ashes: Kadorto (always works)', 19: 'out of magic (20%)',
                  20: 'stage 1 HP', 21: 'stage 2 HP', 22: 'stage 3 HP (bug: 2:135 with Madi; 2:134 meant)', 23: 'cancelled'},
    (1, 0x17d8): {6: 'never played (rerolled)', 7: 'never played (rerolled)', 8: 'never played (rerolled)',
                  27: 'never picked', 28: 'never picked',
                  29: 'stage 3, areas 5-8, Tablet stone bit 4 missing', 30: 'stage 3, areas 0x13-0x16, stone bit 0x20 missing',
                  31: 'stage 3, areas 0x1c-0x1f, stone bit 0x80 missing'},
    (2, 0x18): {0: 'maze changed', 1: 'maze changed', 2: 'first meeting'},
    (2, 0x838): {1: 'healthy', 3: 'can\'t treat', 8: 'cancelled',
                 10: 'healthy', 11: 'played for stone/dead at stage 1 (shifted)', 12: 'played for paralysis (shifted; casts Latumofis)',
                 13: 'played for poison (shifted; casts Madi)', 14: 'played for status at stages 2-3 (shifted)',
                 15: 'played for stage 2 dead (shifted): Kadorto (always works)', 16: 'played for stage 3 dead (shifted)',
                 17: 'played for "out of magic" (shifted; heals)', 20: 'cancelled'},
    (2, 0xab8): {6: 'never played (rerolled)', 7: 'never played (rerolled)', 8: 'never picked',
                 9: 'stage 1 special (90%)', 10: 'stage 1 special (90%)', 15: 'stage 1 special (90%)',
                 16: 'stage 1 special (90%)', 19: 'stage 1 special (90%)', 24: 'areas 0x20-0x23 before the maze changes'},
    (3, 0x10): {0: 'maze changed, not introduced', 1: 'maze changed, introduced', 2: 'first visit',
                3: 'not introduced', 4: 'Cleo greets', 5: 'Cleo and Bergamot or Cresson',
                6: 'stage 2, Cresson alone, not met', 7: 'stage 2, Cresson alone, met'},
    (3, 0x8a8): {1: 'healthy', 2: 'poison/paralysis/stone: Madi', 3: 'dead or ashes: Kadorto (always works)',
                 4: 'out of magic (20%)', 5: 'HP: Madi', 6: 'cancelled', 8: 'healthy', 9: 'status: Madi',
                 10: 'stage 2, dead or ashes: Kadorto (always works)', 11: 'out of magic, or stage 1 stone/dead',
                 12: 'HP: Madi', 13: 'cancelled'},
    (4, 0x18): {0: 'first meeting', 1: 'seen, not introduced', 2: 'never picked', 3: 'never picked',
                4: 'Zaril greets', 5: 'Gaura or Fritillaria greets'},
}

# strings a script reads from a global: (file, first, last, where, when), or
# (file, [indexes], where, when)
VARS = [
    (1, list(range(2, 16)) + list(range(19, 24)), 'greet_guy (talk_str_a)', 'member greetings, random speaker'),
    (1, [14, 20, 21, 22], 'greet_guy (talk_str_b)', 'greetings'),
    (1, 0x35, 0x40, 'Guy variant 0x800bdc08', 'introduced, compatible greeting'),
    (1, 0x2e, 0x34, 'Guy variant 0x800bd898', 'introduced greeting'),
    (1, 0x41, 0x48, 'Guy variant 0x800be88c', 'introduced greeting'),
    (1, 0x49, 0x4d, 'Guy variant 0x800bf3b8', 'introduced greeting'),
    (1, 0x4e, 0x4f, 'Guy variant 0x800bf174', 'introduced greeting'),
    (1, 0x10, 0x11, 'Guy variant 0x800bd4a4 (talk_str_b)', 'greeting'),
    (1, 0x71, 0x72, 'Guy variant 0x800bd4a4 (talk_str_b)', 'greeting'),
    (1, 0x122, 0x123, 'Guy variant 0x800bf174', 'introduced greeting'),
    (1, 0x125, 0x127, 'Guy variant 0x800bf3b8', 'introduced greeting'),
    (1, 0x119, 0x11d, 'talk_guy (talk_topic_str)', 'chat topic bar line'),
    (1, 0xaa, 0xaa, 'talk_guy (talk_str_b)', 'set in the handler'),
    (1, 0x58, 0x59, 'handler 7', 'statue warning (88 met Guy, 89 not)'),
    (1, 0x56, 0x56, 'handler 8', 'statue warning, met Guy'),
    (1, 0x127, 0x127, 'handler 8', 'statue warning, not met Guy'),
    (1, 0x50, 0x51, 'handler 9', 'Ruby Slippers request (80 met Guy, 81 not)'),
    (1, 0x53, 0x55, 'handler 9', 'Ruby Slippers answer: 83 no, 84 none in packs, 85 given'),
    (2, 7, 20, 'greet_balbo (talk_str_a)', 'greetings by speaker and descriptor'),
    (2, 0x23, 0x23, 'talk_balbo (talk_str_a)', ''),
    (2, 0x2d, 0x2d, 'talk_balbo (talk_str_a)', ''),
    (2, [0x2f, 0x30, 0x31, 0x33] + list(range(0x36, 0x41)) + list(range(0x41, 0x48)), 'Balbo variants 0x800cd104 0x800cd600 0x800cda60 0x800cdfd4 0x800cf878', 'introduced greetings'),
    (2, 3, 4, 'Balbo variant 0x800ccfac (talk_str_b)', 'greeting'),
    (2, 0x5e, 0x5f, 'Balbo variant 0x800ccfac (talk_str_b)', 'greeting'),
    (2, list(range(21, 35)) + list(range(36, 45)) + [46], 'talk_balbo farewell (talk_str_b)', 'Leave: 21-25 by speaker, 26 not met, 27-31/32 by alignment, 33-46 with a dead member named'),
    (2, 0x95, 0x95, 'talk_balbo (talk_str_b)', ''),
    (2, 0x52, 0x59, 'handlers 13-16', 'scene lines (odd met Balbo)'),
    (2, 0x108, 0x109, 'handler 17', 'scene line'),
    (3, 2, 6, 'greet_fontana (talk_str_a)', 'greeting by speaker'),
    (3, list(range(0x21, 0x2c)) + list(range(0x2c, 0x32)) + list(range(0x33, 0x3c)) + list(range(0x3c, 0x43)), 'Fontana variants 0x800d3664 0x800d3fd4 0x800d42d4 0x800d47ec 0x800d4da4', 'introduced greetings'),
    (3, 7, 8, 'Fontana variant 0x800d3bd8 (talk_str_b)', 'greeting'),
    (3, 0x6d, 0x6e, 'Fontana variant 0x800d3bd8 (talk_str_b)', 'greeting'),
    (3, list(range(12, 18)) + list(range(21, 25)) + list(range(27, 33)), 'talk_fontana farewell (talk_str_b)', 'Leave'),
    (3, 0x9e, 0x9e, 'talk_fontana (talk_str_b)', ''),
    (3, 0x5d, 0x64, 'handler 21 (talk_str_b + 0..3)', 'the pit: 93-94 met Fontana, 97-98 not (95-96, 99-100 never)'),
    (4, 2, 4, 'greet_cleo_line (talk_str_b)', 'Cleo\'s greeting'),
    (4, 0x38, 0x38, 'greet_cleo_line (talk_str_b)', 'Cleo\'s greeting'),
    (4, 9, 13, 'greet_bergamot_line (talk_str_a)', 'Bergamot\'s greeting'),
    (4, 0x86, 0x86, 'greet_bergamot_line (talk_str_a)', 'Bergamot\'s greeting'),
    (4, 14, 16, 'greet_cresson_line (talk_str_a)', 'Cresson\'s greeting'),
    (4, 18, 18, 'greet_cresson_line (talk_str_a)', 'Cresson\'s greeting, the usual one'),
    (4, 21, 21, 'greet_cresson_line (talk_str_a)', 'Cresson\'s greeting'),
    (4, 5, 7, 'talk_cresson farewell (talk_str_b)', 'Leave'),
    (4, 0x9a, 0x9b, 'talk_cresson farewell (talk_str_b)', 'Leave, stage 2'),
    (4, 0x2a, 0x2b, 'handler 24', 'Cleo\'s report'),
    (5, 0x7a, 0x7b, 'greet_zaril (talk_str_a)', 'Fritillaria / Gaura greet before you\'ve met them'),
    (5, 13, 17, 'greet_fritillaria_line (talk_str_a)', 'Fritillaria\'s greeting'),
    (5, 18, 19, 'greet_gaura_line (talk_str_a)', 'Gaura\'s greeting'),
    (5, 5, 12, 'talk_zaril farewell (talk_str_b)', 'Leave: 5-7 not introduced to Gaura; 8/9 Zaril, 10/11 Gaura, 12 Fritillaria'),
    (5, 0x2e, 0x2e, 'talk_zaril (talk_str_b)', ''),
    (5, 0x69, 0x6b, 'handler 26 (talk_str_b)', 'the warning, by the maze\'s entry value'),
]

NOTES = """## What the unplaced strings are

Read from their text and the code around them; none of these has a script block or a
store that reaches it. [inferred unless marked]

- **A cut identify service.** Rosea (2:137-141), Cephala (3:145-150) and Cleo (4:78-83)
  each have a full set of "identify an item?" lines, with success, failure and cursed
  outcomes. Every party file also has the log line "We asked them to identify items."
  (1:300, 2:268, 3:280, 4:164, 5:115). No handler has an identify state, and the
  scholars' state 0x3c is the decipher check instead. [code: no handler stores these
  numbers]
- **Unused log lines.** "We asked them to rescue our companions." (1:301, 2:269,
  3:281, 4:165, 5:116) and Zaril's "We asked them for healing." (5:114). The rescue is
  offered by the NPC, so the "we asked" line never runs.
- **Zaril's healing.** 5:35-42 are a whole healing table for Zaril (Dialko, Latumofis,
  Dialma, out of spells). His handler has no heal offer. [code]
- **Re-introductions that don't happen.** Guy's handler and Fontana's play the full
  introductions whenever any member hasn't met the leader, so their "didn't we do this
  already?" lines (1:134-139, 3:117-123) and the second Guy line-up (1:128-133) never
  play. [code: 0x1e has no partial branch in either]
- **Bugs.** 1:87 (handler 7 uses 1:89), 2:134 (Rosea's block uses 2:135), 3:134
  (missing from Cephala's table), 4:19 and 4:20 (Cresson only stores 4:18). See
  C-talk.md.
- **Maze text, probably.** 2:79-80 (pressing the switches) and 3:108 (the rope) read
  like the maze's own event text. They may be printed by MAZE from the loaded NPC file
  (A's area; not checked).
- **Others not traced.** 1:45, 1:292, 2:5, 2:50, 2:52-53, 3:10-11, 3:50, 3:198, 4:8,
  4:17, 4:44, 4:144-146, 5:3-4, 5:20-25, 5:113. Most are greetings or one-liners. They
  may come from a variant function's computed store that VARS doesn't cover, so they
  aren't proof of dead text.
"""


def english():
    out = {}
    for n in range(1, 6):
        p = os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json')
        out[n] = [s.get('translation') or '' for s in
                  json.load(open(p, encoding='utf-8'))['sections'][0]['strings']]
    return out


def label(text, n=60):
    t = text.replace('{ff40}', '').replace('\r', ' ').replace('\n', ' ').replace('|', '/')
    t = ' '.join(t.split())
    return t[:n] + ('...' if len(t) > n else '')


def main():
    args = sys.argv[1:]
    src = os.path.join(ROOT, 'rips/re/work/C/scripts.json')
    out = os.path.join(ROOT, 'docs/re/C-talk-lines.md')
    if '--json' in args:
        src = args[args.index('--json') + 1]
    if '--out' in args:
        out = args[args.index('--out') + 1]
    data = json.load(open(src))
    eng = english()
    refs = {n: {} for n in range(1, 6)}       # file -> string -> [where, ...]

    def add(f, k, where):
        lst = refs[f].setdefault(k, [])
        if where not in lst:
            lst.append(where)

    for h, v in sorted(data.items(), key=lambda x: int(x[0])):
        h = int(h)
        f = v['file']
        arrays = [(a['base'], a['stride'], [(b['block'], [(o[0], [x[0] for x in o[1]],
                   [x[1] for x in o[1]]) for o in b['ops']]) for b in a['blocks']]) for a in v['arrays']]
        for base, stride, blocks in arrays:
            for blk, ops in blocks:
                if stride == 0 and any(s and b2 == base for b2, s, _ in arrays):
                    continue                       # same script listed with its stride
                for name, vals, taints in ops:
                    if name not in ('say', 'bar', 'say2'):
                        continue
                    # in the -2 (name) form the dumper tags N with the member slot's
                    # global, since both halfwords are stored from one register pair
                    if taints[-1] and not (len(vals) == 3 and vals[0] == -2
                                           and taints[-1] == 'g:80079a5a'):
                        continue
                    k = vals[-1]
                    if h in NAMES:
                        what, how = ARRAYS.get((h, base), ('?', ''))
                        note = BLOCKS.get((h, base), {}).get(blk, '')
                        where = f'h{h} {NAMES[h]} {what} [{blk}]' + (f': {note}' if note else '')
                    else:
                        where = f'h{h} {SCENES[h]}' + (f' [{blk}]' if stride else '')
                    add(f, k, where)
    for h, lst in MANUAL.items():
        for base, blk, ops in lst:
            for _, name, k in ops:
                add(3, k, f'h{h} {SCENES[h]}')
    for v in VARS:
        if len(v) == 5:
            f, lo, hi, where, when = v
            ks = range(lo, hi + 1)
        else:
            f, ks, where, when = v
        for k in ks:
            add(f, k, f'{where}' + (f': {when}' if when else '') + ' (run time)')

    lines = ['# C. Every NPC talk line and when it plays', '',
             'Generated by `scripts/re/talklines.py` from the scripts `scripts/re/talkscripts.py`',
             'dumps out of the talk handlers, and the conditions read from the code. The rules',
             'behind the conditions are in `docs/re/C-talk.md`. Run it again after changing either.',
             '',
             'Each string lists every place that can play it. "hN" is the talk handler',
             '(`talk_party` N), then the array and the block number in brackets, then when that',
             'block runs where it isn\'t plain from the array. The arrays\' general rules are in',
             'the key below each file\'s heading. "(run time)" means the script takes the',
             'number from a global the code sets; those come from reading the code, not the dump,',
             'so they\'re ranges and less exact. A string with no entry wasn\'t found in any',
             'script or store; it may be unused or reached some way not traced yet.', '']
    total = found = 0
    for f in range(1, 6):
        n = len(eng[f])
        hits = sum(1 for k in range(n) if k in refs[f])
        total += n
        found += hits
        lines += [f'## NPC_MES{f}', '', f'{hits} of {n} strings placed.', '']
        keys = sorted({(h, b) for (h, b) in ARRAYS if h == f - 1})
        if keys:
            lines.append('Arrays:')
            for h, b in keys:
                what, how = ARRAYS[(h, b)]
                lines.append(f'- {what} (sp+{b:#x}): {how}')
            lines.append('')
        lines += ['| # | Text | Where and when |', '|---|---|---|']
        for k in range(n):
            where = '<br>'.join(refs[f].get(k, [])) or '**not found**'
            lines.append(f'| {f}:{k} | {label(eng[f][k])} | {where} |')
        lines.append('')
        missing = [k for k in range(n) if k not in refs[f]]
        lines += [f'Not found in NPC_MES{f}: ' + (', '.join(map(str, missing)) or 'none'), '']
    lines.append(NOTES)
    lines.insert(13, '')
    lines.insert(14, f'In all, {found} of {total} strings are placed.')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'{os.path.relpath(out)}: {found}/{total} strings placed')


if __name__ == '__main__':
    main()
