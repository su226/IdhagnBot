from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional, Set

from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, GroupRecallNoticeEvent, Message
from nonebot.message import event_preprocessor
from nonebot.typing import T_State

from util import hook

from .common import AutoDeleteDict


class Record:
  def __init__(self) -> None:
    hook.on_message_sent(self._on_message_sent)
    event_preprocessor(self._on_delete_event)
    self._results = AutoDeleteDict[int, Set[int]](120)
    self._caused_by = AutoDeleteDict[int, int](120)
    self._deleted = AutoDeleteDict[int, None](120)

  async def _on_message_sent(
    self, event: Optional[Event], is_group: bool, target_id: int, message: Message, message_id: int
  ) -> None:
    if not (
      message_id
      and isinstance(event, GroupMessageEvent)
      and is_group
      and event.group_id == target_id
    ):
      return
    self._caused_by[message_id] = event.user_id
    if event.message_id:
      recall_time = datetime.fromtimestamp(event.time) + timedelta(seconds=120)
      if event.message_id not in self._results and recall_time > datetime.now():
        self._results[event.message_id] = set()
      if event.message_id in self._results:
        self._results[event.message_id].add(message_id)
  
  async def _on_delete_event(self, event: Optional[Event]) -> None:
    if not isinstance(event, GroupRecallNoticeEvent):
      return
    self._deleted[event.message_id] = None

  def _remove_result(self, id: int) -> None:
    if id in self._results:
      del self._results[id]

  def _remove_caused_by(self, id: int) -> None:
    if id in self._caused_by:
      del self._caused_by[id]

  async def has(self, event: GroupRecallNoticeEvent, state: T_State) -> bool:
    return event.message_id in self._results

  async def get(self, event: GroupRecallNoticeEvent, state: T_State) -> AsyncGenerator[int, None]:
    for i in self._results[event.message_id]:
      yield i  # 异步函数不能yield from
    self._remove_result(event.message_id)

  async def is_caused_by(self, message_id: int, user_id: int) -> bool:
    return self._caused_by.get(message_id) == user_id
  
  async def is_deleted(self, message_id: int) -> bool:
    return message_id in self._deleted
