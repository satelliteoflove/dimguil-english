#!/usr/bin/env python3
"""Drive headless Ghidra over Dimguil's code. See docs/code-map.md for the whole picture.

    ghidra.py build [MOD ...] [-j N]   import, map the overlay, analyze, clean, label, apply
                                       symbols, export (all modules if none given; ~3 min each)
    ghidra.py refresh MOD ...          apply symbols and re-export (fast; use after editing CSVs)
    ghidra.py check                    validate scripts/re/symbols/*.csv
    ghidra.py merge                    rebuild rips/re/xref.json and rips/re/globals.json
    ghidra.py where ADDR               which modules have a function at or around ADDR

Modules: MAIN (the executable, SLPS_026.91) and the overlays, which all load at 0x800a1000:
MAZE, BATTLE, MCARD, JOUKA, HAZURE, CMAIN, CMENU. Each module is its own Ghidra project,
rips/re/ghidra/<MOD>/, holding the executable with that overlay mapped, so calls between
them resolve. Runs on one module take a lock (rips/re/locks/<MOD>.lock), so agents working
in parallel on different modules don't wait on each other, and two on the same module take
turns.

Symbols live in scripts/re/symbols/*.csv, one file per subsystem or analyst, merged at apply
time. Columns: module,address,name,kind,confidence,source,note,type
  module      MAIN (executable code, applied to every program), RAM (data outside any
              overlay: .data, .bss, heap; applied to every program), or an overlay name
              (applied to that overlay's program only; overlays share addresses)
  kind        function | label (code location inside a function) | global | table |
              field (a record offset like roster+0x7a; documentation only, not applied)
  confidence  confirmed | inferred
  source      how it was learned (code read, RAM watch, emulator test, doc, commit)
  type        optional, for global/table rows: a struct from scripts/re/types.h or u8, u16,
              u32, s8, s16, s32, with [N] for an array (Roster[20])
Output: rips/re/decomp/<MOD>/<addr>_<name>.c and index.json.
"""
import csv, fcntl, glob, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DISC = os.path.join(ROOT, 'rips/q7iso/dimguil')        # the original disc's files
RE = os.path.join(ROOT, 'rips/re')
SYMS = os.path.join(ROOT, 'scripts/re/symbols')
SCRIPTS = os.path.join(ROOT, 'scripts/re/ghidra_scripts')
GHIDRA = os.path.expanduser('~/tools/ghidra/ghidra_12.1.4_PUBLIC/support/analyzeHeadless')
JDK = os.path.expanduser('~/tools/jdk/jdk-21.0.12.1+1')
MODULES = ['MAIN', 'MAZE', 'BATTLE', 'MCARD', 'JOUKA', 'HAZURE', 'CMAIN', 'CMENU']
OVERLAY_BASE = 0x800a1000
MAIN_GAME_END = 0x80024bf0   # executable game code ends here; PsyQ library code follows
# A smaller overlay leaves the previous one's tail in RAM, and these call into it (checked
# in RAM dumps: battles run over MAZE, Edge of Town over the castle town).
UNDERLAY = {'BATTLE': 'MAZE', 'HAZURE': 'JOUKA'}
PROGRAM = 'SLPS_026.91'
FIELDS = ['module', 'address', 'name', 'kind', 'confidence', 'source', 'note']   # + optional type
TYPES = os.path.join(ROOT, 'scripts/re/types.h')
KINDS = {'function', 'label', 'global', 'table', 'field'}


def env():
    e = dict(os.environ)
    e['JAVA_HOME'] = JDK
    e['PATH'] = os.path.join(JDK, 'bin') + ':' + e['PATH']
    e.setdefault('GHIDRA_HEADLESS_MAXMEM', '3G')
    return e


def overlay_end(mod):
    return OVERLAY_BASE + os.path.getsize(os.path.join(DISC, mod + '.BIN'))


def load_symbols():
    rows = []
    for path in sorted(glob.glob(os.path.join(SYMS, '*.csv'))):
        with open(path, encoding='utf-8', newline='') as f:
            for i, r in enumerate(csv.DictReader(f), 2):
                r['_file'] = f'{os.path.basename(path)}:{i}'
                rows.append(r)
    return rows


