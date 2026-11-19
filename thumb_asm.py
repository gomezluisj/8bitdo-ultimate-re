"""Minimal ARM Thumb-1/2 encoder and single-pass assembler for Cortex-M0/M0+."""
import struct

COND_EQ = 0x0
COND_NE = 0x1
COND_CS = 0x2
COND_CC = 0x3


def _check(cond, msg):
    if not cond:
        raise ValueError(msg)


def t_push(regs, lr=False):
    mask = 0
    for r in regs:
        _check(0 <= r <= 7, f"t_push register out of range: r{r}")
        mask |= 1 << r
    if lr:
        mask |= 1 << 8
    return struct.pack("<H", 0xB400 | mask)


def t_pop(regs, pc=False):
    mask = 0
    for r in regs:
        _check(0 <= r <= 7, f"t_pop register out of range: r{r}")
        mask |= 1 << r
    if pc:
        mask |= 1 << 8
    return struct.pack("<H", 0xBC00 | mask)


def t_sub_sp(imm_bytes):
    _check(imm_bytes % 4 == 0 and 0 <= (imm_bytes >> 2) <= 127,
           f"t_sub_sp immediate out of range: {imm_bytes}")
    return struct.pack("<H", 0xB080 | (imm_bytes >> 2))


def t_add_sp(imm_bytes):
    _check(imm_bytes % 4 == 0 and 0 <= (imm_bytes >> 2) <= 127,
           f"t_add_sp immediate out of range: {imm_bytes}")
    return struct.pack("<H", 0xB000 | (imm_bytes >> 2))


def t_add_rd_sp(rd, imm_bytes):
    _check(0 <= rd <= 7 and imm_bytes % 4 == 0 and 0 <= (imm_bytes >> 2) <= 255,
           f"t_add_rd_sp out of range: r{rd}, {imm_bytes}")
    return struct.pack("<H", 0xA800 | (rd << 8) | (imm_bytes >> 2))


def t_mov_high(rd, rm):
    _check(0 <= rd <= 15 and 0 <= rm <= 15, f"t_mov_high out of range: r{rd}, r{rm}")
    d = (rd >> 3) & 1
    return struct.pack("<H", 0x4600 | (d << 7) | ((rm & 0xF) << 3) | (rd & 0x7))


def t_movs(rd, imm8):
    _check(0 <= rd <= 7 and 0 <= imm8 <= 255, f"t_movs out of range: r{rd}, {imm8}")
    return struct.pack("<H", 0x2000 | (rd << 8) | imm8)


def t_subs_imm8(rd, imm8):
    _check(0 <= rd <= 7 and 0 <= imm8 <= 255, f"t_subs_imm8 out of range: r{rd}, {imm8}")
    return struct.pack("<H", 0x3800 | (rd << 8) | imm8)


def t_adds_imm3(rd, rn, imm3):
    _check(0 <= rd <= 7 and 0 <= rn <= 7 and 0 <= imm3 <= 7,
           f"t_adds_imm3 out of range: r{rd}, r{rn}, {imm3}")
    return struct.pack("<H", 0x1C00 | (imm3 << 6) | (rn << 3) | rd)


def t_adds_imm8(rd, imm8):
    _check(0 <= rd <= 7 and 0 <= imm8 <= 255, f"t_adds_imm8 out of range: r{rd}, {imm8}")
    return struct.pack("<H", 0x3000 | (rd << 8) | imm8)


def t_adds_reg(rd, rn, rm):
    _check(0 <= rd <= 7 and 0 <= rn <= 7 and 0 <= rm <= 7,
           f"t_adds_reg out of range: r{rd}, r{rn}, r{rm}")
    return struct.pack("<H", 0x1800 | (rm << 6) | (rn << 3) | rd)


def t_cmp_imm8(rn, imm8):
    _check(0 <= rn <= 7 and 0 <= imm8 <= 255, f"t_cmp_imm8 out of range: r{rn}, {imm8}")
    return struct.pack("<H", 0x2800 | (rn << 8) | imm8)


def t_cmp_reg(rn, rm):
    _check(0 <= rn <= 7 and 0 <= rm <= 7, f"t_cmp_reg out of range: r{rn}, r{rm}")
    return struct.pack("<H", 0x4280 | (rm << 3) | rn)


def t_orrs_reg(rdn, rm):
    _check(0 <= rdn <= 7 and 0 <= rm <= 7, f"t_orrs_reg out of range: r{rdn}, r{rm}")
    return struct.pack("<H", 0x4300 | (rm << 3) | rdn)


def t_ands_reg(rdn, rm):
    _check(0 <= rdn <= 7 and 0 <= rm <= 7, f"t_ands_reg out of range: r{rdn}, r{rm}")
    return struct.pack("<H", 0x4000 | (rm << 3) | rdn)


def t_strb_imm(rt, rn, imm5=0):
    _check(0 <= rt <= 7 and 0 <= rn <= 7 and 0 <= imm5 <= 31,
           f"t_strb_imm out of range: r{rt}, r{rn}, {imm5}")
    return struct.pack("<H", 0x7000 | (imm5 << 6) | (rn << 3) | rt)


def t_ldrb_imm(rt, rn, imm5=0):
    _check(0 <= rt <= 7 and 0 <= rn <= 7 and 0 <= imm5 <= 31,
           f"t_ldrb_imm out of range: r{rt}, r{rn}, {imm5}")
    return struct.pack("<H", 0x7800 | (imm5 << 6) | (rn << 3) | rt)


def t_ldrb_reg(rt, rn, rm):
    _check(0 <= rt <= 7 and 0 <= rn <= 7 and 0 <= rm <= 7,
           f"t_ldrb_reg out of range: r{rt}, r{rn}, r{rm}")
    return struct.pack("<H", 0x5C00 | (rm << 6) | (rn << 3) | rt)


