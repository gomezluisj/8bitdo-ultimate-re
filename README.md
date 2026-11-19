# 8bitdo-ultimate-re — Nintendo Switch 2 Shake-to-Wake (`v22`)

Reverse engineering and open-source firmware patcher adding **Nintendo Switch 2 BLE `0x0553` shake-to-wake and direct Cycle-1 Classic BT + HID reconnect** to the **8BitDo Ultimate Bluetooth Controller (`80NA`, firmware `1.11`, YiChip YCM1310)**.

> **Hardware validation:** `v22` has been built, verified byte-for-byte via XIP decrypted readback on real hardware (`main=111 beta=0`), and confirmed on Nintendo Switch 2 with immediate single-cycle wake-on-motion and stable Bluetooth connection.

---

## Warning & Compatibility

- **Supported device ONLY:** 8BitDo Ultimate Bluetooth Controller (`80NA`) running official **firmware `1.11`**.
- **Do NOT use on** Ultimate 2C, Ultimate 2 Bluetooth (`UM2BT`, PID `0x301B`), or any other controller/version. (`flash-firmware.sh` enforces `VID:PID 2dc8:3208`, bootloader `(main=111)`, and the `80NA` binary marker before erasing flash.)
- **No proprietary firmware binaries are distributed in this repository.** The patcher operates strictly on a clean stock `1.11` dump read from your own controller via USB BOOT mode.
- **Pair with your Switch 2 first on stock `1.11` (Slot 0).** `v22` reads your paired console's Bluetooth MAC address at runtime from NV Slot 0 (`0x0107E006..0x0107E00B`) — no console MAC needs to be hardcoded in source or firmware.

---

## Known Behaviors & Tradeoffs

