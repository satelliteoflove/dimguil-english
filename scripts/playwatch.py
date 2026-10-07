#!/usr/bin/env python3
"""Run beside RetroArch during the recorded play-through: save states, memory-card
backups, and a monitor that pauses the game before an unreviewed line is shown.

    playwatch.py [--interval SECONDS] [--no-pause] [--playdir DIR] [--bin IMAGE]
    playwatch.py --selftest STATE...     check the matching on emulator states (emu.py)

It talks to RetroArch over its network commands (network_cmd_enable, UDP 55355; see
../playthrough/retroarch-dimguil.cfg). Everything goes in the play folder:

  states/auto/   a save state every --interval seconds (default 180) while the game is
                 running and not paused, named by wall-clock time. Each is taken in a
                 fresh slot (STATE_SLOT_PLUS, then SAVE_STATE) and moved out of the way,
                 so RetroArch never overwrites a state file: overwriting reads the old
                 one into its undo buffer and can drop a frame.
  archive/srm/   a copy of the memory card each time it changes.
  logs/          one JSON line per event: every string the game shows, with its file,
                 index and review status (textstatus.py), each save state, each pause.

The monitor reads the game's text buffer (0x8008b400). Dialogue, event, castle and
battle strings are expanded whole into it just before they print, so the monitor sees a
string before its first page is drawn. It identifies the string against the image being
played (read from the disc image itself, so it always matches what's on screen) and, if
textstatus.py says it's open or to be checked, pauses RetroArch and says why. Unpause
to carry on. Text it can't match is logged; if it has Japanese in it, that pauses too.
"""
import argparse, hashlib, json, os, re, shutil, socket, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import textstatus

BUF, BUF_LEN, HEAD = 0x8b400, 576, 64     # text buffer (physical address)
STAGE = 0x1a0400                          # where EVENTMES / NPC_MESn are loaded
FRAME = 0x60788                           # frame counter, for lining up with the video
FILES = ['DATA06/EVENTMES.BIN'] + [f'DATA06/NPC_MES{n}.OBJ' for n in range(1, 6)] + \
        ['DATA06/SISETU.OBJ', 'DATA01/FIGHTMSG.OBJ', 'DATA01/STATUS.OBJ']
STAGED = 6                                # the first six share the staging area


# --- the disc image ---

