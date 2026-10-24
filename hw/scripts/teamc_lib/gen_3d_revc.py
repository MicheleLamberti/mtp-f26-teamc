#!/usr/bin/env python3
"""VRML models for carrier rev C (hw/teamc-carrier-simple): the three hand-soldered modules on their 2.54 mm headers
and the wire link. Simple boxes for renders and for checking heights, not for mechanical CAD.

    python3 hw/scripts/teamc_lib/gen_3d_revc.py

Writes into hw/lib/teamc.3dshapes/ (next to gen_3d.py's models; nothing of rev A/B is changed):
  RevC_Pololu_U3V70F5.wrl     40.64 x 15.24 mm board on 2.5 mm header spacers, inductor + IC + capacitors
  RevC_Pololu_IdealDiode_5388.wrl   17.78 x 11.05 mm board, MOSFET + controller
  RevC_Adafruit_MAX17048_5580.wrl   25.4 x 20.32 mm board, two JST-PH ports, chip
  RevC_WireLink_unit.wrl      an insulated wire 1 mm long (scaled to each link's length by its footprint)
  RevC_BatteryHolder_MPD_BH-18650-PC.wrl, RevC_Fuseholder_Keystone_3517_5x20.wrl, RevC_TestPoint_Keystone_5010.wrl,
  RevC_D_DO-41_P3.81mm_Vertical_CathodeUp.wrl
                              stand-ins for four stock footprints whose models kicad-packages3D does not have
                              (fetch_3d.SUBSTITUTES points the stock refs here)
Module sizes and pin positions: hw/teamc-carrier-simple/sheets/modules.py (from the makers' CAD). Origin = the
footprint origin (module centre), +x right, +y up (= KiCad -y), +z up from the carrier's component side; KiCad's
VRML unit is 0.1 inch, so coordinates are written in mm / 2.54 (the writer of gen_3d.py).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "lib", "teamc.3dshapes")
sys.path.insert(0, os.path.join(HERE, "..", "..", "teamc-carrier-simple", "sheets"))
from modules import MODULES  # noqa: E402

# gen_3d.py writes its own models when it is imported; take only its mesh writer (the part before the first model)
_src = open(os.path.join(HERE, "gen_3d.py"), encoding="utf-8").read()
_ns = {"__name__": "gen_3d_helpers", "__file__": os.path.join(HERE, "gen_3d.py")}
exec(_src.split("# ------------------------------------------------------------------ E01-ML01SP4")[0], _ns)  # noqa: S102
Model, rrect = _ns["Model"], _ns["rrect"]
_ns["MATS"]["red"] = ((0.75, 0.08, 0.06), (0.30, 0.20, 0.20), 0.30, 0)
_ns["MATS"]["glass"] = ((0.80, 0.85, 0.90), (0.90, 0.90, 0.90), 0.60, 0.45)

SPACER = 2.5      # header plastic between the carrier and the module
PCB_T = 1.57


def module(key, board_mat, parts):
    """A module: header plastic under each pin row, gold pins, the board, then parts [(x0, y0, x1, y1, h, mat)]
    in module coordinates (origin bottom-left, y up, mm, heights from the module's top surface)."""
    m = Model()
    md = MODULES[key]
    w, h = md["size"]
    cx, cy = w / 2, h / 2
    rows = {}
    for p in md["pins"]:
        rows.setdefault(round(p["x"], 2), []).append(p["y"])
    pins = [(p["x"], p["y"]) for p in md["pins"]]
    if all(abs(y - pins[0][1]) < 0.01 for _, y in pins[:6]):        # pins in a row along x (MAX17048 board)
        rows = {}
        for x, y in pins:
            rows.setdefault(round(y, 2), []).append(x)
        for y, xs in rows.items():
            m.box(min(xs) - 1.27 - cx, y - 1.27 - cy, max(xs) + 1.27 - cx, y + 1.27 - cy, 0, SPACER, "black")
    else:
        for x, ys in rows.items():
            m.box(x - 1.27 - cx, min(ys) - 1.27 - cy, x + 1.27 - cx, max(ys) + 1.27 - cy, 0, SPACER, "black")
    for x, y in pins:
        m.boxc(x - cx, y - cy, 0.64, 0.64, -2.0, SPACER + PCB_T + 0.8, "gold")
    m.prism([(x - cx, y - cy) for x, y in rrect(0, 0, w, h, 0.6)], SPACER, SPACER + PCB_T, board_mat)
    top = SPACER + PCB_T
    for x0, y0, x1, y1, ph, mat in parts:
        m.box(x0 - cx, y0 - cy, x1 - cx, y1 - cy, top, top + ph, mat)
    return m


def u3v70f5():
    # Pololu: "top parts 3.0 mm, nothing on the bottom"; inductor in the middle, controller and capacitors around it
    return module("U3V70F5", "pcb_green", [
        (13.0, 2.5, 25.0, 12.7, 3.0, "black"),          # inductor
        (27.0, 4.0, 31.0, 8.0, 1.0, "black"),           # controller
        (8.0, 2.0, 11.2, 5.2, 2.0, "ivory"), (8.0, 9.5, 11.2, 12.7, 2.0, "ivory"),       # input capacitors
        (31.5, 9.5, 34.7, 12.7, 2.0, "ivory"), (27.0, 9.5, 30.2, 12.7, 2.0, "ivory"),   # output capacitors
        (37.5, 1.2, 40.0, 3.4, 0.6, "silver"), (0.6, 12.0, 3.4, 14.4, 0.6, "silver"),   # M2 hole rings (marks)
    ])


def ideal_diode():
    return module("IDEAL_DIODE", "pcb_green", [
        (6.4, 3.0, 11.4, 9.0, 1.1, "black"),            # MOSFET
        (6.8, 0.6, 9.8, 2.4, 0.9, "black"),             # LM74700 controller
        (11.8, 0.8, 13.0, 2.4, 0.8, "ivory"),
    ])


def max17048():
    return module("MAX17048", "black", [
        (0.4, 13.0, 6.4, 19.9, 5.6, "white"),           # JST-PH battery port, left
        (19.0, 13.0, 25.0, 19.9, 5.6, "white"),         # JST-PH battery port, right
        (11.4, 14.5, 14.0, 17.1, 0.8, "black"),         # MAX17048
        (8.0, 6.0, 17.4, 9.0, 1.2, "white"),            # STEMMA QT sockets (approx.)
    ])


def wire_unit():
    """1 mm of insulated 22 AWG wire lying on the board between two holes: bare legs into the holes at x = 0 and
    x = 1, insulation between; the footprint scales x by the link's length."""
    m = Model()
    m.box(0.0, -0.32, 1.0, 0.32, 0.25, 0.9, "silver")             # bare conductor along the whole length
    m.box(0.12, -0.7, 0.88, 0.7, 0.0, 1.4, "white")               # insulation (stripped ~3 mm at each end)
    for x in (0.0, 1.0):
        m.box(x - 0.03, -0.32, x + 0.03, 0.32, -1.8, 0.9, "silver")  # leg through the hole
    return m


def holder_18650():
    """MPD BH-18650-PC (about 77.6 x 20.4 x 21.3 mm, DigiKey) with a protected cell in it; origin = pad 1 (+), pad 2
    at x = 72.9 (stock footprint Battery:BatteryHolder_MPD_BH-18650-PC)."""
    m = Model()
    x0, x1, hw_ = -2.35, 75.25, 10.2
    m.box(x0, -hw_, x1, hw_, 0, 1.5, "black")                      # base
    for xa, xb in ((x0, x0 + 3.0), (x1 - 3.0, x1)):                # end walls with the contacts
        m.box(xa, -hw_, xb, hw_, 0, 21.3, "black")
    for ya, yb in ((-hw_, -hw_ + 1.5), (hw_ - 1.5, hw_)):          # side rails
        m.box(x0, ya, x1, yb, 0, 9.0, "black")
    m.cyl(0.0, 10.5, 9.3, x0 + 3.2, x1 - 3.2, "pcb_blue", axis="x")  # the cell (protected 18650, ~69 mm)
    m.cyl(0.0, 10.5, 2.5, x1 - 3.3, x1 - 3.1, "silver", axis="x")    # + button
    return m


def fuse_clips():
    """Two Keystone 3517 clips and a 5 x 20 mm fuse; pads at x 0 / 6.76 (clip 1) and 16.35 / 23.11 (clip 2)."""
    m = Model()
    for cx in (3.38, 19.73):
        m.box(cx - 3.5, -3.2, cx + 3.5, 3.2, 0, 1.0, "silver")
        for sy in (-1, 1):
            m.box(cx - 3.0, sy * 2.6 - 0.25, cx + 3.0, sy * 2.6 + 0.25, 0, 7.5, "silver")
    m.cyl(0.0, 6.2, 2.5, 1.56, 21.56, "glass", axis="x")
    for xa, xb in ((1.56, 6.5), (16.6, 21.56)):
        m.cyl(0.0, 6.2, 2.55, xa, xb, "silver", axis="x")
    return m


def test_loop():
    """Keystone 5010 (red) multipurpose test point, about 8 mm tall; origin = its pad."""
    m = Model()
    m.box(-1.2, -0.5, 1.2, 0.5, 0, 6.0, "red")
    m.box(-1.0, -0.3, 1.0, 0.3, 6.0, 8.4, "silver")
    return m


def do41_vertical():
    """P4KE10A TVS (DO-41) standing on its anode pad (pad 2, x = 3.81 mm), cathode band on top, the cathode lead bent
    over and down into pad 1 (x = 0): kicad-packages3D has no model for the 3.81 mm vertical footprint. ~7.2 mm tall."""
    m = Model()
    m.box(3.81 - 1.35, -1.35, 3.81 + 1.35, 1.35, 0.6, 4.8, "black")        # body (square stand-in for the 2.7 mm cylinder)
    m.box(3.81 - 1.36, -1.36, 3.81 + 1.36, 1.36, 4.8, 5.8, "marking")      # cathode band
    m.box(3.81 - 0.4, -0.4, 3.81 + 0.4, 0.4, 5.8, 7.2, "silver")           # lead up out of the band
    m.box(-0.4, -0.4, 3.81 + 0.4, 0.4, 6.4, 7.2, "silver")                 # over the top
    m.box(-0.4, -0.4, 0.4, 0.4, 0.0, 7.2, "silver")                        # down into pad 1
    m.box(3.81 - 0.4, -0.4, 3.81 + 0.4, 0.4, 0.0, 0.6, "silver")           # anode lead into pad 2
    return m


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn, mk, title in (("RevC_Pololu_U3V70F5.wrl", u3v70f5, "Pololu U3V70F5 on 2.54 mm headers (approximate)"),
                          ("RevC_Pololu_IdealDiode_5388.wrl", ideal_diode, "Pololu #5388 on headers (approximate)"),
                          ("RevC_Adafruit_MAX17048_5580.wrl", max17048, "Adafruit #5580 on headers (approximate)"),
                          ("RevC_WireLink_unit.wrl", wire_unit, "insulated wire link, 1 mm (scaled per link)"),
                          ("RevC_BatteryHolder_MPD_BH-18650-PC.wrl", holder_18650, "MPD BH-18650-PC + cell (approx.)"),
                          ("RevC_Fuseholder_Keystone_3517_5x20.wrl", fuse_clips, "2 x Keystone 3517 + 5x20 fuse"),
                          ("RevC_TestPoint_Keystone_5010.wrl", test_loop, "Keystone 5010 test point (approx.)"),
                          ("RevC_D_DO-41_P3.81mm_Vertical_CathodeUp.wrl", do41_vertical, "DO-41 standing (approx.)")):
        mk().write(os.path.join(OUT, fn), title)
