#!/usr/bin/env python3
"""Decode the NPC talk scripts in MCARD.BIN, static and stack-built.

    talkscripts.py [HANDLER ...] [--text] [--ram DUMP] [--json OUT]

HANDLER is a talk_party number (0-0x1c) or a function address; default all 28 handlers
main dispatches to in game state 0x35 (docs/re/C-talk.md). Prints, per handler, every
call site of talk_script_run with the script array it runs (base and stride per
talk_block), then each block decoded; --text adds the patch's English for each string.

How: each handler builds its scripts on its own stack every frame, from constant stores,
memset and copy loops out of MCARD's data, with a few slots filled from globals. A small
MIPS interpreter runs the handler from its entry, faithfully, over a RAM dump (default
rips/probe/ram_talk94.bin, taken during a talk) with the original MCARD.BIN mapped at
0x800a1000, until the handler first branches on its state (talk_state, the sub-state
0x80079669, talk_script_status) or calls anything but memset. Stack bytes stored from a
global that the code writes are marked {name=value}: those slots change at run time.
Each `jal talk_script_run` is then found in the handler, and the few instructions that
compute its argument are run twice, with talk_block 0 and 1, to get base and stride.

Opcodes (talk_script_run 0x800b8ccc, halfwords): see OPS below.
"""
import json, os, struct, sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
MCARD = os.path.join(ROOT, 'rips/q7iso/dimguil/MCARD.BIN')
BASE = 0x800a1000
RUN = 0x800b8ccc
MEMSET = 0x80024c50
SP0 = 0x801f8000                      # entry sp for the run; any unused high RAM
STACK = 0x20000                       # bytes below SP0 treated as the stack
# Builders: functions that build a script on their own stack and copy it into the
# caller's array (param_1). The run follows calls into these instead of skipping them.
DESCEND = {0x800c154c, 0x800c2564}
# Builders a handler calls in a later state are found by their argument (the base of a
# script array) and run on their own into the same stack image.
STATE = {0x8007981c: 'talk_state', 0x80079669: 'talk_sub', 0x800798a4: 'talk_script_status',
         0x80079bb4: 'talk_block'}

HANDLERS = {0: 0x800b5694, 1: 0x800c7264, 2: 0x800cf8c0, 3: 0x800d65c8, 4: 0x800d9b34,
            6: 0x800bff60, 7: 0x800c064c, 8: 0x800c08d0, 9: 0x800c0b68, 10: 0x800c12f4,
            11: 0x800ce4ec, 12: 0x800cea7c, 13: 0x800cebc8, 14: 0x800cee54, 15: 0x800cf0dc,
            16: 0x800cf364, 17: 0x800cf5f0, 18: 0x800d5750, 19: 0x800d5910, 20: 0x800d5d2c,
            21: 0x800d5f8c, 22: 0x800d902c, 23: 0x800d9334, 24: 0x800d9558, 25: 0x800d97e4,
            26: 0x800dbdd4, 27: 0x800dc114, 28: 0x800dc2d8}

# NPC_MES file each handler sets (DAT_800796bf = 0x33..0x37, table 2 index 51..55)
FILE = {0: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
        1: 2, 11: 2, 12: 2, 13: 2, 14: 2, 15: 2, 16: 2, 17: 2,
        2: 3, 18: 3, 19: 3, 20: 3, 21: 3,
        3: 4, 22: 4, 23: 4, 24: 4, 25: 4,
        4: 5, 26: 5, 27: 5, 28: 5}

# opcode: (name, fixed arg count); print-type ops take 3 when the first arg is -2 or -3
OPS = {-1: ('end', 0), 0: ('show', 2), 1: ('hide', 2), 2: ('say', 1), 3: ('face', 3),
       4: ('end4', 0), 5: ('close', 0), 6: ('load', 1), 7: ('bar', 1), 8: ('gold', 1),
       9: ('cure', 1), 10: ('slide', 4), 11: ('say2', 1)}
PRINTS = {2, 7, 11}


class Val:
    __slots__ = ('v', 't')

    def __init__(self, v, t=None):
        self.v = v & 0xffffffff
        self.t = t