def check(quiet=False):
    """Format errors, and the same address named differently in one module."""
    rows, problems, seen = load_symbols(), [], {}
    for r in rows:
        where = r['_file']
        if None in r or any(r.get(k) is None for k in FIELDS):
            problems.append(f'{where}: wrong number of columns'); continue
        mod = r['module']
        if mod not in MODULES + ['RAM']:
            problems.append(f'{where}: unknown module {mod}')
        if r['kind'] not in KINDS:
            problems.append(f'{where}: unknown kind {r["kind"]}')
        if r['confidence'] not in ('confirmed', 'inferred'):
            problems.append(f'{where}: confidence must be confirmed or inferred')
        if r['kind'] == 'field':
            continue
        try:
            a = int(r['address'], 16)
        except ValueError:
            problems.append(f'{where}: bad address {r["address"]}'); continue
        if not r['name'].replace('_', '').isalnum() or r['name'][0].isdigit():
            problems.append(f'{where}: name must be an identifier: {r["name"]}')
        if mod in MODULES[1:] and not OVERLAY_BASE <= a < overlay_end(mod):
            problems.append(f'{where}: {r["address"]} is outside {mod}')
        if mod == 'MAIN' and not 0x80010000 <= a < 0x80079c88:
            problems.append(f'{where}: {r["address"]} is outside the executable; use RAM for data')
        key = (mod, a)
        if key in seen and seen[key]['name'] != r['name']:
            problems.append(f'{where}: {r["address"]} is {r["name"]} here but {seen[key]["name"]} '
                            f'in {seen[key]["_file"]}')
        seen.setdefault(key, r)
    if not quiet:
        print('\n'.join(problems) or f'{len(rows)} symbols, no problems')
    return problems


def tsv_for(mod):
    """Rows that apply to MOD's program, as address<TAB>name<TAB>kind<TAB>comment."""
    lines = []
    for r in load_symbols():
        if r['kind'] == 'field' or r['module'] not in (mod, 'MAIN', 'RAM'):
            continue
        note = ' '.join(x for x in (f'[{r["confidence"]}]', r['note'],
                                    f'({r["source"]})' if r['source'] else '') if x)
        note = note.replace('\t', ' ').replace('\n', '\\n')
        lines.append(f'{int(r["address"], 16):08x}\t{r["name"]}\t{r["kind"]}\t{note}\t{r.get("type") or ""}')
    path = os.path.join(RE, mod, 'symbols.tsv')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    return path


