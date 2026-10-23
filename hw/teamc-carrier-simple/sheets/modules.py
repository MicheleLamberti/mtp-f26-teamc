"""Hand-soldered modules of carrier rev C (copied from rev B, hw/teamc-carrier-lab/sheets/modules.py, 23-Oct-26): pads
for the footprints (generated for rev B by hw/scripts/teamc_lib/gen_modules.py into hw/lib/teamc.pretty; rev C uses
those footprints as they are) and the symbol pin order (power.py). Data gathered 23-Oct-26 from the makers' CAD, not read off the drawings by eye:
Pololu DXF drill guides (hole crosshairs) checked against the dimension PDFs and pinout photos; the Adafruit Eagle
.brd (GitHub) parsed as XML.

Convention: module top view, component side up, origin = bottom-left corner of the module PCB, x right, y up, mm.
Every pin is a 0.1" male header through the carrier (drill 1.0, pad 2.0 = hole + 1.0 mm, UPC lab rule); the
modules' screw-terminal holes are not used.
"""

MODULES = {
    "U3V70F5": {
        "value": "Pololu U3V70F5 5V boost", "mpn": "2891 (U3V70F5)", "mfr": "Pololu",
        "url": "https://www.pololu.com/product/2891", "footprint": "Pololu_U3V70F5_Headers",
        "source": "Pololu reg21a-drill.dxf + u3v70x dimensions PDF",
        "size": (40.64, 15.24),   # PCB 1.57 mm, top parts 3.0 mm, nothing on the bottom
        "pins": [
            {"name": "VIN", "x": 5.08, "y": 1.27}, {"name": "VIN", "x": 5.08, "y": 3.81},
            {"name": "GND", "x": 5.08, "y": 6.35}, {"name": "GND", "x": 5.08, "y": 8.89},
            {"name": "ENABLE", "x": 5.08, "y": 11.43},
            {"name": "VOUT", "x": 35.56, "y": 6.35}, {"name": "VOUT", "x": 35.56, "y": 8.89},
            {"name": "GND", "x": 35.56, "y": 11.43}, {"name": "GND", "x": 35.56, "y": 13.97},
        ],
        "holes": [(2.16, 13.08, 2.2), (38.48, 2.16, 2.2)],   # M2 mounting holes (optional screws)
    },
    "IDEAL_DIODE": {
        "value": "Pololu ideal diode 20A", "mpn": "5388 (rvp01b)", "mfr": "Pololu",
        "url": "https://www.pololu.com/product/5388", "footprint": "Pololu_IdealDiode_5388_Headers",
        "source": "Pololu rvp01b-drill.dxf + reverse-voltage-protectors PDF p.2",
        "size": (17.78, 11.05),   # PCB 1.57 mm, top parts 1.4 mm; no mounting holes
        "pins": [
            {"name": "VIN", "x": 3.81, "y": 9.33}, {"name": "VIN", "x": 3.81, "y": 6.80},
            {"name": "GND", "x": 3.81, "y": 4.26}, {"name": "GND", "x": 3.81, "y": 1.71},
            {"name": "VOUT", "x": 13.97, "y": 9.33}, {"name": "VOUT", "x": 13.97, "y": 6.80},
            {"name": "GND", "x": 13.97, "y": 4.26}, {"name": "GND", "x": 13.97, "y": 1.71},
        ],
    },
    "MAX17048": {
        "value": "Adafruit MAX17048 fuel gauge", "mpn": "5580 (Rev B)", "mfr": "Adafruit",
        "url": "https://www.adafruit.com/product/5580", "footprint": "Adafruit_MAX17048_5580_Headers",
        "source": "Adafruit-MAX17048-PCB Adafruit-MAX17048-STEMMA.brd",
        "size": (25.40, 20.32),   # R2.54 corners; parts on top only (~5.6 mm), JST-PH ports left empty
        "pins": [
            {"name": "VIN", "x": 6.35, "y": 2.54}, {"name": "GND", "x": 8.89, "y": 2.54},
            {"name": "SCL", "x": 11.43, "y": 2.54}, {"name": "SDA", "x": 13.97, "y": 2.54},
            {"name": "INT", "x": 16.51, "y": 2.54}, {"name": "QSTART", "x": 19.05, "y": 2.54},
            {"name": "BAT", "x": 11.43, "y": 11.43}, {"name": "BAT_GND", "x": 13.97, "y": 11.43},   # JP2
        ],
        # its 2.5 mm plated holes (2.54, 2.54)/(22.86, 2.54) are not used: no carrier holes there
        "nets": {"VIN": "3V3_PI", "GND": "GND", "SCL": "I2C_SCL", "SDA": "I2C_SDA", "INT": None,
                 "QSTART": None, "BAT": "VBAT", "BAT_GND": "GND"},
        "note": "Runs from the cell: its chip (VDD) must sit on BAT through the 3-pad jumper SJ2 (centre pad = VDD, one side VIN,\n"
                "the other BAT). Adafruit says it runs with 3.3 or 5 V on VIN, so it ships VDD-BAT, but the GitHub board\n"
                "file shows SJ2 open (review 24-Oct): ON ARRIVAL check with a meter that SJ2's centre pad connects to BAT;\n"
                "if it does not, bridge centre-to-BAT with solder. VIN = the Pi's 3.3 V (3V3_PI, header pin 1): only its\n"
                "10 k I2C/INT pull-ups and its LED. BAT / BAT_GND = the JP2 pair, straight at VBAT. INT, QSTART unused:\n"
                "the software polls the gauge over I2C (0x36). Never set MODE.EnSleep in software.",
    },
}
