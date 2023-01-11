import asyncio
from typing import cast

import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, GroupRecallNoticeEvent, Message, MessageEvent
from nonebot.adapters.onebot.v11.event import Reply
from nonebot.exception import ActionFailed
from nonebot.params import EventMessage
from nonebot.typing import T_State

from util import context, permission

try:
  from .sql import Record
except ImportError:
  logger.warning("未安装 SQL 相关依赖，recall 功能受限")
  from .memory import Record


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
    and msg.extract_plain_text().strip() in ("撤", "撤回")
  )
manual_recall = nonebot.on_message(
  manual_recall_rule,
  context.build_permission(("recall", "manual_recall"), permission.Level.MEMBER)
)
@manual_recall.handle()
async def handle_manual_recall(bot: Bot, event: MessageEvent) -> None:
  try:
    await bot.delete_msg(message_id=cast(Reply, event.reply).message_id)
  except ActionFailed:
    await manual_recall.send("撤回失败，可能已超过两分钟、已经被撤回，或者不支持这种消息")
  try:
    await bot.delete_msg(message_id=event.message_id)
  except ActionFailed:
    pass


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
