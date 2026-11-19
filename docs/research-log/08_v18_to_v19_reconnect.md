# Diagnóstico de `v18` y solución final `v19` (fw `1.11`, `80NA` — Wake + Reconexión Switch 2)

**Estado final:** `v19` compilado, verificado (`objdump` + roundtrip `8cryptdo.py`), flasheado vía `boot_macos flashe` (readback `131072/131072` OK) y **confirmado en consola Nintendo Switch 2 real: despierta por movimiento y reconecta al primer intento**.

---

> **Nota:** Reporte histórico del hito `v19`. Las mejoras posteriores de confiabilidad y gestión de reconexión (`v20` -> `v22`, firmware final recomendado) están documentadas en [REPORT_V20_TO_V22.md](09_v20_to_v22_universal.md) y [../build_v22.py](../../build_v22.py).

## 1. Síntoma observado en pruebas reales con `v18`

Configuración de `v18`: `WINDOW_MS = 4000`, `ARMED_MAGIC = 0x56313801`, `6` hooks (`0x01021A3E`, `0x01021A6A`, `0x01025E76`, `0x01025E82`, `0x0101A2C4`, `0x0101A526`), `fw111_v18.bin` (`sha256`: `57f8e831759a338238ab4cd2dc8bbb1b07d5594cf66ab0c59138a264e3ef3d82`).

Resultado en pruebas repetidas sobre Switch 2:
1. **Intento 1:** encender control con `Home` -> agitar -> la Switch 2 despierta de forma fiable, **pero el control no conecta**; la consola vuelve a dormir.
2. **Intento 2:** continuar agitando -> el control vuelve a despertar la Switch 2 **y logra conectar**.

Conclusión: la ráfaga BLE `0x0553` (`"HH"`, `flag=0x81`, `C8:48:05:0F:CE:71`) ya despertaba de forma consistente, pero la transición post-wake hacia reconexión Classic BT quedaba bloqueada o interrumpida tras el primer ciclo.

---

## 2. Dos causas raíz verificadas en `backups/pre-flash-stock-v2.bin`

Inspección directa de Thumb, literales y cadenas `BL` sobre el dump limpio stock `1.11` (`pre-flash-stock-v2.bin`, con referencia cruzada contra `dec4_UM2BT_200.bin`):

### Causa 1: Marcador `[0x0002fff8] == 0x20221031` bloqueando `BT_CreatBtReconnect()`
- **Escritura en idle/sleep:** `0x010218D2 -> 0x0101BD70 -> 0x0101BD92: BL 0x01026EA8` escribe `0x20221031` en `[0x0002ffc0 + 0x38]` (`0x0002fff8`) antes de reiniciar hacia el modo de espera `"80NA"`.
- **Preservación en arranque `"80NA"`:** `0x0101B618` (llamado en `0x0102a830`) consulta `[0x0002fff8]` vía `0x0101E320` en `0x0101B624`. Cuando `[0x0002fff8] == 0x20221031` (`0x0101B62C: bne`) y su byte de estado es `0`, salta (`b 0x101b64c`) por encima de `0x0101B642: BL 0x0101BFFC`.
- **Salida temprana en `BT_CreatBtReconnect` (`0x01025D04`, llamadores `0x0101A386`, `0x0101C1AA`):**
  - `0x01025D26`: `BL 0x0101E320` lee `[0x0002fff8]`.
  - `0x01025D2A..0x01025D2E`: compara contra `0x20221031` (`bne 0x1025d3c`).
  - `0x01025D30..0x01025D3A`: si `[0x0002fff8] == 0x20221031` **y** `[0x000201aa] == 0` (modo Switch, `0x01025D36: bne 0x1025d3c`), ejecuta `add sp, #0x88; pop {r4, pc}` y **retorna sin iniciar paging Classic BT**.
- **Por qué fallaba `v18`:** en `fw111` stock, los únicos llamadores de `0x0101BFFC` (`clr_20221031`, pone `0` en `[0x0002fff8]`) eran `0x0101B642` y `0x0101FA36`. `v18` llamaba a `0x0101BB5C(0)` (que solo escribe `0x20220228` en `[0x0002fff4]` vía `0x01026FC4` y reinicia vía `0x01026358`) sin limpiar `[0x0002fff8]`, por lo que al reiniciar tras despertar la consola `BT_CreatBtReconnect()` seguía abortando temprano.

