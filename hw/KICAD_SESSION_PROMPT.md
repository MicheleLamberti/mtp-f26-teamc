# Prompt for the KiCad board-design session

Rewritten 19-Oct-26 for a lead agent with subagents (v2; v1 18-Oct was a single-agent brief, in git history).
Start a new Claude Code session in `~/dev/mtp-f26` (Opus) and paste everything below the line.

---

You are the **lead** for Team C's KiCad session (MTP F26, UPC). You plan, delegate to subagents, integrate their work
and talk to me (Santiago, radio team). **I'm asking you to use subagents** (Agent tool, general-purpose, Opus) for the
research and drafting described below; keep it to about 8 subagents in total and run independent ones in parallel.
You own every file in the KiCad project: subagents either return data to you or write only the files you assign them.

The goal of this session: **(1) the SP4 breakout board, ready to make in the lab** (the radio modules arrive in 1–3
weeks and the bench tests need it on day one), and **(2) the Pi 3 HAT carrier: verified parts list with symbols and
footprints, schematic with ERC clean, board outline and a placement**, as a **draft for the electronics team (ET)**.
Label everything "DRAFT – for ET review": ET (Carlos, Michele, Bikash, Guillem) owns the board.

## 0. Read first (you, before any subagent)

- `CLAUDE.md` (team, calendar, decisions, git rules, working rules), then `radio/HANDOFF_ET.md` (radio interface,
  power), `radio/DECISIONS.md` (D-H1 Pi 3, D-R2c module, D-R5c antenna), `radio/hw_proposal.html` (hardware page v0.5.1:
  block diagram, pin map, BoM), `radio/pi3_impact.html` (power tree, runtime, mechanics), `radio/TEST_PLAN.md` T0
  (what the breakout must allow), `proto/port/linux/README.md` and `proto/port/linux/ui.c` (the GPIOs the software uses).
- The competition rules PDF and the Ebyte manual are under **`~/dev/mtp-f26/docs/`** in my main checkout. `docs/` is
  git-ignored, so **it is not in a worktree**: read it from that absolute path. Sections: "Mechanical Features" and
  "Telecom and Electronics Hardware". The SP4 user manual is also online: https://voltiq.ru/datasheets/ebyte/E01-ML01SP4.pdf
- Ordered on 19-Oct (Santiago): **2 × Raspberry Pi 3 Model A+**, **4 × Ebyte E01-ML01SP4** (2 with the Ebyte
  TX2400-FPC-2509 flex antenna, 2 with the TX2400-JKS-IPX20 rod + IPEX-to-SMA cable), **SanDisk Ultra 32 GB A1**
  microSD cards. Those parts are fixed.

## 1. Tools (checked 19-Oct; re-check at the start)

- KiCad **10.0** (`kicad-cli version`), standard libraries in `/usr/share/kicad/{symbols,footprints}`, templates
  `RaspberryPi-HAT` and `RaspberryPi-uHAT` in `/usr/share/kicad/template`. KiCad's Python API imports
  (`python3 -c "import pcbnew"` → 10.0.6).
- KiCad MCP (`mcp__kicad__*`, deferred: load the schemas with ToolSearch first). What it does:
  - **Project:** `create_kicad_project` (`template="RaspberryPi-HAT"` gives the HAT outline, header and holes).
  - **Parts:** `search_parts_registry` → `get_registry_part` (datasheet, dimension provenance, field reports) →
    `download_registry_part` (symbol, footprint, STEP into a project folder).
  - **Schematic:** `add_component_from_library` (symbol + footprint + position), `add_wire`, `add_label`,
    `add_global_label`, `add_hierarchical_label`. Reading: `get_schematic_info`, `list_schematic_components`,
    `get_symbol_details`, netlist tools, `validate_pin_configuration`, `detect_pin_conflicts`, `extract_*`.
  - **Checks:** `run_erc` / `get_erc_violations`; `run_drc` / `get_drc_violations`.
  - **PCB:** only `setup_pcb_layout` (outline), analysis (`list_pcb_footprints`, `analyze_pcb_nets`,
    `analyze_pcb_power_integrity`, `find_tracks_by_net`) and output (`render_pcb`, `export_gerber`, `export_pcb_3d`,
    `export_schematic_svg`).
- **The MCP cannot place footprints, route, pour zones or edit footprints.** For those use `pcbnew` Python scripts
  run with Bash (load the board, update from the netlist, set footprint positions, add tracks/zones, save), or
  `kicad-cli`. No autorouter is installed: route power and the SPI lines by script where it is simple, and leave the
  rest to ET in the KiCad GUI with a written placement/routing plan. Tell me plainly what you could not do.
- Write every script into the job scratch dir, not into the repo, unless it is a reusable generator worth keeping
  (then `hw/scripts/`).

