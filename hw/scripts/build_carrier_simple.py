"""Build carrier rev C ("simple", UPC lab) in hw/teamc-carrier-simple: lab footprints, schematic, ERC, netlist,
board with outline and unplaced footprints. Placement and routing come later (checkpoint 3).

    python3 hw/scripts/build_carrier_simple.py            # everything above
    python3 hw/scripts/build_carrier_simple.py --no-board # schematic + ERC + netlist only

Concept and decisions: hw/teamc-carrier-simple/CONCEPT.md. Sheets: hw/teamc-carrier-simple/sheets/<name>.py
(build() -> schgen.Sheet). Copied from build_carrier_lab.py (rev B); rev A/B files are not touched.
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
import schgen  # noqa: E402
from schgen import Project  # noqa: E402

schgen.DATE = "2026-10-24"

NAME = "teamc-carrier-simple"
DIR = os.path.join(bu.HW, NAME)
sys.path.insert(0, os.path.join(DIR, "sheets"))
SHEETS = ["power", "pi_link", "radio", "ui"]
SCH = os.path.join(DIR, NAME + ".kicad_sch")
PCB = os.path.join(DIR, NAME + ".kicad_pcb")
PRO = os.path.join(DIR, NAME + ".kicad_pro")
NET = os.path.join(DIR, "build", NAME + ".net")

# UPC lab milling (Chavez slides; Jimenez guide v1.2): track >= 0.5 mm (0.3 only on short necks), clearance
# >= 0.3 mm (0.2 floor), holes >= 0.7 mm, pads >= hole + 0.7 (better + 1.0). Rev C is a big board: wider defaults.
LAB_C = {"clearance": 0.4, "track": 0.8, "via_d": 2.0, "via_drill": 1.0, "edge": 0.5}
NET_CLASSES = [
    ("Power", 2.0, ["/power/BAT_IN", "VBAT", "5V_BOOST", "5V_PI"]),
    ("Radio3V3", 1.0, ["3V3_RADIO"]),
    ("Ground", 1.0, ["GND"]),
]
# provisional outline (KiCad page mm): 120 x 63 mm, box inside dimensions not measured yet (checkpoint 2)
OUTLINE = (50.0, 50.0, 170.0, 113.0)


def lab_floor(pro_path):
    """Board minimums for the lab (as rev B): 0.3 mm tracks only on short necks, 0.2 mm clearance at most where
    unavoidable, 0.7 mm holes, at least one thermal spoke. No silkscreen and no solder mask at the lab: those checks
    are off and the references live on the Fab layers (assembly drawing)."""
    with open(pro_path, encoding="utf-8") as f:
        p = json.load(f)
    p["board"]["design_settings"]["rules"].update(
        min_clearance=0.2, min_track_width=0.3, min_through_hole_diameter=0.7, min_via_diameter=1.7,
        min_via_annular_width=0.35, min_hole_clearance=0.3, min_hole_to_hole=0.5, min_resolved_spokes=1,
        min_copper_edge_clearance=LAB_C["edge"])
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
    """W1, W2, ... from links.json (written by route/finish_carrier_simple.py): one Conn_01x01 per wire link on the
    sheet that owns its net (global nets and GND on pi_link), footprint teamc:RevC_WireLink_L<len>mm."""
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
            s.note("WIRE LINKS (one copper layer): INSULATED 22 AWG solid tinned copper wire on the component side between\n"
                   "two unplated 1.0 mm holes, ends stripped ~3 mm, soldered on the copper side; lay it flat, glue it for the\n"
                   "drop test. Positions and lengths: hw/teamc-carrier-simple/links.json and the assembly drawing.",
                   at=(25.4, 262.89), size=1.27)
        length = link_length(lk)
        s.add("Connector_Generic:Conn_01x01", f"W{i}", f"wire link {length:.1f} mm", at=(30.48 + n * 20.32, 276.86),
              fp=f"teamc:RevC_WireLink_L{length:.1f}mm", nets={"1": local},
              mpn="22 AWG solid tinned copper hook-up wire, PVC insulated (ends stripped)")
    return len(links)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-board", action="store_true")
    a = ap.parse_args()
    print(bu.run(sys.executable, os.path.join(HERE, "teamc_lib", "gen_lab_revc.py")))
    new_project()
    bu.write_lib_tables(DIR)
    bu.set_project_rules(PRO, rules=LAB_C, classes=NET_CLASSES)
    lab_floor(PRO)
    sheets = [importlib.import_module(n).build() for n in SHEETS]
    print(f"{add_links(sheets)} wire links")
    Project(NAME, sheets, title="Team C carrier rev C – simple, UPC lab, through-hole + modules (DRAFT)").write(DIR)
    rpt = os.path.join(DIR, "build", "erc.rpt")
    print(bu.run("kicad-cli", "sch", "erc", "--severity-all", "-o", rpt, SCH))
    bu.run("kicad-cli", "sch", "export", "netlist", "-o", NET, SCH)
    if not a.no_board:
        print(bu.run(sys.executable, os.path.join(HERE, "netlist2pcb.py"), PCB, NET))


if __name__ == "__main__":
    main()
