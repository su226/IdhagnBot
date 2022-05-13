from typing import cast
from util import context
from apscheduler.schedulers.base import BaseScheduler
from aiohttp import ClientSession
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg
from . import util, contents
import nonebot
import time

scheduler: BaseScheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler
driver = nonebot.get_driver()
info_api = "https://api.bilibili.com/x/space/acc/info?mid={uid}"
list_api = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}&offset_dynamic_id={offset}"
detail_api = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?dynamic_id={id}"

@driver.on_startup
async def startup():
  async with ClientSession() as http:
    for user in util.CONFIG.users:
      try:
        user._name = (await (await http.get(info_api.format(uid=user.uid))).json())["data"]["name"]
      except: # 防止作为系统服务开机时出现网络错误，获取不到名字而导致整个功能出错
        user._name = f"未知_{user.uid}"
      user._time = time.time()
      logger.info(f"B站动态: {user.uid} -> {user._name}")

async def new_activities(http: ClientSession, user: util.User):
  offset = 0
  while True:
    data = (await (await http.get(list_api.format(uid=user.uid, offset=offset))).json())["data"]
    for card in data["cards"]:
      # 更新用户名（防止启动时出现网络错误或UP主改了名字）
      user._name = card["desc"]["user_profile"]["info"]["uname"]
      if card["desc"]["timestamp"] <= user._time:
        return
      yield card
    if not data["has_next"]:
      return
    offset = data["next_offset"]

@scheduler.scheduled_job("interval", seconds=util.CONFIG.interval)
async def check():
  bot = cast(Bot, nonebot.get_bot())
  async with ClientSession() as http:
    for user in util.CONFIG.users:
      logger.debug(f"检查 {user._name} 的动态更新")
      async for activity in new_activities(http, user):
        activity_id = activity["desc"]["dynamic_id_str"]
        try:
          message = contents.handle(activity)
        except util.IgnoredException as e:
          logger.info(f"{user._name} 的动态 {activity_id} 已被忽略: {e}")
          continue
        logger.info(f"推送 {user._name} 的动态 {activity_id}")
        for target in user.targets:
          if isinstance(target, util.GroupTarget):
            await bot.send_group_msg(group_id=target.group, message=message)
          else:
            await bot.send_private_msg(user_id=target.user, message=message)
      user._time = time.time()

force_push = nonebot.on_command("推送动态", permission=context.Permission.ADMIN)
force_push.__cmd__ = "推送动态"
force_push.__brief__ = "强制推送B站动态"
force_push.__doc__ = '''\
/推送动态 <动态号>
动态的动态号是t.bilibili.com后面的数字
视频的动态号只能通过API获取（不是AV或BV号）'''
force_push.__perm__ = context.Permission.ADMIN
@force_push.handle()
async def handle_force_push(bot: Bot, event: Event, args: Message = CommandArg()):
  args = str(args).rstrip()
  ctx = context.get_event_context(event)
  if len(args) == 0:
    await force_push.send(force_push.__doc__)
    return
  async with ClientSession() as http:
    data = (await (await http.get(detail_api.format(id=args))).json())["data"]
  if not "card" in data:
    await force_push.send("无法获取这条动态")
    return
  message = contents.handle(data["card"])
  real_ctx = getattr(event, "group_id", -1)
  if ctx != real_ctx:
    await bot.send_group_msg(group_id=ctx, message=message)
    await force_push.send(f"已推送到 {context.GROUP_IDS[ctx].name}")
  else:
    await force_push.send(Message(message))

check_now = nonebot.on_command("检查动态", permission=context.Permission.ADMIN)
check_now.__cmd__ = "检查动态"
check_now.__brief__ = "立即检查B站动态更新"
check_now.__perm__ = context.Permission.ADMIN
@check_now.handle()
async def handle_check_now():
  await check()
  await check_now.send(f"检查动态更新完成")