def s32(x):
    x &= 0xffffffff
    return x - (1 << 32) if x & 0x80000000 else x


def sx16(x):
    return x - 0x10000 if x & 0x8000 else x


class Stop(Exception):
    pass


class Machine:
    def __init__(self, ram, writable):
        self.ram = bytearray(ram)
        self.writable = writable
        self.stack = {}          # addr -> (byte, taint)
        self.r = [Val(0) for _ in range(32)]
        self.hi = self.lo = Val(0)
        self.calls = []
        self.depth = 0

    # memory
    def rd(self, a, n, signed=False):
        a &= 0xffffffff
        if SP0 - STACK <= a < SP0 + 0x100:
            bs = [self.stack.get(a + i, (0, None)) for i in range(n)]
            v = sum(b[0] << (8 * i) for i, b in enumerate(bs))
            t = next((b[1] for b in bs if b[1]), None)
        else:
            off = a & 0x1fffff
            v = int.from_bytes(self.ram[off:off + n], 'little')
            t = None
            if a & ~3 in STATE or a in STATE:
                t = STATE.get(a, STATE.get(a & ~3))
            elif any((a + i) in self.writable for i in range(n)) or not (BASE <= a < BASE + 0x40000):
                if not (0x80010000 <= a < 0x80079538):   # executable code and rodata are constant
                    t = f'g:{a:08x}'
        if signed:
            v = v - (1 << (8 * n)) if v & (1 << (8 * n - 1)) else v
        return Val(v, t)

    def wr(self, a, n, val):
        a &= 0xffffffff
        if SP0 - STACK <= a < SP0 + 0x100:
            for i in range(n):
                self.stack[a + i] = ((val.v >> (8 * i)) & 0xff, val.t)
        # writes elsewhere are ignored: the run must not change the dump

    def reg(self, i):
        return self.r[i] if i else Val(0)

    def set(self, i, v):
        if i:
            self.r[i] = v

    def step(self, pc):
        """Execute one instruction (and its delay slot for branches); return the next pc."""
        w = struct.unpack_from('<I', self.ram, pc & 0x1fffff)[0]
        op, rs, rt, rd, sa, fn = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, (w >> 6) & 31, w & 63
        imm = w & 0xffff
        simm = sx16(imm)
        R = self.reg
        if op == 0:
            a, b = R(rs), R(rt)
            t = a.t or b.t
            if fn == 0x00: self.set(rd, Val(b.v << sa, b.t))
            elif fn == 0x02: self.set(rd, Val(b.v >> sa, b.t))
            elif fn == 0x03: self.set(rd, Val(s32(b.v) >> sa, b.t))
            elif fn == 0x04: self.set(rd, Val(b.v << (a.v & 31), t))
            elif fn == 0x06: self.set(rd, Val(b.v >> (a.v & 31), t))
            elif fn == 0x07: self.set(rd, Val(s32(b.v) >> (a.v & 31), t))
            elif fn == 0x08:                       # jr
                if rs == 31 and self.depth > 0:
                    ret = self.r[31].v
                    self.step(pc + 4)
                    self.depth -= 1
                    return ret
                raise Stop(f'jr at {pc:08x}')
            elif fn == 0x09:
                raise Stop(f'jalr at {pc:08x}')
            elif fn == 0x10: self.set(rd, self.hi)
            elif fn == 0x12: self.set(rd, self.lo)
            elif fn in (0x18, 0x19):
                p = (s32(a.v) * s32(b.v)) if fn == 0x18 else a.v * b.v
                self.lo, self.hi = Val(p, t), Val(p >> 32, t)
            elif fn in (0x1a, 0x1b):
                if b.v:
                    if fn == 0x1a:
                        q = int(s32(a.v) / s32(b.v)); m = s32(a.v) - q * s32(b.v)
                    else:
                        q, m = a.v // b.v, a.v % b.v
                    self.lo, self.hi = Val(q, t), Val(m, t)
            elif fn in (0x20, 0x21): self.set(rd, Val(a.v + b.v, t))
            elif fn in (0x22, 0x23): self.set(rd, Val(a.v - b.v, t))
            elif fn == 0x24: self.set(rd, Val(a.v & b.v, t))
            elif fn == 0x25: self.set(rd, Val(a.v | b.v, t))
            elif fn == 0x26: self.set(rd, Val(a.v ^ b.v, t))
            elif fn == 0x27: self.set(rd, Val(~(a.v | b.v), t))
            elif fn == 0x2a: self.set(rd, Val(int(s32(a.v) < s32(b.v)), t))
            elif fn == 0x2b: self.set(rd, Val(int(a.v < b.v), t))
            elif fn in (0x0c, 0x0d): raise Stop(f'syscall/break at {pc:08x}')
            return pc + 4
        if op in (2, 3):
            target = (pc & 0xf0000000) | ((w & 0x3ffffff) << 2)
            if op == 3:
                self.step(pc + 4)                  # delay slot first, then the call
                if target == MEMSET:
                    a0, a1, a2 = R(4).v, R(5).v & 0xff, R(6).v
                    for i in range(a2):
                        self.wr(a0 + i, 1, Val(a1))
                    self.set(2, Val(a0))
                    return pc + 8
                if target == RUN:
                    raise Stop(f'call talk_script_run at {pc:08x}')
                if target in DESCEND:
                    self.set(31, Val(pc + 8))
                    self.depth += 1
                    return target
                # any other call: assume it leaves the stack alone; its result is marked
                self.calls.append((pc, target))
                self.set(2, Val(0, f'ret:{target:08x}'))
                self.set(3, Val(0, f'ret:{target:08x}'))
                return pc + 8
            self.step(pc + 4)
            return target
        if op in (4, 5, 6, 7, 1):
            a, b = R(rs), R(rt)
            if op == 4: take = a.v == b.v
            elif op == 5: take = a.v != b.v
            elif op == 6: take = s32(a.v) <= 0
            elif op == 7: take = s32(a.v) > 0
            else:
                if rt in (0x10, 0x11):
                    raise Stop(f'bal at {pc:08x}')
                take = s32(a.v) < 0 if rt == 0 else s32(a.v) >= 0
            t = a.t or (b.t if op in (4, 5) else None)
            if t in STATE.values() and self.depth == 0:
                raise Stop(f'branch on {t} at {pc:08x}')
            self.step(pc + 4)
            return (pc + 4 + (simm << 2)) if take else pc + 8
        a = R(rs)
        if op == 8 or op == 9: self.set(rt, Val(a.v + simm, a.t)); return pc + 4
        if op == 0x0a: self.set(rt, Val(int(s32(a.v) < simm), a.t)); return pc + 4
        if op == 0x0b: self.set(rt, Val(int(a.v < (simm & 0xffffffff)), a.t)); return pc + 4
        if op == 0x0c: self.set(rt, Val(a.v & imm, a.t)); return pc + 4
        if op == 0x0d: self.set(rt, Val(a.v | imm, a.t)); return pc + 4
        if op == 0x0e: self.set(rt, Val(a.v ^ imm, a.t)); return pc + 4
        if op == 0x0f: self.set(rt, Val(imm << 16)); return pc + 4
        ea = (a.v + simm) & 0xffffffff
        if op == 0x20: self.set(rt, self.rd(ea, 1, True)); return pc + 4
        if op == 0x21: self.set(rt, self.rd(ea, 2, True)); return pc + 4
        if op == 0x23: self.set(rt, self.rd(ea, 4)); return pc + 4
        if op == 0x24: self.set(rt, self.rd(ea, 1)); return pc + 4
        if op == 0x25: self.set(rt, self.rd(ea, 2)); return pc + 4
        if op in (0x22, 0x26):                     # lwl, lwr
            al = ea & ~3
            word = self.rd(al, 4)
            old = R(rt)
            k = ea & 3
            if op == 0x22:
                shift = (3 - k) * 8
                mask = (0xffffffff << shift) & 0xffffffff
                v = (old.v & ~mask) | ((word.v << shift) & mask)
            else:
                shift = k * 8
                mask = 0xffffffff >> shift
                v = (old.v & ~mask) | (word.v >> shift)
            self.set(rt, Val(v, word.t or old.t))
            return pc + 4
        if op == 0x28: self.wr(ea, 1, R(rt)); return pc + 4
        if op == 0x29: self.wr(ea, 2, R(rt)); return pc + 4
        if op == 0x2b: self.wr(ea, 4, R(rt)); return pc + 4
        if op in (0x2a, 0x2e):                     # swl, swr
            val = R(rt)
            k = ea & 3
            al = ea & ~3
            if op == 0x2a:
                for i in range(k + 1):
                    self.wr(al + i, 1, Val(val.v >> (8 * (4 - k - 1 + i)), val.t))
            else:
                for i in range(4 - k):
                    self.wr(al + k + i, 1, Val(val.v >> (8 * i), val.t))
            return pc + 4
        if op == 0x32 or op == 0x3a or op == 0x12:  # lwc2/swc2/cop2: not in the builders
            raise Stop(f'cop2 at {pc:08x}')
        raise Stop(f'unknown op {op:#x} at {pc:08x}')


