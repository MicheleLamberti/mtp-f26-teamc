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
    0.7 mm holes, pads >= hole + 0.7 mm, two thermal spokes."""
    with open(pro_path, encoding="utf-8") as f:
        p = json.load(f)
    p["board"]["design_settings"]["rules"].update(
        min_clearance=0.2, min_track_width=0.3, min_through_hole_diameter=0.7, min_via_diameter=1.7,
        min_via_annular_width=0.35, min_hole_clearance=0.3, min_hole_to_hole=0.5, min_resolved_spokes=2,
        min_copper_edge_clearance=LAB_B["edge"])
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
    Project(NAME, sheets, title="Team C carrier rev B – UPC lab, hand-soldered modules (DRAFT)").write(DIR)
    rpt = os.path.join(DIR, "build", "erc.rpt")
    print(bu.run("kicad-cli", "sch", "erc", "--severity-all", "-o", rpt, SCH))
    bu.run("kicad-cli", "sch", "export", "netlist", "-o", NET, SCH)
    if not a.no_board:
        print(bu.run(sys.executable, os.path.join(HERE, "netlist2pcb.py"), PCB, NET))


if __name__ == "__main__":
    main()
