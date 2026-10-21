#!/usr/bin/env python3
"""3D renders of a Team C board with component bodies (kicad-cli pcb render, raytraced).

    python3 hw/scripts/render_board.py hw/teamc-carrier/teamc-carrier.kicad_pcb --with-pi
    python3 hw/scripts/render_board.py hw/sp4-breakout/sp4-breakout.kicad_pcb

1. fetch_3d.py: stock models into hw/.3dmodels/ (KiCad's 3D library is not installed here).
2. A temp copy of the board in which the teamc footprints get their models (teamc:E01-ML01SP4, teamc:MAX17048_*,
   teamc:PinSocket_*), stock refs that kicad-packages3D lacks get their substitute (fetch_3d.SUBSTITUTES), and every
   ${KIPRJMOD} / ${KICAD10_3DMODEL_DIR} is made absolute. --with-pi adds the simplified Pi 3 A+ under the HAT,
   lined up on J1 pin 1, its top copper 11 mm below the HAT's bottom (8.5 mm socket on the Pi's 2.5 mm header body).
3. Renders <board>_render_top.png, _bottom.png, _iso.png (+ _stack.png with --with-pi) into --out (default: the
   board's folder).

--apply-models writes the corrected model refs (${KIPRJMOD}/${KICAD10_3DMODEL_DIR} form, no Pi) into the board
file itself, then renders as usual.
"""
import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_3d  # noqa: E402

HW = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LIB3D = os.path.join(HW, "lib", "teamc.3dshapes")
SOCKET = fetch_3d.STOCK + "Connector_PinSocket_2.54mm.3dshapes/PinSocket_2x20_P2.54mm_Vertical.step"
# lib id prefix -> model ref
TEAMC_MODELS = {
    "teamc:E01-ML01SP4": fetch_3d.TEAMC_3D + "E01-ML01SP4.wrl",
    "teamc:MAX17048_": fetch_3d.TEAMC_3D + "MAX17048_TDFN-8-1EP_2x2mm.wrl",
    "teamc:PinSocket_2x20": SOCKET,
}
PI_MODEL = os.path.join(LIB3D, "RPi3_Aplus_simplified.wrl")
STACK_MM = 11.0  # HAT bottom -> Pi top copper

VIEWS = {  # name: (kicad-cli args, floor + shadows)
    "top": (["--side", "top"], False),
    "bottom": (["--side", "bottom"], False),
    "iso": (["--side", "top", "--perspective", "--rotate", "-50,0,30", "--zoom", "0.8"], True),
}
STACK_VIEW = ["--side", "top", "--perspective", "--rotate", "-68,0,-150", "--zoom", "0.8"]


def want_model(lib_id):
    return next((m for k, m in TEAMC_MODELS.items() if lib_id.startswith(k)), None)


def fix_models(board, absolute, board_dir):
    """Set the teamc models and stock substitutes on every footprint. absolute: expand the path variables."""
    changed = []

    def expand(p):
        if absolute:
            p = p.replace(fetch_3d.TEAMC_3D, LIB3D + "/").replace("${KIPRJMOD}", board_dir).replace(fetch_3d.STOCK, fetch_3d.CACHE + "/")
        return p

    for fp in board.GetFootprints():
        lib_id = f"{fp.GetFPID().GetLibNickname()}:{fp.GetFPID().GetLibItemName()}"
        models = fp.Models()
        want = want_model(lib_id)
        if want:
            if len(models) == 0:
                m = pcbnew.FP_3DMODEL()
                m.m_Filename = want
                models.push_back(m)
                changed.append(f"{fp.GetReference()}: + {want}")
            elif models[0].m_Filename != want:
                changed.append(f"{fp.GetReference()}: {models[0].m_Filename} -> {want}")
                models[0].m_Filename = want
        for i in range(len(models)):  # index access: iterating the SWIG vector yields copies
            f = models[i].m_Filename
            if f.startswith(fetch_3d.STOCK) and f[len(fetch_3d.STOCK):] in fetch_3d.SUBSTITUTES:
                f = fetch_3d.SUBSTITUTES[f[len(fetch_3d.STOCK):]]
                changed.append(f"{fp.GetReference()}: {models[i].m_Filename} -> {f}")
            models[i].m_Filename = expand(f)
    return changed


def add_pi(board):
    """A pad-less front footprint carrying the Pi model, at J1 pad 1, turned to follow pad 1 -> pad 39."""
    j1 = next((f for f in board.GetFootprints() if str(f.GetFPID().GetLibItemName()).startswith("PinSocket_2x20")), None)
    if j1 is None:
        sys.exit("--with-pi: no 2x20 socket footprint on this board")
    pads = {p.GetNumber(): p.GetPosition() for p in j1.Pads()}
    p1, p39 = pads["1"], pads["39"]
    ang = math.degrees(math.atan2(-(p39.y - p1.y), p39.x - p1.x))
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("PI3A")
    fp.SetValue("Raspberry Pi 3 A+ (context)")
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
    board.Add(fp)
    fp.SetPosition(p1)
    fp.SetOrientationDegrees(ang)
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = PI_MODEL
    thick = pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness())
    m.m_Offset = pcbnew.VECTOR3D(0, 0, -(thick + STACK_MM))
    fp.Models().push_back(m)


