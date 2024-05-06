import asyncio
from contextlib import AsyncExitStack
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Type, Union

import nonebot
import nonebot.message
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.base import JobLookupError
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent
from nonebot.exception import ActionFailed, IgnoredException
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor
from nonebot.permission import Permission as BotPermission
from nonebot.rule import Rule
from nonebot.typing import T_DependencyCache, T_State
from pydantic import BaseModel, Field, PrivateAttr, RootModel

from . import configs, misc, permission

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402


class Group(RootModel[List[str]]):
  _name: str = PrivateAttr("")


class Config(BaseModel):
  groups: Dict[int, Group] = Field(default_factory=dict)
  private_limit: Set[int] = Field(default_factory=set)
  private_limit_whitelist: bool = False
  timeout: int = 600

  _names: Dict[str, int] = PrivateAttr(default_factory=dict)

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    for id, info in self.groups.items():
      for alias in info.root:
        self._names[alias] = id

  async def fetch_names(self) -> None:
    bot = nonebot.get_bot()
    for info in await bot.call_api("get_group_list"):
      if info["group_id"] in self.groups:
        self.groups[info["group_id"]]._name = info["group_name"]


class Context(BaseModel):
  group: int
  expire: datetime


class HasGroupCache:
  def __init__(self, user: int) -> None:
    self.created = datetime.now()
    self.user = user
    self.results: Dict[int, bool] = {}
    self.tasks: Dict[int, asyncio.Future[None]] = {}

  def clear(self) -> None:
    self.created = datetime.now()
    self.results.clear()
    self.tasks.clear()

  async def check(self, bot: Bot, *groups: int) -> bool:
    delta = datetime.now() - self.created
    if delta.seconds > 600:
      self.clear()
    for group in groups:
      if self.results.get(group, False) is True:
        return True
    tasks: List[asyncio.Future[None]] = []
    for group in groups:
      if group not in self.tasks:
        task = self.tasks[group] = asyncio.create_task(self.check_one(bot, group))
      else:
        task = self.tasks[group]
      tasks.append(task)
    try:
      await misc.first_result(tasks)
      return True
    except Exception:
      return False

  async def check_one(self, bot: Bot, group: int) -> None:
    try:
      await bot.get_group_member_info(group_id=group, user_id=self.user)
      self.results[group] = True
    except ActionFailed as e:
      self.results[group] = False
      # asyncio.CancelledError 不会有 Task exception was never retrieved
      raise asyncio.CancelledError from e


class State(BaseModel):
  contexts: Dict[int, Context] = Field(default_factory=dict)

  _has_group_cache: Dict[int, HasGroupCache] = PrivateAttr(default_factory=dict)

  def __init__(self, **kw: Any) -> None:
    super().__init__(**kw)
    now = datetime.now()
    expired = [id for id, context in self.contexts.items() if context.expire <= now]
    for user in expired:
      del self.contexts[user]


CONFIG = configs.SharedConfig("context", Config, "eager")
STATE = configs.SharedState("context", State, "eager")
PRIVATE = -1
ANY_GROUP = -2
JOBSTORE = "context_timeout"
scheduler.add_jobstore(MemoryJobStore(), JOBSTORE)
driver = nonebot.get_driver()


@STATE.onload()
def state_onload(prev: Optional[State], curr: State) -> None:
  scheduler.remove_all_jobs(JOBSTORE)
  for user, context in curr.contexts.items():
    scheduler.add_job(
      timeout_exit, "date", (user,), id=f"{JOBSTORE}_{user}", replace_existing=True,
      run_date=context.expire, jobstore=JOBSTORE
    )


@CONFIG.onload()
def config_onload(prev: Optional[Config], curr: Config) -> None:
  asyncio.create_task(curr.fetch_names())


@driver.on_bot_connect
async def on_bot_connect(bot: Bot) -> None:
  CONFIG()
  STATE()


@event_preprocessor
async def pre_event(event: Event, state: T_State):
  config = CONFIG()
  if (group_id := getattr(event, "group_id", None)) is not None:
    if group_id not in config.groups:
      raise IgnoredException("机器人在当前上下文不可用")
  elif (user_id := getattr(event, "user_id", None)) is not None:
    if config.private_limit_whitelist:
      if user_id not in config.private_limit:
        raise IgnoredException("私聊用户不在白名单内")
    else:
      if user_id in config.private_limit:
        raise IgnoredException("私聊用户在黑名单内")
    refresh_context(user_id)


def enter_context(uid: int, gid: int):
  state = STATE()
  state.contexts[uid] = Context(group=gid, expire=datetime.min)
  return refresh_context(uid)


