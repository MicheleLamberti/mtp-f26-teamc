"""Route carrier rev B for the UPC lab (hw/teamc-carrier-lab) on ONE copper layer (F.Cu). Run after
place_carrier_lab.py.

    python3 hw/scripts/route_carrier_lab.py            # route, write links.json, report
    python3 hw/scripts/route_carrier_lab.py --grid 0.2 # faster draft

Power first (cell path and 5 V at 1.5 mm, the boost loop's ground as a star at J20), then the small power-control
nets, 3V3_RADIO at 0.8 mm, the signals at 0.5 mm (shortest first) and 3V3_PI last. Where a net cannot cross on one
layer, linkroute.LinkRouter jumps it with a wire link (a bare wire on the component side between two unplated
holes); the links are written to hw/teamc-carrier-lab/links.json for build_carrier_lab.py, which adds them to the
schematic as W1, W2, ... (see finish_carrier_lab.py).
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
from place_carrier_lab import CAP_X, DIR, H, LEAD_X, MOUNT, MOUNT_KEEPOUT, ORIGIN, PCB, UI_ROWS, W, k  # noqa: E402

LINKS = os.path.join(DIR, "links.json")
SIG = 0.5
PW = 1.5      # cell path, VBAT trunk, 5 V
MID = 0.8     # VBAT branches, 3V3_RADIO
# nets still for the router after power(): (net, pads or None = all, widths)
POWER_REST = [
    ("VBAT", None, [MID, SIG]),
    ("3V3_RADIO", None, [MID]),
]


# Routing order (after the hand-routed power path and SCK swap): (net, widths, link cost in mm or None = --link-cost,
# pads or None = all). The nets with a planar route go first with links priced out. Then the even-row lines that
# come over the top of J1 and must cross the radio lanes or each other, innermost first (MRM is J1's top even pin),
# and last the fuel gauge's cell sense, which has to cross the left-hand lines.
PLAIN = 60.0
ORDER = [
    ("UART_TX", [SIG], PLAIN, None), ("UART_RX", [SIG], PLAIN, None),
    ("I2C_SDA", [SIG], PLAIN, None), ("I2C_SCL", [SIG], PLAIN, None),
    ("LED_ACT", [SIG], PLAIN, None), ("LED_STATUS", [SIG], PLAIN, None),
    ("/ui/LED_ACT_A", [SIG], PLAIN, None), ("/ui/LED_STATUS_A", [SIG], PLAIN, None),
    ("SPI_MISO", [SIG], PLAIN, None), ("SPI_MOSI", [SIG], PLAIN, None), ("SPI_SCK", [SIG], PLAIN, None),
    ("/radio/MISO_R", [SIG], PLAIN, None), ("/radio/MOSI_R", [SIG], PLAIN, None),
    ("/radio/SCK_R", [SIG], PLAIN, None), ("RADIO_CE", [SIG], PLAIN, None),
    ("VBAT", [MID, SIG], PLAIN, ["C11.1", "U4.1"]),
    ("LED_RTN", [SIG], PLAIN, None),
    ("BTN_TXRX", [SIG], PLAIN, None), ("SW_ROLE", [SIG], PLAIN, None),
    ("SW_MODE_MRM", [SIG], None, None), ("RADIO_CSN", [SIG], 20.0, None), ("RADIO_IRQ", [SIG], None, None),
    ("SW_MODE_NM", [SIG], None, None),
    ("VBAT", [SIG], None, None),
    ("3V3_PI", [SIG], None, None),
]


def power(board):
    """Hand-routed power path (seen from the copper side; see place_carrier_lab.py for the floorplan).

    Cell end: J20 (+ right, - left) -> F1 up -> Q1 (drain left, source up) -> VBAT riser along the right edge ->
    VBAT line at y = VL over U2's cell end -> U2 pads 1/2, C5, D3, TP1, J23 (charger), R8. Ground of the boost loop: a trunk
    under U2 (x = GX) from its cell-end GND pads to its 5 V-end GND pads, with C5, D3 and J20 tied straight to it
    (star at the trunk, J20 next to it). 5 V: U2 pads 6/7 -> U3 pads 1/2; U3 pads 5/6 -> J1 pins 4/2, C9, C10, D2.
    """
    P = lambda ref, n: bu.pad_xy(board, ref, n)  # noqa: E731
    T = lambda pts, w, net: bu.track(board, pts, w, net)  # noqa: E731
    # -- cell path
    j1, f1, f2 = P("J20", 1), P("F1", 1), P("F1", 2)
    T([j1, (j1[0], f1[1]), f1], PW, "/power/BAT_IN")
    qd, qs, qg = P("Q1", 3), P("Q1", 2), P("Q1", 1)
    T([f2, (qd[0], f2[1] - 1.0), qd], PW, "/power/BAT_RAW")          # in from below, clear of the gate pad
    r1g, r1n = P("R1", 1), P("R1", 2)
    T([qg, (r1g[0] - 1.2, qg[1]), r1g], SIG, "/power/Q1_G")
    # -- VBAT riser and line
    rx, vl = 98.4 + ORIGIN[0], 15.5 + ORIGIN[1]
    u1, u2 = P("U2", 1), P("U2", 2)
    T([qs, (rx, qs[1] - (rx - qs[0])), (rx, vl), (u2[0], vl)], PW, "VBAT")
    T([(u1[0], vl), u1], PW, "VBAT")
    T([(u2[0], vl), u2], PW, "VBAT")
    c5p, d3p = P("C5", 1), P("D3", 1)
    T([(rx, c5p[1]), c5p], PW, "VBAT")
    T([(rx, d3p[1]), d3p], PW, "VBAT")
    tp1 = P("TP1", 1)
    T([(tp1[0], vl), tp1], MID, "VBAT")
    r8 = P("R8", 1)
    T([(u2[0], vl), (r8[0] + 1.5, vl), (r8[0], r8[1])], MID, "VBAT")
    # -- ground trunk under U2
    g3, g4, g8, g9 = P("U2", 3), P("U2", 4), P("U2", 8), P("U2", 9)
    gx = (g3[0] + g4[0]) / 2
    top, bot = g3[1] + 2.5, g8[1] - 3.0
    T([g4, (g4[0], top), (g3[0], top), g3], PW, "GND")
    T([(gx, top), (gx, bot)], PW, "GND")
    T([g9, (g9[0], bot), (gx, bot)], PW, "GND")
    T([g8, (g8[0], bot)], PW, "GND")
    for ref in ("C5", "D3"):
        g = P(ref, 2)
        T([g, (gx, g[1])], PW, "GND")
    j2 = P("J20", 2)
    T([j2, (gx, j2[1])], PW, "GND")
    # charger lead J23 on VBAT behind F1/Q1 (review 23-Oct): VBAT pin straight up to the VBAT line, GND pin down to
    # C5's ground pad (on the trunk). R1 returns below the cell lead to J20's GND pin.
    c1, c2 = P("J23", 1), P("J23", 2)
    T([c1, (c1[0], vl)], PW, "VBAT")
    c5g = P("C5", 2)
    T([c2, (c2[0], c2[1] + 2.5), (c5g[0], c2[1] + 2.5), c5g], 1.0, "GND")
    T([r1n, (r1n[0], j1[1] + 3.5), (j2[0], j1[1] + 3.5), j2], 1.0, "GND")
    # -- EN and the toggle cluster
    T([P("Q2", 3), (P("U2", 5)[0] - 1.5, P("Q2", 3)[1]), P("U2", 5)], SIG, "/power/PWR_EN")
    T([P("R8", 2), P("Q2", 1)], SIG, "/power/PWR_G")
    T([P("C18", 1), (P("Q2", 1)[0] - 1.0, P("C18", 1)[1]), P("Q2", 1)], SIG, "/power/PWR_G")
    T([P("R9", 2), (P("C18", 1)[0], P("R9", 2)[1]), P("C18", 1)], SIG, "/power/PWR_G")
    T([P("J22", 1), (P("J22", 1)[0], P("R9", 1)[1]), P("R9", 1)], SIG, "/power/PWR_SW_J")
    # -- 5 V: boost -> ideal diode
    b6, b7, d1, d2 = P("U2", 6), P("U2", 7), P("U3", 1), P("U3", 2)
    jx = d1[0] + 1.9
    T([b6, (b6[0], b6[1] + 3.0), (b7[0], b6[1] + 3.0)], PW, "5V_BOOST")
    T([b7, (b7[0], d1[1] - 3.0), (jx, d1[1] - 0.5), (jx, d2[1]), d2], PW, "5V_BOOST")
    T([(jx, d1[1]), d1], PW, "5V_BOOST")
    # -- 5V_PI: ideal diode -> J1 pins 4/2, C9, C10, D2
    o5, o6 = P("U3", 5), P("U3", 6)
    T([o5, o6], PW, "5V_PI")
    T([o5, P("C9", 1)], PW, "5V_PI")
    T([o5, P("J1", 4)], PW, "5V_PI")
    T([o6, P("J1", 2)], PW, "5V_PI")
    for ref in ("C10", "D2"):
        c = P(ref, 1)
        T([(c[0], o6[1]), c], 1.0, "5V_PI")
    # the 5V_PI TVS and 100 nF return to U3's ground pads (south of the 5 V tracks); U3's two ground rows tied
    # under the module, C9's ground pad on the tie
    T([P("D2", 2), P("C10", 2), P("U3", 8)], MID, "GND")
    T([P("U3", 8), P("U3", 4)], PW, "GND")
    T([P("C9", 2), (P("C9", 2)[0], P("U3", 8)[1])], MID, "GND")
    # the Pi's 5 V return: J1 pins 14 and 6 (via J13's ground pin) east to the boost's 5 V-end ground trunk
    j14, j13g = P("J1", 14), P("J13", 1)
    T([j13g, (j13g[0] + 2.5, j13g[1]), (j13g[0] + 2.5, j14[1])], PW, "GND")
    T([j14, (g9[0] - 4.0, j14[1]), (g9[0], bot + 1.0), (g9[0], bot)], PW, "GND")
    # -- J1 pin 6 to the UART ground pin (the header ground next to TX/RX)
    T([P("J1", 6), P("J13", 1)], SIG, "GND")


def left_side(board):
    """Hand-routed left half: the UI rows, the fuel gauge's VIN, the radio LDO.

    Each UI row: lead pin -> TVS -> 1 k -> 100 nF, straight along the row (the router takes the GPIO end to J1).
    3V3_PI leaves J1 pin 1 south, runs west under the fuel gauge's header row and up its west side to VIN.
    LDO: VOUT -> C12 -> socket pin 2 (south side) -> R80 (north side); GND west to C11; CSN from R80 to pin 4.
    """
    P = lambda ref, n: bu.pad_xy(board, ref, n)  # noqa: E731
    T = lambda pts, w, net: bu.track(board, pts, w, net)  # noqa: E731
    B = lambda x, y: (x + ORIGIN[0], y + ORIGIN[1])  # noqa: E731  board -> page
    for line, jref, _y, tvs, _x, _ts, ser, cap, _cs in UI_ROWS:
        jp = "3" if line == "SW_MODE_MRM" else "1"
        T([P(jref, jp), P(tvs, 1), P(ser, 1)], SIG, bu.pad(board, tvs, 1).GetNetname())
        T([P(ser, 2), P(cap, 1)], SIG, line)
    j, vin = P("J1", 1), P("U6", 1)
    turn = B(33.5, 75.0)
    T([j, (j[0] - 1.5, j[1] + 1.5), (j[0] - 1.5, turn[1]), turn, (turn[0], vin[1] + 1.2), (turn[0] + 1.2, vin[1]),
       vin], SIG, "3V3_PI")
    vo, c12, s2, r80 = P("U4", 5), P("C12", 1), P("J30", 2), P("R80", 1)
    T([vo, (c12[0] - 1.2, vo[1]), c12, (s2[0], c12[1] - 1.5), s2], MID, "3V3_RADIO")
    T([s2, (s2[0], r80[1] + 1.0), r80], SIG, "3V3_RADIO")
    T([P("U4", 2), P("C11", 2)], SIG, "GND")
    r2, s4 = P("R80", 2), P("J30", 4)
    T([r2, (s4[0], r2[1] + 1.0), s4], SIG, "RADIO_CSN")


def radio_swap(board):
    """SCK leaves J1 north of MISO and MOSI but lands south of them on the socket (CE, SCK, MOSI, MISO from west to
    east): it drops south between the pads of R84 (MISO) and R83 (MOSI) - the two 1206 resistors bridge it."""
    P = lambda ref, n: bu.pad_xy(board, ref, n)  # noqa: E731
    sx = (P("R84", 1)[0] + P("R84", 2)[0]) / 2
    j = P("J1", 23)
    r = P("R82", 1)
    bu.track(board, [j, (sx, j[1]), (sx, r[1]), r], SIG, "SPI_SCK")
    for ref, pin in (("R84", 21), ("R83", 19)):
        bu.track(board, [P("J1", pin), P(ref, 1)], SIG, bu.pad(board, ref, 1).GetNetname())


def pads_of(board, net, names=None):
    """Pads of `net` (only `names` "REF.pin" if given); wire links (W*) are placed later by finish_carrier_lab.py."""
    out = []
    for f in board.GetFootprints():
        if f.GetReference().startswith("W"):
            continue
        for p in f.Pads():
            if p.GetNetname() == net and (names is None or f"{f.GetReference()}.{p.GetNumber()}" in names):
                out.append(p)
    return out


def mst_length(pads):
    pts = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in pads]
    if len(pts) < 2:
        return 0.0
    done, rest, total = [pts[0]], pts[1:], 0.0
    while rest:
        a, c = min(((a, c) for a in done for c in rest), key=lambda ac: math.dist(*ac))
        total += math.dist(a, c)
        done.append(c)
        rest.remove(c)
    return total


def signal_nets(board):
    nets = {}
    for f in board.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n and not n.startswith("unconnected"):
                nets.setdefault(n, []).append(p)
    skip = {"GND", "3V3_PI", "VBAT", "3V3_RADIO", "5V_BOOST", "5V_PI", "/power/BAT_IN",
            "/power/BAT_RAW", "/power/Q1_G", "/power/PWR_EN", "/power/PWR_G", "/power/PWR_SW_J"}
    rest = [n for n, ps in nets.items() if n not in skip and len(ps) > 1]
    return sorted(rest, key=lambda n: mst_length(nets[n])), nets


def route(order, grid, link_cost, verbose=False):
    """One routing pass in `order` [(net, widths, link cost, pads)]. Returns (board, router, failed [(net, pad)], track length)."""
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        board.Delete(t)
    for z in list(board.Zones()):
        board.Delete(z)
    for f in board.GetFootprints():      # wire links of an earlier run: off the board until finish places them
        if f.GetReference().startswith("W"):
            f.SetPosition(bu.v(ORIGIN[0] + W + 20, ORIGIN[1]))
    keep = [(*k(x, y), MOUNT_KEEPOUT) for x, y in MOUNT.values()]
    h30 = bu.fp(board, "H30").GetPosition()
    keep.append((pcbnew.ToMM(h30.x), pcbnew.ToMM(h30.y), MOUNT_KEEPOUT))
    x0, y0 = ORIGIN
    # the UI rows are hand-routed; other nets keep out of them (a wall of foreign copper there would cut the pour
    # between the rows off from the rest), but may cross them with a wire link
    ui = [r_[2] for r_ in UI_ROWS]
    rect = (*k(LEAD_X + 2.0, min(ui) - 2.5), *k(CAP_X - 1.2, max(ui) + 3.5))
    r = LinkRouter(board, x0, y0, x0 + W, y0 + H, grid=grid, link_cost=link_cost, keep_out=keep, keep_rects=[rect])
    t0 = time.time()
    failed = []
    power(board)
    radio_swap(board)
    left_side(board)
    for net in sorted({t.GetNetname() for t in board.GetTracks()}):
        r.seed(net)
    for net, widths, lc, names in order:
        done, bad = r.connect(net, pads_of(board, net, names), widths, link_cost=lc)
        failed.extend((net, b) for b in bad)
        if verbose:
            thin = [d for d in done if d[0] < widths[0]]
            print(f"{time.time() - t0:6.1f}s {net:24s} {len(done)} ok" + (f", thin {thin}" if thin else "")
                  + (f", FAILED {bad}" if bad else ""), flush=True)
    length = sum(pcbnew.ToMM(t.GetLength()) for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))
    return board, r, failed, length


BAND = ("SW_MODE_MRM", "RADIO_CSN", "RADIO_IRQ", "SW_MODE_NM")


def make_order(band_order, link_cost):
    """ORDER with the band nets (the even-row lines over the top of J1) in `band_order` at `link_cost`."""
    plain = [(n, w, lc, pads) for n, w, lc, pads in ORDER if lc is not None and n not in BAND]
    band = {n: (n, w, link_cost, pads) for n, w, lc, pads in ORDER if n in BAND}
    rest = [(n, w, link_cost, pads) for n, w, lc, pads in ORDER if lc is None and n not in BAND]
    # the fuel gauge's cell sense and the LDO's EN before the band: their way to the bottom-left corner is the
    # one the band lines would otherwise take round the bottom of J1
    return plain + rest + [band[n] for n in band_order]


def trial(args):
    band_order, link_cost, grid = args
    _, r, failed, length = route(make_order(band_order, link_cost), grid, link_cost)
    links = r.links()
    wire = sum(math.dist(p, q) for _, p, q in links)
    return (len(failed), len(links), round(wire, 1), round(length)), band_order, link_cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", type=float, default=0.1)
    ap.add_argument("--link-cost", type=float, default=12.0, help="mm a wire link costs for the crossing nets")
    ap.add_argument("--band", default=",".join(BAND), help="order of the band nets")
    ap.add_argument("--search", action="store_true", help="try every band order at link costs 5/8/12, keep the best")
    a = ap.parse_args()
    board = pcbnew.LoadBoard(PCB)
    sig, _ = signal_nets(board)
    done_by_hand = {"3V3_RADIO"} | {r[0] + "_J" for r in UI_ROWS} | {"/ui/" + r[0] + "_J" for r in UI_ROWS}
    missing = [n for n in sig if n not in {o[0] for o in ORDER} | done_by_hand]
    if missing:
        raise SystemExit(f"nets missing from ORDER: {missing}")
    band, cost = tuple(a.band.split(",")), a.link_cost
    if a.search:
        import itertools
        jobs = [(bo, lc, a.grid) for bo in itertools.permutations(BAND) for lc in (5.0, 8.0, 12.0)]
        results = []
        for job in jobs:          # sequential: pcbnew does not survive a forked worker pool
            results.append(trial(job))
            print("  trial", results[-1], flush=True)
        results.sort()
        for score, bo, lc in results[:8]:
            print(f"  {score} {','.join(bo)} link cost {lc}")
        _, band, cost = results[0]
    order = make_order(band, cost)
    board, r, failed, length = route(order, a.grid, cost, verbose=True)
    board.Save(PCB)
    x0, y0 = ORIGIN
    links = [{"net": n, "a": [round(p[0] - x0, 2), round(p[1] - y0, 2)], "b": [round(q[0] - x0, 2),
                                                                             round(q[1] - y0, 2)]}
             for n, p, q in r.links()]
    with open(LINKS, "w", encoding="utf-8") as f:
        json.dump({"band": list(band), "link_cost": cost, "links": links}, f, indent=1)
    wire = sum(math.dist(lk["a"], lk["b"]) for lk in links)
    print(f"band {','.join(band)}, link cost {cost}: {len(failed)} pads unrouted, {len(links)} wire links "
          f"({wire:.0f} mm of wire), {length:.0f} mm of track -> {LINKS}")
    for lk in links:
        print("  ", lk)
    print("failed:", failed or "none")


if __name__ == "__main__":
    main()
