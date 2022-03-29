from typing import Any, cast
from datetime import datetime, timedelta
from apscheduler.schedulers.base import BaseScheduler
from nonebot.adapters.onebot.v11 import Bot, Event, MessageEvent, NoticeEvent, GroupRecallNoticeEvent, FriendRecallNoticeEvent, Message, MessageSegment
from nonebot.params import EventMessage
from nonebot.matcher import current_event
import asyncio
import nonebot
import time

scheduler = cast(BaseScheduler, nonebot.require("nonebot_plugin_apscheduler").scheduler)

async def manual_recall_rule(event: MessageEvent, msg: Message = EventMessage()) -> bool:
  return event.reply and event.reply.sender.user_id == event.self_id and msg.extract_plain_text().strip() == "撤"

manual_recall = nonebot.on_message(manual_recall_rule)
@manual_recall.handle()
async def handle_manual_recall(bot: Bot, event: MessageEvent):
  try:
    await bot.delete_msg(message_id=event.reply.message_id)
  except:
    await manual_recall.send("撤回失败，可能已超过两分钟、已经被撤回，或者不支持这种消息")

messages: dict[int, set[int]] = {}

def remove_message(id: int):
  if id in messages:
    del messages[id]

def add_message(event: MessageEvent, api_result: dict[str, Any]):
  recall_remaining = 120 - (time.time() - event.time)
  print("add mapping", event.message_id, api_result["message_id"])
  if event.message_id not in messages and recall_remaining > 0:
    messages[event.message_id] = set()
    scheduler.add_job(remove_message, "date", (event.message_id,), run_date=datetime.now() + timedelta(seconds=recall_remaining))
  if event.message_id in messages and api_result["message_id"] != 0:
    messages[event.message_id].add(api_result["message_id"])

driver = nonebot.get_driver()
@driver.on_bot_connect
def on_bot_connect(bot: Bot):
  async def on_called_api(bot: Bot, e: Exception | None, api: str, params: dict[str, Any], result: Any):
    event = current_event.get(None)
    if (
      isinstance(event, MessageEvent) and event.message_id != 0 and
      api in ("send_private_msg", "send_group_msg", "send_group_forward_msg", "send_msg")
    ):
      add_message(event, result)
  bot.on_called_api(on_called_api)

bot_send_original = Bot.send
async def bot_send(bot: Bot, event: Event, message: str | Message | MessageSegment, **kw) -> Any:
  result = await bot_send_original(bot, event, message, **kw)
  if isinstance(event, MessageEvent) and event.message_id != 0:
    add_message(event, result)
  return result
Bot.send = bot_send

AnyRecallNoticeEvent = GroupRecallNoticeEvent | FriendRecallNoticeEvent
async def rule_auto_recall(event: NoticeEvent):
  return isinstance(event, AnyRecallNoticeEvent) and event.message_id in messages

async def try_delete_msg(bot: Bot, id: int):
  try:
    await bot.delete_msg(message_id=id)
  except:
    pass

on_auto_recall = nonebot.on_notice(rule_auto_recall)
@on_auto_recall.handle()
async def handle_auto_recall(bot: Bot, event: AnyRecallNoticeEvent):
  coros = []
  for message in messages[event.message_id]:
    coros.append(try_delete_msg(bot, message))
  await asyncio.gather(*coros)
  del messages[event.message_id]
