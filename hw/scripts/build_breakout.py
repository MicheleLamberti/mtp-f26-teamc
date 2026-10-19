"""Build the E01-ML01SP4 breakout (hw/sp4-breakout): schematic, ERC, board, routing, DRC, fab files.

    python3 hw/scripts/build_breakout.py [--fab]

Single-sided (F.Cu only) so the ETSETB lab can make it in an evening: the SP4 and the 0805 parts sit on the copper
side; the 1 x 8 header and the 1 x 2 bench-supply header go in from the back (pins point down, breadboard-friendly).
Header order = the common nRF24 module order: 1 GND, 2 VCC, 3 CE, 4 CSN, 5 SCK, 6 MOSI, 7 MISO, 8 IRQ.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402
from schgen import Sheet  # noqa: E402

NAME = "sp4-breakout"
DIR = os.path.join(bu.HW, NAME)
SCH = os.path.join(DIR, NAME + ".kicad_sch")
PCB = os.path.join(DIR, NAME + ".kicad_pcb")
PRO = os.path.join(DIR, NAME + ".kicad_pro")
NET = os.path.join(DIR, "build", NAME + ".net")
SP4_DS = "https://www.cdebyte.com/products/E01-ML01SP4"
CX, CY = 100.0, 100.0          # SP4 centre on the board
SIG_W = 0.5


def schematic():
    s = Sheet(NAME, "E01-ML01SP4 breakout (DRAFT – for ET review)", paper="A4")
    s.add("teamc:E01-ML01SP4", "U1", "E01-ML01SP4", fp="teamc:E01-ML01SP4", at=(127, 88.9), mpn="E01-ML01SP4",
          mfr="Ebyte", ds=SP4_DS,
          nets={"1": "VCC", "2": "CE", "3": "CSN", "4": "SCK", "5": "MOSI", "6": "MISO", "7": "IRQ",
                "8": "GND", "9": "GND", "10": "GND"})
    s.add("Connector_Generic:Conn_01x08", "J1", "nRF24 header", at=(63.5, 88.9),
          fp="Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical", mpn="1x08 2.54 mm pin header",
          nets={"1": "GND", "2": "VCC", "3": "CE", "4": "CSN", "5": "SCK", "6": "MOSI", "7": "MISO", "8": "IRQ"})
    s.add("Connector_Generic:Conn_01x02", "J2", "3V3 bench supply", at=(63.5, 119.38),
          fp="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", mpn="1x02 2.54 mm pin header",
          nets={"1": "VCC", "2": "GND"})
    s.add("Device:C_Polarized", "C1", "100u 10V", at=(165.1, 81.28), fp="Capacitor_SMD:CP_Elec_6.3x5.4",
          mpn="EEE-FK1A101P (or any 100 uF >= 6.3 V, 6.3 x 5.4 mm SMD)", mfr="Panasonic",
          nets={"1": "VCC", "2": "GND"})
    s.add("Device:C", "C2", "10u X5R", at=(177.8, 81.28),
          fp="Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", mpn="CL21A106KAYNNNE", mfr="Samsung",
          nets={"1": "VCC", "2": "GND"})
    s.add("Device:C", "C3", "100n X7R", at=(190.5, 81.28),
          fp="Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", mpn="CL21B104KBCNNNC", mfr="Samsung",
          nets={"1": "VCC", "2": "GND"})
    s.add("Connector:TestPoint", "TP1", "GND", at=(165.1, 109.22),
          fp="TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm", mpn="wire loop or Keystone 5001", nets={"1": "GND"})
    s.add("Mechanical:MountingHole", "H1", "M3", at=(190.5, 109.22), fp="MountingHole:MountingHole_3.2mm_M3",
          nets={})
    s.pwr_flag("VCC", (147.32, 66.04))
    s.pwr_flag("GND", (154.94, 66.04))
    s.note("DRAFT – for ET review. SP4 VCC 2.0–3.6 V, ABS. MAX 3.6 V: feed it from the radio LDO or a bench supply,\n"
           "never from the Li-ion cell or the Pi's 3V3 pin. >= 100 uF at the module (C1).\n"
           "Header J1 = common nRF24 order; J2 = bench supply input (same VCC/GND).\n"
           "Pi 3 wiring: radio/fw/linux/README.md. Footprint: Ebyte manual rev 1.7 p.4 (14.5 x 18 mm).",
           (25.4, 30.48), 1.5)
    s.write_standalone(DIR, NAME)


def choose_rotation(board, ref, back, want):
    """Pick the orientation whose pads match want(pad_xy_list) (tries the four right angles)."""
    for rot in (0, 90, 180, 270):
        bu.place(board, ref, 0, 0, rot, back)
        pts = [bu.pad_xy(board, ref, n) for n in range(1, len(bu.fp(board, ref).Pads()) + 1)]
        if want(pts):
            return rot
    raise SystemExit(f"no orientation for {ref}")


def layout():
    board = pcbnew.LoadBoard(PCB)
    for item in list(board.GetTracks()) + list(board.Zones()) + list(board.GetDrawings()):
        board.Delete(item)
    x1, y1, x2, y2 = 88.5, 72.0, 119.5, 109.5
    bu.outline_rect(board, x1, y1, x2, y2, r=1.0)

    bu.place(board, "U1", CX, CY, 0)
    # header row: pin 1 (GND) at the right, pin 8 (IRQ) at the left, pins in a horizontal line
    hy = 79.0
    row = lambda p: all(abs(a[1] - p[0][1]) < 1e-3 for a in p) and p[0][0] > p[-1][0]  # noqa: E731
    r = choose_rotation(board, "J1", True, row)
    bu.place(board, "J1", 0, 0, r, True)
    px, py = bu.pad_xy(board, "J1", 1)
    sig_x = {n: bu.pad_xy(board, "U1", n)[0] for n in range(1, 9)}
    # centre header pins 8..2 on the signal pads 7..1 (pin 5 SCK above pad 4 SCK)
    want_x5 = sig_x[4]
    p5x, _ = bu.pad_xy(board, "J1", 5)
    bu.place(board, "J1", want_x5 - p5x, hy - py, r, True)
    r2 = choose_rotation(board, "J2", True, lambda p: abs(p[0][1] - p[1][1]) < 1e-3 and p[0][0] < p[1][0])
    bu.place(board, "J2", 0, 0, r2, True)
    jx, jy = bu.pad_xy(board, "J2", 1)
    bu.place(board, "J2", 111.5 - jx, 100.0 - jy, r2, True)
    bu.place(board, "C1", 114.6, 93.6, 90)      # + pad (1) at the top
    bu.place(board, "C2", 111.6, 84.6, 0)        # pad 1 (VCC) on the left
    bu.place(board, "C3", 111.6, 87.2, 0)
    bu.place(board, "TP1", 116.8, 79.0, 0)
    bu.place(board, "H1", 115.0, 105.6, 0)
    if bu.pad_xy(board, "C1", 1)[1] > bu.pad_xy(board, "C1", 2)[1]:
        bu.place(board, "C1", 114.6, 93.6, 270)

    # signal fan-out: straight up from each pad, 45 degrees, straight up into the header
    bend = 88.5
    jpin = {"CE": 3, "CSN": 4, "SCK": 5, "MOSI": 6, "MISO": 7, "IRQ": 8}
    upin = {"CE": 2, "CSN": 3, "SCK": 4, "MOSI": 5, "MISO": 6, "IRQ": 7}
    for net, jp in jpin.items():
        ux, uy = bu.pad_xy(board, "U1", upin[net])
        hx, hy2 = bu.pad_xy(board, "J1", jp)
        dx = hx - ux
        bu.track(board, [(ux, uy), (ux, bend), (hx, bend - abs(dx)), (hx, hy2)], SIG_W, net)
    # VCC: header pin 2 down the right side, across to pad 1; caps and C1 hang off it
    vx, vy = bu.pad_xy(board, "J1", 2)
    u1x, u1y = bu.pad_xy(board, "U1", 1)
    vbus = 88.9
    c2x, c2y = bu.pad_xy(board, "C2", 1)
    c3x, c3y = bu.pad_xy(board, "C3", 1)
    c1x, c1y = bu.pad_xy(board, "C1", 1)
    j2x, j2y = bu.pad_xy(board, "J2", 1)
    tap = c1x - 2.2                       # where the bench-supply feed joins the VCC bus
    # every junction is a segment end point (a T in the middle of a segment counts as dangling)
    bu.track(board, [(vx, vy), (vx, c2y), (vx, c3y), (vx, vbus)], 0.6, "VCC")
    bu.track(board, [(u1x, u1y), (u1x, vbus), (vx, vbus)], SIG_W, "VCC")
    bu.track(board, [(vx, vbus), (tap, vbus), (c1x, vbus), (c1x, c1y)], 0.6, "VCC")
    bu.track(board, [(c2x, c2y), (vx, c2y)], 0.6, "VCC")
    bu.track(board, [(c3x, c3y), (vx, c3y)], 0.6, "VCC")
    bu.track(board, [(j2x, j2y), (j2x, 96.0), (tap, 96.0), (tap, vbus)], 0.6, "VCC")

    # ground pour over the whole copper side (also under the module, as Ebyte asks)
    m = 0.5
    bu.zone(board, "GND", pcbnew.F_Cu, [(x1 + m, y1 + m), (x2 - m, y1 + m), (x2 - m, y2 - m), (x1 + m, y2 - m)])

    # silkscreen (F side = module side)
    names = {1: "GND", 2: "VCC", 3: "CE", 4: "CSN", 5: "SCK", 6: "MOSI", 7: "MISO", 8: "IRQ"}
    for n, s in names.items():
        hx, hy2 = bu.pad_xy(board, "J1", n)
        t = bu.text(board, s, hx, hy2 - 2.4, size=0.8, rot=90, thick=0.12)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    bu.text(board, "+3V3 GND", 112.8, 102.0, size=0.8, thick=0.12)
    bu.text(board, "SP4 v0.1", 115.6, 83.2, size=0.8, thick=0.12)
    bu.fp(board, "H1").Reference().SetVisible(False)
    for c in ("C2", "C3"):
        f = bu.fp(board, c)
        f.Reference().SetPosition(bu.v(pcbnew.ToMM(f.GetPosition().x) + 3.3, pcbnew.ToMM(f.GetPosition().y)))
    bu.fp(board, "TP1").Reference().SetVisible(False)
    bu.text(board, "MTP F26 Team C - DRAFT for ET", 104.0, 84.0, layer=pcbnew.B_SilkS,
            size=0.8, thick=0.12)
    bu.fill_zones(board)
    board.Save(PCB)


def fab():
    out = os.path.join(DIR, "fab")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    layers = "F.Cu,F.Mask,F.SilkS,B.SilkS,Edge.Cuts"
    bu.run("kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--no-protel-ext", "-o", out + "/", PCB)
    bu.run("kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
           "--generate-map", "--map-format", "pdf", "-o", out + "/", PCB)
    # 1:1 copper artwork for the lab: as seen from the copper side, and mirrored (toner transfer / photo mask)
    for mirror, suffix in ((False, "copper_1to1"), (True, "copper_1to1_mirrored")):
        args = ["kicad-cli", "pcb", "export", "pdf", "--layers", "F.Cu,Edge.Cuts", "--black-and-white",
                "--mode-single", "--include-border-title", "-o", os.path.join(out, f"{NAME}_{suffix}.pdf")]
        if mirror:
            args.insert(-2, "--mirror")
        bu.run(*args, PCB)
    bu.run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Fab,F.SilkS,Edge.Cuts", "--mode-single",
           "-o", os.path.join(out, f"{NAME}_assembly.pdf"), PCB)
    bu.run("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(out, f"{NAME}_schematic.pdf"), SCH)
    zipname = os.path.join(DIR, f"{NAME}_gerbers")
    shutil.make_archive(zipname, "zip", out)
    print("fab files in", out, "and", zipname + ".zip")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fab", action="store_true")
    a = ap.parse_args()
    os.makedirs(os.path.join(DIR, "build"), exist_ok=True)
    bu.write_lib_tables(DIR)
    bu.set_project_rules(PRO, classes=[("Power", 0.6, ["VCC"])])
    schematic()
    print(bu.run("kicad-cli", "sch", "erc", "--severity-all", "-o", os.path.join(DIR, "build", "erc.rpt"), SCH))
    bu.run("kicad-cli", "sch", "export", "netlist", "-o", NET, SCH)
    print(bu.run(sys.executable, os.path.join(os.path.dirname(__file__), "netlist2pcb.py"), PCB, NET))
    layout()
    print(bu.drc(PCB, os.path.join(DIR, "build", "drc.rpt")))
    if a.fab:
        fab()


if __name__ == "__main__":
    main()
