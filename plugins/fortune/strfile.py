import struct
from dataclasses import dataclass
from io import StringIO
from typing import BinaryIO, TextIO


@dataclass
class StrFile:
  version: int
  count: int
  maxlen: int
  minlen: int
  flags: int
  delim: str
  offsets: list[int]


def read_dat(f: BinaryIO) -> StrFile:
  version, count, maxlen, minlen, flags, delim = struct.unpack("!IIIIIcxxx", f.read(24))
  offsets = []
  for _ in range(count):
    offsets.append(*struct.unpack("!I", f.read(4)))
  f.seek(4)  # last offset is EOF
  return StrFile(version, count, maxlen, minlen, flags, delim.decode(), offsets)


def read_text(f: TextIO, offset: int, delim: str) -> str:
  f.seek(offset)
  buf = StringIO()
  ch = f.read(1)
  while ch and ch != delim:
    buf.write(ch)
    ch = f.read(1)
  return buf.getvalue().removesuffix("\n")
