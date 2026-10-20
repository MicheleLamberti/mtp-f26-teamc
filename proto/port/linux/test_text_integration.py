"""Whole-node Unicode tests: FatFs images -> real nodes/UDP -> original bytes and UTF-8 view."""
from pathlib import Path
import json
import os
import random
import signal
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
NODE = ROOT / "build/teamc-node"
MK = ROOT / "build/mkstick"
BOMS = {"utf-8": b"\xef\xbb\xbf", "utf-16-le": b"\xff\xfe", "utf-16-be": b"\xfe\xff",
        "utf-32-le": b"\xff\xfe\x00\x00", "utf-32-be": b"\x00\x00\xfe\xff"}


class NodeTextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="node_text_", dir=ROOT / "build")
        self.root = Path(self.temp.name)
        self.children = []
        self.logs = []

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
        for log in self.logs:
            log.close()
        self.temp.cleanup()

    def command(self, *args):
        return subprocess.run([str(a) for a in args], cwd=ROOT, check=True,
                              capture_output=True, timeout=10)

    def prepare(self, payload):
        (self.root / "source.txt").write_bytes(payload)
        self.command(MK, "make", self.root / "tx.img", 16, "fat16", self.root / "source.txt")
        for name in ("rx", "out"):
            self.command(MK, "make", self.root / f"{name}.img", 16, "fat16")
        sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in range(2)]
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        ports = [sock.getsockname()[1] for sock in sockets]
        for sock in sockets:
            sock.close()
        return ports

    def start(self, role, port, peer, options=(), go=0.4):
        log = (self.root / f"{role}.log").open("wb")
        self.logs.append(log)
        args = [NODE, "--radio", f"udp:{port}:{peer}", "--data", self.root / role,
                "--stick", self.root / f"{role}.img", "--sim-ui", role, "sri",
                "--go-after", str(go), "--stop-after", "15", "--exit-after-save", *options]
        if role == "rx":
            args += ["--stick-out", self.root / "out.img"]
        child = subprocess.Popen([str(a) for a in args], cwd=ROOT, stdout=log, stderr=log)
        self.children.append(child)
        return child

    def wait_for(self, condition, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.02)
        logs = "\n".join(p.read_text(errors="replace") for p in self.root.glob("*.log"))
        self.fail("node condition timed out:\n" + logs)

    def stop(self, children):
        for child in children:
            if child.poll() is None:
                child.send_signal(signal.SIGUSR1)
        for child in children:
            code = child.wait(timeout=6)
            if code:
                logs = "\n".join(p.read_text(errors="replace") for p in self.root.glob("*.log"))
                self.fail(f"node exited {code}:\n{logs}")

    def transfer(self, payload, expected_text=None, options=()):
        tx_port, rx_port = self.prepare(payload)
        rx = self.start("rx", rx_port, tx_port, options)
        tx = self.start("tx", tx_port, rx_port, options)
        self.wait_for(lambda: all("DONE after" in (self.root / f"{role}.log").read_text()
                                 for role in ("rx", "tx")))
        self.stop([rx, tx])
        self.command(MK, "get", self.root / "out.img", "RX_source.txt", self.root / "got.bin")
        self.assertEqual((self.root / "got.bin").read_bytes(), payload)
        self.assertEqual((self.root / "rx/received.bin").read_bytes(), payload)
        preview = self.root / "rx/received.utf8.txt"
        if expected_text is None:
            self.assertFalse(preview.exists())
        else:
            self.assertEqual(preview.read_bytes(), expected_text.encode("utf-8"))
        return self.root / "rx/received.encoding.json"

    def test_five_encodings_and_compression(self):
        # Each subtest gets fresh USB images/data; includes the strict UTF-32 LE overlap.
        for encoding in BOMS:
            with self.subTest(encoding=encoding):
                if self.children:
                    self.tearDown()
                    self.setUp()
                text = ("A\u00e9\u6f22\U0001f600\r\ne\u0301\x00\ufeff\n" * 80)
                payload = BOMS[encoding] + text.encode(encoding)
                expected = None if encoding == "utf-32-le" else text
                report = self.transfer(payload, expected)
                self.assertEqual(json.loads(report.read_bytes())["size_bytes"], len(payload))
                self.assertIn("codec=1", (self.root / "tx/tx.meta").read_text())

    def test_declared_utf16_overlapping_signature(self):
        self.transfer(bytes.fromhex("ff fe 00 00 41 00 00 00"), "\x00A\x00",
                      ("--text-encoding", "utf-16-le"))

    def test_longest_signature_convention(self):
        self.transfer(bytes.fromhex("ff fe 00 00 41 00 00 00"), "A",
                      ("--text-bom-policy", "longest"))

    def test_bomless_ambiguity(self):
        report = self.transfer(b"A\x00")
        self.assertEqual(json.loads(report.read_bytes())["detection"], "ambiguous")

    def test_invalid_text_still_transfers(self):
        report = self.transfer(b"\xef\xbb\xbf\xc0\xaf")
        self.assertEqual(json.loads(report.read_bytes())["detection"], "invalid_bom")

    def test_empty_file(self):
        report = self.transfer(b"", "", ("--text-encoding", "utf-8"))
        self.assertEqual(json.loads(report.read_bytes())["detection"], "empty")

    def test_decoding_disabled(self):
        report = self.transfer(b"\xef\xbb\xbfA", options=("--text-encoding", "none"))
        self.assertFalse(report.exists())

    def test_partial_stop_preserves_prefix(self):
        payload = random.Random(741).randbytes(600_000)
        tx_port, rx_port = self.prepare(payload)
        rx = self.start("rx", rx_port, tx_port)
        tx = self.start("tx", tx_port, rx_port)
        data = self.root / "rx/rx.bin"
        self.wait_for(lambda: data.exists() and data.stat().st_size >= 56)
        self.stop([rx, tx])
        self.command(MK, "get", self.root / "out.img", "RX_source.txt", self.root / "got.bin")
        got = (self.root / "got.bin").read_bytes()
        self.assertGreater(len(got), 0)
        self.assertLess(len(got), len(payload))
        self.assertEqual(got, payload[:len(got)])
        self.assertEqual((self.root / "rx/received-prefix.bin").read_bytes(), got)
        self.assertFalse((self.root / "rx/received.utf8.txt").exists())
        self.assertFalse((self.root / "rx/received.bin").exists())

    def test_corrupt_sender_cache_is_rejected_at_go(self):
        tx_port, rx_port = self.prepare(b"123456789")
        tx = self.start("tx", tx_port, rx_port, go=1.5)
        cache = self.root / "tx/tx.bin"
        self.wait_for(lambda: (self.root / "tx/tx.meta").exists())
        cache.write_bytes(b"X23456789")
        self.assertEqual(tx.wait(timeout=5), 1)
        self.assertIn("source changed after preparation", (self.root / "tx.log").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
