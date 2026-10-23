"""Route carrier rev C ("simple", UPC lab) on ONE copper layer (F.Cu). Run after place_carrier_simple.py.

    python3 hw/scripts/route_carrier_simple.py            # route, write links.json, report
    python3 hw/scripts/route_carrier_simple.py --grid 0.2 # faster draft

1. The backbone is hand-routed (backbone()): every net whose way across the board is decided by J1's pin order, with
   the coordinates in board mm (copper-side view, see place_carrier_simple.py). Where one copper layer cannot avoid a
   crossing it uses, in this order: a track passing between the two legs of a through-hole resistor that is in the
   other net anyway (SCK under R84/R83, LED_ACT_A under R61, CSN and IRQ under R57, ROLE under R54/R55), or a wire
   link (an insulated wire on the component side between two unplated holes: here only IRQ over CSN).
2. linkroute.LinkRouter connects what is left (short local branches) on F.Cu, with a wire link only if it must.
GND is not routed here: it is the copper pour (finish_carrier_simple.py). The links go to links.json and become
parts W1, W2, ... in finish_carrier_simple.py.
"""
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402
from linkroute import LinkRouter  # noqa: E402
from place_carrier_simple import DIR, H, MOUNT, MOUNT_KEEPOUT, ORIGIN, PCB, W, k, j1_xy  # noqa: E402

LINKS = os.path.join(DIR, "links.json")
SIG = 0.8
PW = 2.0           # cell path, VBAT trunk, 5 V from the boost
P5 = 1.5           # 5 V to the Pi
LINK_D, LINK_DRILL = 2.0, 1.0


def hand_links(board, net, a, b):
    """A wire link from a to b (board mm): two unplated holes and the wire, as linkroute makes them (a via pair +
    a B.Cu track); finish_carrier_simple.py turns it into a W part."""
    for x, y in (a, b):
        bu.via(board, *k(x, y), net, d=LINK_D, drill=LINK_DRILL)
    bu.track(board, [k(*a), k(*b)], 0.6, net, layer=pcbnew.B_Cu)


