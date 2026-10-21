#!/usr/bin/env python3
"""Write the teamc.3dshapes VRML 2.0 models (simple, hand-built meshes for renders; not for mechanical CAD).

    python3 hw/scripts/teamc_lib/gen_3d.py [output .3dshapes folder]

Models (origin = footprint origin, +x right, +y up = KiCad -y, +z up from the board surface; KiCad's VRML convention
is 1 unit = 0.1 inch = 2.54 mm, so every coordinate is written in mm / 2.54):
  E01-ML01SP4.wrl                 Ebyte E01-ML01SP4 (14.5 x 18 mm, shield can, castellations, IPEX), on teamc:E01-ML01SP4
  MAX17048_TDFN-8-1EP_2x2mm.wrl   TDFN-8 2 x 2 x 0.75 mm, on teamc:MAX17048_TDFN-8-1EP_2x2mm
  JST_VH_B2P-VH_1x02_P3.96mm_Vertical.wrl
                                  stand-in for the stock footprint's model, which kicad-packages3D does not have
  RPi3_Aplus_simplified.wrl       Raspberry Pi 3 Model A+, approximate (positions from the official 65 x 56 mm
                                  mechanical drawing), origin = GPIO header pin 1, z = 0 at the Pi's top copper.
                                  For context renders only (hw/scripts/render_board.py --with-pi).
"""
import math
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                                         "lib", "teamc.3dshapes")
S = 1 / 2.54  # mm -> VRML unit

# name: (diffuse, specular, shininess, transparency)
MATS = {
    "pcb_blue": ((0.05, 0.12, 0.42), (0.10, 0.10, 0.15), 0.15, 0),
    "pcb_green": ((0.04, 0.36, 0.14), (0.10, 0.15, 0.10), 0.15, 0),
    "shield": ((0.55, 0.56, 0.58), (0.70, 0.70, 0.72), 0.50, 0),
    "gold": ((0.82, 0.62, 0.20), (0.75, 0.65, 0.35), 0.50, 0),
    "silver": ((0.62, 0.62, 0.64), (0.80, 0.80, 0.80), 0.55, 0),
    "black": ((0.07, 0.07, 0.08), (0.20, 0.20, 0.20), 0.25, 0),
    "dark": ((0.02, 0.02, 0.02), (0.05, 0.05, 0.05), 0.05, 0),
    "marking": ((0.70, 0.70, 0.68), (0.10, 0.10, 0.10), 0.10, 0),
    "white": ((0.90, 0.88, 0.82), (0.20, 0.20, 0.20), 0.20, 0),
    "ivory": ((0.92, 0.88, 0.76), (0.15, 0.15, 0.15), 0.15, 0),
    "brown": ((0.35, 0.20, 0.08), (0.10, 0.10, 0.10), 0.15, 0),
}


