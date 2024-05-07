import asyncio
from datetime import date, timedelta
from typing import List, cast

import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

from util import context

from . import Module

EMOJIS = ["🥇", "🥈", "🥉"]


class RankModule(Module):
  def __init__(self, group_id: int, limit: int) -> None:
    self.group_id = group_id
    self.limit = 10

  async def format(self) -> List[Message]:
    if self.group_id == -1:
      return []  # rank 模块在私聊上下文中不可用
    try:
      from sqlalchemy.ext.asyncio import AsyncSession
      from sqlmodel import col, desc, func, select

      from util import record
    except ImportError:
      logger.warning("没有安装 SQL 相关依赖，不能使用 rank 模块。")
      return []
    today = date.today()
    yesterday = today - timedelta(1)
    async with AsyncSession(record.engine) as session:
      result = await session.execute(
        select(
          record.Received.user_id,
          count_func := func.count(col(record.Received.user_id)),
        )
        .where(
          record.Received.group_id == self.group_id,
          record.Received.time >= yesterday,
          record.Received.time < today,
        )
        .group_by(col(record.Received.user_id))
        .order_by(desc(count_func))
        .limit(self.limit),
      )
    members = list(result)
    if not members:
      return []
    lines = ["昨天最能水的成员："]
    bot = cast(Bot, nonebot.get_bot())
    infos = await asyncio.gather(*(
      context.get_card_or_name(bot, self.group_id, user_id) for user_id, _ in members
    ))
    for i, (name, (_, count)) in enumerate(zip(infos, members)):
      if i < len(EMOJIS):
        prefix = EMOJIS[i]
      else:
        prefix = f"{i + 1}."
      lines.append(f"{prefix} {name} - {count} 条")
    return [Message(MessageSegment.text("\n".join(lines)))]
