"""Fab outputs for the carrier (run once DRC shows 0 errors and 0 unconnected).

    python3 hw/scripts/fab_carrier.py

hw/teamc-carrier/fab/: gerbers (2 layers + mask, paste, silk, edge), Excellon drill (PTH/NPTH) + maps, the
placement file (KiCad CSV, and JLCPCB's CPL columns), assembly and schematic PDFs; zipped as
hw/teamc-carrier/teamc-carrier_gerbers.zip (gerbers + drill only: what the fab's upload page takes).
"""
import csv
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boardutil as bu  # noqa: E402
from place_carrier import PCB  # noqa: E402

DIR = os.path.dirname(PCB)
NAME = "teamc-carrier"
SCH = os.path.join(DIR, NAME + ".kicad_sch")


def main():
    out = os.path.join(DIR, "fab")
    shutil.rmtree(out, ignore_errors=True)
    gerb = os.path.join(out, "gerbers")
    os.makedirs(gerb)
    layers = "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.SilkS,B.SilkS,Edge.Cuts"
    bu.run("kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--no-protel-ext", "-o", gerb + "/", PCB)
    bu.run("kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
           "--generate-map", "--map-format", "pdf", "-o", gerb + "/", PCB)
    pos = os.path.join(out, f"{NAME}-pos.csv")
    bu.run("kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
           "--exclude-dnp", "-o", pos, PCB)
    with open(pos, newline="") as f, open(os.path.join(out, f"{NAME}-cpl-jlcpcb.csv"), "w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in csv.DictReader(f):
            w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm",
                        "Top" if r["Side"] == "top" else "Bottom", r["Rot"]])
    bu.run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Fab,F.SilkS,Edge.Cuts", "--mode-single",
           "--include-border-title", "-o", os.path.join(out, f"{NAME}_assembly.pdf"), PCB)
    bu.run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Cu,B.Cu,Edge.Cuts", "--mode-separate",
           "-o", os.path.join(out, "copper") + "/", PCB)
    bu.run("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(DIR, f"{NAME}_schematic.pdf"), SCH)
    shutil.copy(os.path.join(os.path.dirname(DIR), "BOM.csv"), os.path.join(out, f"{NAME}-BOM.csv"))
    zipname = os.path.join(DIR, f"{NAME}_gerbers")
    shutil.make_archive(zipname, "zip", gerb)
    print("fab files in", out, "and", zipname + ".zip")
    for root, _, files in os.walk(out):
        for n in sorted(files):
            print("  ", os.path.relpath(os.path.join(root, n), out))


if __name__ == "__main__":
    main()
