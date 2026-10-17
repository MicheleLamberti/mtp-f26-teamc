# Network Mode — common physical layer (D-R3): moved

**Superseded on 16-Oct-26 by [`NM_SPEC.md`](NM_SPEC.md)** (NM interop spec v1.0 draft), which covers the radio
settings of this v0.2 proposal and adds the frame, the gossip rules, the CRC, a test vector and the interop test.
Shareable page: NM Interop Spec artifact (link in `CLAUDE.md`).

Changes from v0.2 (9-Oct-26): the NM channel moved from RF_CH 80 (2480 MHz, BLE advertising channel 39) to
**RF_CH 77** (2477 MHz); the registers are now given in hexadecimal (RF_CH 0x4D); minimum e.i.r.p. (8 dBm) and
receiver sensitivity (≤ −90 dBm) were added. The v0.2 text is in git history.
