"""Team C carrier rev B (UPC lab), sheet pi_link: 2x20 IDC box header to the Raspberry Pi 3 A+ by ribbon, UART,
mounting holes.

DRAFT – for ET review. Pin map as rev A (hw/teamc-carrier/sheets/pi_header.py, hw/DESIGN_NOTES.md "Pin map"), except
GPIO 26 (CHG_STAT): the TP4056 charger has no status line, so pin 37 is not connected. A standard 40-way
female-female GPIO ribbon keeps pin 1 = pin 1 when both ends are keyed the same way (box header key toward the
board edge, red wire = pin 1). Keep the ribbon <= ~10 cm: 5 V for the Pi crosses it on pins 2/4.
"""

import schgen  # noqa: E402
from schgen import Sheet
from nets import GLOBAL_NETS, LAB

# header pin -> (net, BCM GPIO / function) ; None = not connected (no-connect flag)
HEADER = {
    1: (None, "3V3 (unused: pin 17 feeds the pull-ups)"), 2: ("5V_PI", "5V"),
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
    37: (None, "GPIO 26 (rev A CHG_STAT; no charger status in rev B)"), 38: (None, "GPIO 20"),
    39: ("GND", "GND"), 40: (None, "GPIO 21"),
}

J1_AT = (209.55, 147.32)


def build():
    s = Sheet("pi_link", "Pi link: 2x20 IDC box header + ribbon, UART, holes (rev B lab, DRAFT)",
              global_nets=GLOBAL_NETS)

    s.note("PI LINK – Raspberry Pi 3 Model A+ by a 40-way ribbon", at=(25.4, 20.32), size=2.5)
    s.note("DRAFT – for ET review. Rev B is not a HAT: on the lab's unplated holes a socket under a HAT would have to be\n"
           "soldered on the top side while the modules solder on the bottom. J1 is a shrouded 2x20 box header soldered\n"
           "on the copper side like every other THT part; odd pins leave to one side, even pins to the other.\n"
           "No ID EEPROM: pins 27/28 stay unconnected. The Pi's WiFi/BT chip is disabled or desoldered (Atenea Q22).\n"
           "5V_PI comes from the power sheet's ideal diode. Rule as in rev A: never plug the Pi's micro-USB while the\n"
           "carrier is connected and switched on (the ideal diode blocks back-feed into the boost, but two 5 V sources\n"
           "would still share the Pi). 3V3_PI = the Pi's own 3.3 V (pin 17): pull-ups and the radio LDO's EN only.",
           at=(25.4, 27.94))

    nets = {str(p): HEADER[p][0] for p in HEADER}
    s.add("Connector_Generic:Conn_02x20_Odd_Even", "J1", "RPi GPIO ribbon", at=J1_AT, fp=LAB["IDC40"], nets=nets,
          mpn="2x20 2.54 mm shrouded box header, straight (e.g. Würth 61204021621 / generic) + 40-way F-F ribbon")
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
    s.note("PWR_FLAG: the Pi drives 3V3_PI through the ribbon", at=(x0 - 24.13, y0 - 53.34), size=1.27)

    s.note("UART CONSOLE", at=(320.04, 40.64), size=2.0)
    s.add("Connector_Generic:Conn_01x03", "J13", "UART console", at=(337.82, 58.42), fp=LAB["HDR3"],
          nets={"1": "GND", "2": "UART_TX", "3": "UART_RX"}, mpn="1x03 2.54 mm pin header", mfr="Würth Elektronik")
    s.note("1 GND, 2 TX (Pi GPIO 14 out), 3 RX (GPIO 15 in). 3.3 V levels only.", at=(320.04, 71.12), size=1.27)

    s.note("MOUNTING (M3, unplated, keep copper away)", at=(320.04, 99.06), size=2.0)
    for i, ref in enumerate(("MH1", "MH2", "MH3", "MH4")):
        s.add("Mechanical:MountingHole", ref, "M3", at=(325.12 + (i % 2) * 25.4, 116.84 + (i // 2) * 17.78),
              fp=LAB["M3"], nets={}, mpn="M3 nylon standoff + screws (to the box base plate or above the Pi)")
    return s
