import asyncio
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, cast

import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.matcher import current_event

__all__ = ["on_message_sent", "MessageSentHook"]

send_event: ContextVar[Event | None] = ContextVar("send_event", default=None)
MessageSentHook = Callable[[Event | None, bool, int, Any, int], Awaitable[None]]
message_sent_hook: list[MessageSentHook] = []
driver = nonebot.get_driver()


@Bot.on_called_api
async def on_called_api(_, e: Exception | None, api: str, params: dict[str, Any], result: Any):
  if e is not None:
    return
  if api in ("send_private_msg", "send_group_msg", "send_msg"):
    message = params["message"]
  elif api in ("send_private_forward_msg", "send_group_forward_msg", "send_forward_msg"):
    message = params["messages"]
  else:
    return
  event = cast(Event, current_event.get(None)) or send_event.get()
  is_group = "group_id" in params
  target_id = params["group_id" if is_group else "user_id"]
  message_id = result["message_id"]
  try:
    await asyncio.gather(*(
      x(event, is_group, target_id, message, message_id) for x in message_sent_hook
    ))
  except Exception:
    logger.exception("执行 on_message_sent 失败！")


async def bot_send(self: Bot, event: Event, message: str | Message | MessageSegment, **kw) -> Any:
  token = send_event.set(event)
  try:
    return await bot_send_original(self, event, message, **kw)
  finally:
    send_event.reset(token)
bot_send_original = Bot.send
Bot.send = bot_send


def on_message_sent(hook: MessageSentHook) -> MessageSentHook:
  message_sent_hook.append(hook)
  return hook