"""Fights fought with a member out (Chris, 2026-10-15: "A party should not proceed 'as
normal' if one or more characters in the party are dead, paralyzed, or poisoned").

    python3 -m harness.nodead LOG.jsonl [FIRST_LINE]

Reads a run's log.jsonl (from FIRST_LINE on: a chapter's log starts with the memory's
lines, chapters.load_memory) and counts the fights that started with a member dead,
stoned, ashed or lost, paralyzed or poisoned: the fight's 'out_start' (battle.fight,
from 2026-10-15), else the 'dead_end' and 'down_end' of the fight before with no trip
home between (poison unknown there). Each is put down as 'homeward' (between a 'trip
end' and its 'trip home'; home_ran: the ones the party tried to run from) or 'on' (the
trip, the goal or the walk out carried on)."""
import json
import sys


def stats(path, first=0):
    L = [json.loads(l) for l in open(path)][first:]
    out = dict(fights=0, deaths=0, wipes=0, on=0, homeward=0, on_dead=0, on_para=0, on_poison=0,
               home_ran=0, home_deaths=0,
               dead_sum=0, streaks=[])
    prev = (set(), set(), set())
    home = False
    streak = 0
    for x in L:
        k = x[1] if len(x) > 1 else None
        if k == 'trip end':
            home = True
        elif k == 'trip home':
            home = False
            prev = (set(), set(), set())
            if streak:
                out['streaks'].append(streak)
            streak = 0
        elif k == 'death':
            out['deaths'] += 1
            out['home_deaths'] += home
        elif k == 'retry' and 'wipe' in json.dumps(x[2:]).lower():
            out['wipes'] += 1
        elif k == 'fought' and isinstance(x[2], dict):
            f = x[2]
            out['fights'] += 1
            dead, para, pois = prev
            if 'out_start' in f:
                o = f['out_start']
                dead = {n for n, b in o if b & 0x3c0}
                para = {n for n, b in o if b & 0x20} - dead
                pois = {n for n, b in o if b & 0x04} - dead - para
            if dead or para or pois:
                if home:
                    out['homeward'] += 1
                    out['home_ran'] += bool(f.get('ran'))
                else:
                    out['on'] += 1
                    out['on_dead'] += bool(dead)
                    out['on_para'] += bool(para)
                    out['on_poison'] += bool(pois)
                    streak += 1
            elif streak:
                out['streaks'].append(streak)
                streak = 0
            d = set(f.get('dead_end') or ())
            w = set(f.get('down_end') or ()) - d
            out['dead_sum'] += len(d)
            prev = (d, w, set())
    if streak:
        out['streaks'].append(streak)
    out['dead_per_fight'] = round(out['dead_sum'] / out['fights'], 2) if out['fights'] else None
    return out


if __name__ == '__main__':
    print(json.dumps(stats(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0)))
