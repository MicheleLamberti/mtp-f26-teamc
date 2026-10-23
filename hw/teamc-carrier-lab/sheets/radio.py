"""Team C carrier rev B (UPC lab), sheet radio: socket for the lab-made SP4 breakout (hw/sp4-breakout).

DRAFT – for ET review. The breakout carries the E01-ML01SP4 and its 100 uF + 10 uF + 100 nF; its 1x8 header (pins
pointing down, on the breakout's back) plugs into J30 here, SP4 side up. Header order = the breakout's J1:
1 GND, 2 VCC, 3 CE, 4 CSN, 5 SCK, 6 MOSI, 7 MISO, 8 IRQ (hw/scripts/build_breakout.py).
Pi side: radio/fw/linux/README.md (CE = GPIO 22, CSN = SPI0 CE0 = GPIO 8, IRQ = GPIO 24).
"""

import schgen  # noqa: E402
from schgen import Sheet
from nets import GLOBAL_NETS, LAB


def standalone_flags(s, nets, at):
    """PWR_FLAGs only for a stand-alone sheet ERC (the nets are driven on another sheet); never in the project."""
    if not schgen.STANDALONE:
        return
    for i, n in enumerate(nets):
        s.pwr_flag(n, at=(at[0] + i * 20.32, at[1]))


def build():
    s = Sheet("radio", "Radio: SP4 breakout socket (rev B lab, DRAFT – for ET review)", global_nets=GLOBAL_NETS)

    s.note("RADIO – socket for the lab-made E01-ML01SP4 breakout", at=(25.4, 20.32), size=2.5)
    s.note("DRAFT – for ET review.\n"
           "VCC 2.0–3.6 V, ABS. MAX 3.6 V: only 3V3_RADIO from the AP2112K on the power sheet (enabled by the Pi's 3V3,\n"
           "so the radio is off whenever the Pi is off). Never the cell, never the Pi's 3V3 pin.\n"
           "The breakout has the module's 100 uF + 10 uF + 100 nF. Rev B: no socket-end cap (rev A C71) and no test loop\n"
           "(rev A TP10): C12 (10 uF) at the LDO is 6 mm from the socket, and 3V3_RADIO is probed on C12's pad.\n"
           "Place J30 so the breakout's IPEX end faces the board edge, far from the boost module; M3 standoff at the\n"
           "breakout's H1 (H30 here, ~11 mm standoff = socket + header height). Antenna: TX2400-FPC-2509 flex on a box\n"
           "wall on the U.FL (glue the plug, drop test).",
           at=(25.4, 27.94))

    s.note("BREAKOUT SOCKET", at=(165.1, 81.28), size=2.0)
    s.add("Connector_Generic:Conn_01x08", "J30", "SP4 breakout", at=(190.5, 116.84), fp=LAB["SOCK8"],
          nets={"1": "GND", "2": "3V3_RADIO", "3": "RADIO_CE", "4": "RADIO_CSN", "5": "SCK_R", "6": "MOSI_R",
                "7": "MISO_R", "8": "RADIO_IRQ"},
          mpn="1x08 2.54 mm female socket, 8.5 mm (e.g. Samtec SSW-108-01-T-S / generic)")
    s.add("Mechanical:MountingHole", "H30", "M3", at=(215.9, 99.06), fp=LAB["M3"], nets={},
          mpn="M3 x 11 mm F/F nylon standoff + 2 x M3 x 6 screws")

    s.note("SPI SOURCE TERMINATION (33 Ω)", at=(25.4, 81.28), size=2.0)
    s.add("Device:R", "R82", "33", at=(63.5, 99.06), rot=90, fp=LAB["R"], nets={"1": "SPI_SCK", "2": "SCK_R"},
          mpn="RC1206FR-0733RL", mfr="Yageo")
    s.add("Device:R", "R83", "33", at=(63.5, 116.84), rot=90, fp=LAB["R"], nets={"1": "SPI_MOSI", "2": "MOSI_R"},
          mpn="RC1206FR-0733RL", mfr="Yageo")
    s.add("Device:R", "R84", "33", at=(63.5, 134.62), rot=90, fp=LAB["R"], nets={"1": "SPI_MISO", "2": "MISO_R"},
          mpn="RC1206FR-0733RL", mfr="Yageo")
    s.note("R82 SCK, R83 MOSI: at the IDC header J1 (drivers = Pi, through the ribbon).\n"
           "R84 MISO: at J30 (driver = SP4). The ribbon adds ~10 cm: keep these (0 Ω if the bench shows no need).",
           at=(25.4, 144.78), size=1.27)

    s.note("PULL-UP TO 3V3_RADIO", at=(25.4, 172.72), size=2.0)
    s.add("Device:R", "R80", "10k", at=(63.5, 190.5), rot=90, fp=LAB["R"], nets={"1": "3V3_RADIO", "2": "RADIO_CSN"},
          mpn="RC1206FR-0710KL", mfr="Yageo")
    s.note("R80: CSN high = radio deselected while the Pi boots.\n"
           "Rev B: to 3V3_RADIO (rev A: 3V3_PI), so it sits at the socket without a 3V3_PI track there on the single\n"
           "copper layer. 3V3_RADIO comes up with 3V3_PI (the LDO's EN is 3V3_PI): CSN is still high from the first\n"
           "milliseconds of the Pi's boot, and both rails are off together.\n"
           "No IRQ pull-up in rev B (rev A R81): the Linux HAL requests the Pi's pull-up on GPIO 24 (IRQ is open drain,\n"
           "falling edge only; radio/fw/linux/nrf24_hal_linux.c), and on one copper layer 3V3 does not reach pin 8.",
           at=(25.4, 218.44), size=1.27)

    standalone_flags(s, ["GND", "3V3_RADIO", "RADIO_CE"], at=(165.1, 248.92))
    return s
