"""Finish the carrier's routing with Freerouting (run after route_carrier.py, which routes power + SPI/radio).

    python3 hw/scripts/autoroute_carrier.py --java <java> --freerouting <freerouting.jar> [--keep power] [--passes 30]

Freerouting (https://github.com/freerouting/freerouting, v2.5 needs Java 25) is a Specctra autorouter: the board goes
out as a .dsn, comes back as a .ses session. What the script does:
  1. export a copy of the board: the copper of the --keep nets locked (the script-routed power path, copper areas
     and, with "radio", SPI), the other nets' escape stubs and the grid GND stitching vias deleted, the GND pours
     removed (GND is the pour on both layers; its net class "Ground" is ignored by Freerouting); the boost copper
     areas go out as planes of their nets, so other nets keep out;
  2. Freerouting routes the rest;
  3. merge: the session is imported into a scratch copy, and only the tracks and vias of the autorouted nets are
     copied into the real board. KiCad's import replaces every track with the session's, and Freerouting's session
     does not carry the fixed copper faithfully (19-Oct test: the power path came back cut), so the kept nets and
     GND are never taken from it; tracks Freerouting necked down below 0.2 mm are widened back to 0.2 mm;
  4. the pours are refilled, GND stitching vias go back where both pours remain, GND pads the pours miss get a via.
Then run DRC (kicad-cli pcb drc --schematic-parity). Work files go to --work (default build/autoroute/, git-ignored).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402
from gridroute import Router  # noqa: E402
from place_carrier import PCB, X0, X1, Y0, Y1  # noqa: E402
from route_carrier import FINE_NETS, FINE_REFS, POWER, RADIO, isolated_gnd_pads  # noqa: E402

BUILD = os.path.join(os.path.dirname(PCB), "build")
MIN_TRACK = 0.2
CLEARANCE_PAD = 20       # um added to the DSN clearances (0.2 mm classes)
FINE_PAD = 10            # um added to the 0.15 mm (fine-pitch) classes
EDGE_UM = 550            # Freerouting's copper-to-edge clearance (board rule 0.5 mm)
_BOARDS = []   # every loaded board stays referenced: pcbnew 10.0.6 breaks (track list, segfaults) when one is freed


def load(path):
    _BOARDS.append(pcbnew.LoadBoard(path))
    return _BOARDS[-1]


def kept_nets(board, groups):
    keep = {"GND"}
    if "power" in groups:
        keep |= {n for n, _ in POWER} | {"/power/SW_NODE"}
    if "radio" in groups:
        keep |= {n for n, _ in RADIO}
    if "all" in groups:
        keep |= {str(n) for n in board.GetNetsByName().keys()}
    return keep


BRANCH_W = 0.4     # mm: power tracks this thin are branches (Kelvin, gate, fine-pitch necks), not the main path
_branch = {"pts": [], "radius": 0.0}   # finishing pass: power branches near these pads are rerouted too


def near_pts(x1, y1, x2, y2):
    r2 = _branch["radius"] ** 2
    for x, y in _branch["pts"]:
        dx, dy = x2 - x1, y2 - y1
        k = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy or 1)))
        if (x1 + k * dx - x) ** 2 + (y1 + k * dy - y) ** 2 <= r2:
            return True
    return False


def strip(keep, out, lock=False):
    """The board without the grid stitching vias (GND vias not at a GND track end and not in a GND pad) and
    without the tracks/vias of the nets that are not kept, written to `out` (+ project file) and loaded from there.
    The deletion is a text edit of the top-level segment/via blocks: deleting many tracks through pcbnew's SWIG
    API (10.0.6) corrupts its track list and then segfaults. In a finishing pass the thin power branches near
    the stuck pads go too (_branch). Returns (board, dropped tracks, stitching vias, nets with dropped branches)."""
    board = load(PCB)
    ends = set()
    for t in board.GetTracks():
        if t.GetNetname() == "GND" and t.GetClass() != "PCB_VIA":
            ends |= {(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)}
    pads = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() == "GND"]
    stitch = {(round(pcbnew.ToMM(t.GetPosition().x), 4), round(pcbnew.ToMM(t.GetPosition().y), 4))
              for t in board.GetTracks()
              if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"
              and (t.GetPosition().x, t.GetPosition().y) not in ends
              and not any(p.HitTest(t.GetPosition()) for p in pads)}
    with open(PCB, encoding="utf-8") as f:
        lines = f.read().split("\n")
    kept, block, dropped, dropped_stitch, partial = [], None, 0, 0, set()
    for line in lines:
        if block is None and line in ("\t(segment", "\t(via", "\t(arc"):
            block = [line]
            continue
        if block is None:
            kept.append(line)
            continue
        block.append(line)
        if line != "\t)":
            continue
        text = "\n".join(block)
        net = re.search(r'\(net "([^"]*)"\)', text)
        net = net.group(1) if net else ""
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", text)
        if block[0] == "\t(via" and net == "GND" and at and \
                (round(float(at.group(1)), 4), round(float(at.group(2)), 4)) in stitch:
            dropped_stitch += 1
        elif net not in keep:
            dropped += 1
        elif block[0] == "\t(segment" and net != "GND" and _branch["radius"] > 0 and \
                float(re.search(r"\(width ([\d.]+)\)", text).group(1)) <= BRANCH_W + 1e-6 and \
                near_pts(*map(float, re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", text).groups()),
                         *map(float, re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", text).groups())):
            dropped += 1
            partial.add(net)
        else:
            kept += block
        block = None
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(kept))
    shutil.copy(os.path.splitext(PCB)[0] + ".kicad_pro", os.path.splitext(out)[0] + ".kicad_pro")
    board = load(out)
    if lock:
        for t in board.GetTracks():
            t.SetLocked(True)
    return board, dropped, dropped_stitch, partial


def export_dsn(dsn, keep, work):
    board, dropped, stitch, partial = strip(keep, os.path.join(work, "export.kicad_pcb"), lock=True)
    print(f"kept {len(board.GetTracks())} tracks/vias ({len(keep)} nets), dropped {dropped} + {stitch} "
          "GND stitching vias" + (f"; power branches freed: {', '.join(sorted(partial))}" if partial else ""))
    for z in [z for z in board.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()]:
        board.Delete(z)   # not Remove(): that leaves pcbnew's lists unusable from Python
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("DSN export failed")
    # Freerouting rounds its clearances down by a few um (0.195 mm against 0.2 mm), and the merge widens its necked
    # tracks to 0.2 mm: the clearances go out a little larger. Not at the 0.5 mm-pitch parts: KiCad lets their own
    # pins sit at 0.15 mm (a footprint clearance the DSN does not carry), and Freerouting would not enter pins it
    # sees as violations. Ground (never routed, it only meets pins) goes out at the fine-pitch 0.15 mm.
    with open(dsn, encoding="utf-8") as f:
        s = f.read()

    def pad(m):
        c = float(m.group(1))
        return f"(clearance {c + (CLEARANCE_PAD if c > 150 else FINE_PAD):g})"

    s = re.sub(r"\(clearance (\d+(?:\.\d+)?)\)", pad, s)
    s = re.sub(r"(\(class Ground\b.*?\(clearance )[\d.]+\)", r"\g<1>150)", s, flags=re.S)
    with open(dsn, "w", encoding="utf-8") as f:
        f.write(s)
    print("exported", dsn)


def neighbours(nets, radius):
    """Nets with copper within `radius` mm of a pad of `nets`."""
    if radius <= 0:
        return set()
    board = load(PCB)
    pts = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
           for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() in nets]
    near = set()
    for t in board.GetTracks():
        a = (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y))
        b = (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
        for x, y in pts:
            dx, dy = b[0] - a[0], b[1] - a[1]
            k = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy or 1)))
            if (a[0] + k * dx - x) ** 2 + (a[1] + k * dy - y) ** 2 <= radius ** 2:
                near.add(t.GetNetname())
                break
    return near - {"GND", ""}


def unconnected_nets():
    """Nets KiCad's DRC reports with unconnected items (GND left out: it is the pours' job)."""
    rpt = os.path.join(BUILD, "drc_unconnected.rpt")
    bu.run("kicad-cli", "pcb", "drc", "-o", rpt, PCB)
    nets, section = set(), ""
    with open(rpt, encoding="utf-8") as f:
        for line in f:
            if line.startswith("["):
                section = line.split("]")[0][1:]
            elif section == "unconnected_items":
                m = re.search(r"\[([^\]]+)\]", line)
                if m and m.group(1) != "GND":
                    nets.add(m.group(1))
    return nets


EP_TIES = {"U6": ("9", ["1", "4", "6"]),    # MAX17048: CTG, GND, QSTRT to the exposed pad
           "U5": ("11", ["3", "9"])}          # TPS63001 (DNP option): PGND, GND


def ep_ties(board):
    """A 0.2 mm track from each GND pin of the QFN/TDFN parts into their exposed pad, under the package: the EP via
    then joins the pins' ground (the pours cannot reach between 0.5 mm-pitch pins)."""
    made = 0
    have = {(t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) for t in board.GetTracks()}
    for ref, (ep, pins) in EP_TIES.items():
        e = bu.pad(board, ref, ep).GetBoundingBox()
        inset = pcbnew.FromMM(0.15)
        for num in pins:
            c = bu.pad(board, ref, num).GetPosition()
            x = min(max(c.x, e.GetLeft() + inset), e.GetRight() - inset)
            y = min(max(c.y, e.GetTop() + inset), e.GetBottom() - inset)
            if (c.x, c.y, x, y) in have:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(c)
            t.SetEnd(pcbnew.VECTOR2I(x, y))
            t.SetWidth(pcbnew.FromMM(0.2))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(board.FindNet("GND"))
            board.Add(t)
            made += 1
    return made