def t_strb_reg(rt, rn, rm):
    _check(0 <= rt <= 7 and 0 <= rn <= 7 and 0 <= rm <= 7,
           f"t_strb_reg out of range: r{rt}, r{rn}, r{rm}")
    return struct.pack("<H", 0x5400 | (rm << 6) | (rn << 3) | rt)


def t_ldr_imm(rt, rn, imm_bytes=0):
    _check(0 <= rt <= 7 and 0 <= rn <= 7 and imm_bytes % 4 == 0,
           f"t_ldr_imm invalid args: r{rt}, r{rn}, {imm_bytes}")
    imm5 = imm_bytes >> 2
    _check(0 <= imm5 <= 31, f"t_ldr_imm offset out of range: {imm_bytes}")
    return struct.pack("<H", 0x6800 | (imm5 << 6) | (rn << 3) | rt)


def t_str_imm(rt, rn, imm_bytes=0):
    _check(0 <= rt <= 7 and 0 <= rn <= 7 and imm_bytes % 4 == 0,
           f"t_str_imm invalid args: r{rt}, r{rn}, {imm_bytes}")
    imm5 = imm_bytes >> 2
    _check(0 <= imm5 <= 31, f"t_str_imm offset out of range: {imm_bytes}")
    return struct.pack("<H", 0x6000 | (imm5 << 6) | (rn << 3) | rt)


def t_str_sp(rt, imm_bytes):
    _check(0 <= rt <= 7 and imm_bytes % 4 == 0 and 0 <= (imm_bytes >> 2) <= 255,
           f"t_str_sp out of range: r{rt}, {imm_bytes}")
    return struct.pack("<H", 0x9000 | (rt << 8) | (imm_bytes >> 2))


def t_ldr_pc(rt, label):
    _check(0 <= rt <= 7, f"t_ldr_pc register out of range: r{rt}")
    return ("ldr_pc", rt, label)


def t_b_cond(cond, label):
    return ("b_cond", cond, label)


def t_b(label):
    return ("b", label)


def t_bl(target_addr):
    return ("bl", target_addr)


def t_bl_lbl(label):
    return ("bl_lbl", label)


def t_nop():
    return struct.pack("<H", 0xBF00)


def assemble_raw(base_addr, items, pool_dict):
    pc = base_addr
    labels = {}
    for it in items:
        if isinstance(it, str):
            _check(it not in labels, f"duplicate label: {it}")
            labels[it] = pc
        elif isinstance(it, tuple):
            pc += 4 if it[0] == "bl" else 2
        else:
            pc += len(it)
    if pool_dict and pc % 4 != 0:
        items = list(items) + [t_nop()]
        pc += 2
    pool_addrs = {}
    for k in pool_dict:
        pool_addrs[k] = pc
        pc += 4

    out = bytearray()
    cur = base_addr
    for it in items:
        if isinstance(it, str):
            continue
        elif isinstance(it, tuple):
            op = it[0]
            if op == "ldr_pc":
                _, rt, k = it
                target = pool_addrs[k]
                base_pc = (cur + 4) & ~3
                off = target - base_pc
                _check(off >= 0 and off % 4 == 0 and (off >> 2) <= 255,
                       f"ldr_pc out of range for {k}: off={off}")
                out += struct.pack("<H", 0x4800 | (rt << 8) | (off >> 2))
                cur += 2
            elif op == "b_cond":
                _, cond, lbl = it
                target = labels[lbl]
                off = (target - (cur + 4)) >> 1
                _check(-128 <= off <= 127, f"b_cond out of range for {lbl}: off={off}")
                out += struct.pack("<H", 0xD000 | (cond << 8) | (off & 0xFF))
                cur += 2
            elif op == "b":
                _, lbl = it
                target = labels[lbl]
                off = (target - (cur + 4)) >> 1
                _check(-1024 <= off <= 1023, f"b out of range for {lbl}: off={off}")
                out += struct.pack("<H", 0xE000 | (off & 0x7FF))
                cur += 2
            elif op == "bl":
                _, target = it
                rel = target - (cur + 4)
                _check(-16777216 <= rel <= 16777214 and rel % 2 == 0,
                       f"bl out of range: target=0x{target:x}, rel={rel}")
                s = (rel >> 24) & 1
                i1 = (rel >> 23) & 1
                i2 = (rel >> 22) & 1
                j1 = (~i1 ^ s) & 1
                j2 = (~i2 ^ s) & 1
                imm10 = (rel >> 12) & 0x3FF
                imm11 = (rel >> 1) & 0x7FF
                hw1 = 0xF000 | (s << 10) | imm10
                hw2 = 0xF800 | (j1 << 13) | (j2 << 11) | imm11
                out += struct.pack("<HH", hw1, hw2)
                cur += 4
            else:
                raise ValueError(f"unknown pseudo-op: {op}")
        else:
            out += it
            cur += len(it)

    for _, val in pool_dict.items():
        out += struct.pack("<I", val)
    return bytes(out), labels


def assemble(base_addr, items, pool_dict):
    pc = base_addr
    labels = {}
    for it in items:
        if isinstance(it, str):
            _check(it not in labels, f"duplicate label: {it}")
            labels[it] = pc
        elif isinstance(it, tuple):
            pc += 4 if it[0] in ("bl", "bl_lbl") else 2
        else:
            pc += len(it)
    resolved = [
        t_bl(labels[it[1]]) if isinstance(it, tuple) and it[0] == "bl_lbl" else it
        for it in items
    ]
    return assemble_raw(base_addr, resolved, pool_dict)
