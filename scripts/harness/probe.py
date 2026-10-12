"""Find the RAM bytes that track a button: candidates that change by the same step every
time the button is pressed, and back again with the opposite button. A development aid.

    probe.find_cursor(g, 'right', 'left')  ->  [(addr, values seen), ...]
"""
RANGES = [(0x80079500, 0x8007a000), (0x8007e800, 0x8007f000), (0x800a1000, 0x80100000)]


def snap(g, ranges=None):
    return {lo: g.e.read(lo, hi - lo) for lo, hi in ranges or RANGES}


def find_cursor(g, fwd, back, n=3, settle=12, ranges=None):
    ranges = ranges or RANGES
    seq = []
    s = snap(g, ranges); seq.append(s)
    for b in [fwd] * n + [back] * n:
        g.tap(b)
        g.step(settle)
        seq.append(snap(g, ranges))
    out = []
    for lo, hi in ranges:
        for off in range(hi - lo):
            vals = [x[lo][off] for x in seq]
            d = [(vals[k + 1] - vals[k]) & 0xff for k in range(len(vals) - 1)]
            if len(set(d[:n])) == 1 and d[0] != 0 and len(set(d[n:])) == 1 and (d[0] + d[n]) & 0xff == 0:
                out.append((lo + off, vals))
    return out
