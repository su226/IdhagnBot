from typing import AsyncGenerator

from nonebot.adapters.onebot.v11 import GroupRecallNoticeEvent
from nonebot.typing import T_State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from util import record


class Record:
  async def has(self, event: GroupRecallNoticeEvent, state: T_State) -> bool:
    async with AsyncSession(record.engine) as session:
      result = await session.execute(select(record.Sent.message_id).where(
        record.Sent.caused_by == event.message_id,
        record.Sent.is_group == True,  # noqa
        record.Sent.target_id == event.group_id
      ))
    if (rows := result.all()):
      state["sql_result"] = rows
      return True
    return False

  async def get(self, event: GroupRecallNoticeEvent, state: T_State) -> AsyncGenerator[int, None]:
    for message_id, in state["sql_result"]:
      yield message_id
