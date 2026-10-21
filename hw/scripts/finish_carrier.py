"""Last routing step for the carrier (after autoroute_carrier.py): the few connections Freerouting leaves open.

    python3 hw/scripts/finish_carrier.py

They sit where the fixed power copper boxes a pin in, so each gets a fix by hand here, then the grid router:
  - U6 (MAX17048): its GND pins are tied to the exposed pad under the package (ep_ties), so pin 6's own GND stub
    goes, and FG_ALRT (pin 5) leaves east between the VBAT Kelvin branch and the 1 mm VBAT track, to a via;
  - the buck-boost option (DNP) is rerouted as a block: L2 turned 90 degrees as in TI's TPS63001 layout (one pad
    faces L2/pin 2, the other L1/pin 4; before, both pads were on one line and the far one could not reach its
    pin), U5's GND pin stubs go (pins tied to the EP), then VINA, VOUT, SW1, SW2; pin 10 (VOUT/FB) leaves north
    over the package on a fixed stub, so that VINA (pin 8) gets the only lane to the north-east;
  - C15 (VOUT cap, DNP) turns 180 degrees so VOUT reaches it without walling its GND pad in;
  - 3V3_RADIO's via between R16's pads moves onto R16 pin 2's edge, out of U5 pin 10's way, and R15 pin 1's
    1 mm VBAT_SW branch (it walls R16 pin 1 in) is ripped and re-fed last with an ordinary track;
  - ZVD_G, PWR_G, FG_ALRT and the buck-boost nets are then grid-routed (gridroute.py);
  - the GND pours are refilled and checked: islands joined by a via (or a short GND track where no via
    reaches the main ground), isolated GND pads get a via or a GND track.
Then DRC: kicad-cli pcb drc --schematic-parity hw/teamc-carrier/teamc-carrier.kicad_pcb
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402

import boardutil as bu  # noqa: E402
from autoroute_carrier import EP_TIES, ep_ties, link_islands, link_pads, stitch_fragments  # noqa: E402
from gridroute import Router  # noqa: E402
from place_carrier import PCB, X0, X1, Y0, Y1  # noqa: E402
from route_carrier import FINE_NETS, FINE_REFS, isolated_gnd_pads  # noqa: E402

BUCK_BOOST = ["/power/BB_VINA", "/power/BB_OUT", "/power/BB_SW1", "/power/BB_SW2"]   # routing order
# BB_OUT (VOUT of the DNP option) after a ground pass: routed early it took a bottom-layer detour that cut the
# bottom pour under the radio LDO (U4) off; R15 pin 1's VBAT_SW feed (ripped to open R16 pin 1's lane) comes back
ORDER = ["/power/BB_VINA", "/power/BB_SW1", "/power/BB_SW2", "/power/ZVD_G", "/power/PWR_G", "FG_ALRT", "GROUND",
         "VBAT_SW", "ANCHOR", "/power/BB_OUT", "GROUND"]   # of 7 orders tried on 21-Oct, 3 reached 0 unconnected
# the buck-boost caps' GND pads: BB_OUT, routed last, would otherwise wall C15 pin 2 in (21-Oct test)
ANCHOR_PADS = [("C13", "2"), ("C14", "2"), ("C15", "2"), ("C16", "2")]
REFEED = ("VBAT_SW", "R15", "1")   # its 1 mm branch walls R16 pin 1 (BB_OUT) in from the south; rerouted last
GND_PIN_STUBS = [("U6", "6"), ("U5", "3"), ("U5", "9")]   # redundant once the pins are tied to the exposed pad
RADIO_VIA_OLD, RADIO_VIA_NEW = (141.45, 66.65), (141.8, 65.55)
L2_AT = (133.5, 67.3)    # L2 centre after the turn (was 133.5, 67.8): the lower pad clears VBAT_SW's track


def router(board):
    return Router(board, X0, Y0, X1, Y1, grid=0.05, margin=0.03, clearance=bu.FAB_RULES["clearance"],
                  fine_refs=FINE_REFS, fine_nets=FINE_NETS + ["/power/ZVD_G", "/power/PWR_G"])


def delete_tracks(board, pred):
    """Delete the tracks/vias matching pred (a handful: pcbnew's SWIG API misbehaves after many deletions)."""
    doomed = [t for t in board.GetTracks() if pred(t)]
    for t in doomed:
        board.Delete(t)
    return len(doomed)


def dedupe_vias(board, min_c2c=0.9):
    """GND vias closer than the hole-to-hole rule allows (0.4 mm drill + 0.5 mm): keep the one with a track or in
    a pad."""
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    ends = set()
    for t in board.GetTracks():
        if t.GetNetname() == "GND" and t.GetClass() != "PCB_VIA":
            ends |= {(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)}
    pads = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() == "GND"]
    ends |= {(v.GetPosition().x, v.GetPosition().y) for v in vias if any(p.HitTest(v.GetPosition()) for p in pads)}
    lim = pcbnew.FromMM(min_c2c)
    pos = [(v.GetPosition().x, v.GetPosition().y) for v in vias]   # by position: SWIG wrappers are not stable
    doomed = set()
    for i, a in enumerate(pos):
        for b in pos[i + 1:]:
            if a in doomed or b in doomed:
                continue
            if (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < lim ** 2:
                doomed.add(b if a in ends else a)
    return delete_tracks(board, lambda t: t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND" and
                         (t.GetPosition().x, t.GetPosition().y) in doomed) if doomed else 0


def rip_branch(board, ref, num):
    """Delete the track branch that runs from a pad back to the first junction (a via, a pad, or a point where
    three or more segments meet); returns the segments deleted."""
    pad = bu.pad(board, ref, num)
    net = pad.GetNetname()
    segs = [t for t in board.GetTracks() if t.GetNetname() == net and t.GetClass() != "PCB_VIA"]
    vias = {(t.GetPosition().x, t.GetPosition().y) for t in board.GetTracks()
            if t.GetNetname() == net and t.GetClass() == "PCB_VIA"}
    pads = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() == net]
    key = lambda v: (v.x, v.y)  # noqa: E731
    # a track touches a pad when its end is within half its width of the pad (round ends)
    hit = lambda q, s, e: q.HitTest(e, s.GetWidth() // 2)  # noqa: E731
    doomed, frontier = set(), [s for s in segs if hit(pad, s, s.GetStart()) or hit(pad, s, s.GetEnd())]
    while frontier:
        s = frontier.pop()
        k = (key(s.GetStart()), key(s.GetEnd()))
        if k in doomed:
            continue
        doomed.add(k)
        for e in (s.GetStart(), s.GetEnd()):
            if hit(pad, s, e) or key(e) in vias or any(hit(q, s, e) for q in pads if q is not pad):
                continue
            touching = [t for t in segs if key(e) in (key(t.GetStart()), key(t.GetEnd()))
                        and (key(t.GetStart()), key(t.GetEnd())) not in doomed]
            if len(touching) == 1:
                frontier.append(touching[0])
    return delete_tracks(board, lambda t: t.GetNetname() == net and t.GetClass() != "PCB_VIA" and
                         (key(t.GetStart()), key(t.GetEnd())) in doomed)


def drop_dangling_stubs(board, pins):
    """Delete escape stubs that start at one of these pads and end nowhere (no other track, via or pad at their far
    end); returns how many went."""
    gone = 0
    for ref, num in pins:
        pad = bu.pad(board, ref, num)
        c = pad.GetPosition()
        net = pad.GetNetname()
        items = [t for t in board.GetTracks() if t.GetNetname() == net]
        pads = [q for f in board.GetFootprints() for q in f.Pads() if q.GetNetname() == net]
        for t in items:
            if t.GetClass() == "PCB_VIA" or c not in (t.GetStart(), t.GetEnd()):
                continue
            far = t.GetEnd() if t.GetStart() == c else t.GetStart()
            shared = any(o is not t and o.GetClass() != "PCB_VIA" and far in (o.GetStart(), o.GetEnd()) for o in items)
            on_via = any(o.GetClass() == "PCB_VIA" and (o.GetPosition() - far).EuclideanNorm() <= o.GetWidth(pcbnew.F_Cu) // 2
                         for o in items)
            on_pad = any(q.HitTest(far, t.GetWidth() // 2) for q in pads if q.m_Uuid.AsString() != pad.m_Uuid.AsString())
            if not (shared or on_via or on_pad):
                s0, e0 = t.GetStart(), t.GetEnd()
                gone += delete_tracks(board, lambda u, s0=s0, e0=e0: u.GetNetname() == net and
                                      u.GetClass() != "PCB_VIA" and u.GetStart() == s0 and u.GetEnd() == e0)
                items = [u for u in board.GetTracks() if u.GetNetname() == net]
    return gone


def copper_cells(r, item):
    """Grid cells (layer, x, y) of a pad, a via or along a track."""
    if isinstance(item, pcbnew.PAD):
        return r.pad_cells(item)
    if item.GetClass() == "PCB_VIA":
        x, y = (int(round(c)) for c in r._px(pcbnew.ToMM(item.GetPosition().x), pcbnew.ToMM(item.GetPosition().y)))
        return [(0, x, y), (1, x, y)]
    li = 0 if item.GetLayer() == pcbnew.F_Cu else 1
    (x1, y1), (x2, y2) = (r._px(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)) for p in (item.GetStart(), item.GetEnd()))
    n = max(1, int(max(abs(x2 - x1), abs(y2 - y1))))
    return [(li, int(round(x1 + (x2 - x1) * k / n)), int(round(y1 + (y2 - y1) * k / n))) for k in range(n + 1)]


def complete_net(board, net, widths=(0.25, 0.2)):
    """Connect what is still apart on a net: the clusters come from KiCad's connectivity (pads, tracks, vias,
    copper areas); each smaller cluster is routed (A*, vias allowed) to the copper of the main one. Unlike
    gridroute's route_net it starts from the copper that is already there. Returns the clusters left apart."""
    for _ in range(12):
        board.BuildConnectivity()
        conn = board.GetConnectivity()
        pads = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() == net]
        tracks = [t for t in board.GetTracks() if t.GetNetname() == net]
        items = {i.m_Uuid.AsString(): i for i in pads + tracks}
        clusters, seen = [], set()
        for p in pads:
            u = p.m_Uuid.AsString()
            if u in seen:
                continue
            c = {i.m_Uuid.AsString() for i in conn.GetConnectedItems(p)} | {u}
            seen |= c
            clusters.append(c)
        if len(clusters) < 2:
            return 0
        clusters.sort(key=len, reverse=True)
        main, other = clusters[0], clusters[-1]
        r = router(board)
        # sorted: set order of strings changes from run to run (hash seed), and with it the A* target
        tgt = [c for u in sorted(main) if u in items for c in copper_cells(r, items[u])]
        if any(z.GetNetname() == net for z in board.Zones() if not z.GetIsRuleArea()):
            tgt += r.zone_cells(net)
        src = [c for u in sorted(other) if u in items for c in copper_cells(r, items[u])]
        tx, ty = tgt[len(tgt) // 2][1:]
        done = False
        for w in widths:
            path = r.astar(src, tgt, r.obstacles(net, w / 2), r.via_block(net), tx, ty, limit=4_000_000)
            if path:
                r.commit(path, net, w)
                done = True
                break
        if not done:
            return len(clusters) - 1
    return 0


def route(board, nets):
    for net in nets:
        left = complete_net(board, net)
        print(f"{net:18s}", "ok" if not left else f"FAILED ({left} pieces left apart)")
    bu.fill_zones(board)


def anchor(board, pads, near=1.5):
    """A GND via next to each of these GND pads that has none within `near` mm, before a net that could wall it
    in is routed; returns the pads anchored."""
    vias = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    done = []
    for ref, num in pads:
        p = bu.pad(board, ref, num)
        if any((v - p.GetPosition()).EuclideanNorm() <= pcbnew.FromMM(near) for v in vias):
            continue
        if router(board).via_to(p, "GND", reach=3.0):
            done.append(f"{ref}.{num}")
            vias = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    bu.fill_zones(board)
    return ", ".join(done)


def ground(board):
    """Join the GND pour islands to the main ground: a via where one reaches, else a GND track."""
    for _ in range(8):
        d = dedupe_vias(board)
        if d:
            bu.fill_zones(board)
            print("GND vias too close to another, removed:", d)
        n = stitch_fragments(board)
        bu.fill_zones(board)
        m = link_islands(board) if not n else 0
        if m:
            bu.fill_zones(board)
        print(f"GND pour islands joined: {n} by a via, {m} by a track")
        if not n and not m:
            break
    # GND pads no pour reaches (boxed in by other nets): a via next to the pad, else a GND track to the pours
    board.Save(PCB)
    lonely = isolated_gnd_pads(board)
    if lonely:
        r = router(board)
        names = [f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in lonely]
        placed = [nm for p, nm in zip(lonely, names) if r.via_to(p, "GND", reach=5.0)]
        bu.fill_zones(board)
        rest = [p for p, nm in zip(lonely, names) if nm not in placed]
        linked = [f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in link_pads(board, rest)]
        bu.fill_zones(board)
        print("isolated GND pads: via", ", ".join(placed) or "none", "| track", ", ".join(linked) or "none",
              "| left", ", ".join(nm for nm in names if nm not in placed + linked) or "none")


def drop_dangling(board, rounds=4):
    """Delete what KiCad's DRC reports as dangling (escape stubs and vias the routes no longer use), until none."""
    import re
    gone = 0
    for _ in range(rounds):
        board.Save(PCB)
        rpt = os.path.join(os.path.dirname(PCB), "build", "drc_dangling.rpt")
        bu.run("kicad-cli", "pcb", "drc", "-o", rpt, PCB)
        found, kind = [], ""
        for line in open(rpt, encoding="utf-8"):
            if line.startswith("["):
                kind = line.split("]")[0][1:]
            elif kind in ("track_dangling", "via_dangling"):
                m = re.search(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (Track|Via) \[([^\]]*)\]"
                              r"(?: on (\S+), length ([\d.]+) mm)?", line)
                if m:
                    found.append(m.groups())
        if not found:
            break
        for x, y, what, net, _layer, length in found:
            print(f"  dangling {what} {net} at ({x}, {y})" + (f" {length} mm" if length else ""))
            at = bu.v(float(x), float(y))
            if what == "Via":
                gone += delete_tracks(board, lambda t, at=at, net=net: t.GetClass() == "PCB_VIA" and
                                      t.GetNetname() == net and (t.GetPosition() - at).EuclideanNorm() < 1000)
            else:
                ln = pcbnew.FromMM(float(length))
                gone += delete_tracks(board, lambda t, at=at, net=net, ln=ln: t.GetClass() != "PCB_VIA" and
                                      t.GetNetname() == net and abs(t.GetLength() - ln) < 2000 and
                                      min((t.GetStart() - at).EuclideanNorm(), (t.GetEnd() - at).EuclideanNorm(),
                                          (t.GetCenter() - at).EuclideanNorm()) < 2000)
        bu.fill_zones(board)
    return gone


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="east", choices=["east", "north"], help="how U5 pin 10 (VOUT/FB) leaves")
    ap.add_argument("--order", default=",".join(ORDER), help="routing order; GROUND = a ground pass")
    a = ap.parse_args()
    variant, order = a.variant, a.order.split(",")
    board = pcbnew.LoadBoard(PCB)
    # GND pin stubs that wall in their neighbours (U6 pin 5, U5 pin 8): the tracks leaving the pad outwards
    # (away from the exposed pad); the pins are tied to the EP instead
    for ref, num in GND_PIN_STUBS:
        pc = bu.pad(board, ref, num).GetPosition()
        ep = bu.pad(board, ref, EP_TIES[ref][0]).GetPosition()
        out = lambda t, pc=pc, ep=ep: (t.GetEnd() if t.GetStart() == pc else t.GetStart())  # noqa: E731
        n = delete_tracks(board, lambda t: t.GetNetname() == "GND" and t.GetClass() != "PCB_VIA" and
                          pc in (t.GetStart(), t.GetEnd()) and
                          (out(t) - ep).EuclideanNorm() > (pc - ep).EuclideanNorm())
        print(f"{ref} pin {num}: GND stub removed ({n})")
    print("GND pins tied to exposed pads:", ep_ties(board))
    # FG_ALRT out of U6 pin 5: east, then up to a via clear of the VBAT tracks
    x5, y5 = bu.pad_xy(board, "U6", 5)
    if not any(t.GetNetname() == "FG_ALRT" and t.GetStart() == bu.v(x5, y5) for t in board.GetTracks()):
        bu.track(board, [(x5, y5), (x5 + 0.8, y5), (x5 + 1.41, y5 - 0.6)], 0.2, "FG_ALRT")
        bu.via(board, x5 + 1.41, y5 - 0.6, "FG_ALRT")
    # 3V3_RADIO's via between R16's pads walls in U5 pin 10 (BB_OUT): it moves onto the edge of R16 pin 2 (R16 is
    # DNP, a via there is harmless), with a bottom-layer link to where it was
    old = bu.v(*RADIO_VIA_OLD)
    if delete_tracks(board, lambda t: t.GetNetname() == "3V3_RADIO" and (
            (t.GetClass() == "PCB_VIA" and t.GetPosition() == old) or
            (t.GetClass() != "PCB_VIA" and t.GetLayer() == pcbnew.F_Cu and old in (t.GetStart(), t.GetEnd())))):
        bu.via(board, *RADIO_VIA_NEW, "3V3_RADIO")
        bu.track(board, [RADIO_VIA_NEW, RADIO_VIA_OLD], 0.6, "3V3_RADIO", layer=pcbnew.B_Cu)
        print("3V3_RADIO via moved off U5 pin 10's way")
    # the buck-boost block: L2 turned 90 degrees, all its tracks redone by the grid router
    if round(bu.fp(board, "L2").GetOrientationDegrees()) % 180 == 0:
        bu.place(board, "L2", *L2_AT, rot=90)
    # C15 (VOUT cap, DNP) turned 180 degrees: its VOUT pad faces C14's, so VOUT no longer wraps round its GND pad
    c15 = bu.fp(board, "C15")
    if bu.pad_xy(board, "C15", 1)[1] > bu.pad_xy(board, "C15", 2)[1]:
        pos = c15.GetPosition()
        c15.SetOrientationDegrees(c15.GetOrientationDegrees() + 180)
        c15.SetPosition(pos)
    print("buck-boost tracks ripped up:", delete_tracks(board, lambda t: t.GetNetname() in BUCK_BOOST))
    print(f"{REFEED[1]}.{REFEED[2]} {REFEED[0]} branch ripped up:", rip_branch(board, REFEED[1], REFEED[2]))
    # U5 pins 6/7 (EN, PS/SYNC = VBAT_SW) are joined to each other and to the VBAT_SW via at pin 6; their old east
    # stubs end nowhere and leave pin 8 (VINA) no lane past R16
    print("U5 dangling stubs removed:", drop_dangling_stubs(board, [("U5", "7"), ("U5", "6")]))
    x10, y10 = bu.pad_xy(board, "U5", 10)
    if variant == "north":   # pin 10 leaves north over the package: VINA takes the lane north-east of the pins
        bu.track(board, [(x10, y10), (x10, y10 - 0.55)], 0.25, "/power/BB_OUT")   # longer reaches VBAT_SW
    else:                    # pin 10 straight east to R16 pin 1: VINA passes south of R16
        xr, yr = bu.pad_xy(board, "R16", 1)
        bu.track(board, [(x10, y10), (xr - 1.1, y10), (xr - 0.5, y10 + 0.6)], 0.25, "/power/BB_OUT")
    bu.fill_zones(board)
    for step in order:
        if step == "GROUND":
            ground(board)
        elif step == "ANCHOR":
            print("GND vias anchoring pads:", anchor(board, ANCHOR_PADS) or "none")
        else:
            route(board, [step])
    for _ in range(3):   # the clean-up can take a stub the ground leaned on: repair, then check again
        n = drop_dangling(board)
        print("dangling tracks/vias removed:", n)
        if not n:
            break
        ground(board)
    board.Save(PCB)


if __name__ == "__main__":
    main()
