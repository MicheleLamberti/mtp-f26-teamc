# Carrier rev B (UPC lab, hand-soldered modules) — plan; placed and routed, DRAFT for ET review

Status 23-Oct-26 (evening): **placed and routed on one copper layer** — ERC 0, DRC 0 violations / 0 unconnected /
0 schematic parity (all severities), 10 wire links, gerbers + 1:1 copper PDFs in `hw/teamc-carrier-lab/fab/` and
`teamc-carrier-lab_gerbers.zip`, BoM `hw/BOM_revB.csv` (≈ €139/box). Outline 100 × 80 mm is **provisional** until the
box is measured. How it is built, the wire links and the **schematic changes for one copper layer** (pull-ups, TVS,
3V3 from J1 pin 1, LED return, unused GND pins, no TP2/TP10/C71/R81, FG_ALRT not routed) and the **review fixes of
23-Oct** (J23 charger back on VBAT behind F1/Q1; insulated link wire; SPI at 4 MHz because the ribbon grounds 20/25
cannot reach the pour):
`hw/DESIGN_NOTES.md`, "Carrier rev B". Next: box dimensions → re-run place/route/finish/fab; ET review; email the
zip to Prof. Chávez.

Set-up (23-Oct, afternoon): decisions taken with Santiago (meeting with Prof. Juan A. Chávez), `hw/teamc-carrier-lab/`
(4 sheets, lab rules in the .kicad_pro), built by `python3 hw/scripts/build_carrier_lab.py`; the loop was
`hw/REVB_LOOP_PROMPT.md`.
Rev A (`hw/teamc-carrier/`, JLCPCB-class HAT) stays as it is: external fab is still an allowed option (Chávez slides).

## Why
- The UPC lab mills boards: **no plated holes** (vias = wires soldered both sides, never under a part; a THT pin
  only connects on the side opposite the component), no solder mask, no silkscreen, OSP finish.
- Chávez slides (`0. MTP PCB - 2026.pdf`): track **> 0.3 mm, better > 0.5 mm**; via hole **>= 0.7 mm**. Gerbers by
  email to juan.antonio.chavez@upc.edu, he reports problems, pick-up at office C5-114.
- Jiménez guide (`5. Guidelines for Milling Machines (SPANISH).pdf`, v1.2): clearance >= 0.2 mm, pad >= hole +
  0.7 mm (better + 1.0..1.5), pour clearance <= 0.4 mm, thermal reliefs, no pour between SMD pads (FR10), no
  QFN/DFN, pitch < 1 mm "problematic", 0805/1206 hand-solder pads OK, check plane continuity by hand (FA8).
- Rev A cannot be milled (0.25 mm tracks, 0.2 mm clearance, 146 vias of 0.4 mm, QFN/TDFN/USB-C at 0.5 mm pitch),
  and its boost (TPS61022) and P-FETs (Si2333DDS) are out of stock until Jan-27 / Dec-26 anyway.

## Decisions (Santiago, 23-Oct)
| Item | Choice |
|---|---|
| Fab | UPC lab milling, single-sided where possible (copper on one face, THT parts on the other, SMD on the copper face) |
| Pi link | **2x20 IDC ribbon** to a box header on the carrier (not a HAT: avoids the two-sided soldering problem; board size free within the IKEA 365+ box). Odd pins fan out to one side, even pins to the other. Keep the ribbon <= ~10 cm (5 V on pins 2/4). |
| Radio | **The lab-made SP4 breakout plugs into a 1x8 socket** on the carrier (header order 1 GND, 2 VCC, 3 CE, 4 CSN, 5 SCK, 6 MOSI, 7 MISO, 8 IRQ); M3 standoff at the breakout's H1 |
| Charger | **TP4056 USB-C module with protection** (Botland "HW-373", ~1 EUR): off-board at the box wall, 2-pin JST-XH lead to VBAT/GND. Charge with the box OFF (no power path). No CHG_STAT signal (GPIO 26 freed; software never read it). |

