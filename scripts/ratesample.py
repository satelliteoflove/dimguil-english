#!/usr/bin/env python3
"""ratesample.py OUTDIR [SECONDS]
Record sample footage for the play-through data-rate tests: dungeon walking, a battle
and town menus, played from the standard test states with scripted input. Each segment
is written losslessly (OUTDIR/<name>.mkv, 320x240 RGB at the core's frame rate, the same
picture RetroArch records) with its sound (OUTDIR/<name>.wav)."""
import ctypes as C, os, random, subprocess, sys, wave
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rips', 'probe'))
import emu, fixstate

OUT = sys.argv[1]
SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 90
FPS = '59.826'   # Beetle's NTSC rate for this game (RetroArch log: 59.83)
X0 = 14          # the 320-wide game picture sits at x 14..334 of Beetle's 350-wide frame

e = emu.Emu('rips/iso/dimguil-en.cue')
pcm = bytearray()
def _audio(data, n):
    pcm.extend(C.string_at(data, n * 4)); return n
_cb = emu.AUDIOB_CB(_audio)
e.lib.retro_set_audio_sample_batch(_cb)

enc = None
def _start(name):
    global enc
    pcm.clear()
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                            '-s', '320x240', '-r', FPS, '-i', '-', '-c:v', 'libx264rgb', '-qp', '0',
                            '-preset', 'ultrafast', os.path.join(OUT, name + '.mkv')],
                           stdin=subprocess.PIPE)

def _stop(name):
    enc.stdin.close(); enc.wait()
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100); w.writeframes(bytes(pcm))

def run(frames, hold=()):
    """Like Emu.run, but every frame goes to the encoder."""
    e.buttons = 0
    for b in hold:
        e.buttons |= 1 << emu.BTN[b]
    for _ in range(frames):
        e.lib.retro_run(); e.frame_no += 1
        im = e.image()
        if im.width != 350 or im.height != 240:
            im = im.resize((350, 240))   # never expected in these segments
        enc.stdin.write(im.crop((X0, 0, X0 + 320, 240)).tobytes())
    e.buttons = 0

def tap(b, hold=6, after=30):
    run(hold, (b,)); run(after)

def segment(name, state, play):
    e.load(state if '/' in state else f'rips/states/{state}.state'); fixstate.fix(e); e.run(2)
    _start(name)
    n = SECS * 60
    rnd = random.Random(name)
    while e.frame_no < start_frame[0] + n:
        play(rnd)
    _stop(name)
    e.save(os.path.join(OUT, name + '_end.state'))
    print(name, 'done', flush=True)

start_frame = [0]
def begin(name, state, play):
    start_frame[0] = e.frame_no + 3
    segment(name, state, play)

# Dungeon: mostly forward steps and turns. Circle takes any battle along (it picks the
# offered command), and in the maze it only searches or opens a door.
def dungeon(r):
    k = r.random()
    if k < 0.55: tap('up', after=r.choice((20, 30, 45)))
    elif k < 0.7: tap('left')
    elif k < 0.85: tap('right')
    else: tap('circle', after=r.choice((15, 25, 40)))

# Town: move along the facility icons (0-5; 6 is the edge of town), step into one,
# look around, step out.
pos = [0]
def town(r):
    want = r.randint(0, 5)
    while pos[0] != want:
        d = 1 if want > pos[0] else -1
        tap('right' if d > 0 else 'left', after=20); pos[0] += d
    tap('circle', after=150)
    for _ in range(r.randint(1, 5)):
        tap(r.choice(('up', 'down')), after=25)
    tap('cross', after=60); tap('cross', after=120)

os.makedirs(OUT, exist_ok=True)
begin('town', 'town_party', town)
begin('jungle', 'maze_door', dungeon)
begin('battle', 'battle_start', dungeon)
# The training maze (stone walls), reached through the edge of town.
e.load('rips/states/town_party.state'); fixstate.fix(e); e.run(2)
e.seq('right right right right right right w20 circle w150 right w20 circle w200 circle w300 w300 cross w120')
e.save(os.path.join(OUT, 'training_start.state'))
begin('training', os.path.join(OUT, 'training_start.state'), dungeon)