def backbone(board):
    def T(pts, w, net):
        bu.track(board, [k(*p) if not isinstance(p[0], str) else p for p in pts], w, net)

    J = j1_xy
    # ---- power ----------------------------------------------------------------------------------------------------
    # cell + -> fuse clips (both pins of the clip) -> VBAT trunk up to the boost's VIN pads
    T([(77.4, 54.8), (82.4, 49.8), (82.4, 47.3), (89.16, 47.3)], PW, "/power/BAT_IN")
    T([(98.75, 47.3), (105.51, 47.3), (105.52, 36.08), (108.06, 36.08)], PW, "VBAT")
    # D1 (crowbar) cathode and the fuel gauge's cell sense (JP2 BAT) from the VBAT trunk
    T([(98.75, 47.3), (98.75, 40.2), (100.6, 38.4), (100.6, 36.7)], 1.5, "VBAT")
    T([(100.6, 36.7), (99.0, 38.3), (84.5, 38.3), (82.92, 36.7), (82.92, 34.09)], SIG, "VBAT")
    # boost 5 V -> ideal diode VIN
    T([(94.16, 2.2), (94.16, 4.73), (96.0, 4.73), (96.9, 5.6), (113.14, 5.6)], PW, "5V_BOOST")
    # ideal diode VOUT -> J1 pins 4 and 2 -> C9 (100 uF); C10 (100 nF) on the way
    T([(84.0, 2.2), (84.0, 4.73), (86.6, 4.73), (86.6, 13.3), J(4)], P5, "5V_PI")
    T([(86.6, 13.3), (89.0, 13.3), J(2)], P5, "5V_PI")
    T([(89.0, 13.3), (97.0, 13.3), (98.5, 14.8), (98.5, 16.7)], P5, "5V_PI")
    T([(101.3, 8.0), (103.0, 9.5), (103.0, 15.0), (100.2, 16.7), (98.5, 16.7)], SIG, "5V_PI")   # C10
    T([(94.16, 9.82), (96.5, 11.0), (100.0, 11.0), (101.3, 13.0)], SIG, "GND")      # U3 GND to C10's
    # the radio's 5 V: along the top edge to the radio regulator U4 (any other way crosses a row of J1's escapes)
    T([(84.0, 2.2), (84.0, 1.0), (9.54, 1.0), (9.54, 15.5)], 1.0, "5V_PI")
    T([(9.54, 15.5), (9.54, 18.5), (10.5, 19.5), (10.5, 20.5)], 1.0, "5V_PI")
    T([(10.5, 20.5), (10.5, 25.5), (9.0, 27.0), (9.0, 27.8)], SIG, "5V_PI")                   # TP2
    # radio 3.3 V: U4 VOUT -> C12 -> socket pin 2 -> R80 (CSN pull-up); TP4
    T([(12.08, 15.5), (12.08, 13.0), (13.4, 11.8), (14.6, 11.8), (14.54, 7.0), (14.54, 3.6)], 1.0, "3V3_RADIO")
    T([(12.08, 15.5), (12.3, 16.5), (12.3, 21.0), (13.2, 22.5), (13.2, 24.5)], SIG, "3V3_RADIO")   # TP4
    # boost ENABLE -> R9
    T([(115.68, 36.08), (115.2, 37.5), (115.2, 41.0), (118.3, 43.18)], SIG, "/power/PWR_EN")   # past U2's M2 hole
    # ---- radio: bottom-row lines down, west under the LED group, north into the socket's south face -------------
    T([J(23), (61.06, 34.8), (31.5, 34.8), (31.5, 30.62)], SIG, "SPI_SCK")
    T([J(21), (63.6, 36.0), (28.5, 36.0), (28.5, 21.12)], SIG, "SPI_MISO")
    T([J(19), (66.14, 37.2), (24.0, 37.2), (24.0, 21.12)], SIG, "SPI_MOSI")
    T([J(15), (71.22, 38.4), (17.08, 38.4), (17.08, 7.0)], SIG, "RADIO_CE")
    # SCK_R west between the legs of R84 and R83 to pin 5; MOSI_R / MISO_R up to pins 6 / 7
    T([(31.5, 23.0), (31.5, 17.3), (22.16, 17.3), (22.16, 7.0)], SIG, "/radio/SCK_R")
    T([(24.0, 13.5), (24.0, 9.5), (24.7, 8.8), (24.7, 7.0)], SIG, "/radio/MOSI_R")
    T([(28.5, 13.5), (28.5, 9.8), (27.24, 8.5), (27.24, 7.0)], SIG, "/radio/MISO_R")
    # ---- radio: top-row lines up, west over J1 (CSN above IRQ), CSN to R80 and the socket's north face ----------
    T([J(24), (61.06, 8.8), (31.6, 8.8), (31.6, 4.6), (23.2, 4.6), (22.16, 3.6)], SIG, "RADIO_CSN")
    T([(22.16, 3.6), (20.8, 4.9), (19.62, 6.0), (19.62, 7.0)], SIG, "RADIO_CSN")
    T([J(18), (68.68, 10.8), (64.0, 10.8)], SIG, "RADIO_IRQ")
    hand_links(board, "RADIO_IRQ", (64.0, 10.8), (58.3, 10.8))                                 # over CSN
    T([(58.3, 10.8), (30.3, 10.8), (29.78, 9.0), (29.78, 7.0)], SIG, "RADIO_IRQ")
    # ---- mode, UART -----------------------------------------------------------------------------------------------
    T([J(36), (45.82, 13.4), (34.5, 13.4), (33.55, 13.2)], SIG, "SW_MODE_MRM")                # to R57 (bridge)
    T([(33.55, 5.58), (34.4, 6.2), (46.0, 6.2), (47.4, 4.8), (47.4, 4.3)], SIG, "/ui/SW_MODE_MRM_J")
    T([J(16), (71.22, 9.0), (66.4, 9.0), (66.4, 3.8), (65.3, 3.8)], SIG, "SW_MODE_NM")
    T([(57.68, 3.8), (52.4, 3.8), (52.4, 4.3)], SIG, "/ui/SW_MODE_NM_J")
    T([J(8), (81.38, 6.4), (70.76, 6.4), (70.76, 4.3)], SIG, "UART_TX")
    T([J(10), (78.84, 7.6), (68.22, 7.6), (68.22, 4.3)], SIG, "UART_RX")
    # ---- LEDs: straight down into R60/R61; LED_ACT_A west between R61's legs to J14 -------------------------------
    T([J(29), (53.44, 25.0)], SIG, "LED_ACT")
    T([J(31), (50.9, 21.0), (49.5, 22.4), (49.5, 25.0)], SIG, "LED_STATUS")
    T([(53.44, 32.62), (50.8, 28.8), (45.0, 28.8), (45.0, 28.5)], SIG, "/ui/LED_ACT_A")
    T([(49.5, 32.62), (43.6, 32.62), (42.5, 31.5), (42.5, 28.5)], SIG, "/ui/LED_STATUS_A")
    # ---- GO/STOP and role: down past the fuel gauge and the holder's + end to their 1 k in the bottom row --------
    T([J(13), (73.76, 20.0), (73.4, 20.4), (73.4, 63.6), (99.82, 63.6), (99.82, 61.8)], SIG, "SW_ROLE")
    T([J(11), (76.3, 20.5), (74.8, 22.0), (74.8, 60.4), (80.9, 60.4), (82.3, 61.8)], SIG, "BTN_TXRX")
    T([(89.92, 61.8), (89.92, 58.6), (84.2, 58.6), (84.2, 55.6)], SIG, "/ui/BTN_TXRX_J")
    T([(92.2, 61.8), (92.2, 58.0), (92.7, 57.5), (92.7, 55.6)], SIG, "/ui/SW_ROLE_J")
    # ---- I2C straight down into the fuel gauge; its VIN (the Pi's 3.3 V) round the end of its header row ---------
    T([J(5), (83.92, 21.5), (82.92, 22.5), (82.92, 25.2)], SIG, "I2C_SCL")
    T([J(3), (86.46, 21.5), (85.46, 22.5), (85.46, 25.2)], SIG, "I2C_SDA")
    T([J(1), (89.0, 20.6), (92.6, 22.2), (92.6, 27.6), (78.6, 27.6), (77.84, 26.8), (77.84, 25.2)], SIG, "3V3_PI")
    # ---- ground: three pockets of the pour that one layer cannot reach get a wire link each -----------------------
    hand_links(board, "GND", (7.6, 10.2), (11.6, 10.2))      # top band + socket pin 1, over the radio's 5 V
    hand_links(board, "GND", (77.0, 9.4), (77.0, 3.4))       # J1 pin 14, over the UART lines
    hand_links(board, "GND", (56.3, 33.0), (56.3, 40.2))     # the LED/radio pocket (J1 pins 25-39), over the SPI bus


