# Carrier rev C ("simple") — shopping list (2 boxes + 1 spare = 3 boards)

24-Oct-26. Stock and prices read on the shop pages on 24-Oct-26, EUR excl. VAT. **Re-check before paying.** Build
guide: `hw/REVC_GUIDE.md`. Per-box BoM (`hw/BOM_revC.csv`) **€148.29** (cap €150), of which €115.24 bought by the team.

## How to order (for the team) — four orders

1. **DigiKey.es — one cart with almost everything:** log in at digikey.es → *BOM Manager* (or *Quick Add* → *Upload*)
   → upload **`hw/teamc-carrier-simple/order/digikey_cart.csv`** (columns: DigiKey part number, manufacturer part
   number, quantity for 3 boards incl. spares, our reference). ≈ **€164.45 excl. VAT**. Free delivery to Spain above
   €50 (check at checkout). The two Pololu modules (2183-…) are DigiKey marketplace items and may arrive separately.
   It includes the **charger, Adafruit #4410** (24-Oct: no TP4056 USB-C board with protection was orderable).
2. **Kiwi Electronics:** 3 × Adafruit MAX17048 #5580, 3 × 40-way GPIO ribbon (code 1160), 1 × M2.5 nylon screw +
   standoff set (KW-2754, the Pi standoffs) — ≈ €35.43 excl.
3. **TME:** the panel switches and button (3 × PS1024ABLK, 6 × 100SP1T1B1M1QEH, 3 × 100SP3T1B1M1QEH) — ≈ €28.35.
   Buying them at TME instead of DigiKey keeps the box under €150 (Santiago's budget lever).
4. **nkon.nl:** 3 × Keeppower P1835J protected 18650 (3500 mAh, 69.1 mm) — ≈ €24.66 excl. + shipping.

Links, stock and prices for 2–4: `hw/teamc-carrier-simple/order/other_shops.md`. Full per-line check:
`hw/teamc-carrier-simple/order/order_check.md`. Grand total for 3 boards ≈ **€253 excl. / €306 incl. VAT**
(excl. shipping outside DigiKey).

### Check before paying
- **Cell fit:** the MPD BH-18650-PC holder is made for protected cells, but its inside length was not verified
  against the 69.1 mm Keeppower — buy one cell first, or check the holder's datasheet. Also confirm nkon ships to Spain.
- **40-way ribbon (Kiwi 1160):** checked 24-Oct: the page says it plugs onto the Pi's 40-pin header (so female
  sockets; Kiwi sells the male/female "extender" separately) but does not state female-female or keying in words —
  every comparable 20 cm rainbow GPIO cable is female-female. Buy it (or ask Kiwi to confirm); **keying is not
  needed**: the guide (step F) has you line up the marked wire with pin 1 at both ends and beep-check before power.
- **Charger #4410:** on arrival close its **500 mA solder jumper** (default 100 mA); see the guide.

### Changes from the first list (24-Oct order check)
- **C1/C9 100 µF:** KEMET **ESS107M016AE2EA** (6.3 mm, 2.50 mm leads, 8.5 mm tall). Panasonic EEU-FR1C101 is 5 mm with
  2.0 mm leads (does not fit the footprint); the exact EEU-FC1C101 is out of stock until December. Schematic updated.
- **Red LED:** Kingbright **WP7113SURDK** (WP7113ID out of stock until 10-Dec).
- LED clips, M3 standoffs and nylon screws now from DigiKey (TME minimum order; one order instead of two).
- JST crimps come in strips of 100 at DigiKey (48 needed).

**Botland (botland.store) is now business-only (B2B)** — it was the rev B source for the Pololu modules, the TP4056
and the ribbon.

Already bought or owned (not in this list): 2 × Raspberry Pi 3 A+, microSD cards, 4 × E01-ML01SP4 with antennas
(19-Oct). The third (spare) board needs no Pi or radio of its own.

## 1. DigiKey.es (in `order/digikey_cart.csv`)

