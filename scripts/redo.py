#!/usr/bin/env python3
"""Replay a stretch of the play-through on a new build, after the monitor stopped on a
line and the line was fixed.

    redo.py [--dry-run] [--state NAME] [--force] [--playdir DIR] [--bin IMAGE]

Quit RetroArch and playwatch first, rebuild, check the log and publish (publish_test.sh).
Then this:

  1. compares the published build with the one the last session played, and lists the
     strings the fix changed;
  2. picks the newest automatic state taken before the stop and not in the middle of a
     conversation or event (whose text the game wouldn't load again, so the replay would
     show the old wording), and without old castle, battle or status text in memory;
     or the one named with --state;
  3. moves the states taken after it to states/abandoned/, since that stretch is being
     replayed;
  4. starts RetroArch on the new build, paused, loads the state, writes the new build's
     file tables into RAM so the game finds the new files on the disc, and starts
     recording;
  5. writes logs/<time>-redo.json for splice.py, and runs playwatch.py.

Unpause and play. Afterwards, splice.py finds where the redo recording joins the old
one. --dry-run does steps 1 and 2 and says what the rest would do.

A save state holds the code that was loaded when it was made, so if the fix changed code
(the executable outside its file tables, or an overlay), this stops unless --force.
"""
import argparse, glob, json, os, shutil, struct, subprocess, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import playwatch as pw

TABLES = (0x80051760, 0x80052700)          # the executable's file tables (MSF and size)
EXE_BASE = 0x80010000 - 0x800              # file offset 0x800 is loaded at 0x80010000
CORE = os.path.expanduser('~/.config/retroarch/cores/mednafen_psx_hw_libretro.so')
REDO_CFG = '''# Written by redo.py, loaded after retroarch-dimguil.cfg for a redo: the state to
# replay from is put in slot 0.
state_slot = "0"
savestate_auto_load = "false"
'''


# --- save states ---

def state_ram(path):
    """Main RAM (2 MB) from a RetroArch state of the Beetle PSX core."""
    d = open(path, 'rb').read()
    if d[:8] == b'#RZIPv\x01#':           # savestate_file_compression
        out, i = bytearray(), 20
        while i < len(d):
            n = struct.unpack_from('<I', d, i)[0]
            out += zlib.decompress(d[i + 4:i + 4 + n])
            i += 4 + n
        d = bytes(out)
    tag = b'MainRAM.data8'
    j = d.find(tag)
    if j < 0:
        raise ValueError(f'{path}: no MainRAM in this state')
    size = struct.unpack_from('<I', d, j + len(tag))[0]
    return d[j + len(tag) + 4:j + len(tag) + 4 + size]


STAGE_END = pw.STAGE + 32 * 2048           # the staging area holds up to 32 sectors


def stale_in(ram, changed):
    """The changed strings (old versions) present in RAM outside the staging area (see
    mid_conversation) and the text buffer, which keeps the last line shown until the
    next one. What's left is resident text (castle, battle, status), which a replay
    can't refresh."""
    ram = bytearray(ram)
    ram[pw.BUF:pw.BUF + pw.BUF_LEN] = bytes(pw.BUF_LEN)
    ram[pw.STAGE:STAGE_END] = bytes(STAGE_END - pw.STAGE)
    ram = bytes(ram)
    return [(f, i) for f, i, s in changed if ram.find(s) >= 0]


def mid_conversation(ram, t, ev, heads):
    """The staged file if the state was taken during a conversation or event, else None.
    Each encounter loads the party's portrait and then its text into the staging area,
    and each event loads EVENTMES, so text staged at a state is read again from the new
    disc unless its conversation was already under way. It was if the next staged-file
    line after the state comes from what the state has staged, with no load logged in
    between. (The portrait sits there for about a second, against the monitor's tenth
    of a second, so meeting the same party twice still shows up as two loads.)"""
    head = ram[pw.STAGE:pw.STAGE + 16]
    staged = next((f for f, h in heads.items() if h == head), None)
    nxt = None
    for e in ev:
        if e['t'] <= t:
            continue
        if e['kind'] == 'load':
            return None
        if e['kind'] == 'text' and e.get('file') in heads:
            nxt = e
            break
    return staged if nxt and staged == nxt['file'] else None


# --- builds ---

def changes(old, new):
    """[(file, index, old bytes)] for strings of the old build that the new one doesn't
    have, and the code files that differ (outside the executable's file tables)."""
    changed = []
    for p in pw.FILES:
        now = set(pw.strings(new[p]))
        for i, s in enumerate(pw.strings(old[p])):
            s = s.split(b'\xff\x40')[0]
            if len(s) >= 6 and not any(s in t for t in now):
                changed.append((os.path.basename(p), i, s))
    code = []
    lo, hi = TABLES[0] - EXE_BASE, TABLES[1] - EXE_BASE
    for p in pw.CODE:
        a, b = old[p], new[p]
        if p == pw.EXE:
            a, b = a[:lo] + a[hi:], b[:lo] + b[hi:]
        if a != b:
            code.append(p)
    return changed, code


