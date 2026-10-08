#!/usr/bin/env python3
"""Find where each redo recording joins the recording it replaces, and list the cut.

    splice.py [--playdir DIR]        find the join for every redo not done yet
    splice.py --list                 the edit: what's kept of each recording file

redo.py loads a save state and starts recording before the game runs a frame, so the
redo's first frame is the frame after the state. Emulation from a state is exact, so
that frame, and the sound with it, is in the old recording sample for sample, up to the
point where the player did something different. This finds it: the sound first (the
first two frames' worth, searched through the whole old recording), then the picture to
confirm it and to fix the frame. In silence it goes by the picture alone and takes the
match nearest to where the logs put the state.

Each join goes in cuts.json, and a clip of six seconds around it (three of the old
recording, three of the redo) goes in archive/splices/ to watch. The recordings are
never changed; --list is the edit to assemble them by.
"""
import argparse, glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
RATE = 44100
NEEDLE = 1474                       # samples: about two frames


def recfile(play, name):
    return os.path.join(play, 'recordings', name)


def video_md5(path, cache=None, limit=None):
    """One md5 per video frame. Cached per recording once it's finished."""
    if cache and os.path.exists(cache):
        return open(cache).read().split()
    cmd = ['ffmpeg', '-v', 'error', '-i', path, '-map', '0:v']
    if limit:
        cmd += ['-frames:v', str(limit)]
    out = subprocess.run(cmd + ['-f', 'framemd5', '-'], capture_output=True, text=True).stdout
    md5 = [l.split(',')[-1].strip() for l in out.splitlines() if l and not l.startswith('#')]
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        open(cache, 'w').write('\n'.join(md5))
    return md5


def pcm(path, start=0, count=None):
    """s16 stereo samples as bytes."""
    cmd = ['ffmpeg', '-v', 'error', '-i', path, '-map', '0:a', '-af',
           f'atrim=start_sample={start}' + (f':end_sample={start + count}' if count else ''),
           '-f', 's16le', '-']
    return subprocess.run(cmd, capture_output=True).stdout


