"""Team C carrier rev B (UPC lab), sheet power: cell, fuse, reverse FET, charger lead, power toggle, 5 V boost
module, ideal-diode module, radio LDO, fuel-gauge module, test points. DRAFT – for ET review.

Modules and their pins: modules.py (from the makers' drawings); the symbol pin numbers are the order there and the
footprints come from hw/scripts/teamc_lib/gen_modules.py. Parts and stock: hw/REVB_LAB_PLAN.md.
Pinouts: AP2112K (Diodes AP2112 datasheet, SOT-23-5: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT; >= 1 uF ceramic in/out);
DMP2035U / AO3401A / 2N7002 SOT-23: 1 G, 2 S, 3 D; SMF5V0A: pin 1 = cathode.
"""
import schgen
from schgen import Sheet
from nets import GLOBAL_NETS, DS, LAB
from modules import MODULES

RES = {"10k": "RC0805FR-0710KL", "100k": "RC0805FR-07100KL", "1k": "RC0805FR-071KL"}


def R(s, ref, val, at, n1, n2):
    return s.add("Device:R", ref, val + " 1%", fp=LAB["R"], at=at, rot=90, nets={"1": n1, "2": n2}, mpn=RES[val],
                 mfr="Yageo")


def C(s, ref, val, at, n1, n2, fp=None, mpn=""):
    return s.add("Device:C", ref, val, fp=fp or LAB["C"], at=at, rot=90, nets={"1": n1, "2": n2}, mpn=mpn)


def CP(s, ref, at, plus):
    return s.add("Device:C_Polarized", ref, "100u 16V", fp=LAB["CP"], at=at, rot=90, nets={"1": plus, "2": "GND"},
                 mpn="EEE-FK1C101P", mfr="Panasonic")


def TVS(s, ref, at, net):
    return s.add("Diode:SMF5V0A", ref, "SMF5.0A", fp=LAB["TVS"], at=at, nets={"1": net, "2": "GND"},
                 mpn="SMF5V0A-E3-08", mfr="Vishay", ds="")


def module(s, ref, key, at, nets_by_name, **kw):
    """A module as one Conn_01xNN symbol: pin n = the n-th pad in modules.py; nets given by pad name."""
    m = MODULES[key]
    pins = m["pins"]
    nets = {}
    for i, p in enumerate(pins, 1):
        if p["name"] not in nets_by_name:
            raise ValueError(f"{ref} ({key}): no net for pad {p['name']}")
        nets[str(i)] = nets_by_name[p["name"]]
    return s.add(f"Connector_Generic:Conn_01x{len(pins):02d}", ref, m["value"], fp="teamc:" + m["footprint"],
                 at=at, nets=nets, mpn=m["mpn"], mfr=m["mfr"], ds=m["url"], **kw)


