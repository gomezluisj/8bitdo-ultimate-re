# REPORTE FASE 1 — Análisis estático (cero hardware) · 2026-11-08

## 1.1 Anatomía del container 0x101b368 (fw111)

**Prólogo:** `push {r4,r5,lr}; sub sp,#0x24`.

**Flujo verificado (disasm completo, 0x101b368..0x101b4e8):**
1. `ldr r3 = 0x01030e8c` ('80NA' zone) → `ldm r3!, {r0-r3}` → guarda 16B en stack `sp+0x14..0x23` (copia identidad de fábrica).
2. `bl 0x10194c0` (init/sub-sistema).
3. Set bit 11 → `0xe000e100` (NVIC enable, IRQ 11 = radio).
4. `bl 0x1018268` (crypto/copy con r2=6, dst=sp+4) → **checksum loop inline** (suma bytes 4..9 = bytes 7..9 del resultado, tres pares).
5. `bl 0x1018268` (r2=3, src=sp+4, dst=sp+0xc) → empaqueta 3 bytes con checksums.
6. `bl 0x101ac24` (r0=sp+0x14, r1=0xe) → **send-wrapper id 0x04, payload 14B** (identidad+MAC).
7. `bl 0x101ab6c` (r0=sp+0xc) → wrapper id 0x01, payload 6B → lee estado; si ret==1 → `bl 0x1024f60` (log "setBtAddr_suc").
8. `bl 0x101e15c` (r0=sp+0xc).
9. `bl 0x101ac80` (r0=sp+0xc) → **wrapper id 0x00, payload 6B**; ret==1 → log ×2; else → log fail.
10. `bl 0x101aeb8` (r0=1) → branch por resultado, logs.
11. `bl 0x101ada4` (r0=0x00020556) → **wrapper id 0x15, payload 3B** (¡claim de canal por radio, confirmando hipótesis!).
12. Sección NV: `bl 0x102cfcc` (read page 0x0107f000 a 0x000248cc, 0xaa pattern check con r1=0xaa)…
13. Chequeos de bytes de sesión >5 en 4 offsets de RAM (0x000248cc+x)… y `bl 0x101829a` (memset 0xaa).
14. `bl 0x101ae5c` (r0=0x000248cc, r1=0xaa) → wrapper id 0x26, len variable → logs; loop 0xAA veces logueando bytes de la página leída (debug dump embebido).
15. `bl 0x1019328`, `bl 0x1019094` (r0=0x20559, r1=0x11), `bl 0x101902c` (r0=0x2056a, r1=0x14) → `strh` a 0x00020554.

**Canales reclamados en 0x2000c:** el container NO toca el bitfield directamente — los ids viajan como **r1 del acquire/send-wrapper** (0x01, 0x00, 0x04, 0x15, 0x26). `0x10190fc`/`0x101911e` = **clear-bit / test-bit** sobre el bitfield 64-bit `0x2000c..0x20013` (verificado: sin tabla, OOB imposible, ids válidos 0..0x3F).

**MAC de consola:** se copia del bloque factory `0x01030e8c` + se actualiza vía `0x101ac24` con el checksum generado inline — **la MAC no se lee de 0x107e000 en este container** (la página 0x107f000 sí se lee para sesión/debug).

**Cierre del container (0x101b4e8..):** secuencia de logging + configuración NVIC/radio. Sin claim(0x15) explícito por bitfield — el claim está embebido en el wrapper 0x101ada4.

## 1.2 Firmas IPC fw111 vs v2.00 — v2.00 es recompilación, no copy

| Función | fw111 | v2.00 (file off) | Match 8B | Comentario |
|---|---|---|---|---|
| claim_channel (clear-bit) | `0x10190fc` y `0x101914c` | `0x1240` y `0x1290` | ✓ prologue idéntico | shift `+0x144` |
| release_check (test-bit) | `0x101911e` | `0x1262` | ✓ | shift `+0x144` |
| send-wrapper id 0x04 | `0x101ac24` | `0x2e4c` | ✓ | shift `+0x228` |
| queue_send | `0x1026880` | NO FOUND | — | **recompilado en v2, sin match byte** |
| get_tick/sync | `0x10281b4` | múltiples (`0x6eec`, `0x13948`…) | parcial | patrón ldr/bx repetido |
| ser24/crypt | `0x10182f0`/`0x1018268` | NO FOUND | — | v2 usa variantes |
| read_NV / program / erase | `0x102cfcc`/`0x102d030`/`0x102d008` | `0x1a8a8`/`0x1a90c` (24B sig match, roles intercambiados vs 8B) | parcial | driver en `0x1a8a8..0x1a90c`; erase=0 en 8B sig pero **`bl 0x1a8e4` aparece en el flujo S2-writer — es el erase v2** |

**Consecuencia crítica:** las direcciones de fw111 **NO son válidas para v2.00** por shift uniforme; cada función requiere su propio mapeo. Las primitivas de fw111 para v7-r2 (claim/check bitfield, wrappers) están **verificadas en el desasm directo de fw111** — no dependen de v2.

