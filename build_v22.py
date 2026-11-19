#!/usr/bin/env python3
"""Build fw111_v22.bin, v22_enc.dat, and v22_enc_body.bin for 8BitDo Ultimate BT (80NA, fw 1.11).

Standalone patcher (no external build_v*.py dependencies) adding Nintendo Switch 2
wireless shake-to-wake and Cycle-1 Classic BT + HID reconnect onto stock 1.11:
- Hooks 0x0101b880 (once-per-boot init) to zero STATE_RAM across warm resets.
- Reads Console MAC at runtime from NV Slot 0 (0x0107e006..0x0107e00b) -> works with
  any Switch 2 paired in Slot 0 without hardcoding personal MACs.
- WINDOW_MS = 2400 real ms BLE "HH" burst (via stock poll_wait 0x010281c0), checking
  expiry before LED toggle in fn_on_tick() + COOLDOWN_MS = 1800 ms post-wake debounce.
- In fn_finish_wake(): sets [0x000201b4] bit 20 via 0x01026e98(1<<20) so 0x0101c180
  always starts BT_CreatBtReconnect() even after USB bootloader cmd-7 resets; fixes
  solid Home LED ON; clears [0x00020582] & [0x000201e8]; enables Page Scan.
- GRACE_MS = 15000 real ms reconnect grace window (matching v2.00) shielding all
  premature 6s timer resets (0x01025e64, 0x01025e76, 0x01025e82), error-count resets
  (0x0101a26e, 0x0101a2a2), and Switch-1 wake fallbacks until HID connects or 15s ends.
"""
import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

from thumb_asm import (
    COND_CC,
    COND_EQ,
    COND_NE,
    assemble,
    assemble_raw,
    t_add_rd_sp,
    t_add_sp,
    t_adds_imm3,
    t_adds_imm8,
    t_adds_reg,
    t_ands_reg,
    t_b_cond,
    t_bl,
    t_bl_lbl,
    t_cmp_imm8,
    t_cmp_reg,
    t_ldr_imm,
    t_ldr_pc,
    t_ldrb_imm,
    t_ldrb_reg,
    t_mov_high,
    t_movs,
    t_orrs_reg,
    t_pop,
    t_push,
    t_str_imm,
    t_str_sp,
    t_strb_imm,
    t_strb_reg,
    t_sub_sp,
    t_subs_imm8,
)

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED_STOCK_SHA256 = "934ff2a60637ab517ce434affb274d68c065242801ac068e0ede42f35a315d3c"


def _require(cond, msg):
    """Runtime invariant check that cannot be stripped by `python3 -O`."""
    if not cond:
        raise RuntimeError(msg)


# ----------------------------------------------------------------------
# Switch 2 Wake Payload & Verified fw 1.11 (80NA) Stock Symbols
# ----------------------------------------------------------------------
# Universal 31-byte Switch 2 BLE ADV template (flag=0x81, PID 0x2066);
# bytes 17..22 are zeroed here and filled at runtime from NV Slot 0 (+0x06..+0x0b)
adv_31b_tpl = bytes.fromhex(
    "0201061bff53050100037e0566200001"
    "810000000000000f00000000000000"
)
_require(len(adv_31b_tpl) == 31, f"Invalid ADV template length: {len(adv_31b_tpl)}")
adv_words = struct.unpack("<8I", adv_31b_tpl + b"\x00")

BASE = 0x01031A00
ADDR_MEMCPY = 0x01018268
ADDR_SER24 = 0x010182F0
ADDR_CLAIM = 0x010190FC
ADDR_CHECK = 0x0101911E
ADDR_SET_BLE_ADDR = 0x0101AB6C
ADDR_SET_BLE_NAME = 0x0101AC24
ADDR_RADIO_CFG = 0x0101AF70
ADDR_BOOT_BLE_INIT = 0x0101B368
ADDR_RESET_20220228 = 0x0101BB5C
ADDR_CLR_20221031 = 0x0101BFFC
ADDR_BT_RECONNECT_START = 0x0101C180
ADDR_TIMER_CANCEL = 0x0101DD44
ADDR_GET_WAKEUP_FLAG = 0x0101E998
ADDR_RESET_CLEAN = 0x01026358
ADDR_IPC_SEND = 0x01026880
ADDR_LED_TOGGLE = 0x01026E4C
ADDR_SET_PWR_BIT = 0x01026E98
ADDR_SET_WAKEUP_FLAG = 0x010271C0
ADDR_GET_TICK = 0x010281B4
ADDR_POLL_WAIT = 0x010281C0
ADDR_S1_WAKE_FAIL = 0x0102855C
ADDR_HID_CB = 0x0102C2FC
ADDR_READ_NV = 0x0102CFCC
ADDR_STOCK_BLE_NAME = 0x01030E8C
ADDR_UID_RAM = 0x00020000
ADDR_BT_PEND_FLAGS = 0x000201E8
ADDR_ERR_CNT = 0x00020582

