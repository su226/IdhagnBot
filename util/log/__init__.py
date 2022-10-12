import linecache
import os
import sys
import tracemalloc
import warnings
from io import StringIO
from typing import TYPE_CHECKING, Literal

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
  stdio_as_log: bool = False


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


CONFIG = config_v2.SharedConfig("log", Config, "eager")
showwarning_orig = warnings._showwarnmsg_impl  # type: ignore


@CONFIG.onload()
def config_onload(_: Config | None, cur: Config) -> None:
  if cur.warnings_as_log:
    warnings._showwarnmsg_impl = showwarning  # type: ignore
  else:
    warnings._showwarnmsg_impl = showwarning_orig  # type: ignore
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


def colorize_filename(filename: str) -> str:
  if not filename.startswith("<"):
    dirname, basename = os.path.split(filename)
    filename = f"{dirname}{os.path.sep}<b>{basename}</b>"
  return filename


def showwarning(msg: warnings.WarningMessage) -> None:
  line = msg.line
  if line is None:
    line = linecache.getline(msg.filename, msg.lineno)
  line = line.strip()
  log = logger.opt(colors=True, depth=2)
  log.warning(f"<b><y>{msg.category.__name__}</y>: {str(msg.message).strip()}</b>")
  log.warning(f"  <g>{colorize_filename(msg.filename)}</g>:<y>{msg.lineno}</y>")
  if line:
    log.warning("    " + line)
  if msg.source is not None:
    if not tracemalloc.is_tracing():
      log.warning("启用 tracemalloc 以查看对象分配栈。")
    elif (tb := tracemalloc.get_object_traceback(msg.source)):
      log.warning("<b><y>对象分配于</y>:</b>")
      for frame in tb:
        log.warning(f"  <g>{colorize_filename(frame.filename)}</g>:<y>{frame.lineno}</y>")
        line = linecache.getline(frame.filename, frame.lineno).strip()
        log.warning("    " + line.strip())
