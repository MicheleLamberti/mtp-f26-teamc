"""A small two-layer grid router on top of pcbnew (no autorouter is installed here).

Each net is grown as a tree from its pads with A* on a 0.1 mm grid (45-degree moves, turn and via penalties).
Every other net's copper (pads, tracks, vias) is rasterized with PIL and inflated by half the track width plus the
clearance, so a track centre on a free cell keeps the clearance; rule areas that forbid tracks (the SP4's top side,
the M2.5 hole lands) and the board edge are blocked too. The result is plain tracks and vias that KiCad's DRC
then checks. It is a draft router: ET should review and tidy the result in the KiCad GUI.
"""
import heapq
import math

import numpy as np
import pcbnew
from PIL import Image, ImageDraw

MM = pcbnew.FromMM
TO = pcbnew.ToMM
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


class Router:
    def __init__(self, board, x0, y0, x1, y1, grid=0.1, clearance=0.3, edge=0.5, via_d=0.8, via_drill=0.4,
                 via_cost=4.0, margin=0.08, fine_refs=(), fine_nets=(), fine_clearance=0.15):
        self.b, self.g = board, grid
        # nets in the fine-pitch net class may pass the pads of fine-pitch footprints at fine_clearance
        self.fine_refs, self.fine_nets, self.fine_c = set(fine_refs), set(fine_nets), fine_clearance
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.nx, self.ny = int(round((x1 - x0) / grid)) + 1, int(round((y1 - y0) / grid)) + 1
        self.c, self.edge, self.via_d, self.via_drill = clearance, edge, via_d, via_drill
        self.via_cost, self.margin = via_cost / grid, margin

    # ---- rasterization ------------------------------------------------------------------------------------------
    def _px(self, x, y):
        return (x - self.x0) / self.g, (y - self.y0) / self.g

    def _draw_polyset(self, draw, ps):
        for i in range(ps.OutlineCount()):
            o = ps.Outline(i)
            pts = [self._px(TO(o.CPoint(k).x), TO(o.CPoint(k).y)) for k in range(o.PointCount())]
            if len(pts) >= 3:
                draw.polygon(pts, fill=1)

    def _item_poly(self, item, layer, inflate):
        ps = pcbnew.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(ps, layer, MM(max(inflate, 0.0)), MM(0.01), pcbnew.ERROR_OUTSIDE)
        return ps

    def _copper_items(self):
        for f in self.b.GetFootprints():
            for p in f.Pads():
                yield p, p.GetNetname()
        for t in self.b.GetTracks():
            yield t, t.GetNetname()

    def obstacles(self, net, half_width):
        """Per-layer boolean grids: True where a track centre (half_width) of `net` may not go."""
        inflate = half_width + self.c + self.margin
        fine = half_width + self.fine_c + self.margin
        out = []
        for layer in LAYERS:
            img = Image.new("1", (self.nx, self.ny), 0)
            d = ImageDraw.Draw(img)
            for item, n in self._copper_items():
                if n == net and n != "":
                    continue
                if not item.IsOnLayer(layer):
                    continue
                amount = inflate
                if (net in self.fine_nets and isinstance(item, pcbnew.PAD)
                        and item.GetParentFootprint().GetReference() in self.fine_refs):
                    amount = fine
                self._draw_polyset(d, self._item_poly(item, layer, amount))
            # copper areas of other nets (GND is the pour: it gives way to tracks)
            for z in self.b.Zones():
                if (not z.GetIsRuleArea() and z.IsOnLayer(layer) and z.GetNetname() not in (net, "GND", "")):
                    ps = pcbnew.SHAPE_POLY_SET(z.Outline())
                    ps.Inflate(MM(inflate), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
                    self._draw_polyset(d, ps)
            # rule areas that forbid tracks (footprint and board level)
            areas = [z for z in self.b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
            for f in self.b.GetFootprints():
                areas += [z for z in f.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
            for z in areas:
                if z.IsOnLayer(layer):
                    ps = pcbnew.SHAPE_POLY_SET(z.Outline())
                    ps.Inflate(MM(half_width + self.margin), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
                    self._draw_polyset(d, ps)
            a = np.array(img, dtype=bool)
            # board edge: keep (edge clearance + half width) inside the outline rectangle
            k = int(math.ceil((self.edge + half_width + self.margin) / self.g))
            a[:k, :] = True
            a[-k:, :] = True
            a[:, :k] = True
            a[:, -k:] = True
            out.append(a)
        return out

    def via_block(self, net):
        """True where a via of `net` may not sit (on either layer)."""
        obs = self.obstacles(net, self.via_d / 2)
        blocked = obs[0] | obs[1]
        img = Image.new("1", (self.nx, self.ny), 0)
        d = ImageDraw.Draw(img)
        # drilled holes of any net (a via next to a same-net THT pad still needs hole-to-hole room) and vias
        hole = self.via_d / 2 + 0.3 + self.margin
        for f in self.b.GetFootprints():
            for p in f.Pads():
                if p.GetDrillSize().x > 0:
                    x, y = self._px(TO(p.GetPosition().x), TO(p.GetPosition().y))
                    r = (TO(p.GetDrillSize().x) / 2 + hole) / self.g
                    d.ellipse([x - r, y - r, x + r, y + r], fill=1)
        for t in self.b.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA):
                x, y = self._px(TO(t.GetPosition().x), TO(t.GetPosition().y))
                r = (self.via_drill / 2 + hole) / self.g
                d.ellipse([x - r, y - r, x + r, y + r], fill=1)
        areas = [z for z in self.b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
        for z in areas:
            ps = pcbnew.SHAPE_POLY_SET(z.Outline())
            ps.Inflate(MM(self.via_d / 2 + self.margin), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
            self._draw_polyset(d, ps)
        return blocked | np.array(img, dtype=bool)

    def zone_cells(self, net):
        """Cells inside this net's own copper areas (their outlines shrunk by 0.2 mm)."""
        cells = []
        for z in self.b.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != net:
                continue
            for li, layer in enumerate(LAYERS):
                if not z.IsOnLayer(layer):
                    continue
                ps = pcbnew.SHAPE_POLY_SET(z.Outline())
                ps.Inflate(MM(-0.2), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
                img = Image.new("1", (self.nx, self.ny), 0)
                self._draw_polyset(ImageDraw.Draw(img), ps)
                ys, xs = np.nonzero(np.array(img, dtype=bool))
                cells += [(li, int(x), int(y)) for x, y in zip(xs, ys)]
        return cells

    def stub_cells(self, pad):
        """Cells of this pad's own escape tracks (tracks of its net that start or end on the pad)."""
        cells = []
        for t in self.b.GetTracks():
            if t.GetNetname() != pad.GetNetname() or isinstance(t, pcbnew.PCB_VIA):
                continue
            if not (pad.HitTest(t.GetStart()) or pad.HitTest(t.GetEnd())):
                continue
            chain = [t]
            ends = {(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)}
            grown = True
            while grown:   # follow the stub's segments
                grown = False
                for u in self.b.GetTracks():
                    if u in chain or u.GetNetname() != pad.GetNetname() or isinstance(u, pcbnew.PCB_VIA):
                        continue
                    ue = {(u.GetStart().x, u.GetStart().y), (u.GetEnd().x, u.GetEnd().y)}
                    if ue & ends:
                        chain.append(u)
                        ends |= ue
                        grown = True
            for u in chain:
                li = LAYERS.index(u.GetLayer())
                img = Image.new("1", (self.nx, self.ny), 0)
                self._draw_polyset(ImageDraw.Draw(img), self._item_poly(u, u.GetLayer(), 0.0))
                ys, xs = np.nonzero(np.array(img, dtype=bool))
                cells += [(li, int(x), int(y)) for x, y in zip(xs, ys)]
        return cells

    def pad_cells(self, pad):
        cells = self.stub_cells(pad)
        for li, layer in enumerate(LAYERS):
            if not pad.IsOnLayer(layer):
                continue
            img = Image.new("1", (self.nx, self.ny), 0)
            self._draw_polyset(ImageDraw.Draw(img), self._item_poly(pad, layer, -0.05))
            ys, xs = np.nonzero(np.array(img, dtype=bool))
            if len(xs) == 0:   # tiny pad: its centre cell
                cx, cy = self._px(TO(pad.GetPosition().x), TO(pad.GetPosition().y))
                xs, ys = np.array([int(round(cx))]), np.array([int(round(cy))])
            cells += [(li, int(x), int(y)) for x, y in zip(xs, ys)]
        return cells

    # ---- search -----------------------------------------------------------------------------------------------
    def astar(self, sources, targets, obs, vblock, tx, ty, limit=3_000_000):
        nx = self.nx
        blk = [o.ravel() for o in obs]           # True = a track centre may not go there
        vblk = vblock.ravel()
        tset = set(targets)
        openq, g, parent = [], {}, {}
        for s in sources:
            li, x, y = s
            if not blk[li][y * nx + x] and s not in g:
                g[s] = 0.0
                parent[s] = None
                heapq.heappush(openq, (self._h(x, y, tx, ty), 0.0, s, -1))
        n = 0
        while openq:
            f, gc, s, pdir = heapq.heappop(openq)
            if gc > g.get(s, 1e18):
                continue
            if s in tset:
                return self._path(parent, s)
            n += 1
            if n > limit:
                return None
            li, x, y = s
            for di, (dx, dy) in enumerate(DIRS):
                X, Y = x + dx, y + dy
                if not (0 <= X < nx and 0 <= Y < self.ny) or blk[li][Y * nx + X]:
                    continue
                if dx and dy and (blk[li][y * nx + X] and blk[li][Y * nx + x]):
                    continue   # no squeezing diagonally between two blocked cells
                cost = gc + (1.41421 if dx and dy else 1.0) + (0.6 if pdir not in (-1, di) else 0.0)
                ns = (li, X, Y)
                if cost < g.get(ns, 1e18):
                    g[ns] = cost
                    parent[ns] = s
                    heapq.heappush(openq, (cost + self._h(X, Y, tx, ty), cost, ns, di))
            # layer change through a via
            ol = 1 - li
            if not vblk[y * nx + x] and not blk[ol][y * nx + x]:
                ns = (ol, x, y)
                cost = gc + self.via_cost
                if cost < g.get(ns, 1e18):
                    g[ns] = cost
                    parent[ns] = s
                    heapq.heappush(openq, (cost + self._h(x, y, tx, ty), cost, ns, -1))
        return None

    def _mm(self, c):
        return self.x0 + c[1] * self.g, self.y0 + c[2] * self.g

    @staticmethod
    def _h(x, y, tx, ty):
        dx, dy = abs(x - tx), abs(y - ty)
        return max(dx, dy) + 0.41421 * min(dx, dy)

    @staticmethod
    def _path(parent, s):
        out = []
        while s is not None:
            out.append(s)
            s = parent[s]
        return out[::-1]

    # ---- output -----------------------------------------------------------------------------------------------
    def commit(self, path, net, width):
        """Turn a cell path into tracks and vias on the board."""
        ni = self.b.FindNet(net)
        mm = lambda c: (self.x0 + c[1] * self.g, self.y0 + c[2] * self.g)  # noqa: E731
        segs, start = [], path[0]
        prev, pdir = path[0], None
        for c in path[1:]:
            if c[0] != prev[0]:   # via
                if prev != start:
                    segs.append((start, prev))
                v = pcbnew.PCB_VIA(self.b)
                x, y = mm(prev)
                v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
                v.SetWidth(MM(self.via_d))
                v.SetDrill(MM(self.via_drill))
                v.SetNet(ni)
                self.b.Add(v)
                start, prev, pdir = c, c, None
                continue
            d = (c[1] - prev[1], c[2] - prev[2])
            if pdir is not None and d != pdir:
                segs.append((start, prev))
                start = prev
            pdir, prev = d, c
        if prev != start:
            segs.append((start, prev))
        for a, b in segs:
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(pcbnew.VECTOR2I(*[MM(v) for v in mm(a)]))
            t.SetEnd(pcbnew.VECTOR2I(*[MM(v) for v in mm(b)]))
            t.SetWidth(MM(width))
            t.SetLayer(LAYERS[a[0]])
            t.SetNet(ni)
            self.b.Add(t)
        return [c for c in path]

    def route_net(self, net, widths, limit=3_000_000):
        """Connect every pad of `net` (Prim order); each connection takes the first width in `widths` that fits.
        Returns ([(width, pad) ...] per connection, [unrouted pad names])."""
        pads = [p for f in self.b.GetFootprints() for p in f.Pads() if p.GetNetname() == net]
        if len(pads) < 2:
            return [], []
        obs_cache = {}
        vblock = self.via_block(net)
        cells = {id(p): self.pad_cells(p) for p in pads}
        pos = {id(p): (TO(p.GetPosition().x), TO(p.GetPosition().y)) for p in pads}
        zc = self.zone_cells(net)
        if zc:   # the net's copper area is the trunk; pads it already covers are connected
            zset = set(zc)
            tree_pads = [p for p in pads if zset & set(cells[id(p)])]
            rest = [p for p in pads if p not in tree_pads]
            tree = list(zc)
            for p in tree_pads:
                tree += cells[id(p)]
            if not tree_pads:
                tree_pads = [min(pads, key=lambda p: min(math.dist(pos[id(p)], self._mm(c)) for c in zc[::50]))]
        else:
            tree_pads, rest = [pads[0]], pads[1:]
            tree = list(cells[id(pads[0])])
        done, failed = [], []
        name = lambda p: f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}"  # noqa: E731
        while rest:
            nxt = min(rest, key=lambda p: min(math.dist(pos[id(p)], pos[id(q)]) for q in tree_pads))
            rest.remove(nxt)
            tx, ty = self._px(*pos[id(nxt)])
            for w in widths:
                if w not in obs_cache:
                    obs_cache[w] = self.obstacles(net, w / 2)
                path = self.astar(tree, cells[id(nxt)], obs_cache[w], vblock, tx, ty, limit)
                if path is not None:
                    self.commit(path, net, w)
                    tree += path + cells[id(nxt)]
                    tree_pads.append(nxt)
                    done.append((w, name(nxt)))
                    break
            else:
                failed.append(name(nxt))
        return done, failed

    def stitch(self, net, pitch=4.0):
        """Vias of `net` on a grid wherever one fits clear of all copper and drills (ties the two ground pours
        together). Returns the vias; prune() removes those the pours do not reach on both layers."""
        vblock = self.via_block("__stitch__")   # every pad and track is an obstacle, even the net's own
        ni = self.b.FindNet(net)
        made = []
        step = int(round(pitch / self.g))
        for iy in range(step // 2, self.ny, step):
            for ix in range(step // 2, self.nx, step):
                if not vblock[iy, ix]:
                    v = pcbnew.PCB_VIA(self.b)
                    v.SetPosition(pcbnew.VECTOR2I(MM(self.x0 + ix * self.g), MM(self.y0 + iy * self.g)))
                    v.SetWidth(MM(self.via_d))
                    v.SetDrill(MM(self.via_drill))
                    v.SetNet(ni)
                    self.b.Add(v)
                    made.append(v)
        return made

    def via_to(self, pad, net, width=0.3, reach=3.0):
        """A via of `net` next to `pad` (F.Cu) with a straight track to it, where both fit; True if placed."""
        obs = self.obstacles(net, width / 2)[0]
        vblk = self.via_block(net)
        fills = [z.GetFilledPolysList(pcbnew.B_Cu) for z in self.b.Zones()
                 if not z.GetIsRuleArea() and z.GetNetname() == net and z.IsOnLayer(pcbnew.B_Cu)]
        px, py = self._px(TO(pad.GetPosition().x), TO(pad.GetPosition().y))
        best = None
        rmax = int(reach / self.g)
        for iy in range(int(py) - rmax, int(py) + rmax + 1):
            for ix in range(int(px) - rmax, int(px) + rmax + 1):
                if not (0 <= ix < self.nx and 0 <= iy < self.ny) or vblk[iy, ix]:
                    continue
                dist = math.hypot(ix - px, iy - py)
                if dist > rmax or (best and dist >= best[0]):
                    continue
                x_, y_ = self.x0 + ix * self.g, self.y0 + iy * self.g
                if not any(fp.Contains(pcbnew.VECTOR2I(MM(x_), MM(y_))) for fp in fills):
                    continue   # only where the bottom pour actually is
                n = max(2, int(dist * 2))
                if all(not obs[int(round(py + (iy - py) * k / n)), int(round(px + (ix - px) * k / n))]
                       for k in range(n + 1)):
                    best = (dist, ix, iy)
        if best is None:
            return False
        _, ix, iy = best
        x, y = self.x0 + ix * self.g, self.y0 + iy * self.g
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(pad.GetPosition())
        t.SetEnd(pcbnew.VECTOR2I(MM(x), MM(y)))
        t.SetWidth(MM(width))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(self.b.FindNet(net))
        self.b.Add(t)
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        v.SetWidth(MM(self.via_d))
        v.SetDrill(MM(self.via_drill))
        v.SetNet(self.b.FindNet(net))
        self.b.Add(v)
        return True

    def prune(self, vias, net):
        """After a zone fill: delete vias of `net` that do not sit in that net's filled copper on both layers."""
        zones = [z for z in self.b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == net]
        gone = 0
        for v in vias:
            pos = v.GetPosition()
            ok = all(any(z.IsOnLayer(lay) and z.GetFilledPolysList(lay).Contains(pos) for z in zones)
                     for lay in LAYERS)
            if not ok:
                self.b.Delete(v)
                gone += 1
        return gone