# STATE_RAM layout (24 bytes in verified-unused SRAM 0x00026000..0x00026018):
#   [+0x00]=wake_tick, [+0x04]=armed_magic
#   [+0x08]=cd_tick,   [+0x0c]=cd_magic
#   [+0x10]=grace_tick,[+0x14]=grace_magic
STATE_RAM = 0x00026000
ARMED_MAGIC = 0x56323201
COOLDOWN_MAGIC = 0x56323243
GRACE_MAGIC = 0x56323247
WINDOW_MS = 2400
COOLDOWN_MS = 1800
GRACE_MS = 15000

prog = [
    # ------------------------------------------------------------------
    # 0) fn_boot_init(r0, r1): hooked at 0x0101B880 (replaces BL 0x0101B368)
    #    Clears STATE_RAM on every cold or warm reset before calling BLE init.
    # ------------------------------------------------------------------
    "fn_boot_init",
    t_push([4, 5, 6], lr=True),
    t_mov_high(4, 0),
    t_mov_high(5, 1),
    t_ldr_pc(2, "STATE_RAM"),
    t_movs(3, 0),
    *(t_str_imm(3, 2, off) for off in range(0, 24, 4)),
    t_mov_high(0, 4),
    t_mov_high(1, 5),
    t_bl(ADDR_BOOT_BLE_INIT),
    t_pop([4, 5, 6], pc=True),

    # ------------------------------------------------------------------
    # Shared helpers: fn_window_state, fn_check_state_timer,
    # fn_restore_ble_identity, fn_close_wake, fn_finish_wake, fn_reset_guard_common
    # ------------------------------------------------------------------
    # fn_window_state() -> r0 = 0 (unarmed), 1 (active < WINDOW_MS), 2 (expired)
    "fn_window_state",
    t_push([4], lr=True),
    t_ldr_pc(4, "STATE_RAM"),
    t_ldr_imm(0, 4, 4),
    t_ldr_pc(1, "ARMED_MAGIC"),
    t_cmp_reg(0, 1),
    t_b_cond(COND_EQ, "ws_armed"),
    t_movs(0, 0),
    t_pop([4], pc=True),
    "ws_armed",
    t_ldr_imm(0, 4, 0),
    t_ldr_pc(1, "WINDOW_MS"),
    t_bl(ADDR_POLL_WAIT),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_EQ, "ws_active"),
    t_movs(0, 2),
    t_pop([4], pc=True),
    "ws_active",
    t_movs(0, 1),
    t_pop([4], pc=True),

    # fn_check_state_timer(r0=byte_off, r1=magic, r2=dur_ms) -> r0 (1 active, 0 inactive)
    "fn_check_state_timer",
    t_push([4, 5, 6], lr=True),
    t_ldr_pc(4, "STATE_RAM"),
    t_adds_reg(4, 4, 0),
    t_mov_high(5, 2),
    t_ldr_imm(0, 4, 4),
    t_cmp_reg(0, 1),
    t_b_cond(COND_EQ, "st_armed"),
    t_movs(0, 0),
    t_pop([4, 5, 6], pc=True),
    "st_armed",
    t_ldr_imm(0, 4, 0),
    t_mov_high(1, 5),
    t_bl(ADDR_POLL_WAIT),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_NE, "st_expired"),
    t_movs(0, 1),
    t_pop([4, 5, 6], pc=True),
    "st_expired",
    t_movs(0, 0),
    t_str_imm(0, 4, 4),
    t_pop([4, 5, 6], pc=True),

    "fn_restore_ble_identity",
    t_push([4], lr=True),
    t_sub_sp(0x18),
    t_add_rd_sp(0, 0x08),
    t_ldr_pc(1, "ADDR_STOCK_BLE_NAME"),
    t_movs(2, 16),
    t_bl(ADDR_MEMCPY),
    t_ldr_pc(4, "ADDR_UID_RAM"),
    t_add_rd_sp(1, 0x00),
    *(
        op
        for i in range(3)
        for op in (
            t_ldrb_imm(2, 4, i),
            t_ldrb_imm(3, 4, i + 3),
            t_adds_reg(2, 2, 3),
            t_strb_imm(2, 1, i),
        )
    ),
    t_movs(2, 0xD8),
    t_strb_imm(2, 1, 3),
    t_movs(2, 0x17),
    t_strb_imm(2, 1, 4),
    t_movs(2, 0xE4),
    t_strb_imm(2, 1, 5),
    t_add_rd_sp(0, 0x08),
    t_movs(1, 0x0E),
    t_bl(ADDR_SET_BLE_NAME),
    t_add_rd_sp(0, 0x00),
    t_bl(ADDR_SET_BLE_ADDR),
    t_add_sp(0x18),
    t_pop([4], pc=True),

    "fn_close_wake",
    t_push([4], lr=True),
    t_ldr_pc(4, "STATE_RAM"),
    t_movs(0, 0),
    t_str_imm(0, 4, 4),          # ARMED_MAGIC = 0
    t_bl(ADDR_CLR_20221031),     # clear [0x0002fff8] so BT_CreatBtReconnect runs
    t_movs(0, 0),
    t_bl(ADDR_SET_WAKEUP_FLAG),  # [0x0002057e] = 0
    t_movs(0, 0),
    t_movs(1, 0),
    t_movs(2, 0),
    t_bl(ADDR_RADIO_CFG),        # radio_cfg(0, 0, 0): stop HH BLE adv
    t_bl_lbl("fn_restore_ble_identity"),
    t_movs(0, 2),
    t_bl(ADDR_LED_TOGGLE),       # restore solid Home LED ON (avoid random toggle-off)
    t_pop([4], pc=True),

    "fn_finish_wake",
    t_push([4], lr=True),
    t_bl_lbl("fn_close_wake"),
    t_movs(0, 0),
    t_ldr_pc(1, "ADDR_BT_PEND_FLAGS"),
    t_strb_imm(0, 1, 0),
    t_ldr_pc(1, "ADDR_ERR_CNT"),
    t_strb_imm(0, 1, 0),
    t_bl(ADDR_GET_TICK),
    t_ldr_pc(4, "STATE_RAM"),
    t_str_imm(0, 4, 8),          # cd_tick
    t_str_imm(0, 4, 16),         # grace_tick
    t_ldr_pc(0, "COOLDOWN_MAGIC"),
    t_str_imm(0, 4, 12),
    t_ldr_pc(0, "GRACE_MAGIC"),
    t_str_imm(0, 4, 20),
    t_ldr_pc(0, "PWR_BIT20"),
    t_bl(ADDR_SET_PWR_BIT),      # ensure bit 20 is set even after USB cmd-7 reset
    t_movs(0, 0),
    t_movs(1, 1),
    t_movs(2, 0),
    t_bl(ADDR_RADIO_CFG),        # radio_cfg(0, 1, 0): enable Page Scan
    t_bl(ADDR_BT_RECONNECT_START),
    t_pop([4], pc=True),

    # fn_reset_guard_common() -> r0 = 1 if reset/fallback suppressed, 0 if stock allowed
    "fn_reset_guard_common",
    t_push([4], lr=True),
    t_bl_lbl("fn_window_state"),
    t_cmp_imm8(0, 1),
    t_b_cond(COND_EQ, "rg_block"),
    t_cmp_imm8(0, 2),
    t_b_cond(COND_NE, "rg_chk_grace"),
    t_bl_lbl("fn_finish_wake"),
    "rg_block",
    t_movs(0, 1),
    t_pop([4], pc=True),
    "rg_chk_grace",
    t_movs(0, 16),
    t_ldr_pc(1, "GRACE_MAGIC"),
    t_ldr_pc(2, "GRACE_MS"),
    t_bl_lbl("fn_check_state_timer"),
    t_pop([4], pc=True),

    # ------------------------------------------------------------------
    # 1) fn_on_shake(): hooked at 0x01021A3E (replaces BL 0x010191F0)
    # ------------------------------------------------------------------
    "fn_on_shake",
    t_push([4, 5, 6, 7], lr=True),
    t_movs(0, 8),
    t_ldr_pc(1, "COOLDOWN_MAGIC"),
    t_ldr_pc(2, "COOLDOWN_MS"),
    t_bl_lbl("fn_check_state_timer"),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_EQ, "shake_go"),
    t_movs(0, 0),
    t_bl(ADDR_SET_WAKEUP_FLAG),
    t_movs(0, 2),
    t_bl(ADDR_LED_TOGGLE),
    t_pop([4, 5, 6, 7], pc=True),

    "shake_go",
    t_sub_sp(0x5C),

    # Read NV Slot 0 (28 bytes) into sp+0x38
    t_ldr_pc(0, "NV_BASE"),
    t_add_rd_sp(1, 0x38),
    t_movs(2, 0x1C),
    t_bl(ADDR_READ_NV),

    # Verify Console MAC [sp+0x3e..0x43] is not 00*6 or FF*6
    t_add_rd_sp(3, 0x38),
    t_adds_imm8(3, 6),
    t_movs(4, 0),
    t_movs(5, 0xFF),
    t_movs(2, 0),
    "nv_chk_loop",
    t_ldrb_reg(0, 3, 2),
    t_orrs_reg(4, 0),
    t_ands_reg(5, 0),
    t_adds_imm3(2, 2, 1),
    t_cmp_imm8(2, 6),
    t_b_cond(COND_CC, "nv_chk_loop"),

    t_cmp_imm8(4, 0),
    t_b_cond(COND_EQ, "nv_unpaired"),
    t_cmp_imm8(5, 0xFF),
    t_b_cond(COND_NE, "nv_paired"),

    "nv_unpaired",
    t_movs(0, 0),
    t_bl(ADDR_SET_WAKEUP_FLAG),
    t_add_sp(0x5C),
    t_pop([4, 5, 6, 7], pc=True),

    "nv_paired",
    t_bl(ADDR_TIMER_CANCEL),     # cancel any pending 6s reconnect timer
    t_movs(0, 0),
    t_ldr_pc(1, "STATE_RAM"),
    t_str_imm(0, 1, 20),         # GRACE_MAGIC = 0
    t_ldr_pc(1, "ADDR_BT_PEND_FLAGS"),
    t_strb_imm(0, 1, 0),         # clear pending boot reconnect retries
    t_ldr_pc(1, "ADDR_ERR_CNT"),
    t_strb_imm(0, 1, 0),         # clear [0x00020582] error count

    t_ldr_pc(2, "MAC_W0"),
    t_str_sp(2, 0x08),
    t_ldr_pc(2, "MAC_W1"),
    t_str_sp(2, 0x0C),
    t_ldr_pc(2, "HH_WORD"),
    t_str_sp(2, 0x10),
]

