"""Finish carrier rev B for the UPC lab (hw/teamc-carrier-lab) after route_carrier_lab.py: ground pour, ground
islands, wire links as parts, DRC.

    python3 hw/scripts/finish_carrier_lab.py

1. GND pour on the copper side (F.Cu): clearance 0.4 mm (the mill clears it), thermal reliefs, no copper within
   MOUNT_KEEPOUT of the M3 holes, and a no-fill rule area in the gap between the pads of every SMD part (Jimenez
   guide FR10: no pour between SMD pads; the pads themselves still get their spokes).
2. Ground islands: on one layer the signal tracks cut the pour into islands. Every "missing connection" on GND that
   DRC reports is joined with linkroute (a track, or a wire link where a track cannot get through); refill; repeat.
3. Wire links become parts: links.json -> build_carrier_lab.py adds W1, W2, ... to the schematic (one-pin symbol on
   the net) and teamc:WireLink_L<len>mm footprints to the board; here they are put on the link's two holes and the
   temporary vias and B.Cu wire tracks go.
4. Refill and DRC with schematic parity, all severities.
"""
import json
import math
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pcbnew  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import boardutil as bu  # noqa: E402
from linkroute import LinkRouter  # noqa: E402
from place_carrier_lab import DIR, H, MOUNT, MOUNT_KEEPOUT, ORIGIN, PCB, W, k  # noqa: E402

LINKS = os.path.join(DIR, "links.json")
DRC_RPT = os.path.join(DIR, "build", "drc.rpt")
POUR_CLEARANCE = 0.4
GND_W = 0.5
GND_LINK_COST = 8.0
HERE = os.path.dirname(os.path.abspath(__file__))


def holes(board):
    """(x, y) page mm of the M3 holes (board mounting holes and the breakout's standoff)."""
    pts = [k(x, y) for x, y in MOUNT.values()]
    h = bu.fp(board, "H30").GetPosition()
    pts.append((pcbnew.ToMM(h.x), pcbnew.ToMM(h.y)))
    return pts


def rule_area(board, name, pts, no_tracks=False):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetLayer(pcbnew.F_Cu)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(no_tracks)
    z.SetDoNotAllowVias(no_tracks)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(bu.MM(x), bu.MM(y))
    board.Add(z)
    return z


def smd_gaps(board):
    """No-fill rule areas between the pads of each SMD part on the copper side (FR10).

    In the part's own frame the pads split into two rows (left/right of its origin, or above/below); the area is
    the strip between the rows' inner edges, as long as the pads. Gaps too narrow for the pour (< 2 x clearance +
    0.3 mm) need none."""
    n = 0
    for f in board.GetFootprints():
        pads = list(f.Pads())
        if f.IsFlipped() or len(pads) < 2 or any(p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD for p in pads):
            continue
        ang = math.radians(f.GetOrientationDegrees())
        ox, oy = pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y)

        def to_local(x, y):
            dx, dy = x - ox, y - oy
            return dx * math.cos(ang) - dy * math.sin(ang), dx * math.sin(ang) + dy * math.cos(ang)

        def to_page(u, v):
            return ox + u * math.cos(ang) + v * math.sin(ang), oy - u * math.sin(ang) + v * math.cos(ang)

        boxes = []
        for p in pads:
            bb = p.GetBoundingBox()
            corners = [to_local(pcbnew.ToMM(x), pcbnew.ToMM(y)) for x in (bb.GetLeft(), bb.GetRight())
                       for y in (bb.GetTop(), bb.GetBottom())]
            us, vs = [c[0] for c in corners], [c[1] for c in corners]
            boxes.append((min(us), max(us), min(vs), max(vs)))
        spread_u = max(b[1] for b in boxes) - min(b[0] for b in boxes)
        spread_v = max(b[3] for b in boxes) - min(b[2] for b in boxes)
        axis = 0 if spread_u >= spread_v else 1          # the rows are split along this local axis
        lo = [b for b in boxes if (b[0] + b[1] if axis == 0 else b[2] + b[3]) < 0]
        hi = [b for b in boxes if (b[0] + b[1] if axis == 0 else b[2] + b[3]) >= 0]
        if not lo or not hi:
            continue
        if axis == 0:
            g0, g1 = max(b[1] for b in lo), min(b[0] for b in hi)
            s0, s1 = min(b[2] for b in boxes), max(b[3] for b in boxes)
            corners = [(g0, s0), (g1, s0), (g1, s1), (g0, s1)]
        else:
            g0, g1 = max(b[3] for b in lo), min(b[2] for b in hi)
            s0, s1 = min(b[0] for b in boxes), max(b[1] for b in boxes)
            corners = [(s0, g0), (s1, g0), (s1, g1), (s0, g1)]
        if g1 - g0 < 2 * POUR_CLEARANCE + 0.3:
            continue
        rule_area(board, f"{f.GetReference()}_no_pour", [to_page(u, v) for u, v in corners])
        n += 1
    return n


