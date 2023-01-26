import asyncio
from datetime import date
from typing import Any, Dict, Set, Tuple

import nonebot
from aiohttp.client_exceptions import ClientError
from nonebot.adapters.onebot.v11 import (
  ActionFailed, Bot, Event, GroupRecallNoticeEvent, Message, MessageEvent
)
from nonebot.message import event_postprocessor, run_postprocessor, run_preprocessor
from nonebot.params import CommandArg
from nonebot.typing import T_State
from PIL import Image
from pydantic import BaseModel, Field, PrivateAttr
from pygtrie import Trie

from util import command, configs, context, imutil, misc, textutil


class QQBot(BaseModel):
  total: int = 0
  today: Tuple[int, date] = (0, date.min)
  total_by_group: Dict[int, int] = Field(default_factory=dict)
  today_by_group: Dict[int, Tuple[int, date]] = Field(default_factory=dict)


class State(BaseModel):
  qqbot: QQBot = Field(default_factory=QQBot)
  show_is_bot_disabled: Set[int] = Field(default_factory=set)


class Config(BaseModel):
  show_invaild_command: misc.EnableSet = misc.EnableSet.true()
  invaild_command_ignore: Dict[int, Set[str]] = Field(default_factory=dict)
  show_is_bot: misc.EnableSet = misc.EnableSet.true()
  show_exception: misc.EnableSet = misc.EnableSet.true()
  send_exception_to_superuser: misc.EnableSet = misc.EnableSet.true()
  _invaild_command_ignore: Dict[int, Trie] = PrivateAttr()

  def __init__(self, **data: Any) -> None:
    super().__init__(**data)
    self._invaild_command_ignore = {}
    for group_id, prefixes in self.invaild_command_ignore.items():
      self._invaild_command_ignore[group_id] = Trie((x, None) for x in prefixes)

  def has_ignored_prefix(self, group_id: int, message: Message) -> bool:
    return (
      message[0].is_text()
      and group_id in self.invaild_command_ignore
      and bool(self._invaild_command_ignore[group_id].shortest_prefix(str(message[0])))
    )


class ManualException(Exception):
  def __init__(self):
    super().__init__("管理员使用 /raise 手动触发了错误")


QQBOT_ID = 2854196310
CONFIG = configs.SharedConfig("fallback", Config)
STATE = configs.SharedState("fallback", State)
suppressed: Set[int] = set()
driver = nonebot.get_driver()


@run_preprocessor
async def pre_run(state: T_State) -> None:
  if state.get("_as_command", True):
    state["_prefix"]["run"] = True


async def try_send(bot: Bot, user: int, message: str) -> None:
  try:
    await bot.send_private_msg(user_id=user, message=message)
  except ActionFailed:
    pass


