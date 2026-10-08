#!/usr/bin/env python3
"""Run beside RetroArch during the recorded play-through: save states, memory-card
backups, and a monitor that pauses the game before an unreviewed line is shown.

    playwatch.py [--interval SECONDS] [--no-pause] [--no-record] [--playdir DIR] [--bin IMAGE]
    playwatch.py --selftest STATE...     check the matching on emulator states (emu.py)

It starts RetroArch's recording as the ASCII logo starts to fade in, when the game sets
up its own screen mode (recording from launch fails at the BIOS screen), unless a
recording is already going or --no-record.

It talks to RetroArch over its network commands (network_cmd_enable, UDP 55355; see
../playthrough/retroarch-dimguil.cfg). Everything goes in the play folder:

  states/auto/   a save state every --interval seconds (default 180) while the game is
                 running and not paused, named by wall-clock time. Each is taken in a
                 fresh slot (STATE_SLOT_PLUS, then SAVE_STATE) and moved out of the way,
                 so RetroArch never overwrites a state file: overwriting reads the old
                 one into its undo buffer and can drop a frame.
  archive/srm/   a copy of the memory card each time it changes.
  archive/builds/  the text and code files of each image played, so a later build can
                 be compared with it (redo.py) and old text recognised (see below).
  logs/          one JSON line per event: every string the game shows, with its file,
                 index and review status (textstatus.py), each save state, each pause,
                 each new recording file.

The monitor reads the game's text buffer (0x8008b400). Dialogue, event, castle and
battle strings are expanded whole into it just before they print, so the monitor sees a
string before its first page is drawn. It identifies the string against the image being
played (read from the disc image itself, so it always matches what's on screen) and, if
textstatus.py says it's open or to be checked, pauses RetroArch and says why. Unpause
to carry on. Text it can't match is logged; if it has Japanese in it, that pauses too,
and so does text from an earlier build that this one has changed (after a redo, a line
the state already had in memory).

After a fix, redo.py restarts the game from a save state on the new build; it runs this
with --from-state.
"""
import argparse, hashlib, json, os, re, shutil, signal, socket, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import textstatus

BUF, BUF_LEN, HEAD = 0x8b400, 576, 64     # text buffer (physical address)
STAGE = 0x1a0400                          # where EVENTMES / NPC_MESn are loaded
FRAME = 0x60788                           # frame counter, for lining up with the video
SCREEN = 0x793ec                          # the game's 320x240 screen setup (two u16s),
                                          # written as the ASCII logo starts to fade in;
                                          # 0xff filler before that
CODE_AT = 0x10000                         # where the executable's code is loaded
FILES = ['DATA06/EVENTMES.BIN'] + [f'DATA06/NPC_MES{n}.OBJ' for n in range(1, 6)] + \
        ['DATA06/SISETU.OBJ', 'DATA01/FIGHTMSG.OBJ', 'DATA01/STATUS.OBJ']
STAGED = 6                                # the first six share the staging area
EXE = 'SLPS_026.91'
CODE = [EXE] + [f'{n}.BIN' for n in ('BATTLE', 'CMAIN', 'CMENU', 'HAZURE', 'JOUKA', 'MAZE', 'MCARD')]


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


def archive_build(image, play):
    """Copy the image's text and code files to archive/builds/<key>/, once; return the key
    (a hash of the files, so two builds from the same commit still differ)."""
    data = iso_files(image, FILES + CODE)
    h = hashlib.md5()
    for p in sorted(data):
        h.update(p.encode() + data[p])
    key = h.hexdigest()[:12]
    d = os.path.join(play, 'archive/builds', key)
    if not os.path.isdir(d):
        for p, b in data.items():
            os.makedirs(os.path.dirname(os.path.join(d + '.tmp', p)), exist_ok=True)
            open(os.path.join(d + '.tmp', p), 'wb').write(b)
        ver = re.sub(r'\.bin$', '.version.txt', image)
        if os.path.exists(ver):
            shutil.copy(ver, os.path.join(d + '.tmp', 'version.txt'))
        os.rename(d + '.tmp', d)
    return key


def build_files(play, key):
    d = os.path.join(play, 'archive/builds', key)
    return {p: open(os.path.join(d, p), 'rb').read() for p in FILES + CODE}


