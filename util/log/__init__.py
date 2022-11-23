import linecache
import os
import sys
import warnings
from datetime import time, timedelta
from io import StringIO
from typing import TYPE_CHECKING, List, Literal, Optional, Tuple, Union

from loguru import logger
from pydantic import BaseModel, Field

from util import configs

if TYPE_CHECKING:
  from loguru import Record


Level = Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]


class Target(BaseModel):
  level: Union[Level, int] = "INFO"
  fold_nonebot: bool = True
  format: str = "<g>{time:HH:mm:ss}</g>|<lvl>{level:8}</lvl>| <c>{name}</c> - {message}"
  colorize: Optional[bool] = None
  backtrace: bool = True
  diagnose: bool = False


class FileTarget(Target):
  file: str
  rotation: Union[str, int, time, timedelta, None] = None
  retention: Union[str, int, timedelta, None] = None
  compression: Union[str, None] = None
  encoding: str = "utf8"
  newline: Literal[None, '\r', '\n', '\r\n'] = None


class SpecialTarget(Target):
  type: Literal["stdout", "stderr", "syslog"] = "stdout"


class Config(BaseModel):
  sinks: List[Union[FileTarget, SpecialTarget]] = Field(default_factory=lambda: [SpecialTarget()])
  warnings_as_log: bool = True
  stdio_as_log: bool = False


class LoggerStream:
  def __init__(self, name: str, level: Union[str, int]):
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


CONFIG = configs.SharedConfig("log", Config, "eager")
showwarning_orig = warnings._showwarnmsg_impl  # type: ignore


@CONFIG.onload()
def config_onload(_: Optional[Config], cur: Config) -> None:
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
    def filter(
      record: "Record",
      level=logger.level(sink.level.upper()).no if isinstance(sink.level, str) else sink.level
    ) -> bool:
      if sink.fold_nonebot and (record["name"] or "").startswith("nonebot."):
        record["name"] = "nonebot"
      return record["level"].no >= level

    if isinstance(sink, SpecialTarget):
      if sink.type == "stdout":
        real_sink = sys.__stdout__
      elif sink.type == "stderr":
        real_sink = sys.__stderr__
      else:
        from .syslog import syslog_handler
        real_sink = syslog_handler
      kw = {}
    else:
      real_sink = sink.file
      kw = {
        "rotation": sink.rotation,
        "retention": sink.retention,
        "compression": sink.compression,
        "encoding": sink.encoding,
        "newline": sink.newline,
      }

    logger.add(
      real_sink,
      filter=filter,
      format=sink.format,
      colorize=sink.colorize,
      diagnose=sink.diagnose,
      backtrace=sink.backtrace,
      **kw
    )


def init():
  CONFIG()


def colorize_filename(filename: str) -> Tuple[str, str]:
  if filename.startswith("<"):
    return filename, ""
  dirname, basename = os.path.split(filename)
  return f"{dirname}{os.path.sep}", basename


def showwarning(msg: warnings.WarningMessage) -> None:
  line = msg.line
  if line is None:
    line = linecache.getline(msg.filename, msg.lineno)
  line = line.strip()
  category = msg.category.__name__
  message = str(msg.message).strip()
  dirname, basename = colorize_filename(msg.filename)
  log = logger.opt(colors=True, depth=2)  # 不使用 f-string 是防止 loguru 转义问题
  log.warning("<b><y>{}</y>: {}</b>", category, message)
  log.warning("  <g>{}<b>{}</b></g>:<y>{}</y>", dirname, basename, msg.lineno)
  if line:
    log.warning("    {}", line)
  if msg.source is not None:
    try:
      import tracemalloc
    except ImportError:
      return
    if not tracemalloc.is_tracing():
      log.warning("启用 tracemalloc 以查看对象分配栈。")
    elif (tb := tracemalloc.get_object_traceback(msg.source)):
      log.warning("<b><y>对象分配于</y>:</b>")
      for frame in tb:
        dirname, basename = colorize_filename(frame.filename)
        log.warning("  <g>{}<b>{}</b></g>:<y>{}</y>", dirname, basename, frame.lineno)
        line = linecache.getline(frame.filename, frame.lineno).strip()
        log.warning("    {}", line)
