from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from apscheduler.schedulers.base import BaseScheduler
from datetime import datetime, timedelta
from util.config import BaseConfig, BaseModel, BaseState, Field
from enum import Enum
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.rule import Rule
from nonebot.log import logger
from nonebot.permission import Permission as BotPermission, SUPERUSER
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
import nonebot

class Config(BaseConfig):
  __file__ = "context"
  groups: dict[int, list[str]] = Field(default_factory=dict)

class Context(BaseModel):
  group: int
  expire: datetime

class State(BaseState):
  __file__ = "context"
  contexts: dict[int, Context] = Field(default_factory=dict)

@dataclass
class Group:
  id: int
  name: str
  aliases: list[str]

CONFIG = Config.load()
STATE = State.load()
GROUP_IDS: dict[int, Group] = {}
GROUP_NAMES: dict[str, Group] = {}

now = datetime.now()
expired = []
for user, context in STATE.contexts.items():
  if context.expire <= now:
    expired.append(user)
for user in expired:
  del STATE.contexts[user]

for id, aliases in CONFIG.groups.items():
  group = Group(id, f"未知_{id}", aliases)
  GROUP_IDS[id] = group
  for alias in aliases:
    GROUP_NAMES[alias] = group

driver = nonebot.get_driver()
@driver.on_bot_connect
async def bot_connect(bot: Bot):
  for info in await bot.call_api("get_group_list"):
    if info["group_id"] in GROUP_IDS:
      GROUP_IDS[info["group_id"]].name = info["group_name"]

@event_preprocessor
async def pre_event(event: Event):
  if hasattr(event, "group_id"):
    if event.group_id not in GROUP_IDS:
      raise IgnoredException("机器人在当前上下文不可用")
  elif hasattr(event, "user_id"):
    refresh_context(event.user_id)

def format_duration(seconds: int) -> str:
  minutes, seconds = divmod(seconds, 60)
  hours,   minutes = divmod(minutes, 60)
  days,    hours   = divmod(hours, 24)
  segments = []
  if days:
    segments.append(f"{days} 天")
  if hours:
    segments.append(f"{hours} 时")
  if minutes:
    segments.append(f"{minutes} 分")
  if seconds:
    segments.append(f"{seconds} 秒")
  return " ".join(segments)

class Permission(BotPermission, Enum):
  MEMBER = 0
  ADMIN = 1
  OWNER = 2
  SUPER = 3

  def __init__(self, value: int):
    super().__init__(self.check)

  def __lt__(self, other):
    if self.__class__ is other.__class__:
      return self.value < other.value
    return NotImplemented

  def __le__(self, other):
    if self.__class__ is other.__class__:
      return self.value <= other.value
    return NotImplemented

  async def check(self, bot: Bot, event: Event) -> bool:
    result = await get_permission(bot, event)
    return result >= self

  @classmethod
  def parse(cls, value: str) -> "Permission":
    return {
      "member": cls.MEMBER,
      "admin": cls.ADMIN,
      "owner": cls.OWNER,
      "super": cls.SUPER
    }[value]

PRIVATE = -1
ANY_GROUP = -2
scheduler: BaseScheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler
timeout = 600
timeout_str = format_duration(timeout)

def enter_context(uid: int, gid: int):
  STATE.contexts[uid] = Context(group=gid, expire=0)
  return refresh_context(uid)

def get_uid_context(uid: int) -> int:
  context = STATE.contexts.get(uid, None)
  return context.group if context else PRIVATE

def refresh_context(uid: int):
  if uid not in STATE.contexts:
    return None
  date = datetime.now() + timedelta(seconds=timeout)
  STATE.contexts[uid].expire = date
  STATE.dump()
  return scheduler.add_job(timeout_exit, "date", (uid,), id=f"context_timeout_{uid}", replace_existing=True, run_date=date)

def exit_context(uid: int) -> bool:
  try:
    scheduler.remove_job(f"context_timeout_{uid}")
  except:
    pass
  if uid in STATE.contexts:
    del STATE.contexts[uid]
    STATE.dump()
    return True
  return False

async def timeout_exit(uid: int):
  if exit_context(uid):
    await nonebot.get_bot().call_api("send_private_msg", 
      user_id=uid,
      message=f"由于 {timeout_str}内未操作，已退出上下文")

def get_event_context(event: Event) -> int:
  if hasattr(event, "group_id"):
    return event.group_id
  return get_uid_context(event.user_id)

def in_context(ctx: int, *contexts: int) -> bool:
  for i in contexts:
    if i == ctx or (i == ANY_GROUP and ctx != PRIVATE):
      return True
  return len(contexts) == 0

def in_context_rule(*contexts: int) -> Rule:
  async def rule(event: Event) -> bool:
    return in_context(get_event_context(event), *contexts)
  return Rule(rule)

members_cache: dict[int, dict[int, dict[str, Any]]] = defaultdict(lambda: {"__time__": 0})
cache_duration = 86400

async def get_permission(bot: Bot, event: Event) -> Permission:
  if await SUPERUSER(bot, event):
    return Permission.SUPER
  ctx = get_event_context(event)
  if ctx == PRIVATE:
    return Permission.MEMBER
  try:
    return Permission.parse(event.sender.role)
  except:
    pass
  try:
    member = await bot.get_group_member_info(group_id=ctx, user_id=event.user_id)
    return Permission.parse(member["role"])
  except:
    logger.exception("获取权限失败，这通常不应该发生！")
  return Permission.MEMBER

for user, context in STATE.contexts.items():
  scheduler.add_job(timeout_exit, "date", (user,), id=f"context_timeout_{user}", replace_existing=True, run_date=context.expire)