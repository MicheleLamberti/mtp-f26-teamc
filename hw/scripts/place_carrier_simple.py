"""Place carrier rev C ("simple", UPC lab) in hw/teamc-carrier-simple. Run after build_carrier_simple.py.

    python3 hw/scripts/place_carrier_simple.py

One copper layer (F.Cu). Every part is through-hole or a module: it sits on the back (B, the component side) and is
soldered on the copper side. Coordinates below are board mm seen from the copper side as KiCad shows F.Cu (origin =
top-left corner of the outline, x right, y down); on the component side everything is mirrored left-right.

THE BOX IS NOT MEASURED YET (Santiago, checkpoint 2): W, H, the holes, the slot and every position are in the tables
below, measured from the outline's top-left corner, so a new outline is a matter of editing W/H (and the rows near the
edges) and re-running place -> route -> finish -> fab. Defaults: board 120 x 66 mm for a 125 x 125 mm box floor with
the Pi (65 x 56) beside it.

Floorplan, copper-side view (the component side is the mirror image):
  top left     the SP4 breakout's socket J30; the breakout lies over the top-left 31 x 38 mm (H30 = its standoff);
               under it only low parts: the radio regulator U4 + C11/C12, the CSN pull-up R80 over the socket, the
               33 ohm SPI resistors R82-R84 upright in their lines (SCK passes between the legs of R84 and R83)
  middle       J1 (2x20 box header, ribbon to the Pi): pin 1 at the right end of the bottom (odd) row
  top band     the mode lead J12 with R57/R56, the UART header J13, U3 ideal diode over J1's right end (5 V down to
               pins 2/4); C9/C10 between U3 and U2 (TP2, the 5 V test loop, is at the radio regulator)
  right column U2 boost, upright: 5 V end at the top (to U3), cell end + ENABLE at the bottom; D1 left of its cell end
  band         under J1, left: the LED lead J14 + R60/R61 (inside the radio lines' loop); right: the fuel gauge U6, its
               header row right under J1's pins 1-5 (I2C straight down)
  bottom       the 18650 holder BT1 (+ at its right end); bottom right: F1 fuse clips, the GO/STOP and role leads
               J10/J11 + R54/R55, the charger lead J23, C1; right strip: the power toggle lead J22, R9, C18, TP1, TP3
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402

DIR = os.path.join(bu.HW, "teamc-carrier-simple")
PCB = os.path.join(DIR, "teamc-carrier-simple.kicad_pcb")
ORIGIN = (50.0, 50.0)
W, H = 120.0, 66.0                 # provisional outline (box inside dimensions still to measure)
# The SP4 breakout relative to its socket's pin 1 (hw/sp4-breakout; same numbers as place_carrier_lab.BREAKOUT):
# pins run along +u, the breakout's board spans u and w (w = the body side), its M3 hole H1 at h1
BREAKOUT = {"u": (-8.7, 22.3), "w": (-7.0, 30.5), "h1": (-4.205, 26.6)}
MOUNT = {"MH1": (3.5, 3.5), "MH2": (W - 3.5, H - 3.5), "MH3": (3.5, 39.5)}
MOUNT_KEEPOUT = 3.5                # no copper within this radius of an M3 hole (screw head, nylon standoff)
# cable-tie slot over the cell (centre x, y, length, width) and a notch at the bottom edge on its other side
STRAP_X = 41.0
SLOT = (STRAP_X, 42.0, 4.6, 2.0)
NOTCH = (STRAP_X, 4.6, 1.6)        # (centre x, width, depth from the bottom edge)

J30_P1 = (12.0, 7.0)               # socket horizontal, pins 1..8 to +x, breakout body to +y
J1_P1 = (89.0, 18.35)               # J1 pin 1 (right end of the bottom = odd row)
BT1_PLUS = (77.4, 54.8)            # holder + contact; - is 72.9 mm to the left


def k(x, y):
    """Board coordinates -> KiCad page coordinates."""
    return x + ORIGIN[0], y + ORIGIN[1]


def pads_at(board, ref):
    return {p.GetNumber(): bu.pad_xy(board, ref, p.GetNumber()) for p in bu.fp(board, ref).Pads() if p.GetNumber()}


def orient(board, ref, back, want):
    """First right-angle rotation whose pad positions satisfy want(pads: {num: (x, y)})."""
    for rot in (0, 90, 180, 270):
        bu.place(board, ref, 0, 0, rot, back)
        if want(pads_at(board, ref)):
            return rot
    raise SystemExit(f"no orientation for {ref}")


def put(board, ref, pad, x, y, want=None, rot=None):
    """Place ref (on the back) so that `pad` lands on board point (x, y); rotation from want() or given."""
    if rot is None:
        rot = orient(board, ref, True, want)
    bu.place(board, ref, 0, 0, rot, True)
    px, py = bu.pad_xy(board, ref, pad)
    kx, ky = k(x, y)
    bu.place(board, ref, kx - px, ky - py, rot, True)
    return rot


def tht(board, ref, x, y, rot=0):
    kx, ky = k(x, y)
    bu.place(board, ref, kx, ky, rot, True)


def left_of(a, b):
    return lambda p: p[a][0] < p[b][0] - 1e-3


def above(a, b):
    return lambda p: p[a][1] < p[b][1] - 1e-3


def both(*fs):
    return lambda p: all(f(p) for f in fs)


def j1_xy(pin):
    """Board position of J1 pin `pin` (pin 1 right end, odd row at J1_P1's y, even row 2.54 mm above)."""
    x = J1_P1[0] - (pin - 1) // 2 * 2.54
    return x, J1_P1[1] - (2.54 if pin % 2 == 0 else 0.0)


# 2-pin THT passives: (ref, pad 1 x, pad 1 y, orientation test). Resistors: 7.62 mm between the legs.
PASSIVES = [
    # radio corner, under the breakout (low parts only)
    ("R80", 14.54, 3.6, left_of("1", "2")),           # CSN pull-up over the socket: pad 1 (3V3) over pin 2
    ("C12", 14.6, 11.8, above("1", "2")),             # 3V3_RADIO (top) / GND at the regulator output
    ("C11", 10.5, 20.5, left_of("2", "1")),           # 5V_PI (pad 1, right) / GND at the regulator input
    ("R83", 24.0, 21.12, above("2", "1")),            # MOSI 33 ohm, upright: socket side (2) on top
    ("R84", 28.5, 21.12, above("2", "1")),            # MISO 33 ohm, upright
    ("R82", 31.5, 30.62, above("2", "1")),            # SCK 33 ohm, upright, lower: SCK_R then runs left between
                                                      # the legs of R84 and R83 to the socket's pin 5
    # 5 V at J1 pins 2/4, between U3 and U2
    ("C9", 98.5, 16.7, above("1", "2")),              # 100 uF, + on top
    ("C10", 101.3, 8.0, above("1", "2")),             # 100 nF
    # cell end of the boost
    ("D1", 100.6, 36.7, above("2", "1")),             # crowbar: anode (2) GND on top, cathode (1) VBAT at the bottom
    # bottom right, row C: the 1 k of GO/STOP and role, the 100 uF on VBAT
    ("R54", 89.92, 61.8, left_of("2", "1")),          # GO/STOP 1 k: GPIO side (2) left, lead side (1) right
    ("R55", 92.2, 61.8, left_of("1", "2")),           # role 1 k
    ("C1", 103.45, 62.0, left_of("1", "2")),          # 100 uF on VBAT, + left
    # right strip: power toggle
    ("R9", 118.3, 50.8, above("2", "1")),             # power toggle 1 k: ENABLE side (2) on top, lead side below
    ("C18", 112.0, 50.5, above("1", "2")),            # 100 nF on the toggle lead (1) / GND
    # band, left: LED resistors upright under J1 pins 29/31
    ("R60", 53.44, 25.0, above("1", "2")),            # LED_ACT (1) on top, LED_ACT_A below
    ("R61", 49.5, 25.0, above("1", "2")),             # LED_STATUS
    # top band: the mode inputs' 1 k
    ("R57", 33.55, 5.58, above("1", "2")),            # MRM 1 k, upright west of J1: its legs straddle CSN and IRQ
    ("R56", 57.68, 3.8, left_of("1", "2")),           # NM: lead side (1) left towards J12, GPIO side (2) right
]
TESTPOINTS = [("TP1", 110.3, 61.0), ("TP2", 9.0, 27.8), ("TP4", 13.2, 24.5), ("TP3", 116.8, 55.5)]


def place_all(board):
    # ---- J1: pin 1 at the right end of the odd row, the even row above it -------------------------------------
    put(board, "J1", "1", *J1_P1, both(left_of("39", "1"), above("2", "1")))
    # ---- radio --------------------------------------------------------------------------------------------------
    put(board, "J30", "1", *J30_P1, left_of("1", "8"))
    tht(board, "H30", J30_P1[0] + BREAKOUT["h1"][0], J30_P1[1] + BREAKOUT["h1"][1])
    put(board, "U4", "1", 7.0, 15.5, left_of("1", "3"))          # TO-92: GND, VIN, VOUT left to right
    # ---- power --------------------------------------------------------------------------------------------------
    # U2 upright in the right column: VOUT (pads 6/7) at the top towards U3, VIN/GND/EN (pads 1-5) at the bottom
    put(board, "U2", "6", 110.6, 5.6, lambda p: p["1"][1] - p["6"][1] > 20 and p["6"][0] < p["8"][0])
    # U3 in the top band over J1's right end: VOUT (5/6) left over J1 pins 2/4, VIN (1/2) right towards U2
    put(board, "U3", "5", 84.0, 2.2, lambda p: p["5"][0] < p["1"][0] - 5 and p["5"][1] < p["8"][1])
    # holder along the bottom, + at the right
    put(board, "BT1", "1", *BT1_PLUS, left_of("2", "1"))
    # fuse clips, row A over the bottom-right: BAT_IN (pads 1) at the left next to the holder's +, VBAT at the right
    put(board, "F1", "1", 82.4, 47.3, left_of("1", "2"))
    # fuel gauge in the band: header row on top under J1 pins 1-5 (VIN, GND, SCL, SDA, INT, QSTART left to right;
    # SCL right under J1 pin 5, SDA under pin 3)
    put(board, "U6", "3", j1_xy(5)[0] - 1.0, 25.2, lambda p: abs(p["1"][1] - p["6"][1]) < 0.1 and p["7"][1] > p["1"][1])
    # bottom right, row B: GO/STOP, role, charger leads
    put(board, "J10", "1", 84.2, 55.6, left_of("1", "2"))         # GO/STOP: lead (1), GND (2)
    put(board, "J11", "1", 92.7, 55.6, left_of("1", "2"))         # role
    put(board, "J23", "1", 101.2, 55.6, left_of("1", "2"))        # charger lead: BAT+ (1), BAT- (2)
    # right strip: power toggle lead
    put(board, "J22", "1", 113.6, 44.6, left_of("2", "1"))        # toggle (1) right, GND (2)
    # ---- Pi side ------------------------------------------------------------------------------------------------
    put(board, "J13", "1", 73.3, 4.3, left_of("3", "1"))          # UART: RX (3) left, TX, GND (1) right
    put(board, "J12", "1", 52.4, 4.3, left_of("3", "1"))          # mode lead: MRM (3) left, GND, NM (1) right
    put(board, "J14", "1", 45.0, 28.5, left_of("3", "1"))         # LEDs: GND (3) left, STATUS, ACT (1) right
    for ref, x, y, want in PASSIVES:
        put(board, ref, "1", x, y, want)
    for ref, x, y in TESTPOINTS:
        tht(board, ref, x, y)
    for ref, (x, y) in MOUNT.items():
        tht(board, ref, x, y)


def outline(board):
    """Board outline with the cable-tie slot and the notch at the bottom edge (Edge.Cuts)."""
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(bu.v(*k(*a)))
        s.SetEnd(bu.v(*k(*b)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(bu.MM(0.1))
        board.Add(s)
    nx, nw, nd = NOTCH
    pts = [(0, 0), (W, 0), (W, H), (nx + nw / 2, H), (nx + nw / 2, H - nd), (nx - nw / 2, H - nd),
           (nx - nw / 2, H), (0, H)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        seg(a, b)
    sx, sy, sw, sh = SLOT
    r = sh / 2
    seg((sx - sw / 2 + r, sy - r), (sx + sw / 2 - r, sy - r))
    seg((sx - sw / 2 + r, sy + r), (sx + sw / 2 - r, sy + r))
    for cx, start in ((sx + sw / 2 - r, (sx + sw / 2 - r, sy - r)), (sx - sw / 2 + r, (sx - sw / 2 + r, sy + r))):
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(bu.v(*k(cx, sy)))
        a.SetStart(bu.v(*k(*start)))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(180, pcbnew.DEGREES_T), True)
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(bu.MM(0.1))
        board.Add(a)


def breakout_outline(board):
    """The SP4 breakout's board on Dwgs.User: it lies ~11 mm above the component side; only low parts under it."""
    u0, u1 = BREAKOUT["u"]
    w0, w1 = BREAKOUT["w"]
    px, py = J30_P1
    xs, ys = (px + u0, px + u1), (py + w0, py + w1)
    corners = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[1], ys[1]), (xs[0], ys[1])]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(bu.v(*k(*a)))
        s.SetEnd(bu.v(*k(*b)))
        s.SetLayer(pcbnew.Dwgs_User)
        s.SetWidth(bu.MM(0.15))
        board.Add(s)
    bu.text(board, "SP4 breakout above (11 mm)", *k((xs[0] + xs[1]) / 2, ys[1] - 2.5), layer=pcbnew.Dwgs_User,
            size=1.0)


def main():
    board = pcbnew.LoadBoard(PCB)
    for item in list(board.GetTracks()) + list(board.Zones()) + list(board.GetDrawings()):
        board.Delete(item)
    outline(board)
    place_all(board)
    breakout_outline(board)
    board.Save(PCB)
    print(bu.run("kicad-cli", "pcb", "drc", "--severity-all", "-o", os.path.join(DIR, "build", "drc_place.rpt"),
                 PCB))


if __name__ == "__main__":
    main()
