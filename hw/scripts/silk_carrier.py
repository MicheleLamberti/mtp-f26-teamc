"""Place the carrier's reference designators where they clear pads, vias, other silkscreen and the board edge.

    python3 hw/scripts/silk_carrier.py

For each footprint (largest first) it tries positions around the courtyard (above, below, left, right, then shifted
along each side, then inside the body for big parts) at 0.8 mm and then 0.6 mm text, and keeps the first that
collides with nothing. A reference with no free spot moves to F.Fab (assembly drawing only) and is listed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

from place_carrier import PCB  # noqa: E402

MM, TO = pcbnew.FromMM, pcbnew.ToMM
PAD_GAP = 0.2      # silk to exposed copper (mask opening)
SILK_GAP = 0.15    # silk to silk
EDGE_GAP = 0.4


class Rect:
    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1, self.x2, self.y2 = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    @classmethod
    def of(cls, box, grow=0.0):
        return cls(TO(box.GetLeft()) - grow, TO(box.GetTop()) - grow, TO(box.GetRight()) + grow,
                   TO(box.GetBottom()) + grow)

    def hits(self, o):
        return self.x1 < o.x2 and o.x1 < self.x2 and self.y1 < o.y2 and o.y1 < self.y2


def seg_rects(shape, grow):
    """A silkscreen line as a chain of small boxes (a diagonal line's bounding box would block too much)."""
    if shape.GetShape() != pcbnew.SHAPE_T_SEGMENT:
        return [Rect.of(shape.GetBoundingBox(), grow)]
    x1, y1 = TO(shape.GetStart().x), TO(shape.GetStart().y)
    x2, y2 = TO(shape.GetEnd().x), TO(shape.GetEnd().y)
    w = TO(shape.GetWidth()) / 2 + grow
    n = max(1, int(max(abs(x2 - x1), abs(y2 - y1)) / 0.2))
    return [Rect(x1 + (x2 - x1) * i / n - w, y1 + (y2 - y1) * i / n - w,
                 x1 + (x2 - x1) * i / n + w, y1 + (y2 - y1) * i / n + w) for i in range(n + 1)]


def main():
    board = pcbnew.LoadBoard(PCB)
    edge = Rect.of(board.GetBoardEdgesBoundingBox(), -EDGE_GAP)
    copper, silk = [], []
    for f in board.GetFootprints():
        for p in f.Pads():
            copper.append(Rect.of(p.GetBoundingBox(), PAD_GAP))
        for g in f.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS and isinstance(g, pcbnew.PCB_SHAPE):
                silk += seg_rects(g, SILK_GAP)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            copper.append(Rect.of(t.GetBoundingBox(), PAD_GAP))
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.F_SilkS:
            silk += seg_rects(d, SILK_GAP) if isinstance(d, pcbnew.PCB_SHAPE) else [Rect.of(d.GetBoundingBox(), SILK_GAP)]
    # holes: their copper-free land
    for f in board.GetFootprints():
        if f.GetReference().startswith("MH"):
            copper.append(Rect.of(f.GetBoundingBox(), 0.2))
    placed, fab = [], []
    fps = [f for f in board.GetFootprints() if not f.GetReference().startswith(("MH", "TP"))
           and f.GetLayer() == pcbnew.F_Cu]
    fps.sort(key=lambda f: -f.GetBoundingBox(False).GetArea())
    for f in fps:
        ref = f.Reference()
        ref.SetLayer(pcbnew.F_SilkS)
        ref.SetVisible(True)
        cy = Rect.of(f.GetCourtyard(pcbnew.F_CrtYd).BBox()) if not f.GetCourtyard(pcbnew.F_CrtYd).IsEmpty() \
            else Rect.of(f.GetBoundingBox(False))
        cx, cyy = (cy.x1 + cy.x2) / 2, (cy.y1 + cy.y2) / 2
        w, h = cy.x2 - cy.x1, cy.y2 - cy.y1
        ok = False
        for size in (0.8, 0.7, 0.6):
            ref.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
            ref.SetTextThickness(MM(0.12 if size > 0.65 else 0.1))
            gap = size / 2 + 0.15
            cands = []
            for dx in (0, -0.25, 0.25, -0.5, 0.5, -1.0, 1.0):
                cands += [(cx + dx * w, cy.y1 - gap, 0), (cx + dx * w, cy.y2 + gap, 0)]
            for dy in (0, -0.25, 0.25, -0.5, 0.5):
                cands += [(cy.x1 - gap, cyy + dy * h, 90), (cy.x2 + gap, cyy + dy * h, 90)]
            for dx in (0, -0.3, 0.3):
                for dy in (0, -0.3, 0.3):
                    cands.append((cx + dx * w, cyy + dy * h, 0))
            for x, y, rot in cands:
                ref.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
                ref.SetTextAngleDegrees(rot)
                r = Rect.of(ref.GetBoundingBox())
                if not (edge.x1 <= r.x1 and r.x2 <= edge.x2 and edge.y1 <= r.y1 and r.y2 <= edge.y2):
                    continue
                if any(r.hits(o) for o in copper) or any(r.hits(o) for o in silk) \
                        or any(r.hits(o) for o in placed):
                    continue
                placed.append(Rect.of(ref.GetBoundingBox(), SILK_GAP))
                ok = True
                break
            if ok:
                break
        if not ok:
            ref.SetLayer(pcbnew.F_Fab)
            ref.SetPosition(pcbnew.VECTOR2I(MM(cx), MM(cyy)))
            ref.SetTextAngleDegrees(0)
            fab.append(f.GetReference())
    board.Save(PCB)
    print(f"references placed on the silkscreen: {len(fps) - len(fab)}; moved to F.Fab (no room): "
          f"{', '.join(sorted(fab)) or 'none'}")


if __name__ == "__main__":
    main()
