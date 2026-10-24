"""Team C carrier rev C ("simple"), sheet power: cell holder, fuse, crowbar diode, charger lead, power toggle, 5 V
boost module, ideal-diode module, radio regulator, fuel-gauge module, test points. DRAFT - checkpoint 2.

Decisions (Santiago, checkpoint 1, 23-Oct-26): cell holder on the carrier; keep the Pololu #5388 ideal diode; the
power toggle drives the boost's ENABLE (sleep, fail-on); 1N5822 across the cell + 4 A fuse, easy to replace (5x20 mm
fuse in clips, a spare in the BoM). Modules and their pins: modules.py (from the makers' CAD, as rev B).
Pinouts: MCP1700 TO-92 (Microchip DS20001826, package figure): 1 GND, 2 VIN, 3 VOUT, flat side facing you, legs down.
1N5822 (DO-201AD): band = cathode = pin 1.
"""
import schgen
from schgen import Sheet
from nets import GLOBAL_NETS, DS, FP, MPN
from modules import MODULES


def R(s, ref, val, at, n1, n2):
    mpn, mfr = MPN[val]
    return s.add("Device:R", ref, val, fp=FP["R"], at=at, rot=90, nets={"1": n1, "2": n2}, mpn=mpn, mfr=mfr)


def C(s, ref, val, at, n1, n2):
    mpn, mfr = MPN[val]
    return s.add("Device:C", ref, val + " X7R", fp=FP["C"], at=at, rot=90, nets={"1": n1, "2": n2}, mpn=mpn, mfr=mfr)


def CP(s, ref, at, plus):
    mpn, mfr = MPN["100u"]
    return s.add("Device:C_Polarized", ref, "100u 16V", fp=FP["CP"], at=at, rot=90, nets={"1": plus, "2": "GND"},
                 mpn=mpn, mfr=mfr)


def module(s, ref, key, at, nets_by_name, **kw):
    """A module as one Conn_01xNN symbol: pin n = the n-th pad in modules.py; nets given by pad name."""
    m = MODULES[key]
    nets = {}
    for i, p in enumerate(m["pins"], 1):
        if p["name"] not in nets_by_name:
            raise ValueError(f"{ref} ({key}): no net for pad {p['name']}")
        nets[str(i)] = nets_by_name[p["name"]]
    return s.add(f"Connector_Generic:Conn_01x{len(m['pins']):02d}", ref, m["value"], fp="teamc:RevC_" + m["footprint"],
                 at=at, nets=nets, mpn=m["mpn"], mfr=m["mfr"], ds=m["url"], **kw)


