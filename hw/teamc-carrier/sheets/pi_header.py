"""Team C carrier, sheet pi_header: the Raspberry Pi 3 Model A+ 40-pin header, mounting holes, UART console.

DRAFT – for ET review. Pin map: hw/DESIGN_NOTES.md "Pin map", proto/port/linux/ui.c (GPIO 17/27/23/16 inputs,
5/6 LEDs), radio/fw/linux/README.md (CE 22, IRQ 24, CSN = SPI0 CE0). Header numbering checked against
https://pinout.xyz (Raspberry Pi 40-pin header, same on every 40-pin model incl. the 3 A+).
"""

import schgen  # noqa: E402
from schgen import Sheet
from nets import GLOBAL_NETS, DS

# header pin -> (net, BCM GPIO / function) ; None = not connected (no-connect flag)
HEADER = {
    1: ("3V3_PI", "3V3"), 2: ("5V_PI", "5V"),
    3: ("I2C_SDA", "GPIO 2 SDA1"), 4: ("5V_PI", "5V"),
    5: ("I2C_SCL", "GPIO 3 SCL1"), 6: ("GND", "GND"),
    7: (None, "GPIO 4"), 8: ("UART_TX", "GPIO 14 TXD0"),
    9: ("GND", "GND"), 10: ("UART_RX", "GPIO 15 RXD0"),
    11: ("BTN_TXRX", "GPIO 17"), 12: (None, "GPIO 18"),
    13: ("SW_ROLE", "GPIO 27"), 14: ("GND", "GND"),
    15: ("RADIO_CE", "GPIO 22"), 16: ("SW_MODE_NM", "GPIO 23"),
    17: ("3V3_PI", "3V3"), 18: ("RADIO_IRQ", "GPIO 24"),
    19: ("SPI_MOSI", "GPIO 10 MOSI0"), 20: ("GND", "GND"),
    21: ("SPI_MISO", "GPIO 9 MISO0"), 22: ("FG_ALRT", "GPIO 25"),
    23: ("SPI_SCK", "GPIO 11 SCLK0"), 24: ("RADIO_CSN", "GPIO 8 CE0"),
    25: ("GND", "GND"), 26: (None, "GPIO 7 CE1"),
    27: (None, "ID_SD (GPIO 0): keep NC"), 28: (None, "ID_SC (GPIO 1): keep NC"),
    29: ("LED_ACT", "GPIO 5"), 30: ("GND", "GND"),
    31: ("LED_STATUS", "GPIO 6"), 32: (None, "GPIO 12"),
    33: (None, "GPIO 13"), 34: ("GND", "GND"),
    35: (None, "GPIO 19"), 36: ("SW_MODE_MRM", "GPIO 16"),
    37: ("CHG_STAT", "GPIO 26"), 38: (None, "GPIO 20"),
    39: ("GND", "GND"), 40: (None, "GPIO 21"),
}

J1_AT = (209.55, 147.32)


def standalone_flags(s, nets, at):
    """PWR_FLAGs only for `build_carrier.py --sheet` (the nets are driven on another sheet); never in the project."""
    if not schgen.STANDALONE:
        return
    for i, n in enumerate(nets):
        s.pwr_flag(n, at=(at[0] + i * 15.24, at[1]))
    s.note("Stand-alone ERC only: PWR_FLAG(s) above stand in for the drivers on the power sheet.",
           at=(at[0], at[1] - 7.62), size=1.27)


def build():
    s = Sheet("pi_header", "Pi header: RPi 3 A+ 40-pin, UART, holes (DRAFT)",
              global_nets=GLOBAL_NETS)

    s.note("PI HEADER – Raspberry Pi 3 Model A+ only (65 x 56 mm)", at=(25.4, 20.32), size=2.5)
    s.note("DRAFT – for ET review. The HAT sits on the Pi's 40-pin header (J1, socket on the HAT's underside).\n"
           "No ID EEPROM: pins 27/28 (ID_SD/ID_SC) stay unconnected (allowed for a non-'HAT' add-on board).\n"
           "The Pi's WiFi/BT chip is disabled in software or desoldered (rules p.6, Atenea Q22).\n"
           "5V_PI comes from the power sheet's ideal diode (back-feeds the Pi's 5 V after its polyfuse).\n"
           "3V3_PI = the Pi's own 3.3 V (pins 1/17): pull-ups only, no load. The radio has its own LDO (3V3_RADIO).",
           at=(25.4, 27.94))

    nets = {str(p): HEADER[p][0] for p in HEADER}
    s.add("Connector_Generic:Conn_02x20_Odd_Even", "J1", "RPi 3 A+ GPIO", at=J1_AT,
          fp="teamc:PinSocket_2x20_P2.54mm_Vertical_Pad1.5mm", nets=nets,
          mpn="M20-7832046 (2x20 female, 8.5 mm; 11 mm stack with M2.5x11 standoffs)", mfr="Harwin")
    # pin-function table next to the labels: odd pins on the left, even on the right
    x0, y0 = J1_AT
    for p, (net, fn) in HEADER.items():
        row = (p - 1) // 2
        y = y0 - 22.86 + row * 2.54 - 0.64
        if p % 2:
            s.note(f"{p:>2}  {fn}", at=(x0 - 62.23, y), size=1.27)
        else:
            s.note(f"{p:>2}  {fn}", at=(x0 + 36.83, y), size=1.27)
    s.note("Header pin / BCM function (pinout.xyz)", at=(x0 - 62.23, y0 - 30.48), size=1.27)
    s.note("Header pin / BCM function", at=(x0 + 36.83, y0 - 30.48), size=1.27)

    s.pwr_flag("3V3_PI", at=(x0 - 30.48, y0 - 50.8))
    s.note("PWR_FLAG: the Pi drives 3V3_PI\n(5V_PI and GND are flagged on the power sheet)",
           at=(x0 - 24.13, y0 - 53.34), size=1.27)

    # UART console
    s.note("UART CONSOLE", at=(320.04, 40.64), size=2.0)
    s.add("Connector_Generic:Conn_01x03", "J13", "UART console", at=(337.82, 58.42),
          fp="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
          nets={"1": "GND", "2": "UART_TX", "3": "UART_RX"}, mpn="61300311121 (1x03 2.54 mm pin header)",
          mfr="Würth Elektronik")
    s.note("1 GND, 2 TX (Pi GPIO 14 out), 3 RX (GPIO 15 in).\nMatches common USB-UART leads (their RX to pin 2).\n"
           "3.3 V levels only: never a 5 V adapter.", at=(320.04, 71.12), size=1.27)

    # mounting
    s.note("MOUNTING (HAT spec: M2.5, non-plated, not grounded)", at=(320.04, 99.06), size=2.0)
    for i, ref in enumerate(("MH1", "MH2", "MH3", "MH4")):
        s.add("Mechanical:MountingHole", ref, "M2.5", at=(325.12 + (i % 2) * 25.4, 116.84 + (i // 2) * 17.78),
              fp="MountingHole:MountingHole_2.7mm_M2.5", nets={},
              mpn="Würth 970110155 standoff M2.5x11 F/F nylon + M2.5x6 screws", mfr="Würth Elektronik")
    s.note("Holes at the Pi's 49 x 58 mm pattern (board template places them).\n"
           "Nylon standoffs: the hole is NPTH, keep copper 3.1 mm away (Ø6.2).", at=(320.04, 147.32), size=1.27)

    standalone_flags(s, ["GND"], at=(320.04, 190.5))
    return s
