import linecache
import os
import sys
import warnings
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

  def write(self, buffer: str):
    for line in buffer.rstrip().splitlines():
      logger.opt(depth=1, colors=True).log(self.level, self.prefix + " | {}", line)

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
    sys.stdout = LoggerStream("<b>STDOUT</b>", "INFO")
    sys.stderr = LoggerStream("<b><r>STDERR</r></b>", "ERROR")
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
  if (path := os.path.split(filename))[0]:
    dirname = path[0].rstrip(os.path.sep + (os.path.altsep or ""))
    filename = f"{dirname}{os.path.sep}<b>{path[1]}</b>"
  log = logger.opt(colors=True, depth=2)
  log.warning(f"<b><y>{category.__name__}</y>: {str(message).strip()}</b>")
  log.warning(f"<g>{filename}</g>:<y>{lineno}</y>")
  if line:
    log.warning(line)
