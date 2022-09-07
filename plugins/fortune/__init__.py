import codecs
from dataclasses import dataclass
import os
import random
import posixpath
import re
from argparse import Namespace
from typing import Sequence

from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from pydantic import BaseModel

from util import command, config_v2

from . import strfile


class Config(BaseModel):
  fortunes: str = "/usr/share/fortune"
  offensive: bool = False


CONFIG = config_v2.SharedConfig("fortune", Config)
RE_033 = re.compile("\033\\[(\\d*;?)*m")


def list_fortunes(recursive: bool) -> list[str]:
  config = CONFIG()
  if recursive:
    result = []
    for root, _, files in os.walk(config.fortunes, True):
      result.extend(os.path.relpath(os.path.join(root, i), config.fortunes) for i in files)
  else:
    result = [i.name for i in os.scandir(config.fortunes) if i.is_file()]
  return [i.replace(os.sep, "/") for i in result if not i.endswith(".dat")]


def strip_033(src: str) -> str:
  return RE_033.sub("", src)


parser = ArgumentParser(add_help=False)
parser.add_argument("files", metavar="[权重] 文件", nargs="*",
  help="来源，默认为全部，权重可以是小数，不提供权重时会根据文本数量计算")
parser.add_argument("--offensive", "-o", action="store_true",
  help="包含可能不雅的文本，可能被群主或超管禁用")
parser.add_argument("--source", "-u", action="store_true",
  help="显示文本来源")
parser.add_argument("--equal", "-e", action="store_true",
  help="所有来源权重相等，而非根据文本数量计算")
parser.add_argument("--list", "-i", action="store_true",
  help="显示文件列表")
parser.add_argument("--length", "-n", type=int, default=160, metavar="长度",
  help="长度限制，默认为 160，只有和 --long 或 --short 一起使用时才有意义")
group = parser.add_mutually_exclusive_group()
group.add_argument("--long", "-l", action="store_true", default=None,
  help="只显示长于指定长度的文本")
group.add_argument("--short", "-s", action="store_false", dest="long",
  help="只显示短于指定长度的文本")
parser.epilog = "灵感及数据来自同名 UNIX / Linux 命令"
fortune = (
  command.CommandBuilder("fortune", "fortune")
  .brief("随机显示一条可能有用的格言")
  .shell(parser)
  .build())


class StrFileChoice:
  def __init__(self, name: str, weight: float, length: int, long: bool | None):
    self.name = name
    self.weight = weight
    with open(os.path.join(CONFIG().fortunes, name + ".dat"), "rb") as f:
      self.header = strfile.read_header(f)
      if long is not None:
        offsets = strfile.read_offsets(f)
        if self.header.ordered or self.header.random:
          offsets = sorted(offsets)
        offsets = self._filter_offsets(offsets, length, long)
        self.count = len(offsets)
        self.choice = random.choice(offsets) if offsets else 0
      else:
        self.count = self.header.count
        self.choice = strfile.read_offset(f, random.randrange(self.count))

  @staticmethod
  def _filter_offsets(offsets: Sequence[int], length: int, long: bool) -> list[int]:
    return [
      offset for i, offset in enumerate(offsets) if
      i + 1 < len(offsets) and (offsets[i + 1] - offset >= length) == long]


@fortune.handle()
async def handle_fortune(args: Namespace | ParserExit = ShellCommandArgs()) -> None:
  if isinstance(args, ParserExit):
    await fortune.finish(args.message)
  config = CONFIG()
  if args.offensive and not config.offensive:
    await fortune.finish("禁止查看可能不雅的文本")
  if args.files:
    files: list[StrFileChoice] = []
    manual_weight = 0
    manual_texts = 0
    manual_files = 0
    weight: float = -1
    for filename in args.files:
      try:
        weight = float(filename)
      except ValueError:
        filename = posixpath.normpath("///" + filename).removeprefix("/")
        if not os.path.isfile(os.path.join(config.fortunes, filename)):
          await fortune.finish(f"{filename} 不存在")
        elif not config.offensive and "/" in filename:
          await fortune.finish("禁止查看可能不雅的文本")
        choice = StrFileChoice(filename, weight, args.length, args.long)
        if choice.count > 0:
          files.append(choice)
          if weight > 0:
            manual_weight += weight
            manual_texts += choice.count
            manual_files += 1
        weight = -1
    for i in files:
      if i.weight < 0:
        if args.equal:
          if manual_files != 0:
            i.weight = manual_weight / manual_files
          else:
            i.weight = 1
        else:
          if manual_texts != 0:
            i.weight = i.header.count / manual_texts * manual_weight
          else:
            i.weight = i.header.count
  else:
    files = [
      choice for i in list_fortunes(args.offensive)
      if (choice := StrFileChoice(i, 1, args.length, args.long)).count > 0]
    if not args.equal:
      for i in files:
        i.weight = i.header.count
  if not files:
    await fortune.finish("似乎什么都没有")
  if args.list:
    total_weight = sum(i.weight for i in files)
    files.sort(key=lambda x: -x.weight)
    await fortune.finish("\n".join(
      f"{round(i.weight / total_weight * 100, 2)}% {i.name} {i.count}" for i in files))
  file = random.choices(files, [i.weight for i in files])[0]
  with open(os.path.join(config.fortunes, file.name)) as f:
    f.seek(file.choice)
    text = strfile.read_raw_text(f, file.header.delim)
  if file.header.rotated:
    text = codecs.encode(text, "rot13")
  text = strip_033(text)
  if args.source:
    text = f"({file.name})\n%\n{text}"
  await fortune.finish(text)
