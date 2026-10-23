"""Fab files for carrier rev B (UPC lab mill), as build_breakout.fab does for the SP4 breakout.

    python3 hw/scripts/fab_carrier_lab.py

hw/teamc-carrier-lab/fab/: gerbers of the copper layer (F.Cu) and the outline, one Excellon drill file (every hole is
unplated at the lab, whatever KiCad calls it) with a PDF map, 1:1 copper artwork as seen from the copper side and
mirrored (toner transfer / photo mask), the assembly drawing of each side (component side = THT parts and the wire
links, copper side = SMD parts), the schematic, and teamc-carrier-lab_gerbers.zip for the email to the lab.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boardutil as bu  # noqa: E402

NAME = "teamc-carrier-lab"
DIR = os.path.join(bu.HW, NAME)
PCB = os.path.join(DIR, NAME + ".kicad_pcb")
SCH = os.path.join(DIR, NAME + ".kicad_sch")


def main():
    out = os.path.join(DIR, "fab")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    bu.run("kicad-cli", "pcb", "export", "gerbers", "--layers", "F.Cu,Edge.Cuts", "--no-protel-ext",
           "-o", out + "/", PCB)
    bu.run("kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--generate-map", "--map-format", "pdf",
           "-o", out + "/", PCB)
    for mirror, suffix in ((False, "copper_1to1"), (True, "copper_1to1_mirrored")):
        args = ["kicad-cli", "pcb", "export", "pdf", "--layers", "F.Cu,Edge.Cuts", "--black-and-white",
                "--mode-single", "--include-border-title", "-o", os.path.join(out, f"{NAME}_{suffix}.pdf")]
        if mirror:
            args.insert(-2, "--mirror")
        bu.run(*args, PCB)
    bu.run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Fab,F.Cu,Edge.Cuts", "--mode-single",
           "-o", os.path.join(out, f"{NAME}_assembly_copper_side.pdf"), PCB)
    bu.run("kicad-cli", "pcb", "export", "pdf", "--layers", "B.Fab,B.CrtYd,Dwgs.User,Edge.Cuts", "--mode-single",
           "--mirror", "-o", os.path.join(out, f"{NAME}_assembly_component_side.pdf"), PCB)
    bu.run("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(out, f"{NAME}_schematic.pdf"), SCH)
    zipname = os.path.join(DIR, f"{NAME}_gerbers")
    shutil.make_archive(zipname, "zip", out)
    print("fab files in", out, "and", zipname + ".zip")
    for f in sorted(os.listdir(out)):
        print("  ", f)


if __name__ == "__main__":
    main()
