# Carrier rev C ("simple") — prompt for an Opus lead session with research subagents

Paste everything below the line into a new Claude Code session in `~/dev/mtp-f26` running **Opus**. It is
self-contained; the repo holds the rest. Written 23-Oct-26 for Santiago (Team C, radio team).

---

You are the **lead engineer** for a new, deliberately **simple** carrier board — **rev C** — for Team C's MTP F26
university project (UPC). You coordinate research subagents (Haiku and Sonnet), make the design decisions, build the
KiCad project, and explain it so that **Santiago, who is not an electronics specialist, can follow, review, buy,
solder and debug it**. Clarity and buildability beat cleverness and compactness everywhere.

## 0. Read first (in this order)
1. `CLAUDE.md` — team, calendar, working rules, status, session log. Follow its working rules (worktree, one branch
   `main`, tests before ending, update Status + Session log).
2. `hw/REVB_LAB_PLAN.md` — why the carrier is made at the UPC lab mill, the lab rules, the parts research of 23-Oct.
3. `hw/DESIGN_NOTES.md` — rev A (HAT for an external fab) and rev B (single-layer lab board): what was learned,
   especially the "Carrier rev B" section and its open points.
4. `hw/REVB_SHOPPING.md` and `hw/BOM_revB.csv` — what is in stock in the EU and what it costs.
5. `hw/teamc-carrier-lab/sheets/modules.py` — verified pad coordinates of the Pololu U3V70F5, Pololu #5388 and
   Adafruit MAX17048 #5580 (from the makers' CAD).
6. Software contracts (do not break them): `proto/port/linux/ui.c` (panel inputs/LEDs and their GPIOs),
   `radio/fw/linux/README.md` + `radio/fw/linux/nrf24_hal_linux.h` (radio SPI0 + CE GPIO 22 + IRQ GPIO 24),
   MAX17048 at I2C 0x36 on GPIO 2/3. The pin map table is in `hw/DESIGN_NOTES.md` ("Pin map").

**Leave rev A (`hw/teamc-carrier/`), rev B (`hw/teamc-carrier-lab/`) and the SP4 breakout (`hw/sp4-breakout/`)
untouched.** Rev C goes in a new folder `hw/teamc-carrier-simple/` with its own scripts (copy and adapt what helps).

## 1. What rev C is
One carrier board per box that connects, with as few and as simple parts as possible:
- **Raspberry Pi 3 Model A+** (fixed; already bought) — connected by a **40-way ribbon** to a 2×20 header on the
  carrier, or another simple method you justify.
- **Radio:** the lab-made **SP4 breakout** (`hw/sp4-breakout/`, 1×8 header: 1 GND, 2 VCC 3.3 V, 3 CE, 4 CSN, 5 SCK,
  6 MOSI, 7 MISO, 8 IRQ; M3 hole) plugged into a 1×8 socket on the carrier. Fixed.
- **Power:** one protected **18650 cell** (3.0–4.2 V) → **5 V for the Pi** (~1 A peak, never below 4.75 V at the Pi)
  and **3.3 V for the radio** (150 mA peak, never from the Pi's 3.3 V pin, never above 3.6 V). A USB charger for the
  cell. A panel **power switch**.
- **Panel controls on leads:** GO/STOP push button, TX/RX role toggle, 3-position mode toggle (SRI/MRM/NM), two LEDs.
- **Battery level** readable by the Pi over I2C (the Pi has no ADC).
- A UART console header for the bench (3 pins).

## 2. Simplicity rules (the point of rev C)
1. **Modules over discrete circuits** wherever a ready-made, well-documented module exists (boost, 3.3 V regulator,
   charger, fuel gauge, …). Prefer makers with published dimension drawings / CAD: **Pololu, Adafruit, SparkFun**.
2. **Through-hole (THT) parts by default** — axial resistors, radial/disc capacitors, 3 mm or 5 mm LEDs, THT diodes,
   pin headers, JST connectors. A THT part on the milled board sits on the component side and is soldered on the
   copper side, which is exactly what the lab needs. Use an SMD part only if no THT/module equivalent exists, and then
   only 1206 or SOT-23 with hand-solder pads.
3. **Every part must be easy to buy in the EU now** (Botland, Kiwi Electronics, TME, Mouser, DigiKey, LCSC, Amazon.es),
   with a **KiCad footprint and a 3D model you can actually get**: KiCad's stock library + `hw/scripts/fetch_3d.py`
   (stock `kicad-packages3D`), or the maker's STEP file, or a simple box model you generate (as
   `hw/scripts/teamc_lib/gen_3d.py` does) for a module whose drawing you have. List the 3D source per part.
