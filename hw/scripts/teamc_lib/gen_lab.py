"""Lab copies of stock through-hole footprints for the UPC milling rules (carrier rev B, 23-Oct-26).

    python3 hw/scripts/teamc_lib/gen_lab.py

The lab cannot plate holes and the parts are hand soldered, so a THT pad should be the hole + 1.0 mm (Jimenez
guide SR5; SA3 absolute minimum + 0.7 mm). The stock 2.54 mm parts have 1.7 mm pads on a 1.0 mm drill: the copies
get 2.0 mm (0.54 mm copper-to-copper at the pitch, rules 0.3 mm). Library copies rather than pad overrides on the
board, so DRC's library-parity check stays clean (as build_breakout.header_fp and gen_socket.py do).
"""
import os

import pcbnew

FP = "/usr/share/kicad/footprints"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib", "teamc.pretty")

# (stock library, stock name, new pad size (x, y) mm, suffix)
COPIES = [
    ("Connector_IDC", "IDC-Header_2x20_P2.54mm_Vertical", (2.0, 2.0), "Pad2.0mm"),
    ("Connector_PinSocket_2.54mm", "PinSocket_1x08_P2.54mm_Vertical", (2.0, 2.0), "Pad2.0mm"),
    ("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical", (2.0, 2.0), "Pad2.0mm"),
    # JST-XH: 2.50 mm pitch along x, stock pads 1.7 x 2.0 (1.7 x 1.95 on the B3B) on a 0.95-1.0 mm drill
    ("Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", (2.0, 2.4), "Pad2.0x2.4mm"),
    ("Connector_JST", "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical", (2.0, 2.4), "Pad2.0x2.4mm"),
]


def lab_copy(lib, stock, size, suffix):
    name = f"{stock}_{suffix}"
    f = pcbnew.FootprintLoad(os.path.join(FP, lib + ".pretty"), stock)
    if f is None:
        raise SystemExit(f"{lib}:{stock} not found")
    for p in f.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            p.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(pcbnew.FromMM(size[0]), pcbnew.FromMM(size[1])))
    f.SetFPID(pcbnew.LIB_ID("teamc", name))
    f.SetLibDescription(f"{f.GetLibDescription()} -- {suffix} pads for the UPC lab's unplated, hand-soldered holes "
                        f"(copy of {lib}:{stock})")
    f.SetKeywords(f"{f.GetKeywords()} Team C lab")
    f.SetValue(name)
    pcbnew.FootprintSave(OUT, f)
    return "teamc:" + name


def wire_link(length):
    """teamc:WireLink_L<length>mm: an insulated 22 AWG solid wire on the component side between two unplated 1.0 mm holes
    (2.0 mm pads, soldered on the copper side), `length` mm centre to centre along +x.

    Both pads are pad 1 and the footprint declares duplicate pad numbers as jumpers, so KiCad's connectivity (and
    DRC) treats the link as copper; the schematic symbol is a one-pin Conn_01x01 on the net it carries."""
    name = f"WireLink_L{length:.1f}mm"
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
        s = pcbnew.PCB_SHAPE(f)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        f.Add(s)

    seg(pcbnew.F_Fab, (0, 0), (length, 0), 0.6)        # the wire
    c = 1.25
    for a, b in (((-c, -c), (length + c, -c)), ((length + c, -c), (length + c, c)), ((length + c, c), (-c, c)),
                 ((-c, c), (-c, -c))):
        seg(pcbnew.F_CrtYd, a, b, 0.05)
    f.SetLibDescription(f"Wire link {length:.1f} mm: insulated 22 AWG solid tinned wire on the component side between two "
                        f"unplated 1.0 mm holes (Team C rev B, single-sided UPC lab board)")
    f.SetKeywords("wire link jumper Team C lab")
    f.SetValue(name)
    f.Reference().SetText("W**")
    pcbnew.FootprintSave(OUT, f)
    return "teamc:" + name


def main():
    for c in COPIES:
        print(lab_copy(*c))
    links = os.path.join(os.path.dirname(OUT), "..", "teamc-carrier-lab", "links.json")
    if os.path.exists(links):
        import json
        with open(links, encoding="utf-8") as fh:
            data = json.load(fh)
        keep = set()
        for length in sorted({link_length(lk) for lk in data.get("links", [])}):
            name = wire_link(length)
            keep.add(name.split(":")[1] + ".kicad_mod")
            print(name)
        for fn in os.listdir(OUT):          # links of earlier routing runs
            if fn.startswith("WireLink_") and fn not in keep:
                os.remove(os.path.join(OUT, fn))


def link_length(lk):
    """Centre-to-centre length of a link from links.json (board mm), rounded to 0.1 mm."""
    return round(((lk["a"][0] - lk["b"][0]) ** 2 + (lk["a"][1] - lk["b"][1]) ** 2) ** 0.5, 1)


if __name__ == "__main__":
    main()