def headless(mod, args, log):
    os.makedirs(os.path.join(RE, 'locks'), exist_ok=True)
    os.makedirs(os.path.join(RE, 'logs'), exist_ok=True)
    proj = os.path.join(RE, 'ghidra', mod)
    os.makedirs(proj, exist_ok=True)
    with open(os.path.join(RE, 'locks', mod + '.lock'), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        t = time.time()
        with open(os.path.join(RE, 'logs', log), 'w') as out:
            rc = subprocess.call([GHIDRA, proj, 'dimguil_' + mod] + args, stdout=out,
                                 stderr=subprocess.STDOUT, env=env())
        took = time.time() - t
        # read the log while holding the lock: the next run on this module overwrites it
        text = open(os.path.join(RE, 'logs', log), encoding='utf-8', errors='replace').read().split('\n')
    lines = [l.split('> ', 1)[1].split(' (GhidraScript)')[0] for l in text if '.java> ' in l]
    errors = sum(1 for l in text if 'SCRIPT ERROR' in l)
    if errors and rc == 0:
        rc = 1   # headless Ghidra exits 0 even when a script throws
    status = 'ok' if rc == 0 else f'FAILED (exit {rc}, {errors} script errors; see rips/re/logs/{log})'
    print(f'{mod}: {status} in {took:.0f}s; ' + '; '.join(lines), flush=True)
    return rc


def post_args(mod):
    out = os.path.join(RE, 'decomp', mod)
    lib = os.path.join(RE, mod, 'library.csv')
    clean = ['-postScript', 'CleanOverlay.java', mod] if mod != 'MAIN' else []
    return ['-postScript', 'ApplySymbols.java', tsv_for(mod), TYPES] + clean + [
            '-postScript', 'ExportModule.java', out, mod, lib, hex(MAIN_GAME_END)]


def build(mod):
    os.makedirs(os.path.join(RE, mod), exist_ok=True)
    args = ['-import', os.path.join(DISC, PROGRAM), '-overwrite', '-scriptPath', SCRIPTS,
            '-analysisTimeoutPerFile', '1800']
    if mod == 'MAIN':
        args += ['-postScript', 'SeedOrphans.java', '0x800114d8', hex(MAIN_GAME_END)] + \
                [os.path.join(DISC, m + '.BIN') for m in MODULES[1:]]
    else:
        under = [os.path.join(DISC, UNDERLAY[mod] + '.BIN'), UNDERLAY[mod]] if mod in UNDERLAY else []
        args += ['-postScript', 'LoadOverlay.java', os.path.join(DISC, mod + '.BIN'), mod] + under + [
                 # MAIN's routines that only overlays call, so every program has the same
                 # MAIN functions (and ApplySymbols never has to disassemble MAIN code)
                 '-postScript', 'SeedOrphans.java', '0x800114d8', hex(MAIN_GAME_END)] + \
                [os.path.join(DISC, m + '.BIN') for m in MODULES[1:]] + [
                 '-postScript', 'CleanOverlay.java', mod,
                 '-postScript', 'SeedOrphans.java', hex(OVERLAY_BASE), hex(overlay_end(mod)),
                 '-postScript', 'CleanOverlay.java', mod]
    args += ['-postScript', 'RecordLibrary.java', os.path.join(RE, mod, 'library.csv'), hex(MAIN_GAME_END)]
    return headless(mod, args + post_args(mod), f'build_{mod}.log')


def refresh(mod):
    args = ['-process', PROGRAM, '-noanalysis', '-scriptPath', SCRIPTS] + post_args(mod)
    return headless(mod, args, f'refresh_{mod}.log')


def merge():
    """Cross-module call and global maps. A MAIN function's callers include overlay
    functions (inverted from their callees); every function is keyed MOD:addr."""
    names = {(r['module'], r['address'].lower().replace('0x', '').zfill(8)): r['name']
             for r in load_symbols() if r['kind'] != 'field'}
    funcs, globals_ = {}, {}
    for mod in MODULES:
        p = os.path.join(RE, 'decomp', mod, 'index.json')
        if not os.path.exists(p):
            continue
        for f in json.load(open(p))['functions']:
            funcs[f'{mod}:{f["addr"]}'] = dict(f, module=mod, callers=[
                ('MAIN' if int(c, 16) < OVERLAY_BASE else mod) + ':' + c for c in f['callers']])
    main = {k.split(':')[1]: k for k in funcs if k.startswith('MAIN:')}
    for key, f in funcs.items():
        mod = f['module']
        for c in f['callees']:
            if mod != 'MAIN' and c in main and int(c, 16) < OVERLAY_BASE:
                funcs[main[c]]['callers'].append(key)
            elif mod in UNDERLAY and int(c, 16) >= overlay_end(mod) and f'{UNDERLAY[mod]}:{c}' in funcs:
                funcs[f'{UNDERLAY[mod]}:{c}']['callers'].append(key)
        for kind in ('reads', 'writes'):
            for g in f[kind]:
                a = int(g, 16)
                gmod = mod if mod != 'MAIN' and OVERLAY_BASE <= a < overlay_end(mod) else 'RAM'
                if gmod == 'RAM' and 0x80010000 <= a < 0x80079c88 and funcs.get(f'MAIN:{g}'):
                    continue
                e = globals_.setdefault(f'{gmod}:{g}', {
                    'name': names.get((gmod, g)) or names.get(('MAIN', g)) or '', 'readers': [], 'writers': []})
                e['readers' if kind == 'reads' else 'writers'].append(key)
    for f in funcs.values():
        f['callers'] = sorted(set(f['callers']))
    json.dump(funcs, open(os.path.join(RE, 'xref.json'), 'w'), indent=0)
    json.dump(dict(sorted(globals_.items())), open(os.path.join(RE, 'globals.json'), 'w'), indent=0)
    print(f'xref.json: {len(funcs)} functions; globals.json: {len(globals_)} globals')


def where(addr):
    a = int(addr, 16)
    for mod in MODULES:
        p = os.path.join(RE, 'decomp', mod, 'index.json')
        if not os.path.exists(p):
            continue
        for f in json.load(open(p))['functions']:
            if int(f['addr'], 16) <= a <= int(f['end'], 16):
                off = f' +0x{a - int(f["addr"], 16):x}' if a != int(f['addr'], 16) else ''
                print(f'{mod}: {f["name"]}{off}  rips/re/decomp/{mod}/{f["addr"]}_{f["name"]}.c')


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return 1
    cmd, rest = args[0], args[1:]
    jobs = 4
    if '-j' in rest:
        k = rest.index('-j'); jobs = int(rest[k + 1]); del rest[k:k + 2]
    mods = [m.upper() for m in rest] or MODULES
    for m in mods:
        if cmd in ('build', 'refresh') and m not in MODULES:
            print('unknown module', m); return 1
    if cmd in ('build', 'refresh'):
        if check(quiet=True):
            print('symbol problems; run ghidra.py check'); return 1
        fn = build if cmd == 'build' else refresh
        with ThreadPoolExecutor(jobs) as ex:
            rcs = list(ex.map(fn, mods))
        merge()
        return max(rcs)
    if cmd == 'check':
        return 1 if check() else 0
    if cmd == 'merge':
        merge(); return 0
    if cmd == 'where':
        where(rest[0]); return 0
    print(__doc__); return 1


if __name__ == '__main__':
    sys.exit(main())
