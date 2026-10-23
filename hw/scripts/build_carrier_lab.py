"""Build the set-up of carrier rev B for the UPC lab (hw/teamc-carrier-lab): footprints, schematic, ERC, netlist,
board with outline and unplaced footprints. Placement, routing and fab files are the design loop
(hw/REVB_LOOP_PROMPT.md), not this script.

    python3 hw/scripts/build_carrier_lab.py            # everything above
    python3 hw/scripts/build_carrier_lab.py --no-board # schematic + ERC + netlist only

Plan and decisions: hw/REVB_LAB_PLAN.md. Sheets: hw/teamc-carrier-lab/sheets/<name>.py (build() -> schgen.Sheet);
module pads: hw/teamc-carrier-lab/sheets/modules.py.
"""
import argparse
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402
from schgen import Project  # noqa: E402

NAME = "teamc-carrier-lab"
DIR = os.path.join(bu.HW, NAME)
sys.path.insert(0, os.path.join(DIR, "sheets"))
SHEETS = ["power", "pi_link", "radio", "ui"]
SCH = os.path.join(DIR, NAME + ".kicad_sch")
PCB = os.path.join(DIR, NAME + ".kicad_pcb")
PRO = os.path.join(DIR, NAME + ".kicad_pro")
NET = os.path.join(DIR, "build", NAME + ".net")

# UPC lab milling (Chávez slides 23-Oct-26: track > 0.3, better > 0.5 mm; via hole >= 0.7 mm. Jiménez guide v1.2:
# clearance >= 0.2 mm, pad >= hole + 0.7, better + 1.0..1.5). Vias are wires soldered on both sides: 2.0 / 1.0 mm.
LAB_B = {"clearance": 0.3, "track": 0.5, "via_d": 2.0, "via_drill": 1.0, "edge": 0.5}
NET_CLASSES = [
    ("Power", 1.5, ["/power/BAT_IN", "/power/BAT_RAW", "VBAT", "5V_BOOST", "5V_PI"]),
    ("Radio3V3", 0.8, ["3V3_RADIO"]),
    ("Ground", 0.5, ["GND"]),
]
# provisional outline (mm, KiCad page coordinates); the loop fixes it from the box's inside dimensions
OUTLINE = (50.0, 50.0, 150.0, 130.0)


def lab_floor(pro_path):
    """Board minimums for the lab: 0.3 mm tracks only on short necks, 0.2 mm clearance at most where unavoidable,
    0.7 mm holes, pads >= hole + 0.7 mm, at least one thermal spoke (a pad in a narrow strip of pour - the sense
    ground of U6, the socket's ground - gets one 0.5 mm spoke, plenty for their currents).

    The lab board has no silkscreen and no solder mask (Chavez slides, Jimenez guide), so the silkscreen and mask
    checks are off; the references live on the Fab layers (assembly drawing)."""
    with open(pro_path, encoding="utf-8") as f:
        p = json.load(f)
    p["board"]["design_settings"]["rules"].update(
        min_clearance=0.2, min_track_width=0.3, min_through_hole_diameter=0.7, min_via_diameter=1.7,
        min_via_annular_width=0.35, min_hole_clearance=0.3, min_hole_to_hole=0.5, min_resolved_spokes=1,
        min_copper_edge_clearance=LAB_B["edge"])
    p["board"]["design_settings"]["rule_severities"].update(
        silk_edge_clearance="ignore", silk_over_copper="ignore", silk_overlap="ignore", solder_mask_bridge="ignore")
    with open(pro_path, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)


def new_project():
    """Start from the breakout's project file (a valid KiCad 10 .kicad_pro) and an empty board."""
    os.makedirs(os.path.join(DIR, "build"), exist_ok=True)
    if not os.path.exists(PRO):
        with open(os.path.join(bu.HW, "sp4-breakout", "sp4-breakout.kicad_pro"), encoding="utf-8") as f:
            p = json.load(f)
        p["meta"]["filename"] = NAME + ".kicad_pro"
        p.get("erc", {}).pop("erc_exclusions", None)
        with open(PRO, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
    if not os.path.exists(PCB):
        board = pcbnew.NewBoard(PCB)
        x1, y1, x2, y2 = OUTLINE
        bu.outline_rect(board, x1, y1, x2, y2, r=2.0)
        board.Save(PCB)


def link_length(lk):
    return round(((lk["a"][0] - lk["b"][0]) ** 2 + (lk["a"][1] - lk["b"][1]) ** 2) ** 0.5, 1)


def add_links(sheets):
    """W1, W2, ... from links.json (written by finish_carrier_lab.py): one Conn_01x01 per wire link on the sheet
    that owns its net (global nets and GND on pi_link), footprint teamc:WireLink_L<len>mm (gen_lab.wire_link)."""
    path = os.path.join(DIR, "links.json")
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        links = json.load(f).get("links", [])
    by_name = {s.name: s for s in sheets}
    count = {}
    for i, lk in enumerate(links, 1):
        net = lk["net"]
        if net.startswith("/"):
            sheet, local = net.strip("/").split("/", 1)
        else:
            sheet, local = "pi_link", net
        s = by_name[sheet]
        n = count.get(sheet, 0)
        count[sheet] = n + 1
        if n == 0:
            s.note("WIRE LINKS (rev B, single copper layer): bare 0.6 mm tinned copper wire on the component side\n"
                   "between two unplated 1.0 mm holes, soldered on the copper side; the board's crossings.\n"
                   "Positions and lengths: hw/teamc-carrier-lab/links.json.", at=(25.4, 262.89), size=1.27)
        length = link_length(lk)
        s.add("Connector_Generic:Conn_01x01", f"W{i}", f"wire link {length:.1f} mm", at=(30.48 + n * 20.32, 276.86),
              fp=f"teamc:WireLink_L{length:.1f}mm", nets={"1": local},
              mpn="0.6 mm (22 AWG) tinned copper wire, bare")
    return len(links)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-board", action="store_true")
    a = ap.parse_args()
    for gen in ("gen_lab.py", "gen_modules.py"):
        print(bu.run(sys.executable, os.path.join(HERE, "teamc_lib", gen)))
    new_project()
    bu.write_lib_tables(DIR)
    bu.set_project_rules(PRO, rules=LAB_B, classes=NET_CLASSES)
    lab_floor(PRO)
    sheets = [importlib.import_module(n).build() for n in SHEETS]
    print(f"{add_links(sheets)} wire links")
    Project(NAME, sheets, title="Team C carrier rev B – UPC lab, hand-soldered modules (DRAFT)").write(DIR)
    rpt = os.path.join(DIR, "build", "erc.rpt")
    print(bu.run("kicad-cli", "sch", "erc", "--severity-all", "-o", rpt, SCH))
    bu.run("kicad-cli", "sch", "export", "netlist", "-o", NET, SCH)
    if not a.no_board:
        print(bu.run(sys.executable, os.path.join(HERE, "netlist2pcb.py"), PCB, NET))


if __name__ == "__main__":
    main()
