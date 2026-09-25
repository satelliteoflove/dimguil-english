#!/usr/bin/env python3
"""Disassemble MIPS from a RAM snapshot or bytes. dis(ram_bytes, addr, n) -> lines"""
import capstone
_md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 | capstone.CS_MODE_LITTLE_ENDIAN)
def dis(ram, addr, n=32, base=0x80000000):
    off = (addr - base) & 0x1fffff
    out = []
    for ins in _md.disasm(bytes(ram[off:off + 4 * n]), addr):
        out.append(f'{ins.address:08x}  {ins.mnemonic:8s} {ins.op_str}')
    return out
