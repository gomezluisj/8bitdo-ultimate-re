# REPORT: S2 Wake — Deep Trace v2.00 + Reevaluación de Estrategias
Fecha: 2026-11-07 · Nota histórica de investigación

## Resumen ejecutivo

El wake S2 del **8BitDo Ultimate 2 BT** (v2.00, productos 80GQ/80ND) **NO es un beacon BLE**.
Es una secuencia de **HCI vendor commands** hacia el radio + **state machine de reconexión con timer de 15 s**.
La premisa original del port v1–v4 (beacon `0x0553` con PID `0x2066` emitido por adv_tx) queda **refutada por evidencia directa**.

**CORRECCIÓN DE REGISTRO:** `0x102dd30` (v2.00), identificado en PORT_SPEC v1.1 (en revisión previa) como "builder del beacon S2", es en realidad el **wake del dongle 2.4G**: construye `02|20|MAC-propia` (8 B) y transmite por `0x1030c34` con guard `mode==5` (protocolo propietario del dongle). El template `0553` no aparece en su flujo.

## 1. Cadena wake S2 real (v2.00), con evidencia

### 1.1 Trigger — el gesto
`0x1023b24` (llamada desde `0x102abb4` ← `0x10224cc`): handler de shake/IMU con debounce
(ventana `0xbb8`=3000 ms, poll `0x64`=100 ms, contadores en RAM `0x2020a`/`0x20214`).
Pre-checks antes de disparar: `0x101d0a0()` != 0 y `0x101fa98()` == 0. **Corrección post-review:** `0x101fa98` lee el flag RAM `0x205e6` — es un **guard one-shot "wake S2 ya disparado"**, puesto a 1 justo tras la llamada al orquestador (`0x1023d5a: movs r0,#1; bl 0x102a7a4`, y `0x102a7a4 = strb [0x205e6]`). No indica presencia/ausencia del récord.
→ llama al orquestador `0x101da20` @`0x1023d56`.

### 1.2 Orquestador `0x101da20`
1. `0x101faa4(dst)` — reader récord S2: `config_read(0x107e000, sp, 0x11c)` (página completa), check **magic `0x20250815` @ sp+0xe8**, copia `0x34` B a dst. Bail si ausente.
2. `0x101ae4c(0x1037d03, 4)` — **fn A**: vendor command **canal 4**, payload 4 B del struct identidad `0x1037c80` (zona BD-address/modelo 80GQ/80ND).
3. `0x101ad94(record+4)` — **wake_parse**: vendor command **canal 1**, opcode 1, packet `[1][len=6][ptr32→record+4]` — envía puntero a la **MAC de la consola (6 B)**; el consumidor desreferencia.
4. `0x101b098(record+0x12, record[0x11])` — **fn C**: vendor command **canal 0x15**, opcode `0x34`, payload variable = **sección del récord S2 con material de link** (`record+0x12`, largo tomado de `record[0x11]`, máx 0x22 B).
5. `0x101b264(0,0,1)` — radio_cfg. Si retorna 1: `0x102a798(1)` — set flag `0x2027c` (estado "wake en curso").
6. **Condicional** — si flag `0x20208 & 0x80`: `0x101e808` (visibilidad off) + `0x101e818` — **timer arm: callback `0x1028b4c`, duración `0x3a98` = 15000 ms, handle RAM `0x20208`**. La rama sin `0x80` termina sin timer (ver §1.3).

### 1.3 Timer callback `0x1028b4c` — supervisión de reconexión (15 s, CONDICIONAL)
**Precisión post-review:** el timer solo se arma si flag `0x20208 & 0x80`. El disparo primario del wake son los vendor commands del §1.2 (programan el radio); el timer es una **state machine de supervisión/reintento**, no el mecanismo de emisión. Rama sin `0x80`: sin timer, no trazada más allá.
- Si ya conectado (`0x1026650`): `0x10289dc()` y terminar.
- Loop de espera: radio mode==2, `0x1026170()`, `0x1026ab0()` (link status).
- Rama activa: `0x101c06c(flag)` = **intento de conexión BT**; o `0x1030e18(0)` (abort/radio op).
- Retry vía `0x102911c` si `0x101fa98()` (guard one-shot) cambia.
**Ventana de 15 s para que la consola despierte y reconecte**, con reintentos — no hay emisión continua en este callback.

