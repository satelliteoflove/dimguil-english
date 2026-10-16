#!/usr/bin/env python3
"""List every monster and NPC-party attack with its noun, its verb and the battle message
template it can print (docs/engine-notes.md, "Battle text and monster files").

    attackverbs.py [--built DIR] [--verbs]

Reads the enemy files the encounter loader can load (table 1: M_DTnnn, MPTnn, NPTnn in
DATA02), each ending in one 0xd0-byte record per group. Each record has three 10-byte
attacks at +0xac/+0xb6/+0xc0: u16 noun, verb byte, swings, damage dice, effect bits,
effect chance.

What decides the template (BATTLE.BIN, read in the code):
- monster_attack_roll (0x800aaed0) sets noun = raw + 427 (0x800aafe8), takes 2000 off a
  noun of 2000 or more (0x800ab084), and sends a noun of 683 (0x2ab) or more to cast_spell
  as an innate ability (0x800ab0d0). cast_spell (0x800abcc0) sets message code 5 for a
  monster's ability, battle_run_actions (0x800a8548) returns 3 because the action is now
  a spell, and battle_message_build (0x800b4194) prints FIGHTMSG 214 "{ff13} {ff15} {ff14}."
  with no target.
- Any other noun is a melee hit: battle_run_actions returns 2 and battle_message_build
  prints 108 or 109 "{ff13} {ff15} {ff18} with {ff14}." (109 when the 2000 flag was set).
So the template is fixed by the attack's noun; the same attack can't print both.

Which slots run (monster_melee 0x800aaa04): attack 1 always; attack 2 when its raw noun
is 0xff or more or it has swings; attack 3 only with swings, after attack 1 or 2. An
ability in attack 3 would print attack 1's or 2's noun and verb (its own sit in the
second message slot); the script flags any such record.

The {ff15} verbs were written for 108/109 ("startles Venus with a shriek"), so in 214
several read wrong ("Ghost startles a shriek."). TARGETLESS below gives those abilities a
verb of their own: FIGHTMSG 65-71 (unused, 未使用) and 74 (unused), or an existing verb
that already reads right without a target. Verbs 46 and 76 are only ever used in 214, so
their strings were reworded in place instead.

--built DIR reads the files from a built disc tree (default: the clean disc), so the
patched verb bytes show up. --verbs prints only the per-verb summary. --write writes
binary/<file>.verbs.json for every ability whose verb TARGETLESS changes (kept apart from
the name patches that nptnames.py and namefixes.py write).
"""
import collections, json, os, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from gametext import dec

REC = 0xd0

# Old verb -> targetless verb, for abilities (template 214) only.
TARGETLESS = {
    16: 65,   # takes aim at -> fires (BIG GUN)
    45: 66,   # glares at -> glares at everyone with (a piercing glare)
    47: 67,   # startles -> startles everyone with (a shriek, eerie smoke)
    48: 68,   # tries to melt -> tries to melt everyone with (eerie smoke)
    56: 55,   # pelts -> sprays (pollen), 55 already reads "Fire Rock sprays red-hot stones."
    58: 69,   # stares at -> stares at everyone with (a sultry look, hollow eyes)
    60: 70,   # "{ff18} plays {ff14}." (a whole sentence for the party's item use) -> plays
    63: 70,   # "{ff18} strikes up {ff14}." -> plays (LUTE)
    64: 74,   # "{ff18} beats {ff14}." -> beats (DEVIL'S DRUM)
    73: 71,   # pelts -> throws (ASH OF CONFUSION)
}


def strings(name):
    p = os.path.join(ROOT, 'translations', name + '.json')
    d = json.load(open(p, encoding='utf-8'))
    return [s['translation'] for sec in d['sections'] for s in sec['strings']]


def records(d):
    """Group records at the end of the file, walking back while the Japanese name reads."""
    out, o = [], len(d) - REC
    while o >= 0:
        name = d[o:o + 0x12]
        i = struct.unpack_from('<H', d, o + 0x6c)[0]
        if name.find(b'\xff\x40') <= 0 or '<' in dec(d, o) or not i < 1000:
            break
        out.append(o)
        o -= REC
    return out          # first group first


def attacks(disc):
    d2 = os.path.join(disc, 'DATA02')
    for fn in sorted(os.listdir(d2)):
        if not fn.startswith(('M_DT', 'MPT', 'NPT')):
            continue
        d = open(os.path.join(d2, fn), 'rb').read()
        for g, o in enumerate(records(d), 1):
            en = dec(d, o + 0x24).replace('{ff21}', ' ')
            for k in range(3):
                a = o + 0xac + 10 * k
                raw, verb, swings = struct.unpack_from('<HBB', d, a)
                noun = raw + 427
                flag = noun >= 2000
                if flag:
                    noun -= 2000
                noun = (noun + 0x8000 & 0xffff) - 0x8000      # the game compares signed
                if k == 0:
                    used = True
                elif k == 1:
                    used = raw >= 0xff or swings > 0
                else:
                    used = swings > 0
                ability = noun >= 683
                yield dict(file=fn, group=g, off=a, name=en, slot=k + 1, raw=raw, noun=noun,
                           verb=verb, swings=swings, used=used, ability=ability,
                           template=214 if ability else (109 if flag else 108))


def main():
    a = sys.argv[1:]
    disc = os.path.join(ROOT, 'rips/clean/dimguil')
    if '--built' in a:
        disc = a[a.index('--built') + 1]
    nouns, msgs = strings('I_NAME_E.OBJ'), strings('FIGHTMSG.OBJ')
    rows = list(attacks(disc))
    if '--write' in a:
        edits = collections.defaultdict(dict)
        for r in rows:
            if r['ability'] and r['verb'] in TARGETLESS:
                edits[r['file']][f"{r['off'] + 2:x}"] = f"{TARGETLESS[r['verb']]:02x}"
        for fn, e in sorted(edits.items()):
            path = os.path.join(ROOT, 'binary', fn + '.verbs.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'file': 'DATA02/' + fn, 'edits': e}, f, indent=4)
                f.write('\n')
        print(f'{sum(len(e) for e in edits.values())} verb bytes in {len(edits)} files')
        return
    by_verb = collections.defaultdict(lambda: collections.defaultdict(set))
    if '--verbs' not in a:
        for r in rows:
            if not r['used']:
                continue
            n = nouns[r['noun']] if 0 <= r['noun'] < len(nouns) else '?'
            warn = '  ** ability in attack 3' if r['ability'] and r['slot'] == 3 else ''
            print(f"{r['file']:12} g{r['group']} {r['name']:24} atk{r['slot']} "
                  f"@{r['off']:05x} noun {r['noun']:4} {n!r:28} verb {r['verb']:3} "
                  f"{msgs[r['verb']]!r:28} -> {r['template']}{warn}")
    for r in rows:
        if r['used']:
            by_verb[r['verb']][r['template']].add(nouns[r['noun']] if 0 <= r['noun'] < len(nouns) else '?')
    print('\nverb  text                          templates (nouns)')
    for v in sorted(by_verb):
        t = by_verb[v]
        print(f"{v:4}  {msgs[v]!r:30}" + '; '.join(
            f"{k}: {', '.join(sorted(t[k]))}" for k in sorted(t)))


if __name__ == '__main__':
    main()
