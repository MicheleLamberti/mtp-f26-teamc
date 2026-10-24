# Carrier rev C ("simple") — shopping list (2 boxes + 1 spare = 3 boards)

24-Oct-26. Stock and prices read on the shop pages on 24-Oct-26, EUR excl. VAT. **Re-check before paying.** Build
guide: `hw/REVC_GUIDE.md`. Per-box BoM (`hw/BOM_revC.csv`) **€148.00** (cap €150), of which €114.95 bought by the team.

## How to order (for the team)

1. **DigiKey.es — one cart with almost everything:** log in at digikey.es → *BOM Manager* (or *Quick Add* → *Upload*)
   → upload **`hw/teamc-carrier-simple/order/digikey_cart.csv`** (columns: DigiKey part number, manufacturer part
   number, quantity for 3 boards incl. spares, our reference). ≈ **€185.50 excl. / €224.46 incl. VAT**. Free delivery
   to Spain above €50 (check at checkout). The two Pololu modules (2183-…) are DigiKey marketplace items and may
   arrive in a separate parcel.
2. **Kiwi Electronics:** 3 × Adafruit MAX17048 #5580 + 3 × 40-way GPIO ribbon (code 1160) — see
   `hw/teamc-carrier-simple/order/other_shops.md`. ≈ €25.44 excl.
3. **nkon.nl:** 3 × Keeppower P1835J protected 18650 (3500 mAh, 69.1 mm). ≈ €24.66 excl. + shipping.
4. **Still to pick before ordering** (see "Open" below): the TP4056 USB-C charger modules and M2.5 standoffs for the Pi.

Full per-line check (part numbers, stock, prices, what changed and why): `hw/teamc-carrier-simple/order/order_check.md`.
Grand total for 3 boards ≈ **€242 excl. / €293 incl. VAT** (excl. shipping outside DigiKey).

### Open (check before paying)
- **Cell fit:** the MPD BH-18650-PC holder is made for protected cells, but its inside length was not verified
  against the 69.1 mm Keeppower — buy one cell first, or check the holder's datasheet. Also confirm nkon ships to Spain.
- **TP4056 USB-C module with protection (DW01A), 3 + 1 spare:** pick a live Amazon.es listing (a 5-pack is ~€8 incl.);
  Amazon could not be read automatically. In-stock fallback on the DigiKey cart: Adafruit #4410 (1528-4410-ND, €5.22) —
  a different board (0.5 A, no DW01A protection): ask ET first.
- **40-way ribbon (Kiwi 1160):** confirm on the page/photo that both ends are **female** and **keyed**; 20 cm is fine.
- **M2.5 standoffs** (4 per Pi): not on DigiKey; any M2.5 nylon standoff kit (Amazon.es). The M2.5 screws are on the
  DigiKey cart.

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
| E-Switch **PS1024ABLK** push button (GO/STOP) | 1 | 3 | 1.46 | EG2011-ND (5,531) |
| E-Switch **100SP1T1B1M1QEH** toggle (power, role) | 2 | 6 | 2.70 | EG2350-ND (8,552) |
| E-Switch **100SP3T1B1M1QEH** ON-OFF-ON toggle (mode) | 1 | 3 | 4.75 | EG2375-ND (2,223) |
| Kingbright **WP7113GD** green / **WP7113SURDK** red 5 mm LEDs | 1 + 1 | 10 + 10 | 0.135 / 0.168 | 754-1263-ND, 754-WP7113SURDK-ND |
| Kingbright **RTC51** LED panel clips | 2 | 6 | 0.45 | 754-RTC51-ND (1,047) |
| Keystone **25510** M3 × 10 nylon standoff F/F (carrier) | 4 | 12 | 0.59 | 36-25510-ND (19,042) |
| Essentra **MTS-11** M3 × 11 nylon standoff (breakout, H30) | 1 | 3 | 0.68 | RPC4425-ND (12,230) |
| Essentra M3 × 6 nylon screws / M2.5 × 6 nylon screws (Pi) | — | 40 / 20 | 0.077 / 0.094 | RPC7002-ND, 145-50M025045P006-ND |

If DigiKey runs out of the P4KE10A, any maker's P4KE10A in DO-41 fits (Vishay P4KE10A-E3/54, ST, onsemi).

**Saving lever if the budget gets tight:** the E-Switch toggles and the button are cheaper at TME (about €2 per box);
that needs a second order.

## 2. Other shops (details and links: `order/other_shops.md`)

| Item | Shop | Buy | Unit € excl. |
|---|---|---|---|
| Adafruit **MAX17048** fuel gauge #5580 | Kiwi (ADA-5580, 41 in stock) | 3 | 5.69 |
| 40-way GPIO ribbon 20 cm (verify female-female + keyed) | Kiwi (1160, 50 in stock) | 3 | 2.79 |
| Keeppower **P1835J** protected 18650 3500 mAh (button top, 69.1 mm) | nkon.nl (alt. tinytronics.nl €9.50) | 3 | 8.22 |
| **TP4056 USB-C module with protection** | Amazon.es (pick a listing) | 4 | ~1.65 |
| M2.5 nylon standoff kit | Amazon.es | 1 | ~4 |

On arrival, check the jumper SJ2 on each MAX17048 (guide, step A4).

## 3. Lab stock / already in the team

22 AWG insulated solid wire (wire links), bare tinned copper wire (~0.8 mm, test loops TP2–TP4), 24 AWG hook-up wire
(panel leads), cable ties, hot glue, Kapton tape, solder, flux; the UPC lab mills the boards (counted at €15 each).
