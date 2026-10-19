"""Route the Team C carrier with the grid router (run after place_carrier.py).

    python3 hw/scripts/route_carrier.py [--only power,radio]

Order: the power path first (short, wide), then SPI and the radio control lines, then everything else. GND is not
routed: it is the pour on both layers, tied together with stitching vias. Prints what could not be routed.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402
from gridroute import Router  # noqa: E402
from place_carrier import PCB, X0, X1, Y0, Y1  # noqa: E402

FINE_REFS = ["U2", "U5", "U6", "J2"]   # 0.5 mm pitch: TPS61022, TPS63001, MAX17048, USB-C
FINE_NETS = ["/power/SW_NODE", "/power/5V_BOOST", "/power/FB", "VBAT_SW", "VBAT", "/power/BB_OUT",
             "/power/BB_SW1", "/power/BB_SW2", "/power/BB_VINA", "FG_ALRT", "I2C_SCL", "I2C_SDA", "/power/CC1",
             "/power/CC2", "VBUS_USB"]
# SW_NODE is only the boost's copper area (place_carrier.BOOST_ZONES): not routed
POWER = [("/power/5V_BOOST", [1.0, 0.6, 0.4, 0.25]),
         ("5V_PI", [1.0, 0.6, 0.4]), ("/power/BAT_RAW", [1.5, 1.0, 0.6]), ("VBAT", [1.0, 0.6, 0.4, 0.25]),
         ("VBAT_SW", [1.0, 0.6, 0.4, 0.25]), ("/power/FB", [0.3, 0.25]), ("/power/LDO_OUT", [0.6, 0.4]),
         ("3V3_RADIO", [0.6, 0.4])]
RADIO = [(n, [0.4, 0.3]) for n in ("SPI_SCK", "/radio/SCK_R", "SPI_MOSI", "/radio/MOSI_R", "SPI_MISO",
                                    "/radio/MISO_R", "RADIO_CSN", "RADIO_CE", "RADIO_IRQ")]


def header_escapes(board):
    """Exact escape stubs for the used pins of the header's edge row (even pins), which the grid cannot thread:
    0.3 mm from the pad, 45 degrees into the gap between the two inner-row pads beside it, straight down past
    the inner row. 5V_PI: pins 2 and 4 joined by a 1.0 mm link, plus a 0.6 mm lane outside pin 2."""
    j1 = bu.fp(board, "J1")
    pads = {p.GetNumber(): p for p in j1.Pads()}
    xy = {n: (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for n, p in pads.items()}
    made = []
    for n in range(2, 41, 2):
        net = pads[str(n)].GetNetname()
        if net in ("", "GND") or net.startswith("unconnected-"):
            continue
        x, y = xy[str(n)]
        xi, yi = xy[str(n - 1)]                       # the inner-row pin beside it (same column)
        if net == "5V_PI":
            if n == 2:
                x4, _ = xy["4"]
                out = -1.0 if x4 > x else 1.0          # the side away from pin 4
                lane = x + out * 1.37
                bu.track(board, [(x, y), (x4, y)], 1.0, net)
                bu.track(board, [(x, y), (lane, y), (lane, yi + 1.85)], 0.6, net)
                made.append("J1.2/J1.4 5V_PI")
            continue
        x2, _ = xy[str(n + 1)] if str(n + 1) in xy else xy[str(n - 3)]
        gx = (xi + x2) / 2                            # middle of the gap between pins n-1 and n+1
        my = (y + yi) / 2
        bu.track(board, [(x, y), (gx, my), (gx, yi + 1.85)], 0.3, net)
        made.append(f"J1.{n} {net}")
    print("header escapes:", ", ".join(made))


def sp4_escapes(board, length=2.6):
    """Straight stubs up from the SP4's signal pads (pad row at the top), as on the breakout: at 1.27 mm pitch the
    grid router would otherwise box a pad in with its neighbours' tracks."""
    made = []
    for p in bu.fp(board, "U7").Pads():
        if p.GetNumber() in ("2", "3", "4", "5", "6", "7"):   # pad 1 (VCC) sits at the end of the row
            x, y = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
            bu.track(board, [(x, y), (x, y - length)], 0.4, p.GetNetname())
            made.append(p.GetNumber())
    print("SP4 escapes: pads", ",".join(made))


def boost_escapes(board):
    """EN (U2 pin 5) sits between GND (6) and FB (4) at 0.5 mm pitch: a 0.25 mm stub out to the right and up into
    the VBAT_SW copper area (0.25 mm from both neighbours; the FinePitch class asks for 0.15 mm)."""
    x, y = bu.pad_xy(board, "U2", 5)
    bu.track(board, [(x, y), (x + 0.95, y), (x + 0.95, y - 0.95)], 0.25, "VBAT_SW")
    # FB (pin 4, below EN): straight down out of the package, then right between U2 and C8
    x, y = bu.pad_xy(board, "U2", 4)
    bu.track(board, [(x, y), (x, 65.1), (x + 1.6, 65.1)], 0.25, "/power/FB")
    print("boost escapes: U2.5 EN -> VBAT_SW area, U2.4 FB -> right of the IC")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="power,radio,rest")
    ap.add_argument("--grid", type=float, default=0.05, help="router grid (mm)")
    ap.add_argument("--margin", type=float, default=0.04, help="extra clearance against rasterization error (mm)")
    a = ap.parse_args()
    groups = a.only.split(",")
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        board.Delete(t)
    header_escapes(board)
    sp4_escapes(board)
    boost_escapes(board)
    r = Router(board, X0, Y0, X1, Y1, grid=a.grid, margin=a.margin, fine_refs=FINE_REFS, fine_nets=FINE_NETS)
    plan = []
    if "power" in groups:
        plan += POWER
    if "radio" in groups:
        plan += RADIO
    if "rest" in groups:
        named = {n for n, _ in POWER + RADIO} | {"/power/SW_NODE"}
        others = sorted({p.GetNetname() for f in board.GetFootprints() for p in f.Pads()}
                        - named - {"", "GND"})
        plan += [(n, [0.4, 0.3, 0.25]) for n in others if not n.startswith("unconnected-")]
    report = []
    for net, widths in plan:
        t = time.time()
        done, failed = r.route_net(net, widths)
        report.append((net, done, failed))
        ws = sorted({w for w, _ in done})
        print(f"{net:22s} widths {ws} {'FAILED ' + ', '.join(failed) if failed else 'ok'} ({time.time() - t:.1f} s)",
              flush=True)
    n = r.stitch("GND", pitch=4.0)
    print("GND stitching vias:", n)
    bu.fill_zones(board)
    board.Save(PCB)
    bad = [(n, f) for n, _, f in report if f]
    print("UNROUTED:", bad if bad else "none")


if __name__ == "__main__":
    main()
