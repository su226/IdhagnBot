import random
import time
from copy import deepcopy
from datetime import datetime

import nonebot
from apscheduler.jobstores.memory import MemoryJobStore
from loguru import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.adapters.onebot.v11.event import Sender
from nonebot.message import handle_event
from nonebot.params import CommandArg
from pydantic import BaseModel, Field

from util import command, configs, context, misc

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class Task(BaseModel):
  user: int
  message: str
  date: datetime

  async def send(self, group: int, id: str):
    bot = nonebot.get_bot()
    msg = Message(self.message)
    if not misc.is_command(msg):
      msg[0].data["text"] = misc.command_start() + msg[0].data["text"]
    await handle_event(bot, GroupMessageEvent(
      time=int(time.time()),
      self_id=int(bot.self_id),
      post_type="message",
      sub_type="normal",
      user_id=self.user,
      message_type="group",
      message_id=0,
      message=msg,
      original_message=deepcopy(msg),
      raw_message=str(msg),
      font=0,
      sender=Sender(),
      group_id=group
    ))
    del STATE(group).tasks[id]

  def schedule(self, ctx: int, id: str):
    scheduler.add_job(
      self.send, "date", (ctx, id), id=f"{JOBSTORE}_{id}", run_date=self.date,
      jobstore=JOBSTORE
    )


class State(BaseModel):
  tasks: dict[str, Task] = Field(default_factory=dict)


STATE = configs.GroupState("scheduled", State)
JOBSTORE = "scheduled_command"
scheduler.add_jobstore(MemoryJobStore(), JOBSTORE)
driver = nonebot.get_driver()


@STATE.onload()
def onload(prev: State | None, curr: State, group_id: int) -> None:
  scheduler.remove_all_jobs(JOBSTORE)
  now = datetime.now()
  expired: list[str] = []
  for id, msg in curr.tasks.items():
    if msg.date <= now:
      logger.warning(f"ID 为 {id} 的定时任务已过期，其内容为：{msg.message}")
      expired.append(id)
    else:
      msg.schedule(group_id, id)
  for id in expired:
    del curr.tasks[id]


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
  .build()
)
@schedule.handle()
async def handle_schedule(event: MessageEvent, msg: Message = CommandArg()):
  args = get_message(msg).rstrip().split(None, 1)
  if len(args) == 0:
    await schedule.finish("运行 /帮助 定时 查看使用说明")

  ctx = context.get_event_context(event)
  state = STATE(ctx)

  if args[0] in ("列表", "list"):
    if not state.tasks:
      await schedule.finish("没有定时任务")
    segments = ["所有定时任务:"]
    for id, content in state.tasks.items():
      segments.append(f"{id} {content.date:%Y-%m-%d %H:%M:%S} {ellipsis(content.message, 16)}")
    await schedule.finish("\n".join(segments))
  elif args[0] in ("预览", "preview"):
    if len(args) < 2:
      await schedule.finish("/定时 预览|preview <任务ID>")
    id = args[1]
    if id not in state.tasks:
      await schedule.finish("没有这个定时任务")
    await schedule.finish(state.tasks[id].message)
  elif args[0] in ("取消", "cancel"):
    if len(args) < 2:
      await schedule.finish("/定时 取消|cancel <任务ID>")
    id = args[1]
    if id not in state.tasks:
      await schedule.finish("没有这条定时任务")
    del state.tasks[id]
    STATE.dump(ctx)
    scheduler.remove_job(f"{JOBSTORE}_{id}")
    await schedule.finish("已取消定时任务")
  else:
    if len(args) < 2:
      await schedule.finish("/定时 <时间> <命令>")
    try:
      date = datetime.fromisoformat(args[0])
    except ValueError:
      await schedule.finish("时间格式无效")
    if date < datetime.now():
      await schedule.finish("目标时间比当前时间早")
    id = str(random.randint(1000000000, 9999999999))
    state.tasks[id] = task = Task(user=event.user_id, message=args[1], date=date)
    task.schedule(ctx, id)
    name = context.CONFIG().groups[context.get_event_context(event)]._name
    await schedule.finish(f"已设置在 {date} 时在 {name} 中执行的定时任务，ID 为 {id}")
