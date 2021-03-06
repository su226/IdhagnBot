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
      logger.warning(f"ID ??? {id} ??????????????????????????????????????????{msg.message}")
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
  command.CommandBuilder("schedule", "??????", "schedule")
  .in_group()
  .level("super")
  .brief("??????????????????")
  .usage('''\
/?????? <??????> <??????> - ??????????????????
/?????? ??????|list - ??????????????????
/?????? ??????|preview <??????ID> - ??????????????????
/?????? ??????|cancel <??????ID> - ??????????????????''')
  .build())


@schedule.handle()
async def handle_schedule(event: MessageEvent, msg: Message = CommandArg()):
  args = get_message(msg).rstrip().split(None, 1)
  ctx = context.get_event_context(event)
  if len(args) == 0:
    await schedule.send("?????? /?????? ?????? ??????????????????")
  elif args[0] in ("??????", "list"):
    if not STATE.len_scheduled(ctx):
      await schedule.send("??????????????????")
      return
    segments = ["??????????????????:"]
    for id, content in STATE.scheduled[ctx].items():
      job = cast(Job, scheduler.get_job(f"scheduled_message_{id}"))
      trigger = cast(DateTrigger, job.trigger)
      segments.append(f"{id} {trigger.run_date.isoformat('T')} {ellipsis(content.message, 16)}")
    await schedule.send("\n".join(segments))
  elif args[0] in ("??????", "preview"):
    if len(args) < 2:
      await schedule.send("/?????? ??????|preview <??????ID>")
      return
    id = args[1]
    if not STATE.has_scheduled(ctx, id):
      await schedule.send("????????????????????????")
      return
    await schedule.send(STATE.scheduled[ctx][id].message)
  elif args[0] in ("??????", "cancel"):
    if len(args) < 2:
      await schedule.send("/?????? ??????|cancel <??????ID>")
      return
    id = args[1]
    if not STATE.has_scheduled(ctx, id):
      await schedule.send("????????????????????????")
      return
    scheduler.remove_job(f"scheduled_message_{id}")
    STATE.del_scheduled(ctx, id)
    await schedule.send("?????????????????????")
  else:
    if len(args) < 2:
      await schedule.send("/?????? <??????> <??????>")
      return
    try:
      date = datetime.fromisoformat(args[0])
    except ValueError:
      await schedule.send("??????????????????")
      return
    if date < datetime.now():
      await schedule.send("??????????????????????????????")
      return
    id = format(random.randint(0, 0xffffffff), "08x")
    STATE.set_scheduled(ctx, id, event.user_id, args[1], date)
    await schedule.send(f"???????????? {date} ?????? {context.GROUP_IDS[ctx].name} ???????????????????????????ID ??? {id}")