def load_ram(dump):
    ram = bytearray(open(dump, 'rb').read())
    code = open(MCARD, 'rb').read()
    ram[BASE & 0x1fffff:(BASE & 0x1fffff) + len(code)] = code
    return ram, len(code)


def writable_set():
    g = json.load(open(os.path.join(ROOT, 'rips/re/globals.json')))
    out = set()
    for k, v in g.items():
        mod, a = k.split(':')
        if v.get('writers'):
            a = int(a, 16)
            for i in range(4):
                out.add(a + i)
    return out


def build_stack(ram, writable, entry, limit=3_000_000):
    m = Machine(ram, writable)
    m.r[29] = Val(SP0)
    m.r[31] = Val(0xdeadbeef)
    pc = entry
    why = 'step limit'
    try:
        for _ in range(limit):
            pc = m.step(pc)
    except Stop as e:
        why = str(e)
    return m, why


def call_sites(code, entry, end, target=RUN):
    """jal sites in [entry, end) calling `target` (None: any MCARD function)."""
    sites = []
    for a in range(entry, end, 4):
        w = struct.unpack_from('<I', code, a - BASE)[0]
        if w >> 26 == 3:
            t = (w & 0x3ffffff) << 2 | 0x80000000
            if t == target or (target is None and BASE <= t < BASE + len(code) and t != RUN):
                sites.append((a, t) if target is None else a)
    return sites


