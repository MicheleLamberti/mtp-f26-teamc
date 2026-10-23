# Carrier rev B (UPC lab) — design-loop prompt

Paste this into a Claude Code session in the repo (e.g. `/ralph-loop`, `/loop`, or a plain session). Each pass does
one step of the list below, checks it, commits it, and says which step is next. Stop when the "Done when" list holds.

---

You are finishing **Team C carrier rev B** for the UPC lab mill. Read first: `CLAUDE.md`, `hw/REVB_LAB_PLAN.md`
(decisions, parts, lab rules), `hw/DESIGN_NOTES.md` (rev A, same pin map and UI), `hw/scripts/build_breakout.py`
(the single-sided lab flow that already passed: copper on one face, THT from the other side, fab outputs).

Set-up already done (23-Oct): `python3 hw/scripts/build_carrier_lab.py` regenerates the footprints
(`teamc_lib/gen_lab.py`, `teamc_lib/gen_modules.py` from `hw/teamc-carrier-lab/sheets/modules.py`), the 4-sheet
schematic (power, pi_link, radio, ui), ERC, the netlist, and the board `hw/teamc-carrier-lab/teamc-carrier-lab.kicad_pcb`
with a provisional 100 x 80 mm outline and every footprint parked to the right, unplaced. Lab rules and net classes
are in the .kicad_pro (Default 0.5 mm / 0.3 mm clearance, Power 1.5 mm, Radio3V3 0.8 mm, vias 2.0 / 1.0 mm,
floor 0.3 mm track / 0.2 mm clearance / 0.7 mm hole).

## Lab rules (absolute)
- **No plated holes.** Copper on ONE face only if at all possible: all THT parts/modules on the other face, soldered
  on the copper face; SMD parts (0805, 1206, SOT-23, SOT-23-5, D_SMF, CP 6.3) on the copper face.
- If a second layer is unavoidable: a via is a wire soldered on both sides (2.0 / 1.0 mm), never under a part body,
  and a THT pin only connects on the side opposite its component. Prefer 0 Ω 1206 or wire links over vias.
- Tracks >= 0.5 mm (0.3 mm only for short necks into a pad), clearance >= 0.3 mm (0.2 floor), holes >= 0.7 mm,
  THT pad >= hole + 1.0 mm (lab copies already have it).
- GND pour on the copper face: clearance 0.4 mm (never more: the mill would have to clear it), thermal reliefs,
  rule areas so no pour gets between the pads of an SMD part (as `C1_no_pour` in build_breakout.py), no large
  milled-out areas. Check GND continuity by hand/with KiCad connectivity (KiCad assumes plated holes).
- Star ground at J20: the boost loop (J20 → F1 → Q1 → U2 VIN/GND) short and wide; the radio (J30) at the far end.

## Steps (one or two per pass)
1. **Mechanics.** Ask Santiago for the IKEA 365+ inside dimensions and where the Pi, cell holder, panel controls,
   TP4056 charger and antenna go, if not in `hw/REVB_LAB_PLAN.md` yet; set the outline (`OUTLINE` in
   build_carrier_lab.py, or a new place script) and the M3 holes MH1–MH4.
2. **Placement script** `hw/scripts/place_carrier_lab.py` (style of place_carrier.py / build_breakout.layout): J1 IDC
   header with odd pins fanning out to one side and even pins to the other (no track between header pins), U2 boost
   + J20 + F1 + Q1 + C5 in one corner, U3 ideal diode and C9/C10/D2 next to J1 pins 2/4, U4 + C11/C12 between the
   cell node and J30, J30 + H30 positioned so the breakout (31 x 37.5 mm, M3 at its H1; take the J1-to-H1 offset
   from hw/sp4-breakout) sits over free board with its IPEX end at an edge, UI connectors J10/J11/J12/J22 and J23 on
   one edge, U6 fuel gauge near the cell node with a Kelvin sense track. Commit a placement render
   (`render_board.py`) and check courtyards (DRC courtyard overlaps = 0).
3. **Routing script** `hw/scripts/route_carrier_lab.py`: power by hand-coded tracks (as build_breakout does), then
   the signals with `gridroute.Router` restricted to the copper layer (LAYERS) — or hand-coded where few; jumpers
   for crossings. Iterate placement if a net cannot be routed on one layer.
4. **Pour + rule areas**, fill, DRC: `kicad-cli pcb drc --schematic-parity --severity-all` → 0 violations, 0
   unconnected, 0 parity. Verify FR10 (no pour between SMD pads) and GND continuity.
5. **Fab outputs** (copy `build_breakout.fab`): gerbers of the copper layer + Edge.Cuts + drill (one Excellon, all
   NPTH in practice), 1:1 copper PDFs plain + mirrored, assembly PDF, schematic PDF, zip. Renders.
6. **Docs.** `hw/DESIGN_NOTES.md` (a rev B section), `hw/BOM.csv` (rev B list; `build_bom.py` may need a rev B
   variant), `hw/REVB_LAB_PLAN.md` status, CLAUDE.md status + session log. Do not touch rev A.
7. **Hand-off.** Commit, fast-forward main, push (CLAUDE.md: one branch). Tell Santiago: email the zip to
   juan.antonio.chavez@upc.edu; order list with current stock.

## Done when
- ERC 0, DRC 0 / 0 unconnected / 0 parity (all severities), with the lab floor rules in the .kicad_pro.
- One copper layer (or a justified handful of wire vias, none under a part).
- No track < 0.5 mm except necks <= 2 mm long; no hole < 0.7 mm; every THT pad >= hole + 0.7 mm.
- Fab zip + 1:1 PDFs exist; DESIGN_NOTES, BOM and CLAUDE.md updated; `make -C radio/fw test`, `make -C proto test`
  and `python3 radio/phy_config.py` still pass (they should: nothing outside hw/ changes).
