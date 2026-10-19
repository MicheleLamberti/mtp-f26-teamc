"""Unit tests and Python/C++ interoperability; no radio or USB device required."""
from pathlib import Path
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import encoding_stream as mt

CPP = None
if "--cpp" in sys.argv:
    index = sys.argv.index("--cpp")
    CPP = str(Path(sys.argv[index + 1]).resolve())
    del sys.argv[index:index + 2]

TEXT = "ASCII\x00 caf\u00e9 \u20ac \u6f22 \U0001f600 e\u0301\r\nLF\nCR\r\ufeffEND\uffff"


def samples():
    result = {"empty": b"", "ascii_even": b"AB", "ascii_odd": b"ABC",
              "all_bytes": bytes(range(256)), "overlap": bytes.fromhex("fffe000041000000"),
              "trailing_nul": b"A\x00", "utf8_overlong": b"\xc0\xaf", "utf8_surrogate": b"\xed\xa0\x80",
              "utf8_range": b"\xf4\x90\x80\x80", "utf8_truncated": b"\xf0\x9f\x98",
              "utf16_truncated": b"\xff\xfeA", "utf16_high": b"\xff\xfe\x00\xd8",
              "utf16_low": b"\xfe\xff\xdc\x00", "utf32_range": b"\xff\xfe\x00\x00\x00\x00\x11\x00",
              "bom_prefix_1": b"\xef", "bom_prefix_2": b"\xef\xbb"}
    for enc in mt.ENCODINGS:
        bom = next(b for b, e in mt.BOMS if e == enc)
        result[enc] = TEXT.encode(enc)
        result[enc + "_bom"] = bom + TEXT.encode(enc)
        result[enc + "_bom_only"] = bom
    return result


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mtp_encoding_")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, data):
        source = self.root / "source.bin"
        source.write_bytes(data)
        return source

    def run_cli(self, command, *args, data=None, ok=True):
        result = subprocess.run(command + list(map(str, args)), input=data,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode == 0, ok, result.stderr.decode(errors="replace"))
        return result


