"""Lab copies of the stock through-hole footprints that carrier rev C (hw/teamc-carrier-simple) uses with pads too
small for the UPC lab: pad = hole + 1.0 mm (Jimenez guide SR5), same drill. Written into hw/lib/teamc.pretty with a
`_Pad<size>` suffix, like gen_lab.py does for rev B (rev B's files are not touched).

    python3 hw/scripts/teamc_lib/gen_lab_revc.py

Stock footprints whose pads already meet hole + 1.0 mm are used as they are (the 18650 holder 3.0 on 1.57, the
Keystone 3517 fuse clips 2.7 on 1.7, the DO-201AD diode 3.2 on 1.6, the Keystone 5010 test point 2.8 on 1.6).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_lab import lab_copy  # noqa: E402

# (stock library, stock name, new pad size (x, y) mm, suffix); all stock drills 0.8 mm
COPIES = [
    ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", (1.8, 1.8), "Pad1.8mm"),
    ("Capacitor_THT", "CP_Radial_D6.3mm_P2.50mm", (1.8, 1.8), "Pad1.8mm"),
    ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", (1.8, 1.8), "Pad1.8mm"),     # 100 nF Vishay K104K10, 1 uF TDK FG28 (5 mm)
    ("Package_TO_SOT_THT", "TO-92_Inline_Wide", (1.8, 1.8), "Pad1.8mm"),
]




def wire_link_revc(length):
    """teamc:RevC_WireLink_L<length>mm: an insulated 22 AWG solid wire on the component side between two unplated
    1.0 mm holes (2.0 mm pads, soldered on the copper side), `length` mm centre to centre along +x. Same construction
    as gen_lab.wire_link (rev B): both pads are pad 1 and declared jumpers, so connectivity and DRC treat the link as
    copper; its own name prefix so rev B's generator, which prunes WireLink_*, leaves it alone."""
    import pcbnew
    from gen_lab import OUT
    name = f"RevC_WireLink_L{length:.1f}mm"
    mm = pcbnew.FromMM
    f = pcbnew.FOOTPRINT(None)
    f.SetFPID(pcbnew.LIB_ID("teamc", name))
    f.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    f.SetDuplicatePadNumbersAreJumpers(True)
    for x in (0.0, length):
        p = pcbnew.PAD(f)
        p.SetNumber("1")
        p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        p.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(mm(2.0), mm(2.0)))
        p.SetDrillSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
        p.SetLayerSet(pcbnew.PAD.PTHMask())
        p.SetPosition(pcbnew.VECTOR2I(mm(x), 0))
        f.Add(p)

    def seg(layer, a, b, w):
        sh = pcbnew.PCB_SHAPE(f)
        sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
        sh.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        sh.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        sh.SetLayer(layer)
        sh.SetWidth(mm(w))
        f.Add(sh)

    seg(pcbnew.F_Fab, (0, 0), (length, 0), 0.6)
    c = 1.25
    for a, b in (((-c, -c), (length + c, -c)), ((length + c, -c), (length + c, c)), ((length + c, c), (-c, c)),
                 ((-c, c), (-c, -c))):
        seg(pcbnew.F_CrtYd, a, b, 0.05)
    f.SetLibDescription(f"Wire link {length:.1f} mm: insulated 22 AWG solid tinned wire on the component side between two "
                        f"unplated 1.0 mm holes (Team C rev C, single-sided UPC lab board)")
    f.SetKeywords("wire link jumper Team C lab")
    f.SetValue(name)
    f.Reference().SetText("W**")
    m = pcbnew.FP_3DMODEL()                                  # 1 mm of wire scaled to the link's length
    m.m_Filename = "${KIPRJMOD}/../lib/teamc.3dshapes/RevC_WireLink_unit.wrl"
    m.m_Scale = pcbnew.VECTOR3D(length, 1.0, 1.0)
    f.Models().push_back(m)
    pcbnew.FootprintSave(OUT, f)
    return "teamc:" + name


def wire_links():
    """RevC_WireLink footprints for the links in hw/teamc-carrier-simple/links.json; stale ones are removed."""
    import json
    from gen_lab import OUT
    path = os.path.join(os.path.dirname(OUT), "..", "teamc-carrier-simple", "links.json")
    keep = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            links = json.load(fh).get("links", [])
        for length in sorted({link_length(lk) for lk in links}):
            name = wire_link_revc(length)
            keep.add(name.split(":")[1] + ".kicad_mod")
            print(name)
    for fn in os.listdir(OUT):
        if fn.startswith("RevC_WireLink_") and fn not in keep:
            os.remove(os.path.join(OUT, fn))


def link_length(lk):
    return round(((lk["a"][0] - lk["b"][0]) ** 2 + (lk["a"][1] - lk["b"][1]) ** 2) ** 0.5, 1)


MODEL_DIR = "${KIPRJMOD}/../lib/teamc.3dshapes/"
# rev B's module footprints (gen_modules.py, pads from the makers' CAD) copied as RevC_* with a 3D model
# (gen_3d_revc.py); rev B's own files are left as they are
MODULE_COPIES = [
    ("Pololu_U3V70F5_Headers", "RevC_Pololu_U3V70F5.wrl"),
    ("Pololu_IdealDiode_5388_Headers", "RevC_Pololu_IdealDiode_5388.wrl"),
    ("Adafruit_MAX17048_5580_Headers", "RevC_Adafruit_MAX17048_5580.wrl"),
]


def module_copy(name, model):
    import pcbnew
    from gen_lab import OUT
    f = pcbnew.FootprintLoad(OUT, name)
    if f is None:
        raise SystemExit(f"teamc:{name} not found (run hw/scripts/teamc_lib/gen_modules.py)")
    new = "RevC_" + name
    f.SetFPID(pcbnew.LIB_ID("teamc", new))
    f.SetValue(new)
    f.SetLibDescription(f.GetLibDescription() + " -- rev C copy with a simple 3D model")
    f.Models().clear()
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = MODEL_DIR + model
    f.Models().push_back(m)
    pcbnew.FootprintSave(OUT, f)
    return "teamc:" + new


def main():
    for c in COPIES:
        print(lab_copy(*c))
    for c in MODULE_COPIES:
        print(module_copy(*c))
    wire_links()


if __name__ == "__main__":
    main()
