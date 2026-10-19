"""Update a .kicad_pcb from a KiCad netlist (what "Update PCB from Schematic" does in the GUI).

    python3 netlist2pcb.py board.kicad_pcb board.net [--keep REF ...]

Footprints already on the board keep their position, side and rotation; new ones are loaded from the KiCad
libraries (or hw/lib/teamc.pretty) and stacked to the right of the board for placement. Footprints whose
reference is no longer in the netlist are removed unless listed with --keep. Pad nets and the schematic links
(paths) are rewritten every time, so DRC's schematic-parity check passes.
"""
import argparse
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import find, find_all, parse  # noqa: E402

FP_ROOT = "/usr/share/kicad/footprints"
TEAMC_PRETTY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "teamc.pretty")


def lib_path(lib):
    return TEAMC_PRETTY if lib == "teamc" else os.path.join(FP_ROOT, lib + ".pretty")


def read_netlist(path):
    with open(path, encoding="utf-8") as f:
        t = parse(f.read())
    comps = {}
    for c in find_all(find(t, "components"), "comp"):
        ref = str(find(c, "ref")[1])
        fp = find(c, "footprint")
        sp = find(c, "sheetpath")
        stamps = find(c, "tstamps")
        comps[ref] = {
            "fp": str(fp[1]) if fp else "",
            "value": str(find(c, "value")[1]),
            "path": str(find(sp, "tstamps")[1]) + str(stamps[1]),
            "dnp": any(str(p[1]) == "dnp" for p in find_all(c, "property")),
            "fields": {str(find(f, "name")[1]): str(f[2]) if len(f) > 2 else "" for f in find_all(find(c, "fields") or [], "field")
                       if str(find(f, "name")[1]) != "Footprint"},
        }
    nets = {}
    for n in find_all(find(t, "nets"), "net"):
        name = str(find(n, "name")[1])
        for node in find_all(n, "node"):
            nets.setdefault(str(find(node, "ref")[1]), {})[str(find(node, "pin")[1])] = name
    return comps, nets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcb")
    ap.add_argument("netlist")
    ap.add_argument("--keep", nargs="*", default=[])
    a = ap.parse_args()
    board = pcbnew.LoadBoard(a.pcb)
    comps, pin_nets = read_netlist(a.netlist)
    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for ref, fp in existing.items():
        if ref not in comps and ref not in a.keep:
            board.Remove(fp)
            print("removed", ref)
    netinfo = {}
    for names in pin_nets.values():
        for name in names.values():
            if name not in netinfo:
                ni = board.FindNet(name)
                if ni is None:
                    ni = pcbnew.NETINFO_ITEM(board, name)
                    board.Add(ni)
                netinfo[name] = ni
    bb = board.GetBoardEdgesBoundingBox()
    park_x = bb.GetRight() + pcbnew.FromMM(10)
    park_y = bb.GetTop()
    for ref in sorted(comps):
        c = comps[ref]
        if not c["fp"]:
            continue
        lib, name = c["fp"].split(":", 1)
        fp = existing.get(ref)
        if fp is not None and fp.GetFPID().GetUniStringLibId() != c["fp"]:
            pos, rot, layer = fp.GetPosition(), fp.GetOrientationDegrees(), fp.GetLayer()
            board.Remove(fp)
            fp = None
        else:
            pos = rot = layer = None
        if fp is None:
            new = pcbnew.FootprintLoad(lib_path(lib), name)
            if new is None:
                raise SystemExit(f"{ref}: footprint {c['fp']} not found")
            new.SetFPID(pcbnew.LIB_ID(lib, name))
            board.Add(new)
            if pos is not None:
                new.SetPosition(pos)
                if layer == pcbnew.B_Cu:
                    new.Flip(new.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
                new.SetOrientationDegrees(rot)
            else:
                new.SetPosition(pcbnew.VECTOR2I(int(park_x), int(park_y)))
                park_y += pcbnew.FromMM(8)
            fp = new
            print("added", ref, c["fp"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetDNP(c["dnp"])
        for k, v in c["fields"].items():
            fp.SetField(k, v)
            fp.GetField(k).SetVisible(False)
        nets = pin_nets.get(ref, {})
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num in nets:
                pad.SetNet(netinfo[nets[num]])
            else:
                pad.SetNetCode(0)
    board.BuildConnectivity()
    board.Save(a.pcb)


if __name__ == "__main__":
    main()
