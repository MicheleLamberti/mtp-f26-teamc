"""Bill of materials per box for carrier rev C ("simple", UPC lab) -> hw/BOM_revC.csv

    python3 hw/scripts/build_bom_revc.py

Board parts come from the rev C netlist (hw/teamc-carrier-simple/build/teamc-carrier-simple.net), grouped by value,
footprint and MPN. Off-board parts (the Pi, the microSD, the radio and its breakout, the cell, the charger, the
ribbon, panel parts, mechanics, consumables) and the UPC lab PCB at the fixed EUR 15 come from OFF_BOARD.
Competition rules (cost section): everything goes in the BoM, owned or lab-stock items at market price; "purchased"
separates what the team buys from what it already has or the lab provides.
Columns: supplier link, stock as read on the supplier's product page with the date, footprint, 3D-model source.
Prices: EUR excl. VAT at the price break of the order for 2 boxes + 1 spare (qty 1, or qty 10 where noted), read on
23/24-Oct-26; "est." = not read on a shop page.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import find, find_all, parse  # noqa: E402

HW = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NET = os.path.join(HW, "teamc-carrier-simple", "build", "teamc-carrier-simple.net")
OUT = os.path.join(HW, "BOM_revC.csv")
DK = "https://www.digikey.es/en/products/result?keywords="
TME_PS = "https://www.tme.eu/en/details/"
STOCK_DATE = "24-Oct-26"

# MPN (as in the schematic, text before " (" / "+") -> (unit EUR excl. VAT, supplier, link, stock as read)
SUPPLY = {
    # modules
    "2891": (22.78, "DigiKey.es 2183-2891-ND", DK + "pololu%202891", "152 (24-Oct)"),
    "5388": (5.70, "DigiKey.es 2183-5388-ND", DK + "pololu%205388", "500 (24-Oct)"),
    "5580": (5.69, "Kiwi Electronics ADA-5580",
             "https://www.kiwi-electronics.com/en/adafruit-max17048-lipoly-liion-fuel-gauge-battery-monitor-11061",
             "41 (23-Oct)"),
    # power parts
    "MCP1700-3302E/TO": (0.44, "DigiKey.es MCP1700-3302E/TO-ND", DK + "MCP1700-3302E%2FTO", "11,755 (24-Oct)"),
    "BH-18650-PC": (2.94, "DigiKey.es BH-18650-PC-ND",
                    "https://www.digikey.es/en/products/detail/mpd-memory-protection-devices/BH-18650-PC/3029216",
                    "9,726 (23-Oct)"),
    "1N5822": (0.54, "DigiKey.es (STMicroelectronics)", DK + "1N5822",
               "price listed, stock not shown (TME: 221 on 23-Oct)"),
    "2 x Keystone 3517 clips": (2 * 0.42 + 0.53, "DigiKey.es: 2 x Keystone 3517 (EUR 0.42) + Littelfuse 0217004.HXP glass F4A "
                                "(EUR 0.53; ceramic 0216004.MXP EUR 1.85, 4,517 pcs)",
                                DK + "0217004.HXP", "fuse price listed; clips TME 2,170 (23-Oct)"),
    # passives (qty-10 price breaks where the order for 3 boxes reaches them)
    "K104K10X7RF5UH5": (0.155, "DigiKey.es (Vishay, 5 mm leads; price at qty 10: 6 needed for 3 boxes, buy 10)",
                        DK + "K104K10X7RF5UH5", "186,026 (24-Oct)"),
    "FG28X7R1E105KRT06": (0.183, "DigiKey.es 445-173583-1-ND (TDK, 5 mm leads; price at qty 10: 6 needed, buy 10)",
                          DK + "FG28X7R1E105KRT06", "85,335 (24-Oct)"),
    "ESS107M016AE2EA": (0.114, "DigiKey.es 399-18280-1-ND (KEMET 6.3 mm, 2.50 mm leads, 8.5 mm tall; qty-10 price)",
                        DK + "ESS107M016AE2EA", "14,855 (24-Oct)"),
    "MFR-25FBF52-33R": (0.04, "DigiKey.es (Yageo; qty-10 price, buy 10 per value)", DK + "MFR-25FBF52-33R", "price listed"),
    "MFR-25FBF52-330R": (0.04, "DigiKey.es (Yageo)", DK + "MFR-25FBF52-330R", "est. (same series as 1K)"),
    "MFR-25FBF52-1K": (0.04, "DigiKey.es (Yageo)", "https://www.digikey.es/en/products/detail/yageo/MFR-25FBF52-1K/13011",
                       "46,691 (24-Oct)"),
    "MFR-25FBF52-10K": (0.04, "DigiKey.es (Yageo)", DK + "MFR-25FBF52-10K", "est. (same series as 1K)"),
    "5010": (0.30, "DigiKey.es (Keystone)", DK + "keystone%205010", "price listed"),
    "wire loop": (0.02, "lab stock (bare tinned copper wire 0.8 mm, ~1.5 cm per loop)", "", "-"),
    "P4KE10A": (0.371, "DigiKey.es (Littelfuse; price at qty 10, 15 needed for 3 boxes; TME P4KE10A-LF: 0 in stock)",
                "https://www.digikey.es/en/products/detail/littelfuse-inc/P4KE10A/715501", "1,543 (24-Oct)"),
    "5011": (0.29, "DigiKey.es (Keystone)", DK + "keystone%205011", "price listed (TME: 6,460, MOQ 400)"),
    # connectors
    "B2B-XH-A(LF)(SN)": (0.09, "DigiKey.es (JST)", DK + "B2B-XH-A", "price listed (TME B3B: 18,622)"),
    "B3B-XH-A(LF)(SN)": (0.11, "DigiKey.es (JST)", DK + "B3B-XH-A",
                         "price listed; TME 18,622 (23-Oct)"),
    "61204021621": (1.01, "DigiKey.es 732-5401-ND (Würth)", DK + "61204021621", "1,700 (24-Oct)"),
    "PPTC081LFBN-RC": (0.51, "DigiKey.es S7006-ND (Sullins)", DK + "PPTC081LFBN-RC", "84,501 (24-Oct)"),
    "1x03 male pin header": (0.10, "cut from the 1x40 strip (off-board line)", "", "-"),
    "22 AWG solid tinned copper hook-up wire, PVC insulated": (0.03, "lab stock (insulated solid hook-up wire, ~2 cm per link)",
                                                                "", "-"),
    "M3 x 10 mm nylon standoff": (0.00, "counted in the off-board mechanics line", "", "-"),
    "M3 x 11 mm nylon standoff F/F": (0.00, "counted in the off-board mechanics line", "", "-"),
}

# 3D model source by footprint library (stock models: kicad-packages3D via hw/scripts/fetch_3d.py)
MODEL_3D = {
    "teamc:RevC_Pololu_U3V70F5_Headers": "hw/lib/teamc.3dshapes/RevC_Pololu_U3V70F5.wrl (gen_3d_revc.py, from Pololu's "
                                          "drawing); Pololu STEP www.pololu.com/file/0J1561",
    "teamc:RevC_Pololu_IdealDiode_5388_Headers": "hw/lib/teamc.3dshapes/RevC_Pololu_IdealDiode_5388.wrl (gen_3d_revc.py); "
                                                 "Pololu STEP www.pololu.com/file/0J2101",
    "teamc:RevC_Adafruit_MAX17048_5580_Headers": "hw/lib/teamc.3dshapes/RevC_Adafruit_MAX17048_5580.wrl (gen_3d_revc.py, "
                                                 "from Adafruit's board file)",
}

OFF_BOARD = [   # (item, qty, unit EUR excl. VAT, supplier, link, stock as read, purchased)
    ("Raspberry Pi 3 Model A+ (WiFi/BT disabled or removed, Atenea Q22)", 1, 22.75,
     "bought 19-Oct; market price Kiwi EUR 27.53 incl. VAT = 22.75 excl.",
     "https://www.kiwi-electronics.com/en/raspberry-pi-3-model-aplus-3913", "out of stock at Kiwi (24-Oct)", "yes"),
    ("microSD SanDisk Ultra 32 GB A1 (half a twin pack)", 1, 6.00, "bought 19-Oct (est.)", "", "-", "yes"),
    ("Ebyte E01-ML01SP4 + TX2400-FPC-2509 flex antenna (bundle)", 1, 3.60, "ebyteiot.com, bought 19-Oct", "", "-",
     "yes"),
    ("SP4 breakout: lab PCB (rules EUR 15) + 100 uF, 10 uF, 100 nF, 1x08 + 1x02 headers (hw/sp4-breakout)", 1, 16.00,
     "UPC lab + generic", "", "-", "no"),
    ("Protected 18650 Li-ion cell >= 3000 mAh, button top, ~69 mm (e.g. Keeppower P1835J, Nitecore NL1835)", 1, 8.22,
     "nkon.nl Keeppower P1835J 3500 mAh (EUR 8.22 excl.; alt. tinytronics.nl EUR 9.50)",
     "https://www.nkon.nl/en/keeppower-18650-3500-li-ion.html", "in stock (24-Oct); fit in BH-18650-PC not verified",
     "yes"),
    ("Spare 5x20 mm 4 A fast glass fuse Littelfuse 0217004.HXP (keep it in the box)", 1, 0.44, "DigiKey.es F2394-ND",
     DK + "0217004.HXP", "4,721 (24-Oct)", "yes"),
    ("USB-C charger Adafruit Micro-Lipo #4410 at the box wall (500 mA jumper closed; TP4056 boards out of stock "
     "24-Oct)", 1, 5.22, "DigiKey.es 1528-4410-ND (also Kiwi)", DK + "1528-4410-ND", "966 (24-Oct)", "yes"),
    ("40-way female-female GPIO ribbon, 15-20 cm (fallback: 2 x 3M 89140-0101 IDC sockets + 40-wire flat cable)", 1,
     2.79, "Kiwi Electronics 1160 (40-pin rainbow GPIO cable 20 cm)",
     "https://www.kiwi-electronics.com/en/40-pins-rainbow-gpio-cable-20cm-1160", "50 (24-Oct); F/F + keyed not stated",
     "yes"),
    ("2.54 mm male header strip 1x40, Sullins PRPC040SAAN-RC (module pins + UART header)", 1, 1.08, "DigiKey.es",
     DK + "PRPC040SAAN-RC", "price listed", "yes"),
    # panel switches from TME (Santiago's budget lever, 24-Oct: the Adafruit charger put the box at EUR 150.45).
    # TME showed USD to our reader; counted 1:1 as EUR (the EUR price is lower).
    ("Panel pushbutton E-Switch PS1024ABLK (GO/STOP)", 1, 1.31, "TME (USD price counted as EUR)",
     TME_PS + "ps1024ablk/push-button-switches/e-switch/", "1,379 (24-Oct)", "yes"),
    ("Panel toggle E-Switch 100SP1T1B1M1QEH (power: closed = OFF)", 1, 2.44, "TME (qty-5 price, USD as EUR)",
     TME_PS + "100sp1t1b1m1qeh/toggle-switches/e-switch/", "654 (24-Oct)", "yes"),
    ("Panel toggle E-Switch 100SP1T1B1M1QEH (role TX/RX; may stay unfitted, Atenea Q8)", 1, 2.44,
     "TME (qty-5 price, USD as EUR)", TME_PS + "100sp1t1b1m1qeh/toggle-switches/e-switch/", "654 (24-Oct)", "yes"),
    ("Panel toggle E-Switch 100SP3T1B1M1QEH ON-OFF-ON (mode SRI/MRM/NM)", 1, 3.26, "TME (USD price counted as EUR)",
     TME_PS + "100sp3t1b1m1qeh/toggle-switches/e-switch/", "906 (24-Oct)", "yes"),
    ("5 mm LED green diffused Kingbright WP7113GD (activity)", 1, 0.20, "DigiKey.es 754-1263-ND", DK + "WP7113GD",
     "91,488 (24-Oct)", "yes"),
    ("5 mm LED red diffused Kingbright WP7113SURDK (status; WP7113ID out of stock until Dec)", 1, 0.17,
     "DigiKey.es 754-WP7113SURDK-ND", DK + "WP7113SURDK", "11,546 (24-Oct)", "yes"),
    ("5 mm LED panel clips (2)", 2, 0.45, "DigiKey.es 754-RTC51-ND (Kingbright RTC51)", DK + "RTC51",
     "1,047 (24-Oct)", "yes"),
    ("JST XHP-2 housings (button, role, power, charger)", 4, 0.09, "DigiKey.es", DK + "XHP-2", "price listed", "yes"),
    ("JST XHP-3 housings (mode, LEDs)", 2, 0.09, "DigiKey.es", DK + "XHP-3", "price listed", "yes"),
    ("JST SXH-001T-P0.6 crimps (14 + spares)", 16, 0.04, "DigiKey.es", DK + "SXH-001T-P0.6", "price listed", "yes"),
    ("Hook-up wire 24 AWG for the panel leads, ~1 m", 1, 0.50, "lab stock (market price est.)", "", "-", "no"),
    ("M3 x 10 mm nylon standoffs F/F x4 (carrier to the floor) + M3 x 11 mm x1 (breakout) + M3 x 6 nylon screws x10",
     1, 4.40, "DigiKey.es Keystone 25510 (M3x10) + Essentra MTS-11 (M3x11) + 50M030050P006 (M3x6 screws)",
     DK + "25510", "19,042 / 12,230 / 61,147 (24-Oct)", "yes"),
    ("M2.5 nylon standoffs x4 + screws x8 (the Pi on the box floor), from one 380-piece kit for all boxes (share of "
     "EUR 9.99)", 1, 0.50, "Kiwi KW-2754 M2.5 black nylon screw + standoff set (380 pcs)",
     "https://www.kiwi-electronics.com/en/m2-5-screw-and-stand-off-set-black-nylon-380-pieces-10252",
     "43 (24-Oct)", "yes"),
    ("Cable tie 3.6 mm through the board slots over the cell (drop test)", 1, 0.05, "lab stock (est.)", "", "-", "no"),
    ("IKEA 365+ food container 15 x 15 x 7 cm (plastic, 750 ml) with lid", 1, 3.00, "IKEA (est.)", "", "-", "yes"),
    ("Hot glue, Kapton tape (U.FL plug, microSD, XH housings), foam", 1, 1.00, "lab stock (est.)", "", "-", "no"),
    ("Solder, flux", 1, 0.50, "lab stock (est.)", "", "-", "no"),
    ("PCB: carrier rev C milled at the UPC lab (rules: counts EUR 15)", 1, 15.00, "UPC lab", "", "-", "no"),
]


def model_source(fp):
    if fp in MODEL_3D:
        return MODEL_3D[fp]
    if fp.startswith("teamc:RevC_WireLink"):
        return "hw/lib/teamc.3dshapes/RevC_WireLink_unit.wrl, scaled to the link (gen_3d_revc.py)"
    if fp.startswith("teamc:"):
        return "stock kicad-packages3D model of the footprint it copies (fetch_3d.py)"
    return "stock kicad-packages3D (fetch_3d.py)" if fp else ""


def mpn_key(mpn):
    return mpn.split(" (")[0].split(" + ")[0].strip()


def main():
    with open(NET, encoding="utf-8") as f:
        t = parse(f.read())
    groups = {}
    for c in find_all(find(t, "components"), "comp"):
        ref = str(find(c, "ref")[1])
        val = str(find(c, "value")[1])
        fp = str((find(c, "footprint") or [0, ""])[1])
        fields = {str(find(x, "name")[1]): (str(x[2]) if len(x) > 2 else "")
                  for x in find_all(find(c, "fields") or [], "field")}
        key = (val, fp, fields.get("MPN", ""), fields.get("Manufacturer", ""))
        groups.setdefault(key, []).append(ref)

    def refkey(r):
        stem = r.rstrip("0123456789")
        return stem, int("0" + r[len(stem):])

    rows, missing = [], []
    for (val, fp, mpn, mfr), refs in sorted(groups.items(), key=lambda kv: refkey(sorted(kv[1], key=refkey)[0])):
        k = mpn_key(mpn)
        if k not in SUPPLY:
            missing.append(k or val)
            price, sup, link, stock = 0.0, "?", "", ""
        else:
            price, sup, link, stock = SUPPLY[k]
        qty = len(refs)
        rows.append([" ".join(sorted(refs, key=refkey)), qty, val, fp, mpn, mfr, sup, link, stock, model_source(fp),
                     f"{price:.2f}", f"{qty * price:.2f}", "yes"])
    for item, qty, price, sup, link, stock, bought in OFF_BOARD:
        rows.append(["(off-board)", qty, item, "", "", "", sup, link, stock, "", f"{price:.2f}", f"{qty * price:.2f}",
                     bought])
    if missing:
        raise SystemExit(f"no SUPPLY entry for: {missing}")
    total = sum(float(r[11]) for r in rows)
    bought = sum(float(r[11]) for r in rows if r[12] == "yes")
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ref", "qty", "value / item", "footprint", "MPN", "manufacturer", "supplier",
                    "supplier link", f"stock as read", "3D model source", "unit EUR excl. VAT", "total EUR",
                    "purchased"])
        w.writerows(rows)
        w.writerow([])
        w.writerow(["TOTAL per box (all items at market price excl. VAT, lab PCB EUR 15)"] + [""] * 10 + [f"{total:.2f}", ""])
        w.writerow(["of which purchased by the team"] + [""] * 10 + [f"{bought:.2f}", ""])
        w.writerow(["of which owned / lab stock / lab PCB (non-purchased)"] + [""] * 10 + [f"{total - bought:.2f}", ""])
        w.writerow([f"Cap per box (rules): EUR 150. DRAFT rev C; stock and prices read {STOCK_DATE} or as noted - "
                    "re-check before ordering. Shopping list for 2 boxes + 1 spare: hw/REVC_SHOPPING.md (checkpoint 4)."])
    print(f"BOM rev C: {len(rows)} lines, total EUR {total:.2f} (purchased {bought:.2f}, other {total - bought:.2f})")


if __name__ == "__main__":
    main()
