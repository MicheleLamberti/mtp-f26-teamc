"""Footprints for the hand-soldered modules of carrier rev B (UPC lab), from hw/teamc-carrier-lab/sheets/modules.py.

    python3 hw/scripts/teamc_lib/gen_modules.py

Each module sits component side up on 2.54 mm male headers whose pins go through the carrier and are soldered on
its copper side. modules.py gives the pads in the module's top view (origin and axes stated there, y up, mm, from
the makers' drawings); here y is flipped to KiCad's y-down and the footprint origin is the module's centre.
Pads: round, pad = hole + 1.0 mm (UPC lab rule), pin 1 square. The module outline goes on F.Fab and F.SilkS (the
lab has no silkscreen; it only helps the assembly drawing) and the courtyard 0.5 mm outside it.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "lib", "teamc.pretty")
sys.path.insert(0, os.path.join(HERE, "..", "..", "teamc-carrier-lab", "sheets"))
from modules import MODULES  # noqa: E402

MM = pcbnew.FromMM


def v(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def rect(f, layer, x1, y1, x2, y2, w):
    for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        s = pcbnew.PCB_SHAPE(f)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(v(*a))
        s.SetEnd(v(*b))
        s.SetLayer(layer)
        s.SetWidth(MM(w))
        f.Add(s)


def build(key, m):
    f = pcbnew.FOOTPRINT(None)
    name = m["footprint"]
    f.SetFPID(pcbnew.LIB_ID("teamc", name))
    f.SetLibDescription(f"{m['value']} ({m['mfr']} {m['mpn']}) on 2.54 mm headers; pads from {m['source']}")
    f.SetKeywords("Team C lab module THT")
    f.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    w, h = m["size"]
    cx, cy = w / 2, h / 2
    to_fp = lambda x, y: (x - cx, -(y - cy))  # noqa: E731  module top view (y up, corner origin) -> KiCad
    for i, p in enumerate(m["pins"], 1):
        drill = p.get("drill", 1.0)
        size = p.get("pad", drill + 1.0)
        pad = pcbnew.PAD(f)
        pad.SetNumber(str(i))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_RECT if i == 1 else pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.F_Cu, v(size, size))
        pad.SetDrillSize(v(drill, drill))
        pad.SetLayerSet(pcbnew.PAD.PTHMask())
        pad.SetPosition(v(*to_fp(p["x"], p["y"])))
        pad.SetPinFunction(p["name"])
        f.Add(pad)
    for hx, hy, d in m.get("holes", []):   # module mounting holes: copper-free NPTH on the carrier (optional screw)
        pad = pcbnew.PAD(f)
        pad.SetNumber("")
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.F_Cu, v(d, d))
        pad.SetDrillSize(v(d, d))
        pad.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
        pad.SetPosition(v(*to_fp(hx, hy)))
        f.Add(pad)
    rect(f, pcbnew.F_Fab, -cx, -cy, cx, cy, 0.1)
    rect(f, pcbnew.F_SilkS, -cx - 0.15, -cy - 0.15, cx + 0.15, cy + 0.15, 0.12)
    rect(f, pcbnew.F_CrtYd, -cx - 0.5, -cy - 0.5, cx + 0.5, cy + 0.5, 0.05)
    f.Reference().SetPosition(v(0, -cy - 1.5))
    f.Reference().SetLayer(pcbnew.F_SilkS)
    f.Value().SetText(name)
    f.Value().SetPosition(v(0, 0))
    f.Value().SetLayer(pcbnew.F_Fab)
    pcbnew.FootprintSave(OUT, f)
    return "teamc:" + name


def main():
    for key, m in MODULES.items():
        print(build(key, m))


if __name__ == "__main__":
    main()