for i in range(8):
    prog += [
        t_ldr_pc(2, f"ADV_W{i}"),
        t_str_sp(2, 0x14 + i * 4),
    ]

prog += [
    # Patch Console MAC from sp+0x3e..0x43 into sp+0x25..0x2a (adv_31b[17..22])
    t_add_rd_sp(0, 0x38),
    t_adds_imm8(0, 6),
    t_add_rd_sp(1, 0x14),
    t_adds_imm8(1, 17),
    t_movs(2, 0),
    "nv_copy_loop",
    t_ldrb_reg(3, 0, 2),
    t_strb_reg(3, 1, 2),
    t_adds_imm3(2, 2, 1),
    t_cmp_imm8(2, 6),
    t_b_cond(COND_CC, "nv_copy_loop"),

    t_add_rd_sp(0, 0x10),
    t_movs(1, 4),
    t_bl(ADDR_SET_BLE_NAME),

    t_add_rd_sp(0, 0x08),
    t_bl(ADDR_SET_BLE_ADDR),

    t_add_rd_sp(0, 0x00),
    t_movs(1, 0),
    t_strb_imm(1, 0, 0),
    t_movs(1, 0x34),
    t_strb_imm(1, 0, 1),
    t_movs(1, 0x1F),
    t_strb_imm(1, 0, 2),
    t_adds_imm3(1, 0, 3),
    t_add_rd_sp(0, 0x14),
    t_bl(ADDR_SER24),

    t_ldr_pc(0, "IPC_ACK"),
    t_movs(1, 0x15),
    t_bl(ADDR_CLAIM),

    t_add_rd_sp(0, 0x00),
    t_bl(ADDR_IPC_SEND),

    t_bl(ADDR_GET_TICK),
    t_mov_high(7, 0),
    t_movs(6, 200),

    "poll_loop",
    t_ldr_pc(0, "IPC_ACK"),
    t_movs(1, 0x15),
    t_bl(ADDR_CHECK),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_NE, "poll_done"),
    t_subs_imm8(6, 1),
    t_b_cond(COND_EQ, "poll_done"),
    t_mov_high(0, 7),
    t_ldr_pc(1, "TIMEOUT_500"),
    t_bl(ADDR_POLL_WAIT),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_EQ, "poll_loop"),

    "poll_done",
    t_movs(0, 0),
    t_movs(1, 0),
    t_movs(2, 1),
    t_bl(ADDR_RADIO_CFG),

    t_bl(ADDR_GET_TICK),
    t_ldr_pc(1, "STATE_RAM"),
    t_str_imm(0, 1, 0),
    t_ldr_pc(2, "ARMED_MAGIC"),
    t_str_imm(2, 1, 4),

    t_add_sp(0x5C),
    t_pop([4, 5, 6, 7], pc=True),

    # ------------------------------------------------------------------
    # 2) fn_on_tick(r0): hooked at 0x01021A6A (replaces BL 0x01026E4C)
    # ------------------------------------------------------------------
    "fn_on_tick",
    t_push([4], lr=True),
    t_mov_high(4, 0),
    t_bl_lbl("fn_window_state"),
    t_cmp_imm8(0, 2),
    t_b_cond(COND_EQ, "tick_finish"),
    t_mov_high(0, 4),
    t_bl(ADDR_LED_TOGGLE),
    t_pop([4], pc=True),
    "tick_finish",
    t_bl_lbl("fn_finish_wake"),
    t_pop([4], pc=True),

    # ------------------------------------------------------------------
    # 3) fn_timer_guard_early(r0): hooked at 0x01025E64 & 0x01025E76
    # ------------------------------------------------------------------
    "fn_timer_guard_early",
    t_push([4], lr=True),
    t_mov_high(4, 0),
    t_bl_lbl("fn_reset_guard_common"),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_NE, "early_done"),
    t_mov_high(0, 4),
    t_bl(ADDR_RESET_20220228),
    "early_done",
    t_pop([4], pc=True),

    # ------------------------------------------------------------------
    # 4) fn_timer_guard_late(): hooked at 0x01025E82, 0x0101A26E, 0x0101A2A2
    # ------------------------------------------------------------------
    "fn_timer_guard_late",
    t_push([4], lr=True),
    t_bl_lbl("fn_reset_guard_common"),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_NE, "late_done"),
    t_bl(ADDR_RESET_CLEAN),
    "late_done",
    t_pop([4], pc=True),

    # ------------------------------------------------------------------
    # 5) fn_bb_guard(): hooked at 0x0101A2C4 (replaces BL 0x0101E998)
    # ------------------------------------------------------------------
    "fn_bb_guard",
    t_push([4], lr=True),
    t_bl_lbl("fn_window_state"),
    t_cmp_imm8(0, 1),
    t_b_cond(COND_EQ, "bb_suppress"),
    t_cmp_imm8(0, 2),
    t_b_cond(COND_NE, "bb_stock"),
    t_bl_lbl("fn_finish_wake"),
    "bb_suppress",
    t_movs(0, 0),
    t_pop([4], pc=True),
    "bb_stock",
    t_bl(ADDR_GET_WAKEUP_FLAG),
    t_pop([4], pc=True),

    # ------------------------------------------------------------------
    # 6) fn_hid_connect(): hooked at 0x0101A526 (replaces BL 0x0102C2FC)
    # ------------------------------------------------------------------
    "fn_hid_connect",
    t_push([4], lr=True),
    t_bl(ADDR_HID_CB),
    t_ldr_pc(4, "STATE_RAM"),
    t_movs(0, 0),
    t_str_imm(0, 4, 12),         # clear cooldown once HID is up
    t_str_imm(0, 4, 20),         # clear grace once HID is up
    t_ldr_imm(0, 4, 4),
    t_ldr_pc(1, "ARMED_MAGIC"),
    t_cmp_reg(0, 1),
    t_b_cond(COND_NE, "hid_done"),
    t_bl_lbl("fn_close_wake"),
    "hid_done",
    t_pop([4], pc=True),

    # ------------------------------------------------------------------
    # 7) fn_skip_s1_wake(): hooked at 0x0101A272, 0x0101A2A6, 0x0101A322
    # ------------------------------------------------------------------
    "fn_skip_s1_wake",
    t_push([4], lr=True),
    t_bl_lbl("fn_reset_guard_common"),
    t_cmp_imm8(0, 0),
    t_b_cond(COND_NE, "skip_s1_done"),
    t_bl(ADDR_S1_WAKE_FAIL),
    "skip_s1_done",
    t_pop([4], pc=True),
]

