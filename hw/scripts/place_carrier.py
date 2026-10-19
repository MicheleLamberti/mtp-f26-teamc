"""Place (and partly route) the Team C carrier board with pcbnew. Run after build_carrier.py.

    python3 hw/scripts/place_carrier.py

Board: Raspberry Pi 3 Model A+ HAT outline from the KiCad template (65 x 56 mm, origin (100, 44), M2.5 holes on
58 x 49 mm), display/camera cutouts removed (we use neither). Key parts are placed by hand (FIXED below, Pi
coordinates in the comments are from the A+ mechanical drawing, origin bottom-left, y up); every other part is placed
next to the part it shares its most specific net with, avoiding courtyards, the hole keep-outs and the board edge.
Then GND is poured on both layers. Routing beyond that is listed in hw/DESIGN_NOTES.md for ET.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402

DIR = os.path.join(bu.HW, "teamc-carrier")
PCB = os.path.join(DIR, "teamc-carrier.kicad_pcb")
X0, Y0, X1, Y1 = 100.0, 44.0, 165.0, 100.0       # board edges (KiCad mm)
HOLES = [(103.5, 47.5), (161.5, 47.5), (103.5, 96.5), (161.5, 96.5)]
HOLE_KEEPOUT_R = 3.1                               # HAT spec: 6.2 mm copper-free land
EDGE_MARGIN = 0.5

# ref: (x, y, rotation, back side)
FIXED = {
    # radio corner (Pi bottom-right, far from the SoC and the Pi's wireless can)
    "U7": (149.0, 89.5, 0, False),     # SP4: pad row up, IPEX near the bottom edge, clear of MH4's keep-out
    "C70": (159.8, 68.6, 90, False),   # 100 uF at pad 1
    "C72": (154.6, 77.3, 0, False),    # 100 nF right at pad 1, above the module's courtyard
    "C71": (158.9, 77.3, 0, False),    # 10 uF
    "U4": (141.0, 75.5, 0, False),     # radio LDO
    "R84": (147.5, 74.5, 90, False),   # MISO series R at the radio end, above the pad escapes
    "TP10": (161.5, 82.0, 0, False),
    "U5": (138.5, 68.0, 0, False),     # buck-boost option (DNP)
    "L2": (133.5, 67.8, 0, False),     # its inductor, beside the L1/L2 pins
    # power corner (Pi top-left, next to header pins 2/4)
    # boost laid out as TI's RWU example: L1 above the IC (SW pad on the left, VIN on the right), input cap at VIN,
    # output caps in a row under VOUT; SW_NODE / VBAT_SW / 5V_BOOST are copper areas (BOOST_ZONES)
    "L1": (109.65, 58.8, 180, False),   # pad 1 (VBAT_SW) right, pad 2 (SW) left
    "U2": (112.5, 63.6, 0, False),
    "C4": (116.2, 60.2, 0, False),     # 22 uF at VIN (pin 7)
    "C6": (107.4, 67.9, 90, False),    # 3 x 22 uF at VOUT (pin 3)
    "C7": (110.0, 67.9, 90, False),
    "C8": (112.6, 67.9, 90, False),
    "C5": (124.0, 63.5, 90, False),    # 100 uF boost input bulk
    "Q4": (108.0, 52.6, 0, False),     # ideal diode under header pins 2/4
    "U3": (112.4, 52.6, 0, False),     # its left escape stubs must clear Q4's drain pad
    "R12": (116.6, 52.8, 90, False),   # mirror base resistor right at U3
    "R13": (104.3, 53.8, 90, False),   # gate resistor at Q4
    "C9": (123.0, 54.0, 0, False),     # 100 uF at 5V_PI
    "C10": (104.4, 58.5, 90, False),   # 100 nF at 5V_PI, left strip under header pin 2
    "D2": (104.4, 63.6, 90, False),    # 5V_PI TVS
    # left edge: battery lead above the USB-C mouth
    "J20": (107.46, 76.3, 180, False),  # battery lead, + (pin 1) on the right, towards the fuse
    "J2": (103.4, 87.5, 270, False),   # rotation re-checked below so the mouth faces the left edge
    "F1": (113.5, 73.7, 0, False),     # battery path: J20 -> F1 -> Q1 -> Q2, stacked beside J20
    "Q1": (113.0, 77.2, 0, False),
    "Q2": (113.0, 81.2, 0, False),
    # boost feedback divider right of U2 (FB pin 4 escapes to the right), clear of the FB stub
    "R10": (116.0, 67.3, 90, False),
    "C3": (118.5, 67.3, 90, False),
    "R11": (117.0, 71.0, 0, False),
    # charger + USB-C below the battery path: CC resistors at the CC pins, ESD array under the charger
    "U1": (115.0, 85.4, 0, False),
    "U12": (113.6, 89.6, 0, False),
    "R2": (110.5, 84.6, 0, False),
    "R3": (109.6, 89.4, 90, False),
    "R4": (119.6, 83.4, 0, False),     # PROG at U1 pin 5
    "C1": (119.3, 86.9, 90, False),    # 10 uF at U1 VDD (pin 4)
    "C2": (122.0, 89.8, 90, False),    # 10 uF at the charger output (VBAT)
    "U6": (120.5, 74.5, 0, False),     # fuel gauge in the open part of the battery area (its escapes need room)
    # bottom edge: panel leads
    "J22": (111.5, 95.0, 0, False),    # power toggle
    "J10": (121.0, 95.0, 0, False),    # GO/STOP button
    "J11": (130.5, 95.0, 0, False),    # role toggle
    "J12": (126.5, 86.0, 0, False),    # mode toggle
    "U11": (137.6, 88.0, 0, False),    # ESD at the leads
    # signals next to the header
    "R83": (131.2, 53.5, 90, False),   # MOSI series R at header pin 19
    "R82": (136.3, 53.5, 90, False),   # SCK series R at header pin 23
    "J13": (141.0, 56.0, 90, False),   # UART console
    "TP2": (129.8, 59.0, 0, False),
    "TP3": (134.0, 62.0, 0, False),
}
# copper areas of the boost (F.Cu, above the GND pour): net, polygon. The SW neck at the IC sits between the GND
# (pin 1) and VOUT (pin 3) bars; the VBAT_SW area covers VIN (7), MODE (6) and EN (5) from the right and
# stops 0.275 mm above FB (4); the 5V_BOOST area stays 0.45 mm clear of FB.
BOOST_ZONES = [
    ("/power/SW_NODE", [(106.4, 57.7), (108.75, 57.7), (108.75, 63.375), (112.8, 63.375), (112.8, 63.825),
                        (106.4, 63.825)]),
    ("VBAT_SW", [(110.6, 57.7), (116.0, 57.7), (116.0, 62.6), (114.6, 62.6), (114.6, 63.95), (113.15, 63.95),
                 (113.15, 61.5), (110.6, 61.5)]),
    ("/power/5V_BOOST", [(106.0, 64.05), (112.8, 64.05), (112.8, 66.95), (106.0, 66.95)]),
]
# functional clusters: each member goes next to its anchor (a part: its pad on the shared net; or a point),
# inside the cluster's region only, so one cluster cannot take another's room. Placed before everything else.
CLUSTERS = [
    ("battery", (110.4, 72.0, 128.0, 84.0), [("R1", "Q1"), ("D3", "Q1"), ("C17", "U6"),
                                             ("C18", "Q2"), ("R8", "Q2"), ("R9", "Q2")]),
    ("charger", (108.2, 82.6, 122.5, 92.1), []),
    # UI inputs: pull-up and series R at the connector side with the ESD array, the 100 nF at the GPIO pin; the
    # GPIO line runs as one track to the header
    ("ui_bot", (128.0, 76.0, 140.2, 92.1), [("R50", "U11"), ("R51", "U11"), ("R52", "U11"), ("R53", "U11"),
                                            ("R54", "U11"), ("R55", "U11"), ("R56", "U11"), ("R57", "U11")]),
    # under the header: LEDs, and the pull-ups to 3V3_PI next to their GPIO pins (short 3V3_PI from pin 17)
    ("ui_top", (127.5, 51.2, 158.5, 60.6), [("C50", "J1"), ("C51", "J1"), ("C52", "J1"), ("C53", "J1"),
                                            ("R80", "J1"), ("R81", "J1"), ("R17", "J1"), ("R7", "J1"),
                                            ("R60", "J1"), ("R61", "J1"), ("D10", "R60"), ("D11", "R61")]),
    ("mid", (126.0, 60.6, 157.0, 78.8), [("C11", "U4"), ("C12", "U4"), ("R14", "U4"),
                                         ("Q3", (130.0, 73.5)), ("R6", "Q3"), ("D4", "Q3"), ("R5", "D4"),
                                         ("TP1", (126.5, 70.5)), ("R16", "U5"), ("R15", "U5"), ("C13", "U5"),
                                         ("C14", "U5"), ("C15", "U5"), ("C16", "U5"), ("L2", "U5")]),
]
# parts whose own nets are rails: put them next to the part they serve (anchor's pad on the shared net)
NEAR = {
    "C1": "J2", "R2": "J2", "R3": "J2",
    "C2": "U1", "R4": "U1", "R5": "U1", "D4": "U1", "Q3": "U1", "R6": "Q3", "R7": "Q3",
    "R1": "Q1", "D3": "Q1", "R8": "Q2", "R9": "Q2", "C18": "Q2", "F1": "J20",
    "C3": "U2", "R10": "U2", "R11": "U2", "C4": "U2", "C6": "U2", "C7": "U2", "C8": "U2",
    "C10": "C9", "D2": "C9", "R12": "U3", "R13": "U3",
    "C11": "U4", "C12": "U4", "R14": "U4",
    "R16": "U5", "C13": "U5", "C14": "U5", "C15": "U5", "C16": "U5", "L2": "U5", "R15": "U5",
    "C17": "U6", "R17": "U6",

}
# nets too common to pick a neighbour by
COMMON = {"GND", "VBAT", "VBAT_SW", "3V3_PI", "5V_PI", "3V3_RADIO", "/power/5V_BOOST"}


def courtyard(f, margin=0.25):
    lay = pcbnew.B_CrtYd if f.GetLayer() == pcbnew.B_Cu else pcbnew.F_CrtYd
    bb = f.GetCourtyard(lay).BBox()
    if bb.GetWidth() == 0:
        bb = f.GetBoundingBox(False)
    return (pcbnew.ToMM(bb.GetLeft()) - margin, pcbnew.ToMM(bb.GetTop()) - margin,
            pcbnew.ToMM(bb.GetRight()) + margin, pcbnew.ToMM(bb.GetBottom()) + margin)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def inside_board(r):
    if r[0] < X0 + EDGE_MARGIN or r[2] > X1 - EDGE_MARGIN or r[1] < Y0 + EDGE_MARGIN or r[3] > Y1 - EDGE_MARGIN:
        return False
    for hx, hy in HOLES:   # rectangle vs circle
        cx, cy = min(max(hx, r[0]), r[2]), min(max(hy, r[1]), r[3])
        if math.hypot(cx - hx, cy - hy) < HOLE_KEEPOUT_R:
            return False
    return True


def pad_gap(a, b):
    """Copper-to-copper distance of two pads on a layer they share (mm)."""
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        if a.IsOnLayer(lay) and b.IsOnLayer(lay):
            return pcbnew.ToMM(a.GetEffectiveShape(lay).GetClearance(b.GetEffectiveShape(lay)))
    return 1.0


def redraw_outline(board):
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Delete(d)
    bu.outline_rect(board, X0, Y0, X1, Y1, r=3.0)


def main():
    board = pcbnew.LoadBoard(PCB)
    for item in list(board.GetTracks()) + [z for z in board.Zones()
                                           if not z.GetIsRuleArea() or z.GetZoneName() == "hole_keepout"]:
        board.Delete(item)
    for d in list(board.GetDrawings()):
        if d.GetLayer() != pcbnew.Edge_Cuts and isinstance(d, pcbnew.PCB_TEXT):
            board.Delete(d)
    redraw_outline(board)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    placed = {}
    # template parts keep their positions (J1 socket on the bottom side, MH1-MH4)
    for ref in ("J1", "MH1", "MH2", "MH3", "MH4"):
        if ref in fps:
            placed[ref] = courtyard(fps[ref], 0.0)
    for ref, (x, y, rot, back) in FIXED.items():
        if ref not in fps:
            print("not on the board (yet):", ref)
            continue
        bu.place(board, ref, x, y, rot, back)
        r = courtyard(fps[ref])
        if not inside_board(r):
            print(f"WARNING {ref} fixed position leaves the board/keep-out: {r}")
        placed[ref] = r
    # USB-C: rotate so its pads sit inboard of the mouth (mouth on the left edge)
    if "J2" in fps:
        f = fps["J2"]
        for rot in (0, 90, 180, 270):
            bu.place(board, "J2", FIXED["J2"][0], FIXED["J2"][1], rot)
            xs = [pcbnew.ToMM(p.GetPosition().x) for p in f.Pads() if p.GetNumber() != "SH"]
            if min(xs) > FIXED["J2"][0] + 2.0:
                break
        placed["J2"] = courtyard(f)

    # lanes the escape stubs need (route_carrier.py): the SP4 pad row going up, the header's edge-row pins going
    # down below the inner row
    placed["sp4_lane"] = (145.2, 76.6, 154.1, 80.2)
    placed["header_band"] = (107.0, 49.4, 158.0, 51.2)
    placed["fb_stub"] = (113.2, 64.4, 114.8, 65.4)       # U2 FB escape (route_carrier.boost_escapes)
    placed["u2_gnd_via"] = (109.3, 61.7, 110.7, 63.1)    # U2 power-GND via
    placed["u6_escapes"] = (117.6, 72.6, 123.4, 76.4)     # MAX17048 escape stubs + its EP via

    # the boost copper areas are not for parts that do not belong to them
    for i, (_net, pts) in enumerate(BOOST_ZONES):
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        placed[f"zone{i}"] = (min(xs), min(ys), max(xs), max(ys))

    # nets per footprint
    nets = {ref: {p.GetNetname() for p in f.Pads() if p.GetNetname()} for ref, f in fps.items()}
    users = {}
    for ref, ns in nets.items():
        for n in ns:
            users.setdefault(n, set()).add(ref)

    def anchor(ref):
        """NEAR's choice, else the placed part sharing this part's most specific net (rails and GND last)."""
        if ref in NEAR:
            a = NEAR[ref]
            if a not in placed:
                return None, None
            shared = sorted(nets[ref] & nets[a], key=lambda n: (n == "GND", len(users[n])))
            return a, (shared[0] if shared else None)
        order = sorted(nets[ref], key=lambda n: (n in COMMON, len(users[n])))
        for n in order:
            cands = sorted(r for r in users[n] if r in placed and r != ref and r in fps
                           and not r.startswith("MH"))
            if cands:
                return cands[0], n
        return None, None

    def place_near(ref, a, n, region=None):
        if isinstance(a, tuple):
            ax, ay = a
        else:
            ax, ay = [pcbnew.ToMM(c) for c in (fps[a].GetPosition().x, fps[a].GetPosition().y)]
            for p in fps[a].Pads():   # aim at the anchor's pad on the shared net
                if n and p.GetNetname() == n:
                    ax, ay = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
                    break
        for ring in range(0, 120):
            rad = 1.0 + ring * 0.5
            steps = max(8, int(2 * math.pi * rad / 0.8))
            for k in range(steps):
                t = 2 * math.pi * k / steps
                x, y = round(ax + rad * math.cos(t), 2), round(ay + rad * math.sin(t), 2)
                for rot in (0, 90):
                    if region and not (region[0] <= x <= region[2] and region[1] <= y <= region[3]):
                        continue
                    bu.place(board, ref, x, y, rot)
                    r = courtyard(fps[ref])
                    if region and not (region[0] - 0.25 <= r[0] and r[2] <= region[2] + 0.25
                                       and region[1] - 0.25 <= r[1] and r[3] <= region[3] + 0.25):
                        continue
                    if inside_board(r) and not any(overlaps(r, o) for o in placed.values()):
                        placed[ref] = r
                        return True
        return False

    # clusters first, each inside its region; a member that does not fit falls back to the general pass
    for name, region, members in CLUSTERS:
        for ref, a in members:
            if ref not in fps or ref in placed:
                continue
            if isinstance(a, tuple):
                n = None
            else:
                shared = sorted(nets[ref] & nets.get(a, set()), key=lambda n: (n == "GND", len(users[n])))
                n = shared[0] if shared else None
            if not place_near(ref, a, n, region):
                print(f"cluster {name}: {ref} did not fit its region, placed in the general pass")

    # NEAR parts next (in dependency order), then everything else
    todo = sorted((r for r in fps if r not in placed), key=lambda r: (r not in NEAR, r))
    for _ in range(4):
        left = []
        for ref in todo:
            a, n = anchor(ref)
            if a is None or not place_near(ref, a, n):
                left.append(ref)
        if len(left) == len(todo):
            break
        todo = left
    for i, ref in enumerate(todo):   # park what did not fit to the right of the board, in plain view
        bu.place(board, ref, X1 + 8.0, Y0 + 4.0 + 5.0 * i, 0)
        print("UNPLACED (parked right of the board):", ref)

    # fine-pitch footprints (QFN/TDFN 0.5 mm, SOT-363, USB-C): their own pads sit closer than the lab's 0.3 mm,
    # which is inherent to the package; a footprint-level clearance of 0.15 mm covers exactly those pads
    # (pad-to-pour and pad-to-track still take the larger 0.3 mm net-class value)
    for ref, f in fps.items():
        pads = [p for p in f.Pads() if p.GetNumber()]
        gap = min((pad_gap(a, b) for i, a in enumerate(pads) for b in pads[i + 1:]
                   if a.GetNetname() != b.GetNetname()), default=1.0)
        if gap < bu.FAB_RULES["clearance"]:
            f.SetLocalClearance(bu.MM(0.15))
            print(f"fine pitch {ref}: own pad gap {gap:.3f} mm -> footprint clearance 0.15 mm")

    for net, pts in BOOST_ZONES:
        z = bu.zone(board, net, pcbnew.F_Cu, pts, clearance=0.2, min_width=0.2, name="boost_" + net.split("/")[-1])
        z.SetAssignedPriority(10)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)

    # ground pours on both layers (the SP4's own rule area keeps tracks out from under it on F.Cu)
    poly = [(X0 + 0.3, Y0 + 0.3), (X1 - 0.3, Y0 + 0.3), (X1 - 0.3, Y1 - 0.3), (X0 + 0.3, Y1 - 0.3)]
    bu.zone(board, "GND", pcbnew.F_Cu, poly, clearance=0.3, name="GND_top")
    bu.zone(board, "GND", pcbnew.B_Cu, poly, clearance=0.3, name="GND_bottom")
    for hx, hy in HOLES:   # copper-free land around the M2.5 holes (HAT spec 6.2 mm)
        ra = pcbnew.ZONE(board)
        ra.SetIsRuleArea(True)
        ra.SetDoNotAllowTracks(True)
        ra.SetDoNotAllowVias(True)
        ra.SetDoNotAllowZoneFills(True)
        ra.SetDoNotAllowPads(False)
        ra.SetDoNotAllowFootprints(False)
        ra.SetLayerSet(pcbnew.LSET.AllCuMask())
        o = ra.Outline()
        o.NewOutline()
        for k in range(24):
            t = 2 * math.pi * k / 24
            o.Append(bu.MM(hx + HOLE_KEEPOUT_R * math.cos(t)), bu.MM(hy + HOLE_KEEPOUT_R * math.sin(t)))
        ra.SetZoneName("hole_keepout")
        board.Add(ra)
    bu.text(board, "Team C Pi 3 A+ HAT - DRAFT for ET review - 19-Oct-26", 132.5, 66.0, layer=pcbnew.B_SilkS,
            size=1.0, thick=0.15)
    # review F6: the A+ has no reverse blocking on micro-USB; the boost would back-feed a supply plugged in there
    bu.text(board, "HAT ON: never plug the Pi's micro-USB", 132.5, 70.0, layer=pcbnew.B_SilkS, size=1.0, thick=0.15)
    bu.fill_zones(board)
    board.Save(PCB)


if __name__ == "__main__":
    main()
