from typing import TYPE_CHECKING, Any
import sys

from pydantic import BaseModel, Field
from nonebot.adapters.onebot.v11 import Adapter
from nonebot.log import logger, logger_id
import nonebot

if TYPE_CHECKING:
  from loguru import Record

from util.config import BaseConfig

class LogOverride(BaseModel):
  fold_nonebot: bool = True
  format: str = "<g>{time:HH:mm:ss}</g>|<lvl>{level:8}</lvl>| <c>{name}</c> - {message}"
  level: str | int = "INFO"

class Config(BaseConfig, file="bot"):
  nonebot: dict[str, Any] = Field(default_factory=dict)
  log_override: LogOverride | None = LogOverride()

CONFIG = Config.load()

if CONFIG.log_override is not None:
  _override = CONFIG.log_override
  def loguru_filter(record: "Record") -> bool:
    if _override.fold_nonebot and (record["name"] or "").startswith("nonebot."):
      record["name"] = "nonebot"
    level = logger.level(_override.level.upper()).no if isinstance(_override.level, str) else _override.level
    return record["level"].no >= level
  logger.remove(logger_id)
  logger.add(
    sys.stderr,
    filter=loguru_filter,
    format=CONFIG.log_override.format,
    colorize=True,
    diagnose=False)

nonebot.init(_env_file="configs/nonebot.env", **CONFIG.nonebot, apscheduler_autostart=True)
nonebot.get_driver().register_adapter(Adapter)
nonebot.load_plugins("plugins")
nonebot.load_plugins("user_plugins")

from util.help import add_all_from_plugins
add_all_from_plugins()

if __name__ == "__main__":
  nonebot.run()
