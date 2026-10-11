#!/usr/bin/env python3
"""List where our asm/ patches change the game's code, by module and function.

    patchsites.py            table of every .org in asm/*.asm, with the function it lands in
    patchsites.py --md       the same as a markdown table (for docs/code-map.md)

Analysis reads the original disc (rips/clean/dimguil), so the decompiled C shows the
game's own code. Where a patch site falls in a function, the patched build behaves
differently there; read the .asm file named before trusting the C for that spot.
Needs rips/re/decomp/*/index.json (scripts/re/ghidra.py build).
"""
import glob, json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODS = {'SLPS_026.91': 'MAIN', 'MAZE.BIN': 'MAZE', 'BATTLE.BIN': 'BATTLE', 'MCARD.BIN': 'MCARD',
        'JOUKA.BIN': 'JOUKA', 'HAZURE.BIN': 'HAZURE', 'CMAIN.BIN': 'CMAIN', 'CMENU.BIN': 'CMENU'}


def functions():
    out = {}
    for mod in set(MODS.values()):
        p = os.path.join(ROOT, 'rips/re/decomp', mod, 'index.json')
        if os.path.exists(p):
            out[mod] = [(int(f['addr'], 16), int(f['end'], 16), f['name'])
                        for f in json.load(open(p))['functions']]
    return out


def sites():
    """(asm file, module, address) for each .org and each macro call that names a file
    and an address (config_names "dirty/dimguil/MAZE.BIN", 0x800a1cbc)."""
    found = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'asm/*.asm'))):
        mod = None
        for line in open(path, encoding='utf-8'):
            code = line.split(';')[0]
            m = re.search(r'\.open\s+(?:"[^"]*",\s*)?"[^"]*/([A-Z_0-9.]+)"', code)
            if m:
                mod = MODS.get(m.group(1)); continue
            m = re.search(r'"[^"]*/([A-Z_0-9.]+)"\s*,\s*(0x[0-9a-fA-F]{8})', code)
            if m and not code.strip().startswith('.open'):
                found.append((os.path.basename(path), MODS.get(m.group(1)), int(m.group(2), 16))); continue
            m = re.match(r'\s*\.?org\s+(0x[0-9a-fA-F]{8})', code)
            if m and mod:
                found.append((os.path.basename(path), mod, int(m.group(1), 16)))
    return found


def main():
    funcs = functions()
    rows = []
    for asm, mod, a in sites():
        name = ''
        for lo, hi, n in funcs.get(mod, []):
            if lo <= a <= hi:
                name = n + (f'+0x{a - lo:x}' if a != lo else ''); break
        rows.append((mod, a, name or '(data or outside a function)', asm))
    rows.sort()
    if '--md' in sys.argv:
        print('| Module | Address | Function | Patch |\n|---|---|---|---|')
        for mod, a, n, asm in rows:
            print(f'| {mod} | 0x{a:08x} | {n} | asm/{asm} |')
    else:
        for mod, a, n, asm in rows:
            print(f'{mod:7s} 0x{a:08x}  {n:40s} asm/{asm}')


if __name__ == '__main__':
    main()
