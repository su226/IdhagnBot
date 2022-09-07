import array
import struct
import sys
from dataclasses import dataclass
from io import StringIO
from typing import BinaryIO, TextIO

STR_RANDOM = 1 << 0
STR_ORDERED = 1 << 1
STR_ROTATED = 1 << 2


@dataclass
class StrFile:
  version: int
  count: int
  maxlen: int
  minlen: int
  flags: int
  delim: str

  @property
  def random(self) -> bool:
    return bool(self.flags & STR_RANDOM)

  @random.setter
  def random(self, value: bool) -> None:
    self.flags = self.flags & ~STR_RANDOM | value

  @property
  def ordered(self) -> bool:
    return bool(self.flags & STR_ORDERED)

  @ordered.setter
  def ordered(self, value: bool) -> None:
    self.flags = self.flags & ~STR_ORDERED | value << 1

  @property
  def rotated(self) -> bool:
    return bool(self.flags & STR_ROTATED)

  @rotated.setter
  def rotated(self, value: bool) -> None:
    self.flags = self.flags & ~STR_ROTATED | value << 2


def read_header(f: BinaryIO) -> StrFile:
  version, count, maxlen, minlen, flags, delim = struct.unpack("!IIIIIcxxx", f.read(24))
  return StrFile(version, count, maxlen, minlen, flags, delim.decode())


def read_offset(f: BinaryIO, i: int) -> int:
  f.seek(24 + i * 4)
  return struct.unpack("!I", f.read(4))[0]


# array.array is not generic, but pyright allow this
def read_offsets(f: BinaryIO) -> "array.array[int]":
  f.seek(24)
  offsets = array.array("I", f.read())
  if sys.byteorder == "little":
    offsets.byteswap()  # strfile is always network(big) endian
  return offsets


# this doesn't handle rot13, use `codecs.encode(text, "rot13")`
def read_raw_text(f: TextIO, delim: str) -> str:
  delim += "\n"
  buf = StringIO()
  line = f.readline()
  while line and line != delim:
    buf.write(line)
    line = f.readline()
  buf.truncate(buf.tell() - 1)
  return buf.getvalue()
