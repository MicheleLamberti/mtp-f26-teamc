"""Team C carrier, sheet radio: Ebyte E01-ML01SP4 (nRF24L01P + PA/LNA) on SPI0 of the Pi 3 A+.

DRAFT – for ET review. Pinout: Ebyte E01-ML01SP4 user manual rev 1.7 §3 p.4 (1 VCC, 2 CE, 3 CSN, 4 SCK, 5 MOSI,
6 MISO, 7 IRQ, 8/9/10 GND); limits §2.1/2.2 p.3 (VCC 2.0–3.6 V, abs. max 3.6 V, TX 120 mA); layout §4.1 p.5.
Pi side: radio/fw/linux/README.md (CE = GPIO 22, CSN = SPI0 CE0 = GPIO 8, IRQ = GPIO 24).
"""

import schgen  # noqa: E402
from schgen import Sheet
from nets import GLOBAL_NETS, DS

R0805 = "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"
C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"


def standalone_flags(s, nets, at):
    """PWR_FLAGs only for `build_carrier.py --sheet` (the nets are driven on another sheet); never in the project."""
    if not schgen.STANDALONE:
        return
    for i, n in enumerate(nets):
        s.pwr_flag(n, at=(at[0] + i * 20.32, at[1]))
    s.note("Stand-alone ERC only: these PWR_FLAGs stand in for the drivers on the power and pi_header sheets\n"
           "(LDO output, GND, the Pi's GPIO 22 through J1). They are not in the project.",
           at=(at[0], at[1] - 10.16), size=1.27)


