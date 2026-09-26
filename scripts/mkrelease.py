#!/usr/bin/env python3
"""Package a release from a finished build: an xdelta patch for Track 1, a readme and notes.

    mkrelease.py VERSION ORIGINAL.cue

ORIGINAL.cue is the redump Rev 1 cue sheet (one .bin per track). The build writes one
merged .bin, but only track 1 changes: the audio tracks come out byte-identical, just
later on the disc because track 1 grew. So the patch covers the Track 1 .bin alone, and
players keep their cue sheet and audio tracks as they are. This checks that assumption
on every release and stops if it ever breaks.

Writes rips/release/VERSION/: the zip for players (patch + readme.txt) and notes.md
(this version's section of CHANGELOG.md, for the GitHub release). Needs xdelta3 (set
XDELTA3 if it isn't on PATH).
"""
import hashlib, os, re, shutil, subprocess, sys, zipfile, zlib

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BUILT_CUE = os.path.join(ROOT, 'rips/iso/dimguil-en.cue')
TRACK1_MD5 = '9eeb5c508abb23c0e3538108b7755890'  # redump 60391, Rev 1
SECTOR = 2352
XDELTA3 = os.environ.get('XDELTA3', 'xdelta3')


def cue_files(cue):
    """[(bin path, [(track no, {index no: sector})])] in cue order."""
    out, base = [], os.path.dirname(os.path.abspath(cue))
    for line in open(cue, encoding='utf-8', errors='replace'):
        w = line.split()
        if not w:
            continue
        if w[0] == 'FILE':
            out.append((os.path.join(base, re.match(r'\s*FILE\s+"(.*)"', line).group(1)), []))
        elif w[0] == 'TRACK':
            out[-1][1].append((int(w[1]), {}))
        elif w[0] == 'INDEX':
            m, s, f = map(int, w[2].split(':'))
            out[-1][1][-1][1][int(w[1])] = (m * 60 + s) * 75 + f
    return out


def digests(path, start=0, length=None):
    md5, sha1, crc = hashlib.md5(), hashlib.sha1(), 0
    with open(path, 'rb') as f:
        f.seek(start)
        left = length if length is not None else os.path.getsize(path) - start
        while left:
            b = f.read(min(left, 1 << 20))
            if not b:
                sys.exit(f'{path} is shorter than expected')
            md5.update(b); sha1.update(b); crc = zlib.crc32(b, crc)
            left -= len(b)
    return {'md5': md5.hexdigest(), 'sha1': sha1.hexdigest(), 'crc32': f'{crc:08x}'}


def changelog_section(version):
    text = open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read()
    m = re.search(rf'^## {re.escape(version)}\b.*?\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not m or not m.group(1).strip():
        sys.exit(f'CHANGELOG.md has no section for {version}')
    return m.group(1).strip() + '\n'


def main():
    version, orig_cue = sys.argv[1], sys.argv[2]
    notes = changelog_section(version)

    orig = cue_files(orig_cue)
    if len(orig) < 2 or any(len(t) != 1 for _, t in orig):
        sys.exit('expected a redump cue sheet with one .bin per track')
    orig_t1 = orig[0][0]
    src = digests(orig_t1)
    if src['md5'] != TRACK1_MD5:
        sys.exit(f'{orig_t1} is not the Rev 1 Track 1 (md5 {src["md5"]})')

    # Track 1 of the build ends where track 2's pregap (INDEX 00) starts.
    built = cue_files(BUILT_CUE)
    (built_bin, tracks), = built
    t1_sectors = dict(tracks)[2][0]
    t1_len = t1_sectors * SECTOR

    # Everything after track 1 must be the original audio tracks, untouched.
    audio = hashlib.md5()
    for path, _ in orig[1:]:
        with open(path, 'rb') as f:
            while b := f.read(1 << 20):
                audio.update(b)
    rest = digests(built_bin, t1_len)['md5']
    if rest != audio.hexdigest():
        sys.exit('the audio tracks in the build differ from the originals; a Track 1 patch won\'t do')

    out = os.path.join(ROOT, 'rips/release', version)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    new_t1 = os.path.join(out, 'track1.bin')
    with open(built_bin, 'rb') as f, open(new_t1, 'wb') as g:
        left = t1_len
        while left:
            b = f.read(min(left, 1 << 20))
            g.write(b); left -= len(b)
    dst = digests(new_t1)

    name = f'Wizardry - Dimguil (English {version})'
    patch = os.path.join(out, name + '.xdelta')
    # No secondary compression: some patchers (Rom Patcher JS among them) can't read it.
    subprocess.run([XDELTA3, '-e', '-9', '-S', 'none', '-f', '-s', orig_t1, new_t1, patch], check=True)

    # Apply it back and compare, so a bad patch never ships.
    check = os.path.join(out, 'check.bin')
    subprocess.run([XDELTA3, '-d', '-f', '-s', orig_t1, patch, check], check=True)
    if digests(check)['md5'] != dst['md5']:
        sys.exit('the patch does not reproduce the built Track 1')
    os.remove(check)
    os.remove(new_t1)

    template = open(os.path.join(ROOT, 'docs/release-readme.txt'), encoding='utf-8').read()
    readme = template.format(
        version=version, patch=os.path.basename(patch), notes=notes.rstrip(),
        src_md5=src['md5'], src_sha1=src['sha1'], src_crc=src['crc32'],
        dst_md5=dst['md5'], dst_sha1=dst['sha1'], dst_crc=dst['crc32'])
    readme = readme.replace('\n', '\r\n')  # Notepad-friendly

    zpath = os.path.join(out, name + '.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(patch, os.path.basename(patch))
        z.writestr('readme.txt', readme)
    open(os.path.join(out, 'notes.md'), 'w', encoding='utf-8').write(notes)
    print(zpath)


if __name__ == '__main__':
    main()
