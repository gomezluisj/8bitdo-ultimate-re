# REPORT — Validador de imagen 8BitDo Ultimate 1 (80NA) · RE deep dive 2026-11-08

**Estado proyecto:** stock restaurado y verificado (control vivo, app mode `2dc8:3106`).
**Pregunta central:** ¿por qué toda imagen parcheada (v5, v6.1) no ejecuta NI UNA instrucción, y qué regenerar para que corra?

---

## 0. RESOLUCIÓN (2026-11-08, serie discriminatoria cerrada — 7 flashes en vivo)

**El validador global NO existe.** El asesino de v5/v6.1 es la **operación ERASE del driver NV en early-boot**.

| Flash | Cambio vs stock | Resultado |
|---|---|---|
| H5 | 1 byte dead-padding | bootea |
| v6.2a | módulo 536B como datos (huérfano) | bootea |
| v6.2b | hook→trampolín BL container | bootea |
| v6.3a-r3 | hook→read_NV + container (r0-r3 preservados) | bootea |
| v6.3b-r2 | + program() 4B 0xAA @0x10378f0 (guard FF) | bootea |
| v6.3c-r3 | + erase(0x1037000), tripwire 0x55 @0x1036000 (unidad separada) | **muere** |
| v6.1 | read+erase+program+radio | muere |

Causalidad cerrada: todo el camino hook→módulo→container→read→program es seguro; solo el erase mata. **Hipótesis confirmada (2026-11-08):** el erase cae dentro de la ventana XIP mapeada por hardware — borrar cualquier sector `0x1037000`.. while fetching XIP cuelga el QSPI, independiente del contenido (ambas unidades verificadas virgin FF en stock). El stock sí borra `0x107e000` (FUERA de la ventana) en re-pairing y sobrevive. REEMPLAZA mi hipótesis 'scheduler no maduro'.

Además: el misterio E2 queda resuelto — el tripword v6.1 @0x1037800 estaba DENTRO del sector borrado; el módulo SÍ corrió y su propio erase destruyó su evidencia. v5 muere por radio en boot-init (secuencia aún arrancando). Ambos puntos integrados.

Forense pendiente próxima sesión boot: byte @0x1036000 debe ser 0x55 (programa pre-erase que sobrevivió).

Camino v6.4 (sonda real): **persist deferred/post-init** — erase+program desde hook site más tardío (scheduler maduro) o encolados al task loop; el hook temprano solo marca la intención en RAM.

---

## [HISTÓRICO refutado por §0] 1. Evidencia firmada por experimentos (live verification)

| # | Experimento | Resultado | Consecuencia |
|---|---|---|---|
| E1 | Flash v5 (sonda, hook @`0x101b880`) | LED sólido, sin BLE, NV intacta | app parcheada no corre |
| E2 | Flash v6.1 (tripwire first, checkpoint E ANTES de todo) | tripword `0x1037800` = **FF puro**, checkpoint E = FF, NV `0x107e000` **byte-idéntica** al pre-flash | el módulo ni siquiera ejecutó su primer PROG → **ni el primer read se hizo en código nuestro** (o ni siquiera se invocó) |
| E3 | Restaurar stock (`stock_enc.bin`, verify byte-perfecto) | control vivo instantáneo, app mode | el hardware y el mecanismo de flash están OK; el fallo no es físico |
| E4 | `config_dump2` (7-Nov) vs NV post-v6.1 | idéntico | nada escribió; no bootloop destructivo |

**Conclusión de E1+E2+E3:** existe un **validador de integridad de imagen** (ROM bootloader y/o early-boot de la app). Toda imagen con bytes modificados es rechazada **silenciosamente** (sin crash visible, el device solo cae a boot mode o muere). Los dos probes independientes con diseño anti-brick distinto compartieron el mismo destino porque el bloqueo es previo al código de la app.

## [HISTÓRICO refutado por §0] 2. Anatomía del mapa de flash (reconstruido)

