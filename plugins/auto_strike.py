from datetime import date, datetime
from datetime import time as time_

import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Message
from pydantic import Field

from util.config import BaseConfig, BaseState

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class Config(BaseConfig):
  __file__ = "auto_strike"
  groups: list[int] = Field(default_factory=list)
  time: time_ = time_(4, 0, 0)
  message: str = "续火"


class State(BaseState):
  __file__ = "auto_strike"
  last_strike: dict[int, date] = Field(default_factory=dict)


CONFIG = Config.load()
STATE = State.load()

driver = nonebot.get_driver()


async def strike(bot: Bot, ontime: bool = True):
  ontime_str = "准时" if ontime else "超时补发"
  cur_date = date.today()
  for group in CONFIG.groups:
    if group not in STATE.last_strike or STATE.last_strike[group] < cur_date:
      logger.info(f"自动续火: {group}, {ontime_str}")
      await bot.send_group_msg(group_id=group, message=Message(CONFIG.message))
      STATE.last_strike[group] = cur_date
  STATE.dump()


@driver.on_bot_connect
async def on_bot_connect(bot: Bot):
  if datetime.now().time() > CONFIG.time:
    await strike(bot, False)
  scheduler.add_job(
    strike, "cron", (bot,),
    hour=CONFIG.time.hour, minute=CONFIG.time.minute, second=CONFIG.time.second)
