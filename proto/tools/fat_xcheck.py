"""Cross-check usb_msc (FatFs) against a second FAT implementation (pyfatfs) and real partition tables.

pyfatfs formats the volume and writes the input file (plus decoys); build/test_usb --image loads it with our
code and writes RX.TXT and NM_LOG.TXT back; pyfatfs then reads both and compares byte for byte. Layouts:
  - bare FAT16 / FAT32 volume (no partition table)
  - Windows / factory stick: MBR partition table (sfdisk), FAT32 partition at 1 MiB
  - macOS Disk Utility stick: GPT (sgdisk), EFI partition first, FAT32 "Microsoft basic data" partition second
The input file name is non-ASCII (UTF-8 names). pyfatfs cannot make exFAT; test_usb covers exFAT.

    pip install pyfatfs "setuptools<81";  needs sfdisk and sgdisk (util-linux, gdisk) for the partitioned cases
    python3 tools/fat_xcheck.py build/test_usb build
"""

import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from pyfatfs.PyFat import PyFat  # noqa: E402
from pyfatfs.PyFatFS import PyFatFS  # noqa: E402

tool, build = sys.argv[1], Path(sys.argv[2])
NAME = "Fichero señal € 文件.txt"
content = "".join(f"{i:05d} línea de prueba, señal y año {i * 7919 % 10007:05d}\r\n" for i in range(9000)).encode()
MB = 1 << 20


def format_volume(path: Path, fat_type, size: int) -> None:
    path.write_bytes(b"\0" * size)
    pf = PyFat()
    pf.mkfs(str(path), fat_type, size=size)
    pf.close()


def partitioned(img: Path, label: str, part_size: int) -> int:
    """Image with a partition table; returns the byte offset of the FAT32 data partition."""
    img.write_bytes(b"\0" * (part_size + 8 * MB))
    if label == "mbr":
        subprocess.run(["sfdisk", "-q", str(img)], input="label: dos\nstart=2048, type=c\n", text=True, check=True)
        start = 2048
    else:   # GPT the way macOS Disk Utility lays it out: EFI system partition, then the data partition
        subprocess.run(["sgdisk", "-o", "-n", "1:2048:+2M", "-t", "1:EF00", "-n", f"2:0:+{part_size // MB}M",
                        "-t", "2:0700", str(img)], check=True, capture_output=True)
        info = subprocess.run(["sgdisk", "-i", "2", str(img)], check=True, capture_output=True, text=True).stdout
        start = int(re.search(r"First sector: (\d+)", info).group(1))
    vol = img.with_suffix(".vol")
    format_volume(vol, PyFat.FAT_TYPE_FAT32, part_size)
    with open(img, "r+b") as f:
        f.seek(start * 512)
        f.write(vol.read_bytes())
    vol.unlink()
    return start * 512


cases = [("FAT16 bare", "bare16"), ("FAT32 bare", "bare32")]
if shutil.which("sfdisk"):
    cases.append(("FAT32 in MBR (Windows stick)", "mbr"))
if shutil.which("sgdisk"):
    cases.append(("FAT32 in GPT after EFI (macOS stick)", "gpt"))
fails = 0
for label, kind in cases:
    img, out = build / f"xcheck_{kind}.img", build / f"xcheck_{kind}_out.img"
    if kind == "bare16":
        format_volume(img, PyFat.FAT_TYPE_FAT16, 32 * MB)
        off = 0
    elif kind == "bare32":
        format_volume(img, PyFat.FAT_TYPE_FAT32, 64 * MB)
        off = 0
    else:
        off = partitioned(img, kind, 64 * MB)
    fs = PyFatFS(str(img), offset=off)
    fs.writebytes("/" + NAME, content)
    fs.writebytes("/readme.txt", b"short")
    fs.writebytes("/._" + NAME, content[:4096])
    fs.makedir("/.Spotlight-V100")
    fs.writebytes("/.DS_Store", b"\0" * 6148)
    fs.close()
    run = subprocess.run([tool, "--image", str(img), str(out)], capture_output=True, text=True)
    print(f"{label}: {run.stdout.strip()}")
    ok = run.returncode == 0
    if ok:
        fs = PyFatFS(str(out), offset=off)
        rx, log, orig = fs.readbytes("/RX.TXT"), fs.readbytes("/NM_LOG.TXT").decode(), fs.readbytes("/" + NAME)
        fs.close()
        ok = rx == content and orig == content and NAME in log and f"{len(content)}" in log
    print(f"  pyfatfs reads RX.TXT back {'identical' if ok else 'DIFFERENT'} ({len(content)} bytes)")
    fails += not ok
print("ALL PASSED" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