pool = {
    "NV_BASE":             0x0107E000,
    "MAC_W0":              0x050FCE71,
    "MAC_W1":              0x0000C848,
    "HH_WORD":             0x00004848,
    "ADV_W0":              adv_words[0],
    "ADV_W1":              adv_words[1],
    "ADV_W2":              adv_words[2],
    "ADV_W3":              adv_words[3],
    "ADV_W4":              adv_words[4],
    "ADV_W5":              adv_words[5],
    "ADV_W6":              adv_words[6],
    "ADV_W7":              adv_words[7],
    "IPC_ACK":             0x0002000C,
    "TIMEOUT_500":         0x000001F4,
    "STATE_RAM":           STATE_RAM,
    "ARMED_MAGIC":         ARMED_MAGIC,
    "COOLDOWN_MAGIC":      COOLDOWN_MAGIC,
    "GRACE_MAGIC":         GRACE_MAGIC,
    "WINDOW_MS":           WINDOW_MS,
    "COOLDOWN_MS":         COOLDOWN_MS,
    "GRACE_MS":            GRACE_MS,
    "PWR_BIT20":           1 << 20,
    "ADDR_STOCK_BLE_NAME": ADDR_STOCK_BLE_NAME,
    "ADDR_UID_RAM":        ADDR_UID_RAM,
    "ADDR_BT_PEND_FLAGS":  ADDR_BT_PEND_FLAGS,
    "ADDR_ERR_CNT":        ADDR_ERR_CNT,
}


