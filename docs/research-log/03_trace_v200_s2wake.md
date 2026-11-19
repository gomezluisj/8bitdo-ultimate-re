
## 1. Callers del orquestador wake 0x101da20

### contexto caller 0x1023d56 @ `0x1023d3e`
- `0x01023d3e` `2348        ` ldr r0, [pc, #0x8c]  ; =0x000201be
- `0x01023d40` `0078        ` ldrb r0, [r0]
- `0x01023d42` `0028        ` cmp r0, #0
- `0x01023d44` `28d1        ` bne #0x1023d98
- `0x01023d46` `f9f7abf9    ` bl #0x101d0a0
- `0x01023d4a` `0028        ` cmp r0, #0
- `0x01023d4c` `0ed0        ` beq #0x1023d6c
- `0x01023d4e` `fbf7a3fe    ` bl #0x101fa98
- `0x01023d52` `0028        ` cmp r0, #0
- `0x01023d54` `0ad1        ` bne #0x1023d6c
- `0x01023d56` `f9f763fe    ` bl #0x101da20
- `0x01023d5a` `0120        ` movs r0, #1

## 2. Pools del orquestador (0x101da7c..0x101da8c)
- word @0x101da7c = 0x01037d03
- word @0x101da80 = 0x00020208
- word @0x101da84 = 0x01028b4d
- word @0x101da88 = 0x00003a98
- word @0x101da8c = 0xb082b5f7

## 3. Timer callback completo

### timer cb 15s @ `0x1028b4c`
- `0x01028b4c` `10b5        ` push {r4, lr}
- `0x01028b4e` `0446        ` mov r4, r0
- `0x01028b50` `fdf77efd    ` bl #0x1026650
- `0x01028b54` `0028        ` cmp r0, #0
- `0x01028b56` `02d0        ` beq #0x1028b5e
- `0x01028b58` `fff740ff    ` bl #0x10289dc
- `0x01028b5c` `10bd        ` pop {r4, pc}
- `0x01028b5e` `f6f761fa    ` bl #0x101f024
- `0x01028b62` `0228        ` cmp r0, #2
- `0x01028b64` `00d1        ` bne #0x1028b68
- `0x01028b66` `f9e7        ` b #0x1028b5c
- `0x01028b68` `fdf702fb    ` bl #0x1026170
- `0x01028b6c` `0028        ` cmp r0, #0
- `0x01028b6e` `00d0        ` beq #0x1028b72
- `0x01028b70` `f4e7        ` b #0x1028b5c
- `0x01028b72` `fdf79dff    ` bl #0x1026ab0
- `0x01028b76` `0028        ` cmp r0, #0
- `0x01028b78` `00d0        ` beq #0x1028b7c
- `0x01028b7a` `efe7        ` b #0x1028b5c
- `0x01028b7c` `1648        ` ldr r0, [pc, #0x58]  ; =0x000201be
- `0x01028b7e` `0078        ` ldrb r0, [r0]
- `0x01028b80` `0028        ` cmp r0, #0
- `0x01028b82` `0cd0        ` beq #0x1028b9e
- `0x01028b84` `fdf7ecfc    ` bl #0x1026560
- `0x01028b88` `0028        ` cmp r0, #0
- `0x01028b8a` `04d0        ` beq #0x1028b96
- `0x01028b8c` `1248        ` ldr r0, [pc, #0x48]  ; =0x000201be
- `0x01028b8e` `0078        ` ldrb r0, [r0]
- `0x01028b90` `f3f76cfa    ` bl #0x101c06c
- `0x01028b94` `17e0        ` b #0x1028bc6
- `0x01028b96` `0020        ` movs r0, #0
- `0x01028b98` `08f03ef9    ` bl #0x1030e18
- `0x01028b9c` `13e0        ` b #0x1028bc6
- `0x01028b9e` `fdf7cbfe    ` bl #0x1026938
- `0x01028ba2` `0028        ` cmp r0, #0
- `0x01028ba4` `0fd1        ` bne #0x1028bc6
- `0x01028ba6` `fdf775ff    ` bl #0x1026a94
- `0x01028baa` `0028        ` cmp r0, #0
- `0x01028bac` `0bd1        ` bne #0x1028bc6
- `0x01028bae` `fdf7d7fc    ` bl #0x1026560
- `0x01028bb2` `0028        ` cmp r0, #0
- `0x01028bb4` `04d0        ` beq #0x1028bc0
- `0x01028bb6` `0848        ` ldr r0, [pc, #0x20]  ; =0x000201be
- `0x01028bb8` `0078        ` ldrb r0, [r0]
- `0x01028bba` `f3f757fa    ` bl #0x101c06c
- `0x01028bbe` `02e0        ` b #0x1028bc6
- `0x01028bc0` `0020        ` movs r0, #0
- `0x01028bc2` `08f029f9    ` bl #0x1030e18
- `0x01028bc6` `f6f767ff    ` bl #0x101fa98
- `0x01028bca` `0028        ` cmp r0, #0
- `0x01028bcc` `01d0        ` beq #0x1028bd2
- `0x01028bce` `00f0a5fa    ` bl #0x102911c
- `0x01028bd2` `00bf        ` nop 
- `0x01028bd4` `c2e7        ` b #0x1028b5c
- `0x01028bd6` `0000        ` movs r0, r0
- `0x01028bd8` `be01        ` lsls r6, r7, #6
- `0x01028bda` `0200        ` movs r2, r0
- `0x01028bdc` `10b5        ` push {r4, lr}
- `0x01028bde` `2421        ` movs r1, #0x24
- `0x01028be0` `0348        ` ldr r0, [pc, #0xc]  ; =0x00022cc0
- `0x01028be2` `eff75afb    ` bl #0x101829a
- `0x01028be6` `0349        ` ldr r1, [pc, #0xc]  ; =0x00002008
- `0x01028be8` `0348        ` ldr r0, [pc, #0xc]  ; =0x00022ce4
- `0x01028bea` `eff756fb    ` bl #0x101829a
- `0x01028bee` `10bd        ` pop {r4, pc}
- `0x01028bf0` `c02c        ` cmp r4, #0xc0
- `0x01028bf2` `0200        ` movs r2, r0
- `0x01028bf4` `0820        ` movs r0, #8
- `0x01028bf6` `0000        ` movs r0, r0
- `0x01028bf8` `e42c        ` cmp r4, #0xe4
- `0x01028bfa` `0200        ` movs r2, r0
- `0x01028bfc` `7047        ` bx lr
- `0x01028bfe` `0000        ` movs r0, r0
- `0x01028c00` `30b5        ` push {r4, r5, lr}
- `0x01028c02` `89b0        ` sub sp, #0x24
- `0x01028c04` `0446        ` mov r4, r0
- `0x01028c06` `002c        ` cmp r4, #0
- `0x01028c08` `15d1        ` bne #0x1028c36
- `0x01028c0a` `2021        ` movs r1, #0x20
- `0x01028c0c` `01a8        ` add r0, sp, #4
- `0x01028c0e` `eff744fb    ` bl #0x101829a
- `0x01028c12` `4549        ` ldr r1, [pc, #0x114]  ; =0x01037771
- `0x01028c14` `01a8        ` add r0, sp, #4
- `0x01028c16` `eff758fb    ` bl #0x10182ca
- `0x01028c1a` `4449        ` ldr r1, [pc, #0x110]  ; =0x00000229
- `0x01028c1c` `4448        ` ldr r0, [pc, #0x110]  ; =0x00020330
- `0x01028c1e` `f2f773f8    ` bl #0x101ad08
- `0x01028c22` `0028        ` cmp r0, #0
- `0x01028c24` `03d0        ` beq #0x1028c2e
- `0x01028c26` `43a0        ` adr r0, #0x10c
- `0x01028c28` `fef704ff    ` bl #0x1027a34
- `0x01028c2c` `6ce0        ` b #0x1028d08
- `0x01028c2e` `4ba0        ` adr r0, #0x12c
- `0x01028c30` `fef700ff    ` bl #0x1027a34
- `0x01028c34` `68e0        ` b #0x1028d08
- `0x01028c36` `012c        ` cmp r4, #1
- `0x01028c38` `21d1        ` bne #0x1028c7e
- `0x01028c3a` `0821        ` movs r1, #8
- `0x01028c3c` `5148        ` ldr r0, [pc, #0x144]  ; =0x00020318
- `0x01028c3e` `f1f73fff    ` bl #0x101aac0
- `0x01028c42` `2021        ` movs r1, #0x20
- `0x01028c44` `01a8        ` add r0, sp, #4
- `0x01028c46` `eff728fb    ` bl #0x101829a

## 4. Callers de fn C 0x101b098 (canal 0x15)

## 4b. Callers de fn A 0x101ae4c (canal 4)

## 5. API cola: canales usados por callers de 0x1019240/0x1019262
- canal 0x0: 7 llamadas ['0x10192cc', '0x1019324', '0x101934c', '0x10193a4', '0x1019484', '0x101af32', '0x101af4a']
- canal 0x1: 2 llamadas ['0x101adae', '0x101adc6']
- canal 0x2: 3 llamadas ['0x101b2ae', '0x101b33a', '0x101b2c6']
- canal 0x3: 2 llamadas ['0x101af92', '0x101afaa']
- canal 0x4: 2 llamadas ['0x101ae66', '0x101ae7e']
- canal 0x5: 4 llamadas ['0x101abcc', '0x101ac18', '0x101ac52', '0x101ac6a']
- canal 0x6: 2 llamadas ['0x101ab5e', '0x101ab76']
- canal 0x8: 2 llamadas ['0x101b1c8', '0x101b1e0']
- canal 0xb: 3 llamadas ['0x101934c', '0x10193a4', '0x1019364']
- canal 0xc: 3 llamadas ['0x10192cc', '0x1019324', '0x10192e4']
- canal 0xd: 2 llamadas ['0x101b16a', '0x101b182']
- canal 0xe: 2 llamadas ['0x101b224', '0x101b23c']
- canal 0x10: 2 llamadas ['0x10193ce', '0x10193e6']
- canal 0x15: 2 llamadas ['0x101b0b2', '0x101b0ca']
- canal 0x1d: 2 llamadas ['0x101b056', '0x101b06e']
- canal 0x1f: 2 llamadas ['0x1019484', '0x101949c']
- canal 0x20: 4 llamadas ['0x101918a', '0x10191f2', '0x10191a2', '0x101920a']
- canal 0x32: 2 llamadas ['0x101ad24', '0x101ad3c']
- canal 0x33: 2 llamadas ['0x101aae0', '0x101aaf8']
- canal 0x34: 2 llamadas ['0x101affa', '0x101b012']
- canal 0x35: 2 llamadas ['0x101acb4', '0x101accc']
- canal 0x36: 2 llamadas ['0x101ae0c', '0x101ae24']
- canal 0x37: 2 llamadas ['0x101b110', '0x101b128']
- canal 0x38: 2 llamadas ['0x101aed8', '0x101aef0']
- canal 0x3c: 2 llamadas ['0x101942a', '0x1019442']

## 6. Struct identidad 0x1037c80..0x1037d60
```hexdump
0x01037c80  b1ff020161fe0201ddff0201fbfe0201  ....a...........
0x01037c90  f1fe02010500030175fe0201f1ff0201  ........u.......
0x01037ca0  03ff0201f9fe02019dff02010efe34d8  ..............4.
0x01037cb0  17e427dae260e1f7a121384000e1addd  ..'..`...!8@....
0x01037cc0  e778aa07750b804057c3179032365545  .x..u..@W...26UE
0x01037cd0  12235666554512235666554512230201  .#VfUE.#VfUE.#..
0x01037ce0  061bff53050100037e05662000018105  ...S....~.f ....
0x01037cf0  08550548c80f000000000000005ea341  .U.H.........^.A
0x01037d00  d817e448480000003830475100000000  ...HH...80GQ....
0x01037d10  000000000000000038304e4400000000  ........80ND....
0x01037d20  0000000000000000499e1bc172999a19  ........I...r...
0x01037d30  4eac24d2e90036ceb5bb471fb7968424  N.$...6...G....$
0x01037d40  64d3b239142f2e4187669a536a0d92f4  d..9./.A.f.Sj...
0x01037d50  b4370d323588c36f15c5bc26cdeaece6  .7.25..o...&....
```

## 7. Writer record S2 (0x102993c) completo

### writer @ `0x102993c`
- `0x0102993c` `30b5        ` push {r4, r5, lr}
- `0x0102993e` `c7b0        ` sub sp, #0x11c
- `0x01029940` `0546        ` mov r5, r0
- `0x01029942` `ff22        ` movs r2, #0xff
- `0x01029944` `1d32        ` adds r2, #0x1d
- `0x01029946` `6946        ` mov r1, sp
- `0x01029948` `1a48        ` ldr r0, [pc, #0x68]  ; =0x0107e000
- `0x0102994a` `08f0adff    ` bl #0x10328a8
- `0x0102994e` `3aac        ` add r4, sp, #0xe8
- `0x01029950` `1949        ` ldr r1, [pc, #0x64]  ; =0x20250815
- `0x01029952` `2068        ` ldr r0, [r4]
- `0x01029954` `8842        ` cmp r0, r1
- `0x01029956` `2bd1        ` bne #0x10299b0
- `0x01029958` `0622        ` movs r2, #6
- `0x0102995a` `1849        ` ldr r1, [pc, #0x60]  ; =0x01036ee2
- `0x0102995c` `2046        ` mov r0, r4
- `0x0102995e` `0b30        ` adds r0, #0xb
- `0x01029960` `eef7a6fc    ` bl #0x10182b0
- `0x01029964` `0028        ` cmp r0, #0
- `0x01029966` `0fd1        ` bne #0x1029988
- `0x01029968` `0622        ` movs r2, #6
- `0x0102996a` `2946        ` mov r1, r5
- `0x0102996c` `2046        ` mov r0, r4
- `0x0102996e` `0b30        ` adds r0, #0xb
- `0x01029970` `eef77afc    ` bl #0x1018268
- `0x01029974` `0f48        ` ldr r0, [pc, #0x3c]  ; =0x0107e000
- `0x01029976` `08f0b5ff    ` bl #0x10328e4
- `0x0102997a` `ff22        ` movs r2, #0xff
- `0x0102997c` `1d32        ` adds r2, #0x1d
- `0x0102997e` `6946        ` mov r1, sp
- `0x01029980` `0c48        ` ldr r0, [pc, #0x30]  ; =0x0107e000
- `0x01029982` `08f0c3ff    ` bl #0x103290c
- `0x01029986` `13e0        ` b #0x10299b0
- `0x01029988` `0622        ` movs r2, #6
- `0x0102998a` `2946        ` mov r1, r5
- `0x0102998c` `2046        ` mov r0, r4
- `0x0102998e` `0b30        ` adds r0, #0xb
- `0x01029990` `eef78efc    ` bl #0x10182b0
- `0x01029994` `0028        ` cmp r0, #0
- `0x01029996` `0bd0        ` beq #0x10299b0
- `0x01029998` `0020        ` movs r0, #0
- `0x0102999a` `c043        ` mvns r0, r0
- `0x0102999c` `2060        ` str r0, [r4]
- `0x0102999e` `0548        ` ldr r0, [pc, #0x14]  ; =0x0107e000
- `0x010299a0` `08f0a0ff    ` bl #0x10328e4
- `0x010299a4` `ff22        ` movs r2, #0xff
- `0x010299a6` `1d32        ` adds r2, #0x1d
- `0x010299a8` `6946        ` mov r1, sp
- `0x010299aa` `0248        ` ldr r0, [pc, #8]  ; =0x0107e000
- `0x010299ac` `08f0aeff    ` bl #0x103290c
- `0x010299b0` `47b0        ` add sp, #0x11c
- `0x010299b2` `30bd        ` pop {r4, r5, pc}
- `0x010299b4` `00e0        ` b #0x10299b8
- `0x010299b6` `0701        ` lsls r7, r0, #4
- `0x010299b8` `1508        ` lsrs r5, r2, #0x20
- `0x010299ba` `2520        ` movs r0, #0x25
- `0x010299bc` `e26e        ` ldr r2, [r4, #0x6c]
- `0x010299be` `0301        ` lsls r3, r0, #4
- `0x010299c0` `00b5        ` push {lr}
- `0x010299c2` `89b0        ` sub sp, #0x24
- `0x010299c4` `0f48        ` ldr r0, [pc, #0x3c]  ; =0x00024cf8
- `0x010299c6` `4068        ` ldr r0, [r0, #4]
- `0x010299c8` `0028        ` cmp r0, #0
- `0x010299ca` `19d0        ` beq #0x1029a00
- `0x010299cc` `0e48        ` ldr r0, [pc, #0x38]  ; =0x20240507
- `0x010299ce` `0d49        ` ldr r1, [pc, #0x34]  ; =0x00024cf8
- `0x010299d0` `0860        ` str r0, [r1]
- `0x010299d2` `0846        ` mov r0, r1
- `0x010299d4` `0068        ` ldr r0, [r0]
- `0x010299d6` `0190        ` str r0, [sp, #4]
- `0x010299d8` `0846        ` mov r0, r1
- `0x010299da` `8068        ` ldr r0, [r0, #8]
- `0x010299dc` `0290        ` str r0, [sp, #8]
- `0x010299de` `0b46        ` mov r3, r1
- `0x010299e0` `0c33        ` adds r3, #0xc
- `0x010299e2` `0fcb        ` ldm r3, {r0, r1, r2, r3}
- `0x010299e4` `0693        ` str r3, [sp, #0x18]
- `0x010299e6` `03ab        ` add r3, sp, #0xc
- `0x010299e8` `07c3        ` stm r3!, {r0, r1, r2}
- `0x010299ea` `f5f7e3fd    ` bl #0x101f5b4
- `0x010299ee` `0790        ` str r0, [sp, #0x1c]
- `0x010299f0` `0648        ` ldr r0, [pc, #0x18]  ; =0x010170c0
- `0x010299f2` `06f0c7fc    ` bl #0x1030384
- `0x010299f6` `2022        ` movs r2, #0x20
- `0x010299f8` `01a9        ` add r1, sp, #4
- `0x010299fa` `0448        ` ldr r0, [pc, #0x10]  ; =0x010170c0
- `0x010299fc` `06f022fd    ` bl #0x1030444
- `0x01029a00` `09b0        ` add sp, #0x24
- `0x01029a02` `00bd        ` pop {pc}
- `0x01029a04` `f84c        ` ldr r4, [pc, #0x3e0]  ; =0x2120d10c
- `0x01029a06` `0200        ` movs r2, r0
- `0x01029a08` `0705        ` lsls r7, r0, #0x14
- `0x01029a0a` `2420        ` movs r0, #0x24

### call site writer @0x10290fe @ `0x10290ee`
- `0x010290ee` `0748        ` ldr r0, [pc, #0x1c]  ; =0x00020181
- `0x010290f0` `eff7baf8    ` bl #0x1018268
- `0x010290f4` `0648        ` ldr r0, [pc, #0x18]  ; =0x000201be
- `0x010290f6` `0078        ` ldrb r0, [r0]
- `0x010290f8` `0028        ` cmp r0, #0
- `0x010290fa` `02d1        ` bne #0x1029102
- `0x010290fc` `0348        ` ldr r0, [pc, #0xc]  ; =0x00020181
- `0x010290fe` `00f01dfc    ` bl #0x102993c
- `0x01029102` `3846        ` mov r0, r7
- `0x01029104` `47b0        ` add sp, #0x11c
- `0x01029106` `f0bd        ` pop {r4, r5, r6, r7, pc}
- `0x01029108` `00e0        ` b #0x102910c
- `0x0102910a` `0701        ` lsls r7, r0, #4
- `0x0102910c` `8101        ` lsls r1, r0, #6
- `0x0102910e` `0200        ` movs r2, r0
- `0x01029110` `be01        ` lsls r6, r7, #6
- `0x01029112` `0200        ` movs r2, r0
- `0x01029114` `10b5        ` push {r4, lr}

## 8. Callers del getter 0x102ff88

### caller getter 0x101bc0a @ `0x101bc02`
- `0x0101bc02` `13f0abff    ` bl #0x102fb5c
- `0x0101bc06` `14f01df8    ` bl #0x102fc44
- `0x0101bc0a` `14f0bdf9    ` bl #0x102ff88
- `0x0101bc0e` `0446        ` mov r4, r0
- `0x0101bc10` `14f05cfa    ` bl #0x10300cc
- `0x0101bc14` `00f03cf8    ` bl #0x101bc90

### fn 0x101e808 @ `0x101e808`
- `0x0101e808` `10b5        ` push {r4, lr}
- `0x0101e80a` `0248        ` ldr r0, [pc, #8]  ; =0x000250ec
- `0x0101e80c` `11f084fc    ` bl #0x1030118
- `0x0101e810` `10bd        ` pop {r4, pc}
- `0x0101e812` `0000        ` movs r0, r0
- `0x0101e814` `ec50        ` str r4, [r5, r3]
- `0x0101e816` `0200        ` movs r2, r0
- `0x0101e818` `70b5        ` push {r4, r5, r6, lr}
- `0x0101e81a` `0446        ` mov r4, r0
- `0x0101e81c` `0d46        ` mov r5, r1
- `0x0101e81e` `0748        ` ldr r0, [pc, #0x1c]  ; =0x000250ec
- `0x0101e820` `11f07afc    ` bl #0x1030118
- `0x0101e824` `2946        ` mov r1, r5
- `0x0101e826` `0548        ` ldr r0, [pc, #0x14]  ; =0x000250ec
- `0x0101e828` `11f092fc    ` bl #0x1030150
- `0x0101e82c` `2146        ` mov r1, r4
- `0x0101e82e` `0348        ` ldr r0, [pc, #0xc]  ; =0x000250ec
- `0x0101e830` `11f080fc    ` bl #0x1030134
- `0x0101e834` `0148        ` ldr r0, [pc, #4]  ; =0x000250ec
- `0x0101e836` `11f0d9fa    ` bl #0x102fdec
- `0x0101e83a` `70bd        ` pop {r4, r5, r6, pc}
- `0x0101e83c` `ec50        ` str r4, [r5, r3]
- `0x0101e83e` `0200        ` movs r2, r0
- `0x0101e840` `70b5        ` push {r4, r5, r6, lr}
- `0x0101e842` `0446        ` mov r4, r0
- `0x0101e844` `0d46        ` mov r5, r1
- `0x0101e846` `2a46        ` mov r2, r5

### fn 0x101e818 @ `0x101e818`
- `0x0101e818` `70b5        ` push {r4, r5, r6, lr}
- `0x0101e81a` `0446        ` mov r4, r0
- `0x0101e81c` `0d46        ` mov r5, r1
- `0x0101e81e` `0748        ` ldr r0, [pc, #0x1c]  ; =0x000250ec
- `0x0101e820` `11f07afc    ` bl #0x1030118
- `0x0101e824` `2946        ` mov r1, r5
- `0x0101e826` `0548        ` ldr r0, [pc, #0x14]  ; =0x000250ec
- `0x0101e828` `11f092fc    ` bl #0x1030150
- `0x0101e82c` `2146        ` mov r1, r4
- `0x0101e82e` `0348        ` ldr r0, [pc, #0xc]  ; =0x000250ec
- `0x0101e830` `11f080fc    ` bl #0x1030134
- `0x0101e834` `0148        ` ldr r0, [pc, #4]  ; =0x000250ec
- `0x0101e836` `11f0d9fa    ` bl #0x102fdec
- `0x0101e83a` `70bd        ` pop {r4, r5, r6, pc}
- `0x0101e83c` `ec50        ` str r4, [r5, r3]
- `0x0101e83e` `0200        ` movs r2, r0
- `0x0101e840` `70b5        ` push {r4, r5, r6, lr}
- `0x0101e842` `0446        ` mov r4, r0
- `0x0101e844` `0d46        ` mov r5, r1
- `0x0101e846` `2a46        ` mov r2, r5
- `0x0101e848` `2146        ` mov r1, r4
- `0x0101e84a` `8220        ` movs r0, #0x82
- `0x0101e84c` `00f026fa    ` bl #0x101ec9c
- `0x0101e850` `70bd        ` pop {r4, r5, r6, pc}
- `0x0101e852` `0000        ` movs r0, r0
- `0x0101e854` `f7b5        ` push {r0, r1, r2, r4, r5, r6, r7, lr}
- `0x0101e856` `92b0        ` sub sp, #0x48
- `0x0101e858` `1546        ` mov r5, r2
- `0x0101e85a` `6946        ` mov r1, sp
- `0x0101e85c` `1298        ` ldr r0, [sp, #0x48]
- `0x0101e85e` `0872        ` strb r0, [r1, #8]
- `0x0101e860` `002d        ` cmp r5, #0
- `0x0101e862` `08dd        ` ble #0x101e876
- `0x0101e864` `3f2d        ` cmp r5, #0x3f
- `0x0101e866` `00d9        ` bls #0x101e86a
- `0x0101e868` `3f25        ` movs r5, #0x3f
- `0x0101e86a` `2a46        ` mov r2, r5
- `0x0101e86c` `02a8        ` add r0, sp, #8
- `0x0101e86e` `0130        ` adds r0, #1
- `0x0101e870` `1399        ` ldr r1, [sp, #0x4c]
- `0x0101e872` `f9f7f9fc    ` bl #0x1018268
- `0x0101e876` `681c        ` adds r0, r5, #1

## 10. Presencia de fn A/C y API cola en fw111 (BAK)

## 11. fw111 s1_wake_pkt 0x102aa80 (transporte wake S1)

### fw111 s1_wake_pkt @ `0x102aa80`
- `0x0102aa80` `70b5        ` push {r4, r5, r6, lr}
- `0x0102aa82` `8cb0        ` sub sp, #0x30
- `0x0102aa84` `0446        ` mov r4, r0
- `0x0102aa86` `0d46        ` mov r5, r1
- `0x0102aa88` `0026        ` movs r6, #0
- `0x0102aa8a` `1aa0        ` adr r0, #0x68
- `0x0102aa8c` `faf768fa    ` bl #0x1024f60
- `0x0102aa90` `2046        ` mov r0, r4
- `0x0102aa92` `02f0a5f8    ` bl #0x102cbe0
- `0x0102aa96` `1da0        ` adr r0, #0x74
- `0x0102aa98` `faf762fa    ` bl #0x1024f60
- `0x0102aa9c` `2421        ` movs r1, #0x24
- `0x0102aa9e` `03a8        ` add r0, sp, #0xc
- `0x0102aaa0` `edf7fbfb    ` bl #0x101829a
- `0x0102aaa4` `c021        ` movs r1, #0xc0
- `0x0102aaa6` `6846        ` mov r0, sp
- `0x0102aaa8` `0173        ` strb r1, [r0, #0xc]
- `0x0102aaaa` `1221        ` movs r1, #0x12
- `0x0102aaac` `4173        ` strb r1, [r0, #0xd]
- `0x0102aaae` `2178        ` ldrb r1, [r4]
- `0x0102aab0` `8173        ` strb r1, [r0, #0xe]
- `0x0102aab2` `6178        ` ldrb r1, [r4, #1]
- `0x0102aab4` `c173        ` strb r1, [r0, #0xf]
- `0x0102aab6` `a178        ` ldrb r1, [r4, #2]
- `0x0102aab8` `0174        ` strb r1, [r0, #0x10]
- `0x0102aaba` `e178        ` ldrb r1, [r4, #3]
- `0x0102aabc` `4174        ` strb r1, [r0, #0x11]
- `0x0102aabe` `2179        ` ldrb r1, [r4, #4]
- `0x0102aac0` `8174        ` strb r1, [r0, #0x12]
- `0x0102aac2` `6179        ` ldrb r1, [r4, #5]
- `0x0102aac4` `c174        ` strb r1, [r0, #0x13]
- `0x0102aac6` `2146        ` mov r1, r4
- `0x0102aac8` `01a8        ` add r0, sp, #4
- `0x0102aaca` `00f031fe    ` bl #0x102b730
- `0x0102aace` `01a9        ` add r1, sp, #4
- `0x0102aad0` `05a8        ` add r0, sp, #0x14
- `0x0102aad2` `f1f707fb    ` bl #0x101c0e4
- `0x0102aad6` `1022        ` movs r2, #0x10
- `0x0102aad8` `2946        ` mov r1, r5
- `0x0102aada` `08a8        ` add r0, sp, #0x20
- `0x0102aadc` `edf7c4fb    ` bl #0x1018268
- `0x0102aae0` `2421        ` movs r1, #0x24
- `0x0102aae2` `03a8        ` add r0, sp, #0xc
- `0x0102aae4` `eff7c2ff    ` bl #0x101aa6c
- `0x0102aae8` `0aa0        ` adr r0, #0x28
- `0x0102aaea` `faf739fa    ` bl #0x1024f60
- `0x0102aaee` `0cb0        ` add sp, #0x30
- `0x0102aaf0` `70bd        ` pop {r4, r5, r6, pc}
- `0x0102aaf2` `0000        ` movs r0, r0
- `0x0102aaf4` `0d0a        ` lsrs r5, r1, #8
- `0x0102aaf6` `5761        ` str r7, [r2, #0x14]
- `0x0102aaf8` `6b65        ` str r3, [r5, #0x54]
- `0x0102aafa` `5570        ` strb r5, [r2, #1]
- `0x0102aafc` `5f53        ` strh r7, [r3, r5]
- `0x0102aafe` `7769        ` ldr r7, [r6, #0x14]
- `0x0102ab00` `7463        ` str r4, [r6, #0x34]
- `0x0102ab02` `6820        ` movs r0, #0x68
- `0x0102ab04` `3a0d        ` lsrs r2, r7, #0x14
- `0x0102ab06` `0a0d        ` lsrs r2, r1, #0x14
- `0x0102ab08` `0a00        ` movs r2, r1
- `0x0102ab0a` `0000        ` movs r0, r0
- `0x0102ab0c` `0d0a        ` lsrs r5, r1, #8
- `0x0102ab0e` `0d0a        ` lsrs r5, r1, #8

## 12. fw111: canales API cola (0x10190fc / 0x101911e)
- canal 0x0: 7 llamadas ['0x1019188', '0x10191e0', '0x1019208', '0x1019260', '0x1019340', '0x101ac9a', '0x101acb2']
- canal 0x1: 2 llamadas ['0x101ab86', '0x101ab9e']
- canal 0x2: 3 llamadas ['0x101afba', '0x101b046', '0x101afd2']
- canal 0x3: 2 llamadas ['0x101acfa', '0x101ad12']
- canal 0x4: 2 llamadas ['0x101ac3e', '0x101ac56']
- canal 0x5: 4 llamadas ['0x101a9a4', '0x101a9f0', '0x101aa2a', '0x101aa42']
- canal 0x6: 2 llamadas ['0x101a936', '0x101a94e']
- canal 0x8: 2 llamadas ['0x101aed4', '0x101aeec']
- canal 0xb: 3 llamadas ['0x1019208', '0x1019260', '0x1019220']
- canal 0xc: 3 llamadas ['0x1019188', '0x10191e0', '0x10191a0']
- canal 0xd: 2 llamadas ['0x101ae76', '0x101ae8e']
- canal 0xe: 2 llamadas ['0x101af30', '0x101af48']
- canal 0x10: 2 llamadas ['0x101928a', '0x10192a2']
- canal 0x1d: 2 llamadas ['0x101adbe', '0x101add6']
- canal 0x1f: 2 llamadas ['0x1019340', '0x1019358']
- canal 0x20: 4 llamadas ['0x1019046', '0x10190ae', '0x101905e', '0x10190c6']
- canal 0x2c: 2 llamadas ['0x101a8d0', '0x101a8e8']
- canal 0x32: 2 llamadas ['0x101aafc', '0x101ab14']
- canal 0x33: 2 llamadas ['0x101a850', '0x101a868']
- canal 0x34: 2 llamadas ['0x101ad62', '0x101ad7a']
- canal 0x35: 2 llamadas ['0x101aa8c', '0x101aaa4']
- canal 0x36: 2 llamadas ['0x101abe4', '0x101abfc']
- canal 0x37: 2 llamadas ['0x101ae1c', '0x101ae34']
- canal 0x3c: 2 llamadas ['0x10192e6', '0x10192fe']