def build():
    s = Sheet("radio", "Radio: E01-ML01SP4 (DRAFT – for ET review)", global_nets=GLOBAL_NETS)

    s.note("RADIO – Ebyte E01-ML01SP4 (nRF24L01P + PA/LNA, 2.4 GHz)", at=(25.4, 20.32), size=2.5)
    s.note("DRAFT – for ET review.\n"
           "VCC 2.0–3.6 V, ABS. MAX 3.6 V (manual §2.1): only 3V3_RADIO from the TLV75533 LDO on the power sheet,\n"
           "never the cell (4.2 V) and never the Pi's 3V3 (shared with the SoC, TX bursts of 120 mA).\n"
           "Layout (manual §4.1): GND pour under the module on both layers, stitched; no top-layer tracks under it;\n"
           "keep it away from the boost converter and its inductor (far corner of the HAT); IPEX end toward the board edge.\n"
           "Antenna: Ebyte TX2400-FPC-2509 flex, off-board on a box wall, on the module's IPEX (U.FL);\n"
           "glue the U.FL plug (drop test).",
           at=(25.4, 27.94))

    # --- module ---------------------------------------------------------------------------------------------
    s.note("MODULE", at=(165.1, 81.28), size=2.0)
    s.add("teamc:E01-ML01SP4", "U7", "E01-ML01SP4", fp="teamc:E01-ML01SP4", at=(190.5, 116.84),
          nets={"1": "3V3_RADIO", "2": "RADIO_CE", "3": "RADIO_CSN", "4": "SCK_R", "5": "MOSI_R", "6": "MISO_R",
                "7": "RADIO_IRQ", "8": "GND", "9": "GND", "10": "GND"},
          mpn="E01-ML01SP4", mfr="Ebyte", ds=DS["SP4"])
    s.note("Pads 9/10 = GND half-holes on the long edges\n(hidden, stacked on pin 8). CE also enables\n"
           "the LNA (manual §4.2): driven by GPIO 22,\n"
           "whose boot default pull-down keeps the\nradio idle until the driver starts.",
           at=(203.2, 134.62), size=1.27)

    # --- decoupling ---------------------------------------------------------------------------------------------
    s.note("DECOUPLING AT PAD 1 (110 µF total; TLV75533 allows 1–200 µF)", at=(254.0, 81.28), size=2.0)
    s.add("Device:C_Polarized", "C70", "100u 10V", at=(271.78, 99.06), rot=90, fp="Capacitor_SMD:CP_Elec_6.3x5.4",
          nets={"1": "3V3_RADIO", "2": "GND"},
          mpn="EEE-HA1A101WP (100 µF 10 V, 6.3 x 5.4 mm, 105 °C)", mfr="Panasonic")
    s.add("Device:C", "C71", "10u X5R", at=(271.78, 116.84), rot=90, fp=C0805, nets={"1": "3V3_RADIO", "2": "GND"},
          mpn="CL21A106KAYNNNE (10 µF 25 V X5R 0805)", mfr="Samsung")
    s.add("Device:C", "C72", "100n X7R", at=(271.78, 134.62), rot=90, fp=C0805, nets={"1": "3V3_RADIO", "2": "GND"},
          mpn="CL21B104KBCNNNC (100 nF 50 V X7R 0805)", mfr="Samsung")
    s.note("Place all three at pad 1, smallest closest. C70 rides the 120 mA TX bursts\n"
           "(PA on) so the LDO's load step does not dip VCC.", at=(254.0, 144.78), size=1.27)

    # --- SPI series resistors -----------------------------------------------------------------------------------
    s.note("SPI SOURCE TERMINATION (33 Ω)", at=(25.4, 81.28), size=2.0)
    s.add("Device:R", "R82", "33", at=(63.5, 99.06), rot=90, fp=R0805, nets={"1": "SPI_SCK", "2": "SCK_R"},
          mpn="RC0805FR-0733RL", mfr="Yageo")
    s.add("Device:R", "R83", "33", at=(63.5, 116.84), rot=90, fp=R0805, nets={"1": "SPI_MOSI", "2": "MOSI_R"},
          mpn="RC0805FR-0733RL", mfr="Yageo")
    s.add("Device:R", "R84", "33", at=(63.5, 134.62), rot=90, fp=R0805, nets={"1": "SPI_MISO", "2": "MISO_R"},
          mpn="RC0805FR-0733RL", mfr="Yageo")
    s.note("R82 SCK, R83 MOSI: at the Pi end (header J1, drivers = Pi).\n"
           "R84 MISO: at the radio end (driver = SP4 pad 6).\n"
           "Source termination of the 30–40 mm lines: cheap ringing control,\n"
           "0 Ω if the bench shows no need (spidev runs at ≤ 8 MHz).", at=(25.4, 144.78), size=1.27)

    # --- pull-ups ---------------------------------------------------------------------------------------------
    s.note("PULL-UPS TO 3V3_PI", at=(25.4, 172.72), size=2.0)
    s.add("Device:R", "R80", "10k", at=(63.5, 190.5), rot=90, fp=R0805, nets={"1": "3V3_PI", "2": "RADIO_CSN"},
          mpn="RC0805FR-0710KL", mfr="Yageo")
    s.add("Device:R", "R81", "10k", at=(63.5, 208.28), rot=90, fp=R0805, nets={"1": "3V3_PI", "2": "RADIO_IRQ"},
          mpn="RC0805FR-0710KL", mfr="Yageo")
    s.note("R80: CSN high = radio deselected while the Pi boots (GPIO 8 is an input\n"
           "with its default pull-up until spidev takes it).\n"
           "R81: IRQ idle level while the SP4 is unpowered or in reset; harmless otherwise.\n"
           "Both rails come from VBAT_SW together (boost → Pi, LDO → radio): no back-feed of the Pi.",
           at=(25.4, 218.44), size=1.27)

    # --- test point -------------------------------------------------------------------------------------------
    s.note("TEST POINT", at=(254.0, 172.72), size=2.0)
    s.add("Connector:TestPoint", "TP10", "3V3_RADIO", at=(271.78, 187.96),
          fp="TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm", nets={"1": "3V3_RADIO"},
          mpn="wire loop or Keystone 5000", mfr="Keystone")
    s.note("At the module: T0 checks VCC under TX bursts (3.6/3.3/3.0 V cell).", at=(254.0, 203.2), size=1.27)

    standalone_flags(s, ["GND", "3V3_RADIO", "RADIO_CE"], at=(165.1, 248.92))
    return s
