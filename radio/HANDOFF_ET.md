# Radio → Electronics handoff — Ebyte E01-ML01SP4 (nRF24L01+ PA/LNA), 2.4 GHz, one omni

From: Radio Team (Santiago, Andrian, Marcos) · To: Electronics Team (Carlos, Michele, Bikash,
Guillem) · Version 0.4, 16-Oct-26 (v0.4: D-R6, higher TX power while hopping in SRI/MRM; v0.3 SP4 + omni;
v0.2 had two DP5 modules and patches; v0.1 the RFM69 at 868 MHz) ·
Status: **module and antenna decided 13-Oct (Santiago, with Marcos)**, see `DECISIONS.md` D-R2c / D-R5c.

Per the team's division of decisions, the RT picks the transceiver and ET adapts to it and picks
the micro. This sheet lists what the micro and board must provide.

## Part

- **Ebyte E01-ML01SP4**, one per box: genuine Nordic nRF24L01P + PA/LNA, SMD **14.85 × 18 mm**, 10 pads
  at **1.27 mm** pitch, **IPEX (U.FL) antenna socket on the module**. Not the E01C-* parts (Si24R1 clone).
- Antenna: **Molex 146153-0100** flex dipole (34.9 × 9 mm, 100 mm cable, U.FL) plugged straight into the
  module, stuck vertically on a box wall. No RF trace or RF connector on our PCB.
- Order (D-R2c): 6 × E01-ML01SP4, 4 × Molex 146153-0100, 2 × U.FL-to-SMA pigtails (lab measurements).

## Electrical interface (Ebyte E01-ML01SP4 user manual, section 3)

| Pad | Signal | Direction (micro) | Notes |
|---|---|---|---|
| 1 | VCC | supply | **2.0–3.6 V, abs. max 3.6 V.** Never the battery rail (Li-ion reaches 4.2 V). ~120 mA peak in TX, 26 mA in RX |
| 2 | CE | out | High = RX on / pulse ≥ 10 µs = send one frame |
| 3 | CSN | out | SPI chip select, active low |
| 4 | SCK | out | **SPI mode 0**, MSB first, ≤ 10 MHz (8 MHz is plenty: 250 kbps = 31 kB/s) |
| 5 | MOSI | out | |
| 6 | MISO | in | |
| 7 | IRQ | in (optional) | Active low: TX done / RX ready. The driver polls today |
| 8–10 | GND | — | Solid ground under the module; no traces under it on the top layer (Ebyte §4.1) |

The module drives its own PA/LNA switch from the nRF24, so there is **no TXEN/RXEN** to wire.
Check the pad drawing (1.27 mm pitch, pad 0.8 × 1.5 mm per the manual) before making the footprint.

## Power

- A dedicated **3.3 V LDO for the radio** (e.g. AP2112K-3.3 or TLV75533, ≥ 300 mA) from the switched battery
  rail, with **100 µF + 10 µF + 100 nF** at the module. PA/LNA modules are sensitive to supply noise:
  short, wide VCC/GND, away from the 5 V boost.
- **D-R6 (baseline since 16-Oct):** SRI/MRM hop at up to 20 dBm e.i.r.p., so the same SP4 runs at RF_PWR −12
  or −6 and TX bursts move toward the datasheet's **120 mA**. Same parts; size the LDO,
  the bulk capacitor and the battery path for 120 mA peaks (they already are). No hardware change.

## What the micro needs (radio side only)

- One SPI master plus CSN, CE and IRQ: **6 GPIOs** (5 without IRQ).
- A microsecond clock and a busy-wait delay: everything the driver's HAL needs (`fw/nrf24.h`).
- Proposed Pico 2 pins: SPI0 GP16 MISO / GP18 SCK / GP19 MOSI, CSN GP17, CE GP20, IRQ GP21
  (see `hw/KICAD_SESSION_PROMPT.md`).
- **No WiFi/BT chip on the board** (protocol ban), and no micro with an integrated radio.

## Breakout from day one

Modules shown at Quick Mode are final, and the SP4 is SMD. So the first bench test already needs the SP4
on a small breakout (lab-made, 1.27 mm pads → 2.54 mm header) or on the carrier PCB. There is no
breadboard-friendly variant of the same part.

## Firmware

`radio/fw/` is a portable C99 driver (no Arduino or vendor dependencies) with host tests
(`make -C radio/fw test`, 194 checks against a mock nRF24). The board only has to implement
`nrf24_hal_t`: select, transfer, ce, delay_us, micros. Register profiles come from
`radio/phy_config.py`. The driver refuses any power setting above RF_PWR −18 dBm (10 mW e.i.r.p. limit),
except for the hopping profile `TEAM_FHSS` (D-R6, the SRI/MRM baseline), which may use −12 but must pass a listen-before-talk
check (`nrf24_cca`) before every burst. It needs the 100 ms power-on wait and nothing else from the board.

## Placement and antenna

- Module near the wall that carries the antenna, so the 100 mm cable reaches without strain.
- Antenna vertical, **as high in the box as possible** (antenna height is our biggest link-budget lever),
  ≥ 1–2 cm from the battery, the PCB copper, the USB cable and the 5 V boost.

## Needed back from ET

1. OK on the SP4, the radio LDO and the pin map.
2. Who makes the SP4 breakout for the first bench test, and when.
3. Power budget check: battery + regulators deliver the TX peak without brown-out.
4. The box inside height and where the antenna can sit highest.
