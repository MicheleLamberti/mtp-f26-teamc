"""Drawing: where the SP4 breakout sits on carrier rev C (component-side view + side view).
Usage: breakout_drawing.py <repo> <out.png>"""
import os
import sys

import pcbnew
from PIL import Image, ImageDraw, ImageFont

repo, out = sys.argv[1], sys.argv[2]
T = pcbnew.ToMM
cb = pcbnew.LoadBoard(os.path.join(repo, "hw/teamc-carrier-simple/teamc-carrier-simple.kicad_pcb"))
br = pcbnew.LoadBoard(os.path.join(repo, "hw/sp4-breakout/sp4-breakout.kicad_pcb"))


def fp(b, ref):
    for f in b.GetFootprints():
        if f.GetReference() == ref:
            return f
    return None


def pads(f):
    return {p.GetNumber(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in f.Pads()}


def bbox(f, back):
    c = f.GetCourtyard(pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
    bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    return T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())


eb = cb.GetBoardEdgesBoundingBox()
X0, Y0, X1, Y1 = T(eb.GetLeft()), T(eb.GetTop()), T(eb.GetRight()), T(eb.GetBottom())
S, M = 9.0, 40          # px per mm, margin px
TOP = 150               # room above the board for the ribbon cable to the Pi
W = int((X1 - X0) * S) + 2 * M
H_TOP = int((Y1 - Y0) * S) + 2 * M + TOP
H = H_TOP + 330
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
except OSError:
    font = small = big = ImageFont.load_default()


def P(x, y):
    """KiCad page mm -> pixel, seen from the COMPONENT side (mirror x)."""
    return M + (X1 - x) * S, M + TOP + (y - Y0) * S


def rect(x1, y1, x2, y2, **kw):
    a, b = P(x1, y1), P(x2, y2)
    d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], **kw)


def label(x, y, text, f=font, fill="black"):
    px, py = P(x, y)
    w = d.textlength(text, font=f)
    d.text((px - w / 2, py - 8), text, fill=fill, font=f)


# carrier outline
rect(X0, Y0, X1, Y1, outline="#2e7d32", width=3, fill="#e8f5e9")
names = {"J1": "J1 40-pin to Pi", "U2": "U2 5V boost", "U3": "U3 ideal diode", "U6": "U6 battery level",
         "BT1": "BT1 18650 holder", "F1": "F1 fuse", "J13": "J13 UART"}
for ref, name in names.items():
    f = fp(cb, ref)
    if f:
        x1, y1, x2, y2 = bbox(f, f.IsFlipped())
        rect(x1, y1, x2, y2, outline="#555555", width=2, fill="#f5f5f5")
        label((x1 + x2) / 2, (y1 + y2) / 2, name, small)
for ref in ("MH1", "MH2", "MH3"):
    f = fp(cb, ref)
    if f:
        x, y = T(f.GetPosition().x), T(f.GetPosition().y)
        a, b = P(x - 1.6, y - 1.6), P(x + 1.6, y + 1.6)
        d.ellipse([min(a[0], b[0]), a[1], max(a[0], b[0]), b[1]], outline="#555555", width=2)

# breakout outline from its own board, mapped through J30 pin 1 (breakout pins point down into the socket;
# seen from the carrier's component side the breakout reads as its own top view)
j30, h30 = fp(cb, "J30"), fp(cb, "H30")
cj = pads(j30)
bj = pads(fp(br, "J1"))
beb = br.GetBoardEdgesBoundingBox()


def map_b(x, y):
    """breakout page mm -> carrier page mm (mirror in x, as the socket is on the back)."""
    return cj["1"][0] - (x - bj["1"][0]), cj["1"][1] + (y - bj["1"][1])


bx1, by1 = map_b(T(beb.GetLeft()), T(beb.GetTop()))
bx2, by2 = map_b(T(beb.GetRight()), T(beb.GetBottom()))
a, b = P(bx1, by1), P(bx2, by2)
box = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
d.rectangle(box, outline="#1565c0", width=4, fill="#e3f2fd")
u1 = fp(br, "U1")
ux1, uy1, ux2, uy2 = bbox(u1, False)
s1, s2 = map_b(ux1, uy1), map_b(ux2, uy2)
rect(s1[0], s1[1], s2[0], s2[1], outline="#0d47a1", width=2, fill="#bbdefb")
label((s1[0] + s2[0]) / 2, (s1[1] + s2[1]) / 2 - 2, "SP4 module", small, "#0d47a1")
label((s1[0] + s2[0]) / 2, (s1[1] + s2[1]) / 2 + 2, "(faces up)", small, "#0d47a1")
cx, cy = (box[0] + box[2]) / 2, box[1] - 14
t = "SP4 BREAKOUT (sits 11 mm above the carrier)"
d.text((box[2] - d.textlength(t, font=font), box[3] + 4), t, fill="#1565c0", font=font)

# socket J30 + pin numbers, standoff H30
names_j30 = {"1": "GND", "2": "3V3", "3": "CE", "4": "CSN", "5": "SCK", "6": "MOSI", "7": "MISO", "8": "IRQ"}
for n, (x, y) in cj.items():
    px, py = P(x, y)
    r = 9
    shape = d.rectangle if n == "1" else d.ellipse
    shape([px - r, py - r, px + r, py + r], outline="#b71c1c", width=3, fill="#ffcdd2")
    d.text((px - 4, py - 8), n, fill="#b71c1c", font=small)
    tw = d.textlength(names_j30[n], font=small)
    d.text((px - tw / 2, py + (12 if int(n) % 2 else 28)), names_j30[n], fill="#b71c1c", font=small)
