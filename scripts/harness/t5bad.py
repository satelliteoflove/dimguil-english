#!/usr/bin/env python3
"""The T5 known-bad set: layout bugs we've already fixed, put back, to measure the checks.

    python3 scripts/harness/t5bad.py [CASE ...] [--out t5/bad]

Each case loads a rig state, sets the code word that fixed the bug either to its fixed
value or back to the old one (a diagnostic RAM write, never used in play), plays the keys
that bring up the screen, and captures it with harness.screens. Both variants are then
checked with t5check. A case is caught when the bad variant gets a finding of the
expected kind on the expected screen and the fixed variant gets none there.

The rig states (rips/states/) are older than the current disc, so code words that matter
are written either way, and the event box cases write their string into the loaded
EVENTMES like scripts/evsweep.py does. Writes rips/harness/<out>/<case>_<variant>/ and
rips/harness/<out>/results.json.
"""
import argparse, json, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'rips', 'probe'))
from harness.game import Game, OUT
from harness.screens import Screens
from harness import t5check

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ST = os.path.join(ROOT, 'rips/states')
# the disc under test's copy (suite_round.sh installs it); rips/dirty is whatever this
# checkout last built, and a stale copy puts the strings at the wrong offsets
EVENTMES = os.path.join(ROOT, 'rips/harness/disc/dimguil/DATA06/EVENTMES.BIN')
if not os.path.exists(EVENTMES):
    EVENTMES = os.path.join(ROOT, 'rips/dirty/dimguil/DATA06/EVENTMES.BIN')
OLD_DISC = os.path.join(ROOT, 'rips/harness/disc/f068468/dimguil-en.cue')
OLD_T2 = os.path.join(ROOT, 'rips/harness/t2/states') + '/'
EV_RAM = 0x801a0400          # where EVENTMES loads; searching the Shrine door prints string 11


def li(rt, imm):
    return 0x34000000 | rt << 16 | imm & 0xffff


def addiu(rt, imm):
    return 0x24000000 | rt << 16 | imm & 0xffff


A0, A1 = 4, 5
SLTIU_V0 = 0x2c420002        # sltiu v0, v0, 2: "is the next glyph a voicing mark"
MOVE_V0 = 0x00001021         # move v0, zero
# the event box code as built (evsweep.patches()), written first in both variants: the
# Shrine door state predates these fixes
EVENT_BOX = [(0x8001ffe8, MOVE_V0), (0x80021bfc, 0x000a2440), (0x800a3134, 0x03e00008),
             (0x800a3138, MOVE_V0)]


def ev_offset(i):
    return struct.unpack_from('<I', open(EVENTMES, 'rb').read(), 4 * i)[0]


def ev_string(i):
    d = open(EVENTMES, 'rb').read()
    n = struct.unpack_from('<I', d, 0)[0] // 4
    o = [struct.unpack_from('<I', d, 4 * k)[0] for k in range(n)] + [len(d)]
    return d[o[i]:o[i + 1]]


def padded(i, n):
    """String i with the Japanese-style padding the old text had: n spaces first."""
    return b'\xba' * n + ev_string(i)