- **Switch 2 wake replaces Switch 1 wake:** `v22` replaces the stock Nintendo Switch 1 shake-to-wake (`0x057E`) fallback with Switch 2 BLE `0x0553` wake. If you still use a Switch 1, shake-to-wake will no longer wake it from sleep while `v22` is installed (reverting anytime with `./boot/flash-firmware.sh --restore backups/pre-flash-stock-v2.bin` restores stock Switch 1 wake).
- **Never-paired / wiped NV Slot 0 (statically verified, hardware test welcome):** Firmware analysis (`0x0101E4B0`, `0x01025D04`, `0x0101D0E8`, `0x0102631C`, and `v22`'s `nv_unpaired` guard) confirms that shaking with a blank Slot 0 (`00*6` / `FF*6`) emits nothing and leaves normal first-time Switch pairing intact. Because hardware validation so far used an already-paired `80NA` unit, community confirmation on a never-paired controller is welcome.
- **Hold Pair steadily when switching consoles:** When re-pairing an already-paired controller to a second console, keep the controller steady while holding Pair. Shaking mid-pairing can trigger a `0x0553` wake attempt for the old Slot-0 MAC before the new pairing overwrites Slot 0 (`0x01021A10` skips shake only on `[0x00020176] == 2`, not Pair state `3`).
- **8BitDo Ultimate Software / remapping & profiles:** `v22` only hooks 13 BLE/wake/reconnect calls and does not modify profile NV storage, button remapping, macros, or the `80NA` / `main=111` identifiers. However, live testing with the 8BitDo Ultimate Software app has not been performed yet — community confirmation is welcome.

---

## Quick Start (macOS & Linux)

### Prerequisites
- Supported OS: **macOS** or **Linux** (no native Windows flasher is included in this repository).
- USB-C data cable.
- `python3` (standard library only; uses [`8cryptdo.py`](8cryptdo.py) included here).
- C compiler + OS USB HID dependencies:
  - **macOS:** Xcode or Command Line Tools (`clang`). If prompted by macOS Privacy & Security, allow **Input Monitoring** for your terminal so IOKit can access `"8BitDo Boot"` (`2dc8:3208`).
  - **Linux:** `cc`/`gcc` and Linux kernel headers (`<linux/hidraw.h>`). Run with `sudo`, or install the included `udev` rule once:
    ```bash
    sudo cp boot/99-8bitdo-boot.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules && sudo udevadm trigger
    ```
- Controller already on official **`fw 1.11`** and paired in Switch mode (`Slot 0`).

### 1. Enter USB BOOT mode
Hold **`LB + RB`** while plugging the USB-C cable into your computer. The controller enumerates as **`"8BitDo Boot"` (`VID 0x2DC8 : PID 0x3208`)**.

### 2. Identify & back up your controller flash
```bash
./boot/flash-firmware.sh --identify
./boot/flash-firmware.sh --backup backups/pre-flash-stock-v2.bin
```
This dumps the `128 KB` (`131072` B) application flash starting at `0x01018000` and checks its SHA-256. Keep `backups/pre-flash-stock-v2.bin` safe so you can restore stock anytime (verified clean stock backups are protected from accidental overwrite by `--backup`).

### 3. Build, verify & flash `v22`
```bash
# Optional offline build check first:
./boot/flash-firmware.sh --build-only

# Full flow (verifies BOOT mode, saves a pre-flash backup, builds v22, prompts confirmation, flashes & verifies readback):
./boot/flash-firmware.sh
```
The flasher erases `0x20000` bytes at `0x01018000`, writes the `8cryptdo` encrypted payload (`v22_enc_body.bin`), reads back through the XIP decrypted address window, verifies all `131072` bytes against `fw111_v22.bin`, and resets the controller automatically.

### 4. Revert to stock anytime
```bash
./boot/flash-firmware.sh --restore backups/pre-flash-stock-v2.bin
```

---

## Troubleshooting

- **Controller not detected (`no 8BitDo Boot (VID 2dc8 PID 3208) device found`):**
  - Unplug USB, hold **`LB + RB`** firmly, and plug the cable back in (use a data-capable USB-C cable, not a charge-only cable).
  - Verify USB enumeration: `lsusb | grep -i 2dc8` (Linux) or `ioreg -p IOUSB -l | grep -i -E "8BitDo|3208"` (macOS).
  - On Linux, verify `/dev/hidraw*` permissions (`sudo` or `boot/99-8bitdo-boot.rules`). On macOS, check **System Settings → Privacy & Security → Input Monitoring** for your terminal app.
- **`controller bootloader version does not report (main=111)`:**
  - Update your `80NA` controller to official firmware `1.11` using the 8BitDo Ultimate Software / Firmware Updater first, or stop if you have a different controller model.
- **Write or verify fails mid-flash:**
  - **Do NOT unplug USB.** The controller stays in USB BOOT mode after an error — immediately re-run `./boot/flash-firmware.sh` or restore your backup with `./boot/flash-firmware.sh --restore backups/pre-flash-stock-v2.bin`.

---

## Manual Usage & Offline Self-Test

```bash
# Offline self-test (no firmware dump or hardware required):
python3 build_v22.py --selftest

# Build plaintext + encrypted firmware images from a stock 1.11 dump:
python3 build_v22.py -i backups/pre-flash-stock-v2.bin

# Direct bootloader CLI (macOS: ./boot/boot_macos, Linux: ./boot/boot_linux):
./boot/boot_macos identify
./boot/boot_macos backup backups/my-dump.bin
./boot/boot_macos flashe v22_enc_body.bin fw111_v22.bin
```

Note on `objdump` verification: `build_v22.py` automatically runs Thumb disassembly checks (`311` instructions + `13` hooks, `0` invalid) if an ARM-capable `objdump` (`/usr/bin/objdump --triple=thumbv6m-none-eabi`, `llvm-objdump`, or `arm-none-eabi-objdump`) is installed; otherwise it proceeds using its built-in encoder bounds checks and `8cryptdo.py` roundtrip decryption check.

---

## Verified `v22` Checksums

| File | Size | SHA-256 |
|---|---|---|
| Clean stock `80NA fw 1.11` (`0x01018000`) | `131072` B | `934ff2a60637ab517ce434affb274d68c065242801ac068e0ede42f35a315d3c` |
| `fw111_v22.bin` (plaintext patched) | `131072` B | `6c76206d467795301433fa304c83b6b76ef1726888c78540ca094572cc724904` |
| `v22_enc.dat` (`28` B header + encrypted) | `131100` B | `bec50de51fb638963fcbf2b6ba6e562140508a199ead82475fc5d98a9cc5409c` |
| `v22_enc_body.bin` (encrypted flash body) | `131072` B | `3adc7948a883ba1555cd5b8842102e1f9346b973f2e993387dfafc7f7e228cc4` |

---

## Repository Layout & Documentation

- [`build_v22.py`](build_v22.py) — `v22` firmware patcher, `8cryptdo` image builder, and `--selftest`.
- [`thumb_asm.py`](thumb_asm.py) — Minimal ARM Thumb-1/2 encoder and single-pass assembler used by `build_v22.py`.
- [`8cryptdo.py`](8cryptdo.py) — 8BitDo YiChip/GD32 firmware encryption/decryption tool (MIT License, AeroModes).
- [`boot/`](boot/):
  - [`boot_proto.h`](boot/boot_proto.h) — Shared USB HID bootloader protocol (CRC-16, ACK checks, read/write/verify, CLI).
  - [`boot_macos.c`](boot/boot_macos.c) — Zero-dependency macOS IOKit USB HID transport (`VID 0x2DC8 / PID 0x3208`).
  - [`boot_linux.c`](boot/boot_linux.c) — Zero-dependency Linux `/dev/hidraw*` USB HID transport.
  - [`flash-firmware.sh`](boot/flash-firmware.sh) — Safe backup, build, verify, flash, and restore wrapper for macOS & Linux.
  - [`99-8bitdo-boot.rules`](boot/99-8bitdo-boot.rules) — Linux `udev` permissions rule for `2dc8:3208`.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Current English technical specification of `v22` (memory map, hooks, BLE `0x0553` payload, state machine).
- [`docs/research-log/`](docs/research-log/README.md) — Chronological reverse-engineering notes (`01`–`09`, Spanish).
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — Cross-platform CI (`ubuntu-latest` + `macos-latest`: `-Werror` C builds, `bash -n`, `--selftest`).
- [`LICENSE`](LICENSE) — MIT License.

---

## Credits & Disclosures

- **Third-party credits:**
  - [`8cryptdo.py`](8cryptdo.py) — MIT License, by AeroModes (https://github.com/aeromodes/8cryptdo).
  - USB HID bootloader protocol in [`boot/`](boot/) — based on `Alan-Gomes/8bitdo-macos`.
- **Security, Data & Monetization:** 100% free and open-source (MIT License, no monetization). Everything runs locally and offline on your machine with zero telemetry or data collection, and no copyrighted 8BitDo firmware binaries are distributed.
- **Generative AI Disclosure:** Reverse-engineering analysis, ARM Thumb patch authoring/verification, host tooling hardening, and documentation were developed with the assistance of generative AI coding tools, with final `v22` firmware behavior verified on physical hardware.