def build():
    s = Sheet("power", "Power: cell, boost/ideal-diode/fuel-gauge modules, radio LDO (rev B lab, DRAFT)",
              global_nets=GLOBAL_NETS)
    s.note("POWER – one protected 18650 → 5 V for the Pi 3 A+ (Pololu U3V70F5) and 3.3 V for the radio (AP2112K)",
           at=(15.24, 12.7), size=2.5)

    # ===== 1. battery, fuse, reverse FET ===========================================================================
    s.note("1  BATTERY, FUSE & REVERSE PROTECTION", at=(15.24, 20.32), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J20", "BATT 18650", at=(43.18, 38.1), fp=LAB["VH2"],
          nets={"1": "BAT_IN", "2": "GND"}, mpn="B2P-VH", mfr="JST")
    s.add("Device:Fuse", "F1", "5A fast", fp=LAB["FUSE"], at=(62.23, 25.4), rot=90,
          nets={"1": "BAT_IN", "2": "BAT_RAW"}, mpn="0466005.NR (1206, 5 A, very fast; or 0466005.NRHF)",
          mfr="Littelfuse")
    s.add("Transistor_FET:AO3401A", "Q1", "DMP2035U", fp=LAB["SOT23"], at=(80.01, 38.1), rot=90,
          nets={"1": "Q1_G", "2": "VBAT", "3": "BAT_RAW"}, mpn="DMP2035U-7 (AO3401A fallback)", mfr="Diodes Inc.",
          ds="")
    R(s, "R1", "10k", (80.01, 63.5), "Q1_G", "GND")
    TVS(s, "D3", (80.01, 81.28), "VBAT")
    CP(s, "C5", (106.68, 63.5), "VBAT")
    s.note("Protected 18650 (PCM inside, trip >= 3 A) in a holder on the box floor, JST-VH lead to J20.\n"
           "Q1: body diode conducts for a correct cell, then VGS = -VBAT turns it on; a reversed cell is blocked.\n"
           "DMP2035U <= 45 mΩ at -2.5 V (AO3401A ~85 mΩ: ~0.25 V at 3 A). C5: bulk at the boost input (Pololu asks\n"
           "for >= 33 uF when the cell is on a lead). Charger (J23) on VBAT: Q1 conducts both ways once on.",
           at=(15.24, 91.44), size=1.27)

    # ===== 2. charger lead =========================================================================================
    s.note("2  CHARGER LEAD (TP4056 USB-C module at the box wall)", at=(137.16, 20.32), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J23", "TP4056 B+/B-", at=(160.02, 38.1), fp=LAB["XH2"],
          nets={"1": "VBAT", "2": "GND"}, mpn="B2B-XH-A(LF)(SN)", mfr="JST")
    s.note("TP4056 USB-C module with protection (HW-373), off-board where the USB-C is reachable:\n"
           "its B+/B- to this lead (1 A charge; XH is rated 3 A). OUT+/OUT- unused.\n"
           "No power path: charge with the box switched OFF. Check its CC resistors with a C-to-C cable.",
           at=(137.16, 50.8), size=1.27)

    # ===== 3. power toggle → boost EN ==============================================================================
    s.note("3  POWER TOGGLE → BOOST EN (closed = ON)", at=(256.54, 20.32), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J22", "PWR toggle", at=(279.4, 38.1), fp=LAB["XH2"],
          nets={"1": "PWR_SW_J", "2": "GND"}, mpn="B2B-XH-A", mfr="JST")
    R(s, "R9", "1k", (304.8, 38.1), "PWR_SW_J", "PWR_G")
    R(s, "R8", "100k", (304.8, 55.88), "VBAT", "PWR_G")
    C(s, "C18", "100n X7R", (304.8, 73.66), "PWR_G", "GND", mpn="CL21B104KBCNNNC")
    s.add("Transistor_FET:2N7002", "Q2", "2N7002", fp=LAB["SOT23"], at=(335.28, 55.88),
          nets={"1": "PWR_G", "2": "GND", "3": "PWR_EN"}, mpn="2N7002,215", mfr="Nexperia", ds="")
    s.note("Toggle closed: PWR_G = 0 → Q2 off → the module's own 100 k pull-up holds EN high → boost ON.\n"
           "Toggle open (or a broken lead): R8 → Q2 on → EN low → boost OFF (true shutdown, output disconnected).\n"
           "~40 µA either way. R9/C18: filter + ESD for the panel lead.",
           at=(256.54, 86.36), size=1.27)

    # ===== 4. boost module =========================================================================================
    s.note("4  5 V BOOST MODULE (Pololu U3V70F5)", at=(15.24, 119.38), size=2.0)
    module(s, "U2", "U3V70F5", (55.88, 147.32),
           {"VIN": "VBAT", "GND": "GND", "ENABLE": "PWR_EN", "VOUT": "5V_BOOST"})
    s.note("~2.9 A out at 3.0 V in (Pololu graph), 5.0 V ±4 %, reverse-voltage protected, UVLO 2.4/2.8 V, Iq < 1 mA.\n"
           "ENABLE: 100 k pull-up to VIN on the module, < 0.4 V = true shutdown (load disconnected).\n"
           "High-current loop: J20 → F1 → Q1 → U2 VIN, U2 GND → J20 GND: short and wide (1.5 mm), star point at J20.\n"
           "Keep U2 at the opposite end of the board from J30 (radio).",
           at=(15.24, 177.8), size=1.27)

    # ===== 5. ideal diode + 5V_PI bulk =============================================================================
    s.note("5  BACK-POWER IDEAL DIODE (Pololu #5388) & 5V_PI AT THE IDC HEADER", at=(137.16, 119.38), size=2.0)
    module(s, "U3", "IDEAL_DIODE", (172.72, 147.32), {"VIN": "5V_BOOST", "VOUT": "5V_PI", "GND": "GND"})
    CP(s, "C9", (231.14, 139.7), "5V_PI")
    C(s, "C10", "100n X7R", (231.14, 157.48), "5V_PI", "GND", mpn="CL21B104KBCNNNC")
    TVS(s, "D2", (231.14, 175.26), "5V_PI")
    s.note("< 3 mΩ: the Pi sees 5.0 V - ribbon (~0.03 V at 1 A) > 4.63 V throttle. A Schottky here would not do.\n"
           "LM74700 inside: needs ~3.9 V to start (runs down to 3.2 V) - fine here on the 5 V side, never on the cell.\n"
           "C9/C10/D2 at J1 pins 2/4.", at=(137.16, 187.96), size=1.27)

    # ===== 6. radio LDO ============================================================================================
    s.note("6  RADIO SUPPLY: AP2112K-3.3 (EN = the Pi's 3V3)", at=(15.24, 203.2), size=2.0)
    s.add("Regulator_Linear:AP2112K-3.3", "U4", "AP2112K-3.3", fp=LAB["SOT23_5"], at=(55.88, 223.52),
          nets={"1": "VBAT", "2": "GND", "3": "3V3_PI", "4": None, "5": "3V3_RADIO"},
          mpn="AP2112K-3.3TRG1", mfr="Diodes Inc.", ds=DS["AP2112"])
    C(s, "C11", "10u X5R", (106.68, 215.9), "VBAT", "GND", mpn="CL21A106KAYNNNE")
    C(s, "C12", "1u X7R", (106.68, 231.14), "3V3_RADIO", "GND", mpn="CL21B105KBFNNNE")
    s.note("~0.1 V dropout at 150 mA (600 mA part). EN from 3V3_PI: the radio is off whenever the Pi is off\n"
           "(else the SP4 in RX drains ~26 mA from the cell with the box 'off'). The breakout adds 110 uF at the module.",
           at=(15.24, 241.3), size=1.27)

    # ===== 7. fuel gauge module ====================================================================================
    s.note("7  FUEL GAUGE (Adafruit MAX17048 #5580, I2C 0x36)", at=(137.16, 203.2), size=2.0)
    module(s, "U6", "MAX17048", (172.72, 231.14), MODULES["MAX17048"]["nets"])
    s.note(MODULES["MAX17048"]["note"], at=(137.16, 254.0), size=1.27)

    # ===== 8. test points & flags ==================================================================================
    s.note("8  TEST POINTS", at=(256.54, 203.2), size=2.0)
    for ref, net, x in (("TP1", "VBAT", 261.62), ("TP2", "5V_PI", 281.94), ("TP3", "GND", 302.26)):
        s.add("Connector:TestPoint", ref, net, fp=LAB["TP"], at=(x, 215.9), nets={"1": net},
              mpn="wire loop (or Keystone 5000/5001)")
    # nets driven only through passive pins (connector, fuse, FET, module headers)
    for i, net in enumerate(("GND", "VBAT", "5V_BOOST", "5V_PI", "PWR_EN")):
        s.pwr_flag(net, at=(261.62 + i * 15.24, 238.76))
    if schgen.STANDALONE:
        s.pwr_flag("3V3_PI", at=(261.62, 259.08))
    return s