# keys: an e.seq() string per step; 'EVENT' steps print the case's string (see run_case)
CASES = [
    dict(name='event_pool', fix='6dc52dd', state='shrine_door.state', string=lambda: ev_string(11),
         base=EVENT_BOX, words=[(0x80021bfc, 0x000a2440, 0x000a2400)],
         keys=['EVENT'], expect=['cut', 'missing'],
         what='Event box pool back to 72 (rows x columns): at the Shrine door, "Do we need something?" '
              'loses its end (the cut Chris first saw was ".........Sure enough, the")'),
    dict(name='voicing_event', fix='9a955ba', state='shrine_door.state', string=lambda: ev_string(15),
         base=EVENT_BOX, words=[(0x8001ffe8, MOVE_V0, SLTIU_V0)],
         keys=['EVENT'], expect=['japanese', 'missing'],
         what='Event printer merges voicing marks again: "how hard" prints as a voiced kana'),
    dict(name='event_padding', fix='fc8eabc', state='shrine_door.state', string=lambda: padded(34, 3),
         string_fixed=lambda: ev_string(34), base=EVENT_BOX,
         keys=['EVENT'], expect=['center'],
         what='Japanese padding kept on one side (EVENTMES 34 as it was): the line prints off center'),
    dict(name='textbuf_overflow', fix='98aec10 (textbuf.py)', state='shrine_door.state',
         string=lambda: long_string(640), string_fixed=lambda: long_string(640)[:540].rsplit(b'\xff\x20', 1)[0],
         base=EVENT_BOX, keys=['EVENT'], expect=['overflow', 'garbage', 'missing'],
         what='An event string past the 576-byte expand buffer: later pages print what overwrote it'),
    dict(name='training_sign', fix='ec26800', state='training_sign_front.state',
         words=[(0x800bef6c, addiu(A0, 177), addiu(A0, 172))],
         keys=['triangle w700', 'circle w300', 'circle w300'], expect=['cut', 'missing'],
         what='Training maze sign layer back to 172: the text stops at "but as a b"'),
    dict(name='return_icon', fix='3653a07', state='return_prompt.state',
         words=[(0x800bab9c, addiu(A1, -94), addiu(A1, -6))],
         keys=['down w90', 'up w150', 'w60'], expect=['render', 'overlap'],
         what='Return prompt triangle icon back at x -6: drawn over the text'),
    dict(name='shop_caption', fix='f5d4e8f', state='party.state',
         words=[(a, li(r, new), addiu(r, old)) for base in (0x800bb0a0, 0x800bbca4, 0x800c0d78)
                for a, r, new, old in ((base, A0, 240, 270), (base + 4, A1, 58, 28))],
         keys=['cross w180 right w20 right w20 circle w150', 'circle w90', 'circle w90',
               'down w30 down w30 circle w90', 'w60'],
         expect=['cut', 'missing'],
         what="Boltac's Trade caption layer back to 28: \"Choose an item to un\" (Dispel Curse)"),
    dict(name='inn_pool', fix='2a207be', state='party.state',
         words=[(0x800a348c, addiu(A1, 172), addiu(A1, 154))],
         keys=['cross w180 right w20 circle w150', 'circle w90', 'circle w90', 'start w60',
               'down w40', 'down w40', 'down w40', 'down w40', 'down w40'], expect=['cut', 'missing'],
         what="Town map's main layer back to 154: the Inn's room help lines lose their ends"),
    # Not in the set: the status screen's help layer back to 70 (status_text_pool.asm).
    # Its help lines were cut when the command labels took 50 of the 70 ("Spellbook" ...);
    # today's labels are shorter and every help line fits in 70 again, so putting the old
    # size back shows nothing (checked 2026-10-13: layers (346, 70), help lines whole).
    # the old disc f068468 (before 71d14dd and the FIGHTMSG 221 fix): only a bad variant,
    # its states hold that disc's code; the current disc's runs are the clean comparison
    dict(name='old_battle_wrap', fix='71d14dd', disc=OLD_DISC, state=OLD_T2 + 'battle_cmd0.state',
         keys=['FIGHT'], expect=['center', 'lint'], variants=['bad'],
         what='Old disc f068468, a fight: wrapped battle lines with a space left at a line end or start '
              '(fixed in 71d14dd and 8c26893)'),
    dict(name='old_oops', fix='FIGHTMSG 221', disc=OLD_DISC, state=OLD_T2 + 'chest_fresh.state',
         keys=['CHEST_OOPS'], expect=['lint'], variants=['bad'],
         what='Old disc f068468: "Oops! There\'s no trap.!!"'),
]


def print_event(e, scr, text, limit=9000):
    """Search the Shrine door with `text` written over EVENTMES 11 (until it's expanded:
    the file loads after a pause), and press circle on each page once it has settled,
    until the box closes."""
    from harness.screens import read_sprites
    box = lambda: [g for g in read_sprites(e) if g['L'] == 1 and g['y'] < 72]
    at = EV_RAM + ev_offset(11)
    e.press('triangle', after=0)
    f0, shown, idle, last = e.frame_no, False, 0, 0
    while e.frame_no - f0 < limit:
        if e.frame_no - f0 < 600:
            e.write(at, text)
        e.run(1)
        if box():
            shown, idle = True, 0
        elif shown:
            idle += 1
            if idle > 90:
                break
        if shown and scr.hold_c >= 40 and e.frame_no - last >= 60 and box():
            e.press('circle', hold=4, after=0)
            last = e.frame_no


def long_string(n):
    """Event strings joined page after page ({ff20}) to n bytes or more: the expand
    buffer at 0x8008b400 has 576 bytes before live data."""
    out, i = b'', 0
    while len(out) < n:
        body = ev_string(i)
        body = body[:-2] if body.endswith(b'\xff\x40') else body
        if len(body) > 20:
            out += (b'\xff\x20' if out else b'') + body
        i += 1
    return out