### 1.4 Récord S2 — layout, writer y fuente de datos (pairing)
**Layout verificado (cierra la aritmética 0x34 B):**
- `+0x00`: magic `0x20250815` (4 B)
- `+0x04`: **MAC de la consola** (6 B) — la que envía wake_parse
- `+0x0a`: 1 B (rol no determinado)
- `+0x0b`: **MAC2** (6 B) — gestionado por el writer, comparado contra holder estático `0x1036ee2`
- `+0x11`: byte de largo N (≤ 0x22)
- `+0x12`: material de link (N B) — lo que envía fn C
Total: 4 + 0x30 = `0x34` B. Reside @`0x107e0e8` (página data-flash `0x107e000`, offset +0xe8).

**Escritores:** `0x10290b0(slot, idx)` escribe **slots de 0x1c B** desde eventos de pairing (callers `0x101a57a`, `0x102a6b4`, `0x102a790`, `0x1030558` — copian MAC 6 B + 0x10 B link key/digest de eventos de autorización BT).
`0x102993c(new_MAC, 6)`: lee página, check magic; si MAC2@+0xb == holder `0x1036ee2` → **actualiza MAC2** con la nueva (memcpy + persist `0x10328e4` write + `0x103290c` readback); si MAC2 ≠ holder y ≠ nueva → **invalida el magic** (escribe `0xFFFFFFFF`) y persiste. **No trazado:** quién escribe el magic `0x20250815` inicial ni el enlace exacto slots→récord (inferido del offset +0xe8 compartido y del material). Estado: parcial.
**Conclusión sólida:** el récord se llena con datos del **pairing con la S2** (MAC consola + material de link de eventos de auth BT) — igual que el bonding S1 en `0x107e000`.

### 1.5 El template `0x0553` (dónde vive realmente)
En `0x1037cde`, dentro del **struct de identidad del radio** (`0x1037c80..0x1037d60`): BD-address, template ADV 31 B, MAC default `5e:a3:41:d8:17:e4`, strings "80GQ"/"80ND", 64 B de material de claves. Referenciado por config-setters (`0x10291e0`: `0x1030134(ptr, 0x1e)`, `0x102fdec`), no por el flujo wake. **Probable rol: datos ADV del modo pairing BLE, no wake.** Ningún xref directo desde el flujo wake S2.

### 1.6 Mecanismo de vendor commands (la "cola")
- `0x1019240(bitfield, ch)` / `0x1019262(bitfield, ch)`: claim/libera **canales** (bitfield de 64 bits en RAM `0x2000c`; ch<0x20 → word[0], si no word[1]).
- `0x1029b6c(pkt)`: queue_build — valida espacio, marca `[pkt+0]=1`, encola.
- `0x102b948()`: queue_wait — **espera bloqueante con timeout vía `0x1018240`** (delay).
- `0x102b954(t0, timeout)`: retry loop.
- **Formato del paquete (corregido post-review):** `[status][opcode][len][ptr32 LE]` — el payload NO va inline: los 4 bytes tras `len` son un **puntero serializado** (0x10182f0 emite LE32 del valor de r0) que el consumidor desreferencia. El **canal NO va en el paquete**: se reclama/libera aparte vía bitfield alrededor de la encolación. Opcode y canal son independientes (la igualdad op==ch en fn A y wake_parse es coincidencia).

## 2. Estado del firmware 1.11 instalado (80NA Ultimate BT) frente a esta cadena

| Componente v2.00 | Estado en 1.11 | Nota |
|---|---|---|
| shake handler / dispatcher wake | ✓ presente (case 0xb1 → Try_WakeUpNs S1) | el nuestro funciona (despierta S1) |
| reader récord S2 (0x101faa4) | NO LOCALIZADA (firma no hallada tras búsqueda exhaustiva) | récord 0x107e0e8 vacío en nuestro control |
| writer récord S2 (0x102993c/0x10290b0) | NO LOCALIZADA | sin writer no hay quien llene el récord al parear |
| fn A (ch4 sender) | ✓ reubicada a 0x101ac24 | mismo mecanismo de cola |
| fn C (ch0x15 sender) | AUSENTE (evidencia estructural) | cmd_slot_get SÍ existe en 1.11 (reubicada 0x10190fc) y **ningún caller pasa ch=0x15** — el inmediato 0x15 en el call-site sobrevive recompilación; ausencia estructural, no solo de firma |
| queue_build (0x1029b6c) | NO LOCALIZADA (firma 16B no hallada) | fn A/fw111 no la usa (usa poll directo) |
| radio_cfg (0x101b264) | ✓ reubicada a 0x101af70 | |
| timer_arm / visibility / bt_connect | NO LOCALIZADAS (por firma — evidencia débil) | |
| Try_WakeUpNs S1 (0x102aa80 wake pkt) | ✓ presente y funcional | wake S1 = `0xC0 0x12 MAC digest16` |

