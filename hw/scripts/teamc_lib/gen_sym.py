#!/usr/bin/env python3
"""Write hw/lib/teamc.kicad_sym (KiCad 10 format): E01-ML01SP4 and MAX17048."""
import sys

OUT = sys.argv[1]


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def prop(name, val, x, y, hide=False, justify=None):
    h = "\n\t\t\t(hide yes)" if hide else ""
    j = f"\n\t\t\t\t(justify {justify})" if justify else ""
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {f(x)} {f(y)} 0)\n\t\t\t(show_name no)\n'
            f'\t\t\t(do_not_autoplace no){h}\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            f'\t\t\t\t){j}\n\t\t\t)\n\t\t)\n')


def pin(typ, x, y, ang, name, num, hide=False):
    h = "\n\t\t\t\t(hide yes)" if hide else ""
    return (f'\t\t\t(pin {typ} line\n\t\t\t\t(at {f(x)} {f(y)} {ang})\n\t\t\t\t(length 2.54){h}\n'
            f'\t\t\t\t(name "{name}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n'
            f'\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t\t(number "{num}"\n\t\t\t\t\t(effects\n'
            f'\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n')


def rect(x0, y0, x1, y1):
    return (f'\t\t\t(rectangle\n\t\t\t\t(start {f(x0)} {f(y0)})\n\t\t\t\t(end {f(x1)} {f(y1)})\n'
            f'\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n'
            f'\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n')


def text(s, x, y, size=1.27):
    return (f'\t\t\t(text "{s}"\n\t\t\t\t(at {f(x)} {f(y)} 0)\n\t\t\t\t(effects\n\t\t\t\t\t(font\n'
            f'\t\t\t\t\t\t(size {f(size)} {f(size)})\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n')


def symbol(name, props, body, pins):
    s = (f'\t(symbol "{name}"\n\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)\n\t\t(exclude_from_sim no)\n'
         '\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(duplicate_pin_numbers_are_jumpers no)\n')
    s += "".join(props)
    s += f'\t\t(symbol "{name}_0_1"\n' + "".join(body) + "\t\t)\n"
    s += f'\t\t(symbol "{name}_1_1"\n' + "".join(pins) + "\t\t)\n"
    s += "\t\t(embedded_fonts no)\n\t)\n"
    return s


sp4 = symbol(
    "E01-ML01SP4",
    [prop("Reference", "U", -7.62, 11.43, justify="left"),
     prop("Value", "E01-ML01SP4", 1.27, 11.43, justify="left"),
     prop("Footprint", "teamc:E01-ML01SP4", 0, -15.24, hide=True),
     prop("Datasheet", "https://www.cdebyte.com/products/E01-ML01SP4", 0, -17.78, hide=True),
     prop("Description", "Ebyte nRF24L01P + PA/LNA 2.4 GHz module, SMD castellated 14.5x18 mm, IPEX", 0, -20.32,
          hide=True),
     prop("MPN", "E01-ML01SP4", 0, -22.86, hide=True),
     prop("Manufacturer", "Ebyte", 0, -25.4, hide=True),
     prop("ki_keywords", "nRF24L01+ nRF24L01P 2.4GHz PA LNA transceiver module Ebyte", 0, 0, hide=True),
     prop("ki_fp_filters", "E01-ML01SP4*", 0, 0, hide=True)],
    [rect(-7.62, 10.16, 12.7, -10.16),
     text("PA/LNA", 6.35, 2.54), text("IPEX ant.", 6.35, 0)],
    [pin("power_in", 0, 12.7, 270, "VCC", "1"),
     pin("input", -10.16, 5.08, 0, "CE", "2"),
     pin("input", -10.16, 2.54, 0, "CSN", "3"),
     pin("input", -10.16, 0, 0, "SCK", "4"),
     pin("input", -10.16, -2.54, 0, "MOSI", "5"),
     pin("tri_state", -10.16, -5.08, 0, "MISO", "6"),
     pin("output", -10.16, -7.62, 0, "IRQ", "7"),
     pin("power_in", 0, -12.7, 90, "GND", "8"),
     pin("passive", 0, -12.7, 90, "GND", "9", hide=True),
     pin("passive", 0, -12.7, 90, "GND", "10", hide=True)])

ds = "https://cdn.sparkfun.com/assets/5/2/7/6/6/MAX17048-MAX17049.pdf"
mx = symbol(
    "MAX17048",
    [prop("Reference", "U", -7.62, 8.89, justify="left"),
     prop("Value", "MAX17048", 1.27, 8.89, justify="left"),
     prop("Footprint", "teamc:MAX17048_TDFN-8-1EP_2x2mm", 0, -12.7, hide=True),
     prop("Datasheet", ds, 0, -15.24, hide=True),
     prop("Description", "1-cell Li-ion ModelGauge fuel gauge, I2C 0x36, 2.5-4.5 V, TDFN-8-EP 2x2 mm (EP = GND). "
          "Based on partreel.com max17048, CC-BY-4.0; pinout per datasheet 19-6171 rev 7 p.6", 0, -17.78, hide=True),
     prop("MPN", "MAX17048G+T10", 0, -20.32, hide=True),
     prop("Manufacturer", "Analog Devices (Maxim)", 0, -22.86, hide=True),
     prop("ki_keywords", "fuel gauge battery LiPo Li-ion I2C ModelGauge Maxim", 0, 0, hide=True),
     prop("ki_fp_filters", "MAX17048*TDFN* TDFN*1EP*2x2mm*", 0, 0, hide=True)],
    [rect(-7.62, 7.62, 7.62, -7.62)],
    [pin("power_in", -10.16, 5.08, 0, "VDD", "3"),
     pin("passive", -10.16, 2.54, 0, "CELL", "2"),
     pin("input", -10.16, -2.54, 0, "QSTRT", "6"),
     pin("passive", -10.16, -5.08, 0, "CTG", "1"),
     pin("bidirectional", 10.16, 5.08, 180, "SDA", "8"),
     pin("input", 10.16, 2.54, 180, "SCL", "7"),
     pin("open_collector", 10.16, -2.54, 180, "~{ALRT}", "5"),
     pin("power_in", 0, -10.16, 90, "GND", "4"),
     pin("passive", 2.54, -10.16, 90, "EP", "9")])

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write('(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "kicad_symbol_editor")\n'
             '\t(generator_version "10.0")\n' + sp4 + mx + ")\n")
print("wrote", OUT)
