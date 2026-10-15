#!/usr/bin/env python3
"""Watch a human play Dimguil in RetroArch, read-only, and log the trip in a shape close
to the harness's trip logs, so a person's choices can be set beside the bot's.

    humanwatch.py [--session NAME] [--out DIR] [--port 55355] [--bin IMAGE]

It talks to RetroArch over its network commands (network_cmd_enable, UDP 55355; see
rips/humanplay/humanplay.cfg) and only ever sends READ_CORE_MEMORY and GET_STATUS: no
pause, no save state, nothing that changes the game. RetroArch answers once per frame,
so every read costs about a frame; the loop reads the text buffer every pass and the
rest of RAM every other pass.

What it reads (physical addresses; the harness's, scripts/harness/game.py and friends):
  0x8b400   the text buffer: every dialogue, event, town and battle string is expanded
            whole into it just before it prints (playwatch.py's reader; identified
            against the disc image's text files)
  0x60788   the game's frame counter, the stamp on every line
  0x79600-  the game's globals: overlay 0x798b3, game state 0x79a13 (3 camp), town state
            0x79b18, area 0x79668, x/y 0x79906/0x79916, facing 0x79b34, battle phase
            0x796fa (0x1c commands, 0x42 chest), fixed battle 0x79bde, roster count 0x79891
  0x7d708   the roster, 0xd0 a character (game.py char()); 0x7e810 the party's slots
  0x8c480   battle groups, 8 bytes each: +0 identified, +2 monster id, +4 count, +5 standing
  0x8e230   combatants, 14 bytes each, group k at +k*0x7e: +6 HP, +0xc status
  0x8a918   monster records, 0xd0 a group: +0x24 the English name, +0x74 level

Output: <out>/<session>/log.jsonl, one JSON list per line, [frame, kind, ...] like the
harness's run log:
  msg        every string the game shows: file, index, text, mode
  start      the session's first look: where, party
  set out / home   leaving town for the maze, and back
  floor      a change of area; pos: each square stepped on (area, x, y, facing)
  battle     a fight starts: where, groups (id, name, level, count), HP and points
  fought     a fight ends: rounds, frames, outcome, groups at start and end, casts and
             item uses (from the messages), points spent by school and level, HP before
             and after, down_end, dead_end, deaths, fled, gold and experience, chest
  chest      the chest's messages in order and how it ended (disarmed, sprung, ...)
  camp       a camp or START-menu visit: points spent, HP, status, items changed
  town       a town facility visit: gold, items bought, sold or gone, HP, status,
             levels, points, party changes
  trip       on getting home (or at stop): fights, rounds, runs, deaths, chests, floors,
             and each member's experience, gold and levels from setting out
  status / death / level   a member's status or level changing outside those
  snap       the whole party block, when it changed (at most every 30 frames) and at
             every change of mode
"""
import argparse, json, os, re, signal, socket, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from playwatch import Text, iso_files, FILES, BUF, BUF_LEN, HEAD, FRAME, STAGE   # noqa: E402
from harness import text as T                                             # noqa: E402

ALLOWED = ('READ_CORE_MEMORY', 'GET_STATUS')     # the only commands this ever sends

G0, G_LEN = 0x79600, 0x680                       # the globals block
RESIDENT, GAME_STATE, TOWN_STATE = 0x798b3, 0x79a13, 0x79b18
AREA, POS_X, POS_Y, FACING = 0x79668, 0x79906, 0x79916, 0x79b34
PHASE, FIXED, ROSTER_COUNT = 0x796fa, 0x79bde, 0x79891
ROSTER, REC = 0x7d708, 0xd0
PARTY_REC = 0x7e810
GROUPS, COMBAT, MREC = 0x8c480, 0x8e230, 0x8a918
OVL = {1: 'JOUKA', 2: 'MAZE', 3: 'BATTLE', 4: 'HAZURE', 5: 'MCARD'}
CMD_PHASE, CHEST_PHASE = 0x1c, 0x42
CAMP, START_MENU = 3, 0x34      # game states: the camp, the maze's START menu (spells, items)
FACILITY = {5: None, 1: None, 10: 'tavern', 15: 'inn', 20: 'boltac', 25: 'temple',
            30: 'training', 40: 'edge'}