class PythonTests(Workspace):
    def test_every_sample_binary_roundtrip_at_adversarial_boundaries(self):
        for name, data in samples().items():
            source = self.source(data)
            expected = mt.file_info(source)
            self.assertEqual(expected.crc32, f"{zlib.crc32(data):08x}")
            for size in (1, 2, 3, 7, 4096):
                with self.subTest(sample=name, chunk=size):
                    wire = io.BytesIO()
                    self.assertEqual(mt.send_file(source, wire, size, expected), expected)
                    self.assertEqual(wire.getvalue(), data)  # No injected header or BOM.
                    target = self.root / (name + "_" + str(size))
                    mt.receive_stream(io.BytesIO(wire.getvalue()), target, expected, size)
                    self.assertEqual(target.read_bytes(), data)

    def test_explicit_decoding_preserves_text_and_original(self):
        for encoding in mt.ENCODINGS:
            bom = next(b for b, e in mt.BOMS if e == encoding)
            for initial in (b"", bom):
                raw = initial + TEXT.encode(encoding)
                source = self.source(raw)
                for chunk in (1, 3, 7):
                    output = self.root / f"text_{encoding}_{len(initial)}_{chunk}"
                    mt.decode_file(source, output, encoding=encoding, chunk_size=chunk)
                    self.assertEqual(output.read_bytes(), TEXT.encode("utf-8"))
                    self.assertEqual(source.read_bytes(), raw)

    def test_ambiguous_and_missing_bom_policies(self):
        for data in (b"", b"AB", b"A\x00", bytes.fromhex("fffe000041000000")):
            source = self.source(data)
            self.assertIsNone(mt.inspect_file(source)["auto_encoding"])
            output = self.root / "not_created"
            with self.assertRaises(ValueError): mt.decode_file(source, output)
            self.assertFalse(output.exists())
        source = self.source(bytes.fromhex("fffe000041000000"))
        mt.decode_file(source, self.root / "convention", bom_policy="longest", chunk_size=1)
        mt.decode_file(source, self.root / "declared", encoding="utf-16-le", chunk_size=1)
        self.assertEqual((self.root / "convention").read_bytes(), b"A")
        self.assertEqual((self.root / "declared").read_bytes(), b"\x00A\x00")

    def test_literal_and_interior_feff(self):
        source = self.source(b"\xef\xbb\xbf" + "A\ufeffB".encode())
        mt.decode_file(source, self.root / "keep", encoding="utf-8", keep_bom=True, chunk_size=1)
        mt.decode_file(source, self.root / "strip", encoding="utf-8", chunk_size=1)
        self.assertEqual((self.root / "keep").read_bytes(), source.read_bytes())
        self.assertEqual((self.root / "strip").read_bytes(), "A\ufeffB".encode())

    def test_corrupt_truncated_extra_and_no_clobber(self):
        original = b"hello\x00\r\nworld"
        expected = mt.file_info(self.source(original))
        for data in (original[:-1], original + b"!", b"X" + original[1:]):
            output = self.root / "incomplete"
            with self.assertRaises(ValueError): mt.receive_stream(io.BytesIO(data), output, expected, 3)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix(".part").exists())
        output = self.root / "existing"
        output.write_bytes(b"KEEP")
        with self.assertRaises(FileExistsError): mt.receive_stream(io.BytesIO(original), output, expected)
        self.assertEqual(output.read_bytes(), b"KEEP")
        partial = self.root / "reserved.part"
        partial.write_bytes(b"KEEP PART")
        with self.assertRaises(FileExistsError): mt.receive_stream(io.BytesIO(original), self.root / "reserved", expected)
        self.assertEqual(partial.read_bytes(), b"KEEP PART")

    def test_offsets_partial_write_failure_and_publication_race(self):
        expected = mt.file_info(self.source(b"abc"))
        with mt.FileReceiver(self.root / "ordered", expected) as receiver:
            with self.assertRaises(ValueError): receiver.accept(1, b"a")
            receiver.accept(0, b"a")
            with self.assertRaises(ValueError): receiver.accept(0, b"a")
            with self.assertRaises(ValueError): receiver.accept(1, b"bcd")
            receiver.accept(1, b"bc")
            receiver.finish()
        with mt.FileReceiver(self.root / "race", expected) as receiver:
            receiver.accept(0, b"abc")
            (self.root / "race").write_bytes(b"WINNER")
            with self.assertRaises(OSError): receiver.finish()
        self.assertEqual((self.root / "race").read_bytes(), b"WINNER")
        class Short(io.BytesIO):
            def write(self, b): return super().write(b[:1])
        short = Short()
        mt.send_file(self.source(b"123456789"), short, 7)
        self.assertEqual(short.getvalue(), b"123456789")
        class Stalled:
            def write(self, _): return 0
        with self.assertRaises(OSError): mt.send_file(self.source(b"x"), Stalled())

    def test_source_change_and_limits(self):
        source = self.source(b"old")
        prepared = mt.file_info(source)
        source.write_bytes(b"new")
        with self.assertRaises(ValueError): mt.send_file(source, io.BytesIO(), expected=prepared)
        for size in (0, -1, 1048577):
            with self.assertRaises(ValueError): mt.file_info(source, size)
        for metadata in (mt.FileInfo(-1, "00000000"), mt.FileInfo(0, "-0000001"), mt.FileInfo(0, "x")):
            with self.assertRaises(ValueError): mt.FileReceiver(self.root / "bad", metadata)

    def test_discovery_and_unicode_filename(self):
        folder = self.root / "input"
        folder.mkdir()
        with self.assertRaises(ValueError): mt.discover(folder)
        path = folder / "caf\u00e9.TXT"
        path.write_bytes(b"ABC")
        (folder / "directory.txt").mkdir()
        self.assertEqual(mt.discover(folder), path)
        (folder / "second.txt").write_bytes(b"ABC")
        with self.assertRaises(ValueError): mt.discover(folder)

    def test_large_file_bounded_reads(self):
        source = self.root / "large"
        block = TEXT.encode("utf-8") * 100
        with source.open("wb") as stream:
            for _ in range(512): stream.write(block)
        expected = mt.file_info(source, 4096)
        with source.open("rb") as stream:
            mt.receive_stream(stream, self.root / "large_rx", expected, 4093)
        self.assertEqual(mt.file_info(self.root / "large_rx"), expected)