def _find_thumb_objdump():
    if os.path.exists("/usr/bin/objdump"):
        probe = subprocess.run(
            ["/usr/bin/objdump", "--help"], capture_output=True, text=True
        )
        if "--triple" in probe.stdout:
            return ["/usr/bin/objdump", "--triple=thumbv6m-none-eabi", "-d"]
    for exe in ("llvm-objdump", "arm-none-eabi-objdump"):
        p = shutil.which(exe)
        if p:
            if "llvm" in exe:
                return [p, "--triple=thumbv6m-none-eabi", "-d"]
            return [p, "-marm", "-Mforce-thumb", "-d"]
    return None


def _verify_thumb_code(code_bytes, base_addr, disasm_cmd=None):
    """Assemble minimal ARM ELF and check Thumb decoding when an ARM disassembler exists."""
    if disasm_cmd is None:
        return None
    shstr = b"\x00.text\x00.shstrtab\x00"
    code_off = 52
    shstr_off = code_off + len(code_bytes)
    pad = (-shstr_off) & 3
    shoff = shstr_off + len(shstr) + pad
    ehdr = struct.pack(
        "<16sHHIIIIIHHHHHH",
        b"\x7fELF\x01\x01\x01" + b"\x00" * 9,
        2, 40, 1, base_addr | 1, 0, shoff, 0, 52, 0, 0, 40, 3, 2,
    )
    sh0 = struct.pack("<10I", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    sh1 = struct.pack("<10I", 1, 1, 6, base_addr, code_off, len(code_bytes), 0, 0, 2, 0)
    sh2 = struct.pack("<10I", 7, 3, 0, 0, shstr_off, len(shstr), 0, 0, 1, 0)
    with tempfile.NamedTemporaryFile(suffix=".elf") as tmp:
        tmp.write(ehdr + code_bytes + shstr + (b"\x00" * pad) + sh0 + sh1 + sh2)
        tmp.flush()
        res = subprocess.run(disasm_cmd + [tmp.name], capture_output=True, text=True, check=True)
    lines = [l for l in res.stdout.splitlines() if re.match(r"^\s*[0-9a-f]+:", l)]
    bad_toks = ("udf", "trap", "<unknown>", ".short", ".word", ".byte", "invalid")
    bad = [l for l in lines if any(tok in l.lower() for tok in bad_toks)]
    _require(len(lines) > 0 and not bad, f"Invalid Thumb sequence count: {len(bad)}")
    first_addr = int(lines[0].split(":", 1)[0].strip(), 16)
    last_addr = int(lines[-1].split(":", 1)[0].strip(), 16)
    _require(first_addr == base_addr and last_addr >= base_addr + len(code_bytes) - 4,
             f"Disassembly span mismatch: 0x{first_addr:x}..0x{last_addr:x}")
    return len(lines)


def _load_cryptdo():
    crypt_path = os.path.join(HERE, "8cryptdo.py")
    spec = importlib.util.spec_from_file_location("cryptdo", crypt_path)
    crypt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crypt)
    return crypt


