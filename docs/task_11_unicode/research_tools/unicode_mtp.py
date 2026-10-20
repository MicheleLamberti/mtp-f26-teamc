"""Diagnostico de codificacion y comparacion binaria para MTP. Python 3.10+.

No convierte, normaliza ni modifica los archivos inspeccionados.
La validez sintactica de una codificacion no identifica el formato de origen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")
# Las firmas largas preceden a las cortas; FF FE es prefijo de FF FE 00 00.
BOMS = (
    (bytes.fromhex("FF FE 00 00"), "utf-32-le"),
    (bytes.fromhex("00 00 FE FF"), "utf-32-be"),
    (bytes.fromhex("EF BB BF"), "utf-8"),
    (bytes.fromhex("FF FE"), "utf-16-le"),
    (bytes.fromhex("FE FF"), "utf-16-be"),
)


def valid_as(data: bytes, encoding: str) -> bool:
    try:
        data.decode(encoding, errors="strict")
        return True
    except UnicodeDecodeError:
        return False


def inspect_bytes(data: bytes) -> dict:
    matches = [
        {"encoding": enc, "hex": bom.hex(" ").upper(), "length": len(bom),
         "payload_valid": valid_as(data[len(bom):], enc)}
        for bom, enc in BOMS if data.startswith(bom)
    ]
    preferred = matches[0] if matches else None
    return {
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "first_32_bytes_hex": data[:32].hex(" ").upper(),
        "bom_matches": matches,
        "preferred_bom_by_longest_signature": preferred,
        "valid_full_stream_decodings_without_removing_bytes": [
            enc for enc in ENCODINGS if valid_as(data, enc)
        ],
        "encoding_proven": False,
        "diagnostic": (
            "Archivo vacio: no permite identificar la codificacion."
            if not data else
            "Firma reconocida y contenido valido bajo esa convencion; no es una prueba universal."
            if preferred and preferred["payload_valid"] else
            "Firma reconocida pero contenido invalido bajo esa convencion. No convertir ni corregir."
            if preferred else
            "Sin BOM: solo se enumeran candidatos sintacticamente validos; no se elige uno."
        ),
        "transport_policy": "Conservar todos los bytes originales, incluidos BOM y saltos de linea.",
    }


def compare_files(original: Path, received: Path, block_size: int = 65536) -> dict:
    """Comparacion exacta y hashes auxiliares; memoria O(block_size)."""
    if block_size <= 0:
        raise ValueError("block_size debe ser positivo")
    ha, hb = hashlib.sha256(), hashlib.sha256()
    size_a = size_b = offset = 0
    mismatch = None
    with original.open("rb") as fa, received.open("rb") as fb:
        while True:
            a, b = fa.read(block_size), fb.read(block_size)
            if not a and not b:
                break
            ha.update(a)
            hb.update(b)
            size_a += len(a)
            size_b += len(b)
            if mismatch is None and a != b:
                mismatch = offset + next(
                    (i for i, (x, y) in enumerate(zip(a, b)) if x != y),
                    min(len(a), len(b)),
                )
            offset += max(len(a), len(b))
    return {
        "identical": mismatch is None,
        "original_bytes": size_a,
        "received_bytes": size_b,
        "first_difference_offset_zero_based": mismatch,
        "original_sha256": ha.hexdigest(),
        "received_sha256": hb.hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Diagnostico; nunca modifica el archivo")
    inspect.add_argument("file", type=Path)
    compare = commands.add_parser("compare", help="Comparacion binaria exacta (0=iguales, 1=distintos)")
    compare.add_argument("original", type=Path)
    compare.add_argument("received", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inspect_bytes(args.file.read_bytes())
        else:
            result = compare_files(args.original, args.received)
    except OSError as exc:
        parser.exit(2, f"Error de archivo: {exc}\n")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if args.command == "inspect" or result["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
