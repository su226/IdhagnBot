import asyncio
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

import nonebot
from loguru import logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.exception import MockApiException
from nonebot.matcher import current_event
from pydantic import TypeAdapter

from . import misc

__all__ = ["on_message_sending", "on_message_sent", "MessageSendingHook", "MessageSentHook"]

send_event: ContextVar[Optional[Event]] = ContextVar("send_event", default=None)
MessageSendingHook = Callable[[Optional[Event], bool, int, Message], Awaitable[None]]
MessageSentHook = Callable[[Optional[Event], bool, int, Message, int], Awaitable[None]]
MessageSendFailedHook = Callable[[Optional[Event], bool, int, Message, Exception], Awaitable[None]]
message_sending_hook: List[MessageSendingHook] = []
message_sent_hook: List[MessageSentHook] = []
message_send_failed_hook: List[MessageSendFailedHook] = []
driver = nonebot.get_driver()


def normalize_message(raw: Any) -> Message:
  if isinstance(raw, Message):
    message = raw
  elif isinstance(raw, MessageSegment):
    message = Message(raw)
  else:
    message = TypeAdapter(Message).validate_python(raw)
  for seg in message:
    if seg.type == "node" and "content" in seg.data:
      seg.data["content"] = normalize_message(seg.data["content"])
  return message


@BaseBot.on_calling_api
async def on_calling_api(bot: BaseBot, api: str, params: Dict[str, Any]) -> None:
  if not message_sending_hook or not isinstance(bot, Bot):
    return
  if api in ("send_private_msg", "send_group_msg", "send_msg"):
    message = params["message"]
  elif api in ("send_private_forward_msg", "send_group_forward_msg", "send_forward_msg"):
    message = params["messages"]
  else:
    return
  message = normalize_message(message)
  event = cast(Event, current_event.get(None)) or send_event.get()
  is_group = "group_id" in params
  target_id = params["group_id" if is_group else "user_id"]
  try:
    await asyncio.gather(*(
      x(event, is_group, target_id, message) for x in message_sending_hook
    ))
  except MockApiException:
    raise
  except Exception:
    logger.exception("执行 on_message_sending 失败！")


@BaseBot.on_called_api
async def on_called_api(
  bot: BaseBot, e: Optional[Exception], api: str, params: Dict[str, Any], result: Any,
) -> None:
  if e is None:
    if not message_sent_hook:
      return
  else:
    if not message_send_failed_hook:
      return
  if not isinstance(bot, Bot):
    return
  if api in ("send_private_msg", "send_group_msg", "send_msg"):
    message = params["message"]
  elif api in ("send_private_forward_msg", "send_group_forward_msg", "send_forward_msg"):
    message = params["messages"]
  else:
    return
  message = normalize_message(message)
  event = cast(Event, current_event.get(None)) or send_event.get()
  is_group = "group_id" in params
  target_id = params["group_id" if is_group else "user_id"]
  message_id = result["message_id"]
  try:
    if e is None:
      await asyncio.gather(*(
        x(event, is_group, target_id, message, message_id) for x in message_sent_hook
      ))
    else:
      await asyncio.gather(*(
        x(event, is_group, target_id, message, e) for x in message_send_failed_hook
      ))
  except MockApiException:
    raise
  except Exception:
    name = "on_message_sent" if e is None else "on_message_send_failed"
    logger.exception(f"执行 {name} 失败！")


async def bot_send(self: Bot, event: Event, message: misc.AnyMessage, **kw: Any) -> Any:
  token = send_event.set(event)
  try:
    return await bot_send_original(self, event, message, **kw)
  finally:
    send_event.reset(token)
bot_send_original = Bot.send
Bot.send = bot_send


def on_message_sending(hook: MessageSendingHook) -> MessageSendingHook:
  message_sending_hook.append(hook)
  return hook


def on_message_sent(hook: MessageSentHook) -> MessageSentHook:
  message_sent_hook.append(hook)
  return hook


def on_message_send_failed(hook: MessageSendFailedHook) -> MessageSendFailedHook:
  message_send_failed_hook.append(hook)
  return hook
