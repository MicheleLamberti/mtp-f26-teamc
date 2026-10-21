#!/usr/bin/env python3
"""Download the stock KiCad 3D models a board references into a local cache (hw/.3dmodels/).

KiCad's 3D library (kicad-packages3D) is not installed on this machine, so renders show bare pads. This script reads
every `(model "${KICAD10_3DMODEL_DIR}/<lib>.3dshapes/<name>.<ext>"` in the given boards / footprint files and fetches
the missing ones from the official repository (raw files): first the tag of the installed KiCad (e.g. 10.0.6), then
the 10.0 branch, then master. A missing .step falls back to the .wrl of the same name (and vice versa).

    python3 hw/scripts/fetch_3d.py hw/teamc-carrier/teamc-carrier.kicad_pcb hw/sp4-breakout/sp4-breakout.kicad_pcb
    KICAD10_3DMODEL_DIR=hw/.3dmodels kicad-cli pcb render ...

Idempotent: files already in the cache are skipped. Exit code 1 if any model could not be resolved.
"""
import argparse
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.normpath(os.path.join(HERE, "..", ".3dmodels"))
REPO = "https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/{ref}/{path}"
TEAMC_3D = "${KIPRJMOD}/../lib/teamc.3dshapes/"
# Stock footprints whose model kicad-packages3D does not ship (checked at tag 10.0.6, 21-Oct-26): the closest stock
# model, or a stand-in from hw/lib/teamc.3dshapes (gen_3d.py). render_board.py rewrites these refs.
SUBSTITUTES = {
    "Connector_JST.3dshapes/JST_VH_B2P-VH_1x02_P3.96mm_Vertical.step":
        TEAMC_3D + "JST_VH_B2P-VH_1x02_P3.96mm_Vertical.wrl",               # no JST VH models upstream at all
    "Inductor_SMD.3dshapes/L_Coilcraft_LPS4018.step":
        "${KICAD10_3DMODEL_DIR}/Inductor_SMD.3dshapes/L_Bourns-SRN4018.step",  # same 4 x 4 x 1.8 mm class
    "Package_DFN_QFN.3dshapes/Texas_RWU0007A_VQFN-7_2x2mm_P0.5mm.step":
        "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/DFN-8_2x2mm_P0.5mm.step",  # 2 x 2 mm body, leads left/right
    "Package_SON.3dshapes/Texas_DRC0010J.step":
        "${KICAD10_3DMODEL_DIR}/Package_SON.3dshapes/VSON-10-1EP_3x3mm_P0.5mm_EP1.65x2.4mm.step",  # same package
}
STOCK = "${KICAD10_3DMODEL_DIR}/"
MODEL_RE = re.compile(r'\(model\s+"\$\{KICAD\d*_3DMODEL_DIR\}/([^"]+)"')


def kicad_refs():
    refs = []
    try:
        v = subprocess.run(["kicad-cli", "version"], capture_output=True, text=True, timeout=30).stdout.strip()
        if re.fullmatch(r"\d+\.\d+\.\d+", v):
            refs.append(v)
            refs.append(".".join(v.split(".")[:2]))
    except (OSError, subprocess.SubprocessError):
        pass
    refs.append("master")
    return list(dict.fromkeys(refs))


def model_paths(files):
    out = []
    for fn in files:
        with open(fn, encoding="utf-8") as fh:
            out += MODEL_RE.findall(fh.read())
    return sorted(set(out))


def download(path, refs):
    """Return (ref, bytes) for the first ref that has `path`, else None."""
    for ref in refs:
        try:
            with urllib.request.urlopen(REPO.format(ref=ref, path=urllib.request.quote(path)), timeout=60) as r:
                data = r.read()
            if data:
                return ref, data
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"  ! {path} @ {ref}: HTTP {e.code}", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  ! {path} @ {ref}: {e}", file=sys.stderr)
    return None


def fetch(files, cache=CACHE, verbose=True):
    """Fetch every model referenced by `files` into `cache`. Returns the list of unresolved model paths."""
    refs = kicad_refs()
    failed = []
    paths = model_paths(files)
    for p in list(paths):
        if p in SUBSTITUTES:
            sub = SUBSTITUTES[p]
            if verbose:
                print(f"subst   {p} -> {sub}")
            paths.remove(p)
            if sub.startswith(STOCK) and sub[len(STOCK):] not in paths:
                paths.append(sub[len(STOCK):])
    for p in paths:
        stem, ext = os.path.splitext(p)
        alts = [p] + [stem + e for e in (".step", ".stp", ".wrl") if stem + e != p]
        have = next((a for a in alts if os.path.isfile(os.path.join(cache, a))), None)
        if have:
            if verbose:
                print(f"skip    {have}" + ("" if have == p else f"  (for {p})"))
            continue
        got = None
        for a in alts:
            got = download(a, refs)
            if got:
                dst = os.path.join(cache, a)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst + ".part", "wb") as fh:
                    fh.write(got[1])
                os.replace(dst + ".part", dst)
                if verbose:
                    print(f"fetched {a}  ({len(got[1]) // 1024} kB, {got[0]})" + ("" if a == p else f"  (for {p})"))
                break
        if not got:
            print(f"FAILED  {p}")
            failed.append(p)
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help=".kicad_pcb or .kicad_mod files")
    ap.add_argument("--cache", default=CACHE, help=f"cache directory (default {CACHE})")
    a = ap.parse_args()
    failed = fetch(a.files, a.cache)
    print(f"{len(failed)} unresolved" if failed else "all models resolved", f"(cache {a.cache})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
