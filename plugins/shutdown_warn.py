import os
import time
from typing import Optional

import nonebot
from loguru import logger
from nonebot.adapters import Bot

from util import misc

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

driver = nonebot.get_driver()
bot_crash_time: Optional[float] = None
backend_crash_time: Optional[float] = None


@driver.on_startup
async def on_startup() -> None:
  global bot_crash_time
  if os.path.exists("states/poweroff_warn.txt"):
    with open("states/poweroff_warn.txt") as f:
      bot_crash_time = float(f.read())
  write_timestamp()


@driver.on_bot_connect
async def on_bot_connect(bot: Bot) -> None:
  global bot_crash_time
  if bot_crash_time is not None:
    crash_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(bot_crash_time))
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    bot_crash_time = None
    prefix = f"机器人在 {crash_str} 到 {now_str} 之间可能有非正常退出"
    if driver.env == "prod":
      logger.warning(prefix + "，将向超管发送警告！")
      message = prefix + "，请注意！"
      for user in misc.superusers():
        await bot.send_private_msg(user_id=user, message=message)
    else:
      logger.info(prefix + "，但当前处于调试模式，将不会发送警告。")
  global backend_crash_time
  if backend_crash_time is not None:
    backend_crash_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(backend_crash_time))
    prefix = f"后端在 {backend_crash_str} 左右断开"
    logger.warning(prefix + "，将向超管发送警告！")
    message = prefix + "，请注意！"
    for user in misc.superusers():
      await bot.send_private_msg(user_id=user, message=message)
    backend_crash_time = None


@scheduler.scheduled_job("interval", minutes=1)
def write_timestamp():
  with open("states/poweroff_warn.txt", "w") as f:
    f.write(str(time.time()))


@driver.on_bot_disconnect
async def on_bot_disconnect(bot: Bot) -> None:
  global backend_crash_time
  backend_crash_time = time.time()


@driver.on_shutdown
async def on_shutdown():
  os.remove("states/poweroff_warn.txt")
