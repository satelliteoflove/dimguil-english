#!/usr/bin/env python3
"""Find text cut off by a full glyph layer, in the emulator harness (emu.py).

    cutsweep.py STATE "KEYS" [--cue CUE]    e.g. cutsweep.py rips/states/trn_1.state "circle w90 start w60 down w60"

0x8001f840 refuses a glyph once its layer is full (docs/engine-notes.md, "Glyph sprite
layers"), and the line just stops. A line refused at its very first glyph is static
text being redrawn into a layer it already filled, which happens every frame on some
screens and is harmless; a cut-off is a refusal right after glyphs of the same line
were accepted. Prints (layer, y, x) for each one found while KEYS play.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import emu

ACCEPT, REFUSE = 0x8001f840, 0x8001f9cc
s16 = lambda v: (v & 0xffff) - 0x10000 if v & 0x8000 else v & 0xffff


def cuts(e, keys, frames_after=10):
    e.dbg_clear()
    e.bp(ACCEPT)
    e.bp(REFUSE)
    e.seq(keys)
    e.run(frames_after)
    log, out = e.log(), set()
    for k in range(3, len(log)):
        x, call, prev = log[k], log[k - 1], log[k - 2]
        # call: the glyph refused (logged at entry, just before REFUSE); prev: the glyph
        # before it, accepted, same layer and line (not itself a refusal)
        if x['pc'] == REFUSE and prev['pc'] == ACCEPT and log[k - 3]['pc'] != REFUSE \
                and prev['regs'][6] == x['regs'][6] and s16(prev['regs'][5]) == s16(call['regs'][5]):
            out.add((x['regs'][6], s16(call['regs'][5]), s16(call['regs'][4])))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('state')
    ap.add_argument('keys')
    ap.add_argument('--cue', default=os.path.join(os.path.dirname(__file__), '../rips/iso/dimguil-en.cue'))
    a = ap.parse_args()
    e = emu.Emu(a.cue)
    e.load(a.state)
    e.run(2)
    found = cuts(e, a.keys)
    print('\n'.join(f'layer {l}, line at y={y}: cut at x={x}' for l, y, x in found) or 'no cut-offs')


if __name__ == '__main__':
    main()
