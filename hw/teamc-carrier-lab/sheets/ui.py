"""Team C carrier rev B (UPC lab), sheet ui: same circuit as rev A (hw/teamc-carrier/sheets/ui.py), lab footprints
(JST-XH copies with 2.0 x 2.4 mm pads; 1206 hand-solder R/C (a 0.5 mm track fits between their pads on the single copper layer), 0805 LEDs and SMF TVS diodes are fine for the lab).

DRAFT – for ET review. Software contract: proto/port/linux/ui.c — inputs use the Pi's internal pull-ups, active low
(GPIO 17 GO/STOP button, GPIO 27 role low = TX, GPIO 23 low = NM, else GPIO 16 low = MRM, else SRI); LEDs active
high on GPIO 5 (activity) and GPIO 6 (status).
Per input: the Pi's pull-up (rev A also had 10 kΩ to 3V3_PI at the connector; rev B drops it, see the sheet),
1 kΩ series to the GPIO (limits current if a GPIO is driven, e.g. GPIO 16 by legacy firmware; HAT design guide),
100 nF at the GPIO (debounce + ESD/RF filter, tau = 1 kΩ x 100 nF = 0.1 ms), one SMF5.0A TVS per lead at the
connectors (rev A: SP0504BAHTG array).
"""

import schgen  # noqa: E402
from schgen import Sheet
from nets import GLOBAL_NETS, LAB

R1206 = LAB["R"]
C1206 = LAB["C"]
LED0805 = LAB["LED"]
XH2 = LAB["XH2"]
XH3 = LAB["XH3"]

# (line, pull-up ref, series ref, cap ref, GPIO text)
INPUTS = [
    ("BTN_TXRX", "R50", "R54", "C50", "GPIO 17, GO/STOP, low = pressed"),
    ("SW_ROLE", "R51", "R55", "C51", "GPIO 27, role, low = TX"),
    ("SW_MODE_NM", "R52", "R56", "C52", "GPIO 23, low = NM"),
    ("SW_MODE_MRM", "R53", "R57", "C53", "GPIO 16, low = MRM (neither = SRI)"),
]
ROW0, ROWSTEP = 99.06, 20.32
X_PU, X_SER, X_CAP = 154.94, 220.98, 287.02


def standalone_flags(s, nets, at):
    """PWR_FLAGs only for `build_carrier.py --sheet` (the nets are driven on another sheet); never in the project."""
    if not schgen.STANDALONE:
        return
    for i, n in enumerate(nets):
        s.pwr_flag(n, at=(at[0] + i * 15.24, at[1]))
    s.note("Stand-alone ERC only: PWR_FLAG stands in for the power sheet's GND flag.",
           at=(at[0], at[1] - 7.62), size=1.27)


