"""Zaril's chat table in the emulator, block by block (bugs.md 2.10 check, investigation only).

RAM-write setup, as the P3 talk tests (rips/re/work/P3-zaril/zaril_heal_test.py):
  - rips/states/npc_talkmode.state (a real talk, made 2026-10-07);
  - laid in from this worktree's build: MAIN's patch sites where the state's MAIN differs
    from the built executable (the code/VWF changes since the state was made), the file
    tables 0x80051760-0x80052700, and MCARD.BIN at 0x800a1000;
  - talk switched to Zaril (talk_party 0x80079797 = 4, greeting block 4), every member
    "met Zaril" (+0xc7 |= 4) with +0xc7 bit 0 cleared (no sale: greet_flags bit 0), all
    healthy (no heal offer), the Talk-press count 0x80079be8 = 0.
  - FORCE: the chat roll's `jal rand_upto` at MCARD 0x800dab0c becomes
    `addiu v0, zero, BLOCK` (0x2402000N), so the do/while stores BLOCK in talk_block.
    The word is put back (0x0c0072c6) before the second Talk press, which then takes
    the game's own path (0x80079be8 == 2 -> block 1).
Then button presses only. Every text_expand call is captured (harness/text.py Capture:
a0 = string index, a1 = the loaded file's base), and a screenshot is saved each time a
new message has been drawn.

    zchat.py OUTDIR BLOCK [BLOCK ...]      (BLOCK -1: no forcing, the game's own roll)
"""
import json, os, struct, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
os.chdir(ROOT)
sys.path.insert(0, 'scripts'); sys.path.insert(0, 'scripts/harness')
from emu import Emu
from text import Capture, decode
BAR_PRINT = 0x800b3c40      # MCARD bar_print(0xa6, 6, N, 1): op 7 'bar N', a2 = N
SAY_RA = 0x800b8fd8         # text_expand's return address for op 2 'say N'

out = sys.argv[1]; blocks = [int(x) for x in sys.argv[2:]]
os.makedirs(out, exist_ok=True)
exe = open('rips/iso/dimguil/SLPS_026.91', 'rb').read()
clean = open('rips/clean/dimguil/SLPS_026.91', 'rb').read()
mc = open('rips/iso/dimguil/MCARD.BIN', 'rb').read()
mes5 = open('rips/iso/dimguil/DATA06/NPC_MES5.OBJ', 'rb').read()
T_ADDR, T_SIZE = struct.unpack_from('<II', exe, 0x18)
ROLL = 0x800dab0c
JAL = struct.unpack_from('<I', mc, ROLL - 0x800a1000)[0]
assert JAL == 0x0c0072c6, hex(JAL)

e = Emu('rips/iso/dimguil-en.cue')
u8 = lambda a: e.read(a, 1)[0]
s16 = lambda a: int.from_bytes(e.read(a, 2), 'little', signed=True)
def w8(a, v): e.write(a, bytes([v & 0xff]))
def w16(a, v): e.write(a, (v & 0xffff).to_bytes(2, 'little'))
def w32(a, v): e.write(a, (v & 0xffffffff).to_bytes(4, 'little'))
rec = lambda r: 0x8007d708 + r * 0xd0


def setup(block):
    e.load('rips/states/npc_talkmode.state'); e.run(2)
    ram = e.read(T_ADDR, T_SIZE)
    img = exe[0x800:0x800 + T_SIZE]; cimg = clean[0x800:0x800 + T_SIZE]
    laid = 0
    for i in range(T_SIZE):           # MAIN patch bytes the old state lacks
        if ram[i] != img[i] and (img[i] != cimg[i] or 0x80073900 <= T_ADDR + i < 0x80073d00):
            e.write(T_ADDR + i, img[i:i + 1]); laid += 1
    e.write(0x80051760, exe[0x80051760 - 0x80010000 + 0x800: 0x80052700 - 0x80010000 + 0x800])
    e.write(0x800a1000, mc)
    if block >= 0:
        w32(ROLL, 0x24020000 | block)
    for r in [r for r in e.read(0x8007e812, 6) if r != 0xff]:
        w8(rec(r) + 0xc7, (u8(rec(r) + 0xc7) | 4) & ~1)
        w16(rec(r) + 0xe, 0)
        w16(rec(r) + 0x46, s16(rec(r) + 0x4a))
    w8(0x80079797, 4); w8(0x80079bb4, 4)
    w16(0x8007981c, 0); w16(0x800798a4, 0); w16(0x80079a26, 0)
    w8(0x80079565, 0); w8(0x80079566, 0); w8(0x80079be8, 0)
    w16(0x80079a3e, 0)                # the state's pending message box (Guy's line)
    return laid


