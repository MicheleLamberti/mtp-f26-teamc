"""Team C carrier rev C ("simple"), sheet pi_link: 2x20 box header to the Raspberry Pi 3 A+ by a 40-wire ribbon,
UART console, mounting holes. DRAFT - checkpoint 2.

Pin map unchanged (hw/DESIGN_NOTES.md "Pin map", proto/port/linux/ui.c, radio/fw/linux/nrf24_hal_linux.h) - no GPIO
changes (Santiago, checkpoint 1). Rev C ties ALL eight GND pins to the carrier ground (simplicity rule 4). FG_ALRT
(GPIO 25) and CHG_STAT (GPIO 26) are not used. A standard 40-way female-female GPIO ribbon keeps pin 1 = pin 1 when
both ends are keyed the same way (red wire = pin 1); check it with a multimeter before the first power-up.
"""

from schgen import Sheet
from nets import GLOBAL_NETS, FP

# header pin -> (net, BCM function); None = not connected (no-connect flag)
HEADER = {
    1: ("3V3_PI", "3V3 (feeds 3V3_PI: the fuel gauge's I2C pull-ups only)"), 2: ("5V_PI", "5V"),
    3: ("I2C_SDA", "GPIO 2 SDA1"), 4: ("5V_PI", "5V"),
    5: ("I2C_SCL", "GPIO 3 SCL1"), 6: ("GND", "GND"),
    7: (None, "GPIO 4"), 8: ("UART_TX", "GPIO 14 TXD0"),
    9: ("GND", "GND"), 10: ("UART_RX", "GPIO 15 RXD0"),
    11: ("BTN_TXRX", "GPIO 17 GO/STOP"), 12: (None, "GPIO 18"),
    13: ("SW_ROLE", "GPIO 27 role"), 14: ("GND", "GND"),
    15: ("RADIO_CE", "GPIO 22 radio CE"), 16: ("SW_MODE_NM", "GPIO 23 mode NM"),
    17: (None, "3V3 (unused: pin 1 is used)"), 18: ("RADIO_IRQ", "GPIO 24 radio IRQ"),
    19: ("SPI_MOSI", "GPIO 10 MOSI0"), 20: ("GND", "GND"),
    21: ("SPI_MISO", "GPIO 9 MISO0"), 22: (None, "GPIO 25 (FG_ALRT, not used)"),
    23: ("SPI_SCK", "GPIO 11 SCLK0"), 24: ("RADIO_CSN", "GPIO 8 CE0 = radio CSN"),
    25: ("GND", "GND"), 26: (None, "GPIO 7 CE1"),
    27: (None, "ID_SD: keep NC"), 28: (None, "ID_SC: keep NC"),
    29: ("LED_ACT", "GPIO 5 LED activity"), 30: ("GND", "GND"),
    31: ("LED_STATUS", "GPIO 6 LED status"), 32: (None, "GPIO 12"),
    33: (None, "GPIO 13"), 34: ("GND", "GND"),
    35: (None, "GPIO 19"), 36: ("SW_MODE_MRM", "GPIO 16 mode MRM"),
    37: (None, "GPIO 26 (not used)"), 38: (None, "GPIO 20"),
    39: ("GND", "GND"), 40: (None, "GPIO 21"),
}

J1_AT = (209.55, 147.32)


def build():
    s = Sheet("pi_link", "Pi link: 2x20 box header + ribbon, UART, holes (rev C, DRAFT)", global_nets=GLOBAL_NETS)

    s.note("PI LINK – Raspberry Pi 3 Model A+ on a 40-wire ribbon", at=(25.4, 20.32), size=2.5)
    s.note("J1 is a shrouded (keyed) 2x20 box header; a 15 cm 40-wire female-female ribbon goes to the Pi's GPIO header.\n"
           "The key stops it going in rotated. Red wire = pin 1 at both ends.\n"
           "5V_PI (pins 2, 4) comes from the ideal diode on the power sheet. All eight GND pins go to the carrier ground:\n"
           "they are the return path of the Pi's supply and of the SPI signals.\n"
           "3V3_PI = the Pi's own 3.3 V, from pin 1 only (pin 17 unused): it only feeds the fuel gauge's I2C pull-ups.\n"
           "Pins 27/28 (ID EEPROM) stay unconnected. The Pi's WiFi/BT chip is disabled or removed (Atenea Q22).\n"
           "Do not power the Pi from its micro-USB while the box is on (the ideal diode protects the boost, but two\n"
           "supplies would share the Pi). For development: unplug the ribbon, or switch the box off.",
           at=(25.4, 27.94))

    nets = {str(p): HEADER[p][0] for p in HEADER}
    s.add("Connector_Generic:Conn_02x20_Odd_Even", "J1", "RPi GPIO ribbon", at=J1_AT, fp=FP["IDC40"], nets=nets,
          mpn="61204021621 (Würth 2x20 shrouded box header, straight THT; any equivalent)", mfr="Würth Elektronik")
    x0, y0 = J1_AT
    for p, (net, fn) in HEADER.items():
        row = (p - 1) // 2
        y = y0 - 22.86 + row * 2.54 - 0.64
        if p % 2:
            s.note(f"{p:>2}  {fn}", at=(x0 - 72.39, y), size=1.27)
        else:
            s.note(f"{p:>2}  {fn}", at=(x0 + 36.83, y), size=1.27)
    s.note("Header pin / BCM function (pinout.xyz)", at=(x0 - 72.39, y0 - 30.48), size=1.27)
    s.note("Header pin / BCM function", at=(x0 + 36.83, y0 - 30.48), size=1.27)

    s.pwr_flag("3V3_PI", at=(x0 - 30.48, y0 - 50.8))
    s.note("PWR_FLAG: the Pi drives 3V3_PI through the ribbon", at=(x0 - 24.13, y0 - 53.34), size=1.27)

    s.note("UART CONSOLE (bench)", at=(320.04, 40.64), size=2.0)
    s.add("Connector_Generic:Conn_01x03", "J13", "UART console", at=(337.82, 58.42), fp=FP["HDR3"],
          nets={"1": "GND", "2": "UART_TX", "3": "UART_RX"}, mpn="1x03 male pin header (cut from the 1x40 strip in the BoM)")
    s.note("1 GND, 2 TX (Pi GPIO 14 out), 3 RX (GPIO 15 in). 3.3 V USB-serial adapters only (never 5 V).",
           at=(320.04, 71.12), size=1.27)

    s.note("MOUNTING (M3, unplated, no copper around)", at=(320.04, 99.06), size=2.0)
    for i, ref in enumerate(("MH1", "MH2", "MH3")):
        s.add("Mechanical:MountingHole", ref, "M3", at=(325.12 + (i % 2) * 25.4, 116.84 + (i // 2) * 17.78),
              fp=FP["M3"], nets={}, mpn="M3 x 10 mm nylon standoff + M3 x 6 nylon screws (to the box floor)")
    return s
