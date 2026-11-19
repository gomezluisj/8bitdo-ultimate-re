# `v22` Technical Architecture (`80NA` fw `1.11`)

This document summarizes the final `v22` firmware patch implemented in [`build_v22.py`](../build_v22.py) for the **8BitDo Ultimate Bluetooth Controller (`80NA`, YiChip YCM1310, official firmware `1.11`)**.

For the chronological investigation notes (in Spanish), see [`docs/research-log/`](research-log/README.md).

---

## 1. Flash, XIP & Bootloader Model

- **Application flash region:** `0x01018000..0x01037FFF` (`131,072` B / `128 KB`).
- **On-flash encryption (XIP):** The YiChip YCM1310 stores application firmware **encrypted** in QSPI flash and decrypts it transparently on fetch/read via its XIP engine (`8cryptdo.py`, cipher `yichip`).
  - `boot_macos` / `boot_linux` `backup` reads through the decrypted XIP window (`0x01018000`) and produces plaintext `131,072` B dumps.
  - `flashe` erases `0x20000` bytes at `0x01018000`, writes the `8cryptdo`-encrypted body (`v22_enc_body.bin`), and verifies every byte by reading back through XIP and comparing against the plaintext `fw111_v22.bin`.
- **USB BOOT mode:** Hold `LB + RB` while plugging USB-C (`VID 0x2DC8 : PID 0x3208`, `"8BitDo Boot"`). Bootloader version metadata lives at `0x01017040` (`main=111 beta=0` on `80NA fw 1.11`), and the model identifier `"80NA\0\0"` sits at `0x01030E8C` (file offset `0x18E8C`).
- **Non-volatile pairing storage (NV):** `0x0107E000` stores 4 pairing records of `0x1C` (`28`) bytes each. In Switch mode, **Slot 0** (`0x0107E000..0x0107E01B`) holds the paired console's 6-byte Bluetooth MAC at offset `+6..+11` (`0x0107E006..0x0107E00B`).

---

## 2. Memory Footprint of `v22`

- **Code cave in flash:** `0x01031A00..0x01031D38` (`824` bytes total: `720` bytes of ARM Thumb-1/2 code across `14` routines + `104` bytes literal pool), placed in verified virgin `0xFF` flash space.
- **SRAM state block (`STATE_RAM`):** `0x00026000..0x00026018` (`24` bytes), situated cleanly between stock `1.11` globals (highest referenced static global `~0x00025434`) and the initial stack top (`0x0002FF00`):

| Offset | Field | Purpose |
|---|---|---|
| `+0x00` | `wake_tick` | Tick captured when the `0x0553` BLE burst starts |
| `+0x04` | `armed_magic` | `0x56323201` while the `2400` ms BLE wake burst is active |
| `+0x08` | `cd_tick` | Tick captured when the wake burst finishes |
| `+0x0C` | `cd_magic` | `0x56323243` during the `1800` ms post-wake shake debounce |
| `+0x10` | `grace_tick` | Tick captured when Classic BT reconnect starts |
| `+0x14` | `grace_magic` | `0x56323247` during the `15000` ms reconnect grace window |

---

## 3. Switch 2 BLE `0x0553` Wake & Direct Reconnect Flow

1. **Boot / warm-reset initialization (`fn_boot_init` @ `0x0101B880`):**
   - Zeroes all `24` bytes of `STATE_RAM` before calling stock BLE init (`0x0101B368`), preventing stale magic values across warm resets.
2. **Shake trigger (`fn_on_shake` @ `0x01021A3E`, replacing Switch 1 wake `0x010191F0`):**
   - Checks the `1800` ms post-wake cooldown (`fn_check_state_timer`). If active, clears `wakeup_flag` and keeps Home LED solid without restarting BLE.
   - Reads `28` bytes from NV Slot 0 (`0x0107E000`) via `0x0102CFCC` and checks bytes `+6..+11`. If all `0x00` or all `0xFF` (unpaired), restores `wakeup_flag = 0` and exits cleanly.
   - Cancels any pending 6-second reconnect timer (`0x0101DD44`) and clears retry/error counters (`0x000201E8`, `0x00020582`).
   - Builds the `31`-byte Switch 2 BLE manufacturer advertisement (`company 0x0553`, `flag = 0x81`, `PID 0x2066`), patching the 6-byte Console MAC dynamically into bytes `17..22`.
   - Temporarily sets BLE name to `"HH"` (`0x0101AC24`) and dummy BLE address `C8:48:05:0F:CE:71` (`0x0101AB6C`), transmits the `31`-byte payload via radio IPC (`op 0x34 / ch 0x15`, `0x01026880`) with a bounded ACK poll loop (`200` iterations / `500` ms timeout), enables BLE advertising (`radio_cfg(0, 0, 1)`), and arms `WINDOW_MS = 2400` real ms (measured via stock `poll_wait` `0x010281C0`).