# ------------------------------------------------------------------ tiny mesh writer
def _area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def _earclip(pts):
    """Triangulate a simple CCW polygon; returns index triples."""
    idx = list(range(len(pts)))
    tris = []

    def inside(p, a, b, c):
        def s(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
        return not ((d1 < -1e-12 or d2 < -1e-12 or d3 < -1e-12) and (d1 > 1e-12 or d2 > 1e-12 or d3 > 1e-12))

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 1e-12:
                continue  # reflex or degenerate
            if any(inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


class Model:
    def __init__(self):
        self.parts = {}  # material -> (points, triangles)

    def _add(self, mat, verts, tris):
        p, t = self.parts.setdefault(mat, ([], []))
        o = len(p)
        p.extend(verts)
        t.extend((a + o, b + o, c + o) for a, b, c in tris)

    def prism(self, poly, w0, w1, mat, axis="z"):
        """Extrude polygon `poly` [(u, v)] (mm) from w0 to w1 along `axis` (z: (u,v,w)=(x,y,z); x: (y,z,x); y: (z,x,y))."""
        if _area(poly) < 0:
            poly = poly[::-1]
        n = len(poly)

        def m(u, v, w):
            return {"z": (u, v, w), "x": (w, u, v), "y": (v, w, u)}[axis]

        verts = [m(u, v, w0) for u, v in poly] + [m(u, v, w1) for u, v in poly]
        tris = []
        for a, b, c in _earclip(poly):
            tris.append((a + n, b + n, c + n))      # top, CCW from +w
            tris.append((a, c, b))                  # bottom, reversed
        for i in range(n):
            j = (i + 1) % n
            tris += [(i, j, j + n), (i, j + n, i + n)]
        self._add(mat, verts, tris)

    def box(self, x0, y0, x1, y1, z0, z1, mat):
        self.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat)

    def boxc(self, cx, cy, w, h, z0, z1, mat):
        self.box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, z0, z1, mat)

    def cyl(self, cu, cv, r, w0, w1, mat, axis="z", n=28):
        self.prism([(cu + r * math.cos(2 * math.pi * k / n), cv + r * math.sin(2 * math.pi * k / n))
                    for k in range(n)], w0, w1, mat, axis)

    def write(self, path, title):
        out = [f"#VRML V2.0 utf8\n# {title}\n# generated by hw/scripts/teamc_lib/gen_3d.py; units 1 = 2.54 mm (KiCad)\n"]
        for mat, (pts, tris) in self.parts.items():
            d, s, sh, tr = MATS[mat]
            ps = ",\n".join(f"{x * S:.5f} {y * S:.5f} {z * S:.5f}" for x, y, z in pts)
            ts = ",\n".join(f"{a},{b},{c},-1" for a, b, c in tris)
            out.append(
                f"Shape {{\n appearance Appearance {{ material DEF M_{mat} Material {{\n"
                f"  diffuseColor {d[0]} {d[1]} {d[2]}\n  specularColor {s[0]} {s[1]} {s[2]}\n"
                f"  emissiveColor 0 0 0\n  ambientIntensity 0.3\n  shininess {sh}\n  transparency {tr}\n }} }}\n"
                f" geometry IndexedFaceSet {{\n  solid FALSE\n  creaseAngle 0.6\n"
                f"  coord Coordinate {{ point [\n{ps}\n  ] }}\n  coordIndex [\n{ts}\n  ]\n }}\n}}\n")
        with open(path, "w", encoding="ascii") as fh:
            fh.write("".join(out))
        print("wrote", path, f"({os.path.getsize(path) // 1024} kB)")


def rrect(x0, y0, x1, y1, r, n=8):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ------------------------------------------------------------------ E01-ML01SP4
def sp4():
    """Footprint (KiCad y down): body x -7.25..7.25, y -9..9, pin-1 chamfer top right, pads 1-8 at y = -9 (x 4.445 ..
    -4.445, P1.27), GND 9/10 on the long edges at y = +4, IPEX centre (-4.9, 6.7). Here y is flipped (VRML up)."""
    m = Model()
    t = 0.8                                   # PCB
    m.prism([(-7.25, -9), (7.25, -9), (7.25, 8), (6.25, 9), (-7.25, 9)], 0, t, "pcb_blue")
    # castellations: gold half-pads on the top face + the plated half-hole walls on the edge
    for i in range(8):
        x = 4.445 - 1.27 * i
        m.box(x - 0.35, 8.0, x + 0.35, 9.0, t, t + 0.03, "gold")
        m.box(x - 0.35, 8.98, x + 0.35, 9.02, 0, t, "gold")
    for sx in (-1, 1):
        m.box(sx * 7.25 - 0.6 * sx, -4.6, sx * 7.25, -3.4, t, t + 0.03, "gold")
        m.box(sx * 7.25 - 0.02, -4.5, sx * 7.25 + 0.02, -3.5, 0, t, "gold")
    # shield can: everything but the pad strip (y > 7.4) and the IPEX corner (x < -2.6, y < -4.2)
    sh = [(-2.6, -8.7), (6.95, -8.7), (6.95, 7.4), (-6.95, 7.4), (-6.95, -4.2), (-2.6, -4.2)]
    m.prism(sh, t, t + 1.95, "shield")
    m.prism([(-2.45, -8.55), (6.8, -8.55), (6.8, 7.25), (-6.8, 7.25), (-6.8, -4.35), (-2.45, -4.35)],
            t + 1.95, t + 2.0, "shield")
    # a few visible parts outside the can: PA/LNA matching parts near the IPEX
    for x, y in ((-6.3, -5.2), (-6.3, -6.0), (-1.8, -6.2), (-1.8, -7.4)):
        m.boxc(x, y, 0.5, 0.9, t, t + 0.35, "black")
    # IPEX / U.FL receptacle: square base + round body + centre pin
    cx, cy = -4.9, -6.7
    m.boxc(cx, cy, 2.6, 2.6, t, t + 0.2, "gold")
    m.cyl(cx, cy, 1.0, t + 0.2, t + 1.25, "silver")
    m.cyl(cx, cy, 0.75, t + 1.25, t + 1.26, "dark")
    m.cyl(cx, cy, 0.22, t + 0.2, t + 1.1, "gold")
    return m


