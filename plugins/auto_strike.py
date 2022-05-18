from pydantic import Field
from util.config import BaseConfig, BaseState
from apscheduler.schedulers.base import BaseScheduler
from datetime import date, time, datetime
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.log import logger
import nonebot

_time = time
class Config(BaseConfig):
  __file__ = "auto_strike"
  groups: list[int] = Field(default_factory=list)
  time: _time = _time(4, 0, 0)
  message: str = "续火"
del _time

class State(BaseState):
  __file__ = "auto_strike"
  last_strike: dict[int, date] = Field(default_factory=dict)

CONFIG = Config.load()
STATE = State.load()

scheduler: BaseScheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler
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
  scheduler.add_job(strike, "cron", (bot,), hour=CONFIG.time.hour, minute=CONFIG.time.minute, second=CONFIG.time.second)
