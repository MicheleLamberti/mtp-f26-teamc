# Team C hardware — design notes (DRAFT – for ET review)

MTP F26 · Team C · started 19-Oct-26 in the KiCad session (`hw/KICAD_SESSION_PROMPT.md` v2).
Owner of the boards: **ET (Carlos, Michele, Bikash, Guillem)**. Everything here is a proposal from the radio team
unless `CLAUDE.md` says it is decided. Fixed parts (ordered 19-Oct): Raspberry Pi 3 Model A+, Ebyte E01-ML01SP4,
Ebyte TX2400-FPC-2509 flex antenna, SanDisk Ultra 32 GB A1 microSD.

## Boards

| Board | Folder | Purpose |
|---|---|---|
| SP4 breakout | `hw/sp4-breakout/` | E01-ML01SP4 → 1 × 8 2.54 mm header for the bench (T0/T2) from day one |
| Pi 3 A+ HAT carrier | `hw/teamc-carrier/` | Radio, power (boost, LDO, charger, fuel gauge), UI, on the Pi's 40-pin header |
| Project library | `hw/lib/` | `teamc.kicad_sym` + `teamc.pretty/` (E01-ML01SP4 and parts missing from the KiCad libraries) |

## Net table

Global labels between the carrier's sheets use exactly these names.

| Net | What | From → to |
|---|---|---|
| `VBAT` | Cell +, after the reverse-polarity FET; charger output | holder(s) → RP-FET → charger, fuel gauge, slide switch |
| `VBAT_SW` | Switched cell | slide switch → boost input, radio LDO input |
| `5V_PI` | 5.1 V for the Pi, after back-power protection | boost → header pins 2/4 |
| `3V3_RADIO` | Radio supply (never the Pi's 3V3, never the cell) | LDO → SP4 pad 1 |
| `3V3_PI` | The Pi's own 3.3 V (header 1/17): pull-ups only, no load | header → pull-ups |
| `VBUS_USB` | USB-C charge input (5 V) | USB-C → TVS → MCP73831 VDD |
| `GND` | Ground | everywhere |
| `SPI_SCK` / `SPI_MOSI` / `SPI_MISO` | SPI0 | GPIO 11 / 10 / 9 ↔ SP4 pads 4 / 5 / 6 |
| `RADIO_CSN` | SPI0 CE0 | GPIO 8 → SP4 pad 3 |
| `RADIO_CE` | Radio CE | GPIO 22 → SP4 pad 2 |
| `RADIO_IRQ` | Radio IRQ, active low | SP4 pad 7 → GPIO 24 |
| `I2C_SDA` / `I2C_SCL` | I2C1 (1.8 kΩ pull-ups on the Pi) | GPIO 2 / 3 ↔ MAX17048 |
| `FG_ALRT` | Fuel-gauge alert, open drain | MAX17048 → GPIO 25 |
| `BTN_TXRX` | GO/STOP button, active low | button → GPIO 17 |
| `SW_ROLE` | Role switch TX/RX, active low = TX | switch → GPIO 27 |
| `SW_MODE_NM` / `SW_MODE_MRM` | Mode switch, active low; neither = SRI | switch → GPIO 23 / GPIO 16 |
| `LED_ACT` / `LED_STATUS` | LEDs, active high | GPIO 5 / 6 → LED + resistor → GND |
| `CHG_STAT` | MCP73831 STAT (needs level care: STAT is powered from VBUS) | charger → GPIO 26 |
| `UART_TX` / `UART_RX` | Console | GPIO 14 / 15 ↔ debug header |

## Pin map (BCM GPIO, header pin)

Matches `proto/port/linux/ui.c` (inputs with the Pi's internal pull-up, active low; LEDs active high; MAX17048 at
I2C address 0x36) and `radio/fw/linux/README.md`.

| GPIO | Pin | Net | | GPIO | Pin | Net |
|---|---|---|---|---|---|---|
| 2 | 3 | I2C_SDA | | 17 | 11 | BTN_TXRX |
| 3 | 5 | I2C_SCL | | 27 | 13 | SW_ROLE |
| 14 | 8 | UART_TX | | 23 | 16 | SW_MODE_NM |
| 15 | 10 | UART_RX | | 16 | 36 | SW_MODE_MRM |
| 22 | 15 | RADIO_CE | | 5 | 29 | LED_ACT |
| 24 | 18 | RADIO_IRQ | | 6 | 31 | LED_STATUS |
| 10 | 19 | SPI_MOSI | | 25 | 22 | FG_ALRT |
| 9 | 21 | SPI_MISO | | 26 | 37 | CHG_STAT |
| 11 | 23 | SPI_SCK | | — | 2, 4 | 5V_PI |
| 8 | 24 | RADIO_CSN | | — | 1, 17 | 3V3_PI |
| — | 6, 9, 14, 20, 25, 30, 34, 39 | GND | | 0 / 1 | 27 / 28 | ID_SD / ID_SC: not connected (no ID EEPROM) |

## Sheets of the carrier

| Sheet | Contents |
|---|---|
| `power` | 18650 holder(s), reverse-polarity FET, USB-C charge-only + TVS, MCP73831, slide switch, 5.1 V boost, back-power protection + TVS + bulk at the header, radio LDO (+ buck-boost option), MAX17048 fuel gauge (sits on the cell), test points |
| `pi_header` | 40-pin header, `3V3_PI`, GND pins, UART debug header |
| `radio` | E01-ML01SP4, decoupling 100 µF + 10 µF + 100 nF, IRQ/CSN pull-ups, test point |
| `ui` | Button, role switch, mode switch, ESD, RC, LEDs |