def _run_path(ram, pieces, site):
    """Run the instruction ranges in `pieces` (lists of addresses), skipping branches,
    then the delay slot of the jal at `site`, with talk_block 0 and 1; return a0 for both."""
    res = []
    for tb in (0, 1):
        r2 = bytearray(ram)
        r2[0x80079bb4 & 0x1fffff] = tb
        m = Machine(r2, set())
        m.r[29] = Val(SP0)
        try:
            for pc in pieces:
                w = struct.unpack_from('<I', r2, pc & 0x1fffff)[0]
                op = w >> 26
                if op in (1, 2, 3, 4, 5, 6, 7) or (op == 0 and (w & 63) in (8, 9)):
                    continue
                m.step(pc)
            m.step(site + 4)
        except Stop:
            return None
        res.append(m.r[4].v)
    return res


def _is_branch(w):
    op = w >> 26
    return op in (1, 4, 5, 6, 7) or op == 2


def _target(pc, w):
    op = w >> 26
    if op == 2:
        return (pc & 0xf0000000) | ((w & 0x3ffffff) << 2)
    return pc + 4 + (sx16(w & 0xffff) << 2)


def site_args(ram, code, entry, end, site, back=16):
    """Every (base offset, stride) a jal talk_script_run at `site` can run: the straight
    path into it, and each branch elsewhere in the handler that lands just before it."""
    paths = []
    lo = site - 4 * back
    # the straight path: from the last branch target or branch before the site
    start = lo
    for a in range(site - 4, lo - 4, -4):
        w = struct.unpack_from('<I', code, a - BASE)[0]
        if _is_branch(w) or (w >> 26 == 0 and (w & 63) == 8):
            start = a + 8
            break
    paths.append(list(range(start, site, 4)))
    # branches from elsewhere (outside the straight path) into it
    for b in range(entry, end, 4):
        w = struct.unpack_from('<I', code, b - BASE)[0]
        if not _is_branch(w):
            continue
        t = _target(b, w)
        if lo <= t <= site and not (start - 8 <= b < site):
            pre = []
            for a in range(b - 4, b - 4 * 12, -4):
                w2 = struct.unpack_from('<I', code, a - BASE)[0]
                if _is_branch(w2) or (w2 >> 26 == 0 and (w2 & 63) == 8):
                    break
                pre.insert(0, a)
            paths.append(pre + [b + 4] + list(range(t, site, 4)))
    out = []
    for pieces in paths:
        r = _run_path(ram, pieces, site)
        if r is None:
            continue
        a0, a1 = r
        off = (a0 - SP0) & 0xffffffff
        stride = (a1 - a0) & 0xffffffff
        if 0 <= off < 0x10000 and 0 <= stride < 0x400 and (off, stride) not in out:
            out.append((off, stride))
    return out


