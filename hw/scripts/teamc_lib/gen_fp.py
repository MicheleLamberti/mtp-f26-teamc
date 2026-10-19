#!/usr/bin/env python3
"""Write teamc.pretty footprints (E01-ML01SP4, MAX17048 TDFN-8) as KiCad 10 text."""
import os
import sys
import uuid

OUT = sys.argv[1]
NS = uuid.UUID("a4c1e0f2-2b7d-4c59-8d4e-1f0c3b6e9a77")


def U(*k):
    return str(uuid.uuid5(NS, "/".join(map(str, k))))


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def line(fp, x1, y1, x2, y2, layer, w):
    return (f'\t(fp_line\n\t\t(start {f(x1)} {f(y1)})\n\t\t(end {f(x2)} {f(y2)})\n'
            f'\t\t(stroke\n\t\t\t(width {f(w)})\n\t\t\t(type solid)\n\t\t)\n\t\t(layer "{layer}")\n'
            f'\t\t(uuid "{U(fp, "l", x1, y1, x2, y2, layer)}")\n\t)\n')


def poly(fp, pts, layer, w, fill):
    p = " ".join(f"(xy {f(x)} {f(y)})" for x, y in pts)
    return (f'\t(fp_poly\n\t\t(pts\n\t\t\t{p}\n\t\t)\n\t\t(stroke\n\t\t\t(width {f(w)})\n\t\t\t(type solid)\n\t\t)\n'
            f'\t\t(fill {"yes" if fill else "no"})\n\t\t(layer "{layer}")\n\t\t(uuid "{U(fp, "p", p, layer)}")\n\t)\n')


def circle(fp, cx, cy, r, layer, w, fill):
    return (f'\t(fp_circle\n\t\t(center {f(cx)} {f(cy)})\n\t\t(end {f(cx + r)} {f(cy)})\n'
            f'\t\t(stroke\n\t\t\t(width {f(w)})\n\t\t\t(type solid)\n\t\t)\n\t\t(fill {"yes" if fill else "no"})\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{U(fp, "c", cx, cy, r, layer)}")\n\t)\n')


def text(fp, s, x, y, layer, size, th, rot=0, justify=None):
    j = f"\n\t\t\t(justify {justify})" if justify else ""
    return (f'\t(fp_text user "{s}"\n\t\t(at {f(x)} {f(y)} {f(rot)})\n\t\t(layer "{layer}")\n'
            f'\t\t(uuid "{U(fp, "t", s, x, y, layer)}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(size)} {f(size)})\n'
            f'\t\t\t\t(thickness {f(th)})\n\t\t\t){j}\n\t\t)\n\t)\n')


def prop(fp, name, val, x, y, layer, hide=False, size=1.0, th=0.15):
    h = "\n\t\t(hide yes)" if hide else ""
    unl = "\n\t\t(unlocked yes)" if name not in ("Reference", "Value") else ""
    return (f'\t(property "{name}" "{val}"\n\t\t(at {f(x)} {f(y)} 0){unl}\n\t\t(layer "{layer}"){h}\n'
            f'\t\t(uuid "{U(fp, "prop", name)}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(size)} {f(size)})\n'
            f'\t\t\t\t(thickness {f(th)})\n\t\t\t)\n\t\t)\n\t)\n')


def pad(fp, num, shape, x, y, w, h, layers, rr=None, extra=""):
    r = f"\n\t\t(roundrect_rratio {rr})" if rr is not None else ""
    lay = " ".join(f'"{l}"' for l in layers)
    return (f'\t(pad "{num}" smd {shape}\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(w)} {f(h)}){extra}\n'
            f'\t\t(layers {lay}){r}\n\t\t(uuid "{U(fp, "pad", num, x, y)}")\n\t)\n')


def header(name, descr, tags):
    return (f'(footprint "{name}"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n'
            f'\t(layer "F.Cu")\n\t(descr "{descr}")\n\t(tags "{tags}")\n')