# ------------------------------------------------------------------ MAX17048 TDFN-8 2x2
def max17048():
    """Pads 1-4 down the left side (x = -0.99, KiCad y -0.75..0.75), 5-8 up the right; pin 1 top left."""
    m = Model()
    m.box(-1.0, -1.0, 1.0, 1.0, 0.02, 0.75, "black")
    for i, y in enumerate((0.75, 0.25, -0.25, -0.75)):
        for sx in (-1, 1):
            m.box(sx * 1.0 - (0.35 if sx > 0 else 0), y - 0.125, sx * 1.0 + (0.35 if sx < 0 else 0), y + 0.125,
                  0, 0.2, "silver")
    m.box(-0.4, -0.69, 0.4, 0.69, 0, 0.02, "silver")
    m.cyl(-0.55, 0.55, 0.15, 0.75, 0.76, "marking", n=16)
    return m


# ------------------------------------------------------------------ JST VH 2-pin vertical
def jst_vh2():
    """Stock footprint fab: body x -1.95..5.91, KiCad y -2..4.8, latch -0.75..4.71 / -3.7..-2; pins at (0,0), (3.96,0).
    Height ~9.6 mm (approximate)."""
    m = Model()
    m.box(-1.95, -4.8, 5.91, 2.0, 0, 9.6, "ivory")
    m.box(-0.75, 2.0, 4.71, 3.7, 0, 6.5, "ivory")
    for x in (0, 3.96):
        m.box(x - 1.45, -3.9, x + 1.45, 1.2, 9.0, 9.61, "dark")          # cavity opening
        m.box(x - 0.55, -0.55, x + 0.55, 0.55, 2.0, 9.62, "silver")      # pin tab
        m.box(x - 0.55, -0.55, x + 0.55, 0.55, -3.4, 0, "silver")        # tail under the board
    return m