def halfwords(m, addr, n):
    out = []
    for i in range(n):
        lo = m.stack.get(addr + 2 * i)
        hi = m.stack.get(addr + 2 * i + 1)
        if lo is None and hi is None:
            out.append(None)
            continue
        v = (lo or (0, None))[0] | ((hi or (0, None))[0] << 8)
        t = (lo or (0, None))[1] or (hi or (0, None))[1]
        out.append((sx16(v), t))
    return out


def english():
    tr = {}
    for n in range(1, 6):
        p = os.path.join(ROOT, f'translations/NPC_MES{n}.OBJ.json')
        d = json.load(open(p, encoding='utf-8'))
        tr[n] = [s.get('translation') or '' for s in d['sections'][0]['strings']]
    return tr


def decode_block(hw, names=None):
    """Decode one block (list of (value, taint)); return (ops, ok)."""
    ops, i = [], 0
    while i < len(hw):
        if hw[i] is None:
            return ops, False
        v, t = hw[i]
        if v not in OPS:
            return ops, False
        name, n = OPS[v]
        args = []
        if v in PRINTS and i + 1 < len(hw) and hw[i + 1] and hw[i + 1][0] in (-2, -3):
            n = 3
        for k in range(n):
            if i + 1 + k >= len(hw) or hw[i + 1 + k] is None:
                return ops, False
            args.append(hw[i + 1 + k])
        ops.append((name, v, args))
        i += 1 + n
        if v in (-1, 4, 5):
            return ops, True
    return ops, False


def fmt_arg(a):
    v, t = a
    return f'{{{t}={v}}}' if t else str(v)


def label(text, n=48):
    """Speaker and the start of a string, on one line."""
    t = text.replace('{ff40}', '').replace('\r', ' ').replace('\n', ' ')
    t = ' '.join(t.split())
    return t[:n] + ('...' if len(t) > n else '')


def string_ref(op, args):
    """The string index a print op shows, or None if it's chosen at run time."""
    if len(args) == 3:
        v, t = args[2]
    else:
        v, t = args[0]
    return None if t else v