def holes(board):
    pts = [k(x, y) for x, y in MOUNT.values()]
    h = bu.fp(board, "H30").GetPosition()
    pts.append((pcbnew.ToMM(h.x), pcbnew.ToMM(h.y)))
    return pts


def nets_with_pads(board):
    nets = {}
    for f in board.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n and not n.startswith("unconnected"):
                nets.setdefault(n, []).append(p)
    return nets


def route(grid, link_cost, verbose=True):
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        board.Delete(t)
    for z in list(board.Zones()):
        board.Delete(z)
    for f in board.GetFootprints():      # wire links of an earlier run: off the board until finish places them
        if f.GetReference().startswith("W"):
            f.SetPosition(bu.v(ORIGIN[0] + W + 20, ORIGIN[1]))
    backbone(board)
    x0, y0 = ORIGIN
    r = LinkRouter(board, x0, y0, x0 + W, y0 + H, grid=grid, clearance=0.4, link_cost=link_cost,
                   keep_out=[(x, y, MOUNT_KEEPOUT) for x, y in holes(board)])
    nets = nets_with_pads(board)
    todo = sorted(n for n, ps in nets.items() if n != "GND" and len(ps) > 1)
    for net in todo:
        r.seed(net)
    failed, t0 = [], time.time()
    for net in todo:
        widths = [1.0, SIG, 0.5] if net in ("VBAT", "/power/PWR_SW_J", "5V_PI", "3V3_RADIO") else [SIG, 0.5]
        done, bad = r.connect(net, None, widths)
        failed.extend((net, b) for b in bad)
        if verbose and (done or bad):
            print(f"{time.time() - t0:6.1f}s {net:24s} {len(done)} new" + (f", FAILED {bad}" if bad else ""),
                  flush=True)
    return board, r, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", type=float, default=0.1)
    ap.add_argument("--link-cost", type=float, default=30.0, help="mm a wire link costs (router part only)")
    a = ap.parse_args()
    board, r, failed = route(a.grid, a.link_cost)
    board.Save(PCB)
    x0, y0 = ORIGIN
    links = [{"net": n, "a": [round(p[0] - x0, 2), round(p[1] - y0, 2)], "b": [round(q[0] - x0, 2), round(q[1] - y0, 2)]}
             for n, p, q in r.links()]
    with open(LINKS, "w", encoding="utf-8") as f:
        json.dump({"links": links}, f, indent=1)
    wire = sum(math.dist(lk["a"], lk["b"]) for lk in links)
    print(f"{len(failed)} pads unrouted, {len(links)} wire links ({wire:.0f} mm of wire) -> {LINKS}")
    for lk in links:
        print("  ", lk)
    print("failed:", failed or "none")


if __name__ == "__main__":
    main()
