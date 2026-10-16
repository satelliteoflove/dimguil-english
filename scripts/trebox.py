"""Dump DATA03/TRE_BOX.BIN (the 30 0x5c-byte reward records chest_loot reads) and each monster's
reward bytes +0x82/+0x83 (the battle uses group 1's +0x83, 1-based)."""
import struct, glob, os, json, collections, sys
CLEAN = 'rips/clean/dimguil'
TR = ['ok', 'Stone', 'Needle', 'MDrain', 'Gas', 'Explode', 'Ghost', 'DEye', 'Rainbow', 'Kiss', 'Blaster', 'Alarm', 'Telep']
d = open(f'{CLEAN}/DATA03/TRE_BOX.BIN', 'rb').read()
recs = []
for i in range(len(d) // 0x5c):
    r = d[i*0x5c:(i+1)*0x5c]
    u = lambda o: struct.unpack_from('<i', r, o)[0]
    rec = dict(n=i+1, items=r[0], traps=[TR[b] for b in range(13) if u(4) >> b & 1],
               chance=[u(8+4*k) for k in range(3)], minidx=[u(0x14+4*k) for k in range(3)],
               mfactor=[u(0x20+4*k) for k in range(3)], maxtimes=[u(0x2c+4*k) for k in range(3)],
               range=[u(0x38+4*k) for k in range(3)], percbigr=[u(0x44+4*k) for k in range(3)],
               gold1=list(r[0x50:0x53]), mult=u(0x54), gold2=list(r[0x58:0x5b]))
    recs.append(rec)
mons = {}
site = json.load(open(os.path.expanduser('~/Documents/bartoks-trading-post/archive/rom-findings/dimguil.json')))['monsters']['records']
for p in sorted(glob.glob(f'{CLEAN}/DATA02/M_DT*.BIN')):
    n = int(os.path.basename(p)[4:7]); b = open(p, 'rb').read()
    s = site.get(str(n))
    off = (s['record_offset'] - 0x6c) if s and 'record_offset' in s else len(b) - 0xd0
    r = b[off:off+0xd0]
    idok = struct.unpack_from('<H', r, 0x6c)[0] == n
    mons[n] = dict(n=n, en=(s or {}).get('en'), r82=r[0x82], r83=r[0x83], idok=idok, lvl=struct.unpack_from('<H', r, 0x74)[0])
if __name__ == '__main__':
    for rec in recs:
        print(rec)
    print('monsters with id mismatch:', [m['n'] for m in mons.values() if not m['idok']])
    print('+0x83:', sorted(collections.Counter(m['r83'] for m in mons.values() if m['idok']).items()))
    json.dump(dict(trebox=recs, monsters=list(mons.values())), open('rips/agents/chests/trebox.json', 'w'), indent=0, ensure_ascii=False)
