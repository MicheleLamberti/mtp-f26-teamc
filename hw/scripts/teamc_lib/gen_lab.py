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


def main():
    for c in COPIES:
        print(lab_copy(*c))


if __name__ == "__main__":
    main()
