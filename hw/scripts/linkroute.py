"""Single-sided grid router with wire links (carrier rev B, UPC lab).

Copper is F.Cu only. Where a net cannot get through on one layer, it may jump with a wire link: a straight bare wire
on the component side (B), horizontal or vertical, between two unplated 1.0 mm holes with 2.0 mm pads. While routing,
a link is a pair of vias joined by a B.Cu track (so gridroute's commit/rip work unchanged); route_carrier_lab.py turns
each one into a teamc:WireLink footprint afterwards. A link costs `link_cost` mm on top of its length, so the search
only takes one when the copper detour is longer than that.

Link wires may not pass under a back-side part (courtyards on B.CrtYd), over a hole, or near another link; their holes
may not sit under a part either.
"""
import heapq
import math

import numpy as np
import pcbnew
from PIL import Image, ImageDraw

import gridroute

MM = pcbnew.FromMM
TO = pcbnew.ToMM
DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
WIRE_CY = 1.25        # courtyard half-width of teamc:WireLink (gen_lab.wire_link)


class LinkRouter(gridroute.Router):
    def __init__(self, board, x0, y0, x1, y1, grid=0.1, clearance=0.3, edge=0.5, link_cost=30.0, link_min=5.0,
                 link_max=40.0, lattice=0.5, link_pad=2.0, link_drill=1.0, margin=0.08, keep_out=(), keep_rects=()):
        super().__init__(board, x0, y0, x1, y1, grid=grid, clearance=clearance, edge=edge, via_d=link_pad,
                         via_drill=link_drill, margin=margin)
        self.link_cost = link_cost / grid
        self.link_min, self.link_max = int(round(link_min / grid)), int(round(link_max / grid))
        self.lat = int(round(lattice / grid))
        self.keep_out = keep_out          # [(x, y, r)] circles where no copper may go (mounting holes)
        self.keep_rects = keep_rects      # [(x1, y1, x2, y2)] areas the router's tracks keep out of (links may cross)
        self.tree = {}                    # net -> cells already connected (pads and copper made so far)

    # ---- grids --------------------------------------------------------------------------------------------------
    def _blank(self):
        return Image.new("1", (self.nx, self.ny), 0)

    def _keep_out(self, d, extra):
        for x, y, r in self.keep_out:
            px, py = self._px(x, y)
            rr = (r + extra) / self.g
            d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=1)
        for x1, y1, x2, y2 in self.keep_rects:
            a, b = self._px(x1, y1), self._px(x2, y2)
            d.rectangle([a[0], a[1], b[0], b[1]], fill=1)

    def back_bodies(self, inflate, front=False):
        """Courtyards of the parts on the back side (bodies the link wire must not pass under), or with
        front=True of the SMD parts on the copper side (a link hole must not sit under one)."""
        img = self._blank()
        d = ImageDraw.Draw(img)
        for f in self.b.GetFootprints():
            if f.IsFlipped() == front or f.GetReference().startswith("W"):
                continue
            ps = pcbnew.SHAPE_POLY_SET(f.GetCourtyard(pcbnew.F_CrtYd if front else pcbnew.B_CrtYd))
            if ps.OutlineCount():
                ps.Inflate(MM(inflate), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
                self._draw_polyset(d, ps)
        return np.array(img, dtype=bool)

    def holes(self, extra):
        img = self._blank()
        d = ImageDraw.Draw(img)
        for f in self.b.GetFootprints():
            for p in f.Pads():
                if p.GetDrillSize().x > 0:
                    x, y = self._px(TO(p.GetPosition().x), TO(p.GetPosition().y))
                    r = (TO(p.GetDrillSize().x) / 2 + extra) / self.g
                    d.ellipse([x - r, y - r, x + r, y + r], fill=1)
        for t in self.b.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA):
                x, y = self._px(TO(t.GetPosition().x), TO(t.GetPosition().y))
                r = (TO(t.GetDrillValue()) / 2 + extra) / self.g
                d.ellipse([x - r, y - r, x + r, y + r], fill=1)
        return np.array(img, dtype=bool)

    def obstacles(self, net, half_width, soft=()):
        """[F.Cu track-centre grid, B link-wire grid]."""
        f = super().obstacles(net, half_width, soft)[0]
        img = self._blank()
        self._keep_out(ImageDraw.Draw(img), half_width + self.c)
        f = f | np.array(img, dtype=bool)
        # link wires: away from bodies, holes, other links (any net) and the edge
        # a W footprint's courtyard is 1.25 mm either side of its wire and around its holes
        wire = self.back_bodies(WIRE_CY + 0.05) | self.holes(0.6)
        img = self._blank()
        d = ImageDraw.Draw(img)
        for t in self.b.GetTracks():
            if t.GetLayer() == pcbnew.B_Cu and not isinstance(t, pcbnew.PCB_VIA):
                ps = pcbnew.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(ps, pcbnew.B_Cu, MM(2 * WIRE_CY + 0.1), MM(0.01), pcbnew.ERROR_OUTSIDE)
                self._draw_polyset(d, ps)
        wire |= np.array(img, dtype=bool)
        k = int(math.ceil(1.5 / self.g))
        wire[:k, :] = wire[-k:, :] = True
        wire[:, :k] = wire[:, -k:] = True
        return [f, wire]

    def via_block(self, net, soft=()):
        """True where a link hole (2.0 mm pad) of `net` may not sit."""
        f = super().obstacles(net, self.via_d / 2, soft)[0]
        img = self._blank()
        self._keep_out(ImageDraw.Draw(img), self.via_d / 2 + self.c)
        return (f | np.array(img, dtype=bool) | self.back_bodies(WIRE_CY + 0.05)
                | self.back_bodies(self.via_d / 2 + 0.05, front=True) | self.wire_ends()
                | self.holes(self.via_drill / 2 + 0.5 + self.margin))

    def wire_ends(self):
        """Around the other links' wires (their W courtyards): no new link hole there."""
        img = self._blank()
        d = ImageDraw.Draw(img)
        for t in self.b.GetTracks():
            if t.GetLayer() == pcbnew.B_Cu and not isinstance(t, pcbnew.PCB_VIA):
                ps = pcbnew.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(ps, pcbnew.B_Cu, MM(2 * WIRE_CY + 0.1), MM(0.01), pcbnew.ERROR_OUTSIDE)
                self._draw_polyset(d, ps)
        return np.array(img, dtype=bool)

    # ---- search -------------------------------------------------------------------------------------------------
    def astar(self, sources, targets, obs, vblock, tx, ty, limit=3_000_000, cost=None):
        nx, ny = self.nx, self.ny
        fblk, wire = obs
        fr = fblk.ravel()
        vb = vblock | fblk
        tset = {(c[1], c[2]) for c in targets if c[0] == 0}
        openq, g, parent, land = [], {}, {}, {}
        gap = int(round(3.0 / self.g))   # a new link starts >= 3 mm from where the last one landed
        for c in sources:
            if c[0] != 0:
                continue
            s = (c[1], c[2])
            if not fr[s[1] * nx + s[0]] and s not in g:
                g[s] = 0.0
                parent[s] = None
                heapq.heappush(openq, (self._h(s[0], s[1], tx, ty), 0.0, s, -1))
        n = 0
        lat = self.lat
        while openq:
            f, gc, s, pdir = heapq.heappop(openq)
            if gc > g.get(s, 1e18):
                continue
            if s in tset:
                return self._link_path(parent, s)
            n += 1
            if n > limit:
                return None
            x, y = s
            for di, (dx, dy) in enumerate(gridroute.DIRS):
                X, Y = x + dx, y + dy
                if not (0 <= X < nx and 0 <= Y < ny) or fr[Y * nx + X]:
                    continue
                if dx and dy and (fr[y * nx + X] and fr[Y * nx + x]):
                    continue
                c_ = gc + (1.41421 if dx and dy else 1.0) + (0.6 if pdir not in (-1, di) else 0.0)
                ns = (X, Y)
                if c_ < g.get(ns, 1e18):
                    g[ns] = c_
                    parent[ns] = (s, False)
                    if s in land:
                        land[ns] = land[s]
                    heapq.heappush(openq, (c_ + self._h(X, Y, tx, ty), c_, ns, di))
            # a wire link from a lattice point (not straight after another link: they would share a hole)
            if x % lat or y % lat or vb[y, x]:
                continue
            if s in land and abs(land[s][0] - x) + abs(land[s][1] - y) < gap:
                continue
            for dx, dy in DIRS4:
                if dx:
                    run = wire[y, x + dx: x + dx * (self.link_max + 1): dx] if dx > 0 else \
                        wire[y, max(x - self.link_max, 0): x][::-1]
                else:
                    run = wire[y + dy: y + dy * (self.link_max + 1): dy, x] if dy > 0 else \
                        wire[max(y - self.link_max, 0): y, x][::-1]
                stop = int(np.argmax(run)) if run.any() else len(run)
                for L in range(self.link_min, stop + 1, lat):
                    X, Y = x + dx * L, y + dy * L
                    if not (0 <= X < nx and 0 <= Y < ny) or vb[Y, X]:
                        continue
                    c_ = gc + self.link_cost + L
                    ns = (X, Y)
                    if c_ < g.get(ns, 1e18):
                        g[ns] = c_
                        parent[ns] = (s, True)
                        land[ns] = ns
                        heapq.heappush(openq, (c_ + self._h(X, Y, tx, ty), c_, ns, -1))
        return None

    @staticmethod
    def _link_path(parent, s):
        out = [(0, s[0], s[1])]
        while parent[s] is not None:
            p, link = parent[s]
            if link:
                out += [(1, s[0], s[1]), (1, p[0], p[1])]
            out.append((0, p[0], p[1]))
            s = p
        return out[::-1]

    # ---- nets ---------------------------------------------------------------------------------------------------
    def seed(self, net):
        """Start the net's tree from copper already on the board (hand-routed tracks and the pads they touch)."""
        name = lambda p: f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}"  # noqa: E731
        tree = self.tree.setdefault(net, {"cells": [], "pads": []})
        tracks = [t for t in self.b.GetTracks() if t.GetNetname() == net and not isinstance(t, pcbnew.PCB_VIA)]
        if not tracks:
            return
        img = self._blank()
        d = ImageDraw.Draw(img)
        for t in tracks:
            self._draw_polyset(d, self._item_poly(t, t.GetLayer(), 0.0))
        ys, xs = np.nonzero(np.array(img, dtype=bool))
        tree["cells"] += [(0, int(x), int(y)) for x, y in zip(xs, ys)]
        for f in self.b.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() == net and name(p) not in tree["pads"] and any(
                        p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()) for t in tracks):
                    tree["pads"].append(name(p))
                    tree["cells"] += self.pad_cells(p)

    def connect(self, net, pads, widths, limit=12_000_000, link_cost=None):
        """Connect `pads` (all pads of the net if None) to what this net already has (Prim order); `link_cost`
        (mm) overrides the router's for this net. Returns (done [(width, pad)], failed [pad])."""
        saved = self.link_cost
        if link_cost is not None:
            self.link_cost = link_cost / self.g
        try:
            return self._connect(net, pads, widths, limit)
        finally:
            self.link_cost = saved

    def _connect(self, net, pads, widths, limit):
        name = lambda p: f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}"  # noqa: E731
        allp = {name(p): p for f in self.b.GetFootprints() for p in f.Pads() if p.GetNetname() == net}
        pads = list(allp) if pads is None else [name(p) for p in pads]
        pos = {n: (TO(p.GetPosition().x), TO(p.GetPosition().y)) for n, p in allp.items()}
        cells = {n: self.pad_cells(allp[n]) for n in pads}
        tree = self.tree.setdefault(net, {"cells": [], "pads": []})
        rest = list(pads)
        if not tree["pads"]:
            first = rest.pop(0)
            tree["pads"].append(first)
            tree["cells"] += cells[first]
        rest = [n for n in rest if n not in tree["pads"]]
        obs_cache = {}
        vblock = self.via_block(net)
        done, failed = [], []
        while rest:
            nxt = min(rest, key=lambda n: min(math.dist(pos[n], pos[q]) for q in tree["pads"]))
            rest.remove(nxt)
            tx, ty = self._px(*pos[nxt])
            for w in widths:
                if w not in obs_cache:
                    obs_cache[w] = self.obstacles(net, w / 2)
                path = self.astar(tree["cells"], cells[nxt], obs_cache[w], vblock, tx, ty, limit)
                if path is not None:
                    self.commit(path, net, w)
                    if any(c[0] == 1 for c in path):   # a link changes everyone's obstacles
                        obs_cache, vblock = {}, self.via_block(net)
                    tree["cells"] += path + cells[nxt]
                    tree["pads"].append(nxt)
                    done.append((w, nxt))
                    break
            else:
                failed.append(nxt)
        return done, failed

    def links(self):
        """[(net, (x1, y1), (x2, y2))] of the wire links made so far (B.Cu tracks)."""
        out = []
        for t in self.b.GetTracks():
            if t.GetLayer() == pcbnew.B_Cu and not isinstance(t, pcbnew.PCB_VIA):
                out.append((t.GetNetname(), (TO(t.GetStart().x), TO(t.GetStart().y)),
                            (TO(t.GetEnd().x), TO(t.GetEnd().y))))
        return out
