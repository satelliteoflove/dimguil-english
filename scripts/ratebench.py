#!/usr/bin/env python3
"""ratebench.py SAMPLEDIR OUT.json
Encode each ratesample.py segment in every candidate recording format and measure
size, encoding speed (2 threads, as RetroArch records) and, for lossy formats, how far
the pixels drift from the lossless original."""
import json, os, subprocess, sys, time
import numpy as np

D, OUT = sys.argv[1], sys.argv[2]
SEGS = ['town', 'jungle', 'battle', 'training']
W, H = 320, 240

def rgb(*a):
    return ['-c:v', 'libx264rgb', '-pix_fmt', 'bgr24', *a]

VIDEO = [  # (key, label, lossless, ffmpeg args, ext)
    ('x264rgb-ultrafast', 'H.264 RGB lossless, ultrafast', True, rgb('-qp', '0', '-preset', 'ultrafast'), 'mkv'),
    ('x264rgb-veryfast', 'H.264 RGB lossless, veryfast (current setting)', True, rgb('-qp', '0', '-preset', 'veryfast'), 'mkv'),
    ('x264rgb-medium', 'H.264 RGB lossless, medium', True, rgb('-qp', '0', '-preset', 'medium'), 'mkv'),
    ('x264rgb-veryslow', 'H.264 RGB lossless, veryslow', True, rgb('-qp', '0', '-preset', 'veryslow'), 'mkv'),
    ('ffv1', 'FFV1 (archival lossless)', True, ['-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'bgr0'], 'mkv'),
    ('x265-lossless', 'HEVC RGB lossless, medium', True, ['-c:v', 'libx265', '-pix_fmt', 'gbrp', '-x265-params', 'lossless=1:log-level=error'], 'mkv'),
    ('x264rgb-crf4', 'H.264 RGB, CRF 4', False, rgb('-crf', '4', '-preset', 'veryfast'), 'mkv'),
    ('x264rgb-crf8', 'H.264 RGB, CRF 8', False, rgb('-crf', '8', '-preset', 'veryfast'), 'mkv'),
    ('x264rgb-crf12', 'H.264 RGB, CRF 12', False, rgb('-crf', '12', '-preset', 'veryfast'), 'mkv'),
    ('x264rgb-crf16', 'H.264 RGB, CRF 16', False, rgb('-crf', '16', '-preset', 'veryfast'), 'mkv'),
    ('x264rgb-crf20', 'H.264 RGB, CRF 20', False, rgb('-crf', '20', '-preset', 'veryfast'), 'mkv'),
    ('x264-420-crf18', 'H.264 4:2:0, CRF 18 (ordinary video)', False, ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'veryfast'], 'mkv'),
]
AUDIO = [
    ('flac', 'FLAC (current setting)', ['-c:a', 'flac'], 'flac'),
    ('opus192', 'Opus 192 kbit/s', ['-c:a', 'libopus', '-b:a', '192k'], 'opus'),
]

def frames(path, step):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f"select='not(mod(n\\,{step}))'",
                        '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       capture_output=True, check=True).stdout
    return np.frombuffer(p, np.uint8).reshape(-1, H, W, 3).astype(np.int16)

def duration(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                                 'csv=p=0', path], capture_output=True, text=True).stdout)

res = {'segments': {}, 'video': [v[:3] for v in VIDEO], 'audio': [a[:2] for a in AUDIO]}
work = os.path.join(D, 'bench'); os.makedirs(work, exist_ok=True)
for s in SEGS:
    src = os.path.join(D, s + '.mkv')
    secs = duration(src)
    ref = frames(src, 10)
    r = res['segments'][s] = {'seconds': secs, 'video': {}, 'audio': {}}
    for key, label, lossless, args, ext in VIDEO:
        out = os.path.join(work, f'{s}.{key}.{ext}')
        t = time.time()
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-an', '-threads', '2', *args, out], check=True)
        el = time.time() - t
        m = {'bytes': os.path.getsize(out), 'mbps': os.path.getsize(out) * 8 / secs / 1e6,
             'gb_per_hour': os.path.getsize(out) / secs * 3600 / 1e9, 'encode_fps': secs * 59.826 / el}
        got = frames(out, 10)
        d = np.abs(got - ref)
        m['identical'] = bool(d.max() == 0)
        if not m['identical']:
            mse = float((d.astype(np.float64) ** 2).mean())
            m['psnr'] = 10 * np.log10(255 ** 2 / mse)
            m['max_err'] = int(d.max())
            m['pct_changed'] = float((d.max(axis=3) > 0).mean() * 100)
            m['pct_over8'] = float((d.max(axis=3) > 8).mean() * 100)
        r['video'][key] = m
        print(s, key, f"{m['gb_per_hour']:.2f} GB/h", f"{m['encode_fps']:.0f} fps",
              'lossless' if m['identical'] else f"PSNR {m['psnr']:.1f} max {m['max_err']}", flush=True)
    wav = os.path.join(D, s + '.wav')
    for key, label, args, ext in AUDIO:
        out = os.path.join(work, f'{s}.{key}.{ext}')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, *args, out], check=True)
        r['audio'][key] = {'bytes': os.path.getsize(out), 'kbps': os.path.getsize(out) * 8 / secs / 1e3,
                           'gb_per_hour': os.path.getsize(out) / secs * 3600 / 1e9}
    json.dump(res, open(OUT, 'w'), indent=1)
print('done')
