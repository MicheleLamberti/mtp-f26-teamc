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
    "U7": (149.5, 89.5, 0, False),     # SP4 bottom-right, pad row up, IPEX near the bottom edge (Pi x 42-57, y 1-19)
    "J2": (103.4, 81.0, 270, False),   # USB-C mouth on the left edge (rotation checked below)
    "J20": (109.0, 93.5, 0, False),    # battery lead, bottom-left
    "J21": (117.0, 93.5, 0, False),    # 2nd cell (DNP)
    "J22": (124.5, 95.5, 0, False),    # power toggle lead
    "J10": (131.0, 95.5, 0, False),    # GO/STOP button lead
    "J11": (138.0, 95.5, 0, False),    # role toggle lead
    "J12": (123.5, 88.5, 0, False),    # mode toggle lead
    "U2": (112.5, 62.0, 0, False),     # boost next to header pins 2/4 (Pi top-left)
    "L1": (106.0, 62.0, 90, False),
    "Q4": (112.0, 54.0, 0, False),     # ideal diode right below header pins 2/4
    "U3": (116.0, 54.0, 0, False),
    "U4": (141.0, 78.0, 0, False),     # radio LDO beside the SP4
    "U5": (136.0, 72.0, 0, False),     # buck-boost option (DNP)
    "U1": (110.0, 75.0, 0, False),     # charger near the USB-C
    "U6": (114.0, 86.5, 0, False),     # fuel gauge near the battery lead (Kelvin)
    "Q1": (108.5, 87.0, 0, False),
    "Q2": (119.0, 80.0, 0, False),
    "U11": (134.0, 90.0, 0, False),    # ESD at the UI connectors
    "U12": (108.0, 81.5, 0, False),    # ESD at the USB-C / power toggle
    "J13": (121.0, 57.0, 90, False),   # UART console
    "SW1": (128.0, 77.0, 0, False),    # bench button
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

    # nets per footprint
    nets = {ref: {p.GetNetname() for p in f.Pads() if p.GetNetname()} for ref, f in fps.items()}
    users = {}
    for ref, ns in nets.items():
        for n in ns:
            users.setdefault(n, set()).add(ref)

    def anchor(ref):
        """The placed part sharing this part's most specific net (fewest users; rails and GND last)."""
        order = sorted(nets[ref], key=lambda n: (n in COMMON, len(users[n])))
        for n in order:
            cands = sorted(r for r in users[n] if r in placed and r != ref and not r.startswith("MH"))
            if cands:
                return cands[0], n
        return None, None

    todo = [r for r in sorted(fps) if r not in placed]
    for _ in range(3):
        left = []
        for ref in todo:
            a, n = anchor(ref)
            if a is None:
                left.append(ref)
                continue
            ax, ay = [pcbnew.ToMM(c) for c in (fps[a].GetPosition().x, fps[a].GetPosition().y)]
            # the anchor pad on the shared net, if any, is the better target
            for p in fps[a].Pads():
                if p.GetNetname() == n:
                    ax, ay = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
                    break
            ok = False
            for ring in range(0, 80):
                rad = 1.0 + ring * 0.5
                steps = max(8, int(2 * math.pi * rad / 0.8))
                for k in range(steps):
                    t = 2 * math.pi * k / steps
                    x, y = round(ax + rad * math.cos(t), 2), round(ay + rad * math.sin(t), 2)
                    for rot in (0, 90):
                        bu.place(board, ref, x, y, rot)
                        r = courtyard(fps[ref])
                        if inside_board(r) and not any(overlaps(r, o) for o in placed.values()):
                            placed[ref] = r
                            ok = True
                            break
                    if ok:
                        break
                if ok:
                    break
            if not ok:
                left.append(ref)
                print("could not place", ref)
        todo = left
        if not todo:
            break
    for ref in todo:
        print("UNPLACED", ref)

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
        ra.SetDoNotAllowPads(True)
        ra.SetDoNotAllowFootprints(False)
        ra.SetLayerSet(pcbnew.LSET.AllCuMask())
        o = ra.Outline()
        o.NewOutline()
        for k in range(24):
            t = 2 * math.pi * k / 24
            o.Append(bu.MM(hx + HOLE_KEEPOUT_R * math.cos(t)), bu.MM(hy + HOLE_KEEPOUT_R * math.sin(t)))
        ra.SetZoneName("hole_keepout")
        board.Add(ra)
    bu.text(board, "Team C Pi 3 A+ HAT - DRAFT for ET review - 19-Oct-26", 132.5, 98.6, size=0.8, thick=0.12)
    bu.fill_zones(board)
    board.Save(PCB)


if __name__ == "__main__":
    main()
