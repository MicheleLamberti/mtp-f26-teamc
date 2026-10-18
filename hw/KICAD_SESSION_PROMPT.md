# Prompt for the KiCad board-design session

Paste everything below the line into a new Claude Code session started in `~/dev/mtp-f26`.

---

We're starting the **carrier PCB** for Team C's MTP F26 transceiver, using the **KiCad MCP**
tools. Since 18-Oct-26 the micro is a **Raspberry Pi 3** (team request; Model A+ suggested), so the
board is a **HAT-style carrier on the Pi's 40-pin header**. Read `CLAUDE.md` first: team, calendar,
the decisions so far and the git rules. Then read `radio/HANDOFF_ET.md`, `radio/DECISIONS.md` (D-R1b band;
D-R2c module and D-R5c antenna, decided 13-Oct; D-H1 the Pi 3), `radio/hw_proposal.html` (hardware suggestion v0.5),
`radio/pi3_impact.html` (what the Pi 3 changes) and the "Mechanical Features" and "Telecom and Electronics Hardware"
sections of the competition rules (`docs/`, if present locally).

**Ownership:** the electronics team (Carlos, Michele, Bikash, Guillem) owns the board and the micro
choice. This is the radio team's **draft for them to review**. Label the schematic and the PCB
"DRAFT – for ET review", and never present a choice as agreed unless `CLAUDE.md` says so.

## Hard constraints (competition rules)

- **One and only one module with a microprocessor** (the Pi 3). No other part may contain a CPU:
  no micro + radio combo boards, no fuel gauge or charger with its own MCU.
- **No chip implementing WiFi, Bluetooth, ZigBee, 2G–5G.** The Pi 3 carries a WiFi/BT chip (CYW43455 on the
  A+/B+, BCM43438 on the B). Working assumption (Santiago, 18-Oct): it is disabled for good in software or
  desoldered; **Atenea Q22** asks which. Nothing on our HAT may add another wireless chip.
- Everything fits **inside an IKEA 365+ box, 15 × 15 × 7 cm** (outside). Only connectors, switches
  and buttons may stick out. Operates **autonomously** on battery; no cables plugged in during a round.
- **At least one Tx/Rx switch or button** and a **pilot light that blinks in Tx/Rx**. Extra
  switches are allowed (e.g. a network-mode switch), but **no switch may indicate the position
  in the network**.
- **Drop test** from table height to concrete before MRM: nothing loose. The HAT is either soldered to the
  Pi's header pins or held by four standoffs; the microSD card is taped; the battery is strapped.
- ESD and RF-exposure compliance (the rules name IEEE C95.1 for RF exposure and EN 60825-1 / ANSI Z136.5
  for lasers; ESD protection on every connector and button people touch). Cost **≤ €150 per device**. A board made at the
  ETSETB lab counts **€15** in the BoM, and every part (screws, wire, foam, the Pi even if owned) must be in the BoM.
- **Modules shown at Quick Mode are final:** the Pi 3 model and the Ebyte E01-ML01SP4 radio must be
  the same parts on the bench, at Quick Mode and in the final board. The SP4 is SMD, so it needs a
  breakout or this board from the first bench test.

## Decided parts (baseline; ET may challenge)