@unittest.skipUnless(CPP, "supply --cpp to run cross-language tests")
class InteropTests(Workspace):
    def test_identical_inspection_for_valid_invalid_and_random_bytes(self):
        rng = random.Random(314159)
        cases = list(samples().values()) + [rng.randbytes(i) for i in range(1, 65)]
        for index, raw in enumerate(cases):
            source = self.source(raw)
            with self.subTest(case=index):
                result = self.run_cli([CPP], "inspect", source, "--chunk-size", "1")
                self.assertEqual(json.loads(result.stdout), mt.inspect_file(source, 1))

    def test_cross_language_send_receive_and_decoding(self):
        for index, (name, raw) in enumerate(samples().items()):
            source = self.source(raw)
            info = mt.file_info(source)
            for sender, receiver in (([sys.executable, str(ROOT / "encoding_stream.py")], [CPP]),
                                     ([CPP], [sys.executable, str(ROOT / "encoding_stream.py")])):
                result = self.run_cli(sender, "send", source, "-", "--chunk-size", "3")
                self.assertEqual(result.stdout, raw)
                self.assertEqual(json.loads(result.stderr), mt.asdict(info))
                output = self.root / f"rx_{index}_{len(sender)}"
                self.run_cli(receiver, "receive", "-", output, "--size", info.size_bytes,
                             "--crc32", info.crc32, "--chunk-size", "1", data=result.stdout)
                self.assertEqual(output.read_bytes(), raw)
            if name in mt.ENCODINGS or name.endswith("_bom"):
                encoding = name.removesuffix("_bom")
                output = self.root / ("decoded_" + str(index))
                self.run_cli([CPP], "decode", source, output, "--encoding", encoding, "--chunk-size", "1")
                self.assertEqual(output.read_bytes(), TEXT.encode())

    def test_cpp_failures_and_detection_policy(self):
        source = self.source(bytes.fromhex("fffe000041000000"))
        self.run_cli([CPP], "decode", source, self.root / "ambiguous", ok=False)
        self.run_cli([CPP], "decode", source, self.root / "longest", "--bom-policy", "longest")
        self.assertEqual((self.root / "longest").read_bytes(), b"A")
        self.run_cli([CPP], "decode", source, self.root / "explicit", "--encoding", "utf-16-le")
        self.assertEqual((self.root / "explicit").read_bytes(), b"\x00A\x00")
        for i, (raw, enc) in enumerate(((b"\xed\xa0\x80", "utf-8"), (b"\x00\xd8", "utf-16-le"), (b"\x00\x00\x11\x00", "utf-32-le"))):
            self.run_cli([CPP], "decode", self.source(raw), self.root / f"invalid_{i}", "--encoding", enc, ok=False)
            self.assertFalse((self.root / f"invalid_{i}").exists())
        expected = mt.file_info(self.source(b"hello"))
        for data in (b"hell", b"helloo", b"jello"):
            target = self.root / "bad_rx"
            self.run_cli([CPP], "receive", "-", target, "--size", 5, "--crc32", expected.crc32, data=data, ok=False)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix(".part").exists())
        target = self.root / "keep"
        target.write_bytes(b"KEEP")
        self.run_cli([CPP], "receive", "-", target, "--size", 5, "--crc32", expected.crc32, data=b"hello", ok=False)
        self.assertEqual(target.read_bytes(), b"KEEP")


if __name__ == "__main__":
    unittest.main()