def _encrypt_payload(raw_bytes):
    crypt = _load_cryptdo()
    cipher = crypt.CIPHERS["yichip"]
    enc_dat = crypt.build_section(
        raw_bytes, cipher, version=111, addr=0x01018000, length=len(raw_bytes), pid=0
    )
    enc_body = enc_dat[crypt.HEADER_SIZE:]
    secs = crypt.parse_sections(enc_dat)
    _require(len(secs) == 1, f"Expected 1 encrypted section, got {len(secs)}")
    _require(crypt.decrypt_section(enc_dat, secs[0], cipher) == raw_bytes,
             "8cryptdo roundtrip decryption mismatch")
    _require(len(enc_body) == len(raw_bytes),
             f"Encrypted body size mismatch: {len(enc_body)} != {len(raw_bytes)}")
    return enc_dat, enc_body


def _write_encrypted(raw_bytes, out_dir):
    enc_dat, enc_body = _encrypt_payload(raw_bytes)
    dat_path = os.path.join(out_dir, "v22_enc.dat")
    body_path = os.path.join(out_dir, "v22_enc_body.bin")
    with open(dat_path, "wb") as f:
        f.write(enc_dat)
    with open(body_path, "wb") as f:
        f.write(enc_body)
    return dat_path, enc_dat, body_path, enc_body


