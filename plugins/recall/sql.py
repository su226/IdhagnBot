from typing import AsyncGenerator

from nonebot.typing import T_State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from util import record


class Record:
  async def has(self, message_id: int, state: T_State) -> bool:
    async with AsyncSession(record.engine) as session:
      result = await session.execute(
        select(record.Sent.message_id).where(record.Sent.caused_by == message_id))
    if (rows := result.all()):
      state["sql_result"] = rows
      return True
    return False

  async def get(self, message_id: int, state: T_State) -> AsyncGenerator[int, None]:
    for message_id, in state["sql_result"]:
      yield message_id
