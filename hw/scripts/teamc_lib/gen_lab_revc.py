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
    ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", (1.8, 1.8), "Pad1.8mm"),
    ("Capacitor_THT", "CP_Radial_D6.3mm_P2.50mm", (1.8, 1.8), "Pad1.8mm"),
    ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", (1.8, 1.8), "Pad1.8mm"),     # 100 nF Vishay K104K10, 1 uF TDK FG28 (5 mm)
    ("Package_TO_SOT_THT", "TO-92_Inline_Wide", (1.8, 1.8), "Pad1.8mm"),
]


def main():
    for c in COPIES:
        print(lab_copy(*c))


if __name__ == "__main__":
    main()
