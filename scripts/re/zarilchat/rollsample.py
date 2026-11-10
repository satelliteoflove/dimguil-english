"""The game's own chat roll, sampled (no forcing). Same setup as zchat.py (block -1). Each
trial seeds rand_upto's state (0x80079558 = 0x2345 + 1543 * t, as chat8_sample.py did),
plays the greeting, presses Talk once and logs every value the roll's rand_upto(0xd)
returned (breakpoint at MCARD 0x800dab14, just after the jal: v0), rerolls included, and
the talk_block that results.

    rollsample.py FIRST COUNT OUT.jsonl
"""
import json, os, sys
first, count, outp = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
sys.argv = [sys.argv[0], os.path.dirname(os.path.abspath(outp))]
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, 'zchat.py')).read().split('results = {}')[0]
__file__ = os.path.join(here, 'zchat.py')
exec(compile(src, 'zchat', 'exec'))
outp = os.path.abspath(os.path.join(here, os.path.basename(outp)))
fo = open(outp, 'a')
for t in range(first, first + count):
    setup(-1)
    e.write(0x80079558, (0x2345 + 1543 * t).to_bytes(4, 'little'))
    e.dbg_clear(); e.bp(0x800dab14); e.log()
    f = 0
    while s16(0x8007981c) != 0x14 and f < 3000:
        e.run(26); f += 26
        if s16(0x8007981c) != 0x14:
            e.press('circle', hold=2, after=2); f += 4
    while u8(0x80079b8c) != 0:
        e.press('up', hold=3, after=12)
    e.log()
    e.press('circle', hold=3, after=1)
    got = None
    for _ in range(300):
        e.run(2)
        ts = s16(0x8007981c)
        if ts not in (0x14, 0x19, 0x1e):
            got = (ts, u8(0x80079bb4)); break
    rolls = [x['regs'][2] for x in e.log() if x['type'] == 'X' and x['pc'] == 0x800dab14]
    row = dict(trial=t, talk_state=got[0] if got else None, block=got[1] if got else None,
               rolls=rolls, press_count=u8(0x80079be8))
    fo.write(json.dumps(row) + '\n'); fo.flush()
    e.dbg_clear()