def play(block, tag, talks=int(os.environ.get('TALKS', 2))):
    """Greeting, then Talk `talks` times; log each chat's messages and shoot each one."""
    cap = Capture(e)
    e.bp(BAR_PRINT)
    order = []          # ('bar'|'say', N, frame, chat) in execution order
    raw_log = e.log
    def log_hook(reset=True):
        xs = raw_log(reset)
        for x in sorted(xs, key=lambda x: x['seq']):
            if x['type'] != 'X':
                continue
            if x['pc'] == BAR_PRINT and x['ra'] in (0x800b930c, 0x800b9324):   # from op 7 only
                order.append(('bar', x['regs'][6] & 0xffff, e.frame_no, cur))
            elif x['pc'] == 0x8001dfc0 and x['ra'] == SAY_RA:
                order.append(('say', x['regs'][4] & 0xffff, e.frame_no, cur))
        return xs
    e.log = log_hook
    log = []
    cur = None          # (press number, talk_block) of the chat being played
    presses = 0
    f = 0; last = None; shot_n = 0; seen_msgs = 0
    while f < 9000:
        ts = s16(0x8007981c); blk = u8(0x80079bb4); menu = u8(0x80079b50)
        st = (ts, blk)
        if st != last:
            log.append(dict(frame=f, talk_state=ts, block=blk, press_count=u8(0x80079be8),
                            greet_flags=u8(0x800799b0), menu=menu))
            last = st
            if ts == 0x28:
                cur = (presses, blk)
        if ts == 0x14:
            cap.poll()
            if presses >= talks or not (menu & 1):
                break
            if presses == 1 and block >= 0:
                w32(ROLL, JAL)            # second press: the game's own path
            if u8(0x80079b8c) != 0:
                e.press('up', hold=3, after=12); f += 15; continue
            e.press('circle', hold=3, after=20); f += 23; presses += 1
            continue
        if ts == 0x3d:                    # a sale (should not happen): decline, note it
            log.append(dict(frame=f, note='sale offered'))
            e.press('cross', hold=3, after=20); f += 23; continue
        if u8(0x80079566) == 1:           # member picker (heal offer; should not happen)
            log.append(dict(frame=f, note='picker'))
            e.press('cross', hold=3, after=20); f += 23; continue
        e.run(40); f += 40
        cap.poll()
        new = cap.messages[seen_msgs:]
        if new and ts == 0x28:
            ids = '_'.join(str(m['idx']) for m in new if m['ra'] == SAY_RA)
            shot_n += 1
            e.shot(f'{out}/{tag}_p{cur[0]}_b{cur[1]}_{shot_n:02d}_{ids or "x"}.png', scale=2)
        seen_msgs = len(cap.messages)
        if s16(0x8007981c) in (0x14, 0x3d) or u8(0x80079566) == 1:
            continue
        e.press('circle', hold=2, after=2); f += 4
    cap.poll()
    e.log = raw_log
    e.dbg_clear()
    return cap, log, order


def mes5_base(cap):
    for b, fn in cap.base_file.items():
        if fn and fn.startswith('NPC_MES5'):
            return b
    return None


def text5(n):
    if n * 4 + 4 > len(mes5) or not 0 < struct.unpack_from('<i', mes5, n * 4)[0] < len(mes5):
        return f'<not a NPC_MES5 index: {n:#x}>'
    off = struct.unpack_from('<i', mes5, n * 4)[0]
    j = off
    while not (mes5[j] == 0xff and mes5[j + 1] == 0x40):
        j += 2 if mes5[j] >= 0xf7 else 1
    return decode(mes5[off:j])


results = {}
for b in blocks:
    laid = setup(b)
    tag = f'force{b:02d}' if b >= 0 else 'natural'
    cap, log, order = play(b, tag)
    base = mes5_base(cap)
    same = None
    if base is not None:
        same = e.read(base, len(mes5)) == mes5
    msgs = [dict(frame=m['frame'], idx=m['idx'], base=hex(m['base']), file=m['file'],
                 ra=hex(m['ra']), text=m['text']) for m in cap.messages]
    results[b] = dict(main_bytes_laid=laid, mes5_base=hex(base) if base else None,
                      mes5_matches_build=same, states=log, messages=msgs,
                      order=[dict(op=o, n=n, frame=fr, chat=c, text=text5(n)) for o, n, fr, c in order])
    print(f'== block {b}: laid {laid}, NPC_MES5 at {hex(base) if base else None} matches build: {same}')
    for x in log:
        print('  ', x)
    for o, n, fr, c in order:
        print('   ', c, o, n, repr(text5(n)[:90]))
    sys.stdout.flush()
json.dump(results, open(f'{out}/results_{"_".join(map(str, blocks))}.json', 'w'), indent=1)