## 2. Hard constraints (competition rules)

- **One and only one module with a microprocessor** (the Pi 3). No other part may contain a CPU: no micro + radio
  combo boards, no fuel gauge or charger with its own MCU.
- **No chip implementing WiFi, Bluetooth, ZigBee, 2G–5G.** The Pi 3's CYW43455 is disabled in software or desoldered
  (working assumption, **Atenea Q22** pending). Nothing on our boards may add a wireless chip.
- Fits **inside an IKEA 365+ box, 15 × 15 × 7 cm** (outside). Only connectors, switches and buttons may stick out.
  Runs **autonomously** on battery; no cables plugged in during a round.
- **At least one Tx/Rx switch or button** and a **pilot light that blinks in Tx/Rx**. Extra switches are allowed
  (mode switch), but **no switch may indicate the position in the network**.
- **Drop test** from table height to concrete before MRM: nothing loose (HAT on standoffs or soldered, microSD taped,
  battery strapped, glue dot on the U.FL plug).
- ESD protection on every connector and button people touch. Cost **≤ €150 per device**. A board made at the ETSETB
  lab counts **€15** in the BoM; every part (screws, wire, foam, the Pi, the microSD) must be in the BoM.
- **Modules shown at Quick Mode (Fri 6-Nov) are final**: Pi 3 A+ and E01-ML01SP4.

## 3. Parts baseline (ET may challenge; the subagents verify and complete it)

| Block | Part | Notes |
|---|---|---|
| Micro | **Raspberry Pi 3 Model A+** (ordered) | HAT on the 40-pin header (2 × 20, 2.54 mm). A+ 65 × 56 mm, M2.5 holes on 58 × 49 mm |
| Radio | **Ebyte E01-ML01SP4** (nRF24L01P + PA/LNA, SMD 14.85 × 18 mm per our docs, 14.5 × 18 per the store; IPEX on the module) | 10 pads at **1.27 mm**: 1 VCC, 2 CE, 3 CSN, 4 SCK, 5 MOSI, 6 MISO, 7 IRQ, 8–10 GND (manual §3). **Custom footprint from the manual's pad drawing.** No top-layer traces under it, ground pour under it, at the board edge away from the SoC and the boost |
| Antenna | **Ebyte TX2400-FPC-2509** flex (25 × 9 mm, 100 mm cable, IPEX), Molex 146153-0100 (34.9 × 9 mm) as fallback | No RF on our PCB. Clearance around the IPEX for the cable; module edge facing the antenna wall |
| USB stick | The Pi's own USB-A port | No USB host circuitry on the HAT |
| 5 V for the Pi | **5.1 V boost ≥ 2.5 A out** from 3.0–4.2 V (TPS61088-class; ~2 A input at 3.0 V) into header pins 2/4 | Always on. ≥ 100 µF + 100 nF at the header. **TVS + reverse-polarity protection** (header 5 V bypasses the Pi's input protection). Away from the SP4 |
| Battery sense | **MAX17048** on I2C1 (GPIO 2/3), ALRT → GPIO 25 | The Pi has no ADC |
| Battery | 1 × **protected 18650** (≥ 3000 mAh), holder with strap slots; footprint for a **second cell in parallel** | ~2 W load: 4–5 h per cell |
| Charger | **MCP73831-2** (4.2 V), ~500 mA, from a **charge-only USB-C** receptacle (CC1/CC2 5.1 kΩ to GND) | Charge LED; TVS on VBUS; STAT → GPIO 26 |
| Power path | Battery → **panel slide switch** → boost (Pi) and radio LDO | |
| Radio supply | **3.3 V LDO ≥ 300 mA, dropout ≤ 0.1 V at 150 mA** (AP2112K-3.3 / TLV75533) from the switched cell; **100 µF + 10 µF + 100 nF at the module** | SP4 abs. max 3.6 V; **never the cell, never the Pi's 3V3**. Footprint option for a **buck-boost** (TPS63001/TPS63020) if T0 shows > 2 dB less output at 3.0 V |
| UI | Tx/Rx button (GPIO 17), role switch TX/RX (GPIO 27, may stay unfitted, Atenea Q8), **3-position mode switch** on-off-on (GPIO 23 = NM, GPIO 16 = MRM, neither = SRI), activity LED GPIO 5 (blinks), status LED GPIO 6 | RC + ESD on button/switch lines; switches at the board edge |
| Debug | UART header (GPIO 14/15 + GND), test points VBAT, 5V_PI, 3V3_RADIO, GND | |

Pin map (BCM): SCK 11 (pin 23), MOSI 10 (19), MISO 9 (21), CSN = CE0 8 (24, pull-up), CE 22 (15), IRQ 24 (18,
pull-up), SDA/SCL 2/3 (3/5), ALRT 25 (22), button 17 (11), role 27 (13), mode NM 23 (16), mode MRM 16 (36), LEDs
5/6 (29/31), charger STAT 26 (37), UART 14/15 (8/10), 5 V on 2/4, GND 6/9/14/20/25/30/34/39, 3V3 (1/17) unused for the
radio. It must match `proto/port/linux/ui.c` and `radio/fw/linux/README.md`; if you change a pin, change the
software docs with it and record it in `hw/DESIGN_NOTES.md`.

## 4. Plan and subagents

### Phase A: research (parallel, read-only for the project; each returns a table, writes nothing in `hw/`)

Give every research subagent: the relevant rows of §3, the rules in §2, and this **output schema per part**:
`function | MPN | manufacturer | package | KiCad symbol (lib:name, checked to exist) | KiCad footprint (lib:name, checked
to exist) or registry part id | datasheet URL | key values (from the datasheet's reference circuit) | EU stock + price
(DigiKey/Mouser/LCSC, date) | 3D model available? | notes/risks`. Footprint names must be verified against
`/usr/share/kicad/footprints/<lib>.pretty/` or a registry record (`get_registry_part`); never guess a name.

1. **Power chain:** boost (TPS61088 or a better-stocked equivalent that delivers 5.1 V / 2.5 A from 3.0 V, with its
   inductor, sense resistors, compensation), reverse-polarity P-FET + TVS on the 5 V rail, MCP73831-2 + RPROG + LED,
   USB-C charge-only receptacle (hand-solderable, mid-mount or through-hole shell), VBUS TVS, panel slide switch
   (rated ≥ 3 A), 18650 holder(s) (e.g. Keystone 1042/1043) with polarity, radio LDO, buck-boost option. Include the
   **power budget**: Pi ~0.3–0.6 A at 5 V, radio 120 mA TX / 26 mA RX at 3.3 V, stick 50–100 mA from the Pi's port;
   cell current up to ~2 A near 3.0 V; track widths for that.
2. **Pi + radio + mechanics:** Pi 3 A+ mechanical drawing (header position, holes, USB-A and microSD positions),
   what the `RaspberryPi-HAT` template contains (outline, header, holes; does it match the A+?), the 2 × 20 female
   header (height for the stack and the standoffs), M2.5 standoffs/screws, the HAT spec's back-powering advice (5 V
   via the header: ideal diode or not), ID EEPROM (optional; say whether we skip it). **SP4 footprint data** from the
   Ebyte manual: pad size, pitch, pad-to-edge distances, outline, keep-out, IPEX position, layout rules (§4). Cross-check
   with the store page (14.5 × 18 mm vs 14.85 × 18 mm) and with any KiCad/SnapEDA footprint for E01-ML01SP4 (SnapEDA
   lists one); state which numbers you trust and why.
