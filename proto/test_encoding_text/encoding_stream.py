"""Binary file transfer and strict Unicode decoding for the Raspberry Pi 3.

The stream contains the original file bytes only. Size and CRC-32 are supplied
separately by the caller; this module does not define radio frames. Run --help
for the local file/pipe harness. No third-party Python packages are required.
"""
from __future__ import annotations

import argparse
import codecs
import ctypes
import json
import os
from pathlib import Path
import stat
import sys
import zlib
from dataclasses import asdict, dataclass
from typing import BinaryIO, Iterable

ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")
BOMS = ((b"\xff\xfe\x00\x00", "utf-32-le"),
        (b"\x00\x00\xfe\xff", "utf-32-be"),
        (b"\xef\xbb\xbf", "utf-8"),
        (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"))
DEFAULT_CHUNK = 4096


@dataclass(frozen=True)
class FileInfo:
    size_bytes: int
    crc32: str


def check_chunk(size: int) -> None:
    if not 1 <= size <= 1024 * 1024:
        raise ValueError("chunk size must be between 1 and 1048576 bytes")


def file_chunks(path: Path, chunk_size: int = DEFAULT_CHUNK) -> Iterable[bytes]:
    check_chunk(chunk_size)
    with Path(path).open("rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("source must be a regular file")
        while block := source.read(chunk_size):
            yield block


def file_info(path: Path, chunk_size: int = DEFAULT_CHUNK) -> FileInfo:
    size, crc = 0, 0
    for block in file_chunks(path, chunk_size):
        size += len(block)
        crc = zlib.crc32(block, crc)
    return FileInfo(size, f"{crc:08x}")


def discover(directory: Path) -> Path:
    """Select a single regular .txt file; never guess among several files."""
    candidates = sorted(p for p in Path(directory).iterdir()
                        if not p.is_symlink() and p.is_file() and p.suffix.lower() == ".txt")
    if len(candidates) != 1:
        raise ValueError(f"expected one .txt file, found {len(candidates)}; specify a file explicitly")
    return candidates[0]


def _valid(path: Path, encoding: str, skip: int, chunk_size: int) -> bool:
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    try:
        for block in file_chunks(path, chunk_size):
            n = min(skip, len(block))
            skip -= n
            decoder.decode(block[n:])
        decoder.decode(b"", final=True)
        return skip == 0
    except UnicodeDecodeError:
        return False


def inspect_file(path: Path, chunk_size: int = DEFAULT_CHUNK) -> dict:
    """Validate all five supported encodings, without modifying the file.

    A unique candidate is unique within this supported set, not a universal
    encoding proof. BOM overlap remains visible even when longest-first lookup
    would choose a conventional interpretation.
    """
    info = file_info(path, chunk_size)
    with Path(path).open("rb") as source:
        prefix = source.read(4)
    matches = [(bom, enc) for bom, enc in BOMS if prefix.startswith(bom)]
    valid = [enc for enc in ENCODINGS if _valid(path, enc, 0, chunk_size)]
    valid_boms = [enc for bom, enc in matches if _valid(path, enc, len(bom), chunk_size)]
    selected = None
    if not info.size_bytes:
        status = "empty"
    elif matches:
        status = "bom" if len(valid_boms) == 1 else "ambiguous_bom" if valid_boms else "invalid_bom"
        if len(valid_boms) == 1:
            selected = valid_boms[0]
    else:
        status = "unique_valid" if len(valid) == 1 else "ambiguous" if valid else "invalid"
        if len(valid) == 1:
            selected = valid[0]
    return dict(asdict(info), bom_matches=[enc for _, enc in matches],
                valid_bom_encodings=valid_boms, valid_encodings=valid,
                auto_encoding=selected, detection=status)


def select_encoding(report: dict, encoding: str = "auto", bom_policy: str = "strict") -> str:
    if bom_policy not in ("strict", "longest"):
        raise ValueError("unknown BOM policy")
    if encoding != "auto":
        if encoding not in ENCODINGS:
            raise ValueError("use utf-8, utf-16-le/be or utf-32-le/be")
        if encoding not in report["valid_encodings"]:
            raise ValueError("file is invalid in the declared encoding")
        return encoding
    if bom_policy == "longest" and report["bom_matches"]:
        selected = report["bom_matches"][0]
        if selected not in report["valid_bom_encodings"]:
            raise ValueError("longest BOM signature has invalid text")
        return selected
    if report["auto_encoding"] is None:
        raise ValueError("encoding unresolved (" + report["detection"] + "); specify --encoding")
    return report["auto_encoding"]


def write_all(sink: BinaryIO, data: bytes) -> None:
    view = memoryview(data)
    while view:
        count = sink.write(view)
        if count is None or not 0 < count <= len(view):
            raise OSError("stream made no valid write progress")
        view = view[count:]


def send_file(path: Path, sink: BinaryIO, chunk_size: int = DEFAULT_CHUNK,
              expected: FileInfo | None = None) -> FileInfo:
    """Send raw bytes. Supplying prepared metadata detects a changed source."""
    size, crc = 0, 0
    for block in file_chunks(path, chunk_size):
        write_all(sink, block)
        size += len(block)
        crc = zlib.crc32(block, crc)
    result = FileInfo(size, f"{crc:08x}")
    if expected is not None and result != expected:
        raise ValueError("source changed after preparation")
    return result


def _publish_no_replace(source: Path, target: Path) -> None:
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise OSError("renameat2 is required for safe publication on Linux")
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(source), -100, os.fsencode(target), 1) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(target))
    elif os.name == "nt":
        os.rename(source, target)  # Windows rename fails if target exists.
    else:
        raise OSError("publication is supported on Linux and Windows")


class AtomicOutput:
    """Owned .part file; final name appears only after validation and fsync.

    Existing final or partial files are never overwritten. A process killed
    before commit may leave its .part file for manual inspection/removal.
    """
    def __init__(self, path: Path):
        self.path = Path(path)
        self.partial = self.path.with_name(self.path.name + ".part")
        if os.path.lexists(self.path):
            raise FileExistsError(str(self.path))
        self.file = self.partial.open("xb")
        self.owned = True
        self.size = self.crc = 0

    def __enter__(self):
        return self

    def write(self, block: bytes) -> None:
        write_all(self.file, block)
        self.size += len(block)
        self.crc = zlib.crc32(block, self.crc)

    def finish(self, expected: FileInfo | None = None) -> FileInfo:
        actual = FileInfo(self.size, f"{self.crc:08x}")
        if expected is not None and actual != expected:
            raise ValueError("received size or CRC-32 differs from sender metadata")
        self.file.flush()
        os.fsync(self.file.fileno())
        self.file.close()
        if file_info(self.partial) != actual:
            raise OSError("saved file failed read-back validation")
        _publish_no_replace(self.partial, self.path)
        self.owned = False
        if sys.platform.startswith("linux"):
            fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return actual

    def __exit__(self, *_):
        try:
            self.file.close()
        finally:
            if self.owned:
                self.partial.unlink(missing_ok=True)


class FileReceiver(AtomicOutput):
    def __init__(self, path: Path, expected: FileInfo):
        if not 0 <= expected.size_bytes <= 0xffffffffffffffff or len(expected.crc32) != 8 or any(c not in "0123456789abcdefABCDEF" for c in expected.crc32):
            raise ValueError("invalid file metadata")
        try:
            int(expected.crc32, 16)
        except ValueError as exc:
            raise ValueError("invalid CRC-32") from exc
        self.expected = FileInfo(expected.size_bytes, expected.crc32.lower())
        super().__init__(path)

    def accept(self, offset: int, block: bytes) -> None:
        if offset != self.size:
            raise ValueError("duplicate, missing or out-of-order data; reorder at transport layer")
        if len(block) > self.expected.size_bytes - self.size:
            raise ValueError("received more bytes than declared")
        self.write(block)

    def finish(self, expected: FileInfo | None = None) -> FileInfo:
        return super().finish(self.expected)


def receive_stream(source: BinaryIO, path: Path, expected: FileInfo,
                   chunk_size: int = DEFAULT_CHUNK) -> FileInfo:
    check_chunk(chunk_size)
    with FileReceiver(path, expected) as receiver:
        while block := source.read(chunk_size):
            receiver.accept(receiver.size, block)
        return receiver.finish()


def decode_file(source: Path, destination: Path, encoding: str = "auto",
                bom_policy: str = "strict", keep_bom: bool = False,
                chunk_size: int = DEFAULT_CHUNK) -> str:
    report = inspect_file(source, chunk_size)
    selected = select_encoding(report, encoding, bom_policy)
    with Path(source).open("rb") as stream:
        prefix = stream.read(4)
    skip = next((len(b) for b, e in BOMS if e == selected and prefix.startswith(b)), 0) if not keep_bom else 0
    decoder = codecs.getincrementaldecoder(selected)(errors="strict")
    size, crc = 0, 0
    with AtomicOutput(destination) as output:
        for block in file_chunks(source, chunk_size):
            size += len(block)
            crc = zlib.crc32(block, crc)
            n = min(skip, len(block))
            skip -= n
            output.write(decoder.decode(block[n:]).encode("utf-8"))
        output.write(decoder.decode(b"", final=True).encode("utf-8"))
        if size != report["size_bytes"] or f"{crc:08x}" != report["crc32"]:
            raise ValueError("source changed during decoding")
        output.finish()
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "send", "receive", "copy", "decode", "discover"):
        sub = commands.add_parser(name)
        sub.add_argument("source", type=Path)
        if name in ("send", "receive", "copy", "decode"):
            sub.add_argument("destination", type=Path)
        sub.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
        if name == "receive":
            sub.add_argument("--size", type=int, required=True)
            sub.add_argument("--crc32", required=True)
        if name == "decode":
            sub.add_argument("--encoding", choices=("auto",) + ENCODINGS, default="auto")
            sub.add_argument("--bom-policy", choices=("strict", "longest"), default="strict")
            sub.add_argument("--keep-bom", action="store_true")
    args = parser.parse_args()
    try:
        check_chunk(args.chunk_size)
        if args.command == "discover":
            result = {"file": str(discover(args.source))}
        elif args.command == "inspect":
            result = inspect_file(args.source, args.chunk_size)
        elif args.command == "decode":
            result = {"encoding": decode_file(args.source, args.destination, args.encoding,
                                              args.bom_policy, args.keep_bom, args.chunk_size)}
        elif args.command == "send":
            prepared = file_info(args.source, args.chunk_size)
            if str(args.destination) == "-":
                sent = send_file(args.source, sys.stdout.buffer, args.chunk_size, prepared)
                sys.stdout.buffer.flush()
                print(json.dumps(asdict(sent)), file=sys.stderr)
                return 0
            with AtomicOutput(args.destination) as output:
                sent = send_file(args.source, output.file, args.chunk_size, prepared)
                output.size, output.crc = sent.size_bytes, int(sent.crc32, 16)
                output.finish(prepared)
            result = asdict(sent)
        else:
            expected = file_info(args.source, args.chunk_size) if args.command == "copy" else FileInfo(args.size, args.crc32)
            if str(args.source) == "-":
                result = asdict(receive_stream(sys.stdin.buffer, args.destination, expected, args.chunk_size))
            else:
                with args.source.open("rb") as source:
                    result = asdict(receive_stream(source, args.destination, expected, args.chunk_size))
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