CLASSES = ['Fighter', 'Mage', 'Priest', 'Thief', 'Samurai', 'Lord', 'Valkyrie', 'Ranger',
           'Bard', 'Alchemist', 'Psionic', 'Bishop', 'Ninja', 'Monk']
SCHOOL = 'MPAS'
DEAD = 0x80 | 0x100 | 0x200
STATUS = [(0x200, 'lost'), (0x100, 'ashes'), (0x80, 'dead'), (0x40, 'stoned'), (0x20, 'paralyzed'),
          (0x10, 'out'), (0x08, 'asleep'), (0x04, 'poisoned'), (0x02, 'confused'), (0x01, 'afraid')]
IDENT, EQUIPPED, CURSED = 0x4000, 0x2000, 0x8000

NAME_DEC = {}
for _l in open(os.path.join(ROOT, 'tables/dimguil_dec.tbl'), encoding='utf-8'):
    _k, _, _v = _l.rstrip('\n').partition('=')
    if _k and len(_k) <= 2:
        NAME_DEC[int(_k, 16)] = _v

ITEM_NAMES = {}
try:
    for _r in json.load(open(os.path.expanduser(
            '~/Documents/bartoks-trading-post/data/items/dim/ps.json')))['records']:
        ITEM_NAMES[_r['no']] = _r['name']['en'].replace('/', ' ')   # '/' is the menus' line break
except Exception:
    pass


def item_name(w):
    s = ITEM_NAMES.get(w & 0x1ff, '#%d' % (w & 0x1ff))
    if not w & IDENT:
        s += ' (unidentified)'
    if w & CURSED:
        s += ' (cursed)'
    return s


def status_name(st):
    names = [n for b, n in STATUS if st & b]
    return '+'.join(names) if names else 'ok'


# --- RetroArch, read-only ---

