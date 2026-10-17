#!/usr/bin/env python3
# texttool.py: dump the Japanese script, encode the translations and apply byte patches.
#
# This is a Python port of Remisse's dimguil-patcher (https://github.com/remii7/dimguil-patcher),
# the Kotlin tool this project was built on. The port keeps its behaviour byte for byte,
# including its quirks, so a build with it gives the same disc as the Kotlin tool did.
#
# Copyright (C) Remisse (dimguil-patcher), and the contributors to this port.
#
# This program is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this
# program (LICENSE in the repository root). If not, see <https://www.gnu.org/licenses/>.
"""Dump, encode and patch the game's text. Run from the staging directory (build.sh uses
rips/stage), which holds tables/, sections.json, binary/, translations/ and rips/.

    texttool.py dump                       JP script -> out/dumps/<file>.json
    texttool.py encode-all                 translations/*.json + binary/*.json, applied
                                           to rips/clean/dimguil -> rips/dirty/dimguil
    texttool.py encode-string [-compress] TEXT
                                           print one string's bytes as hex

Text format: characters go through tables/dimguil_enc.tbl (a newline is the table's \\n
entry); {name} is a control code from tables/codes.tbl and {hex} is raw bytes. With
compression on, two-letter pairs inside a word become the codes in
tables/compression.tbl. Each string ends in {ff40} unless addStringTerminator is false.

A section is a run of u16 offsets (each padded to 4 bytes with zeros) from the section's
first header, then the strings. Encoding rewrites each section's strings one after
another from firstHeader and points the offsets at them. A file whose sections outgrow
their room by more than its extendByBytes is left untranslated, with an [ERROR] line.
"""
import json, os, re, sys

BINARY_PATCHES_PATH = 'binary'
TRANSLATIONS_PATH = 'translations'
TEXT_DUMPS_PATH = os.path.join('out', 'dumps')
CLEAN_DUMP_PATH = os.path.join('rips', 'clean', 'dimguil')
DIRTY_DUMP_PATH = os.path.join('rips', 'dirty', 'dimguil')
SECTIONS_FILE_PATH = 'sections.json'
DECODING_TABLE_PATH = os.path.join('tables', 'dimguil_dec.tbl')
ENCODING_TABLE_PATH = os.path.join('tables', 'dimguil_enc.tbl')
CODES_TABLE_PATH = os.path.join('tables', 'codes.tbl')
DIGRAPH_TABLE_PATH = os.path.join('tables', 'compression.tbl')

TERMINATOR = b'\xff\x40'
NO_LENGTH = 2 ** 64 - 1
U32, U64 = 2 ** 32 - 1, 2 ** 64 - 1


def s32(n):
    """An int wrapped to a signed 32-bit value (Kotlin's Int)."""
    n &= U32
    return n - 2 ** 32 if n >= 2 ** 31 else n


def info(s):
    print(s)


def warn(s):
    print(f'[WARNING] {s}')


def err(s):
    print(f'[ERROR] {s}')


# ---- input files

def hex_int(s, digits):
    """Strict hex (no prefix, sign or spaces), as Kotlin's hexToUInt/hexToULong/hexToByte."""
    if not re.fullmatch(r'[0-9a-fA-F]{1,%d}' % digits, s):
        raise ValueError(f'invalid hex number: {s!r}')
    return int(s, 16)


