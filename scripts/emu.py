#!/usr/bin/env python3
"""Minimal headless libretro frontend for Beetle PSX (mednafen_psx_libretro.so).

Lets scripts boot a disc, step frames with controller input, grab screenshots,
peek/poke main RAM and save/load states. No audio/video output.

    from emu import Emu
    e = Emu('build/dimguil-en.cue')
    e.run(600)                 # 10 seconds
    e.press('circle'); e.shot('out.png')
    e.save('states/title.state')
"""
import ctypes as C, os, sys, time, struct
from PIL import Image

CORE = os.environ.get('PSX_CORE', os.path.expanduser('~/src/beetle-psx-libretro/mednafen_psx_libretro.so'))
SYSDIR = os.environ.get('PSX_SYSDIR', os.path.expanduser('~/src/bios'))

# RetroPad ids; Beetle maps Cross=B, Circle=A, Square=Y, Triangle=X
BTN = dict(cross=0, square=1, select=2, start=3, up=4, down=5, left=6, right=7,
           circle=8, triangle=9, l1=10, r1=11, l2=12, r2=13, l3=14, r3=15)

OPTIONS = {
    'beetle_psx_renderer': 'software',
    'beetle_psx_internal_resolution': '1x(native)',
    'beetle_psx_cpu_dynarec': 'disabled',   # interpreter = most accurate
    'beetle_psx_skip_bios': 'disabled',
    'beetle_psx_cd_access_method': 'precache',
    'beetle_psx_frame_duping': 'disabled',
    'beetle_psx_crop_overscan': 'enabled',
}


class GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]


class Variable(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]


ENV_CB = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO_CB = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIOB_CB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL_CB = C.CFUNCTYPE(None)
STATE_CB = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)
LOG_CB = C.CFUNCTYPE(None, C.c_int, C.c_char_p)  # variadic in reality; we only print fmt