## 1.3 Escritor del récord S2 (magic 0x20250815) en v2.00

**Dos sitios** (ambos con `0x107e000` + `0x20250815` en pool):

**Site A `0x7aa4`** (`sub sp,#0x11c`) — COMPLETO:
1. `read_NV(0x107e000, sp, 0x11c)` (vía 0x1a8a8).
2. `r4 = sp+0xe8` → `ldr r0,[r4]` — **compara [sp+0xe8] contra 0x20250815**.
3. Si match: `memcpy(r0=r5, r1=r4, r2=0x34)` (vía 0x268) — copia 0x34 bytes del récord al buffer del caller.
4. **Devuelve 1.** Si no match: devuelve sin copiar.
   → Este es el **lector** del récord S2 (el updater consulta el récord persistido).

**Site B `0x1193c`** — WRITER (parcial, truncado en extracción pero flujo claro):
1. `read_NV(0x107e000, sp, 0x11c)`.
2. `r4 = sp+0xe8`; compara `[r4]` contra `0x20250815`.
3. Si match: **compara 6 bytes en `[r4+0xb]`** contra bloque `0x1036ee2` (vía 0x2b0 = memcmp):
   - Si difiere → `memcpy([r4+0xb], r5, 6)` (escribe MAC 6B desde r5 del caller) → `erase(0x107e000)` (vía 0x1a8e4) → `read_NV` de verificación.
   - Si igual → `memcmp` inverso, si match → `mvns r0` (-1) **borra el magic** → erase → read verify.
   → **El dato escrito en récord+0xb es la MAC (6 bytes), NO 16B.** El bloque de 16B en récord+0x12 NO aparece escrito aquí (el memcpy de site A lee 0x34 bytes desde +0, cubriendo +0xb..+0x3f, pero el writer solo toca +0xb..+0x10).
4. `erase()` v2 = `0x1a8e4` (confirmado por llamadas — 8B sig no matcheo pero el rol es inequívoco en flujo).

**Respuesta al punto 1.3:** el dato exacto no es LTK ni Link Key — es la **MAC de consola** (6B en récord+0xb; el magic 4B en récord+0). El bloque factory `0x1030e7c` no aparece en este writer. Récord persistido = `{magic 0x20250815 @+0, MAC 6B @+0xb}`.

## 1.4 Template BLE 0x0553 (v2.00) — PARCIAL, gap declarado

- En v2.00 existe un word `0x00000553` en file `0xc96c` (≈VA `0x102496c`) junto a `0x00002066` — **dato, no código**.
- En fw111, la región 0x1037c80..0x1037d60 es **0xFF (virgen)** — el template NO existe en fw111 (era esperable: fw111 es el beta del 80NA, el template es de v2.00 para hardware con S2).
- El desasm en el **VA 0x101bc0a mencionado por el plan no muestra prólogo de función** (cae en medio de código de otro flujo, con BLs a 0x102ff88/0x10300cc/logs). Necesito el prólogo real: escaneo de callers BL→VA 0x101bc0a en v2 sec1 dio **0 hits**, lo que indica que 0x101bc0a no es un target de función (o el VA base de v2 que asumió el plan difiere).
- **Gap declarado (no verificado):** el llamador real del getter del template 0x0553 en v2.00 requiere re-localizar la función con el VA base correcto de v2 (pendiente de un solo reescaneo). **No bloquea el diseño v7** (v7 no usa template), pero queda abierto para v8.

## Veredicto de la Fase 1 — GATE

✅ 1.1 completo · 1.2 completo (con tabla de shifts por-función) · 1.3 completo (récord = magic+MAC, sin 16B de claves) · 1.4 **parcial con gap declarado**.

**Impacto en v7-r2 (re-evaluación):**
1. Claim de canal por bitfield: **válido** (clear-bit, sin tabla, id 0x34 legal).
2. El container ya usa el patrón wrapper(id) — **nuestro acquire(0x2000c, 0x34) es correcto en fw111**.
3. El payload de 16B: el plan pedía serializar ptr24 a `0x1030e7c`. 1.3 demuestra que ese bloque es **identidad factory** (parte de la zona '80NA', con material críptico delante) — es un candidato legítimo de dato, no una key runtime. En v7-r2 la variante conservadora (0xAA×16) sigue siendo la más segura para un primer disparo.
4. **Nueva restricción del plan asumida**: pkt descriptor de 8 bytes con ptr24 serializado (no frame de 19B inline como construí). Requiere `ser24` (0x10182f0, verificada en wrapper pattern) — diseño v7-r3.
5. El plan exige **poll_wait(handle, timeout)** en vez del sync bloqueante `0x10281b4`. El wrapper `0x101ab6c`-style con check(FLAGS,id) tras BL cubre esto; para reproducir el patrón del plan hace falta la firma de `0x10281c0` (poll_wait) — 8B sig pendiente de extraer antes de compilar v7-r3.

**Estado:** fase 2 (v7-r3 ensamblador comentado al byte) espera solo la firma de `0x10281c0`. Ningún .dat se genera hasta que el ensamblador pase el gate de revisión de bytes del plan.
