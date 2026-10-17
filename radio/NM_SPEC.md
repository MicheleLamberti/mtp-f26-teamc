# Network Mode interop spec — MTP F26 (draft v1.0 for all teams)

From: Team C (radio: Santiago, Andrian, Marcos · protocol: Ibrahim, Guillem, Sofia) · 16-Oct-26 ·
**Draft for agreement between all teams.** Replaces `NM_PHY_PROPOSAL.md` v0.2 (NM channel moved from
RF_CH 80 to 77, frame and gossip rules added). Reference code: <https://github.com/SantiBarrios2002/mtp-f26-teamc>
(`proto/src/nm_gossip.c`, `radio/fw/`).

## 1. Why a common spec

In Network Mode (NM) every team puts one box on the South rim and one on the East rim of Campus Nord, in a
random order. The NM-file (5 lines, about 0.5 KB) must travel from the box at the South-West corner to the
North-East end. No position switch is allowed. A team wins NM by **delivering a byte-identical copy of the
NM-file from at least one of its boxes** after STOP (rules). If every team contributes and the file reaches
the end, every team also gets the +0.5 "poker" bonus. So all boxes must speak one radio format and relay
each other's frames.

## 2. Radio (physical layer)

Any nRF24L01+ (or a genuine-compatible clone such as the Si24R1) can join with these register values.

