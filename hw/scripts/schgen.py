"""Generate KiCad 10 schematics from a Python parts list (Team C, DRAFT – for ET review).

Every pin gets a short wire stub and a net label: GND becomes a power:GND symbol, nets in `global_nets` become
global labels (they connect across sheets), anything else a local label. A pin mapped to None gets a no-connect
flag. Every pin of a placed unit must be listed, so a forgotten pin fails here instead of in ERC.
UUIDs are derived from names (uuid5), so regenerating keeps the links to the board.

    sh = Sheet("radio", "Radio: E01-ML01SP4")
    sh.add("teamc:E01-ML01SP4", "U4", "E01-ML01SP4", fp="teamc:E01-ML01SP4", at=(100, 80),
           nets={"1": "3V3_RADIO", "2": "RADIO_CE", ...}, mpn="E01-ML01SP4", mfr="Ebyte", ds="https://...")
    Project("teamc-carrier", [sh, ...]).write(folder)       # hierarchical: root + one file per sheet
    sh.write_standalone(folder, "sp4-breakout")              # a single-sheet project
"""
import copy
import math
import os
import uuid

from sexpr import Q, dump, find, find_all, parse

KICAD_SYM = "/usr/share/kicad/symbols"
HERE = os.path.dirname(os.path.abspath(__file__))
EXTRA_LIBS = {"teamc": os.path.join(HERE, "..", "lib", "teamc.kicad_sym")}
GRID = 1.27
STUB = 2.54
NS = uuid.UUID("5d3c1b0e-7c55-4b6f-9a51-7e3c0f4e2a10")
_lib_cache = {}


def uid(*parts):
    return Q(str(uuid.uuid5(NS, "/".join(str(p) for p in parts))))


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def _lib(name):
    if name not in _lib_cache:
        path = EXTRA_LIBS.get(name, os.path.join(KICAD_SYM, name + ".kicad_sym"))
        with open(path, encoding="utf-8") as f:
            tree = parse(f.read())
        _lib_cache[name] = {s[1]: s for s in find_all(tree, "symbol")}
    return _lib_cache[name]


def load_symbol(lib_id):
    """The library symbol flattened (extends resolved) and renamed to lib_id, as eeschema embeds it."""
    lib, name = lib_id.split(":", 1)
    syms = _lib(lib)
    if name not in syms:
        raise KeyError(f"symbol {lib_id} not found")
    sym = copy.deepcopy(syms[name])
    ext = find(sym, "extends")
    if ext:
        parent = load_symbol(f"{lib}:{ext[1]}")
        own_props = {p[1]: p for p in find_all(sym, "property")}
        flat = [e for e in parent if not (isinstance(e, list) and e and e[0] == "property")]
        flat[1] = Q(lib_id)
        # the child's properties replace the parent's; keep the parent's order for the rest
        props = [own_props.pop(p[1], p) for p in find_all(parent, "property")] + list(own_props.values())
        head = [e for e in flat if not (isinstance(e, list) and e and e[0] in ("symbol", "embedded_fonts"))]
        tail = [e for e in flat if isinstance(e, list) and e and e[0] in ("symbol", "embedded_fonts")]
        pname = parent[1].split(":", 1)[1]
        for u in tail:
            if u[0] == "symbol":
                u[1] = Q(name + u[1][len(pname):])
        sym = head + props + tail
        return sym
    sym[1] = Q(lib_id)
    return sym


def symbol_pins(sym, unit):
    """[(number, name, type, x, y, angle, hidden)] in library coordinates (Y up) for the unit (and unit 0)."""
    out = []
    base = sym[1].split(":", 1)[1]
    for u in find_all(sym, "symbol"):
        suffix = u[1][len(base) + 1:].split("_")
        if len(suffix) != 2 or int(suffix[0]) not in (0, unit) or suffix[1] not in ("0", "1"):
            continue
        for p in find_all(u, "pin"):
            at = find(p, "at")
            num = find(p, "number")[1]
            nm = find(p, "name")[1]
            hidden = "hide" in p or find(p, "hide") is not None
            out.append((str(num), str(nm), p[1], float(at[1]), float(at[2]), float(at[3]), hidden))
    return out


