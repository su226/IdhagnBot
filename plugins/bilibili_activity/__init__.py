import asyncio
import time
from collections import deque
from datetime import datetime, timedelta
from typing import AsyncGenerator, Deque, List, Optional, Tuple, cast

import nonebot
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_MISSED, JobEvent
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg

from util import command, context
from util.api_common import bilibili_activity

from . import common, contents

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

driver = nonebot.get_driver()
queue: Deque[common.User] = deque()


@common.CONFIG.onload()
def onload(prev: Optional[common.Config], curr: common.Config) -> None:
  global queue
  queue = deque()
  for i in curr.users:
    queue.append(i)
  if curr.grpc:
    delta = timedelta(seconds=1)
  else:
    delta = timedelta(seconds=curr.interval)
  schedule(datetime.now() + delta)


def schedule(date: datetime) -> None:
  async def check_activity() -> None:
    try:
      bot = cast(Bot, nonebot.get_bot())
    except ValueError:
      return
    try:
      await try_check_all(bot)
    except asyncio.CancelledError:
      pass  # 这里仅仅是防止在关闭机器人时日志出现 CancelledError
  scheduler.add_job(
    check_activity, "date", id="bilibili_activity", replace_existing=True, run_date=date
  )


def schedule_next(event: JobEvent) -> None:
  if event.job_id == "bilibili_activity":
    schedule(datetime.now() + timedelta(seconds=common.CONFIG().interval))
scheduler.add_listener(schedule_next, EVENT_JOB_EXECUTED | EVENT_JOB_MISSED)


@driver.on_bot_connect
async def on_bot_connect() -> None:
  common.CONFIG()


async def new_activities(user: common.User) -> AsyncGenerator[bilibili_activity.Activity, None]:
  offset = ""
  use_grpc = common.CONFIG().grpc
  while offset is not None:
    if use_grpc:
      raw, next_offset = await bilibili_activity.grpc_fetch(user.uid, offset)
      activities = [bilibili_activity.Activity.grpc_parse(x) for x in raw]
    else:
      raw, next_offset = await bilibili_activity.json_fetch(user.uid, offset)
      activities = [bilibili_activity.Activity.json_parse(x) for x in raw]
    for activity in activities:
      user._name = activity.name
      is_new = (
        not user._offset or int(activity.id) > int(user._offset)
        if activity.time is None
        else activity.time > user._time
      )
      if is_new:
        yield activity
      elif not activity.top:
        return
    offset = next_offset


async def try_check(bot: Bot, user: common.User) -> int:
  async def try_send(
    activity: bilibili_activity.Activity, message: Message, target: common.AnyTarget
  ) -> None:
    if isinstance(target, common.GroupTarget):
      kw = {"group_id": target.group}
    else:
      kw = {"user_id": target.user}
    try:
      await bot.send_msg(message=message, **kw)
    except ActionFailed:
      logger.exception(
        f"推送 {user._name}({user.uid}) 的动态 {activity.id} 到目标 {target} 失败！\n"
        f"动态内容: {activity}"
      )
      try:
        await bot.send_msg(message=(
          f"{user._name} 更新了一条动态，但在推送时发送消息失败。"
          f"https://t.bilibili.com/{activity.id}"
        ), **kw)
      except ActionFailed:
        pass

  async def try_send_all(activity: bilibili_activity.Activity) -> None:
    logger.info(f"推送 {user._name}({user.uid}) 的动态 {activity.id}")
    try:
      message = await contents.format(activity)
    except common.IgnoredException:
      logger.info(f"{user._name}({user.uid}) 的动态 {activity.id} 含有忽略的关键字")
      return
    except Exception:
      logger.exception(
        f"格式化 {user._name}({user.uid}) 的动态 {activity.id} 失败！\n"
        f"动态内容: {activity}"
      )
      message = Message(MessageSegment.text(
        f"{user._name} 更新了一条动态，但在推送时格式化消息失败。"
        f"https://t.bilibili.com/{activity.id}"
      ))
    await asyncio.gather(*[try_send(activity, message, target) for target in user.targets])

  if user._offset == "-1" and common.CONFIG().grpc:
    try:
      raw, _ = await bilibili_activity.grpc_fetch(user.uid)
      activities = [bilibili_activity.Activity.grpc_parse(x) for x in raw]
      if len(activities) > 1:
        user._offset = str(max(int(activities[0].id), int(activities[1].id)))
      elif activities:
        user._offset = activities[0].id
      else:
        user._offset = ""
      if activities:
        user._name = activities[0].name
      logger.success(f"初始化 {user._name}({user.uid}) 的动态推送完成 {user._offset}")
    except Exception:
      logger.exception(f"初始化 {user.uid} 的动态推送失败")
    return 0

  try:
    activities: List[bilibili_activity.Activity] = []
    async for activity in new_activities(user):
      activities.append(activity)
    activities.reverse()
    for activity in activities:
      user._offset = activity.id
      await try_send_all(activity)
    user._time = time.time()
    logger.debug(f"检查 {user._name}({user.uid}) 的动态更新完成")
    return len(activities)
  except Exception:
    logger.exception(f"检查 {user._name}({user.uid}) 的动态更新失败")
    return 0


async def try_check_all(bot: Bot, concurrency: Optional[int] = None) -> Tuple[int, int]:
  if concurrency is None:
    concurrency = common.CONFIG().concurrency
  queue_ = queue
  if concurrency == 0:
    users = list(queue_)
    queue_.clear()
  else:
    users = []
    while queue_ and len(users) < concurrency:
      users.append(queue_.popleft())
  results = await asyncio.gather(*[try_check(bot, user) for user in users])
  queue_.extend(users)
  return len([x for x in results if x]), sum(results)


force_push = (
  command.CommandBuilder("bilibili_activity.force_push", "推送动态")
  .level("admin")
  .brief("强制推送B站动态")
  .usage('''\
/推送动态 <动态号>
动态的动态号是t.bilibili.com后面的数字
视频的动态号只能通过API获取（不是AV或BV号）''')
  .build()
)
@force_push.handle()
async def handle_force_push(bot: Bot, event: Event, arg: Message = CommandArg()) -> None:
  args = arg.extract_plain_text().rstrip()
  if len(args) == 0:
    await force_push.finish(force_push.__doc__)
  config = common.CONFIG()
  try:
    if config.grpc:
      activity = bilibili_activity.Activity.grpc_parse(await bilibili_activity.grpc_get(args))
    else:
      activity = bilibili_activity.Activity.json_parse(await bilibili_activity.json_get(args))
  except Exception:
    await force_push.finish("无法获取这条动态")
  message = await contents.format(activity)
  ctx = context.get_event_context(event)
  real_ctx = getattr(event, "group_id", -1)
  if ctx != real_ctx:
    await bot.send_group_msg(group_id=ctx, message=message)
    name = context.CONFIG().groups[ctx]._name
    await force_push.finish(f"已推送到 {name}")
  else:
    await force_push.finish(Message(message))


check_now = (
  command.CommandBuilder("bilibili_activity.check_now", "检查动态")
  .level("admin")
  .brief("立即检查B站动态更新")
  .build()
)
@check_now.handle()
async def handle_check_now(bot: Bot):
  users, activities = await try_check_all(bot, 0)
  if users:
    await check_now.finish(f"检查动态更新完成，推送了 {users} 个UP主的 {activities} 条动态。")
  else:
    await check_now.finish("检查动态更新完成，没有可推送的内容。")
