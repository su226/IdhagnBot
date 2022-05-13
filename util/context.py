from typing import cast
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

from apscheduler.schedulers.base import BaseScheduler
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent
from nonebot.exception import IgnoredException
from nonebot.permission import Permission as BotPermission
from nonebot.rule import Rule
from nonebot.message import event_preprocessor
import nonebot

from . import helper, permission
from util.config import BaseConfig, BaseModel, BaseState, Field

Permission = permission.Level
scheduler = cast(BaseScheduler, nonebot.require("nonebot_plugin_apscheduler").scheduler)

class Config(BaseConfig):
  __file__ = "context"
  groups: dict[int, list[str]] = Field(default_factory=dict)
  private_limit: set[int] = Field(default_factory=set)
  private_limit_whitelist: bool = False
  timeout: int = 600

class Context(BaseModel):
  group: int
  expire: datetime

class State(BaseState):
  __file__ = "context"
  contexts: dict[int, Context] = Field(default_factory=dict)

CONFIG = Config.load()
STATE = State.load()

@dataclass
class Group:
  id: int
  name: str
  aliases: list[str]

GROUP_IDS: dict[int, Group] = {}
GROUP_NAMES: dict[str, Group] = {}
PRIVATE = -1
ANY_GROUP = -2

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
  if (group_id := getattr(event, "group_id", None)) is not None:
    if group_id not in GROUP_IDS:
      raise IgnoredException("机器人在当前上下文不可用")
  elif (user_id := getattr(event, "user_id", None)) is not None:
    if CONFIG.private_limit_whitelist:
      if user_id not in CONFIG.private_limit:
        raise IgnoredException("私聊用户不在白名单内")
    else:
      if user_id in CONFIG.private_limit:
        raise IgnoredException("私聊用户在黑名单内")
    refresh_context(user_id)

def enter_context(uid: int, gid: int):
  STATE.contexts[uid] = Context(group=gid, expire=datetime.min)
  return refresh_context(uid)

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

def get_uid_context(uid: int) -> int:
  context = STATE.contexts.get(uid, None)
  return context.group if context else PRIVATE

def get_event_context(event: Event) -> int:
  if (group_id := getattr(event, "group_id", None)) is not None:
    return group_id
  if (user_id := getattr(event, "user_id", None)) is not None:
    return get_uid_context(user_id)
  return -1

def refresh_context(uid: int):
  if uid not in STATE.contexts:
    return None
  date = datetime.now() + timedelta(seconds=CONFIG.timeout)
  STATE.contexts[uid].expire = date
  STATE.dump()
  return scheduler.add_job(timeout_exit, "date", (uid,), id=f"context_timeout_{uid}", replace_existing=True, run_date=date)

async def timeout_exit(uid: int):
  if exit_context(uid):
    await nonebot.get_bot().call_api("send_private_msg", 
      user_id=uid,
      message=f"由于 {helper.format_time(CONFIG.timeout)}内未操作，已退出上下文")

for user, context in STATE.contexts.items():
  scheduler.add_job(timeout_exit, "date", (user,), id=f"context_timeout_{user}", replace_existing=True, run_date=context.expire)

def in_group(ctx: int, *contexts: int) -> bool:
  for i in contexts:
    if i == ctx or (i == ANY_GROUP and ctx != PRIVATE):
      return True
  return len(contexts) == 0

def in_group_rule(*contexts: int) -> Rule:
  async def rule(event: Event) -> bool:
    return in_group(get_event_context(event), *contexts)
  return Rule(rule)

async def has_group(bot: Bot, user: int, *groups: int) -> bool:
  tasks = [asyncio.create_task(bot.get_group_member_info(group_id=group, user_id=user)) for group in groups]
  done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
  return any(i.exception() is None for i in done)

def has_group_rule(*groups: int) -> Rule:
  async def check(bot: Bot, event: Event) -> bool:
    if (group_id := getattr(event, "group_id", None)) is not None:
      return group_id in groups
    if (user_id := getattr(event, "user_id", None)) is not None:
      return await has_group(bot, user_id, *groups)
    return False
  return Rule(check)

async def get_event_level(bot: Bot, event: Event) -> Permission:
  if (user_id := getattr(event, "user_id", None)) is None:
    return Permission.MEMBER
  group_id = get_event_context(event)
  if (result := permission.get_override_level(bot, user_id, group_id)) is not None:
    return result
  if isinstance(event, GroupMessageEvent) and event.sender.role is not None:
    return Permission.parse(event.sender.role)
  return await permission.get_group_level(bot, user_id, group_id) or Permission.MEMBER

def build_permission(node: permission.Node, default: permission.Level) -> BotPermission:
  permission.register_for_export(node, default)
  async def checker(bot: Bot, event: Event) -> bool:
    if (user_id := getattr(event, "user_id", None)) is None:
      return False
    if (result := permission.check(node, user_id, get_event_context(event))) is not None:
      return result
    command_level = permission.get_node_level(node) or default
    if command_level == permission.Level.MEMBER:
      return True
    return await get_event_level(bot, event) >= command_level
  return BotPermission(checker)
