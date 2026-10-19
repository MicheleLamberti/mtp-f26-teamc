"""Shared helpers for Team C board scripts: lab design rules, library tables, pcbnew drawing, fab outputs."""
import json
import os
import subprocess

import pcbnew

HW = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MM = pcbnew.FromMM

# Conservative rules while the lab's limits are unknown (KiCad brief §4 Phase D): the SP4 breakout
LAB_RULES = {"clearance": 0.3, "track": 0.4, "via_d": 0.8, "via_drill": 0.4, "edge": 0.5}
# The carrier (19-Oct): a JLCPCB-class 2-layer fab (it needs plated vias and 0.15 mm at its QFN/TDFN anyway);
# 0.2 mm clearance and 0.25 mm signals are well inside such a fab's limits (0.1/0.1 mm), power stays wide
FAB_RULES = {"clearance": 0.2, "track": 0.25, "via_d": 0.8, "via_drill": 0.4, "edge": 0.5}


def set_project_rules(pro_path, rules=LAB_RULES, classes=()):
    """Write the Default net class and the board minimums into the .kicad_pro;
    classes = [(name, width, nets[, clearance])], highest priority first."""
    with open(pro_path, encoding="utf-8") as f:
        p = json.load(f)
    ns = p["net_settings"]
    default = ns["classes"][0]
    default.update(clearance=rules["clearance"], track_width=rules["track"], via_diameter=rules["via_d"],
                   via_drill=rules["via_drill"])
    ns["classes"] = [default]
    patterns = []
    for i, cl in enumerate(classes):
        name, width, nets = cl[:3]
        c = dict(default)
        c.update(name=name, track_width=width, priority=i)
        if len(cl) > 3:
            c["clearance"] = cl[3]
        ns["classes"].append(c)
        patterns += [{"netclass": name, "pattern": n} for n in nets]
    ns["netclass_patterns"] = patterns
    r = p["board"]["design_settings"]["rules"]
    # the net classes carry the lab's 0.3 mm; the board floor only has to admit the pads inside fine-pitch
    # packages (QFN/TDFN 0.5 mm pitch: 0.2-0.29 mm between their own pads), which get a 0.15 mm footprint clearance
    r.update(min_clearance=0.15, min_track_width=0.2,
             min_copper_edge_clearance=rules["edge"], min_via_diameter=rules["via_d"],
             min_through_hole_diameter=rules["via_drill"], min_hole_clearance=0.3, min_hole_to_hole=0.5,
             min_via_annular_width=0.2, min_resolved_spokes=1)
    with open(pro_path, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2)


def write_lib_tables(folder):
    rel = os.path.relpath(os.path.join(HW, "lib"), folder)
    with open(os.path.join(folder, "sym-lib-table"), "w") as f:
        f.write(f'(sym_lib_table\n  (version 7)\n  (lib (name "teamc")(type "KiCad")(uri "${{KIPRJMOD}}/{rel}/teamc.kicad_sym")'
                f'(options "")(descr "Team C project symbols"))\n)\n')
    with open(os.path.join(folder, "fp-lib-table"), "w") as f:
        f.write(f'(fp_lib_table\n  (version 7)\n  (lib (name "teamc")(type "KiCad")(uri "${{KIPRJMOD}}/{rel}/teamc.pretty")'
                f'(options "")(descr "Team C project footprints"))\n)\n')


def run(*cmd):
    out = subprocess.run(cmd, capture_output=True, text=True)
    text = "\n".join(l for l in (out.stdout + out.stderr).splitlines() if "assert" not in l)
    if out.returncode:
        raise SystemExit(f"{' '.join(cmd)} failed:\n{text}")
    return text


def v(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def fp(board, ref):
    for f in board.GetFootprints():
        if f.GetReference() == ref:
            return f
    raise KeyError(ref)


def pad(board, ref, num):
    for p in fp(board, ref).Pads():
        if p.GetNumber() == str(num):
            return p
    raise KeyError(f"{ref}.{num}")


def pad_xy(board, ref, num):
    p = pad(board, ref, num).GetPosition()
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def place(board, ref, x, y, rot=0, back=False):
    f = fp(board, ref)
    if back != (f.GetLayer() == pcbnew.B_Cu):
        f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(rot)
    f.SetPosition(v(x, y))
    return f


def find_net(board, net):
    """A net by its schematic name: global ("VCC"), root-local ("/CE") or sheet-local ("/power/SW_NODE")."""
    for name in (net, "/" + net):
        ni = board.FindNet(name)
        if ni is not None:
            return ni
    raise KeyError(net)


def track(board, pts, width, net, layer=pcbnew.F_Cu):
    """A polyline of tracks; pts are (x, y) mm or ("ref", pad) tuples."""
    ni = find_net(board, net)
    xy = [pad_xy(board, p[0], p[1]) if isinstance(p[0], str) else p for p in pts]
    for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
        if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(v(x1, y1))
        t.SetEnd(v(x2, y2))
        t.SetWidth(MM(width))
        t.SetLayer(layer)
        t.SetNet(ni)
        board.Add(t)


def via(board, x, y, net, d=0.8, drill=0.4):
    vi = pcbnew.PCB_VIA(board)
    vi.SetPosition(v(x, y))
    vi.SetWidth(MM(d))
    vi.SetDrill(MM(drill))
    vi.SetNet(find_net(board, net))
    board.Add(vi)


def zone(board, net, layer, poly, clearance=0.4, min_width=0.3, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(find_net(board, net))
    z.SetZoneName(name or f"{net}_{board.GetLayerName(layer)}")
    z.SetLocalClearance(MM(clearance))
    z.SetMinThickness(MM(min_width))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.4))
    z.SetThermalReliefSpokeWidth(MM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    for x, y in poly:
        o.Append(MM(x), MM(y))
    board.Add(z)
    return z


def fill_zones(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def outline_rect(board, x1, y1, x2, y2, r=1.0):
    """Rounded rectangle on Edge.Cuts."""
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(v(*a))
        s.SetEnd(v(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    def arc(c, start, angle):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(v(*c))
        s.SetStart(v(*start))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T), True)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    seg((x1 + r, y1), (x2 - r, y1))
    seg((x2, y1 + r), (x2, y2 - r))
    seg((x2 - r, y2), (x1 + r, y2))
    seg((x1, y2 - r), (x1, y1 + r))
    arc((x2 - r, y1 + r), (x2 - r, y1), 90)
    arc((x2 - r, y2 - r), (x2, y2 - r), 90)
    arc((x1 + r, y2 - r), (x1 + r, y2), 90)
    arc((x1 + r, y1 + r), (x1, y1 + r), 90)


def text(board, s, x, y, layer=pcbnew.F_SilkS, size=1.0, rot=0, thick=0.15, mirror=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(v(x, y))
    t.SetLayer(layer)
    t.SetTextSize(v(size, size))
    t.SetTextThickness(MM(thick))
    t.SetTextAngleDegrees(rot)
    if mirror if mirror is not None else layer in (pcbnew.B_SilkS, pcbnew.B_Cu):
        t.SetMirrored(True)
    board.Add(t)
    return t


def drc(pcb_path, report):
    out = run("kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-all", "-o", report, pcb_path)
    return out