def audio_find(path, needle):
    """Every sample position where needle (s16 stereo bytes) occurs, and the total
    number of samples."""
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:a', '-f', 's16le', '-'],
                         stdout=subprocess.PIPE)
    hits, buf, base = [], b'', 0
    while True:
        chunk = p.stdout.read(1 << 24)
        if not chunk:
            break
        buf += chunk
        j = buf.find(needle)
        while j >= 0:
            if j % 4 == 0:
                hits.append((base + j) // 4)
            j = buf.find(needle, j + 1)
        keep = len(needle) - 1
        keep -= keep % 4
        base += len(buf) - keep
        buf = buf[len(buf) - keep:]
    p.wait()
    return hits, (base + len(buf)) // 4


def redo_stream(play, record):
    """The redo's recording files: the first one and any that RetroArch started right
    after it (the frame-rate correction about 14 frames in)."""
    names = sorted(os.listdir(os.path.join(play, 'recordings')))
    i = names.index(record['recording'])
    files = [names[i]]
    if len(video_md5(recfile(play, names[i]), limit=60)) < 60 and i + 1 < len(names):
        files.append(names[i + 1])
    return files


def old_candidates(play, record):
    """Old recording files that may hold the state, best guess first, with the frame the
    logs put it at (or None)."""
    ev = []
    for path in sorted(glob.glob(os.path.join(play, 'logs', '*.jsonl'))):
        ev += [json.loads(l) for l in open(path, encoding='utf-8')]
    st = next((e for e in ev if e['kind'] == 'state' and e.get('file') == record['state']), None)
    recs = [e for e in ev if e['kind'] == 'recording' and st and e['t'] <= st['t']]
    out = []
    if recs:
        r = recs[-1]
        est = st['frame'] - r['frame'] if st.get('frame') and r.get('frame') else None
        out.append((r['file'], est))
    s = record['state']                      # 20261007-210835.state
    stamp = s[2:8] + '-' + s[9:15]           # 261007-210835, as in RetroArch's names
    for name in sorted(os.listdir(os.path.join(play, 'recordings')), reverse=True):
        if name[-17:-4] <= stamp and name not in [o[0] for o in out] \
                and name != record['recording']:
            out.append((name, None))
    return out[:3]


def find_join(play, record):
    redo = redo_stream(play, record)
    rv = sum((video_md5(recfile(play, f), limit=600) for f in redo), [])[:600]
    ra = pcm(recfile(play, redo[0]), 0, NEEDLE)
    silent = not ra.strip(b'\0')
    for name, est in old_candidates(play, record):
        path = recfile(play, name)
        ov = video_md5(path, os.path.join(play, 'archive/hashes', name + '.md5'))
        hits, total = audio_find(path, ra) if not silent else ([], None)
        if total is None:
            total = len(pcm(path)) // 4
        spf = total / len(ov)
        if hits:
            cands = []
            for p in hits:
                k0 = round(p / spf)
                for k in range(max(0, k0 - 3), min(len(ov), k0 + 4)):
                    if ov[k] == rv[0]:
                        cands.append((k, p))
        else:
            cands = [(k, round(k * spf)) for k in range(len(ov)) if ov[k] == rv[0]]
        if not cands:
            continue

        def agree(c):
            n = 0
            while n < len(rv) and c[0] + n < len(ov) and ov[c[0] + n] == rv[n]:
                n += 1
            return n
        scored = sorted(cands, key=lambda c: (-agree(c), abs(c[0] - est) if est is not None
                                              else 0))
        best = scored[0]
        same = [c for c in scored if agree(c) == agree(best)]
        return {'redo': record['_name'], 'old': name, 'frame': best[0], 'sample': best[1],
                'redo_files': redo, 'agree_frames': agree(best), 'by': 'sound' if hits else 'picture',
                'estimate': est, 'ambiguous': len(same) > 1 and est is None,
                'samples_per_frame': spf}
    return None


def clip(play, cut, secs=3):
    """Six seconds around the join, lossless, in archive/splices/."""
    n = round(secs * 59.826)
    spf = cut['samples_per_frame']
    k, p = cut['frame'], cut['sample']
    a0 = max(0, k - n)
    ins = ['-i', recfile(play, cut['old'])]
    parts = [f'[0:v]trim=start_frame={a0}:end_frame={k},setpts=N/(59.826*TB)[v0];'
             f'[0:a]atrim=start_sample={round(a0 * spf)}:end_sample={p},asetpts=N/SR/TB[a0];']
    for i, f in enumerate(cut['redo_files'], 1):
        ins += ['-i', recfile(play, f)]
        parts.append(f'[{i}:v]setpts=N/(59.826*TB)[v{i}];[{i}:a]asetpts=N/SR/TB[a{i}];')
    m = len(cut['redo_files']) + 1
    graph = ''.join(parts) + ''.join(f'[v{i}][a{i}]' for i in range(m)) + \
        f'concat=n={m}:v=1:a=1[v][a];[v]trim=end_frame={(k - a0) + n}[vo];' \
        f'[a]atrim=end_sample={round(((k - a0) + n) * spf)}[ao]'
    out = os.path.join(play, 'archive/splices', cut['redo'].replace('-redo.json', '') + '.mkv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + ins + ['-filter_complex', graph,
                    '-map', '[vo]', '-map', '[ao]', '-c:v', 'libx264rgb', '-qp', '0',
                    '-preset', 'veryfast', '-c:a', 'flac', out], check=True)
    return out


def edit(play, cuts):
    """[(file, first frame, end frame or None)] in playing order."""
    names = sorted(os.listdir(os.path.join(play, 'recordings')))
    keep = {n: [0, None] for n in names}
    for c in cuts:
        keep[c['old']][1] = c['frame']
        a, b = names.index(c['old']), names.index(c['redo_files'][0])
        for n in names[a + 1:b]:             # the rest of the replaced stretch
            keep[n] = None
    return [(n, *keep[n]) for n in names if keep[n]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--playdir', default=os.path.join(ROOT, '../playthrough'))
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    play = os.path.abspath(a.playdir)
    cuts_path = os.path.join(play, 'cuts.json')
    cuts = json.load(open(cuts_path)) if os.path.exists(cuts_path) else []
    if a.list:
        for n, k0, k1 in edit(play, cuts):
            print(f'{n}  frames {k0}-{"end" if k1 is None else k1 - 1}')
        return
    done = {c['redo'] for c in cuts}
    for path in sorted(glob.glob(os.path.join(play, 'logs', '*-redo.json'))):
        name = os.path.basename(path)
        if name in done:
            continue
        record = json.load(open(path))
        record['_name'] = name
        cut = find_join(play, record)
        if not cut:
            print(f'{name}: no join found; the state may not be in any recording')
            continue
        cut['clip'] = os.path.relpath(clip(play, cut), play)
        cuts.append(cut)
        json.dump(cuts, open(cuts_path, 'w'), indent=1)
        print(f'{name}: {cut["old"]} frame {cut["frame"]} (by {cut["by"]}; the recordings '
              f'agree for {cut["agree_frames"]} frames after it'
              + (f'; the logs said about {cut["estimate"]}' if cut['estimate'] is not None else '')
              + ')' + ('\n   AMBIGUOUS: several equally good places' if cut['ambiguous'] else '')
              + f'\n   clip: {cut["clip"]}')


if __name__ == '__main__':
    main()
