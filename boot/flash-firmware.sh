#!/usr/bin/env bash
# Build, back up, flash, or restore Switch 2 shake-to-wake v22 firmware
# on an 8BitDo Ultimate Bluetooth Controller (80NA, fw 1.11).
#
# Put the controller into USB BOOT mode first:
#   Hold LB + RB while plugging in the USB-C cable ("8BitDo Boot", 2dc8:3208).
#
# Examples:
#   ./boot/flash-firmware.sh --identify
#   ./boot/flash-firmware.sh --backup
#   ./boot/flash-firmware.sh --build-only --stock backups/pre-flash-stock-v2.bin
#   ./boot/flash-firmware.sh
#   ./boot/flash-firmware.sh --restore backups/pre-flash-stock-v2.bin

set -euo pipefail

CALLER_PWD="$(pwd)"
BOOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$BOOT_DIR/.." && pwd)"

EXPECTED_STOCK_SHA256="934ff2a60637ab517ce434affb274d68c065242801ac068e0ede42f35a315d3c"
EXPECTED_V22_PLAIN_SHA256="6c76206d467795301433fa304c83b6b76ef1726888c78540ca094572cc724904"
EXPECTED_V22_BODY_SHA256="3adc7948a883ba1555cd5b8842102e1f9346b973f2e993387dfafc7f7e228cc4"
EXPECTED_FLASH_LEN=131072

usage() {
  cat <<'EOF'
Usage: ./boot/flash-firmware.sh [options]

Modes (default: build v22 from stock 1.11 dump and flash controller):
  --identify             Compile boot tool and print bootloader / version info.
  --backup [PATH]        Dump current 128 KB flash (@0x01018000) to PATH
                         (default: backups/pre-flash-stock-v2.bin or timestamped).
  --build-only           Build boot tool + v22 outputs without accessing USB.
  --restore PATH         Re-encrypt a plaintext 128 KB dump and flash it back.
  -h, --help             Show this help message and exit.

Options:
  --stock PATH           Clean stock 1.11 plaintext dump (131072 bytes).
                         Defaults to backups/pre-flash-stock-v2.bin if present,
                         or automatically dumps from the controller before flash.
  --out-dir DIR          Directory for fw111_v22.bin, v22_enc.dat, v22_enc_body.bin
                         (default: repository root).
  --allow-unknown-stock  Allow non-matching stock SHA-256 (opcode checks still run).
  -y, --yes              Skip interactive confirmation before erasing flash
                         (also honored via I_UNDERSTAND_BRICK_RISK=1).
EOF
}