## Proposed parts (research 23-Oct, EU stock that day; re-check before ordering — Botland lots are small)
| Function | Part | Source |
|---|---|---|
| 5 V boost | **Pololu U3V70F5** (#2891): ~2.9 A at 3.0 V in, true shutdown on EN (100 k pull-up to VIN), reverse-protected | Botland 18.90 EUR (39 pcs) |
| Back-power protection | **Pololu ideal diode #5388** (< 3 mOhm). Not a Schottky: 4.8 V - 0.4 V is below the Pi's 4.63 V throttle | Botland 5.90 EUR (25) |
| Fuel gauge | **Adafruit MAX17048 #5580** (same chip/address 0x36: no software change) | Kiwi 6.88 / Botland 8.00 EUR |
| Radio 3.3 V | **AP2112K-3.3TRG1** SOT-23-5, ~0.1 V dropout at 150 mA; **EN from the Pi's 3V3** so the radio is off when the Pi is off | TME 0.25 EUR |
| Power switch | Panel toggle -> 2N7002 inverter -> U3V70F5 EN (closed = ON; a broken lead = OFF; ~40 uA) | — |
| Fuse | Littelfuse 0251005.MRT1L PICO 5 A axial (~15 mOhm), or 0466005.NR(HF) 1206 | TME / LCSC |
| Reverse cell | **DMP2035U-7** SOT-23 (<= 45 mOhm at -2.5 V; AO3401A fallback ~85 mOhm) | LCSC/Farnell/Mouser |
| Keep from rev A | UI network (JST-XH, 1 k / 100 nF), LEDs, 33 Ohm SPI series, CSN pull-up, UART 1x3, JST-VH battery lead, test points TP1/TP3, SMF5.0A TVS, 100 uF bulk at the boost input and at 5V_PI. **Changed in the loop (one copper layer, 23-Oct):** 1206 R/C, SMF5.0A per lead instead of the SP0504, no UI pull-ups, no IRQ pull-up, no TP2/TP10/C71 — see `hw/DESIGN_NOTES.md` | — |
Backups: boost S13V30F5 (Botland 14.50, ~1.8 A at 3.0 V); ideal diode #5382 (Pololu direct); LDO MCP1700 (TO-92).
Rejected: PowerBoost 1000C / MT3608 / U3V16F5 (2 A switch, <= 1 A at 3 V), IP5306 (light-load cut-off), XL6009.
Estimated box cost ~125-130 EUR (rev A 102); confirm in a new BoM. Cell: check the 18650 PCM trips above ~3 A.
Rev A BoM substitutions if rev A is ever fabbed: 22 uF -> CL31A226KAHNNNE; Si2333DDS -> DMP2035U-7.

## Rules for the design loop
- Tracks 0.5 mm (0.3 only on short necks), power 1.0-1.5 mm, 3V3_RADIO 0.8 mm; clearance 0.3 mm (floor 0.2).
- THT pads = hole + 1.0 mm (library copies like `build_breakout.header_fp`); wire vias 2.0 / 1.0 mm, outside part
  bodies, as few as possible; prefer 0 Ohm 1206 or wire links for crossings.
- GND pour on the copper face, clearance 0.4 mm, thermal reliefs, rule areas between SMD pads; star ground at the
  battery/boost, radio return away from the boost loop.
- Generated like rev A: `hw/teamc-carrier-lab/sheets/*.py` -> schgen -> netlist2pcb -> place/route scripts
  (`gridroute.Router` is two-layer; restrict it to the copper layer) -> DRC 0 -> 1:1 copper PDFs + gerbers (as
  `build_breakout.fab`).
- Module footprints from the makers' drawings only (Pololu dimension diagrams, Adafruit board files).

## Module data (done 23-Oct)
Pads in `hw/teamc-carrier-lab/sheets/modules.py` from the makers' CAD (Pololu reg21a / rvp01b drill DXFs, Adafruit
Adafruit-MAX17048-STEMMA.brd). Findings: the #5388 ideal diode (LM74700) needs ~3.9 V to start, so it only goes on
the 5 V side; the MAX17048 board runs from the cell (SJ2 bridged as shipped) and its header VIN only feeds the I2C
pull-ups and LED → VIN = 3V3_PI, cell sense through its JP2 Bat/GND holes. Backup boost S13V30F5 idles at 10–20 mA
(poor standby). TP4056 pad positions vary by seller: measure on arrival, it is wired off-board anyway.

## Still open
- Box inside dimensions (IKEA 365+), where the cell, panel switches, USB-C charger and antenna sit: the outline,
  the M3 holes and the lead edges follow from them (re-run `place_carrier_lab.py` → `route_carrier_lab.py` →
  `finish_carrier_lab.py` → `fab_carrier_lab.py`).