# ---------------------------------------------------------------- E01-ML01SP4
def sp4():
    n = "E01-ML01SP4"
    descr = ("Ebyte E01-ML01SP4 nRF24L01P + PA/LNA 2.4 GHz module, castellated SMD 14.5x18.0 mm, IPEX; "
             "per Ebyte E01-ML01SP4 user manual rev 1.7 sect. 3 p.4 (pads 1-8 P1.27 on the short edge, "
             "GND 9/10 on the long edges 13.0 mm from the pad edge); hand-solder lands (signal pads 1.2 mm "
             "outside the outline); top-layer keep-out for tracks under the module (manual sect. 4.1)")
    tags = "Ebyte E01-ML01SP4 nRF24L01P nRF24L01+ PA LNA 2.4GHz castellated hand-solder"
    s = header(n, descr, tags)
    s += prop(n, "Reference", "REF**", 0, -11.6, "F.SilkS")
    s += prop(n, "Value", n, 0, 10.4, "F.Fab")
    s += prop(n, "Datasheet", "https://www.cdebyte.com/products/E01-ML01SP4", 0, 0, "F.Fab", hide=True, size=1.27)
    s += prop(n, "Description", "Ebyte nRF24L01P + PA/LNA 2.4 GHz module, SMD castellated 14.5x18 mm, IPEX",
              0, 0, "F.Fab", hide=True, size=1.27)
    s += "\t(attr smd)\n\t(duplicate_pad_numbers_are_jumpers no)\n"
    # F.Fab body with pin-1 chamfer (top-right)
    s += poly(n, [(-7.25, -9.0), (6.25, -9.0), (7.25, -8.0), (7.25, 9.0), (-7.25, 9.0)], "F.Fab", 0.1, False)
    s += circle(n, -4.9, 6.7, 1.0, "F.Fab", 0.1, False)
    s += text(n, "IPEX", -4.9, 8.25, "F.Fab", 0.5, 0.08)
    s += text(n, "${REFERENCE}", 0, 0, "F.Fab", 1.0, 0.15)
    # F.SilkS outline 0.15 mm outside the module, >= 0.2 mm from copper (line width 0.12)
    sx, sy = 7.40, 9.15
    s += line(n, -sx, -sy, -5.15, -sy, "F.SilkS", 0.12)
    s += line(n, 5.15, -sy, sx, -sy, "F.SilkS", 0.12)
    s += line(n, -sx, -sy, -sx, 2.94, "F.SilkS", 0.12)
    s += line(n, sx, -sy, sx, 2.94, "F.SilkS", 0.12)
    s += line(n, -sx, 5.06, -sx, sy, "F.SilkS", 0.12)
    s += line(n, sx, 5.06, sx, sy, "F.SilkS", 0.12)
    s += line(n, -sx, sy, sx, sy, "F.SilkS", 0.12)
    s += circle(n, 5.6, -10.0, 0.25, "F.SilkS", 0, True)          # pin-1 dot, right of pad 1
    s += text(n, "IPEX", -8.1, 7.0, "F.SilkS", 0.8, 0.12, rot=90)   # IPEX corner, outside the module
    # F.CrtYd
    cx, cy0, cy1 = 8.70, -10.45, 9.25
    s += line(n, -cx, cy0, cx, cy0, "F.CrtYd", 0.05)
    s += line(n, cx, cy0, cx, cy1, "F.CrtYd", 0.05)
    s += line(n, cx, cy1, -cx, cy1, "F.CrtYd", 0.05)
    s += line(n, -cx, cy1, -cx, cy0, "F.CrtYd", 0.05)
    # Cmts.User note
    s += text(n, "Ebyte manual rev1.7 p.4;\\nmeasure a module (14.5 mm) before fab;\\nIPEX position ±0.5 mm",
              0, -3.0, "Cmts.User", 0.45, 0.07)
    # pads
    lay = ["F.Cu", "F.Mask", "F.Paste"]
    for i in range(1, 9):
        x = 4.445 - (i - 1) * 1.27
        if i == 1:
            s += pad(n, i, "rect", x, -9.10, 0.80, 2.20, lay)
        else:
            s += pad(n, i, "roundrect", x, -9.10, 0.80, 2.20, lay, rr=0.25)
    s += pad(n, 9, "roundrect", -7.35, 4.00, 2.20, 1.60, lay, rr=0.25)
    s += pad(n, 10, "roundrect", 7.35, 4.00, 2.20, 1.60, lay, rr=0.25)
    # keep-out: no tracks on F.Cu under the module body
    s += (f'\t(zone\n\t\t(layer "F.Cu")\n\t\t(uuid "{U(n, "keepout")}")\n'
          '\t\t(name "SP4 no top tracks")\n\t\t(hatch edge 0.5)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n'
          '\t\t(min_thickness 0.25)\n\t\t(keepout\n\t\t\t(tracks not_allowed)\n'
          '\t\t\t(vias allowed)\n\t\t\t(pads allowed)\n\t\t\t(copperpour allowed)\n\t\t\t(footprints allowed)\n\t\t)\n'
          '\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)\n'
          '\t\t(fill\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t\t(island_removal_mode 0)\n\t\t)\n'
          '\t\t(polygon\n\t\t\t(pts\n\t\t\t\t(xy -7.25 -7.8) (xy 7.25 -7.8) (xy 7.25 9) (xy -7.25 9)\n\t\t\t)\n\t\t)\n\t)\n')
    s += "\t(embedded_fonts no)\n)\n"
    return n, s