3. **UI + sensing + protection:** MAX17048 (package and its footprint, I2C pull-ups vs the Pi's 1.8 kΩ), tactile
   button (panel-reachable), 3-position on-off-on switch and 2-position role switch (panel mount or right angle at
   the edge), LEDs + resistors for 3.3 V GPIO, ESD arrays for button/switch/USB-C lines, UART header, test points.

You (the lead), while they run: create the worktree (`EnterWorktree`), read the rules, decide the **net names** (one
table: `VBAT`, `VBAT_SW`, `5V_PI`, `3V3_RADIO`, `VBUS_USB`, `GND`, `SPI_SCK`, `SPI_MOSI`, `SPI_MISO`, `RADIO_CSN`,
`RADIO_CE`, `RADIO_IRQ`, `I2C_SDA`, `I2C_SCL`, `FG_ALRT`, `BTN_TXRX`, `SW_ROLE`, `SW_MODE_NM`, `SW_MODE_MRM`,
`LED_ACT`, `LED_STATUS`, `CHG_STAT`, `UART_TX`, `UART_RX`) and the sheet split.

**Checkpoint 1 (stop and ask me):** block diagram, final pin map, power budget, the merged parts table (with prices
and the cheapest EU source), the open choices with your recommendation. Wait for my OK before drawing.

### Phase B: libraries and the breakout (first deliverable)

4. **Footprint/symbol subagent:** builds the project library `hw/lib/teamc.kicad_sym` + `hw/lib/teamc.pretty/`:
   the **E01-ML01SP4 symbol and footprint** (from the Phase A data; write the `.kicad_mod` with pcbnew Python or as
   text, then check it: pad count, pitch 1.27 mm, pad 1 marker, courtyard, keep-out; render it), plus any part the
   standard libraries lack (download registry parts into `hw/lib/` with `download_registry_part`). It reports each
   footprint's checks.
5. **Breakout (you):** a tiny board `hw/sp4-breakout/`: SP4 footprint → 2 × 5 (or 1 × 8) 2.54 mm header in the
   nRF24 "standard" order where possible (GND, VCC, CE, CSN, SCK, MOSI, MISO, IRQ), 10 µF + 100 nF at VCC, a 100 µF
   footprint, a GND test point, the IPEX at the board edge, mounting hole. Single-sided if the lab prefers; ERC + DRC
   clean; gerbers + drill + a 1:1 PDF of the copper for the lab. This one you place and route completely with
   pcbnew Python (it is small). Show me the render.

### Phase C: carrier schematic (one owner per sheet, in parallel)

Create `hw/teamc-carrier/` from the `RaspberryPi-HAT` template (`create_kicad_project`). Hierarchical sheets
`power`, `pi_header`, `radio`, `ui`; nets between sheets by the **global labels** from your net table. Each sheet's
subagent writes **only its own `.kicad_sch`** and gets: its parts table rows (symbol, footprint, MPN, values), the
net table, the rule "set Value, Footprint, MPN, Manufacturer, Datasheet on every symbol", and "run `run_erc` on your
sheet and return the remaining violations with an explanation". Subagents: 6 = `power`, 7 = `radio` + `pi_header` +
`ui` (smaller sheets; or split if it gets long). You assemble the root sheet, run **ERC to 0 errors**, and explain any
warning you keep.

**Checkpoint 2:** schematic PDF/SVG (`export_schematic_svg` or `kicad-cli sch export pdf`), ERC summary, BoM draft.
Wait for my OK.

### Phase D: board, review, outputs

- Board outline from the template (65 × 56 mm, A+ holes). Before freezing it, ask me for the box's inside
  dimensions (I'll measure). **Placement with pcbnew Python**: USB-C, slide switch, button and mode switch on one edge
  (holes in the box wall); SP4 at the opposite edge facing the antenna wall, away from the SoC, the boost and the
  battery; boost close to the header 5 V pins; LDO next to the SP4. Route power and SPI by script if you can; pour GND
  on both sides. Conservative rules (lab unknown): 0.4 mm signals, 0.8–1.0 mm power, ≥ 1.5 mm on the boost's 2 A
  input, 0.3 mm clearance, vias 0.8/0.4 mm. **DRC 0 errors** for what is routed; list what is left for ET.
- 8. **Reviewer subagent (independent, adversarial):** checks the schematic against the datasheets: pin numbers
  (SP4, MAX17048, MCP73831, boost, LDO, USB-C CC), values against the reference circuits, power ratings, the pin map
  against `ui.c`, the rules in §2 (one CPU, no wireless chip, ESD, drop test). It returns findings with severity and
  the datasheet page; you fix or justify each one.
- Renders (`render_pcb` top/bottom/isometric). **Checkpoint 3:** show me before any fabrication export.
- Outputs: gerbers + drill (zip) only for DRC-clean boards; `hw/BOM.csv` (ref, qty, value, footprint, MPN, supplier,
  unit price excl. VAT, total), including the Pi 3 A+, the microSD, standoffs, the battery and holder, wire, the €15
  lab-PCB line, totals with and without non-purchased parts (BoM rule); `hw/DESIGN_NOTES.md` (decisions, pin map, net
  table, power budget, sources, what the MCP/scripts could not do, open questions for ET and the lab).

## 5. Working rules

- **Git:** work in a worktree (`EnterWorktree`), small commits, push the branch tip straight to `main` with
  `git push origin HEAD:main` after checking it is a fast-forward (never force-push); one branch only (`main`).
  `docs/` stays out of git (copyrighted).
- Before ending: update `CLAUDE.md` (Layout: `hw/` contents; Status; Session log), run `make -C radio/fw test`,
  `make -C proto test` and `python3 radio/phy_config.py` (all must pass), and give me the pull command for my checkout.
- Treat everything as a proposal unless `CLAUDE.md` says it is decided. Don't write to the team Drive folder.
- Report honestly: which footprints you verified against a datasheet drawing and which come from a library or the
  registry unverified; what you could not route.

## 6. Open questions to keep visible

- Atenea Q22: may the Pi 3's WiFi/BT chip stay on the board, disabled? If not: desolder it (trial on a spare Pi) or
  fall back to a Compute Module 3+ (no chip; SODIMM carrier).
- Atenea Q6 (foil opened at the USB port during setup?) decides where the Pi's USB-A port faces.
- Atenea Q8: role switch allowed? Keep the footprint; it can stay unfitted.
- ET: agree the boost, the LDO, the battery and holder, lab vs external fab (JLCPCB-class 2-layer is ~€1/board + 1–2
  weeks).
- Lab (Prof. Chávez / Prof. Jiménez): minimum track/clearance, plated vias, solder mask, turnaround.
