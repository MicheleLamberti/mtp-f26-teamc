"""Team C carrier rev C ("simple"): global nets, reference ranges and footprints.

Concept and checkpoint-1 decisions: hw/teamc-carrier-simple/CONCEPT.md. A net listed in GLOBAL_NETS becomes a global
label and connects across sheets; GND is the power:GND symbol; any other net name is local to its sheet.
"""

GLOBAL_NETS = [
    "VBAT", "5V_BOOST", "5V_PI", "3V3_RADIO", "3V3_PI",
    "SPI_SCK", "SPI_MOSI", "SPI_MISO", "RADIO_CSN", "RADIO_CE", "RADIO_IRQ",
    "I2C_SDA", "I2C_SCL", "BTN_TXRX", "SW_ROLE", "SW_MODE_NM", "SW_MODE_MRM",
    "LED_ACT", "LED_STATUS", "UART_TX", "UART_RX",
]

# Same reference names as rev A/B where the part does the same job, so the docs keep their names.
REF_RANGES = {
    "power": "BT1 (cell holder), F1 (fuse clips), D1 (crowbar), J22 (power toggle), J23 (charger lead), U2 (boost), "
             "U3 (ideal diode), U4 (radio LDO), U6 (fuel gauge), C1-C19, R9, TP1-TP4",
    "pi_link": "J1 (2x20 box header), J13 (UART), MH1-MH3",
    "ui": "J10-J12, J14 (LED lead), C50-C53, R54-R57, R60-R61",
    "radio": "J30 (SP4 breakout socket), H30, R80, R82-R84",
}

DS = {
    "U3V70F5": "https://www.pololu.com/product/2891",
    "IDEAL_DIODE": "https://www.pololu.com/product/5388",
    "MAX17048_BRK": "https://www.adafruit.com/product/5580",
    "MCP1700": "https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/"
               "MCP1700-Low-Quiescent-Current-LDO-20001826F.pdf",
    "1N5822": "https://www.st.com/resource/en/datasheet/1n5822.pdf",
    "BH18650": "https://www.memoryprotectiondevices.com/datasheets/BH-18650-PC-datasheet.pdf",
    "KEYS3517": "https://www.keyelco.com/product.cfm/product_id/794",
}

# Footprints. THT everywhere; lab copies (pad = hole + 1.0 mm) from hw/scripts/teamc_lib/gen_lab_revc.py and
# gen_lab.py (rev B), stock ones where the stock pads already meet the rule. 3D models: the stock model each
# footprint names (fetched by hw/scripts/fetch_3d.py), the modules' models from hw/lib/teamc.3dshapes.
FP = {
    "R": "teamc:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal_Pad1.8mm",   # 0.25 W body 6.3 mm, legs bent at 7.62
    "C": "teamc:C_Disc_D5.0mm_W2.5mm_P5.00mm_Pad1.8mm",   # 100 nF Vishay K104K10 / 1 uF TDK FG28: 5.0 mm leads
    "CP": "teamc:CP_Radial_D6.3mm_P2.50mm_Pad1.8mm",
    "TO92": "teamc:TO-92_Inline_Wide_Pad1.8mm",
    "D201": "Diode_THT:D_DO-201AD_P12.70mm_Horizontal",
    "FUSE": "Fuse:Fuseholder_Clip-5x20mm_Keystone_3517_Inline_P23.11x6.76mm_D1.70mm_Horizontal",
    "CELL": "Battery:BatteryHolder_MPD_BH-18650-PC",
    "TP": "TestPoint:TestPoint_Keystone_5010-5014_Multipurpose",
    "XH2": "teamc:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical_Pad2.0x2.4mm",
    "XH3": "teamc:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical_Pad2.0x2.4mm",
    "IDC40": "teamc:IDC-Header_2x20_P2.54mm_Vertical_Pad2.0mm",
    "SOCK8": "teamc:PinSocket_1x08_P2.54mm_Vertical_Pad2.0mm",
    "HDR3": "teamc:PinHeader_1x03_P2.54mm_Vertical_Pad2.0mm",
    "M3": "MountingHole:MountingHole_3.2mm_M3",
}

# Through-hole part numbers (EU stock: hw/BOM_revC.csv)
MPN = {
    "33": ("MFR-25FBF52-33R", "Yageo"), "330": ("MFR-25FBF52-330R", "Yageo"),
    "1k": ("MFR-25FBF52-1K", "Yageo"), "10k": ("MFR-25FBF52-10K", "Yageo"),
    "100n": ("K104K10X7RF5UH5", "Vishay"), "1u": ("FG28X7R1E105KRT06", "TDK"),
    "100u": ("EEU-FR1C101", "Panasonic"),
}
