"""Team C carrier, sheet power: cell, reverse protection, charger, power switch, 5.1 V boost, back-power ideal diode,
radio LDO (+ buck-boost option, DNP), fuel gauge, test points. DRAFT – for ET review.

Pinouts checked against the datasheets (19-Oct):
  MCP73831  DS20001984G Table 3-1 p.11 (SOT-23-5: 1 STAT, 2 VSS, 3 VBAT, 4 VDD, 5 PROG); STAT states Table 5-1;
            IREG = 1000 V / RPROG §5.
  TPS61022  SLVSDX7D Table 5-1 p.3 (RWU: 1 GND, 2 SW, 3 VOUT, 4 FB, 5 EN, 6 MODE, 7 VIN; the RWU0007A land pattern
            has no separate exposed pad); VREF 0.600 V (PWM) / 0.606 V (PFM) §6.5 p.5; Fig 8-1 p.13; §8.2.2 p.14-16.
  TLV755P   Table 4-1 p.3 (DBV: 1 IN, 2 GND, 3 EN, 4 NC, 5 OUT); CIN >= 1 uF, COUT 1-200 uF §6.3 p.4.
  TPS63001  SLVS520C Pin Functions p.3 (DRC: 1 VOUT, 2 L2, 3 PGND, 4 L1, 5 VIN, 6 EN, 7 PS/SYNC, 8 VINA, 9 GND,
            10 FB, pad = PGND); Table 1 p.10 (2.2 uH, 10 uF in, 2 x 10 uF out, 100 ohm + 0.1 uF on VINA).
  MAX17048  pin table p.6 (TDFN: 1 CTG, 2 CELL, 3 VDD, 4 GND, 5 ALRT, 6 QSTRT, 7 SCL, 8 SDA, EP = GND).
  AO3401A (AOS p.1) / 2N7002  SOT-23: 1 G, 2 S, 3 D.   SMF5V0A: symbol pin 1 = cathode bar (Vishay 85881 p.1).
  Ideal diode: Raspberry Pi 3B reduced schematic rev 1.2, "POWER IN": Q3 DMG2305UX (D = input, S = 5V),
            U14 BCM857BS (pins 1/2/6 diode-connected at the input, 4/5/3 at the output), R2 10K, R3 47K.
"""
import schgen
from schgen import Sheet
from nets import GLOBAL_NETS, DS

R0805 = "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"
C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
CP63 = "Capacitor_SMD:CP_Elec_6.3x5.4"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
TVS_FP = "Diode_SMD:D_SOD-123F"
TP_FP = "TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm"

# Yageo RC0805FR-07 (1 %, 0805, 150 V) and Murata MLCC part numbers; any equivalent is fine
RES = {"10k": "RC0805FR-0710KL", "5k1": "RC0805FR-075K1L", "2k21": "RC0805FR-072K21L", "1k": "RC0805FR-071KL",
       "100k": "RC0805FR-07100KL", "750k": "RC0805FR-07750KL", "47k": "RC0805FR-0747KL", "100R": "RC0805FR-07100RL",
       "0R": "RC0805JR-070RL"}
CAP = {"10u": ("10u 25V X5R", C0805, "GRM21BR61E106KA73L"),
       "22u": ("22u 25V X5R", C1206, "GRM31CR61E226KE15L"),
       "1u": ("1u 16V X7R", C0805, "GRM21BR71C105KA01L"),
       "100n": ("100n 50V X7R", C0805, "GRM21BR71H104KA01L"),
       "100p": ("100p 50V C0G", C0805, "GRM2165C1H101JA01D")}


def R(s, ref, val, at, n1, n2, dnp=False, shown=None):
    """0805 resistor, horizontal: pin 1 left, pin 2 right."""
    return s.add("Device:R", ref, shown or (val if val.endswith("R") else val + " 1%"), fp=R0805, at=at, rot=90,
                 nets={"1": n1, "2": n2}, mpn=RES[val], mfr="Yageo", dnp=dnp)


def C(s, ref, kind, at, n1, n2, dnp=False):
    """MLCC, horizontal: pin 1 left, pin 2 right."""
    val, fp, mpn = CAP[kind]
    return s.add("Device:C", ref, val, fp=fp, at=at, rot=90, nets={"1": n1, "2": n2}, mpn=mpn, mfr="Murata", dnp=dnp)


def CP(s, ref, at, plus):
    """100 uF 16 V aluminium electrolytic (Panasonic FK case D, 6.3 x 5.8 mm), + left, - to GND."""
    return s.add("Device:C_Polarized", ref, "100u 16V", fp=CP63, at=at, rot=90, nets={"1": plus, "2": "GND"},
                 mpn="EEE-FK1C101P", mfr="Panasonic")