class Text:
    """Every string of the tracked files in one image, and how to recognise them."""

    def __init__(self, data):
        """data: {path: bytes} for FILES, from iso_files() or build_files()."""
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
        self.pidfile = os.path.join(self.play, 'logs', 'playwatch.pid')
        open(self.pidfile, 'w').write(str(os.getpid()))
        self.build = archive_build(a.bin, self.play)
        self.text = Text(build_files(self.play, self.build))
        self.old = []                       # earlier builds, to catch text a state kept
        for e in sorted(os.scandir(os.path.join(self.play, 'archive/builds')),
                        key=lambda e: e.stat().st_mtime, reverse=True):
            if e.is_dir() and e.name != self.build and not e.name.endswith('.tmp'):
                self.old.append((e.name, Text(build_files(self.play, e.name))))
        self.recdir = os.path.join(self.play, 'recordings')
        self.recordings = set(os.listdir(self.recdir)) if os.path.isdir(self.recdir) else set()
        self.record_pending = False if a.no_record else 'check'
        self.screen_armed = False   # seen the game's code loaded, its screen not yet set
        self.exe_sig = build_files(self.play, self.build)[EXE][0x800:0x820]
        self.status_of = textstatus.table()
        self.last_head = None
        self.last_id = None
        self.first = True           # what's in the buffer at the start was already shown
        self.staged = None          # what the staging area holds, as staged_name() says
        self.next_state = time.time() + a.interval
        self.next_srm = 0
        self.srm_hash = None
        ver = open(re.sub(r'\.bin$', '.version.txt', a.bin)).read().strip() \
            if os.path.exists(re.sub(r'\.bin$', '.version.txt', a.bin)) else '?'
        self.log('start', image=os.path.basename(a.bin), version=ver, build=self.build,
                 interval=a.interval, pause=not a.no_pause, from_state=a.from_state)
        print(f'playwatch: {os.path.basename(a.bin)} ({ver}); states every {a.interval}s; '
              f'log {self.log_f.name}')

    def log(self, kind, **kw):
        kw = {'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'kind': kind, **kw}
        self.log_f.write(json.dumps(kw, ensure_ascii=False) + '\n')
        self.log_f.flush()

    def frame(self):
        d = self.ra.read(FRAME, 4)
        return int.from_bytes(d, 'little') if d else None

    def staged_name(self, head):
        if head is None:
            return None
        return next((f for f, h in self.text.heads.items() if h == head), 'other')

    def check_stage(self):
        """Log each load into the staging area: meeting a party puts its portrait there
        for about a second ('other'), then its text; an event loads EVENTMES. redo.py uses
        these to tell whether a state was taken mid-conversation."""
        name = self.staged_name(self.ra.read(STAGE, 16))
        if name and name != self.staged:
            self.staged = name
            self.log('load', file=name, frame=self.frame())

    def check_text(self):
        head = self.ra.read(BUF, HEAD)
        if head is None or head == self.last_head:
            self.first = self.first and head is None
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
            for key, old in self.old:
                hit = old.identify(buf, staged)
                if hit:
                    f, i = hit
                    st, why = 'stale', f'text from an earlier build ({key}) that this one changed'
                    break
        self.last_id = f'{f}:{i}' if hit else None
        pause = (st in textstatus.PAUSE or st in ('japanese', 'stale')) and not self.first
        self.log('text', file=f, index=i, status=st, staged=self.staged_name(staged),
                 frame=self.frame(), text=shown,
                 paused=pause and not self.a.no_pause, **({'already_shown': True} if self.first else {}))
        self.first = False
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
        self.log('state', file=name, frame=frame, after=self.last_id, staged=self.staged)
        print(f'{time.strftime("%H:%M:%S")} save state {name} (after {self.last_id})')
        return True

    def recording_now(self):
        """Whether a recording file is growing (the game is running when this is asked)."""
        def sizes():
            return {e.name: e.stat().st_size for e in os.scandir(self.recdir) if e.name.endswith('.mkv')}
        a = sizes()
        time.sleep(1)
        b = sizes()
        return any(b[n] != a.get(n) for n in b)

    def start_recording(self):
        """Once, as the ASCII logo starts (or at once if the game is well past it)."""
        os.makedirs(self.recdir, exist_ok=True)
        if self.record_pending == 'check':  # first time the game runs: recording already?
            if self.recording_now():
                self.record_pending = False
                self.log('recording-already')
                print('   a recording is already going; leaving it alone')
                return
            self.record_pending = True
            print('   recording will start at the ASCII logo')
        d = self.ra.read(SCREEN, 4)
        fc = self.frame()
        if not d or fc is None or self.ra.read(CODE_AT, len(self.exe_sig)) != self.exe_sig:
            return                          # still in the BIOS
        if struct.unpack('<HH', d) != (320, 240):
            self.screen_armed = True        # black, before the logo
            return
        if not self.screen_armed and not 3000 < fc < 0xaaaaaaaa:
            return                          # can't tell yet whether the logo just started
        self.record_pending = False
        before = set(os.listdir(self.recdir))
        self.ra.send('RECORDING_TOGGLE')
        for _ in range(20):
            time.sleep(0.25)
            if set(os.listdir(self.recdir)) - before:
                self.ra.send('SHOW_MSG playwatch: recording')
                print(f'{time.strftime("%H:%M:%S")} started recording at the ASCII logo'
                      if self.screen_armed else
                      f'{time.strftime("%H:%M:%S")} started recording (the game was past the logo)')
                return
        self.log('recording-failed')
        msg = 'Recording did not start: use Quick Menu > Start Recording'
        self.ra.send(f'SHOW_MSG playwatch: {msg}')
        print(f'   {msg}')
        notify('Dimguil playwatch', msg)

    def check_recordings(self):
        if not os.path.isdir(self.recdir):
            return
        for name in sorted(set(os.listdir(self.recdir)) - self.recordings):
            self.recordings.add(name)
            self.log('recording', file=name, frame=self.frame())
            print(f'{time.strftime("%H:%M:%S")} recording {name}')

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
            if self.record_pending and st == 'PLAYING':
                self.start_recording()
            self.check_stage()
            self.check_text()
            self.check_recordings()
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
    text = Text(iso_files(image, FILES))
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
    ap.add_argument('--no-record', action='store_true', help="don't start RetroArch's recording")
    ap.add_argument('--playdir', default=os.path.join(ROOT, '../playthrough'))
    ap.add_argument('--bin', default=os.path.join(ROOT, '../Wizardry - Dimguil (English WIP).bin'))
    ap.add_argument('--selftest', nargs='+', metavar='STATE')
    ap.add_argument('--from-state', help='set by redo.py: the state this session starts from')
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.selftest)
    s = Session(a)
    signal.signal(signal.SIGTERM, signal.default_int_handler)   # stop the same way as Ctrl-C
    try:
        s.run()
    except KeyboardInterrupt:
        print('stopped')
    finally:
        os.remove(s.pidfile)


if __name__ == '__main__':
    main()