| Item | Per box | Buy | Unit € | DigiKey PN (stock 24-Oct) |
|---|---|---|---|---|
| Pololu **U3V70F5** 5 V boost (#2891) | 1 | 3 | 22.78 | 2183-2891-ND (152) |
| Pololu **ideal diode** #5388 | 1 | 3 | 5.70 | 2183-5388-ND (500) |
| **MCP1700-3302E/TO** 3.3 V regulator, TO-92 | 1 | 4 | 0.44 | MCP1700-3302E/TO-ND (11,755) |
| MPD **BH-18650-PC** cell holder | 1 | 3 | 2.94 | BH-18650-PC-ND (9,726) |
| **1N5822** Schottky (reversed-cell guard) | 1 | 4 | 0.54 | 497-11370-1-ND (14,375) |
| Littelfuse **P4KE10A** TVS, DO-41 (D12–D16) | 5 | 15 | 0.371 | 18-P4KE10ACT-ND (1,543) |
| Keystone **3517** 5×20 fuse clips | 2 | 6 | 0.42 | 36-3517-ND (50,892) |
| Littelfuse **0217004.HXP** 5×20 mm F4A fuse (fitted + spare) | 2 | 6 | 0.44 | F2394-ND (4,721) |
| KEMET **ESS107M016AE2EA** 100 µF 16 V | 2 | 10 | 0.114 | 399-18280-1-ND (14,855) |
| Vishay **K104K10X7RF5UH5** 100 nF | 2 | 10 | 0.155 | BC2665CT-ND (186,026) |
| TDK **FG28X7R1E105KRT06** 1 µF | 2 | 10 | 0.183 | 445-173583-1-ND (85,335) |
| Yageo MFR-25 **1 kΩ / 330 Ω / 10 kΩ / 33 Ω** | 5 / 2 / 1 / 3 | 20 / 10 / 10 / 10 | ~0.04 | 1.00KXBK-ND, MFR-25FBF52-330R-ND, 10.0KXBK-ND, 13-MFR-25FBF52-33R-ND |
| Keystone **5010** red test point (TP1) | 1 | 3 | 0.30 | 36-5010-ND |
| Würth **61204021621** 2×20 shrouded box header | 1 | 3 | 1.01 | 732-5401-ND (1,700) |
| Sullins **PPTC081LFBN-RC** 1×8 socket (breakout) | 1 | 3 | 0.51 | S7006-ND (84,501) |
| Sullins **PRPC040SAAN-RC** 1×40 male strip | 1 | 3 | 1.08 | S1011EC-40-ND (45,098) |
| JST **B2B-XH-A** / **B3B-XH-A** headers | 4 / 2 | 12 / 6 | 0.076 / 0.11 | 455-B2B-XH-A-ND, 455-2248-ND |
| JST **XHP-2** / **XHP-3** housings, **SXH-001T-P0.6** crimps | 4 / 2 / 16 | 12 / 6 / 100 | 0.052 / 0.09 / 0.041 | 455-2266-ND, 455-2219-ND, 455-1135-100-ND |
| Adafruit **Micro-Lipo USB-C charger #4410** (at the box wall) | 1 | 3 | 5.22 | 1528-4410-ND (966) |
| Kingbright **WP7113GD** green / **WP7113SURDK** red 5 mm LEDs | 1 + 1 | 10 + 10 | 0.135 / 0.168 | 754-1263-ND, 754-WP7113SURDK-ND |
| Kingbright **RTC51** LED panel clips | 2 | 6 | 0.45 | 754-RTC51-ND (1,047) |
| Keystone **25510** M3 × 10 nylon standoff F/F (carrier) | 4 | 12 | 0.59 | 36-25510-ND (19,042) |
| Essentra **MTS-11** M3 × 11 nylon standoff (breakout, H30) | 1 | 3 | 0.68 | RPC4425-ND (12,230) |
| Essentra M3 × 6 nylon screws | — | 40 | 0.077 | RPC7002-ND (61,147) |

If DigiKey runs out of the P4KE10A, any maker's P4KE10A in DO-41 fits (Vishay P4KE10A-E3/54, ST, onsemi).

## 2. Other shops (details and links: `order/other_shops.md`)

| Item | Shop | Buy | Unit € excl. |
|---|---|---|---|
| Adafruit **MAX17048** fuel gauge #5580 | Kiwi (ADA-5580, 41 in stock) | 3 | 5.69 |
| 40-way GPIO ribbon 20 cm, female-female (keying not needed, see the guide step F) | Kiwi (1160, 50 in stock) | 3 | 2.79 |
| M2.5 black nylon screw + standoff set, 380 pcs (Pi standoffs) | Kiwi (KW-2754, 43 in stock) | 1 | 9.99 |
| E-Switch **PS1024ABLK** push button (GO/STOP) | TME (1,379) | 3 | 1.31 |
| E-Switch **100SP1T1B1M1QEH** toggle (power, role) | TME (654) | 6 | 2.44 |
| E-Switch **100SP3T1B1M1QEH** ON-OFF-ON toggle (mode) | TME (906) | 3 | 3.26 |
| Keeppower **P1835J** protected 18650 3500 mAh (button top, 69.1 mm) | nkon.nl (alt. tinytronics.nl €9.50) | 3 | 8.22 |

On arrival, check the jumper SJ2 on each MAX17048 (guide, step A4).

## 3. Lab stock / already in the team

22 AWG insulated solid wire (wire links), bare tinned copper wire (~0.8 mm, test loops TP2–TP4), 24 AWG hook-up wire
(panel leads), cable ties, hot glue, Kapton tape, solder, flux; the UPC lab mills the boards (counted at €15 each).
