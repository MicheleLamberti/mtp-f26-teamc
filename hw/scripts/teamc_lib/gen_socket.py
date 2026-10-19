"""teamc:PinSocket_2x20_P2.54mm_Vertical_Pad1.5mm — the KiCad 2x20 socket with 1.5 mm pads (drill 1.0 kept).

The stock 1.7 mm pads leave 0.84 mm between neighbours: under the lab-safe rules (0.3 mm track, 0.3 mm clearance)
nothing can leave the header's edge row (the even pins) and the ground pour cannot reach them. 1.5 mm pads leave
1.04 mm (a 0.3 mm track or a 0.44 mm pour neck) and still a 0.25 mm annular ring.

    python3 hw/scripts/teamc_lib/gen_socket.py
"""
import os

import pcbnew

SRC = "/usr/share/kicad/footprints/Connector_PinSocket_2.54mm.pretty"
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib", "teamc.pretty")
NAME = "PinSocket_2x20_P2.54mm_Vertical_Pad1.5mm"

f = pcbnew.FootprintLoad(SRC, "PinSocket_2x20_P2.54mm_Vertical")
for p in f.Pads():
    p.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(pcbnew.FromMM(1.5), pcbnew.FromMM(1.5)))
    for lay in (pcbnew.B_Cu,):
        p.SetSize(lay, pcbnew.VECTOR2I(pcbnew.FromMM(1.5), pcbnew.FromMM(1.5)))
f.SetFPID(pcbnew.LIB_ID("teamc", NAME))
f.SetLibDescription("Raspberry Pi 2x20 female socket, 2.54 mm, vertical, 1.5 mm pads (from the KiCad "
                    "PinSocket_2x20_P2.54mm_Vertical; smaller pads so the edge row can be routed at 0.3/0.3 mm)")
f.SetKeywords("Raspberry Pi HAT socket 2x20 Team C")
f.SetValue(NAME)
pcbnew.FootprintSave(DST, f)
print("wrote", os.path.join(DST, NAME + ".kicad_mod"))