| Function | Part | Notes |
|---|---|---|
| Micro module | **Raspberry Pi 3 Model A+** (B if the team owns them) | The HAT plugs onto the 40-pin header (2 × 20, 2.54 mm). A+ outline 65 × 56 mm, M2.5 holes on 58 × 49 mm. KiCad has a `Connector_PinSocket_2.54mm` 2 × 20 footprint and RPi HAT templates; check the hole pattern |
| Radio | **1 × Ebyte E01-ML01SP4** (nRF24L01P + PA/LNA, SMD 14.85 × 18 mm, IPEX on the module) | 10 pads, **1.27 mm** pitch: 1 VCC, 2 CE, 3 CSN, 4 SCK, 5 MOSI, 6 MISO, 7 IRQ, 8–10 GND (Ebyte manual §3). **Draw the footprint from the manual's pad drawing.** No traces under the module on the top layer; ground pour under it. Place it at the HAT edge away from the Pi's SoC. Also make a tiny **breakout** (SP4 → 2.54 mm header) for the bench |
| Antenna | **Molex 146153-0100** flex dipole, cable plugs into the module's IPEX | No RF on our PCB. Leave clearance around the IPEX for the cable; module near the board edge facing the antenna wall. Drop test: room for a glue dot over the U.FL plug and a cable tie point |
| USB stick port | **The Pi's own USB-A port** | No USB host circuitry on the HAT. Place the Pi so its port faces a box wall, or add a short internal USB extension to a panel socket |
| 5 V for the Pi | **5.1 V boost, ≥ 2.5 A out** from 3.0–4.2 V (TPS61088-class + inductor; size for ~2 A input at 3.0 V), into header pins 2 and 4 | Always on. ≥ 100 µF + 100 nF at the header. **TVS + reverse-polarity protection** (header 5 V bypasses the Pi's input protection). Keep it away from the SP4 |
| Battery sense | **MAX17048** fuel gauge on I2C1 (GPIO 2/3) | The Pi has no ADC. Reads cell voltage and state of charge; ALRT to a GPIO |
| Battery | 1 × **protected 18650** Li-ion (≥ 3000 mAh) in a holder with strap/zip-tie slots; footprint for a **second cell in parallel** | ~2 W load: ~4–5 h per cell with the A+. Drop test |
| Charger | **MCP73831-2** (4.2 V), RPROG for ~500 mA, from a **charge-only USB-C** receptacle (CC1/CC2 5.1 kΩ to GND, no data) | Charge LED; TVS on its VBUS. ~6–7 h for 3000 mAh (overnight) |
| Power path | Battery → **slide switch** (panel) → boost (Pi) and radio LDO | No ideal diode needed any more (the fuel gauge reads the cell) |
| Radio supply | **Dedicated 3.3 V LDO** (AP2112K-3.3 or TLV75533, ≥ 300 mA, **dropout ≤ 0.1 V at 150 mA**) from the switched battery rail; **100 µF + 10 µF + 100 nF at the module** | SP4 VCC is 2.0–3.6 V, abs. max 3.6 V (never the 4.2 V battery, **never the Pi's 3V3 pin**). ~120 mA TX peak. PA/LNA modules are supply-noise sensitive: short, wide VCC/GND, keep away from the 5 V boost |
| Low battery | Fuel gauge + firmware thresholds (≥ 3.5 V ok, 3.4–3.5 V warn, < 3.2 V fsync data every burst), re-measured at T0 under the Pi's load | Below ~3.4 V the LDO passes the cell through (≥ 2.95 V at cutoff, SP4 fine to 2.0 V). Leave room for a **buck-boost option** for the radio (TPS63001/TPS63020 + ferrite/10 µF at the module) in case T0 shows > 2 dB less output at 3.0 V |
| UI | Tx/Rx pushbutton, TX/RX role switch, SRI/MRM↔NM mode switch, activity LED (blinks), status LED | Switches/button at the board edge; RC + ESD on button lines |
| Debug | UART console header (GPIO 14/15 + GND), test points | Test points: VBAT, 5V_PI, 3V3_RADIO, GND. No screen or network on the box |

## Proposed Raspberry Pi 3 pin map (BCM numbering; verify against the Pi pinout before using it)

| GPIO | Header pin | Signal | Notes |
|---|---|---|---|
| GPIO 11 | 23 | SCK → radio | SPI0, ≤ 8 MHz (7.8 MHz with `core_freq=250`) |
| GPIO 10 | 19 | MOSI → radio | SPI0 |
| GPIO 9 | 21 | MISO ← radio | SPI0 |
| GPIO 8 | 24 | CSN → radio | SPI0 CE0, driven by the kernel per transfer; pull-up |
| GPIO 22 | 15 | CE → radio | Same as the RF24 examples, so bench tests can use it |
| GPIO 24 | 18 | IRQ ← radio | Active low, pull-up. Wire it: edge timestamps help the hop sync |
| GPIO 2 / 3 | 3 / 5 | I2C1 SDA / SCL → MAX17048 | The Pi has 1.8 kΩ pull-ups on these |
| GPIO 25 | 22 | MAX17048 ALRT | Open drain, pull-up |
| GPIO 17 | 11 | Tx/Rx button | To GND, pull-up, RC + ESD |
| GPIO 27 | 13 | Role switch TX/RX | Atenea Q8 pending: keep it, it can stay unpopulated |
| GPIO 23 | 16 | Mode switch SRI/MRM ↔ NM | |
| GPIO 5 | 29 | Activity LED (blinks in Tx/Rx, rule) | |
| GPIO 6 | 31 | Status LED | Also "safe to pull the stick" |
| GPIO 26 | 37 | MCP73831 STAT | With pull-up |
| GPIO 14 / 15 | 8 / 10 | UART console TX / RX | Debug header |
| 5 V | 2, 4 | From the boost | |
| GND | 6, 9, 14, 20, 25, 30, 34, 39 | | |
| 3V3 | 1, 17 | **not used for the radio** | |

The radio driver (`radio/fw/nrf24.h`) only needs SPI + CSN + CE (+ IRQ) + a microsecond clock, so
moving pins is fine. Record any change in `hw/DESIGN_NOTES.md`.

## Mechanical

- HAT outline **65 × 56 mm** (Pi 3 A+), 2 layers, 1.6 mm, 4 × **M2.5** holes matching the Pi (58 × 49 mm pattern).
  With a Pi 3 B the HAT still fits; the Pi itself is 85 × 56 mm. Before freezing the outline, ask me for the box's
  inside dimensions (I'll measure). Stack height with standoffs is about 30 mm.
- **USB-C (charge), slide switch and Tx/Rx button on one edge**, flush with the board edge, so they
  reach holes in the box wall. The Pi's USB-A port should face a wall too.
- The SP4 sits near the edge facing the antenna wall, away from the Pi's SoC, as high as possible, so the 100 mm
  antenna cable reaches the top of the wall. Keep the battery, the 5 V boost and the Pi's processor away from it.
- Silkscreen: "MTP F26 · Team C · Pi 3 HAT rev A · DRAFT", pin labels, test-point names.
- **Design rules:** the ETSETB lab's capabilities are unknown (plated vias? minimum track?).
  Start conservative: 0.4 mm signal tracks, 0.8–1.0 mm power (1.5 mm or wider on the boost's 2 A input), 0.3 mm
  clearance, few vias of 0.8/0.4 mm, a ground pour on both sides. List the questions for Prof. Chávez / Prof. Jiménez
  in the design notes. Note the alternative: an external 2-layer fab (cheaper per board, but 1–2 weeks).

## How to work

1. **Check the tools first:** KiCad version (`kicad-cli version`), and which KiCad MCP tools exist
   and what they can do (schematic editing, PCB setup, routing?). Tell me plainly what the MCP
   cannot do (e.g. autorouting) before planning around it.
2. **Research before drawing:** the Raspberry Pi 3 A+ mechanical drawing and GPIO pinout, the Pi HAT guidelines
   (back-powering through the 5 V pins), the Ebyte E01-ML01SP4 user manual (pad drawing, pin order, IPEX position,
   layout rules §4.1), and the datasheets for MCP73831, the 5 V boost (TPS61088 or the chosen part) and MAX17048.
   Cite sources in `hw/DESIGN_NOTES.md`.
3. **Checkpoint 1:** show me the block diagram, the final pin map and the power budget (Pi ~0.3–0.6 A at 5 V,
   radio ~120 mA TX / 26 mA RX at 3.3 V, stick 50–100 mA from the Pi's port; cell current up to ~2 A near 3.0 V),
   and wait for my OK.
4. **Schematic** in `hw/teamc-carrier/`, hierarchical sheets: `power`, `pi_header`, `radio`, `ui`.
   Real part numbers in a field (MPN) on every symbol. **ERC with 0 errors**; explain any warning you leave.
5. **Checkpoint 2:** export the schematic (PDF/SVG) and summarise ERC; wait for my OK.
6. **PCB:** outline, holes, placement following the mechanical rules, then routing as far as
   the tools allow (power first, short SPI, ground pour). **DRC with 0 errors.**
   Render top/bottom and a 3D view; show me before exporting fabrication files.
7. **Outputs:** gerbers + drill (zip) only if routed and DRC-clean; `hw/BOM.csv` (ref, qty, value,
   footprint, MPN, supplier, unit price excl. VAT, total), including the Pi 3, the microSD card and the €15
   lab-PCB line, with totals with and without non-purchased parts (BoM rule); `hw/DESIGN_NOTES.md` (decisions,
   pin map, power budget, open questions for ET and the lab).
8. **Git:** edit in a worktree, small commits. Pushing early commits straight to `main` is OK
   (never force-push). Afterwards update `CLAUDE.md` (layout, status, session log), run
   `make -C radio/fw test` and `make -C proto test`, and give me the pull command for my checkout.

## Open questions to keep visible

- Atenea Q22: may the Pi 3's WiFi/BT chip stay on the board, disabled? If not, desolder it (trial on a spare)
  or fall back to a Compute Module 3+ (no chip, but a SODIMM carrier).
- Atenea Q6: may the foil be opened at the USB port during setup? The Pi's USB-A position on the box wall depends on it.
- Atenea Q8: role switch allowed? Keep it on the board; it can stay unfitted.
- ET: agree the Pi 3 model + E01-ML01SP4, the radio LDO, the 5 V boost, the SP4 breakout, the PCB route (lab or
  external fab), the battery choice and the holder.
- Lab: design rules, plated vias, solder mask, turnaround time.
