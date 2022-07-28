import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, cast

import nonebot
from nonebot.adapters.onebot.v11 import (
  Bot, Event, FriendRecallNoticeEvent, GroupRecallNoticeEvent, Message, MessageEvent,
  MessageSegment)
from nonebot.adapters.onebot.v11.event import Reply
from nonebot.exception import ActionFailed
from nonebot.matcher import current_event
from nonebot.params import EventMessage
from nonebot.typing import T_State

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


async def try_delete_msg(bot: Bot, id: int):
  try:
    await bot.delete_msg(message_id=id)
  except ActionFailed:
    pass


async def manual_recall_rule(event: MessageEvent, msg: Message = EventMessage()) -> bool:
  if event.reply is None:
    return False
  return (
    event.reply.sender.user_id == event.self_id
    and msg.extract_plain_text().strip() in ("撤", "撤回"))

manual_recall = nonebot.on_message(manual_recall_rule)


@manual_recall.handle()
async def handle_manual_recall(bot: Bot, event: MessageEvent, state: T_State):
  state["_prefix"]["special"] = True
  try:
    await bot.delete_msg(message_id=cast(Reply, event.reply).message_id)
  except ActionFailed:
    await manual_recall.finish("撤回失败，可能已超过两分钟、已经被撤回，或者不支持这种消息")
  try:
    await bot.delete_msg(message_id=event.message_id)
  except ActionFailed:
    pass

messages: dict[int, set[int]] = {}
driver = nonebot.get_driver()
bot_send_original = Bot.send
AnyRecallNoticeEvent = GroupRecallNoticeEvent | FriendRecallNoticeEvent


def remove_message(id: int):
  if id in messages:
    del messages[id]


def add_message(event: MessageEvent, api_result: dict[str, Any]):
  recall_remaining = 120 - (time.time() - event.time)
  if event.message_id not in messages and recall_remaining > 0:
    messages[event.message_id] = set()
    scheduler.add_job(
      remove_message, "date", (event.message_id,),
      run_date=datetime.now() + timedelta(seconds=recall_remaining))
  if event.message_id in messages and api_result["message_id"] != 0:
    messages[event.message_id].add(api_result["message_id"])


@driver.on_bot_connect
async def on_bot_connect(bot: Bot):
  async def on_called_api(_, e: Exception | None, api: str, params: dict[str, Any], result: Any):
    event = current_event.get(None)
    if isinstance(event, MessageEvent) and event.message_id != 0 and e is None and api in (
        "send_private_msg", "send_group_msg", "send_msg",
        "send_private_forward_msg", "send_group_forward_msg", "send_forward_msg"
    ):
      add_message(event, result)
  bot.on_called_api(on_called_api)


async def bot_send(self: Bot, event: Event, message: str | Message | MessageSegment, **kw) -> Any:
  result = await bot_send_original(self, event, message, **kw)
  if isinstance(event, MessageEvent) and event.message_id != 0:
    add_message(event, result)
  return result
Bot.send = bot_send


async def rule_auto_recall(event: AnyRecallNoticeEvent):
  return event.message_id in messages


on_auto_recall = nonebot.on_notice(rule_auto_recall)


@on_auto_recall.handle()
async def handle_auto_recall(bot: Bot, event: AnyRecallNoticeEvent):
  coros = []
  for message in messages[event.message_id]:
    coros.append(try_delete_msg(bot, message))
  await asyncio.gather(*coros)
  del messages[event.message_id]
