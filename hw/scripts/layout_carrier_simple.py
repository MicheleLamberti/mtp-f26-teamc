"""Rebuild carrier rev C ("simple", UPC lab) from scratch: schematic, placement, routing, pour, DRC, fab files,
renders, BoM. Run it again after any change to the sheets or to the floorplan (e.g. once the box is measured:
edit W/H and the positions in place_carrier_simple.py first).

    python3 hw/scripts/layout_carrier_simple.py            # everything
    python3 hw/scripts/layout_carrier_simple.py --no-fab   # stop after the DRC

Steps (each script can also be run alone, in this order):
  1. build_carrier_simple.py   lab footprints + 3D models, sheets, ERC, netlist, board update (no wire links yet)
  2. place_carrier_simple.py   outline (slot, notch), every part at its position
  3. route_carrier_simple.py   hand-routed backbone + router for the rest; links.json
  4. finish_carrier_simple.py  GND pour, ground joins, wire links -> W parts, DRC with schematic parity
  5. fab_carrier_simple.py     gerbers, drill, 1:1 copper PDFs, assembly PDFs, wire-link list, zip; renders; BoM
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.normpath(os.path.join(HERE, "..", "teamc-carrier-simple"))


def run(*args):
    print("==", " ".join(os.path.basename(a) for a in args), flush=True)
    out = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    lines = [ln for ln in (out.stdout + out.stderr).splitlines() if "assert" not in ln and "Debug:" not in ln]
    print("\n".join(lines[-12:]), flush=True)
    if out.returncode:
        raise SystemExit(f"{args[0]} failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fab", action="store_true")
    a = ap.parse_args()
    links = os.path.join(DIR, "links.json")
    if os.path.exists(links):
        os.remove(links)
    run(os.path.join(HERE, "teamc_lib", "gen_3d_revc.py"))
    run(os.path.join(HERE, "build_carrier_simple.py"))
    run(os.path.join(HERE, "place_carrier_simple.py"))
    run(os.path.join(HERE, "route_carrier_simple.py"))
    run(os.path.join(HERE, "finish_carrier_simple.py"))
    if not a.no_fab:
        run(os.path.join(HERE, "fab_carrier_simple.py"))


if __name__ == "__main__":
    main()