def _xform(px, py, rot, mirror_x=False):
    """Library point → schematic offset (Y down) for a symbol rotated by rot degrees (counter-clockwise)."""
    if mirror_x:
        py = -py
    r = math.radians(rot)
    x = px * math.cos(r) - py * math.sin(r)
    y = px * math.sin(r) + py * math.cos(r)
    return x, -y


def _prop(name, value, x, y, hide=False, angle=0):
    p = ["property", Q(name), Q(value), ["at", x, y, angle], ["effects", ["font", ["size", 1.27, 1.27]]]]
    if hide:
        p[-1].append(["hide", "yes"])
    return p


class Part:
    def __init__(self, sheet, lib_id, ref, value, fp, at, rot, nets, unit, fields, dnp):
        self.sheet, self.lib_id, self.ref, self.value, self.fp = sheet, lib_id, ref, value, fp
        self.at, self.rot, self.nets, self.unit, self.fields, self.dnp = at, rot, nets, unit, fields, dnp


class Sheet:
    def __init__(self, name, title="", global_nets=(), paper="A3"):
        self.name, self.title, self.paper = name, title or name, paper
        self.global_nets = set(global_nets)
        self.parts, self.flags, self.notes, self.extra = [], [], [], []
        self.lib_syms = {}
        self.pwr_base = 0

    def add(self, lib_id, ref, value, fp="", at=(50, 50), rot=0, nets=None, unit=1, mpn="", mfr="", ds="",
            dnp=False, **fields):
        sym = self.lib_syms.setdefault(lib_id, load_symbol(lib_id))
        nets = {str(k): v for k, v in (nets or {}).items()}
        pins = symbol_pins(sym, unit)
        nums = {p[0] for p in pins}
        missing = nums - set(nets)
        extra = set(nets) - nums
        if missing or extra:
            raise ValueError(f"{self.name} {ref} ({lib_id} unit {unit}): unlisted pins {sorted(missing)}, "
                             f"unknown pins {sorted(extra)}")
        f = {"MPN": mpn, "Manufacturer": mfr}
        f.update(fields)
        part = Part(self, lib_id, ref, value, fp, (snap(at[0]), snap(at[1])), rot, nets, unit, f, dnp)
        part.datasheet = ds
        self.parts.append(part)
        return part

    def pwr_flag(self, net, at):
        self.flags.append((net, (snap(at[0]), snap(at[1]))))

    def note(self, text, at, size=1.5):
        self.notes.append((text, at, size))

    # ---- output -------------------------------------------------------------------------------------------
    def _body(self, project, path_uuid):
        items = []
        self._npwr = 0
        gnd = 0
        for part in self.parts:
            sym = self.lib_syms[part.lib_id]
            sx, sy = part.at
            props = {p[1]: p for p in find_all(sym, "property")}
            flag = lambda k: (find(sym, k) or [k, "yes"])[1]  # noqa: E731  (the library symbol's own flags)
            inst = ["symbol", ["lib_id", Q(part.lib_id)], ["at", sx, sy, part.rot], ["unit", part.unit],
                    ["exclude_from_sim", "no"], ["in_bom", flag("in_bom")], ["on_board", flag("on_board")],
                    ["dnp", "yes" if part.dnp else "no"], ["uuid", uid(self.name, part.ref, part.unit)]]
            ry = sy - 2.54
            inst.append(_prop("Reference", part.ref, sx + 2.54, ry - 5.08))
            inst.append(_prop("Value", part.value, sx + 2.54, ry - 2.54))
            inst.append(_prop("Footprint", part.fp, sx, sy, hide=True))
            inst.append(_prop("Datasheet", part.datasheet or (props.get("Datasheet") or [0, 0, Q("")])[2],
                              sx, sy, hide=True))
            if "Description" in props:
                inst.append(_prop("Description", props["Description"][2], sx, sy, hide=True))
            for k, v in part.fields.items():
                if v:
                    inst.append(_prop(k, v, sx, sy, hide=True))
            seen = set()
            for num, _nm, ptype, px, py, pang, _hid in symbol_pins(sym, part.unit):
                inst.append(["pin", Q(num), ["uuid", uid(self.name, part.ref, part.unit, "pin", num)]])
                dx, dy = _xform(px, py, part.rot)
                ex, ey = round(sx + dx, 4), round(sy + dy, 4)
                if (ex, ey) in seen:
                    continue
                seen.add((ex, ey))
                net = part.nets[num]
                key = (self.name, part.ref, part.unit, num)
                if net is None:
                    if ptype != "no_connect":
                        items.append(["no_connect", ["at", ex, ey], ["uuid", uid(*key, "nc")]])
                    continue
                # outward direction: opposite to the pin's direction into the body
                odx, ody = _xform(math.cos(math.radians(pang + 180)), math.sin(math.radians(pang + 180)), part.rot)
                ox, oy = round(ex + odx * STUB, 4), round(ey + ody * STUB, 4)
                items.append(["wire", ["pts", ["xy", ex, ey], ["xy", ox, oy]],
                              ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid(*key, "w")]])
                ang = (round(math.degrees(math.atan2(-ody, odx))) + 360) % 360
                if net == "GND":
                    gnd += 1
                    items.append(self._power("power:GND", "#PWR", f"{self.name}_gnd{gnd}", ox, oy, project,
                                             path_uuid, key))
                elif net in self.global_nets:
                    just = "right" if ang == 180 or ang == 270 else "left"
                    items.append(["global_label", Q(net), ["shape", "passive"], ["at", ox, oy, ang],
                                  ["fields_autoplaced", "yes"],
                                  ["effects", ["font", ["size", 1.27, 1.27]], ["justify", just]],
                                  ["uuid", uid(*key, "gl")]])
                else:
                    just = "right" if ang == 180 or ang == 270 else "left"
                    items.append(["label", Q(net), ["at", ox, oy, ang], ["fields_autoplaced", "yes"],
                                  ["effects", ["font", ["size", 1.27, 1.27]], ["justify", just, "bottom"]],
                                  ["uuid", uid(*key, "l")]])
            inst.append(["instances", ["project", Q(project), ["path", Q(path_uuid), ["reference", Q(part.ref)],
                                                               ["unit", part.unit]]]])
            items.append(inst)
        for i, (net, (fx, fy)) in enumerate(self.flags):
            items.append(self._power("power:PWR_FLAG", "#FLG", f"{self.name}_flg{i}", fx, fy, project, path_uuid,
                                     (self.name, "flag", i)))
            items.append(["wire", ["pts", ["xy", fx, fy], ["xy", fx, fy + STUB]],
                          ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid(self.name, "flagw", i)]])
            lbl = ["global_label", Q(net), ["shape", "passive"], ["at", fx, fy + STUB, 270],
                   ["fields_autoplaced", "yes"], ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "right"]],
                   ["uuid", uid(self.name, "flagl", i)]] if net in self.global_nets else \
                  ["label", Q(net), ["at", fx, fy + STUB, 270], ["fields_autoplaced", "yes"],
                   ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "right", "bottom"]],
                   ["uuid", uid(self.name, "flagl", i)]]
            if net == "GND":
                lbl = self._power("power:GND", "#PWR", f"{self.name}_flggnd{i}", fx, fy + STUB, project, path_uuid,
                                  (self.name, "flaggnd", i))
            items.append(lbl)
        for i, (text, (tx, ty), size) in enumerate(self.notes):
            items.append(["text", Q(text), ["exclude_from_sim", "no"], ["at", tx, ty, 0],
                          ["effects", ["font", ["size", size, size]], ["justify", "left", "top"]],
                          ["uuid", uid(self.name, "note", i)]])
        return items + self.extra

    def _power(self, lib_id, refbase, key, x, y, project, path_uuid, ukey):
        self.lib_syms.setdefault(lib_id, load_symbol(lib_id))
        self._npwr += 1
        ref = f"{refbase}{self.pwr_base + self._npwr:04d}"
        val = lib_id.split(":")[1]
        return ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, 0], ["unit", 1], ["exclude_from_sim", "no"],
                ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", uid(*ukey, "pwr")],
                _prop("Reference", ref, x, y + 3.81 if val == "GND" else y - 3.81, hide=True),
                _prop("Value", val, x, y + 3.81 if val == "GND" else y - 3.81, hide=val == "GND"),
                _prop("Footprint", "", x, y, hide=True), _prop("Datasheet", "", x, y, hide=True),
                ["pin", Q("1"), ["uuid", uid(*ukey, "pwrpin")]],
                ["instances", ["project", Q(project), ["path", Q(path_uuid), ["reference", Q(ref)], ["unit", 1]]]]]

    def document(self, project, root_uuid, path_uuid, own_uuid, page):
        items = self._body(project, path_uuid)
        head = ["kicad_sch", ["version", "20260306"], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
                ["uuid", Q(own_uuid)], ["paper", Q(self.paper)],
                ["title_block", ["title", Q(self.title)], ["date", Q("2026-10-19")], ["rev", Q("DRAFT")],
                 ["company", Q("MTP F26 Team C (UPC)")], ["comment", 1, Q("DRAFT – for ET review")],
                 ["comment", 2, Q("Generated by hw/scripts/schgen.py; edit the sheet's .py, not this file")]],
                ["lib_symbols"] + list(self.lib_syms.values())]
        return head + items

    def write_standalone(self, folder, project):
        """A one-sheet project (e.g. the breakout)."""
        root = uid(project, "root")
        doc = self.document(project, root, "/" + root, root, "1")
        doc.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
        doc.append(["embedded_fonts", "no"])
        _write(os.path.join(folder, project + ".kicad_sch"), doc)


