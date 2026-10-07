#!/usr/bin/env python3
"""Check the training maze's sign (SISETU 492) against the glyph layer its box gets.

    signfit.py            (after a build; reads rips/dirty/dimguil)

The box draws one sprite per glyph code from layer 0, which the maze resizes for the
sign at 0x800bef6c (see asm/training_sign_pool.asm). The size is read back from the
built MAZE.BIN, so the check follows whatever the asm sets.
"""
import os, struct, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
DIRTY = os.path.join(ROOT, 'rips/dirty/dimguil')
MAZE_BASE, SIZE_AT, STRING = 0x800a1000, 0x800bef6c, 492


def glyph_codes(s):
    """Glyph codes in an encoded string: 0xff xx is a control code, 0xf7-0xfe xx a
    two-byte glyph, anything else one glyph (a digraph counts once)."""
    i = n = 0
    while i < len(s):
        if s[i] == 0xff:
            i += 2
        else:
            n += 1
            i += 2 if s[i] >= 0xf7 else 1
    return n


def main():
    maze = open(os.path.join(DIRTY, 'MAZE.BIN'), 'rb').read()
    op = struct.unpack_from('<I', maze, SIZE_AT - MAZE_BASE)[0]
    if op >> 16 not in (0x2404, 0x3404):   # addiu or ori a0, zero, imm
        sys.exit(f'signfit: unexpected instruction {op:08x} at {SIZE_AT:#x}')
    size = op & 0xffff
    d = open(os.path.join(DIRTY, 'DATA06/SISETU.OBJ'), 'rb').read()
    offs = [struct.unpack_from('<I', d, 4 * i)[0] for i in range(STRING + 2)]
    n = glyph_codes(d[offs[STRING]:offs[STRING + 1]])
    print(f'SISETU {STRING}: {n} glyph codes, layer holds {size}')
    if n > size:
        sys.exit(f'!! SISETU {STRING} needs {n} glyphs; the sign box draws {size}')


if __name__ == '__main__':
    main()
