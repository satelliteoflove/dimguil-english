#!/usr/bin/env python3
"""Check the built dialogue, event and castle strings against the text buffer.

    textbuf.py            (after a build; reads rips/dirty/dimguil)

Before printing, the game expands a whole string (all its pages) into a buffer at
0x8008b400 (expander 0x8001dfc0; dialogue, events and the castle text all go through
it). The buffer isn't bounded: 16 bytes of live data start at 0x8008b640, and a string
that expands past byte 576 has that part overwritten. Measured in the emulator with
filler strings: 557 bytes print whole; at 625 bytes, page 9 shows a run of zeros where
bytes 576-592 were, and the rest of the line is lost. This is the "random cutoff"
Remisse saw in long narrator lines.

Inserted names make a string a little longer when expanded than on disc, so strings are
held to LIMIT bytes, leaving MARGIN for them.
"""
import os, struct, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
FILES = ['DATA06/EVENTMES.BIN', 'DATA06/SISETU.OBJ'] + [f'DATA06/NPC_MES{n}.OBJ' for n in range(1, 6)]
BUFFER, MARGIN = 576, 32
LIMIT = BUFFER - MARGIN


def strings(d):
    """The file's strings, via the u32 offset table at its start."""
    first = struct.unpack_from('<I', d, 0)[0]
    offs = [struct.unpack_from('<I', d, 4 * i)[0] for i in range(first // 4)] + [len(d)]
    return [d[offs[i]:offs[i + 1]] for i in range(first // 4)]


def main():
    bad = 0
    for f in FILES:
        d = open(os.path.join(ROOT, 'rips/dirty/dimguil', f), 'rb').read()
        ss = strings(d)
        n, k = max((len(s), k) for k, s in enumerate(ss))
        for k2, s in enumerate(ss):
            if len(s) > LIMIT:
                bad += 1
                print(f'!! {f} string {k2}: {len(s)} bytes (max {LIMIT})')
        print(f'   {f}: longest is string {k}, {n} bytes')
    print(f'{bad} strings over {LIMIT} bytes')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
