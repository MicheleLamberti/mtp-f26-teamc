# Carrier rev C — non-DigiKey orders, 3 boards (24-Oct-26, EUR excl. VAT unless noted)

The DigiKey part is `digikey_cart.csv` (upload in BOM Manager). These are the other three shops.

## Kiwi Electronics (kiwi-electronics.com) — ≈ €35.43
| Part | Qty | Link | Stock 24-Oct | Unit |
|---|---|---|---|---|
| Adafruit MAX17048 #5580 fuel gauge (ADA-5580) | 3 | https://www.kiwi-electronics.com/en/adafruit-max17048-lipoly-liion-fuel-gauge-battery-monitor-11061 | 41 | 5.69 (6.88 incl.) |
| 40 pins GPIO cable 20 cm (code 1160), female-female (page: "connects to the Pi's 40-pin GPIO header"; keying not needed, guide step F) | 3 | https://www.kiwi-electronics.com/en/40-pins-rainbow-gpio-cable-20cm-1160 | 50 | 2.79 |
| M2.5 black nylon screw + stand-off set, 380 pcs (KW-2754): Pi standoffs + screws for all boxes | 1 | https://www.kiwi-electronics.com/en/m2-5-screw-and-stand-off-set-black-nylon-380-pieces-10252 | 43 | 9.99 (11.89 incl.) |

## TME (tme.eu) — ≈ €28.35 (prices were shown in USD to our reader; counted 1:1, the EUR price is lower)
Santiago's budget lever (24-Oct): the panel switches here instead of DigiKey keep the box under €150.
| Part | Qty | Link | Stock 24-Oct | Unit |
|---|---|---|---|---|
| E-Switch PS1024ABLK push button (GO/STOP) | 3 | https://www.tme.eu/en/details/ps1024ablk/push-button-switches/e-switch/ | 1,379 | 1.31 |
| E-Switch 100SP1T1B1M1QEH toggle (power, role) | 6 | https://www.tme.eu/en/details/100sp1t1b1m1qeh/toggle-switches/e-switch/ | 654 | 2.44 (5+) |
| E-Switch 100SP3T1B1M1QEH ON-OFF-ON toggle (mode) | 3 | https://www.tme.eu/en/details/100sp3t1b1m1qeh/toggle-switches/e-switch/ | 906 | 3.26 |
If TME is inconvenient: the same three parts are on DigiKey (EG2011-ND, EG2350-ND, EG2375-ND), ≈ €2.2 per box more —
the box then lands at ≈ €150.4, just over the cap.

## nkon.nl (Netherlands) — ≈ €24.66 + shipping
| Part | Qty | Link | Stock | Unit |
|---|---|---|---|---|
| Keeppower 18650 3500 mAh protected, button top (P1835J), 69.1 mm, 10 A | 3 | https://www.nkon.nl/en/keeppower-18650-3500-li-ion.html | in stock | 8.22 (9.95 incl. NL VAT) |
Alternative: https://www.tinytronics.nl/en/power/batteries/18650/keeppower-18650-li-ion-battery-3500mah-10a (€9.50 excl.).
Before buying 3: the fit in the MPD BH-18650-PC holder is not verified (buy one first or check the holder datasheet);
confirm nkon ships to Spain.

## Charger (decided 24-Oct): Adafruit Micro-Lipo USB-C #4410 — on the DigiKey cart (1528-4410-ND, 966 in stock)
The TP4056 USB-C boards with protection were not orderable on 24-Oct (TinyTronics 2–4 weeks, Grobotronics and
Electrokit out of stock, Amazon.es 3-pack apparently out of stock, AZ-Delivery stock unknown). The protected 18650 has
its own protection, so the #4410 (no protection IC) is fine. Close its 500 mA jumper; a full charge takes ~7–8 h.