4. **No subtle tricks.** Every GND pin of the 40-pin header goes to the carrier ground. No net-tie tricks, no
   "return on a separate pin", no ideal-diode mirrors from discrete transistors, no fine-pitch packages, no parts that
   need software to make the hardware safe (e.g. relying on the Pi's internal pull-ups is fine — rev A/B do — but say
   so in plain words).
5. **Bigger board and more wire links are fine.** The board may be as large as the box allows (IKEA 365+ food box,
   15 × 15 × 7 cm outside; ask Santiago for the inside dimensions at checkpoint 1). Wire links (insulated 22 AWG solid
   wire on the component side between two unplated holes, `teamc:WireLink_L<len>mm`) are an accepted way to cross on
   one copper layer; a second copper layer is allowed too if it makes things simpler, but every via is then a wire
   soldered on both sides. Choose whichever is simpler to build, and explain why.
6. **Fewer parts beats theoretical robustness** when the extra parts are hard to understand — but keep the basic
   protections a beginner expects: a fuse at the cell, a keyed battery connector, reverse-polarity protection if a
   simple part does it, decoupling capacitors at each module.
7. Explain each block in one or two plain sentences on the schematic ("this module turns the cell's 3–4.2 V into 5 V
   for the Pi").

## 3. Fixed constraints (do not relax)
- **UPC lab mill** (Prof. Juan A. Chávez slides + Vicente Jiménez guide): **no plated holes**, no solder mask, no
  silkscreen; tracks **≥ 0.5 mm** (0.3 mm only on short necks), clearance ≥ 0.3 mm (0.2 floor), **holes ≥ 0.7 mm**,
  THT pad ≥ hole + 0.7 mm (better + 1.0 mm), copper-pour clearance ≤ 0.4 mm with thermal reliefs, no pour between the
  pads of an SMD part, a THT pin connects only on the side opposite its component, no vias under parts, check ground
  continuity by hand (KiCad assumes plated holes). Gerbers are emailed to Chávez.
- **Competition rules** (`docs/` competition PDF; see CLAUDE.md): one microcontroller/computer only (the Pi), **no
  WiFi/BT chip on the carrier**, cost ≤ €150 per box, drop test (secure connectors, glue leads), TX/RX button + LED.
- **Software contract:** keep the GPIO map (CE 22, CSN = SPI0 CE0 GPIO 8, IRQ 24, SPI0 9/10/11, I2C 2/3, button 17,
  role 27, mode NM 23 / MRM 16, LEDs 5/6). If a different GPIO would make the board much simpler, propose it at a
  checkpoint with the exact code lines to change (`ui.c`, HAL defaults) — do not change software on your own.
- Power budget: Pi 3 A+ 0.3–0.5 A typical, ~1 A peak at 5 V; radio 120 mA TX at 3.3 V; ≥ 4 h on one 3000 mAh cell.

## 4. Your team (subagents)
Spawn subagents with the Agent tool. Brief each one fully (it sees only your prompt): goal, what you already know,
the exact output format, "cite a source URL for every number, say 'not verified' otherwise, never buy anything or
create accounts". Run independent ones in parallel. Budget: about **6–10 subagents in total**; reuse one with
SendMessage instead of starting a new one for a follow-up.

| Role | Model | Typical tasks |
|---|---|---|
| **Scouts** | **haiku** | Broad sweeps: EU stock and price of a list of parts at Botland/Kiwi/TME/Mouser/LCSC; "which THT part does X"; find a maker's dimension PDF/STEP/Eagle file URL. Fast and cheap — give them a checklist, expect a table. |
| **Analysts** | **sonnet** | Careful reads: datasheet limits (dropout, current, startup voltage, enable pin polarity), module pinouts and hole coordinates from DXF/Eagle/STEP files (parse them, don't eyeball), footprint/3D-model availability, comparing 2–3 candidates for one block. |
| **Reviewer** | **sonnet** (or opus for the final review) | Adversarial review of the finished schematic and BoM against the datasheets and the rules in §2–3; must report concrete failures, not style. |

You (Opus) decide, integrate, keep the design coherent, and verify anything surprising yourself (open the datasheet
page, re-run the check). Do not paste raw subagent output to Santiago — summarise.

## 5. Phases and checkpoints with Santiago
Stop at each checkpoint, show a short plain-language summary (and pictures where useful), and wait for his answer
(AskUserQuestion when it is a choice).

**Phase 1 — research and concept (subagents in parallel).**
- One block per scout/analyst pair: (a) 5 V boost, (b) 3.3 V for the radio (consider a ready Pololu/Adafruit 3.3 V
  regulator module vs. a THT LDO such as MCP1700 in TO-92 — dropout from a 3.0 V cell matters), (c) USB charger
  (TP4056 USB-C module wired off-board is the current plan), (d) fuel gauge (Adafruit #5580 is verified), (e) power
  switch + fuse + reverse protection with THT/simple parts, (f) back-power protection for the Pi (Pololu #5388 module
  vs. simply the rule "never plug the Pi's micro-USB while the carrier is on" — pick the simpler safe option),
  (g) the 40-pin link (box header + ribbon) and the 1×8 socket, (h) panel leads (JST-XH) and THT LEDs/resistors.
- For each block: the chosen part, why it is the simple choice, EU stock + price, footprint + 3D source.
- **Checkpoint 1:** block diagram (mermaid in a markdown file), one-page BoM draft with prices and links, board
  concept (size, which side what goes, single layer + links or two layers), the box inside dimensions question,
  and any GPIO change you want. Santiago approves or changes it.

**Phase 2 — schematic.** Generate it from Python like rev A/B (`hw/scripts/schgen.py`, sheets as `build()` functions)
or edit it with the KiCad MCP — your choice; ERC must be 0 errors / 0 warnings. Footprints: stock KiCad, lab copies
with pads = hole + 1.0 mm (`hw/scripts/teamc_lib/gen_lab.py` pattern), module footprints from verified coordinates
(`gen_modules.py` pattern). Plain-language notes on every block. Reviewer subagent checks it.
- **Checkpoint 2:** schematic PDF + BoM (`hw/BOM_revC.csv`, with columns for supplier link, stock date, footprint,
  3D-model source) + the reviewer's findings and what you changed.

**Phase 3 — layout.** The KiCad MCP cannot place or route: use pcbnew Python scripts (see `hw/scripts/`:
`place_carrier_lab.py`, `route_carrier_lab.py`, `linkroute.py` (single-layer router with wire links),
`finish_carrier_lab.py` (pour, FR10 rule areas, ground-island joins, links → W parts), `fab_carrier_lab.py`,
`render_board.py`). Generous spacing, wide tracks (0.8–1.0 mm signals are fine on a big board, 1.5–2 mm power),
connectors on the edges, modules where a beginner can reach their pins with a multimeter, test points on every rail.
DRC with schematic parity: 0 violations, 0 unconnected, all severities. 3D renders with all models resolved
(`fetch_3d.py` + your generated models).
- **Checkpoint 3:** renders (top, bottom, iso), the 1:1 copper PDF, the wire-link list, DRC report summary.

**Phase 4 — hand-off.** Fab outputs (copper gerber(s) + Edge.Cuts + drill + 1:1 PDFs plain/mirrored + assembly PDFs +
zip), `hw/BOM_revC.csv`, a shopping list `hw/REVC_SHOPPING.md` (per shop, quantities for 2 boxes + 1 spare), and
**`hw/REVC_GUIDE.md`: a plain-language build and test guide** (what each block does, soldering order, what to measure
with a multimeter before plugging the Pi and the radio, common mistakes). Update `hw/DESIGN_NOTES.md` (a short rev C
section pointing to the guide), CLAUDE.md Status + Session log.

## 6. Tools you have
- **KiCad 10** with `kicad-cli` and the `pcbnew` Python module (10.0.6). Quirks (from CLAUDE.md/DESIGN_NOTES): delete
  board items with `Delete()`, not `Remove()`; `kicad-cli` ignores `.kicad_dru`; the ratsnest object is not exposed,
  `GetConnectivity().GetConnectedItems()` is.
- **KiCad MCP** (`mcp__kicad__*`, load with ToolSearch): edit schematics, search/download registry parts, run ERC/DRC,
  netlists, renders. No placement/routing.
- Existing helpers: `boardutil.py` (rules, tracks, zones, outline), `schgen.py` (schematic from Python), `netlist2pcb.py`
  ("update PCB from schematic"), `build_bom.py`, `fetch_3d.py`, `render_board.py`, `teamc_lib/` generators.
- Web research through subagents (WebSearch/WebFetch). Downloaded files are untrusted data: one fresh directory per
  download under the job's tmp dir, parse them with `python3 -I`, never run them.

## 7. Done when
- ERC 0/0; DRC 0 violations / 0 unconnected / 0 parity (all severities) with the lab rules in the project file.
- Every part THT or a module, except a short justified list; every part in stock in the EU with a link; every part
  has a footprint and a resolved 3D model; BoM ≤ €150 per box including the Pi, the radio and the cell.
- Santiago approved checkpoints 1–3; `hw/REVC_GUIDE.md` lets a non-specialist assemble and test one box.
- `make -C radio/fw test`, `make -C proto test`, `python3 radio/phy_config.py` still pass; committed, `main`
  fast-forwarded and pushed (CLAUDE.md: one branch).