def _build_hooks(labels):
    return [
        (0x0101B880, 0x0101B368, labels["fn_boot_init"],          "boot_init"),
        (0x01021A3E, 0x010191F0, labels["fn_on_shake"],           "shake"),
        (0x01021A6A, 0x01026E4C, labels["fn_on_tick"],            "tick"),
        (0x01025E64, 0x0101BB5C, labels["fn_timer_guard_early"],  "timer_acl"),
        (0x01025E76, 0x0101BB5C, labels["fn_timer_guard_early"],  "timer_early"),
        (0x01025E82, 0x01026358, labels["fn_timer_guard_late"],   "timer_late"),
        (0x0101A26E, 0x01026358, labels["fn_timer_guard_late"],   "err_rst_a"),
        (0x0101A2A2, 0x01026358, labels["fn_timer_guard_late"],   "err_rst_b"),
        (0x0101A2C4, 0x0101E998, labels["fn_bb_guard"],           "bb_guard"),
        (0x0101A526, 0x0102C2FC, labels["fn_hid_connect"],        "hid_connect"),
        (0x0101A272, 0x0102855C, labels["fn_skip_s1_wake"],       "s1_wake_a"),
        (0x0101A2A6, 0x0102855C, labels["fn_skip_s1_wake"],       "s1_wake_b"),
        (0x0101A322, 0x0102855C, labels["fn_skip_s1_wake"],       "s1_wake_c"),
    ]


def patch_stock_image(stock_bytes, disasm_cmd=None, verbose=True):
    stock = bytearray(stock_bytes)
    _require(len(stock) == 131072, f"Expected 131072 B stock dump, got {len(stock)} B")

    module_bytes, labels = assemble(BASE, prog, pool)
    code_size = sum(
        4 if (isinstance(x, tuple) and x[0] in ("bl", "bl_lbl"))
        else (2 if isinstance(x, tuple) else len(x))
        for x in prog if not isinstance(x, str)
    )
    if verbose:
        print(
            f"Module size: {len(module_bytes)} bytes (code {code_size} bytes) "
            f"(0x{BASE:07x}..0x{BASE + len(module_bytes):07x})"
        )
        for k in (
            "fn_boot_init",
            "fn_window_state",
            "fn_check_state_timer",
            "fn_restore_ble_identity",
            "fn_close_wake",
            "fn_finish_wake",
            "fn_reset_guard_common",
            "fn_on_shake",
            "fn_on_tick",
            "fn_timer_guard_early",
            "fn_timer_guard_late",
            "fn_bb_guard",
            "fn_hid_connect",
            "fn_skip_s1_wake",
        ):
            print(f"  {k:24s}: 0x{labels[k]:07x}")

    mod_off = BASE - 0x01018000
    _require(all(b == 0xFF for b in stock[mod_off:mod_off + len(module_bytes)]),
             "Code cave not clean 0xFF!")

    for hook_addr, expected_old_target, new_target, name in _build_hooks(labels):
        off = hook_addr - 0x01018000
        expected_bl, _ = assemble_raw(hook_addr, [t_bl(expected_old_target)], {})
        _require(stock[off:off + 4] == expected_bl,
                 f"Original instruction mismatch at 0x{hook_addr:07x} ({name})")
        patch_bl, _ = assemble_raw(hook_addr, [t_bl(new_target)], {})
        _require(len(patch_bl) == 4, f"Invalid BL length at 0x{hook_addr:07x}")
        if disasm_cmd:
            _require(_verify_thumb_code(patch_bl, hook_addr, disasm_cmd) == 1,
                     f"Hook disassembly check failed at 0x{hook_addr:07x} ({name})")
        stock[off:off + 4] = patch_bl
        if verbose:
            print(f"  hook {name:11s} @ 0x{hook_addr:07x} -> BL 0x{new_target:07x}")

    if disasm_cmd:
        n_insns = _verify_thumb_code(module_bytes[:code_size], BASE, disasm_cmd)
        if verbose:
            print(f"Thumb check: ok ({n_insns} instructions verified, 0 invalid)")
    elif verbose:
        print("Thumb check: skipped (no ARM Thumb objdump installed; encoder checks passed)")

    stock[mod_off:mod_off + len(module_bytes)] = module_bytes
    return bytes(stock), module_bytes, code_size, labels


