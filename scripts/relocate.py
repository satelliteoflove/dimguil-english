#!/usr/bin/env python3
"""Relocate files that outgrew their sectors, and write the mkpsxiso XML.

The game never looks files up by name. The executable holds four tables of BCD MSF
start positions plus matching sector counts, and the loader at 0x80012f5c calls
CdRead(count, dest, 0x80) with them:

    table  MSF base     count base   count width
      0    0x80051760   0x80051a60   u16
      1    0x80051bc8   0x80052234   u8   (DATA00/01 ... DATA03)
      2    0x80052458   0x8005258c   u8   (DATA06)
      3    0x800525f4   0x800526c8   u8   (DATA05)

So every file must keep its original LBA. A file that needs more sectors than it had is
appended after the last data file instead, and every table entry that pointed at its old
LBA gets the new MSF and count. The file's RAM destination buffer must have room too, so
only files listed in MAX_SECTORS may grow; anything else stops the build.

relocate.py CLEAN_XML DIRTY_DIR OUT_XML
  - patches DIRTY_DIR/SLPS_026.91 (copied from clean if the build hasn't touched it)
  - OUT_XML: CLEAN_XML with sources pointed at the iso tree and moved files' offs updated
"""
import math, os, re, shutil, sys

EXE_BASE = 0x80010000 - 0x800  # RAM address of file offset 0
TABLES = [(0x80051760, 0x80051a60, 2), (0x80051bc8, 0x80052234, 1),
          (0x80052458, 0x8005258c, 1), (0x800525f4, 0x800526c8, 1)]
TABLE_LEN = {0: 263, 1: 547, 2: 102, 3: 70}

# Largest sector count each file's load buffer can take, checked in RAM:
# SISETU.OBJ loads to 0x801d8c00, next live data at 0x801e0200 -> 14 whole sectors.
# NPC_MES1-5.OBJ load (one at a time, when an NPC is met) to 0x801a0400, the staging
# area the maze also uses for 66-sector wall textures. Nothing else is loaded or read
# there during a conversation; 32 sectors stays below MAZE.BIN's second buffer at 0x801b0400.
# I_NAME_E.OBJ (and I_NAME_J) load to 0x801d1000; FIGHTMSG.OBJ is resident from 0x801d7000
# in town and maze alike -> 12 whole sectors.
MAX_SECTORS = {
    'DATA06/SISETU.OBJ': 14,
    'DATA06/I_NAME_E.OBJ': 12,
    **{f'DATA06/NPC_MES{n}.OBJ': 32 for n in range(1, 6)},
}


def bcd(n):
    return (n // 10) << 4 | (n % 10)


def unbcd(b):
    return (b >> 4) * 10 + (b & 15)


def msf(lba):
    a = lba + 150
    return bytes((bcd(a // 4500), bcd(a // 75 % 60), bcd(a % 75)))


def main(clean_xml, dirty, out_xml):
    xml = open(clean_xml, encoding='utf-8').read()
    clean_root = os.path.join(os.path.dirname(clean_xml), 'dimguil')
    # file entries: path -> (offs, match span)
    entries, mixed = {}, set()
    for m in re.finditer(r'<file name="[^"]+" source="dimguil/([^"]+)" type="(\w+)"[^>]*offs="(\d+)"/>', xml):
        entries[m.group(1)] = int(m.group(3))
        if m.group(2) != 'data':
            mixed.add(m.group(1))  # XA/STR: extracted as 2336-byte sectors
    last_end = 0
    for path, offs in entries.items():
        sz = os.path.getsize(os.path.join(clean_root, path))
        last_end = max(last_end, offs + math.ceil(sz / (2336 if path in mixed else 2048)))
    next_free = last_end

    exe_path = os.path.join(dirty, 'SLPS_026.91')
    if not os.path.exists(exe_path):
        shutil.copy(os.path.join(clean_root, 'SLPS_026.91'), exe_path)
    exe = bytearray(open(exe_path, 'rb').read())
    off = lambda ram: ram - EXE_BASE

    moved = {}
    for base, _, files in os.walk(dirty):
        for f in files:
            path = os.path.relpath(os.path.join(base, f), dirty)
            if path not in entries:
                continue
            old = math.ceil(os.path.getsize(os.path.join(clean_root, path)) / 2048)
            new = math.ceil(os.path.getsize(os.path.join(dirty, path)) / 2048)
            if new <= old:
                continue
            if new > MAX_SECTORS.get(path, old):
                sys.exit(f'relocate: {path} needs {new} sectors (had {old}); its load buffer '
                         f'allows {MAX_SECTORS.get(path, old)}. Shorten the text or verify a larger buffer.')
            lba = entries[path]
            hits = 0
            for t, (mbase, cbase, w) in enumerate(TABLES):
                for i in range(TABLE_LEN[t]):
                    p = off(mbase) + 3 * i
                    e = exe[p:p + 3]
                    if unbcd(e[0]) * 4500 + unbcd(e[1]) * 75 + unbcd(e[2]) - 150 != lba:
                        continue
                    exe[p:p + 3] = msf(next_free)
                    c = off(cbase) + w * i
                    exe[c:c + w] = new.to_bytes(w, 'little')
                    hits += 1
            if not hits:
                sys.exit(f'relocate: no table entry for {path} (LBA {lba})')
            print(f'  moved {path}: LBA {lba} -> {next_free}, {old} -> {new} sectors ({hits} table entries)')
            moved[path] = next_free
            next_free += new
    open(exe_path, 'wb').write(bytes(exe))

    def fix(m):
        path = m.group(1)
        s = m.group(0)
        if path in moved:
            s = re.sub(r'offs="\d+"', f'offs="{moved[path]}"', s)
        return s
    xml = re.sub(r'<file name="[^"]+" source="dimguil/([^"]+)"[^>]*/>', fix, xml)
    if moved:
        # postgap and audio positions follow the (now longer) data track: let mkpsxiso place them
        xml = re.sub(r'(<dummy sectors="150" type="0") offs="\d+"', r'\1', xml)
        xml = re.sub(r'(<file name="[^"]+\.DA" trackid="\d+" type="da" date="\d+") offs="\d+"', r'\1', xml)
    open(out_xml, 'w', encoding='utf-8').write(xml)


if __name__ == '__main__':
    main(*sys.argv[1:4])
