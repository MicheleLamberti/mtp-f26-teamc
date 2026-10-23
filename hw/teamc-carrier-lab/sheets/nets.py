"""Team C carrier rev B (UPC lab, hand-soldered modules): global nets and reference ranges per sheet.

Plan and decisions: hw/REVB_LAB_PLAN.md. A net listed here becomes a global label and connects across sheets;
GND is the power:GND symbol; any other net name is local to its sheet.
"""

GLOBAL_NETS = [
    "VBAT", "5V_BOOST", "5V_PI", "3V3_RADIO", "3V3_PI",
    "SPI_SCK", "SPI_MOSI", "SPI_MISO", "RADIO_CSN", "RADIO_CE", "RADIO_IRQ",
    "I2C_SDA", "I2C_SCL", "FG_ALRT", "BTN_TXRX", "SW_ROLE", "SW_MODE_NM", "SW_MODE_MRM",
    "LED_ACT", "LED_STATUS", "UART_TX", "UART_RX",
]

# Same ranges as rev A where the part is the same, so the docs keep their names
REF_RANGES = {
    "power": "J20 (cell), J22 (power toggle), J23 (charger lead), F1, Q1-Q9, U2 (boost), U3 (ideal diode), "
             "U4 (radio LDO), U6 (fuel gauge), D1-D9, C1-C49, R1-R49, TP1-TP9",
    "pi_link": "J1 (2x20 IDC box header), J13 (UART), MH1-MH4",
    "ui": "J10-J12, U11, D10-D19, C50-C69, R50-R79",
    "radio": "J30 (SP4 breakout socket), H30, C70-C79, R80-R89, TP10-TP19",
}

DS = {
    "AP2112": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "U3V70F5": "https://www.pololu.com/product/2891",
    "IDEAL_DIODE": "https://www.pololu.com/product/5388",
    "MAX17048_BRK": "https://www.adafruit.com/product/5580",
}

LAB = {   # footprints: lab copies (hw/scripts/teamc_lib/gen_lab.py) and hand-solder SMD
    "R": "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder",
    "C": "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder",
    "C1206": "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder",
    "CP": "Capacitor_SMD:CP_Elec_6.3x5.4",
    "LED": "LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder",
    "SOT23": "Package_TO_SOT_SMD:SOT-23",
    "SOT23_5": "Package_TO_SOT_SMD:SOT-23-5",
    "TVS": "Diode_SMD:D_SMF",
    "FUSE": "Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder",
    "TP": "TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm",
    "XH2": "teamc:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical_Pad2.0x2.4mm",
    "XH3": "teamc:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical_Pad2.0x2.4mm",
    "VH2": "Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical",     # stock pads 2.7 on 1.7 drill = + 1.0
    "IDC40": "teamc:IDC-Header_2x20_P2.54mm_Vertical_Pad2.0mm",
    "SOCK8": "teamc:PinSocket_1x08_P2.54mm_Vertical_Pad2.0mm",
    "HDR3": "teamc:PinHeader_1x03_P2.54mm_Vertical_Pad2.0mm",
    "M3": "MountingHole:MountingHole_3.2mm_M3",
}