def pour(board):
    for z in list(board.Zones()):
        board.Delete(z)
    m = 0.5
    x0, y0 = ORIGIN
    bu.zone(board, "GND", pcbnew.F_Cu, [(x0 + m, y0 + m), (x0 + W - m, y0 + m), (x0 + W - m, y0 + H - m),
                                        (x0 + m, y0 + H - m)], clearance=POUR_CLEARANCE, name="GND_pour")
    for i, (x, y) in enumerate(holes(board)):
        r = MOUNT_KEEPOUT
        rule_area(board, f"M3_{i}", [(x + r * math.cos(t * math.pi / 8), y + r * math.sin(t * math.pi / 8))
                                     for t in range(16)], no_tracks=True)
    n = smd_gaps(board)
    bu.fill_zones(board)
    return n


def drc(board_path):
    out = subprocess.run(["kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-all", "-o", DRC_RPT,
                          board_path], capture_output=True, text=True)
    return out.stdout


def gnd_gaps():
    """[(item a, item b)] of the GND 'missing connection' pairs in the last DRC report; item = (kind, x, y, text)."""
    pairs = []
    lines = open(DRC_RPT, encoding="utf-8").read().splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("[unconnected_items]"):
            continue
        items = []
        for nxt in lines[i + 1:i + 5]:
            m = re.match(r"\s+@\(([-\d.]+) mm, ([-\d.]+) mm\): (.*)", nxt)
            if m:
                items.append((float(m.group(1)), float(m.group(2)), m.group(3)))
        if len(items) == 2 and all("[GND]" in it[2] for it in items):
            pairs.append(tuple(items))
    return pairs


def item_cells(r, board, item):
    """Router cells of a DRC item: a pad, or the filled pour island / track at the reported point."""
    x, y, text = item
    pos = bu.v(x, y)
    m = re.match(r"Pad (\S+) \[GND\] of (\S+)", text)
    if m:
        return r.pad_cells(bu.pad(board, m.group(2), m.group(1)))
    img = r._blank()
    d = ImageDraw.Draw(img)
    if text.startswith("Zone"):
        for z in board.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != "GND":
                continue
            polys = z.GetFilledPolysList(pcbnew.F_Cu)
            for i in range(polys.OutlineCount()):
                one = pcbnew.SHAPE_POLY_SET(polys.Outline(i))
                if one.Contains(pos) or one.Collide(pos, bu.MM(0.3)):
                    hole_free = pcbnew.SHAPE_POLY_SET()
                    hole_free.AddOutline(polys.Outline(i))
                    for h in range(polys.HoleCount(i)):
                        hole_free.AddHole(polys.Hole(i, h))
                    one = hole_free
                    one.Inflate(bu.MM(-0.25), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, bu.MM(0.01))
                    r._draw_polyset(d, one)
    else:
        for t in board.GetTracks():
            if t.GetNetname() == "GND" and t.HitTest(pos, bu.MM(0.1)):
                r._draw_polyset(d, r._item_poly(t, pcbnew.F_Cu, 0.0))
    ys, xs = np.nonzero(np.array(img, dtype=bool))
    return [(0, int(a), int(b)) for a, b in zip(xs, ys)]


def gnd_components(r, board):
    """Connected pieces of GND copper on the router's grid: the filled pour, GND tracks and pads; a wire link (vias
    joined by a B.Cu track) joins its two ends. Returns a list of cell lists (layer 0), largest first."""
    img = r._blank()
    d = ImageDraw.Draw(img)
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() == "GND":
            r._draw_polyset(d, z.GetFilledPolysList(pcbnew.F_Cu))
    for t in board.GetTracks():
        if t.GetNetname() == "GND" and (isinstance(t, pcbnew.PCB_VIA) or t.GetLayer() == pcbnew.F_Cu):
            r._draw_polyset(d, r._item_poly(t, pcbnew.F_Cu, 0.0))
    for f in board.GetFootprints():
        for pd in f.Pads():
            if pd.GetNetname() == "GND" and pd.IsOnLayer(pcbnew.F_Cu):
                r._draw_polyset(d, r._item_poly(pd, pcbnew.F_Cu, 0.0))
    grid = np.array(img, dtype=bool)
    label = np.zeros(grid.shape, dtype=np.int32)
    ny, nx = grid.shape
    comps = []
    for y0, x0 in zip(*np.nonzero(grid)):
        if label[y0, x0]:
            continue
        n = len(comps) + 1
        stack, cells = [(y0, x0)], []
        label[y0, x0] = n
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                Y, X = y + dy, x + dx
                if 0 <= Y < ny and 0 <= X < nx and grid[Y, X] and not label[Y, X]:
                    label[Y, X] = n
                    stack.append((Y, X))
        comps.append(cells)
    # wire links on GND join their ends
    parent = list(range(len(comps) + 1))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for t in board.GetTracks():
        if t.GetNetname() == "GND" and t.GetLayer() == pcbnew.B_Cu and not isinstance(t, pcbnew.PCB_VIA):
            ends = []
            for pt in (t.GetStart(), t.GetEnd()):
                x, y = r._px(pcbnew.ToMM(pt.x), pcbnew.ToMM(pt.y))
                ends.append(label[int(round(y)), int(round(x))])
            if all(ends):
                parent[find(ends[0])] = find(ends[1])
    merged = {}
    for i, cells in enumerate(comps, 1):
        merged.setdefault(find(i), []).extend(cells)
    out = [[(0, int(x), int(y)) for y, x in cells] for cells in merged.values()]
    return sorted(out, key=len, reverse=True)


