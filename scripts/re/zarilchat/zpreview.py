"""PREVIEW copy of zpages.py: VARIANT=now|prop|alt picks table changes (see VARIANTS).
"""
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
import hashlib, json, os, struct, sys
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
mc = bytearray(open('rips/iso/dimguil/MCARD.BIN', 'rb').read())
# PREVIEW: VARIANT names a set of operand changes to Zaril's chat table (MCARD data at
# 0x800a8988, 200 bytes a block), laid into the MCARD copy before it goes into RAM.
TABLE = 0x800a8988 - 0x800a1000
OPN = {-1: 0, 0: 2, 1: 2, 2: 1, 3: 3, 4: 0, 5: 0, 6: 1, 7: 1, 8: 1, 9: 1, 10: 4, 11: 1}
VARIANTS = {
    'now': {},
    'prop': {6: {'bar': 98}, 9: {'bar': 98, 84: 87}, 10: {87: 84}, 13: {'bar': 99}},
    'alt': {8: {80: 95}, 13: {'bar': 99, 95: 80}},
    # 2026-11-09, after Chris: 13 takes Zaril's 80; 8 becomes "told them", keeps 80 and 81,
    # and Gaura reuses his block-1 "Mmm..." (59); his 82 replaces 91 in block 11 (91 is the
    # same Japanese as 88 in block 10).
    'v3': {8: {'bar': 99, 82: 59}, 11: {91: 82}, 13: {'bar': 99, 95: 80}},
    # Fritillaria's 93 ("Whoa, awesome! You guys are good!") to block 1 ("told them"), and
    # his 58 ("You got business with me?") to block 12 ("about themselves"). Block 1 is the
    # second Talk press: capture it with block 0 forced and TALKS=2.
    'v4': {1: {58: 93}, 12: {93: 58}},
    # what's approved so far (2026-11-09), expressions moving with their lines
    'final': {6: {'bar': 98}, 8: {'bar': 99, 82: 59}, 9: {'bar': 98, 84: 87}, 10: {87: 84},
              11: {91: 82}, 13: {'bar': 99, 95: 80}},
    'v4f': {6: {'bar': 98}, 8: {'bar': 99, 82: 59}, 9: {'bar': 98, 84: 87}, 10: {87: 84},
            11: {91: 82}, 13: {'bar': 99, 95: 80}, 1: {58: 93}, 12: {93: 58}},
}
VARIANT = os.environ.get('VARIANT', 'now')
def walk(blk):
    """(position, op, args) for each op of a block in mc."""
    p = TABLE + blk * 200; end = p + 200
    while p < end:
        op = struct.unpack_from('<h', mc, p)[0]
        if op == -1: return
        yield p, op, [struct.unpack_from('<h', mc, p + 2 + 2 * k)[0] for k in range(OPN[op])]
        p += 2 + 2 * OPN[op]
ORIG_FACE = {}          # line -> the expression its own block shows it with (face op arg 2)
for _b in range(14):
    _f = None
    for _p, _op, _a in walk(_b):
        if _op == 3: _f = _a[1]
        if _op == 2: ORIG_FACE[_a[0]] = _f
def patch_table(changes):
    """bar and say operands; a moved line takes its expression along (the face op before it)."""
    for blk, ch in changes.items():
        face_at = None
        for p, op, a in list(walk(blk)):
            if op == 7 and 'bar' in ch:
                struct.pack_into('<h', mc, p + 2, ch['bar'])
            if op == 3:
                face_at = p
            if op == 2 and a[0] in ch:
                struct.pack_into('<h', mc, p + 2, ch[a[0]])
                if os.environ.get('FACES', '1') == '1':
                    struct.pack_into('<h', mc, face_at + 4, ORIG_FACE[ch[a[0]]])
# RAW: halfwords written straight into MCARD (address, value), for variants taken against
# a disc that already carries the fix (asm/bugfix_zaril_chat_topics.asm), whose table
# ORIG_FACE can't read the original expressions from.
RAW = {
    # 2026-11-10 recommendation against disc adc20ddd: blocks 8 and 11 back to the original
    # (bar 102 and Gaura's 82 in 8, his 91 in 11); 13 keeps "told them" but Zaril says his
    # own 95 again, with its own expression (3).
    'rec': [(0x800a8fca, 102), (0x800a9018, 82), (0x800a9270, 91), (0x800a93c2, 3), (0x800a93c8, 95)],
    # 2026-11-10, against disc ba971011 (block 13 already "told them"): Zaril says his own
    # "told them" reply 57 (".........And? So what?", blocks 1 and 2; same expression, 3)
    'b13': [(0x800a93c8, 57)],
}
if VARIANT == 'orig':            # the original table, from the clean MCARD, on the fixed disc
    _cl = open('rips/clean/dimguil/MCARD.BIN', 'rb').read()
    mc[TABLE:TABLE + 14 * 200] = _cl[TABLE:TABLE + 14 * 200]
elif VARIANT in RAW:
    for _a, _v in RAW[VARIANT]:
        struct.pack_into('<h', mc, _a - 0x800a1000, _v)
else:
    patch_table(VARIANTS[VARIANT])
mc = bytes(mc)
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
    f = 0; last = None; shot_n = 0; seen_msgs = 0; last_hash = [None]; msg_now = [None]
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
        if new:
            says = [m['idx'] for m in new if m['ra'] == SAY_RA]
            if says:
                msg_now[0] = says[-1]
        if ts == 0x28 and cur and msg_now[0] is not None:
            # one shot per page: shoot after every advance, keep it only if the screen changed
            tmp = f'{out}/_tmp.png'
            e.shot(tmp, scale=1)
            h = hashlib.md5(open(tmp, 'rb').read()).hexdigest()
            if h != last_hash[0]:
                last_hash[0] = h
                shot_n += 1
                os.replace(tmp, f'{out}/{tag}_p{cur[0]}_b{cur[1]}_{shot_n:02d}_{msg_now[0]}.png')
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
    tag = f'{VARIANT}{b:02d}' if b >= 0 else 'natural'
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
json.dump(results, open(f'{out}/results_{VARIANT}_{"_".join(map(str, blocks))}.json', 'w'), indent=1)
