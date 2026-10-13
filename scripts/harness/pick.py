"""Choose which enemy group a battle command is aimed at, checked against RAM.

    from pick import pick_group, pick_screen
    if pick_screen(e):                 # the game is waiting at an enemy group pick
        r = pick_group(e, 3)           # aim at group 3, confirm, verify
        # r = dict(target=3, mode='list', member=0, screen=17, ...)

`e` is either scripts/emu.py's Emu or the harness's Game (anything with .tap/.step and
.e is driven through those, so the text capture keeps ticking). Nothing waits a fixed
number of frames: each press is retried until the cursor byte changes, and the confirm
until the member's command record shows the target. Raises PickError when the group
can't be chosen from this screen (out of the weapon's reach, gone, no pick showing).

The mechanism (BATTLE 0x800cbec8 party_commands, 0x800cf0dc group_pick and the two
pickers it calls; see README.md here and docs/engine-notes.md):

  SCREEN 0x800796e0: 0x11 Fight, 0x34 spell, 0x54 item, 0x41 Dispel, 0x71 Ambush,
                     0x91 Breath (all the same picker)
  0x80079bde        0 random encounter: a vertical list, cursor LIST 0x80079b95,
                    group = LIST + 1, LIST 0..max (wraps)
                    1 fixed battle: a 3x2 grid, cursor col 0x800da800 / row 0x800da801,
                    grid position p = col + 3*row + 1 holds entry 0x80079c28[p]; group g
                    is entry 0x80079c50[g]; group spells pick a row instead
  combatant +0xb    (0x8008e23b + member*0xe) the target the confirm writes
"""
import struct

SCREEN = 0x800796e0
MEMBER = 0x80079786
FIXED = 0x80079bde          # 1 in a fixed battle (the grid), 0 in a random one (the list)
NGROUPS = 0x800798b8        # groups standing
FRONT = 0x800796d3          # fixed battle: groups in the front row (s8)
BACK = 0x8007967c           # fixed battle: groups in the back row (s8)
NFRONT = 0x8007989d         # groups a short weapon reaches (fixed: the front row; random: 2)
REACH = 0x800da7fb          # this member's weapon reach (weapon_reach), set at the command list
FIGHT_MAX = 0x800da7fc      # last list index for Fight/Dispel/Ambush/Breath
LIST = 0x80079b95           # list cursor
COL, ROW = 0x800da800, 0x800da801
POS_ENTRY = 0x80079c28      # [1..6]: grid position -> fixed-battle entry (0xff empty)
GROUP_ENTRY = 0x80079c50    # [1..6]: group -> entry (0xff gone)
SPELL_FLAGS = 0x800da804    # u16; 0x40 a group spell (in a fixed battle it takes a row)
COMBAT = 0x8008e230
PICKS = {0x11: 'fight', 0x34: 'spell', 0x54: 'item', 0x41: 'dispel', 0x71: 'ambush',
         0x91: 'breath'}
SPELLISH = (0x34, 0x54, 0x91, 0x41, 0x71)   # screens whose grid may go to the back row
RETRY = 8


class PickError(Exception):
    pass


class _Drive:
    """Taps and frames through a Game (g.tap/g.step) or a bare Emu (e.run)."""
    def __init__(self, x):
        self.x = x
        self.emu = x.e if hasattr(x, 'tap') and hasattr(x, 'e') else x

    def u8(self, a):
        return self.emu.read(a, 1)[0]

    def s8(self, a):
        return struct.unpack('<b', self.emu.read(a, 1))[0]

    def step(self, n=1):
        if hasattr(self.x, 'step'):
            self.x.step(n)
        else:
            self.emu.run(n)

    def tap(self, btn, hold=2):
        if hasattr(self.x, 'tap'):
            self.x.tap(btn, hold=hold)
        else:
            self.emu.run(hold, (btn,))

    def press_until(self, btn, cond, limit=120):
        n = 0
        while n < limit:
            if cond():
                return True
            self.tap(btn)
            n += 2
            for _ in range(RETRY):
                if cond():
                    return True
                self.step()
                n += 1
        return cond()


def pick_screen(e):
    """The pick screen showing now (0x11, 0x34 ...), or None."""
    s = _Drive(e).u8(SCREEN)
    return s if s in PICKS else None


def _target_addr(m):
    return COMBAT + m * 0xe + 0xb


