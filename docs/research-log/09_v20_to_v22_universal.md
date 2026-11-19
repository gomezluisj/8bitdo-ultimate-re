# Evolución `v20` -> `v21` -> `v22` (fw `1.11`, `80NA` — Solución final universal)

Documentación de las tres iteraciones posteriores a [`v19`](08_v18_to_v19_reconnect.md) hasta la versión final [`../../build_v22.py`](../../build_v22.py), validada en consola Nintendo Switch 2 real con despertar por movimiento en el primer ciclo y reconexión directa Classic BT + HID sin reinicios prematuros.

---

## 1. De `v19` a `v22`: qué resolvió cada versión

| Versión | Cambio principal | Limitación observada / motivo de evolución |
|---|---|---|
| **`v20`** | Generaliza `v19` eliminando cualquier Console MAC embebida: `fn_on_shake()` lee NV Slot 0 (`0x0107E000`, `0x1C` B vía `0x0102CFCC`), verifica que `MAC[+6..+11]` no sea `00*6` ni `FF*6` y la inserta en tiempo de ejecución en `adv_31b[17..22]`. | Dependía aún de ticks crudos (escala variable `5..30 ms`) y de reinicio forzado (`0x0101BB5C`) tras el burst BLE. |
| **`v21`** | Cambia el cómputo de tiempo a milisegundos reales usando `poll_wait` (`0x010281C0`), introduce reconexión in-place sin `0x0101BB5C` (`fn_restore_ble_identity()` + Page Scan `0x0101AF70(0,1,0)` + `0x0101C180`) y `COOLDOWN_MS = 3000` (`WINDOW_MS = 1200`). | En hardware real Switch 2 requirió hasta 3 ciclos para despertar/conectar: `1200 ms` resultaba corto frente al intervalo de escaneo BLE, faltaba asegurar el bit 20 de `[0x000201B4]` tras reset USB cmd-7, `STATE_RAM` no se limpiaba en warm reset y faltaba una ventana de gracia post-wake para frenar resets tempranos y fallbacks Switch 1. |
| **`v22`** | Arreglo completo: limpieza de `STATE_RAM` al arranque (`fn_boot_init`), `WINDOW_MS = 2400 ms`, `COOLDOWN_MS = 1800 ms`, `GRACE_MS = 15000 ms`, bit 20 en `[0x000201B4]` vía `0x01026E98`, limpieza de `[0x00020582]`/`[0x000201E8]`, cancelación de timer `0x0101DD44`, orden correcto tick/LED y LED Home sólido en transición. | **Validado en Switch 2 real:** despertar inmediato en el primer ciclo y reconexión directa estable. |

---

## 2. Arquitectura exacta de `v22` ([`../../build_v22.py`](../../build_v22.py))

- **Base stock requerida:** dump plaintext limpio `80NA fw 1.11` (`131072` B cargados en `0x01018000`, `sha256`: `934ff2a60637ab517ce434affb274d68c065242801ac068e0ede42f35a315d3c`).
- **Code cave:** `0x01031A00..0x01031D38` — **`824` bytes** totales (`720` B código Thumb + `104` B literal pool; `311` instrucciones Thumb verificadas con `objdump`).
- **SRAM de estado (`STATE_RAM = 0x00026000`, `24` bytes):**
  - `+0x00`: `wake_tick`, `+0x04`: `ARMED_MAGIC` (`0x56323201`), ventana BLE `WINDOW_MS = 2400` ms.
  - `+0x08`: `cd_tick`, `+0x0C`: `COOLDOWN_MAGIC` (`0x56323243`), debounce post-wake `COOLDOWN_MS = 1800` ms.
  - `+0x10`: `grace_tick`, `+0x14`: `GRACE_MAGIC` (`0x56323247`), gracia de reconexión `GRACE_MS = 15000` ms (alineada con `v2.00`).
- **Plantilla BLE Switch 2 (`adv_31b_tpl`, `31` B):**
  - `0201061bff53050100037e0566200001810000000000000f00000000000000`
  - MAC BLE pública dummy `C8:48:05:0F:CE:71`, nombre `"HH"` (largo `4`), enviado por IPC `op 0x34 / ch 0x15`; los bytes `17..22` se copian dinámicamente desde NV Slot 0 (`0x0107E006..0x0107E00B`).

### 2.1 Rutinas del code cave