**Nota metodológica (post-review):** "NO LOCALIZADA" ≠ ausencia categórica — una variante recompilada evadiría la búsqueda por firma. Para fn C el argumento es más fuerte (canal 0x15 ausente del mapa estructural de callers de cmd_slot_get). Para reader/writer/queue_build/timer_arm la ausencia es por firma: alta probabilidad, no certeza.

**Canales vendor usados por 1.11:** 0,1,2,3,4,5,6,8,b,c,d,e,10,1d,1f,20,2c,32–38,3c — **canal 0x15 NO está en la lista**. El stack radio del 1.11 probablemente no implementa el comando 0x34/0x15.

## 3. Veredicto sobre v1–v4

- **v1–v3 (EMIT beacon por adv_tx `0x101d148`):** `0x101d148` pertenece a la familia de senders del protocolo **propietario 2.4G** (`(handle, 0x81, buf, param)` → API interna; análogo v2.00 `0x1030c34` tiene guard `mode==5` y lo usa el wake del dongle). El template S2 inyectado ahí **jamás llegaría por BLE**.
- **v4 (TRAMP sobre Try_WakeUpNs):** NO flasheado — correcto: la comparación contra v2.00 refuta su premisa (EMIT beacon). Quedó en `fw_installed_v4.bin` sin flashear.
- El módulo v3 flasheado sigue con el **hook 0xb0 activo**: el dispatcher redirige el evento 0xb0 al módulo, que ejecuta PARSER/LEARN y bail-out silencioso (récord S2 vacío) antes de caer al path original. Efecto en hardware: el flujo 0xb0 nativo corre con un overhead mínimo; ningún otro evento se toca. Inofensivo pero presente — decisión pendiente: restaurar stock puro (re-flash del backup) o dejarlo como base para una iteración futura.

## 4. Estrategias reevaluadas

**S1 — Port fiel de la cadena v2.00 (vendor commands + state machine):** INVIABLE como port directo. 5+ funciones ausentes en 1.11, canal 0x15 sin soporte probable en el radio. Solo viable si el radio del 80NA es el mismo chip que el 80ND y soporta el comando — improbable (producto 2022 vs 2025).

**S2 — Wake S1-style con parámetros S2:** Inventario honesto (post-review, sin cifras inventadas): el 1.11 **conserva** el shake handler (evento 0xb1), Try_WakeUpNs S1 funcional, bonding con la MAC de la S2 en `0x107e000`, radio_cfg, cmd_slot_get/poll, queue_wait/retry y el sender ch4. **Le faltan** (no localizadas): reader/writer del récord S2, fn C ch0x15, queue_build, timer_arm, bt_connect. Viable SOLO SI el delta real es formato de paquete y no la cadena vendor completa. Dato en contra: probado en hardware, el wake S1 nativo nunca despertó la S2 — el gap es handshake/link-params o formato, no solo un byte.

**S3 — Sniffing del wake real (ground truth):** La única fuente de verdad sobre qué acepta la S2 es capturar un wake real. Opciones: (a) Joycon 2 / mando oficial de la S2 despertándola, con sniffer BT (necesita hardware: Ubertooth, o HCI research), (b) btmon sobre un adaptador con firmware sniffer (btlejack, scapy-ble). Es la vía de mayor valor informativo y la que rompió el protocolo S1 originalmente.

**S4 — Esperar/solicitar soporte oficial:** 8BitDo no publica wake S2 para el Ultimate BT (confirmado por la existencia de este proyecto). Cerrar.

**S5 — Hardware swap:** comprar un Ultimate 2 BT (o el que tenga wake S2) y donar el Ultimate 1 a otra consola. $40-60, riesgo cero, resultado garantizado hoy.

## 5. Recomendación

S3 es el único camino con retorno de información real (protocol-level). S5 es el atajo pragmático. S2 (S1-style S2) es la apuesta de ingeniería si S3 revela que el delta es solo formato de paquete — el 1.11 ya tiene el 80% de la maquinaria (Try_WakeUpNs, bonding S2 presente, radio_cfg, reconexión).

## 6. Evidencia cruda
- `trace_v200_s2wake.md` (454 líneas, disasms anotados)
- Disasms inline en transcripción de sesión: 0x101da20, 0x101ae4c, 0x101b098, 0x101ad94, 0x102993c, 0x10290b0(+callers), 0x1023b24(+caller), 0x1028b4c, 0x101f024/0x101fa98, 0x1019240/62, 0x1029b6c/0x102b948/54, 0x102dd30 (dongle wake), 0x1030c34 (sender 2.4G), struct identidad 0x1037c80 dump.