# ---------------------------------------------------------------- MAX17048 TDFN-8
def max17048():
    n = "MAX17048_TDFN-8-1EP_2x2mm"
    descr = ("Maxim/ADI MAX17048 fuel gauge, TDFN-8-EP 2x2x0.75 mm (T822+3, outline 21-0168), land per 90-0065: "
             "pads 0.30x0.70 P0.5, rows 1.98 c-c, EP 0.8x1.38 (pad 9 = GND); pinout datasheet 19-6171 rev 7 p.6. "
             "Based on partreel.com max17048, CC-BY-4.0; EP paste split into 4 windows (~60 %)")
    tags = "MAX17048 MAX17049 fuel gauge TDFN-8 2x2 T822"
    s = header(n, descr, tags)
    s += prop(n, "Reference", "REF**", 0, -2.2, "F.SilkS")
    s += prop(n, "Value", n, 0, 2.2, "F.Fab", size=0.6, th=0.09)
    s += prop(n, "Datasheet", "https://cdn.sparkfun.com/assets/5/2/7/6/6/MAX17048-MAX17049.pdf", 0, 0, "F.Fab",
              hide=True, size=1.27)
    s += prop(n, "Description", "MAX17048 1-cell ModelGauge fuel gauge, I2C 0x36, TDFN-8-EP 2x2 mm", 0, 0, "F.Fab",
              hide=True, size=1.27)
    s += "\t(attr smd)\n\t(duplicate_pad_numbers_are_jumpers no)\n"
    s += poly(n, [(-0.5, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0), (-1.0, -0.5)], "F.Fab", 0.1, False)
    s += text(n, "${REFERENCE}", 0, 0, "F.Fab", 0.5, 0.08)
    s += line(n, -0.55, -1.17, 1.0, -1.17, "F.SilkS", 0.12)
    s += line(n, -1.0, 1.17, 1.0, 1.17, "F.SilkS", 0.12)
    s += poly(n, [(-0.99, -1.17), (-1.13, -1.36), (-0.85, -1.36)], "F.SilkS", 0.12, True)
    s += line(n, -1.6, -1.45, 1.6, -1.45, "F.CrtYd", 0.05)
    s += line(n, 1.6, -1.45, 1.6, 1.45, "F.CrtYd", 0.05)
    s += line(n, 1.6, 1.45, -1.6, 1.45, "F.CrtYd", 0.05)
    s += line(n, -1.6, 1.45, -1.6, -1.45, "F.CrtYd", 0.05)
    lay = ["F.Cu", "F.Mask", "F.Paste"]
    ys = [-0.75, -0.25, 0.25, 0.75]
    for i, y in enumerate(ys):           # 1-4 down the left side, 5-8 up the right side (CCW, top view)
        s += pad(n, i + 1, "roundrect", -0.99, y, 0.70, 0.30, lay, rr=0.25)
    for i, y in enumerate(reversed(ys)):
        s += pad(n, i + 5, "roundrect", 0.99, y, 0.70, 0.30, lay, rr=0.25)
    s += pad(n, 9, "rect", 0, 0, 0.80, 1.38, ["F.Cu", "F.Mask"], extra="\n\t\t(property pad_prop_heatsink)")
    s = s.replace('(property pad_prop_heatsink)\n\t\t(layers "F.Cu" "F.Mask")',
                  '(property pad_prop_heatsink)\n\t\t(layers "F.Cu" "F.Mask")\n\t\t(zone_connect 2)')
    for x in (-0.2, 0.2):
        for y in (-0.33, 0.33):
            s += pad(n, "", "roundrect", x, y, 0.32, 0.52, ["F.Paste"], rr=0.25)
    s += "\t(embedded_fonts no)\n)\n"
    return n, s


os.makedirs(OUT, exist_ok=True)
for name, txt in (sp4(), max17048()):
    with open(os.path.join(OUT, name + ".kicad_mod"), "w", encoding="utf-8") as fh:
        fh.write(txt)
    print("wrote", name)