def build():
    s = Sheet("ui", "UI: panel button, toggles, LEDs (DRAFT – for ET review)", global_nets=GLOBAL_NETS)

    s.note("UI – panel controls on JST-XH leads, bench button, LEDs", at=(25.4, 20.32), size=2.5)
    s.note("DRAFT – for ET review. Software: proto/port/linux/ui.c (inputs active low with the Pi's pull-ups; LEDs active high).\n"
           "Mode switch (J12, ON-OFF-ON): GPIO 23 low = NM, else GPIO 16 low = MRM, else (centre) SRI. Role (J11): low = TX.\n"
           "Pull-ups: the Pi's own (ui.c); rev A's external 10 kΩ are gone in rev B (one copper layer). 1 kΩ series: GPIO 16 may be driven by legacy firmware at boot\n"
           "(HAT design guide); 1 kΩ limits that to 3.3 mA into a closed switch. A TVS per lead right at the connectors.\n"
           "Panel holes: Ø7.5 mm for the PS1024 button, Ø6.5 mm for the 100-series toggles.\n"
           "Glue the XH housings to the board and the leads to the box (drop test).",
           at=(25.4, 27.94))

    # --- connectors -------------------------------------------------------------------------------------------
    s.note("CONNECTORS (panel parts off-board)", at=(25.4, 81.28), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J10", "GO/STOP button", at=(78.74, ROW0), fp=XH2,
          nets={"1": "BTN_TXRX_J", "2": "GND"}, mpn="B2B-XH-A(LF)(SN)", mfr="JST",
          Panel="E-Switch PS1024ABLK momentary, Ø7.5 mm hole")
    s.add("Connector_Generic:Conn_01x02", "J11", "role toggle", at=(78.74, ROW0 + ROWSTEP * 2), fp=XH2,
          nets={"1": "SW_ROLE_J", "2": "GND"}, mpn="B2B-XH-A(LF)(SN)", mfr="JST",
          Panel="E-Switch 100SP1T1B1M1QEH SPST, closed = TX, Ø6.5 mm hole")
    s.add("Connector_Generic:Conn_01x03", "J12", "mode toggle", at=(78.74, ROW0 + ROWSTEP * 3.25), fp=XH3,
          nets={"1": "SW_MODE_NM_J", "2": "GND", "3": "SW_MODE_MRM_J"}, mpn="B3B-XH-A(LF)(SN)", mfr="JST",
          Panel="E-Switch 100SP3T1B1M1QEH ON-OFF-ON, common = pin 2, Ø6.5 mm hole")
    s.note("J10: panel button E-Switch PS1024ABLK (momentary).\n"
           "Bench: plug the panel button into J10 (or bridge its two pins); no on-board button.\n"
           "J11: role toggle E-Switch 100SP1T1B1M1QEH, closed = TX;\n"
           "  may stay unfitted until Atenea Q8 (open = RX).\n"
           "J12: mode toggle E-Switch 100SP3T1B1M1QEH ON-OFF-ON:\n"
           "  1 NM, 2 common (GND), 3 MRM; centre = SRI.",
           at=(25.4, 182.88), size=1.27)

    # --- input conditioning -----------------------------------------------------------------------------------
    s.note("NO EXTERNAL PULL-UPS IN REV B (R50-R53 of rev A)", at=(X_PU - 20.32, 81.28), size=2.0)
    s.note("The inputs use the Pi's pull-ups, which ui.c requests (GPIO_V2_LINE_FLAG_BIAS_PULL_UP) before it reads\n"
           "them. Until then (boot) the BCM2837 default pull-down makes an open toggle read 'active' - nothing reads\n"
           "them then. On one copper layer a 3V3 bus to four pull-ups at the leads cuts the ground pour into islands.",
           at=(X_PU - 20.32, 86.36), size=1.27)
    s.note("SERIES 1 kΩ", at=(X_SER - 12.7, 81.28), size=2.0)
    s.note("100 nF AT THE GPIO", at=(X_CAP - 12.7, 81.28), size=2.0)
    for i, (line, rpu, rser, cap, gpio) in enumerate(INPUTS):
        y = ROW0 + i * ROWSTEP
        s.add("Device:R", rser, "1k", at=(X_SER, y), rot=90, fp=R1206, nets={"1": line + "_J", "2": line},
              mpn="RC1206FR-071KL", mfr="Yageo")
        s.add("Device:C", cap, "100n X7R", at=(X_CAP, y), rot=90, fp=C1206, nets={"1": line, "2": "GND"},
              mpn="CL31B104KBCNNNC", mfr="Samsung")
        s.note(gpio, at=(X_CAP + 12.7, y - 0.64), size=1.27)

    # --- ESD --------------------------------------------------------------------------------------------------
    s.note("ESD (one TVS per lead, at the connectors)", at=(X_PU - 20.32, 182.88), size=2.0)
    for i, (line, ref) in enumerate((("BTN_TXRX", "D12"), ("SW_ROLE", "D13"), ("SW_MODE_NM", "D14"),
                                     ("SW_MODE_MRM", "D15"))):
        s.add("Diode:SMF5V0A", ref, "SMF5.0A", at=(X_PU - 20.32 + i * 20.32, 203.2), fp=LAB["TVS"],
              nets={"1": line + "_J", "2": "GND"}, mpn="SMF5V0A-E3-08", mfr="Vishay", ds="")
    s.note("Rev B: four SMF5.0A (5 V standoff, 200 W, pin 1 = cathode to the line), the part already used for D2/D3,\n"
           "instead of rev A's SP0504 4-line array: on one copper layer a single SOT-23-5 cannot reach four parallel\n"
           "lead lines without a crossing. The TVS capacitance (~1 nF) sits before the 1 kΩ / 100 nF filter: harmless.",
           at=(X_PU - 20.32, 215.9), size=1.27)

    # --- LEDs -------------------------------------------------------------------------------------------------
    s.note("LEDs (active high, ≈ 4 mA from 3.3 V)", at=(X_SER - 12.7, 182.88), size=2.0)
    for i, (net, d, r, col, mpn) in enumerate((("LED_ACT", "D10", "R60", "green", "150080VS75000"),
                                               ("LED_STATUS", "D11", "R61", "red", "150080RS75000"))):
        y = 198.12 + i * 17.78
        s.add("Device:R", r, "330", at=(X_SER, y), rot=90, fp=R1206, nets={"1": net, "2": net + "_A"},
              mpn="RC1206FR-07330RL", mfr="Yageo")
        s.add("Device:LED", d, col, at=(X_CAP, y), rot=180, fp=LED0805, nets={"2": net + "_A", "1": "LED_RTN"},
              mpn=mpn, mfr="Würth Elektronik")
    s.note("D10 activity (GPIO 5), D11 status (GPIO 6).\n"
           "(3.3 − ~2.0 V) / 330 Ω ≈ 4 mA, well under the\n"
           "Pi's 16 mA per pin. No InGaN (blue/white: Vf too high).\n"
           "Rev B: the cathodes return on LED_RTN = J1 pin 25 (a Pi GND pin) - on one copper layer the LEDs sit\n"
           "in a pocket of J1's escape tracks, away from the carrier's pour.",
           at=(X_SER - 12.7, 233.68), size=1.27)

    standalone_flags(s, ["GND"], at=(101.6, 254.0))
    return s