class Emu:
    def __init__(self, cue, verbose=False):
        self.lib = C.CDLL(CORE)
        self.verbose = verbose
        self.buttons = 0
        self.frame = None
        self.frame_no = 0
        self._keep = []
        self._sysdir = C.c_char_p(SYSDIR.encode())
        self._opts = {k.encode(): C.c_char_p(v.encode()) for k, v in OPTIONS.items()}
        self._log_iface = (C.c_void_p * 1)()
        self._logfn = C.CFUNCTYPE(None, C.c_int, C.c_char_p)(self._log)
        self._log_iface[0] = C.cast(self._logfn, C.c_void_p)

        cbs = [(self.lib.retro_set_environment, ENV_CB(self._env)),
               (self.lib.retro_set_video_refresh, VIDEO_CB(self._video)),
               (self.lib.retro_set_audio_sample, AUDIO_CB(lambda l, r: None)),
               (self.lib.retro_set_audio_sample_batch, AUDIOB_CB(lambda d, n: n)),
               (self.lib.retro_set_input_poll, POLL_CB(lambda: None)),
               (self.lib.retro_set_input_state, STATE_CB(self._input))]
        for setter, cb in cbs:
            self._keep.append(cb)
            setter(cb)
        self.lib.retro_init()
        gi = GameInfo(os.path.abspath(cue).encode(), None, 0, None)
        if not self.lib.retro_load_game(C.byref(gi)):
            raise RuntimeError('retro_load_game failed')
        self.lib.retro_get_memory_data.restype = C.c_void_p
        self.lib.retro_get_memory_size.restype = C.c_size_t
        self.lib.retro_serialize_size.restype = C.c_size_t
        self._ram_ptr = self.lib.retro_get_memory_data(2)
        self._ram_size = self.lib.retro_get_memory_size(2)

    # --- callbacks ---
    def _log(self, level, fmt):
        if self.verbose:
            sys.stderr.write(fmt.decode(errors='replace'))

    def _env(self, cmd, data):
        cmd &= 0xffff  # strip experimental/private flags
        if cmd == 3:  # GET_CAN_DUPE
            C.cast(data, C.POINTER(C.c_bool))[0] = True; return True
        if cmd in (9, 31):  # system / save dir
            C.cast(data, C.POINTER(C.c_char_p))[0] = self._sysdir; return True
        if cmd == 10:  # SET_PIXEL_FORMAT
            self.pixfmt = C.cast(data, C.POINTER(C.c_int))[0]; return self.pixfmt in (1, 2)
        if cmd == 15:  # GET_VARIABLE
            var = C.cast(data, C.POINTER(Variable))[0]
            v = self._opts.get(var.key)
            if v is None:
                return False
            C.cast(data, C.POINTER(Variable))[0].value = v; return True
        if cmd == 17:  # GET_VARIABLE_UPDATE
            C.cast(data, C.POINTER(C.c_bool))[0] = False; return True
        if cmd == 27:  # GET_LOG_INTERFACE
            C.cast(data, C.POINTER(C.c_void_p))[0] = self._log_iface[0]; return True
        return False

    def _video(self, data, w, h, pitch):
        if data:
            self.frame = (C.string_at(data, pitch * h), w, h, pitch)

    def _input(self, port, device, index, id_):
        if port != 0 or device != 1:
            return 0
        if id_ == 256:  # RETRO_DEVICE_ID_JOYPAD_MASK
            return self.buttons
        return (self.buttons >> id_) & 1

    # --- control ---
    def run(self, frames=1, hold=()):
        self.buttons = 0
        for b in hold:
            self.buttons |= 1 << BTN[b]
        for _ in range(frames):
            self.lib.retro_run()
            self.frame_no += 1
        self.buttons = 0

    def press(self, *btns, hold=4, after=20):
        """Tap button(s) together for `hold` frames, then idle `after` frames."""
        self.run(hold, btns)
        self.run(after)

    def seq(self, s, hold=4, after=20):
        """Space-separated button taps, e.g. 'down down circle'. 'wN' waits N frames."""
        for tok in s.split():
            if tok[0] == 'w' and tok[1:].isdigit():
                self.run(int(tok[1:]))
            else:
                self.press(*tok.split('+'), hold=hold, after=after)

    def image(self):
        data, w, h, pitch = self.frame
        if self.pixfmt == 1:  # XRGB8888
            return Image.frombuffer('RGB', (w, h), data, 'raw', 'BGRX', pitch, 1)
        return Image.frombuffer('RGB', (w, h), data, 'raw', 'BGR;16', pitch, 1)  # RGB565

    def shot(self, path, scale=2):
        im = self.image()
        if scale != 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        im.save(path)
        return path

    # --- memory (addresses may be given as 0x80xxxxxx or physical) ---
    def ram(self):
        return (C.c_ubyte * self._ram_size).from_address(self._ram_ptr)

    def read(self, addr, n):
        a = addr & 0x1fffff
        return bytes(self.ram()[a:a + n])

    def write(self, addr, data):
        a = addr & 0x1fffff
        self.ram()[a:a + len(data)] = data

    def u32(self, addr):
        return int.from_bytes(self.read(addr, 4), 'little')

    # --- states ---
    def save(self, path):
        n = self.lib.retro_serialize_size()
        buf = C.create_string_buffer(n)
        assert self.lib.retro_serialize(buf, C.c_size_t(n))
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        open(path, 'wb').write(buf.raw)

    def load(self, path):
        d = open(path, 'rb').read()
        self.run(1)  # core must have run once before unserialize
        assert self.lib.retro_unserialize(d, C.c_size_t(len(d))), 'unserialize failed'

    # --- debugger hooks (custom-patched core: retro_dbg_*) ---
    EXEC, READ, WRITE = 1, 2, 4

    def dbg_clear(self):
        self.lib.retro_dbg_clear()

    def watch(self, lo, hi=None, mode=6):
        """Log accesses to [lo, hi). mode: READ=2 | WRITE=4."""
        hi = lo + 1 if hi is None else hi
        assert self.lib.retro_dbg_watch(C.c_uint32(lo & 0x1fffffff), C.c_uint32(hi & 0x1fffffff), C.c_uint32(mode))

    def bp(self, pc):
        """Log every execution of pc (with registers)."""
        assert self.lib.retro_dbg_break(C.c_uint32(pc))

    def log(self, reset=True):
        n = self.lib.retro_dbg_log_count()
        self.lib.retro_dbg_log_data.restype = C.c_void_p
        raw = C.string_at(self.lib.retro_dbg_log_data(), n * 160)
        out = []
        for k in range(n):
            v = struct.unpack_from('<40I', raw, k * 160)
            out.append(dict(type={1: 'X', 2: 'R', 4: 'W'}[v[0]], pc=v[1], addr=v[2], value=v[3],
                            size=v[4], seq=v[5], ra=v[6], regs=v[8:40]))
        if reset:
            self.lib.retro_dbg_log_reset()
        return out

    def coverage(self, on=True):
        self.lib.retro_dbg_coverage(C.c_int(on))

    def covered(self):
        """Set of executed RAM PCs (0x80xxxxxx) since coverage(True)."""
        self.lib.retro_dbg_coverage_data.restype = C.c_void_p
        cov = C.string_at(self.lib.retro_dbg_coverage_data(), 0x80000)
        return {0x80000000 + i * 4 for i, b in enumerate(cov) if b}


REGN = 'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split()


def fmt_entry(e):
    r = e['regs']
    return (f"{e['type']} pc={e['pc']:08x} addr={e['addr']:08x} sz={e['size']} val={e['value']:08x} "
            f"ra={e['ra']:08x} a0={r[4]:08x} a1={r[5]:08x} a2={r[6]:08x} v0={r[2]:08x}")