| Item | Value |
|---|---|
| Channel | **RF_CH 77 = 2477 MHz** (above WiFi channel 11 and away from BLE advertising channel 39 at 2480 MHz; confirmed or moved after the campus survey) |
| Data rate | **250 kbps** (`RF_SETUP` RF_DR_LOW = 1, RF_DR_HIGH = 0) |
| Address | **5 bytes**. Write `TX_ADDR` and `RX_ADDR_P0` over SPI as the bytes **`C2 5A 9D 3E 71`** in that order (SPI sends the least significant byte first); as a 40-bit number this is **0x713E9D5AC2** (the value to pass to Arduino RF24's `openReadingPipe`/`openWritingPipe`) |
| CRC | hardware **CRC-16** (`CONFIG` EN_CRC = 1, CRCO = 1) |
| Payload | **dynamic length**, 1–32 bytes (`FEATURE` = 0x05: EN_DPL + EN_DYN_ACK; `DYNPD` = 0x01; `EN_AA` = 0x01, needed for DPL) |
| Acknowledgements | **none on air**: send every frame with `W_TX_PAYLOAD_NOACK` (0xB0), `SETUP_RETR` = 0x00. Chip ACKs from several receivers would collide |
| Power | **≤ 10 dBm e.i.r.p.** (CNAF UN-85 b, no hopping in NM) and **≥ 8 dBm e.i.r.p.** recommended, so the weakest box still reaches the next one. Bare nRF24 at 0 dBm with a PCB antenna is ~8 dB short: please use a PA module or a better antenna |
| Antenna | omnidirectional, **vertical polarisation** (crossed polarisation costs 10–20 dB) |
| Receiver | 1 %-packet-error sensitivity ≤ −90 dBm at 250 kbps (measure it) |
| Channel access | listen before talk recommended: RX for ≥ 170 µs, read `RPD` (register 0x09) a few times; if set, wait a random 0–2 ms and retry |

Register summary, **all values hexadecimal** (write `CONFIG` last; it powers the radio up):

```
EN_AA 0x01   EN_RXADDR 0x01   SETUP_AW 0x03   SETUP_RETR 0x00   RF_CH 0x4D (= 77)
RF_SETUP 0x20 | power bits   RX_PW_P0 0x20   FEATURE 0x05   DYNPD 0x01   STATUS 0x70 (clear)
CONFIG 0x0E (TX) / 0x0F (RX)
```

Write `SETUP_AW` = 0x03 **before** the two address registers, or the fifth address byte may not latch.

**Teams not using an nRF24** (e.g. CC2500, SX1280 in GFSK): you must reproduce Nordic's Enhanced ShockBurst
frame bit for bit: 1 B preamble (0xAA or 0x55, matching the first address bit), the 5-byte address MSB first,
a 9-bit packet control field (6-bit payload length, 2-bit PID, NO_ACK bit = 1), the payload, and a CRC-16
(CCITT, init 0xFFFF) over address + control field + payload, GFSK at 250 kbps with ±160 kHz deviation.
Tell us early: it is hard, and we would rather adapt together.

## 3. Frame (one per radio packet)

```
byte:  0      1-2        3      4       5 .. 5+n-1       5+n .. 6+n
       0x4E   file_id    idx    total   data (n ≤ 25)    crc16
       'N'    big-endian                                 big-endian
```

- **type** `0x4E` ('N'): any other first byte is not an NM frame and is ignored.
- **file_id**: CRC-16/CCITT-FALSE of the **whole** NM-file (see §5). Identifies the file and checks it end to end.
- **idx**: chunk number, 0 … total−1. Chunk *i* is file bytes [25·i, 25·i + 25) (the last one may be shorter).
- **total**: number of chunks, ⌈length / 25⌉, 1 … 64 (so files up to 1600 B; a 5-line UTF-16 file fits).
- **data**: the chunk, unchanged (no compression, no re-encoding).
- **crc16**: CRC-16/CCITT-FALSE over bytes 0 … 4+n (everything before it). The radio's own CRC protects each
  hop; this one protects the chunk end to end across relays.
- Frame length on air = 7 + n bytes (32 for a full chunk).

## 4. Behaviour of every box (gossip, no routing)

Based on the Trickle algorithm (IETF RFC 6206). No addresses, no positions, no routing table.

1. **At GO** every box starts empty: forget anything from earlier rounds or tests (do not keep NM state across
   power-up). The origin box (the South-West corner) loads the NM-file from its USB stick, cuts it into chunks
   and holds them all.
2. **Receive** on RF_CH 77 whenever not transmitting. For each frame: check type 0x4E, length 8–32, crc16,
   `idx < total ≤ 64`. Adopt the `file_id` and `total` of the **first valid frame** heard; ignore frames with a
   different `file_id` or `total` afterwards. Store each new chunk; count a chunk you already hold as a
   duplicate.
3. **Transmit** on a timer: an interval I starts at **Imin = 1 s**. At a random moment in [I/2, I), if fewer than
   **k × total** duplicate frames (k = 3) were heard in this interval, broadcast **every chunk you hold**, back
   to back; otherwise stay silent this interval. At the end of the interval, double I up to **Imax = 8 s**.
4. **Hearing a new chunk** (one you did not have) resets I to Imin, so the file spreads quickly; once every box
   has it the channel quietens down by itself.
5. **Complete** when all `total` chunks are held **and** CRC-16 of the reassembled file equals `file_id`.
   Write the file to non-volatile memory at once (not only at STOP), then **keep gossiping until STOP**: boxes
   further down the rim may still need it.
6. **After STOP**: write the NM-file to the team's USB stick, byte-identical. File name: as the professors
   decide (Atenea questions Q9/Q21); until then `NM_FILE.TXT`. Optionally also a relay log (`NM_LOG.TXT`,
   §7).

Airtime: a full rebroadcast of a 20-chunk file is ~34 ms; in our simulator the busiest of 8–10 boxes transmits
about 1.1 s in 5 minutes, and all 10 boxes of a line hold the file after 12 s (10 % loss to the next box,
70 % two boxes away) or 43 s (30 % / 95 %).

## 5. CRC-16/CCITT-FALSE

Polynomial 0x1021, initial value 0xFFFF, no input/output reflection, no final XOR. Check value: CRC of the
ASCII string `123456789` = **0x29B1**.

```c
uint16_t crc16_ccitt(const uint8_t *data, size_t len)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
    }
    return crc;
}
```

## 6. Test vector

NM-file (56 bytes, CRLF line ends): `Line 1 of the NM file.\r\nLine 2: hola equipos MTP-F26!!\r\n`
→ file_id **0xA7E6**, total **3**. The three frames, hex:

```
chunk 0: 4E A7 E6 00 03 4C 69 6E 65 20 31 20 6F 66 20 74 68 65 20 4E 4D 20 66 69 6C 65 2E 0D 0A 4C 87 6B
chunk 1: 4E A7 E6 01 03 69 6E 65 20 32 3A 20 68 6F 6C 61 20 65 71 75 69 70 6F 73 20 4D 54 50 2D 46 76 6D
chunk 2: 4E A7 E6 02 03 32 36 21 21 0D 0A 0A E5
```

If your code builds these exact bytes from that file, and reassembles the file from them, you interoperate.

## 7. Relay log (optional, recommended)

Evidence that a box took part, written next to its copy: role (origin/relay), file_id, CRC-32, when the
first frame was heard and the file completed, how many broadcasts and frames it sent, when each chunk first
arrived. Plain text. Our format: `proto/src/nm_log.c`. Not required by the rules; the copy is the proof.

## 8. Interop test

1. **By Fri 6-Nov (week 7):** each team brings one box. Every box sends 1 000 NM frames to every other box at
   10 m on RF_CH 77; pass = ≥ 99 % received with a valid crc16.
2. Then a gossip run in one room: one box starts with the test-vector file; pass = every box writes an identical
   copy within 60 s.
3. **Fri 20-Nov:** full rehearsal along part of the rims, all teams.

## 9. Not part of NM, but please agree for MRM

Everyone transmits at 20 dBm in MRM, which for these narrowband radios means frequency hopping with listen
before talk (EN 300 328 adaptive FHSS). To keep teams from colliding in a fixed pattern: **use your own hop
order** (Team C: stride 7 over its channel list; pick another stride or your own permutation), **listen before
every hop**, and ask the organisers for **≥ 10 m between teams' boxes** at each end (more between the senders).

## 10. Changes

- v1.0 draft (16-Oct-26): NM channel RF_CH 80 → **77** (BLE advertising channel 39 is 2480 MHz); frame,
  gossip rules, CRC and test vector added; ≤ 64 chunks; minimum e.i.r.p. and sensitivity; interop dates.
- v0.2 (9-Oct-26): nRF24 PHY proposal (`NM_PHY_PROPOSAL.md`).