def join_gnd(board, rounds=40):
    """Join every GND piece to the largest one (a track, or a wire link where none fits); refill between joins."""
    x0, y0 = ORIGIN
    made = 0
    for rnd in range(rounds):
        r = LinkRouter(board, x0, y0, x0 + W, y0 + H, grid=0.1, link_cost=GND_LINK_COST,
                       keep_out=[(x, y, MOUNT_KEEPOUT) for x, y in holes(board)])
        comps = gnd_components(r, board)
        print(f"  GND round {rnd + 1}: {len(comps)} pieces", flush=True)
        if len(comps) <= 1:
            return made
        main, small = comps[0], comps[-1]
        vblock = r.via_block("GND")
        tx, ty = main[len(main) // 2][1], main[len(main) // 2][2]
        for w in (0.8, GND_W):
            path = r.astar(small[::2], main[::3], r.obstacles("GND", w / 2), vblock, tx, ty)
            if path is not None:
                break
        if path is None:
            print(f"    no path for a piece of {len(small)} cells at {r._mm(small[0])}")
            return made
        r.commit(path, "GND", w)
        nl = sum(1 for i in range(1, len(path)) if path[i][0] != path[i - 1][0]) // 2
        print(f"    joined a piece at {tuple(round(c, 1) for c in r._mm(small[0]))}"
              + (f" with {nl} link(s)" if nl else ""), flush=True)
        made += 1
        bu.fill_zones(board)
    return made


def links_to_parts(board):
    """Write links.json from the B.Cu wire tracks, rebuild the schematic with W parts, place their footprints."""
    x0, y0 = ORIGIN
    wires = [t for t in board.GetTracks() if t.GetLayer() == pcbnew.B_Cu and not isinstance(t, pcbnew.PCB_VIA)]
    links = []
    for t in wires:
        a = (pcbnew.ToMM(t.GetStart().x) - x0, pcbnew.ToMM(t.GetStart().y) - y0)
        b = (pcbnew.ToMM(t.GetEnd().x) - x0, pcbnew.ToMM(t.GetEnd().y) - y0)
        a, b = sorted([tuple(round(c, 2) for c in a), tuple(round(c, 2) for c in b)])
        links.append({"net": t.GetNetname(), "a": list(a), "b": list(b)})
    links.sort(key=lambda lk: (lk["net"], lk["a"]))
    data = json.load(open(LINKS, encoding="utf-8")) if os.path.exists(LINKS) else {}
    data["links"] = links
    with open(LINKS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    # the temporary vias and wires go; the W footprints take their place
    for t in list(board.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA) or t.GetLayer() == pcbnew.B_Cu:
            board.Delete(t)
    board.Save(PCB)
    print(bu.run(sys.executable, os.path.join(HERE, "build_carrier_lab.py")))
    board = pcbnew.LoadBoard(PCB)
    for i, lk in enumerate(links, 1):
        ref = f"W{i}"
        (ax, ay), (bx, by) = k(*lk["a"]), k(*lk["b"])
        f = bu.fp(board, ref)
        for rot in (0, 90, 180, 270):
            bu.place(board, ref, 0, 0, rot, True)
            pads = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in f.Pads()]
            d0 = (pads[1][0] - pads[0][0], pads[1][1] - pads[0][1])
            if abs(d0[0] - (bx - ax)) < 0.05 and abs(d0[1] - (by - ay)) < 0.05:
                bu.place(board, ref, ax - pads[0][0], ay - pads[0][1], rot, True)
                break
        else:
            raise SystemExit(f"{ref}: no orientation for {lk}")
    return board, links


def main():
    board = pcbnew.LoadBoard(PCB)
    n = pour(board)
    print(f"pour: {n} SMD gap rule areas")
    made = join_gnd(board)
    print(f"GND joins: {made}")
    board, links = links_to_parts(board)
    print(f"{len(links)} wire links -> W1..W{len(links)}")
    bu.fill_zones(board)
    board.Save(PCB)
    print(drc(PCB))


if __name__ == "__main__":
    main()
