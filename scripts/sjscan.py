#!/usr/bin/env python3
"""Scan a binary for runs of Shift-JIS / ASCII text. Usage: sjscan.py file [minchars]"""
import sys
def scan(data, minc=3):
    i, n = 0, len(data)
    while i < n:
        j, chars, jp = i, [], 0
        while j < n:
            b = data[j]
            if 0x20 <= b < 0x7f:
                chars.append(chr(b)); j += 1
            elif (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef) and j+1 < n and 0x40 <= data[j+1] <= 0xfc and data[j+1] != 0x7f:
                try:
                    chars.append(data[j:j+2].decode('cp932')); jp += 1; j += 2
                except UnicodeDecodeError:
                    break
            elif b == 0x0a:
                chars.append('\\n'); j += 1
            else:
                break
        if len(chars) >= minc and (jp >= 2 or len(chars) >= 6):
            yield i, ''.join(chars), jp
            i = j
        else:
            i = max(j, i+1) if j > i else i+1
if __name__ == '__main__':
    d = open(sys.argv[1],'rb').read()
    m = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    for off, s, jp in scan(d, m):
        print(f"{off:08x} {'J' if jp else 'A'} {s}")