def table_pairs(path, delimiter='='):
    """Non-empty lines split once at the delimiter; lines without one are skipped."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, encoding='utf-8', newline='') as f:
        lines = re.split(r'\r\n|\r|\n', f.read())
    return [p for p in (l.split(delimiter, 1) for l in lines if l) if len(p) == 2]


def parse_table(path):
    """code -> text (decoding). A repeated code is an error; the last one is kept."""
    table = {}
    for k, v in table_pairs(path):
        c = hex_int(k, 8)
        if c in table:
            err(f"Code point '{c:x}' has been defined multiple times.")
        table[c] = v
    return table


def parse_table_inverse(path):
    """text -> code (encoding). A repeated text keeps its first code, with a warning."""
    table = {}
    for k, v in table_pairs(path):
        c = hex_int(k, 8)
        if v in table:
            warn(f"Character '{v}' has been defined multiple times. "
                 f"Keeping first encoding ({table[v]:x}).")
        else:
            table[v] = c
    return table


def read_name_table(path, what):
    """name=value table (control codes, digraphs); repeated names or values are errors."""
    pairs = table_pairs(path)
    out = {}
    for k, v in pairs:
        out[k] = v
    for k, v in out.items():
        if sum(p[0] == k for p in pairs) > 1:
            err(f"{what}: sequence '{k}' is associated to multiple encodings.")
        if sum(p[1] == v for p in pairs) > 1:
            err(f"{what}: encoding '{v}' is associated to multiple sequences.")
    return out


_JSON_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)


def load_json(path):
    """json.load that allows // and /* */ comments, as the Kotlin tool did."""
    with open(path, encoding='utf-8') as f:
        src = f.read()
    return json.loads(_JSON_TOKEN.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else '', src))


def fields(obj, what, required, optional):
    """Check an object's keys: unknown keys and missing required ones are errors."""
    if not isinstance(obj, dict):
        raise ValueError(f'{what}: expected an object')
    unknown = set(obj) - set(required) - set(optional)
    if unknown:
        raise ValueError(f'{what}: unknown key(s) {sorted(unknown)}')
    missing = [k for k in required if k not in obj]
    if missing:
        raise ValueError(f'{what}: missing key(s) {missing}')
    out = {k: obj[k] for k in required}
    for k, default in optional.items():
        out[k] = obj.get(k, default)
    return out


def uint(v, what, bits):
    if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < 2 ** bits:
        raise ValueError(f'{what}: expected an unsigned {bits}-bit number, got {v!r}')
    return v


def opt_bool(v, what):
    if v is not None and not isinstance(v, bool):
        raise ValueError(f'{what}: expected true, false or null, got {v!r}')
    return v


def read_unit(path):
    """A translation file: {file, extendByBytes?, sections: [{firstHeaderAddress,
    firstHeader, sectionLength, compress?, strings: [{length, source, translation?,
    compress?, addStringTerminator?}]}]}."""
    u = fields(load_json(path), path, ['file', 'sections'], {'extendByBytes': None})
    if not isinstance(u['file'], str):
        raise ValueError(f'{path}: file must be a string')
    if u['extendByBytes'] is not None and (not isinstance(u['extendByBytes'], int)
                                           or isinstance(u['extendByBytes'], bool)
                                           or not -2 ** 31 <= u['extendByBytes'] < 2 ** 31):
        raise ValueError(f'{path}: extendByBytes must be a 32-bit number')
    sections = []
    for n, s in enumerate(u['sections']):
        w = f'{path} section {n}'
        s = fields(s, w, ['firstHeaderAddress', 'firstHeader', 'sectionLength', 'strings'],
                   {'compress': False})
        uint(s['firstHeaderAddress'], w + ' firstHeaderAddress', 64)
        uint(s['firstHeader'], w + ' firstHeader', 16)
        uint(s['sectionLength'], w + ' sectionLength', 32)
        opt_bool(s['compress'], w + ' compress')
        strings = []
        for m, t in enumerate(s['strings']):
            ws = f'{w} string {m}'
            t = fields(t, ws, ['length', 'source'],
                       {'translation': '', 'compress': None, 'addStringTerminator': True})
            uint(t['length'], ws + ' length', 32)
            for k in ('source', 'translation'):
                if not isinstance(t[k], str):
                    raise ValueError(f'{ws}: {k} must be a string')
            opt_bool(t['compress'], ws + ' compress')
            opt_bool(t['addStringTerminator'], ws + ' addStringTerminator')
            strings.append(t)
        s['strings'] = strings
        sections.append(s)
    u['sections'] = sections
    return u