# ------------------------------------------------------------------ Raspberry Pi 3 Model A+
def rpi3a():
    """Drawing coordinates X from the left edge, Y from the bottom edge (top view, GPIO header on the top edge,
    USB-A on the right edge, power/HDMI/audio on the bottom edge). Model origin = header pin 1 (X 8.37, Y 51.23)."""
    m = Model()
    ox, oy = 8.37, 56 - 4.77

    def B(x0, y0, x1, y1, z0, z1, mat):
        m.box(x0 - ox, y0 - oy, x1 - ox, y1 - oy, z0, z1, mat)

    def C(x, y, r, z0, z1, mat, n=28):
        m.cyl(x - ox, y - oy, r, z0, z1, mat, n=n)

    t = 1.6
    m.prism([(x - ox, y - oy) for x, y in rrect(0, 0, 65, 56, 3)], -t, 0, "pcb_green")
    for x, y in ((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)):
        for z0, z1 in ((0, 0.03), (-t - 0.03, -t)):
            C(x, y, 3.0, z0, z1, "gold")
        C(x, y, 1.375, -t - 0.05, 0.05, "dark")
    # GPIO header: 2.5 mm black body, square posts 8.5 mm above the board and 3 mm below
    B(7.1, 49.96, 57.9, 55.04, 0, 2.5, "black")
    for i in range(20):
        for y in (51.23, 53.77):
            x = 8.37 + 2.54 * i
            B(x - 0.32, y - 0.32, x + 0.32, y + 0.32, -t - 3.0, 8.5, "gold")
    # SoC (BCM2837B0, metal heat spreader on a substrate)
    B(19, 25, 33, 39, 0, 0.9, "pcb_green")
    B(19.6, 25.6, 32.4, 38.4, 0.9, 1.45, "silver")
    # wireless shield can (CYW43455) + PCB antenna area at the top-left corner
    B(8.5, 35.5, 18.5, 46.5, 0, 1.3, "shield")
    B(1.0, 42, 6.5, 47, 0, 0.6, "white")
    # PMIC + small parts
    B(36, 30, 41, 35, 0, 0.9, "black")
    B(13, 14, 19, 20, 0, 0.9, "black")
    for x, y in ((40, 44), (44, 40), (47, 30), (16, 30), (25, 18), (37, 42)):
        B(x, y, x + 1.6, y + 0.8, 0, 0.5, "black")
    # DSI (left edge) and CSI (between HDMI and audio) FFC connectors
    B(1.3, 16, 5.3, 38, 0, 5.5, "white")
    B(1.0, 16, 5.6, 38, 4.6, 5.6, "brown")
    B(43.4, 1.0, 47.4, 23, 0, 5.5, "white")
    B(43.1, 1.0, 47.7, 23, 4.6, 5.6, "brown")
    # micro-USB power, HDMI, 3.5 mm jack on the bottom edge
    B(6.6, -1.0, 14.6, 4.6, 0, 3.0, "silver")
    B(7.3, -1.01, 13.9, 0.0, 0.6, 2.4, "dark")
    B(24.5, -1.0, 39.5, 10.5, 0, 6.5, "silver")
    B(25.6, -1.01, 38.4, 0.0, 1.2, 5.4, "dark")
    B(50.5, 0.0, 56.5, 12.0, 0, 6.0, "black")
    m.cyl(3.0, 53.5 - ox, 2.5, -2.5 - oy, 0.0 - oy, "black", axis="y")
    m.cyl(3.0, 53.5 - ox, 1.75, -2.51 - oy, -2.4 - oy, "dark", axis="y")
    # USB-A receptacle on the right edge, overhanging ~2.5 mm
    B(53.5, 24.9, 67.5, 38.0, 0, 7.0, "silver")
    B(67.5, 26.0, 67.51, 36.9, 1.0, 6.0, "dark")
    B(67.0, 27.0, 67.52, 35.9, 2.5, 4.4, "white")
    # microSD socket + card on the underside, card sticking out of the left edge
    B(0.5, 21.5, 14.5, 34.5, -t - 1.45, -t, "silver")
    B(-2.5, 22.5, 1.0, 33.5, -t - 1.2, -t - 0.4, "black")
    return m


os.makedirs(OUT, exist_ok=True)
for fn, mk, title in (("E01-ML01SP4.wrl", sp4, "Ebyte E01-ML01SP4 (simplified)"),
                      ("MAX17048_TDFN-8-1EP_2x2mm.wrl", max17048, "MAX17048 TDFN-8-1EP 2x2x0.75 mm"),
                      ("JST_VH_B2P-VH_1x02_P3.96mm_Vertical.wrl", jst_vh2, "JST VH B2P-VH (approximate)"),
                      ("RPi3_Aplus_simplified.wrl", rpi3a, "Raspberry Pi 3 Model A+ (simplified, approximate)")):
    mk().write(os.path.join(OUT, fn), title)