@run_postprocessor
async def post_run(bot: Bot, event: MessageEvent, e: Exception) -> None:
  config = CONFIG()

  if isinstance(e, ActionFailed) and e.info.get("msg", None) == "SEND_MSG_API_ERROR":
    reason = "消息发送失败"
    explain = "可能是发送的内容过长、图片过大、含有敏感内容或者机器人帐号被风控。"
  elif isinstance(e, ClientError):
    reason = "网络错误"
    explain = "可能是命令使用的在线 API 不稳定，或者机器人服务器的网络问题。"
  elif isinstance(e, ManualException):
    reason = "管理员手动触发"
    explain = "如果你不是群管理员，可以忽略这个。"
  elif isinstance(e, misc.PromptTimeout):
    reason = "等待回应超时"
    explain = "请及时发送消息回应机器人。"
  else:
    reason = "未知错误"
    explain = "这可能是 IdhagnBot 的设计缺陷，请向开发者寻求帮助。"

  group_id = getattr(event, "group_id", None)
  if config.show_exception[group_id] and group_id not in suppressed:
    markup = '''\
  <span weight='heavy' size='200%'>这个要慌，问题很大</span>
  <span color='#ffffff88'>Something really bad happens. Panic!</span>'''
    header = textutil.render(markup, "sans", 32, color=(255, 255, 255), align="m", markup=True)

    markup = f'''\
<b>IdhagnBot 遇到了一个内部错误。</b>
<span color='#f5f543'>可能原因: </span>{reason}
{explain}'''
    fallback = f"IdhagnBot 遇到了一个内部错误。\n可能原因：{reason}\n{explain}"
    if group_id is not None:
      markup += (
        "\n<span color='#29b8db'>提示: </span>"
        "群管理员可以发送 /suppress true 暂时禁用本群错误消息。"
      )
      fallback += "\n群管理员可以发送 /suppress true 暂时禁用本群错误消息。"
    content = textutil.render(
      markup, "span", 32, color=(255, 255, 255), box=max(640, header.width), markup=True
    )

    size = (max(header.width, content.width) + 64, header.height + content.height + 80)
    im = Image.new("RGB", size, (30, 30, 30))
    im.paste((205, 49, 49), (0, 32, im.width, 32 + header.height))
    imutil.paste(im, header, (im.width // 2, 32), anchor="mt")
    im.paste(content, (32, 48 + header.height), content)
    segment = imutil.to_segment(im)
    try:
      await bot.send(event, segment)
    except ActionFailed:
      await bot.send(event, fallback)

  if not config.send_exception_to_superuser[group_id]:
    return

  user_id = getattr(event, "user_id", None)
  superusers = list(misc.superusers())
  if user_id in superusers:
    return

  exc_type = type(e)
  exc_typename = exc_type.__qualname__
  exc_mod = exc_type.__module__
  if exc_mod not in ("__main__", "builtins"):
    if not isinstance(exc_mod, str):
      exc_mod = "<unknown>"
    exc_typename = exc_mod + '.' + exc_typename
  try:
    exc_info = str(e)
  except Exception:
    exc_info = ""

  message = str(event.message)
  if len(message) > 50:
    message = f"{message[:50]}……（{len(message)}字符）"
  notify = f"机器人出错 - {reason}\n{exc_typename}"
  if exc_info:
    notify += f": {exc_info}"
  notify += f"\n群聊: {group_id}\n用户: {user_id}\n消息: {message}"
  await asyncio.gather(*(try_send(bot, user, notify) for user in superusers))


@event_postprocessor
async def post_event(bot: Bot, event: Event, bot_state: T_State) -> None:
  if not isinstance(event, MessageEvent) or event.user_id == QQBOT_ID:
    return
  group_id = getattr(event, "group_id", -1)
  if group_id in suppressed or "run" in bot_state["_prefix"]:
    return
  config = CONFIG()
  if (
    misc.is_command(event.message)
    and config.show_invaild_command[group_id]
    and not config.has_ignored_prefix(group_id, event.message)
  ):
    await bot.send(event, "命令不存在、权限不足或不适用于当前上下文")
    return
  state = STATE()
  if (
    event.is_tome() and config.show_is_bot[group_id]
    and event.user_id not in state.show_is_bot_disabled
  ):
    await bot.send(
      event, "本帐号为机器人，请发送 /帮助 查看可用命令（可以不@）\n发送 /禁用提示 为你禁用本提示"
    )


# 使用 nonebot.on_command 是为了不显示在帮助里
async def check_disable_show_is_bot(event: Event) -> bool:
  return CONFIG().show_is_bot[event]
disable_show_is_bot = nonebot.on_command("禁用提示", check_disable_show_is_bot)
@disable_show_is_bot.handle()
async def handle_disable_show_is_bot(event: MessageEvent) -> None:
  state = STATE()
  if event.user_id in state.show_is_bot_disabled:
    state.show_is_bot_disabled.remove(event.user_id)
    STATE.dump()
    await disable_show_is_bot.finish("你已恢复“本帐号为机器人”的提示。")
  state.show_is_bot_disabled.add(event.user_id)
  STATE.dump()
  await disable_show_is_bot.finish("你已禁用“本帐号为机器人”的提示，再次发送 /禁用提示 可恢复。")


suppress = (
  command.CommandBuilder("fallback.suppress", "suppress")
  .in_group()
  .level("admin")
  .brief("暂时禁用错误消息")
  .usage('''\
/suppress - 查看是否已禁用本群错误消息
/suppress true - 禁用本群错误消息
/suppress false - 重新启用本群错误消息''')
  .build()
)
@suppress.handle()
async def handle_suppress(bot: Bot, event: MessageEvent, args: Message = CommandArg()) -> None:
  value = str(args).rstrip()
  ctx = context.get_event_context(event)
  if not value:
    status = "已" if ctx in suppressed else "未"
    await suppress.finish(f"本群错误消息{status}被禁用")
  elif value in ("true", "t", "1", "yes", "y", "on"):
    suppressed.add(ctx)
    await suppress.finish("已禁用本群错误消息")
  elif value in ("false", "f", "0", "no", "n", "off"):
    suppressed.remove(ctx)
    await suppress.finish("已恢复本群错误消息")
  await suppress.finish(suppress.__doc__)


raise_ = (
  command.CommandBuilder("fallback.raise", "raise")
  .level("admin")
  .in_group()
  .brief("手动触发一个错误")
  .build()
)
@raise_.handle()
async def handle_raise(args: Message = CommandArg()) -> None:
  if str(args).rstrip() == "confirm":
    raise ManualException
  await raise_.finish("/raise confirm - 手动触发一个错误")


def check_group_recall(event: GroupRecallNoticeEvent):
  return event.self_id == event.user_id and event.operator_id == QQBOT_ID
on_group_recall = nonebot.on_notice(check_group_recall)
@on_group_recall.handle()
def handle_group_recall(event: GroupRecallNoticeEvent) -> None:
  state = STATE()
  today = date.today()
  count, prev = state.qqbot.today
  if prev < today:
    state.qqbot.today = (1, today)
  else:
    state.qqbot.today = (count + 1, prev)
  state.qqbot.total += 1
  count, prev = state.qqbot.today_by_group.get(event.group_id, (0, date.min))
  if prev < today:
    state.qqbot.today_by_group[event.group_id] = (1, today)
  else:
    state.qqbot.today_by_group[event.group_id] = (count + 1, prev)
  total_count = state.qqbot.total_by_group.get(event.group_id, 0)
  state.qqbot.total_by_group[event.group_id] = total_count + 1
  STATE.dump()


query_recall = (
  command.CommandBuilder("fallback.query_recall", "今天被Q群管家针对了吗", "今天被q群管家针对了吗")
  .brief("IdhagnBot今天被Q群管家撤了几次？")
  .build()
)
@query_recall.handle()
async def handle_query_recall(event: Event) -> None:
  ctx = context.get_event_context(event)
  state = STATE()
  today = date.today()
  count, prev = state.qqbot.today
  if prev < today:
    count = 0
  msg = f"全部：今天 {count} / 总计 {state.qqbot.total}"
  if ctx != -1:
    count, prev = state.qqbot.today_by_group.get(ctx, (0, date.min))
    if prev < today:
      count = 0
    total_count = state.qqbot.total_by_group.get(ctx, 0)
    msg += f"\n本群：今天 {count} / 总计 {total_count}"
  await query_recall.finish(msg)