def read_patch(path):
    """A byte patch: {file, edits: {"hexoffset": "hex bytes, spaces allowed"}}."""
    p = fields(load_json(path), path, ['file'], {'edits': {}})
    if not isinstance(p['file'], str) or not isinstance(p['edits'], dict):
        raise ValueError(f'{path}: bad file or edits')
    edits = {}
    for k, s in p['edits'].items():
        if not isinstance(s, str):
            raise ValueError(f'{path}: edit {k} must be a string')
        b, i = bytearray(), 0
        while i < len(s):
            if i + 1 >= len(s):
                raise ValueError(f'{path}: edit {k} has an odd hex digit at the end')
            # As the Kotlin reader: a pair is two non-space characters; otherwise skip one.
            if s[i] != ' ' and s[i + 1] != ' ':
                b.append(hex_int(s[i:i + 2], 2))
                i += 2
            else:
                i += 1
        edits[hex_int(k, 16)] = bytes(b)
    return p['file'], edits


# ---- encoding

class Encoder:
    def __init__(self):
        self.codes = read_name_table(CODES_TABLE_PATH, 'Control codes table')
        self.digraphs = read_name_table(DIGRAPH_TABLE_PATH, 'Digraph table')
        self.table = parse_table_inverse(ENCODING_TABLE_PATH)

    # Digraph compression: each word (up to and including the next space) is scanned
    # left to right; {...} blocks are copied, and a pair in the table becomes {code}.
    def compress(self, s):
        out, cur = [], 0
        while cur < len(s):
            end = s.find(' ', cur)
            if end < 0:
                end = len(s) - 1
            out.append(self._encode_word(s, cur, end))
            cur = end + 1
        return ''.join(out)

    def _encode_word(self, s, start, end):
        out, i = [], start
        while i <= end:
            if s[i] == '{':
                while True:
                    out.append(s[i])
                    i += 1
                    if not (i <= end and s[i - 1] != '}'):
                        break
                continue
            if i + 1 <= end:
                code = self.digraphs.get(s[i] + s[i + 1])
                if code is not None:
                    out.append('{' + code + '}')
                    i += 2
                    continue
            out.append(s[i])
            i += 1
        return ''.join(out)

    def control_code(self, s, start):
        end = s.find('}', start)
        if end < 0:
            raise ValueError(f"Missing '}}' in string:\n{s}")
        code = s[start + 1:end]
        h = self.codes.get(code, code)
        try:
            return bytes(hex_int(h[k:k + 2], 2) for k in range(0, len(h) - 1, 2))
        except ValueError as e:
            raise ValueError(f"{e} for code '{code}' in string:\n{s}") from None

    def encode_plain(self, s, compress):
        string = self.compress(s) if compress else s
        res, i = bytearray(), 0
        while i < len(string):
            ch = string[i]
            if ch in '\n\r':
                enc = self.table.get('\\n' if ch == '\n' else '\\r')
                if enc is None:
                    raise ValueError(f'Unexpected escape sequence: {ord(ch)}')
                res += bytes([(enc & 0xff00) >> 8, enc & 0xff])
                i += 1
            elif ch == '{':
                res += self.control_code(string, i)
                i = string.index('}', i) + 1
            elif ch == '}':
                raise ValueError(f"Missing '{{' from hex/code sequence:\n{string}")
            else:
                # The Kotlin tool read UTF-16 units, so nothing outside the BMP matched.
                enc = self.table.get(ch) if ord(ch) <= 0xffff else None
                if enc is None:
                    raise ValueError(f'{string} - Unknown character: {ch}')
                if enc > 0xff:
                    res.append((enc & 0xff00) >> 8)
                res.append(enc & 0xff)
                i += 1
        return bytes(res)

    def encode_string(self, sd, compress):
        b = self.encode_plain(sd['translation'] or sd['source'], compress)
        if sd['addStringTerminator'] is not False:
            b += TERMINATOR
        return b

    def encode_unit(self, unit):
        """-> (file, {offset: bytes}): each section's strings repacked from firstHeader,
        and its u16 offsets pointed at them."""
        expand = unit['extendByBytes'] or 0
        if expand < 0:
            raise ValueError(f"{unit['file']}: expandByBytes must be non-negative.")
        result, extra = {}, 0
        info(unit['file'])
        for sec in unit['sections']:
            temp = {}
            used = 0
            first = sec['firstHeaderAddress']
            head_addr = first
            new_head = sec['firstHeader']
            for sd in sec['strings']:
                compress = (sd['compress'] is None and sec['compress'] is True) or sd['compress'] is True
                enc = self.encode_string(sd, compress)
                temp[(new_head + first) & U64] = enc
                temp[head_addr] = bytes([new_head & 0xff, (new_head >> 8) & 0xff])
                head_addr = (head_addr + 4) & U64
                new_head = (new_head + len(enc)) & U32
                used = (used + ((len(enc) - 2) & U32)) & U32
            length = sec['sectionLength']
            if used > length:
                extra = s32(extra + s32(used - length))
                warn(f'\tsection 0x{first:x}: exceeds size by {used - length} bytes. '
                     'File expansion may be required.')
            else:
                info(f'\tsection 0x{first:x}: {s32(s32(length) - s32(used))} unused bytes')
            result.update(temp)
        if extra > expand:
            err(f'\t-> exceeded size + expansion by {s32(extra - expand)} bytes. Ignoring translations.')
            result.clear()
        return unit['file'], result


