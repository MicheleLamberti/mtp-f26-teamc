# Carrier rev C ("simple") — shopping list (2 boxes + 1 spare = 3 boards)

24-Oct-26, DRAFT. Stock and prices as read on the shop pages on 23/24-Oct-26 (per line in `hw/BOM_revC.csv`), EUR
excl. VAT. **Re-check before paying.** Build guide: `hw/REVC_GUIDE.md`. Per-box BoM total **€145.51** (cap €150),
of which €112.46 bought by the team.

**Botland (botland.store) is now business-only (B2B)** — it was the rev B source for the Pololu modules, the TP4056
and the ribbon; rev C buys them at DigiKey.es and Amazon.es instead.

Already bought or owned (not in this list): 2 × Raspberry Pi 3 A+, microSD cards, 4 × E01-ML01SP4 with antennas
(19-Oct). The third (spare) board needs no Pi or radio of its own.

## 1. DigiKey.es — almost everything (≈ €167 for 3 boards; check the free-shipping threshold at checkout)

| Item | Per box | Buy | Unit € | Link |
|---|---|---|---|---|
| Pololu **U3V70F5** 5 V boost (#2891, 2183-2891-ND) | 1 | 3 | 22.78 | [DigiKey](https://www.digikey.es/en/products/result?keywords=pololu%202891) (152, 24-Oct) |
| Pololu **ideal diode** #5388 (2183-5388-ND) | 1 | 3 | 5.70 | [DigiKey](https://www.digikey.es/en/products/result?keywords=pololu%205388) (500) |
| **MCP1700-3302E/TO** 3.3 V regulator, TO-92 | 1 | 4 | 0.44 | [DigiKey](https://www.digikey.es/en/products/result?keywords=MCP1700-3302E%2FTO) (11,755) |
| MPD **BH-18650-PC** cell holder | 1 | 3 | 2.94 | [DigiKey](https://www.digikey.es/en/products/detail/mpd-memory-protection-devices/BH-18650-PC/3029216) (9,726) |
| **1N5822** Schottky (reversed-cell guard) | 1 | 4 | 0.54 | [DigiKey](https://www.digikey.es/en/products/result?keywords=1N5822) |
| Littelfuse **P4KE10A** TVS, DO-41 (D12–D16) | 5 | 15 | 0.371 (qty 10) | [DigiKey](https://www.digikey.es/en/products/detail/littelfuse-inc/P4KE10A/715501) (1,543) |
| Keystone **3517** 5×20 fuse clips | 2 | 6 | 0.42 | [DigiKey](https://www.digikey.es/en/products/result?keywords=keystone%203517) |
| Littelfuse **0217004.HXP** 5×20 mm F4A fuse (one fitted + one spare per box) | 2 | 6 | 0.53 | [DigiKey](https://www.digikey.es/en/products/result?keywords=0217004.HXP) |
| Panasonic **EEU-FR1C101** 100 µF 16 V | 2 | 6 | 0.36 | [DigiKey](https://www.digikey.es/en/products/result?keywords=EEU-FR1C101) |
| Vishay **K104K10X7RF5UH5** 100 nF | 2 | 10 | 0.155 | [DigiKey](https://www.digikey.es/en/products/result?keywords=K104K10X7RF5UH5) |
| TDK **FG28X7R1E105KRT06** 1 µF | 2 | 10 | 0.183 | [DigiKey](https://www.digikey.es/en/products/result?keywords=FG28X7R1E105KRT06) |
| Yageo MFR-25 resistors: **1 kΩ** ×20, **330 Ω** ×10, **10 kΩ** ×10, **33 Ω** ×10 | 5 / 2 / 1 / 3 | 50 | 0.04 | [1 k](https://www.digikey.es/en/products/detail/yageo/MFR-25FBF52-1K/13011), same series for the others |
| Keystone **5010** red test point (TP1) | 1 | 3 | 0.30 | [DigiKey](https://www.digikey.es/en/products/result?keywords=keystone%205010) |
| Würth **61204021621** 2×20 shrouded box header | 1 | 3 | 1.01 | [DigiKey](https://www.digikey.es/en/products/result?keywords=61204021621) (1,700) |
| Sullins **PPTC081LFBN-RC** 1×8 socket (breakout) | 1 | 3 | 0.51 | [DigiKey](https://www.digikey.es/en/products/result?keywords=PPTC081LFBN-RC) |
| Sullins **PRPC040SAAN-RC** 1×40 male strip (module pins + UART) | 1 | 3 | 1.08 | [DigiKey](https://www.digikey.es/en/products/result?keywords=PRPC040SAAN-RC) |
| JST **B2B-XH-A** / **B3B-XH-A** headers | 4 / 2 | 12 / 6 | 0.09 / 0.11 | [B2B](https://www.digikey.es/en/products/result?keywords=B2B-XH-A), [B3B](https://www.digikey.es/en/products/result?keywords=B3B-XH-A) |
| JST **XHP-2** / **XHP-3** housings, **SXH-001T-P0.6** crimps | 4 / 2 / 16 | 12 / 6 / 50 | 0.09 / 0.09 / 0.04 | [XHP-2](https://www.digikey.es/en/products/result?keywords=XHP-2), [crimps](https://www.digikey.es/en/products/result?keywords=SXH-001T-P0.6) |
| E-Switch **PS1024ABLK** push button (GO/STOP) | 1 | 3 | 1.46 | [DigiKey](https://www.digikey.es/en/products/result?keywords=PS1024ABLK) |
| E-Switch **100SP1T1B1M1QEH** toggle (power, role) | 2 | 6 | 2.70 | [DigiKey](https://www.digikey.es/en/products/result?keywords=100SP1T1B1M1QEH) |
| E-Switch **100SP3T1B1M1QEH** ON-OFF-ON toggle (mode) | 1 | 3 | 4.75 | [DigiKey](https://www.digikey.es/en/products/result?keywords=100SP3T1B1M1QEH) |
| Kingbright **WP7113GD** green / **WP7113ID** red 5 mm LEDs | 1 + 1 | 3 + 3 | 0.20 / 0.18 | [green](https://www.digikey.es/en/products/result?keywords=WP7113GD), [red](https://www.digikey.es/en/products/result?keywords=WP7113ID) |

Not available: **TME has the P4KE10A (P4KE10A-LF) at 0 stock** (24-Oct); Mouser lists 576-P4KE10A (not verified).
If DigiKey runs out, any maker's P4KE10A in DO-41 fits (Vishay P4KE10A-E3/54, ST, onsemi).

## 2. Kiwi Electronics (kiwi-electronics.com)

| Item | Per box | Buy | Unit € | Link |
|---|---|---|---|---|
| Adafruit **MAX17048** fuel gauge #5580 | 1 | 3 | 5.69 | [Kiwi](https://www.kiwi-electronics.com/en/adafruit-max17048-lipoly-liion-fuel-gauge-battery-monitor-11061) (41, 23-Oct) |

On arrival, check the jumper SJ2 on each one (guide, step A4).

## 3. Amazon.es / AliExpress (est., not verified)

| Item | Per box | Buy | Unit € (est.) |
|---|---|---|---|
| **TP4056 USB-C charger module with protection** (HW-373) | 1 | 4 | 1.00 |
| 40-way female-female GPIO ribbon, 15–20 cm | 1 | 3 | 2.00 |
| Protected 18650 cell ≥ 3000 mAh, button top, ~69 mm (Keeppower P1835J, Nitecore NL1835; or nkon.nl) | 1 | 3 | 9.00 |
| M3 × 10 mm nylon standoffs F/F (×4 per box), M3 × 11 mm (×1), M3 × 6 nylon screws; M2.5 standoffs + screws for the Pi | — | 1 kit | ~4 |

## 4. TME (tme.eu)

| Item | Per box | Buy | Note |
|---|---|---|---|
| Kingbright **RTC-51** 5 mm LED panel clips | 2 | 6 | [TME](https://www.tme.eu/en/details/clip5mm/holders/kingbright-electronic/rtc-51/) (not verified) |

**Saving lever if the budget gets tight:** the E-Switch toggles and the button are cheaper at TME (rev B read
100SP1T1B1M1QEH 2.60 USD, 100SP3T1B1M1QEH 3.25 USD, PS1024ABLK 1.31 USD on 23-Oct): about €2 per box less. No other
change to the parts is needed to stay under €150.

## 5. Lab stock / already in the team

22 AWG insulated solid wire (wire links), bare tinned copper wire (~0.8 mm, test loops TP2–TP4), 24 AWG hook-up wire
(panel leads), cable ties, hot glue, Kapton tape, solder, flux; the UPC lab mills the boards (counted at €15 each).
