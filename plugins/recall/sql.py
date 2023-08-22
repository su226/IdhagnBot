import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Tuple, cast

import nonebot
from nonebot.adapters.onebot.v11 import (
  ActionFailed, Bot, GroupMessageEvent, GroupRecallNoticeEvent
)
from nonebot.adapters.onebot.v11.event import Reply
from nonebot.typing import T_State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from util import context, permission, record

from .common import (
  AutoDeleteDict, has_keyword, recall_others_permission, schedule_delete, try_delete_msg
)


class Record:
  async def has(self, event: GroupRecallNoticeEvent, state: T_State) -> bool:
    async with AsyncSession(record.engine) as session:
      result = await session.execute(select(record.Sent.message_id).where(
        record.Sent.caused_by == event.message_id,
        record.Sent.is_group == True,  # noqa
        record.Sent.target_id == event.group_id
      ))
    if (rows := result.scalars().all()):
      state["sql_result"] = rows
      return True
    return False

  async def get(self, event: GroupRecallNoticeEvent, state: T_State) -> AsyncGenerator[int, None]:
    for message_id in state["sql_result"]:
      yield message_id

  async def is_caused_by(self, message_id: int, user_id: int) -> bool:
    async with AsyncSession(record.engine) as session:
      result = await session.execute(select(cast(Any, record.Sent.caused_by)).where(
        record.Sent.message_id == message_id,
      ))
      caused_by = result.scalar()
      if caused_by is None:
        return False
      result = await session.execute(select(record.Received.user_id).where(
        record.Received.message_id == caused_by
      ))
    return result.scalar() == user_id


batch_recall_permission = context.build_permission(
  ("recall", "manual_recall", "batch"), permission.Level.MEMBER
)
recall_dates = AutoDeleteDict[Tuple[int, int], datetime](600)


def recall_begin_rule(event: GroupMessageEvent) -> bool:
  return has_keyword(event, "从这撤回")

recall_begin = nonebot.on_message(recall_begin_rule, batch_recall_permission)

@recall_begin.handle()
async def handle_recall_begin(bot: Bot, event: GroupMessageEvent) -> None:
  recall_dates[event.group_id, event.user_id] = datetime.fromtimestamp(
    cast(Reply, event.reply).time
  )
  await try_delete_msg(bot, event.message_id)


def recall_end_rule(event: GroupMessageEvent) -> bool:
  return has_keyword(event, "撤回到这") and (event.group_id, event.user_id) in recall_dates

recall_end = nonebot.on_message(recall_end_rule, batch_recall_permission)

@recall_end.handle()
async def handle_recall_end(bot: Bot, event: GroupMessageEvent) -> None:
  can_recall_others = await recall_others_permission(bot, event)
  begin_time = recall_dates[event.group_id, event.user_id]
  end_time = datetime.fromtimestamp(cast(Reply, event.reply).time + 1)

  async with AsyncSession(record.engine) as session:
    result = await session.execute(select(
      record.Sent.message_id,
      cast(Any, record.Sent.caused_by),
    ).where(
      record.Sent.time >= begin_time,
      record.Sent.time <= end_time,
    ))

    succeed = 0
    failed = 0
    forbidden = 0

    async def delete_one(message_id: int, caused_by: int) -> None:
      if not can_recall_others:
        result = await session.execute(select(record.Received.user_id).where(
          record.Received.message_id == caused_by,
        ))
        if result.scalar() != event.user_id:
          nonlocal forbidden
          forbidden += 1
          return
      try:
        await bot.delete_msg(message_id=message_id)
        nonlocal succeed
        succeed += 1
      except ActionFailed:
        nonlocal failed
        failed += 1

    await asyncio.gather(*[
      delete_one(message_id, caused_by) for message_id, caused_by in result.all()
    ])

  msg = f"成功撤回 {succeed} 条消息"
  if failed:
    msg += f"，{failed} 条消息撤回失败"
  if forbidden:
    msg += f"，{forbidden} 条消息你不能撤回"

  result = await recall_end.send(f"{msg}。\n这条消息将在 30 秒后自动撤回。")
  schedule_delete(bot, result["message_id"], 30)

  await try_delete_msg(bot, event.message_id)