def layout(e):
    """What the pick offers now: dict(mode 'list' | 'grid' | 'rows', screen, member,
    choices {group: cursor position}). List: position = LIST index. Grid: (col, row).
    Rows: (row, value written to +0xb)."""
    d = e if isinstance(e, _Drive) else _Drive(e)
    scr = d.u8(SCREEN)
    if scr not in PICKS:
        raise PickError('no group pick on screen (screen %d)' % scr)
    m = d.u8(MEMBER)
    ng = d.u8(NGROUPS)
    out = dict(screen=scr, member=m, groups=ng, kind=PICKS[scr])
    if d.u8(FIXED) == 0:
        mx = ng - 1 if scr in (0x34, 0x54) else d.s8(FIGHT_MAX)
        out.update(mode='list', max=mx, choices={g: g - 1 for g in range(1, mx + 2)})
        return out
    rows = False
    if scr in (0x34, 0x54):
        rows = bool(struct.unpack('<H', d.emu.read(SPELL_FLAGS, 2))[0] & 0x40)
    elif scr == 0x91:
        rows = struct.unpack('<h', d.emu.read(COMBAT + m * 0xe, 2))[0] > 8
    entries = d.emu.read(POS_ENTRY, 7)
    gent = d.emu.read(GROUP_ENTRY, 8)
    front, back = d.s8(FRONT), d.s8(BACK)
    if rows:
        # a group spell in a fixed battle hits a whole row (spell_group_range): the top
        # row is target 1, the bottom one target 2 (only while both rows stand)
        ch = {}
        for g in range(1, ng + 1):
            if front > 0 and back >= 1 and g > front:
                ch[g] = (1, 2)
            else:
                ch[g] = (0, 1)
        out.update(mode='rows', choices=ch, front=front, back=back)
        return out
    last = 6 if (scr in SPELLISH or d.u8(NFRONT) < d.s8(REACH)) else 3
    ch = {}
    for g in range(1, ng + 1):
        ent = gent[g]
        if ent == 0xff:
            continue
        for p in range(1, last + 1):
            if entries[p] == ent:
                ch[g] = ((p - 1) % 3, (p - 1) // 3)
    out.update(mode='grid', choices=ch, last=last, front=front, back=back)
    return out


def pick_group(e, want, limit=600, before_confirm=None):
    """Move the pick cursor to group `want` (1-based, battle_groups order), confirm, and
    check the member's command record. Returns the layout dict plus target (the byte
    written to +0xb: the group, or in a fixed battle's group-spell pick the row 1/2).
    before_confirm(layout) runs with the cursor in place, before the confirm (a shot)."""
    d = _Drive(e)
    lay = layout(d)
    m, scr = lay['member'], lay['screen']
    if lay['groups'] == 1:
        # one group: the pick takes it by itself (group_pick's first branch). Fight never
        # shows screen 0x11; a spell or item shows 0x34/0x54 for a frame. A press now
        # would land on the next screen, so wait it out and check the record.
        for _ in range(4):
            if d.u8(SCREEN) != scr:
                break
            d.step()
        if d.u8(SCREEN) != scr:
            if want != 1 or d.u8(_target_addr(m)) != 1:
                raise PickError('one group: target %d, wanted %d' % (d.u8(_target_addr(m)), want))
            lay.update(target=1, auto=True)
            return lay
    if want not in lay['choices']:
        raise PickError('group %d not offered on screen %#x (%s; offers %s)'
                        % (want, scr, lay['mode'], sorted(lay['choices'])))
    pos = lay['choices'][want]
    on = lambda: d.u8(SCREEN) == scr
    if lay['mode'] == 'list':
        n = lay['max'] + 1
        while d.s8(LIST) != pos:
            cur = d.s8(LIST)
            fwd = (pos - cur) % n
            btn = 'down' if fwd <= n - fwd else 'up'
            if not d.press_until(btn, lambda: d.s8(LIST) != cur or not on(), limit) or not on():
                raise PickError('list cursor stuck at %d' % cur)
        expect = want
    else:
        tcol, trow = (None, pos[0]) if lay['mode'] == 'rows' else pos
        tries = 0
        at = lambda: d.s8(ROW) == trow and (tcol is None or d.s8(COL) == tcol)
        while not at():
            tries += 1
            if tries > 8:
                raise PickError('grid cursor stuck at col %d row %d' % (d.s8(COL), d.s8(ROW)))
            cur = (d.s8(COL), d.s8(ROW))
            if d.s8(ROW) != trow:
                btn = 'down' if trow > d.s8(ROW) else 'up'
            else:
                btn = 'right' if (tcol - cur[0]) % 3 == 1 else 'left'
            if not d.press_until(btn, lambda: (d.s8(COL), d.s8(ROW)) != cur or not on(), limit) \
                    or not on():
                raise PickError('grid cursor won\'t move %s from %s' % (btn, cur))
        expect = want if lay['mode'] == 'grid' else pos[1]
    if before_confirm:
        before_confirm(lay)
    # confirm: the routine writes +0xb and leaves the screen in the same frame
    if not d.press_until('circle', lambda: not on(), limit):
        raise PickError('confirm not taken')
    got = d.u8(_target_addr(m))
    if got != expect:
        raise PickError('member %d target %d, wanted %d' % (m, got, expect))
    lay['target'] = got
    return lay