### Causa 2: Fallback Switch 1 (`0x0102855C`) disparándose durante el ciclo de Switch 2
- **Timeout inicial de paging:** `BT_CreatBtReconnect` fija `page_timeout = 0x12c0` (`4800` slots = `3.0 s` vía `movs r1, #0x4b; lsls r1, r1, #6` en `0x01025D6E..72`; idéntico en `v2.00` en `0x01028A6A..6E`).
- **Disparo de `0x0102855C` (`s1_wake_fail`):** al expirar/fallar la reconexión o llegar eventos BT de enlace/desconexión mientras `[0x0002057e] == 1`, el manejador HCI en `fw111` tiene exactamente **3 llamadores** de `0x0102855C`: `0x0101A272`, `0x0101A2A6` y `0x0101A322`.
- **Efecto de `0x0102855C`:** en `0x010285AE` envía `s1_wake_pkt` (`0x0102AA80`) y en `0x010285B4..0x010285B8` arma un temporizador (`0x0101DD54`) de `4000 ms` (`0x7d << 5`) apuntando a `0x0102AB29` (`0x0102AB28` Thumb) para resetear/reintentar flujo de Switch 1.
- **Referencia en `v2.00` (`dec4_UM2BT_200.bin`):** `0x0102BD28..0x0102BD58` consulta en `0x0102BD3A` el estado `0x0101FA8C` para **omitir** el fallback cuando el flujo de Switch 2 está en curso (y su orquestador `0x0101DA20` supervisa con un timer de `15000 ms`, `0x3a98`, en `0x01028B4D`).

---

## 3. Especificación exacta de `v19`

- **Base:** dump stock `1.11` (`131072` B, cargada en `0x01018000`).
- **Code cave:** `BASE = 0x01031A00`, tamaño ensamblado **`468` bytes** (`0x1031a00..0x1031bd4`; `402` bytes de instrucciones Thumb + `2` B alineación + `64` B literal pool de `16` words).
- **SRAM temporal:** `STATE_RAM = 0x00026000` (`[0] = start_tick`, `[4] = armed_magic`), `ARMED_MAGIC = 0x56313901`, **`WINDOW_MS = 4500`**.
- **Payload BLE (`adv_31b`, 31 B):** `0201061bff53050100037e056620000181<CONSOLE_MAC_6B>0f00000000000000`, MAC `C8:48:05:0F:CE:71`, nombre `"HH"` (largo `4`), IPC `op 0x34 / ch 0x15` con bucle de espera acotado a `200` iteraciones.

### Rutinas en el code cave

| Símbolo | Dirección | Función |
|---|---|---|
| `fn_window_state` | `0x1031a00` | Retorna `r0 = 0` (desarmado), `1` (activo `< 4500 ms`), `2` (expirado `>= 4500 ms`). |
| `fn_finish_wake` | `0x1031a26` | Desarma (`ARMED_MAGIC = 0`), llama `0x0101BFFC()` (`[0x0002fff8] = 0`), limpia `[0x0002057e] = 0` (`0x010271C0`), apaga BLE `0x0101AF70(0,0,0)` y llama `0x0101BB5C(0)` (`0x20220228` + reset). |
| `fn_on_shake` | `0x1031a4a` | Cancela timer previo (`0x0101DD44`), envía `"HH"` + MAC + `adv_31b` por `op 0x34 / ch 0x15`, habilita BLE `0x0101AF70(0,0,1)` y arma `STATE_RAM`. |
| `fn_on_tick` | `0x1031aee` | Mantiene LED (`0x01026E4C`) y si `fn_window_state() == 2` ejecuta `fn_finish_wake`. |
| `fn_timer_guard_early` | `0x1031b02` | En `0x01025E76`: preserva `r0` y bloquea el reset mientras la ventana está activa (`1`), ejecuta `fn_finish_wake` si expiró (`2`), o delega a `0x0101BB5C(r0)` si desarmado (`0`). |
| `fn_timer_guard_late` | `0x1031b20` | En `0x01025E82`: misma guarda delegando a `0x01026358` si desarmado. |
| `fn_bb_guard` | `0x1031b3a` | Si activo (`1`) devuelve `r0 = 0` para evitar fallback Switch 1 durante `"HH"`; si expirado (`2`) desarma y delega a `0x0101E998`. |
| `fn_hid_connect` | `0x1031b58` | Ejecuta `0x0102C2FC`; si estaba armado, desarma y llama `0x0101BFFC()` + `0x010271C0(0)` + `0x0101AF70(0,0,0)`. |
| `fn_skip_s1_wake` | `0x1031b82` | Si `fn_window_state() != 0`, retorna sin llamar a `0x0102855C`; si `== 0`, delega a `0x0102855C`. |

