from core_plugins.context.typing import Context
from apscheduler.schedulers.base import BaseScheduler
from aiohttp import ClientSession
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg
from . import util, contents
import nonebot
import time

context: Context = nonebot.require("context")
scheduler: BaseScheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler
driver = nonebot.get_driver()
info_api = "https://api.bilibili.com/x/space/acc/info?mid={uid}"
list_api = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}&offset_dynamic_id={offset}"
detail_api = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?dynamic_id={id}"

@driver.on_startup
async def startup():
  async with ClientSession() as http:
    for user in util.config["users"]:
      user["name"] = (await (await http.get(info_api.format(uid=user["uid"]))).json())["data"]["name"]
      user["time"] = time.time()
      logger.info(f"B站动态: {user['uid']} -> {user['name']}")

async def new_activities(http: ClientSession, uid: int, timestamp: float):
  offset = 0
  while True:
    data = (await (await http.get(list_api.format(uid=uid, offset=offset))).json())["data"]
    for card in data["cards"]:
      if card["desc"]["timestamp"] <= timestamp:
        return
      yield card
    if not data["has_next"]:
      return
    offset = data["next_offset"]

@scheduler.scheduled_job("interval", seconds=util.config["interval"])
async def check():
  bot = nonebot.get_bot()
  async with ClientSession() as http:
    for user in util.config["users"]:
      logger.info(f"检查 {user['name']} 的动态更新")
      async for activity in new_activities(http, user['uid'], user['time']):
        message = contents.handle(activity)
        for target in user["targets"]:
          if "group" in target:
            await bot.call_api("send_group_msg", group_id=target["group"], message=message)
          else:
            await bot.call_api("send_private_msg", user_id=target["group"], message=message)
      user['time'] = time.time()

force_push = nonebot.on_command("推送动态", permission=context.ADMIN)
force_push.__cmd__ = "推送动态"
force_push.__brief__ = "强制推送B站动态"
force_push.__doc__ = "/推送动态 <动态号>"
force_push.__perm__ = context.ADMIN
@force_push.handle()
async def handle_force_push(bot: Bot, event: Event, args: Message = CommandArg()):
  args = str(args).rstrip()
  ctx = context.get_context(event)
  if len(args) == 0:
    await force_push.send("用法: /推送动态 <动态号>")
    return
  async with ClientSession() as http:
    data = (await (await http.get(detail_api.format(id=args))).json())["data"]
  if not "card" in data:
    await force_push.send("无法获取这条动态")
    return
  message = contents.handle(data["card"])
  if ctx == context.PRIVATE:
    await force_push.send(Message(message))
  else:
    await bot.send_group_msg(group_id=ctx, message=message)
    await force_push.send(f"已推送到 {context.get_group_name(ctx)}")

contexts = list(util.groups.keys())
check_now = nonebot.on_command("检查动态", context.in_context_rule(*contexts), permission=context.ADMIN)
check_now.__cmd__ = "检查动态"
check_now.__brief__ = "立即检查B站动态更新"
check_now.__ctx__ = contexts
check_now.__perm__ = context.ADMIN
@check_now.handle()
async def handle_check_now():
  await check_now.send(f"开始检查动态更新")
  await check()
  await check_now.send(f"检查动态更新完成")
