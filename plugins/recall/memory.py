from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Optional, Set

import nonebot
from nonebot.adapters.onebot.v11 import Event, Message, MessageEvent
from nonebot.typing import T_State

from util import hook

nonebot.require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


class Record:
  def __init__(self) -> None:
    hook.on_message_sent(self.on_message_sent)
    self.messages: Dict[int, Set[int]] = {}

  async def on_message_sent(
    self, event: Optional[Event], is_group: bool, target_id: int, message: Message, message_id: int
  ) -> None:
    if isinstance(event, MessageEvent) and event.message_id and message_id:
      recall_time = datetime.fromtimestamp(event.time) + timedelta(seconds=120)
      if event.message_id not in self.messages and recall_time > datetime.now():
        self.messages[event.message_id] = set()
        scheduler.add_job(self.remove_message, "date", (event.message_id,), run_date=recall_time)
      if event.message_id in self.messages:
        self.messages[event.message_id].add(message_id)

  def remove_message(self, id: int) -> None:
    if id in self.messages:
      del self.messages[id]

  async def has(self, message_id: int, state: T_State) -> bool:
    return message_id in self.messages

  async def get(self, message_id: int, state: T_State) -> AsyncGenerator[int, None]:
    for i in self.messages[message_id]:
      yield i  # 异步函数不能yield from
    self.remove_message(message_id)