def apply_edits(name, source, edits):
    """Edits in offset order. Bytes from the file's size at the start of an edit onward are
    appended, so an edit that starts past the end lands at the end (as the Kotlin tool)."""
    if not source:
        raise ValueError('No file has been loaded.')
    added = 0
    for base in sorted(edits):
        size = len(source)
        for i, b in enumerate(edits[base]):
            if base + i >= size:
                source.append(b)
                added += 1
            else:
                source[base + i] = b
    if added > 0:
        warn(f'{name} was expanded by {added} bytes')
    return source


def json_files(d):
    """d/*.json in name order (the Kotlin tool took directory order; see merge below)."""
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.endswith('.json') and os.path.isfile(os.path.join(d, f))]


def encode_all():
    enc = Encoder()
    rules = [enc.encode_unit(read_unit(p)) for p in json_files(TRANSLATIONS_PATH)]
    if not rules:
        err(f'No translation units were found in {TRANSLATIONS_PATH}.')
    binary = [read_patch(p) for p in json_files(BINARY_PATCHES_PATH)]
    if not binary:
        warn(f'No binary patches were found in {BINARY_PATCHES_PATH}.')

    # Merge per file, translations first: a later rule's edit at the same offset replaces
    # an earlier one. The Kotlin tool read files in directory order, so two rules writing
    # different bytes at one offset would have depended on that order; say so if it happens.
    combined, owner = {}, {}
    sources = json_files(TRANSLATIONS_PATH) + json_files(BINARY_PATCHES_PATH)
    for (f, edits), src in zip(rules + binary, sources):
        m = combined.setdefault(f, {})
        for o, b in edits.items():
            if o in m and m[o] != b:
                warn(f'{f} 0x{o:x}: {src} replaces the edit from {owner[f, o]}')
            m[o] = b
            owner[f, o] = src

    if not os.path.exists(CLEAN_DUMP_PATH) or not os.path.exists(DIRTY_DUMP_PATH):
        raise RuntimeError(f'Incomplete setup: {CLEAN_DUMP_PATH} and/or {DIRTY_DUMP_PATH} not found.')
    for f, edits in combined.items():
        src = os.path.join(CLEAN_DUMP_PATH, f)
        if not os.path.exists(src):
            raise ValueError(f'Failed to load {f}')
        data = apply_edits(f, bytearray(open(src, 'rb').read()), edits)
        out = os.path.join(DIRTY_DUMP_PATH, f)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as o:
            o.write(data)


# ---- dumping

