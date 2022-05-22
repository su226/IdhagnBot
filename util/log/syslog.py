# Windows上不能用syslog，所以单独放置这个模块
import syslog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from loguru import Message

__all__ = ["syslog_handler"]


def syslog_handler(message: "Message") -> None:
  levelno = message.record["level"].no
  if levelno >= 50:  # CRITICAL
    priority = syslog.LOG_CRIT
  elif levelno >= 40:  # ERROR
    priority = syslog.LOG_ERR
  elif levelno >= 30:  # WARNING
    priority = syslog.LOG_WARNING
  elif levelno >= 25:  # SUCCESS
    priority = syslog.LOG_NOTICE
  elif levelno >= 20:  # INFO
    priority = syslog.LOG_INFO
  else:  # DEBUG, TRACE
    priority = syslog.LOG_DEBUG
  syslog.syslog(priority, message)