### Tabla exacta de los 9 hooks `BL` (arranque `0x0101B880 -> BL 0x0101B368` intacto)

| Hook | Dirección | Stock `BL` | Nuevo `BL` | Parche hex |
|---|---|---|---|---|
| `shake` | `0x01021A3E` | `0x010191F0` | `0x01031A4A` (`fn_on_shake`) | `f7f7d7fb -> 10f004f8` |
| `tick` | `0x01021A6A` | `0x01026E4C` | `0x01031AEE` (`fn_on_tick`) | `05f0eff9 -> 10f040f8` |
| `timer_early` | `0x01025E76` | `0x0101BB5C` | `0x01031B02` (`fn_timer_guard_early`) | `f5f771fe -> 0bf044fe` |
| `timer_late` | `0x01025E82` | `0x01026358` | `0x01031B20` (`fn_timer_guard_late`) | `00f069fa -> 0bf04dfe` |
| `bb_guard` | `0x0101A2C4` | `0x0101E998` | `0x01031B3A` (`fn_bb_guard`) | `04f068fb -> 17f039fc` |
| `hid_connect` | `0x0101A526` | `0x0102C2FC` | `0x01031B58` (`fn_hid_connect`) | `11f0e9fe -> 17f017fb` |
| `s1_wake_a` | `0x0101A272` | `0x0102855C` | `0x01031B82` (`fn_skip_s1_wake`) | `0ef073f9 -> 17f086fc` |
| `s1_wake_b` | `0x0101A2A6` | `0x0102855C` | `0x01031B82` (`fn_skip_s1_wake`) | `0ef059f9 -> 17f06cfc` |
| `s1_wake_c` | `0x0101A322` | `0x0102855C` | `0x01031B82` (`fn_skip_s1_wake`) | `0ef01bf9 -> 17f02efc` |

---

## 4. Verificación binaria, cifrado y flasheo ejecutados

1. **Desensamblado Thumb (`xcrun objdump -d --triple=thumbv6m-none-eabi`):**
   - Zona ejecutable (`0x01031A00..0x01031B92`, `402` B): `168` instrucciones válidas, `bad=0`.
   - Decodificación verificada de los `9` hooks `BL` + `0x0101B880 -> 0x0101B368`.
2. **Cifrado y roundtrip (`8cryptdo.py`):**
   - `fw111_v19.bin`: `131072` B · `sha256`: `08187e67ec83d479e3573a9aaee1d03f684c3ea9f0e3bc30d1125293a1be083c`
   - `v19_enc.dat`: `131100` B (`28` B cabecera + cuerpo) · `sha256`: `de404eb9b88ce58b4490bf8acbdb9d53a9d54e309250c1bfca11854aa765c09a`
   - `v19_enc_body.bin`: `131072` B · `sha256`: `4c0e844b4b79216457a1ba99e443afad56def14cfa1ac1aaf329d08998cbc71c`
   - Roundtrip `8cryptdo.py decrypt v19_enc.dat` == `fw111_v19.bin` byte a byte (`131072` B).
3. **Flasheo real en hardware (`./boot/boot_macos`):**
   - `identify`: `[found] VID 2dc8 PID 3208 "8BitDo Boot"`, `main=111 beta=0`.
   - `flashe v19_enc_body.bin fw111_v19.bin`: borró `0x20000` desde `0x1018000`, escribió `131072/131072`, verificó readback desencriptado `131072/131072` contra texto plano y reinició (`verified. resetting... done.`, exit `0`).
4. **Prueba final del usuario en Nintendo Switch 2:** despertar por agitado + conexión automática al primer intento funcionando correctamente.
