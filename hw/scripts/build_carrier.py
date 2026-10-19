"""Build the Team C Pi 3 A+ HAT carrier (hw/teamc-carrier): schematic sheets, ERC, netlist, board update.

    python3 hw/scripts/build_carrier.py            # schematic + ERC + netlist + board footprints/nets
    python3 hw/scripts/build_carrier.py --sheet ui # one sheet alone as a scratch project (ERC for its owner)

Each sheet lives in hw/teamc-carrier/sheets/<name>.py and defines build() -> schgen.Sheet.
Placement and routing are in place_carrier.py.
"""
import argparse
import importlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boardutil as bu  # noqa: E402
import schgen  # noqa: E402
from schgen import Project  # noqa: E402

NAME = "teamc-carrier"
DIR = os.path.join(bu.HW, NAME)
sys.path.insert(0, os.path.join(DIR, "sheets"))
SHEETS = ["power", "pi_header", "radio", "ui"]
SCH = os.path.join(DIR, NAME + ".kicad_sch")
PCB = os.path.join(DIR, NAME + ".kicad_pcb")
PRO = os.path.join(DIR, NAME + ".kicad_pro")
NET = os.path.join(DIR, "build", NAME + ".net")
POWER_NETS = ["VBAT", "VBAT_SW", "BAT_RAW", "5V_BOOST", "5V_PI", "SW_NODE", "/power/BAT_RAW", "/power/5V_BOOST",
              "/power/SW_NODE", "/power/BAT2_RAW"]


def build(names):
    return [importlib.import_module(n).build() for n in names]


def one_sheet(name, out):
    """Write one sheet as a stand-alone project in `out` and run ERC on it (for the sheet's owner)."""
    os.makedirs(out, exist_ok=True)
    schgen.STANDALONE = True
    sh = build([name])[0]
    sh.write_standalone(out, name)
    shutil.copy(PRO, os.path.join(out, name + ".kicad_pro"))
    bu.write_lib_tables(out)
    # lib tables point to hw/lib relative to `out`; rewrite them with an absolute path
    for t in ("sym-lib-table", "fp-lib-table"):
        p = os.path.join(out, t)
        s = open(p).read().replace("${KIPRJMOD}/" + os.path.relpath(os.path.join(bu.HW, "lib"), out),
                                   os.path.join(bu.HW, "lib"))
        open(p, "w").write(s)
    rpt = os.path.join(out, name + "_erc.rpt")
    print(bu.run("kicad-cli", "sch", "erc", "--severity-all", "-o", rpt, os.path.join(out, name + ".kicad_sch")))
    print(open(rpt).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", help="build one sheet alone into --out and run ERC")
    ap.add_argument("--out", default=os.path.join(DIR, "build", "sheet"))
    ap.add_argument("--no-board", action="store_true")
    a = ap.parse_args()
    if a.sheet:
        one_sheet(a.sheet, a.out)
        return
    os.makedirs(os.path.join(DIR, "build"), exist_ok=True)
    bu.write_lib_tables(DIR)
    from route_carrier import FINE_NETS
    bu.set_project_rules(PRO, classes=[("FinePitch", 0.4, FINE_NETS, 0.15), ("Power", 1.0, ["VBAT", "VBAT_SW", "5V_PI", "/power/*"]),
                                       ("Radio3V3", 0.5, ["3V3_RADIO"])])
    Project(NAME, build(SHEETS), title="Team C Pi 3 A+ HAT carrier (DRAFT – for ET review)").write(DIR)
    rpt = os.path.join(DIR, "build", "erc.rpt")
    print(bu.run("kicad-cli", "sch", "erc", "--severity-all", "-o", rpt, SCH))
    bu.run("kicad-cli", "sch", "export", "netlist", "-o", NET, SCH)
    if not a.no_board:
        print(bu.run(sys.executable, os.path.join(HERE, "netlist2pcb.py"), PCB, NET, "--refresh", "J1"))


if __name__ == "__main__":
    main()
