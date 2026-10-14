"""replay.py DISC_CUE STATE CADENCE OFFSET [LIMIT]: from a state taken before BATTLE.BIN
loads, run into the battle and fight it with the harness's command policy, advancing the
narration with circle: CADENCE 'hold' (held every frame) or N (a 2-frame tap every N
frames), after OFFSET idle frames at the battle's start and after each round's commands. If STATE.inputs.json exists
(hunt.py), its buttons are replayed first, frame by frame, up to the battle. Logs every spell-file load
(load_file_alt, table 1, index 0x1bb-0x1f5) and every run of the fix's stop routine
(0x800c3188), by breakpoint only (no RAM is written). Before the first press checks the
36 fix words in RAM against the built (ba2a42a6) and published (ca912fe8) BATTLE.BIN.
A hang: the VSync counter (0x80060788) still for 3000 frames; then the RAM PCs run over
the next 300 frames and the kernel's saved EPC/Cause. Prints one JSON line.
Run from the repo root. The two discs are copied to rips/re/work/spellfix/discs/<md5>/
(dimguil-en.cue, .bin and BATTLE.BIN): ca912fe8 published, ba2a42a6 with the fix
(bugs.md 1.15)."""
import os, sys, json
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from harness.game import Game
from harness import battle
cue, st, cad, off = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
limit = int(sys.argv[5]) if len(sys.argv) > 5 else 15000
D = 'rips/re/work/spellfix/discs/'
NEW = open(D + 'ba2a42a6/BATTLE.BIN', 'rb').read(); OLD = open(D + 'ca912fe8/BATTLE.BIN', 'rb').read()
B = 0x800a1000
FIX = [B + i for i in range(0, len(NEW), 4) if NEW[i:i + 4] != OLD[i:i + 4]]
assert len(FIX) == 36
g = Game(disc=cue, capture=True)
e = g.e
e.load(st)          # not g.load: that runs a frame after, which the recorded inputs don't have
e.bp(0x80012f5c); e.bp(0x800c3188)
# the text capture reads (and resets) the debug log every frame: keep our breakpoint hits
MINE = []
_log = e.log
def log(reset=True):
    out = _log(reset)
    MINE.extend(x for x in out if x['type'] == 'X' and x['pc'] in (0x80012f5c, 0x800c3188))
    return out
e.log = log
REG = 'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split()
R = dict(disc=os.path.basename(os.path.dirname(cue)), state=os.path.basename(st), cad=cad, off=off,
         loads=[], stops=0, casts=[])
f0 = g.frame
vs = [None, 0]
nmsg = [0]
def poll():
    while MINE:
        x = MINE.pop(0)
        r = dict(zip(REG, x['regs']))
        if x['pc'] == 0x800c3188:
            R['stops'] += 1
        elif r['a2'] == 1 and 0x1bb <= (r['a1'] & 0xffff) < 0x1f6 and r['a0'] == 0x801a0400:
            R['loads'].append((g.frame - f0, r['a1'] & 0xffff))
    c = g.cap.messages
    for m in c[nmsg[0]:]:
        if m['file'] == 'FIGHTMSG.OBJ' and m['idx'] in (102, 112):
            R['casts'].append((g.frame - f0, m['text'].replace('\n', ' ')))
    nmsg[0] = len(c)
    v = e.u32(0x80060788)
    if v != vs[0]:
        vs[0], vs[1] = v, g.frame
    return g.frame - vs[1]
g.t.ticks.append(poll)
# the hunt's buttons from the state to the battle (hunt.py writes them beside the state)
ip = st.replace('.state', '.inputs.json')
if os.path.exists(ip):
    for b in json.load(open(ip))['inputs']:
        e.run(1, tuple(b))
        for t in g.t.ticks:
            t()
while g.overlay() != 'BATTLE' and g.frame - f0 < 3000:
    g.step()
R['battle_at'] = g.frame - f0
ram = [e.u32(a) for a in FIX]
R['words'] = ('new' if all(w == int.from_bytes(NEW[a - B:a - B + 4], 'little') for w, a in zip(ram, FIX))
              else 'old' if all(w == int.from_bytes(OLD[a - B:a - B + 4], 'little') for w, a in zip(ram, FIX))
              else 'mixed')
g.step(off)
battle.CAST.clear(); battle.ROUND = 0; battle._vrng.seed(1); battle.VARY = 0
log = []
res = 'limit'
try:
    while g.frame - f0 < limit:
        if g.frame - vs[1] > 3000:
            res = 'HANG'
            break
        if g.overlay() != 'BATTLE':
            res = 'left battle'; break
        ph = g.u8(battle.PHASE)
        if ph == battle.CHEST_PHASE:
            res = 'battle over'; break
        if ph == battle.CMD_PHASE:
            battle.ROUND += 1
            battle.command_phase(g, battle.default_policy, log)
            g.step(off)          # the offset again after every round's commands
            continue
        if cad == 'hold':
            g.tap('circle', hold=1)
        else:
            g.tap('circle'); g.step(max(int(cad) - 2, 0))
except Exception as ex:
    res = 'error ' + repr(ex)[:120]
R['result'] = res
R['frames'] = g.frame - f0
R['words_end'] = sum(e.u32(a) == int.from_bytes(NEW[a - B:a - B + 4], 'little') for a in FIX)
if res == 'HANG':
    R['hang_from'] = vs[1] - f0
    e.dbg_clear(); e.coverage(True); e.run(300); pcs = sorted(e.covered()); e.coverage(False)
    R['pcs'] = '%d PCs, %08x-%08x' % (len(pcs), pcs[0], pcs[-1]) if pcs else 'none in RAM'
    tcb = 0xa000e29c
    R['epc'] = '%08x' % e.u32(tcb + 0x88); R['cause'] = '%08x' % e.u32(tcb + 0x98)
    R['vsync_still'] = g.frame - vs[1]
    if len(sys.argv) > 6:
        e.save(sys.argv[6])
print(json.dumps(R), flush=True)
