"""Team C carrier: global nets shared by the sheets and the reference-designator ranges per sheet.

See hw/DESIGN_NOTES.md (net table). A net listed here becomes a global label and connects across sheets;
GND is the power:GND symbol; any other net name is local to its sheet.
"""

GLOBAL_NETS = [
    "VBAT", "VBAT_SW", "5V_PI", "3V3_RADIO", "3V3_PI", "VBUS_USB",
    "SPI_SCK", "SPI_MOSI", "SPI_MISO", "RADIO_CSN", "RADIO_CE", "RADIO_IRQ",
    "I2C_SDA", "I2C_SCL", "FG_ALRT", "BTN_TXRX", "SW_ROLE", "SW_MODE_NM", "SW_MODE_MRM",
    "LED_ACT", "LED_STATUS", "CHG_STAT", "UART_TX", "UART_RX",
]

# Reference designators per sheet (keeps the sheets independent; the template's J1 and MH1-MH4 keep their places)
REF_RANGES = {
    "power": "J2 (USB-C), J20-J29, U1-U6, U12, Q1-Q9, L1-L9, D1-D9, C1-C49, R1-R49, TP1-TP9, JP1-JP9",
    "pi_header": "J1 (40-pin socket), MH1-MH4, J13 (UART), C90-C99, R90-R99",
    "ui": "J10-J12, SW1-SW9, U11, D10-D19, C50-C69, R50-R79",
    "radio": "U7, C70-C79, R80-R89, TP10-TP19",
}

DS = {
    "SP4": "https://www.cdebyte.com/products/E01-ML01SP4",
    "MAX17048": "https://cdn.sparkfun.com/assets/5/2/7/6/6/MAX17048-MAX17049.pdf",
    "TPS61022": "https://www.ti.com/lit/ds/symlink/tps61022.pdf",
    "TLV755P": "https://www.ti.com/lit/ds/symlink/tlv755p.pdf",
    "TPS63001": "https://www.ti.com/lit/ds/symlink/tps63001.pdf",
    "MCP73831": "https://ww1.microchip.com/downloads/en/DeviceDoc/20001984g.pdf",
    "HAT": "https://github.com/raspberrypi/hats/blob/master/designguide.md",
    "PI3B_SCHEM": "https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-reduced-schematics.pdf",
}
# Parts not listed: leave ds="" so the KiCad library symbol's own Datasheet field is used.
