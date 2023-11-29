import asyncio
from typing import Optional, cast

import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import (
  Bot, Event, GroupMessageEvent, GroupRecallNoticeEvent, Message
)
from nonebot.adapters.onebot.v11.event import Reply
from nonebot.exception import ActionFailed, MockApiException
from nonebot.typing import T_State

from util import context, hook, permission

from .common import has_keyword, recall_others_permission, schedule_delete, try_delete_msg

try:
  from .sql import Record
except ImportError:
  logger.warning("未安装 SQL 相关依赖，recall 功能受限")
  from .memory import Record


def manual_recall_rule(event: GroupMessageEvent) -> bool:
  return has_keyword(event, "撤", "撤回")

manual_recall = nonebot.on_message(
  manual_recall_rule,
  context.build_permission(("recall", "manual_recall", "single"), permission.Level.MEMBER)
)

@manual_recall.handle()
async def handle_manual_recall(bot: Bot, event: GroupMessageEvent) -> None:
  if (
    not await recall_others_permission(bot, event)
    and not await record.is_caused_by(cast(Reply, event.reply).message_id, event.user_id)
  ):
    result = await manual_recall.send(
      "你没有权限撤回这条消息。\n"
      "这条消息将在 30 秒后自动撤回。"
    )
    schedule_delete(bot, result["message_id"], 30)
    return
  try:
    await bot.delete_msg(message_id=cast(Reply, event.reply).message_id)
  except ActionFailed:
    result = await manual_recall.send(
      "撤回失败，可能已超过两分钟、已经被撤回，或者不支持这种消息。\n"
      "这条消息将在 30 秒后自动撤回。"
    )
    schedule_delete(bot, result["message_id"], 30)
  await try_delete_msg(bot, event.message_id)


driver = nonebot.get_driver()
record = Record()


async def rule_auto_recall(event: GroupRecallNoticeEvent, state: T_State) -> bool:
  return await record.has(event, state)

on_auto_recall = nonebot.on(
  "notice",
  rule_auto_recall,
  context.build_permission(("recall", "auto_recall"), permission.Level.MEMBER)
)

@on_auto_recall.handle()
async def handle_auto_recall(bot: Bot, event: GroupRecallNoticeEvent, state: T_State) -> None:
  coros = []
  async for message in record.get(event, state):
    coros.append(try_delete_msg(bot, message))
  await asyncio.gather(*coros)


@hook.on_message_sending
async def on_calling_api(
  event: Optional[Event], is_group: bool, target_id: int, message: Message
) -> None:
  if isinstance(event, GroupMessageEvent):
    if await record.is_deleted(event.message_id):
      raise MockApiException({"message_id": 0})
