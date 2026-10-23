"""Place carrier rev B for the UPC lab (hw/teamc-carrier-lab). Run after build_carrier_lab.py.

    python3 hw/scripts/place_carrier_lab.py

Single-sided board: copper on F.Cu only. Every through-hole part (modules, IDC box header, JST leads, socket, test
loops, wire links) sits on the back (B) and is soldered on the copper side; the SMD parts sit on the copper side,
where they may also go under a module body. Positions below are board coordinates (mm, origin = top-left corner of
the outline, y down); they are shifted by ORIGIN into KiCad's page.

Floorplan (seen from the copper side, as KiCad shows F.Cu):
  top right    power: U3 ideal diode at J1 pins 2/4, U2 boost below it (5 V end left, cell end right), J20 cell lead,
               F1/Q1/C5 under U2's cell end, J23 charger lead (on VBAT, above C5) and J22 power toggle;
  centre       J1 2x20 IDC box header, odd pins (left column) escape left, even pins (right column) escape right;
  top left     U6 fuel gauge, its header row facing J1 (SDA/SCL on J1 pins 3/5);
  left edge    J10 GO/STOP and J11 role leads between U6 and the breakout;
  bottom left  J30 socket for the SP4 breakout (the breakout lies over the carrier towards the bottom edge, its IPEX
               end at the edge; H30 = its M3 standoff), U4 radio LDO at J30 pins 1/2;
  bottom       J12 mode lead, J13 UART, LEDs.
The box (IKEA 365+, 15 x 15 x 7 cm outside) is not measured yet: OUTLINE is provisional (hw/REVB_LAB_PLAN.md).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402

DIR = os.path.join(bu.HW, "teamc-carrier-lab")
PCB = os.path.join(DIR, "teamc-carrier-lab.kicad_pcb")
ORIGIN = (50.0, 50.0)
W, H = 100.0, 80.0             # provisional outline (box inside dimensions still to measure)
BREAKOUT = {"u": (-8.7, 22.3), "w": (-7.0, 30.5), "h1": (-4.205, 26.6)}   # from hw/sp4-breakout, pin 1 = origin


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


def put(board, ref, pad, x, y, back, want=None, rot=None):
    """Place ref so that `pad` lands on board point (x, y); rotation from want() or given."""
    if rot is None:
        rot = orient(board, ref, back, want)
    bu.place(board, ref, 0, 0, rot, back)
    px, py = bu.pad_xy(board, ref, pad)
    kx, ky = k(x, y)
    bu.place(board, ref, kx - px, ky - py, rot, back)
    return rot


def smd(board, ref, x, y, rot=0):
    kx, ky = k(x, y)
    bu.place(board, ref, kx, ky, rot, False)


def tht(board, ref, x, y, rot=0):
    kx, ky = k(x, y)
    bu.place(board, ref, kx, ky, rot, True)


def first_left(a, b):
    return lambda p: p[a][0] < p[b][0] - 1e-3


def first_above(a, b):
    return lambda p: p[a][1] < p[b][1] - 1e-3


def vertical(a, b, side):
    """Pads a and b one above the other, b below a (side = +1) or above it (side = -1)."""
    return lambda p: abs(p[a][0] - p[b][0]) < 1e-3 and (p[b][1] - p[a][1]) * side > 0


def both(*fs):
    return lambda p: all(f(p) for f in fs)


# J1 pin 1 (board coordinates). On the back the header is mirrored: with the odd column on the left, pin 1 is at
# the bottom and the pins run up.
J1_P1 = (46.0, 70.0)
# J30 pin 1: socket horizontal along the top edge, pins 1..8 to the RIGHT; the breakout body then extends down over
# the board (its handedness on the back), so CE/MOSI/MISO land on the socket straight from J1's left column
J30_P1 = (12.0, 7.5)
# UI leads on the left edge (board coordinates). Per row: (line, lead connector, row y = the lead's signal pin,
# TVS, its x, side of its GND pad (-1 north, +1 south), 1 k series, 100 nF, side of its GND pad). Nothing runs up
# the left edge (no pull-ups in rev B), so the pour between the rows reaches round the connectors.
LEAD_X, SER_X, CAP_X = 3.5, 16.0, 21.5
UI_ROWS = [
    ("SW_MODE_NM", "J12", 42.0, "D14", 8.5, +1, "R56", "C52", +1),
    ("SW_MODE_MRM", "J12", 47.0, "D15", 11.5, -1, "R57", "C53", +1),
    ("SW_ROLE", "J11", 55.0, "D13", 8.5, +1, "R55", "C51", -1),
    ("BTN_TXRX", "J10", 63.5, "D12", 8.5, +1, "R54", "C50", +1),
]
# M3 holes to the box (board coordinates); copper keeps MOUNT_KEEPOUT mm from their centres
MOUNT = {"MH1": (3.5, 76.5), "MH2": (96.5, 76.5), "MH3": (96.5, 3.5), "MH4": (3.5, 3.5)}   # MH4 under the breakout
MOUNT_KEEPOUT = 3.2


def place_all(board):
    # ---- connectors and modules (back side) -------------------------------------------------------------------
    put(board, "J1", "1", *J1_P1, True, both(first_left("1", "2"), first_above("3", "1")))
    jx, jy = J1_P1
    row = lambda p: jy - (p - 1) // 2 * 2.54   # noqa: E731  y of J1 pin p
    # UART straight out of J1 pins 6/8/10 (GND, TX, RX)
    put(board, "J13", "1", jx + 8.5, row(6), True, first_above("3", "1"))
    # ideal diode right of J13: 5V_PI pads 5/6 level with J1 pins 2/4, 5V_BOOST pads 1/2 facing U2
    put(board, "U3", "5", 63.0, row(4), True, first_left("5", "1"))
    # boost upright: 5 V end (pads 6-9) at the bottom next to U3, cell end (pads 1-5: VBAT VBAT GND GND EN from the
    # right) at the top. Its ground reaches the cell end from below (a trunk under the module), so VBAT can leave
    # above the cell end to the left.
    put(board, "U2", "6", 80.0, 53.0, True, lambda p: p["6"][1] - p["1"][1] > 20)
    # cell lead in the right-edge column: BAT_IN up through F1/Q1, GND left to the trunk
    put(board, "J20", "1", 96.0, 47.0, True, first_left("2", "1"))
    # charger lead on VBAT, behind F1/Q1 (review 23-Oct: a reversed cell must not reach the TP4056): in the gap
    # between the VBAT line and C5, VBAT pin under the line, GND pin to C5's ground pad. Power toggle left of U2's EN
    put(board, "J23", "1", 95.5, 20.0, True, first_left("2", "1"))
    put(board, "J22", "1", 57.0, 23.0, True, first_left("1", "2"))
    # fuel gauge bottom left, header row facing J1 (SDA/SCL level with J1 pins 3/5)
    put(board, "U6", "4", jx - 10.0, row(3), True,
        lambda p: abs(p["1"][0] - p["6"][0]) < 0.1 and p["7"][0] < p["1"][0])
    # breakout socket top left (see the module docstring)
    put(board, "J30", "1", *J30_P1, True, first_left("1", "8"))
    tht(board, "H30", J30_P1[0] + BREAKOUT["h1"][0], J30_P1[1] + BREAKOUT["h1"][1])
    # panel leads on the left edge below the breakout: mode (NM, GND, MRM), role, GO/STOP
    for line, jref, ry, *_ in UI_ROWS:
        if jref != "J12" or line == "SW_MODE_NM":
            put(board, jref, "1", LEAD_X, ry, True, first_above("1", "3" if jref == "J12" else "2"))
    for ref, x, y in (("TP1", 94.0, 11.0), ("TP3", 90.0, 64.0)):
        tht(board, ref, x, y)
    for ref, (x, y) in MOUNT.items():
        tht(board, ref, x, y)

    # ---- SMD (copper side) --------------------------------------------------------------------------------------
    # 5V_PI at J1 pins 2/4: TVS and 100 nF at the header, 100 uF between it and U3
    smd(board, "D2", 52.0, 73.5, 270)
    smd(board, "C10", 55.5, 73.5, 270)
    smd(board, "C9", 68.0, 70.0, 270)
    # cell path in the right-edge column: J20 -> F1 -> Q1 (drain down, source up) -> VBAT riser along the edge
    smd(board, "F1", 96.0, 42.0, 90)
    smd(board, "Q1", 95.5, 37.0, 180)
    smd(board, "R1", 98.6, 41.5, 270)
    # bulk + TVS between the VBAT riser and the ground trunk under U2
    smd(board, "C5", 91.0, 27.0, 180)
    smd(board, "D3", 91.0, 32.0, 180)
    # power toggle -> 2N7002 -> boost EN, left of U2's cell end, under the VBAT line
    smd(board, "R8", 68.0, 17.3, 270)
    smd(board, "R9", 63.5, 19.0, 0)
    smd(board, "C18", 65.5, 23.0, 270)
    smd(board, "Q2", 70.0, 21.5, 0)
    # radio LDO at J30 pins 1/2
    smd(board, "U4", 11.0, 14.0, 0)
    put(board, "C11", "1", 6.5, 11.0, False, vertical("1", "2", +1))   # VBAT on top, GND level with U4's GND
    smd(board, "C12", 15.0, 14.0, 270)     # 3V3_RADIO on top (to socket pin 2), GND below
    # radio: series R at the driver ends (R82/R83 at J1, R84 at J30), pull-ups at J30
    # SCK swaps under R84 (MISO) and R83 (MOSI): it drops south between their pads, so the lanes leave J1 in
    # the socket's order (MISO_R, MOSI_R, SCK_R, CE from north to south = CE, SCK, MOSI, MISO from west to east)
    smd(board, "R84", 40.0, row(21), 180)
    smd(board, "R83", 40.0, row(19), 180)
    smd(board, "R82", 34.0, row(19) + 1.6, 180)
    # CSN pull-up to 3V3_RADIO north of the socket between pins 2 and 4
    smd(board, "R80", 17.0, 3.2, 0)
    # UI rows beside the leads (see UI_ROWS): lead pin -> TVS on the _J node -> 1 k along the row -> 100 nF at the
    # GPIO end
    for line, jref, ry, tvs, tvs_x, tvs_side, ser, cap, cap_side in UI_ROWS:
        put(board, tvs, "1", tvs_x, ry, False, vertical("1", "2", tvs_side))
        put(board, ser, "1", SER_X, ry, False, first_left("1", "2"))
        put(board, cap, "1", CAP_X + (3.0 if line == "SW_ROLE" else 0.0), ry, False, vertical("1", "2", cap_side))
    # LEDs left of J1's top (pins 29/31)
    smd(board, "R60", 40.0, row(29), 0)
    smd(board, "D10", 34.5, row(29), 0)
    smd(board, "R61", 40.0, row(31) - 3.0, 0)
    smd(board, "D11", 34.5, row(31) - 3.0, 0)


def breakout_outline(board):
    """The SP4 breakout's board on Dwgs.User: it lies ~11 mm above the back side, keep tall parts out from under it."""
    u0, u1 = BREAKOUT["u"]
    w0, w1 = BREAKOUT["w"]
    px, py = J30_P1
    # pins run to +x, the body extends to +y (see the module docstring)
    xs = sorted((px + u0, px + u1))
    ys = sorted((py + w0, py + w1))
    for (x1, y1), (x2, y2) in (((xs[0], ys[0]), (xs[1], ys[0])), ((xs[1], ys[0]), (xs[1], ys[1])),
                               ((xs[1], ys[1]), (xs[0], ys[1])), ((xs[0], ys[1]), (xs[0], ys[0]))):
        sh = pcbnew.PCB_SHAPE(board)
        sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
        sh.SetStart(bu.v(*k(x1, y1)))
        sh.SetEnd(bu.v(*k(x2, y2)))
        sh.SetLayer(pcbnew.Dwgs_User)
        sh.SetWidth(bu.MM(0.15))
        board.Add(sh)
    bu.text(board, "SP4 breakout above (IPEX end)", *k((xs[0] + xs[1]) / 2, ys[1] - 3), layer=pcbnew.Dwgs_User,
            size=1.0)


def main():
    board = pcbnew.LoadBoard(PCB)
    for item in list(board.GetTracks()) + list(board.Zones()) + list(board.GetDrawings()):
        board.Delete(item)
    bu.outline_rect(board, *k(0, 0), *k(W, H), r=2.0)
    place_all(board)
    breakout_outline(board)
    board.Save(PCB)
    print(bu.run("kicad-cli", "pcb", "drc", "--severity-all", "-o", os.path.join(DIR, "build", "drc_place.rpt"),
                 PCB))


if __name__ == "__main__":
    main()
