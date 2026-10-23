"""Fab files, wire-link list, renders and BoM for carrier rev C ("simple", UPC lab mill).

    python3 hw/scripts/fab_carrier_simple.py [--no-render]

hw/teamc-carrier-simple/fab/: gerbers of the copper layer (F.Cu) and the outline (with the cable-tie slot and notch),
one Excellon drill file (every hole is unplated at the lab, whatever KiCad calls it) with a PDF map, 1:1 copper
artwork as seen from the copper side and mirrored (toner transfer / photo mask), the assembly drawing of the
component side (every part, the wire links, the SP4 breakout's outline) and of the copper side, the schematic,
wire_links.csv (what to cut and where it goes), and teamc-carrier-simple_gerbers.zip for the email to the lab.
Then the 3D renders (render_board.py: top, bottom, iso) and hw/BOM_revC.csv (build_bom_revc.py).
"""
import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boardutil as bu  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "teamc-carrier-simple"
DIR = os.path.join(bu.HW, NAME)
PCB = os.path.join(DIR, NAME + ".kicad_pcb")
SCH = os.path.join(DIR, NAME + ".kicad_sch")
STRIP = 3.0       # insulation stripped at each end (mm)
BOARD_T = 1.6


def wire_list(out):
    """fab/wire_links.csv: one row per wire link (W1..), positions in board mm from the top-left corner of the
    copper-side view (the assembly drawing of the component side is its mirror image)."""
    with open(os.path.join(DIR, "links.json"), encoding="utf-8") as f:
        links = json.load(f)["links"]
    rows = []
    for i, lk in enumerate(links, 1):
        length = round(math.dist(lk["a"], lk["b"]), 1)
        rows.append([f"W{i}", lk["net"].split("/")[-1], f"{lk['a'][0]:.1f}, {lk['a'][1]:.1f}",
                     f"{lk['b'][0]:.1f}, {lk['b'][1]:.1f}", f"{length:.1f}",
                     f"{length + 2 * (STRIP + BOARD_T + 1.0):.0f}"])
    path = os.path.join(out, "wire_links.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["link", "net", "hole A (x, y mm, copper-side view)", "hole B", "hole to hole (mm)",
                    "cut the insulated 22 AWG wire to (mm)"])
        w.writerows(rows)
    return rows


def parts_view():
    """A perspective render of the component side (the parts), next to render_board.py's views."""
    import tempfile
    import pcbnew
    import render_board as rb
    tmp = tempfile.mkdtemp(prefix="render3d_")
    try:
        b = pcbnew.LoadBoard(PCB)
        rb.fix_models(b, absolute=True, board_dir=DIR)
        t = os.path.join(tmp, NAME + ".kicad_pcb")
        b.Save(t)
        rb.render(t, os.path.join(DIR, f"{NAME}_render_iso_parts.png"),
                  ["--side", "bottom", "--perspective", "--rotate", "-50,0,30", "--zoom", "0.8"], 1600, 1200, True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
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
    bu.run("kicad-cli", "pcb", "export", "pdf", "--layers", "B.Fab,B.CrtYd,Dwgs.User,Edge.Cuts", "--mode-single",
           "--mirror", "-o", os.path.join(out, f"{NAME}_assembly_component_side.pdf"), PCB)
    bu.run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Cu,B.Fab,Edge.Cuts", "--mode-single",
           "-o", os.path.join(out, f"{NAME}_assembly_copper_side.pdf"), PCB)
    bu.run("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(out, f"{NAME}_schematic.pdf"), SCH)
    shutil.copy(os.path.join(out, f"{NAME}_schematic.pdf"), os.path.join(DIR, f"{NAME}_schematic.pdf"))
    rows = wire_list(out)
    zipname = os.path.join(DIR, f"{NAME}_gerbers")
    shutil.make_archive(zipname, "zip", out)
    print("fab files in", out, "and", zipname + ".zip")
    for f in sorted(os.listdir(out)):
        print("  ", f)
    print(f"{len(rows)} wire links:", ", ".join(f"{r[0]} {r[1]} {r[4]} mm" for r in rows))
    if not a.no_render:
        r = subprocess.run([sys.executable, os.path.join(HERE, "render_board.py"), PCB], capture_output=True,
                           text=True)
        print("\n".join(ln for ln in (r.stdout + r.stderr).splitlines() if "assert" not in ln)[-1500:])
        parts_view()
    print(bu.run(sys.executable, os.path.join(HERE, "build_bom_revc.py")))


if __name__ == "__main__":
    main()