def TVS(s, ref, at, net):
    """SMF5.0A: cathode (pin 1) on the rail, anode to GND."""
    return s.add("Diode:SMF5V0A", ref, "SMF5.0A", fp=TVS_FP, at=at, nets={"1": net, "2": "GND"},
                 mpn="SMF5V0A-E3-08", mfr="Vishay", ds="")


def pfet(s, ref, at, rot, d, src, g):
    """AO3401A P-FET. rot 90: D left, S right, G below; rot 270: S left, D right, G above."""
    return s.add("Transistor_FET:AO3401A", ref, "AO3401A", fp=SOT23, at=at, rot=rot,
                 nets={"1": g, "2": src, "3": d}, mpn="AO3401A", mfr="Alpha & Omega", ds="")


def build():
    s = Sheet("power", "Power: cell, charger, boost, ideal diode, radio LDO, fuel gauge (DRAFT – for ET review)",
              global_nets=GLOBAL_NETS)

    s.note("POWER – one protected 18650 → 5.1 V for the Pi 3 A+ and 3.3 V for the radio (DRAFT – for ET review)",
           at=(15.24, 12.7), size=2.5)

    # ===== 1. battery & reverse protection ========================================================================
    s.note("1  BATTERY & REVERSE PROTECTION", at=(15.24, 20.32), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J20", "BATT 18650", at=(43.18, 38.1),
          fp="Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical", nets={"1": "BAT_RAW", "2": "GND"},
          mpn="B2P-VH", mfr="JST")
    s.add("Connector_Generic:Conn_01x02", "J21", "BATT 2 (DNP)", at=(43.18, 58.42),
          fp="Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical", nets={"1": "BAT_RAW", "2": "GND"},
          mpn="B2P-VH", mfr="JST", dnp=True)
    pfet(s, "Q1", (80.01, 38.1), 90, d="BAT_RAW", src="VBAT", g="Q1_G")
    R(s, "R1", "10k", (80.01, 63.5), "Q1_G", "GND")
    TVS(s, "D3", (80.01, 81.28), "VBAT")
    s.note("Cells: protected 18650 (PCM inside) in an MPD BH-18650-PC\n"
           "holder on the box floor (off-board), lead to J20 (JST-VH, 10 A).\n"
           "J21 = second cell in parallel (DNP; only matched cells).\n"
           "Q1: the body diode conducts for a correct cell, then VGS = -VBAT\n"
           "turns it on; a reversed cell is blocked. D3: ESD/hot-plug clamp.\n"
           "Do not plug USB with a reversed cell (the charger, current-limited,\n"
           "would bias Q1 partly on).",
           at=(15.24, 91.44), size=1.27)

    # ===== 2. charger & USB-C =====================================================================================
    s.note("2  CHARGER & USB-C (charge-only, 452 mA; charges with the switch OFF)", at=(110.49, 20.32), size=2.0)
    s.add("Connector:USB_C_Receptacle_PowerOnly_6P", "J2", "USB-C charge", at=(125.73, 53.34),
          fp="Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x-0190_6P_TopMnt_Horizontal",
          nets={"A5": "CC1", "B5": "CC2", "A9": "VBUS_USB", "B9": "VBUS_USB", "A12": "GND", "B12": "GND",
                "SH": "GND"}, mpn="USB4125-GF-A-0190", mfr="GCT", ds="")
    TVS(s, "D1", (175.26, 35.56), "VBUS_USB")
    C(s, "C1", "10u", (220.98, 35.56), "VBUS_USB", "GND")
    R(s, "R2", "5k1", (175.26, 58.42), "CC1", "GND")
    R(s, "R3", "5k1", (175.26, 76.2), "CC2", "GND")
    s.add("Power_Protection:SP0504BAHT", "U12", "SP0504BAHTG", fp="Package_TO_SOT_SMD:SOT-23-5", at=(220.98, 76.2),
          rot=90, nets={"1": "CC1", "3": "CC2", "4": "PWR_SW_J", "5": None, "2": "GND"},
          mpn="SP0504BAHTG", mfr="Littelfuse", ds="")
    s.add("Battery_Management:MCP73831-2-OT", "U1", "MCP73831-2", fp="Package_TO_SOT_SMD:SOT-23-5", at=(266.7, 58.42),
          nets={"1": "CHG_STAT_RAW", "2": "GND", "3": "VBAT", "4": "VBUS_USB", "5": "PROG"},
          mpn="MCP73831T-2ACI/OT", mfr="Microchip", ds=DS["MCP73831"])
    C(s, "C2", "10u", (299.72, 35.56), "VBAT", "GND")
    R(s, "R4", "2k21", (231.14, 53.34), "PROG", "GND")
    R(s, "R5", "1k", (148.59, 93.98), "VBUS_USB", "CHG_LED_A")
    s.add("Device:LED", "D4", "red CHG", fp="LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder", at=(196.85, 93.98),
          rot=180, nets={"1": "CHG_STAT_RAW", "2": "CHG_LED_A"}, mpn="150080RS75000", mfr="Würth Elektronik")
    s.add("Transistor_FET:2N7002", "Q3", "2N7002", fp=SOT23, at=(256.54, 93.98),
          nets={"1": "CHG_STAT_RAW", "2": "GND", "3": "CHG_STAT"}, mpn="2N7002,215", mfr="Nexperia", ds="")
    R(s, "R6", "100k", (299.72, 76.2), "CHG_STAT_RAW", "GND")
    R(s, "R7", "10k", (299.72, 93.98), "CHG_STAT", "3V3_PI")
    s.note("CC1/CC2 5.1 k = sink (default USB 5 V). RPROG 2.21 k → 452 mA\n"
           "(1000 V / RPROG). VC of the SMF5.0A (9.2 V) > MCP73831 VDD abs. max\n"
           "7 V: ESD only, not a guard against a faulty charger. No power path:\n"
           "the charger feeds VBAT, upstream of the power switch.",
           at=(110.49, 104.14), size=1.27)
    s.note("STAT pushes to VDD (5 V): never straight to a GPIO.\n"
           "Charging: STAT low → D4 on, Q3 off → CHG_STAT = 1.\n"
           "Complete: STAT high → Q3 on → CHG_STAT = 0.  No USB: STAT Hi-Z,\n"
           "R6 holds Q3 off → CHG_STAT = 1. (USB with no cell / shutdown: Hi-Z,\n"
           "R5-D4-R6 bias Q3 on → reads 0 and D4 glows faintly.)",
           at=(218.44, 104.14), size=1.27)

    # ===== 3. power switch ========================================================================================
    s.note("3  POWER SWITCH (P-FET, panel toggle on J22)", at=(325.12, 20.32), size=2.0)
    pfet(s, "Q2", (365.76, 40.64), 270, d="VBAT_SW", src="VBAT", g="PWR_G")
    R(s, "R8", "100k", (345.44, 60.96), "PWR_G", "VBAT")
    R(s, "R9", "1k", (345.44, 78.74), "PWR_G", "PWR_SW_J")
    s.add("Connector_Generic:Conn_01x02", "J22", "PWR toggle", at=(393.7, 78.74),
          fp="Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", nets={"1": "PWR_SW_J", "2": "GND"},
          mpn="B2B-XH-A", mfr="JST")
    s.note("Toggle (E-Switch 100SP1T1B1M1QEH, off-board), closed = ON:\n"
           "pulls PWR_G low through R9 → Q2 on. Open: R8 holds Q2 off\n"
           "and its body diode blocks VBAT → VBAT_SW. The toggle carries\n"
           "~40 µA only. ESD on PWR_SW_J: U12 pin 4.",
           at=(325.12, 91.44), size=1.27)

    # ===== 4. boost ===============================================================================================
    s.note("4  5.1 V BOOST (TPS61022, 1 MHz, auto-PFM)", at=(15.24, 119.38), size=2.0)
    s.add("Converter_DCDC:TPS61022", "U2", "TPS61022", fp="Package_DFN_QFN:Texas_RWU0007A_VQFN-7_2x2mm_P0.5mm",
          at=(96.52, 160.02),
          nets={"1": "GND", "2": "SW_NODE", "3": "5V_BOOST", "4": "FB", "5": "VBAT_SW", "6": "GND", "7": "VBAT_SW"},
          mpn="TPS61022RWUR", mfr="Texas Instruments", ds=DS["TPS61022"])
    s.add("Device:L", "L1", "1u Isat 11.5A", fp="Inductor_SMD:L_Wuerth_HCI-5040", at=(40.64, 132.08), rot=90,
          nets={"1": "VBAT_SW", "2": "SW_NODE"}, mpn="744316100", mfr="Würth Elektronik")
    C(s, "C4", "22u", (40.64, 149.86), "VBAT_SW", "GND")
    CP(s, "C5", (40.64, 167.64), "VBAT_SW")
    R(s, "R10", "750k", (149.86, 132.08), "5V_BOOST", "FB")
    C(s, "C3", "100p", (149.86, 149.86), "5V_BOOST", "FB")
    R(s, "R11", "100k", (149.86, 167.64), "FB", "GND")
    C(s, "C6", "22u", (195.58, 132.08), "5V_BOOST", "GND")
    C(s, "C7", "22u", (195.58, 149.86), "5V_BOOST", "GND")
    C(s, "C8", "22u", (195.58, 167.64), "5V_BOOST", "GND")
    s.note("VOUT = 0.600 V x (1 + 750k/100k) = 5.10 V (PFM 5.15 V; OVP 5.5 V min).\n"
           "L1 744316100 is in TI's Table 8-2; peak ~5.7 A at 3.0 V in / 2.5 A out.\n"
           "C3 100 pF: feed-forward zero 1/(2π·750k·100p) = 2.1 kHz (§8.2.2.4, COUT_eff\n"
           "> 40 µF). EN = VBAT_SW: on with the switch. MODE = GND: auto PFM (light-load\n"
           "efficiency, no reverse inductor current). C5 bulk: the cell sits on a lead\n"
           "(§8.2.2.5). Tight SW loop, VIN/VOUT caps at the pins; far corner from the SP4.",
           at=(15.24, 177.8), size=1.27)

    # ===== 5. back-power ideal diode & header bulk ==================================================================
    s.note("5  BACK-POWER IDEAL DIODE (Pi 3B circuit) & 5V_PI AT THE HEADER", at=(220.98, 119.38), size=2.0)
    pfet(s, "Q4", (264.16, 137.16), 90, d="5V_BOOST", src="5V_PI", g="ZVD_G")
    s.add("Transistor_BJT:BC857BS", "U3", "BC857BS", fp="Package_TO_SOT_SMD:SOT-363_SC-70-6", at=(243.84, 160.02),
          rot=180, unit=1, nets={"1": "5V_BOOST", "2": "ZVD_B", "6": "ZVD_B"}, mpn="BC857BS,115", mfr="Nexperia",
          ds="")
    s.add("Transistor_BJT:BC857BS", "U3", "BC857BS", fp="Package_TO_SOT_SMD:SOT-363_SC-70-6", at=(289.56, 160.02),
          rot=180, unit=2, nets={"4": "5V_PI", "5": "ZVD_B", "3": "ZVD_G"}, mpn="BC857BS,115", mfr="Nexperia",
          ds="")
    R(s, "R12", "10k", (330.2, 132.08), "ZVD_B", "GND")
    R(s, "R13", "47k", (330.2, 149.86), "ZVD_G", "GND")
    CP(s, "C9", (330.2, 167.64), "5V_PI")
    C(s, "C10", "100n", (378.46, 132.08), "5V_PI", "GND")
    TVS(s, "D2", (378.46, 149.86), "5V_PI")
    s.note("U3A, diode-connected with its emitter on 5V_BOOST, sets ~0.45 mA through R12; U3B mirrors it\n"
           "against 5V_PI. Forward (5V_BOOST above 5V_PI by more than ~40 mV): U3B starves, R13 pulls ZVD_G\n"
           "low → Q4 on (≈ 0.15 V at 2.5 A). Back-power (micro-USB on the Pi, or the boost off): 5V_PI >\n"
           "5V_BOOST, U3B saturates, ZVD_G ≈ 5V_PI → Q4 off, and its body diode (D → S) is reverse biased.\n"
           "Pi 3B values: 10 k on the mirror base (R12), 47 k on the gate (R13). The Pi 3 A+ has no such\n"
           "circuit and header pins 2/4 bypass its polyfuse. C9/C10/D2 at header pins 2/4.\n"
           "Q4: AO3401A (or DMG2305UX as in the Pi). U3: one BC857BS (units A and B).",
           at=(220.98, 177.8), size=1.27)

    # ===== 6. radio supply ========================================================================================
    s.note("6  RADIO SUPPLY: TLV75533 LDO (fitted) | TPS63001 buck-boost option (all DNP)", at=(15.24, 203.2),
           size=2.0)
    s.add("Regulator_Linear:TLV75533PDBV", "U4", "TLV75533", fp="Package_TO_SOT_SMD:SOT-23-5", at=(55.88, 223.52),
          nets={"1": "VBAT_SW", "2": "GND", "3": "VBAT_SW", "4": None, "5": "LDO_OUT"},
          mpn="TLV75533PDBVR", mfr="Texas Instruments", ds=DS["TLV755P"])
    C(s, "C11", "10u", (106.68, 215.9), "VBAT_SW", "GND")
    C(s, "C12", "1u", (106.68, 231.14), "LDO_OUT", "GND")
    R(s, "R14", "0R", (106.68, 246.38), "LDO_OUT", "3V3_RADIO", shown="0R (fit)")
    R(s, "R16", "0R", (106.68, 261.62), "BB_OUT", "3V3_RADIO", dnp=True, shown="0R (DNP)")
    s.add("Regulator_Switching:TPS63001", "U5", "TPS63001", fp="Package_SON:Texas_DRC0010J_ThermalVias",
          at=(180.34, 238.76),
          nets={"1": "BB_OUT", "2": "BB_SW2", "3": "GND", "4": "BB_SW1", "5": "VBAT_SW", "6": "VBAT_SW",
                "7": "VBAT_SW", "8": "BB_VINA", "9": "GND", "10": "BB_OUT", "11": "GND"},
          mpn="TPS63001DRCR", mfr="Texas Instruments", ds=DS["TPS63001"], dnp=True)
    s.add("Device:L", "L2", "2u2", fp="Inductor_SMD:L_Coilcraft_LPS4018", at=(231.14, 215.9), rot=90,
          nets={"1": "BB_SW1", "2": "BB_SW2"}, mpn="LPS4018-222MRB", mfr="Coilcraft", dnp=True)
    C(s, "C13", "10u", (231.14, 231.14), "VBAT_SW", "GND", dnp=True)
    C(s, "C14", "10u", (231.14, 246.38), "BB_OUT", "GND", dnp=True)
    C(s, "C15", "10u", (231.14, 261.62), "BB_OUT", "GND", dnp=True)
    R(s, "R15", "100R", (55.88, 251.46), "VBAT_SW", "BB_VINA", dnp=True)
    C(s, "C16", "100n", (55.88, 266.7), "BB_VINA", "GND", dnp=True)
    s.note("LDO: ≈ 65 mV dropout at 150 mA; COUT 1–200 µF (C12 + the 110 µF at the SP4, radio sheet).\n"
           "Fit exactly ONE of R14 (LDO, default) / R16 (buck-boost). Buck-boost only if T0 shows > 2 dB less\n"
           "output at a 3.0 V cell: FB = VOUT (fixed 3.3 V), PS/SYNC high = forced PWM (low ripple at the radio).",
           at=(15.24, 274.32), size=1.27)

    # ===== 7. fuel gauge ==========================================================================================
    s.note("7  FUEL GAUGE (MAX17048, I2C 0x36)", at=(266.7, 203.2), size=2.0)
    s.add("teamc:MAX17048", "U6", "MAX17048", fp="teamc:MAX17048_TDFN-8-1EP_2x2mm", at=(299.72, 223.52),
          nets={"1": "GND", "2": "VBAT", "3": "VBAT", "4": "GND", "5": "FG_ALRT", "6": "GND", "7": "I2C_SCL",
                "8": "I2C_SDA", "9": "GND"}, mpn="MAX17048G+T10", mfr="Analog Devices (Maxim)", ds=DS["MAX17048"])
    C(s, "C17", "100n", (281.94, 243.84), "VBAT", "GND")
    R(s, "R17", "10k", (325.12, 243.84), "FG_ALRT", "3V3_PI")
    s.note("VDD/CELL and GND: Kelvin traces to J20, not along the boost input path.\n"
           "No I2C pull-ups here (the Pi has 1.8 k). Software: never set MODE.EnSleep.",
           at=(266.7, 251.46), size=1.27)

    # ===== 8. test points & power flags ===========================================================================
    s.note("8  TEST POINTS", at=(358.14, 203.2), size=2.0)
    for ref, net, x in (("TP1", "VBAT", 363.22), ("TP2", "5V_PI", 383.54), ("TP3", "GND", 403.86)):
        s.add("Connector:TestPoint", ref, net, fp=TP_FP, at=(x, 215.9), nets={"1": net},
              mpn="wire loop (or Keystone 5000/5001)")
    # Nets driven here only through passive pins (connector, FET, 0R/100R) but feeding power_in pins
    s.pwr_flag("GND", at=(363.22, 233.68))
    s.pwr_flag("VBAT_SW", at=(383.54, 233.68))
    s.pwr_flag("VBUS_USB", at=(152.4, 68.58))
    s.pwr_flag("BB_VINA", at=(81.28, 248.92))
    s.pwr_flag("3V3_RADIO", at=(139.7, 241.3))
    if schgen.STANDALONE:
        # stand-alone ERC only: the Pi drives I2C_SCL through the header on the pi_header sheet
        s.pwr_flag("I2C_SCL", at=(403.86, 233.68))
    return s