```
0x00000000       ROM bootloader (64KB, dump parcial 32KB hasta 0x7f94 sin referencias a metadata)
0x10170000?/     (n/a)
0x01017000..0x01018000  METADATA FACTORY (4KB) — el updater oficial NO la toca
  +0x00: 12 B  fec95da3-2845e25f-8fac870c   ← desconocido (no md5/sha/crc32/adler del plaintext)
  +0x40: u32 0x6f = versión (111)           ← el `boot identify` lee aquí
  +0x60: ptr 0x01348a68 + halfwords (0x01b9d, 0x00a66, 0x00ba2, 0x00ba7)
  +0x80: ptr 0x01348a68 + 6 halfwords (0x00ad0,0x0c5b / 0x00a9b,0x0c80~ / 0x0abc,0x0c8e)
0x01018000..0x01038000  APP (128KB, cifrada en flash, XIP descifra al vuelo)
0x1037800 region        (dentro de la ventana XIP) — usado por nosotros como tripwire; FF-run real hasta 0x1038000
0x107e000        NV/pairing page (4KB) — slots pairing, config
```

- El dat oficial 1.11 = **una sola sección** (`0x01018000, 0x19800`, pid `0x6007`) → el updater nunca escribe la metadata factory.
- El dat v2.00 (Ultimate 2) = 2 secciones: loader-RAM @`0x40004000` (8.7KB, para el propio updater) + app 133632 B @`0x01018000`. Formato distinto (n=2, u32-aligned) — dos generaciones de formato Yichip.

## [HISTÓRICO refutado por §0] 3. Hipótesis del validador (ranked)

| # | Hipótesis | A favor | En contra | Coste de verificar |
|---|---|---|---|---|
| H1 | **CRC/hash de la app en la metadata factory**, calculado en el bootloader ROM al boot | región persistente en fábrica; exactamente el patrón Yichip/RT | el dat oficial no la actualiza, y el 1.11 FINAL instalado difiere del 1.11 Beta1 oficial (todos los bloques 4KB difieren) → el hash factory no correspondería a la app instalada **salvo** que la metadata la escribió el *updater* en el último upgrade | leer ROM completo (falta 32KB) y reversing el flujo de arranque |
| H2 | La app se auto-verifica (early-boot calcula hash de sí misma contra metadata) | la app referencia la región (literal `0x01017040` en 2 sitios) | el E2 muestra que nada corrió — pero el fallo puede ocurrir en el primer ciclo de CRT0 antes de main | disasm del vector/reset handler — *pendiente: los primeros words `0x47004859` no son un vector table estándar → formato Yichip propio (boot stub con jump table) aún sin decodificar* |
| H3 | La metadata es una sección cifrada adicional (clave/key-schedule factory) que la app usa; si falta el match, el XIP o el stub aborta | 12 B = un bloque cifrado plausible (SM4/DES) | requiere conocer el cifrador del stub | decodificar el boot stub (`0x59480047 0x00f06ff8...` = Thumb con saltos `e0xx` — patrón de "boilerplate con tabla de saltos computada") |
| H4 | Firmas ECDSA/RSA (pub-priv), imposible regenerar sin clave privada | 12 B es demasiado pequeño para RSA; para ECDSA r||s también | sería el fin de la ruta software | n/a hasta decodificar stub |
| H5 | **NO hay validador**; el fallo es otra clase (p.ej. el hook patch rompe una tabla de saltos por offset que el stub usa para saltar a la app; v5/v6.1 tocaron bytes de código real = el stub salta a una dirección corrupta) | el stub al inicio de la app (`0x47004859...`) usa **adds/slls con offsets literales** — código sensible a offsets; los dat oficiales de 1.11 beta1 vs stock FINAL difieren en todos los bloques → el stub no valida, **navega** | los offsets del stub apuntan a código dentro de los primeros 128 B; nuestro hook está en 0x101b880 (39KB adentro) — los offsets del stub no lo tocan | **El experimento A/B más barato: flash de una imagen con UN SO byte cambiado en el ÚLTIMO KB** (zona muerta al final, código no ejecutable). Si falla el boot → validador global (H1/H2/H3). Si bootea → validador es local/paginal y el hook site quedó tocado por algo más. |

**Nota crítica sobre H5:** nuestro patch toca exactamente 4 bytes (hook) + slot libre (FF→código) = **39KB lejos del stub de arranque**. Si el stub "navega" con offsets, no toca nuestro código. El A/B de H5 discrimina validador-global vs local con **1 ciclo de flash**.