def autocrop(png, width, no_shadow, margin=0.04):
    """Crop the transparent border, keep a margin, scale down to `width` px. no_shadow: drop the faint black floor
    shadow that --quality high draws even without --floor (flat top/bottom views)."""
    try:
        from PIL import Image
    except ImportError:
        return
    im = Image.open(png)
    if no_shadow and im.mode == "RGBA":
        px = [(0, 0, 0, 0) if a < 110 and max(r, g, b) < 12 else (r, g, b, a) for r, g, b, a in im.getdata()]
        im.putdata(px)
    bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox() if im.mode == "RGBA" else None
    if not bb:
        return
    m = int(margin * max(bb[2] - bb[0], bb[3] - bb[1]))
    im = im.crop((max(bb[0] - m, 0), max(bb[1] - m, 0), min(bb[2] + m, im.width), min(bb[3] + m, im.height)))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(png)


def render(pcb, out_png, view, width, height, floor):
    env = dict(os.environ, KICAD10_3DMODEL_DIR=fetch_3d.CACHE)
    w, h = int(width * 1.25), int(height * 1.25)  # rendered larger, then cropped to the board and scaled to `width`
    cmd = ["kicad-cli", "pcb", "render", "--quality", "high", "--width", str(w), "--height", str(h),
           "--background", "transparent", "--preset", "follow_pcb_editor", *(["--floor"] if floor else []), *view, "-o", out_png, pcb]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(out_png):
        sys.exit(f"render failed ({' '.join(cmd)}):\n{r.stdout}\n{r.stderr}")
    autocrop(out_png, width, no_shadow=not floor)
    print("wrote", out_png)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--with-pi", action="store_true", help="also render the HAT on a Raspberry Pi 3 A+ (_stack.png)")
    ap.add_argument("--out", help="output folder (default: the board's folder)")
    ap.add_argument("--apply-models", action="store_true", help="write the corrected model refs into the board file")
    ap.add_argument("--views", default="top,bottom,iso", help="comma list of top,bottom,iso (default all)")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=1200)
    ap.add_argument("--no-floor", action="store_true", help="no floor/shadows")
    a = ap.parse_args()

    board_path = os.path.abspath(a.board)
    board_dir = os.path.dirname(board_path)
    stem = os.path.splitext(os.path.basename(board_path))[0]
    out = os.path.abspath(a.out or board_dir)
    os.makedirs(out, exist_ok=True)

    libmods = [os.path.join(HW, "lib", "teamc.pretty", f) for f in os.listdir(os.path.join(HW, "lib", "teamc.pretty"))
               if f.endswith(".kicad_mod")]
    failed = fetch_3d.fetch([board_path] + libmods, verbose=False)
    if failed:
        print("warning: unresolved models:", ", ".join(failed), file=sys.stderr)
    if not os.path.isfile(PI_MODEL):
        sys.exit(f"{PI_MODEL} missing: run hw/scripts/teamc_lib/gen_3d.py")

    if a.apply_models:
        b = pcbnew.LoadBoard(board_path)
        ch = fix_models(b, absolute=False, board_dir=board_dir)
        if ch:
            b.Save(board_path)
        print(f"--apply-models: {len(ch)} change(s) in {board_path}", *("  " + c for c in ch), sep="\n")

    tmp = tempfile.mkdtemp(prefix="render3d_")
    try:
        for ext in (".kicad_pro",):
            if os.path.isfile(os.path.join(board_dir, stem + ext)):
                shutil.copy(os.path.join(board_dir, stem + ext), tmp)
        b = pcbnew.LoadBoard(board_path)
        fix_models(b, absolute=True, board_dir=board_dir)
        tpcb = os.path.join(tmp, stem + ".kicad_pcb")
        b.Save(tpcb)
        for v in [v.strip() for v in a.views.split(",") if v.strip()]:
            args, floor = VIEWS[v]
            render(tpcb, os.path.join(out, f"{stem}_render_{v}.png"), args, a.width, a.height,
                   floor and not a.no_floor)
        if a.with_pi:
            add_pi(b)
            spcb = os.path.join(tmp, stem + "_stack.kicad_pcb")
            b.Save(spcb)
            render(spcb, os.path.join(out, f"{stem}_render_stack.png"), STACK_VIEW, a.width, a.height,
                   not a.no_floor)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