class Reader:
    """READ_CORE_MEMORY and GET_STATUS over UDP; nothing else can be sent. A large read
    goes in one command when RetroArch takes it; a short or missing reply halves the
    chunk (down to 256 bytes, what playwatch.py uses) and the read goes on from there."""

    def __init__(self, port=55355, host='127.0.0.1', chunk=8192):
        self.addr = (host, port)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.chunk = chunk
        self.asks = 0

    def ask(self, cmd):
        if cmd.split()[0] not in ALLOWED:
            raise ValueError('humanwatch never sends ' + cmd.split()[0])
        self.s.setblocking(False)
        while True:                             # drop stale replies
            try:
                self.s.recv(65536)
            except (BlockingIOError, OSError):
                break
        self.s.settimeout(0.5)
        self.asks += 1
        self.s.sendto(cmd.encode(), self.addr)
        try:
            return self.s.recv(65536).decode('ascii', 'replace').strip()
        except (socket.timeout, ConnectionRefusedError, OSError):
            return None

    def read(self, addr, n):
        out = b''
        while len(out) < n:
            k = min(self.chunk, n - len(out))
            a = addr + len(out)
            r = self.ask('READ_CORE_MEMORY %x %d' % (a, k))
            parts = r.split() if r else []
            if len(parts) < 3 or parts[2] == '-1':
                if r is not None and k <= 256:
                    return None
                if k > 256:
                    self.chunk = max(256, k // 2)
                    continue
                return None
            try:
                got = bytes(int(x, 16) for x in parts[2:])
            except ValueError:
                return None
            if not got:
                return None
            if len(got) < k:
                self.chunk = max(256, len(got))
            out += got
        return out

    def status(self):
        r = self.ask('GET_STATUS')              # GET_STATUS PLAYING|PAUSED|CONTENTLESS ...
        return r.split()[1] if r and len(r.split()) > 1 else None


# --- snapshots ---

def u8(b, a):
    return b[a - G0]


def char(d, ri):
    return dict(ri=ri, name=''.join(NAME_DEC.get(c, '?') for c in d[:10].split(b'\xff')[0]),
                cls=CLASSES[d[0x0b] & 0x7f] if (d[0x0b] & 0x7f) < len(CLASSES) else d[0x0b] & 0x7f,
                lv=struct.unpack_from('<H', d, 0x44)[0], exp=struct.unpack_from('<I', d, 0x40)[0],
                hp=struct.unpack_from('<h', d, 0x46)[0], mhp=struct.unpack_from('<h', d, 0x4a)[0],
                st=struct.unpack_from('<H', d, 0x0e)[0], sp=list(d[0x5c:0x78]),
                gold=struct.unpack_from('<I', d, 0x1c)[0],
                items=[w for w in struct.unpack_from('<10H', d, 0x20) if w != 0xffff],
                at=d[0x7a])


def mon_name(rec):
    return ' '.join(T.decode(rec[0x24:0x48].split(b'\0')[0]).split())


class Snapper:
    """One look at the game's state (a few reads)."""

    def __init__(self, ra):
        self.ra = ra
        self.names = {}             # group -> (id, name, level), read once per battle

    def frame(self):
        d = self.ra.read(FRAME, 4)
        return struct.unpack('<I', d)[0] if d else None

    def snap(self, battle_names=False):
        f = self.frame()
        g = self.ra.read(G0, G_LEN)
        if f is None or g is None:
            return None
        ovl = OVL.get(u8(g, RESIDENT), '?')
        s = dict(f=f, ovl=ovl, gs=u8(g, GAME_STATE), town=u8(g, TOWN_STATE), area=u8(g, AREA),
                 x=u8(g, POS_X), y=u8(g, POS_Y), face=u8(g, FACING), phase=u8(g, PHASE),
                 fixed=u8(g, FIXED))
        if ovl in ('JOUKA', 'HAZURE'):
            s['mode'] = 'town'
        elif ovl == 'BATTLE':
            s['mode'] = 'battle'
        elif ovl in ('MAZE', 'MCARD') and s['town'] == 0xff:
            s['mode'] = 'camp' if s['gs'] in (CAMP, START_MENU) else 'maze'
        else:
            s['mode'] = 'other'
        pr = self.ra.read(PARTY_REC, 8)
        if pr is None:
            return None
        s['slots'] = [None if b == 0xff else b for b in pr[2:8]]
        n = min(max(u8(g, ROSTER_COUNT), max([i for i in s['slots'] if i is not None] + [-1]) + 1), 20)
        rd = self.ra.read(ROSTER, n * REC) if n else b''
        if rd is None:
            return None
        s['roster'] = {i: char(rd[i * REC:(i + 1) * REC], i) for i in range(n)
                       if rd[i * REC] not in (0, 0xff)}
        if s['mode'] == 'battle':
            gr = self.ra.read(GROUPS, 7 * 8)
            cb = self.ra.read(COMBAT, 7 * 0x7e)
            if gr and cb:
                nmax = 6 if s['fixed'] else 4
                s['groups'] = []
                for k in range(1, nmax + 1):
                    cnt, up = gr[k * 8 + 4], gr[k * 8 + 5]
                    if not cnt:
                        continue
                    mid = struct.unpack_from('<H', gr, k * 8 + 2)[0]
                    hp = [struct.unpack_from('<h', cb, k * 0x7e + j * 0xe + 6)[0] for j in range(min(cnt, 9))]
                    s['groups'].append(dict(k=k, id=mid, n=cnt, up=up, ident=gr[k * 8], hp=hp))
                s['cmb'] = [(struct.unpack_from('<h', cb, m * 0xe + 6)[0],
                             struct.unpack_from('<H', cb, m * 0xe + 0xc)[0]) for m in range(6)]
                if battle_names:
                    mr = self.ra.read(MREC, 7 * 0xd0)
                    if mr:
                        for q in s['groups']:
                            rec = mr[q['k'] * 0xd0:(q['k'] + 1) * 0xd0]
                            self.names[q['k']] = (q['id'], mon_name(rec), struct.unpack_from('<H', rec, 0x74)[0])
        return s


# --- the log ---

def party_of(s):
    return [i for i in s['slots'] if i is not None]


def brief(s):
    return [dict(name=c['name'], cls=c['cls'], lv=c['lv'], hp=c['hp'], mhp=c['mhp'],
                 st=status_name(c['st']), sp=sp_str(c['sp']), gold=c['gold'],
                 items=[item_name(w) + (' [E]' if w & EQUIPPED else '') for w in c['items']])
            for c in (s['roster'][i] for i in party_of(s) if i in s['roster'])]


def sp_str(sp):
    return ' '.join(SCHOOL[k] + ''.join(str(v) for v in sp[k * 7:k * 7 + 7])
                    for k in range(4) if any(sp[k * 7:k * 7 + 7]))


def where(s):
    return [s['area'], s['x'], s['y'], s['face']]


def spent(a, b):
    """Points used between two copies of a member: [(school, level, n)]."""
    return [(SCHOOL[k // 7], k % 7 + 1, a['sp'][k] - b['sp'][k]) for k in range(28) if a['sp'][k] > b['sp'][k]]


def diff_members(s0, s1, who=None):
    """What changed for each member between two snapshots: HP, status, level, points,
    gold, items (gained / lost / identified / equipped)."""
    out = []
    ids = who if who is not None else sorted(set(s0['roster']) | set(s1['roster']))
    for i in ids:
        a, b = s0['roster'].get(i), s1['roster'].get(i)
        if not a or not b:
            continue
        d = {}
        if a['hp'] != b['hp']:
            d['hp'] = [a['hp'], b['hp']]
        if a['mhp'] != b['mhp']:
            d['mhp'] = [a['mhp'], b['mhp']]
        if a['st'] != b['st']:
            d['status'] = [status_name(a['st']), status_name(b['st'])]
        if a['lv'] != b['lv']:
            d['level'] = [a['lv'], b['lv']]
        if a['gold'] != b['gold']:
            d['gold'] = b['gold'] - a['gold']
        sp = spent(a, b)
        if sp:
            d['spent'] = sp
        if any(b['sp'][k] > a['sp'][k] for k in range(28)):
            d['sp'] = [sp_str(a['sp']), sp_str(b['sp'])]
        # items: words kept exactly are no change; of the rest, the same item id on both
        # sides is a flag change (identified, equipped, cursed), the others came or went
        ra, rb = list(a['items']), list(b['items'])
        for w in list(ra):
            if w in rb:
                ra.remove(w)
                rb.remove(w)
        idd, eq, gone = [], [], []
        for w in ra:
            m = next((v for v in rb if v & 0x1ff == w & 0x1ff), None)
            if m is None:
                gone.append(w)
                continue
            rb.remove(m)
            nm = ITEM_NAMES.get(w & 0x1ff, '#%d' % (w & 0x1ff))
            if m & IDENT and not w & IDENT:
                idd.append(nm)
            if (m ^ w) & EQUIPPED:
                eq.append([nm, 'on' if m & EQUIPPED else 'off'])
            if m & CURSED and not w & CURSED:
                d.setdefault('cursed', []).append(nm)
        if gone:
            d['items_gone'] = [item_name(w) for w in gone]
        if rb:
            d['items_new'] = [item_name(w) for w in rb]
        if idd:
            d['identified'] = idd
        if eq:
            d['equip'] = eq
        if d:
            out.append(dict(name=b['name'], **d))
    return out


def shown(msgs):
    """The texts of messages worth reading back: no menu labels redrawn every frame
    (STATUS.OBJ), no bare numbers or 'Empty', no repeats in a row."""
    out = []
    for m in msgs:
        t = ' '.join(m['text'].split())
        if m['file'] == 'STATUS.OBJ' or not t or re.fullmatch(r'[\d/ ]+|Empty|\?', t):
            continue
        if not out or out[-1] != t:
            out.append(t)
    return out


CAST_RE = re.compile(r'^(.*?)\s+casts\s+(.+?)\.?$', re.S)
USE_RE = re.compile(r'^(.*?)\s+uses\s+(.+?)\.?$', re.S)
GAIN_RE = re.compile(r'gains\s+(\d+)\s+(experience|gold)')


class Watch:
    def __init__(self, a):
        self.a = a
        self.ra = Reader(a.port, chunk=a.chunk)
        self.snapper = Snapper(self.ra)
        img = a.bin
        self.text = Text(iso_files(img, FILES))
        d = os.path.join(a.out, a.session)
        os.makedirs(d, exist_ok=True)
        self.path = os.path.join(d, 'log.jsonl')
        self.f = open(self.path, 'a')
        self.last_head = None
        self.prev = None            # the last snapshot
        self.fight = None
        self.visit = None           # an open town facility visit
        self.camp = None            # the snapshot as a camp or START menu opened
        self.last_snap = None       # (frame, key) of the last snap line
        self.msgs_since = []        # the messages since the last mode change
        self.cur_frame = 0
        self.mode = None
        self.chest = None
        self.trip = None            # from setting out to home (trip_summary)

    # -- output --
    def log(self, kind, *a):
        x = [self.cur_frame, kind] + list(a)
        self.f.write(json.dumps(x, ensure_ascii=False, default=str) + '\n')
        self.f.flush()
        if kind != 'snap' and not self.a.quiet:
            s = json.dumps(a, ensure_ascii=False, default=str)
            print('%9d %-8s %s' % (self.cur_frame, kind, s[:150]), flush=True)

    # -- text --
    def check_text(self):
        head = self.ra.read(BUF, HEAD)
        if head is None or head == self.last_head:
            return False
        first = self.last_head is None
        self.last_head = head
        buf = self.ra.read(BUF, BUF_LEN) or head
        end = buf.find(b'\xff\x40')
        if end <= 0:
            return False
        buf = buf[:end]
        hit = self.text.identify(buf, self.ra.read(STAGE, 16) or b'')
        shown = self.text.decode(buf)
        f = self.snapper.frame()
        if f is not None:
            self.cur_frame = f
        m = dict(file=hit[0] if hit else None, idx=hit[1] if hit else None, text=shown,
                 mode=self.mode)
        if first:
            m['already_shown'] = True
        self.log('msg', m)
        self.msgs_since.append(m)
        if self.fight is not None:
            self.fight['msgs'].append(m)
        if self.camp is not None:
            self.camp[1].append(m)
        if self.visit is not None:
            self.visit['msgs'].append(m)
        return True

    # -- state --
    def snap_line(self, s, force=False):
        key = json.dumps([[c['hp'], c['st'], c['sp'], c['gold'], c['items'], c['lv']]
                          for c in (s['roster'][i] for i in party_of(s) if i in s['roster'])])
        if not force and self.last_snap and (key == self.last_snap[1] or s['f'] - self.last_snap[0] < 30):
            return
        self.last_snap = (s['f'], key)
        self.log('snap', dict(mode=s['mode'], where=where(s), town=s['town'], party=brief(s)))

    def update(self, s):
        self.cur_frame = s['f']
        p = self.prev
        if p is None:
            self.mode = s['mode']
            self.log('start', dict(mode=s['mode'], where=where(s), town=s['town'],
                                   ovl=s['ovl'], party=brief(s)))
            self.snap_line(s, force=True)
            self.prev = s
            if s['mode'] == 'battle':
                self.open_fight(s, s)
            if s['mode'] == 'camp':
                self.camp = (s, [])
            if s['mode'] == 'town':
                self.open_visit(s)
            return
        if s['mode'] == 'other':
            return                      # loading between overlays: wait for the next look
        if s['mode'] != p['mode']:
            self.change_mode(p, s)
        elif s['mode'] == 'battle':
            self.battle_step(p, s)
        elif s['mode'] == 'town':
            self.town_step(p, s)
        if s['mode'] == 'maze' and (s['area'], s['x'], s['y'], s['face']) != (p['area'], p['x'], p['y'], p['face']):
            if s['area'] != p['area']:
                self.log('floor', dict(frm=p['area'], to=s['area'], where=where(s)))
                if self.trip is not None and s['area'] not in self.trip['floors']:
                    self.trip['floors'].append(s['area'])
            self.log('pos', where(s))
        if s['mode'] == 'maze' and p['mode'] == 'maze':
            self.loose_changes(p, s)
        self.snap_line(s, force=s['mode'] != p['mode'])
        self.prev = s

    def loose_changes(self, p, s):
        """Status and level changes outside a fight, a camp or town (a trap, a poison
        tick, an event)."""
        for i in party_of(s):
            for d in diff_members(p, s, [i]):
                if 'status' in d:
                    dead = s['roster'][i]['st'] & DEAD and not p['roster'][i]['st'] & DEAD
                    self.log('death' if dead else 'status', dict(where=where(s), **d))
                    if dead and self.trip is not None:
                        self.trip['deaths'].append([d['name'], where(s)])
                elif 'level' in d:
                    self.log('level', dict(where=where(s), **d))

    def change_mode(self, p, s):
        a, b = p['mode'], s['mode']
        if a == 'battle':
            self.close_fight(p, s)
        if a == 'camp' and self.camp:
            self.close_camp(s)
        if a == 'town':
            self.close_visit(s)
            self.log('set out', dict(where=where(s), party=brief(s)))
            self.trip = dict(s=s, fights=0, rounds=0, fled=0, floors=[s['area']], deaths=[], chests=[])
        if b == 'town' and a != 'town':
            self.log('home', dict(frm=where(p), via=a, party=brief(s)))
            self.trip_summary(s)
            self.open_visit(s)
        if b == 'battle':
            self.open_fight(p, s)
        if b == 'camp':
            self.camp = (s if a != 'maze' else p, [])
        self.mode = b
        self.msgs_since = []

    def trip_summary(self, s):
        """From setting out to now: fights, rounds, deaths, chests, floors, and per member
        experience, gold and levels gained."""
        t, self.trip = self.trip, None
        if not t:
            return
        s0 = t['s']
        per = []
        for i in party_of(s0):
            a, b = s0['roster'].get(i), s['roster'].get(i)
            if a and b:
                per.append(dict(name=b['name'], exp=b['exp'] - a['exp'], gold=b['gold'] - a['gold'],
                                level=[a['lv'], b['lv']], hp=[b['hp'], b['mhp']], st=status_name(b['st'])))
        self.log('trip', dict(frames=s['f'] - s0['f'], fights=t['fights'], rounds=t['rounds'],
                              fled=t['fled'], deaths=t['deaths'], chests=t['chests'],
                              floors=t['floors'], members=per))

    # -- fights --
    def open_fight(self, p, s):
        self.snapper.names = {}
        self.fight = dict(f0=s['f'], where=[p['area'], p['x'], p['y'], p['face']], before=p,
                          rounds=0, groups=None, msgs=[], last=s, fixed=s['fixed'])
        self.battle_step(s, s)

    def battle_step(self, p, s):
        F = self.fight
        if F is None:
            return
        F['last'] = s
        if s.get('groups') and F['groups'] is None:
            # the groups are set up a moment after the overlay loads: read the names once
            s2 = self.snapper.snap(battle_names=True)
            if s2 and s2.get('groups'):
                s = s2
                F['last'] = s
            F['groups'] = [dict(id=q['id'], name=self.snapper.names.get(q['k'], (0, '?', 0))[1],
                                level=self.snapper.names.get(q['k'], (0, '?', 0))[2], n=q['n'],
                                ident=q['ident']) for q in s['groups']]
            self.log('battle', dict(where=F['where'], fixed=s['fixed'], groups=F['groups'],
                                    hp=[[c['name'], c['hp'], c['mhp']] for c in brief(F['before'])],
                                    sp={c['name']: c['sp'] for c in brief(F['before']) if c['sp']}))
        if s['phase'] == CMD_PHASE and (p is s or p['phase'] != CMD_PHASE):
            F['rounds'] += 1
        if s['phase'] == CHEST_PHASE and self.chest is None:
            self.chest = dict(f0=s['f'], k0=len(F['msgs']))

    def close_fight(self, p, s):
        F, self.fight = self.fight, None
        if F is None:
            return
        last = F['last']
        before = F['before']
        who = party_of(before)
        M = F['msgs']
        casts, uses, fled, gold, exp = [], [], [0, 0], 0, 0
        for m in M:
            t = ' '.join(m['text'].split())
            if m['file'] == 'FIGHTMSG.OBJ' and m['idx'] == 205:
                fled[0] += 1
            elif m['file'] == 'FIGHTMSG.OBJ' and m['idx'] == 206:
                fled[1] += 1
            c = CAST_RE.match(t)
            if c:
                casts.append([c.group(1), c.group(2)])
            u = USE_RE.match(t)
            if u:
                uses.append([u.group(1), u.group(2)])
            gm = GAIN_RE.search(t)
            if gm:
                if gm.group(2) == 'gold':
                    gold += int(gm.group(1))
                else:
                    exp += int(gm.group(1))
        mine = {before['roster'][i]['name'] for i in who if i in before['roster']}
        changes = diff_members(before, s, who)
        end = [s['roster'][i] for i in who if i in s['roster']]
        groups_end = [dict(id=q['id'], n=q['n'], up=q['up']) for q in last.get('groups', [])]
        if s['mode'] == 'town':
            outcome = 'town'          # a wipe, or the party carried home
        elif fled[0] and not exp:
            outcome = 'fled'          # the groups read empty after a run too
        elif all(q['up'] == 0 for q in last.get('groups', [])) and last.get('groups'):
            outcome = 'won'
        else:
            outcome = 'ended'
        rec = dict(rounds=F['rounds'], frames=s['f'] - F['f0'], where=F['where'], fixed=F['fixed'],
                   outcome=outcome, groups=F['groups'], groups_end=groups_end,
                   casts=[c for c in casts if c[0] in mine], monster_casts=[c for c in casts if c[0] not in mine],
                   items=[u for u in uses if u[0] in mine],
                   spent={d['name']: d['spent'] for d in changes if 'spent' in d},
                   hp_start=[[c['name'], c['hp'], c['mhp']] for c in brief(before)],
                   hp_end=[[c['name'], c['hp'], c['mhp']] for c in end],
                   down_end=[c['name'] for c in end if c['st'] >= 0x20],
                   dead_end=[c['name'] for c in end if c['st'] & DEAD],
                   status_end=[[c['name'], status_name(c['st'])] for c in end if c['st']],
                   fled=fled, gold=gold, exp=exp,
                   items_new={d['name']: d['items_new'] for d in changes if 'items_new' in d},
                   items_gone={d['name']: d['items_gone'] for d in changes if 'items_gone' in d},
                   levels={d['name']: d['level'] for d in changes if 'level' in d})
        died = []
        for c in end:
            b = before['roster'].get(c['ri'])
            if b and c['st'] & DEAD and not b['st'] & DEAD:
                died.append(c['name'])
                self.log('death', dict(who=c['name'], where=F['where'], status=status_name(c['st']),
                                       groups=[q['name'] for q in F['groups'] or []]))
        cm = [m for m in M[self.chest['k0']:]] if self.chest is not None else []
        if not any(m['file'] == 'FIGHTMSG.OBJ' and 239 <= (m['idx'] or 0) <= 251 for m in cm):
            self.chest = None           # the chest phase only showed the loot message
        if self.chest is not None:
            texts = shown(cm)
            idx = [m['idx'] for m in cm if m['file'] == 'FIGHTMSG.OBJ']
            if 242 in idx:
                how = 'sprung'
            elif 241 in idx:
                how = 'disarmed'
            elif 240 in idx:
                how = 'no trap'
            elif 239 in idx:
                how = 'disarm failed'
            elif any(i in (261,) for i in idx):
                how = 'opened'
            else:
                how = 'left'
            ch = dict(where=F['where'], how=how, inspects=idx.count(246), disarm_tries=idx.count(249),
                      opens=idx.count(250), calfo=idx.count(247), messages=texts,
                      items=rec['items_new'])
            rec['chest'] = ch
            self.log('chest', ch)
            self.chest = None
        self.log('fought', rec)
        t = self.trip
        if t is not None:
            t['fights'] += 1
            t['rounds'] += rec['rounds']
            t['fled'] += rec['outcome'] == 'fled'
            t['deaths'] += [[c, F['where']] for c in died]
            if rec.get('chest'):
                t['chests'].append([F['where'], rec['chest']['how']])

    # -- camp --
    def close_camp(self, s):
        c0, msgs = self.camp
        self.camp = None
        ch = diff_members(c0, s, sorted(set(party_of(c0)) | set(party_of(s))))
        self.log('camp', dict(where=where(s), frames=s['f'] - c0['f'], changes=ch,
                              spent={d['name']: d['spent'] for d in ch if 'spent' in d},
                              messages=shown(msgs)[:40],
                              order=[s['roster'][i]['name'] for i in party_of(s) if i in s['roster']]
                              if party_of(s) != party_of(c0) else None))

    # -- town --
    def open_visit(self, s):
        self.visit = dict(s=s, fac=FACILITY.get(s['town']), msgs=[])

    def town_step(self, p, s):
        # town states other than the bar and the facilities (1-4: a refusal, transitions)
        # leave the visit open
        if s['town'] in FACILITY and FACILITY[s['town']] != (self.visit or {}).get('fac', 0):
            self.close_visit(s)
            self.open_visit(s)

    def close_visit(self, s):
        v, self.visit = self.visit, None
        if not v:
            return
        s0 = v['s']
        ch = diff_members(s0, s)
        msgs = shown(v['msgs'])
        if v['fac'] is None and not ch:
            return
        party0 = [s0['roster'][i]['name'] for i in party_of(s0) if i in s0['roster']]
        party1 = [s['roster'][i]['name'] for i in party_of(s) if i in s['roster']]
        gold0 = sum(c['gold'] for c in s0['roster'].values())
        gold1 = sum(c['gold'] for c in s['roster'].values())
        self.log('town', dict(place=v['fac'] or 'castle', frames=s['f'] - s0['f'], gold=gold1 - gold0,
                              changes=ch, party=party1 if party1 != party0 else None,
                              messages=msgs[:60]))

    # -- the loop --
    def run(self):
        print('humanwatch: logging to %s (port %d); Ctrl-C stops' % (self.path, self.a.port), flush=True)
        waiting, k, every = False, 0, self.a.every
        while True:
            if k % 50 == 0:
                st = self.ra.status()
                if st not in ('PLAYING', 'PAUSED'):
                    if not waiting:
                        print('   waiting for RetroArch and the game...', flush=True)
                        waiting = True
                    time.sleep(1)
                    continue
                waiting = False
            k += 1
            self.check_text()
            if k % every == 0:
                s = self.snapper.snap()
                if s is not None and s['ovl'] != '?':
                    self.update(s)
            if self.a.sleep:
                time.sleep(self.a.sleep)


def find_bin():
    for d in (os.path.join(ROOT, '..'), os.path.join(ROOT, '..', '..')):
        p = os.path.join(d, 'Wizardry - Dimguil (English WIP).bin')
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--session', default=time.strftime('%Y%m%d-%H%M%S'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'rips/humanplay'))
    ap.add_argument('--port', type=int, default=55355)
    ap.add_argument('--bin', default=find_bin())
    ap.add_argument('--chunk', type=int, default=8192, help='bytes per READ_CORE_MEMORY at first')
    ap.add_argument('--every', type=int, default=2, help='a full look every N text checks')
    ap.add_argument('--sleep', type=float, default=0.0)
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if not a.bin:
        sys.exit('no disc image: give --bin')
    w = Watch(a)
    signal.signal(signal.SIGTERM, signal.default_int_handler)   # stop the same way as Ctrl-C
    try:
        w.run()
    except KeyboardInterrupt:
        if w.prev is not None and w.trip is not None:
            w.trip_summary(w.prev)
        if w.prev is not None:
            w.log('stop', dict(mode=w.prev['mode'], where=where(w.prev), open_fight=w.fight is not None,
                               party=brief(w.prev)))
        print('stopped; log %s' % w.path)


if __name__ == '__main__':
    main()
