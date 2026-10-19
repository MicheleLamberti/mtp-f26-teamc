"""Create small, reproducible input files for manual encoding experiments."""
import argparse
import json
from pathlib import Path
from encoding_stream import BOMS, ENCODINGS, inspect_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    text = "MTP: caf\u00e9, \u20ac, \u6f22, \U0001f600\r\nNUL:\x00; e\u0301\nEND"
    samples = {"empty.txt": b"", "ambiguous_no_bom.txt": b"A\x00",
               "overlapping_bom.txt": bytes.fromhex("fffe000041000000"),
               "invalid_utf8.bin": b"\xc0\xaf", "incomplete_utf16.bin": b"\xff\xfeA",
               "all_byte_values.bin": bytes(range(256))}
    for enc in ENCODINGS:
        bom = next(b for b, e in BOMS if e == enc)
        samples[enc + ".txt"] = text.encode(enc)
        samples[enc + "_bom.txt"] = bom + text.encode(enc)
    # Refuse partial replacement of an existing fixture collection.
    paths = [args.directory / name for name in samples] + [args.directory / "manifest.json"]
    if any(path.exists() for path in paths):
        parser.error("sample files already exist; choose a new directory")
    reports = {}
    for name, raw in samples.items():
        path = args.directory / name
        with path.open("xb") as output:
            output.write(raw)
        reports[name] = inspect_file(path)
    with (args.directory / "manifest.json").open("x", encoding="utf-8") as output:
        json.dump(reports, output, indent=2)
    print(f"Created {len(samples)} samples and manifest.json in {args.directory}")


if __name__ == "__main__":
    main()
