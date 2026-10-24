"""Team C carrier rev C ("simple"), sheet ui: panel button, toggles and LEDs on JST-XH leads. DRAFT - checkpoint 2.

Software contract: proto/port/linux/ui.c — inputs use the Pi's internal pull-ups (ui.c requests them), active low:
GPIO 17 GO/STOP button, GPIO 27 role (low = TX), GPIO 23 low = NM, else GPIO 16 low = MRM, else SRI. LEDs active
high on GPIO 5 (activity) and GPIO 6 (status). Per input: a P4KE10A through-hole TVS at the lead connector (added
after checkpoint 3, D12-D15) and 1 kΩ in series (the 100 nF of checkpoint 2 dropped at layout); per LED: 330 Ω on the
board, the 5 mm LED itself in a panel clip on the lead (the LED lines have no TVS: the LEDs sit in plastic clips).
"""

import schgen
from schgen import Sheet
from nets import GLOBAL_NETS, FP, MPN

INPUTS = [   # (line, series R, TVS at the lead, text)
    ("BTN_TXRX", "R54", "D12", "GPIO 17, GO/STOP, low = pressed"),
    ("SW_ROLE", "R55", "D13", "GPIO 27, role, low = TX"),
    ("SW_MODE_NM", "R56", "D14", "GPIO 23, low = NM"),
    ("SW_MODE_MRM", "R57", "D15", "GPIO 16, low = MRM (neither = SRI)"),
]
ROW0, ROWSTEP = 99.06, 20.32
X_SER, X_CAP = 160.02, 226.06


