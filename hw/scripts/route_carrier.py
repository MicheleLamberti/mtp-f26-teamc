"""Route the Team C carrier with the grid router (run after place_carrier.py).

    python3 hw/scripts/route_carrier.py [--only power,radio]

Order: the power path first (short, wide), then SPI and the radio control lines, then everything else. GND is not
routed: it is the pour on both layers, tied together with stitching vias. Prints what could not be routed.
"""
import argparse
import os
import re
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
         ("5V_PI", [1.0, 0.6, 0.4]), ("/power/BAT_IN", [1.5, 1.0, 0.6]), ("/power/BAT_RAW", [1.5, 1.0, 0.6]), ("VBAT", [1.0, 0.6, 0.4, 0.25]),
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
    """FB (U2 pin 4) cannot be reached by the grid between the VBAT_SW area and the output caps: a 0.25 mm stub."""
    # FB (pin 4, the bottom pin on the right): straight down out of the package, then right between U2 and C8
    x, y = bu.pad_xy(board, "U2", 4)
    bu.track(board, [(x, y), (x, 65.1), (x + 1.6, 65.1)], 0.25, "/power/FB")
    # power GND (pin 1 bar): the only free pocket is left of the IC, between the SW_NODE and VBAT_SW areas:
    # a via there and a 0.25 mm track into the top edge of the bar (0.3 mm from the SW neck below it)
    gx, gy = bu.pad_xy(board, "U2", 1)
    bu.via(board, gx - 1.875, gy - 0.65, "GND")
    bu.track(board, [(gx - 1.875, gy - 0.65), (gx - 0.325, gy - 0.1)], 0.25, "GND")
    print("boost escapes: U2.4 FB -> right of the IC, U2.1 GND -> via left of the IC")


def package_escapes(board, ref, width, beyond):
    """Straight stubs outward from every signal pad of a fine-pitch package (pad pitch 0.5-0.65 mm, where the
    grid cannot place a centre line at exactly the legal distance), `beyond` mm past the pad's outer end."""
    f = bu.fp(board, ref)
    cx, cy = pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y)
    made = []
    for p in f.Pads():
        net = p.GetNetname()
        if not p.GetNumber() or net == "" or net.startswith("unconnected-"):
            continue
        x, y = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
        bb = p.GetBoundingBox()
        w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
        if abs(x - cx) < 0.05 and abs(y - cy) < 0.05:
            continue                                  # exposed pad: handled separately
        if w >= h:                                    # pad long along x: leave along x, away from the centre
            sx = 1.0 if x > cx else -1.0
            end = (x + sx * (w / 2 + beyond), y)
        else:
            sy = 1.0 if y > cy else -1.0
            end = (x, y + sy * (h / 2 + beyond))
        bu.track(board, [(x, y), end], width, net)
        made.append(p.GetNumber())
    print(f"{ref} escapes: pads {','.join(made)}")


def isolated_gnd_pads(board):
    """GND pads KiCad's DRC reports as unconnected (the zone fill cannot reach them)."""
    rpt = os.path.join(os.path.dirname(PCB), "build", "drc_gnd.rpt")
    board.Save(PCB)
    bu.run("kicad-cli", "pcb", "drc", "-o", rpt, PCB)
    want = set()
    section = ""
    with open(rpt, encoding="utf-8") as f:
        for line in f:
            if line.startswith("["):
                section = line.split("]")[0][1:]
            m = re.search(r"Pad (\S+) \[GND\] of (\S+) on", line)
            if m and section == "unconnected_items":
                want.add((m.group(2), m.group(1)))
    return [p for f in board.GetFootprints() for p in f.Pads()
            if (f.GetReference(), p.GetNumber()) in want and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]