def run_case(c, variant, out):
    """variant 'bad' or 'fixed'. Returns the capture dir (relative to rips/harness)."""
    import fixstate
    d = os.path.join(out, '%s_%s' % (c['name'], variant))
    full = os.path.join(OUT, d)
    if os.path.exists(os.path.join(full, 'screens.jsonl')):
        os.remove(os.path.join(full, 'screens.jsonl'))
    g = Game(capture=True, **({'disc': c['disc']} if c.get('disc') else {}))
    s = Screens(g, d)
    e = g.e
    g.load(os.path.join(ST, c['state']))
    if not c.get('disc'):
        fixstate.fix(e)              # the rig states' file tables, to the current disc
    e.run(2)
    wrote = []
    for a, v in c.get('base', []):
        e.write(a, struct.pack('<I', v))
    for a, new, old in c.get('words', []):
        have = e.u32(a)
        if have not in (new, old):
            raise SystemExit('%s: word at %08x is %08x, neither fixed %08x nor old %08x'
                             % (c['name'], a, have, new, old))
        e.write(a, struct.pack('<I', new if variant == 'fixed' else old))
        wrote.append('%08x=%08x' % (a, new if variant == 'fixed' else old))
    text = None
    if 'string' in c:
        f = c.get('string_fixed') if variant == 'fixed' else None
        text = (f or c['string'])()
        body = text[:-2] if text.endswith(b'\xff\x40') else text
        if not body.endswith(b'\xff\x26'):
            body += b'\xff\x26'
        text = body + b'\xff\x40'
    for k in c['keys']:
        s.keys.clear()               # a fresh shot per step: the screen may look the same
        if k == 'FIGHT':
            from harness.battle import fight
            fight(g)
        elif k == 'CHEST_OOPS':
            # inspect the chest with Ace, waiting a little longer each time, until a
            # failed inspection sets it off ("Oops! ...")
            from harness.battle import chest
            for wait in range(0, 400, 7):
                g.load(os.path.join(ST, c['state']))
                e.run(1 + wait)
                if chest(g, 'inspect', who=0) == 'oops':
                    e.run(120)
                    break
        elif k == 'EVENT':
            print_event(e, s, text)
        else:
            e.seq(k)
    e.run(30)
    s.close()
    return d, wrote


def judge(c, findings_bad, findings_fixed):
    """Caught: the bad variant has a finding of an expected kind that the fixed variant
    doesn't have (same check and text), so a finding the two share (a real issue on the
    same screen, like a centering one) doesn't count."""
    sig = lambda f: (f['check'], f.get('detail'))
    fixed = {sig(f) for f in findings_fixed}
    hit = [f for f in findings_bad if f['check'] in c['expect'] and sig(f) not in fixed]
    return dict(caught=bool(hit), bad_findings=len(findings_bad), fixed_findings=len(findings_fixed),
                bad_checks=sorted({f['check'] for f in findings_bad}),
                fixed_checks=sorted({f['check'] for f in findings_fixed}),
                hits=[f['check'] + ': ' + f['what'] + ' | ' + str(f.get('detail'))[:60] for f in hit][:4])


def ratchet(name, out='regress/screen'):
    """One known-bad case as a regression case (kind 'screen' in the suite): both
    variants captured and checked; passes when the bad one is caught."""
    c = next(x for x in CASES if x['name'] == name)
    found = {}
    for v in c.get('variants', ('bad', 'fixed')):
        d, _ = run_case(c, v, out)
        fp = os.path.join(OUT, d, 'findings.jsonl')
        t5check.run([d], fp)
        found[v] = [json.loads(l) for l in open(fp)]
    r = judge(c, found['bad'], found.get('fixed', []))
    return dict(result=r['caught'], **{k: v for k, v in r.items() if k != 'caught'})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cases', nargs='*')
    ap.add_argument('--out', default='t5/bad')
    ap.add_argument('--recheck', action='store_true', help='check the existing captures again')
    a = ap.parse_args()
    todo = [c for c in CASES if not a.cases or c['name'] in a.cases]
    results = {}
    rp = os.path.join(OUT, a.out, 'results.json')
    if os.path.exists(rp):
        results = json.load(open(rp))
    for c in todo:
        t0 = time.time()
        found = {}
        for v in c.get('variants', ('bad', 'fixed')):
            if a.recheck:
                d = os.path.join(a.out, '%s_%s' % (c['name'], v))
                if not os.path.exists(os.path.join(OUT, d, 'screens.jsonl')):
                    continue
            else:
                d, wrote = run_case(c, v, a.out)
            fp = os.path.join(OUT, d, 'findings.jsonl')
            t5check.run([d], fp)
            found[v] = [json.loads(l) for l in open(fp)]
        if 'bad' not in found:
            continue
        r = judge(c, found['bad'], found.get('fixed', []))
        if 'fixed' not in found:
            r['fixed_findings'] = None
            r['fixed_checks'] = ['(no fixed variant)']
        r.update(what=c['what'], fix=c['fix'], expect=c['expect'], secs=round(time.time() - t0, 1))
        results[c['name']] = r
        print(c['name'], r, flush=True)
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    json.dump(results, open(rp, 'w'), indent=1)


if __name__ == '__main__':
    main()
