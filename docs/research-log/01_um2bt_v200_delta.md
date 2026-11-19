# UM_2_BT 1.04b15 -> 2.00 — Delta de funciones (módulo wake Switch 2)

Método: Ghidra 12.2 headless, ARM Cortex-M (Thumb), base 0x01018000, export de
todas las funciones decompiladas (v1.04b15: 910 fns, v2.00: 919 fns). Emparejamiento
por cuerpo normalizado (direcciones absolutas, sub_FUNC, locals y números abstractos):
814/910 emparejadas exactas.

## Funciones nuevas del módulo wake S2 (v2.00, con rol identificado)

| Addr v2.00 | Rol (verificado por disasm/decomp + strings) |
|---|---|
| FUN_0102bd30 | Try_WakeUpNs core: guards -> read bonded MAC (config 0x11c B) -> SetBtAddr/Visibility -> WakeUp_Switch -> timer 4000ms |
| FUN_0102eb20 | WakeUp_Switch packet builder: 0xC0 0x12 + MAC(6) + digest(16) (idéntico al S1) |
| FUN_0101a22c | dispatcher HCI expandido: cases nuevos 0x2a, 8 (sniff), 9 (BASEBAND_CONNECT), 10/0xb (WAKEUP_NS TIMEOUT/FAIL + retry<=2), 0xb1 (trigger wake) |
| FUN_0102911c | abort back-to-idle (retry agotado) |
| FUN_01029150 | HID "get info" 0x0e handshake post-connect |
| FUN_0101fa8c / FUN_0101fa98 | getters guard A/B (mismo byte @0x4770, struct BT global, 116 refs) |
| FUN_0101fd2c / FUN_0101fd4c | sniff tuning 5/10/15 ms -> parámetros de radio |
| FUN_0101e808 / FUN_0101d41c | SetBtAddr + SetVisibility (strings "SetBtAddr_suc", "SetVisibility_sucess") |
| FUN_01024f68 | timing helper (500ms/200, 1000ms/200) |
| FUN_0102a38c / FUN_0102a1f0 | HID setup / bit 0x400000 post-wake |

## Cadena completa (reconstruida)

1. case 0xb0 BT HID CONNECT -> flagA=0, handshake HID 0x0e
2. case 0x2a paquete 31-49 B -> delay 300ms
3. case 9 BASEBAND_CONNECT: SetBtAddr + SetVisibility -> timing -> HID setup -> sniff tuning (case 8)
4. case 0xb1: retry=0 -> Try_WakeUpNs()
5. case 10/0xb WAKEUP_NS_TIMEOUT/FAIL: retry <= 2, si no abort
6. Try_WakeUpNs: guardA==0 -> MAC bondada -> guardB!=0 -> SetBtAddr/SetVisibility -> packet 0xC0 0x12+MAC+digest16 -> 4000ms

## Hallazgo crítico contra hipótesis (c) (parche de identidad)

fw111 (Ultimate BT 1.11): WakeUp_Switch existe @0x0102aa08 con cuerpo idéntico
pero CERO callers en las 730 funciones exportadas. Try_WakeUpNs: AUSENTE.
BASEBAND_CONNECT / sniff negotiation / retry machine: AUSENTES.
=> La lógica wake S2 no existe en fw111. El port es de módulo completo (~2.5 KB), no parche de bytes.

## Hashes SHA-256 (artefatos fuente)

fda8f49ad9db183aedf1c726dc713a3339831393047f85310fb7fd6c941d374b  dec_UM_2_BT_sec1.bin (v1.04b15, 131072 B)
e5a0f81e6a8fdd113959acc95e80b5fe698c086443f7eaca1011a03f1130791e  dec4_UM2BT_200.bin (v2.00, 133632 B)
3149dce8855db9c470086c3e03fec41b9de79bfd01f1c17c8b7f8619d4f7b11e  fw111_dec.bin (Ultimate BT 1.11, 104448 B)

## Round-trip cripto (gate 1) — PASSED (offline)

Ultimate_Firmware_V1.11_Beta1.dat stock (104476 B, SHA-256 abajo) ->
decrypt yichip (8cryptdo) -> encrypt yichip (v111, base 0x01018000, pid 0x6007) ->
diff vs stock: 104475/104476 bytes idénticos; único diff = byte 3 del header
(campo version: stock 0x01, tool escribe 0x00). Parcheado ese byte: byte-idéntico.
=> La cadena decrypt->encrypt es reversible y exacta. Falta la mitad física:
flash del .dat re-encriptado + test con Switch 1 (requiere hardware físico).

stock .dat SHA-256: (ver commit; archivo incluido como fw111_stock.dat)
