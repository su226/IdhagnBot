import linecache
import os
import sys
import warnings
from io import StringIO
from typing import TYPE_CHECKING, Literal, TextIO

from loguru import logger
from pydantic import BaseModel, Field

from util import config_v2

if TYPE_CHECKING:
  from loguru import Record


class Target(BaseModel):
  level: str | int = "INFO"
  fold_nonebot: bool = True
  format: str = "<g>{time:HH:mm:ss}</g>|<lvl>{level:8}</lvl>| <c>{name}</c> - {message}"


class FileTarget(Target):
  file: str


class SpecialTarget(Target):
  type: Literal["stdout", "stderr", "syslog"] = "stdout"


class Config(BaseModel):
  sinks: list[FileTarget | SpecialTarget] = Field(default_factory=lambda: [SpecialTarget()])
  warnings_as_log: bool = True
  stdio_as_log: bool = True


class LoggerStream:
  def __init__(self, name: str, level: str | int):
    self.prefix = name
    self.level = level
    self.buffer = StringIO()

  def write(self, buffer: str):
    *lines, last = buffer.split("\n")
    if lines:
      first, *lines = lines
      self.buffer.write(first)
      log = logger.opt(depth=1, colors=True)
      log.log(self.level, self.prefix + " | {}", self.buffer.getvalue())
      self.buffer.truncate(0)
      for line in lines:
        log.log(self.level, self.prefix + " | {}", line)
    self.buffer.write(last)

  def flush(self):
    pass


CONFIG = config_v2.SharedConfig("log", Config)
showwarning_orig = warnings.showwarning


@CONFIG.onload(False)
def config_onload(_: Config | None, cur: Config) -> None:
  if cur.warnings_as_log:
    warnings.showwarning = showwarning
  else:
    warnings.showwarning = showwarning_orig
  if cur.stdio_as_log:
    sys.stdout = LoggerStream("<lvl>STDOUT</lvl>", "INFO")
    sys.stderr = LoggerStream("<lvl>STDERR</lvl>", "ERROR")
  else:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

  logger.remove()
  for sink in cur.sinks:
    def filter(record: "Record") -> bool:
      if sink.fold_nonebot and (record["name"] or "").startswith("nonebot."):
        record["name"] = "nonebot"
      level = logger.level(sink.level.upper()).no if isinstance(sink.level, str) else sink.level
      return record["level"].no >= level

    if isinstance(sink, SpecialTarget):
      if sink.type == "stdout":
        real_sink = sys.__stdout__
      elif sink.type == "stderr":
        real_sink = sys.__stderr__
      else:
        from .syslog import syslog_handler
        real_sink = syslog_handler
    else:
      real_sink = sink.file

    logger.add(
      real_sink,
      filter=filter,
      format=sink.format,
      colorize=True,
      diagnose=False)


def init():
  CONFIG.load()


def showwarning(
  message: Warning | str, category: type[Warning], filename: str, lineno: int,
  file: TextIO | None = None, line: str | None = None
):
  if line is None:
    line = linecache.getline(filename, lineno)
  line = line.strip()
  if not filename.startswith("<"):
    dirname, basename = os.path.split(filename)
    dirname = dirname.rstrip(os.path.sep + (os.path.altsep or ""))
    filename = f"{dirname}{os.path.sep}<b>{basename}</b>"
  log = logger.opt(colors=True, depth=2)
  log.warning(f"<b><y>{category.__name__}</y>: {str(message).strip()}</b>")
  log.warning(f"<g>{filename}</g>:<y>{lineno}</y>")
  if line:
    log.warning(line)