def iso_files(image, paths):
    """{path: bytes} read through the ISO 9660 directory of a raw 2352-byte image."""
    f = open(image, 'rb')

    def sector(lba):
        f.seek(lba * 2352 + 24)            # mode 2 form 1: sync, header, subheader
        return f.read(2048)

    def extent(lba, size):
        return b''.join(sector(lba + i) for i in range((size + 2047) // 2048))[:size]

    def listing(lba, size):
        d, out, i = extent(lba, size), {}, 0
        while i < len(d):
            n = d[i]
            if n == 0:                     # records don't cross sectors
                i = (i // 2048 + 1) * 2048
                continue
            nl = d[i + 32]
            name = d[i + 33:i + 33 + nl].decode('ascii', 'replace').split(';')[0]
            out[name] = (struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0])
            i += n
        return out

    pvd = sector(16)
    root = (struct.unpack_from('<I', pvd, 156 + 2)[0], struct.unpack_from('<I', pvd, 156 + 10)[0])
    out = {}
    for p in paths:
        lba, size = root
        for part in p.split('/'):
            lba, size = listing(lba, size)[part]
        out[p] = extent(lba, size)
    return out


def strings(d):
    first = struct.unpack_from('<I', d, 0)[0]
    offs = [struct.unpack_from('<I', d, 4 * i)[0] for i in range(first // 4)] + [len(d)]
    return [d[offs[i]:offs[i + 1]] for i in range(first // 4)]


def segments(s):
    """The literal runs of a string, split at control codes (names, page breaks)."""
    s = s.split(b'\xff\x40')[0]
    out, cur, i = [], bytearray(), 0
    while i < len(s):
        if s[i] == 0xff and i + 1 < len(s):
            if cur:
                out.append(bytes(cur))
                cur = bytearray()
            i += 2
        else:
            cur.append(s[i])
            i += 1
    if cur:
        out.append(bytes(cur))
    return out


class Text:
    """Every string of the tracked files in one image, and how to recognise them."""

    def __init__(self, image):
        data = iso_files(image, FILES)
        self.heads = {}
        self.table = {}
        for p in FILES:
            f = os.path.basename(p)
            self.heads[f] = data[p][:16]
            self.table[f] = [(i, segments(s), sum(map(len, segments(s))))
                             for i, s in enumerate(strings(data[p]))]
        self.decode = decoder()

    def identify(self, buf, staged_head):
        """(file, index) for the expanded string in buf, or None. The file loaded in the
        staging area is tried first, so a line shared between NPC files is credited to
        the one being played."""
        order = [f for f in self.table if self.heads[f] == staged_head]
        order += [os.path.basename(p) for p in FILES[STAGED:]]
        for f in order:
            best = None
            for i, segs, n in self.table[f]:
                if n and (best is None or n > best[0]) and n >= 0.5 * len(buf) and in_order(segs, buf):
                    best = (n, i)
            if best:
                return f, best[1]
        return None


def in_order(segs, buf):
    p = 0
    for s in segs:
        j = buf.find(s, p)
        if j < 0:
            return False
        p = j + len(s)
    return True


def decoder():
    t = {}
    for line in open(os.path.join(ROOT, 'tables/dimguil_enc.tbl'), encoding='utf-8'):
        a, sep, b = line.rstrip('\n').partition('=')
        if sep:
            try:
                t.setdefault(int(a, 16), b)
            except ValueError:
                pass
    for line in open(os.path.join(ROOT, 'tables/compression.tbl'), encoding='utf-8'):
        line = line.rstrip('\n')
        if len(line) >= 4 and line[2] == '=':
            t[int(line[3:], 16)] = line[:2]

    def dec(d):
        out, i = [], 0
        while i < len(d):
            b = d[i]
            if b == 0xff and i + 1 < len(d):
                out.append('\n' if d[i + 1] == 0x21 else '{ff%02x}' % d[i + 1])
                i += 2
            elif b >= 0xf7 and i + 1 < len(d):
                out.append('<%02x%02x>' % (b, d[i + 1]))
                i += 2
            else:
                out.append(t.get(b, '<%02x>' % b))
                i += 1
        return ''.join(out)
    return dec


def japanese(buf):
    i = 0
    while i < len(buf):
        if buf[i] == 0xff:
            i += 2
            continue
        if buf[i] >= 0xd8:
            return True
        i += 1
    return False


# --- RetroArch ---

class RetroArch:
    def __init__(self, port=55355):
        self.addr = ('127.0.0.1', port)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(0.5)

    def send(self, cmd):
        self.s.sendto(cmd.encode(), self.addr)

    def ask(self, cmd):
        while True:                         # drop stale replies
            self.s.setblocking(False)
            try:
                self.s.recv(65536)
            except (BlockingIOError, OSError):
                break
        self.s.settimeout(0.5)
        self.send(cmd)
        try:
            return self.s.recv(65536).decode('ascii', 'replace').strip()
        except (socket.timeout, ConnectionRefusedError):
            return None

    def read(self, addr, n):
        out = b''
        while len(out) < n:
            k = min(256, n - len(out))
            r = self.ask(f'READ_CORE_MEMORY {addr + len(out):x} {k}')
            if not r or ' -1' in r.split(maxsplit=2)[-1][:3]:
                return None
            out += bytes(int(x, 16) for x in r.split()[2:])
        return out

    def status(self):
        r = self.ask('GET_STATUS')        # GET_STATUS PLAYING|PAUSED|CONTENTLESS ...
        return r.split()[1] if r and len(r.split()) > 1 else None


def notify(title, body):
    """A desktop notification, through notify-send or straight over D-Bus."""
    for cmd in (['notify-send', '-u', 'critical', title, body],
                ['gdbus', 'call', '--session', '--dest', 'org.freedesktop.Notifications',
                 '--object-path', '/org/freedesktop/Notifications',
                 '--method', 'org.freedesktop.Notifications.Notify', 'playwatch', '0', '',
                 title, body, '[]', '{"urgency": <byte 2>}', '0']):
        try:
            if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                return
        except FileNotFoundError:
            pass


# --- the session ---

class Session:
    def __init__(self, a):
        self.a = a
        self.ra = RetroArch()
        self.play = os.path.abspath(a.playdir)
        self.stamp = time.strftime('%Y%m%d-%H%M%S')
        for d in ('states/auto', 'archive/srm', 'logs'):
            os.makedirs(os.path.join(self.play, d), exist_ok=True)
        self.log_f = open(os.path.join(self.play, 'logs', self.stamp + '.jsonl'), 'a')
        self.text = Text(a.bin)
        self.status_of = textstatus.table()
        self.last_head = None
        self.last_id = None
        self.next_state = time.time() + a.interval
        self.next_srm = 0
        self.srm_hash = None
        ver = open(re.sub(r'\.bin$', '.version.txt', a.bin)).read().strip() \
            if os.path.exists(re.sub(r'\.bin$', '.version.txt', a.bin)) else '?'
        self.log('start', image=os.path.basename(a.bin), version=ver, interval=a.interval,
                 pause=not a.no_pause)
        print(f'playwatch: {os.path.basename(a.bin)} ({ver}); states every {a.interval}s; '
              f'log {self.log_f.name}')

    def log(self, kind, **kw):
        kw = {'t': time.strftime('%H:%M:%S'), 'kind': kind, **kw}
        self.log_f.write(json.dumps(kw, ensure_ascii=False) + '\n')
        self.log_f.flush()

    def frame(self):
        d = self.ra.read(FRAME, 4)
        return int.from_bytes(d, 'little') if d else None

    def check_text(self):
        head = self.ra.read(BUF, HEAD)
        if head is None or head == self.last_head:
            return
        self.last_head = head
        buf = self.ra.read(BUF, BUF_LEN) or head
        end = buf.find(b'\xff\x40')
        if end <= 0:        # every expanded string ends with {ff40}; before the game
            return          # first uses the buffer it holds leftover data
        buf = buf[:end]
        staged = self.ra.read(STAGE, 16)
        hit = self.text.identify(buf, staged)
        shown = self.text.decode(buf)
        if hit:
            f, i = hit
            st, why = self.status_of(f, i)
        else:
            f = i = None
            st, why = ('japanese', 'unmatched text with Japanese in it') if japanese(buf) \
                else ('unmatched', 'not one of the tracked strings')
        self.last_id = f'{f}:{i}' if hit else None
        pause = st in textstatus.PAUSE or st == 'japanese'
        self.log('text', file=f, index=i, status=st, frame=self.frame(), text=shown,
                 paused=pause and not self.a.no_pause)
        tag = f'{f}:{i}' if hit else '?'
        print(f'{time.strftime("%H:%M:%S")} {tag:18} {st:11} {shown[:70]!r}')
        if pause:
            self.stop(f'{tag} {st}: {why}', shown)

    def stop(self, reason, shown):
        if not self.a.no_pause and self.ra.status() == 'PLAYING':
            self.ra.send('PAUSE_TOGGLE')
        self.ra.send(f'SHOW_MSG playwatch: {reason}')
        print(f'   PAUSED: {reason}\n   {shown!r}')
        notify('Dimguil playwatch', f'{reason}\n\n{shown}')

    def save_state(self):
        if self.ra.status() != 'PLAYING':
            return False
        states = os.path.join(self.play, 'states')
        before = {e.name: e.stat().st_mtime for e in os.scandir(states) if e.is_file()}
        t0 = time.time()
        self.ra.send('STATE_SLOT_PLUS')
        time.sleep(0.05)
        self.ra.send('SAVE_STATE')
        frame = self.frame()
        new = None
        while time.time() - t0 < 10 and not new:      # the state is written on a task thread
            time.sleep(0.25)
            for e in os.scandir(states):
                if e.is_file() and '.state' in e.name and e.stat().st_mtime > before.get(e.name, 0):
                    new = e.path
        if not new:
            self.log('state-missing')
            print('   save state: no new file appeared')
            return True
        size = -1
        while size != os.path.getsize(new):          # wait until it stops growing
            size = os.path.getsize(new)
            time.sleep(0.3)
        name = f'{time.strftime("%Y%m%d-%H%M%S")}.state'
        shutil.move(new, os.path.join(states, 'auto', name))
        self.log('state', file=name, frame=frame, after=self.last_id)
        print(f'{time.strftime("%H:%M:%S")} save state {name} (after {self.last_id})')
        return True

    def backup_srm(self):
        for e in os.scandir(os.path.join(self.play, 'saves')):
            if e.name.endswith('.srm'):
                h = hashlib.md5(open(e.path, 'rb').read()).hexdigest()
                if h != self.srm_hash:
                    self.srm_hash = h
                    name = f'{time.strftime("%Y%m%d-%H%M%S")}.srm'
                    shutil.copy2(e.path, os.path.join(self.play, 'archive/srm', name))
                    self.log('srm', file=name, md5=h)

    def run(self):
        waiting = False
        while True:
            st = self.ra.status()
            if st not in ('PLAYING', 'PAUSED'):
                if not waiting:
                    print('   waiting for RetroArch and the game...')
                    waiting = True
                time.sleep(1)
                continue
            waiting = False
            self.check_text()
            now = time.time()
            if now >= self.next_state and self.save_state():
                self.next_state = now + self.a.interval
            if now >= self.next_srm:
                self.backup_srm()
                self.next_srm = now + 30
            time.sleep(0.1)


def selftest(states):
    """Identify the text buffer in emulator states, as the monitor would."""
    import emu
    image = os.path.join(ROOT, 'rips/iso/dimguil-en.bin')
    text = Text(image)
    status = textstatus.table()
    e = emu.Emu(os.path.join(ROOT, 'rips/iso/dimguil-en.cue'))
    for path in states:
        e.load(path)
        e.run(2)
        buf = e.read(0x80000000 | BUF, BUF_LEN)
        buf = buf[:buf.find(b'\xff\x40')] if b'\xff\x40' in buf else buf
        hit = text.identify(buf, e.read(0x80000000 | STAGE, 16))
        st = status(*hit) if hit else ('unmatched', '')
        print(f'{os.path.basename(path):24} {hit} {st[0]:11} {text.decode(buf)[:60]!r}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--interval', type=int, default=180)
    ap.add_argument('--no-pause', action='store_true', help='log only, never pause')
    ap.add_argument('--playdir', default=os.path.join(ROOT, '../playthrough'))
    ap.add_argument('--bin', default=os.path.join(ROOT, '../Wizardry - Dimguil (English WIP).bin'))
    ap.add_argument('--selftest', nargs='+', metavar='STATE')
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.selftest)
    try:
        Session(a).run()
    except KeyboardInterrupt:
        print('stopped')


if __name__ == '__main__':
    main()
