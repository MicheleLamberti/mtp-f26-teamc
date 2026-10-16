"""Cross-check usb_msc (FatFs) against a second FAT implementation (pyfatfs).

pyfatfs formats a stick image and writes the input file (plus decoys); build/test_usb --image loads it
with our code, writes RX.TXT and NM_LOG.TXT back; pyfatfs then reads both and compares byte for byte.
Covers FAT16 and FAT32 (pyfatfs cannot make exFAT; test_usb covers exFAT against FatFs's own mkfs).

    pip install pyfatfs "setuptools<81"
    python3 tools/fat_xcheck.py build/test_usb build
"""

import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from pyfatfs.PyFat import PyFat  # noqa: E402
from pyfatfs.PyFatFS import PyFatFS  # noqa: E402

tool, build = sys.argv[1], Path(sys.argv[2])
content = "".join(f"{i:05d} línea de prueba, señal y año {i * 7919 % 10007:05d}\r\n" for i in range(9000)).encode()
fails = 0
for label, fat_type, size in (("FAT16", PyFat.FAT_TYPE_FAT16, 32 << 20), ("FAT32", PyFat.FAT_TYPE_FAT32, 64 << 20)):
    img, out = build / f"xcheck_{label}.img", build / f"xcheck_{label}_out.img"
    img.write_bytes(b"\0" * size)
    pf = PyFat()
    pf.mkfs(str(img), fat_type, size=size)
    pf.close()
    fs = PyFatFS(str(img))
    fs.writebytes("/Fichero MTP F26.txt", content)
    fs.writebytes("/readme.txt", b"short")
    fs.writebytes("/._Fichero MTP F26.txt", content[:4096])
    fs.close()
    run = subprocess.run([tool, "--image", str(img), str(out)], capture_output=True, text=True)
    print(f"{label}: {run.stdout.strip()}")
    ok = run.returncode == 0
    if ok:
        fs = PyFatFS(str(out))
        rx, log = fs.readbytes("/RX.TXT"), fs.readbytes("/NM_LOG.TXT").decode()
        orig = fs.readbytes("/Fichero MTP F26.txt")
        fs.close()
        ok = rx == content and orig == content and "Fichero MTP F26.txt" in log and f"{len(content)}" in log
    print(f"  pyfatfs reads RX.TXT back {'identical' if ok else 'DIFFERENT'} ({len(content)} bytes)")
    fails += not ok
print("ALL PASSED" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