def build():
    s = Sheet("ui", "UI: panel button, toggles, LEDs (rev C, DRAFT)", global_nets=GLOBAL_NETS)

    s.note("UI – panel controls and LEDs on JST-XH leads", at=(25.4, 20.32), size=2.5)
    s.note("Every panel part sits on the box wall and plugs into the board with a JST-XH lead (glue the housings and\n"
           "tie the leads down for the drop test). Inputs: the switch pulls the GPIO to GND; the Pi's own pull-up\n"
           "(turned on by ui.c) holds it high otherwise. A TVS at each lead + 1 kΩ in series protect the GPIO from a zap\n"
           "and from a GPIO driven by old firmware at boot (GPIO 16). LEDs light when the GPIO is high.\n"
           "Panel holes: Ø7.5 mm for the PS1024 button, Ø6.5 mm for the 100-series toggles, Ø8 mm for the LED clips.",
           at=(25.4, 27.94))

    s.note("CONNECTORS (panel parts off-board)", at=(25.4, 81.28), size=2.0)
    s.add("Connector_Generic:Conn_01x02", "J10", "GO/STOP button", at=(78.74, ROW0), fp=FP["XH2"],
          nets={"1": "BTN_TXRX_J", "2": "GND"}, mpn="B2B-XH-A(LF)(SN)", mfr="JST",
          Panel="E-Switch PS1024ABLK momentary, Ø7.5 mm hole")
    s.add("Connector_Generic:Conn_01x02", "J11", "role toggle", at=(78.74, ROW0 + ROWSTEP), fp=FP["XH2"],
          nets={"1": "SW_ROLE_J", "2": "GND"}, mpn="B2B-XH-A(LF)(SN)", mfr="JST",
          Panel="E-Switch 100SP1T1B1M1QEH, closed = TX, Ø6.5 mm hole")
    s.add("Connector_Generic:Conn_01x03", "J12", "mode toggle", at=(78.74, ROW0 + ROWSTEP * 2.5), fp=FP["XH3"],
          nets={"1": "SW_MODE_NM_J", "2": "GND", "3": "SW_MODE_MRM_J"}, mpn="B3B-XH-A(LF)(SN)", mfr="JST",
          Panel="E-Switch 100SP3T1B1M1QEH ON-OFF-ON, common = pin 2, Ø6.5 mm hole")
    s.note("J10: GO/STOP button (also the bench button: bridge its two pins).\n"
           "J11: role toggle, closed = TX, open = RX (may stay unfitted until Atenea Q8).\n"
           "J12: mode toggle ON-OFF-ON: 1 NM, 2 common (GND), 3 MRM; centre = SRI.",
           at=(25.4, 172.72), size=1.27)

    s.note("TVS AT THE LEAD + SERIES 1 kΩ", at=(X_SER - 55.88, 81.28), size=2.0)
    for i, (line, rser, tvs, gpio) in enumerate(INPUTS):
        y = ROW0 + i * ROWSTEP
        mpn, mfr = MPN["TVS"]
        s.add("Device:D_Zener", tvs, "P4KE10A TVS", at=(X_SER - 40.64, y), rot=0, fp=FP["TVS"],
              nets={"1": line + "_J", "2": "GND"}, mpn=mpn, mfr=mfr)
        mpn, mfr = MPN["1k"]
        s.add("Device:R", rser, "1k", at=(X_SER, y), rot=90, fp=FP["R"], nets={"1": line + "_J", "2": line},
              mpn=mpn, mfr=mfr)
        s.note(gpio, at=(X_CAP - 12.7, y - 0.64), size=1.27)
    s.note("D12-D15 (Santiago, checkpoint 3): one TVS per panel line, right at its lead connector, cathode (band) to the\n"
           "line, anode to GND. A zap on a metal lever goes into the TVS (it clamps at ~14.5 V), and the 1 kΩ then limits\n"
           "what reaches the Pi's own protection diodes to ~10 mA for a few nanoseconds. P4KE10A: stand-off 8.55 V, leakage\n"
           "at most 10 µA (at 8.55 V; far less at 3.3 V), so the Pi's ~50 kΩ pull-up still reads high. Stands upright.",
           at=(X_SER - 55.88, 167.64), size=1.27)
    s.note("Layout change at checkpoint 3: the 100 nF capacitors at the GPIOs (C50-C53 of checkpoint 2) are gone.\n"
           "On one copper layer each needed a ground return in a crowded place (and two of them a wire link). The\n"
           "switches are slow and the software debounces them (30 ms, ui.c); the 1 kΩ still limits the current of a\n"
           "zap or of a GPIO driven at boot to a few mA into the Pi's own protection diodes.",
           at=(X_SER - 55.88, 177.8), size=1.27)

    s.note("LEDs (5 mm, in panel clips; ≈ 4 mA from 3.3 V)", at=(X_SER - 12.7, 190.5), size=2.0)
    for i, (net, r) in enumerate((("LED_ACT", "R60"), ("LED_STATUS", "R61"))):
        mpn, mfr = MPN["330"]
        s.add("Device:R", r, "330", at=(X_SER, 205.74 + i * 17.78), rot=90, fp=FP["R"],
              nets={"1": net, "2": net + "_A"}, mpn=mpn, mfr=mfr)
    s.add("Connector_Generic:Conn_01x03", "J14", "LED lead", at=(X_CAP, 213.36), fp=FP["XH3"],
          nets={"1": "LED_ACT_A", "2": "LED_STATUS_A", "3": "GND"}, mpn="B3B-XH-A(LF)(SN)", mfr="JST",
          Panel="1 = green LED anode (activity), 2 = red LED anode (status), 3 = both cathodes")
    s.note("J14 lead: pin 1 to the green LED's long leg (activity, GPIO 5), pin 2 to the red LED's long leg\n"
           "(status, GPIO 6), pin 3 to both short legs. (3.3 V - ~2.0 V) / 330 Ω ≈ 4 mA, far under the Pi's\n"
           "16 mA per pin. Red/green/yellow only (blue/white need more voltage than 3.3 V leaves).",
           at=(X_SER - 12.7, 243.84), size=1.27)

    if schgen.STANDALONE:
        s.pwr_flag("GND", at=(101.6, 254.0))
    return s