def run_selftest():
    """Offline self-test requiring no proprietary firmware dump or hardware."""
    # 1. Verify encoder bounds checks remain active even under `python3 -O`
    try:
        t_mov_high(16, 0)
        raise RuntimeError("t_mov_high failed to reject r16")
    except ValueError:
        pass
    try:
        t_movs(8, 0)
        raise RuntimeError("t_movs failed to reject r8")
    except ValueError:
        pass

    # 2. Assemble module and verify exact size & Thumb decoding
    module_bytes, labels = assemble(BASE, prog, pool)
    _require(len(module_bytes) == 824, f"Unexpected module size: {len(module_bytes)}")

    # 3. Synthesize a clean 128 KB image with expected stock hook BLs + 0xFF cave
    synth = bytearray(b"\xFF" * 131072)
    for hook_addr, expected_old_target, _, _ in _build_hooks(labels):
        off = hook_addr - 0x01018000
        expected_bl, _ = assemble_raw(hook_addr, [t_bl(expected_old_target)], {})
        synth[off:off + 4] = expected_bl

    disasm_cmd = _find_thumb_objdump()
    patched, _, code_size, _ = patch_stock_image(synth, disasm_cmd=disasm_cmd, verbose=False)
    _require(len(patched) == 131072 and code_size == 720, "Synthetic patch size mismatch")

    # 4. Verify 8cryptdo roundtrip on synthetic patched image
    enc_dat, enc_body = _encrypt_payload(patched)
    _require(len(enc_dat) == 131100 and len(enc_body) == 131072, "Encrypted output length mismatch")

    # 5. Verify negative checks reject dirty cave, mismatched hook, and wrong size
    bad_cave = bytearray(synth)
    bad_cave[BASE - 0x01018000] = 0x00
    try:
        patch_stock_image(bad_cave, disasm_cmd=None, verbose=False)
        raise RuntimeError("Dirty cave was not rejected")
    except RuntimeError as e:
        _require("Code cave not clean" in str(e), f"Unexpected error: {e}")

    bad_hook = bytearray(synth)
    bad_hook[0x0101B880 - 0x01018000] ^= 0xFF
    try:
        patch_stock_image(bad_hook, disasm_cmd=None, verbose=False)
        raise RuntimeError("Corrupted hook was not rejected")
    except RuntimeError as e:
        _require("Original instruction mismatch" in str(e), f"Unexpected error: {e}")

    try:
        patch_stock_image(b"\xFF" * 64, disasm_cmd=None, verbose=False)
        raise RuntimeError("Short image was not rejected")
    except RuntimeError as e:
        _require("Expected 131072 B" in str(e), f"Unexpected error: {e}")

    print(
        f"selftest ok: module={len(module_bytes)} B (code={code_size} B), "
        f"hooks=13, 8cryptdo roundtrip=ok, negative guards=ok, "
        f"thumb_objdump={'ok' if disasm_cmd else 'skipped'}"
    )


def main():
    parser = argparse.ArgumentParser(description="Build 8BitDo 80NA fw 1.11 Switch-2 wake v22 image.")
    parser.add_argument(
        "-i", "--input",
        default=os.path.join(HERE, "backups", "pre-flash-stock-v2.bin"),
        help="Path to clean stock 1.11 plaintext dump (131072 bytes).",
    )
    parser.add_argument(
        "-o", "--out-dir",
        default=HERE,
        help="Output directory for fw111_v22.bin, v22_enc.dat, and v22_enc_body.bin.",
    )
    parser.add_argument(
        "--allow-unknown-stock",
        action="store_true",
        help="Proceed even if input SHA-256 differs from verified 80NA 1.11 stock (hook opcodes still verified).",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run offline self-test (encoder, synthetic patch, 8cryptdo roundtrip, negative checks).",
    )
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not os.path.isfile(args.input):
        sys.stderr.write(
            f"Error: stock firmware dump not found: {args.input}\n"
            f"Back up your controller's stock 1.11 firmware first with:\n"
            f"  ./boot/flash-firmware.sh --backup {args.input}\n"
        )
        sys.exit(1)

    with open(args.input, "rb") as f:
        stock = f.read()

    _require(len(stock) == 131072, f"Expected 131072 B stock dump, got {len(stock)} B")
    in_sha = hashlib.sha256(stock).hexdigest()
    if in_sha != EXPECTED_STOCK_SHA256:
        if not args.allow_unknown_stock:
            sys.stderr.write(
                f"Error: input SHA-256 ({in_sha}) != verified stock 1.11 ({EXPECTED_STOCK_SHA256}).\n"
                f"If this is a valid stock 1.11 dump variant, re-run with --allow-unknown-stock.\n"
            )
            sys.exit(2)
        print(f"Warning: non-standard input SHA-256 ({in_sha}); relying on opcode checks.")

    disasm_cmd = _find_thumb_objdump()
    raw_bytes, _, _, _ = patch_stock_image(stock, disasm_cmd=disasm_cmd, verbose=True)

    os.makedirs(args.out_dir, exist_ok=True)
    out_bin = os.path.join(args.out_dir, "fw111_v22.bin")
    with open(out_bin, "wb") as f:
        f.write(raw_bytes)

    dat_path, enc_dat, body_path, enc_body = _write_encrypted(raw_bytes, args.out_dir)

    print(f"{out_bin} sha256: {hashlib.sha256(raw_bytes).hexdigest()}")
    print(f"{dat_path} ({len(enc_dat)} bytes) sha256: {hashlib.sha256(enc_dat).hexdigest()}")
    print(f"{body_path} ({len(enc_body)} bytes) sha256: {hashlib.sha256(enc_body).hexdigest()}")


if __name__ == "__main__":
    main()