## [HISTÓRICO refutado por §0] 4. Lo que ya está RE-engineered (activo, reutilizable)

- **Formato dat Yichip gen-1 (Ultimate 1):** hdr u16 ver + (addr u32, len u32, pid u16) + body SM4-encrypted; decrypt/encrypt deterministas (8cryptdo), roundtrip verificado.
- **Formato dat gen-2 (Ultimate 2):** multi-sección (u32 n; loader SRAM @0x40004000 + app), pid distinto (`0x6010`/`0x600f`), longitudes que cuadran con el file size al byte.
- **Protocolo boot HID (report id 5):** `BootReadFlash/BootWriteFlash/BootEraseFlash/BootGetPID` — mismo comando que usa el exe oficial `8Bitdo_Update.exe` (strings capturadas). `boot_linux.c` portable ready.
- **Boot stub de la app @0x1018000:** secuencia `ldr r0,[pc,#...] / bx` con 12-16 branches computadas (`e04b/e048/e045...`) — patrón "dispatch table" que hay que decodificar para entender dónde salta el boot.
- **Call-graph funcional (fw111):** task-loop `0x102a650→0x1028240→0x102be20→0x102caa0→0x102a650`, hook-site `0x101b880` dentro del loop (y boot-init), NV readers mapeados (5 sites), writer NV, reader NV (`0x102cfcc`, cpsid i + 5 callee).
- **NV page `0x107e000`:** layout slots pairing (4×0x1C) / record / status; dump y diff verificados.
- **Mecanismo anti-brick probado v6.1:** tripwire single-shot (unidad erase virgen `0x1037000`), checkpoints E/A/C/S/F/W fuera de la unidad erased, passthrough cero-flash — **APPROVED por adversarial review 2 rondas**, solo faltaba que el validador lo dejara correr.

## [HISTÓRICO refutado por §0] 5. El gap de conocimiento crítico (y cómo cerrarlo)

**Gap único:** *dónde y cómo se decide "esta imagen es legítima"*. Todo lo demás ya funciona.

Plan de cierre (ordenado por coste, todos sin flashear la app parcheada de nuevo):

1. **Dump completo del ROM** (64KB, con retries — el control está sano, solo se cayó por timeout): reversar el flujo ROM-boot→app-load para ver si calcula hash sobre la app. *(1 ciclo de USB, 0 flash)*
2. **Decodificar el boot stub** de la app (los primeros 128 B con tabla de saltos computada) → revela si la app valida su propia imagen (H2/H3) y contra qué. *(solo estático)*
3. **Experimento H5 A/B** (1 flash): imagen con 1 solo byte modificado en zona muerta final → discrimina validador global vs local/offset-based. Es el test más barato que separa las hipótesis restantes.
4. **Extraer la clave/ruta del cifrador de la metadata** si el stub confirma H3 (los 12 B descifrarían a algo predecible — p.ej. texto, versión, CRCs — con el material de la app misma).

**Coste estimado:** (1)-(2) horas de RE estático; (3) 1 ciclo de flash; (4) depende del (2). Riesgo de brick en (3): idéntico a los ya corridos (recovery probado 3×, control sano hoy).

## 6. Artefactos

| Artefacto | Uso |
|---|---|
| `backups/pre-flash-stock-v2.bin` sha256 `934ff2a6...` | stock verificado (recovery) |
| `backups/post_v61_full.bin` (0x67fe8 B) | app+vírgenes post-v6.1 (tripword FF evidencia) |
| `/tmp/low_region.bin`, `/tmp/rom.bin` (32KB parcial) | metadata factory + ROM parcial |
| `boot/dbg_read_low` (con retry) | herramienta dump extendido ready |
| `fw111_probe_v6.bin` / `probe_v61_enc_body.bin` | sonda v6.1 (APPROVED, lista si se resuelve el validador) |
| `reports/…` (este) |

---

## 7. Conclusión sobre borrado en ventana XIP (2026-11-08)

La serie v6.3 midió el mecanismo XIP, no 'early-boot'; v6.4 rediseñada erase-free (program-only, slots vírgenes @0x107e000+0x100..0x200, guard +0xE8, gate de shake real vía Try_WakeUpNs 0x10284f4). El v6.3d adicional ya no hace falta.
