from apscheduler.schedulers.base import BaseScheduler
from nonebot.log import logger
from nonebot.adapters import Bot
import nonebot
import time
import os

scheduler: BaseScheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler
driver = nonebot.get_driver()

@driver.on_bot_connect
async def on_bot_connect(bot: Bot):
  if os.path.exists("states/poweroff_warn.txt"):
    with open("states/poweroff_warn.txt") as f:
      last_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(f.read())))
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S")
    if driver.env == "prod":
      logger.warning(f"机器人在 {last_time} 到 {cur_time} 之间可能有非正常退出，将向超管发送警告！")
      for user in driver.config.superusers:
        await bot.send_private_msg(user_id=user, message=f"机器人在 {last_time} 到 {cur_time} 之间可能有非正常退出，请注意！")
    else:
      logger.info("机器人可能非正常退出，但当前处于调试模式，将不会向超管发送警告。")
  write_timestamp()

@scheduler.scheduled_job("interval", minutes=1)
def write_timestamp():
  with open("states/poweroff_warn.txt", "w") as f:
    f.write(str(time.time()))

@driver.on_shutdown
async def on_shutdown():
  os.remove("states/poweroff_warn.txt")
