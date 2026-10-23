"""Team C carrier rev C ("simple"), sheet radio: socket for the lab-made SP4 breakout (hw/sp4-breakout).
DRAFT - checkpoint 2.

Decided (Santiago, 23-Oct): the carrier only provides the socket, the 3.3 V supply and the SPI/CE/IRQ wiring; the
breakout carries the E01-ML01SP4 and its 100 uF + 10 uF + 100 nF. Header order = the breakout's J1:
1 GND, 2 VCC, 3 CE, 4 CSN, 5 SCK, 6 MOSI, 7 MISO, 8 IRQ (hw/scripts/build_breakout.py). M3 standoff at the breakout's
H1 (offset from J30 pin 1 in place_carrier_lab.BREAKOUT). Pi side: radio/fw/linux/README.md (CE = GPIO 22,
CSN = SPI0 CE0 = GPIO 8, IRQ = GPIO 24; SPI at 4 MHz by default).
"""

import schgen
from schgen import Sheet
from nets import GLOBAL_NETS, FP, MPN


def standalone_flags(s, nets, at):
    """PWR_FLAGs only for a stand-alone sheet ERC (the nets are driven on another sheet); never in the project."""
    if not schgen.STANDALONE:
        return
    for i, n in enumerate(nets):
        s.pwr_flag(n, at=(at[0] + i * 20.32, at[1]))


def build():
    s = Sheet("radio", "Radio: SP4 breakout socket (rev C, DRAFT)", global_nets=GLOBAL_NETS)

    s.note("RADIO – socket for the lab-made E01-ML01SP4 breakout", at=(25.4, 20.32), size=2.5)
    s.note("The breakout plugs into J30 (its pins down, the SP4 on top) and is held by an M3 standoff at H30.\n"
           "VCC = 3V3_RADIO from the MCP1700 on the power sheet only (radio range 2.0-3.6 V, absolute max 3.6 V).\n"
           "Put J30 at the board end nearest the antenna wall and away from the boost module; the flex antenna's\n"
           "U.FL plug goes onto the SP4 (glue the plug for the drop test).",
           at=(25.4, 27.94))

    s.note("BREAKOUT SOCKET", at=(165.1, 81.28), size=2.0)
    s.add("Connector_Generic:Conn_01x08", "J30", "SP4 breakout", at=(190.5, 116.84), fp=FP["SOCK8"],
          nets={"1": "GND", "2": "3V3_RADIO", "3": "RADIO_CE", "4": "RADIO_CSN", "5": "SCK_R", "6": "MOSI_R",
                "7": "MISO_R", "8": "RADIO_IRQ"},
          mpn="PPTC081LFBN-RC (Sullins 1x08 female socket, straight THT)", mfr="Sullins")
    s.add("Mechanical:MountingHole", "H30", "M3", at=(215.9, 99.06), fp=FP["M3"], nets={},
          mpn="M3 x 11 mm nylon standoff F/F + 2 x M3 x 6 nylon screws")

    s.note("SPI SERIES RESISTORS (33 Ω, through-hole)", at=(25.4, 81.28), size=2.0)
    for ref, a, b, y in (("R82", "SPI_SCK", "SCK_R", 99.06), ("R83", "SPI_MOSI", "MOSI_R", 116.84),
                         ("R84", "SPI_MISO", "MISO_R", 134.62)):
        mpn, mfr = MPN["33"]
        s.add("Device:R", ref, "33", at=(63.5, y), rot=90, fp=FP["R"], nets={"1": a, "2": b}, mpn=mpn, mfr=mfr)
    s.note("33 Ω in SCK, MOSI and MISO soften the fast edges that travel down the 15 cm ribbon (less ringing).\n"
           "On this one-layer board their legs are 7.6 mm apart, so another track may pass under a resistor body\n"
           "between its legs: the board drawing says which. A 0 Ω wire link can replace one if the bench shows no need.",
           at=(25.4, 144.78), size=1.27)

    s.note("CSN PULL-UP", at=(25.4, 172.72), size=2.0)
    mpn, mfr = MPN["10k"]
    s.add("Device:R", "R80", "10k", at=(63.5, 190.5), rot=90, fp=FP["R"], nets={"1": "3V3_RADIO", "2": "RADIO_CSN"},
          mpn=mpn, mfr=mfr)
    s.note("R80 keeps CSN high (radio not selected) while the Pi boots. 3V3_RADIO and the Pi's 3.3 V come up and go\n"
           "down together (both from 5V_PI). No IRQ pull-up: the Linux HAL turns on the Pi's own pull-up on GPIO 24\n"
           "(IRQ is open drain, falling edge).",
           at=(25.4, 203.2), size=1.27)

    standalone_flags(s, ["GND", "3V3_RADIO"], at=(165.1, 248.92))
    return s
