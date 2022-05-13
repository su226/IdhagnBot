from typing import TYPE_CHECKING, Any
import argparse
import sys

from pydantic import BaseModel, Field
from nonebot.adapters.onebot.v11 import Adapter
from nonebot.log import logger, logger_id
import nonebot

if TYPE_CHECKING:
  from loguru import Record

from util import config_v2

class LogOverride(BaseModel):
  fold_nonebot: bool = True
  format: str = "<g>{time:HH:mm:ss}</g>|<lvl>{level:8}</lvl>| <c>{name}</c> - {message}"
  level: str | int = "INFO"

class Config(BaseModel):
  nonebot: dict[str, Any] = Field(default_factory=dict)
  log_override: LogOverride | None = LogOverride()

CONFIG = config_v2.SharedConfig("bot", Config, False)

_config = CONFIG()
if (_override := _config.log_override) is not None:
  def loguru_filter(record: "Record") -> bool:
    if _override.fold_nonebot and (record["name"] or "").startswith("nonebot."):
      record["name"] = "nonebot"
    level = logger.level(_override.level.upper()).no if isinstance(_override.level, str) else _override.level
    return record["level"].no >= level
  logger.remove(logger_id)
  logger.add(
    sys.stderr,
    filter=loguru_filter,
    format=_override.format,
    colorize=True,
    diagnose=False)

parser = argparse.ArgumentParser()
parser.add_argument("--export-html")
args = parser.parse_args()

nonebot.init(_env_file="configs/nonebot.env", **_config.nonebot, apscheduler_autostart=True)
nonebot.get_driver().register_adapter(Adapter)
nonebot.load_plugins("plugins")
nonebot.load_plugins("user_plugins")

from util import help, permission
help.add_all_from_plugins()

if args.export_html:
  commands = help.CategoryItem.ROOT.html(False)
  permissions = permission.export_html()
  with open(args.export_html, "w") as f:
    f.write(f"<h2>命令帮助</h2>{commands}<h2>已知权限节点</h2>{permissions}")
  print("已导出所有命令帮助和权限节点")
else:
  nonebot.run()
