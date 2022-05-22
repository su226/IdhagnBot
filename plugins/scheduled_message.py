import random
import time
from datetime import datetime
from typing import cast

import nonebot
from apscheduler.schedulers.base import Job
from apscheduler.triggers.date import DateTrigger
from loguru import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.adapters.onebot.v11.event import Sender
from nonebot.message import handle_event
from nonebot.params import CommandArg
from pydantic import Field

from util import command, context
from util.config import BaseModel, BaseState

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class Scheduled(BaseModel):
  user: int
  message: str
  date: datetime

  async def send(self, group: int, id: str):
    bot = nonebot.get_bot()
    message = "/" + self.message
    await handle_event(bot, GroupMessageEvent(
      time=int(time.time()),
      self_id=int(bot.self_id),
      post_type="message",
      sub_type="normal",
      user_id=self.user,
      message_type="group",
      message_id=0,
      message=Message(message),
      raw_message=message,
      font=0,
      sender=Sender(),
      group_id=group))
    STATE.del_scheduled(group, id)

  def schedule(self, ctx: int, id: str):
    scheduler.add_job(
      self.send, "date", (ctx, id), id=f"scheduled_message_{id}", run_date=self.date)


class State(BaseState):
  __file__ = "scheduled_message"
  scheduled: dict[int, dict[str, Scheduled]] = Field(default_factory=dict)

  def len_scheduled(self, ctx: int) -> int:
    if ctx not in self.scheduled:
      return 0
    return len(self.scheduled[ctx])

  def has_scheduled(self, ctx: int, id: str) -> bool:
    if ctx not in self.scheduled:
      return False
    return id in self.scheduled[ctx]

  def del_scheduled(self, ctx: int, id: str):
    del self.scheduled[ctx][id]
    if not len(self.scheduled[ctx]):
      del self.scheduled[ctx]
    self.dump()

  def set_scheduled(self, ctx: int, id: str, user: int, message: str, date: datetime):
    if ctx not in self.scheduled:
      self.scheduled[ctx] = {}
    scheduled = Scheduled(user=user, message=message, date=date)
    self.scheduled[ctx][id] = scheduled
    self.dump()
    scheduled.schedule(ctx, id)


STATE = State.load()

driver = nonebot.get_driver()
now = datetime.now()
expired: list[tuple[int, str]] = []
for ctx, messages in STATE.scheduled.items():
  for id, msg in messages.items():
    if msg.date <= now:
      logger.warning(f"ID 为 {id} 的定时任务已过期，其内容为：{msg.message}")
      expired.append((ctx, id))
    else:
      msg.schedule(ctx, id)
for ctx, id in expired:
  STATE.del_scheduled(ctx, id)


def ellipsis(content: str, limit: int) -> str:
  if len(content) > limit:
    return content[:limit - 3] + "..."
  return content


def get_message(msg: Message) -> str:
  texts = []
  for seg in msg:
    texts.append(seg.data["text"] if seg.is_text() else str(seg))
  return "".join(texts)


schedule = (
  command.CommandBuilder("schedule", "定时", "schedule")
  .in_group()
  .level("super")
  .brief("设置定时任务")
  .usage('''\
/定时 <时间> <命令> - 添加定时任务
/定时 列表|list - 显示定时任务
/定时 预览|preview <任务ID> - 预览定时任务
/定时 取消|cancel <任务ID> - 取消定时任务''')
  .build())


@schedule.handle()
async def handle_schedule(event: MessageEvent, msg: Message = CommandArg()):
  args = get_message(msg).rstrip().split(None, 1)
  ctx = context.get_event_context(event)
  if len(args) == 0:
    await schedule.send("运行 /帮助 定时 查看使用说明")
  elif args[0] in ("列表", "list"):
    if not STATE.len_scheduled(ctx):
      await schedule.send("没有定时任务")
      return
    segments = ["所有定时任务:"]
    for id, content in STATE.scheduled[ctx].items():
      job = cast(Job, scheduler.get_job(f"scheduled_message_{id}"))
      trigger = cast(DateTrigger, job.trigger)
      segments.append(f"{id} {trigger.run_date.isoformat('T')} {ellipsis(content.message, 16)}")
    await schedule.send("\n".join(segments))
  elif args[0] in ("预览", "preview"):
    if len(args) < 2:
      await schedule.send("/定时 预览|preview <任务ID>")
      return
    id = args[1]
    if not STATE.has_scheduled(ctx, id):
      await schedule.send("没有这个定时任务")
      return
    await schedule.send(STATE.scheduled[ctx][id].message)
  elif args[0] in ("取消", "cancel"):
    if len(args) < 2:
      await schedule.send("/定时 取消|cancel <任务ID>")
      return
    id = args[1]
    if not STATE.has_scheduled(ctx, id):
      await schedule.send("没有这条定时任务")
      return
    scheduler.remove_job(f"scheduled_message_{id}")
    STATE.del_scheduled(ctx, id)
    await schedule.send("已取消定时任务")
  else:
    if len(args) < 2:
      await schedule.send("/定时 <时间> <命令>")
      return
    try:
      date = datetime.fromisoformat(args[0])
    except ValueError:
      await schedule.send("时间格式无效")
      return
    if date < datetime.now():
      await schedule.send("目标时间比当前时间早")
      return
    id = format(random.randint(0, 0xffffffff), "08x")
    STATE.set_scheduled(ctx, id, event.user_id, args[1], date)
    await schedule.send(f"已设置在 {date} 时在 {context.GROUP_IDS[ctx].name} 中执行的定时任务，ID 为 {id}")