def exit_context(uid: int) -> bool:
  try:
    scheduler.remove_job(f"{JOBSTORE}_{uid}", JOBSTORE)
  except JobLookupError:
    pass
  state = STATE()
  if uid in state.contexts:
    del state.contexts[uid]
    STATE.dump()
    return True
  return False


def get_uid_context(uid: int) -> int:
  context = STATE().contexts.get(uid, None)
  return context.group if context else PRIVATE


def get_event_context(event: Event) -> int:
  if (group_id := getattr(event, "group_id", None)) is not None:
    return group_id
  if (user_id := getattr(event, "user_id", None)) is not None:
    return get_uid_context(user_id)
  return -1


def refresh_context(uid: int):
  config = CONFIG()
  state = STATE()
  if uid not in state.contexts:
    return None
  date = datetime.now() + timedelta(seconds=config.timeout)
  state.contexts[uid].expire = date
  STATE.dump()
  return scheduler.add_job(
    timeout_exit, "date", (uid,), id=f"context_timeout_{uid}", replace_existing=True,
    run_date=date, jobstore=JOBSTORE
  )


async def timeout_exit(uid: int):
  if exit_context(uid):
    await nonebot.get_bot().call_api(
      "send_private_msg", user_id=uid,
      message=f"由于 {misc.format_time(CONFIG().timeout)}内未操作，已退出上下文"
    )


def in_group(ctx: int, *contexts: int) -> bool:
  for i in contexts:
    if i == ctx or (i == ANY_GROUP and ctx != PRIVATE):
      return True
  return len(contexts) == 0


def in_group_rule(*contexts: int) -> Rule:
  async def rule(event: Event) -> bool:
    return in_group(get_event_context(event), *contexts)
  return Rule(rule)


def has_group_rule(*groups: int) -> Rule:
  async def check(bot: Bot, event: Event) -> bool:
    if (group_id := getattr(event, "group_id", None)) is not None:
      return group_id in groups
    if (user_id := getattr(event, "user_id", None)) is not None:
      state = STATE()
      if user_id not in state._has_group_cache:
        state._has_group_cache[user_id] = HasGroupCache(user_id)
      return await state._has_group_cache[user_id].check(bot, *groups)
    return False
  return Rule(check)


async def get_event_level(bot: Bot, event: Event) -> permission.Level:
  if (user_id := getattr(event, "user_id", None)) is None:
    return permission.Level.MEMBER
  group_id = get_event_context(event)
  if (result := permission.get_override_level(bot, user_id, group_id)) is not None:
    return result
  if isinstance(event, GroupMessageEvent) and event.sender.role is not None:
    return permission.Level.parse(event.sender.role)
  return await permission.get_group_level(bot, user_id, group_id) or permission.Level.MEMBER


# XXX: 对 Nonebot 2 进行 Monkey Patch 以在 Permission 中拿到 State
_check_matcher_orig = nonebot.message._check_matcher
_current_state: ContextVar[T_State] = ContextVar("_current_state")
_current_stack: ContextVar[Optional[AsyncExitStack]] = ContextVar("_current_stack", default=None)
_current_dependency_cache: ContextVar[Optional[T_DependencyCache]] = ContextVar(
  "_current_dependency_cache", default=None
)
async def _check_matcher(
  Matcher: Type[Matcher],
  bot: "Bot",
  event: "Event",
  state: T_State,
  stack: Optional[AsyncExitStack] = None,
  dependency_cache: Optional[T_DependencyCache] = None,
) -> bool:
  token = _current_state.set(state)
  token2 = _current_stack.set(stack)
  token3 = _current_dependency_cache.set(dependency_cache)
  try:
    return await _check_matcher_orig(Matcher, bot, event, state, stack, dependency_cache)
  finally:
    _current_state.reset(token)
    _current_stack.reset(token2)
    _current_dependency_cache.reset(token3)
nonebot.message._check_matcher = _check_matcher


def build_permission(node: permission.Node, default: permission.Level) -> BotPermission:
  async def checker(bot: Bot, event: Event) -> bool:
    if (user_id := getattr(event, "user_id", None)) is None:
      return False
    event_level = await get_event_level(bot, event)
    state = _current_state.get(None)
    prefix = state["_prefix"]["command_start"] if state else None
    if (result := permission.check(
      node, user_id, get_event_context(event), event_level, prefix
    )) is not None:
      return result
    command_level = permission.get_node_level(node) or default
    return event_level >= command_level
  permission.register_for_export(node, default)
  return BotPermission(checker)


async def get_card_or_name(bot: Bot, group_id: Union[Event, int], user_id: int) -> str:
  if isinstance(group_id, Event):
    group_id = get_event_context(group_id)
  if group_id != -1:
    try:
      info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
      return info["card"] or info["nickname"]
    except ActionFailed:
      pass
  info = await bot.get_stranger_info(user_id=user_id)
  return info["nickname"]
