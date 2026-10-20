"""Genera muestras y evidencia reproducible. Pruebas locales, sin radio ni USB fisico."""
from __future__ import annotations

import codecs
import io
import json
import sys
import tempfile
import unicodedata
from pathlib import Path

from unicode_mtp import BOMS, ENCODINGS, compare_files, inspect_bytes, valid_as

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation"
SAMPLES = OUT / "muestras"


def main() -> int:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, condition):
        checks.append({"prueba": name, "ok": bool(condition)})

    # Se usan escapes para que la fuente sea portable entre editores.
    text = "MTP: Espa\u00f1a, caf\u00e9, \u20ac, \u6f22, \U0001f600\r\ne\u0301\nFIN\r"
    samples = {}
    for enc in ENCODINGS:
        payload = text.encode(enc)
        bom = next(b for b, e in BOMS if e == enc)
        samples[f"{enc}_sin_bom.txt"] = payload
        samples[f"{enc}_con_bom.txt"] = bom + payload
        info = inspect_bytes(bom + payload)
        preferred = info["preferred_bom_by_longest_signature"]
        check(f"BOM y validacion estricta {enc}", preferred["encoding"] == enc and preferred["payload_valid"])
    samples.update({
        "ascii_sin_bom.txt": b"MTP\r\nOK\r\n",
        "vacio.txt": b"",
        "utf8_invalido.bin": b"A\xC0\xAF\xFF\r\n",
        "utf16le_incompleto.bin": bytes.fromhex("FF FE 41"),
        "utf16le_surrogate_aislado.bin": bytes.fromhex("FF FE 00 D8"),
        "utf32le_fuera_rango.bin": bytes.fromhex("FF FE 00 00 00 00 11 00"),
        "utf8_nul_y_sin_salto_final.txt": b"MTP\x00fin",
        "utf8_nfc.txt": "caf\u00e9\r\n".encode("utf-8"),
        "utf8_nfd.txt": "cafe\u0301\r\n".encode("utf-8"),
        "utf16le_falso_lf.txt": "\u010aX\r\n".encode("utf-16-le"),
        "todos_los_bytes.bin": bytes(range(256)),
    })
    for name, data in samples.items():
        (SAMPLES / name).write_bytes(data)

    # Copia fragmentada: cortes deliberadamente no alineados con caracteres.
    # No simula perdida de paquetes, CRC, ARQ ni el protocolo de red.
    sizes = (1, 2, 3, 7, 31, 64, 255)
    for name, data in samples.items():
        for size in sizes:
            source, received = io.BytesIO(data), io.BytesIO()
            while chunk := source.read(size):
                received.write(chunk)
            check(f"Bytes exactos: {name}, bloque {size}", received.getvalue() == data)

    no_bom = inspect_bytes(b"AB")
    check("Sin BOM no se afirma una codificacion", no_bom["preferred_bom_by_longest_signature"] is None and not no_bom["encoding_proven"])
    check("ASCII par tambien admite lecturas UTF-16", len(no_bom["valid_full_stream_decodings_without_removing_bytes"]) > 1)
    overlapping = inspect_bytes(bytes.fromhex("FF FE 00 00 41 00 00 00"))
    check("BOM largo antes del corto", overlapping["preferred_bom_by_longest_signature"]["encoding"] == "utf-32-le")
    check("Se conserva ambiguedad de firma FF FE", len(overlapping["bom_matches"]) == 2 and not overlapping["encoding_proven"])
    check("UTF-8 overlong se rechaza", not valid_as(bytes.fromhex("C0 AF"), "utf-8"))
    check("UTF-16 surrogate aislado se rechaza", not valid_as(bytes.fromhex("00 D8"), "utf-16-le"))
    check("UTF-32 mayor que U+10FFFF se rechaza", not valid_as(bytes.fromhex("00 00 11 00"), "utf-32-le"))
    check("BOM invalido no dispara conversion", not inspect_bytes(samples["utf16le_incompleto.bin"])["preferred_bom_by_longest_signature"]["payload_valid"])
    nfc, nfd = samples["utf8_nfc.txt"], samples["utf8_nfd.txt"]
    check("Equivalencia visual no implica bytes iguales", nfc != nfd and unicodedata.normalize("NFC", nfd.decode()) == nfc.decode())
    check("Convertir CRLF a LF cambia el archivo", nfc != nfc.replace(b"\r\n", b"\n"))
    raw = "\U0001f600".encode("utf-8")
    check("Un fragmento UTF-8 puede ser invalido aunque el texto completo sea valido", not valid_as(raw[:2], "utf-8") and valid_as(raw, "utf-8"))
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    check("Decodificacion incremental conserva un caracter partido", decoder.decode(raw[:2]) + decoder.decode(raw[2:], final=True) == "\U0001f600")
    check("0A suelto da un falso salto en UTF-16", samples["utf16le_falso_lf.txt"].count(b"\n") == 2 and samples["utf16le_falso_lf.txt"].decode("utf-16-le").count("\n") == 1)

    with tempfile.TemporaryDirectory(prefix="mtp_task11_") as folder:
        original, received = Path(folder) / "tx.bin", Path(folder) / "rx.bin"
        original.write_bytes(b"abcdefgh")
        for label, content, expected_offset in [
            ("iguales", b"abcdefgh", None),
            ("byte alterado", b"abcXefgh", 3),
            ("truncado", b"abcdef", 6),
            ("byte extra", b"abcdefghX", 8),
            ("vacio", b"", 0),
        ]:
            received.write_bytes(content)
            result = compare_files(original, received, block_size=3)
            check(f"Comparador exacto: {label}", result["first_difference_offset_zero_based"] == expected_offset and result["identical"] == (expected_offset is None))
        original.write_bytes(b"")
        received.write_bytes(b"")
        check("Comparador: ambos vacios", compare_files(original, received)["identical"])
        # Archivo de 1 MB procesado en bloques sin mantenerlo entero en el comparador.
        seed = text.encode("utf-8")
        data = (seed * ((1000000 + len(seed) - 1) // len(seed)))[:1000000]
        original.write_bytes(data)
        with original.open("rb") as source, received.open("wb") as target:
            while chunk := source.read(255):
                target.write(chunk)
        check("Archivo de 1 MB y bloques de 255 bytes", len(data) == 1000000 and compare_files(original, received)["identical"])

    passed = sum(item["ok"] for item in checks)
    result = {
        "python": sys.version.split()[0],
        "sample_files": len(samples),
        "fragment_sizes_bytes": list(sizes),
        "fragmentation_cases": len(samples) * len(sizes),
        "passed": passed,
        "total": len(checks),
        "scope": "Software local; sin validacion de hardware, radio, CRC ni retransmisiones.",
        "checks": checks,
    }
    (OUT / "resultados.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    # Fragmento LaTeX para incluir en el preambulo del informe.
    latex = (
        "% Generado por codigo/validar_task11.py. No editar a mano.\n"
        + "\\newcommand{\\TestsPassed}{" + str(passed) + "}\n"
        + "\\newcommand{\\TestsTotal}{" + str(len(checks)) + "}\n"
        + "\\newcommand{\\SampleCount}{" + str(len(samples)) + "}\n"
        + "\\newcommand{\\FragmentCases}{" + str(len(samples) * len(sizes)) + "}\n"
        + "\\newcommand{\\PythonVersion}{" + result["python"] + "}\n"
    )
    (ROOT / "report" / "validacion.tex").write_text(latex, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, ensure_ascii=True, indent=2))
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
