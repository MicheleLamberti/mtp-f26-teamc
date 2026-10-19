"""Bill of materials per device for the Team C box (DRAFT – for ET review) -> hw/BOM.csv

    python3 hw/scripts/build_bom.py

Board parts come from the carrier netlist (hw/teamc-carrier/build/teamc-carrier.net), grouped by value, footprint
and MPN; DNP parts are listed with quantity 0. Off-board parts (the Pi, the microSD, the radio, the cell, panel
controls, harness, mechanics, consumables) and the ETSETB lab PCB at the fixed EUR 15 are added from OFF_BOARD.
Rules (competition PDF, cost section): everything goes in the BoM, owned or lab-stock items at market price; the
"purchased" column separates what the team buys from what it already has or the lab provides.
Prices: EUR excl. VAT, qty 1-10, 19-Oct-26, from the research notes (DigiKey.de, LCSC, TME); "est." = estimate.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import find, find_all, parse  # noqa: E402

HW = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NET = os.path.join(HW, "teamc-carrier", "build", "teamc-carrier.net")
OUT = os.path.join(HW, "BOM.csv")

# unit price (EUR) and supplier per MPN; parts not listed fall back to PASSIVE by footprint
PRICE = {
    "TPS61022RWUR": (2.09, "DigiKey.de (stock 0 on 19-Oct: check Mouser/LCSC/TI)"),
    "744316100": (2.39, "DigiKey.de"),
    "MCP73831T-2ACI/OT": (0.67, "DigiKey.de"),
    "TLV75533PDBVR": (0.37, "DigiKey.de"),
    "TPS63001DRCR": (2.41, "DigiKey.de (DNP)"),
    "LPS4018-222MRB": (1.20, "Coilcraft/Mouser est. (DNP)"),
    "MAX17048G+T10": (4.05, "DigiKey.es (LCSC C2682616 ~EUR 2.0)"),
    "AO3401A": (0.46, "DigiKey.de"),
    "Si2333DDS-T1-GE3": (0.68, "DigiKey.de (stock 0 on 19-Oct, due Jan-27; AO3401A fallback)"),
    "BCM857BS,115": (0.45, "DigiKey.de"),
    "0466005.NR": (0.45, "est. (Littelfuse 0466 1206 fast; verify part and stock)"),
    "2N7002,215": (0.18, "DigiKey.de"),
    "BC857BS,115": (0.45, "DigiKey.de"),
    "SP0504BAHTG": (0.45, "LCSC C10675"),
    "SMF5V0A-E3-08": (0.30, "DigiKey.de"),
    "USB4125-GF-A-0190": (0.54, "DigiKey.de"),
    "EEE-FK1C101P": (0.54, "DigiKey.de"),
    "EEE-HA1A101WP": (0.50, "est."),
    "B2P-VH": (0.25, "est. (JST VH)"),
    "B2B-XH-A": (0.05, "LCSC C158012"),
    "B2B-XH-A(LF)(SN)": (0.05, "LCSC C158012"),
    "B3B-XH-A": (0.08, "LCSC C144394"),
    "B3B-XH-A(LF)(SN)": (0.08, "LCSC C144394"),
    "Harwin M20-7832046": (3.50, "DigiKey/Mouser (aggregator)"),
    "M20-7832046": (3.50, "DigiKey/Mouser (aggregator)"),
    "Omron B3F-1000": (0.20, "est."),
    "B3F-1000": (0.20, "est."),
    "150080VS75000": (0.15, "DigiKey"),
    "150080RS75000": (0.20, "DigiKey"),
    "E01-ML01SP4": (3.60, "ebyteiot.com, bundle with TX2400-FPC-2509 ($3.88) — ordered"),
}
PASSIVE = {"Resistor_SMD": (0.02, "generic 0805 1 % (LCSC)"), "Capacitor_SMD": (0.05, "generic MLCC (LCSC)"),
           "TestPoint": (0.05, "wire loop (lab stock) or Keystone 5000/5001 ~EUR 0.30"),
           "MountingHole": (0.0, "hole in the PCB (standoffs listed below)"),
           "Connector_PinHeader_2.54mm": (0.10, "generic pin header")}

# off-board items per device: (item, qty, unit EUR, supplier/source, purchased?)
OFF_BOARD = [
    ("Raspberry Pi 3 Model A+ (WiFi/BT disabled or removed, Atenea Q22)", 1, 27.00, "ordered 19-Oct (market price)", "yes"),
    ("microSD SanDisk Ultra 32 GB A1 (half a twin pack)", 1, 6.00, "ordered 19-Oct (est.)", "yes"),
    ("Antenna Ebyte TX2400-FPC-2509 (in the SP4 bundle)", 1, 0.00, "included in the SP4 line", "yes"),
    ("Protected 18650 Li-ion cell >= 3000 mAh", 1, 8.00, "est.", "yes"),
    ("18650 holder MPD BH-18650-PC (THT, for protected cells), on the box floor", 1, 2.94, "DigiKey.de", "yes"),
    ("Panel pushbutton E-Switch PS1024ABLK (GO/STOP)", 1, 1.17, "TME", "yes"),
    ("Panel toggle E-Switch 100SP1T1B1M1QEH (power ON/OFF)", 1, 2.32, "TME", "yes"),
    ("Panel toggle E-Switch 100SP1T1B1M1QEH (role TX/RX; may stay unfitted, Atenea Q8)", 1, 2.32, "TME", "yes"),
    ("Panel toggle E-Switch 100SP3T1B1M1QEH ON-OFF-ON (mode SRI/MRM/NM)", 1, 2.89, "TME", "yes"),
    ("JST XHP-2 housing (power, button, role leads)", 3, 0.03, "LCSC est.", "yes"),
    ("JST XHP-3 housing (mode lead)", 1, 0.04, "LCSC est.", "yes"),
    ("JST VHR-2N housing (battery lead)", 1, 0.10, "LCSC est.", "yes"),
    ("JST crimps SXH-001T-P0.6 (XH) x9 + SVH-21T-P1.1 (VH) x2", 11, 0.03, "LCSC est.", "yes"),
    ("Hook-up wire (AWG24 leads, AWG20 battery lead), ~1 m", 1, 0.50, "lab stock (market price est.)", "no"),
    ("Standoff Würth 970110155 M2.5 x 11 F/F nylon (HAT on the Pi)", 4, 0.35, "est. (RS)", "yes"),
    ("Standoff M2.5 x 5 F/F (Pi on the box base plate)", 4, 0.25, "est.", "yes"),
    ("Screw M2.5 x 6 (ISO 7380)", 12, 0.05, "est.", "yes"),
    ("IKEA 365+ food container 15 x 15 x 7 cm with lid", 1, 3.00, "IKEA (est.)", "yes"),
    ("Hot glue, Kapton tape (U.FL plug, microSD, XH housings), cable ties, foam", 1, 1.00, "lab stock (est.)", "no"),
    ("Solder, flux", 1, 0.50, "lab stock (est.)", "no"),
    ("PCB: carrier made at the ETSETB lab (rules: counts EUR 15)", 1, 15.00, "ETSETB lab", "no"),
]


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
        dnp = any(str((find(p, "name") or [0, ""])[1]) == "dnp" for p in find_all(c, "property"))
        key = (val, fp, fields.get("MPN", ""), fields.get("Manufacturer", ""), dnp)
        groups.setdefault(key, []).append(ref)
    rows = []
    for (val, fp, mpn, mfr, dnp), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        key = mpn.split(" (")[0].strip()
        price, src = PRICE.get(key, PRICE.get(key.split()[-1] if key else "", None)
                               or PASSIVE.get(fp.split(":")[0], (0.10, "est.")))
        qty = 0 if dnp else len(refs)
        rows.append([" ".join(sorted(refs, key=lambda r: (r.rstrip("0123456789"), int("0" + r[len(r.rstrip("0123456789")):])))),
                     qty, val + (" (DNP)" if dnp and "DNP" not in val else ""), fp, mpn, mfr, src, f"{price:.2f}", f"{qty * price:.2f}",
                     "yes"])
    for item, qty, price, src, bought in OFF_BOARD:
        rows.append(["(off-board)", qty, item, "", "", "", src, f"{price:.2f}", f"{qty * price:.2f}", bought])
    total = sum(float(r[8]) for r in rows)
    bought = sum(float(r[8]) for r in rows if r[9] == "yes")
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ref", "qty", "value / item", "footprint", "MPN", "manufacturer", "supplier / source",
                    "unit EUR excl. VAT", "total EUR", "purchased"])
        w.writerows(rows)
        w.writerow([])
        w.writerow(["TOTAL per device (all items at market price, lab PCB EUR 15)", "", "", "", "", "", "", "",
                    f"{total:.2f}", ""])
        w.writerow(["of which purchased by the team", "", "", "", "", "", "", "", f"{bought:.2f}", ""])
        w.writerow(["of which owned / lab stock / lab PCB (non-purchased)", "", "", "", "", "", "", "",
                    f"{total - bought:.2f}", ""])
        w.writerow(["Cap per device (rules): EUR 150. DRAFT – for ET review; prices 19-Oct-26, verify before ordering"])
    print(f"BOM: {len(rows)} lines, total EUR {total:.2f} (purchased {bought:.2f}, non-purchased {total - bought:.2f})")


if __name__ == "__main__":
    main()