class GndPieces:
    """Ground connectivity as KiCad sees it: KiCad's connectivity gives the main GND cluster (the largest cluster
    reached from the header's GND pins); a piece of the filled GND pours (either layer) is main when it touches an
    item of that cluster (a pad or via through a ring just outside it, i.e. its thermal spokes, or a track end),
    and an island when it only touches items outside it. Pieces touching nothing are removed by the fill anyway."""

    def __init__(self, board):
        mm = pcbnew.FromMM
        self.pieces = []                      # (layer, poly set, outline index, area)
        for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
            for z in board.Zones():
                if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.IsOnLayer(lay):
                    ps = z.GetFilledPolysList(lay)
                    for i in range(ps.OutlineCount()):
                        self.pieces.append((lay, ps, i, ps.Outline(i).Area()))
        board.BuildConnectivity()
        conn = board.GetConnectivity()
        best = set()
        for p in bu.fp(board, "J1").Pads():
            if p.GetNetname() == "GND":
                got = {it.m_Uuid.AsString() for it in conn.GetConnectedItems(p)} | {p.m_Uuid.AsString()}
                if len(got) > len(best):
                    best = got
        both = (pcbnew.F_Cu, pcbnew.B_Cu)
        items = []                            # (connected?, layers, centre, half x, half y)
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() == "GND":
                    bb = p.GetBoundingBox()
                    items.append((p.m_Uuid.AsString() in best, [lay for lay in both if p.IsOnLayer(lay)],
                                  p.GetPosition(), bb.GetWidth() // 2 + mm(0.08), bb.GetHeight() // 2 + mm(0.08)))
        for t in board.GetTracks():
            if t.GetNetname() != "GND":
                continue
            ok = t.m_Uuid.AsString() in best
            if t.GetClass() == "PCB_VIA":
                r = t.GetWidth(pcbnew.F_Cu) // 2 + mm(0.05)
                items.append((ok, both, t.GetPosition(), r, r))
            else:
                items += [(ok, [t.GetLayer()], t.GetStart(), 0, 0), (ok, [t.GetLayer()], t.GetEnd(), 0, 0)]
        self.is_main = [False] * len(self.pieces)
        self.is_island = [False] * len(self.pieces)
        for k, (lay, _, _, _) in enumerate(self.pieces):
            for ok, layers, c, hx, hy in items:
                if lay not in layers or (ok and self.is_main[k]) or (not ok and self.is_island[k]):
                    continue
                ring = [(0, 0), (hx, 0), (-hx, 0), (0, hy), (0, -hy), (hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]
                if any(self.inside(k, pcbnew.VECTOR2I(c.x + dx, c.y + dy)) for dx, dy in ring):
                    if ok:
                        self.is_main[k] = True
                    else:
                        self.is_island[k] = True
        if self.pieces and not any(self.is_main):
            self.is_main[max(range(len(self.pieces)), key=lambda k: self.pieces[k][3])] = True
        self.main = True if self.pieces else None

    def inside(self, k, pt):
        _, ps, i, _ = self.pieces[k]
        return ps.Outline(i).PointInside(pt) and not any(ps.Hole(i, h).PointInside(pt)
                                                        for h in range(ps.HoleCount(i)))

    def islands(self):
        return [k for k in range(len(self.pieces)) if self.is_island[k] and not self.is_main[k]]

    def members(self, k):
        return [k]

    def bbox_mm(self, k):
        bb = self.pieces[k][1].Outline(self.pieces[k][2]).BBox()
        return (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()),
                pcbnew.ToMM(bb.GetBottom()))


def gnd_router(board):
    return Router(board, X0, Y0, X1, Y1, grid=0.05, margin=0.04, clearance=bu.FAB_RULES["clearance"],
                  fine_refs=FINE_REFS, fine_nets=FINE_NETS)


def stitch_fragments(board):
    """A GND via for every group of pour pieces not joined to the main ground, at a free spot inside one of its
    pieces where the main group's pour is on the other layer. Returns the vias placed."""
    g = GndPieces(board)
    if g.main is None:
        return 0
    r = gnd_router(board)
    blocked = r.via_block("GND")
    ring = [(0.45 * dx, 0.45 * dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7),
                                                  (0.7, -0.7), (-0.7, -0.7))]
    placed = 0
    for isl in g.islands():
        spot = None
        for i in g.members(isl):
            lay = g.pieces[i][0]
            targets = [j for j, pc in enumerate(g.pieces) if pc[0] != lay and g.is_main[j]]
            x1, y1, x2, y2 = g.bbox_mm(i)
            y = y1
            while spot is None and y <= y2:
                x = x1
                while x <= x2:
                    ix, iy = (int(round(c)) for c in r._px(x, y))
                    if 0 <= ix < r.nx and 0 <= iy < r.ny and not blocked[iy, ix] and all(
                            g.inside(i, bu.v(x + dx, y + dy)) and
                            any(g.inside(j, bu.v(x + dx, y + dy)) for j in targets) for dx, dy in ring):
                        spot = (x, y)
                        break
                    x += 0.1
                y += 0.1
            if spot:
                break
        if spot:
            bu.via(board, *spot, "GND")
            ix, iy = (int(round(c)) for c in r._px(*spot))
            k = int((0.8 + 0.5) / r.g) + 1          # the next via keeps the hole-to-hole distance from this one
            blocked[max(iy - k, 0):iy + k + 1, max(ix - k, 0):ix + k + 1] = True
            placed += 1
    return placed


def main_cells(g, r, box, reach):
    """Grid cells (layer, x, y) inside the main ground's pours, within `reach` mm of box (x1, y1, x2, y2)."""
    cells = []
    for j, (lay, _, _, _) in enumerate(g.pieces):
        if not g.is_main[j]:
            continue
        li = 0 if lay == pcbnew.F_Cu else 1
        y = max(box[1] - reach, Y0)
        while y <= min(box[3] + reach, Y1):
            x = max(box[0] - reach, X0)
            while x <= min(box[2] + reach, X1):
                if g.inside(j, bu.v(x, y)):
                    ix, iy = (int(round(c)) for c in r._px(x, y))
                    if 0 <= ix < r.nx and 0 <= iy < r.ny:
                        cells.append((li, ix, iy))
                x += 0.25
            y += 0.25
    return cells


def link(r, sources, targets, box, obs, vblock, width):
    if not sources or not targets:
        return False
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    tx, ty = min(targets, key=lambda c: (r.x0 + c[1] * r.g - cx) ** 2 + (r.y0 + c[2] * r.g - cy) ** 2)[1:]
    path = r.astar(sources, targets, obs, vblock, tx, ty, limit=2_000_000)
    if path:
        r.commit(path, "GND", width)
    return bool(path)


def link_pads(board, pads, width=0.25, reach=8.0):
    """A GND track (vias allowed) from each pad to the main ground's pours; returns the pads linked."""
    g = GndPieces(board)
    if g.main is None:
        return []
    done = []
    for p in pads:
        r = gnd_router(board)
        obs, vblock = r.obstacles("GND", width / 2), r.via_block("GND")
        x, y = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
        if link(r, r.pad_cells(p), main_cells(g, r, (x, y, x, y), reach), (x, y, x, y), obs, vblock, width):
            done.append(p)
    return done


def link_islands(board, width=0.3, reach=8.0):
    """A GND track (vias allowed) from each island group the stitching could not reach to the main ground: A* from
    cells inside the island's copper to cells inside the main pours within `reach` mm. Returns the links made."""
    g = GndPieces(board)
    if g.main is None:
        return 0
    made = 0
    for isl in g.islands():
        r = gnd_router(board)                 # fresh: the previous link's tracks and vias are obstacles now
        obs, vblock = r.obstacles("GND", width / 2), r.via_block("GND")
        sources, box = [], None
        for i in g.members(isl):
            li = 0 if g.pieces[i][0] == pcbnew.F_Cu else 1
            x1, y1, x2, y2 = g.bbox_mm(i)
            box = (min(box[0], x1), min(box[1], y1), max(box[2], x2), max(box[3], y2)) if box else (x1, y1, x2, y2)
            y = y1
            while y <= y2:
                x = x1
                while x <= x2:
                    if g.inside(i, bu.v(x, y)):
                        ix, iy = (int(round(c)) for c in r._px(x, y))
                        if 0 <= ix < r.nx and 0 <= iy < r.ny:
                            sources.append((li, ix, iy))
                    x += 0.25
                y += 0.25
        if link(r, sources, main_cells(g, r, box, reach), box, obs, vblock, width):
            made += 1
    return made


def merge_ses(ses, keep, work):
    """Takes the session's tracks and vias of every net not in `keep`."""
    scratch = os.path.join(work, "session.kicad_pcb")
    shutil.copy(PCB, scratch)
    shutil.copy(os.path.splitext(PCB)[0] + ".kicad_pro", os.path.splitext(scratch)[0] + ".kicad_pro")
    routed = load(scratch)
    if not pcbnew.ImportSpecctraSES(routed, ses):
        sys.exit("SES import failed")
    board, dropped, stitch, partial = strip(keep, os.path.join(work, "base.kicad_pcb"))
    added = {"tracks": 0, "vias": 0}
    for t in routed.GetTracks():
        net = t.GetNetname()
        if not net or (net in keep and net not in partial):
            continue
        if t.GetClass() == "PCB_VIA":
            n = pcbnew.PCB_VIA(board)
            n.SetPosition(t.GetPosition())
            n.SetWidth(t.GetWidth(pcbnew.F_Cu))
            n.SetDrill(t.GetDrillValue())
            added["vias"] += 1
        else:
            n = pcbnew.PCB_TRACK(board)
            n.SetStart(t.GetStart())
            n.SetEnd(t.GetEnd())
            # Freerouting necks down at small pads (0.15-0.19 mm); the board minimum is 0.2 mm
            n.SetWidth(max(t.GetWidth(), pcbnew.FromMM(MIN_TRACK)))
            n.SetLayer(t.GetLayer())
            added["tracks"] += 1
        n.SetNet(board.FindNet(net))
        board.Add(n)
    print(f"merged {added['tracks']} tracks + {added['vias']} vias of the autorouted nets "
          f"(replacing {dropped} stub tracks); {stitch} stitching vias to redo")
    bu.fill_zones(board)
    # the new tracks cut the pours: stitching where both layers still have ground, then a via next to every
    # GND pad the pours no longer reach
    r = Router(board, X0, Y0, X1, Y1, grid=0.05, margin=0.04, clearance=bu.FAB_RULES["clearance"],
               fine_refs=FINE_REFS, fine_nets=FINE_NETS)
    vias = r.stitch("GND", pitch=4.0)
    bu.fill_zones(board)
    gone = r.prune(vias, "GND")
    bu.fill_zones(board)
    print(f"GND stitching vias: {len(vias) - gone}")
    print(f"GND pins tied to exposed pads: {ep_ties(board)}")
    bu.fill_zones(board)
    for _ in range(3):
        n = stitch_fragments(board)
        bu.fill_zones(board)
        print(f"GND vias joining pour islands: {n}")
        if not n:
            break
    board.Save(PCB)
    for _ in range(3):
        lonely = isolated_gnd_pads(board)
        if not lonely:
            break
        r = Router(board, X0, Y0, X1, Y1, grid=0.05, margin=0.04, clearance=bu.FAB_RULES["clearance"],
                   fine_refs=FINE_REFS, fine_nets=FINE_NETS)
        names = [f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in lonely]
        placed = [n for p, n in zip(lonely, names) if r.via_to(p, "GND", reach=5.0)]
        print("GND vias at isolated pads:", ", ".join(placed) or "none",
              "| no room:", ", ".join(n for n in names if n not in placed) or "none")
        bu.fill_zones(board)
        board.Save(PCB)
    board.Save(PCB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--java", default="java")
    ap.add_argument("--freerouting", default="freerouting.jar")
    ap.add_argument("--passes", type=int, default=30)
    ap.add_argument("--work", default=os.path.join(BUILD, "autoroute"))
    ap.add_argument("--stage", default="export,route,merge")
    ap.add_argument("--keep", default="power",
                    help="script-routed copper kept as it is: power, radio (SPI), all (every existing track: a "
                         "finishing pass that takes only the nets still unconnected)")
    ap.add_argument("--fr-args", default="", help="extra Freerouting arguments, e.g. '-us hybrid -is random'")
    ap.add_argument("--rip", type=float, default=0.0,
                    help="with --keep all: also reroute the signal nets passing within this many mm of the pads "
                         "of the unconnected nets")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    dsn = os.path.join(a.work, "carrier.dsn")
    ses = os.path.join(a.work, "carrier.ses")
    stages, groups = a.stage.split(","), a.keep.split(",")
    keep = kept_nets(load(PCB), groups)
    if "all" in groups:
        # finishing pass: the nets still unconnected, and the signal nets passing near their pads, are rerouted
        only = unconnected_nets()
        near = neighbours(only, a.rip) - kept_nets(load(PCB), ["power"])
        board = load(PCB)
        _branch["pts"] = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
                          for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() in only]
        _branch["radius"] = a.rip
        keep -= only | near
        print("still unconnected:", ", ".join(sorted(only)) or "none")
        print(f"ripped up within {a.rip} mm:", ", ".join(sorted(near - only)) or "none")
    if "export" in stages:
        export_dsn(dsn, keep, a.work)
    if "route" in stages:
        if os.path.exists(ses):
            os.remove(ses)
        cmd = [a.java, "-jar", a.freerouting, "-de", dsn, "-do", ses, "-mp", str(a.passes),
               "--gui.enabled=false", "--router.autorouter.ignore_net_classes=Ground",   # GND = the pours
               f"--router.copper_to_edge_clearance_um={EDGE_UM}"]
        cmd += a.fr_args.split()
        print(" ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)
        if not os.path.exists(ses):
            sys.exit("Freerouting wrote no session")
    if "merge" in stages:
        merge_ses(ses, keep, a.work)


if __name__ == "__main__":
    main()