3. **Window expiry & Classic BT handoff (`fn_on_tick` @ `0x01021A6A` → `fn_finish_wake` / `fn_close_wake`):**
   - Once `2400` ms elapse, `fn_close_wake` stops `"HH"` BLE advertising (`radio_cfg(0, 0, 0)`), restores factory `"80NA..."` BLE name and UID-derived BLE address (`fn_restore_ble_identity`), clears `[0x0002FFF8]` (`0x0101BFFC`) so `BT_CreatBtReconnect()` is not blocked, clears `wakeup_flag`, and restores solid Home LED ON.
   - `fn_finish_wake` arms `COOLDOWN_MS = 1800` ms and `GRACE_MS = 15000` ms, ensures power bit 20 is set via `0x01026E98(1 << 20)` (fixing reconnect after USB cmd-7 resets), enables Page Scan (`radio_cfg(0, 1, 0)`), and calls `BT_CreatBtReconnect()` (`0x0101C180`).
4. **Reconnect grace guards (`GRACE_MS = 15000` ms):**
   - **`fn_timer_guard_early` (`0x01025E64`, `0x01025E76`):** suppresses premature 6-second ACL/early resets (`0x0101BB5C`).
   - **`fn_timer_guard_late` (`0x01025E82`, `0x0101A26E`, `0x0101A2A2`):** suppresses premature late-timer and error-count resets (`0x01026358`).
   - **`fn_bb_guard` (`0x0101A2C4`):** masks `wakeup_flag` during baseband events while the BLE burst is active.
   - **`fn_skip_s1_wake` (`0x0101A272`, `0x0101A2A6`, `0x0101A322`):** suppresses Switch 1 wake fallback (`0x0102855C`) during active wake/grace windows.
   - **`fn_hid_connect` (`0x0101A526`):** once Switch 2 HID comes up (`0x0102C2FC`), clears cooldown and grace immediately (and closes any still-armed wake window).

---

## 4. Hook Table (`13` `BL` Hooks on Stock `80NA fw 1.11`)

| Hook Address | Stock Target | `v22` Handler | Role |
|---|---|---|---|
| `0x0101B880` | `0x0101B368` | `fn_boot_init` | Zero `STATE_RAM` on cold/warm reset |
| `0x01021A3E` | `0x010191F0` | `fn_on_shake` | NV Slot-0 read + `0x0553` BLE wake burst |
| `0x01021A6A` | `0x01026E4C` | `fn_on_tick` | Check `2400` ms expiry before LED toggle |
| `0x01025E64` | `0x0101BB5C` | `fn_timer_guard_early` | Shield premature ACL timeout reset |
| `0x01025E76` | `0x0101BB5C` | `fn_timer_guard_early` | Shield premature early reconnect reset |
| `0x01025E82` | `0x01026358` | `fn_timer_guard_late` | Shield premature late reconnect reset |
| `0x0101A26E` | `0x01026358` | `fn_timer_guard_late` | Shield error-count reset A |
| `0x0101A2A2` | `0x01026358` | `fn_timer_guard_late` | Shield error-count reset B |
| `0x0101A2C4` | `0x0101E998` | `fn_bb_guard` | Guard baseband wake-flag check |
| `0x0101A526` | `0x0102C2FC` | `fn_hid_connect` | Clear wake/cooldown/grace on HID connect |
| `0x0101A272` | `0x0102855C` | `fn_skip_s1_wake` | Suppress Switch 1 fallback A |
| `0x0101A2A6` | `0x0102855C` | `fn_skip_s1_wake` | Suppress Switch 1 fallback B |
| `0x0101A322` | `0x0102855C` | `fn_skip_s1_wake` | Suppress Switch 1 fallback C |
