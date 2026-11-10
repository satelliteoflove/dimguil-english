"""Python copy of rand_upto (MAIN 0x8001cb18), instruction for instruction, to find its range and odds."""
import collections, random, sys
M = 0xffffffff
def s32(x): x &= M; return x - (1 << 32) if x & 0x80000000 else x
def sra(x, n): return (s32(x) >> n) & M
def rand_upto(a0, st):
    g20, g24 = st
    t2 = a2 = v1 = a3 = a0 & M
    t4 = 1 if s32(a0) < 0 else 0
    t3 = (a0 + 1) & M
    while True:
        a1 = 4
        t1, t0 = g20, g24
        while True:
            a3 = (a3 + t1) & M
            v1 = (v1 + t0) & M
            a2 = (a2 + sra(v1, 16)) & M
            t2 = (t2 + sra(a2, 16)) & M
            v1 &= 0xffff
            a1 -= 1
            a3 &= 0xffff
            if a1 < 0: break
        t0 = (a3 + a2) & M
        a2 = 0
        v0 = (v1 + t2) & M
        v1 = 0
        g20, g24 = t0, v0
        a1 = 0
        if not t4:
            while True:
                v1 = (v1 + t0) & M
                a2 = (a2 + sra(v1, 16)) & M
                a1 += 1
                v1 &= 0xffff
                if s32(a0) < a1: break
        if a2 != t3:
            return a2, (g20, g24)
        a1 = 4
st = (int(sys.argv[1], 0), int(sys.argv[2], 0)) if len(sys.argv) > 2 else (0x2345, 0x6789)
c = collections.Counter(); seq = []
for i in range(200000):
    r, st = rand_upto(13, st); c[r] += 1
    if i < 40: seq.append(r)
print('sequence from the state:', seq)
print('rand_upto(13) over 200000 chained calls:', sorted(c.items()))
c2 = collections.Counter()
for i in range(200000):
    r, _ = rand_upto(13, (random.getrandbits(32), random.getrandbits(32))); c2[r] += 1
print('over 200000 random 32-bit states:', sorted(c2.items()))