class Project:
    def __init__(self, name, sheets, title=""):
        self.name, self.sheets, self.title = name, sheets, title

    def write(self, folder):
        root = uid(self.name, "root")
        items, y = [], 30.48
        for i, sh in enumerate(self.sheets):
            sh.pwr_base = (i + 1) * 1000
            sid = uid(self.name, "sheet", sh.name)
            x = 25.4 + (i % 2) * 101.6
            if i and i % 2 == 0:
                y += 50.8
            items.append(["sheet", ["at", x, y], ["size", 76.2, 30.48], ["exclude_from_sim", "no"],
                          ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                          ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                          ["uuid", sid],
                          ["property", Q("Sheetname"), Q(sh.name), ["at", x, y - 0.7, 0],
                           ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left", "bottom"]]],
                          ["property", Q("Sheetfile"), Q(sh.name + ".kicad_sch"), ["at", x, y + 31.1, 0],
                           ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left", "top"]]],
                          ["instances", ["project", Q(self.name), ["path", Q("/" + root), ["page", Q(str(i + 2))]]]]])
            doc = sh.document(self.name, root, f"/{root}/{sid}", uid(self.name, "file", sh.name), str(i + 2))
            doc.append(["embedded_fonts", "no"])
            _write(os.path.join(folder, sh.name + ".kicad_sch"), doc)
        head = ["kicad_sch", ["version", "20260306"], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
                ["uuid", root], ["paper", Q("A4")],
                ["title_block", ["title", Q(self.title or self.name)], ["date", Q("2026-10-19")], ["rev", Q("DRAFT")],
                 ["company", Q("MTP F26 Team C (UPC)")], ["comment", 1, Q("DRAFT – for ET review")],
                 ["comment", 2, Q("Generated by hw/scripts/schgen.py")]],
                ["lib_symbols"]]
        doc = head + items + [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
        _write(os.path.join(folder, self.name + ".kicad_sch"), doc)


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(doc) + "\n")