def main():
    args = sys.argv[1:]
    dump = os.path.join(ROOT, 'rips/probe/ram_talk94.bin')
    out_json = None
    if '--ram' in args:
        k = args.index('--ram'); dump = args[k + 1]; del args[k:k + 2]
    if '--json' in args:
        k = args.index('--json'); out_json = args[k + 1]; del args[k:k + 2]
    show_text = '--text' in args
    args = [a for a in args if a != '--text']
    which = [int(a, 0) for a in args] or sorted(HANDLERS)
    eng = english()
    ram, codelen = load_ram(dump)
    code = open(MCARD, 'rb').read()
    writable = writable_set()
    idx = json.load(open(os.path.join(ROOT, 'rips/re/decomp/MCARD/index.json')))['functions']
    ends = {int(f['addr'], 16): int(f['end'], 16) + 1 for f in idx}
    allout = {}
    for h in which:
        entry = HANDLERS.get(h, h)
        end = ends[entry]
        fileno = FILE.get(h, 1)
        m, why = build_stack(ram, writable, entry)
        w0 = struct.unpack_from('<I', code, entry - BASE)[0]
        frame = -sx16(w0 & 0xffff) if w0 >> 16 == 0x27bd else 0
        sp = SP0 - frame
        arrays, unresolved = {}, []
        for site in call_sites(code, entry, end):
            rs = site_args(ram, code, entry, end, site)
            if not rs:
                unresolved.append(site)
            for r in rs:
                arrays.setdefault(r, []).append(site)
        # builders called in later states: a call whose a0 is the base of a script array
        bases = {off for off, _ in arrays}
        builders = []
        for site, fn in call_sites(code, entry, end, None):
            for off, _ in site_args(ram, code, entry, end, site):
                if off in bases and (fn, off) not in builders:
                    builders.append((fn, off))
        snaps = {}
        for fn, off in builders:
            # run the builder as if called from the handler's frame, into the same stack;
            # keep a copy right after it, since builders' arrays can overlap (Guy's 43
            # greeting blocks run into the topic array FUN_800c2564 fills in another state)
            m.r = [Val(0) for _ in range(32)]
            m.r[29] = Val(sp)
            m.r[4] = Val(sp + off)
            m.r[31] = Val(0xdeadbeef)
            m.depth = 1
            pc = fn
            try:
                for _ in range(3_000_000):
                    pc = m.step(pc)
                    if pc == 0xdeadbeef:
                        break
            except Stop as e:
                print(f'  (builder {fn:08x} stopped: {e})')
            snaps[off] = dict(m.stack)
        calls = ', '.join(f'{t:08x}' for _, t in m.calls)
        print(f'== handler {h} at {entry:08x}, frame {frame:#x} (stack built; stopped: {why}'
              f'{"; calls " + calls if calls else ""})')
        if builders:
            print('  builders: ' + ', '.join(f'{fn:08x} -> sp+{off:#x}' for fn, off in builders))
        for site in unresolved:
            print(f'  run at {site:08x}: argument not resolved')
        hout = []
        for (off, stride), sites in sorted(arrays.items()):
            where = ', '.join(f'{x:08x}' for x in sites)
            print(f'  array sp+{off:#x}' + (f', talk_block*{stride}' if stride else ' (one script)')
                  + f'; run at {where}')
            blocks = []
            view = m
            if off in snaps:
                view = Machine(m.ram, set())
                view.stack = snaps[off]
            for b in range(64 if stride else 1):
                hw = halfwords(view, sp + off + b * stride, stride // 2 if stride else 400)
                if all(x is None for x in hw):
                    break
                ops, ok = decode_block(hw)
                if not ops or (not ok and b > 0 and all(x and x[0] == 0 for x in hw if x)):
                    break
                text = ' '.join(f'{nm}(' + ','.join(fmt_arg(a) for a in ar) + ')' for nm, _, ar in ops)
                print(f'    [{b}] {text}{"" if ok else "  ..."}')
                if show_text:
                    for nm, v, ar in ops:
                        if v in PRINTS:
                            k = string_ref(v, ar)
                            if k is not None and k < len(eng[fileno]):
                                print(f'          {fileno}:{k} {label(eng[fileno][k])}')
                blocks.append({'block': b, 'ok': ok,
                               'ops': [[nm, [list(x) for x in ar]] for nm, _, ar in ops]})
            hout.append({'base': off, 'stride': stride, 'sites': [f'{x:08x}' for x in sites],
                         'blocks': blocks})
        allout[h] = {'entry': f'{entry:08x}', 'file': fileno, 'stop': why, 'arrays': hout,
                     'unresolved': [f'{x:08x}' for x in unresolved]}
    if out_json:
        json.dump(allout, open(out_json, 'w'), indent=1)


if __name__ == '__main__':
    main()