px, py = P(*cj["1"])
d.text((min(P(*cj["1"])[0], P(*cj["8"])[0]) - 4, py - 34), "J30 socket (square = pin 1)", fill="#b71c1c", font=font)
hx, hy = T(h30.GetPosition().x), T(h30.GetPosition().y)
px, py = P(hx, hy)
d.ellipse([px - 14, py - 14, px + 14, py + 14], outline="#e65100", width=4, fill="#ffe0b2")
t = "H30: M3 standoff 11 mm"
d.text((px - d.textlength(t, font=font) - 20, py - 8), t, fill="#e65100", font=font)

# the breakout's own 1x2 bench-supply header J2 points DOWN like its J1: do not fit it on breakouts used in the box
for x, y in pads(fp(br, "J2")).values():
    px, py = P(*map_b(x, y))
    d.rectangle([px - 6, py - 6, px + 6, py + 6], fill="black")
t = "black squares = the breakout's J2 bench pins: DO NOT FIT J2 on breakouts used in the box"
d.text((box[2] - d.textlength(t, font=small), box[3] + 24), t, fill="black", font=small)

# the 40-wire ribbon to the Pi: female sockets at both ends, one pushes into J1 (the shrouded box header; the cable may be unkeyed),
# the other onto the Pi's 40 male pins; red wire = pin 1 at both ends
j1 = fp(cb, "J1")
jx1, jy1, jx2, jy2 = bbox(j1, True)
jp = pads(j1)
a, b = P(jx1, jy1), P(jx2, jy2)
rl, rr, jtop = min(a[0], b[0]) + 6, max(a[0], b[0]) - 6, min(a[1], b[1])
rtop = P(X0, Y0)[1] - 6                                   # the cable drawn above the board; it rises out of J1
d.rectangle([rl, M + 34, rr, rtop], fill="#cfd8dc", outline="#607d8b", width=2)
for i in range(1, 20):                                   # the ribbon's wires
    xx = rl + (rr - rl) * i / 20
    d.line([xx, M + 34, xx, rtop], fill="#90a4ae", width=1)
p1x = P(*jp["1"])[0]
red_x = rl if abs(p1x - rl) < abs(p1x - rr) else rr      # red wire on the pin-1 side
d.line([red_x, M + 34, red_x, rtop], fill="#d32f2f", width=5)
for xx in (rl, rr):                                      # dashed: the plug goes down into J1 (over U3 / J13)
    for yy in range(int(rtop), int(jtop), 12):
        d.line([xx, yy, xx, min(yy + 6, jtop)], fill="#607d8b", width=2)
for i, t in enumerate(("its plug pushes into J1 (dashed);", "the cable rises out of J1 and", "folds over U3 / J13 to the Pi")):
    d.text((M, rtop - 62 + i * 16), t, fill="#607d8b", font=small)
t = "40-wire ribbon cable, female-female, 20 cm  ->  Raspberry Pi 3 A+ (on the box floor beside the carrier)"
d.text(((rl + rr) / 2 - d.textlength(t, font=font) / 2, M + 12), t, fill="#37474f", font=font)
t = "marked (red/white) wire = pin 1 at BOTH ends - the plug may have no key: line it up, beep-check before power"
d.text(((rl + rr) / 2 - d.textlength(t, font=small) / 2, M + 34 + 8), t, fill="#b71c1c", font=small)
px, py = P(*jp["1"])
d.rectangle([px - 6, py - 6, px + 6, py + 6], outline="#d32f2f", width=3)
d.text((px + 10, py - 7), "J1 pin 1", fill="#d32f2f", font=small)

d.text((M, 8), "Carrier rev C, seen from the COMPONENT side (parts up)  -  where the SP4 breakout goes",
       fill="black", font=big)

# ---- side view --------------------------------------------------------------------------------------------
y0 = H_TOP + 30
d.text((M, y0), "Side view (not to scale in x)", fill="black", font=big)
base = y0 + 230
sx = M + 60
d.rectangle([sx, base, sx + 560, base + 14], fill="#a5d6a7", outline="#2e7d32", width=2)
d.text((sx + 570, base - 4), "carrier (copper side down)", fill="#2e7d32", font=font)
k = 12  # px per mm vertically
d.rectangle([sx + 40, base - 8.5 * k, sx + 70, base], fill="#424242")
d.text((M - 30, base - 5 * k), "J30 socket", fill="#424242", font=small)
d.text((M - 30, base - 5 * k + 14), "8.5 mm", fill="#424242", font=small)
d.rectangle([sx + 40, base - 11 * k, sx + 70, base - 8.5 * k], fill="#212121")
d.text((M - 30, base - 10.7 * k), "header", fill="#212121", font=small)
d.rectangle([sx + 20, base - 11 * k - 14, sx + 420, base - 11 * k], fill="#90caf9", outline="#1565c0", width=2)
d.rectangle([sx + 180, base - 11 * k - 30, sx + 330, base - 11 * k - 14], fill="#1565c0")
d.text((sx + 190, base - 11 * k - 52), "SP4 module (antenna cable to the box wall)", fill="#1565c0", font=small)
d.text((sx + 430, base - 11 * k - 12), "SP4 breakout board", fill="#1565c0", font=font)
d.rectangle([sx + 380, base - 11 * k, sx + 394, base], fill="#ffb74d", outline="#e65100")
d.text((sx + 400, base - 5 * k), "H30 M3 standoff ~11 mm", fill="#e65100", font=small)
d.rectangle([sx + 140, base - 7.3 * k, sx + 165, base], fill="#9e9e9e")
d.text((sx + 172, base - 4 * k), "parts under it <= 7.3 mm tall", fill="#616161", font=small)
img.save(out)
print("saved", out, img.size)