| Símbolo | Dirección | Función |
|---|---|---|
| `fn_boot_init` | `0x01031a00` | Pone a cero los `24` B de `STATE_RAM` en cada arranque frío o warm reset y delega en `0x0101B368`. |
| `fn_window_state` | `0x01031a20` | Devuelve `0` (desarmado), `1` (ventana `< 2400 ms` activa), `2` (ventana expirada vía `0x010281C0`). |
| `fn_check_state_timer` | `0x01031a44` | Helper genérico de temporizador (`COOLDOWN_MAGIC` / `GRACE_MAGIC`) sobre `0x010281C0`; desarma al expirar. |
| `fn_restore_ble_identity` | `0x01031a6c` | Restaura nombre BLE stock desde `0x01030E8C` (`len=0x0E`) y MAC BLE derivada de UID `[0x00020000..+5]`. |
| `fn_close_wake` | `0x01031ab4` | Desarma ventana (`ARMED_MAGIC=0`), limpia `[0x0002fff8]` (`0x0101BFFC`), limpia wakeup flag (`0x010271C0`), detiene `HH` adv (`0x0101AF70(0,0,0)`), restaura identidad BLE y fija LED Home sólido (`0x01026E4C(2)`). |
| `fn_finish_wake` | `0x01031adc` | Llama `fn_close_wake()`, limpia `[0x000201E8]` y `[0x00020582]`, inicia timers de cooldown (`1800 ms`) y gracia (`15000 ms`), fija bit 20 vía `0x01026E98(1<<20)`, activa Page Scan (`0x0101AF70(0,1,0)`) y lanza `0x0101C180`. |
| `fn_reset_guard_common` | `0x01031b14` | Si ventana activa -> suprime reset (`1`); si ventana expiró -> ejecuta `fn_finish_wake()` y suprime; si no -> consulta `GRACE_MS`. |
| `fn_on_shake` | `0x01031b36` | Respeta cooldown (`1800 ms`); si está emparejado en NV Slot 0, cancela timer `6s` (`0x0101DD44`), limpia gracia/`[0x000201E8]`/`[0x00020582]`, envía `HH` + `0x0553` con MAC de consola por IPC `0x34/0x15` y arma `ARMED_MAGIC`. |
| `fn_on_tick` | `0x01031c4a` | Comprueba `fn_window_state()` antes del toggle de LED (`0x01026E4C`): si expiró (`2`), cierra con `fn_finish_wake()`; si no, ejecuta LED toggle normal. |
| `fn_timer_guard_early` | `0x01031c64` | Guardián sobre `0x0101BB5C` en puntos tempranos de reconexión/ACL. |
| `fn_timer_guard_late` | `0x01031c78` | Guardián sobre `0x01026358` en resets tardíos / error count. |
| `fn_bb_guard` | `0x01031c88` | Suprime lectura temprana de wakeup flag (`0x0101E998`) mientras corre el burst BLE y dispara `fn_finish_wake()` al expirar. |
| `fn_hid_connect` | `0x01031ca4` | Hook sobre callback HID (`0x0102C2FC`): limpia cooldown/gracia al conectar HID y cierra ventana si seguía armada. |
| `fn_skip_s1_wake` | `0x01031cc0` | Suprime los 3 llamadores de `0x0102855C` (fallback Switch 1) mientras `fn_reset_guard_common()` siga activo. |

### 2.2 Hooks en el firmware (`13` `BL` parcheados)

| Sitio | Instrucción stock reemplazada | Destino en `v22` | Rol |
|---|---|---|---|
| `0x0101B880` | `BL 0x0101B368` | `BL 0x01031a00` (`fn_boot_init`) | Limpieza de `STATE_RAM` en cada arranque |
| `0x01021A3E` | `BL 0x010191F0` | `BL 0x01031b36` (`fn_on_shake`) | Disparo universal `0x0553` al agitar |
| `0x01021A6A` | `BL 0x01026E4C` | `BL 0x01031c4a` (`fn_on_tick`) | Cierre exacto a `2400 ms` antes de LED |
| `0x01025E64` | `BL 0x0101BB5C` | `BL 0x01031c64` (`fn_timer_guard_early`) | Supresión reset ACL temprano |
| `0x01025E76` | `BL 0x0101BB5C` | `BL 0x01031c64` (`fn_timer_guard_early`) | Supresión reset timer temprano |
| `0x01025E82` | `BL 0x01026358` | `BL 0x01031c78` (`fn_timer_guard_late`) | Supresión reset timer tardío |
| `0x0101A26E` | `BL 0x01026358` | `BL 0x01031c78` (`fn_timer_guard_late`) | Supresión reset por error A |
| `0x0101A2A2` | `BL 0x01026358` | `BL 0x01031c78` (`fn_timer_guard_late`) | Supresión reset por error B |
| `0x0101A2C4` | `BL 0x0101E998` | `BL 0x01031c88` (`fn_bb_guard`) | Guardián wakeup flag |
| `0x0101A526` | `BL 0x0102C2FC` | `BL 0x01031ca4` (`fn_hid_connect`) | Limpieza de estado al levantar HID |
| `0x0101A272` | `BL 0x0102855C` | `BL 0x01031cc0` (`fn_skip_s1_wake`) | Supresión fallback S1 A |
| `0x0101A2A6` | `BL 0x0102855C` | `BL 0x01031cc0` (`fn_skip_s1_wake`) | Supresión fallback S1 B |
| `0x0101A322` | `BL 0x0102855C` | `BL 0x01031cc0` (`fn_skip_s1_wake`) | Supresión fallback S1 C |

---

## 3. Verificación determinista y resultado en hardware

Salidas generadas por `python3 build_v22.py` desde el stock limpio `1.11` (`80NA`):

| Artefacto | Tamaño | SHA-256 |
|---|---|---|
| `fw111_v22.bin` | `131072` B | `6c76206d467795301433fa304c83b6b76ef1726888c78540ca094572cc724904` |
| `v22_enc.dat` | `131100` B | `bec50de51fb638963fcbf2b6ba6e562140508a199ead82475fc5d98a9cc5409c` |
| `v22_enc_body.bin` | `131072` B | `3adc7948a883ba1555cd5b8842102e1f9346b973f2e993387dfafc7f7e228cc4` |

- **Verificación de código:** `311` instrucciones Thumb verificadas (`0` inválidas) + roundtrip `8cryptdo.py decrypt` == `fw111_v22.bin`.
- **Hardware real:** flasheado vía `./boot/boot_macos flashe v22_enc_body.bin fw111_v22.bin` (`identify main=111 beta=0`, borrado `0x20000`, verificación desencriptada `131072/131072` OK) y validado en Nintendo Switch 2 real: despertar en el primer intento y conexión Bluetooth/HID estable.
