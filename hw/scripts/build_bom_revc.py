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
    "K104K10X7RF5UH5": (0.155, "DigiKey.es (Vishay, 5 mm leads; price at qty 10, 18 needed for 3 boxes)",
                        DK + "K104K10X7RF5UH5", "186,026 (24-Oct)"),
    "FG28X7R1E105KRT06": (0.183, "DigiKey.es 445-173583-1-ND (TDK, 5 mm leads; price at qty 10)",
                          DK + "FG28X7R1E105KRT06", "85,335 (24-Oct)"),
    "EEU-FR1C101": (0.36, "DigiKey.es (Panasonic)", DK + "EEU-FR1C101", "price listed, stock not shown"),
    "MFR-25FBF52-33R": (0.04, "DigiKey.es (Yageo; qty-10 price, buy 10 per value)", DK + "MFR-25FBF52-33R", "price listed"),
    "MFR-25FBF52-330R": (0.04, "DigiKey.es (Yageo)", DK + "MFR-25FBF52-330R", "est. (same series as 1K)"),
    "MFR-25FBF52-1K": (0.04, "DigiKey.es (Yageo)", "https://www.digikey.es/en/products/detail/yageo/MFR-25FBF52-1K/13011",
                       "46,691 (24-Oct)"),
    "MFR-25FBF52-10K": (0.04, "DigiKey.es (Yageo)", DK + "MFR-25FBF52-10K", "est. (same series as 1K)"),
    "5010": (0.30, "DigiKey.es (Keystone)", DK + "keystone%205010", "price listed"),
    "5011": (0.29, "DigiKey.es (Keystone)", DK + "keystone%205011", "price listed (TME: 6,460, MOQ 400)"),
    # connectors
    "B2B-XH-A(LF)(SN)": (0.09, "DigiKey.es (JST)", DK + "B2B-XH-A", "price listed (TME B3B: 18,622)"),
    "B3B-XH-A(LF)(SN)": (0.11, "DigiKey.es (JST)", DK + "B3B-XH-A",
                         "price listed; TME 18,622 (23-Oct)"),
    "61204021621": (1.01, "DigiKey.es 732-5401-ND (Würth)", DK + "61204021621", "1,700 (24-Oct)"),
    "PPTC081LFBN-RC": (0.51, "DigiKey.es S7006-ND (Sullins)", DK + "PPTC081LFBN-RC", "84,501 (24-Oct)"),
    "1x03 male pin header": (0.10, "cut from the 1x40 strip (off-board line)", "", "-"),
    "M3 x 10 mm nylon standoff": (0.00, "counted in the off-board mechanics line", "", "-"),
    "M3 x 11 mm nylon standoff F/F": (0.00, "counted in the off-board mechanics line", "", "-"),
}

