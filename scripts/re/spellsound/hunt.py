"""hunt.py DISC_CUE STATE TRIPS SEED TAG OUTDIR: chapter 8 training trips from STATE (as
dev/cast_hunt.py), on the given disc. While MAZE is resident it keeps, in memory, a state
every 30 frames and the buttons of every frame since; when BATTLE becomes resident, the
last such state (taken before BATTLE.BIN started loading) and the inputs from it to the
battle become that battle's entry. When the VSync counter (0x80060788) stops for 600
frames: writes OUTDIR/TAG_enc.state and TAG_enc.inputs.json (the hung battle's entry),
TAG_hung.state, and stops. Writes nothing under rips/harness.
Run from the repo root. The two discs are copied to rips/re/work/spellfix/discs/<md5>/
(dimguil-en.cue, .bin and BATTLE.BIN): ca912fe8 published, ba2a42a6 with the fix
(bugs.md 1.15)."""
import os, sys, struct, json, ctypes as C
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import chapters
cue, st, trips, seed, tag, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6]
os.makedirs(out, exist_ok=True)
g = Game(disc=cue, capture=True)
g.load(st)
BHEAD = open('rips/re/work/spellfix/discs/ca912fe8/BATTLE.BIN', 'rb').read(16)   # BATTLE.BIN not loading yet
e = g.e
def snap():
    n = e.lib.retro_serialize_size(); buf = C.create_string_buffer(n)
    assert e.lib.retro_serialize(buf, C.c_size_t(n)); return buf.raw
class Hung(Exception): pass
S = dict(casts=0, nmsg=0, last=[], vs=None, vsf=0, snap=None, inputs=[], enc=None, res=0)
_run = e.run
def run(frames=1, hold=()):
    for _ in range(frames):
        S['inputs'].append(list(hold))
        _run(1, hold)
e.run = run
def tick():
    c = g.cap.messages
    if len(c) > S['nmsg']:
        for m in c[S['nmsg']:]:
            if m['file'] == 'FIGHTMSG.OBJ' and m['idx'] in (102, 112):
                S['casts'] += 1
                S['last'] = (S['last'] + [(S['casts'], g.frame, m['text'])])[-4:]
        S['nmsg'] = len(c)
    res, mode = g.u8(0x800798b3), g.u8(0x8007967e)
    if res == 2 and (S['snap'] is None or g.frame - S['snap'][0] >= 30) and e.read(0x800a1000, 16) != BHEAD:
        S['snap'], S['inputs'] = (g.frame, snap()), []
    if res == 3 and S['res'] != 3 and S['snap']:
        S['enc'] = (S['snap'][0], S['snap'][1], list(S['inputs']), g.frame)
    S['res'] = res
    v = e.u32(0x80060788)
    if v != S['vs']:
        S['vs'], S['vsf'] = v, g.frame
    elif g.frame - S['vsf'] > 600:
        fr, d, ins, bf = S['enc']
        open(os.path.join(out, '%s_enc.state' % tag), 'wb').write(d)
        json.dump(dict(snap_frame=fr, battle_frame=bf, inputs=ins), open(os.path.join(out, '%s_enc.inputs.json' % tag), 'w'))
        g.save(os.path.join(out, '%s_hung.state' % tag))
        print('HUNG', g.frame, 'casts', S['casts'], 'enc', fr, bf, len(ins),
              'last', json.dumps(S['last']), flush=True)
        raise Hung()
g.t.ticks.append(tick)
r = chapters.Run(g, seed=seed, variant=3, out=os.path.join(out, tag + '_run'), retries=1, auto_cases=False)
r.chapter = 8
fns = r.goal_fns(8)
for k in range(1, trips + 1):
    try:
        print('trip', k, fns['train_%02d' % k](), 'casts', S['casts'], 'frame', g.frame, flush=True)
    except Hung:
        break
    except Exception as ex:
        print('trip', k, 'error', repr(ex)[:150], 'casts', S['casts'], flush=True)
print('end casts', S['casts'], 'frame', g.frame, flush=True)
