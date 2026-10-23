# Carrier rev B — shopping list (2 boxes + 1 spare)

Stock and prices checked 23-Oct-26 (live: Botland stock API, TME product pages, LCSC; Mouser/Farnell via an
aggregator, may lag a few days). **Re-check before paying.** Parts and why: `hw/REVB_LAB_PLAN.md`.

## 1. Botland (botland.store) — the modules. Order first: lots are small. GLS to Spain ~8 EUR, ships in 24 h

| Item | Qty | Unit (gross) | Total | Stock 23-Oct |
|---|---|---|---|---|
| Pololu **U3V70F5** 5 V step-up (#2891) | 3 | 18.90 EUR | 56.70 EUR | 39 |
| Pololu **ideal diode 4–60 V 20 A** (#5388) | 3 | 5.90 EUR | 17.70 EUR | 25 |
| Adafruit **MAX17048** fuel gauge (#5580) | 3 | 8.00 EUR | 24.00 EUR | 21 (+17 on 3 Nov) |
| **TP4056 USB-C charger with protection** (HW-373 v1.2.1) | 4 | 1.00 EUR | 4.00 EUR | 319 |
| | | | **~102 EUR + shipping** | |

Alternatives: MAX17048 #5580 at Kiwi Electronics 6.88 EUR; U3V70F5 at Robotshop EU 25.24 EUR (backorder).
Backup boost S13V30F5 (Botland 14.50 EUR, 35 pcs) — idles at 10–20 mA, so only if the U3V70F5 is gone.

## 2. TME (tme.eu) — small parts

| Item | Qty | Note |
|---|---|---|
| **AP2112K-3.3TRG1** radio LDO, SOT-23-5 | 5 | 1231 pcs, ~0.24 USD |
| **AO3401A** P-FET (reverse-cell fallback) | 5 | 3425 pcs, ~0.33 USD |
| JST **B2P-VH** (cell) | 3 | from 1 pc |
| JST **B2B-XH-A** (button, role, power toggle, charger lead) | 12 | from 1 pc |
| JST **B3B-XH-A** (mode toggle) | 3 | 24,903 pcs |
| Housings **XHP-2** ×12, **XHP-3** ×3, **VHR-2N** ×3; crimps **SXH-001T-P0.6** ×40 | — | from 1 pc |
| E-Switch **PS1024ABLK** button | 3 | 1385 pcs, 1.31 USD |
| E-Switch **100SP1T1B1M1QEH** toggle (power, role) | 6 | 654 pcs, 2.60 USD |
| E-Switch **100SP3T1B1M1QEH** ON-OFF-ON (mode) | 3 | 906 pcs, 3.25 USD |

## 3. Mouser (or Farnell) — what TME lacks

| Item | Qty | Note |
|---|---|---|
| **DMP2035U-7** P-FET (reverse cell) | 5 | Mouser 1544, Farnell 3228 (LCSC C110499) |
| **0466005.NR** 5 A very-fast 1206 fuse | 5 | Mouser 18,515, ~1.04 USD (LCSC 0466005.NRHF C57525) |
| JST **SVH-21T-P1.1** crimps (VH) | 8 | TME sells only a 4,500 reel |

## 4. Generic (Botland / Amazon.es / lab stock) — not stock-checked

| Item | Qty |
|---|---|
| 2x20 2.54 mm **shrouded box header**, straight | 3 |
| **40-way female-female GPIO ribbon**, <= 10 cm | 3 |
| 1x8 2.54 mm **female socket**, ~8.5 mm (SP4 breakout) | 3 |
| 2.54 mm **male header strip**, 40-pin break-away (modules, breakout) | 4 |
| **M3 x 11 mm nylon standoffs** F/F + M3 x 6 screws | 12 + 24 |
| Protected **18650** >= 3000 mAh, PCM trips at **>= 3 A** | 3 |

## Small parts as in the routed rev B (`hw/BOM_revB.csv`, 23-Oct evening)
**1206** resistors and capacitors (not 0805: the routing uses the gap between their pads), 100 uF 6.3 x 5.4
electrolytics (EEE-FK1C101P) x2, **SMF5V0A-E3-08 x6** per box (D2, D3 and one per panel lead, D12–D15; the SP0504
array is no longer used), 2N7002, 0805 LEDs, 18650 holder MPD BH-18650-PC (DigiKey), ~15 cm of bare 0.6 mm tinned
copper wire per box (10 wire links). 22 uF 1206 for rev A only: **CL31A226KAHNNNE** (the GRM31CR61E226KE15L is
obsolete).

## Cost
Modules ~34 EUR per box; the whole box ~125–130 EUR (cap 150 EUR). Confirm in the rev B BoM after the design loop.