# --- logs ---

def events(play):
    out = []
    for path in sorted(glob.glob(os.path.join(play, 'logs', '*.jsonl'))):
        day = os.path.basename(path)[:8]
        for line in open(path, encoding='utf-8'):
            e = json.loads(line)
            if len(e['t']) == 8:           # early logs had the time only
                e['t'] = f'{day[:4]}-{day[4:6]}-{day[6:]} {e["t"]}'
            e['log'] = os.path.basename(path)
            out.append(e)
    return out


def state_time(name):
    """'20261007-193853.state' -> '2026-10-07 19:38:53'"""
    n = name[:15]
    return f'{n[:4]}-{n[4:6]}-{n[6:8]} {n[9:11]}:{n[11:13]}:{n[13:15]}'


# --- RetroArch ---

def wait_status(ra, want, secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        st = ra.status()
        if st in want:
            return st
        time.sleep(0.25)
    return None


def write_ram(ra, addr, data):
    for o in range(0, len(data), 128):
        chunk = data[o:o + 128]
        ra.send(f'WRITE_CORE_MEMORY {addr + o:x} ' + ' '.join(f'{b:02x}' for b in chunk))
        time.sleep(0.03)
    return ra.read(addr, len(data)) == data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='pick the state, change nothing')
    ap.add_argument('--state', help='replay from this state in states/auto instead')
    ap.add_argument('--force', action='store_true', help='go ahead even if code changed')
    ap.add_argument('--playdir', default=os.path.join(pw.ROOT, '../playthrough'))
    ap.add_argument('--bin', default=os.path.join(pw.ROOT, '../Wizardry - Dimguil (English WIP).bin'))
    a = ap.parse_args()
    play = os.path.abspath(a.playdir)
    ra = pw.RetroArch()

    if not a.dry_run:
        if ra.status():
            sys.exit('RetroArch is still running: quit it first.')
        pid = os.path.join(play, 'logs', 'playwatch.pid')
        if os.path.exists(pid):
            try:
                os.kill(int(open(pid).read()), 0)
                sys.exit('playwatch is still running: stop it (Ctrl-C) first.')
            except (ProcessLookupError, ValueError):
                os.remove(pid)

    # 1. what changed
    ev = events(play)
    starts = [e for e in ev if e['kind'] == 'start']
    if not starts:
        sys.exit('No play-through logs yet.')
    old_key = starts[-1].get('build')
    if not old_key:
        sys.exit(f'{starts[-1]["log"]} predates build archiving; use --state with care.')
    new_key = pw.archive_build(a.bin, play)
    if new_key == old_key:
        sys.exit('The published image is the one the last session played: '
                 'publish the fix first (publish_test.sh).')
    changed, code = changes(pw.build_files(play, old_key), pw.build_files(play, new_key))
    ver = lambda k: open(os.path.join(play, 'archive/builds', k, 'version.txt')).read().strip()
    print(f'last session: {old_key} ({ver(old_key)})\nnew build:    {new_key} ({ver(new_key)})')
    by_file = {}
    for f, i, _ in changed:
        by_file.setdefault(f, []).append(i)
    print('changed strings: ' + ('; '.join(f'{f} {", ".join(map(str, ix))}'
                                           for f, ix in by_file.items()) or 'none'))
    if code:
        print(f'code changed: {", ".join(code)}')
        if not a.force:
            sys.exit('A state keeps the code it was made with, so the replay would run the old '
                     'code. Stopping (--force to go ahead anyway).')

    # 2. where to replay from
    session = [e for e in ev if e['log'] == starts[-1]['log']]
    stops = [e for e in session if e['kind'] == 'text' and e.get('paused')]
    stop = stops[-1] if stops else None
    if stop:
        print(f'stop: {stop["t"]} {stop["file"]}:{stop["index"]} {stop["status"]}')
        if stop['file'] and (stop['file'], stop['index']) not in {(f, i) for f, i, _ in changed}:
            print('   (this line is the same in the new build)')
    else:
        print('no stop in the last session: replaying to the end of it')
    until = stop['t'] if stop else session[-1]['t']
    auto = os.path.join(play, 'states/auto')
    names = sorted((n for n in os.listdir(auto) if n.endswith('.state')), reverse=True)
    if a.state:
        names = [a.state] if a.state in names else sys.exit(f'{a.state} is not in states/auto')
    heads = {os.path.basename(p): b[:16]
             for p, b in pw.build_files(play, old_key).items() if p in pw.FILES[:pw.STAGED]}
    chosen = None
    for n in names:
        if state_time(n) >= until and not a.state:
            continue
        ram = state_ram(os.path.join(auto, n))
        conv = mid_conversation(ram, state_time(n), ev, heads)
        hits = stale_in(ram, changed)
        if not conv and not hits:
            chosen = n
            break
        print(f'   {n}: ' + (f'taken during an {conv[:-4]} conversation or event' if conv else
                             f'still has {", ".join(f"{f}:{i}" for f, i in hits[:4])}'
                             + (' ...' if len(hits) > 4 else '')))
        if a.state:
            sys.exit('The old text would show again from that state.')
    if not chosen:
        sys.exit('No state before the stop is clear of the old text.')
    st_ev = next((e for e in ev if e['kind'] == 'state' and e.get('file') == chosen), {})
    print(f'replay from {chosen}' + (f' (frame {st_ev["frame"]})' if st_ev.get('frame') else ''))
    for e in ev:
        if e['kind'] == 'text' and state_time(chosen) <= e['t'] <= until:
            print(f'   {e["t"][11:]} {e["file"]}:{e["index"]} {e["text"][:60]!r}')
    later = [n for n in os.listdir(auto) if n.endswith('.state') and n > chosen]
    print(f'states after it, to move to states/abandoned/: {len(later)}')
    if a.dry_run:
        return

    # 3. set aside the stretch being replayed
    stamp = time.strftime('%Y%m%d-%H%M%S')
    if later:
        gone = os.path.join(play, 'states/abandoned', stamp)
        os.makedirs(gone)
        for n in later:
            shutil.move(os.path.join(auto, n), gone)
    content = os.path.splitext(os.path.basename(a.bin))[0]
    slot0 = os.path.join(play, 'states', content + '.state')
    if os.path.exists(slot0):                # a quick save of Chris's: keep it
        keep = os.path.join(play, 'archive/manual-states')
        os.makedirs(keep, exist_ok=True)
        t = time.strftime('%Y%m%d-%H%M%S', time.localtime(os.path.getmtime(slot0)))
        shutil.move(slot0, os.path.join(keep, f'{t}.state'))
    shutil.copy(os.path.join(auto, chosen), slot0)

    # 4. RetroArch, paused on the state, tables fixed, recording
    cfg = os.path.join(play, 'redo.cfg')
    open(cfg, 'w').write(REDO_CFG)
    cue = os.path.splitext(a.bin)[0] + '.cue'
    ralog = os.path.join(play, 'logs', f'{stamp}-retroarch.log')
    subprocess.Popen(['retroarch', f'--appendconfig={play}/retroarch-dimguil.cfg|{cfg}',
                      '-L', CORE, cue], stdout=open(ralog, 'w'), stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True)
    if not wait_status(ra, ('PLAYING', 'PAUSED'), 60):
        sys.exit(f'RetroArch did not come up; see {ralog}')
    if ra.status() == 'PLAYING':
        ra.send('PAUSE_TOGGLE')
    wait_status(ra, ('PAUSED',), 5)
    want = int.from_bytes(state_ram(slot0)[pw.FRAME:pw.FRAME + 4], 'little')
    for _ in range(5):              # early in the boot RetroArch can ignore LOAD_STATE
        ra.send('LOAD_STATE')
        time.sleep(1.5)
        frame = int.from_bytes(ra.read(pw.FRAME, 4) or b'\0' * 4, 'little')
        if abs(frame - want) <= 2:
            break
        time.sleep(2)
    os.remove(slot0)
    if abs(frame - want) > 2:
        sys.exit(f'The state did not load (frame {frame}, expected about {want}); '
                 'RetroArch is left open, paused.')
    tables = pw.build_files(play, new_key)[pw.EXE][TABLES[0] - EXE_BASE:TABLES[1] - EXE_BASE]
    if not write_ram(ra, TABLES[0] & 0x1fffff, tables):
        sys.exit('Writing the file tables failed; RetroArch is left open, paused. Do not play.')
    # Recording starts here, paused, so its first frame is the one after the state, which
    # is what splice.py looks for in the old recording. About 14 frames in, the core
    # corrects its frame rate and RetroArch starts a second file; splice.py reads them as one.
    before = set(os.listdir(os.path.join(play, 'recordings')))
    ra.send('RECORDING_TOGGLE')
    rec = None
    for _ in range(20):
        time.sleep(0.25)
        new = set(os.listdir(os.path.join(play, 'recordings'))) - before
        if new:
            rec = sorted(new)[0]
            break
    if not rec:
        sys.exit('Recording did not start; RetroArch is left open, paused.')
    frame = int.from_bytes(ra.read(pw.FRAME, 4) or b'\0' * 4, 'little')
    ra.send(f'SHOW_MSG Redo from {state_time(chosen)}: recording. Unpause to play.')

    # 5. the record, then the monitor
    record = {'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'state': chosen,
              'state_frame': st_ev.get('frame'), 'state_log': st_ev.get('log'),
              'stop': stop, 'old_build': old_key, 'new_build': new_key,
              'changed': [[f, i] for f, i, _ in changed], 'abandoned': sorted(later),
              'recording': rec, 'frame': frame}
    json.dump(record, open(os.path.join(play, 'logs', f'{stamp}-redo.json'), 'w'), indent=1)
    print(f'recording {rec}; RetroArch is paused on the state. Unpause to play.')
    os.execvp(sys.executable, [sys.executable, '-u', os.path.join(HERE, 'playwatch.py'),
                               '--playdir', play, '--bin', a.bin, '--from-state', chosen])


if __name__ == '__main__':
    main()