# 3D model source by footprint library (stock models: kicad-packages3D via hw/scripts/fetch_3d.py)
MODEL_3D = {
    "teamc:Pololu_U3V70F5_Headers": "box model generated from Pololu's drawing (layout phase); Pololu STEP www.pololu.com/file/0J1561",
    "teamc:Pololu_IdealDiode_5388_Headers": "box model generated from Pololu's drawing (layout phase); Pololu STEP www.pololu.com/file/0J2101",
    "teamc:Adafruit_MAX17048_5580_Headers": "box model generated from Adafruit's board file (layout phase)",
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
    ("Protected 18650 Li-ion cell >= 3000 mAh, button top, ~69 mm (e.g. Keeppower P1835J, Nitecore NL1835)", 1, 9.00,
     "nkon.nl / Amazon.es (est.)", "https://www.nkon.nl/", "not verified", "yes"),
    ("Spare 5x20 mm 4 A fast glass fuse Littelfuse 0217004.HXP (keep it in the box)", 1, 0.53, "DigiKey.es",
     DK + "0217004.HXP", "price listed", "yes"),
    ("USB-C charger module TP4056 with protection (HW-373), at the box wall (alternative: Adafruit #4410, "
     "DigiKey.es 1528-4410-ND EUR 5.22, 966 pcs, 0.5 A with its jumper)", 1, 1.00,
     "Amazon.es / AliExpress (est.; botland.store is now B2B only)", "", "not verified", "yes"),
    ("40-way female-female GPIO ribbon, 15-20 cm (fallback: 2 x 3M 89140-0101 IDC sockets + 40-wire flat cable)", 1,
     2.00, "Amazon.es (est.; botland.store is B2B only)", "", "not verified", "yes"),
    ("2.54 mm male header strip 1x40, Sullins PRPC040SAAN-RC (module pins + UART header)", 1, 1.08, "DigiKey.es",
     DK + "PRPC040SAAN-RC", "price listed", "yes"),
    ("Panel pushbutton E-Switch PS1024ABLK (GO/STOP)", 1, 1.46, "DigiKey.es EG2011-ND", DK + "PS1024ABLK",
     "5,531 (24-Oct)", "yes"),
    ("Panel toggle E-Switch 100SP1T1B1M1QEH (power: closed = OFF)", 1, 2.70, "DigiKey.es EG2350-ND",
     DK + "100SP1T1B1M1QEH", "8,552 (24-Oct)", "yes"),
    ("Panel toggle E-Switch 100SP1T1B1M1QEH (role TX/RX; may stay unfitted, Atenea Q8)", 1, 2.70,
     "DigiKey.es EG2350-ND", DK + "100SP1T1B1M1QEH", "8,552 (24-Oct)", "yes"),
    ("Panel toggle E-Switch 100SP3T1B1M1QEH ON-OFF-ON (mode SRI/MRM/NM)", 1, 4.75, "DigiKey.es EG2375-ND",
     DK + "100SP3T1B1M1QEH", "2,223 (24-Oct)", "yes"),
    ("5 mm LED green diffused Kingbright WP7113GD (activity)", 1, 0.20, "DigiKey.es 754-1263-ND", DK + "WP7113GD",
     "91,488 (24-Oct)", "yes"),
    ("5 mm LED red diffused Kingbright WP7113ID (status)", 1, 0.18, "DigiKey.es", DK + "WP7113ID", "price listed",
     "yes"),
    ("5 mm LED panel clips (2)", 2, 0.30, "TME Kingbright RTC-51 (est.)",
     "https://www.tme.eu/en/details/clip5mm/holders/kingbright-electronic/rtc-51/", "not verified", "yes"),
    ("JST XHP-2 housings (button, role, power, charger)", 4, 0.09, "DigiKey.es", DK + "XHP-2", "price listed", "yes"),
    ("JST XHP-3 housings (mode, LEDs)", 2, 0.09, "DigiKey.es", DK + "XHP-3", "price listed", "yes"),
    ("JST SXH-001T-P0.6 crimps (14 + spares)", 16, 0.04, "DigiKey.es", DK + "SXH-001T-P0.6", "price listed", "yes"),
    ("Hook-up wire 24 AWG for the panel leads, ~1 m", 1, 0.50, "lab stock (market price est.)", "", "-", "no"),
    ("M3 x 10 mm nylon standoffs F/F x4 (carrier to the floor) + M3 x 11 mm x1 (breakout) + M3 x 6 nylon screws x10",
     1, 2.50, "est.", "", "not verified", "yes"),
    ("M2.5 standoffs x4 + screws x8 (the Pi on the box floor)", 1, 1.40, "est.", "", "not verified", "yes"),
    ("Cable tie 3.6 mm through the board slots over the cell (drop test)", 1, 0.05, "lab stock (est.)", "", "-", "no"),
    ("IKEA 365+ food container 15 x 15 x 7 cm (plastic, 750 ml) with lid", 1, 3.00, "IKEA (est.)", "", "-", "yes"),
    ("Hot glue, Kapton tape (U.FL plug, microSD, XH housings), foam", 1, 1.00, "lab stock (est.)", "", "-", "no"),
    ("Solder, flux", 1, 0.50, "lab stock (est.)", "", "-", "no"),
    ("PCB: carrier rev C milled at the UPC lab (rules: counts EUR 15)", 1, 15.00, "UPC lab", "", "-", "no"),
]


def model_source(fp):
    if fp in MODEL_3D:
        return MODEL_3D[fp]
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
