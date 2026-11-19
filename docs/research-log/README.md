# Research Log (Historical Notes — Spanish)

These chronological notes preserve the reverse-engineering trail that led to [`v22`](../../build_v22.py). They are kept in their original Spanish for reproducibility and historical context.

For the current, concise English technical specification of `v22`, read [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) instead.

| # | Document | Summary |
|---|---|---|
| 01 | [`01_um2bt_v200_delta.md`](01_um2bt_v200_delta.md) | Function delta between `UM2BT` `1.04b15` and `2.00` identifying the Switch 2 wake module |
| 02 | [`02_s2_wake_trace.md`](02_s2_wake_trace.md) | Switch 2 BLE `0x0553` wake protocol discovery and strategy evaluation |
| 03 | [`03_trace_v200_s2wake.md`](03_trace_v200_s2wake.md) | Cross-reference trace of official `UM2BT v2.00` Switch 2 wake & reconnect flow |
| 04 | [`04_static_analysis_fw111.md`](04_static_analysis_fw111.md) | Static analysis of `80NA fw 1.11` radio container, IPC channels, and flash layout |
| 05 | [`05_image_validator_xip.md`](05_image_validator_xip.md) | Root-cause analysis of YiChip QSPI XIP encryption & bootloader verification |
| 06 | [`06_v16c_to_v17.md`](06_v16c_to_v17.md) | First real hardware `0x0553` Switch 2 wake confirmation (`v16c`) & `v17` timing plan |
| 07 | [`07_v17_to_v18.md`](07_v17_to_v18.md) | BLE capture diagnosis of `v17` premature cutoffs & `v18` fix |
| 08 | [`08_v18_to_v19_reconnect.md`](08_v18_to_v19_reconnect.md) | `[0x0002fff8] == 0x20221031` & Switch 1 fallback root-cause (`v19`, first full wake+reconnect) |
| 09 | [`09_v20_to_v22_universal.md`](09_v20_to_v22_universal.md) | Universal runtime NV Slot-0 MAC, real-ms timing, and final `v22` architecture |