def negotiate(r, board, nets, report, iterations, width=0.3):
    """Negotiated-congestion routing (PathFinder) of the small signal nets: every round re-routes all of them on
    hard obstacles (pads, fixed copper) plus a cost that grows where nets would break each other's clearance;
    cells that stay contested get a lasting history cost. Commits when no two nets conflict (or after the last
    round, keeping the conflict-free nets and leaving the others' conflicting connections unrouted)."""
    import numpy as np
    t0 = time.time()
    # the small nets' own routes stay off the board until the end, so everything on it (pads, power and radio
    # copper, all escape stubs) is a hard obstacle
    obs = {n: r.obstacles(n, width / 2) for n in nets}
    vbl = {n: r.via_block(n) for n in nets}
    shape = (2, r.ny, r.nx)
    hist = np.zeros(shape, dtype=np.float32)
    occ = np.zeros(shape, dtype=np.int16)
    masks, paths, failed = {}, {}, {}
    r_track = width / 2 + r.c + width / 2 + 0.05          # centre-to-centre distance two 0.3 mm tracks need
    r_via = r.via_d / 2 + r.c + max(width / 2, r.via_d / 2) + 0.05
    pres = 0.5
    print(f"negotiated routing of {len(nets)} nets (obstacle maps {time.time() - t0:.0f} s)", flush=True)
    for it in range(iterations):
        for n in nets:
            if n in masks:
                occ -= masks[n]
            cost = (1.0 + hist) * (1.0 + pres * occ.astype(np.float32))
            cl = [cost[0].ravel().tolist(), cost[1].ravel().tolist()]
            paths[n], failed[n] = r.route_net_soft(n, width, obs[n], vbl[n], cl)
            masks[n] = r.footprint_mask(paths[n], r_track, r_via) if paths[n] else np.zeros(shape, np.uint8)
            occ += masks[n]
        bad = []
        for n in nets:
            if not paths[n]:
                continue
            li, yi, xi = r.centre_cells(paths[n])
            other = occ[li, yi, xi] - masks[n][li, yi, xi]
            hit = other > 0
            if hit.any():
                bad.append(n)
                np.add.at(hist, (li[hit], yi[hit], xi[hit]), 1.0)
        nf = sum(1 for n in nets if failed[n])
        print(f"  round {it}: {len(bad)} nets in conflict, {nf} with blocked connections, pres {pres:.1f} "
              f"({time.time() - t0:.0f} s)", flush=True)
        if not bad:
            break
        pres *= 1.7
    # commit: conflict-free nets entirely; a net still in conflict loses its conflicting connections
    for n in nets:
        keep = []
        for path in paths[n]:
            m = r.footprint_mask([path], r_track, r_via)
            li, yi, xi = r.centre_cells([path])
            own = masks[n][li, yi, xi]          # contested = another net's footprint covers the cell
            if (occ[li, yi, xi] - own > 0).any():
                failed[n].append("(conflict)")
                continue
            keep.append(path)
        for path in keep:
            r.commit(path, n, width)
        report[n] = ([(width, "")] * len(keep), failed[n])
        print(f"{n:22s} {len(keep)} connections {'FAILED ' + ', '.join(failed[n]) if failed[n] else 'ok'}",
              flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="power,radio,rest")
    ap.add_argument("--grid", type=float, default=0.05, help="router grid (mm)")
    ap.add_argument("--rounds", type=int, default=6, help="rip-up and reroute rounds")
    ap.add_argument("--negotiate", action="store_true",
                    help="route the small signal nets with negotiated congestion instead of rip-up and reroute "
                         "(slow; did not converge on 19-Oct at 0.3 mm clearance)")
    ap.add_argument("--iterations", type=int, default=30, help="negotiated-congestion rounds")
    ap.add_argument("--margin", type=float, default=0.04, help="extra clearance against rasterization error (mm)")
    a = ap.parse_args()
    groups = a.only.split(",")
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        board.Delete(t)
    header_escapes(board)
    sp4_escapes(board)
    boost_escapes(board)
    package_escapes(board, "U3", 0.25, 0.8)          # BC857BS, SOT-363
    package_escapes(board, "U6", 0.2, 0.7)           # MAX17048, TDFN 0.5 mm
    package_escapes(board, "U5", 0.2, 0.6)           # TPS63001 (DNP option), VSON 0.5 mm
    ex, ey = bu.pad_xy(board, "U5", 11)
    bu.via(board, ex, ey, "GND")                      # its exposed pad to the bottom ground pour
    # BCM857BS (SOT-363): the base B1 (pin 2) joins B2/C1 (pins 5/6) straight under the package; 0.325 mm from
    # the neighbouring pins at 0.25 mm wide (the corner between Q4, U3 and the header is too tight for the grid)
    x2, y2 = bu.pad_xy(board, "U3", 2)
    x5, y5 = bu.pad_xy(board, "U3", 5)
    x6, y6 = bu.pad_xy(board, "U3", 6)
    bu.track(board, [(x2, y2), (x5, y5)], 0.25, "/power/ZVD_B")
    bu.track(board, [(x5, y5), (x6, y6)], 0.25, "/power/ZVD_B")
    ex, ey = bu.pad_xy(board, "U6", 9)
    bu.via(board, ex, ey, "GND")                      # exposed pad to the bottom ground pour
    r = Router(board, X0, Y0, X1, Y1, grid=a.grid, margin=a.margin, clearance=bu.FAB_RULES["clearance"],
               fine_refs=FINE_REFS, fine_nets=FINE_NETS)
    plan = []
    if "power" in groups:
        plan += POWER
    if "radio" in groups:
        plan += RADIO
    if "rest" in groups:
        named = {n for n, _ in POWER + RADIO} | {"/power/SW_NODE"}
        others = sorted({p.GetNetname() for f in board.GetFootprints() for p in f.Pads()}
                        - named - {"", "GND"})
        # alphabetical order: it routed more nets than longest-first (15 vs 21 left over on 19-Oct)
        others = sorted(n for n in others if not n.startswith("unconnected-"))
        plan += [(n, [0.3, 0.25]) for n in others]
    report = {}
    fixed_nets = {n for n, _ in POWER + RADIO}
    if a.negotiate and "rest" in groups:
        soft = [n for n, _ in plan if n not in fixed_nets]
        plan = [(n, w) for n, w in plan if n in fixed_nets]
    else:
        soft = []
    widths_of = dict(plan)
    queue = [n for n, _ in plan]
    for rnd in range(a.rounds):
        failed_now = {}
        for net in queue:
            t = time.time()
            r.rip(net)
            done, failed = r.route_net(net, widths_of[net],
                                       limit=3_000_000 if net in fixed_nets else 800_000)
            report[net] = (done, failed)
            ws = sorted({w for w, _ in done})
            print(f"[{rnd}] {net:22s} widths {ws} {'FAILED ' + ', '.join(failed) if failed else 'ok'} "
                  f"({time.time() - t:.1f} s)", flush=True)
            if failed:
                failed_now[net] = failed
        if not failed_now or rnd == a.rounds - 1:
            break
        # rip up the small nets that sit around each failed pad, then route the failed nets first
        victims = []
        for net, pads in failed_now.items():
            for name in pads:
                ref, num = name.split(".", 1)
                x, y = bu.pad_xy(board, ref, num)
                for other in list(r.owned):
                    if other not in fixed_nets and other != net and other not in victims \
                            and r.near(other, x, y, 2.5):
                        victims.append(other)
        print(f"round {rnd}: {len(failed_now)} nets failed; ripping up {len(victims)}: {', '.join(victims)}",
              flush=True)
        for v in victims:
            r.rip(v)
        queue = list(failed_now) + [v for v in victims if v not in failed_now]   # fixed nets retry, never ripped
        if not queue:
            break
    if soft:
        negotiate(r, board, soft, report, a.iterations)
    vias = r.stitch("GND", pitch=4.0)
    bu.fill_zones(board)
    gone = r.prune(vias, "GND")
    bu.fill_zones(board)
    print(f"GND stitching vias: {len(vias) - gone} kept, {gone} removed (not in the pour on both layers)")
    board.Save(PCB)
    # GND pads the pours cannot reach (boxed in by other nets): a via next to each, into the bottom pour
    for _ in range(2):
        lonely = isolated_gnd_pads(board)
        if not lonely:
            break
        placed = [f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in lonely
                  if r.via_to(p, "GND", reach=5.0)]
        print("GND vias at isolated pads:", ", ".join(placed) or "none", "| no room:",
              ", ".join(f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in lonely
                        if f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" not in placed) or "none")
        bu.fill_zones(board)
        board.Save(PCB)
    board.Save(PCB)
    bad = [(n, f) for n, (_, f) in report.items() if f]
    print("UNROUTED:", bad if bad else "none")


if __name__ == "__main__":
    main()