class Decoder:
    def __init__(self):
        self.table = parse_table(DECODING_TABLE_PATH)

    @staticmethod
    def headers(first, d):
        """The section's u16 offsets: 4-byte entries until one has nonzero high bytes."""
        out = []
        for i in range(first, len(d) + 1, 4):
            if not (d[i + 2] == 0 and d[i + 3] == 0):
                break
            out.append(d[i] | d[i + 1] << 8)
        return out

    def section(self, d, addrs):
        """-> [(text, length, add_terminator)]. A string ends at {ff40}; one with a known
        length (to the next offset) ends where only its last two bytes are left, and if
        those aren't {ff40} the string has no terminator. A string that runs off the
        end of the file isn't listed."""
        out = []
        for n, start in enumerate(addrs):
            orig = (addrs[n + 1] - start) & U64 if n + 1 < len(addrs) else NO_LENGTH
            text, length, term, i, end = [], 0, True, start, False

            def add(fmt, c, size):
                nonlocal length, i
                text.append(self.table.get(c, '{' + fmt % c + '}'))
                length = (length + size) & U32
                i += size

            if orig == 1:
                add('%02x', d[i], 1)
                out.append((''.join(text), length, False))
                continue
            while not end and i < len(d):
                b = d[i]
                if b >= 0xf7:
                    c = b << 8 | d[i + 1]
                    if orig == NO_LENGTH and c == 0xff40:
                        end = True
                    elif length == (orig - 2) & U64:
                        end = True
                        if c != 0xff40:
                            add('%04x', c, 2)
                            term = False
                    else:
                        add('%04x', c, 2)
                else:
                    add('%02x', b, 1)
                if end:
                    out.append((''.join(text), length, term))
        return out

    def decode(self, metadata):
        units = {}
        for meta in metadata:
            secs = units.setdefault(meta['file'], [])
            path = os.path.join(CLEAN_DUMP_PATH, meta['file'])
            if not os.path.exists(path):
                raise ValueError(f'Failed to read {path}')
            d = open(path, 'rb').read()
            for first in meta['headers']:
                if len(d) < first:
                    raise ValueError(f'Wrong config for file "{meta["file"]}": '
                                     f'address 0x{first:x} does not exist.')
                addrs = [h + first for h in self.headers(first, d)]
                strings = [{'length': n, 'source': t, 'translation': '', 'compress': None,
                            'addStringTerminator': term}
                           for t, n, term in self.section(d, addrs)]
                secs.append({'firstHeaderAddress': first,
                             'firstHeader': d[first] | d[first + 1] << 8,
                             'sectionLength': sum(s['length'] for s in strings) & U32,
                             'compress': False,
                             'strings': strings})
        return [{'file': f, 'extendByBytes': None, 'sections': s} for f, s in units.items()]


def read_sections():
    out = []
    for n, m in enumerate(load_json(SECTIONS_FILE_PATH)):
        m = fields(m, f'{SECTIONS_FILE_PATH} entry {n}', ['file', 'headers'], {})
        heads = []
        for h in m['headers']:
            h = fields(h, f'{SECTIONS_FILE_PATH} {m["file"]} header', ['address'], {})
            heads.append(hex_int(h['address'], 16))
        out.append({'file': m['file'], 'headers': heads})
    return out


def dump():
    if not os.path.exists(CLEAN_DUMP_PATH):
        raise RuntimeError(f'Incomplete setup: {CLEAN_DUMP_PATH} not found.')
    dec = Decoder()
    if not os.path.exists(SECTIONS_FILE_PATH):
        raise FileNotFoundError(SECTIONS_FILE_PATH)
    os.makedirs(TEXT_DUMPS_PATH, exist_ok=True)
    for unit in dec.decode(read_sections()):
        info(f"Processing {unit['file']}...")
        # The Kotlin tool's output: 4-space JSON with \\ turned back into \, so the
        # table's "\n" entries come out as JSON newline escapes.
        text = json.dumps(unit, indent=4, ensure_ascii=False).replace('\\\\', '\\')
        with open(os.path.join(TEXT_DUMPS_PATH, unit['file'].split('/')[-1] + '.json'),
                  'w', encoding='utf-8', newline='') as f:
            f.write(text)
    info(f'Done. Text dumped to "./{TEXT_DUMPS_PATH}"')


def encode_string(args):
    compress = '-compress' in args
    text = [a for a in args if a != '-compress']
    if len(text) != 1 or not text[0]:
        raise ValueError('usage: texttool.py encode-string [-compress] TEXT')
    print(Encoder().encode_plain(text[0], compress).hex())


def main(argv):
    verb = argv[0] if argv else None
    if verb == 'dump':
        dump()
    elif verb == 'encode-all':
        encode_all()
    elif verb == 'encode-string':
        encode_string(argv[1:])
    else:
        print('Usage: {dump|encode-all|encode-string} <args>')
        sys.exit(255)


if __name__ == '__main__':
    main(sys.argv[1:])