resolve_path() {
  local p="$1"
  case "$p" in
    /*) printf '%s\n' "$p" ;;
    *)  printf '%s/%s\n' "$CALLER_PWD" "$p" ;;
  esac
}

sha256_of() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    python3 - "$1" <<'PY'
import hashlib, sys
with open(sys.argv[1], "rb") as f:
    print(hashlib.sha256(f.read()).hexdigest())
PY
  fi
}

file_size() {
  local os
  os="$(uname -s)"
  if [ "$os" = "Darwin" ]; then
    stat -f%z "$1"
  else
    stat -c%s "$1"
  fi
}

build_boot_tool() {
  local os src bin cc_bin tmp_bin dev_dir xcode_sdk clt_cc clt_sdk
  os="$(uname -s)"
  case "$os" in
    Darwin)
      src="$BOOT_DIR/boot_macos.c"
      bin="$BOOT_DIR/boot_macos"
      cc_bin="${CC:-clang}"
      if [ ! -x "$bin" ] || [ "$src" -nt "$bin" ] || [ "$BOOT_DIR/boot_proto.h" -nt "$bin" ]; then
        echo "Building boot tool for macOS ($bin)..."
        tmp_bin="${bin}.tmp.$$"
        rm -f "$tmp_bin"
        dev_dir="$(xcode-select -p 2>/dev/null || true)"
        xcode_sdk="$dev_dir/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
        clt_cc="/Library/Developer/CommandLineTools/usr/bin/clang"
        clt_sdk="/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"
        if "$cc_bin" -O2 -Wall -Wextra -framework IOKit -framework CoreFoundation \
             -o "$tmp_bin" "$src" 2>/dev/null; then
          :
        elif [ -d "$xcode_sdk" ] && \
             "$cc_bin" -O2 -Wall -Wextra -isysroot "$xcode_sdk" \
               -framework IOKit -framework CoreFoundation -o "$tmp_bin" "$src" 2>/dev/null; then
          :
        elif [ -x "$clt_cc" ] && [ -d "$clt_sdk" ] && \
             "$clt_cc" -O2 -Wall -Wextra -isysroot "$clt_sdk" \
               -framework IOKit -framework CoreFoundation -o "$tmp_bin" "$src"; then
          :
        else
          # Re-run default command visibly so caller sees exact compiler diagnostics.
          rm -f "$tmp_bin"
          "$cc_bin" -O2 -Wall -Wextra -framework IOKit -framework CoreFoundation \
            -o "$tmp_bin" "$src"
        fi
        mv -f "$tmp_bin" "$bin"
      fi
      ;;
    Linux)
      src="$BOOT_DIR/boot_linux.c"
      bin="$BOOT_DIR/boot_linux"
      cc_bin="${CC:-cc}"
      if ! command -v "$cc_bin" >/dev/null 2>&1; then
        cc_bin="gcc"
      fi
      if [ ! -x "$bin" ] || [ "$src" -nt "$bin" ] || [ "$BOOT_DIR/boot_proto.h" -nt "$bin" ]; then
        echo "Building boot tool for Linux ($bin)..."
        tmp_bin="${bin}.tmp.$$"
        rm -f "$tmp_bin"
        if ! "$cc_bin" -O2 -Wall -Wextra -o "$tmp_bin" "$src"; then
          rm -f "$tmp_bin"
          exit 1
        fi
        mv -f "$tmp_bin" "$bin"
      fi
      ;;
    *)
      echo "ERROR: unsupported OS '$os' (supported: Darwin, Linux)." >&2
      exit 1
      ;;
  esac
  BOOT_TOOL="$bin"
}

confirm_flash() {
  local prompt_msg="$1"
  if [ "$YES" = "1" ] || [ "${I_UNDERSTAND_BRICK_RISK:-}" = "1" ]; then
    return 0
  fi
  if [ ! -t 0 ]; then
    echo "Refusing to erase/flash non-interactively without --yes or I_UNDERSTAND_BRICK_RISK=1." >&2
    exit 2
  fi
  echo
  echo "WARNING: Firmware flashing erases and rewrites controller flash."
  echo "Do NOT unplug USB during erase/write/verify."
  printf "%s [type YES to proceed]: " "$prompt_msg"
  local reply=""
  read -r reply
  if [ "$reply" != "YES" ]; then
    echo "Aborted by user."
    exit 1
  fi
}

classify_dump() {
  local path="$1"
  local sz sha
  sz="$(file_size "$path")"
  if [ "$sz" -ne "$EXPECTED_FLASH_LEN" ]; then
    echo "ERROR: dump $path has size $sz bytes (expected $EXPECTED_FLASH_LEN)." >&2
    return 1
  fi
  sha="$(sha256_of "$path")"
  echo "  size:   $sz bytes"
  echo "  sha256: $sha"
  if [ "$sha" = "$EXPECTED_STOCK_SHA256" ]; then
    echo "  status: verified clean 80NA stock 1.11"
  elif [ "$sha" = "$EXPECTED_V22_PLAIN_SHA256" ]; then
    echo "  status: verified 80NA 1.11 v22"
  else
    echo "  status: non-standard / custom firmware image"
  fi
}

verify_80na_plaintext_marker() {
  local path="$1"
  local label="$2"
  if [ "$ALLOW_UNKNOWN_STOCK" -eq 1 ]; then
    return 0
  fi
  python3 - "$path" "$label" <<'PY'
import sys
path, label = sys.argv[1], sys.argv[2]
with open(path, "rb") as f:
    data = f.read()
if len(data) != 131072:
    raise SystemExit(f"ERROR: {label} ({path}) is {len(data)} bytes (expected 131072).")
marker = data[0x18E8C:0x18E92]
if marker != b"80NA\x00\x00":
    raise SystemExit(
        f"ERROR: {label} ({path}) is missing the 80NA identifier at offset 0x18E8C "
        f"(found {marker!r}). Refusing to proceed without --allow-unknown-stock."
    )
PY
}

verify_80na_111_boot() {
  local ident_out
  ident_out="$("$BOOT_TOOL" identify)"
  printf '%s\n' "$ident_out"
  if [ "$ALLOW_UNKNOWN_STOCK" -eq 1 ]; then
    return 0
  fi
  if ! printf '%s\n' "$ident_out" | grep -qE '\(main=111([^0-9]|$)'; then
    echo "ERROR: controller bootloader version does not report (main=111)." >&2
    echo "This patch targets 8BitDo Ultimate Bluetooth (80NA) firmware 1.11 only." >&2
    echo "Other 8BitDo models/versions share VID:PID 2dc8:3208; refusing to erase flash." >&2
    return 1
  fi
}

guard_stock_backup_clobber() {
  local target="$1"
  if [ -f "$target" ]; then
    local existing_sha
    existing_sha="$(sha256_of "$target")"
    if [ "$existing_sha" = "$EXPECTED_STOCK_SHA256" ]; then
      echo "ERROR: refusing to overwrite verified clean stock 1.11 backup at:" >&2
      echo "  $target" >&2
      echo "Pass a different filename (or omit the path to auto-timestamp)." >&2
      return 1
    fi
  fi
}

MODE="flash"
MODE_SET=0
BACKUP_PATH=""
STOCK_PATH=""
RESTORE_PATH=""
OUT_DIR="$REPO_DIR"
ALLOW_UNKNOWN_STOCK=0
YES=0

set_mode() {
  local new_mode="$1"
  if [ "$MODE_SET" -eq 1 ] && [ "$MODE" != "$new_mode" ]; then
    echo "ERROR: conflicting modes (--$MODE and --$new_mode cannot be combined)." >&2
    exit 1
  fi
  MODE="$new_mode"
  MODE_SET=1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --identify)
      set_mode "identify"
      shift
      ;;
    --backup)
      set_mode "backup"
      if [ "$#" -ge 2 ] && [ "${2#-}" = "$2" ]; then
        BACKUP_PATH="$(resolve_path "$2")"
        shift 2
      else
        shift
      fi
      ;;
    --build-only)
      set_mode "build-only"
      shift
      ;;
    --restore)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --restore requires a 128 KB plaintext firmware path." >&2
        exit 1
      fi
      set_mode "restore"
      RESTORE_PATH="$(resolve_path "$2")"
      shift 2
      ;;
    --stock)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --stock requires a path." >&2
        exit 1
      fi
      STOCK_PATH="$(resolve_path "$2")"
      shift 2
      ;;
    --out-dir)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --out-dir requires a directory." >&2
        exit 1
      fi
      OUT_DIR="$(resolve_path "$2")"
      shift 2
      ;;
    --allow-unknown-stock)
      ALLOW_UNKNOWN_STOCK=1
      shift
      ;;
    -y|--yes)
      YES=1
      shift
      ;;
    *)
      echo "ERROR: unknown option '$1'" >&2
      usage >&2
      exit 1
      ;;
  esac
done

BOOT_TOOL=""
build_boot_tool

if [ "$MODE" = "identify" ]; then
  "$BOOT_TOOL" identify
  exit 0
fi

if [ "$MODE" = "backup" ]; then
  mkdir -p "$REPO_DIR/backups"
  if [ -z "$BACKUP_PATH" ]; then
    if [ ! -e "$REPO_DIR/backups/pre-flash-stock-v2.bin" ]; then
      BACKUP_PATH="$REPO_DIR/backups/pre-flash-stock-v2.bin"
    else
      BACKUP_PATH="$REPO_DIR/backups/controller-flash-$(date +%Y%m%d-%H%M%S).bin"
    fi
  else
    mkdir -p "$(dirname "$BACKUP_PATH")"
  fi
  guard_stock_backup_clobber "$BACKUP_PATH"
  echo "Identifying controller..."
  "$BOOT_TOOL" identify
  echo "Backing up controller flash (0x01018000, 131072 bytes) -> $BACKUP_PATH ..."
  "$BOOT_TOOL" backup "$BACKUP_PATH"
  classify_dump "$BACKUP_PATH"
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required." >&2
  exit 1
fi

if [ -n "$STOCK_PATH" ] && [ ! -f "$STOCK_PATH" ]; then
  echo "ERROR: stock image not found: $STOCK_PATH" >&2
  exit 1
fi

if [ "$MODE" = "restore" ]; then
  if [ ! -f "$RESTORE_PATH" ]; then
    echo "ERROR: restore image not found: $RESTORE_PATH" >&2
    exit 1
  fi
  echo "Inspecting restore image: $RESTORE_PATH"
  classify_dump "$RESTORE_PATH"
  verify_80na_plaintext_marker "$RESTORE_PATH" "restore image"

  echo "Checking controller in BOOT mode..."
  verify_80na_111_boot

  mkdir -p "$REPO_DIR/backups"
  SAFETY_BAK="$REPO_DIR/backups/pre-restore-$(date +%Y%m%d-%H%M%S).bin"
  echo "Saving pre-restore flash backup -> $SAFETY_BAK ..."
  "$BOOT_TOOL" backup "$SAFETY_BAK"
  classify_dump "$SAFETY_BAK"

  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  ENC_DAT="$TMP_DIR/restore_enc.dat"
  ENC_BODY="$TMP_DIR/restore_enc_body.bin"

  echo "Encrypting restore payload with 8cryptdo.py (yichip, addr=0x01018000, version=111)..."
  python3 - "$REPO_DIR/8cryptdo.py" "$RESTORE_PATH" "$ENC_DAT" "$ENC_BODY" <<'PY'
import hashlib, importlib.util, sys
crypt_path, plain_path, dat_path, body_path = sys.argv[1:5]
spec = importlib.util.spec_from_file_location("cryptdo", crypt_path)
crypt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crypt)
with open(plain_path, "rb") as f:
    plain = f.read()
if len(plain) != 131072:
    raise SystemExit(f"Expected 131072 bytes, got {len(plain)}")
cipher = crypt.CIPHERS["yichip"]
enc_dat = crypt.build_section(plain, cipher, version=111, addr=0x01018000, length=len(plain), pid=0)
enc_body = enc_dat[crypt.HEADER_SIZE:]
secs = crypt.parse_sections(enc_dat)
assert len(secs) == 1 and crypt.decrypt_section(enc_dat, secs[0], cipher) == plain
with open(dat_path, "wb") as f:
    f.write(enc_dat)
with open(body_path, "wb") as f:
    f.write(enc_body)
print("  restore plaintext sha256:", hashlib.sha256(plain).hexdigest())
print("  restore enc body sha256: ", hashlib.sha256(enc_body).hexdigest())
PY

  confirm_flash "Restore $RESTORE_PATH to controller flash?"
  echo "Flashing and verifying against plaintext..."
  "$BOOT_TOOL" flashe "$ENC_BODY" "$RESTORE_PATH"
  echo
  echo "Restore complete. Controller has reset into restored firmware."
  exit 0
fi

# MODE is "build-only" or default "flash"
DEFAULT_STOCK="$REPO_DIR/backups/pre-flash-stock-v2.bin"

if [ -z "$STOCK_PATH" ] && [ -f "$DEFAULT_STOCK" ]; then
  STOCK_PATH="$DEFAULT_STOCK"
fi

if [ "$MODE" = "build-only" ]; then
  if [ -z "$STOCK_PATH" ] || [ ! -f "$STOCK_PATH" ]; then
    echo "ERROR: no stock 1.11 dump found for --build-only." >&2
    echo "Run one of:" >&2
    echo "  ./boot/flash-firmware.sh --backup backups/pre-flash-stock-v2.bin" >&2
    echo "  ./boot/flash-firmware.sh --build-only --stock /path/to/stock111.bin" >&2
    exit 1
  fi
  verify_80na_plaintext_marker "$STOCK_PATH" "stock image"
fi

PRE_FLASH_BACKUP=""
if [ "$MODE" = "flash" ]; then
  if [ -n "$STOCK_PATH" ]; then
    verify_80na_plaintext_marker "$STOCK_PATH" "stock image"
  fi
  echo "Checking controller in BOOT mode..."
  verify_80na_111_boot

  mkdir -p "$REPO_DIR/backups"
  if [ -z "$STOCK_PATH" ]; then
    PRE_FLASH_BACKUP="$REPO_DIR/backups/pre-flash-$(date +%Y%m%d-%H%M%S).bin"
    echo "No local stock 1.11 dump found; backing up current controller flash -> $PRE_FLASH_BACKUP ..."
    "$BOOT_TOOL" backup "$PRE_FLASH_BACKUP"
    classify_dump "$PRE_FLASH_BACKUP"
    cur_sha="$(sha256_of "$PRE_FLASH_BACKUP")"
    if [ "$ALLOW_UNKNOWN_STOCK" -ne 1 ] && [ "$cur_sha" != "$EXPECTED_STOCK_SHA256" ]; then
      echo "ERROR: controller flash does not match verified stock 1.11 ($EXPECTED_STOCK_SHA256)." >&2
      echo "If v22 or custom firmware is already installed, keep/pass a clean stock dump with --stock <path>." >&2
      exit 1
    fi
    if [ "$cur_sha" = "$EXPECTED_STOCK_SHA256" ] && [ ! -e "$DEFAULT_STOCK" ]; then
      cp "$PRE_FLASH_BACKUP" "$DEFAULT_STOCK"
      STOCK_PATH="$DEFAULT_STOCK"
      echo "Saved verified clean stock 1.11 dump -> $DEFAULT_STOCK"
    else
      STOCK_PATH="$PRE_FLASH_BACKUP"
    fi
  else
    PRE_FLASH_BACKUP="$REPO_DIR/backups/pre-flash-$(date +%Y%m%d-%H%M%S).bin"
    echo "Backing up current controller flash -> $PRE_FLASH_BACKUP ..."
    "$BOOT_TOOL" backup "$PRE_FLASH_BACKUP"
    classify_dump "$PRE_FLASH_BACKUP"
  fi
fi

echo "Building v22 firmware from $STOCK_PATH ..."
BUILD_ARGS=(-i "$STOCK_PATH" -o "$OUT_DIR")
if [ "$ALLOW_UNKNOWN_STOCK" -eq 1 ]; then
  BUILD_ARGS+=(--allow-unknown-stock)
fi
python3 "$REPO_DIR/build_v22.py" "${BUILD_ARGS[@]}"

OUT_PLAIN="$OUT_DIR/fw111_v22.bin"
OUT_BODY="$OUT_DIR/v22_enc_body.bin"

if [ ! -f "$OUT_PLAIN" ] || [ ! -f "$OUT_BODY" ]; then
  echo "ERROR: expected build outputs missing in $OUT_DIR." >&2
  exit 1
fi

PLAIN_SHA="$(sha256_of "$OUT_PLAIN")"
BODY_SHA="$(sha256_of "$OUT_BODY")"
PLAIN_SZ="$(file_size "$OUT_PLAIN")"
BODY_SZ="$(file_size "$OUT_BODY")"

if [ "$PLAIN_SZ" -ne "$EXPECTED_FLASH_LEN" ] || [ "$BODY_SZ" -ne "$EXPECTED_FLASH_LEN" ]; then
  echo "ERROR: invalid output sizes ($PLAIN_SZ, $BODY_SZ)." >&2
  exit 1
fi

if [ "$ALLOW_UNKNOWN_STOCK" -ne 1 ]; then
  if [ "$PLAIN_SHA" != "$EXPECTED_V22_PLAIN_SHA256" ] || [ "$BODY_SHA" != "$EXPECTED_V22_BODY_SHA256" ]; then
    echo "ERROR: built v22 SHA-256 mismatch!" >&2
    echo "  fw111_v22.bin:    $PLAIN_SHA (expected $EXPECTED_V22_PLAIN_SHA256)" >&2
    echo "  v22_enc_body.bin: $BODY_SHA (expected $EXPECTED_V22_BODY_SHA256)" >&2
    exit 1
  fi
fi

echo "Verified build outputs:"
echo "  fw111_v22.bin    sha256: $PLAIN_SHA"
echo "  v22_enc_body.bin sha256: $BODY_SHA"

if [ "$MODE" = "build-only" ]; then
  echo "Build-only complete."
  exit 0
fi

confirm_flash "Flash v22 firmware to controller @0x01018000?"
echo "Flashing encrypted payload and verifying decrypted readback..."
"$BOOT_TOOL" flashe "$OUT_BODY" "$OUT_PLAIN"

echo
echo "Done. Controller reset into v22 firmware."
echo "Next steps:"
echo "  1. Test Switch / Switch 2 shake-to-wake and direct reconnect."
echo "  2. Your backup is saved at: $PRE_FLASH_BACKUP"
echo "  3. To revert to stock anytime: ./boot/flash-firmware.sh --restore \"$STOCK_PATH\""