def build():
    s = Sheet("power", "Power: cell, fuse, 5 V boost, ideal diode, radio 3.3 V, fuel gauge (rev C, DRAFT)",
              global_nets=GLOBAL_NETS)
    s.note("POWER – one protected 18650 cell → 5 V for the Pi (Pololu module) and 3.3 V for the radio (MCP1700)",
           at=(15.24, 12.7), size=2.5)

    # ===== 1. cell, fuse, crowbar =================================================================================
    s.note("1  CELL, FUSE AND REVERSED-CELL PROTECTION", at=(15.24, 20.32), size=2.0)
    s.add("Device:Battery_Cell", "BT1", "18650 protected", fp=FP["CELL"], at=(33.02, 50.8),
          nets={"1": "BAT_IN", "2": "GND"}, mpn="BH-18650-PC (holder; the protected cell is in the BoM off-board)",
          mfr="MPD", ds=DS["BH18650"])
    s.add("Device:Fuse", "F1", "4 A fast 5x20", fp=FP["FUSE"], at=(60.96, 38.1), rot=90,
          nets={"1": "BAT_IN", "2": "VBAT"}, mpn="2 x Keystone 3517 clips + 5x20 mm 4 A fast fuse (Littelfuse 0217004.HXP)",
          mfr="Keystone / Littelfuse", ds=DS["KEYS3517"])
    s.add("Device:D_Schottky", "D1", "1N5822", fp=FP["D201"], at=(86.36, 50.8), rot=270,
          nets={"1": "VBAT", "2": "GND"}, mpn="1N5822", mfr="STMicroelectronics", ds=DS["1N5822"])
    CP(s, "C1", (111.76, 50.8), "VBAT")
    s.note("What it does, in plain words:\n"
           "BT1 - the cell sits in a holder soldered on this board (no battery lead). Use a PROTECTED 18650 (its own\n"
           "  protection circuit cuts at a short or a deep discharge). A cable tie through the two board slots next to\n"
           "  the holder keeps the cell in during the drop test.\n"
           "F1 - a 5x20 mm 4 A fast (F4A) glass fuse in two clips: it blows on a short, and it is pulled out and replaced by hand\n"
           "  (keep the spare from the BoM in the box). 4 A: the box draws <= 1.8 A at a nearly empty cell.\n"
           "D1 - normally does nothing (it points 'backwards'). If the cell is put in the holder the wrong way round,\n"
           "  D1 conducts and shorts it: F1 blows (or the cell's protection cuts) before any module sees -4 V.\n"
           "  Bench check: D1's leakage at 4.2 V adds to the standby drain (datasheet up to mA at 40 V and hot;\n"
           "  measure the cell current with the box off).\n"
           "C1 - 100 uF reservoir at the boost input (Pololu asks for >= 33 uF).",
           at=(15.24, 71.12), size=1.27)

    # ===== 2. charger lead =========================================================================================
    s.note("2  CHARGER LEAD (Adafruit Micro-Lipo USB-C #4410 at the box wall)", at=(160.02, 20.32), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J23", "charger BAT+/BAT-", at=(175.26, 38.1), fp=FP["XH2"],
          nets={"1": "VBAT", "2": "GND"}, mpn="B2B-XH-A(LF)(SN)", mfr="JST")
    s.note("The Adafruit #4410 charger (24-Oct; the TP4056 boards were out of stock) sits at the box wall where its\n"
           "USB-C port is reachable; its BAT and GND pads go to this 2-pin lead. Close its 500 mA solder jumper (default\n"
           "100 mA): a full 3500 mAh cell then takes ~7-8 h (overnight). Any USB-C cable or charger works.\n"
           "It has no cell protection of its own: the protected 18650 has it. Charge with the box switched OFF.\n"
           "J23 is behind F1: a reversed cell never reaches it.",
           at=(160.02, 50.8), size=1.27)

    # ===== 3. power toggle =========================================================================================
    s.note("3  POWER TOGGLE (tells the boost to sleep)", at=(287.02, 20.32), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J22", "PWR toggle", at=(302.26, 38.1), fp=FP["XH2"],
          nets={"1": "PWR_SW_J", "2": "GND"}, mpn="B2B-XH-A(LF)(SN)", mfr="JST",
          Panel="E-Switch 100SP1T1B1M1QEH, wired common + one throw; closed = OFF")
    R(s, "R9", "1k", (325.12, 38.1), "PWR_SW_J", "PWR_EN")
    C(s, "C18", "100n", (345.44, 50.8), "PWR_SW_J", "GND")
    mpn, mfr = MPN["TVS"]
    s.add("Device:D_Zener", "D16", "P4KE10A TVS", fp=FP["TVS"], at=(370.84, 38.1), rot=0,
          nets={"1": "PWR_SW_J", "2": "GND"}, mpn=mpn, mfr=mfr)
    s.note("Toggle CLOSED = ENABLE pulled to GND = boost asleep = box OFF (the battery current never goes through\n"
           "the switch). Toggle OPEN = the module's own 100 k pull-up wakes it = box ON. A lead that breaks in the drop\n"
           "test therefore leaves the box running. Mount the toggle so that 'down' (closed) is marked OFF.\n"
           "C18 + R9: 100 nF at the lead, then 1 k to ENABLE: a zap on the lever goes into C18, R9 limits what reaches\n"
           "the module (C18 sits at the connector since checkpoint 3: room on the board). D16: TVS at the lead (after\n"
           "checkpoint 3), P4KE10A, stand-off 8.55 V > the cell's 4.2 V; its leakage (<= 10 uA even at 8.55 V, far less at\n"
           "4.2 V) would drop at most 1 V across the 100 k pull-up, so ENABLE still reads high (box ON).\n"
           "With the toggle closed: EN = VBAT x 1k / 101k = 0.04 V (< 0.4 V needed). Off drain: ~40 uA in the pull-up.",
           at=(287.02, 63.5), size=1.27)

    # ===== 4. boost module =========================================================================================
    s.note("4  5 V BOOST MODULE (Pololu U3V70F5)", at=(15.24, 119.38), size=2.0)
    module(s, "U2", "U3V70F5", (55.88, 147.32),
           {"VIN": "VBAT", "GND": "GND", "ENABLE": "PWR_EN", "VOUT": "5V_BOOST"})
    s.note("This module turns the cell's 3.0-4.2 V into 5.0 V (+-4 %) for the Pi: about 3 A available at a 3.0 V cell,\n"
           "the Pi needs about 1 A at most. Input protected against reversal; below 2.4 V it stops (UVLO).\n"
           "ENABLE: 100 k pull-up to VIN on the module; < 0.4 V = true shutdown (its output is disconnected).\n"
           "Keep the cell -> F1 -> U2 -> GND loop short and wide (1.5-2 mm tracks); keep U2 away from the radio.",
           at=(15.24, 177.8), size=1.27)

    # ===== 5. ideal diode + 5V_PI ==================================================================================
    s.note("5  ONE-WAY VALVE FOR THE PI'S 5 V (Pololu ideal diode #5388)", at=(160.02, 119.38), size=2.0)
    module(s, "U3", "IDEAL_DIODE", (190.5, 147.32), {"VIN": "5V_BOOST", "VOUT": "5V_PI", "GND": "GND"})
    CP(s, "C9", (241.3, 139.7), "5V_PI")
    C(s, "C10", "100n", (241.3, 157.48), "5V_PI", "GND")
    s.note("U3 lets current flow from the boost to the Pi but never back (< 3 mOhm, so no voltage is lost). If someone\n"
           "plugs the Pi's micro-USB while the box is on, the USB supply cannot push current into the boost or the cell.\n"
           "It needs ~3.9 V to start, so it only works on the 5 V side - never on the cell.\n"
           "C9 (100 uF) + C10 (100 nF) sit at the box header's pins 2/4: the Pi's supply reservoir.\n"
           "Rule all the same: do not power the Pi from its micro-USB AND the box at once (two supplies share the Pi).",
           at=(160.02, 177.8), size=1.27)

    # ===== 6. radio regulator ======================================================================================
    s.note("6  RADIO 3.3 V: MCP1700-3302E/TO from the Pi's 5 V", at=(15.24, 203.2), size=2.0)
    s.add("Regulator_Linear:MCP1700x-330xxTO", "U4", "MCP1700-3302E/TO", fp=FP["TO92"], at=(55.88, 223.52),
          nets={"1": "GND", "2": "5V_PI", "3": "3V3_RADIO"}, mpn="MCP1700-3302E/TO", mfr="Microchip",
          ds=DS["MCP1700"])
    C(s, "C11", "1u", (91.44, 223.52), "5V_PI", "GND")
    C(s, "C12", "1u", (132.08, 223.52), "3V3_RADIO", "GND")
    s.note("A 3-legged regulator: 5 V in, always exactly 3.3 V out for the radio (max 250 mA; the radio takes <= 120 mA).\n"
           "Fed from 5V_PI, so the radio is only powered when the Pi is: it can never push current into a switched-off\n"
           "Pi through its pins. 0.2 W at full transmit: warm, not hot. Never feed the radio from the cell or the Pi's\n"
           "3.3 V pin (absolute max 3.6 V). C11/C12: 1 uF ceramics (datasheet: >= 1 uF at the output); the breakout\n"
           "adds 100 uF + 10 uF + 100 nF at the module. Bench: ripple on 3V3_RADIO during transmit (scope, TP4).",
           at=(15.24, 241.3), size=1.27)

    # ===== 7. fuel gauge module ====================================================================================
    s.note("7  BATTERY LEVEL (Adafruit MAX17048 #5580, I2C 0x36)", at=(160.02, 203.2), size=2.0)
    module(s, "U6", "MAX17048", (190.5, 231.14), MODULES["MAX17048"]["nets"])
    s.note(MODULES["MAX17048"]["note"], at=(160.02, 254.0), size=1.27)

    # ===== 8. test points & flags ==================================================================================
    s.note("8  TEST POINTS (clip a multimeter here)", at=(287.02, 203.2), size=2.0)
    for i, (ref, net, fp, mpn, mfr) in enumerate((
            ("TP1", "VBAT", FP["TP"], "5010 (red)", "Keystone"),
            ("TP2", "5V_PI", FP["LOOP"], "wire loop (bare tinned wire, ~3 mm high)", ""),
            ("TP4", "3V3_RADIO", FP["LOOP"], "wire loop (bare tinned wire, ~3 mm high)", ""),
            ("TP3", "GND", FP["LOOP"], "wire loop (bare tinned wire, ~3 mm high)", ""))):
        s.add("Connector:TestPoint", ref, net, fp=fp, at=(292.1 + i * 20.32, 215.9), nets={"1": net}, mpn=mpn, mfr=mfr)
    s.note("TP1 VBAT 3.0-4.2 V · TP2 5V_PI 4.8-5.2 V · TP4 3V3_RADIO 3.2-3.4 V · TP3 GND (black).\n"
           "Measure all of them BEFORE plugging in the ribbon (Pi) and the radio breakout. TP2/TP4 are low wire loops\n"
           "(~5 mm) under the breakout's place (a Keystone 5010 is too tall there); TP3 (GND) is a loop too, beside TP1.",
           at=(287.02, 228.6), size=1.27)
    # nets driven only through passive pins (holder, fuse, connectors, module headers)
    for i, net in enumerate(("GND", "BAT_IN", "VBAT", "5V_BOOST", "5V_PI", "PWR_EN")):
        s.pwr_flag(net, at=(292.1 + i * 15.24, 246.38))
    if schgen.STANDALONE:
        s.pwr_flag("3V3_PI", at=(292.1, 266.7))
    return s
